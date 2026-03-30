"""Contract tests LO-01 through LO-20 for Domain 2 lifecycle observation.

LO-09, LO-10, LO-11 are implemented in tests/unit/metrics/test_expr.py (Sprint 1).
This file covers the remaining 16 contracts: LO-01 through LO-08, LO-12 through LO-20.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from autom8_asana.lifecycle.loop_detector import LoopDetector
from autom8_asana.lifecycle.observation import (
    EntityStageTimeline,
    StageTransitionEmitter,
    StageTransitionRecord,
)
from autom8_asana.lifecycle.observation_store import StageTransitionStore
from autom8_asana.lifecycle.webhook_dispatcher import (
    LifecycleWebhookDispatcher,
    WebhookDispatcherConfig,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_EXPECTED_FIELDS = (
    "entity_gid",
    "entity_type",
    "business_gid",
    "from_stage",
    "to_stage",
    "pipeline_stage_num",
    "transition_type",
    "entered_at",
    "exited_at",
    "automation_result_id",
    "duration_ms",
)


def _make_record(
    entity_gid: str = "gid-001",
    entity_type: str = "Process",
    business_gid: str | None = "biz-001",
    from_stage: str | None = "outreach",
    to_stage: str = "sales",
    pipeline_stage_num: int = 2,
    transition_type: str = "converted",
    entered_at: datetime | None = None,
    exited_at: datetime | None = None,
    automation_result_id: str | None = "rule_1",
    duration_ms: float | None = 120.0,
) -> StageTransitionRecord:
    """Factory for StageTransitionRecord with sensible defaults."""
    return StageTransitionRecord(
        entity_gid=entity_gid,
        entity_type=entity_type,
        business_gid=business_gid,
        from_stage=from_stage,
        to_stage=to_stage,
        pipeline_stage_num=pipeline_stage_num,
        transition_type=transition_type,
        entered_at=entered_at or datetime(2026, 3, 1, tzinfo=UTC),
        exited_at=exited_at,
        automation_result_id=automation_result_id,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# LO-01: StageTransitionRecord is frozen with all fields
# ---------------------------------------------------------------------------


class TestLO01StageTransitionRecordFrozen:
    """LO-01: StageTransitionRecord is a frozen dataclass with all expected fields."""

    def test_all_fields_present(self) -> None:
        """LO-01: All 11 fields are present on StageTransitionRecord."""
        actual_names = tuple(f.name for f in fields(StageTransitionRecord))
        assert actual_names == _EXPECTED_FIELDS

    def test_field_count(self) -> None:
        """LO-01: StageTransitionRecord has exactly 11 fields."""
        assert len(fields(StageTransitionRecord)) == 11

    def test_frozen_mutation_raises(self) -> None:
        """LO-01: Mutation of a frozen instance raises FrozenInstanceError."""
        record = _make_record()
        with pytest.raises(FrozenInstanceError):
            record.entity_gid = "changed"  # type: ignore[misc]

    def test_frozen_all_fields_immutable(self) -> None:
        """LO-01: Every field rejects mutation via normal attribute assignment."""
        record = _make_record()
        for field_obj in fields(record):
            with pytest.raises(FrozenInstanceError):
                setattr(record, field_obj.name, "tampered")


# ---------------------------------------------------------------------------
# LO-02: EntityStageTimeline.time_in_stage()
# ---------------------------------------------------------------------------


class TestLO02TimeInStage:
    """LO-02: EntityStageTimeline.time_in_stage() sums closed intervals."""

    def test_two_closed_intervals_same_stage(self) -> None:
        """LO-02: Sum of durations across 2 closed intervals in the same stage."""
        r1 = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 6, tzinfo=UTC),  # 5 days
        )
        r2 = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 2, 1, tzinfo=UTC),
            exited_at=datetime(2026, 2, 4, tzinfo=UTC),  # 3 days
        )
        timeline = EntityStageTimeline(
            entity_gid="gid-001",
            entity_type="Process",
            business_gid="biz-001",
            intervals=(r1, r2),
        )
        result = timeline.time_in_stage("sales")
        assert result is not None
        assert result.days == 8

    def test_returns_none_for_unknown_stage(self) -> None:
        """LO-02: Returns None for a stage not present in any interval."""
        r = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 6, tzinfo=UTC),
        )
        timeline = EntityStageTimeline(
            entity_gid="gid-001",
            entity_type="Process",
            business_gid="biz-001",
            intervals=(r,),
        )
        assert timeline.time_in_stage("onboarding") is None


# ---------------------------------------------------------------------------
# LO-03: EntityStageTimeline.current_stage()
# ---------------------------------------------------------------------------


class TestLO03CurrentStage:
    """LO-03: current_stage() returns last open interval's to_stage."""

    def test_last_interval_open(self) -> None:
        """LO-03: current_stage returns to_stage of last interval with exited_at=None."""
        r_closed = _make_record(
            to_stage="outreach",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        r_open = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 10, tzinfo=UTC),
            exited_at=None,
        )
        timeline = EntityStageTimeline(
            entity_gid="gid-001",
            entity_type="Process",
            business_gid="biz-001",
            intervals=(r_closed, r_open),
        )
        assert timeline.current_stage() == "sales"

    def test_all_closed_returns_none(self) -> None:
        """LO-03: Returns None when all intervals are closed."""
        r = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        timeline = EntityStageTimeline(
            entity_gid="gid-001",
            entity_type="Process",
            business_gid="biz-001",
            intervals=(r,),
        )
        assert timeline.current_stage() is None


