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
  * Else if Config.from_env() succeeds (reads AUTOM8Y_DATA_SERVICE_CLIENT_ID
    / CLIENT_ID and the matching _SECRET aliases per ADR-ENV-NAMING-CONVENTION
    Decision 4), mints a JWT via autom8y_core.TokenManager. This matches the
    SA pattern at scripts/smoke_test_api.py:125-146.
  * Else falls back to fetching SA credentials from AWS SSM + Secrets Manager
    (canonical provisioning path — mirrors the receiver runtime):
        SSM /autom8y/platform/asana-dataframe-resolver/oauth-client-id
            -> raw client_id (String parameter)
        SSM /autom8y/platform/asana-dataframe-resolver/oauth-client-secret-path
            -> pointer to SM secret name (e.g. "autom8y/asana-dataframe-resolver")
        SM <pointer>
            -> JSON envelope {"client_id":"sa_...","client_secret":"a8sa_..."}
    Resolved (client_id, client_secret) are passed to TokenManager. Requires
    boto3 in the runtime and AWS credentials available (AWS_PROFILE / IAM role).

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
import json
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

# Canonical provisioning paths for the asana-dataframe-resolver SA credentials.
# These mirror what the receiver runtime reads at startup (the "hermes pattern"):
#
#   SSM /autom8y/platform/asana-dataframe-resolver/oauth-client-id
#       String parameter; value is the raw client_id (e.g. "sa_1a95b...").
#   SSM /autom8y/platform/asana-dataframe-resolver/oauth-client-secret-path
#       String parameter; value is a pointer to the Secrets Manager secret
#       name (e.g. "autom8y/asana-dataframe-resolver").
#   SM  <pointer-value>
#       JSON envelope: {"client_id": "sa_...", "client_secret": "a8sa_..."}.
#       Only the "client_secret" field is consumed by this script; the
#       client_id in the envelope is treated as a cross-check against SSM.
#
# Region is pinned to us-east-1 — the SSM/SM resources live in that region
# regardless of the caller's default boto3 region.
SSM_OAUTH_CLIENT_ID_PATH = "/autom8y/platform/asana-dataframe-resolver/oauth-client-id"
SSM_OAUTH_CLIENT_SECRET_POINTER_PATH = (
    "/autom8y/platform/asana-dataframe-resolver/oauth-client-secret-path"
)
SSM_SM_REGION = "us-east-1"


def _resolve_sa_credentials_from_aws() -> tuple[str, str] | None:
    """Fetch (client_id, client_secret) for the SA from SSM + Secrets Manager.

    Returns None if boto3 is unavailable or any AWS call fails — caller is
    responsible for treating None as a fall-through (NOT a fatal). A clear
    explanatory line is printed to stderr for any failure path so the operator
    can diagnose missing creds vs. missing IAM permissions vs. wrong region.
    """
    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[auth] boto3 not importable; cannot resolve SA credentials from "
            "SSM/Secrets Manager. Install boto3 or supply credentials via env.",
            file=sys.stderr,
        )
        return None

    try:
        ssm = boto3.client("ssm", region_name=SSM_SM_REGION)
        sm = boto3.client("secretsmanager", region_name=SSM_SM_REGION)
    except Exception as e:  # noqa: BLE001
        print(f"[auth] boto3 client construction failed: {e}", file=sys.stderr)
        return None

    try:
        cid_resp = ssm.get_parameter(Name=SSM_OAUTH_CLIENT_ID_PATH, WithDecryption=False)
        client_id = cid_resp["Parameter"]["Value"]
    except Exception as e:  # noqa: BLE001
        print(
            f"[auth] SSM get_parameter {SSM_OAUTH_CLIENT_ID_PATH} failed: {e}",
            file=sys.stderr,
        )
        return None

    try:
        ptr_resp = ssm.get_parameter(
            Name=SSM_OAUTH_CLIENT_SECRET_POINTER_PATH, WithDecryption=False
        )
        secret_name = ptr_resp["Parameter"]["Value"]
    except Exception as e:  # noqa: BLE001
        print(
            f"[auth] SSM get_parameter {SSM_OAUTH_CLIENT_SECRET_POINTER_PATH} "
            f"failed: {e}",
            file=sys.stderr,
        )
        return None

    try:
        sec_resp = sm.get_secret_value(SecretId=secret_name)
    except Exception as e:  # noqa: BLE001
        # Log only the hardcoded SSM pointer path, never the resolved SM name
        # (the pointer's value comes from SSM and CodeQL taints it as sensitive
        # via py/clear-text-logging-sensitive-data; operator can trace which SM
        # secret by reading the pointer).
        print(
            f"[auth] Secrets Manager get_secret_value failed (pointer SSM "
            f"{SSM_OAUTH_CLIENT_SECRET_POINTER_PATH}): {e}",
            file=sys.stderr,
        )
        return None

    try:
        envelope = json.loads(sec_resp.get("SecretString", ""))
    except (ValueError, TypeError) as e:
        print(f"[auth] Secrets Manager envelope is not valid JSON: {e}", file=sys.stderr)
        return None

    client_secret = envelope.get("client_secret")
    if not client_secret:
        # Same redaction discipline: log the pointer constant, not the resolved
        # SM name (CodeQL taint propagation from SSM-sourced values).
        print(
            "[auth] Secrets Manager envelope (resolved via pointer SSM "
            f"{SSM_OAUTH_CLIENT_SECRET_POINTER_PATH}) missing 'client_secret' key",
            file=sys.stderr,
        )
        return None

    # Success log: only reference the hardcoded SSM path constants, never the
    # fetched values (client_id prefix or SM secret name) — CodeQL flags any
    # logging of SSM/SM-sourced values as py/clear-text-logging-sensitive-data.
    print(
        f"[auth] Resolved SA credentials from AWS "
        f"(client_id at SSM {SSM_OAUTH_CLIENT_ID_PATH}, "
        f"client_secret pointer at SSM {SSM_OAUTH_CLIENT_SECRET_POINTER_PATH})"
    )
    return (client_id, client_secret)


