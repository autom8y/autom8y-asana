"""Tests for the ADR-006 / TDD freshness-verification-recency change set.

These tests cover the acceptance criteria specified in
``.ledge/specs/freshness-verification-recency.tdd.md §4`` plus the
QA-gate-2 anti-theater carry conditions:

  - T1..T9 backward-compatibility / mechanism shape
  - T10 amended: stamp-phase failure emits ``section_last_verified_stamp_failed``
  - T11 (SCAR): all-names-null prod-realistic fixture -> loud
    ``section_name_contract_violation``, NOT a silent inert signal
  - T12 (SCAR): single-task section content edit -> CONTENT_CHANGED
  - T13 (SCAR): edit to the exact watermark task -> CONTENT_CHANGED;
    unchanged boundary task stays CLEAN
  - T14 (SCAR): stamp gates on ``applied_gids`` membership for delta
    verdicts
  - T15 (SCAR): ``name`` + ``last_verified_at`` survive completion
  - T16 (SCAR): COMPLETE section with ``prior.name=None`` is RE-SEEDED
    from ``section_names`` on the next warm
  - read_manifest_sync running-loop guard raises loudly

SCAR-marked tests are the anti-theater guards that MUST fail on a
deliberately-unfixed checkout (QA-gate-2 condition 3).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.dataframes.builders.freshness import (
    ProbeVerdict,
    SectionProbeResult,
    _any_modified_after,
    compute_gid_hash,
)
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionStatus,
)
from autom8_asana.metrics.freshness import (
    VerificationAge,
    compute_verification_age,
    read_manifest_sync,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_task_mock(gid: str, modified_at: datetime | None = None) -> MagicMock:
    """Build a mock task with explicit ``gid`` and ``modified_at``."""
    t = MagicMock()
    t.gid = gid
    t.modified_at = modified_at
    return t


def _make_manifest(
    sections: dict[str, SectionInfo],
    *,
    entity_type: str = "offer",
    project_gid: str = "proj_1",
) -> SectionManifest:
    return SectionManifest(
        project_gid=project_gid,
        entity_type=entity_type,
        total_sections=len(sections),
        completed_sections=sum(1 for s in sections.values() if s.status == SectionStatus.COMPLETE),
        sections=sections,
        schema_version="v1",
    )


# ---------------------------------------------------------------------------
# T15: carry-forward survives mark_section_complete
# ---------------------------------------------------------------------------


@pytest.mark.scar
class TestT15CarryForwardSurvivesCompletion:
    """T15: non-null ``name`` and ``last_verified_at`` survive completion.

    On a build that omits the carry-forward in ``mark_section_complete``,
    the assertion ``info.name == 'Active'`` fails (the rebuild wipes
    ``name`` to ``None``). This is the load-bearing guard for the QA D1
    / D5 source-fix.
    """

    def test_carry_forward_preserves_name_and_last_verified_at(self) -> None:
        prior_stamp = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=10,
                    name="Active",
                    last_verified_at=prior_stamp,
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="abc",
                )
            }
        )
        # Re-completion (delta-apply / re-fetch) without a fresh name.
        manifest.mark_section_complete(
            "sec_1",
            12,
            watermark=datetime(2026, 5, 27, 13, 0, tzinfo=UTC),
            gid_hash="def",
        )
        out = manifest.sections["sec_1"]
        assert out.name == "Active", (
            "T15 FAIL: mark_section_complete wiped 'name' to None instead "
            "of carrying it forward. Heal the wipe at the source per "
            "ADR-006 §Decision-7 / TDD §2.2.1."
        )
        assert out.last_verified_at == prior_stamp, (
            "T15 FAIL: mark_section_complete wiped 'last_verified_at' "
            "instead of carrying it forward (silent stamp loss path)."
        )

    def test_mark_section_failed_is_unchanged(self) -> None:
        """``mark_section_failed`` is NOT modified -- FAILED is never in
        the verification denominator (per TDD §2.2.1 'Out of scope').
        """
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name="Active",
                    last_verified_at=datetime(2026, 5, 27, 12, 0, tzinfo=UTC),
                )
            }
        )
        manifest.mark_section_failed("sec_1", "boom")
        out = manifest.sections["sec_1"]
        assert out.status == SectionStatus.FAILED.value
        # The carry-forward semantic was intentionally NOT added to
        # mark_section_failed; the rebuild produces the spartan
        # error-only SectionInfo. The behavior under test is that
        # mark_section_failed remains a stripped reset.
        assert out.name is None
        assert out.last_verified_at is None


# ---------------------------------------------------------------------------
# T16: re-seed COMPLETE/null-name sections from section_names
# ---------------------------------------------------------------------------


@pytest.mark.scar
class TestT16ReSeedFromSectionNames:
    """T16 (SCAR): COMPLETE section with ``prior.name=None`` gets
    re-seeded from the ``section_names`` map on the next warm.

    Constructed against the actual ``mark_section_complete`` re-seed
    parameter -- a build that adds carry-forward but does not thread the
    optional ``name`` keyword cannot pass this test (the assertion
    ``info.name == 'Active'`` fails because ``prior.name`` was already
    ``None`` and there is no other source).
    """

    def test_reseed_uses_supplied_name_when_prior_is_none(self) -> None:
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=None,  # the exact prod state
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="abc",
                )
            }
        )
        # Simulate the completion-path backstop: name supplied from
        # _fetch_and_persist_section's Section object (TDD §2.2.1 edit 3).
        manifest.mark_section_complete(
            "sec_1",
            5,
            watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
            gid_hash="abc",
            name="Active",
        )
        out = manifest.sections["sec_1"]
        assert out.name == "Active", (
            "T16 FAIL: re-seed channel did not populate 'name' on a "
            "section whose prior.name was None. This is the prod case "
            "the carry-forward alone cannot heal (see TDD §2.2.1 edit "
            "3 + ADR-006 §Decision-7)."
        )

    def test_supplied_name_takes_precedence_over_prior(self) -> None:
        """When both ``prior.name`` and ``name`` are non-None, the
        supplied name takes precedence (re-seed is authoritative).
        """
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name="stale-name",
                )
            }
        )
        manifest.mark_section_complete("sec_1", 5, name="Active")
        assert manifest.sections["sec_1"].name == "Active"

    def test_carry_forward_when_no_name_supplied(self) -> None:
        """When ``name`` is omitted AND prior.name is set, carry forward."""
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name="Active",
                )
            }
        )
        manifest.mark_section_complete("sec_1", 5)
        assert manifest.sections["sec_1"].name == "Active"


# ---------------------------------------------------------------------------
# T12 / T13: prober watermark-task-identity test
# ---------------------------------------------------------------------------


@pytest.mark.scar
class TestT12T13ProberWatermarkIdentity:
    """T12 + T13 (SCAR): the §2.5 prober fix catches single-task /
    watermark-task edits without false-positive storms on the unchanged
    boundary task.
    """

    def test_t12_single_task_section_edit_is_caught(self) -> None:
        """T12: a section with exactly 1 task; the task was edited after
        the watermark; ``modified_since`` returns exactly 1 task whose
        ``modified_at > watermark`` -> the helper flags True. Old gate
        (``len > 1``) would falsely return False.
        """
        watermark = datetime(2026, 5, 27, 0, 0, tzinfo=UTC)
        edited_at = datetime(2026, 5, 27, 6, 0, tzinfo=UTC)
        tasks = [_make_task_mock("only_task", modified_at=edited_at)]
        assert _any_modified_after(tasks, watermark) is True, (
            "T12 FAIL: single-task-section edit was not detected. The "
            "old len(modified_tasks) > 1 gate is still in place."
        )

    def test_t13_watermark_task_edit_is_caught(self) -> None:
        """T13: multi-task section; the watermark task itself was edited
        AFTER the watermark instant; ``modified_since`` returns exactly
        1 task whose ``modified_at > watermark``. Caught by the strict
        > test.
        """
        watermark = datetime(2026, 5, 27, 0, 0, tzinfo=UTC)
        edited_at = datetime(2026, 5, 27, 6, 0, tzinfo=UTC)
        # The boundary task is the only one returned, edited.
        tasks = [_make_task_mock("watermark_task", modified_at=edited_at)]
        assert _any_modified_after(tasks, watermark) is True

    def test_t13_unchanged_boundary_task_stays_clean(self) -> None:
        """T13 negative: an UNCHANGED boundary task returns
        ``modified_at == watermark`` -> strict > is False -> CLEAN.
        Guards against false-positive storms.
        """
        watermark = datetime(2026, 5, 27, 0, 0, tzinfo=UTC)
        tasks = [_make_task_mock("boundary", modified_at=watermark)]
        assert _any_modified_after(tasks, watermark) is False, (
            "T13 FAIL: unchanged boundary task (modified_at == "
            "watermark) was wrongly classified as changed -- this "
            "would produce a false-positive storm on every warm."
        )

    def test_helper_handles_missing_modified_at(self) -> None:
        """A task without ``modified_at`` cannot prove a strict-after
        edit; the helper returns False (falls through to CLEAN).
        """
        watermark = datetime(2026, 5, 27, 0, 0, tzinfo=UTC)
        tasks = [_make_task_mock("no_ts", modified_at=None)]
        assert _any_modified_after(tasks, watermark) is False


# ---------------------------------------------------------------------------
# Stamp + re-seed + alarm tier integration tests
# ---------------------------------------------------------------------------


class _FakePersistence:
    """In-memory persistence stub for _probe_freshness integration tests.

    Implements ``get_manifest_async`` + ``_save_manifest_async`` against
    a single shared ``SectionManifest`` reference -- mirrors the
    cache-coherent behavior of the real persistence in a single-process
    warm.
    """

    def __init__(self, manifest: SectionManifest) -> None:
        self.manifest = manifest
        self.save_count = 0
        self.save_should_raise = False

    async def get_manifest_async(self, project_gid: str) -> SectionManifest:
        return self.manifest

    async def _save_manifest_async(self, manifest: SectionManifest) -> bool:
        if self.save_should_raise:
            raise RuntimeError("simulated S3 failure")
        self.save_count += 1
        # Persist by storing the same reference (the in-process cache
        # coherence model of the real SectionPersistence).
        self.manifest = manifest
        return True


def _make_progressive_builder_with_fakes(
    manifest: SectionManifest,
    *,
    section_names: dict[str, str] | None = None,
    probe_results: list[SectionProbeResult] | None = None,
    applied_gids: frozenset[str] = frozenset(),
    save_should_raise: bool = False,
) -> tuple[Any, _FakePersistence, MagicMock]:
    """Construct a ProgressiveProjectBuilder shim wired to call into the
    real ``_probe_freshness`` via test fakes.

    Returns (builder, persistence, fake_prober). The fake prober is what
    the caller passes to ``_invoke_probe`` to take effect via patching
    of ``freshness.SectionFreshnessProber``.

    The builder's ``_probe_freshness`` runs the production code path;
    only the prober construction is intercepted.
    """
    from autom8_asana.dataframes.builders.progressive import (
        ProgressiveProjectBuilder,
    )

    persistence = _FakePersistence(manifest)
    builder = ProgressiveProjectBuilder.__new__(ProgressiveProjectBuilder)
    builder._persistence = persistence
    builder._project_gid = manifest.project_gid
    builder._entity_type = manifest.entity_type
    builder._client = MagicMock()
    builder._dataframe_view = None
    builder._schema = MagicMock()
    builder._schema.version = manifest.schema_version

    # Build the fake prober the test invocation will inject into the
    # freshness module via patch.object.
    fake_prober = MagicMock()
    fake_prober.probe_all_async = AsyncMock(return_value=probe_results or [])
    fake_prober.apply_deltas_async = AsyncMock(return_value=(len(applied_gids), applied_gids))
    persistence.save_should_raise = save_should_raise
    return builder, persistence, fake_prober


class TestStampReseedIntegration:
    """Integration tests for the §2.2/§2.2.1/§2.6 stamp + re-seed pass
    inside ``_probe_freshness``.

    Logger assertion strategy: this project uses ``autom8y_log`` (structlog
    backend) which does not always propagate to pytest's ``caplog`` fixture.
    We instead patch the module-level ``logger`` on
    ``autom8_asana.dataframes.builders.progressive`` and inspect
    ``call_args_list`` -- mirroring the pattern in
    ``tests/unit/dataframes/test_cache_integration.py`` etc.
    """

    @staticmethod
    def _patch_module_logger() -> MagicMock:
        """Replace ``progressive.logger`` with a MagicMock and return it.

        Caller is responsible for restoring; we use this inside a
        ``try/finally`` block in each test.
        """
        import autom8_asana.dataframes.builders.progressive as progressive_mod

        return progressive_mod.logger

    async def test_t14_delta_failure_does_not_stamp(self) -> None:
        """T14 (SCAR): a section whose verdict is CONTENT_CHANGED but
        whose delta-apply FAILED (GID NOT in ``applied_gids``) does NOT
        get its ``last_verified_at`` stamped. A sibling CLEAN section in
        the same warm IS stamped.
        """
        watermark = datetime(2026, 5, 27, 0, 0, tzinfo=UTC)
        manifest = _make_manifest(
            {
                "sec_clean": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name="Active",
                    watermark=watermark,
                    gid_hash="abc",
                ),
                "sec_failed_delta": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name="Onboarding",
                    watermark=watermark,
                    gid_hash="def",
                ),
            }
        )
        probe_results = [
            SectionProbeResult("sec_clean", ProbeVerdict.CLEAN),
            SectionProbeResult("sec_failed_delta", ProbeVerdict.CONTENT_CHANGED),
        ]
        # apply_deltas_async returns (count=0, applied_gids=frozenset())
        # -> sec_failed_delta is NOT in applied_gids.
        builder, persistence, fake_prober = _make_progressive_builder_with_fakes(
            manifest,
            probe_results=probe_results,
            applied_gids=frozenset(),
        )
        manifest.completed_sections = 2  # ensure is_complete()
        await self._invoke_probe(builder, manifest, section_names={}, fake_prober=fake_prober)

        out_clean = persistence.manifest.sections["sec_clean"]
        out_failed = persistence.manifest.sections["sec_failed_delta"]
        assert out_clean.last_verified_at is not None, "T14 FAIL: CLEAN section should be stamped."
        assert out_failed.last_verified_at is None, (
            "T14 FAIL: a delta-requiring verdict whose delta-apply "
            "FAILED was stamped anyway. Stamp must gate on "
            "applied_gids membership (ADR-006 §Decision-5c / TDD §2.2 D4)."
        )

    async def test_t10_stamp_phase_failure_emits_metric(self) -> None:
        """T10 (amended): a stamp-phase exception emits
        ``section_last_verified_stamp_failed`` rather than disappearing
        into the outer BROAD-CATCH. The warm still completes
        (no re-raise).
        """
        import autom8_asana.dataframes.builders.progressive as progressive_mod

        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name="Active",
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="abc",
                )
            }
        )
        manifest.completed_sections = 1
        probe_results = [SectionProbeResult("sec_1", ProbeVerdict.CLEAN)]
        builder, persistence, fake_prober = _make_progressive_builder_with_fakes(
            manifest,
            probe_results=probe_results,
            save_should_raise=True,
        )
        original_logger = progressive_mod.logger
        progressive_mod.logger = MagicMock()
        try:
            probed, _delta = await self._invoke_probe(
                builder, manifest, section_names={}, fake_prober=fake_prober
            )
            # Warm completes; no re-raise.
            assert probed == 1
            # Metric emitted (assert on the error() call).
            error_events = [
                c.args[0] for c in progressive_mod.logger.error.call_args_list if c.args
            ]
            assert "section_last_verified_stamp_failed" in error_events, (
                "T10 FAIL: stamp-phase exception was silently swallowed. "
                "Must emit section_last_verified_stamp_failed (ADR-006 "
                "§Decision-9 / TDD §2.2 D6)."
            )
        finally:
            progressive_mod.logger = original_logger

    @pytest.mark.scar
    async def test_t11_all_names_null_fires_loud_violation(self) -> None:
        """T11 (SCAR): a ≥2-section manifest with all-null names fires
        ``section_name_contract_violation`` rather than silently
        degrading. On a never-warmed manifest the alarm tier is WARN
        (reseed_window=true).
        """
        import autom8_asana.dataframes.builders.progressive as progressive_mod

        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=None,
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="abc",
                ),
                "sec_2": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=None,
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="def",
                ),
            }
        )
        manifest.completed_sections = 2
        # PROBE_FAILED on every section -> nothing stamps -> alarm tier
        # is reseed_window=true (WARN).
        probe_results = [
            SectionProbeResult("sec_1", ProbeVerdict.PROBE_FAILED),
            SectionProbeResult("sec_2", ProbeVerdict.PROBE_FAILED),
        ]
        builder, _persistence, fake_prober = _make_progressive_builder_with_fakes(
            manifest,
            probe_results=probe_results,
        )
        original_logger = progressive_mod.logger
        progressive_mod.logger = MagicMock()
        try:
            await self._invoke_probe(builder, manifest, section_names={}, fake_prober=fake_prober)
            warning_events = [
                c.args[0] for c in progressive_mod.logger.warning.call_args_list if c.args
            ]
            assert "section_name_contract_violation" in warning_events, (
                "T11 FAIL: a ≥2-section manifest with all-null names did "
                "NOT fire the contract violation. The feature would ship "
                "GREEN as a silent inert signal on prod (the false-GREEN "
                "QA D1 named)."
            )
            # Verify it carries reseed_window=true.
            matching = [
                c
                for c in progressive_mod.logger.warning.call_args_list
                if c.args and c.args[0] == "section_name_contract_violation"
            ]
            assert matching, "expected at least one matching call"
            extra = matching[0].kwargs.get("extra", {})
            assert extra.get("reseed_window") is True
        finally:
            progressive_mod.logger = original_logger

    @pytest.mark.scar
    async def test_t11_post_warm_null_name_fires_error_tier(self) -> None:
        """T11 (SCAR, ERROR tier): a manifest with at least one stamped
        section AND any null-named section fires the ERROR tier
        (reseed_window=false) -- this is the true post-warm contract
        violation that should page.
        """
        import autom8_asana.dataframes.builders.progressive as progressive_mod

        prior_stamp = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)
        manifest = _make_manifest(
            {
                "sec_named": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name="Active",
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="abc",
                    last_verified_at=prior_stamp,  # already warmed
                ),
                "sec_null": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=None,
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="def",
                ),
            }
        )
        manifest.completed_sections = 2
        probe_results = [
            SectionProbeResult("sec_named", ProbeVerdict.CLEAN),
            SectionProbeResult("sec_null", ProbeVerdict.PROBE_FAILED),
        ]
        builder, _persistence, fake_prober = _make_progressive_builder_with_fakes(
            manifest,
            probe_results=probe_results,
        )
        original_logger = progressive_mod.logger
        progressive_mod.logger = MagicMock()
        try:
            await self._invoke_probe(builder, manifest, section_names={}, fake_prober=fake_prober)
            error_events = [
                c.args[0] for c in progressive_mod.logger.error.call_args_list if c.args
            ]
            assert "section_name_contract_violation" in error_events, (
                "T11 (ERROR tier) FAIL: post-warm null-name violation did "
                "not fire at ERROR. Should page."
            )
            # Verify reseed_window=false on the ERROR-tier emission.
            matching = [
                c
                for c in progressive_mod.logger.error.call_args_list
                if c.args and c.args[0] == "section_name_contract_violation"
            ]
            assert matching
            assert matching[0].kwargs.get("extra", {}).get("reseed_window") is False
        finally:
            progressive_mod.logger = original_logger

    @pytest.mark.scar
    async def test_t16_reseed_threading_actually_populates_names(self) -> None:
        """T16 (SCAR): with a ``section_names`` map supplied, COMPLETE
        sections whose ``info.name is None`` get re-seeded in the SAME
        single save as the stamps. On a build that adds carry-forward
        but does NOT thread ``section_names`` into ``_probe_freshness``,
        the assertion ``info.name == section_names[gid]`` fails.
        """
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=None,
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="abc",
                ),
                "sec_2": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=None,
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="def",
                ),
            }
        )
        manifest.completed_sections = 2
        section_names = {"sec_1": "Active", "sec_2": "Onboarding"}
        probe_results = [
            SectionProbeResult("sec_1", ProbeVerdict.CLEAN),
            SectionProbeResult("sec_2", ProbeVerdict.CLEAN),
        ]
        builder, persistence, fake_prober = _make_progressive_builder_with_fakes(
            manifest,
            probe_results=probe_results,
        )
        await self._invoke_probe(
            builder, manifest, section_names=section_names, fake_prober=fake_prober
        )
        for gid, name in section_names.items():
            assert persistence.manifest.sections[gid].name == name, (
                f"T16 FAIL: section {gid} name was not re-seeded from "
                "section_names (expected {name!r}). The build adds "
                "carry-forward but does not consume section_names "
                "inside _probe_freshness's stamp block (TDD §2.2.1 "
                "edit 2)."
            )
        # And ONE save -- re-seed + stamp share the single write.
        assert persistence.save_count == 1, (
            f"T16 FAIL: re-seed + stamp produced {persistence.save_count} saves; "
            "should be 1 (single _save_manifest_async write per ADR §Decision-7)."
        )

    async def test_single_section_null_name_does_not_fire_violation(self) -> None:
        """Trivial case per §2.6: a 0-or-1-section manifest with a null
        name does NOT fire the contract violation (no ambiguity about
        the denominator).
        """
        import autom8_asana.dataframes.builders.progressive as progressive_mod

        manifest = _make_manifest(
            {
                "sec_solo": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=None,
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash="abc",
                )
            }
        )
        manifest.completed_sections = 1
        probe_results = [SectionProbeResult("sec_solo", ProbeVerdict.CLEAN)]
        builder, _persistence, fake_prober = _make_progressive_builder_with_fakes(
            manifest,
            probe_results=probe_results,
        )
        original_logger = progressive_mod.logger
        progressive_mod.logger = MagicMock()
        try:
            await self._invoke_probe(builder, manifest, section_names={}, fake_prober=fake_prober)
            warning_events = [
                c.args[0] for c in progressive_mod.logger.warning.call_args_list if c.args
            ]
            error_events = [
                c.args[0] for c in progressive_mod.logger.error.call_args_list if c.args
            ]
            assert "section_name_contract_violation" not in warning_events
            assert "section_name_contract_violation" not in error_events
        finally:
            progressive_mod.logger = original_logger

    async def _invoke_probe(
        self,
        builder: Any,
        manifest: SectionManifest,
        section_names: dict[str, str],
        fake_prober: MagicMock,
    ) -> tuple[int, int]:
        """Run ``_probe_freshness`` with section-freshness-probe enabled
        and the fake prober injected via ``freshness.SectionFreshnessProber``.

        Bypasses the settings gate by patching ``get_settings`` to a
        stub returning ``section_freshness_probe=='1'``.
        """
        import autom8_asana.dataframes.builders.freshness as freshness_mod
        import autom8_asana.settings as settings_mod
        from autom8_asana.settings import get_settings

        real_get_settings = get_settings
        real_prober_class = freshness_mod.SectionFreshnessProber
        try:
            stub = MagicMock()
            stub.runtime.section_freshness_probe = "1"
            settings_mod.get_settings = MagicMock(return_value=stub)  # type: ignore[assignment]
            # Patch the production prober constructor to return our fake.
            freshness_mod.SectionFreshnessProber = MagicMock(return_value=fake_prober)  # type: ignore[assignment]
            return await builder._probe_freshness(manifest, section_names=section_names)
        finally:
            settings_mod.get_settings = real_get_settings  # type: ignore[assignment]
            freshness_mod.SectionFreshnessProber = real_prober_class  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# read_manifest_sync running-loop guard
# ---------------------------------------------------------------------------


class TestReadManifestSyncLoopGuard:
    """QA-gate-2 condition 4: the running-loop guard raises LOUDLY when
    invoked from within an async context (rather than silently nesting a
    second loop).
    """

    def test_no_running_loop_drives_asyncio_run(self) -> None:
        """The sync path: no running loop -> ``asyncio.run`` succeeds."""
        # class-(c): MUST stay sync. This exercises read_manifest_sync's
        # own internal asyncio.run() from a no-running-loop context;
        # making this test async would supply a running loop and invert
        # the no-loop precondition under test.
        persistence = MagicMock()
        sentinel = object()

        async def _coro(project_gid: str) -> Any:
            return sentinel

        persistence.get_manifest_async = _coro
        out = read_manifest_sync(persistence, "proj_1")
        assert out is sentinel

    def test_running_loop_raises_loudly(self) -> None:
        """The async-context path: ``RuntimeError`` raised explicitly
        with a clear message; NOT silently nested.
        """
        # class-(c): MUST stay sync. The asyncio.run() below is
        # load-bearing scaffolding -- it establishes the running-loop
        # context the guard is asserted against. Converting to async def
        # would already provide that loop and remove the very transition
        # (sync -> running-loop) this test exists to cover.
        persistence = MagicMock()
        persistence.get_manifest_async = AsyncMock(return_value=None)

        async def _run_inside_loop() -> None:
            # Inside this coroutine an event loop IS running.
            with pytest.raises(RuntimeError, match="running event loop"):
                read_manifest_sync(persistence, "proj_1")

        asyncio.run(_run_inside_loop())


# ---------------------------------------------------------------------------
# compute_verification_age reader (in-scope join)
# ---------------------------------------------------------------------------


class TestComputeVerificationAge:
    """compute_verification_age: TDD §2.3 reader re-point + §2.6 join
    semantics + §Decision-6 backfill.
    """

    def test_t6_cold_section_excluded_from_signal(self) -> None:
        """T6: a cold-classified section's stale stamp does NOT set the
        ``verification_age`` floor; only ACTIVE-classified sections
        count.
        """
        # Use a known entity_type ("offer") whose classifier exists.
        # The classifier active_sections() returns lower-cased names.
        from autom8_asana.models.business.activity import CLASSIFIERS

        offer = CLASSIFIERS.get("offer")
        assert offer is not None
        active_names = list(offer.active_sections())
        if not active_names:
            pytest.skip("offer classifier has no ACTIVE sections")
        active_name = active_names[0]

        active_stamp = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
        cold_stamp = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        manifest = _make_manifest(
            {
                "sec_active": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=active_name,
                    last_verified_at=active_stamp,
                ),
                "sec_cold": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name="not-a-real-section-zzz",
                    last_verified_at=cold_stamp,  # stale but inactive
                ),
            }
        )
        now = datetime(2026, 5, 27, 19, 0, tzinfo=UTC)
        v = compute_verification_age(
            manifest=manifest,
            entity_type="offer",
            threshold_seconds=21600,
            now=now,
        )
        assert v.available is True
        # Active section is the floor; cold section is excluded.
        assert v.oldest_verified_at == active_stamp
        assert v.in_scope_count == 1
        assert v.backfill_used is False

    def test_t5_legacy_backfill_to_written_at(self) -> None:
        """T5: a manifest with ``last_verified_at=None`` on in-scope
        sections falls back to ``written_at`` (the §Decision-6 backfill
        path); ``backfill_used`` is True.
        """
        from autom8_asana.models.business.activity import CLASSIFIERS

        offer = CLASSIFIERS.get("offer")
        assert offer is not None
        active_names = list(offer.active_sections())
        if not active_names:
            pytest.skip("offer classifier has no ACTIVE sections")
        active_name = active_names[0]

        written_at = datetime(2026, 5, 27, 6, 0, tzinfo=UTC)
        manifest = _make_manifest(
            {
                "sec_active": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=active_name,
                    written_at=written_at,
                    last_verified_at=None,
                )
            }
        )
        now = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
        v = compute_verification_age(
            manifest=manifest,
            entity_type="offer",
            threshold_seconds=21600,
            now=now,
        )
        assert v.available is True
        assert v.oldest_verified_at == written_at
        assert v.backfill_used is True

    def test_t9_classifier_missing_returns_unavailable(self) -> None:
        manifest = _make_manifest({})
        v = compute_verification_age(
            manifest=manifest,
            entity_type="unknown_entity",
            threshold_seconds=21600,
        )
        assert v.available is False
        assert v.max_age_seconds == 0

    def test_join_empty_returns_unavailable(self) -> None:
        """T1's null-name degrade: when no name matches the classifier,
        the join is empty -> unavailable.
        """
        manifest = _make_manifest(
            {
                "sec_1": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=5,
                    name=None,
                ),
            }
        )
        v = compute_verification_age(
            manifest=manifest,
            entity_type="offer",
            threshold_seconds=21600,
        )
        assert v.available is False

    def test_manifest_none_returns_unavailable(self) -> None:
        v = compute_verification_age(
            manifest=None,
            entity_type="offer",
            threshold_seconds=21600,
        )
        assert v.available is False


# ---------------------------------------------------------------------------
# T7: two-signal output
# ---------------------------------------------------------------------------


class TestT7TwoSignalEnvelope:
    """T7: an envelope with both signals populated -- mutation_age old
    (context), verification_age young (alarmable).
    """

    def test_two_signal_envelope_carries_both(self) -> None:
        from autom8_asana.metrics.freshness import (
            FreshnessReport,
            VerificationAge,
            format_json_envelope,
        )

        old_parquet = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
        fresh_stamp = datetime(2026, 5, 27, 18, 0, tzinfo=UTC)
        report = FreshnessReport(
            oldest_mtime=old_parquet,
            newest_mtime=old_parquet,
            max_age_seconds=62 * 86400,
            threshold_seconds=21600,
            parquet_count=10,
            bucket="b",
            prefix="p/",
        ).with_verification(
            VerificationAge(
                oldest_verified_at=fresh_stamp,
                max_age_seconds=120,
                threshold_seconds=21600,
                in_scope_count=5,
                backfill_used=False,
                available=True,
            )
        )
        envelope = format_json_envelope(
            report=report,
            value=1234.0,
            metric_name="active_mrr",
            currency="USD",
            env="production",
            bucket_evidence="ev",
        )
        assert envelope["schema_version"] == 2
        # v1 mutation block intact.
        assert envelope["freshness"]["max_age_seconds"] == 62 * 86400
        assert envelope["mutation_age"] == envelope["freshness"]
        # v2 verification block.
        assert envelope["verification_age"]["available"] is True
        assert envelope["verification_age"]["max_age_seconds"] == 120
        assert envelope["verification_age"]["stale"] is False
        # verification < threshold -> not stale; mutation > threshold ->
        # stale True (context, but under ADR-006 §Decision-4 mutation is
        # NOT --strict-promoted).
        assert envelope["freshness"]["stale"] is True


# ---------------------------------------------------------------------------
# D11 (QA-gate-2): delta-apply path threads `name=` into write_section_async
# ---------------------------------------------------------------------------


@pytest.mark.scar
class TestD11DeltaApplyThreadsName:
    """D11 (SCAR / QA-gate-2): the prober's delta-apply path supplies
    ``name=`` to ``write_section_async`` from the ``section_names`` map
    threaded into ``SectionFreshnessProber.__init__``.

    Without the threading, ``write_section_async`` is called WITHOUT
    ``name=`` -> ``update_manifest_section_async(name=None)`` ->
    ``mark_section_complete(name=None)`` -> the carry-forward falls back
    to ``prior.name``, which is ``None`` on existing prod manifests. A
    section renamed/deleted in Asana mid-warm (and therefore absent from
    ``_list_sections()`` -> not in the warm-entry names map) would lose
    its name permanently AND get stamped ``last_verified_at=now`` ->
    permanent ERROR-tier ``section_name_contract_violation``.

    This test forces the delta-apply path via a CONTENT_CHANGED probe
    result and a non-empty existing parquet, then asserts that
    ``write_section_async`` was called with ``name="orig"`` (the
    warm-entry name from ``section_names``), NOT ``None``.
    """

    async def test_delta_apply_supplies_name_from_section_names(self) -> None:
        import polars as pl

        from autom8_asana.dataframes.builders.freshness import (
            SectionFreshnessProber,
        )

        watermark = datetime(2026, 5, 27, 0, 0, tzinfo=UTC)
        section_gid = "sec_renamed"
        manifest = _make_manifest(
            {
                section_gid: SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=2,
                    # prod steady state: name wiped to None by the
                    # pre-D1 mark_section_complete defect, persisted
                    # to S3 manifests in production.
                    name=None,
                    watermark=watermark,
                    gid_hash=compute_gid_hash(["t1", "t2"]),
                )
            }
        )

        # Existing parquet (DataFrame with a 'gid' column so the delta
        # path takes the merge branch, not the full-refetch fallback).
        existing_df = pl.DataFrame({"gid": ["t1", "t2"]})

        # Stub persistence: read_section_async returns the existing
        # parquet; write_section_async records its kwargs.
        persistence = MagicMock()
        persistence.read_section_async = AsyncMock(return_value=existing_df)
        persistence.write_section_async = AsyncMock(return_value=True)
        persistence.update_manifest_section_async = AsyncMock(return_value=manifest)

        # Stub client: tasks.list_async returns 0 modified tasks (the
        # delta-apply path collapses to "removed nothing, added
        # nothing"; merged_df == existing_df; we only care that the
        # final write_section_async call carries name=).
        client = MagicMock()
        pi_empty = MagicMock()
        pi_empty.collect = AsyncMock(return_value=[])
        client.tasks.list_async.return_value = pi_empty

        schema = MagicMock()
        schema.version = "v1"
        # Make to_polars_schema return something Polars accepts.
        schema.to_polars_schema = MagicMock(return_value={"gid": pl.Utf8})

        # The warm-entry names map (the live single source of truth).
        # Section is in _list_sections() under its current name "orig".
        section_names: dict[str, str | None] = {section_gid: "orig"}

        prober = SectionFreshnessProber(
            client=client,
            persistence=persistence,
            project_gid="proj_1",
            manifest=manifest,
            schema=schema,
            section_names=section_names,
        )

        # Drive the delta path directly via apply_deltas_async with a
        # CONTENT_CHANGED probe result. This is the path that previously
        # called write_section_async WITHOUT name=.
        probe = SectionProbeResult(
            section_gid,
            ProbeVerdict.CONTENT_CHANGED,
            current_gids=["t1", "t2"],
            current_gid_hash=compute_gid_hash(["t1", "t2"]),
        )

        updated, applied = await prober.apply_deltas_async([probe])

        assert updated == 1, "delta-apply did not succeed on the fixture"
        assert section_gid in applied, "applied_gids must include the section to be stamp-eligible"
        # The load-bearing assertion: write_section_async was called
        # with name="orig" (NOT None). Without the D11 fix, the call
        # would lack `name=` and the kwarg would be absent (defaulting
        # to None inside write_section_async itself).
        assert persistence.write_section_async.await_count == 1, (
            "D11 FAIL: expected exactly one write_section_async call on the delta-apply path."
        )
        call = persistence.write_section_async.await_args
        # The kwarg MUST be supplied and MUST be the warm-entry name.
        assert "name" in call.kwargs, (
            "D11 FAIL: write_section_async was called without name= -- "
            "the delta-apply path is not threading the warm-entry name. "
            "A section renamed/deleted in Asana mid-warm would land "
            "with name=None and stamp last_verified_at=now, producing a "
            "permanent ERROR-tier section_name_contract_violation."
        )
        assert call.kwargs["name"] == "orig", (
            f"D11 FAIL: write_section_async received name="
            f"{call.kwargs['name']!r}, expected 'orig' from "
            "section_names. The prober's delta-apply path is not "
            "consuming the single-source-of-truth names map."
        )

    async def test_full_refetch_supplies_name_from_section_names(self) -> None:
        """D11 (SCAR): the full-refetch fallback path
        (``_full_section_refetch`` invoked on NO_BASELINE or missing
        parquet) ALSO supplies ``name=`` to ``write_section_async``.
        Symmetric with the delta-merge path."""
        import polars as pl

        from autom8_asana.dataframes.builders.freshness import (
            SectionFreshnessProber,
        )
        from autom8_asana.dataframes.views.dataframe_view import (
            DataFrameViewPlugin,
        )

        section_gid = "sec_no_baseline"
        manifest = _make_manifest(
            {
                section_gid: SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=0,
                    name=None,
                    # gid_hash is None -> NO_BASELINE verdict.
                )
            }
        )

        persistence = MagicMock()
        # read_section_async returns None -> _full_section_refetch path.
        persistence.read_section_async = AsyncMock(return_value=None)
        persistence.write_section_async = AsyncMock(return_value=True)
        persistence.update_manifest_section_async = AsyncMock(return_value=manifest)

        client = MagicMock()
        # Full refetch fetches with BASE_OPT_FIELDS; return 1 task so we
        # take the populated-write branch (not the empty branch).
        tasks_pi = MagicMock()
        task_obj = MagicMock()
        task_obj.gid = "t1"
        task_obj.model_dump = MagicMock(return_value={"gid": "t1", "name": "task one"})
        tasks_pi.collect = AsyncMock(return_value=[task_obj])
        client.tasks.list_async.return_value = tasks_pi

        schema = MagicMock()
        schema.version = "v1"
        schema.to_polars_schema = MagicMock(return_value={"gid": pl.Utf8})

        # Minimal stub view: returns row dicts that match the schema.
        view = MagicMock(spec=DataFrameViewPlugin)
        view._extract_rows_async = AsyncMock(return_value=[{"gid": "t1"}])

        section_names: dict[str, str | None] = {section_gid: "orig"}

        prober = SectionFreshnessProber(
            client=client,
            persistence=persistence,
            project_gid="proj_1",
            manifest=manifest,
            schema=schema,
            dataframe_view=view,
            section_names=section_names,
        )

        probe = SectionProbeResult(
            section_gid,
            ProbeVerdict.NO_BASELINE,
            current_gids=["t1"],
            current_gid_hash=compute_gid_hash(["t1"]),
        )

        updated, applied = await prober.apply_deltas_async([probe])
        assert updated == 1
        assert section_gid in applied
        assert persistence.write_section_async.await_count == 1
        call = persistence.write_section_async.await_args
        assert "name" in call.kwargs and call.kwargs["name"] == "orig", (
            "D11 FAIL: _full_section_refetch did not thread the "
            "warm-entry name into write_section_async."
        )

    async def test_full_refetch_empty_tasks_supplies_name(self) -> None:
        """D11 (SCAR): the empty-tasks branch of ``_full_section_refetch``
        (calling ``update_manifest_section_async`` directly when the
        section has zero tasks) ALSO threads ``name=``."""
        from autom8_asana.dataframes.builders.freshness import (
            SectionFreshnessProber,
        )

        section_gid = "sec_empty"
        manifest = _make_manifest(
            {
                section_gid: SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=0,
                    name=None,
                )
            }
        )

        persistence = MagicMock()
        persistence.read_section_async = AsyncMock(return_value=None)
        persistence.update_manifest_section_async = AsyncMock(return_value=manifest)
        persistence.write_section_async = AsyncMock(return_value=True)

        client = MagicMock()
        # Empty list of tasks -> empty branch.
        pi_empty = MagicMock()
        pi_empty.collect = AsyncMock(return_value=[])
        client.tasks.list_async.return_value = pi_empty

        schema = MagicMock()
        schema.version = "v1"

        section_names: dict[str, str | None] = {section_gid: "orig"}

        prober = SectionFreshnessProber(
            client=client,
            persistence=persistence,
            project_gid="proj_1",
            manifest=manifest,
            schema=schema,
            section_names=section_names,
        )

        probe = SectionProbeResult(
            section_gid,
            ProbeVerdict.NO_BASELINE,
            current_gids=[],
            current_gid_hash=compute_gid_hash([]),
        )

        updated, applied = await prober.apply_deltas_async([probe])
        assert updated == 1
        assert section_gid in applied
        # The empty branch routes through update_manifest_section_async
        # (not write_section_async) -- assert THAT path got name=.
        assert persistence.update_manifest_section_async.await_count == 1
        call = persistence.update_manifest_section_async.await_args
        assert call.kwargs.get("name") == "orig", (
            "D11 FAIL: the empty-tasks branch of _full_section_refetch "
            "did not thread name= into update_manifest_section_async; "
            "an empty re-fetched section would land with name=None."
        )

    async def test_unknown_section_gid_falls_back_to_none(self) -> None:
        """D11 negative: if a section GID is NOT in ``section_names``
        (e.g. the section was deleted from Asana mid-warm and is no
        longer in ``_list_sections()``), the delta-apply still supplies
        ``name=`` -- but the value is ``None``. The downstream
        ``mark_section_complete`` carry-forward then falls back to
        ``prior.name`` (which may also be ``None`` on prod), and the
        §2.6 alarm tier surfaces the resulting null-name section as the
        true contract violation. No silent breakage; behavior matches
        the design intent that the warm-entry list is the single source
        of truth."""
        import polars as pl

        from autom8_asana.dataframes.builders.freshness import (
            SectionFreshnessProber,
        )

        section_gid = "sec_orphan"
        manifest = _make_manifest(
            {
                section_gid: SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=2,
                    name=None,
                    watermark=datetime(2026, 5, 27, 0, 0, tzinfo=UTC),
                    gid_hash=compute_gid_hash(["t1", "t2"]),
                )
            }
        )

        existing_df = pl.DataFrame({"gid": ["t1", "t2"]})
        persistence = MagicMock()
        persistence.read_section_async = AsyncMock(return_value=existing_df)
        persistence.write_section_async = AsyncMock(return_value=True)
        persistence.update_manifest_section_async = AsyncMock(return_value=manifest)

        client = MagicMock()
        pi_empty = MagicMock()
        pi_empty.collect = AsyncMock(return_value=[])
        client.tasks.list_async.return_value = pi_empty

        schema = MagicMock()
        schema.version = "v1"
        schema.to_polars_schema = MagicMock(return_value={"gid": pl.Utf8})

        # Empty names map -> section is "orphan" w.r.t. warm-entry list.
        prober = SectionFreshnessProber(
            client=client,
            persistence=persistence,
            project_gid="proj_1",
            manifest=manifest,
            schema=schema,
            section_names={},
        )

        probe = SectionProbeResult(
            section_gid,
            ProbeVerdict.CONTENT_CHANGED,
            current_gids=["t1", "t2"],
            current_gid_hash=compute_gid_hash(["t1", "t2"]),
        )

        await prober.apply_deltas_async([probe])
        call = persistence.write_section_async.await_args
        assert "name" in call.kwargs, (
            "D11: write_section_async must always receive name= kwarg "
            "(even if the value is None for orphan GIDs)."
        )
        assert call.kwargs["name"] is None, (
            "D11: GID not in section_names should receive name=None "
            "(orphan-window contract); the §2.6 alarm tier surfaces "
            "this as the true contract violation downstream."
        )

    def test_prober_default_section_names_is_empty(self) -> None:
        """D11: the new ``section_names`` constructor kwarg defaults to
        ``None`` (normalized to empty dict internally). Existing
        single-process tests that construct the prober without the new
        kwarg keep working."""
        from autom8_asana.dataframes.builders.freshness import (
            SectionFreshnessProber,
        )

        manifest = _make_manifest({})
        prober = SectionFreshnessProber(
            client=MagicMock(),
            persistence=MagicMock(),
            project_gid="proj_1",
            manifest=manifest,
            schema=MagicMock(),
        )
        # Internal accessor: empty dict, not None (consumers do
        # ``self._section_names.get(gid)`` -- None would crash).
        assert prober._section_names == {}
