"""S5-F2 CURE RE-ATTACK teeth -- the adversarial-disprover's SCOPED re-fire of the
two conditions from the S5-F standing verdict (DISPROOF-2 moot-at-cap; DISPROOF-3
scheme-version vector) against the S5-E2 cure (``f10d31bb``).

CRITIC-AUTHORED (the load-bearing boundary): this file is the disprover's, NOT the
render builder's. It EXTENDS ``test_insights_band_render_teeth.py`` (the S5-F
fixture, untouched) -- it does not replace it. Every arm below drives the CURED
surface (``_band_direction_moot_at_cap`` + the FIRE-SEAM BAND-SCHEME equality) at
the COMPOSED ``compose_report`` altitude, two-sided, so a regression that reopens
either DISPROOF trips this file RED.

  RA-1 (seeded-false at the cured cap): an ALL-rows-saturated (nsr_ncr=100.0)
    weighted section with the honest [0,1]+understate band must carry the MOOT
    token and must NOT carry ``direction: understates`` -- the S5-F DISPROOF-2
    reproduction, now EXPECTED CAUGHT. Two-sided: a MIXED section (one sub-cap
    row) renders the normal understate line (the moot guard must not over-fire).

  RA-2 (cap-boundary adversarial): 99.999 (sub-cap -> understate) vs 100.0
    (at-cap -> moot) vs a foreign 250.0 (super-cap -> moot); the DRAWN-face vs
    full_rows divergence (a truncated face all-capped while full_rows holds a
    sub-cap row) -- the moot keys on the DRAWN face per the per-TABLE ruling
    (a named residue, NOT a bug: the moot line disagrees with the Copy-TSV
    sidecar under truncation); and a section with NO numeric nsr_ncr on the
    drawn face -> directional line unchanged (no-nsr-column no-change ruling).

  RA-3 (scheme-vector kill confirmation): the exact S5-F 5th-vector payload
    (``scheme-[0.3093,0.3150]-UNRATIFIED``) draws NOTHING, leaks ZERO Wilson
    digits at document altitude, and fires reason=scheme_version_mismatch.
    Two-sided: the matching version renders the line. Plus NEW hostile smuggle
    attempts (moot-token-as-scheme, digit-in-direction, unicode homoglyph
    version, and laundered-digits-in-citation) -- reported honestly.

  RA-4 (falsifier self-check): the two-sided teeth of RA-1 and RA-3 are proven
    genuine -- the moot arm and the understate arm are DIFFERENT compositions,
    and the scheme-refused arm differs from the scheme-matched arm.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
import structlog

from autom8_asana.automation.workflows.insights import formatter as _fmt_mod
from autom8_asana.automation.workflows.insights.formatter import (
    RENDER_NSR_BAND_ENV_VAR,
    DataSection,
    InsightsReportData,
    TableResult,
    _band_direction_moot_at_cap,
    compose_report,
)
from autom8_asana.clients.data._endpoints.operator import WeightIgnoranceBand

_CURRENT_VERSION = "2026-03-24-static-UNRATIFIED"
_FIXTURE_ASOF = "2026-07-13T00:00:00Z"
_SUMMARY = "SUMMARY"

# The S5-F 5th-vector smuggle payload (DISPROOF-3): the Wilson ribbon dressed as a
# scheme-version string. It cannot equal the section's weights_version by
# construction, so the FIRE-SEAM BAND-SCHEME equality refuses it.
_SCHEME_SMUGGLE = "scheme-[0.3093,0.3150]-UNRATIFIED"

# The forbidden proxy numbers (§7.2): no function of the Wilson bounds may reach
# the rendered document via any band slot.
_LAUNDERED_NUMBERS = ("0.309", "0.315", "0.3093", "0.3150")


def _band(
    scheme: str = _CURRENT_VERSION,
    direction: str = "understate",
    lower: float = 0.0,
    upper: float = 1.0,
    citation: str = "WORM-LEDGER §1.1 / BAND-MECHANISM §2",
) -> WeightIgnoranceBand:
    return WeightIgnoranceBand(
        status="ignorance_overlay",
        scheme_version=scheme,
        lower=lower,
        upper=upper,
        overlay_direction=direction,
        overlay_citation=citation,
    )


def _compose(
    rows: list[dict[str, Any]],
    band: Any,
    row_limits: dict[str, int] | None = None,
) -> str:
    """Drive the FULL ``compose_report`` over a weighted SUMMARY table carrying
    ``rows`` + ``band``, clocks frozen. ``row_limits`` forces client-side
    truncation so the DRAWN face (``section.rows``) can be made to diverge from
    ``full_rows`` (SUMMARY carries no ``default_limit`` / ``sort_key``, so display
    order == data order and a runtime limit is the sole truncation lever)."""
    result = {
        _SUMMARY: TableResult(
            table_name=_SUMMARY,
            success=True,
            data=rows,
            row_count=len(rows),
            weights_version=_CURRENT_VERSION,
            synced_at=_FIXTURE_ASOF,
            band=band,
        )
    }
    data = InsightsReportData(
        business_name="Acme Dental",
        office_phone="+17705753103",
        vertical="chiropractic",
        table_results=result,
        started_at=100.0,
        version="insights-export-v1.0",
        row_limits=row_limits or {},
    )
    frozen = SimpleNamespace(now=lambda tz: datetime(2026, 7, 13, tzinfo=UTC))
    with (
        patch.object(_fmt_mod, "datetime", frozen),
        patch.object(_fmt_mod, "time", SimpleNamespace(monotonic=lambda: 100.0)),
    ):
        return compose_report(data)


def _compose_capturing_logs(
    rows: list[dict[str, Any]], band: Any
) -> tuple[str, list[dict[str, Any]]]:
    """As :func:`_compose`, but captures the render REFUSAL log. Clears the module
    logger's cached ``bind`` so ``capture_logs`` intercepts (the
    ``cache_logger_on_first_use`` caveat)."""
    proxy = _fmt_mod.logger
    if "bind" in getattr(proxy, "__dict__", {}):
        del proxy.__dict__["bind"]
    with structlog.testing.capture_logs() as captured:
        html = _compose(rows, band)
    return html, list(captured)


@pytest.fixture
def _flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(RENDER_NSR_BAND_ENV_VAR, "true")


# =====================================================================
# RA-1 -- seeded-false at the cured cap: the DISPROOF-2 reproduction is
#         now CAUGHT. ALL-saturated -> moot; MIXED -> understate stands.
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestRA1MootAtCuredCap:
    """The S5-F DISPROOF-2 seeded-false input, now expected caught by the cure."""

    def test_all_saturated_face_carries_moot_and_never_understates(self) -> None:
        # SEEDED-FALSE (S5-F DISPROOF-2 repro): an all-100.0 face with the honest
        # understate band. Pre-cure this rendered "direction: understates" at a
        # saturated rate (the §2.5.3 MUST-NOT). The cure vacates it to moot.
        html = _compose([{"nsr_ncr": 100.0, "spend": 2.0}, {"nsr_ncr": 100.0, "spend": 1.0}], _band())
        assert "moot at 100% (saturated)" in html
        assert "direction: understates" not in html
        # width + version still convey (only the direction is transformed).
        assert "[0,1] ignorance" in html
        assert f"weights {_CURRENT_VERSION}" in html

    def test_mixed_face_renders_normal_understate_guard_does_not_over_fire(self) -> None:
        # TWO-SIDED: one sub-cap row among the drawn face -> the tilt is observable
        # somewhere, so the directional line STANDS (the moot guard must not fire).
        html = _compose([{"nsr_ncr": 100.0, "spend": 2.0}, {"nsr_ncr": 50.0, "spend": 1.0}], _band())
        assert "direction: understates" in html
        assert "moot at 100%" not in html


# =====================================================================
# RA-2 -- cap-boundary adversarial: 99.999 vs 100.0 vs 250.0; the
#         DRAWN-face vs full_rows divergence; the no-nsr-column ruling.
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestRA2CapBoundary:
    """The exact-cap boundary and the drawn-face-keying ruling under truncation."""

    def test_just_below_cap_is_sub_cap_and_stands(self) -> None:
        # 99.999 < 100.0 -> sub-cap -> the tilt is observable -> understate stands.
        html = _compose([{"nsr_ncr": 99.999, "spend": 1.0}], _band())
        assert "direction: understates" in html
        assert "moot at 100%" not in html

    def test_exactly_at_cap_is_moot(self) -> None:
        html = _compose([{"nsr_ncr": 100.0, "spend": 1.0}], _band())
        assert "moot at 100% (saturated)" in html
        assert "direction: understates" not in html

    def test_foreign_super_cap_value_is_moot(self) -> None:
        # A 250.0 value is unmintable by our own plane (the PercentageFormula
        # clamps at 100.0), but a foreign/corrupt payload >= cap has ALSO
        # saturated past the cap -> moot (>= predicate), never a live tilt.
        html = _compose([{"nsr_ncr": 250.0, "spend": 1.0}], _band())
        assert "moot at 100% (saturated)" in html
        assert "direction: understates" not in html

    def test_drawn_face_all_capped_full_rows_sub_cap_keys_on_drawn_face(self) -> None:
        # THE per-TABLE DRAWN-FACE RULING, adversarially exercised: a runtime
        # row_limit of 1 truncates SUMMARY to its FIRST row (100.0, capped) while
        # full_rows retains the sub-cap 50.0 row. The moot keys on the DRAWN face,
        # so the line goes MOOT even though full_rows holds an observable tilt.
        # This is the RULING behaving as specified (§2.5.3 multi-row: quantify over
        # section.rows, the drawn cells; NOT full_rows, the Copy-TSV sidecar) -- but
        # it is a NAMED RESIDUE, not a clean win: the rendered moot line disagrees
        # with the sub-cap value a reader can copy from the TSV sidecar.
        html = _compose(
            [{"nsr_ncr": 100.0, "spend": 2.0}, {"nsr_ncr": 50.0, "spend": 1.0}],
            _band(),
            row_limits={_SUMMARY: 1},
        )
        assert "moot at 100% (saturated)" in html
        assert "direction: understates" not in html

    def test_drawn_face_ruling_probed_directly_on_the_helper(self) -> None:
        # The same divergence at the helper altitude, isolating the drawn-vs-full
        # keying: drawn=[100] moot=True even though full_rows=[100,50] holds a
        # sub-cap row. This pins the ruling so a future edit that (correctly or
        # not) re-keys the guard onto full_rows trips this assert.
        moot_on_drawn = _band_direction_moot_at_cap(
            DataSection(
                name="S",
                rows=[{"nsr_ncr": 100.0}],
                full_rows=[{"nsr_ncr": 100.0}, {"nsr_ncr": 50.0}],
            )
        )
        assert moot_on_drawn is True

    def test_no_numeric_nsr_ncr_on_drawn_face_leaves_direction_unchanged(self) -> None:
        # No-nsr-column no-change ruling: a drawn face with no numeric nsr_ncr
        # cell (column absent / display-filtered / all-None) is NOT moot -- no
        # saturated 100% face exists to contradict the tilt -> understate stands.
        html = _compose([{"spend": 1.0}], _band())
        assert "direction: understates" in html
        assert "moot at 100%" not in html
        # And the helper agrees for None / bool / NaN faces (never moot).
        assert _band_direction_moot_at_cap(DataSection(name="S", rows=[{"nsr_ncr": None}])) is False
        assert _band_direction_moot_at_cap(DataSection(name="S", rows=[{"nsr_ncr": True}])) is False
        assert (
            _band_direction_moot_at_cap(DataSection(name="S", rows=[{"nsr_ncr": float("nan")}]))
            is False
        )


# =====================================================================
# RA-3 -- scheme-vector kill confirmation: the S5-F 5th vector draws
#         nothing + fires scheme_version_mismatch; NEW smuggles reported.
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestRA3SchemeVectorKill:
    """The FIRE-SEAM BAND-SCHEME equality refuses foreign scheme payloads."""

    def test_s5f_fifth_vector_draws_nothing_and_leaks_no_wilson_digit(self) -> None:
        html, logs = _compose_capturing_logs([{"nsr_ncr": 31.2, "spend": 1.0}], _band(scheme=_SCHEME_SMUGGLE))
        assert "section-band" not in html
        assert "forward-rate band" not in html
        for number in _LAUNDERED_NUMBERS:
            assert number not in html, f"Wilson digit {number!r} leaked at document altitude"
        refusals = [e for e in logs if e.get("event") == "insights_export_band_render_refused"]
        assert len(refusals) == 1
        assert refusals[0]["reason"] == "scheme_version_mismatch"

    def test_matching_version_renders_the_line(self) -> None:
        # TWO-SIDED: the scheme that DOES equal weights_version draws the band.
        html, logs = _compose_capturing_logs([{"nsr_ncr": 31.2, "spend": 1.0}], _band(scheme=_CURRENT_VERSION))
        assert "section-band" in html
        assert f"weights {_CURRENT_VERSION}" in html
        assert [e for e in logs if e.get("event") == "insights_export_band_render_refused"] == []

    def test_new_smuggle_moot_token_as_scheme_is_refused(self) -> None:
        # NEW hostile attempt: put the MOOT token text in scheme_version (it
        # carries "100%" digits). It cannot equal weights_version -> refused; the
        # distinctive token never reaches the document.
        html, logs = _compose_capturing_logs(
            [{"nsr_ncr": 31.2, "spend": 1.0}], _band(scheme="ZZ-SMUGGLE-9931-moot-100pct")
        )
        assert "section-band" not in html
        assert "ZZ-SMUGGLE-9931-moot-100pct" not in html
        refusals = [e for e in logs if e.get("event") == "insights_export_band_render_refused"]
        assert refusals and refusals[0]["reason"] == "scheme_version_mismatch"

    def test_new_smuggle_digit_in_direction_refused_earlier_gate(self) -> None:
        # NEW hostile attempt: a digit-bearing direction token is unrecognized ->
        # refused at the direction gate (BEFORE the scheme gate), nothing drawn.
        html, logs = _compose_capturing_logs(
            [{"nsr_ncr": 31.2, "spend": 1.0}], _band(direction="understate99")
        )
        assert "section-band" not in html
        refusals = [e for e in logs if e.get("event") == "insights_export_band_render_refused"]
        assert refusals and refusals[0]["reason"] == "direction_unconveyable"

    def test_new_smuggle_unicode_homoglyph_version_is_refused(self) -> None:
        # NEW hostile attempt: a version that LOOKS like weights_version but uses a
        # Cyrillic homoglyph 'А'. Byte-equality (the FIRE-SEAM equality) is NOT
        # fooled by homoglyphs -> refused. (Confirms the equality is byte-exact,
        # not a normalized/visual compare -- a homoglyph cannot pass.)
        homoglyph = _CURRENT_VERSION.replace("A", "А")  # Cyrillic capital A
        assert homoglyph != _CURRENT_VERSION
        html, logs = _compose_capturing_logs([{"nsr_ncr": 31.2, "spend": 1.0}], _band(scheme=homoglyph))
        assert "section-band" not in html
        refusals = [e for e in logs if e.get("event") == "insights_export_band_render_refused"]
        assert refusals and refusals[0]["reason"] == "scheme_version_mismatch"

    def test_laundered_digits_in_citation_never_reach_the_document(self) -> None:
        # NEW hostile attempt (the surface the equality does NOT cover): the band
        # renders (scheme MATCHES) but the FREE-TEXT overlay_citation carries the
        # Wilson ribbon. HONEST RESULT: the citation field is diagnostic-only and
        # is NEVER a render surface -- the band line uses only width/direction/
        # version, so no laundered digit reaches the document. No new surface.
        html = _compose(
            [{"nsr_ncr": 31.2, "spend": 1.0}],
            _band(citation="Wilson [0.3093,0.3150] YY-CITATION-8842-TOKEN"),
        )
        assert "section-band" in html  # band renders (scheme matches)
        assert "YY-CITATION-8842-TOKEN" not in html  # citation never rendered
        for number in _LAUNDERED_NUMBERS:
            assert number not in html


# =====================================================================
# RA-4 -- falsifier self-check: the cure re-attack arms have genuine
#         two-sided teeth (moot != understate; refused != rendered).
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestRA4CureReAttackIsAGenuineFalsifier:
    """Prove the DISPROOF-2 and DISPROOF-3 re-attacks are two-sided, not theater."""

    def test_moot_and_understate_are_different_compositions(self) -> None:
        # DISPROOF-2 teeth: the all-saturated (moot) and mixed (understate)
        # compositions are DIFFERENT documents. If the cure were inert (always
        # understate) OR over-fired (always moot), these would be equal for the
        # wrong reason -- so the inequality is the genuine two-sided bite.
        moot_html = _compose([{"nsr_ncr": 100.0, "spend": 1.0}], _band())
        understate_html = _compose([{"nsr_ncr": 50.0, "spend": 1.0}], _band())
        assert "moot at 100% (saturated)" in moot_html
        assert "direction: understates" in understate_html
        assert moot_html != understate_html

    def test_scheme_refused_and_scheme_matched_are_different_compositions(self) -> None:
        # DISPROOF-3 teeth: the refused (foreign scheme -> no band) and matched
        # (scheme == weights_version -> band) compositions differ by exactly the
        # band line -- strip the band line from the matched doc and it equals the
        # refused doc (a clean refusal, not a broken render).
        refused_html = _compose([{"nsr_ncr": 31.2, "spend": 1.0}], _band(scheme=_SCHEME_SMUGGLE))
        matched_html = _compose([{"nsr_ncr": 31.2, "spend": 1.0}], _band(scheme=_CURRENT_VERSION))
        assert "section-band" not in refused_html
        assert "section-band" in matched_html
        assert refused_html != matched_html
        expected_band_line = (
            '<div class="section-provenance section-band">'
            "forward-rate band: [0,1] ignorance · direction: understates "
            f"(weights {_CURRENT_VERSION})</div>"
        )
        assert matched_html.replace(expected_band_line, "") == refused_html
