"""Tombstone reconciliation: a section deleted in Asana leaves the manifest.

Regression suite for the 2026-08-26 offers verification-floor stall. The
manifest was ADDITIVE -- nothing in the read-modify-write cycle ever removed a
key -- so when 19 of the 34 sections of the "business offers" project (gid
1143843662099250) were deleted at ~14:30Z, their entries survived carrying the
stamp of the last full pass. A failed probe never stamps (ADR-006
§Decision-5a), so those 19 stamps could never advance, and
``min(last_verified_at)`` over the manifest was pinned at 13:53:11.149471Z,
growing 1:1 with wall clock. Four consecutive ASR ticks read
7655 -> 22056 -> 36456 -> 50855 seconds against a 3600s threshold while every
producer layer was healthy.

The suite is two-sided throughout:

  CURE (the prune)
    - test_tombstones_leave_the_manifest_after_one_build_cycle
    - test_axis_unpins_after_reconciliation           (the 1:1 incident replay)
    - test_pruned_section_leaves_the_merge_denominator
    - test_prune_recomputes_manifest_counters

  NO OVER-PRUNE (the fence -- these must pass on BOTH sides of the cure)
    - test_live_but_unverified_section_still_forces_axis_null
    - test_transiently_failed_live_section_is_not_pruned
    - test_never_warmed_pending_live_section_is_not_pruned
    - test_empty_live_listing_prunes_nothing
    - test_noop_reconciliation_writes_nothing

The AXIS-NULL honesty in ``metrics/freshness.py``
(``compute_serve_verification``: a missing or unstamped IN-SCOPE section nulls
the axis rather than dropping out of the denominator) is load-bearing and is
pinned in both directions here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionPersistence,
    SectionStatus,
)
from autom8_asana.metrics.freshness import ServeVerification, compute_serve_verification

# ---------------------------------------------------------------------------
# Incident constants (DIAG-offers-staleness-stall-2026-08-27)
# ---------------------------------------------------------------------------

PROJECT_GID = "1143843662099250"
ENTITY_TYPE = "offer"

#: The instant the last 34/34 pass stamped -- what the 19 tombstones held.
PINNED_AT = datetime(2026, 8, 26, 13, 53, 11, 149471, tzinfo=UTC)
#: A later pass that re-stamped only the 15 surviving sections.
RESTAMPED_AT = datetime(2026, 8, 27, 3, 55, 0, tzinfo=UTC)
#: Wall clock at the 04:01:16Z tick that read 50855s.
NOW = datetime(2026, 8, 27, 4, 1, 16, tzinfo=UTC)

#: A representative slice of the sections deleted in the restructure.
DELETED_SECTION_NAMES = (
    "CALL",
    "SYSTEM ERROR",
    "PENDING APPROVAL",
    "OPTIMIZE QUANTITY",
    "OPTIMIZE QUALITY",
    "RESTART",
    "ONE-OFF",
    "RUN OPTIMIZATIONS",
)
LIVE_SECTION_NAMES = ("ACTIVE", "ONBOARDING", "PAUSED", "ARCHIVED")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_storage() -> MagicMock:
    """A DataFrameStorage double with async methods (mirrors
    ``test_manifest_concurrency._make_mock_storage``)."""
    storage = MagicMock()
    storage.is_available = True
    storage.save_json = AsyncMock(return_value=True)
    storage.load_json = AsyncMock(return_value=None)
    storage.save_section = AsyncMock(return_value=True)
    storage.load_section = AsyncMock(return_value=None)
    storage.delete_section = AsyncMock(return_value=True)
    storage.delete_object = AsyncMock(return_value=True)
    return storage


def _complete(name: str, *, verified_at: datetime | None, rows: int = 12) -> SectionInfo:
    return SectionInfo(
        status=SectionStatus.COMPLETE,
        rows=rows,
        name=name,
        written_at=verified_at,
        watermark=PINNED_AT,
        gid_hash=f"hash-{name}",
        last_verified_at=verified_at,
    )


def _incident_manifest() -> SectionManifest:
    """The live prod shape: 15 re-stamping sections + 19 frozen tombstones."""
    sections: dict[str, SectionInfo] = {}
    for i, name in enumerate(LIVE_SECTION_NAMES):
        sections[f"live_{i}"] = _complete(name, verified_at=RESTAMPED_AT)
    for i in range(len(LIVE_SECTION_NAMES), 15):
        sections[f"live_{i}"] = _complete(f"LIVE COLUMN {i}", verified_at=RESTAMPED_AT)
    for i, name in enumerate(DELETED_SECTION_NAMES):
        sections[f"dead_{i}"] = _complete(name, verified_at=PINNED_AT)
    for i in range(len(DELETED_SECTION_NAMES), 19):
        sections[f"dead_{i}"] = _complete(f"DEAD COLUMN {i}", verified_at=PINNED_AT)

    return SectionManifest(
        project_gid=PROJECT_GID,
        entity_type=ENTITY_TYPE,
        total_sections=len(sections),
        completed_sections=len(sections),
        sections=sections,
        schema_version="v1",
    )


def _live_gids(manifest: SectionManifest) -> list[str]:
    """The GIDs ``GET /projects/{gid}/sections`` returns after the restructure."""
    return [gid for gid in manifest.sections if gid.startswith("live_")]


def _persistence_serving(manifest: SectionManifest) -> tuple[SectionPersistence, MagicMock]:
    """A real SectionPersistence whose storage serves ``manifest`` from S3.

    Nothing is pre-seeded into the in-memory cache: the read path (load_json ->
    pydantic validate -> cache) is exercised, so the test round-trips the
    manifest exactly as production does.
    """
    storage = _make_mock_storage()
    storage.load_json = AsyncMock(return_value=manifest.model_dump_json().encode("utf-8"))
    return SectionPersistence(storage=storage), storage


def _whole_frame_axis(manifest: SectionManifest, *, now: datetime = NOW) -> ServeVerification:
    """The wire verification axis over the frame's own section set."""
    return compute_serve_verification(manifest=manifest, section_names=None, now=now)


