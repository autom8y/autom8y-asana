"""Prometheus metric tests for the ``/exports`` route (OBS-EXPORTS-001).

SRE OB2 sprint, Phase-2 emission. Verifies that the exports metrics are
registered on the default prometheus_client REGISTRY and that ``export_handler``
emits each metric from the OB2 span locals at the contracted emission points.

Metrics under test (per the approved contract):
- autom8y_asana_exports_request_duration_seconds (Histogram; entity_type, format)
- autom8y_asana_exports_predicate_split_outcome_total (Counter;
  entity_type, date_filter_applied, section_default_applied)
- autom8y_asana_exports_identity_rows_suppressed_total (Counter; entity_type)
- autom8y_asana_exports_rows (Histogram; entity_type, stage)

Dropped per contract (in_scope=false; asserted ABSENT from the registry):
- autom8y_asana_exports_format_negotiation_fallback_total — no format-fallback
  seam exists (served_format always equals requested_format).

The handler-driving fixtures mirror tests/unit/api/test_exports_spans.py
(mock strategy / entity service / patched PredicateCompiler.compile). Metric
values are read via the same before/after-delta pattern established in
tests/unit/api/test_receiver_bulk_fanout_reliability_stage1.py
(``Counter.labels(...)._value.get()``); histogram ``_count`` / ``_sum`` are read
via ``Histogram.collect()`` samples.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from prometheus_client import REGISTRY

from autom8_asana.api.routes.exports import ExportRequest, export_handler
from autom8_asana.query.compiler import PredicateCompiler

# Sections the ACTIVE-default predicate injects (mirrors test_exports_spans.py).
_ACTIVE_SECTIONS = ["ACTIVE", "BUILDING", "EXECUTING", "PROCESSING", "OPPORTUNITY", "CONTACTED"]


# ---------------------------------------------------------------------------
# Handler-driving helpers (mirror test_exports_spans.py)
# ---------------------------------------------------------------------------


def _make_mock_entity_service(entity_type: str = "process") -> MagicMock:
    svc = MagicMock()
    ctx = MagicMock()
    ctx.entity_type = entity_type
    ctx.project_gid = "1201265144487549"
    svc.validate_entity_type.return_value = ctx
    return svc


def _passthrough_compile(self: Any, node: Any, schema: Any) -> pl.Expr:
    """Patched PredicateCompiler.compile → a section IN filter (no engine call)."""
    return pl.col("section").is_in(_ACTIVE_SECTIONS)


async def _run_handler(req: ExportRequest, fake_df: pl.DataFrame) -> Any:
    """Drive export_handler against a mocked strategy + patched compiler."""
    mock_strategy = MagicMock()
    mock_strategy._get_dataframe = AsyncMock(return_value=fake_df)
    svc = _make_mock_entity_service(req.entity_type)

    with (
        patch(
            "autom8_asana.services.universal_strategy.get_universal_strategy",
            return_value=mock_strategy,
        ),
        patch.object(PredicateCompiler, "compile", _passthrough_compile),
    ):
        return await export_handler(
            request_body=req,
            request_id="abcdef0123456789",
            auth=object(),
            entity_service=svc,
            client=object(),
        )


def _base_df() -> pl.DataFrame:
    """4-row fixture: one null-key row (g3) + one duplicate dedupe key (g4≡g1)."""
    return pl.DataFrame(
        {
            "gid": ["g1", "g2", "g3", "g4"],
            "name": ["acct1", "acct2", "acct3", "acct4"],
            "section": ["ACTIVE", "EXECUTING", "ACTIVE", "ACTIVE"],
            "office_phone": ["555-1", "555-2", None, "555-1"],
            "vertical": ["saas", "retail", "ent", "saas"],
            "pipeline_type": ["reactivation", "outreach", "outreach", "reactivation"],
            "modified_at": ["2026-04-01", "2026-04-15", "2026-04-20", "2026-04-10"],
        }
    )


def _date_df() -> pl.DataFrame:
    """Base fixture with a real ``due_on`` date column for the date-filter path."""
    return _base_df().with_columns(
        due_on=pl.Series(["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04"]).str.to_date()
    )


# ---------------------------------------------------------------------------
# Metric-value read helpers (mirror Stage-1 ._value.get() + histogram collect)
# ---------------------------------------------------------------------------


def _counter_value(name: str, labels: dict[str, str]) -> float:
    """Read a counter sample value off the default REGISTRY (0.0 if absent)."""
    val = REGISTRY.get_sample_value(name, labels)
    return float(val) if val is not None else 0.0


def _hist_count(name: str, labels: dict[str, str]) -> float:
    """Read a histogram ``_count`` sample off the default REGISTRY (0.0 if absent)."""
    val = REGISTRY.get_sample_value(f"{name}_count", labels)
    return float(val) if val is not None else 0.0


def _hist_sum(name: str, labels: dict[str, str]) -> float:
    """Read a histogram ``_sum`` sample off the default REGISTRY (0.0 if absent)."""
    val = REGISTRY.get_sample_value(f"{name}_sum", labels)
    return float(val) if val is not None else 0.0


# ---------------------------------------------------------------------------
# Registration: all in-scope metrics present; dropped metric absent
# ---------------------------------------------------------------------------


class TestExportsMetricsRegistration:
    """The four in-scope metrics are registered; the dropped one is NOT."""

    @pytest.mark.parametrize(
        "metric_name",
        [
            "autom8y_asana_exports_request_duration_seconds",
            "autom8y_asana_exports_predicate_split_outcome_total",
            "autom8y_asana_exports_identity_rows_suppressed_total",
            "autom8y_asana_exports_rows",
        ],
    )
    def test_in_scope_metric_registered(self, metric_name: str) -> None:
        # Histograms register the base name; Counters register the *_total name
        # as a sample family. Probe both the registered names and the create()
        # base by importing the metric objects (the import-side-effect registers
        # them on the default REGISTRY at module load).
        import autom8_asana.api.metrics as _m  # noqa: F401  (forces registration)

        names = {mf.name for mf in REGISTRY.collect()}
        # prometheus_client strips the _total suffix from Counter family names
        # and the _seconds/base name is the histogram family name.
        base = metric_name.removesuffix("_total")
        assert base in names or metric_name in names, (
            f"{metric_name!r} (family {base!r}) not registered; "
            f"present sample families include exports_*: "
            f"{sorted(n for n in names if 'exports' in n)}"
        )

    def test_dropped_format_fallback_metric_absent(self) -> None:
        """The format-negotiation-fallback metric was dropped (no real seam)."""
        import autom8_asana.api.metrics as _m  # noqa: F401

        names = {mf.name for mf in REGISTRY.collect()}
        assert "autom8y_asana_exports_format_negotiation_fallback" not in names
        assert "autom8y_asana_exports_format_negotiation_fallback_total" not in names


# ---------------------------------------------------------------------------
# Emission: request duration histogram
# ---------------------------------------------------------------------------


class TestExportsRequestDurationMetric:
    @pytest.mark.asyncio
    async def test_duration_observed_once_with_entity_and_format_labels(self) -> None:
        name = "autom8y_asana_exports_request_duration_seconds"
        labels = {"entity_type": "process", "format": "json"}
        before = _hist_count(name, labels)

        await _run_handler(
            ExportRequest(entity_type="process", project_gids=[1201265144487549], format="json"),
            _base_df(),
        )

        after = _hist_count(name, labels)
        assert after == before + 1
        # A positive (non-negative) duration was summed in.
        assert _hist_sum(name, labels) >= 0.0

    @pytest.mark.asyncio
    async def test_duration_format_label_tracks_request_format(self) -> None:
        name = "autom8y_asana_exports_request_duration_seconds"
        csv_labels = {"entity_type": "process", "format": "csv"}
        before = _hist_count(name, csv_labels)

        await _run_handler(
            ExportRequest(entity_type="process", project_gids=[1201265144487549], format="csv"),
            _base_df(),
        )

        assert _hist_count(name, csv_labels) == before + 1


# ---------------------------------------------------------------------------
# Emission: predicate-split outcome counter
# ---------------------------------------------------------------------------


class TestExportsPredicateSplitMetric:
    @pytest.mark.asyncio
    async def test_section_default_true_date_filter_false(self) -> None:
        # Caller omits section → ACTIVE-default fires; no date op → no date filter.
        name = "autom8y_asana_exports_predicate_split_outcome_total"
        labels = {
            "entity_type": "process",
            "date_filter_applied": "false",
            "section_default_applied": "true",
        }
        before = _counter_value(name, labels)

        await _run_handler(
            ExportRequest(entity_type="process", project_gids=[1201265144487549]),
            _base_df(),
        )

        assert _counter_value(name, labels) == before + 1

    @pytest.mark.asyncio
    async def test_section_default_false_when_section_supplied(self) -> None:
        name = "autom8y_asana_exports_predicate_split_outcome_total"
        labels = {
            "entity_type": "process",
            "date_filter_applied": "false",
            "section_default_applied": "false",
        }
        before = _counter_value(name, labels)

        await _run_handler(
            ExportRequest(
                entity_type="process",
                project_gids=[1201265144487549],
                predicate={  # type: ignore[arg-type]
                    "field": "section",
                    "op": "in",
                    "value": ["ACTIVE"],
                },
            ),
            _base_df(),
        )

        assert _counter_value(name, labels) == before + 1

    @pytest.mark.asyncio
    async def test_date_filter_applied_true_label(self) -> None:
        # A date-op predicate with no explicit section → date_filter fires AND the
        # ACTIVE-default section is still injected (caller omitted a section), so
        # section_default_applied is true here.
        name = "autom8y_asana_exports_predicate_split_outcome_total"
        labels = {
            "entity_type": "process",
            "date_filter_applied": "true",
            "section_default_applied": "true",
        }
        before = _counter_value(name, labels)

        await _run_handler(
            ExportRequest(
                entity_type="process",
                project_gids=[1201265144487549],
                predicate={  # type: ignore[arg-type]
                    "field": "due_on",
                    "op": "date_gte",
                    "value": "2026-01-01",
                },
            ),
            _date_df(),
        )

        assert _counter_value(name, labels) == before + 1


# ---------------------------------------------------------------------------
# Emission: identity-rows-suppressed counter
# ---------------------------------------------------------------------------


class TestExportsIdentityRowsSuppressedMetric:
    @pytest.mark.asyncio
    async def test_suppressed_count_incremented_by_delta(self) -> None:
        # include=False + one null-key row (g3) → 1 row suppressed.
        name = "autom8y_asana_exports_identity_rows_suppressed_total"
        labels = {"entity_type": "process"}
        before = _counter_value(name, labels)

        await _run_handler(
            ExportRequest(
                entity_type="process",
                project_gids=[1201265144487549],
                options={"include_incomplete_identity": False},  # type: ignore[arg-type]
            ),
            _base_df(),
        )

        assert _counter_value(name, labels) == before + 1

    @pytest.mark.asyncio
    async def test_no_increment_when_include_true(self) -> None:
        # Default include=True → 0 rows suppressed → inc(0) leaves value unchanged.
        name = "autom8y_asana_exports_identity_rows_suppressed_total"
        labels = {"entity_type": "process"}
        before = _counter_value(name, labels)

        await _run_handler(
            ExportRequest(entity_type="process", project_gids=[1201265144487549]),
            _base_df(),
        )

        assert _counter_value(name, labels) == before


# ---------------------------------------------------------------------------
# Emission: pre/post-dedup rows histogram
# ---------------------------------------------------------------------------


class TestExportsRowsMetric:
    @pytest.mark.asyncio
    async def test_pre_and_post_dedup_stages_each_observed_once(self) -> None:
        name = "autom8y_asana_exports_rows"
        pre_labels = {"entity_type": "process", "stage": "pre_dedup"}
        post_labels = {"entity_type": "process", "stage": "post_dedup"}
        pre_before = _hist_count(name, pre_labels)
        post_before = _hist_count(name, post_labels)

        await _run_handler(
            ExportRequest(
                entity_type="process",
                project_gids=[1201265144487549],
                options={"include_incomplete_identity": False},  # type: ignore[arg-type]
            ),
            _base_df(),
        )

        assert _hist_count(name, pre_labels) == pre_before + 1
        assert _hist_count(name, post_labels) == post_before + 1

    @pytest.mark.asyncio
    async def test_pre_dedup_sum_reflects_observed_rowcount(self) -> None:
        # include=False suppresses g3 (null key) → 3 rows enter dedupe (pre),
        # g4≡g1 dedupes → 2 rows post. Sum-delta on the pre stage == 3.
        name = "autom8y_asana_exports_rows"
        pre_labels = {"entity_type": "process", "stage": "pre_dedup"}
        post_labels = {"entity_type": "process", "stage": "post_dedup"}
        pre_sum_before = _hist_sum(name, pre_labels)
        post_sum_before = _hist_sum(name, post_labels)

        await _run_handler(
            ExportRequest(
                entity_type="process",
                project_gids=[1201265144487549],
                options={"include_incomplete_identity": False},  # type: ignore[arg-type]
            ),
            _base_df(),
        )

        assert _hist_sum(name, pre_labels) == pre_sum_before + 3
        assert _hist_sum(name, post_labels) == post_sum_before + 2
