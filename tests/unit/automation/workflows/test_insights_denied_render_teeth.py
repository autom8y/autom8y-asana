"""Render-level two-sided teeth for the typed-refusal-at-render guard.

provenance-to-the-human Sprint-3 (typed-refusal-at-render), the GATE-1 render
altitude. This is the numerical-adversary's DISJOINT day-one fixture pair,
authored FRESH (it does NOT reuse the guard-author's repaired counter-altitude
oracle at ``test_insights_export.py::TestPartialAllowlist``, which asserts ONLY
``tables_failed == 1`` and explicitly delegates the render proof here).

WHAT THIS PROVES (teeth, not presence)
--------------------------------------
The founder acts on the RENDERED HTML the deck publishes, not on the internal
``TableResult``. The guard has teeth ONLY if, at that point of action, a
per-table operator-route DENIAL renders a VISIBLE typed error-box that is
STRUCTURALLY DISTINCT from a genuinely-empty table's "No data" section. The
pre-guard defect (parent 08d9800d) is that a denial ``continue``-skipped the
table -> absent key -> ``.get(office, [])`` null-coerced to ``[]`` ->
``TableResult(success=True, data=[])`` -> an EMPTY-section render, structurally
indistinguishable from real emptiness (the C2 drift).

TWO-SIDED (bites ONLY on the defect)
------------------------------------
- DENIED ARM: ``get_operator_insights_batch_async`` raises
  ``OperatorAccessDeniedError`` for the OFFER TABLE insight (the REAL write-path
  arm at ``_prefetch_operator_tables``). Drives the REAL path
  (_prefetch write-arm -> _fetch_table fire-seam -> compose_report) and asserts
  the composed HTML for OFFER TABLE carries the error-box marker AND NOT the
  empty marker. This ASSERTION TRIPS RED at parent 08d9800d (the denial renders
  empty there) and passes GREEN at the guard commit.
- EMPTY ARM: the SAME OFFER TABLE insight genuinely served with ZERO rows (no
  error). The composed HTML carries the empty marker AND NOT the error-box.
  This arm PASSES at BOTH commits -> proof the fixture bites on the DEFECT, not
  on emptiness (a no-teeth fixture would flip here too).

The RED fires on the REAL code path a denied input traverses (the write-path
``except OperatorAccessDeniedError`` arm + the read-path ordering in
``_fetch_table``), NOT on a synthetic ``TableResult(success=False)`` handed
straight to the formatter -- that would bypass the fire-seam and never go RED at
parent (the formatter is unchanged between the two commits; the defect lives in
``_fetch_table``'s ordering, so the fixture MUST drive it).

DISCRIMINATOR (the one signal nobody else checks)
-------------------------------------------------
error-box (``<div class="error-box">``) vs empty-section (``<p class="empty">``)
in the OFFER TABLE section of the CONSUMED HTML. The cheap signals are blind:
row-count is 0 in BOTH the denied and the empty case; the file exists /
uploads / is valid HTML in BOTH; ``result.success`` at the internal altitude is
what the guard-author's oracle checks -- this fixture reads the RENDER, one
altitude higher.

Construction seams are the guard-author's OWN test harness helpers
(``_make_task`` / ``_make_workflow`` / ``_enumerate_and_execute``) and the
shared ``mock_resolution_context`` conftest fixture -- these are UPSTREAM
neutral scaffolding, not the repaired oracle's assertions. The discriminating
assertions below are authored fresh at the render altitude.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from autom8_asana.errors import OperatorAccessDeniedError

# Reuse ONLY the neutral construction scaffolding from the guard-author's test
# module (task/workflow builders + the enumerate->execute driver). The
# discriminating oracle (assertions) is authored fresh in THIS file.
from tests.unit.automation.workflows.test_insights_export import (
    _enumerate_and_execute,
    _force_fallback,  # noqa: F401  -- module-scoped fixture, imported for usefixtures
    _make_task,
    _make_workflow,
)

# The insight_name the OFFER TABLE spec fetches (tables.py TABLE_SPECS). Denying
# THIS insight denies exactly the OFFER TABLE at the write path.
_OFFER_TABLE_INSIGHT = "offer_level_stats"
_OFFER_TABLE_NAME = "OFFER TABLE"

# The two non-overlapping render markers -- the SOLE discriminator. These are
# literal substrings of the formatter's two mutually-exclusive branches
# (formatter.py _render_error_section vs _render_empty_section).
_ERROR_BOX_MARKER = '<div class="error-box">'
_EMPTY_SECTION_MARKER = '<p class="empty">'

# compose_report is imported at module scope in the workflow; spy it THERE so we
# capture the EXACT consumed HTML string the deck publishes (report_content),
# driven by the real path -- independent of upload/dry-run plumbing.
_COMPOSE_SPY_PATH = "autom8_asana.automation.workflows.insights.workflow.compose_report"


def _offer_table_section_html(full_html: str) -> str:
    """Slice the OFFER TABLE <section> out of the composed report.

    The markers must be asserted WITHIN the OFFER TABLE section, not merely
    somewhere in the document -- another table legitimately rendering empty (or,
    in a leak scenario, an error) must NOT satisfy the OFFER TABLE assertion.
    Sections are ``<section ...> ... </section>``; we return the section whose
    header carries the OFFER TABLE name. Falls back to the whole document only
    if the section cannot be isolated (which itself would fail the marker
    asserts and surface the problem).
    """
    # Section headers render the table name via _render_section_with_body; find
    # the OFFER TABLE occurrence and bound it by the enclosing <section>..</section>.
    name_idx = full_html.find(_OFFER_TABLE_NAME)
    if name_idx == -1:
        return full_html
    start = full_html.rfind("<section", 0, name_idx)
    end = full_html.find("</section>", name_idx)
    if start == -1 or end == -1:
        return full_html
    return full_html[start : end + len("</section>")]


async def _run_and_capture_html(wf: Any) -> str:
    """Drive the REAL path and capture the exact consumed HTML (report_content).

    Spies the module-level compose_report with the REAL function (wraps, does not
    replace) so the composition is genuine; returns the composed HTML string that
    becomes the uploaded attachment bytes.
    """
    from autom8_asana.automation.workflows.insights import workflow as _wf_mod

    real_compose = _wf_mod.compose_report
    captured: dict[str, str] = {}

    def _spy(report_data: Any) -> str:
        html = str(real_compose(report_data))
        captured["html"] = html
        return html

    with patch(_COMPOSE_SPY_PATH, side_effect=_spy):
        result = await _enumerate_and_execute(wf)

    # The offer must still publish (per-table denial does NOT abort the offer) --
    # otherwise compose_report never runs and the render is unproven.
    assert result.succeeded == 1, (
        "offer did not publish -- a per-table denial must not abort the offer; "
        "the render is unproven if compose_report never ran"
    )
    assert "html" in captured, "compose_report was never invoked on the real path"
    return captured["html"]


@pytest.mark.usefixtures("_force_fallback")
class TestDeniedVsEmptyRenderTeeth:
    """Two-sided teeth at the CONSUMED render (denied error-box vs empty section)."""

    async def test_denied_offer_table_renders_typed_error_box_not_empty(
        self, mock_resolution_context
    ) -> None:
        """DENIED ARM -- RED at parent 08d9800d, GREEN at guard c295a99b.

        A route denial on the OFFER TABLE insight must render a VISIBLE typed
        error-box in the OFFER TABLE section of the consumed HTML, NOT an empty
        section. At parent this trips RED (the denial null-coerces to an empty
        render); at the guard it passes GREEN (the typed marker routes through
        the error channel).
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_insight_errors={
                _OFFER_TABLE_INSIGHT: OperatorAccessDeniedError(
                    "offer_level_stats not on the operator allowlist for O"
                )
            },
        )

        html = await _run_and_capture_html(wf)
        section = _offer_table_section_html(html)

        # TEETH: the founder sees a typed error-box for the denied table ...
        assert _ERROR_BOX_MARKER in section, (
            "DENIED render has NO error-box in the OFFER TABLE section -- the "
            "denial is indistinguishable from empty at the point of action "
            "(the C2 drift; this is the pre-guard defect at parent 08d9800d)"
        )
        # ... and it is NOT rendered as a genuinely-empty section.
        assert _EMPTY_SECTION_MARKER not in section, (
            "DENIED render shows the empty-section marker in the OFFER TABLE "
            "section -- a denial is being masked as real emptiness"
        )
        # The typed error_type reaches the surface (not a bare/blank box).
        assert "OperatorAccessDenied" in section, (
            "the typed error_type is absent from the rendered error-box -- the "
            "refusal is not typed at the point of action"
        )

    async def test_genuinely_empty_offer_table_renders_empty_not_error_box(
        self, mock_resolution_context
    ) -> None:
        """EMPTY ARM -- GREEN at BOTH commits (proves bite-only-on-defect).

        The SAME OFFER TABLE insight served with ZERO rows (no error) must
        render the empty-section marker and NOT the error-box. If this arm
        flipped between the two commits, the fixture would be matching on shape
        (a no-teeth fixture); it must pass identically at parent and guard.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            # OFFER TABLE served genuinely EMPTY; the other 3 tables serve rows.
            operator_insight_rows={_OFFER_TABLE_INSIGHT: []},
        )

        html = await _run_and_capture_html(wf)
        section = _offer_table_section_html(html)

        # Positive control: genuine emptiness renders the empty marker ...
        assert _EMPTY_SECTION_MARKER in section, (
            "genuinely-empty OFFER TABLE did NOT render the empty-section marker"
        )
        # ... and NOT the error-box (no false typed-refusal on real emptiness).
        assert _ERROR_BOX_MARKER not in section, (
            "genuinely-empty OFFER TABLE rendered an error-box -- a false typed "
            "refusal on real emptiness (the fixture would be matching on shape)"
        )

    async def test_denied_and_empty_renders_are_structurally_distinct(
        self, mock_resolution_context
    ) -> None:
        """DISTINCTNESS -- the two arms produce NON-OVERLAPPING markers.

        Asserts the discriminator is a real structural split, not two strings of
        the same render class: the denied OFFER TABLE section contains the
        error-box marker and NOT the empty marker; the empty OFFER TABLE section
        contains the empty marker and NOT the error-box. XOR on both markers.
        This is what makes the canary two-sided rather than one-sided.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")

        wf_denied, _, _, _ = _make_workflow(
            offers=[o1],
            operator_insight_errors={_OFFER_TABLE_INSIGHT: OperatorAccessDeniedError("denied")},
        )
        wf_empty, _, _, _ = _make_workflow(
            offers=[o1],
            operator_insight_rows={_OFFER_TABLE_INSIGHT: []},
        )

        denied_section = _offer_table_section_html(await _run_and_capture_html(wf_denied))
        empty_section = _offer_table_section_html(await _run_and_capture_html(wf_empty))

        def _discriminator(section: str) -> str:
            """Reduce a section to its render class: 'error' | 'empty' | 'neither' | 'both'."""
            has_error = _ERROR_BOX_MARKER in section
            has_empty = _EMPTY_SECTION_MARKER in section
            if has_error and not has_empty:
                return "error"
            if has_empty and not has_error:
                return "empty"
            return "both" if (has_error and has_empty) else "neither"

        denied_class = _discriminator(denied_section)
        empty_class = _discriminator(empty_section)

        # Denied renders EXACTLY the typed error-box; empty renders EXACTLY the
        # empty section -- each is a clean single-marker class (not both/neither).
        assert denied_class == "error", (
            f"denied OFFER TABLE render class is {denied_class!r}, expected 'error'"
        )
        assert empty_class == "empty", (
            f"empty OFFER TABLE render class is {empty_class!r}, expected 'empty'"
        )
        # The two artifacts are structurally distinct on the sole discriminator.
        assert denied_class != empty_class