def _acquire_token() -> str:
    """Acquire a bearer token for the SA-canary identity.

    Resolution order:
      1. RECEIVER_DEPLOY_GATE_TOKEN env var (operator override).
      2. autom8y_core.TokenManager from SERVICE_CLIENT_ID +
         SERVICE_CLIENT_SECRET env vars (standard SA convention; matches
         scripts/smoke_test_api.py:125-146).
      3. autom8y_core.TokenManager from AWS-resolved SA credentials
         (SSM + Secrets Manager, canonical provisioning path — mirrors the
         receiver runtime). See module-level constants for the exact paths.

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

    # Path (2): env-var SA convention. Try Config.from_env() first — it does
    # canonical-alias dual-lookup of AUTOM8Y_DATA_SERVICE_CLIENT_ID/_SECRET
    # then CLIENT_ID/CLIENT_SECRET (ADR-ENV-NAMING-CONVENTION Decision 4).
    # This preserves backward compat: any operator who had the env vars set
    # before the SSM fallback was added continues to work unchanged.
    config: Any | None = None
    try:
        config = Config.from_env()
        print("[auth] Config sourced from environment variables")
    except ValueError:
        # Env vars absent — fall through to AWS SSM/SM resolution.
        config = None

    # Path (3): AWS SSM/SM canonical provisioning path.
    if config is None:
        resolved = _resolve_sa_credentials_from_aws()
        if resolved is None:
            print(
                "[auth] FATAL: no auth source available. Set "
                "RECEIVER_DEPLOY_GATE_TOKEN, OR CLIENT_ID + CLIENT_SECRET "
                "(or AUTOM8Y_DATA_SERVICE_CLIENT_ID/_SECRET) env vars, OR "
                "ensure AWS credentials with SSM/SM read access to the "
                "asana-dataframe-resolver SA provisioning paths (see module "
                "docstring).",
                file=sys.stderr,
            )
            sys.exit(2)
        cid, csec = resolved
        # Inject into env using the names Config.from_env() reads
        # (CLIENT_ID + CLIENT_SECRET legacy aliases, dual-lookup-compatible).
        # This mirrors how the receiver runtime hydrates env at boot.
        os.environ["CLIENT_ID"] = cid
        os.environ["CLIENT_SECRET"] = csec
        try:
            config = Config.from_env()
        except ValueError as e:
            print(
                f"[auth] FATAL: Config.from_env() failed after AWS resolution: {e}",
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
