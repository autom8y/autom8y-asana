#!/usr/bin/env python3
# ruff: noqa: TID251
"""Deploy-gate canary probe for receiver-bulk-fanout-reliability Stage-1.

Exercises the production bulk-fan-out pattern (sustained N req/min over a
window) against the deployed receiver and reports whether the deploy-gate
criteria are met:

  * receiver_query_success_rate_project    >= 0.99 (sustained over the window)
  * receiver_query_success_rate_section    >= 0.99 (sustained over the window)
  * rate_limit_429_rate_sa                 == 0    (no SA-namespace 429s)
  * project content-binding                == 0 violations (S7-GATE-FIDELITY)

The probe pattern matches CR-3 consumer behavior: bulk fan-out at the
receiver, not steady-state interactive traffic. Default load mirrors the
Phase-3 Knob-5 derivation (~100 rpm baseline; 10-minute window).

S7-GATE-FIDELITY content-binding (Project arm only):
  The success-rate criteria above are HTTP-2xx *body-blind* — they mirror the
  receiver SLI (api/metrics.py:241/346), which counts a 2xx as a success
  regardless of body. A 2xx carrying an empty/wrong frame is therefore a
  *liveness-masquerade*: green on status, useless on content. To defeat it,
  the PROJECT arm additionally asserts the Contract-B column contract on every
  2xx body — office_phone + vertical + gid, the load-bearing OfferHolders
  MultiIndex-join columns (mirrors the consumer's own attestation set,
  autom8/apis/asana_api/satellite/getdf_signals.py:77 _CONTRACT_COLUMNS).
  A Project 2xx whose frame is empty-without-attestation, malformed, or missing
  a contract column FAILS the gate even though the success-rate reads green.
  A genuinely-empty honest-complete project (zero rows + meta.honest_empty=True)
  is an ATTESTED valid result, NOT a violation.

  The SECTION arm is column-contract-EXEMPT (assert_column_contract=False;
  getdf_signals.py:233-241): section frames legitimately carry no
  office_phone/vertical. It carries NO content criterion here — it is cleared
  on the disaggregated honest-EMF/cause signal + the PQ-5 section_gid
  guard-or-seed decision (OQ-3), NOT on column content.

Section-arm selector (PQ-5 guard-or-seed, OQ-3 resolved 2026-06-11):
  The section arm sends the live `section` NAME selector (RowsRequest.section,
  query/models.py:283; consumed at query.py:512 — `section_gid` is INERT on the
  /rows path). Without it, the receiver's PQ-5 guard fail-closes every section
  call with HTTP 400 [MISSING_SECTION_SELECTOR] (query.py:524-534); a 400 is a
  client error excluded from the mirror-SLI denominator, so the section arm's
  success_rate denominator is 0 and the gate reads a spurious 0.0 STATUS:FAIL
  even when the serve path is perfect (the 2026-06-11 iris smoke). The selector
  defaults to "Active" (the canonical fleet section name; --section-name to
  override for a project whose sections differ). The deliberate degenerate
  no-selector case is preserved as its OWN explicit refusal-contract probe
  (_probe_section_selector_contract) that asserts the 400 as a PASS of the
  fail-closed contract — NOT as a denominator member of the steady-state load.

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
do not count against the success rate. On the PROJECT arm it ADDITIONALLY
inspects the 2xx response BODY (the double-envelope RowsResponse,
models.py:430) to assert the column contract — this is the content-binding
that the status-only inference cannot see.

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
  0 = deploy-gate PASS (all criteria met)
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
import base64
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

# Default values match observability-plan.md §Deploy gate criterion.
DEFAULT_BASE_URL = "https://asana.api.autom8y.io"
DEFAULT_DURATION_MINUTES = 10
DEFAULT_TARGET_RPM = 100
DEFAULT_SUCCESS_RATE_THRESHOLD = 0.99
# Page limit on the content-bound (Project) arm so a real frame is returned to
# inspect — a slightly wider page than 1 makes a partial/wrong frame visible
# while staying cheap. The Section arm stays at limit=1 (content-EXEMPT).
DEFAULT_CONTENT_LIMIT = 5

# S7-GATE-FIDELITY Project-arm column contract.
#
# The load-bearing Contract-B columns the downstream OfferHolders MultiIndex
# join requires (office_phone + vertical), plus the universal row-identity
# invariant (gid). This MIRRORS the consumer's own authoritative attestation
# set, the tuple named _CONTRACT_COLUMNS at
# autom8/apis/asana_api/satellite/getdf_signals.py:77 — consumed by
# offer_holders/main.py:56 (the [office_phone, vertical] subselect) and
# business_offers/main.py:386-391 active_offer_phone_vertical_pairs.
#
# SCOPE: PROJECT frames ONLY. SECTION frames are EXEMPT — they are guaranteed
# `gid` (receiver invariant) but legitimately carry NO office_phone/vertical
# (higher-level business-resolution enrichment). The consumer skips this
# contract on the section arm via assert_column_contract=False
# (getdf_signals.py:233-241); the canary's Section arm does the same.
PROJECT_CONTRACT_COLUMNS = ("office_phone", "vertical", "gid")


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
    # S7-GATE-FIDELITY content-binding (Project arm ONLY).
    #
    # A 2xx whose body carries an empty/wrong frame is a *liveness-masquerade*:
    # it reads green on the HTTP status code while delivering no usable contract
    # content. The deploy-gate's success_rate is HTTP-2xx body-blind by design
    # (it mirrors the receiver SLI, api/metrics.py:241/346), so on its own it
    # CANNOT distinguish a real frame from an empty/wrong one. These counters
    # split the 2xx population on the Project arm so a content-blind success
    # cannot mask a wrong frame.
    #
    # ONLY populated when assert_column_contract=True (the Project arm). The
    # Section arm is column-contract-EXEMPT (assert_column_contract=False; see
    # _CONTRACT_COLUMNS rationale and getdf_signals.py:233-241) and leaves these
    # at 0 — it is cleared on the disaggregated honest-EMF/cause signal + the
    # PQ-5 section_gid guard-or-seed decision, NOT on column content.
    content_ok: int = 0  # 2xx with the office_phone/vertical/gid contract satisfied
    content_honest_empty: int = 0  # 2xx, zero rows, attested meta.honest_empty=True
    content_violations: int = 0  # 2xx that FAILED the column contract (the trap)
    content_violation_reasons: Counter[str] = field(default_factory=Counter)

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
# Content binding (S7-GATE-FIDELITY) — Project arm column contract
# ---------------------------------------------------------------------------


def _classify_project_content(body: dict[str, Any] | None) -> tuple[str, str]:
    """Classify a Project-arm 2xx body against the Contract-B column contract.

    Defeats the HTTP-2xx body-blind liveness-masquerade: a 2xx whose frame is
    empty/wrong must NOT count as a healthy content delivery. Returns one of:

      ("ok", "")                 — at least one row, every row carries
                                   office_phone + vertical + gid keys.
      ("honest_empty", "")       — zero rows AND meta.honest_empty is True: a
                                   legitimately-empty honest-complete project,
                                   an ATTESTED valid result (NOT a violation).
      ("violation", <reason>)    — the trap. Any of:
                                     * unparseable / wrong envelope shape
                                     * zero rows WITHOUT meta.honest_empty
                                       (silent/blind empty — the masquerade)
                                     * one or more rows MISSING a contract column

    The envelope is the canonical double-envelope (RowsResponse, models.py:430):
        body["data"]["data"] -> rows (list[dict]); body["data"]["meta"] -> meta.

    This MIRRORS the consumer's authoritative attestation
    (getdf_signals.py:77 _CONTRACT_COLUMNS) so the canary asserts exactly the
    contract the consumer's MultiIndex join depends on. PROJECT arm only.
    """
    if not isinstance(body, dict):
        return ("violation", "non_json_or_missing_body")

    inner = body.get("data")
    if not isinstance(inner, dict):
        return ("violation", "missing_data_envelope")

    rows = inner.get("data")
    meta = inner.get("meta")
    if not isinstance(rows, list) or not isinstance(meta, dict):
        return ("violation", "malformed_rows_or_meta")

    if len(rows) == 0:
        # An empty frame is ONLY legitimate when ATTESTED honest-empty
        # (engine.py:264; meta.honest_empty, models.py:419-427). An empty 2xx
        # without that attestation IS the liveness-masquerade — fail it.
        if meta.get("honest_empty") is True:
            return ("honest_empty", "")
        return ("violation", "empty_frame_without_honest_empty")

    # Non-empty: every row must carry the full Project column contract. A single
    # row missing office_phone/vertical/gid breaks the downstream join, so any
    # missing column on any row is a content violation.
    missing: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            return ("violation", "row_not_object")
        for col in PROJECT_CONTRACT_COLUMNS:
            if col not in row:
                missing.add(col)
    if missing:
        cols = ",".join(sorted(missing))
        return ("violation", f"missing_columns[{cols}]")

    return ("ok", "")


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
            f"[auth] SSM get_parameter {SSM_OAUTH_CLIENT_SECRET_POINTER_PATH} failed: {e}",
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

    # Accept BOTH the canonical bare-string secret (the reconciler-governed
    # service-api-keys/{name} store — the convergence target, "α") AND the
    # legacy JSON envelope {client_id, client_secret}. The bare form is the
    # single secret the D5 reconciler converges (sa_reconciler.py): pointing
    # the consumer at it means zero ungoverned copies. The envelope branch is
    # retained for backward-compatibility during the transition.
    raw_secret_string = sec_resp.get("SecretString", "")
    try:
        parsed = json.loads(raw_secret_string)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, dict):
        client_secret = parsed.get("client_secret")
    else:
        # Bare-string canonical secret: the whole SecretString IS the secret.
        client_secret = raw_secret_string or None
    if not client_secret:
        # Same redaction discipline: log the pointer constant, not the resolved
        # SM name (CodeQL taint propagation from SSM-sourced values).
        print(
            "[auth] Secrets Manager secret (resolved via pointer SSM "
            f"{SSM_OAUTH_CLIENT_SECRET_POINTER_PATH}) yielded no client_secret "
            "(neither a JSON envelope with 'client_secret' nor a non-empty bare string)",
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


# A SA JWT's TTL is short relative to a full probe window (observed 2026-06-08:
# ~4-5 min vs the 10-min default run). A once-minted token goes stale mid-run
# and EVERY subsequent call 401s — a contaminated gate reading that the
# 4xx-excluding success_rate silently masks. The provider below re-mints
# proactively, _TOKEN_REFRESH_SKEW_S before the decoded JWT `exp`, so a window
# of any length stays authenticated.
_TOKEN_REFRESH_SKEW_S = 60
_ASSUMED_TTL_S = 240  # fallback re-mint cadence when `exp` is unparseable


def _jwt_exp(token: str) -> float | None:
    """Return the JWT ``exp`` (epoch seconds) WITHOUT verifying the signature.

    Used solely to schedule proactive re-minting; the token itself is never
    logged. Returns None for an opaque/unparseable token (the caller then falls
    back to _ASSUMED_TTL_S). This READS the claim, it does not TRUST it — no
    signature check, no authorization decision is made here.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        return float(exp) if exp is not None else None
    except Exception:  # noqa: BLE001
        return None


