"""Guard-PRESENCE tests for the coverage-disclosure render wiring (Sprint 4).

provenance-to-the-human Sprint 4 (coverage-disclosure-at-render), the SPINE
build-half's own suite, under the BR-3 ruling (a) HONEST-FLOOR. These assert the
wiring EXISTS and the ruled faces render on the real hop: the client meta carries
the coverage siblings, the workflow threads them per-table, and the OFFER TABLE
section renders exactly one of the three ruled faces AT THE POINT OF ACTION --
never a fabricated ceiling, never a silent blank, never a throw on the deck's
honest-absent state.

CRITIC-NEVER-AUTHOR (the load-bearing boundary): this file is authored by the
guard's BUILDER. It proves the render faces are PRESENT and WIRED -- it does NOT
author the two-sided coverage teeth (stripped-RED / disclosed-GREEN at the
composed HTML with the genuine pre-carry parent RED). That proof-obligation
(PO-COV-1..5, contract §6) belongs to the rite-disjoint numerical-adversary at
``verify``. Building the render AND grading whether it bites in one soul is the
FORBIDDEN merge.

The named fire-seams handed to the adversary:
  - MEASURED floor: ``formatter._coverage_line_html`` -- an OFFER TABLE
    DataSection whose ``coverage.status == "measured"`` with an
    ``orphan_spend_share`` renders the DIRECTIONAL IGNORANCE FLOOR
    (``spend attribution: ≥ X% unattributed (orphan ads)``) -- a ``≥``-floor,
    never a point-coverage claim.
  - DISCLOSED-UNKNOWN: the same function -- ``coverage=None`` renders the visible
    ``spend attribution: not measured`` token (the deck honest-absent state, and
    the would-be-dropped ``coverage_expected=True`` state until F5-coverage-THROW
    arms); ``status=="no_data"`` renders ``spend attribution: no data this
    window``. Both structurally distinct from a silent blank.
  - THROW-FREE boundary: ``InsightsExportWorkflow._fetch_table`` -- coverage
    absence NEVER produces a ``success=False`` TableResult (the deck typed-THROW
    is NOT-YET-ARMABLE; the weights C2 guard is weights-only, unchanged).
"""

from __future__ import annotations

from typing import Any

from autom8_asana.automation.workflows.insights.formatter import (
    DataSection,
    HtmlRenderer,
    TableResult,
    _coverage_line_html,
    _section_disclosure_html,
)
from autom8_asana.clients.data._endpoints.operator import (
    AttributionCoverage,
    OperatorBatchMeta,
    _merge_batch_metas,
    distribute_per_office_meta,
)

_OFFER = "OFFER TABLE"

_MEASURED = AttributionCoverage(
    status="measured",
    coverage_pct=0.877,
    orphan_spend_share=0.123,
    total_spend=20000.0,
)
_NO_DATA = AttributionCoverage(status="no_data")


def _offer_section(
    coverage: Any = None, coverage_expected: bool = False, name: str = _OFFER
) -> DataSection:
    return DataSection(
        name=name,
        rows=[{"offer_id": "o1", "spend": 100.0}],
        row_count=1,
        coverage=coverage,
        coverage_expected=coverage_expected,
    )


class TestCoverageLineFaces:
    """The three ruled faces of the OFFER TABLE coverage line (BR-3 ruling (a))."""

    def test_measured_renders_directional_ignorance_floor(self) -> None:
        html_out = _coverage_line_html(_offer_section(coverage=_MEASURED))
        assert "spend attribution: ≥ 12.3% unattributed (orphan ads)" in html_out
        assert "section-coverage" in html_out
        # The floor is a ≥ on the UNATTRIBUTED share -- never a point-coverage
        # claim and never the complement presented as accuracy.
        assert "87.7" not in html_out

    def test_no_data_renders_disclosed_unknown_window(self) -> None:
        html_out = _coverage_line_html(_offer_section(coverage=_NO_DATA))
        assert "spend attribution: no data this window" in html_out
        # Never rendered as a zero or full attribution reading.
        assert "0%" not in html_out
        assert "100%" not in html_out

    def test_absent_renders_visible_not_measured_token(self) -> None:
        # The deck honest-absent state (None + False): a VISIBLE token,
        # structurally distinct from a silent blank.
        html_out = _coverage_line_html(_offer_section(coverage=None))
        assert "spend attribution: not measured" in html_out
        assert "section-coverage" in html_out

    def test_would_be_dropped_state_also_discloses_unknown(self) -> None:
        # (None, coverage_expected=True): the would-be-dropped state discloses
        # unknown too -- the typed THROW is NOT-YET-ARMABLE (F5-coverage-THROW).
        html_out = _coverage_line_html(_offer_section(coverage=None, coverage_expected=True))
        assert "spend attribution: not measured" in html_out

    def test_degenerate_measured_without_share_falls_to_no_data(self) -> None:
        degenerate = AttributionCoverage(status="measured", orphan_spend_share=None)
        html_out = _coverage_line_html(_offer_section(coverage=degenerate))
        assert "spend attribution: no data this window" in html_out
        assert "≥" not in html_out

    def test_non_offer_sections_render_no_coverage_line(self) -> None:
        # No cry-wolf: sections that allocate no spend make no coverage claim,
        # even when a coverage payload is (wrongly) present on them.
        html_out = _coverage_line_html(_offer_section(coverage=_MEASURED, name="APPOINTMENTS"))
        assert html_out == ""


