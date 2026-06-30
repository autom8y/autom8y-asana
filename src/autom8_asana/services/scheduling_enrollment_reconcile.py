"""Cascade-change reconciliation sweep -- option (c), the fail-CLOSED invalidation.

The scheduling stratum is a freshness-stamped projection; the enrollment override is
the operator-attested posture.  When a cascade SOURCE field changes underneath an
existing override, the override silently goes stale.  This sweep is the chosen
invalidation mechanism (Phase-2 build ADR, option **(c)**): a PERIODIC
divergence-reconciliation pass that is **INDEPENDENT of the snapshot-push path**.

Per CH-DELTA-01 the option (a) per-guid transactional coupling (push-time
write-through into the enrollment table) is STRUCK -- cross-service two-phase writes
are not TL-A4-coherent.  Option (b) batch retry-with-backoff is the acceptable
fallback; option (c) is adopted because a standalone reconciler decouples
invalidation from the snapshot cadence entirely and degrades to a no-op rather than
corrupting either table on partial failure.

Detection (fail-closed): for each guid carrying BOTH a fresh stratum snapshot and an
enrollment override, divergence fires when the freshly-resolved snapshot stratum no
longer matches the enrolled ``override_stratum`` AND the snapshot was synced AFTER
the override was written (so a just-written override is never immediately re-flagged).
On divergence the sweep APPENDS a fail-closed override (``actor=operator``,
``cascade_changed_at=NOW()``, ``requires_reattestation=True``,
``notes=cascade_field_change_detected_by_normalizer``) that PRESERVES the operator's
existing enrolled ``override_stratum`` (it records the change + forces re-attestation,
it does NOT silently re-enrol the office into the newly-detected stratum) -- the
append-only enrollment log records the change and forces operator re-attestation; the
effective posture fails closed to the GHL fallback until re-attested.

OPERATOR-ACTIVATABLE / DEFAULT-DARK: the live override POST is gated behind
``SCHEDULING_ENROLLMENT_RECONCILE_ENABLED`` (DEFAULT-OFF).  The build runs DRY-RUN
only -- it computes divergence decisions and builds back-fill payloads but performs
NO live POST.  The divergence predicate is PURE so N5 can probe the adopted option
(c) without any live call.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, NamedTuple

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping, Sequence

logger = get_logger(__name__)

#: Activation gate (DEFAULT-OFF).  The live enrollment-override back-fill POST
#: requires an explicit truthy value (deploy-time operator decision).
SCHEDULING_ENROLLMENT_RECONCILE_ENABLED_ENV_VAR = "SCHEDULING_ENROLLMENT_RECONCILE_ENABLED"

#: The Phase-1 enrollment override route (PR #218, append-only).
OVERRIDE_ENDPOINT_PATH = "/api/v1/scheduling-enrollment/override"

#: The actor stamped on a sweep-authored override (the closed Phase-1 actor enum
#: is {self_service, operator}; the sweep acts on the operator's behalf).
RECONCILE_ACTOR = "operator"

#: The marker note stamped on a cascade-change back-fill (a grep anchor for audit).
RECONCILE_NOTE = "cascade_field_change_detected_by_normalizer"


class DivergenceDecision(NamedTuple):
    """The per-office reconciliation verdict + the back-fill payload when divergent."""

    guid: str
    divergent: bool
    reason: str
    override_payload: dict[str, Any] | None


class SweepResult(NamedTuple):
    """Aggregate sweep outcome."""

    dry_run: bool
    examined: int
    divergent: int
    posted: int
    decisions: list[DivergenceDecision]


def _is_reconcile_enabled() -> bool:
    """Whether the LIVE override back-fill POST is enabled (DEFAULT-OFF)."""
    return os.environ.get(SCHEDULING_ENROLLMENT_RECONCILE_ENABLED_ENV_VAR, "").lower() in {
        "true",
        "1",
        "yes",
    }


def _parse_ts(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp (UTC-normalized) or ``None`` if absent/invalid."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return stamp if stamp.tzinfo is not None else stamp.replace(tzinfo=UTC)
    return None


def build_reattestation_override(
    guid: str,
    override: Mapping[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Build the fail-closed cascade-change override (Phase-1 ``override`` contract).

    Field set is a subset of ``SchedulingEnrollmentOverrideRequest`` (extra=forbid):
    ``{guid, actor, override_stratum, override_ghl_calendar_id, cascade_changed_at,
    requires_reattestation, notes}``.  ``requires_reattestation=True`` is the
    fail-closed flag.

    PRESERVES the operator's EXISTING enrolled ``override_stratum`` (and GHL calendar)
    rather than auto-adopting the newly-detected snapshot stratum.  The back-fill row
    must honestly read "still enrolled in <X>, flagged for re-attestation because the
    cascade source changed" -- NOT silently re-enrol the office into the new provider.
    The load-bearing fail-closed safety is delivered by the Phase-1 resolver
    (``requires_reattestation`` dominates regardless of the enrolled stratum, PR #218);
    this row only records the change and forces re-attestation without misrepresenting
    what the operator actually enrolled in.

    ``override`` is the existing operator override mapping (``enrollment["override"]``),
    carrying ``override_stratum`` + ``override_ghl_calendar_id`` from the Phase-1
    enrollment read.  Callers MUST only invoke this when an override exists; a
    snapshot-only office has nothing to flag (see :func:`detect_divergence`).
    """
    return {
        "guid": guid,
        "actor": RECONCILE_ACTOR,
        "override_stratum": override["override_stratum"],
        "override_ghl_calendar_id": override.get("override_ghl_calendar_id"),
        "cascade_changed_at": now.isoformat(),
        "requires_reattestation": True,
        "notes": RECONCILE_NOTE,
    }