@pytest.mark.usefixtures("_force_fallback")
class TestDeniedRenderNonVacuityAndEdges:
    """Non-vacuity (S5) + edge probes the guard MUST catch (property/adversarial)."""

    async def test_no_denial_no_error_box_anywhere_non_vacuity(
        self, mock_resolution_context
    ) -> None:
        """NON-VACUITY (S5) -- with NOTHING denied, the guard emits NO error-box.

        Proves the error-box in the denied arm is CAUSED by the denial, not an
        artifact the renderer always emits. A synthetic case the guard must NOT
        fire on: all 4 tables serve rows -> the consumed HTML contains ZERO
        error-box markers. If an error-box appeared here, the denied-arm GREEN
        would be vacuous (the marker would be present regardless of the defect).
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(offers=[o1])  # every table serves default rows

        html = await _run_and_capture_html(wf)

        assert _ERROR_BOX_MARKER not in html, (
            "an error-box rendered with NOTHING denied -- the denied-arm proof "
            "would be vacuous (the marker is not caused by the denial)"
        )

    async def test_denial_does_not_leak_error_into_other_tables(
        self, mock_resolution_context
    ) -> None:
        """EDGE -- a denial for ONE table must not leak an error render into others.

        Exactly ONE error-box in the whole document (the OFFER TABLE). The other
        3 tables serve rows and must render as data/empty, never as errors. A
        leak (>1 error-box) would mean the marker is not table-scoped -- the
        founder would see phantom refusals on healthy tables.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_insight_errors={_OFFER_TABLE_INSIGHT: OperatorAccessDeniedError("denied")},
        )

        html = await _run_and_capture_html(wf)

        assert html.count(_ERROR_BOX_MARKER) == 1, (
            "denial leaked an error render into other tables -- exactly one "
            f"error-box expected, found {html.count(_ERROR_BOX_MARKER)}"
        )

    async def test_broad_catch_unexpected_error_also_renders_typed_error_box(
        self, mock_resolution_context
    ) -> None:
        """EDGE -- the broad-catch arm (unexpected error) ALSO renders typed.

        The write path has TWO typed-marker arms: OperatorAccessDeniedError AND
        the broad ``except Exception``. A denied table via an UNEXPECTED error
        type (RuntimeError, not OperatorAccessDeniedError) must ALSO render a
        typed error-box, carrying the exception's own type -- proving the second
        arm is guarded too, not just the named-exception arm.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            operator_insight_errors={
                _OFFER_TABLE_INSIGHT: RuntimeError("unexpected operator plane fault")
            },
        )

        html = await _run_and_capture_html(wf)
        section = _offer_table_section_html(html)

        assert _ERROR_BOX_MARKER in section, (
            "broad-catch (unexpected error) did NOT render a typed error-box -- "
            "the unexpected-error arm is unguarded (would render empty)"
        )
        assert _EMPTY_SECTION_MARKER not in section
        # The unexpected exception's OWN type surfaces (not swallowed as denied).
        assert "RuntimeError" in section, (
            "the broad-catch error-box does not carry the unexpected exception's "
            "type at the point of action"
        )

    async def test_all_tables_denied_is_no_op_not_empty_deck(self, mock_resolution_context) -> None:
        """EDGE -- ALL tables denied -> the offer is a no-op, NOT an empty deck.

        When every table is denied (all tables failed), the all-tables-failed
        guard makes the offer FAIL (no deck published), rather than publishing a
        deck of four empty tables. This protects the prior good deck. compose_report
        must NOT have run (no report_content), so no empty-everything deck exists.
        """
        o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
        wf, _, _, _ = _make_workflow(
            offers=[o1],
            # Deny ALL FOUR operator insights.
            operator_insight_errors={
                "account_level_stats": OperatorAccessDeniedError("denied"),
                "question_level_stats": OperatorAccessDeniedError("denied"),
                "asset_level_stats": OperatorAccessDeniedError("denied"),
                "offer_level_stats": OperatorAccessDeniedError("denied"),
            },
        )

        from autom8_asana.automation.workflows.insights import workflow as _wf_mod

        real_compose = _wf_mod.compose_report
        ran = {"composed": False}

        def _spy(report_data: Any) -> str:
            ran["composed"] = True
            return str(real_compose(report_data))

        with patch(_COMPOSE_SPY_PATH, side_effect=_spy):
            result = await _enumerate_and_execute(wf)

        # All-tables-failed -> the offer does NOT succeed and NO deck is composed
        # (the prior good deck is protected; no empty-everything overwrite).
        assert result.succeeded == 0, "all-tables-denied offer must not publish a deck"
        assert ran["composed"] is False, (
            "compose_report ran with all tables denied -- an empty-everything "
            "deck would be built, overwriting the prior good deck"
        )
