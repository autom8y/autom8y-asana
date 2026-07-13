"""Guard-PRESENCE tests for the weight-ignorance band render (Sprint 5).

provenance-to-the-human Sprint 5 (the-band-itself), the S5-E render builder's
own suite, under BAND-MECHANISM spec §7. These assert the wiring EXISTS and the
gates hold on the real hop: the client meta carries the typed ``band`` sibling,
the workflow threads it per-table, and the render surfaces the C1-clean
one-line disclosure ONLY behind the named GATE-B flag ``render_nsr_band``
(``AUTOM8_RENDER_NSR_BAND``), which LANDS OFF -- the shipped default composes a
document byte-identical to pre-band.

CRITIC-NEVER-AUTHOR (the load-bearing boundary): this file is authored by the
render's BUILDER. It proves the gates are PRESENT and WIRED -- it does NOT
author the §7.5 two-sided fixture (the CI-laundered band driven RED by a
seeded-false mutation / the honest ignorance band GREEN / flag-OFF
byte-identical, with the genuine falsifier proof). That proof-obligation
belongs to S5-F with the adversarial-disprover. Building the render AND
grading whether its teeth bite in one soul is the FORBIDDEN merge.

The named fire-seams handed to the disprover (defined in
``formatter._band_line_html``):

  - FIRE-SEAM BAND-FLAG: the GATE-B flag gate -- flag OFF (absent / empty /
    unrecognized env value) returns "" BEFORE any band inspection, so the
    composed document is byte-identical to pre-band by construction.
  - FIRE-SEAM BAND-C1: the C1 render refusal -- an overlay band carrying a
    sub-[0,1] (or bound-less) interval is REFUSED at render (nothing drawn,
    ``insights_export_band_render_refused`` logged with
    reason="c1_interval_launder") rather than drawn as a tight ribbon. The
    client transport deliberately does NOT re-assert C1, so a laundered band
    injected at any altitude flows to exactly this one refusal point.
  - FIRE-SEAM BAND-LINE: the band line render -- flag ON + weighted section +
    honest [0,1] overlay produces EXACTLY the one-line §7.1 disclosure
    (width + direction + version) in the ``.section-provenance`` grammar.

FLAG-ON EXPRESSION under test: the mechanism-default conservative textual form,
pending the operator's GATE-B presentation ruling (OP-3) -- NOT a GATE-B pick;
the four GATE-B presentation shapes (spec §7.3 OPT-A..D) remain the operator's.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from autom8_asana.automation.workflows.insights import formatter as _fmt_mod
from autom8_asana.automation.workflows.insights.formatter import (
    RENDER_NSR_BAND_ENV_VAR,
    DataSection,
    HtmlRenderer,
    InsightsReportData,
    TableResult,
    _band_line_html,
    _render_nsr_band_enabled,
    _section_disclosure_html,
    compose_report,
)
from autom8_asana.clients.data._endpoints.operator import (
    OperatorBatchMeta,
    WeightIgnoranceBand,
)

from .test_insights_export import (
    _default_params,
    _default_scope,
    _force_fallback,  # noqa: F401  -- module-scoped fixture, imported for usefixtures
    _make_task,
    _make_workflow,
)

pytestmark = pytest.mark.usefixtures("_force_fallback")

# The canonical current version-id (byte-identical to the data plane's
# CURRENT_WEIGHT_SCHEME_VERSION). The id ITSELF discloses UNRATIFIED.
_CURRENT_VERSION = "2026-03-24-static-UNRATIFIED"
_FIXTURE_ASOF = "2026-07-13T00:00:00Z"
_SUMMARY = "SUMMARY"
# SUMMARY's operator insight (tables.py TableSpec) -- keys operator_insight_meta.
_SUMMARY_INSIGHT = "account_level_stats"

# The honest emitted band: [0,1]-ignorance + UNDERSTATE overlay (spec §1/§2).
_OVERLAY_BAND = WeightIgnoranceBand(
    status="ignorance_overlay",
    scheme_version=_CURRENT_VERSION,
    lower=0.0,
    upper=1.0,
    overlay_direction="understate",
    overlay_citation="WORM-LEDGER §1.1 / BAND-MECHANISM §2",
)

_NOT_APPLICABLE_BAND = WeightIgnoranceBand(
    status="no_band_applicable",
    scheme_version=_CURRENT_VERSION,
)

# The CI-laundered mutation shape (the §3 REFUSED Wilson ribbon). Constructed
# here only to point the C1 refusal seam at it -- the two-sided RED proof that
# the fixture is a genuine falsifier is S5-F's with the disprover.
_LAUNDERED_BAND = WeightIgnoranceBand(
    status="ignorance_overlay",
    scheme_version=_CURRENT_VERSION,
    lower=0.3093,
    upper=0.3150,
    overlay_direction="understate",
)

# The exact mechanism-default line (FIRE-SEAM BAND-LINE), byte-exact.
_EXPECTED_BAND_LINE = (
    '<div class="section-provenance section-band">'
    "forward-rate band: [0,1] ignorance · direction: understates "
    "(weights 2026-03-24-static-UNRATIFIED)</div>"
)


def _weighted_section(
    band: Any = None,
    *,
    weights_version: str | None = _CURRENT_VERSION,
    name: str = _SUMMARY,
) -> DataSection:
    return DataSection(
        name=name,
        rows=[{"nsr_ncr": 31.2, "spend": 100.0}],
        row_count=1,
        weights_version=weights_version,
        synced_at=_FIXTURE_ASOF,
        band=band,
    )


@pytest.fixture
def _flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the GATE-B flag OFF explicitly (the shipped default: env absent)."""
    monkeypatch.delenv(RENDER_NSR_BAND_ENV_VAR, raising=False)