class TestSectionDisclosureComposition:
    """Coverage joins subtitle + provenance in one disclosure hop (no drift)."""

    def test_offer_section_composes_all_three_disclosures(self) -> None:
        section = DataSection(
            name=_OFFER,
            rows=[{"offer_id": "o1"}],
            row_count=1,
            weights_version="2026-03-24-static-UNRATIFIED",
            synced_at="2026-07-13T00:00:00Z",
            coverage=_MEASURED,
        )
        html_out = _section_disclosure_html(section)
        assert "section-subtitle" in html_out
        assert "weights 2026-03-24-static-UNRATIFIED" in html_out
        assert "spend attribution: ≥ 12.3% unattributed" in html_out

    def test_absent_coverage_is_not_a_silent_blank_on_offer(self) -> None:
        section = DataSection(name=_OFFER, rows=[], coverage=None)
        html_out = _section_disclosure_html(section)
        assert "spend attribution: not measured" in html_out


class TestRenderedDocumentCarriesCoverage:
    """The full HtmlRenderer document carries the OFFER TABLE coverage face."""

    def test_document_contains_measured_floor_for_offer_table(self) -> None:
        renderer = HtmlRenderer()
        doc = renderer.render_document(
            title="t",
            metadata={},
            sections=[_offer_section(coverage=_MEASURED)],
        )
        assert "spend attribution: ≥ 12.3% unattributed (orphan ads)" in doc

    def test_document_disclosed_unknown_distinct_from_blank(self) -> None:
        renderer = HtmlRenderer()
        with_token = renderer.render_document(
            title="t", metadata={}, sections=[_offer_section(coverage=None)]
        )
        # A non-offer section is the honest silent-blank contrast.
        without_token = renderer.render_document(
            title="t",
            metadata={},
            sections=[_offer_section(coverage=None, name="APPOINTMENTS")],
        )
        assert "spend attribution: not measured" in with_token
        assert "spend attribution" not in without_token


class TestDeckAbsenceIsThrowFree:
    """Coverage absence never fails a table; the weights guard stays weights-only."""

    def test_table_result_defaults_are_honest_absent(self) -> None:
        result = TableResult(table_name=_OFFER, success=True, data=[{"spend": 1.0}])
        assert result.coverage is None
        assert result.coverage_expected is False
        assert result.success is True

    def test_client_meta_defaults_are_honest_absent(self) -> None:
        meta = OperatorBatchMeta()
        assert meta.coverage is None
        assert meta.coverage_expected is False

    def test_distribute_meta_reads_coverage_siblings(self) -> None:
        body = {
            "data": {
                "results": [
                    {
                        "status": "success",
                        "data": {
                            "data": [],
                            "meta": {
                                "weights_version": "2026-03-24-static-UNRATIFIED",
                                "coverage_expected": True,
                                "coverage": {
                                    "status": "measured",
                                    "coverage_pct": 0.877,
                                    "orphan_spend_share": 0.123,
                                    "total_spend": 20000.0,
                                },
                            },
                        },
                    }
                ]
            }
        }
        meta = distribute_per_office_meta(body)
        assert meta.coverage is not None
        assert meta.coverage.status == "measured"
        assert meta.coverage.orphan_spend_share == 0.123
        assert meta.coverage_expected is True

    def test_merge_batch_metas_first_observer_owns_coverage(self) -> None:
        empty = OperatorBatchMeta()
        observed = OperatorBatchMeta(coverage=_NO_DATA, coverage_expected=True)
        merged = _merge_batch_metas([empty, observed])
        assert merged.coverage is _NO_DATA
        assert merged.coverage_expected is True

    def test_merge_batch_metas_all_absent_collapses_to_honest_absent(self) -> None:
        merged = _merge_batch_metas([OperatorBatchMeta(), OperatorBatchMeta()])
        assert merged.coverage is None
        assert merged.coverage_expected is False