def _make_builder(persistence: SectionPersistence) -> Any:
    """A ProgressiveProjectBuilder shim that runs the real
    ``_check_resume_and_probe`` (the production wire point).

    Mirrors the ``__new__`` shim in
    ``test_freshness_verification_recency._make_progressive_builder_with_fakes``.
    """
    from autom8_asana.dataframes.builders.progressive import ProgressiveProjectBuilder

    builder = ProgressiveProjectBuilder.__new__(ProgressiveProjectBuilder)
    builder._persistence = persistence
    builder._project_gid = PROJECT_GID
    builder._entity_type = ENTITY_TYPE
    builder._client = MagicMock()
    builder._dataframe_view = None
    builder._schema = MagicMock()
    builder._schema.version = "v1"
    return builder


async def _run_build_cycle(builder: Any, live_gids: list[str]) -> Any:
    """Drive ``_check_resume_and_probe`` with the freshness probe disabled.

    The probe is a separate mechanism with its own suite; disabling it isolates
    reconciliation without stubbing any part of the reconciliation path itself.
    """
    import autom8_asana.settings as settings_mod

    real_get_settings = settings_mod.get_settings
    try:
        stub = MagicMock()
        stub.runtime.section_freshness_probe = "0"
        settings_mod.get_settings = MagicMock(return_value=stub)  # type: ignore[assignment]
        return await builder._check_resume_and_probe(live_gids, True, section_names={})
    finally:
        settings_mod.get_settings = real_get_settings  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# CURE -- the tombstones leave, and the axis unpins
# ---------------------------------------------------------------------------


