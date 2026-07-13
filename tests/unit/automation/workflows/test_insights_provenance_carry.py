"""Guard-PRESENCE tests for the provenance-carry render wiring (Sprint 1).

provenance-to-the-human Sprint 1 (render-wiring), the SPINE build-half's own
suite. These assert the wiring EXISTS and the guards are WIRED on the real path:
the client carries the META, the workflow threads it into state, the C2 guard
routes a weighted-but-provenance-absent table to the typed-refusal rail, and the
render surfaces the weights_version + asOf badge AT THE POINT OF ACTION.

CRITIC-NEVER-AUTHOR (the load-bearing boundary): this file is authored by the
integrity-guard-author (the guard's BUILDER). It proves the guard is PRESENT and
FIRES on the real code path -- it does NOT author the two-sided
stripped-RED/disclosed-GREEN discriminating teeth that grade whether the guard
BITES ONLY on the defect. That proof-obligation (PO-CARRY-1..4) belongs to the
rite-disjoint numerical-adversary at ``verify`` (contract §6/§9.3), who authors
the golden + deliberately-broken day-one fixtures at the consumed render surface.
Building the guard AND grading whether it bites in one soul is the FORBIDDEN
merge (self-attestation). These tests name the fire-seams; they do not arm the
adversary's fixture.

The named fire-seams handed to the adversary:
  - C2 never-hidden: ``InsightsExportWorkflow._fetch_table`` -- a table whose
    served rows carry a WEIGHTED-consumer column (``_rows_are_weighted``) AND whose
    carried ``weights_version`` is None returns ``TableResult(success=False,
    error_type="WeightsProvenanceAbsent")`` BEFORE the success TableResult is built.
  - G1 cardinality: ``operator._merge_batch_metas`` /
    ``distribute_per_office_meta`` -- a batch carrying >1 distinct
    ``weights_version`` raises ``OperatorBatchVersionSkewError`` before a single
    token is chosen.
  - Badge render: ``formatter._provenance_line_html`` / ``_section_disclosure_html``
    -- a DataSection carrying ``weights_version`` renders a ``section-provenance``
    line with the id + asOf; ``synced_at`` stamps the ``section-subtitle`` asOf.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from autom8_asana.automation.workflows.insights.formatter import (
    DataSection,
    HtmlRenderer,
    TableResult,
    _provenance_line_html,
    _section_disclosure_html,
    compose_report,
)
from autom8_asana.automation.workflows.insights.tables import TABLE_SPECS
from autom8_asana.automation.workflows.insights.workflow import _rows_are_weighted
from autom8_asana.clients.data._endpoints.operator import (
    WEIGHTED_CONSUMER_METRICS,
    OperatorBatchMeta,
    _merge_batch_metas,
    distribute_per_office_meta,
)
from autom8_asana.errors import OperatorBatchVersionSkewError

from .test_insights_denied_render_teeth import _run_and_capture_html
from .test_insights_export import (
    _default_params,
    _default_scope,
    _force_fallback,  # noqa: F401  -- module-scoped fixture, imported for usefixtures
    _make_task,
    _make_workflow,
)

# The canonical current version-id (byte-identical to the data plane's
# CURRENT_WEIGHT_SCHEME_VERSION on origin/main). The id ITSELF discloses UNRATIFIED.
_CURRENT_VERSION = "2026-03-24-static-UNRATIFIED"
_FIXTURE_ASOF = "2026-07-13T00:00:00Z"

# The section the operator batch's account_level_stats renders into (SUMMARY is the
# weighted section carrying the solid_scheds-family columns).
_SUMMARY = "SUMMARY"

pytestmark = pytest.mark.usefixtures("_force_fallback")


# =====================================================================
# 1. Client seam (H5): the META extractor carries provenance, typed
# =====================================================================


class TestClientMetaCarry:
    """distribute_per_office_meta extracts the RESPONSE/META-grain provenance."""

    @staticmethod
    def _envelope(
        per_office: dict[str, list[dict[str, Any]]],
        *,
        weights_version: str | None,
        synced_at: str | None,
    ) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        if weights_version is not None:
            meta["weights_version"] = weights_version
        if synced_at is not None:
            meta["data_freshness"] = {"synced_at": synced_at}
        results = [
            {
                "phone": phone,
                "status": "success",
                "data": {"result_type": "result", "data": rows, "meta": meta},
            }
            for phone, rows in per_office.items()
        ]
        return {"data": {"insight": "account_level_stats", "results": results}}

    def test_meta_extracted_from_per_phone_meta_block(self) -> None:
        body = self._envelope(
            {"+1": [{"nsr_ncr": 0.1}], "+2": [{"nsr_ncr": 0.2}]},
            weights_version=_CURRENT_VERSION,
            synced_at=_FIXTURE_ASOF,
        )
        meta = distribute_per_office_meta(body)
        assert meta.weights_version == _CURRENT_VERSION
        assert meta.synced_at == _FIXTURE_ASOF

    def test_absent_provenance_yields_declared_none_not_throw(self) -> None:
        # A meta-less (unweighted / legacy) batch: declared absence, NOT a throw.
        body = self._envelope({"+1": [{"spend": 100}]}, weights_version=None, synced_at=None)
        meta = distribute_per_office_meta(body)
        assert meta.weights_version is None
        assert meta.synced_at is None

    def test_empty_body_yields_empty_meta(self) -> None:
        meta = distribute_per_office_meta({})
        assert meta == OperatorBatchMeta()

    def test_version_skew_across_offices_raises_typed_g1(self) -> None:
        # FIRE-SEAM (G1): two offices in one batch disagree on the id -> typed raise
        # BEFORE a single token is chosen. (Presence of the guard; the adversary
        # owns the two-sided proof it bites only on skew.)
        body = self._envelope(
            {"+1": [{"nsr_ncr": 0.1}]},
            weights_version="A",
            synced_at=None,
        )
        body["data"]["results"].append(
            {
                "phone": "+2",
                "status": "success",
                "data": {"result_type": "result", "data": [], "meta": {"weights_version": "B"}},
            }
        )
        with pytest.raises(OperatorBatchVersionSkewError) as exc:
            distribute_per_office_meta(body)
        assert sorted(exc.value.versions) == ["A", "B"]

    def test_merge_cross_subbatch_skew_raises_typed_g1(self) -> None:
        # The same G1 invariant at the run level (across chunked/bisected sub-batches).
        metas = [
            OperatorBatchMeta(weights_version="A"),
            OperatorBatchMeta(weights_version="B"),
        ]
        with pytest.raises(OperatorBatchVersionSkewError):
            _merge_batch_metas(metas)

    def test_merge_agreeing_subbatches_collapses_to_one(self) -> None:
        metas = [
            OperatorBatchMeta(weights_version=_CURRENT_VERSION, synced_at=None),
            OperatorBatchMeta(weights_version=_CURRENT_VERSION, synced_at=_FIXTURE_ASOF),
        ]
        merged = _merge_batch_metas(metas)
        assert merged.weights_version == _CURRENT_VERSION
        assert merged.synced_at == _FIXTURE_ASOF


# =====================================================================
# 2. Workflow state: the meta is threaded alongside _operator_batch
# =====================================================================


class TestWorkflowStateCarry:
    """The prefetch pass populates _operator_table_meta on the served path."""

    async def test_served_table_carries_meta_into_state(self, mock_resolution_context) -> None:
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[{"nsr_ncr": 0.1, "spend": 100}],
            operator_weights_version=_CURRENT_VERSION,
            operator_synced_at=_FIXTURE_ASOF,
        )
        await _run_and_capture_html(wf)
        # Every served operator table carries its meta keyed by table_name.
        assert _SUMMARY in wf._operator_table_meta
        meta = wf._operator_table_meta[_SUMMARY]
        assert meta.weights_version == _CURRENT_VERSION
        assert meta.synced_at == _FIXTURE_ASOF


# =====================================================================
# 3. C2-at-render guard PRESENCE (the named fire-seam for the adversary)
# =====================================================================


class TestC2GuardPresence:
    """_fetch_table refuses a weighted table lacking weights_version (guard exists)."""

    def _summary_spec(self) -> Any:
        return next(s for s in TABLE_SPECS if s.table_name == _SUMMARY)

    async def _fetch_summary(self, wf: Any) -> TableResult:
        # Drive the REAL _fetch_table read-path (the fire-seam), reading from the
        # workflow's pre-populated batch+meta state. Populated via a real prefetch
        # so this exercises the wired path, not a synthetic TableResult.
        entities = await wf.enumerate_async(_default_scope())
        await wf._prefetch_operator_tables(entities, _default_params())
        return await wf._fetch_table(
            self._summary_spec(),
            offer_gid="o1",
            office_phone="+17705753103",
            vertical="chiropractic",
            row_limits={},
        )

    async def test_weighted_table_without_version_refuses_typed(
        self, mock_resolution_context
    ) -> None:
        # FIRE-SEAM: weighted rows served WITHOUT a weights_version -> the C2 guard
        # routes to the typed-refusal rail (success=False), NEVER naked numbers.
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[{"nsr_ncr": 0.1, "spend": 100}],
            operator_weights_version=None,  # provenance ABSENT for a weighted table
        )
        result = await self._fetch_summary(wf)
        assert result.success is False
        assert result.error_type == "WeightsProvenanceAbsent"
        # Non-null-coercible: the refusal is a typed discriminant, not a null/empty.
        assert result.data is None

    async def test_weighted_table_with_version_succeeds_and_carries_provenance(
        self, mock_resolution_context
    ) -> None:
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[{"nsr_ncr": 0.1, "spend": 100}],
            operator_weights_version=_CURRENT_VERSION,
            operator_synced_at=_FIXTURE_ASOF,
        )
        result = await self._fetch_summary(wf)
        assert result.success is True
        assert result.weights_version == _CURRENT_VERSION
        assert result.synced_at == _FIXTURE_ASOF

    async def test_unweighted_table_without_version_does_not_refuse(
        self, mock_resolution_context
    ) -> None:
        # An UNWEIGHTED table (no weight-governed column) is EXEMPT: it renders
        # normally with NO badge and MUST NOT trip the guard.
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[{"spend": 100, "cpl": 50.0}],  # no weighted column
            operator_weights_version=None,
        )
        result = await self._fetch_summary(wf)
        assert result.success is True
        assert result.weights_version is None

    async def test_empty_served_table_is_not_weighted_no_refusal(
        self, mock_resolution_context
    ) -> None:
        # A genuinely-empty served table has no weight-banded number to disclose:
        # not weighted, so the guard does not fire (renders empty, not refused).
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[],
            operator_weights_version=None,
        )
        result = await self._fetch_summary(wf)
        assert result.success is True
        assert result.row_count == 0


# =====================================================================
# 4. _rows_are_weighted discriminator PRESENCE
# =====================================================================


class TestWeightedDiscriminator:
    """_rows_are_weighted scopes the C2 population to weight-governed columns."""

    def test_mirror_matches_data_plane_frozen_set(self) -> None:
        # The client-side mirror is byte-identical to the data plane's authoritative
        # WEIGHTED_CONSUMER_METRICS (the single source of truth).
        assert (
            frozenset({"ns_rate", "nc_rate", "conv_rate", "nsr_ncr", "xcps"})
            == WEIGHTED_CONSUMER_METRICS
        )

    @pytest.mark.parametrize("col", sorted(WEIGHTED_CONSUMER_METRICS))
    def test_each_weighted_column_flags_weighted(self, col: str) -> None:
        assert _rows_are_weighted([{col: 0.5}]) is True

    def test_unweighted_columns_are_not_weighted(self) -> None:
        assert _rows_are_weighted([{"spend": 1, "cpl": 2.0, "ecps": 3.0}]) is False

    def test_empty_rows_are_not_weighted(self) -> None:
        assert _rows_are_weighted([]) is False


# =====================================================================
# 5. Render badge + subtitle asOf PRESENCE (H7, the point of action)
# =====================================================================


class TestBadgeRenderPresence:
    """The provenance line + asOf subtitle appear in the consumed HTML."""

    def test_provenance_line_renders_version_and_asof(self) -> None:
        html = _provenance_line_html(_CURRENT_VERSION, _FIXTURE_ASOF)
        assert "section-provenance" in html
        assert _CURRENT_VERSION in html  # the id itself discloses UNRATIFIED
        assert _FIXTURE_ASOF in html

    def test_provenance_line_absent_when_no_version(self) -> None:
        # An unweighted section discloses nothing on the provenance line.
        assert _provenance_line_html(None, _FIXTURE_ASOF) == ""

    def test_asof_unknown_disclosed_not_omitted_for_weighted(self) -> None:
        # RULING §4c: weighted + asOf None -> DISCLOSE "as of unknown", never omit.
        html = _provenance_line_html(_CURRENT_VERSION, None)
        assert "section-provenance" in html
        assert _CURRENT_VERSION in html
        assert "as of unknown" in html

    def test_subtitle_stamped_with_asof_when_synced_at_present(self) -> None:
        # R4/DEFER-6: the subtitle carries the LIVE asOf so a snapshot is not read
        # as stable history. The base window prose is preserved.
        section = DataSection(name=_SUMMARY, rows=[{"nsr_ncr": 0.1}], synced_at=_FIXTURE_ASOF)
        html = _section_disclosure_html(section)
        assert "section-subtitle" in html
        assert "Lifetime performance metrics" in html  # base prose preserved
        assert f"as of {_FIXTURE_ASOF}" in html  # live asOf appended

    def test_subtitle_unchanged_when_no_synced_at(self) -> None:
        section = DataSection(name=_SUMMARY, rows=[{"spend": 1}])
        html = _section_disclosure_html(section)
        assert "Lifetime performance metrics" in html
        assert "as of" not in html  # no bare/blank asOf when there is no stamp

    def test_weighted_section_renders_badge_in_full_report(self) -> None:
        # End-to-end at the consumed render: a served weighted table with provenance
        # surfaces the badge DIV in the composed HTML the founder acts on. Assert on
        # the rendered element, not the CSS selector (which is always present).
        data = _report_data(
            {
                _SUMMARY: TableResult(
                    table_name=_SUMMARY,
                    success=True,
                    data=[{"nsr_ncr": 0.1, "spend": 100}],
                    row_count=1,
                    weights_version=_CURRENT_VERSION,
                    synced_at=_FIXTURE_ASOF,
                )
            }
        )
        html = compose_report(data)
        assert '<div class="section-provenance">' in html
        assert _CURRENT_VERSION in html
        assert _FIXTURE_ASOF in html

    def test_unweighted_section_renders_no_badge_in_full_report(self) -> None:
        # An unweighted served table renders NO provenance line DIV (no badge). The
        # CSS selector `.section-provenance` is always inlined; the rendered element
        # `<div class="section-provenance">` is what must be absent.
        data = _report_data(
            {
                _SUMMARY: TableResult(
                    table_name=_SUMMARY,
                    success=True,
                    data=[{"spend": 100, "cpl": 50.0}],
                    row_count=1,
                    weights_version=None,
                    synced_at=None,
                )
            }
        )
        html = compose_report(data)
        assert '<div class="section-provenance">' not in html


# --- Local helpers (neutral scaffolding) ---


def _report_data(table_results: dict[str, TableResult]) -> Any:
    """Build InsightsReportData with the given table_results (others absent)."""
    import time

    from autom8_asana.automation.workflows.insights.formatter import InsightsReportData

    return InsightsReportData(
        business_name="Acme",
        office_phone="+17705753103",
        vertical="chiropractic",
        table_results=table_results,
        started_at=time.monotonic(),
        version="test",
    )


# HtmlRenderer is imported to keep the DataSection provenance fields exercised
# through the real renderer surface (the badge helpers are its collaborators).
_ = HtmlRenderer
