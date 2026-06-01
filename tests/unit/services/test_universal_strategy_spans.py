"""Span tests for strategy.resolution.resolve and strategy.resolution.resolve_group.

Sprint 5, G-04 and G-05.

Test coverage:
- T-G04 (happy path): strategy.resolution.resolve emits span with entity_type,
  criteria_count, project_gid, resolved_count, group_count, null_slot_count=0
- T-G04 (null-slot path): null_slot_count=1, resolution.null_slot event on span,
  StatusCode.UNSET (null slot is diagnostic, not a hard failure)
- T-G05 (parent-child): resolve_group span is a child of the resolve span
- T-G05 (index build failure): resolve_group sets INDEX_UNAVAILABLE, StatusCode.ERROR
- T-G05 (lookup failure): resolve_group adds resolution.lookup_failed event per failure,
  lookup_error_count=1, StatusCode.UNSET
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from autom8_asana.services.dynamic_index import DynamicIndex, DynamicIndexCache
from autom8_asana.services.universal_strategy import UniversalResolutionStrategy

# ---------------------------------------------------------------------------
# OTel fixture: patches the module-level _tracer in universal_strategy.py
# ---------------------------------------------------------------------------


@pytest.fixture()
def otel_provider():
    """Fresh TracerProvider per test for span isolation.

    Patches autom8_asana.services.universal_strategy._tracer so the module-level
    singleton is bound to this test's provider, not the one active at import time.
    """
    import autom8_asana.services.universal_strategy as _strategy_module

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # Do NOT call trace.set_tracer_provider(provider) here: OTel's API
    # documents this as a once-only operation ("This can only be done once, a
    # warning will be logged if any further attempt is made"). Multiple test
    # fixtures calling it race-fail silently, leaving later tests bound to the
    # first fixture's provider and producing empty exporters. Patching the
    # module-local _tracer below is sufficient: spans emitted via that tracer
    # are processed by THIS provider's SpanProcessor (the local exporter).

    fresh_tracer = provider.get_tracer("autom8_asana.services.universal_strategy")
    original_tracer = _strategy_module._tracer
    _strategy_module._tracer = fresh_tracer

    yield provider, exporter

    _strategy_module._tracer = original_tracer
    exporter.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_strategy(entity_type: str = "unit") -> UniversalResolutionStrategy:
    """Create a strategy with a fresh index cache."""
    return UniversalResolutionStrategy(
        entity_type=entity_type,
        index_cache=DynamicIndexCache(max_per_entity=5, ttl_seconds=3600),
    )


def _make_mock_client() -> MagicMock:
    """Create a minimal mock AsanaClient."""
    client = MagicMock()
    client.unified_store = MagicMock()
    return client


def _make_valid_validation(normalized: dict) -> MagicMock:
    """Return a mock CriterionValidation representing a valid criterion."""
    v = MagicMock()
    v.is_valid = True
    v.normalized_criterion = normalized
    v.errors = []
    return v


def _make_unit_df() -> pl.DataFrame:
    """Minimal unit DataFrame for index building."""
    return pl.DataFrame(
        {
            "gid": ["unit-1", "unit-2"],
            "office_phone": ["+11234567890", "+19876543210"],
            "vertical": ["dental", "medical"],
        }
    )


# ---------------------------------------------------------------------------
# T-G04: strategy.resolution.resolve
# ---------------------------------------------------------------------------


class TestStrategyResolveSpan:
    """T-G04: strategy.resolution.resolve span."""

    async def test_happy_path_attributes(self, otel_provider):
        """Resolve emits span with entity_type, criteria_count, resolved/group counts."""
        _, exporter = otel_provider

        strategy = _make_strategy("unit")
        df = _make_unit_df()

        # One resolved result via a real DynamicIndex lookup
        index = DynamicIndex.from_dataframe(df, key_columns=["office_phone", "vertical"])

        mock_validation = _make_valid_validation(
            {"office_phone": "+11234567890", "vertical": "dental"}
        )

        # Mock _get_or_build_index to return the pre-built index
        # Mock _get_dataframe to return None (no classifier = simple path)
        with (
            patch(
                "autom8_asana.services.resolver.validate_criterion_for_entity",
                return_value=mock_validation,
            ),
            patch.object(strategy, "_get_or_build_index", AsyncMock(return_value=index)),
            patch.object(strategy, "_get_dataframe", AsyncMock(return_value=None)),
        ):
            results = await strategy.resolve(
                criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
                project_gid="proj-123",
                client=_make_mock_client(),
            )

        assert len(results) == 1

        spans = exporter.get_finished_spans()
        resolve_spans = [s for s in spans if s.name == "strategy.resolution.resolve"]
        assert len(resolve_spans) == 1, (
            f"Expected 1 'strategy.resolution.resolve' span, got {[s.name for s in spans]}"
        )

        span = resolve_spans[0]
        attrs = dict(span.attributes)

        assert attrs["strategy.entity_type"] == "unit"
        assert attrs["strategy.criteria_count"] == 1
        assert attrs["strategy.project_gid"] == "proj-123"
        assert isinstance(attrs["strategy.resolved_count"], int)
        assert isinstance(attrs["strategy.group_count"], int)
        assert attrs["strategy.null_slot_count"] == 0
        assert span.status.status_code == StatusCode.UNSET

    async def test_null_slot_increments_count_and_adds_event(self, otel_provider):
        """Null slot sets null_slot_count=1, adds resolution.null_slot event, UNSET status."""
        _, exporter = otel_provider

        strategy = _make_strategy("unit")

        mock_validation = _make_valid_validation({"office_phone": "+15551234567"})

        # Patch _resolve_group to a no-op so the slot stays None (null-slot
        # path). Robust target: the strategy's own method, not the xdist-fragile
        # function-local-imported gather_with_limit. The real gather still runs.
        with (
            patch(
                "autom8_asana.services.resolver.validate_criterion_for_entity",
                return_value=mock_validation,
            ),
            patch.object(strategy, "_resolve_group", AsyncMock()),
        ):
            results = await strategy.resolve(
                criteria=[{"office_phone": "+15551234567"}],
                project_gid="proj-456",
                client=_make_mock_client(),
            )

        assert len(results) == 1
        assert results[0].error == "RESOLUTION_NULL_SLOT"

        spans = exporter.get_finished_spans()
        resolve_spans = [s for s in spans if s.name == "strategy.resolution.resolve"]
        assert len(resolve_spans) == 1

        span = resolve_spans[0]
        attrs = dict(span.attributes)

        assert attrs["strategy.null_slot_count"] == 1
        assert span.status.status_code == StatusCode.UNSET  # diagnostic, not a hard fail

        null_slot_events = [e for e in span.events if e.name == "resolution.null_slot"]
        assert len(null_slot_events) == 1

        event_attrs = dict(null_slot_events[0].attributes)
        assert event_attrs["strategy.criterion_index"] == 0
        assert event_attrs["strategy.entity_type"] == "unit"


# ---------------------------------------------------------------------------
# T-G05: strategy.resolution.resolve_group
# ---------------------------------------------------------------------------


class TestStrategyResolveGroupSpan:
    """T-G05: strategy.resolution.resolve_group span."""

    @pytest.mark.worker_isolated
    async def test_parent_child_relationship(self, otel_provider):
        """resolve_group span is a child of the resolve span."""
        _, exporter = otel_provider

        strategy = _make_strategy("unit")
        df = _make_unit_df()
        index = DynamicIndex.from_dataframe(df, key_columns=["office_phone"])
        mock_validation = _make_valid_validation({"office_phone": "+11234567890"})

        with (
            patch(
                "autom8_asana.services.resolver.validate_criterion_for_entity",
                return_value=mock_validation,
            ),
            patch.object(strategy, "_get_or_build_index", AsyncMock(return_value=index)),
            patch.object(strategy, "_get_dataframe", AsyncMock(return_value=None)),
        ):
            await strategy.resolve(
                criteria=[{"office_phone": "+11234567890"}],
                project_gid="proj-789",
                client=_make_mock_client(),
            )

        spans = exporter.get_finished_spans()
        resolve_span = next((s for s in spans if s.name == "strategy.resolution.resolve"), None)
        group_span = next(
            (s for s in spans if s.name == "strategy.resolution.resolve_group"),
            None,
        )

        assert resolve_span is not None
        assert group_span is not None
        assert group_span.parent is not None
        assert group_span.parent.span_id == resolve_span.get_span_context().span_id

    # xdist-fragile: the error-path resolve_group span is intermittently not
    # recorded under -n auto on the CI runner (assert 0 == 1). Run single-process
    # via the non-blocking isolated job until the root async-span fix lands.
    # See .know/defer-watch.yaml ob-universal-strategy-span-xdist.
    @pytest.mark.worker_isolated
    async def test_index_build_failure_sets_error_attributes(self, otel_provider):
        """INDEX_UNAVAILABLE path sets error_code, error.type, StatusCode.ERROR."""
        _, exporter = otel_provider

        strategy = _make_strategy("unit")
        mock_validation = _make_valid_validation({"office_phone": "+15559999999"})

        with (
            patch(
                "autom8_asana.services.resolver.validate_criterion_for_entity",
                return_value=mock_validation,
            ),
            patch.object(
                strategy,
                "_get_or_build_index",
                AsyncMock(side_effect=RuntimeError("index build failed")),
            ),
        ):
            results = await strategy.resolve(
                criteria=[{"office_phone": "+15559999999"}],
                project_gid="proj-err",
                client=_make_mock_client(),
            )

        assert len(results) == 1
        assert results[0].error == "INDEX_UNAVAILABLE"

        spans = exporter.get_finished_spans()
        group_spans = [s for s in spans if s.name == "strategy.resolution.resolve_group"]
        assert len(group_spans) == 1

        span = group_spans[0]
        attrs = dict(span.attributes)

        assert attrs["strategy.entity_type"] == "unit"
        assert isinstance(attrs["strategy.key_columns"], str)
        assert len(attrs["strategy.key_columns"]) > 0
        assert isinstance(attrs["strategy.group_criteria_count"], int)
        assert attrs["strategy.error_code"] == "INDEX_UNAVAILABLE"
        assert attrs["error.type"] == "RuntimeError"
        assert span.status.status_code == StatusCode.ERROR

        exception_events = [e for e in span.events if e.name == "exception"]
        assert len(exception_events) == 1

    # xdist-fragile (same class as test_index_build_failure above): run
    # single-process via the isolated job. See .know/defer-watch.yaml.
    @pytest.mark.worker_isolated
    async def test_lookup_failure_adds_event_and_partial_success(self, otel_provider):
        """Per-criterion lookup failure adds event, lookup_error_count=1, UNSET status."""
        _, exporter = otel_provider

        strategy = _make_strategy("unit")

        # Build an index that has one key; the second lookup will fail
        df = pl.DataFrame(
            {
                "gid": ["unit-1"],
                "office_phone": ["+11111111111"],
            }
        )
        index = DynamicIndex.from_dataframe(df, key_columns=["office_phone"])

        mock_validation_good = _make_valid_validation({"office_phone": "+11111111111"})
        mock_validation_bad = _make_valid_validation({"office_phone": "+19999999999"})

        # Use side_effect to return different validations per call
        call_count = {"n": 0}

        def validation_side_effect(*_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_validation_good
            return mock_validation_bad

        # Patch index.lookup so the second criterion raises KeyError
        original_lookup = index.lookup

        call_count_lookup = {"n": 0}

        def patched_lookup(criterion: dict) -> list:
            call_count_lookup["n"] += 1
            if call_count_lookup["n"] == 2:
                raise KeyError("not found")
            return original_lookup(criterion)

        index.lookup = patched_lookup  # type: ignore[method-assign]

        with (
            patch(
                "autom8_asana.services.resolver.validate_criterion_for_entity",
                side_effect=validation_side_effect,
            ),
            patch.object(strategy, "_get_or_build_index", AsyncMock(return_value=index)),
            patch.object(strategy, "_get_dataframe", AsyncMock(return_value=None)),
        ):
            results = await strategy.resolve(
                criteria=[
                    {"office_phone": "+11111111111"},
                    {"office_phone": "+19999999999"},
                ],
                project_gid="proj-lookup",
                client=_make_mock_client(),
            )

        assert len(results) == 2
        # Second criterion gets LOOKUP_ERROR
        assert results[1].error == "LOOKUP_ERROR"

        spans = exporter.get_finished_spans()
        group_spans = [s for s in spans if s.name == "strategy.resolution.resolve_group"]
        assert len(group_spans) == 1

        span = group_spans[0]
        attrs = dict(span.attributes)

        assert attrs["strategy.lookup_error_count"] == 1
        assert span.status.status_code == StatusCode.UNSET  # partial failure

        lookup_failed_events = [e for e in span.events if e.name == "resolution.lookup_failed"]
        assert len(lookup_failed_events) == 1

        event_attrs = dict(lookup_failed_events[0].attributes)
        assert isinstance(event_attrs["strategy.criterion_index"], int)
        assert event_attrs["error.type"] == "KeyError"