async def test_axis_unpins_after_reconciliation() -> None:
    """The incident, replayed 1:1: pinned before, honest after.

    RED against the pre-cure source -- the pruning branch is the only thing
    that moves the axis off PINNED_AT.
    """
    manifest = _incident_manifest()

    # --- BEFORE: the observed production state. --------------------------
    before = _whole_frame_axis(manifest)
    assert before.verified_at == PINNED_AT.isoformat(), (
        "fixture is not reproducing the incident: the axis should be pinned "
        "to the last 34/34 pass by the 19 tombstones."
    )
    assert before.verification_age_seconds is not None
    assert before.verification_age_seconds > 50000, (
        f"expected the ~50855s reading of the 04:01:16Z tick, got {before.verification_age_seconds}"
    )

    # --- One build cycle. -------------------------------------------------
    persistence, _storage = _persistence_serving(manifest)
    builder = _make_builder(persistence)
    await _run_build_cycle(builder, _live_gids(manifest))

    # --- AFTER: derived from the surviving sections only. -----------------
    reconciled = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert reconciled is not None
    after = _whole_frame_axis(reconciled)
    assert after.verified_at == RESTAMPED_AT.isoformat(), (
        "AXIS STILL PINNED: min(last_verified_at) is still governed by a "
        "section that no longer exists in Asana. The manifest prune did not "
        "run, or ran without persisting."
    )
    assert after.verification_age_seconds is not None
    assert after.verification_age_seconds < 3600, (
        "the surviving 15 sections were re-stamped 6 minutes ago; the axis "
        "must read minutes, not hours."
    )


async def test_tombstones_leave_the_manifest_after_one_build_cycle() -> None:
    """All 19 absent GIDs are gone; all 15 live GIDs remain."""
    manifest = _incident_manifest()
    live = _live_gids(manifest)
    assert len(live) == 15
    assert len(manifest.sections) == 34

    persistence, storage = _persistence_serving(manifest)
    await _run_build_cycle(_make_builder(persistence), live)

    reconciled = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert reconciled is not None
    assert sorted(reconciled.sections) == sorted(live)
    assert not [gid for gid in reconciled.sections if gid.startswith("dead_")]
    # The prune is DURABLE, not just in-memory: it reaches S3.
    assert storage.save_json.await_count >= 1


async def test_pruned_section_leaves_the_merge_denominator() -> None:
    """A tombstone's stale parquet stops being merged into the frame.

    ``read_all_sections_async`` reads ``get_complete_section_gids()``, so an
    un-pruned tombstone keeps feeding rows for tasks that no longer exist in
    Asana into every merged frame.
    """
    manifest = _incident_manifest()
    assert any(gid.startswith("dead_") for gid in manifest.get_complete_section_gids())

    persistence, _storage = _persistence_serving(manifest)
    await _run_build_cycle(_make_builder(persistence), _live_gids(manifest))

    reconciled = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert reconciled is not None
    complete = reconciled.get_complete_section_gids()
    assert complete
    assert not [gid for gid in complete if gid.startswith("dead_")]


async def test_prune_recomputes_manifest_counters() -> None:
    """``is_complete()`` survives the prune.

    ``is_complete()`` gates the whole stamp pass. If ``total_sections`` kept
    its pre-prune value the manifest would read permanently incomplete and
    verification would stop advancing -- trading a pinned axis for a frozen
    one.
    """
    manifest = _incident_manifest()
    persistence, _storage = _persistence_serving(manifest)
    await _run_build_cycle(_make_builder(persistence), _live_gids(manifest))

    reconciled = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert reconciled is not None
    assert reconciled.total_sections == 15
    assert reconciled.completed_sections == 15
    assert reconciled.is_complete() is True


