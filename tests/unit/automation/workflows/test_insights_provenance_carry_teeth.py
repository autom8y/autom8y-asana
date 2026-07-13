"""Two-sided provenance-carry TEETH at the ACTUAL consumed render (Sprint 1).

provenance-to-the-human Sprint 1 (render-wiring), the GATE-1 render altitude.
This is the rite-disjoint numerical-adversary's DISJOINT day-one fixture pair for
the PO-CARRY family (contract ``.ledge/specs/PROVENANCE-CARRY-render-seam.md`` §6 /
§9.3). It is authored FRESH -- it does NOT extend the guard-author's PRESENCE suite
(``test_insights_provenance_carry.py``), which proves the guard EXISTS/FIRES but by
its own header explicitly does NOT author the discriminating stripped-RED/disclosed-
GREEN teeth. Building the guard AND grading whether it bites in one soul is the
FORBIDDEN merge; this file is the disjoint prove-half.

WHAT THIS PROVES (teeth, not presence)
--------------------------------------
Existence != SURVIVAL. A field in the payload proves nothing; the founder acts on
the RENDERED HTML the deck publishes. The predicate is proven at the composed HTML
string or not at all (THE BESPOKE TRAP, contract §0/§52). Every assertion below
reads ``compose_report``'s output on the REAL consumed path (operator batch payload
WITH meta -> workflow prefetch -> ``_fetch_table`` C2 fire-seam -> ``compose_report``),
never emission-side CI, never a green merge, never a payload field.

THE SOLE DISCRIMINATOR (the one signal nobody else checks)
----------------------------------------------------------
For a WEIGHTED section (SUMMARY carries the solid_scheds-family ``nsr_ncr`` column),
the render is one of exactly three mutually-exclusive shapes in the SUMMARY section:
  (D) DISCLOSED : ``<div class="section-provenance">weights <byte-exact-id> · as of
      <asOf>`` PLUS the weighted ``<td>`` cell renders.
  (S) STRIPPED-CAUGHT : ``<div class="error-box">...WeightsProvenanceAbsent`` with
      NO ``section-provenance`` badge and NO ``data-table`` -- the naked weighted
      number is STRUCTURALLY UNREPRESENTABLE (the C2 guard routed it to the typed
      rail BEFORE a success TableResult was built).
  (N) NAKED (the DEFECT) : the weighted ``<td>`` cell renders in a ``data-table``
      with NO ``section-provenance`` and NO ``error-box`` -- a provenance-free number
      the founder would trust. This is the exact silent-degradation the initiative
      kills; it is what the PARENT ``943c688d`` renders (proven below).

The cheap signals are ALL blind to (D) vs (S) vs (N): the file exists and is valid
HTML in all three; ``result.success``/row-count is identical for (D) and (N);
a byte-hash of the doc changes but proves nothing about trustworthiness. The
discriminator is the ``section-provenance`` badge / ``error-box`` in the SUMMARY
section -- read the GROUND TRUTH render string, never an inferred label.

TWO-SIDED, GENUINE-GAP (no defect injection anywhere)
-----------------------------------------------------
The RED-before is a REAL gap at the pre-render-wiring parent ``943c688d`` (the
render wiring is wholly absent there: no ``section-provenance`` render, no
``TableResult.weights_version`` field, no C2 guard, no ``OperatorBatchMeta``, no
``get_operator_insights_batch_with_meta_async`` -- verified by ``git grep`` at
authoring). It is NOT a defect injected into working code (that would be
G-THEATER). ``TestParentGenuineRedBefore`` drives a parent-portable altitude
(``compose_report``, which exists at BOTH commits) with weighted rows and asserts
BOTH arms; the file is copied verbatim into a ``943c688d`` scratch worktree where
both arms FAIL RED (disclosed badge absent + naked number rendered), and both pass
GREEN here. That is the two-sided genuine-gap proof.

A NAMED WORKFLOW PROPERTY (why the stripped arm refuses ONLY SUMMARY)
--------------------------------------------------------------------
The workflow short-circuits an offer to ``failed`` when ALL its tables fail (Step-C,
``workflow.py`` ``if tables_succeeded == 0``), in which case ``compose_report``
never runs. Serving the weighted-STRIPPED row to all four operator tables refuses
all four -> total failure -> NO render. So the stripped arms serve the stripped row
to ONLY the SUMMARY insight (``account_level_stats``) and unweighted rows to the
other three -- the C2 guard refuses only SUMMARY, the other three publish, and
``compose_report`` runs on the SUMMARY error-box. This is a real property of the
workflow, surfaced (not worked around): the render IS reached, and the SUMMARY
section carries the typed refusal.

CONSTRUCTION SEAMS
------------------
The neutral scaffolding (``_make_task`` / ``_make_workflow`` / ``_run_and_capture_html``)
is UPSTREAM test harness shared by the guard-author and the Sprint-3 denied-render
adversary. The discriminating ORACLE (the assertions) is authored fresh here, at the
render altitude, one step higher than the guard-author's ``TestC2GuardPresence``
(which stops at the internal ``TableResult``, not the composed HTML). The G1
version-skew fold is exercised through the REAL wire-envelope fold
(``distribute_per_office_meta``), not only the mocked meta side-channel, so the
byte-match is proven across the actual H5 fold.

Deliberately NOT duplicated from the guard-author's PRESENCE suite
------------------------------------------------------------------
- ``TestClientMetaCarry`` (H5 extractor happy path + declared-None) -- PRESENCE of
  the extractor; the teeth below drive the extractor through the composed render.
- ``TestWorkflowStateCarry`` (meta threaded into ``_operator_table_meta``) -- state
  PRESENCE; subsumed by the end-to-end render arms here.
- ``TestC2GuardPresence`` -- asserts on the internal ``TableResult`` (success/error_type)
  ONE altitude below the render; the STRIPPED arm here asserts the same fire-seam's
  effect at the CONSUMED HTML (error-box, no naked cell).
- ``TestWeightedDiscriminator`` (``_rows_are_weighted`` unit) -- the guard-author's
  discriminator unit test; NOT re-run (cited, not duplicated).
- ``TestBadgeRenderPresence`` -- renders the badge helpers in isolation + one
  ``compose_report`` badge-present/absent pair; the DISCLOSED arm here proves the
  same at the full end-to-end path with the BYTE-EXACT emitted id from the data
  plane and the two-sided stripped counterpart the presence suite omits.

The G1 mixed-version skew: the guard-author's PRESENCE suite proves
``distribute_per_office_meta`` / ``_merge_batch_metas`` RAISE on skew
(``test_version_skew_across_offices_raises_typed_g1`` /
``test_merge_cross_subbatch_skew_raises_typed_g1``). ``TestEdgeProbes`` below adds
the TWO-SIDED counterpart the presence suite omits: the SAME fold PASSES (returns
one token) on a single-version batch -- proving the skew raise bites ONLY on
divergence, not on every multi-office batch.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from autom8_asana.automation.workflows.insights.formatter import (
    InsightsReportData,
    TableResult,
    compose_report,
)
from autom8_asana.errors import OperatorAccessDeniedError

# Build-only symbols (added by the render-wiring commit 74dfc09d). Imported
# DEFENSIVELY so this file COLLECTS at the pre-render-wiring parent 943c688d, where
# they do not exist -- collection must not ImportError, or the parent RED-before
# arms below could never run to prove the genuine gap. When absent (parent), the
# build-only edge probes that USE them are skipped; the parent-portable
# ``TestParentGenuineRedBefore`` arms (which use NONE of these) still run and FAIL
# RED, which is the genuine two-sided gap proof. When present (build), everything runs.
try:
    from autom8_asana.clients.data._endpoints.operator import (
        OperatorBatchMeta,
        distribute_per_office_meta,
    )
    from autom8_asana.errors import OperatorBatchVersionSkewError

    _BUILD_SYMBOLS_PRESENT = True
except ImportError:  # pragma: no cover -- only at the pre-render-wiring parent
    OperatorBatchMeta = None
    distribute_per_office_meta = None
    OperatorBatchVersionSkewError = None
    _BUILD_SYMBOLS_PRESENT = False

# Neutral construction scaffolding shared with the guard-author + Sprint-3 adversary.
# The DISCRIMINATING oracle (assertions) is authored fresh in THIS file. These exist
# at BOTH commits (the Sprint-3 denied-render teeth file predates render-wiring).
from tests.unit.automation.workflows.test_insights_denied_render_teeth import (
    _run_and_capture_html,
)
from tests.unit.automation.workflows.test_insights_export import (
    _force_fallback,  # noqa: F401  -- module-scoped fixture, imported for usefixtures
    _make_task,
    _make_workflow,
)

# Build-only edge probes (version-skew fold) require the render-wiring symbols; skip
# them at the parent where those symbols are absent.
_requires_build_symbols = pytest.mark.skipif(
    not _BUILD_SYMBOLS_PRESENT,
    reason="render-wiring symbols (OperatorBatchMeta / distribute_per_office_meta / "
    "OperatorBatchVersionSkewError) absent at the pre-render-wiring parent 943c688d",
)

# -----------------------------------------------------------------------------
# Byte-match source of truth. This literal is asserted BYTE-IDENTICAL against the
# data plane's emitted CURRENT_WEIGHT_SCHEME_VERSION.
#
# CHOICE (stated per dispatch obligation #1): the emitted id is PINNED here as a
# literal WITH THIS CITATION, not read live from the data repo at fixture-setup
# time. Rationale: (a) the asana worktree has no import path to the data repo's
# solid_scheds_weights module (cross-repo), so a live read would be a brittle
# git-show subprocess; (b) the client-side mirror WEIGHTED_CONSUMER_METRICS is
# ALREADY pinned-with-citation in operator.py:57 under the same "revisited under a
# NAMED ruling, never silently widened" discipline (contract §3.1 / RULING R-WP-2);
# (c) the pin is itself GUARDED against silent drift by
# ``test_pinned_id_matches_data_plane_emitted_constant`` below, which reads the
# data repo origin/main constant via git-show and asserts byte-equality -- so the
# pin cannot rot undetected.
#
# CITATION (verified by ``git -C autom8y-data show origin/main:...`` at authoring):
# autom8y-data solid_scheds_weights.py line 66 declares the constant
# CURRENT_WEIGHT_SCHEME_VERSION as the Final str value pinned just below.
# -----------------------------------------------------------------------------
_EMITTED_VERSION = "2026-03-24-static-UNRATIFIED"

# A synthetic RATIFIED id (NOT containing the substring "UNRATIFIED") -- the RED
# side of the UNRATIFIED-derivation two-sided proof (PO-CARRY-2). This is a
# deliberately-broken INPUT the render must faithfully reflect (no hardcoded-on
# UNRATIFIED disclosure), NOT a defect in production code.
_SYNTHETIC_RATIFIED_ID = "2026-03-24-static-RATIFIED"

_FIXTURE_ASOF = "2026-07-13T00:00:00Z"

# The weighted section the operator batch's account_level_stats renders into.
_SUMMARY = "SUMMARY"
_SUMMARY_SLUG = "summary"
# The insight_name whose rows land in the SUMMARY table (tables.py TABLE_SPECS).
_SUMMARY_INSIGHT = "account_level_stats"
# The insight_name whose rows land in the OFFER TABLE section (S3 no-regression probe).
_OFFER_TABLE_INSIGHT = "offer_level_stats"

# A single weighted row: nsr_ncr is a WEIGHTED_CONSUMER_METRIC, so this row OWES a
# weights_version disclosure (WORM §1.3 never-hidden). The value 0.4242 renders as
# the percentage cell "0.42%" (formatter _FIELD_FORMAT nsr_ncr -> percentage).
_WEIGHTED_ROW: dict[str, Any] = {"nsr_ncr": 0.4242, "spend": 100}
_WEIGHTED_CELL = "0.42%"  # the rendered <td> for nsr_ncr=0.4242 (the NAKED signal)

# An UNWEIGHTED row: no weight-governed column, so it owes NO disclosure and MUST
# NOT trip the C2 guard (non-vacuity control).
_UNWEIGHTED_ROW: dict[str, Any] = {"spend": 100, "cpl": 50.0}

# Render markers -- literal substrings of the formatter's mutually-exclusive
# branches. These are the SOLE discriminator.
_PROVENANCE_BADGE = '<div class="section-provenance">'
_ERROR_BOX = '<div class="error-box">'
_DATA_TABLE = 'class="data-table"'
_WEIGHTS_ABSENT = "WeightsProvenanceAbsent"
_HARDCODED_APPT_WINDOW = "Scheduled appointments from the last 90 days."


def _summary_section(full_html: str) -> str:
    """Slice the SUMMARY <section> out of the composed report.

    The markers MUST be asserted WITHIN the SUMMARY section, not merely somewhere in
    the document -- another table legitimately rendering (or, in a leak, an error)
    must NOT satisfy the SUMMARY assertion.
    """
    return _section_by_slug(full_html, _SUMMARY_SLUG)


def _section_by_slug(full_html: str, slug: str) -> str:
    """Slice the <section id="{slug}"> ... </section> out of the composed report."""
    name_idx = full_html.find(f'id="{slug}"')
    if name_idx == -1:
        return full_html
    start = full_html.rfind("<section", 0, name_idx)
    end = full_html.find("</section>", name_idx)
    if start == -1 or end == -1:
        return full_html
    return full_html[start : end + len("</section>")]


def _make_workflow_summary_stripped(offers: list[Any]) -> Any:
    """Build a workflow that serves the weighted-STRIPPED row to SUMMARY ONLY.

    SUMMARY (account_level_stats) gets a weighted row with NO provenance (the C2
    guard refuses it); the other three operator insights get an unweighted row (they
    succeed) so the offer PUBLISHES and compose_report runs on the SUMMARY error-box.
    Parent-portable: uses only the base _make_workflow params present at BOTH commits
    (no operator_weights_version kwarg -- default meta is empty, i.e. no provenance).
    """
    wf, *_ = _make_workflow(
        offers=offers,
        operator_rows=[dict(_UNWEIGHTED_ROW)],  # default for the other 3 insights
        operator_insight_rows={_SUMMARY_INSIGHT: [dict(_WEIGHTED_ROW)]},  # SUMMARY: weighted
    )
    return wf


# =====================================================================
# PO-CARRY-1 + PO-CARRY-4 -- the render-seam byte-match, TWO-SIDED, at the
# ACTUAL consumed HTML on the REAL end-to-end path.
# =====================================================================


@pytest.mark.usefixtures("_force_fallback")
class TestRenderSeamByteMatchTwoSided:
    """Disclosed GREEN (byte-exact badge) vs stripped RED-CAUGHT (typed error-box)."""

    async def test_disclosed_weighted_summary_renders_byte_exact_badge(
        self, mock_resolution_context
    ) -> None:
        """GREEN (disclosed): the badge on the composed HTML BYTE-MATCHES the
        emitted id, and the asOf renders verbatim, driven end-to-end.

        Real path: operator batch serves a WEIGHTED row WITH provenance ->
        prefetch threads the meta -> _fetch_table attaches it -> compose_report
        renders the section-provenance badge. The rendered version substring is a
        LITERAL substring of the emitted CURRENT_WEIGHT_SCHEME_VERSION.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[dict(_WEIGHTED_ROW)],
            operator_weights_version=_EMITTED_VERSION,
            operator_synced_at=_FIXTURE_ASOF,
        )
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)

        # The badge is present in the SUMMARY section...
        assert _PROVENANCE_BADGE in summary, (
            "the disclosed weighted SUMMARY must render the section-provenance badge "
            "at the point of action"
        )
        # ...and its version substring BYTE-MATCHES the emitted id (byte-for-byte).
        assert _EMITTED_VERSION in summary, (
            "the rendered badge version must byte-match the emitted "
            f"CURRENT_WEIGHT_SCHEME_VERSION ({_EMITTED_VERSION!r})"
        )
        # The exact badge text, byte-for-byte (version + verbatim asOf together).
        assert (
            f'<div class="section-provenance">weights {_EMITTED_VERSION} · as of {_FIXTURE_ASOF}</div>'
            in summary
        ), "the badge must render 'weights <emitted-id> · as of <verbatim-asOf>' byte-exact"
        # The weighted number still renders (disclosure ADDS a badge, hides nothing).
        assert _WEIGHTED_CELL in summary
        assert _DATA_TABLE in summary
        # And it is NOT the refusal shape.
        assert _ERROR_BOX not in summary

    async def test_stripped_weighted_summary_is_caught_never_naked(
        self, mock_resolution_context
    ) -> None:
        """RED-CAUGHT (stripped): a weighted number arriving WITHOUT provenance is
        routed to the typed error-box at the render -- NEVER a naked number, NEVER
        the badge.

        This is the predicate's RED side. The SAME weighted row, served with the
        provenance STRIPPED (no weights_version -> the seam-drop reproduced), drives
        the REAL C2 fire-seam in _fetch_table BEFORE the success TableResult is
        built, so the composed SUMMARY section shows the typed WeightsProvenanceAbsent
        error-box and the weighted <td> cell is STRUCTURALLY UNREPRESENTABLE. A
        weighted number rendering plainly here = the exact silent-degradation this
        initiative kills = the fixture FAILS.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf = _make_workflow_summary_stripped([o1])
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)

        # The typed refusal is VISIBLE at the point of action...
        assert _ERROR_BOX in summary, (
            "a stripped weighted table must render the typed error-box at the consumed render"
        )
        assert _WEIGHTS_ABSENT in summary, (
            "the error-box must carry the typed WeightsProvenanceAbsent discriminant "
            "(non-null-coercible, distinguishable from empty)"
        )
        # ...and the naked number is UNREPRESENTABLE: no badge, no data-table, no cell.
        assert _PROVENANCE_BADGE not in summary, (
            "a stripped table must NOT render a provenance badge (there is none)"
        )
        assert _DATA_TABLE not in summary, (
            "a stripped weighted table must NOT render a data-table -- the naked "
            "number is structurally unrepresentable"
        )
        assert _WEIGHTED_CELL not in summary, (
            "the weighted number must NOT render naked -- this is the silent "
            "degradation the initiative kills"
        )


# =====================================================================
# PO-CARRY-2 -- UNRATIFIED derivation is faithful at the render, TWO-SIDED.
# The disclosure is DERIVED from the id (substring), never hardcoded-on.
# =====================================================================


@pytest.mark.usefixtures("_force_fallback")
class TestUnratifiedDerivationTwoSided:
    """The id's UNRATIFIED substring drives the disclosure -- proven both ways."""

    async def test_unratified_id_renders_the_unratified_token(
        self, mock_resolution_context
    ) -> None:
        """GREEN: an id CONTAINING 'UNRATIFIED' renders the UNRATIFIED token in the
        badge (the id itself is the disclosure source)."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[dict(_WEIGHTED_ROW)],
            operator_weights_version=_EMITTED_VERSION,
            operator_synced_at=_FIXTURE_ASOF,
        )
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)
        assert "UNRATIFIED" in summary
        assert _EMITTED_VERSION in summary

    async def test_ratified_id_does_not_render_unratified(self, mock_resolution_context) -> None:
        """RED side (deliberately-broken INPUT): a synthetic id NOT containing
        'UNRATIFIED' must NOT render the UNRATIFIED token -- proving the disclosure
        is DERIVED from the carried id, not hardcoded-on.

        A hardcoded-on disclosure would leak 'UNRATIFIED' onto a RATIFIED id here
        (the fixture would FAIL) -- the two-sidedness proves the derivation bites on
        the id substring, per contract §1.2.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[dict(_WEIGHTED_ROW)],
            operator_weights_version=_SYNTHETIC_RATIFIED_ID,
            operator_synced_at=_FIXTURE_ASOF,
        )
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)
        # The badge renders the (RATIFIED) id verbatim -- the carry is faithful...
        assert _SYNTHETIC_RATIFIED_ID in summary
        assert _PROVENANCE_BADGE in summary
        # ...but the UNRATIFIED token is ABSENT (the substring is not in the id).
        assert "UNRATIFIED" not in summary, (
            "a RATIFIED id must NOT render the UNRATIFIED disclosure -- the "
            "disclosure is derived from the id substring, not hardcoded"
        )