# ---------------------------------------------------------------------------
# LO-04: EntityStageTimeline.days_in_current_stage()
# ---------------------------------------------------------------------------


class TestLO04DaysInCurrentStage:
    """LO-04: days_in_current_stage() returns days since entering current stage."""

    def test_three_days_ago(self) -> None:
        """LO-04: Entity entered 3 days ago -> days_in_current_stage() == 3."""
        entered = datetime.now(UTC) - timedelta(days=3)
        r = _make_record(
            to_stage="implementation",
            entered_at=entered,
            exited_at=None,
        )
        timeline = EntityStageTimeline(
            entity_gid="gid-001",
            entity_type="Process",
            business_gid="biz-001",
            intervals=(r,),
        )
        assert timeline.days_in_current_stage() == 3

    def test_no_open_interval_returns_zero(self) -> None:
        """LO-04: Returns 0 when there is no open interval."""
        r = _make_record(
            to_stage="sales",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        timeline = EntityStageTimeline(
            entity_gid="gid-001",
            entity_type="Process",
            business_gid="biz-001",
            intervals=(r,),
        )
        assert timeline.days_in_current_stage() == 0


# ---------------------------------------------------------------------------
# LO-05: StageTransitionStore round-trip (save + load)
# ---------------------------------------------------------------------------


class TestLO05StoreRoundTrip:
    """LO-05: StageTransitionStore append -> load round-trip."""

    def test_append_and_load(self, tmp_path) -> None:
        """LO-05: Append a record, load it back, verify data matches."""
        store = StageTransitionStore(base_dir=tmp_path)
        entered = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        exited = datetime(2026, 3, 5, 12, 0, 0, tzinfo=UTC)
        record = _make_record(
            entity_gid="gid-rt",
            entity_type="Process",
            from_stage="outreach",
            to_stage="sales",
            entered_at=entered,
            exited_at=exited,
            duration_ms=345600000.0,
        )

        store.append(record)
        df = store.load("Process")

        assert len(df) == 1
        row = df.row(0, named=True)
        assert row["entity_gid"] == "gid-rt"
        assert row["entity_type"] == "Process"
        assert row["from_stage"] == "outreach"
        assert row["to_stage"] == "sales"
        assert row["transition_type"] == "converted"

    def test_multiple_appends(self, tmp_path) -> None:
        """LO-05: Multiple appends accumulate in the same partition."""
        store = StageTransitionStore(base_dir=tmp_path)
        r1 = _make_record(entity_gid="gid-a", entity_type="Process")
        r2 = _make_record(entity_gid="gid-b", entity_type="Process")

        store.append(r1)
        store.append(r2)
        df = store.load("Process")

        assert len(df) == 2
        gids = df["entity_gid"].to_list()
        assert "gid-a" in gids
        assert "gid-b" in gids

    def test_load_empty_partition(self, tmp_path) -> None:
        """LO-05: Loading a non-existent partition returns empty DataFrame."""
        store = StageTransitionStore(base_dir=tmp_path)
        df = store.load("NonExistent")
        assert len(df) == 0


# ---------------------------------------------------------------------------
# LO-06: StageTransitionEmitter emission
# ---------------------------------------------------------------------------


class TestLO06EmitterEmission:
    """LO-06: StageTransitionEmitter calls store.append on emit."""

    def test_emit_calls_store_append(self) -> None:
        """LO-06: emit() delegates to store.append."""
        mock_store = MagicMock()
        emitter = StageTransitionEmitter(store=mock_store)
        record = _make_record()

        asyncio.run(emitter.emit(record))
        mock_store.append.assert_called_once_with(record)


# ---------------------------------------------------------------------------
# LO-07: Emitter fail-forward
# ---------------------------------------------------------------------------


class TestLO07EmitterFailForward:
    """LO-07: Emitter swallows exceptions (fail-forward contract)."""

    def test_store_exception_swallowed(self) -> None:
        """LO-07: store.append raises -> emit() does NOT propagate."""
        mock_store = MagicMock()
        mock_store.append.side_effect = OSError("disk full")
        emitter = StageTransitionEmitter(store=mock_store)
        record = _make_record()

        # Must not raise
        asyncio.run(emitter.emit(record))
        mock_store.append.assert_called_once()

    def test_store_runtime_error_swallowed(self) -> None:
        """LO-07: RuntimeError from store is also swallowed."""
        mock_store = MagicMock()
        mock_store.append.side_effect = RuntimeError("unexpected failure")
        emitter = StageTransitionEmitter(store=mock_store)
        record = _make_record()

        asyncio.run(emitter.emit(record))
        mock_store.append.assert_called_once()


# ---------------------------------------------------------------------------
# LO-08: stage_transition registered with EntityCategory.OBSERVATION
# ---------------------------------------------------------------------------


class TestLO08EntityRegistryObservation:
    """LO-08: stage_transition descriptor exists in registry with OBSERVATION category."""

    def test_stage_transition_in_registry(self) -> None:
        """LO-08: get_registry() has 'stage_transition' descriptor."""
        from autom8_asana.core.entity_registry import EntityCategory, get_registry

        registry = get_registry()
        desc = registry.get("stage_transition")
        assert desc is not None
        assert desc.name == "stage_transition"

    def test_category_is_observation(self) -> None:
        """LO-08: stage_transition category == EntityCategory.OBSERVATION."""
        from autom8_asana.core.entity_registry import EntityCategory, get_registry

        registry = get_registry()
        desc = registry.get("stage_transition")
        assert desc.category == EntityCategory.OBSERVATION


# ---------------------------------------------------------------------------
# LO-12: 7 lifecycle metrics registered
# ---------------------------------------------------------------------------


class TestLO12LifecycleMetricsRegistered:
    """LO-12: All 7 lifecycle metrics are Metric instances and registered."""

    def test_all_seven_importable(self) -> None:
        """LO-12: All 7 lifecycle metrics can be imported."""
        from autom8_asana.metrics.definitions.lifecycle import (
            ONBOARDING_TO_IMPLEMENTATION_CONVERSION,
            OUTREACH_TO_SALES_CONVERSION,
            SALES_TO_ONBOARDING_CONVERSION,
            STAGE_DURATION_MEDIAN,
            STAGE_DURATION_P95,
            STALLED_ENTITIES,
            WEEKLY_TRANSITIONS,
        )

        all_metrics = [
            OUTREACH_TO_SALES_CONVERSION,
            SALES_TO_ONBOARDING_CONVERSION,
            ONBOARDING_TO_IMPLEMENTATION_CONVERSION,
            STAGE_DURATION_MEDIAN,
            STAGE_DURATION_P95,
            STALLED_ENTITIES,
            WEEKLY_TRANSITIONS,
        ]
        assert len(all_metrics) == 7

    def test_all_are_metric_instances(self) -> None:
        """LO-12: Each import is a Metric instance with correct name."""
        from autom8_asana.metrics.definitions.lifecycle import (
            ONBOARDING_TO_IMPLEMENTATION_CONVERSION,
            OUTREACH_TO_SALES_CONVERSION,
            SALES_TO_ONBOARDING_CONVERSION,
            STAGE_DURATION_MEDIAN,
            STAGE_DURATION_P95,
            STALLED_ENTITIES,
            WEEKLY_TRANSITIONS,
        )
        from autom8_asana.metrics.metric import Metric

        expected_names = {
            "outreach_to_sales_conversion",
            "sales_to_onboarding_conversion",
            "onboarding_to_implementation_conversion",
            "stage_duration_median",
            "stage_duration_p95",
            "stalled_entities",
            "weekly_transitions",
        }

        all_metrics = [
            OUTREACH_TO_SALES_CONVERSION,
            SALES_TO_ONBOARDING_CONVERSION,
            ONBOARDING_TO_IMPLEMENTATION_CONVERSION,
            STAGE_DURATION_MEDIAN,
            STAGE_DURATION_P95,
            STALLED_ENTITIES,
            WEEKLY_TRANSITIONS,
        ]

        for m in all_metrics:
            assert isinstance(m, Metric), f"{m} is not a Metric instance"

        actual_names = {m.name for m in all_metrics}
        assert actual_names == expected_names

    def test_registered_in_metric_registry(self) -> None:
        """LO-12: All 7 metrics are discoverable via MetricRegistry."""
        from autom8_asana.metrics.registry import MetricRegistry

        registry = MetricRegistry()
        available = registry.list_metrics()

        lifecycle_metrics = [
            "outreach_to_sales_conversion",
            "sales_to_onboarding_conversion",
            "onboarding_to_implementation_conversion",
            "stage_duration_median",
            "stage_duration_p95",
            "stalled_entities",
            "weekly_transitions",
        ]
        for name in lifecycle_metrics:
            assert name in available, f"Metric '{name}' not in registry"


# ---------------------------------------------------------------------------
# LO-13: Conversion metrics integration (simplified)
# ---------------------------------------------------------------------------


class TestLO13ConversionMetricExpr:
    """LO-13: Conversion metric expr can be applied to a small polars DataFrame."""

    def test_outreach_to_sales_expr_on_dataframe(self) -> None:
        """LO-13: outreach_to_sales_conversion expr counts matching rows.

        Note: MetricExpr.to_polars_expr() does NOT apply filter_expr (per design:
        filtering happens at the DataFrame level in compute_metric). This test
        applies the filter first, then the agg, matching the real execution path.
        """
        from autom8_asana.metrics.definitions.lifecycle import (
            OUTREACH_TO_SALES_CONVERSION,
        )

        df = pl.DataFrame(
            {
                "entity_gid": ["g1", "g2", "g3"],
                "from_stage": ["outreach", "outreach", "sales"],
                "to_stage": ["sales", "sales", "onboarding"],
                "transition_type": ["converted", "did_not_convert", "converted"],
            }
        )

        expr = OUTREACH_TO_SALES_CONVERSION.expr
        # Apply the filter_expr at DataFrame level first (as compute_metric does)
        assert expr.filter_expr is not None
        filtered_df = df.filter(expr.filter_expr)
        polars_expr = expr.to_polars_expr()
        result = filtered_df.select(polars_expr)

        # Only g1 matches: from_stage=outreach, to_stage=sales, type=converted
        assert result[expr.name][0] == 1


# ---------------------------------------------------------------------------
# LO-14: duration_days computed column
# ---------------------------------------------------------------------------


class TestLO14DurationDaysComputed:
    """LO-14: Store.load() materializes duration_days computed column."""

    def test_duration_days_present_on_load(self, tmp_path) -> None:
        """LO-14: Loaded DataFrame contains duration_days column."""
        store = StageTransitionStore(base_dir=tmp_path)
        entered = datetime(2026, 1, 1, tzinfo=UTC)
        exited = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        record = _make_record(
            entity_gid="gid-dur",
            entity_type="Offer",
            entered_at=entered,
            exited_at=exited,
        )

        store.append(record)
        df = store.load("Offer")

        assert "duration_days" in df.columns
        assert df["duration_days"][0] == pytest.approx(10.0)

    def test_duration_days_none_when_open(self, tmp_path) -> None:
        """LO-14: duration_days is null for open intervals (exited_at=None)."""
        store = StageTransitionStore(base_dir=tmp_path)
        record = _make_record(
            entity_gid="gid-open",
            entity_type="Offer",
            entered_at=datetime(2026, 1, 1, tzinfo=UTC),
            exited_at=None,
        )

        store.append(record)
        df = store.load("Offer")

        assert "duration_days" in df.columns
        assert df["duration_days"][0] is None

    def test_empty_dataframe_has_duration_days(self, tmp_path) -> None:
        """LO-14: Empty DataFrame from load() also includes duration_days."""
        store = StageTransitionStore(base_dir=tmp_path)
        df = store.load("Empty")
        assert "duration_days" in df.columns


# ---------------------------------------------------------------------------
# LO-15: LoopDetector is_self_triggered within window
# ---------------------------------------------------------------------------


class TestLO15LoopDetectorWithinWindow:
    """LO-15: LoopDetector detects self-triggered events within window."""

    def test_recently_written_is_self_triggered(self) -> None:
        """LO-15: record_outbound + immediate is_self_triggered -> True."""
        detector = LoopDetector(window_seconds=30)
        detector.record_outbound("gid-123")
        assert detector.is_self_triggered("gid-123") is True

    def test_unrecorded_gid_is_not_triggered(self) -> None:
        """LO-15: Unrecorded GID is not self-triggered."""
        detector = LoopDetector(window_seconds=30)
        detector.record_outbound("gid-123")
        assert detector.is_self_triggered("gid-other") is False


# ---------------------------------------------------------------------------
# LO-16: LoopDetector expiry
# ---------------------------------------------------------------------------


class TestLO16LoopDetectorExpiry:
    """LO-16: LoopDetector entries expire after window_seconds."""

    def test_zero_second_window_expires_immediately(self) -> None:
        """LO-16: window_seconds=0 -> is_self_triggered returns False after sleep."""
        detector = LoopDetector(window_seconds=0)
        detector.record_outbound("gid-123")
        # Small sleep to ensure monotonic clock advances past 0-second window
        time.sleep(0.01)
        assert detector.is_self_triggered("gid-123") is False

    def test_tracked_count_drops_after_expiry(self) -> None:
        """LO-16: Tracked count drops to 0 after window expires."""
        detector = LoopDetector(window_seconds=0)
        detector.record_outbound("gid-123")
        time.sleep(0.01)
        assert detector.tracked_count == 0


# ---------------------------------------------------------------------------
# LO-17: WebhookDispatcherConfig defaults
# ---------------------------------------------------------------------------


class TestLO17WebhookDispatcherConfigDefaults:
    """LO-17: WebhookDispatcherConfig defaults are maximally conservative."""

    def test_enabled_false_by_default(self) -> None:
        """LO-17: Default enabled is False."""
        config = WebhookDispatcherConfig()
        assert config.enabled is False

    def test_dry_run_true_by_default(self) -> None:
        """LO-17: Default dry_run is True."""
        config = WebhookDispatcherConfig()
        assert config.dry_run is True

    def test_empty_entity_allowlist_by_default(self) -> None:
        """LO-17: Default allowed_entity_types is empty frozenset."""
        config = WebhookDispatcherConfig()
        assert config.allowed_entity_types == frozenset()

    def test_empty_event_allowlist_by_default(self) -> None:
        """LO-17: Default allowed_event_types is empty frozenset."""
        config = WebhookDispatcherConfig()
        assert config.allowed_event_types == frozenset()

    def test_config_is_frozen(self) -> None:
        """LO-17: WebhookDispatcherConfig is frozen (immutable)."""
        config = WebhookDispatcherConfig()
        with pytest.raises(FrozenInstanceError):
            config.enabled = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LO-18: Dry-run mode
# ---------------------------------------------------------------------------


class TestLO18DryRunMode:
    """LO-18: Dry-run mode logs but does not call dispatch_async."""

    def _make_dispatcher(
        self, *, dry_run: bool = True
    ) -> tuple[LifecycleWebhookDispatcher, AsyncMock]:
        config = WebhookDispatcherConfig(
            enabled=True,
            dry_run=dry_run,
            allowed_entity_types=frozenset({"Process"}),
            allowed_event_types=frozenset({"section_changed"}),
        )
        mock_dispatch = AsyncMock()
        mock_dispatch.dispatch_async = AsyncMock(return_value={"success": True})
        loop_detector = LoopDetector(window_seconds=30)

        dispatcher = LifecycleWebhookDispatcher(
            automation_dispatch=mock_dispatch,
            config=config,
            loop_detector=loop_detector,
        )
        return dispatcher, mock_dispatch

    def test_dry_run_does_not_dispatch(self) -> None:
        """LO-18: dry_run=True -> dispatch_async NOT called."""
        dispatcher, mock_dispatch = self._make_dispatcher(dry_run=True)
        result = asyncio.run(
            dispatcher.handle_event("section_changed", "Process", "gid-dry", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "dry_run"
        mock_dispatch.dispatch_async.assert_not_called()

    def test_non_dry_run_does_dispatch(self) -> None:
        """LO-18: dry_run=False -> dispatch_async IS called."""
        dispatcher, mock_dispatch = self._make_dispatcher(dry_run=False)
        result = asyncio.run(
            dispatcher.handle_event("section_changed", "Process", "gid-live", {})
        )
        assert result["dispatched"] is True
        assert result["reason"] == "live"
        mock_dispatch.dispatch_async.assert_called_once()


# ---------------------------------------------------------------------------
# LO-19: Entity type not in allowlist
# ---------------------------------------------------------------------------


class TestLO19EntityTypeNotInAllowlist:
    """LO-19: Dispatch skipped when entity_type not in allowed_entity_types."""

    def test_offer_not_in_business_only_allowlist(self) -> None:
        """LO-19: allowed_entity_types={'Business'} -> Offer dispatch skipped."""
        config = WebhookDispatcherConfig(
            enabled=True,
            dry_run=False,
            allowed_entity_types=frozenset({"Business"}),
            allowed_event_types=frozenset({"section_changed"}),
        )
        mock_dispatch = AsyncMock()
        mock_dispatch.dispatch_async = AsyncMock(return_value={"success": True})
        loop_detector = LoopDetector(window_seconds=30)

        dispatcher = LifecycleWebhookDispatcher(
            automation_dispatch=mock_dispatch,
            config=config,
            loop_detector=loop_detector,
        )

        result = asyncio.run(
            dispatcher.handle_event("section_changed", "Offer", "gid-offer", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "entity_type_not_allowed"
        mock_dispatch.dispatch_async.assert_not_called()

    def test_matching_entity_type_allowed(self) -> None:
        """LO-19: Matching entity type passes the allowlist check."""
        config = WebhookDispatcherConfig(
            enabled=True,
            dry_run=False,
            allowed_entity_types=frozenset({"Business"}),
            allowed_event_types=frozenset({"section_changed"}),
        )
        mock_dispatch = AsyncMock()
        mock_dispatch.dispatch_async = AsyncMock(return_value={"success": True})
        loop_detector = LoopDetector(window_seconds=30)

        dispatcher = LifecycleWebhookDispatcher(
            automation_dispatch=mock_dispatch,
            config=config,
            loop_detector=loop_detector,
        )

        result = asyncio.run(
            dispatcher.handle_event("section_changed", "Business", "gid-biz", {})
        )
        assert result["dispatched"] is True
        mock_dispatch.dispatch_async.assert_called_once()


# ---------------------------------------------------------------------------
# LO-20: Composite scenario (emit -> store -> verify)
# ---------------------------------------------------------------------------


class TestLO20CompositeScenario:
    """LO-20: Full observation pipeline: create record -> emit -> verify stored."""

    def test_end_to_end_pipeline(self, tmp_path) -> None:
        """LO-20: Real store + real emitter round-trip."""
        store = StageTransitionStore(base_dir=tmp_path)
        emitter = StageTransitionEmitter(store=store)

        entered = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
        exited = datetime(2026, 3, 8, 10, 0, 0, tzinfo=UTC)

        record = _make_record(
            entity_gid="gid-e2e",
            entity_type="Business",
            business_gid="biz-e2e",
            from_stage="outreach",
            to_stage="sales",
            pipeline_stage_num=2,
            transition_type="converted",
            entered_at=entered,
            exited_at=exited,
            automation_result_id="rule_e2e",
            duration_ms=604800000.0,
        )

        # emit uses asyncio.to_thread -> runs store.append in thread
        asyncio.run(emitter.emit(record))

        # verify stored
        df = store.load("Business")
        assert len(df) == 1
        row = df.row(0, named=True)
        assert row["entity_gid"] == "gid-e2e"
        assert row["from_stage"] == "outreach"
        assert row["to_stage"] == "sales"
        assert row["transition_type"] == "converted"
        assert row["business_gid"] == "biz-e2e"
        assert row["automation_result_id"] == "rule_e2e"
        assert "duration_days" in df.columns
        assert row["duration_days"] == pytest.approx(7.0)

    def test_multiple_entity_types_partitioned(self, tmp_path) -> None:
        """LO-20: Records for different entity types go to separate partitions."""
        store = StageTransitionStore(base_dir=tmp_path)
        emitter = StageTransitionEmitter(store=store)

        r_process = _make_record(entity_gid="gid-p", entity_type="Process")
        r_offer = _make_record(entity_gid="gid-o", entity_type="Offer")

        asyncio.run(emitter.emit(r_process))
        asyncio.run(emitter.emit(r_offer))

        df_process = store.load("Process")
        df_offer = store.load("Offer")

        assert len(df_process) == 1
        assert df_process["entity_gid"][0] == "gid-p"
        assert len(df_offer) == 1
        assert df_offer["entity_gid"][0] == "gid-o"