@pytest.fixture
def _flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """The explicitly-flagged-ON posture -- ONLY these tests see the band."""
    monkeypatch.setenv(RENDER_NSR_BAND_ENV_VAR, "true")


# =====================================================================
# 1. The flag mechanism (GATE-B, lands OFF)
# =====================================================================


class TestFlagMechanism:
    """render_nsr_band is env-var-driven, read at call time, default OFF."""

    def test_default_is_off_when_env_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(RENDER_NSR_BAND_ENV_VAR, raising=False)
        assert _render_nsr_band_enabled() is False

    @pytest.mark.parametrize("value", ["", "false", "0", "no", "off", "banana", "  "])
    def test_non_optin_values_stay_off(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        # Lands-OFF polarity: anything but an explicit opt-in is OFF (the
        # conservative complement of the kill switch's opt-OUT vocabulary).
        monkeypatch.setenv(RENDER_NSR_BAND_ENV_VAR, value)
        assert _render_nsr_band_enabled() is False

    @pytest.mark.parametrize("value", ["true", "1", "yes", "TRUE", " Yes "])
    def test_explicit_optin_values_enable(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv(RENDER_NSR_BAND_ENV_VAR, value)
        assert _render_nsr_band_enabled() is True


# =====================================================================
# 2. FIRE-SEAM BAND-FLAG: flag OFF => byte-identical composed documents
# =====================================================================


class TestFlagOffByteIdentity:
    """Flag OFF: a band-carrying render is byte-identical to a no-band baseline."""

    @pytest.mark.usefixtures("_flag_off")
    def test_band_line_is_empty_before_any_band_inspection(self) -> None:
        # The gate returns "" even for a band whose attribute reads would
        # refuse/log -- OFF short-circuits FIRST (byte-identical by construction).
        assert _band_line_html(_weighted_section(band=_OVERLAY_BAND)) == ""
        assert _band_line_html(_weighted_section(band=_LAUNDERED_BAND)) == ""

    @pytest.mark.usefixtures("_flag_off")
    def test_full_document_byte_identical_render_document(self) -> None:
        renderer = HtmlRenderer()
        common: dict[str, Any] = {"title": "t", "metadata": {"Phone": "***1234"}}
        with_band = renderer.render_document(
            sections=[_weighted_section(band=_OVERLAY_BAND)], **common
        )
        without_band = renderer.render_document(sections=[_weighted_section(band=None)], **common)
        # Full-document equality: the band field's presence leaves NO trace.
        assert with_band == without_band

    @pytest.mark.usefixtures("_flag_off")
    def test_full_compose_report_byte_identical_with_frozen_clock(self) -> None:
        # compose_report stamps Generated/Duration from live clocks; freeze both
        # (module-local patch) so the band-vs-no-band comparison is byte-exact
        # over the FULL composed pipeline document.
        def _result(band: Any) -> dict[str, TableResult]:
            return {
                _SUMMARY: TableResult(
                    table_name=_SUMMARY,
                    success=True,
                    data=[{"nsr_ncr": 31.2, "spend": 100.0}],
                    row_count=1,
                    weights_version=_CURRENT_VERSION,
                    synced_at=_FIXTURE_ASOF,
                    band=band,
                )
            }

        def _compose(band: Any) -> str:
            data = InsightsReportData(
                business_name="Acme Dental",
                office_phone="+17705753103",
                vertical="chiropractic",
                table_results=_result(band),
                started_at=100.0,
                version="insights-export-v1.0",
            )
            frozen = SimpleNamespace(now=lambda tz: datetime(2026, 7, 13, tzinfo=UTC))
            with (
                patch.object(_fmt_mod, "datetime", frozen),
                patch.object(_fmt_mod, "time", SimpleNamespace(monotonic=lambda: 100.0)),
            ):
                return compose_report(data)

        assert _compose(_OVERLAY_BAND) == _compose(None)

    async def test_pipeline_flag_off_renders_no_band_marker(
        self, mock_resolution_context: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # End-to-end OFF guard on the REAL path: a band-carrying batch composes
        # a document with NO band grammar anywhere (timestamp-insensitive form).
        monkeypatch.delenv(RENDER_NSR_BAND_ENV_VAR, raising=False)
        from .test_insights_denied_render_teeth import _run_and_capture_html

        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[{"nsr_ncr": 31.2, "spend": 100.0}],
            operator_insight_meta={
                _SUMMARY_INSIGHT: OperatorBatchMeta(
                    weights_version=_CURRENT_VERSION,
                    synced_at=_FIXTURE_ASOF,
                    band=_OVERLAY_BAND,
                )
            },
            operator_weights_version=_CURRENT_VERSION,
            operator_synced_at=_FIXTURE_ASOF,
        )
        html_out = await _run_and_capture_html(wf)
        assert "section-band" not in html_out
        assert "forward-rate band" not in html_out
        # The pre-band disclosures are untouched by the dark band carry.
        assert f"weights {_CURRENT_VERSION}" in html_out


# =====================================================================
# 3. FIRE-SEAM BAND-LINE: flag ON + overlay => exactly the one line
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestFlagOnBandLine:
    """The mechanism-default expression renders the §7.1 triple, C1-clean."""

    def test_overlay_band_renders_exact_line(self) -> None:
        html_out = _band_line_html(_weighted_section(band=_OVERLAY_BAND))
        assert html_out == _EXPECTED_BAND_LINE

    def test_line_conveys_width_direction_version_tokens(self) -> None:
        # The §7.1 MUST-convey triple, asserted token-by-token.
        html_out = _band_line_html(_weighted_section(band=_OVERLAY_BAND))
        assert "[0,1] ignorance" in html_out  # width: the full logical range
        assert "direction: understates" in html_out  # the §2 proven sign
        assert f"weights {_CURRENT_VERSION}" in html_out  # version, verbatim id

    def test_line_never_conveys_forbidden_readings(self) -> None:
        # §7.2 MUST-NEVER: no "confidence", no Wilson numbers, no ± ribbon,
        # no point correction.
        html_out = _band_line_html(_weighted_section(band=_OVERLAY_BAND))
        assert "confidence" not in html_out.lower()
        assert "0.309" not in html_out
        assert "0.315" not in html_out
        assert "±" not in html_out

    @pytest.mark.parametrize(
        ("direction", "word"),
        [
            ("understate", "understates"),
            ("overstate", "overstates"),
            ("indeterminate", "indeterminate"),
        ],
    )
    def test_direction_words_render_mechanically(self, direction: str, word: str) -> None:
        band = WeightIgnoranceBand(
            status="ignorance_overlay",
            scheme_version=_CURRENT_VERSION,
            lower=0.0,
            upper=1.0,
            overlay_direction=direction,  # type: ignore[arg-type]
        )
        assert f"direction: {word}" in _band_line_html(_weighted_section(band=band))

    def test_full_document_carries_band_line_when_on(self) -> None:
        renderer = HtmlRenderer()
        doc = renderer.render_document(
            title="t", metadata={}, sections=[_weighted_section(band=_OVERLAY_BAND)]
        )
        assert _EXPECTED_BAND_LINE in doc

    def test_disclosure_hop_orders_provenance_then_band(self) -> None:
        # The single disclosure hop: the band line rides DIRECTLY under the
        # provenance line whose weights it qualifies.
        html_out = _section_disclosure_html(_weighted_section(band=_OVERLAY_BAND))
        provenance_at = html_out.index(f"weights {_CURRENT_VERSION} · as of")
        band_at = html_out.index("forward-rate band")
        assert provenance_at < band_at


# =====================================================================
# 4. Flag ON, no surface: not-applicable / absent / unweighted
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestFlagOnNoSurfaceStates:
    """ON is necessary, not sufficient: the declared-absent states render nothing."""

    def test_no_band_applicable_renders_nothing(self) -> None:
        assert _band_line_html(_weighted_section(band=_NOT_APPLICABLE_BAND)) == ""

    def test_absent_band_renders_nothing(self) -> None:
        assert _band_line_html(_weighted_section(band=None)) == ""

    def test_unweighted_section_renders_nothing_even_with_band(self) -> None:
        # No weights_version => no weight-banded number => no band surface,
        # even when a band object is (incoherently) present on the section.
        section = _weighted_section(band=_OVERLAY_BAND, weights_version=None)
        assert _band_line_html(section) == ""

    def test_document_with_not_applicable_band_has_no_band_grammar(self) -> None:
        renderer = HtmlRenderer()
        doc = renderer.render_document(
            title="t",
            metadata={},
            sections=[_weighted_section(band=_NOT_APPLICABLE_BAND)],
        )
        assert "section-band" not in doc
        assert "forward-rate band" not in doc


# =====================================================================
# 5. FIRE-SEAM BAND-C1: the render REFUSES a laundered interval
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestC1RenderRefusalPresence:
    """A sub-[0,1] overlay renders NOTHING (never a tight ribbon). Presence only:
    the two-sided proof this seam bites exactly on the laundered mutation (and
    stays green on the honest band) is S5-F's with the adversarial-disprover."""

    def test_laundered_wilson_ribbon_refused_nothing_drawn(self) -> None:
        html_out = _band_line_html(_weighted_section(band=_LAUNDERED_BAND))
        assert html_out == ""

    def test_laundered_band_leaks_no_interval_numbers_into_document(self) -> None:
        renderer = HtmlRenderer()
        doc = renderer.render_document(
            title="t", metadata={}, sections=[_weighted_section(band=_LAUNDERED_BAND)]
        )
        assert "0.309" not in doc
        assert "0.315" not in doc
        assert "section-band" not in doc

    @pytest.mark.parametrize(
        ("lower", "upper"),
        [
            (0.3093, 0.3150),  # the Wilson ribbon itself
            (0.0, 0.9),  # narrowed top
            (0.1, 1.0),  # narrowed bottom
            (None, None),  # bound-less overlay cannot prove it is [0,1]
            (None, 1.0),
            (0.0, None),
        ],
    )
    def test_every_non_unit_interval_shape_is_refused(
        self, lower: float | None, upper: float | None
    ) -> None:
        band = WeightIgnoranceBand(
            status="ignorance_overlay",
            scheme_version=_CURRENT_VERSION,
            lower=lower,
            upper=upper,
            overlay_direction="understate",
        )
        assert _band_line_html(_weighted_section(band=band)) == ""

    def test_unconveyable_direction_refused(self) -> None:
        # The §7.1 direction is MANDATORY; a width-only line would
        # under-disclose, so nothing is drawn.
        band = WeightIgnoranceBand(
            status="ignorance_overlay",
            scheme_version=_CURRENT_VERSION,
            lower=0.0,
            upper=1.0,
            overlay_direction=None,
        )
        assert _band_line_html(_weighted_section(band=band)) == ""

    def test_nameless_scheme_refused(self) -> None:
        band = WeightIgnoranceBand(
            status="ignorance_overlay",
            scheme_version="",
            lower=0.0,
            upper=1.0,
            overlay_direction="understate",
        )
        assert _band_line_html(_weighted_section(band=band)) == ""


# =====================================================================
# 6. Workflow threading: the band rides _fetch_table onto TableResult
# =====================================================================


class TestWorkflowBandThreading:
    """_fetch_table carries the batch meta's band per-table, passthrough-only."""

    async def _fetch_summary(self, wf: Any) -> TableResult:
        from autom8_asana.automation.workflows.insights.tables import TABLE_SPECS

        entities = await wf.enumerate_async(_default_scope())
        await wf._prefetch_operator_tables(entities, _default_params())
        spec = next(s for s in TABLE_SPECS if s.table_name == _SUMMARY)
        return await wf._fetch_table(
            spec,
            offer_gid="o1",
            office_phone="+17705753103",
            vertical="chiropractic",
            row_limits={},
        )

    async def test_served_table_carries_band(self, mock_resolution_context: Any) -> None:
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[{"nsr_ncr": 31.2, "spend": 100.0}],
            operator_insight_meta={
                _SUMMARY_INSIGHT: OperatorBatchMeta(
                    weights_version=_CURRENT_VERSION,
                    synced_at=_FIXTURE_ASOF,
                    band=_OVERLAY_BAND,
                )
            },
        )
        result = await self._fetch_summary(wf)
        assert result.success is True
        assert result.band is _OVERLAY_BAND
        # The siblings are undisturbed by the band carry.
        assert result.weights_version == _CURRENT_VERSION
        assert result.synced_at == _FIXTURE_ASOF

    async def test_bandless_meta_yields_declared_none(self, mock_resolution_context: Any) -> None:
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[{"nsr_ncr": 31.2, "spend": 100.0}],
            operator_weights_version=_CURRENT_VERSION,
        )
        result = await self._fetch_summary(wf)
        assert result.success is True
        assert result.band is None

    async def test_c2_weights_guard_unchanged_by_band(self, mock_resolution_context: Any) -> None:
        # The C2 never-hidden guard stays weights-only: a weighted table without
        # a weights_version still refuses typed even when a band is present.
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[{"nsr_ncr": 31.2, "spend": 100.0}],
            operator_insight_meta={_SUMMARY_INSIGHT: OperatorBatchMeta(band=_OVERLAY_BAND)},
        )
        result = await self._fetch_summary(wf)
        assert result.success is False
        assert result.error_type == "WeightsProvenanceAbsent"

    def test_compose_report_threads_band_to_section(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Step-8 carry: the banded TableResult surfaces the line iff flag ON.
        monkeypatch.setenv(RENDER_NSR_BAND_ENV_VAR, "true")
        data = InsightsReportData(
            business_name="Acme Dental",
            office_phone="+17705753103",
            vertical="chiropractic",
            table_results={
                _SUMMARY: TableResult(
                    table_name=_SUMMARY,
                    success=True,
                    data=[{"nsr_ncr": 31.2, "spend": 100.0}],
                    row_count=1,
                    weights_version=_CURRENT_VERSION,
                    synced_at=_FIXTURE_ASOF,
                    band=_OVERLAY_BAND,
                )
            },
            started_at=100.0,
            version="insights-export-v1.0",
        )
        assert _EXPECTED_BAND_LINE in compose_report(data)
