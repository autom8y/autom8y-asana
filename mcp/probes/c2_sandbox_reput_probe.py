#!/usr/bin/env python3
"""C2 SANDBOX RE-PUT PROBE — OPERATOR-WITNESSED SANDBOX PROBE ONLY.

╔══════════════════════════════════════════════════════════════════════════════╗
║  BUILD-ONLY ARTIFACT. NOT RUN THIS SESSION. NOT RUN IN CI. NOT AUTOMATED.     ║
║  Runs ONLY when the operator executes it, by hand, against a SANDBOX Asana    ║
║  workspace, at felt-gate staging. It is fail-loud-gated so it cannot run      ║
║  by accident or be driven by an agent.                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS PROBES
    UV-P #4 (rulings dossier §7 / DECISION-asana-mcp-v1-rulings-B1-B5-W5 §8) and the
    B5 C2 caveat: does a RE-PUT of ``completed=true`` on an ALREADY-complete Asana task
    RE-FIRE Asana Rules automations (notifications, section moves, workflow transitions)?
    W-3 rules the composite's whole chain "safe to re-run" because STATE converges
    (the task ends completed either way) — but state convergence != side-effect silence.
    Whether downstream Rules re-fire is Asana-SERVER-SIDE behavior, unprobeable from the
    repo and fenced from live calls. This harness lets the OPERATOR observe it directly
    in a sandbox, discharging the §8 exposure-precondition (b) evidence at felt-gate
    staging. It does NOT decide anything — the operator witnesses; the operator closes.

STANDING FENCES (held BY CONSTRUCTION)
  * ZERO direct Asana calls. This harness drives the autom8y-asana SATELLITE REST
    surface only (PUT /api/v1/tasks/{gid}); the satellite forwards to Asana under its
    own bot PAT. There is no ``app.asana.com`` call here.
  * The MCP / sidecar process is NOT involved. This is a standalone probe script; it
    does not import ``asana_mcp`` and the sidecar makes zero Asana calls regardless.
  * NO secrets baked in. Base URL, bearer token, and task GID are read from the
    environment AT RUN TIME. The script REFUSES to run if any is missing.
  * NON-DESTRUCTIVE by design: it only re-asserts ``completed=true`` on a task the
    operator has already set complete in a SANDBOX. It never deletes, never mutates a
    production task, and requires explicit sandbox confirmation.

RUN CONTRACT (operator, felt-gate staging, SANDBOX only)
    export ASANA_MCP_C2_SATELLITE_BASE_URL="https://asana.sandbox.<...>"   # sandbox satellite
    export ASANA_MCP_C2_SATELLITE_TOKEN="<operator-minted sandbox S2S bearer>"
    export ASANA_MCP_C2_SANDBOX_TASK_GID="<already-complete sandbox task gid>"
    # optional: a sandbox endpoint that records inbound Asana Rules webhooks, for
    # automated before/after correlation (else the operator observes the workspace):
    export ASANA_MCP_C2_WEBHOOK_EVIDENCE_URL="https://.../sandbox/rule-webhook-log"   # optional
    python c2_sandbox_reput_probe.py --i-am-the-operator-in-a-sandbox

The script prints a structured JSON evidence bundle (both re-PUT responses, task-state
snapshots + modified_at deltas, timings, and any polled webhook evidence) for the
operator to attach to the felt-gate envelope. See README-C2-PROBE.md.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
from typing import Any

_REQUIRED_ENV = (
    "ASANA_MCP_C2_SATELLITE_BASE_URL",
    "ASANA_MCP_C2_SATELLITE_TOKEN",
    "ASANA_MCP_C2_SANDBOX_TASK_GID",
)
_CONFIRM_FLAG = "--i-am-the-operator-in-a-sandbox"
_BANNER = "=== C2 SANDBOX RE-PUT PROBE — OPERATOR-WITNESSED SANDBOX PROBE ONLY ==="


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat()


def _require_env() -> dict[str, str]:
    missing = [k for k in _REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        raise SystemExit(
            f"REFUSED: missing required env var(s): {missing}. No secrets are baked in; "
            "the operator supplies base URL, sandbox bearer, and sandbox task GID at run time."
        )
    return {k: os.environ[k] for k in _REQUIRED_ENV}


def _snapshot(client: Any, base: str, gid: str) -> dict[str, Any]:
    """GET the task state so the operator can diff modified_at / completion across re-PUTs."""
    resp = client.get(f"{base}/api/v1/tasks/{gid}")
    body: Any
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001 - tolerate non-JSON
        body = {"_raw": resp.text[:2000]}
    data = body.get("data", body) if isinstance(body, dict) else body
    return {
        "at": _now(),
        "http_status": resp.status_code,
        "completed": data.get("completed") if isinstance(data, dict) else None,
        "modified_at": data.get("modified_at") if isinstance(data, dict) else None,
    }


def _reput_completed_true(client: Any, base: str, gid: str, attempt: int) -> dict[str, Any]:
    """PUT {completed: true} on the SATELLITE surface — the idempotent re-assert."""
    t0 = time.monotonic()
    resp = client.request("PUT", f"{base}/api/v1/tasks/{gid}", json={"completed": True})
    elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {"_raw": resp.text[:2000]}
    return {
        "attempt": attempt,
        "at": _now(),
        "http_status": resp.status_code,
        "elapsed_ms": elapsed_ms,
        "response": body,
    }


def _poll_webhook_evidence(client: Any, url: str | None, label: str) -> dict[str, Any] | None:
    """OPTIONAL: poll a sandbox endpoint that records inbound Asana Rules webhooks."""
    if not url:
        return None
    resp = client.get(url)
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {"_raw": resp.text[:4000]}
    return {"label": label, "at": _now(), "http_status": resp.status_code, "evidence": body}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="C2 sandbox re-PUT probe (OPERATOR-WITNESSED SANDBOX ONLY)."
    )
    parser.add_argument(
        _CONFIRM_FLAG,
        dest="confirmed",
        action="store_true",
        help="Required. Affirms you are the operator running against a SANDBOX workspace.",
    )
    parser.add_argument(
        "--interval-s",
        type=float,
        default=5.0,
        help="Seconds to wait between the two re-PUTs (window for Rules to fire).",
    )
    args = parser.parse_args(argv)

    print(_BANNER, file=sys.stderr)
    if not args.confirmed:
        raise SystemExit(
            f"REFUSED: this is an OPERATOR-WITNESSED SANDBOX PROBE. Re-run with {_CONFIRM_FLAG} "
            "ONLY if you are the operator and the target is a SANDBOX Asana workspace task."
        )
    if os.environ.get("CI") or os.environ.get("ASANA_MCP_ENABLE_WRITE_SURFACE"):
        raise SystemExit(
            "REFUSED: refusing to run under CI or with the write-surface exposure flag set. "
            "This probe is hand-run by the operator in a sandbox only."
        )

    env = _require_env()
    base = env["ASANA_MCP_C2_SATELLITE_BASE_URL"].rstrip("/")
    gid = env["ASANA_MCP_C2_SANDBOX_TASK_GID"]
    webhook_url = os.environ.get("ASANA_MCP_C2_WEBHOOK_EVIDENCE_URL")

    # Imported here (not at module top) so importing this file is dependency-free.
    import httpx

    headers = {
        "Authorization": f"Bearer {env['ASANA_MCP_C2_SATELLITE_TOKEN']}",
        "user-agent": "asana-mcp-c2-sandbox-probe/0.1 (operator-witnessed)",
    }
    bundle: dict[str, Any] = {
        "probe": "c2_sandbox_reput",
        "target_gid": gid,
        "base_url": base,
        "started_at": _now(),
        "note": "OPERATOR-WITNESSED SANDBOX PROBE ONLY",
    }
    with httpx.Client(headers=headers, timeout=30.0) as client:
        bundle["webhook_before"] = _poll_webhook_evidence(client, webhook_url, "before")
        bundle["snapshot_0"] = _snapshot(client, base, gid)
        bundle["reput_1"] = _reput_completed_true(client, base, gid, 1)
        bundle["snapshot_1"] = _snapshot(client, base, gid)
        bundle["webhook_after_1"] = _poll_webhook_evidence(client, webhook_url, "after_1")
        time.sleep(max(0.0, args.interval_s))
        bundle["reput_2"] = _reput_completed_true(client, base, gid, 2)
        bundle["snapshot_2"] = _snapshot(client, base, gid)
        bundle["webhook_after_2"] = _poll_webhook_evidence(client, webhook_url, "after_2")
    bundle["finished_at"] = _now()

    # Convenience derivation for the operator: did the task's modified_at change on the
    # SECOND (already-complete -> complete) re-PUT? A change is a signal a re-fire MAY
    # have occurred; the operator confirms Rules side-effects in the sandbox workspace.
    bundle["modified_at_delta_on_reput_2"] = bundle["snapshot_1"].get("modified_at") != bundle[
        "snapshot_2"
    ].get("modified_at")
    print(json.dumps(bundle, indent=2, default=str))
    print(
        "\nOPERATOR: correlate the two re-PUT windows above with the SANDBOX workspace's "
        "notifications / section moves / workflow transitions (and any Rules-webhook log) "
        "to witness whether an idempotent re-PUT RE-FIRES Rules. Attach this bundle to the "
        "felt-gate envelope. This script decided nothing.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