class _TokenProvider:
    """Supplies a currently-valid bearer token, re-minting before expiry.

    ``get()`` is synchronous and contains no ``await``, so it is atomic across
    the two concurrent arm coroutines (asyncio single-loop): the first arm to
    cross the refresh threshold re-mints (a brief blocking call), and the other
    observes the fresh token on its next ``get()``. A static provider
    (operator-supplied env token) never re-mints — the operator owns its
    lifetime.
    """

    def __init__(self, mint: Callable[[], str], *, static: bool = False) -> None:
        self._mint = mint
        self._static = static
        self._token: str | None = None
        self._exp_epoch: float = 0.0

    def get(self) -> str:
        if self._static:
            if self._token is None:
                self._token = self._mint()
            return self._token
        now = time.time()
        if self._token is None or now >= self._exp_epoch - _TOKEN_REFRESH_SKEW_S:
            self._token = self._mint()
            exp = _jwt_exp(self._token)
            self._exp_epoch = exp if exp is not None else now + _ASSUMED_TTL_S
        return self._token


def _make_token_provider() -> _TokenProvider:
    """Build a self-refreshing bearer-token provider for the SA-canary identity.

    Resolution order (unchanged):
      1. RECEIVER_DEPLOY_GATE_TOKEN env var (operator override; STATIC — no
         refresh, the operator owns its lifetime).
      2. autom8y_core.TokenManager from SERVICE_CLIENT_ID +
         SERVICE_CLIENT_SECRET env vars (standard SA convention; matches
         scripts/smoke_test_api.py:125-146).
      3. autom8y_core.TokenManager from AWS-resolved SA credentials
         (SSM + Secrets Manager, canonical provisioning path — mirrors the
         receiver runtime). See module-level constants for the exact paths.

    Paths (2)/(3) return a REFRESHING provider that re-mints via a fresh
    TokenManager before the JWT expires. Raises SystemExit(2) on pre-flight
    failure (surfaced immediately by minting once up front).
    """
    env_token = os.environ.get("RECEIVER_DEPLOY_GATE_TOKEN")
    if env_token:
        print(
            f"[auth] Using RECEIVER_DEPLOY_GATE_TOKEN (len={len(env_token)}); static (no refresh)"
        )
        return _TokenProvider(lambda: env_token, static=True)

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

    def _mint() -> str:
        # A fresh TokenManager per mint keeps this robust regardless of whether
        # TokenManager.get_token() caches: at ~once-per-TTL cadence the cost is
        # negligible, and the auth endpoint is never hammered per-call.
        try:
            manager = TokenManager(config)
            token = manager.get_token()
            manager.close()
            return token
        except Exception as e:  # noqa: BLE001
            print(f"[auth] FATAL: JWT exchange failed: {e}", file=sys.stderr)
            sys.exit(2)

    provider = _TokenProvider(_mint)
    # Mint once up front so a pre-flight auth failure exits(2) BEFORE load starts.
    first = provider.get()
    exp = _jwt_exp(first)
    ttl_note = (
        f"exp in ~{int(exp - time.time())}s" if exp is not None else f"assumed {_ASSUMED_TTL_S}s"
    )
    print(
        f"[auth] JWT acquired via TokenManager (len={len(first)}); "
        f"auto-refresh armed (skew={_TOKEN_REFRESH_SKEW_S}s, {ttl_note})"
    )
    return provider


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------


