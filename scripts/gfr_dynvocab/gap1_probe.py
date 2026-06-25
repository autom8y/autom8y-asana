"""GAP-1 probe harness — does bare ``custom_fields`` return ``asset_id`` populated?

Settles the single HIGH platform UV-P for the gfr-dynvocab initiative (R-GAP1,
shape §9): for the live canary ``b167331c-536f-4996-9b2d-2f696f35f556``, does the
entry phase's ``custom_fields`` opt-field set return the ``Asset ID`` custom field
with a populated value? HYP-1's *code layer* is SVR-confirmed (the entry fetch
requests bare ``custom_fields`` + typed subfields). The residual unknown is the
Asana platform semantic — settled ONLY by a live fetch. This is the PT-01 fork
input: free-tail (HYP-1 confirmed) vs ~2x frame-based fallback (refuted).

This harness is a RETAINED operator tool, NOT shipped engine code. It lives under
``scripts/`` (not on pytest ``testpaths``, not in the package), so the certified
suite never auto-collects it.

Two modes, one shared assertion (TDD §3.4):

    # OFFLINE (safe; CI / anyone) — reads the recorded fixture, NO live Asana call:
    ./.venv/bin/python scripts/gfr_dynvocab/gap1_probe.py --mode=offline

    # LIVE (operator's lever ONLY) — double-guarded behind --mode=live AND the env
    # flag GFR_GAP1_LIVE_FIRE=1; the architect/PE does NOT run this:
    GFR_GAP1_LIVE_FIRE=1 ./.venv/bin/python scripts/gfr_dynvocab/gap1_probe.py \
        --mode=live --canary=b167331c-536f-4996-9b2d-2f696f35f556
    # NEVER uv run (CodeArtifact 401).

Importing this module has NO side effects (no fetch, no run). The CLI runs only
under ``if __name__ == "__main__"``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The canonical NAME of the custom field the probe assesses (NAME-keyed, never
#: gid-keyed — the operator correction; gid is a runtime intra-task handle only).
ASSET_ID_CF_NAME = "Asset ID"

#: Live canary task gid (the gfr-dynvocab worked-example entry).
DEFAULT_CANARY = "b167331c-536f-4996-9b2d-2f696f35f556"

#: The double-guard env flag (D-7) — the operator's explicit lever for live fire.
LIVE_FIRE_ENV = "GFR_GAP1_LIVE_FIRE"

_HERE = Path(__file__).resolve().parent
_FIXTURE_PATH = _HERE / "fixtures" / "gap1_canary_custom_fields.json"
# Repo root = .../autom8y-asana-wt-gfr (scripts/gfr_dynvocab/ -> repo root).
_REPO_ROOT = _HERE.parents[1]
_RECEIPT_PATH = _REPO_ROOT / ".ledge" / "spikes" / "gfr-dynvocab-gap1-probe-receipt.md"
_OPT_FIELDS_REF = (
    "src/autom8_asana/models/business/fields.py:232-251 (STANDARD_TASK_OPT_FIELDS)"
)


class LiveFireRefused(RuntimeError):
    """Raised when the live path is invoked without the operator env flag (D-7)."""


@dataclass(frozen=True)
class ProbeVerdict:
    """The probe's verdict of record (TDD §3.5)."""

    verdict: str  # HYP1_CONFIRMED | HYP1_REFUTED | OFFLINE_DRY_RUN
    asset_id_present: bool
    asset_id_populated: bool
    total_custom_fields: int
    asset_id_slice: dict | None
    mode: str  # offline | live
    source: str  # fixture | asana-live


# ---------------------------------------------------------------------------
# Shared assertion logic (D-6) — identical for offline and live
# ---------------------------------------------------------------------------


