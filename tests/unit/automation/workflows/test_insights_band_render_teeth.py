"""The B10 two-sided render TEETH -- the §7.5 falsifier, driven at the COMPOSED
render (provenance-to-the-human Sprint 5, the-band-itself, station S5-F).

CRITIC-AUTHORED (the load-bearing boundary, spec §7.5 / §8.1): this file is the
adversarial-disprover's, NOT the render builder's. The builder's own suite
(``test_insights_band_render.py``) proves the gates are PRESENT and WIRED at the
``_band_line_html`` / ``render_document`` altitude. THIS file discharges the
distinct B10 obligation the builder explicitly DEFERRED (that suite's docstring:
"it does NOT author the §7.5 two-sided fixture ... That proof-obligation belongs
to S5-F with the adversarial-disprover"): the seeded-false CI-laundered band is
driven RED **through the full ``compose_report`` composed document AND the
refusal LOG**, the honest ignorance band GREEN through the same composition, the
flag-OFF composition byte-identical -- and the fixture is proven to be a GENUINE
FALSIFIER by a mutation self-check (a weakened RED assert FAILS against the
honest surface). A band change that leaves Arm 1 green must trip this file RED.

The two-tier C1 structure this file attests (spec §build-receipt + §4):

  Tier 1 (EMISSION, data plane): the data-plane ``WeightIgnoranceBand`` pydantic
    model raises ``BandIntervalLaunderError`` at construction on any interval
    other than exactly [0,1]. The laundered band can NEVER be emitted by our own
    data plane. (Attested in the data worktree; cited here, not re-run.)
  Tier 2 (RENDER, this file): the client transport ``_band_from_meta_block``
    deliberately does TYPE/VOCABULARY-only checks and passes a well-formed-but-
    laundered band THROUGH to a single refusal point -- defense-in-depth against
    a corrupted / FOREIGN payload the data plane did not mint. The composed
    render REFUSES it here (nothing drawn; ``insights_export_band_render_refused``
    logged, reason=c1_interval_launder).

The three §7.5 arms, all at the COMPOSED-DOCUMENT altitude (not the unit
``_band_line_html`` altitude the builder suite covers):

  Arm 1 -- CI-laundered band RED: a composed render fed the Wilson ribbon
    ([0.3093, 0.3150]) posing as the [0,1] band draws NO ribbon and leaks NO
    interval number into the document; the refusal log fires.
  Arm 2 -- ignorance-overlay band GREEN: the same composed render fed the honest
    [0,1]+UNDERSTATE band surfaces EXACTLY the one-line §7.1 disclosure.
  Arm 3 -- flag-OFF byte-identical: with ``render_nsr_band`` OFF, the composed
    document is byte-identical to the no-band baseline.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
import structlog

from autom8_asana.automation.workflows.insights import formatter as _fmt_mod
from autom8_asana.automation.workflows.insights.formatter import (
    RENDER_NSR_BAND_ENV_VAR,
    InsightsReportData,
    TableResult,
    compose_report,
)
from autom8_asana.clients.data._endpoints.operator import WeightIgnoranceBand

_CURRENT_VERSION = "2026-03-24-static-UNRATIFIED"
_FIXTURE_ASOF = "2026-07-13T00:00:00Z"
_SUMMARY = "SUMMARY"

# The honest emitted band: [0,1]-ignorance + UNDERSTATE overlay (spec §1/§2).
_OVERLAY_BAND = WeightIgnoranceBand(
    status="ignorance_overlay",
    scheme_version=_CURRENT_VERSION,
    lower=0.0,
    upper=1.0,
    overlay_direction="understate",
    overlay_citation="WORM-LEDGER §1.1 / BAND-MECHANISM §2",
)

# The seeded-false CI-laundered mutation: the proxy's Wilson ribbon [0.3093,
# 0.3150] populated as if it BOUNDED the show-weight. The data plane's pydantic
# model raises BandIntervalLaunderError on this shape (Tier 1); the CLIENT-side
# frozen mirror does NOT re-assert C1 (transport passthrough), which is why this
# object is constructible here -- it models exactly the corrupted / foreign wire
# payload the render's C1 refusal (Tier 2) exists to catch.
_LAUNDERED_BAND = WeightIgnoranceBand(
    status="ignorance_overlay",
    scheme_version=_CURRENT_VERSION,
    lower=0.3093,
    upper=0.3150,
    overlay_direction="understate",
    overlay_citation="LAUNDERED — the Wilson ribbon posing as the band",
)

# The exact mechanism-default disclosure line (FIRE-SEAM BAND-LINE), byte-exact.
_EXPECTED_BAND_LINE = (
    '<div class="section-provenance section-band">'
    "forward-rate band: [0,1] ignorance · direction: understates "
    "(weights 2026-03-24-static-UNRATIFIED)</div>"
)

# The forbidden proxy numbers (§7.2): no function of the Wilson bounds may reach
# the rendered document via the band's numeric slots.
_LAUNDERED_NUMBERS = ("0.309", "0.315", "0.3093", "0.3150")


def _compose_with_band(band: Any) -> str:
    """Drive the FULL ``compose_report`` composition over a weighted SUMMARY table
    carrying ``band``, with the live clocks frozen so the flag-OFF byte-identity
    arm is exact over the whole pipeline document."""
    result = {
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
    data = InsightsReportData(
        business_name="Acme Dental",
        office_phone="+17705753103",
        vertical="chiropractic",
        table_results=result,
        started_at=100.0,
        version="insights-export-v1.0",
    )
    frozen = SimpleNamespace(now=lambda tz: datetime(2026, 7, 13, tzinfo=UTC))
    with (
        patch.object(_fmt_mod, "datetime", frozen),
        patch.object(_fmt_mod, "time", SimpleNamespace(monotonic=lambda: 100.0)),
    ):
        return compose_report(data)


def _compose_capturing_logs(band: Any) -> tuple[str, list[dict[str, Any]]]:
    """As :func:`_compose_with_band`, but also captures structlog events so the
    render REFUSAL log can be asserted at the composed altitude.

    Clears the module logger's cached ``bind`` (the ``cache_logger_on_first_use``
    caveat proven at ``tests/unit/core/test_concurrency.py``) so
    ``capture_logs`` intercepts even when an earlier test bound the proxy."""
    proxy = _fmt_mod.logger
    if "bind" in getattr(proxy, "__dict__", {}):
        del proxy.__dict__["bind"]
    with structlog.testing.capture_logs() as captured:
        html = _compose_with_band(band)
    return html, list(captured)


@pytest.fixture
def _flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """The GATE-B flag explicitly ON (Arms 1 and 2 -- the band surfaces)."""
    monkeypatch.setenv(RENDER_NSR_BAND_ENV_VAR, "true")


@pytest.fixture
def _flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """The GATE-B flag OFF -- the shipped default (Arm 3)."""
    monkeypatch.delenv(RENDER_NSR_BAND_ENV_VAR, raising=False)


# =====================================================================
# Arm 1 -- the seeded-false CI-laundered band is RED-CAUGHT at the
#          COMPOSED render (nothing drawn; the refusal log fires).
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestArm1LaunderedBandRedAtComposedRender:
    """The Wilson ribbon posing as the band is REFUSED through compose_report."""

    def test_composed_document_draws_no_band_grammar(self) -> None:
        html = _compose_with_band(_LAUNDERED_BAND)
        assert "section-band" not in html
        assert "forward-rate band" not in html

    def test_composed_document_leaks_no_laundered_interval_number(self) -> None:
        # §7.2: no function of the Wilson bounds may reach the rendered document.
        html = _compose_with_band(_LAUNDERED_BAND)
        for number in _LAUNDERED_NUMBERS:
            assert number not in html, (
                f"laundered number {number!r} leaked into the composed document"
            )

    def test_composed_render_fires_c1_refusal_log(self) -> None:
        # The refusal is LOUD: the composed pipeline logs the C1 launder refusal.
        _html, logs = _compose_capturing_logs(_LAUNDERED_BAND)
        refusals = [
            entry for entry in logs if entry.get("event") == "insights_export_band_render_refused"
        ]
        assert len(refusals) == 1, (
            "the composed render must fire EXACTLY ONE C1 refusal on the "
            f"laundered band (the single defense-in-depth refusal point); got {len(refusals)}"
        )
        assert refusals[0]["reason"] == "c1_interval_launder"
        assert refusals[0]["section"] == _SUMMARY

    def test_pre_band_disclosures_survive_the_refusal(self) -> None:
        # The C1 refusal suppresses ONLY the band line -- the pre-band provenance
        # (weights_version + asOf) is untouched, so a laundered band degrades
        # gracefully to the pre-band surface, never to a broken document.
        html = _compose_with_band(_LAUNDERED_BAND)
        assert f"weights {_CURRENT_VERSION}" in html


# =====================================================================
# Arm 2 -- the honest ignorance-overlay band surfaces EXACTLY the
#          one-line §7.1 disclosure through the COMPOSED render (GREEN).
# =====================================================================


@pytest.mark.usefixtures("_flag_on")
class TestArm2HonestBandGreenAtComposedRender:
    """The [0,1]+UNDERSTATE band surfaces the mechanism through compose_report."""

    def test_composed_document_carries_exact_band_line(self) -> None:
        html = _compose_with_band(_OVERLAY_BAND)
        assert _EXPECTED_BAND_LINE in html

    def test_composed_document_conveys_width_direction_version(self) -> None:
        html = _compose_with_band(_OVERLAY_BAND)
        assert "[0,1] ignorance" in html  # width: the full logical range
        assert "direction: understates" in html  # the §2 proven-analytically sign
        assert f"weights {_CURRENT_VERSION}" in html  # version, verbatim id

    def test_composed_document_never_conveys_forbidden_readings(self) -> None:
        # §7.2 MUST-NEVER, asserted over the WHOLE composed document.
        html = _compose_with_band(_OVERLAY_BAND)
        assert "confidence" not in html.lower()
        assert "±" not in html
        for number in _LAUNDERED_NUMBERS:
            assert number not in html

    def test_honest_band_fires_no_refusal_log(self) -> None:
        # The honest band is not refused: no launder log on the GREEN arm.
        _html, logs = _compose_capturing_logs(_OVERLAY_BAND)
        refusals = [
            entry for entry in logs if entry.get("event") == "insights_export_band_render_refused"
        ]
        assert refusals == []


# =====================================================================
# Arm 3 -- flag OFF: the composed document is byte-identical to the
#          no-band baseline (non-interference by construction).
# =====================================================================


@pytest.mark.usefixtures("_flag_off")
class TestArm3FlagOffByteIdenticalComposedDocument:
    """With render_nsr_band OFF, a band-carrying composition == a no-band one."""

    def test_overlay_band_composition_byte_identical_to_no_band(self) -> None:
        assert _compose_with_band(_OVERLAY_BAND) == _compose_with_band(None)

    def test_even_a_laundered_band_composition_is_byte_identical_off(self) -> None:
        # OFF short-circuits BEFORE any band inspection, so even a laundered band
        # leaves no trace and fires no refusal log (byte-identical by construction).
        html_laundered, logs = _compose_capturing_logs(_LAUNDERED_BAND)
        assert html_laundered == _compose_with_band(None)
        assert [e for e in logs if e.get("event") == "insights_export_band_render_refused"] == []


# =====================================================================
# The fixture-is-a-falsifier SELF-CHECK (spec §7.5): a fixture that
# cannot fail is not a falsifier. A WEAKENED Arm-1 RED assert (one that
# accepts a rendered ribbon) MUST FAIL against the honest surface -- i.e.
# the discriminator has genuine two-sided teeth, not vacuous green.
# =====================================================================


class TestFixtureIsAGenuineFalsifier:
    """Prove the RED arm bites: mutate the assertion and confirm it would trip."""

    def test_weakened_red_assert_would_fail_on_the_honest_surface(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The discriminating-canary self-check: the RED arm asserts the LAUNDERED
        # band draws no band grammar. If we MUTATE the target of that assert to the
        # HONEST band (which DOES draw the grammar when ON), the same assertion
        # body flips -- proving the assert is not vacuously true (it distinguishes
        # the two surfaces). A fixture whose RED arm passes for BOTH surfaces would
        # be theater; this proves it does not.
        monkeypatch.setenv(RENDER_NSR_BAND_ENV_VAR, "true")
        laundered_html = _compose_with_band(_LAUNDERED_BAND)
        honest_html = _compose_with_band(_OVERLAY_BAND)
        # The RED-arm predicate ("section-band" not in html) is TRUE for laundered
        # (the fixture's real assertion) and FALSE for honest -- two-sided teeth.
        assert "section-band" not in laundered_html  # the real Arm-1 assertion
        assert "section-band" in honest_html  # the mutation that MUST fail Arm-1
        # And the laundered/honest compositions are genuinely DIFFERENT documents
        # under the flag ON -- the discriminator is not fires-on-both theater.
        assert laundered_html != honest_html

    def test_red_and_green_arms_are_the_same_composition_up_to_the_band_line(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The ONLY difference between the RED (laundered->refused->nothing) and
        # GREEN (honest->band line) compositions is the presence of the band line
        # itself: strip the band line from the GREEN document and it equals the RED
        # document. This proves the RED arm is a clean refusal (the band line is
        # the sole delta), not a broken render masquerading as a refusal.
        monkeypatch.setenv(RENDER_NSR_BAND_ENV_VAR, "true")
        laundered_html = _compose_with_band(_LAUNDERED_BAND)
        honest_html = _compose_with_band(_OVERLAY_BAND)
        stripped = honest_html.replace(_EXPECTED_BAND_LINE, "")
        assert stripped == laundered_html
