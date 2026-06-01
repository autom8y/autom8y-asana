#!/usr/bin/env python3
# ruff: noqa: TID251
"""Deploy-gate canary probe for receiver-bulk-fanout-reliability Stage-1.

Exercises the production bulk-fan-out pattern (sustained N req/min over a
window) against the deployed receiver and reports whether the deploy-gate
criteria are met:

  * receiver_query_success_rate_project    >= 0.99 (sustained over the window)
  * receiver_query_success_rate_section    >= 0.99 (sustained over the window)
  * rate_limit_429_rate_sa                 == 0    (no SA-namespace 429s)

The probe pattern matches CR-3 consumer behavior: bulk fan-out at the
receiver, not steady-state interactive traffic. Default load mirrors the
Phase-3 Knob-5 derivation (~100 rpm baseline; 10-minute window).

Authentication:
  * If RECEIVER_DEPLOY_GATE_TOKEN is set in the environment, used verbatim.
  * Otherwise mints a JWT via autom8y_core.TokenManager (matches the SA
    pattern at scripts/smoke_test_api.py:125-146). Requires
    SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET to be set.

The probe DOES NOT need direct access to receiver-side counters. It infers
success-rate by per-call HTTP status: 2xx = success; 5xx = server_error;
429 on the SA arm = SA-namespace rate-limit signal. 4xx-non-429 (e.g., 422
validation, 404 not-found) are CLIENT errors per the receiver mirror SLI
definition (api/routes/query.py:478-484); they are reported separately and
do not count against the success rate.

Usage:
  .venv/bin/python scripts/canary/receiver_bulk_fanout_deploy_gate.py \
      --base-url https://asana.api.autom8y.io \
      --project-gid 1234567890 \
      --duration-minutes 10 \
      --target-rpm 100

  # Smoke (60s, lower rpm) for local verification:
  .venv/bin/python scripts/canary/receiver_bulk_fanout_deploy_gate.py \
      --base-url http://localhost:5300 \
      --project-gid 1234567890 \
      --duration-minutes 1 \
      --target-rpm 30

Exit codes:
  0 = deploy-gate PASS (all three criteria met)
  1 = deploy-gate FAIL (any criterion missed)
  2 = pre-flight error (missing config, can't acquire token, etc.)

Cross-references:
  - Sprint-1 PR description "Test plan" (.ledge/spikes/HANDOFF-...) lists this
    probe as the deploy-gate enforcement mechanism.
  - .sos/wip/thermia/observability-plan.md §Deploy gate criterion (referenced
    implementation: this script).
  - qa-adversary FG-3 fix 2026-05-31: the conjoint gate (success-rate AND
    no-SA-429) cannot fire without an enforcement probe; this script is
    that probe.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import httpx

# Default values match observability-plan.md §Deploy gate criterion.
DEFAULT_BASE_URL = "https://asana.api.autom8y.io"
DEFAULT_DURATION_MINUTES = 10
DEFAULT_TARGET_RPM = 100
DEFAULT_SUCCESS_RATE_THRESHOLD = 0.99


# ---------------------------------------------------------------------------
# Result aggregation
# ---------------------------------------------------------------------------


@dataclass
class ArmResults:
    """Per-arm probe results (project / section)."""

    arm: str
    total_calls: int = 0
    successes: int = 0  # 2xx
    server_errors: int = 0  # 5xx
    client_errors: int = 0  # 4xx-non-429
    rate_limited: int = 0  # 429
    durations_ms: list[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Receiver mirror SLI: success / (success + server_error).

        Per api/routes/query.py:478-484: 4xx are excluded (client error,
        not receiver health). 429 is also excluded — it has its own
        deploy-gate signal (rate_limit_429_rate_sa).
        """
        denom = self.successes + self.server_errors
        if denom == 0:
            return 0.0
        return self.successes / denom

    @property
    def p50_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        s = sorted(self.durations_ms)
        return s[len(s) // 2]

    @property
    def p99_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        s = sorted(self.durations_ms)
        idx = max(0, int(len(s) * 0.99) - 1)
        return s[idx]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _acquire_token() -> str:
    """Acquire a bearer token for the SA-canary identity.

    Resolution order (matches scripts/smoke_test_api.py:125-146 pattern):
      1. RECEIVER_DEPLOY_GATE_TOKEN env var (operator override).
      2. autom8y_core.TokenManager from SERVICE_CLIENT_ID +
         SERVICE_CLIENT_SECRET (standard SA convention).

    Raises SystemExit(2) on pre-flight failure.
    """
    env_token = os.environ.get("RECEIVER_DEPLOY_GATE_TOKEN")
    if env_token:
        print(f"[auth] Using RECEIVER_DEPLOY_GATE_TOKEN (len={len(env_token)})")
        return env_token

    try:
        from autom8y_core import Config, TokenManager  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[auth] FATAL: autom8y_core not importable AND "
            "RECEIVER_DEPLOY_GATE_TOKEN not set. Install autom8y_core or "
            "supply a token via env var.",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        config = Config.from_env()
    except ValueError as e:
        print(
            f"[auth] FATAL: Config.from_env() failed: {e}. "
            "Set SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET (SA convention) "
            "or supply RECEIVER_DEPLOY_GATE_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        manager = TokenManager(config)
        token = manager.get_token()
        manager.close()
        print(f"[auth] JWT acquired via TokenManager (len={len(token)})")
        return token
    except Exception as e:  # noqa: BLE001
        print(f"[auth] FATAL: JWT exchange failed: {e}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------


async def _one_call(
    client: httpx.AsyncClient,
    base_url: str,
    arm: str,
    project_gid: str,
    token: str,
) -> tuple[int, float]:
    """Issue one POST /v1/query/{arm}/rows call. Returns (status_code, ms)."""
    url = f"{base_url.rstrip('/')}/v1/query/{arm}/rows"
    # Minimal valid body for body-parameterized entities: project_gid + small limit.
    # 'section' arm requires a section identifier; we pass the project_gid in
    # both places — the receiver treats project as the parameterizing entity.
    body: dict[str, Any] = {
        "project_gid": project_gid,
        "limit": 1,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    start = time.perf_counter()
    try:
        resp = await client.post(url, json=body, headers=headers, timeout=30.0)
        status = resp.status_code
    except httpx.RequestError as e:
        # Network-class errors count as server-side failure (5xx-equivalent
        # for the mirror SLI — the receiver did not respond).
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[probe] {arm} network error: {e}", file=sys.stderr)
        return (599, elapsed_ms)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return (status, elapsed_ms)


async def _run_arm(
    client: httpx.AsyncClient,
    base_url: str,
    arm: str,
    project_gid: str,
    token: str,
    target_rpm: int,
    duration_seconds: int,
) -> ArmResults:
    """Run sustained load against one arm for the configured duration.

    Issues `target_rpm` requests-per-minute as a steady drip — i.e., one
    request every (60 / target_rpm) seconds. NOT a burst-then-quiet pattern;
    this matches the consumer's actual fan-out shape (regular outbound calls).
    """
    results = ArmResults(arm=arm)
    interval_s = 60.0 / max(target_rpm, 1)
    end_time = time.monotonic() + duration_seconds

    while time.monotonic() < end_time:
        loop_start = time.monotonic()
        status, ms = await _one_call(client, base_url, arm, project_gid, token)
        results.total_calls += 1
        results.durations_ms.append(ms)
        if 200 <= status < 300:
            results.successes += 1
        elif status == 429:
            results.rate_limited += 1
        elif 400 <= status < 500:
            results.client_errors += 1
        elif status >= 500:
            results.server_errors += 1
        # Pacing: sleep to next interval boundary if there's slack.
        slack = interval_s - (time.monotonic() - loop_start)
        if slack > 0:
            await asyncio.sleep(slack)

    return results


# ---------------------------------------------------------------------------
# Reporting / gate decision
# ---------------------------------------------------------------------------


def _print_arm_report(r: ArmResults) -> None:
    print(f"  arm={r.arm}")
    print(f"    total_calls         = {r.total_calls}")
    print(f"    successes (2xx)     = {r.successes}")
    print(f"    server_errors (5xx) = {r.server_errors}")
    print(f"    client_errors (4xx) = {r.client_errors}")
    print(f"    rate_limited (429)  = {r.rate_limited}")
    print(f"    success_rate        = {r.success_rate:.4f}")
    print(f"    p50_ms              = {r.p50_ms:.1f}")
    print(f"    p99_ms              = {r.p99_ms:.1f}")


def _evaluate_gate(
    project: ArmResults,
    section: ArmResults,
    success_threshold: float,
) -> tuple[bool, list[str]]:
    """Evaluate the three deploy-gate criteria. Returns (pass, reasons)."""
    failures: list[str] = []

    if project.success_rate < success_threshold:
        failures.append(
            f"project success_rate={project.success_rate:.4f} < "
            f"{success_threshold:.2f} threshold"
        )
    if section.success_rate < success_threshold:
        failures.append(
            f"section success_rate={section.success_rate:.4f} < "
            f"{success_threshold:.2f} threshold"
        )

    total_sa_429 = project.rate_limited + section.rate_limited
    if total_sa_429 > 0:
        failures.append(
            f"SA-namespace 429 count={total_sa_429} > 0 "
            f"(project={project.rate_limited}, section={section.rate_limited}); "
            f"rate_limit_429_rate_sa must equal 0"
        )

    return (len(failures) == 0, failures)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def _main_async(args: argparse.Namespace) -> int:
    token = _acquire_token()
    duration_seconds = int(args.duration_minutes * 60)

    print(
        f"[probe] base_url={args.base_url} project_gid={args.project_gid} "
        f"duration={args.duration_minutes}m target_rpm={args.target_rpm} "
        f"success_threshold={args.success_threshold:.2f}"
    )

    async with httpx.AsyncClient(http2=False) as client:
        # Run both arms concurrently — matches the consumer's fan-out shape.
        project_task = asyncio.create_task(
            _run_arm(
                client,
                args.base_url,
                "project",
                args.project_gid,
                token,
                args.target_rpm,
                duration_seconds,
            )
        )
        section_task = asyncio.create_task(
            _run_arm(
                client,
                args.base_url,
                "section",
                args.project_gid,
                token,
                args.target_rpm,
                duration_seconds,
            )
        )
        project_result, section_result = await asyncio.gather(
            project_task, section_task
        )

    print("\n=== Results ===")
    _print_arm_report(project_result)
    _print_arm_report(section_result)

    passed, failures = _evaluate_gate(
        project_result, section_result, args.success_threshold
    )

    print("\n=== Deploy-gate decision ===")
    if passed:
        print("  STATUS: PASS")
        print("  All criteria met:")
        print(f"    receiver_query_success_rate_project >= {args.success_threshold:.2f}")
        print(f"    receiver_query_success_rate_section >= {args.success_threshold:.2f}")
        print("    rate_limit_429_rate_sa == 0")
        return 0
    else:
        print("  STATUS: FAIL")
        for f in failures:
            print(f"    - {f}")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Receiver bulk-fanout deploy-gate canary probe."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Receiver base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--project-gid",
        required=True,
        help="Asana project GID to query against (body-parameterized arm input)",
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        default=DEFAULT_DURATION_MINUTES,
        help=f"Probe duration in minutes (default: {DEFAULT_DURATION_MINUTES})",
    )
    parser.add_argument(
        "--target-rpm",
        type=int,
        default=DEFAULT_TARGET_RPM,
        help=(
            f"Target requests-per-minute per arm (default: {DEFAULT_TARGET_RPM}; "
            "matches Phase-3 Knob-5 SA bulk-pass peak)"
        ),
    )
    parser.add_argument(
        "--success-threshold",
        type=float,
        default=DEFAULT_SUCCESS_RATE_THRESHOLD,
        help=(
            f"Mirror SLI success-rate threshold (default: {DEFAULT_SUCCESS_RATE_THRESHOLD}; "
            "matches observability-plan.md deploy gate)"
        ),
    )
    args = parser.parse_args()

    try:
        rc = asyncio.run(_main_async(args))
    except KeyboardInterrupt:
        print("\n[probe] Interrupted by user.", file=sys.stderr)
        sys.exit(130)
    sys.exit(rc)


if __name__ == "__main__":
    # Counter imported for potential future per-status-code histograms;
    # keep the import to signal intent for follow-up enrichment.
    _ = Counter
    main()