def _is_populated(value: object) -> bool:
    """A cf value counts as populated iff it is non-None and non-empty.

    Distinguishes UNKNOWN/absent from present-but-null: an "Asset ID" entry that
    exists but carries an empty/None typed value is NOT populated (REFUTED).
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def _extract_asset_id_value(cf: dict) -> object:
    """Pull the typed value off an "Asset ID" cf dict (text-typed in production).

    Prefers ``text_value`` (Asset ID is a TextField per offer.py:144), falling
    back to ``display_value`` if the live payload only surfaces the display form.
    """
    if "text_value" in cf:
        return cf.get("text_value")
    return cf.get("display_value")


def assess_custom_fields(custom_fields: list[dict] | None) -> ProbeVerdict:
    """Assess whether the ``Asset ID`` cf is present AND value-populated.

    The single source of truth for the verdict — called by BOTH modes so the
    offline receipt and the live receipt are produced by identical evaluation
    code (D-6). NAME-keyed match on ``ASSET_ID_CF_NAME``.

    Note: ``mode``/``source`` are stamped by the caller (run_offline/run_live);
    this function fills them with placeholder defaults that the runners overwrite.
    """
    cfs = custom_fields or []
    asset_id_slice: dict | None = None
    for cf in cfs:
        if cf.get("name") == ASSET_ID_CF_NAME:
            asset_id_slice = cf
            break

    present = asset_id_slice is not None
    populated = present and _is_populated(_extract_asset_id_value(asset_id_slice or {}))
    verdict = "HYP1_CONFIRMED" if populated else "HYP1_REFUTED"

    return ProbeVerdict(
        verdict=verdict,
        asset_id_present=present,
        asset_id_populated=populated,
        total_custom_fields=len(cfs),
        asset_id_slice=asset_id_slice,
        mode="offline",
        source="fixture",
    )


# ---------------------------------------------------------------------------
# Mode runners
# ---------------------------------------------------------------------------


def _load_fixture() -> list[dict]:
    payload = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload.get("custom_fields", [])


def run_offline() -> ProbeVerdict:
    """Run the probe against the recorded fixture. ALWAYS safe — no Asana call."""
    custom_fields = _load_fixture()
    base = assess_custom_fields(custom_fields)
    # Offline is a faithful dry-run: the assertion ran, but the LIVE verdict is
    # still pending the operator fire. Stamp source/mode; keep the assertion shape.
    return ProbeVerdict(
        verdict=base.verdict,
        asset_id_present=base.asset_id_present,
        asset_id_populated=base.asset_id_populated,
        total_custom_fields=base.total_custom_fields,
        asset_id_slice=base.asset_id_slice,
        mode="offline",
        source="fixture",
    )


def _live_fire_allowed() -> bool:
    return os.environ.get(LIVE_FIRE_ENV) == "1"


def run_live(canary: str = DEFAULT_CANARY) -> ProbeVerdict:
    """Fire the LIVE probe against Asana. OPERATOR's lever only (double-guarded).

    Refuses with :class:`LiveFireRefused` unless ``GFR_GAP1_LIVE_FIRE=1`` is set
    in the environment (D-7) — the structural guarantee that no pytest collection
    or CI path can fire live. Constructs a real client and requests the IDENTICAL
    opt-field set the entry phase uses (D-5: ``STANDARD_TASK_OPT_FIELDS``), then
    runs the SAME ``assess_custom_fields`` logic as the offline mode (D-6).
    """
    if not _live_fire_allowed():
        raise LiveFireRefused(
            "live Asana fire is the operator's lever; set "
            f"{LIVE_FIRE_ENV}=1 to confirm. Refusing to fire (D-7 double-guard)."
        )

    # Imports are LOCAL to the guarded path so the offline mode and module import
    # never touch the engine/client stack or attempt credential resolution.
    import asyncio

    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.fields import STANDARD_TASK_OPT_FIELDS

    async def _fetch() -> list[dict]:
        client = AsanaClient()
        task = await client.tasks.get_async(
            canary, opt_fields=list(STANDARD_TASK_OPT_FIELDS)
        )
        # The SDK may return a dict or a model; normalize to the cf list.
        if isinstance(task, dict):
            return task.get("custom_fields") or []
        return getattr(task, "custom_fields", None) or []

    custom_fields = asyncio.run(_fetch())
    base = assess_custom_fields(custom_fields)
    return ProbeVerdict(
        verdict=base.verdict,
        asset_id_present=base.asset_id_present,
        asset_id_populated=base.asset_id_populated,
        total_custom_fields=base.total_custom_fields,
        asset_id_slice=base.asset_id_slice,
        mode="live",
        source="asana-live",
    )


# ---------------------------------------------------------------------------
# Receipt emission (D-8)
# ---------------------------------------------------------------------------


def render_receipt(verdict: ProbeVerdict, *, canary: str) -> str:
    """Render the receipt markdown (TDD §3.5 format)."""
    fired_by = "operator" if verdict.mode == "live" else "ci"
    fired_at = datetime.now(UTC).isoformat()
    if verdict.mode == "offline":
        fm_verdict = "OFFLINE_DRY_RUN"
    else:
        fm_verdict = verdict.verdict

    slice_repr = (
        json.dumps(verdict.asset_id_slice, ensure_ascii=False)
        if verdict.asset_id_slice is not None
        else "ABSENT"
    )

    verdict_lines = {
        "HYP1_CONFIRMED": "HYP1_CONFIRMED — asset_id present and value-populated on the live canary fetch",
        "HYP1_REFUTED": "HYP1_REFUTED — asset_id absent/empty; PT-01 must pivot to frame-based fallback (~2x)",
        "OFFLINE_DRY_RUN": "OFFLINE_DRY_RUN — fixture-based; live fire pending operator command",
    }

    return f"""---