async def test_prune_is_audited_never_silent() -> None:
    """Every pruned entry emits its GID, name and the stamp it was pinning."""
    import autom8_asana.dataframes.section_persistence as sp_mod

    manifest = _incident_manifest()
    persistence, _storage = _persistence_serving(manifest)

    real_logger = sp_mod.logger
    fake_logger = MagicMock()
    try:
        sp_mod.logger = fake_logger  # type: ignore[assignment]
        loaded = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
        assert loaded is not None
        await persistence.reconcile_manifest_sections_async(loaded, _live_gids(manifest))
    finally:
        sp_mod.logger = real_logger  # type: ignore[assignment]

    pruned_events = [
        call
        for call in fake_logger.warning.call_args_list
        if call.args and call.args[0] == "manifest_section_pruned"
    ]
    assert len(pruned_events) == 19, (
        f"expected one audit record per pruned tombstone, got {len(pruned_events)}"
    )
    payload = pruned_events[0].kwargs["extra"]
    assert payload["section_gid"].startswith("dead_")
    assert payload["last_verified_at"] == PINNED_AT.isoformat()
    assert payload["name"] in DELETED_SECTION_NAMES or payload["name"].startswith("DEAD")
    assert payload["reason"] == "absent_from_live_project_section_listing"

    summaries = [
        call
        for call in fake_logger.info.call_args_list
        if call.args and call.args[0] == "manifest_sections_reconciled"
    ]
    assert len(summaries) == 1
    assert summaries[0].kwargs["extra"]["pruned_count"] == 19
    assert summaries[0].kwargs["extra"]["retained_count"] == 15


# ---------------------------------------------------------------------------
# NO OVER-PRUNE -- the fence. These pass on BOTH sides of the cure.
# ---------------------------------------------------------------------------


async def test_live_but_unverified_section_still_forces_axis_null() -> None:
    """The load-bearing negative control (freshness.py AXIS-NULL honesty).

    A live, in-scope section that cannot be proven verified nulls the axis. If
    reconciliation ever widened from "absent from the listing" to "cannot
    verify", this section would be pruned and the axis would read FRESH over a
    frame containing an unverifiable section -- the exact dishonesty the
    verification axis exists to prevent.
    """
    manifest = _incident_manifest()
    manifest.sections["live_unverified"] = SectionInfo(
        status=SectionStatus.COMPLETE,
        rows=7,
        name="NEW COLUMN",
        watermark=None,
        gid_hash="hash-new",
        last_verified_at=None,
    )
    live = _live_gids(manifest)
    assert "live_unverified" in live

    persistence, _storage = _persistence_serving(manifest)
    await _run_build_cycle(_make_builder(persistence), live)

    reconciled = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert reconciled is not None
    assert "live_unverified" in reconciled.sections, (
        "OVER-PRUNE: an unstamped LIVE section was removed. Absence from the "
        "project listing is the discriminator, never verification health."
    )

    axis = _whole_frame_axis(reconciled)
    assert axis.verified_at is None
    assert axis.verification_age_seconds is None
    assert axis.refusal_reason == ServeVerification.REASON_UNSTAMPED_SECTIONS
    assert axis.missing_count >= 1


async def test_transiently_failed_live_section_is_not_pruned() -> None:
    """A 429/500 is unhealthy, not deleted.

    The section is still in the project listing, so it keeps its entry AND
    keeps governing the axis with its stale stamp. Curing a transient fault by
    deleting the evidence would make every rate-limit burst read as fresh.
    """
    manifest = _incident_manifest()
    manifest.sections["live_transient"] = SectionInfo(
        status=SectionStatus.FAILED,
        rows=0,
        name="RATE LIMITED",
        error="Rate limit exceeded (HTTP 429)",
        last_verified_at=PINNED_AT,
    )
    live = _live_gids(manifest)

    persistence, _storage = _persistence_serving(manifest)
    loaded = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert loaded is not None
    await persistence.reconcile_manifest_sections_async(loaded, live)

    reconciled = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert reconciled is not None
    assert "live_transient" in reconciled.sections, (
        "OVER-PRUNE: a transiently-failing LIVE section was removed."
    )
    # And it is still honestly holding the floor down.
    axis = _whole_frame_axis(reconciled)
    assert axis.verified_at == PINNED_AT.isoformat()