async def _one_call(
    client: httpx.AsyncClient,
    base_url: str,
    arm: str,
    project_gid: str,
    token_provider: _TokenProvider,
    *,
    limit: int,
    parse_body: bool,
    section_name: str | None = None,
) -> tuple[int, float, dict[str, Any] | None]:
    """Issue one POST /v1/query/{arm}/rows call.

    Returns (status_code, elapsed_ms, parsed_body). ``parsed_body`` is the
    decoded JSON envelope when ``parse_body`` is True and the response is a 2xx
    with a JSON body; otherwise None. Content-binding (Project arm) needs the
    body to assert the column contract; the Section arm passes parse_body=False.

    ``section_name`` (Section arm): the live section NAME selector the receiver
    consumes (RowsRequest.section, query/models.py:283; query.py:512). The
    receiver's PQ-5 guard fail-closes a section-entity request that omits this
    selector with a 400 [MISSING_SECTION_SELECTOR] (query.py:524-534) — that 400
    is a CLIENT error, excluded from the success-rate denominator, so a section
    arm with no selector drives the section denominator to 0 and the gate reads
    a spurious success_rate=0.0 STATUS:FAIL even when the serve path is perfect.
    Passing a valid section name reaches the engine (2xx) and lights the section
    arm's mirror-SLI denominator. `section_gid` is INERT on this path (declared
    on RowsRequest but never read by the engine post the S3-MAP fix; the receiver
    requires `section` the NAME, not the gid) — so we send `section`, not
    `section_gid`. The deliberate degenerate-no-selector case is now its own
    explicit refusal-contract probe (see `_probe_section_selector_contract`),
    NOT a denominator member of the steady-state load.
    """
    url = f"{base_url.rstrip('/')}/v1/query/{arm}/rows"
    # Body for body-parameterized entities: project_gid + limit. ``limit`` is
    # raised above 1 on the content-bound (Project) arm so a real frame is
    # actually returned to inspect — a limit=1 read can still surface the
    # contract, but a slightly wider page makes a partial/wrong frame visible.
    body: dict[str, Any] = {
        "project_gid": project_gid,
        "limit": limit,
    }
    # Section arm: supply the live `section` NAME selector so the receiver scopes
    # the query instead of fail-closing with its honest 400. Omitted on the
    # project arm (a project-wide read is legitimate without a section).
    if arm == "section" and section_name is not None:
        body["section"] = section_name
    headers = {
        "Authorization": f"Bearer {token_provider.get()}",
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
        return (599, elapsed_ms, None)
    elapsed_ms = (time.perf_counter() - start) * 1000

    parsed: dict[str, Any] | None = None
    if parse_body and 200 <= status < 300:
        try:
            decoded = resp.json()
            parsed = decoded if isinstance(decoded, dict) else {"_non_dict": decoded}
        except (ValueError, json.JSONDecodeError):
            # A 2xx that is not decodable JSON is itself a content violation;
            # signal it with a sentinel the classifier rejects.
            parsed = None
    return (status, elapsed_ms, parsed)


async def _run_arm(
    client: httpx.AsyncClient,
    base_url: str,
    arm: str,
    project_gid: str,
    token_provider: _TokenProvider,
    target_rpm: int,
    duration_seconds: int,
    *,
    assert_column_contract: bool,
    content_limit: int,
    section_name: str | None = None,
) -> ArmResults:
    """Run sustained load against one arm for the configured duration.

    Issues `target_rpm` requests-per-minute as a steady drip — i.e., one
    request every (60 / target_rpm) seconds. NOT a burst-then-quiet pattern;
    this matches the consumer's actual fan-out shape (regular outbound calls).

    ``assert_column_contract`` (Project arm True; Section arm False): when True,
    every 2xx body is classified against the Contract-B column contract
    (office_phone/vertical/gid) and the per-class counters are incremented. A
    content VIOLATION (empty/wrong frame on a 2xx) is recorded but does NOT alter
    the HTTP-derived success_rate — it surfaces independently in the gate so the
    liveness-masquerade is defeated without conflating the two failure modes.

    ``section_name`` (Section arm): the live `section` NAME selector threaded
    into every section-arm call so the receiver scopes the query (2xx) instead
    of fail-closing with its honest 400 [MISSING_SECTION_SELECTOR] — which, as a
    client error excluded from the denominator, would otherwise zero the section
    arm's success-rate and force a spurious STATUS:FAIL. Ignored on the project
    arm.
    """
    results = ArmResults(arm=arm)
    interval_s = 60.0 / max(target_rpm, 1)
    end_time = time.monotonic() + duration_seconds
    # Only request a wider page (to inspect content) and parse the body on the
    # content-bound arm; the Section arm keeps the cheap limit=1, body-blind.
    per_call_limit = content_limit if assert_column_contract else 1

    while time.monotonic() < end_time:
        loop_start = time.monotonic()
        status, ms, body = await _one_call(
            client,
            base_url,
            arm,
            project_gid,
            token_provider,
            limit=per_call_limit,
            parse_body=assert_column_contract,
            section_name=section_name,
        )
        results.total_calls += 1
        results.durations_ms.append(ms)
        if 200 <= status < 300:
            results.successes += 1
            if assert_column_contract:
                cls, reason = _classify_project_content(body)
                if cls == "ok":
                    results.content_ok += 1
                elif cls == "honest_empty":
                    results.content_honest_empty += 1
                else:  # violation
                    results.content_violations += 1
                    results.content_violation_reasons[reason] += 1
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
# Section-selector refusal-contract probe (PQ-5 degenerate case)
# ---------------------------------------------------------------------------


async def _probe_section_selector_contract(
    client: httpx.AsyncClient,
    base_url: str,
    project_gid: str,
    token_provider: _TokenProvider,
) -> tuple[bool, str]:
    """Assert the receiver's PQ-5 fail-closed refusal contract — as a PASS.

    Sends ONE section-entity request that deliberately omits the `section`
    selector (carries only project_gid) and asserts the receiver REFUSES it with
    HTTP 400 + [MISSING_SECTION_SELECTOR] (query.py:524-534). This is the
    degenerate case the steady-state section arm used to send on every call —
    here it is isolated into a single explicit contract check so it proves the
    refusal works WITHOUT polluting the section arm's success-rate denominator
    (a 400 is a client error; mixed into the load it zeros the section arm).

    Returns (passed, detail). A 400 carrying the MISSING_SECTION_SELECTOR marker
    is the PASS (the refusal contract holds); anything else is a FAIL (the guard
    silently degenerated, or returned an unexpected status).
    """
    url = f"{base_url.rstrip('/')}/v1/query/section/rows"
    headers = {
        "Authorization": f"Bearer {token_provider.get()}",
        "Content-Type": "application/json",
    }
    # Deliberately NO `section` selector — exercise the fail-closed guard.
    body = {"project_gid": project_gid, "limit": 1}
    try:
        resp = await client.post(url, json=body, headers=headers, timeout=30.0)
    except httpx.RequestError as e:
        return (False, f"network error probing the refusal contract: {e}")

    if resp.status_code != 400:
        return (
            False,
            f"expected 400 fail-closed refusal for a section query missing its "
            f"`section` selector, got {resp.status_code}: {resp.text[:200]}",
        )
    if "MISSING_SECTION_SELECTOR" not in resp.text:
        return (
            False,
            f"got a 400 but without the MISSING_SECTION_SELECTOR marker; the "
            f"refusal contract is not the expected one: {resp.text[:200]}",
        )
    return (True, "400 [MISSING_SECTION_SELECTOR] — refusal contract holds")


# ---------------------------------------------------------------------------
# Reporting / gate decision
# ---------------------------------------------------------------------------


def _print_arm_report(r: ArmResults, *, content_bound: bool) -> None:
    print(f"  arm={r.arm}")
    print(f"    total_calls         = {r.total_calls}")
    print(f"    successes (2xx)     = {r.successes}")
    print(f"    server_errors (5xx) = {r.server_errors}")
    print(f"    client_errors (4xx) = {r.client_errors}")
    print(f"    rate_limited (429)  = {r.rate_limited}")
    print(f"    success_rate        = {r.success_rate:.4f}")
    print(f"    p50_ms              = {r.p50_ms:.1f}")
    print(f"    p99_ms              = {r.p99_ms:.1f}")
    if content_bound:
        # S7-GATE-FIDELITY: split the 2xx population so a content-blind success
        # cannot mask a wrong frame. Column contract: office_phone/vertical/gid.
        print(f"    content_ok          = {r.content_ok}")
        print(f"    content_honest_empty= {r.content_honest_empty}")
        print(f"    content_violations  = {r.content_violations}")
        if r.content_violation_reasons:
            for reason, count in sorted(r.content_violation_reasons.items()):
                print(f"      - {reason}: {count}")
    else:
        # Section arm is column-contract-EXEMPT (assert_column_contract=False):
        # cleared on the disaggregated honest-EMF/cause signal + the PQ-5
        # section_gid guard-or-seed decision, NOT on column content.
        print("    content_binding     = EXEMPT (section column-contract-exempt; see PQ-5/OQ-3)")


def _evaluate_gate(
    project: ArmResults,
    section: ArmResults,
    success_threshold: float,
) -> tuple[bool, list[str]]:
    """Evaluate the deploy-gate criteria. Returns (pass, reasons).

    Criteria:
      1. project success_rate    >= threshold (HTTP-derived mirror SLI)
      2. section success_rate    >= threshold (HTTP-derived mirror SLI)
      3. rate_limit_429_rate_sa  == 0
      4. project CONTENT-BINDING: zero Project-arm content violations
         (S7-GATE-FIDELITY). This is the additive criterion that defeats the
         HTTP-2xx body-blind liveness-masquerade — a Project 2xx carrying an
         empty/wrong frame (no office_phone/vertical/gid, or an unattested
         empty) FAILS the gate even though criterion 1 reads green on it.
         The SECTION arm is column-contract-EXEMPT (no content criterion); it
         is cleared on the disaggregated honest-EMF/cause signal + the PQ-5
         section_gid guard-or-seed decision, NOT on column content.
    """
    failures: list[str] = []

    if project.success_rate < success_threshold:
        failures.append(
            f"project success_rate={project.success_rate:.4f} < {success_threshold:.2f} threshold"
        )
    if section.success_rate < success_threshold:
        failures.append(
            f"section success_rate={section.success_rate:.4f} < {success_threshold:.2f} threshold"
        )

    total_sa_429 = project.rate_limited + section.rate_limited
    if total_sa_429 > 0:
        failures.append(
            f"SA-namespace 429 count={total_sa_429} > 0 "
            f"(project={project.rate_limited}, section={section.rate_limited}); "
            f"rate_limit_429_rate_sa must equal 0"
        )

    # Criterion 4 — Project-arm content-binding (S7-GATE-FIDELITY).
    # Any 2xx that failed the Contract-B column contract is the masquerade.
    # honest_empty 2xx are NOT violations (attested valid-empty results).
    if project.content_violations > 0:
        reasons = ", ".join(
            f"{r}={c}" for r, c in sorted(project.content_violation_reasons.items())
        )
        failures.append(
            f"project content_violations={project.content_violations} > 0 "
            f"(2xx with empty/wrong frame — liveness-masquerade; required cols "
            f"{'/'.join(PROJECT_CONTRACT_COLUMNS)}); breakdown: {reasons or 'n/a'}"
        )

    return (len(failures) == 0, failures)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def _main_async(args: argparse.Namespace) -> int:
    token_provider = _make_token_provider()
    duration_seconds = int(args.duration_minutes * 60)

    print(
        f"[probe] base_url={args.base_url} project_gid={args.project_gid} "
        f"section_name={args.section_name!r} "
        f"duration={args.duration_minutes}m target_rpm={args.target_rpm} "
        f"success_threshold={args.success_threshold:.2f}"
    )

    async with httpx.AsyncClient(http2=False) as client:
        # Pre-flight: assert the section-selector REFUSAL contract as a PASS
        # (PQ-5 degenerate case). Isolated from the steady-state load so the
        # 400 it deliberately provokes does NOT pollute the section arm's
        # success-rate denominator. A failed refusal contract fails the gate.
        refusal_ok, refusal_detail = await _probe_section_selector_contract(
            client, args.base_url, args.project_gid, token_provider
        )
        print(f"[probe] section-selector refusal contract: {refusal_detail}")

        # Run both arms concurrently — matches the consumer's fan-out shape.
        # PROJECT arm: content-bound (assert the office_phone/vertical/gid
        # Contract-B columns). SECTION arm: column-contract-EXEMPT but now sends
        # the live `section` NAME selector so it scopes (2xx) and lights its
        # mirror-SLI denominator, instead of fail-closing on every call.
        project_task = asyncio.create_task(
            _run_arm(
                client,
                args.base_url,
                "project",
                args.project_gid,
                token_provider,
                args.target_rpm,
                duration_seconds,
                assert_column_contract=True,
                content_limit=args.content_limit,
            )
        )
        section_task = asyncio.create_task(
            _run_arm(
                client,
                args.base_url,
                "section",
                args.project_gid,
                token_provider,
                args.target_rpm,
                duration_seconds,
                assert_column_contract=False,
                content_limit=args.content_limit,
                section_name=args.section_name,
            )
        )
        project_result, section_result = await asyncio.gather(project_task, section_task)

    print("\n=== Results ===")
    _print_arm_report(project_result, content_bound=True)
    _print_arm_report(section_result, content_bound=False)
    print("\n=== Section-selector refusal contract (PQ-5 degenerate case) ===")
    print(f"  refusal_contract = {'PASS' if refusal_ok else 'FAIL'} ({refusal_detail})")

    passed, failures = _evaluate_gate(project_result, section_result, args.success_threshold)
    if not refusal_ok:
        failures.append(
            f"section-selector refusal contract FAILED: {refusal_detail} "
            "(the receiver did not fail-closed on a section query missing its "
            "`section` selector — PQ-5 guard regression)"
        )
        passed = False

    print("\n=== Deploy-gate decision ===")
    if passed:
        print("  STATUS: PASS")
        print("  All criteria met:")
        print(f"    receiver_query_success_rate_project >= {args.success_threshold:.2f}")
        print(f"    receiver_query_success_rate_section >= {args.success_threshold:.2f}")
        print("    rate_limit_429_rate_sa == 0")
        print(
            "    project content-binding: 0 violations "
            f"(cols {'/'.join(PROJECT_CONTRACT_COLUMNS)}; "
            f"content_ok={project_result.content_ok}, "
            f"honest_empty={project_result.content_honest_empty})"
        )
        print("    section content-binding: EXEMPT (PQ-5/OQ-3; honest-EMF + guard/seed)")
        return 0
    else:
        print("  STATUS: FAIL")
        for f in failures:
            print(f"    - {f}")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Receiver bulk-fanout deploy-gate canary probe.")
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
        "--section-name",
        default="Active",
        help=(
            "Section NAME selector for the section arm (RowsRequest.section; the "
            "receiver consumes the name, not section_gid). Must be a section that "
            "exists in --project-gid so the section arm scopes (2xx) instead of "
            "fail-closing 400 [MISSING_SECTION_SELECTOR]. Default 'Active' (the "
            "canonical fleet section name); override to match the target project."
        ),
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
    parser.add_argument(
        "--content-limit",
        type=int,
        default=DEFAULT_CONTENT_LIMIT,
        help=(
            f"Page limit used on the content-bound (Project) arm so a real frame is "
            f"returned to assert the {'/'.join(PROJECT_CONTRACT_COLUMNS)} column "
            f"contract (default: {DEFAULT_CONTENT_LIMIT}). The Section arm is "
            "content-EXEMPT and always uses limit=1."
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
    main()
