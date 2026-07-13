"""Two-sided coverage-disclosure TEETH at the ACTUAL consumed render (Sprint 4).

provenance-to-the-human Sprint 4 (coverage-disclosure-at-render), the GATE-1
render altitude, under Potnia's BR-3 ruling (a) HONEST-FLOOR. This is the
rite-disjoint numerical-adversary's DISJOINT day-one fixture pair for the PO-COV
family (contract autom8y-data origin/main
``.ledge/specs/COVERAGE-DISCLOSURE-render-seam.md`` §6 / §8.3). It is authored
FRESH -- it does NOT extend the guard-author's PRESENCE suite
(``test_insights_coverage_render.py``), which by its own header proves the render
faces are PRESENT/WIRED but explicitly does NOT author the discriminating
stripped/parent-RED teeth. Building the render AND grading whether it bites in one
soul is the FORBIDDEN merge; this file is the disjoint prove-half.

CITED, NOT DUPLICATED -- what the guard-author's PRESENCE suite already covers
-----------------------------------------------------------------------------
The BUILDER's ``test_insights_coverage_render.py`` asserts, at the INTERNAL /
formatter-helper altitude (one step BELOW the consumed HTML):
  - ``TestCoverageLineFaces`` -- ``_coverage_line_html`` on a hand-built
    ``DataSection`` renders the three faces (measured floor / no_data / not
    measured) + non-offer returns "".
  - ``TestSectionDisclosureComposition`` -- ``_section_disclosure_html`` composes
    subtitle + provenance + coverage.
  - ``TestRenderedDocumentCarriesCoverage`` -- ``HtmlRenderer.render_document`` on
    a hand-built section carries the face; not-measured != a non-offer blank.
  - ``TestDeckAbsenceIsThrowFree`` -- ``TableResult`` / ``OperatorBatchMeta``
    honest-absent defaults; ``distribute_per_office_meta`` reads the siblings;
    ``_merge_batch_metas`` first-observer rule.

Those are PRESENCE (the helper exists and, fed a section, emits the face). This
file adds the DISCRIMINATION the presence suite omits, at ONE ALTITUDE HIGHER:

  1. The REAL END-TO-END PATH to the COMPOSED HTML. Every render arm below reads
     ``compose_report``'s output on the actual consumed path (wire body ->
     ``distribute_per_office_meta`` H5 fold -> workflow prefetch meta ->
     ``_fetch_table`` passthrough -> ``compose_report``), NOT
     ``_coverage_line_html`` handed a hand-built section. The founder acts on the
     RENDERED HTML the deck publishes; the presence suite's helper-altitude green
     proves the function works, not that the WIRING delivers it to the point of
     action (THE BESPOKE TRAP, contract §0 -- existence != SURVIVAL).
  2. The PERTURBATION probe (PO-COV-1 value-faithfulness). A DIFFERENT emitted
     ``orphan_spend_share`` renders a DIFFERENT floor -- proving the render
     reflects the CARRIED value byte-for-byte, not a hardcoded "12.3%" the
     presence suite's single fixture could never catch.
  3. The GENUINE PARENT RED-BEFORE (PO-COV-5, no G-THEATER). The measured-floor
     and not-measured assertions FAIL RED at the coverage-blind parent
     ``ee382897`` (a SILENT BLANK -- the exact gap this sprint closes), and pass
     GREEN at the build ``edfd9f55``. The presence suite has no parent arm.
  4. The NON-VACUITY controls with GROUND-TRUTH discrimination (PO-COV-2/-4): a
     non-offer section renders NO coverage token in the SAME composed document
     where the OFFER TABLE renders one, and no_data renders "no data" NEVER 0/100.

THE SOLE DISCRIMINATOR (the one signal nobody else checks)
----------------------------------------------------------
In the OFFER TABLE ``<section>`` of the composed HTML, the coverage face is one of
exactly three mutually-exclusive shapes (BR-3 ruling (a), contract §Q3/§Q4):
  (M) MEASURED  : ``<div class="section-provenance section-coverage">spend
      attribution: ≥ <byte-exact-share>% unattributed (orphan ads)</div>`` -- a
      ``≥``-floor on the UNATTRIBUTED share, never a point "coverage X%" claim.
  (U) DISCLOSED-UNKNOWN : the SAME ``section-coverage`` div carrying either
      ``spend attribution: not measured`` (coverage absent -- deck honest-absent
      AND the would-be-dropped ``coverage_expected=True`` state, THROW
      not-yet-armable per §Q3 fallback) or ``spend attribution: no data this
      window`` (``status=="no_data"``). VISIBLE, structurally distinct from blank.
  (B) SILENT BLANK (the DEFECT) : no ``section-coverage`` div at all -- the
      coverage-blind OFFER TABLE the founder would trust as complete. This is what
      the PARENT ``ee382897`` renders (proven below), the exact silent
      under-count the initiative kills (``.know/db.md:181-184``).

The cheap signals are ALL blind to (M) vs (U) vs (B): the file exists and is valid
HTML in all three; ``result.success`` and row-count are IDENTICAL across all three
(coverage is a passthrough carry, never a throw on the deck -- contract §2
supersession / DECK TRUTH); a byte-hash of the doc changes but says nothing about
trustworthiness. The discriminator is the ``section-coverage`` div text WITHIN the
OFFER TABLE section -- read the GROUND-TRUTH render string, never an inferred
label, never the internal ``TableResult`` the presence suite stops at.

WHY THE SECTION MUST BE SLICED PRECISELY (adversary finding F-SLICE, filed as a
defect in the verdict): a whole-document substring check is BLIND -- the doc's
inline CSS carries literal ``100%`` and ``0`` tokens, and any OTHER section
rendering coverage would satisfy an OFFER-TABLE assert. This file slices the exact
``<section id="offer-table">...</section>`` (see ``_offer_section``) and asserts
WITHIN it. (The Sprint-3 shared ``_offer_table_section_html`` slicer keys on the
first literal ``"OFFER TABLE"`` -- which is the SIDEBAR NAV link, not the section
-- and mis-slices to the whole document; verified for a denied table. This file
does NOT reuse it; it authors its own id-anchored slicer.)

TWO-SIDED, GENUINE-GAP (no defect injection anywhere)
-----------------------------------------------------
The RED-before is a REAL gap at the coverage-blind parent ``ee382897``: the render
wiring is wholly absent there (``git show ee382897:...formatter.py | grep
coverage`` returns ZERO lines -- no ``_coverage_line_html``, no ``section-
coverage`` div, no ``TableResult.coverage`` field, no ``coverage_expected``). It is
NOT a defect injected into working code (that would be G-THEATER). The
parent-portable ``TestParentGenuineRedBefore`` drives ``compose_report`` (which
exists at BOTH commits) with an OFFER TABLE and asserts BOTH the measured-floor
arm AND the not-measured-token arm; the file is copied verbatim into an
``ee382897`` scratch worktree where BOTH arms FAIL RED (silent blank -- no
coverage div), and both pass GREEN here. That is the two-sided genuine-gap proof.

Parent-portability idiom (the Sprint-1 teeth pattern): (a) the build-only client
symbols (``distribute_per_office_meta`` etc.) are imported DEFENSIVELY so the file
COLLECTS at the parent without ImportError; the end-to-end arms that USE them are
skipped at the parent, and the parent-portable ``compose_report`` arms (which use
NONE of them) still run and FAIL RED. (b) ``TableResult`` / ``DataSection`` are
constructed with kwargs FILTERED to the fields the commit under test actually
declares (``_supported_kwargs`` via ``dataclasses.fields``), so the constructor
does not TypeError at the parent where ``coverage`` / ``coverage_expected`` do not
exist; the ASSERTS then carry the arms (the parent renders no coverage div ->
RED).

Construction seams (``_make_task`` / ``_make_workflow`` / ``_run_and_capture_html``)
are UPSTREAM neutral scaffolding shared with the guard-author and the Sprint-1/3
adversary files. ``_run_and_capture_html`` drives the REAL path and asserts the
offer PUBLISHED (else ``compose_report`` never ran) -- reused verbatim, it has no
slicing dependency. The discriminating ORACLE (the assertions + the id-anchored
``_offer_section`` slicer) is authored fresh here at the render altitude.

DECK TRUTH (why there is no stripped-THROW arm, per contract §2 supersession)
-----------------------------------------------------------------------------
Unlike the Sprint-1 weights carry (which HAS a C2 typed-throw arm), coverage on
the DECK batch path has NO throw arm: ``engine.get_batch`` never runs the coverage
processor, so ``coverage=None`` + ``coverage_expected`` is the TRUTHFUL state and
the typed THROW is NOT-YET-ARMABLE (F5-coverage-THROW watch, contract §7). PO-COV-3
therefore discharges via the §Q3 HONEST-FLOOR VARIANT: the would-be-dropped
(``coverage_expected=True`` + ``coverage=None``) case is CAUGHT-AS-DISCLOSED (the
visible "not measured" token), proven DISTINCT from a silent blank AND from any
fabricated full-attribution ceiling -- still two-sided, still non-vacuous. This
is not a weakness of the fixture; it is faithful to the built arm (grading the
arm that is LIVE, never asserting a THROW the deck cannot raise).
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from autom8_asana.automation.workflows.insights.formatter import (
    InsightsReportData,
    TableResult,
    compose_report,
)

# Build-only client symbols (added by the coverage-carry commit edfd9f55). Imported
# DEFENSIVELY so this file COLLECTS at the coverage-blind parent ee382897, where they
# do not exist -- collection must not ImportError, or the parent RED-before arms
# below could never run to prove the genuine gap. When absent (parent), the
# build-only end-to-end arms that USE them are SKIPPED; the parent-portable
# ``TestParentGenuineRedBefore`` arms (which use NONE of them) still run and FAIL
# RED, which is the genuine two-sided gap proof. When present (build), all run.
try:
    from autom8_asana.clients.data._endpoints.operator import (
        AttributionCoverage,
        OperatorBatchMeta,
        _merge_batch_metas,
        distribute_per_office_meta,
    )

    _BUILD_SYMBOLS_PRESENT = True
except ImportError:  # pragma: no cover -- only at the coverage-blind parent ee382897
    AttributionCoverage = None
    OperatorBatchMeta = None
    _merge_batch_metas = None
    distribute_per_office_meta = None
    _BUILD_SYMBOLS_PRESENT = False

# Neutral construction scaffolding shared with the guard-author + prior adversary
# files (these exist at BOTH commits). ``_run_and_capture_html`` drives the real
# path and asserts the offer published; it has no slicing dependency. This file does
# NOT import the Sprint-3 ``_offer_table_section_html`` slicer (see F-SLICE in the
# module docstring) -- it authors its own id-anchored ``_offer_section`` below.
from tests.unit.automation.workflows.test_insights_denied_render_teeth import (
    _run_and_capture_html,
)
from tests.unit.automation.workflows.test_insights_export import (
    _force_fallback,  # noqa: F401  -- module-scoped fixture, imported for usefixtures
    _make_task,
    _make_workflow,
)

# Build-only end-to-end probes require the client carry symbols; skip them at the
# parent where those symbols are absent (the parent-portable compose_report arms
# carry the genuine RED-before with NO dependency on these).
_requires_build_symbols = pytest.mark.skipif(
    not _BUILD_SYMBOLS_PRESENT,
    reason="coverage-carry client symbols (distribute_per_office_meta / "
    "OperatorBatchMeta / AttributionCoverage) absent at the coverage-blind parent "
    "ee382897",
)

# --- The insight_name whose rows land in the OFFER TABLE section (tables.py). ---
_OFFER_TABLE_INSIGHT = "offer_level_stats"
_OFFER = "OFFER TABLE"
_OFFER_SLUG = "offer-table"
# SUMMARY is a SERVED operator spec (account_level_stats, tables.py:158) that is
# NOT in _COVERAGE_DISCLOSED_SECTIONS -- it renders rows but NO coverage token, the
# no-cry-wolf contrast. (APPOINTMENTS is an SA-only table absent from the
# cross-tenant operator batch, so it never renders on this path -- would be a
# vacuous contrast.)
_NON_OFFER = "SUMMARY"  # a served non-offer section: rows render, coverage does not.
_NON_OFFER_SLUG = "summary"

# --- Render markers -- literal substrings of the formatter's coverage branch.
# These are the SOLE discriminator, read WITHIN the OFFER TABLE section only.
_COVERAGE_DIV = 'class="section-provenance section-coverage"'
_NOT_MEASURED = "spend attribution: not measured"
_NO_DATA = "spend attribution: no data this window"
_ATTRIBUTION_PREFIX = "spend attribution"
_ERROR_BOX = 'class="error-box"'
_DATA_TABLE = 'class="data-table"'


def _measured_floor(share_pct: str) -> str:
    """The byte-exact measured-floor token for a given rendered percent string."""
    return f"spend attribution: ≥ {share_pct} unattributed (orphan ads)"


def _offer_section(full_html: str) -> str:
    """Slice the OFFER TABLE ``<section id="offer-table"> ... </section>``.

    Keyed on the exact section-id opening tag (never emitted verbatim in the sidebar
    nav's ``href="#offer-table"``), so the coverage markers are asserted WITHIN the
    OFFER TABLE section -- not merely somewhere in the document. Returns "" when the
    section is absent so a caller can assert presence explicitly (the whole-doc
    fallback the Sprint-3 slicer used would blind the assert -- F-SLICE).
    """
    return _section_by_slug(full_html, _OFFER_SLUG)


def _section_by_slug(full_html: str, slug: str) -> str:
    """Slice ``<section id="{slug}"> ... </section>`` precisely, or "" if absent."""
    marker = f'<section id="{slug}"'
    start = full_html.find(marker)
    if start == -1:
        return ""
    end = full_html.find("</section>", start)
    if end == -1:
        return ""
    return full_html[start : end + len("</section>")]


# -----------------------------------------------------------------------------
# Byte-match anchors. The rendered floor percent is derived from the emitted
# ``orphan_spend_share`` via the formatter's ``{share:.1%}`` format
# (formatter.py:398). A share of 0.123 -> "12.3%". These are the census band the
# contract cites (.know/db.md:181-184, ~11.6-14.1% orphan) so the fixtures exercise
# real-shaped values, not toy ones. The DISCRIMINATION (floor vs unknown vs blank)
# is exact; the share value is a byte-consistent match against the emitted rounded
# value (contract PO-COV-1 equality operator: |delta| = 0 on the disclosed figure).
# -----------------------------------------------------------------------------
_SHARE_A = 0.123  # -> "12.3%"
_SHARE_A_PCT = "12.3%"
_SHARE_B = 0.087  # -> "8.7%"  (perturbation: a DIFFERENT share must render a DIFFERENT floor)
_SHARE_B_PCT = "8.7%"
_SHARE_C = 0.141  # -> "14.1%" (the census upper anchor)
_SHARE_C_PCT = "14.1%"


def _wire_body_measured(share: float, coverage_expected: bool = True) -> dict[str, Any]:
    """A REAL operator-batch wire body carrying a MEASURED coverage block.

    Shaped exactly like the per-phone ``data.meta`` the deck's operator batch folds
    (guard-author presence suite ``test_distribute_meta_reads_coverage_siblings``
    uses the same shape). Driving ``distribute_per_office_meta`` on THIS body
    exercises the REAL H5 fold that produces the ``OperatorBatchMeta`` the workflow
    threads -- not a hand-built meta side-channel.
    """
    return {
        "data": {
            "results": [
                {
                    "status": "success",
                    "data": {
                        "data": [],
                        "meta": {
                            "coverage_expected": coverage_expected,
                            "coverage": {
                                "status": "measured",
                                "coverage_pct": 1.0 - share,
                                "orphan_spend_share": share,
                                "total_spend": 20000.0,
                            },
                        },
                    },
                }
            ]
        }
    }


def _wire_body_no_data() -> dict[str, Any]:
    """A REAL wire body carrying a ``status="no_data"`` coverage block (empty window)."""
    return {
        "data": {
            "results": [
                {
                    "status": "success",
                    "data": {
                        "data": [],
                        "meta": {
                            "coverage_expected": True,
                            "coverage": {"status": "no_data"},
                        },
                    },
                }
            ]
        }
    }


def _wire_body_dropped() -> dict[str, Any]:
    """A REAL wire body reproducing the computed-then-dropped corrupt seam-drop:

    ``coverage_expected=True`` DECLARED, but the ``coverage`` payload ABSENT (dropped
    between H0 and H7). On the deck this is the would-be-dropped state the §Q3
    honest-floor discloses as UNKNOWN (the THROW is not-yet-armable, F5-coverage-THROW).
    The render must CATCH it as the visible "not measured" token -- never a silent
    blank, never a fabricated ceiling.
    """
    return {
        "data": {
            "results": [
                {
                    "status": "success",
                    "data": {
                        "data": [],
                        "meta": {"coverage_expected": True},  # declared, payload ABSENT
                    },
                }
            ]
        }
    }


async def _offer_section_from_meta(meta: Any) -> str:
    """Drive the REAL end-to-end path for the OFFER TABLE and return its section HTML.

    wire meta (an ``OperatorBatchMeta`` from ``distribute_per_office_meta``) ->
    injected as the per-insight ``operator_insight_meta`` for ``offer_level_stats``
    -> workflow prefetch threads it into ``self._operator_table_meta`` ->
    ``_fetch_table`` passthrough attaches it onto the ``TableResult`` ->
    ``compose_report`` renders the OFFER TABLE coverage face. The default operator
    rows (``{"spend": 100, "imp": 5000}``) are UNWEIGHTED, so the C2 weights guard
    never fires and the OFFER TABLE renders GREEN carrying its coverage line.
    """
    o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
    wf, *_ = _make_workflow(offers=[o1], operator_insight_meta={_OFFER_TABLE_INSIGHT: meta})
    html = await _run_and_capture_html(wf)
    return _offer_section(html)


# =====================================================================
# PO-COV-1 -- the RENDER-SEAM byte-match, driven END-TO-END, two-sided
# against the perturbation probe (value-faithful, not hardcoded).
# =====================================================================


@_requires_build_symbols
@pytest.mark.usefixtures("_force_fallback")
class TestRenderSeamMeasuredFloor:
    """The measured floor on the composed OFFER TABLE HTML byte-matches the emitted share."""

    async def test_measured_share_renders_byte_exact_floor_end_to_end(
        self, mock_resolution_context
    ) -> None:
        """GREEN (PO-COV-1): a batch carrying orphan_spend_share=0.123 renders the
        OFFER TABLE floor ``≥ 12.3% unattributed (orphan ads)`` on the CONSUMED HTML,
        byte-consistent with the emitted share, driven wire -> fold -> render.
        """
        meta = distribute_per_office_meta(_wire_body_measured(_SHARE_A))
        # The fold itself is faithful (sanity on the carried value)...
        assert meta.coverage is not None
        assert meta.coverage.orphan_spend_share == _SHARE_A
        section = await _offer_section_from_meta(meta)
        assert section != "", "the OFFER TABLE section must be present in the composed HTML"

        # ...and the CONSUMED render carries the byte-exact directional floor.
        assert _measured_floor(_SHARE_A_PCT) in section, (
            "the disclosed OFFER TABLE must render the byte-exact measured floor at "
            "the point of action"
        )
        assert _COVERAGE_DIV in section
        # It is a >= floor on the UNATTRIBUTED share -- NEVER the complement as a
        # point-coverage accuracy claim (C1: an ignorance floor must not launder into
        # an accuracy claim). coverage_pct was 0.877 -> "87.7%" must be ABSENT.
        assert "87.7" not in section, "the complement must not render as a point-coverage claim"
        assert "coverage 87" not in section

    async def test_perturbed_share_renders_a_different_floor(self, mock_resolution_context) -> None:
        """PERTURBATION (PO-COV-1 value-faithfulness): a DIFFERENT emitted share
        renders a DIFFERENT floor -- the render reflects the CARRIED value, it is
        NOT hardcoded on one percent. Three distinct shares -> three distinct floors,
        each present ONLY in its own render.
        """
        cases = [(_SHARE_A, _SHARE_A_PCT), (_SHARE_B, _SHARE_B_PCT), (_SHARE_C, _SHARE_C_PCT)]
        sections: dict[str, str] = {}
        for share, pct in cases:
            meta = distribute_per_office_meta(_wire_body_measured(share))
            sections[pct] = await _offer_section_from_meta(meta)

        for _, own_pct in cases:
            section = sections[own_pct]
            assert section != "", f"the OFFER TABLE section for {own_pct} must be present"
            # Each render carries its OWN floor...
            assert _measured_floor(own_pct) in section, (
                f"the {own_pct} share must render the {own_pct} floor"
            )
            # ...and NONE of the OTHER shares' floors (proving no hardcoding: a
            # hardcoded "12.3%" would leak into the 8.7% and 14.1% renders).
            for _, other_pct in cases:
                if other_pct != own_pct:
                    assert _measured_floor(other_pct) not in section, (
                        f"the {own_pct} render must NOT carry the {other_pct} floor -- "
                        "the disclosed floor is derived from the carried share, not hardcoded"
                    )


# =====================================================================
# PO-COV-2 -- the honest-absent NON-VACUITY control (Potnia-mandated,
# load-bearing): coverage_expected=False + None renders the OFFER TABLE
# not-measured token with NO error-box and normal rows; a NON-offer
# section renders NO coverage token at all (the disclosure doesn't cry wolf).
# =====================================================================


@_requires_build_symbols
@pytest.mark.usefixtures("_force_fallback")
class TestHonestAbsentNonVacuity:
    """The disclosure is honestly silent where silence is honest -- proven the guard
    is not a no-op that emits a coverage token everywhere."""

    async def test_absent_coverage_renders_not_measured_no_error_rows_normal(
        self, mock_resolution_context
    ) -> None:
        """GREEN (PO-COV-2): the DECK honest-absent state (coverage=None +
        coverage_expected=False -- the truthful batch-path state, contract §2) renders
        the VISIBLE ``spend attribution: not measured`` token on the OFFER TABLE, with
        NO error-box, and the table rows render normally.
        """
        # An all-default empty meta IS the deck honest-absent state.
        meta = OperatorBatchMeta()
        assert meta.coverage is None and meta.coverage_expected is False
        section = await _offer_section_from_meta(meta)
        assert section != "", "the OFFER TABLE section must be present"

        assert _NOT_MEASURED in section, (
            "the deck honest-absent OFFER TABLE must render the VISIBLE not-measured "
            "token, structurally distinct from a silent blank"
        )
        assert _COVERAGE_DIV in section
        # NO error-box: coverage absence is passthrough, NEVER a throw on the deck.
        assert _ERROR_BOX not in section, (
            "coverage absence must NOT render an error-box -- the deck THROW is "
            "not-yet-armable; absence is honest-disclosed, not refused"
        )
        # The rows still render (a data-table with the offer rows).
        assert _DATA_TABLE in section, "the table rows must render normally"

    async def test_non_offer_section_renders_no_coverage_token_same_document(
        self, mock_resolution_context
    ) -> None:
        """GREEN (PO-COV-2 no-cry-wolf, GROUND-TRUTH discrimination): in the SAME
        composed document where the OFFER TABLE renders a coverage line, a NON-offer
        section (APPOINTMENTS) renders NO coverage token at all. This proves the
        disclosure is scoped to where spend is allocated (contract §Q3 declaration-
        absent -> render nothing), not sprayed on every section.
        """
        # Drive a full document: OFFER TABLE gets a measured meta; the whole doc is
        # composed so the non-offer sections are present alongside it.
        meta = distribute_per_office_meta(_wire_body_measured(_SHARE_A))
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, *_ = _make_workflow(offers=[o1], operator_insight_meta={_OFFER_TABLE_INSIGHT: meta})
        html = await _run_and_capture_html(wf)

        offer_section = _offer_section(html)
        non_offer_section = _section_by_slug(html, _NON_OFFER_SLUG)

        # The OFFER TABLE carries the coverage line...
        assert offer_section != "" and _ATTRIBUTION_PREFIX in offer_section
        # ...and the non-offer section carries NONE (no cry-wolf).
        assert non_offer_section != "", "the APPOINTMENTS section must be present in the document"
        assert _ATTRIBUTION_PREFIX not in non_offer_section, (
            "a non-offer section must render NO coverage token -- the disclosure is "
            "scoped to where spend is allocated, it does not cry wolf"
        )
        assert _COVERAGE_DIV not in non_offer_section


# =====================================================================
# PO-COV-3 -- the corrupt would-be-dropped case is CAUGHT-as-disclosed
# (honest-floor variant, §Q3 fallback: the DECK THROW is NOT-YET-ARMABLE).
# Distinct from (i) a silent blank AND (ii) a fabricated full-attribution ceiling.
# =====================================================================


@_requires_build_symbols
@pytest.mark.usefixtures("_force_fallback")
class TestCorruptDroppedIsCaughtAsDisclosed:
    """coverage_expected=True + payload ABSENT -> CAUGHT as the visible unknown token
    (never a fabricated ceiling, never naked silence) -- the honest-floor teeth."""

    async def test_would_be_dropped_renders_visible_unknown_not_blank_not_ceiling(
        self, mock_resolution_context
    ) -> None:
        """RED-CAUGHT (PO-COV-3 honest-floor variant): a batch that DECLARES coverage
        expected but carries NO payload (the computed-then-dropped corrupt seam-drop
        reproduced) renders the VISIBLE ``not measured`` token on the OFFER TABLE --
        DISTINCT from a silent blank AND from any fabricated full-attribution ceiling.
        The corrupt case is CAUGHT (disclosed), not silently shown as complete.
        """
        meta = distribute_per_office_meta(_wire_body_dropped())
        # The would-be-dropped state travels truthfully: coverage None, expected True.
        assert meta.coverage is None
        assert meta.coverage_expected is True
        section = await _offer_section_from_meta(meta)
        assert section != "", "the OFFER TABLE section must be present"

        # (i) DISTINCT from a silent blank: the visible token IS present.
        assert _NOT_MEASURED in section, (
            "the would-be-dropped case must be CAUGHT as the visible not-measured "
            "token, never a silent blank -- the coverage-blind OFFER TABLE is refused"
        )
        assert _COVERAGE_DIV in section
        # (ii) DISTINCT from a fabricated full-attribution reading: no 100%, no point
        # coverage claim, no "0%" (asserted WITHIN the section -- not the whole doc,
        # whose inline CSS carries a literal 100%).
        assert "100%" not in section, "must NOT fabricate a full-attribution ceiling"
        assert "0%" not in section, "must NOT fabricate a zero-attribution reading"
        assert "coverage 100" not in section
        # And no throw on the deck (the arm is not-yet-armable -- disclosed, not refused).
        assert _ERROR_BOX not in section, (
            "the deck THROW is not-yet-armable (F5-coverage-THROW); the dropped case "
            "is disclosed-unknown, not thrown"
        )


# =====================================================================
# PO-COV-4 -- status="no_data" renders the no-data token, never 0%/100%.
# =====================================================================


@_requires_build_symbols
@pytest.mark.usefixtures("_force_fallback")
class TestNoDataDisclosedUnknown:
    """An empty-window no_data payload renders the honest no-data token, never a
    fabricated 0% or 100% coverage figure (the corrupt disguise the processor refuses)."""

    async def test_no_data_renders_no_data_token_never_zero_or_full(
        self, mock_resolution_context
    ) -> None:
        """GREEN (PO-COV-4): a ``status="no_data"`` batch renders ``spend attribution:
        no data this window`` on the OFFER TABLE, and NEVER 0%/100%.
        """
        meta = distribute_per_office_meta(_wire_body_no_data())
        assert meta.coverage is not None and meta.coverage.status == "no_data"
        section = await _offer_section_from_meta(meta)
        assert section != "", "the OFFER TABLE section must be present"

        assert _NO_DATA in section, (
            "an empty-window (no_data) OFFER TABLE must disclose 'no data this window', "
            "the honest unknown"
        )
        assert _COVERAGE_DIV in section
        # NEVER a 0% or 100% coverage figure (asserted WITHIN the section, not the
        # whole doc whose CSS carries 100%). The corrupt disguise is refused.
        assert "0%" not in section, "no_data must NOT render as 0% coverage"
        assert "100%" not in section, "no_data must NOT render as 100% coverage"
        # And NOT the measured floor shape (no >= directional floor for no_data).
        assert "≥" not in section, "no_data must NOT render a >= directional floor"


# =====================================================================
# PO-COV-5 -- GENUINE RED-before at the coverage-blind parent ee382897.
# Parent-portable: drives compose_report (present at BOTH commits) with
# kwargs FILTERED to the commit's supported fields; both arms FAIL RED at
# the parent (silent blank) and pass GREEN here.
# =====================================================================


def _supported_kwargs(cls: type, **kwargs: Any) -> dict[str, Any]:
    """Keep only the kwargs the dataclass ``cls`` actually declares.

    At the coverage-blind parent ee382897, ``TableResult`` / ``DataSection`` have NO
    ``coverage`` / ``coverage_expected`` fields; passing them would TypeError at
    construction and the parent arm could never run to prove the gap. Filtering to
    the commit's declared fields makes the file parent-portable: at the parent the
    coverage kwargs are silently dropped (so the section renders NO coverage div ->
    RED); at the build they are kept (so the floor renders -> GREEN). The ASSERTS,
    not the constructor, carry the two-sided arms.
    """
    field_names = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in kwargs.items() if k in field_names}


def _compose_offer_only(coverage: Any, coverage_expected: bool) -> str:
    """Compose a minimal report whose ONLY populated table is the OFFER TABLE.

    Parent-portable altitude: ``compose_report`` + ``TableResult`` + ``InsightsReportData``
    all exist at BOTH ee382897 and edfd9f55. Coverage kwargs are filtered to the
    commit's supported fields. Returns the OFFER TABLE section of the composed HTML.
    """
    result = TableResult(
        **_supported_kwargs(
            TableResult,
            table_name=_OFFER,
            success=True,
            data=[{"offer_id": "o1", "spend": 100.0}],
            row_count=1,
            coverage=coverage,
            coverage_expected=coverage_expected,
        )
    )
    data = InsightsReportData(
        business_name="B",
        office_phone="+15555550123",
        vertical="dental",
        table_results={_OFFER: result},
        started_at=0.0,
        version="test",
    )
    return _offer_section(compose_report(data))


class TestParentGenuineRedBefore:
    """The measured-floor and not-measured arms FAIL RED at the coverage-blind parent
    ee382897 (a SILENT BLANK) and pass GREEN at the build edfd9f55.

    NO ``@_requires_build_symbols`` -- these arms use NONE of the build-only client
    symbols and MUST run at the parent to prove the genuine gap. They construct via
    the parent-portable ``_compose_offer_only`` (kwargs filtered), so they COLLECT
    and RUN at ee382897; the coverage div is absent there (no ``_coverage_line_html``
    in the parent formatter) -> both asserts fail RED. This is the non-theater
    control: the RED-before is the REAL coverage-blind parent, not an injected defect.
    """

    def test_parent_red_before_measured_floor_is_absent(self) -> None:
        """Measured floor arm. GREEN here; RED at ee382897 (no coverage div).

        Build a MEASURED coverage carrier the parent-portable way. At the build the
        OFFER TABLE section carries the ``≥ 12.3%`` floor; at the parent the coverage
        div does not exist, so this assert FAILS RED -- the silent blank the sprint kills.
        """
        coverage = _measured_coverage(_SHARE_A)
        section = _compose_offer_only(coverage=coverage, coverage_expected=True)
        assert _measured_floor(_SHARE_A_PCT) in section, (
            "the coverage-blind parent ee382897 renders NO measured floor for the "
            "OFFER TABLE (a silent blank) -- this is the genuine RED-before the "
            "carry turns GREEN; at the build the byte-exact floor renders"
        )
        assert _COVERAGE_DIV in section

    def test_parent_red_before_not_measured_token_is_absent(self) -> None:
        """Not-measured token arm. GREEN here; RED at ee382897 (no coverage div).

        The honest-absent (coverage=None) OFFER TABLE. At the build it renders the
        VISIBLE ``not measured`` token; at the parent there is no coverage div at all,
        so this assert FAILS RED -- proving the parent shows a SILENT BLANK (the exact
        gap this sprint closes), two-sided with the GREEN here.
        """
        section = _compose_offer_only(coverage=None, coverage_expected=False)
        assert _NOT_MEASURED in section, (
            "the coverage-blind parent renders NO not-measured token -- the OFFER "
            "TABLE is a silent blank there; the carry makes the honest-absent state "
            "VISIBLE at the point of action"
        )
        assert _COVERAGE_DIV in section


def _measured_coverage(share: float) -> Any:
    """A MEASURED coverage carrier usable at BOTH commits.

    At the build, use the real ``AttributionCoverage`` frozen mirror. At the parent
    (where the class is absent) return a minimal duck-typed object exposing the two
    fields the render reads (``.status`` / ``.orphan_spend_share``); it is never
    consulted at the parent because ``_supported_kwargs`` drops the coverage kwarg
    there, but it keeps this helper importable at both commits without ImportError.
    """
    if AttributionCoverage is not None:
        return AttributionCoverage(
            status="measured",
            coverage_pct=1.0 - share,
            orphan_spend_share=share,
            total_spend=20000.0,
        )

    class _DuckCoverage:  # pragma: no cover -- only at the parent, never consulted
        status = "measured"
        orphan_spend_share = share

    return _DuckCoverage()


# =====================================================================
# INTERPLAY probes -- ONLY those that discriminate. The denied-vs-empty
# two-sided teeth themselves are CITED (Sprint-3 adversary file, not
# duplicated); the coverage-SPECIFIC interplay is authored fresh.
# =====================================================================


@_requires_build_symbols
@pytest.mark.usefixtures("_force_fallback")
class TestInterplayCoverageWithRefusals:
    """Coverage merging leaves the typed-refusal rails intact and coverage never
    fabricates a ceiling on a refused table -- the carry is orthogonal to refusals."""

    async def test_denied_offer_table_error_box_and_coverage_never_fabricates_ceiling(
        self, mock_resolution_context
    ) -> None:
        """INTERPLAY (S3 denial x coverage): a denied OFFER TABLE renders the typed
        error-box, and any coverage line riding the error section is ONLY the honest
        not-measured token -- NEVER a measured floor or a fabricated full-attribution
        ceiling on a REFUSED table.

        ADVERSARY FINDING F-DENIED-COV (filed as a defect-report in the verdict, NOT
        closed as a pass): the error-section render path
        (``_render_error_section`` -> ``_render_section_with_body`` ->
        ``_section_disclosure_html`` -> ``_coverage_line_html``) DOES emit a
        ``section-coverage`` div, because the error ``DataSection`` carries the
        default ``coverage=None`` -> renders ``spend attribution: not measured``. So a
        denied OFFER TABLE renders BOTH the error-box AND a not-measured coverage line
        (verified own-hands on the consumed HTML). This is BENIGN under the honest-floor
        ruling (the table IS refused; coverage genuinely was not measured; not-measured
        is truthful), but it was NOT an intended interplay and is surfaced as a
        near-miss: the assertion below grades the GROUND TRUTH (error-box present; the
        only coverage token allowed is the honest not-measured; NO measured floor, NO
        fabricated ceiling), so a future regression that leaked a MEASURED floor onto a
        refused table would bite here.

        The denied-vs-empty two-sided teeth themselves are CITED, not duplicated:
        ``test_insights_denied_render_teeth.py::TestDeniedVsEmptyRenderTeeth``.
        """
        from autom8_asana.errors import OperatorAccessDeniedError

        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, *_ = _make_workflow(
            offers=[o1],
            operator_insight_errors={
                _OFFER_TABLE_INSIGHT: OperatorAccessDeniedError("denied for test"),
            },
        )
        section = _offer_section(await _run_and_capture_html(wf))
        assert section != "", "the denied OFFER TABLE section must be present"

        # The typed error-box is VISIBLE (the refusal is not swallowed)...
        assert _ERROR_BOX in section, "a denied OFFER TABLE must render the typed error-box"
        # ...and coverage NEVER fabricates a ceiling / measured floor on a refused table.
        assert _measured_floor(_SHARE_A_PCT) not in section, (
            "a refused OFFER TABLE must NEVER render a measured coverage floor"
        )
        assert "≥" not in section, "a refused OFFER TABLE must render NO directional floor"
        assert "100%" not in section, "a refused OFFER TABLE must NOT fabricate a full ceiling"
        # The ONLY coverage token permitted on the error path is the honest unknown.
        offending = [
            line
            for line in section.splitlines()
            if _ATTRIBUTION_PREFIX in line and _NOT_MEASURED not in line
        ]
        assert not offending, (
            "the ONLY coverage token allowed on a refused table is the honest "
            f"not-measured; found a different attribution claim: {offending!r}"
        )

    def test_merge_first_observer_owns_coverage_two_sided(self) -> None:
        """INTERPLAY (merge ordering x coverage): ``_merge_batch_metas`` takes the
        FIRST sub-batch that OBSERVED a coverage decision, and collapses to honest-
        absent when none did -- two-sided, proving the first-observer rule is not a
        no-op.

        The presence suite (``test_merge_batch_metas_first_observer_owns_coverage`` /
        ``..._all_absent_collapses_to_honest_absent``) asserts EACH side alone. This
        arm asserts BOTH in one place and adds the discrimination that an EARLIER
        all-default meta does NOT steal ownership from a LATER observing sub-batch --
        the ordering bites on 'observed', not on position.
        """
        observed = OperatorBatchMeta(
            coverage=AttributionCoverage(status="measured", orphan_spend_share=_SHARE_A),
            coverage_expected=True,
        )
        empty = OperatorBatchMeta()
        # An earlier all-default meta does NOT own coverage; the later observer does.
        merged = _merge_batch_metas([empty, observed])
        assert merged.coverage is observed.coverage, (
            "the first sub-batch that OBSERVED a coverage decision owns the run's "
            "coverage -- an earlier all-default meta must not steal ownership"
        )
        assert merged.coverage_expected is True
        # Two-sided: all-absent collapses to honest-absent (the rule is not a no-op
        # that always yields the first element's coverage).
        collapsed = _merge_batch_metas([OperatorBatchMeta(), OperatorBatchMeta()])
        assert collapsed.coverage is None
        assert collapsed.coverage_expected is False