type: spike-receipt
initiative: gfr-dynvocab
sprint: sprint-1
probe: GAP-1
canary: {canary}
mode: {verdict.mode}
source: {verdict.source}
fired_by: {fired_by}
fired_at: {fired_at}
opt_fields_ref: "{_OPT_FIELDS_REF}"
verdict: {fm_verdict}
---

# GAP-1 Probe Receipt — does bare custom_fields return asset_id populated?

## Verdict
{verdict_lines[fm_verdict]}

## Evidence (verbatim)
- mode / source: {verdict.mode} / {verdict.source}
- asset_id cf entry (verbatim slice): {slice_repr}
- asset_id present: {verdict.asset_id_present}
- asset_id populated: {verdict.asset_id_populated}
- total custom_fields returned: {verdict.total_custom_fields}
- opt_fields requested: {_OPT_FIELDS_REF}

## PT-01 fork input
- HYP1_CONFIRMED → OPTION A (free-tail): proceed to sprint-2 task-based tail. Default.
- HYP1_REFUTED   → OPTION B (frame-based fallback ~2x): re-shape sprint-2 before tail build.
- OFFLINE_DRY_RUN → verdict pending; operator must run the live fire (TDD §3.6).
"""


def write_receipt(verdict: ProbeVerdict, *, canary: str) -> Path:
    """Write the receipt to its canonical path; return the path."""
    _RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _RECEIPT_PATH.write_text(render_receipt(verdict, canary=canary), encoding="utf-8")
    return _RECEIPT_PATH


# ---------------------------------------------------------------------------
# CLI (runs ONLY under __main__ — import is side-effect-free)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="GAP-1 probe: does bare custom_fields return asset_id populated?"
    )
    parser.add_argument(
        "--mode", choices=("offline", "live"), default="offline",
        help="offline (fixture, safe, default) or live (operator's lever, double-guarded)",
    )
    parser.add_argument("--canary", default=DEFAULT_CANARY, help="canary task gid for --mode=live")
    args = parser.parse_args(argv)

    if args.mode == "live":
        try:
            verdict = run_live(canary=args.canary)
        except LiveFireRefused as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
    else:
        verdict = run_offline()

    path = write_receipt(verdict, canary=args.canary)
    fm_verdict = "OFFLINE_DRY_RUN" if verdict.mode == "offline" else verdict.verdict
    print(f"GAP-1 probe [{verdict.mode}] verdict={fm_verdict} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
