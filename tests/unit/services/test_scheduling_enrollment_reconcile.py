"""Tests for the cascade-change reconciliation sweep -- option (c), fail-CLOSED.

Locks the PURE divergence predicate (the load-bearing logic N5 probes to confirm the
adopted option is (c), not (a)), the fail-closed back-fill override contract (PR #218
enrollment-override, validated against an extra=forbid replica), the DEFAULT-OFF
gate, and the dry-run / live / per-office-isolation sweep behaviour.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.services import scheduling_enrollment_reconcile as rec
from autom8_asana.services.scheduling_enrollment_reconcile import (
    RECONCILE_ACTOR,
    RECONCILE_NOTE,
    build_reattestation_override,
    detect_divergence,
    run_reconciliation_sweep,
)

pytestmark = [pytest.mark.xdist_group("scheduling_normalizer")]

_T0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
_NOW = datetime(2026, 6, 30, 12, 0, tzinfo=UTC)


# --- Local PR #218 enrollment-override replica (extra=forbid) --------------------


class _ActorEnum(StrEnum):
    SELF_SERVICE = "self_service"
    OPERATOR = "operator"


class _StratumEnum(StrEnum):
    REVIEWWAVE = "reviewwave"
    ACUITY = "acuity"
    CALENDLY = "calendly"
    JANEAPP = "janeapp"
    EHR = "ehr"
    TRACKSTAT = "trackstat"
    SKED = "sked"
    GHL = "ghl"
    INACTIVE = "inactive"


class _Pr218Override(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guid: str = Field(min_length=1, max_length=36)
    actor: _ActorEnum
    override_stratum: _StratumEnum
    override_ghl_calendar_id: str | None = Field(default=None, max_length=255)
    cascade_changed_at: datetime | None = None
    requires_reattestation: bool = False
    attested_by: str | None = Field(default=None, max_length=100)
    attested_at: datetime | None = None
    notes: str | None = None


def _snapshot(stratum: str, synced_at: datetime, *, ghl: str | None = None) -> dict[str, Any]:
    return {
        "stratum": stratum,
        "ghl_calendar_id": ghl,
        "custom_ghl_id": None,
        "synced_at": synced_at.isoformat(),
    }


def _enrollment(
    stratum: str, created_at: datetime, *, ghl_calendar_id: str | None = None
) -> dict[str, Any]:
    return {
        "override": {
            "override_stratum": stratum,
            "override_ghl_calendar_id": ghl_calendar_id,
            "created_at": created_at.isoformat(),
        }
    }


# --- detect_divergence (PURE) ---------------------------------------------------


def test_no_snapshot_not_divergent() -> None:
    d = detect_divergence("g", None, _enrollment("acuity", _T0), now=_NOW)
    assert d.divergent is False
    assert d.reason == "no_snapshot"


def test_no_override_not_divergent() -> None:
    d = detect_divergence("g", _snapshot("acuity", _NOW), {"override": None}, now=_NOW)
    assert d.divergent is False
    assert d.reason == "no_override"


def test_snapshot_only_office_synthesizes_no_override() -> None:
    """Edge: a fresh snapshot but NO enrollment record at all (snapshot-only).

    There is no operator override to flag, so the sweep must NOT synthesize a
    spurious override -- the resolver's no-override fail-closed default already
    governs this office. No back-fill payload is produced.
    """
    d = detect_divergence("g", _snapshot("calendly", _NOW), None, now=_NOW)
    assert d.divergent is False
    assert d.reason == "no_override"
    assert d.override_payload is None


def test_stratum_matches_not_divergent() -> None:
    d = detect_divergence("g", _snapshot("acuity", _NOW), _enrollment("acuity", _T0), now=_NOW)
    assert d.divergent is False
    assert d.reason == "stratum_matches"


def test_snapshot_not_newer_not_divergent() -> None:
    """Cascade differs but the snapshot predates the override -> do not re-flag."""
    older_snapshot = _snapshot("calendly", _T0 - timedelta(days=1))
    d = detect_divergence("g", older_snapshot, _enrollment("acuity", _T0), now=_NOW)
    assert d.divergent is False
    assert d.reason == "snapshot_not_newer"


def test_cascade_changed_is_divergent() -> None:
    """Cascade changed away from the enrolled stratum, post-dating the override."""
    snap = _snapshot("calendly", _NOW, ghl="https://x/cal-9")
    d = detect_divergence("g", snap, _enrollment("acuity", _T0), now=_NOW)
    assert d.divergent is True
    assert d.reason == "cascade_changed"
    assert d.override_payload is not None
    # The back-fill PRESERVES the operator's enrolled stratum (semantic honesty);
    # it does NOT auto-adopt the newly-detected snapshot stratum ('calendly').
    assert d.override_payload["override_stratum"] == "acuity"


# --- back-fill override contract -------------------------------------------------


def test_build_reattestation_override_contract() -> None:
    # The operator was enrolled in 'acuity' with their own GHL calendar; a cascade
    # flipped the snapshot to 'calendly'. The flag must PRESERVE the enrolled posture.
    enrolled = {
        "override_stratum": "acuity",
        "override_ghl_calendar_id": "op-cal",
        "created_at": _T0.isoformat(),
    }
    payload = build_reattestation_override("guid-1", enrolled, _NOW)

    assert payload["actor"] == RECONCILE_ACTOR == "operator"
    # PRESERVED enrolled stratum + operator calendar -- NOT the new snapshot stratum.
    assert payload["override_stratum"] == "acuity"
    assert payload["override_ghl_calendar_id"] == "op-cal"
    assert payload["requires_reattestation"] is True  # fail-closed teeth
    assert payload["notes"] == RECONCILE_NOTE
    assert payload["cascade_changed_at"] == _NOW.isoformat()
    # Validates against the extra=forbid PR #218 override replica.
    _Pr218Override.model_validate(payload)


def test_build_reattestation_override_preserves_absent_calendar() -> None:
    # An enrolled override with no GHL calendar preserves None (no snapshot leak-in).
    enrolled = {"override_stratum": "janeapp", "created_at": _T0.isoformat()}
    payload = build_reattestation_override("guid-2", enrolled, _NOW)
    assert payload["override_stratum"] == "janeapp"
    assert payload["override_ghl_calendar_id"] is None
    _Pr218Override.model_validate(payload)


# --- run_reconciliation_sweep ---------------------------------------------------


def _fetchers(snapshots: dict[str, Any], enrollments: dict[str, Any]) -> tuple[Any, Any]:
    async def fetch_snapshot(guid: str) -> Any:
        return snapshots.get(guid)

    async def fetch_enrollment(guid: str) -> Any:
        return enrollments.get(guid)

    return fetch_snapshot, fetch_enrollment


async def test_sweep_dry_run_no_post() -> None:
    snaps = {"g1": _snapshot("calendly", _NOW)}
    enrolls = {"g1": _enrollment("acuity", _T0)}
    fetch_snapshot, fetch_enrollment = _fetchers(snaps, enrolls)
    post = AsyncMock(return_value=True)

    result = await run_reconciliation_sweep(
        ["g1"],
        fetch_snapshot=fetch_snapshot,
        fetch_enrollment=fetch_enrollment,
        post_override=post,
        dry_run=True,
        now=_NOW,
    )
    assert result.dry_run is True
    assert result.divergent == 1
    assert result.posted == 0
    post.assert_not_awaited()


async def test_sweep_live_posts_divergent_override() -> None:
    snaps = {"g1": _snapshot("calendly", _NOW), "g2": _snapshot("acuity", _NOW)}
    enrolls = {"g1": _enrollment("acuity", _T0), "g2": _enrollment("acuity", _T0)}
    fetch_snapshot, fetch_enrollment = _fetchers(snaps, enrolls)
    post = AsyncMock(return_value=True)

    result = await run_reconciliation_sweep(
        ["g1", "g2"],
        fetch_snapshot=fetch_snapshot,
        fetch_enrollment=fetch_enrollment,
        post_override=post,
        dry_run=False,
        now=_NOW,
    )
    assert result.examined == 2
    assert result.divergent == 1  # only g1 diverged
    assert result.posted == 1
    post.assert_awaited_once()
    assert post.await_args.args[0]["guid"] == "g1"


async def test_sweep_isolates_read_failure() -> None:
    async def fetch_snapshot(guid: str) -> Any:
        if guid == "BAD":
            raise RuntimeError("read boom")
        return _snapshot("calendly", _NOW)

    async def fetch_enrollment(guid: str) -> Any:
        return _enrollment("acuity", _T0)

    post = AsyncMock(return_value=True)
    result = await run_reconciliation_sweep(
        ["g1", "BAD", "g2"],
        fetch_snapshot=fetch_snapshot,
        fetch_enrollment=fetch_enrollment,
        post_override=post,
        dry_run=True,
        now=_NOW,
    )
    # BAD is skipped; g1 + g2 examined and both divergent.
    assert result.examined == 2
    assert result.divergent == 2


async def test_sweep_default_gate_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(rec.SCHEDULING_ENROLLMENT_RECONCILE_ENABLED_ENV_VAR, raising=False)
    snaps = {"g1": _snapshot("calendly", _NOW)}
    enrolls = {"g1": _enrollment("acuity", _T0)}
    fetch_snapshot, fetch_enrollment = _fetchers(snaps, enrolls)
    post = AsyncMock(return_value=True)

    result = await run_reconciliation_sweep(
        ["g1"],
        fetch_snapshot=fetch_snapshot,
        fetch_enrollment=fetch_enrollment,
        post_override=post,
        now=_NOW,
    )
    assert result.dry_run is True  # gate default-off
    post.assert_not_awaited()


# --- COMPOSED cross-PR seam (the seam the isolated suites could not see, N5 F-1) ---


def _resolve_posture_replica(
    snapshot_stratum: str, payload: dict[str, Any]
) -> tuple[str, bool, str]:
    """Faithful replica of autom8y-data ``scheduling_posture.resolve_effective_posture``.

    Mirrors the PR #218 resolver's post-F-1 reattestation precedence the same way
    ``_Pr218Override`` mirrors the PR #218 request model: an override flagged
    ``requires_reattestation`` that has NOT been operator-re-attested since the cascade
    change fails closed to GHL -- REGARDLESS of whether ``snapshot_stratum`` corroborates
    the enrolled ``override_stratum`` (the flag dominates; that is the F-1 fix). Returns
    ``(effective_stratum, fallback, reason)``.
    """
    requires_reattestation = bool(payload.get("requires_reattestation", False))
    attested_at = payload.get("attested_at")
    cascade_changed_at = payload.get("cascade_changed_at")
    reattested = (
        attested_at is not None
        and cascade_changed_at is not None
        and attested_at >= cascade_changed_at
    )
    if requires_reattestation and not reattested:
        return ("ghl", True, "reattestation_required")
    # Non-flagged / re-attested override stands (not a path the sweep back-fill takes).
    return (str(payload["override_stratum"]), False, "enrollment_override")


def test_composed_sweep_backfill_fails_closed_against_resolver_replica() -> None:
    """COMPOSED seam guard: REAL sweep payload -> Phase-1 resolver replica (N5 F-1).

    Exercises sweep-payload (this PR #173) -> resolver (autom8y-data #218) end-to-end,
    asserting BOTH halves of the fix:
      (a) HONESTY: the back-fill preserves the operator's ENROLLED stratum (does NOT
          auto-adopt the new snapshot stratum) -- the Phase-2 semantic-honesty fix.
      (b) FAIL-CLOSED: feeding that payload through the resolver yields
          ghl / fallback=True / reattestation_required -- both when the live snapshot
          has moved away AND when it has flapped back to the enrolled value
          (self-corroborating), the exact case the pre-fix resolver fell open on.
    """
    # Operator enrolled in 'acuity'; the normalizer cascade flipped the snapshot to
    # 'calendly'. The REAL sweep detects divergence and builds the back-fill.
    enrolled_office = _enrollment("acuity", _T0, ghl_calendar_id="op-cal")
    snap = _snapshot("calendly", _NOW, ghl="https://x/cal-9")
    decision = detect_divergence("g-1", snap, enrolled_office, now=_NOW)

    assert decision.divergent is True
    payload = decision.override_payload
    assert payload is not None

    # (a) HONESTY: enrolled stratum + operator calendar preserved on the flag.
    assert payload["override_stratum"] == "acuity"
    assert payload["override_ghl_calendar_id"] == "op-cal"
    assert payload["requires_reattestation"] is True

    # (b) FAIL-CLOSED through the resolver replica -- both snapshot arms.
    assert _resolve_posture_replica("calendly", payload) == ("ghl", True, "reattestation_required")
    assert _resolve_posture_replica("acuity", payload) == ("ghl", True, "reattestation_required")