# =====================================================================
# PO-CARRY-3 -- asOf renders the query-date stamp, not the hardcoded window
# (R4 / DEFER-6), TWO-SIDED at the composed subtitle.
# =====================================================================


@pytest.mark.usefixtures("_force_fallback")
class TestAsOfDisciplineTwoSided:
    """asOf disclosed verbatim; asOf-unknown DISCLOSED, never silent (WORM §4.2)."""

    async def test_disclosed_asof_stamps_subtitle_verbatim(self, mock_resolution_context) -> None:
        """GREEN: a weighted SUMMARY carrying synced_at renders the asOf verbatim on
        the subtitle AND the badge -- the live query date rides the snapshot-grain
        section (the hardcoded window alone is no longer the whole subtitle)."""
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[dict(_WEIGHTED_ROW)],
            operator_weights_version=_EMITTED_VERSION,
            operator_synced_at=_FIXTURE_ASOF,
        )
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)
        # asOf renders verbatim (byte-for-byte) on the section.
        assert _FIXTURE_ASOF in summary
        # The subtitle carries the live stamp "· as of <asOf>" (R4/DEFER-6).
        assert f"· as of {_FIXTURE_ASOF}" in summary, (
            "the snapshot-grain subtitle must carry the live asOf query-date stamp"
        )

    async def test_weighted_asof_unknown_is_disclosed_not_silent(
        self, mock_resolution_context
    ) -> None:
        """GREEN (disclosed ignorance): a WEIGHTED SUMMARY with synced_at=None
        renders 'as of unknown' in the badge -- DISCLOSED ignorance, never silence
        (contract §4c / WORM §4.2). Silence on a snapshot-grain number is the defect.

        Two-sided against the disclosed-asOf arm above: same weighted table, asOf
        present -> verbatim ISO; asOf absent -> the literal 'unknown', never a blank.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[dict(_WEIGHTED_ROW)],
            operator_weights_version=_EMITTED_VERSION,
            operator_synced_at=None,  # asOf unknown on a WEIGHTED table
        )
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)
        assert _PROVENANCE_BADGE in summary
        assert _EMITTED_VERSION in summary
        # asOf ignorance is DISCLOSED, never omitted.
        assert "as of unknown" in summary, (
            "a weighted table with no asOf must DISCLOSE 'as of unknown', never "
            "silently omit the query-date stamp (§4c)"
        )


# =====================================================================
# PO-C3 -- no weight value moves through the carry (byte-identity at the render).
# Disclosure ADDS a badge; it perturbs NO number.
# =====================================================================


class TestNoWeightValueMovesAtRender:
    """The disclosed cell value == the raw payload value (Reading-A / C3)."""

    def test_disclosure_adds_badge_perturbs_no_number(self) -> None:
        """The weighted <td> cell renders BYTE-IDENTICAL with and without the
        disclosure badge -- proving the carry adds a disclosure surface only and
        moves no value (contract §5 / Reading-A).

        Altitude note: this asserts the render-side C3 (the disclosure does not
        perturb the rendered number). The upstream numeric-evaluation byte-identity
        (|delta|=0 on solid_scheds evaluate()/get_expression() over the R-WP-4
        sweep) is DISCHARGED IN THE DATA REPO (composite.py is UNTOUCHED by this
        render-wiring commit -- verified: the asana worktree carries no metric
        evaluation code, and the emission-side build-receipt §12.7 records the
        data-repo PO-C3 test test_no_weight_value_moves_through_the_carry). This
        rite's render surface owns only the render-side C3; the numeric byte-identity
        is not re-runnable here and is not this seam's obligation to re-execute.
        """
        # Disclosed: badge present.
        disclosed = compose_report(
            _report_data(
                {
                    _SUMMARY: TableResult(
                        table_name=_SUMMARY,
                        success=True,
                        data=[dict(_WEIGHTED_ROW)],
                        row_count=1,
                        weights_version=_EMITTED_VERSION,
                        synced_at=_FIXTURE_ASOF,
                    )
                }
            )
        )
        disclosed_summary = _summary_section(disclosed)

        # Bare: the SAME row rendered without a badge (an unweighted-shaped success,
        # bypassing the C2 guard at the formatter altitude purely to compare the
        # NUMBER's rendering -- this is a value-comparison probe, not a render the
        # C2 guard would ever emit for a weighted table).
        bare = compose_report(
            _report_data(
                {
                    _SUMMARY: TableResult(
                        table_name=_SUMMARY,
                        success=True,
                        data=[dict(_WEIGHTED_ROW)],
                        row_count=1,
                    )
                }
            )
        )
        bare_summary = _summary_section(bare)

        # The rendered weighted cell is byte-identical either way: no value moved.
        assert _WEIGHTED_CELL in disclosed_summary
        assert _WEIGHTED_CELL in bare_summary
        # And the version id rendered is EXACTLY the emitted id (no rename, C3).
        assert _EMITTED_VERSION in disclosed_summary
        assert _PROVENANCE_BADGE not in bare_summary  # the only difference: the badge


# =====================================================================
# Byte-match PIN guard -- the pinned emitted id cannot rot undetected.
# =====================================================================


class TestPinnedIdMatchesDataPlane:
    """The pinned _EMITTED_VERSION byte-matches the data plane's live constant."""

    def test_pinned_id_matches_data_plane_emitted_constant(self) -> None:
        """Read the data repo origin/main CURRENT_WEIGHT_SCHEME_VERSION via git-show
        and assert the pin above byte-matches it. This is the GATE-2 equivalence
        re-run (PO-CARRY-1): the rendered token (pinned + guarded here) is proven
        byte-identical to the EMITTED token at its authoritative source.

        If the data repo is not reachable from this environment, the test SKIPS with
        an honest reason (never a silent pass) -- the pin's drift-guard is best-effort
        cross-repo, and the render-seam byte-match above stands on the pinned literal
        regardless. The skip is a disclosed gap, not a green-washed absence.
        """
        import subprocess
        from pathlib import Path

        # Locate the sibling autom8y-data repo (fleet layout: .../repos/autom8y-data).
        here = Path(__file__).resolve()
        data_repo = None
        for parent in here.parents:
            candidate = parent / "autom8y-data"
            if (candidate / ".git").exists():
                data_repo = candidate
                break
        if data_repo is None:
            pytest.skip(
                "autom8y-data repo not locatable from this worktree -- cross-repo "
                "byte-match drift-guard skipped (disclosed gap, not a silent pass); "
                "the pinned literal + render-seam byte-match above still hold"
            )

        try:
            out = subprocess.run(
                [
                    "git",
                    "-C",
                    str(data_repo),
                    "show",
                    "origin/main:src/autom8_data/analytics/core/metrics/solid_scheds_weights.py",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        except (subprocess.SubprocessError, OSError) as exc:  # pragma: no cover
            pytest.skip(
                f"could not read data repo origin/main constant ({exc}); cross-repo "
                "drift-guard skipped (disclosed gap, not a silent pass)"
            )

        # Extract the emitted constant literal.
        emitted: str | None = None
        for line in out.stdout.splitlines():
            if line.startswith("CURRENT_WEIGHT_SCHEME_VERSION"):
                # The constant line encloses the id in double quotes; take
                # the first double-quoted token as the emitted id.
                if '"' in line:
                    emitted = line.split('"')[1]
                break
        assert emitted is not None, (
            "CURRENT_WEIGHT_SCHEME_VERSION not found in the data repo origin/main "
            "solid_scheds_weights.py -- the byte-match source moved; re-anchor the pin"
        )
        assert emitted == _EMITTED_VERSION, (
            "the pinned _EMITTED_VERSION has DRIFTED from the data plane's emitted "
            f"constant: pinned={_EMITTED_VERSION!r} emitted={emitted!r}. The render "
            "would show a stale id -- re-pin under a NAMED ruling (contract §3.1)"
        )


# =====================================================================
# EDGE PROBES that DISCRIMINATE (non-vacuity + no-regression).
# =====================================================================


@pytest.mark.usefixtures("_force_fallback")
class TestEdgeProbes:
    """The guard bites ONLY where it should; unweighted + denied are unaffected."""

    async def test_unweighted_table_renders_no_badge_no_refusal(
        self, mock_resolution_context
    ) -> None:
        """NON-VACUITY: an UNWEIGHTED table with NO provenance renders fine -- no
        badge, no error-box. This proves the C2 guard bites ONLY on the
        weighted-stripped case, not on every provenance-absent table. A guard that
        fired here would be over-eager; a guard that never fired anywhere would be
        vacuous. This is the no-defect variant that MUST pass.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[dict(_UNWEIGHTED_ROW)],  # no weight-governed column
            operator_weights_version=None,  # and no provenance -- but that is FINE
        )
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)
        # Renders normally: a data-table with the unweighted cells...
        assert _DATA_TABLE in summary
        # ...NO provenance badge (nothing weighted to disclose)...
        assert _PROVENANCE_BADGE not in summary
        # ...and NO refusal (the guard did NOT over-fire).
        assert _ERROR_BOX not in summary
        assert _WEIGHTS_ABSENT not in summary

    @_requires_build_symbols
    def test_version_skew_fold_raises_but_single_version_passes(self) -> None:
        """G1 TWO-SIDED at the REAL wire-envelope fold: a batch whose offices
        DISAGREE on weights_version raises the typed OperatorBatchVersionSkewError;
        the SAME fold on a single-version batch PASSES (returns one token). This
        proves the skew raise bites ONLY on divergence -- not on every multi-office
        batch (the guard-author's presence suite proves only the raise side).
        """
        # RED arm: two offices, DISTINCT ids -> typed raise (the divergent state a
        # single META token would LIE for).
        skew_body = _wire_envelope(
            [
                ("+17705753101", [dict(_WEIGHTED_ROW)], "A"),
                ("+17705753102", [dict(_WEIGHTED_ROW)], "B"),
            ]
        )
        with pytest.raises(OperatorBatchVersionSkewError) as exc:
            distribute_per_office_meta(skew_body)
        assert sorted(exc.value.versions) == ["A", "B"]

        # GREEN arm (the no-defect variant): two offices, SAME id -> one token, no raise.
        agree_body = _wire_envelope(
            [
                ("+17705753101", [dict(_WEIGHTED_ROW)], _EMITTED_VERSION),
                ("+17705753102", [dict(_WEIGHTED_ROW)], _EMITTED_VERSION),
            ]
        )
        meta = distribute_per_office_meta(agree_body)
        assert isinstance(meta, OperatorBatchMeta)
        assert meta.weights_version == _EMITTED_VERSION

    async def test_denied_table_still_wins_the_s3_denial_rail_no_regression(
        self, mock_resolution_context
    ) -> None:
        """NO-REGRESSION: a per-insight route DENIAL (Sprint-3's typed rail) still
        renders the denial error-box for that table -- the Sprint-1 C2 guard does
        NOT hijack or regress the pre-existing denial path. The denied insight's
        table renders a VISIBLE typed error-box (the S3 rail), distinct from a
        genuinely-empty section.

        This is the interplay probe: the Sprint-3 denial fixture (the disjoint
        adversary's earlier day-one teeth) is unmodified and still bites.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_rows=[dict(_UNWEIGHTED_ROW)],
            operator_insight_errors={
                _OFFER_TABLE_INSIGHT: OperatorAccessDeniedError(
                    "offer table denied", reason="route_denied"
                )
            },
        )
        html = await _run_and_capture_html(wf)
        # The OFFER TABLE section carries the denial error-box (S3 rail intact).
        offer_section = _section_by_slug(html, "offer-table")
        assert _ERROR_BOX in offer_section, (
            "a route-denied table must still render the S3 typed error-box -- the "
            "Sprint-1 C2 guard must not regress the Sprint-3 denial rail"
        )
        # And it is the DENIAL error, not the C2 WeightsProvenanceAbsent (no hijack).
        assert _WEIGHTS_ABSENT not in offer_section


# =====================================================================
# GENUINE RED-BEFORE at the parent 943c688d (pre-render-wiring).
# =====================================================================


@pytest.mark.usefixtures("_force_fallback")
class TestParentGenuineRedBefore:
    """The two arms that FAIL RED at the parent 943c688d (the gap was REAL).

    These drive the SAME real consumed path (execute_async -> _fetch_table ->
    compose_report, captured via _run_and_capture_html) with a WEIGHTED row. Both
    arms pass GREEN here; when this file is copied verbatim into a 943c688d scratch
    worktree BOTH arms FAIL RED:

      - DISCLOSED arm: at parent, TableResult carries no weights_version field, the
        formatter has no _provenance_line_html, and the workflow has no
        _operator_table_meta -- so NO section-provenance badge renders. The badge
        assertion FAILS (the drop was live).
      - STRIPPED arm: at parent, there is no C2 guard in _fetch_table -- a weighted
        number served without provenance renders NAKED (the 0.42% <td> cell in a
        data-table, no error-box). The "caught, not naked" assertion FAILS (naked
        numbers rendered, no guard).

    Altitude chosen: _run_and_capture_html + compose_report, which EXIST at BOTH
    commits (the Sprint-3 denied-render teeth file predates this render-wiring
    commit). The parent _make_workflow lacks operator_weights_version /
    operator_synced_at kwargs -- the DISCLOSED arm therefore feature-detects the
    kwarg (present at build -> badge renders GREEN; absent at parent -> badge cannot
    render -> RED) and lets the ASSERT carry the arm. The STRIPPED arm needs no meta
    kwargs at all (it serves the SUMMARY-only weighted-stripped row and lets the
    naked-vs-caught assert carry it). This is the REAL consumed path, not a synthetic
    bypass: the render string the founder acts on is what is graded.
    """

    @staticmethod
    def _make_workflow_disclosed_portable(offers: list[Any]) -> Any:
        """Build a workflow serving a weighted row WITH provenance iff the harness
        supports the kwarg (build) -- else plain weighted rows (parent). Portable
        across both commits so the SAME test body runs at each; the render output
        carries the arm (at parent no badge can render regardless of kwargs).
        """
        sig = inspect.signature(_make_workflow)
        if "operator_weights_version" in sig.parameters:
            wf, *_ = _make_workflow(
                offers=offers,
                operator_rows=[dict(_WEIGHTED_ROW)],
                operator_weights_version=_EMITTED_VERSION,
                operator_synced_at=_FIXTURE_ASOF,
            )
        else:
            wf, *_ = _make_workflow(offers=offers, operator_rows=[dict(_WEIGHTED_ROW)])
        return wf

    async def test_disclosed_arm_badge_present(self, mock_resolution_context) -> None:
        """RED at parent 943c688d / GREEN at build 74dfc09d.

        A weighted SUMMARY served WITH provenance must render the section-provenance
        badge byte-matching the emitted id. At parent no badge exists -> RED.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf = self._make_workflow_disclosed_portable([o1])
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)
        assert _PROVENANCE_BADGE in summary, (
            "GENUINE RED-BEFORE: at the pre-render-wiring parent 943c688d the badge "
            "is structurally absent (the drop was live); it renders only at the "
            "render-wiring build"
        )
        assert _EMITTED_VERSION in summary

    async def test_stripped_arm_caught_not_naked(self, mock_resolution_context) -> None:
        """RED at parent 943c688d / GREEN at build 74dfc09d.

        A weighted SUMMARY served WITHOUT provenance must be CAUGHT (typed error-box,
        no naked cell). At parent there is no C2 guard -> the weighted number renders
        NAKED (0.42% in a data-table) -> RED. The SUMMARY-only stripped construction
        (unweighted rows for the other three insights) keeps the offer publishing at
        BOTH commits so compose_report always runs.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf = _make_workflow_summary_stripped([o1])
        html = await _run_and_capture_html(wf)
        summary = _summary_section(html)
        # Caught: the typed refusal is present and the naked number is unrepresentable.
        assert _ERROR_BOX in summary and _WEIGHTS_ABSENT in summary, (
            "GENUINE RED-BEFORE: at the pre-render-wiring parent 943c688d there is no "
            "C2 guard, so a weighted number without provenance renders NAKED (no "
            "error-box); the guard exists only at the render-wiring build"
        )
        assert _WEIGHTED_CELL not in summary, (
            "GENUINE RED-BEFORE: at parent the weighted number renders naked in a "
            "data-table -- the exact silent degradation the guard kills"
        )


# --- Local helpers (neutral scaffolding) ---


def _report_data(table_results: dict[str, TableResult]) -> InsightsReportData:
    """Build InsightsReportData with the given table_results (others absent)."""
    import time

    return InsightsReportData(
        business_name="Acme",
        office_phone="+17705753103",
        vertical="chiropractic",
        table_results=table_results,
        started_at=time.monotonic(),
        version="test",
    )


def _wire_envelope(
    offices: list[tuple[str, list[dict[str, Any]], str | None]],
) -> dict[str, Any]:
    """Build a REAL operator batch wire envelope for distribute_per_office_meta.

    Each tuple is (phone, rows, weights_version). This mirrors the data plane's
    per-office SuccessResponse[BatchInsightResponse] shape (data.results[].data.meta),
    so the fold is exercised on the ACTUAL wire structure, not a mocked side-channel.
    """
    results = []
    for phone, rows, version in offices:
        meta: dict[str, Any] = {}
        if version is not None:
            meta["weights_version"] = version
        results.append(
            {
                "phone": phone,
                "status": "success",
                "data": {"result_type": "result", "data": rows, "meta": meta},
            }
        )
    return {"data": {"insight": "account_level_stats", "results": results}}
