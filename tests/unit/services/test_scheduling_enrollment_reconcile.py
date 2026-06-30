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


def _enrollment(stratum: str, created_at: datetime) -> dict[str, Any]:
    return {"override": {"override_stratum": stratum, "created_at": created_at.isoformat()}}


# --- detect_divergence (PURE) ---------------------------------------------------


def test_no_snapshot_not_divergent() -> None:
    d = detect_divergence("g", None, _enrollment("acuity", _T0), now=_NOW)
    assert d.divergent is False
    assert d.reason == "no_snapshot"


def test_no_override_not_divergent() -> None:
    d = detect_divergence("g", _snapshot("acuity", _NOW), {"override": None}, now=_NOW)
    assert d.divergent is False
    assert d.reason == "no_override"


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
    assert d.override_payload["override_stratum"] == "calendly"


# --- back-fill override contract -------------------------------------------------


def test_build_reattestation_override_contract() -> None:
    snap = _snapshot("calendly", _NOW, ghl="https://x/cal-9")
    payload = build_reattestation_override("guid-1", snap, _NOW)

    assert payload["actor"] == RECONCILE_ACTOR == "operator"
    assert payload["override_stratum"] == "calendly"
    assert payload["override_ghl_calendar_id"] == "https://x/cal-9"
    assert payload["requires_reattestation"] is True  # fail-closed teeth
    assert payload["notes"] == RECONCILE_NOTE
    assert payload["cascade_changed_at"] == _NOW.isoformat()
    # Validates against the extra=forbid PR #218 override replica.
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