async def test_never_warmed_pending_live_section_is_not_pruned() -> None:
    """A PENDING entry for a live section is a build that has not run yet."""
    manifest = _incident_manifest()
    manifest.sections["live_pending"] = SectionInfo(status=SectionStatus.PENDING, name="NEW")
    live = _live_gids(manifest)

    persistence, _storage = _persistence_serving(manifest)
    loaded = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert loaded is not None
    await persistence.reconcile_manifest_sections_async(loaded, live)

    reconciled = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert reconciled is not None
    assert "live_pending" in reconciled.sections


async def test_empty_live_listing_prunes_nothing() -> None:
    """The fence: an untrustworthy listing must never empty the manifest."""
    manifest = _incident_manifest()
    persistence, storage = _persistence_serving(manifest)

    loaded = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert loaded is not None
    assert await persistence.reconcile_manifest_sections_async(loaded, []) == []

    result = loaded
    assert len(result.sections) == 34, (
        "an empty section listing was treated as 'the project has no "
        "sections' and wiped the manifest."
    )
    assert storage.save_json.await_count == 0


async def test_noop_reconciliation_writes_nothing() -> None:
    """The steady state costs one read and zero writes or log lines."""
    import autom8_asana.dataframes.section_persistence as sp_mod

    manifest = _incident_manifest()
    all_gids = list(manifest.sections)
    persistence, storage = _persistence_serving(manifest)
    loaded = await persistence.get_manifest_async(PROJECT_GID, ENTITY_TYPE)
    assert loaded is not None

    real_logger = sp_mod.logger
    fake_logger = MagicMock()
    try:
        sp_mod.logger = fake_logger  # type: ignore[assignment]
        pruned = await persistence.reconcile_manifest_sections_async(loaded, all_gids)
    finally:
        sp_mod.logger = real_logger  # type: ignore[assignment]

    assert pruned == []
    assert len(loaded.sections) == 34
    assert storage.save_json.await_count == 0
    assert fake_logger.warning.call_count == 0
    assert fake_logger.info.call_count == 0


async def test_cold_project_with_no_manifest_never_reaches_reconciliation() -> None:
    """A project with no manifest yet returns before the wire point.

    ``_check_resume_and_probe`` returns on ``manifest is None`` (the cold-build
    path) BEFORE reconciliation, so a cold build can never be handed a
    half-built manifest to prune against.
    """
    storage = _make_mock_storage()  # load_json -> None: no manifest in S3
    persistence = SectionPersistence(storage=storage)

    result = await _run_build_cycle(_make_builder(persistence), ["live_0"])

    assert result.manifest is None
    assert storage.save_json.await_count == 0


# ---------------------------------------------------------------------------
# Model tier -- prune_absent_sections in isolation
# ---------------------------------------------------------------------------


def test_prune_absent_sections_returns_the_pinning_stamps() -> None:
    """The pruned entries come back with their info so the audit can name
    the stamp that was holding the floor."""
    manifest = _incident_manifest()

    pruned = manifest.prune_absent_sections(_live_gids(manifest))

    assert len(pruned) == 19
    assert {info.last_verified_at for _gid, info in pruned} == {PINNED_AT}
    assert all(gid.startswith("dead_") for gid, _info in pruned)


def test_prune_absent_sections_is_idempotent() -> None:
    """Running twice prunes once."""
    manifest = _incident_manifest()
    live = _live_gids(manifest)

    assert len(manifest.prune_absent_sections(live)) == 19
    assert manifest.prune_absent_sections(live) == []
    assert len(manifest.sections) == 15


def test_prune_absent_sections_tolerates_live_gids_not_in_manifest() -> None:
    """A section ADDED in Asana is not yet in the manifest; that is the
    AXIS-NULL path's business (an in-scope section absent from the manifest is
    ``missing``), not the prune's. Reconciliation must not choke on it."""
    manifest = _incident_manifest()
    live = [*_live_gids(manifest), "brand_new_section"]

    pruned = manifest.prune_absent_sections(live)

    assert len(pruned) == 19
    assert "brand_new_section" not in manifest.sections
    assert len(manifest.sections) == 15