def detect_divergence(
    guid: str,
    snapshot: Mapping[str, Any] | None,
    enrollment: Mapping[str, Any] | None,
    *,
    now: datetime,
) -> DivergenceDecision:
    """PURE divergence predicate for option (c).

    Compares the freshly-resolved snapshot stratum against the enrolled override.
    Divergence fires when an override exists, its ``override_stratum`` no longer
    matches the snapshot stratum, AND the snapshot was synced strictly after the
    override was written (``synced_at > override.created_at``) -- so a just-written
    override is never re-flagged on the next pass.

    Args:
        guid: The office guid.
        snapshot: The stratum snapshot read (``{stratum, ghl_calendar_id, synced_at,
            ...}``) or ``None`` if the office has no snapshot.
        enrollment: The enrollment read (``{override: {override_stratum, created_at,
            ...}, ...}``) or ``None`` if the office has no enrollment.
        now: The sweep clock (stamped as ``cascade_changed_at`` on a back-fill).

    Returns:
        A :class:`DivergenceDecision`.
    """
    if snapshot is None:
        return DivergenceDecision(guid, False, "no_snapshot", None)

    override = enrollment.get("override") if enrollment else None
    if not override:
        # No operator override to invalidate -- the enrollment plane's own
        # fail-closed default governs; nothing for the sweep to reconcile.
        return DivergenceDecision(guid, False, "no_override", None)

    snapshot_stratum = snapshot.get("stratum")
    enrolled_stratum = override.get("override_stratum")
    if snapshot_stratum == enrolled_stratum:
        return DivergenceDecision(guid, False, "stratum_matches", None)

    synced_at = _parse_ts(snapshot.get("synced_at"))
    override_at = _parse_ts(override.get("created_at"))
    if synced_at is None or override_at is None or synced_at <= override_at:
        # Cannot prove the snapshot post-dates the override -> do NOT re-flag
        # (avoids re-posting against an override the sweep itself just wrote).
        return DivergenceDecision(guid, False, "snapshot_not_newer", None)

    # Preserve the operator's enrolled stratum on the flag (semantic honesty); the
    # snapshot proved the cascade changed but is NOT silently re-enrolled here.
    payload = build_reattestation_override(guid, override, now)
    return DivergenceDecision(guid, True, "cascade_changed", payload)


async def run_reconciliation_sweep(
    guids: Sequence[str],
    *,
    fetch_snapshot: Callable[[str], Awaitable[Mapping[str, Any] | None]],
    fetch_enrollment: Callable[[str], Awaitable[Mapping[str, Any] | None]],
    post_override: Callable[[dict[str, Any]], Awaitable[bool]],
    dry_run: bool | None = None,
    now: datetime | None = None,
) -> SweepResult:
    """Run the option-(c) divergence-reconciliation sweep over ``guids``.

    INDEPENDENT of the snapshot-push path: this reads the already-synced snapshot +
    enrollment per guid and back-fills divergences.  Readers/writer are injected so
    the sweep is exercisable as a dry-run with zero live calls.  ``dry_run`` defers
    to the gate when ``None`` (default-off => dry-run).  Per-office isolation: one
    office's read/post failure is logged and skipped.

    Returns:
        A :class:`SweepResult` (carries every decision for inspection).
    """
    enabled = _is_reconcile_enabled()
    effective_dry_run = (not enabled) if dry_run is None else dry_run
    clock = now if now is not None else datetime.now(UTC)

    decisions: list[DivergenceDecision] = []
    posted = 0
    for guid in guids:
        try:
            snapshot = await fetch_snapshot(guid)
            enrollment = await fetch_enrollment(guid)
        except Exception as exc:  # noqa: BLE001 -- per-office isolation
            logger.warning(
                "scheduling_reconcile_read_error",
                extra={"guid": guid, "error": str(exc), "error_type": type(exc).__name__},
            )
            continue

        decision = detect_divergence(guid, snapshot, enrollment, now=clock)
        decisions.append(decision)
        if not decision.divergent:
            continue

        if effective_dry_run:
            logger.info(
                "scheduling_reconcile_divergence_dry_run",
                extra={"guid": guid, "reason": decision.reason},
            )
            continue

        assert decision.override_payload is not None  # divergent => payload  # noqa: S101
        try:
            if await post_override(decision.override_payload):
                posted += 1
        except Exception as exc:  # noqa: BLE001 -- per-office isolation
            logger.warning(
                "scheduling_reconcile_post_error",
                extra={"guid": guid, "error": str(exc), "error_type": type(exc).__name__},
            )

    divergent = sum(1 for d in decisions if d.divergent)
    logger.info(
        "scheduling_reconcile_sweep_complete",
        extra={
            "dry_run": effective_dry_run,
            "examined": len(decisions),
            "divergent": divergent,
            "posted": posted,
        },
    )
    return SweepResult(
        dry_run=effective_dry_run,
        examined=len(decisions),
        divergent=divergent,
        posted=posted,
        decisions=decisions,
    )


__all__ = [
    "OVERRIDE_ENDPOINT_PATH",
    "RECONCILE_ACTOR",
    "RECONCILE_NOTE",
    "SCHEDULING_ENROLLMENT_RECONCILE_ENABLED_ENV_VAR",
    "DivergenceDecision",
    "SweepResult",
    "build_reattestation_override",
    "detect_divergence",
    "run_reconciliation_sweep",
]
