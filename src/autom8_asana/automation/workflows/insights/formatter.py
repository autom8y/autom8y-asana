"""HTML report formatter for insights export.

Implements the StructuredDataRenderer protocol (Option A+ from
SPIKE-FORMATTER-PROTOCOL-MOONSHOT) with an HtmlRenderer that produces
self-contained HTML documents with inline CSS.

Public API:
    compose_report(data: InsightsReportData) -> str
        Unchanged signature -- adapts InsightsReportData into DataSection
        list and delegates to HtmlRenderer.render_document().

    StructuredDataRenderer (Protocol)
        Reusable protocol for any surface that renders list[dict] data.

    DataSection (frozen dataclass)
        Universal input shape for a single data table/section.

    HtmlRenderer
        The sole StructuredDataRenderer implementation (v1).
"""

from __future__ import annotations

import html
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from autom8y_api_schemas import OfficePhoneField  # noqa: TC002
from autom8y_log import get_logger

from autom8_asana.automation.workflows.insights.tables import (
    TABLE_SPECS,
    DispatchType,
)
from autom8_asana.clients.utils.pii import mask_phone_number

logger = get_logger(__name__)

# Preferred leading columns for period-based and reconciliation tables.
# Keys must match TABLE_ORDER names exactly.
COLUMN_ORDER: dict[str, list[str]] = {
    "BY QUARTER": ["period_label", "period_start", "period_end"],
    "BY MONTH": ["period_label", "period_start", "period_end"],
    "BY WEEK": ["period_label", "period_start", "period_end"],
    "LIFETIME RECONCILIATIONS": [
        "office_phone",
        "vertical",
        "num_invoices",
        "collected",
        "spend",
        "variance",
        "variance_pct",
    ],
    "T14 RECONCILIATIONS": [
        "period",
        "period_label",
        "period_start",
        "period_end",
        "period_len",
        "num_invoices",
        "collected",
        "spend",
        "variance",
        "variance_pct",
    ],
}

# Display-friendly column labels. Checked before title-casing.
_DISPLAY_LABELS: dict[str, str] = {
    "n_distinct_ads": "Distinct Ads",
    "cpl": "CPL",
    "cps": "CPS",
    # GAP-2 "Two metrics, honestly named" (ratified 2026-07-08): ecps is the
    # STATUS-FILTER metric spend/effective_scheds -> "Effective CPS" (the old
    # "Expected CPS" label was drifted); xcps is the NET-NEW probabilistic
    # show-weight metric spend/solid_scheds -> "Expected CPS".
    "ecps": "Effective CPS",
    "xcps": "Expected CPS",
    "cpc": "CPC",
    "ltv": "LTV",
    "ctr": "CTR",
    "lctr": "Lead CTR",
    "nsr_ncr": "NSR/NCR",
    "lp20m": "Leads/20K",
    "sp20m": "Shows/20K",
    "esp20m": "Exp. Shows/20K",
    "ltv20m": "LTV/20K",
    "roas": "ROAS",
    "ns_rate": "No-Show Rate",
    "nc_rate": "No-Close Rate",
    "variance_pct": "Variance %",
    "imp": "Impressions",
    "booking_rate": "Booking Rate",
    "conv_rate": "Conv. Rate",
    "sched_rate": "Sched. Rate",
    "pacing_ratio": "Pacing Ratio",
    "conversion_rate": "Conversion Rate",
    "period_label": "Period",
    "period_start": "Start",
    "period_end": "End",
    "period_len": "Days",
}

# Tooltip definitions for column headers.
_COLUMN_TOOLTIPS: dict[str, str] = {
    "cpl": "Cost Per Lead: Total spend \u00f7 total leads",
    # Legacy drift fixed (GAP-2 2026-07-08): modern cps is cost per SCHEDULED
    # appointment (autom8y-data library.py cps = spend/scheds), not per show.
    "cps": "Cost Per Schedule: Total spend \u00f7 scheduled appointments",
    "ecps": "Effective CPS: Spend \u00f7 effective schedules (excludes no-shows and non-converted)",
    "xcps": "Expected CPS: Spend \u00f7 probability-weighted expected shows",
    "booking_rate": "Booking Rate: Scheduled appointments \u00f7 total leads",
    "roas": "Return on Ad Spend: Revenue \u00f7 ad spend",
    "ctr": "Click-Through Rate: Clicks \u00f7 impressions",
    "ltv": "Lifetime Value: Estimated revenue per customer",
    # R3 honest denominators (2026-07-08 ruling): the four rate metrics all
    # divide by the probability-weighted solid_scheds denominator, NOT bare
    # scheduled/shown/lead counts (autom8y-data core/metrics/library.py conv_rate
    # :2540, ns_rate :2470, nc_rate :2506, nsr_ncr :2579 all total="solid_scheds",
    # ADR-SOLID-SCHEDS-001/002). "probability-weighted" mirrors xcps (above) and
    # the data-side solid_scheds description "Probabilistically-weighted
    # scheduled appointments". Distinct from conversion_rate (scheds/leads,
    # library.py:2107) which correctly divides by leads and carries no tooltip.
    "conv_rate": "Conversion Rate: Conversions \u00f7 probability-weighted scheduled appointments",
    "ns_rate": "No-Show Rate: No-shows \u00f7 probability-weighted scheduled appointments",
    "nc_rate": "No-Close Rate: No-closes \u00f7 probability-weighted scheduled appointments",
    "nsr_ncr": "NSR/NCR: Lost appointments (no-shows + no-closes) \u00f7 probability-weighted scheduled appointments",
    "variance_pct": "Variance %: (Collected - Spend) \u00f7 Spend \u00d7 100",
}

# Section subtitles displayed below section headers.
_SECTION_SUBTITLES: dict[str, str] = {
    "SUMMARY": "Lifetime performance metrics across all campaigns for this business.",
    "APPOINTMENTS": "Scheduled appointments from the last 90 days.",
    "LEADS": "Incoming leads from the last 30 days, excluding those with appointments.",
    "LIFETIME RECONCILIATIONS": "Financial reconciliation across all time periods.",
    "T14 RECONCILIATIONS": "Rolling 14-day financial reconciliation windows.",
    "BY QUARTER": "Quarterly performance trends with key efficiency metrics.",
    "BY MONTH": "Monthly performance trends with key efficiency metrics.",
    "BY WEEK": "Weekly performance trends with key efficiency metrics.",
    "AD QUESTIONS": "Lead-qualifying questions and their conversion impact.",
    "ASSET TABLE": "Creative performance by individual ad asset over the last 30 days.",
    "OFFER TABLE": "Offer-level performance metrics over the last 30 days.",
    "UNUSED ASSETS": "Ad assets with zero activity (spend and leads) plus inventory-only assets, over the last 30 days.",
}


# Sections expanded by default (rest start collapsed).
_DEFAULT_EXPANDED_SECTIONS: frozenset[str] = frozenset(
    {
        "SUMMARY",
        "BY WEEK",
    }
)

# PII columns requiring phone masking in table cells.
_PII_PHONE_COLUMNS: frozenset[str] = frozenset(
    {"office_phone", "phone", "patient_phone", "contact_phone"}
)

# Conditional formatting thresholds for rate columns.
# booking_rate is ratio 0-1; conv_rate is percentage 0-100.
_CONDITIONAL_FORMAT_THRESHOLDS: dict[str, tuple[float, float]] = {
    "booking_rate": (0.40, 0.20),
    "conv_rate": (40.0, 20.0),
}


# ---------------------------------------------------------------------------
# Domain data classes (unchanged public API)
# ---------------------------------------------------------------------------


@dataclass
class TableResult:
    """Result of fetching a single table.

    Attributes:
        table_name: Human-readable table name (e.g., "SUMMARY").
        success: Whether the fetch succeeded.
        data: List of row dicts from the API response (None if failed).
        row_count: Number of rows returned.
        error_type: Error classification string (if failed).
        error_message: Human-readable error description (if failed).
        weights_version: provenance-to-the-human Sprint 1 (render-wiring): the
            applied show-probability weight-scheme version-id carried from the
            operator batch's RESPONSE/META-grain provenance (the single provenance
            token, e.g. ``2026-03-24-static-UNRATIFIED``). None when the table
            carried no weights_version (declared absence). For a WEIGHTED table
            (one carrying a weight-governed column), None is IMPOSSIBLE on a
            ``success=True`` result -- the C2 guard in ``_fetch_table`` routes a
            weighted-but-provenance-absent table to a ``success=False`` typed
            refusal INSTEAD, so a weight-banded number never renders provenance-free.
        synced_at: ISO-8601 asOf timestamp of the data snapshot this table was
            computed over (``DataFreshness.synced_at``), or None when unknown. Read
            by the render to stamp the section subtitle with the live query date
            (R4/DEFER-6) so a snapshot is not misread as stable history.
        coverage: provenance-to-the-human Sprint 4 (coverage-disclosure-at-render):
            the attribution-coverage sidecar (``AttributionCoverage`` from the
            operator batch meta), or None when the batch carried no coverage block.
            Read together with ``coverage_expected`` by the OFFER TABLE render to
            disclose the spend-attribution floor (measured), the unknown (no_data),
            or the honest-absent "not measured" (None + coverage_expected False)
            state -- a typed three-valued disclosure, never a null-coerced full
            attribution reading (G4). Carried as ``Any`` to avoid a formatter->client
            import edge; the render only reads ``.status`` / ``.orphan_spend_share``.
        coverage_expected: provenance-to-the-human Sprint 4: whether a coverage block
            is contractually expected for this table. False == "this table makes no
            coverage promise" (the truthful deck state -> "not measured"). Governs the
            None-coverage render fork: honest-absent (False) vs would-be-dropped
            unknown (True). Defaults False.
        band: provenance-to-the-human Sprint 5 (the-band-itself): the typed
            weight-ignorance band (``WeightIgnoranceBand`` from the operator batch
            meta, BAND-MECHANISM §6.1), or None when the batch carried no band
            block. Read by the GATE-B-flagged band render (``_band_line_html``)
            for weighted sections only; renders NOTHING while the named
            ``render_nsr_band`` flag is OFF (the shipped default). Carried as
            ``Any`` to avoid a formatter->client import edge (mirrors
            ``coverage``); the render only reads ``.status`` / ``.lower`` /
            ``.upper`` / ``.overlay_direction`` / ``.scheme_version``.
    """

    table_name: str
    success: bool
    data: list[dict[str, Any]] | None = None
    row_count: int = 0
    error_type: str | None = None
    error_message: str | None = None
    weights_version: str | None = None
    synced_at: str | None = None
    coverage: Any = None
    coverage_expected: bool = False
    band: Any = None


@dataclass
class InsightsReportData:
    """Input data for composing a full report."""

    business_name: str
    office_phone: OfficePhoneField
    vertical: str
    table_results: dict[str, TableResult]
    started_at: float  # time.monotonic() value
    version: str
    row_limits: dict[str, int] = field(default_factory=dict)
    offer_gid: str | None = None


# ---------------------------------------------------------------------------
# StructuredDataRenderer protocol + DataSection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DataSection:
    """A named section containing tabular data or a status message.

    provenance-to-the-human Sprint 1 (render-wiring, H7): ``weights_version`` and
    ``synced_at`` carry the section's provenance from the ``TableResult`` to the
    rendered HTML. When ``weights_version`` is present the section renders a
    provenance disclosure line (the version-id -- which itself says UNRATIFIED --
    plus the asOf); when ``synced_at`` is present the snapshot-grain subtitle is
    stamped with the live query date (R4/DEFER-6). Both None => no provenance
    surface (an unweighted section, or a section with no snapshot stamp).

    provenance-to-the-human Sprint 4 (coverage-disclosure-at-render): ``coverage``
    + ``coverage_expected`` carry the attribution-coverage sidecar from the
    ``TableResult``. The OFFER TABLE section renders a spend-attribution
    disclosure line from them (:func:`_coverage_line_html` -- measured floor /
    no-data / not-measured); other sections render none (the disclose-mandate is
    scoped to the surface where spend is allocated, autom8y-data db.md:180-184).

    provenance-to-the-human Sprint 5 (the-band-itself): ``band`` carries the
    typed weight-ignorance band from the ``TableResult``. A WEIGHTED section
    (one carrying a ``weights_version``) renders the band disclosure line from
    it (:func:`_band_line_html`) ONLY while the named GATE-B flag
    ``render_nsr_band`` is ON; the flag lands OFF, so the shipped default
    renders nothing and the composed document is byte-identical to pre-band.
    """

    name: str
    rows: list[dict[str, Any]] | None
    row_count: int = 0
    truncated: bool = False
    total_rows: int | None = None
    error: str | None = None
    empty_message: str | None = None
    full_rows: list[dict[str, Any]] | None = None
    weights_version: str | None = None
    synced_at: str | None = None
    coverage: Any = None
    coverage_expected: bool = False
    band: Any = None


class StructuredDataRenderer(Protocol):
    """Renders tabular data sections into a formatted document.

    Protocol class (~15 lines) for any surface that needs to present
    list[dict[str, Any]] data as a human-readable document.
    """

    @property
    def content_type(self) -> str:
        """MIME type of the rendered output (e.g., 'text/html')."""
        ...

    @property
    def file_extension(self) -> str:
        """File extension without dot (e.g., 'html')."""
        ...

    def render_document(
        self,
        *,
        title: str,
        metadata: dict[str, str],
        sections: list[DataSection],
        footer: dict[str, str] | None = None,
    ) -> str:
        """Render a complete document with header, data sections, and footer."""
        ...


# ---------------------------------------------------------------------------
# Provenance disclosure (provenance-to-the-human Sprint 1, render badge H7)
# ---------------------------------------------------------------------------

# The literal disclosed when a weighted section's asOf (synced_at) is unknown.
# Ruling (§4c): for a weighted table the asOf ignorance is DISCLOSED, never
# silently omitted -- a snapshot-grain number with no query-date stamp could be
# misread as reproducible history. An unweighted section renders no provenance
# line at all, so this literal only ever appears for weighted sections.
_ASOF_UNKNOWN_TEXT = "unknown"


def _provenance_line_html(weights_version: str | None, synced_at: str | None) -> str:
    """Render the per-section provenance disclosure line, or "" when none.

    The line is emitted iff a ``weights_version`` is present (the section carries a
    weight-banded number, so WORM §1.3 never-hidden REQUIRES the disclosure). It
    states the version-id verbatim (the id ITSELF discloses UNRATIFIED -- the
    Reading-A truth-telling token) and the asOf query date. When ``synced_at`` is
    None the asOf is DISCLOSED as unknown (§4c ruling), never omitted.

    The founder SEES, e.g.:
        weights 2026-03-24-static-UNRATIFIED · as of 2026-07-13T00:00:00Z
        weights 2026-03-24-static-UNRATIFIED · as of unknown   (asOf absent)

    No ``weights_version`` => "" (an unweighted section discloses nothing here; the
    C2 guard upstream guarantees a WEIGHTED section always arrives with one, so ""
    here can only mean unweighted).
    """
    if not weights_version:
        return ""
    asof = html.escape(synced_at) if synced_at else _ASOF_UNKNOWN_TEXT
    return (
        f'<div class="section-provenance">weights '
        f"{html.escape(weights_version)} · as of {asof}</div>"
    )


# ---------------------------------------------------------------------------
# Coverage disclosure (provenance-to-the-human Sprint 4, OFFER TABLE)
# ---------------------------------------------------------------------------

# The sections that render a spend-attribution coverage line. The disclose-mandate
# is scoped to the surface where spend is ALLOCATED (autom8y-data db.md:180-184);
# widening this set is a define-altitude ruling, never a silent edit.
_COVERAGE_DISCLOSED_SECTIONS = frozenset({"OFFER TABLE"})

# The disclosed-unknown token for a coverage-less OFFER TABLE. Under the BR-3
# honest-floor ruling the deck's batch path never runs the coverage processor, so
# coverage=None (+ coverage_expected either way) is the TRUTHFUL state -- disclosed
# visibly, never a silent blank and never a fabricated full-attribution reading.
_COVERAGE_NOT_MEASURED_TEXT = "spend attribution: not measured"
# The disclosed-unknown token for a measured-window absence (status="no_data"):
# the window has no coverage measurement -- never rendered as 0% or 100%.
_COVERAGE_NO_DATA_TEXT = "spend attribution: no data this window"


def _coverage_line_html(section: DataSection) -> str:
    """Render the OFFER TABLE spend-attribution disclosure line, or "" elsewhere.

    Three faces (BR-3 ruling (a) HONEST-FLOOR; contract §Q3/§Q4):

    - MEASURED (``status=="measured"`` with an ``orphan_spend_share``): the
      DIRECTIONAL IGNORANCE FLOOR -- ``spend attribution: ≥ 12.3% unattributed
      (orphan ads)``. A ``≥``-floor on the UNATTRIBUTED share, never a point
      "coverage 86%" claim and never a CI-shaped interval (C1: an ignorance floor
      must not launder into an accuracy claim).
    - NO_DATA (``status=="no_data"``, or a degenerate measured payload without a
      share): ``spend attribution: no data this window`` -- disclosed-unknown,
      never 0%/100%.
    - NOT MEASURED (``coverage is None``; the deck honest-absent state, and the
      would-be-dropped ``coverage_expected=True`` state until F5-coverage-THROW
      arms): ``spend attribution: not measured`` -- a VISIBLE token, structurally
      distinct from a silent blank. NO error, NO throw (the deck typed-THROW is
      NOT-YET-ARMABLE -- F5-coverage-THROW co-arms with batch measurement).

    Non-OFFER-TABLE sections return "" (no coverage claim is made where spend is
    not allocated -- no cry-wolf).
    """
    if section.name not in _COVERAGE_DISCLOSED_SECTIONS:
        return ""
    coverage = section.coverage
    if coverage is None:
        text = _COVERAGE_NOT_MEASURED_TEXT
    elif (
        getattr(coverage, "status", None) == "measured"
        and getattr(coverage, "orphan_spend_share", None) is not None
    ):
        share = float(coverage.orphan_spend_share)
        text = f"spend attribution: ≥ {share:.1%} unattributed (orphan ads)"
    else:
        # no_data, or a degenerate measured payload without a share.
        text = _COVERAGE_NO_DATA_TEXT
    return f'<div class="section-provenance section-coverage">{html.escape(text)}</div>'


# ---------------------------------------------------------------------------
# Weight-ignorance band disclosure (provenance-to-the-human Sprint 5,
# the-band-itself; BAND-MECHANISM spec §7, behind the named GATE-B flag)
# ---------------------------------------------------------------------------

# The named GATE-B flag (spec §7.4): ``render_nsr_band``, realized as an
# env-var-driven setting mirroring the workflow kill-switch idiom
# (EXPORT_ENABLED_ENV_VAR / os.environ read at call time) with the OPPOSITE,
# lands-OFF polarity: the kill switch defaults ENABLED and is opted OUT; this
# flag defaults OFF and must be opted IN with an explicit truthy value. Flag
# OFF => :func:`_band_line_html` returns "" before inspecting ANY band, so the
# composed document is byte-identical to pre-band BY CONSTRUCTION
# (non-interference; S5-H attests it). Flipping the flag in any shipped
# environment is the OPERATOR'S act, never a station's.
RENDER_NSR_BAND_ENV_VAR = "AUTOM8_RENDER_NSR_BAND"

# Explicit opt-IN vocabulary (the complement of the kill switch's opt-OUT set:
# absent / empty / anything unrecognized stays OFF -- the conservative default).
_RENDER_NSR_BAND_ON_VALUES: frozenset[str] = frozenset({"true", "1", "yes"})

# The §7.1 direction token -> rendered word (the §2 sign of the weight-ignorance
# bias on the rendered rate). "understate" is the shipped UNRATIFIED scheme's
# proven-analytically sign: the surface may look BETTER than reality. A token
# outside this vocabulary cannot convey the MANDATORY direction and is refused
# at render (nothing drawn), never guessed.
_BAND_DIRECTION_TEXT: dict[str, str] = {
    "understate": "understates",
    "overstate": "overstates",
    "indeterminate": "indeterminate",
}

# The deck column whose rendered rate the band line QUALIFIES: the nsr_ncr
# forward rate (the WORM-W1 family face). _FIELD_FORMAT renders it as an
# already-in-percent 0-100 "percentage" (100.0 -> "100.00%").
_BAND_RATE_COLUMN = "nsr_ncr"

# The M5 saturation cap on the rendered rate: the upstream PercentageFormula
# clamps each rate to exactly 100.0 (autom8y-data composite.py:1001), so >= is
# the at-the-cap predicate -- a foreign super-cap value (>100, unmintable by
# our own plane) has ALSO saturated past the cap and carries no observable
# strict-inequality tilt either.
_BAND_RATE_CAP = 100.0

# The §2.5.3 moot-at-cap direction token (DISPROOF-2 cure): at a saturated
# rendered rate the directional overlay is VACATED -- moot, not reversed --
# while the [0,1] ignorance width and the version id still convey. The token
# names WHY no tilt is claimed; the understate/overstate words never appear
# at the cap (the §2.5.3 MUST-NOT).
_BAND_DIRECTION_MOOT_TEXT = "moot at 100% (saturated)"


def _band_direction_moot_at_cap(section: DataSection) -> bool:
    """True iff the section's rendered face is nsr_ncr-saturated (M5 fails everywhere).

    DISPROOF-2 cure (BAND-MECHANISM §2.5.1 / §2.5.3): the overlay direction is a
    strict-inequality tilt claim CONDITIONAL on the rendered rate being sub-cap.
    Where the rate saturates at 100% the direction is moot, not reversed, and the
    presentation MUST NOT imply an understatement remains observable at the cap.

    MULTI-ROW RULING (the direction claim is per-TABLE): the deck tables are
    per-office rows and ONE band line qualifies the WHOLE section face, so the
    direction goes moot ONLY when EVERY rendered nsr_ncr value sits at the cap --
    if ANY rendered row is sub-cap the tilt is observable somewhere on the face
    and the directional line stands. Quantified over ``section.rows`` (the drawn
    face: sorted / truncated / column-filtered, exactly what
    ``_render_table_section`` draws) -- NOT ``full_rows`` (the Copy-TSV JSON
    sidecar, never a drawn cell). A section whose rendered rows carry NO numeric
    nsr_ncr value (column absent, display-filtered, or all-None dashes) is NOT
    moot -- no saturated 100% face exists to contradict the tilt claim, so the
    existing directional line renders unchanged (the no-nsr_ncr-column no-change
    ruling).
    """
    saw_at_cap_rate = False
    for row in section.rows or []:
        value = row.get(_BAND_RATE_COLUMN)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            # None (a dash) / non-numeric never draws as a rate (mirrors the
            # _extract_numeric_values acceptance + the _as_float_or_none
            # bool rejection).
            continue
        if not float(value) >= _BAND_RATE_CAP:
            # A sub-cap rate is on the face: the tilt is observable somewhere,
            # so the direction claim stands. (NaN lands here too -- an
            # out-of-contract face is never treated as a saturated 100%.)
            return False
        saw_at_cap_rate = True
    return saw_at_cap_rate


def _render_nsr_band_enabled() -> bool:
    """True iff the named GATE-B flag ``render_nsr_band`` is explicitly ON.

    Read from the environment at CALL time (``AUTOM8_RENDER_NSR_BAND``), so a
    deployed default carries no band surface and tests pin the flag per-case.
    Only an explicit truthy value ("true"/"1"/"yes", case-insensitive) enables;
    absent, empty, and unrecognized values are all OFF (lands-OFF, spec §7.4).
    """
    raw = os.environ.get(RENDER_NSR_BAND_ENV_VAR, "")
    return raw.strip().lower() in _RENDER_NSR_BAND_ON_VALUES


def _band_line_html(section: DataSection) -> str:
    """Render the weight-ignorance band disclosure line, or "" when gated off.

    FLAG-ON EXPRESSION (mechanism-default pending the operator's GATE-B
    presentation ruling (OP-3) -- NOT a GATE-B pick; the four GATE-B
    presentation shapes OPT-A..D, spec §7.3, remain the operator's): the most
    conservative C1-clean textual form in the existing ``.section-provenance``
    grammar, one line conveying exactly the §7.1 MUST-convey triple --
    width + direction + version:

        forward-rate band: [0,1] ignorance · direction: understates (weights
        2026-03-24-static-UNRATIFIED)

    and NEVER the §7.2 forbidden readings: no "confidence", no sub-[0,1]
    ribbon, no measured-interval numbers, no point correction. The version id
    renders VERBATIM from the band's ``scheme_version`` (== the sibling
    ``weights_version``, asserted at emission) -- the id ITSELF says UNRATIFIED,
    the single-source substring discipline (PROVENANCE-CARRY §1.2).

    THE THREE GATES (all must hold, in order):

    (a) the named GATE-B flag ``render_nsr_band`` is ON -- checked FIRST, before
        any band inspection, so flag-OFF is byte-identical by construction
        [FIRE-SEAM BAND-FLAG: OFF => ""];
    (b) the section is a WEIGHTED section (carries a ``weights_version``) -- an
        unweighted section has no weight-banded number to band;
    (c) ``band.status == "ignorance_overlay"`` -- ``no_band_applicable`` and
        object-absent (None) both render nothing (declared states, not bands).

    THE C1 RENDER REFUSAL [FIRE-SEAM BAND-C1]: if an overlay band somehow
    carries a sub-[0,1] interval (defensive -- the emission type forbids it:
    lower/upper are hard-fenced to exactly 0.0/1.0 upstream), this hop REFUSES
    to render an interval -- it renders NOTHING and logs
    ``insights_export_band_render_refused`` (reason="c1_interval_launder") --
    rather than draw a tight ribbon. Laundered precision on an epistemic gap is
    REFUSED at authoring, at emission, and HERE at render (spec §3). The same
    refusal (distinct reasons) fires when the mandatory §7.1 conveyance is
    impossible: an unconveyable/absent direction or a nameless scheme -- a
    partial band line would under-disclose, so nothing is drawn and the refusal
    is loud in the logs.

    THE SCHEME-EQUALITY REFUSAL [FIRE-SEAM BAND-SCHEME] (DISPROOF-3 cure): the
    band's ``scheme_version`` MUST equal the section's ``weights_version`` --
    the emission side asserts this equality (spec §6.1), so a mismatch arriving
    at render can only be a FOREIGN / corrupted payload the data plane did not
    mint. On mismatch nothing is drawn and the refusal logs
    reason="scheme_version_mismatch". This single equality guard ALSO closes
    the fifth-vector text-smuggle (Wilson digits posing as a version id, e.g.
    ``scheme-[0.3093,0.3150]-UNRATIFIED``): a smuggled string cannot equal the
    section's weights_version. Defense scope, stated honestly: the band line
    thereby adds NO new text surface beyond what the merged provenance badge
    (:func:`_provenance_line_html`) already renders verbatim -- if
    ``weights_version`` itself were the smuggle vector, the badge would already
    render it; that pre-existing accepted surface is the badge's contract, not
    this seam's.

    THE M5 MOOT-AT-CAP DIRECTION [FIRE-SEAM BAND-M5] (DISPROOF-2 cure, spec
    §2.5.3): when EVERY rendered nsr_ncr value on the section face sits at the
    100% cap (:func:`_band_direction_moot_at_cap` -- per-TABLE ruling in its
    docstring), the direction token renders as ``moot at 100% (saturated)``
    instead of the overlay word -- the strict-inequality tilt claim is vacated
    at saturation (moot, not reversed; the understate token MUST NOT appear).
    Width + version still convey unchanged. A sub-cap section renders exactly
    the existing directional line, byte-unchanged. This is a presentation
    transform on an ADMISSIBLE band, applied after every refusal gate: an
    out-of-vocabulary direction still refuses even at saturation (a band that
    cannot convey a direction stays inadmissible).

    [FIRE-SEAM BAND-LINE]: flag ON + weighted section + honest [0,1] overlay
    => exactly the one-line disclosure above, in the ``.section-provenance``
    grammar with the ``section-band`` marker class.
    """
    if not _render_nsr_band_enabled():
        # FIRE-SEAM BAND-FLAG: the GATE-B flag is OFF (the shipped default) --
        # return "" before touching the band at all (byte-identical by
        # construction; S5-H attests the composed-document equality).
        return ""
    if not section.weights_version:
        # Not a weighted section: no weight-banded number, no band surface.
        return ""
    band = section.band
    if band is None:
        # Object-absent: the DISCLOSED-UNKNOWN third state -- no band statement
        # was made, so none is rendered (never fabricated).
        return ""
    if getattr(band, "status", None) != "ignorance_overlay":
        # no_band_applicable (or an unrecognized discriminant): declared
        # not-applicable renders nothing.
        return ""
    lower = getattr(band, "lower", None)
    upper = getattr(band, "upper", None)
    if not (lower == 0.0 and upper == 1.0):
        # FIRE-SEAM BAND-C1: a sub-[0,1] (or bound-less) overlay interval is
        # laundered precision -- REFUSE to render an interval; nothing is drawn.
        logger.warning(
            "insights_export_band_render_refused",
            section=section.name,
            reason="c1_interval_launder",
            lower=lower,
            upper=upper,
        )
        return ""
    direction_text = _BAND_DIRECTION_TEXT.get(getattr(band, "overlay_direction", None) or "")
    if direction_text is None:
        # The §7.1 direction is MANDATORY; an unconveyable direction refuses
        # the whole line (a width-only band would under-disclose the sign).
        logger.warning(
            "insights_export_band_render_refused",
            section=section.name,
            reason="direction_unconveyable",
            overlay_direction=getattr(band, "overlay_direction", None),
        )
        return ""
    scheme_version = getattr(band, "scheme_version", None)
    if not isinstance(scheme_version, str) or not scheme_version:
        # A band that cannot name its scheme is inadmissible (§4): refuse loud.
        logger.warning(
            "insights_export_band_render_refused",
            section=section.name,
            reason="scheme_version_absent",
        )
        return ""
    if scheme_version != section.weights_version:
        # FIRE-SEAM BAND-SCHEME (DISPROOF-3 cure): the emission asserts
        # scheme_version == weights_version, so a mismatch here is a foreign /
        # corrupted payload -- refuse the whole line (nothing drawn), loud in
        # the logs. The offending values ride in the LOG for diagnosis (the
        # c1 refusal logs its offending bounds the same way); they never reach
        # the rendered document. This one equality also refuses the smuggled
        # Wilson-digits-as-version-text vector (it cannot equal the section's
        # weights_version).
        logger.warning(
            "insights_export_band_render_refused",
            section=section.name,
            reason="scheme_version_mismatch",
            scheme_version=scheme_version,
            weights_version=section.weights_version,
        )
        return ""
    if _band_direction_moot_at_cap(section):
        # FIRE-SEAM BAND-M5 (DISPROOF-2 cure, spec §2.5.3): every rendered
        # nsr_ncr value sits at the 100% cap, so the strict-inequality tilt
        # claim is vacated -- render the direction as moot (never the
        # understate token at a saturated face). Width + version convey
        # unchanged; applied only after every refusal gate passed (an
        # admissible band, presentation-transformed).
        direction_text = _BAND_DIRECTION_MOOT_TEXT
    text = (
        f"forward-rate band: [0,1] ignorance · direction: {direction_text} "
        f"(weights {scheme_version})"
    )
    return f'<div class="section-provenance section-band">{html.escape(text)}</div>'


def _section_disclosure_html(section: DataSection) -> str:
    """Build the subtitle (+ live asOf stamp) + provenance + band + coverage lines.

    Four disclosures, one place (so none can drift from the others across the
    three section renderers):

    1. SUBTITLE (R4 / DEFER-6): the base window prose from ``_SECTION_SUBTITLES``,
       with the live asOf query date APPENDED (``· as of <ISO>``) whenever the
       section carries a ``synced_at``. This discharges the emission MANDATE
       (consumers MUST stamp the query date): a snapshot-grain number no longer
       renders a bare hand-maintained time claim -- the LIVE query date rides
       alongside it. The base prose is preserved verbatim (unweighted sections and
       sections without a snapshot stamp render exactly as before).
    2. PROVENANCE line (C2 badge): the weights_version + asOf disclosure for a
       weighted section (:func:`_provenance_line_html`); "" for unweighted.
    3. BAND line (Sprint 5, behind the named GATE-B flag ``render_nsr_band``,
       lands OFF): the weight-ignorance band disclosure for a weighted section
       (:func:`_band_line_html`); "" while the flag is OFF (the shipped
       default -- byte-identical to pre-band by construction), and "" for
       unweighted sections / absent / not-applicable bands even when ON. Placed
       DIRECTLY under the provenance line it qualifies (the band is a property
       of those weights).
    4. COVERAGE line (Sprint 4): the OFFER TABLE spend-attribution disclosure
       (:func:`_coverage_line_html`); "" for every other section.

    Returns the concatenated HTML, or "" only when there is nothing to show.
    """
    subtitle = _SECTION_SUBTITLES.get(section.name, "")
    subtitle_html = ""
    if subtitle:
        stamped = html.escape(subtitle)
        if section.synced_at:
            stamped = f"{stamped} · as of {html.escape(section.synced_at)}"
        subtitle_html = f'<div class="section-subtitle">{stamped}</div>'
    provenance_html = _provenance_line_html(section.weights_version, section.synced_at)
    band_html = _band_line_html(section)
    coverage_html = _coverage_line_html(section)
    return subtitle_html + provenance_html + band_html + coverage_html


# ---------------------------------------------------------------------------
# HtmlRenderer -- sole StructuredDataRenderer implementation (v1)
# ---------------------------------------------------------------------------


class HtmlRenderer:
    """Renders DataSection list into a self-contained HTML document.

    All CSS is inlined. No external resources. Zero dependencies beyond
    the Python standard library.
    """

    @property
    def content_type(self) -> str:
        return "text/html"

    @property
    def file_extension(self) -> str:
        return "html"

    def render_document(
        self,
        *,
        title: str,
        metadata: dict[str, str],
        sections: list[DataSection],
        footer: dict[str, str] | None = None,
    ) -> str:
        """Render a complete self-contained HTML document.

        Args:
            title: Document title (displayed in header and <title>).
            metadata: Key-value pairs for the header info block.
            sections: Ordered list of DataSection objects.
            footer: Key-value pairs for the footer block. None omits footer.

        Returns:
            Complete HTML string.
        """
        parts: list[str] = []
        parts.append(self._render_doctype_and_head(title))
        parts.append("<body>")
        parts.append('<div class="toast" id="toast">Copied</div>')
        parts.append('<div class="layout">')
        parts.append(self._render_sidebar(sections))
        parts.append('<main class="main-content">')
        parts.append(self._render_header(title, metadata))
        parts.append(self._render_kpi_cards(sections))

        for section in sections:
            if section.error is not None:
                parts.append(self._render_error_section(section))
            elif (
                section.rows is None
                or (not section.rows and section.empty_message)
                or not section.rows
            ):
                parts.append(self._render_empty_section(section))
            else:
                parts.append(self._render_table_section(section))

        if footer is not None:
            parts.append(self._render_footer(footer))

        parts.append("</main>")
        parts.append("</div>")  # close layout
        parts.append("</body>")
        parts.append("</html>")
        return "\n".join(parts) + "\n"

    # --- Private rendering methods ---

    def _render_doctype_and_head(self, title: str) -> str:
        escaped_title = html.escape(title)
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en" data-theme="light">\n'
            "<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"<title>{escaped_title}</title>\n"
            f"<style>\n{_CSS}\n</style>\n"
            f"<script>\n{_JS}\n</script>\n"
            "</head>"
        )

    def _render_sidebar(self, sections: list[DataSection]) -> str:
        parts: list[str] = ['<nav class="sidebar">']
        parts.append('<div class="nav-section-label">Sections</div>')
        for section in sections:
            sid = _slugify(section.name)
            row_count = section.row_count if section.rows else 0
            parts.append(
                f'<a href="#{sid}" class="nav-link">'
                f"{html.escape(section.name)}"
                f'<span class="badge">{row_count}</span></a>'
            )
        parts.append("</nav>")
        return "\n".join(parts)

    def _render_header(self, title: str, metadata: dict[str, str]) -> str:
        # Extract business name from title by splitting on ": "
        business_name = title.split(": ", 1)[1] if ": " in title else title
        escaped_business = html.escape(business_name)

        # Build metadata items
        meta_parts: list[str] = []
        for k, v in metadata.items():
            if k == "Offer":
                asana_url = f"https://app.asana.com/0/0/{html.escape(v)}"
                meta_parts.append(
                    f'<strong>{html.escape(k)}:</strong> <a href="{asana_url}">View in Asana</a>'
                )
            else:
                meta_parts.append(f"<strong>{html.escape(k)}:</strong> {html.escape(v)}")
        meta_html = " &nbsp;&bull;&nbsp; ".join(meta_parts)

        parts = [
            '<header class="report-header">',
            f'<h1 class="report-title">{escaped_business}</h1>',
            f'<div class="report-meta">{meta_html}</div>',
            '<div class="header-actions">',
            '<div class="search-wrap">',
            '<input type="text" id="global-search" placeholder="Search rows..." '
            'oninput="onSearch(this.value)">',
            '<span class="search-clear" id="search-clear" onclick="clearSearch()">&times;</span>',
            "</div>",
            '<span class="search-count" id="search-count"></span>',
            '<button class="btn" onclick="window.print()">Print</button>',
            '<button class="btn" id="theme-btn" onclick="toggleTheme()">Dark Mode</button>',
            '<button class="btn" onclick="expandAll()">Expand All</button>',
            '<button class="btn" onclick="collapseAll()">Collapse All</button>',
            "</div>",
            "</header>",
        ]
        return "\n".join(parts)

    @staticmethod
    def _extract_numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
        """Return float values for *key* from *rows*, skipping None and non-numeric."""
        return [
            float(r[key])
            for r in rows
            if r.get(key) is not None and isinstance(r.get(key), (int, float))
        ]

    def _render_kpi_cards(self, sections: list[DataSection]) -> str:
        summary_section: DataSection | None = None
        by_week_section: DataSection | None = None

        for s in sections:
            if s.name == "SUMMARY" and s.rows:
                summary_section = s
            elif s.name == "BY WEEK" and s.rows:
                by_week_section = s

        if summary_section is None and by_week_section is None:
            return ""

        cards: list[str] = []

        # Extract SUMMARY row
        summary_row: dict[str, Any] = {}
        if summary_section and summary_section.rows:
            summary_row = summary_section.rows[0]

        # Extract BY WEEK rows
        week_rows: list[dict[str, Any]] = []
        if by_week_section and by_week_section.rows:
            week_rows = by_week_section.rows

        # Card 1: CPL
        cpl_val = summary_row.get("cpl")
        if cpl_val is not None and isinstance(cpl_val, (int, float)):
            cards.append(self._kpi_card("CPL", f"${cpl_val:,.2f}", "Cost per lead"))
        else:
            cards.append(self._kpi_card("CPL", "n/a", "Awaiting data"))

        # Card 2: Booking Rate (with sparkline)
        br_val = summary_row.get("booking_rate")
        sparkline_svg = ""
        if week_rows:
            br_values = self._extract_numeric_values(week_rows, "booking_rate")
            if br_values:
                sparkline_svg = self._render_sparkline(br_values)

        if br_val is not None and isinstance(br_val, (int, float)):
            cards.append(
                self._kpi_card(
                    "Booking Rate",
                    f"{br_val * 100:.2f}%",
                    "Leads &rarr; scheduled",
                    sparkline=sparkline_svg,
                )
            )
        else:
            cards.append(self._kpi_card("Booking Rate", "n/a", "Awaiting data"))

        # Card 3: CPS
        cps_val = summary_row.get("cps")
        if cps_val is not None and isinstance(cps_val, (int, float)):
            cards.append(self._kpi_card("CPS", f"${cps_val:,.2f}", "Cost per show"))
        else:
            cards.append(self._kpi_card("CPS", "n/a", "Awaiting data"))

        # Card 4: ROAS
        roas_val = summary_row.get("roas")
        if roas_val is not None and isinstance(roas_val, (int, float)):
            cards.append(self._kpi_card("ROAS", f"{roas_val:.2f}x", "Return on ad spend"))
        else:
            cards.append(self._kpi_card("ROAS", "n/a", "Awaiting data"))

        # Card 5: Best Week
        if week_rows:
            br_pairs: list[tuple[float, str]] = [
                (float(r["booking_rate"]), str(r.get("period_label", "")))
                for r in week_rows
                if r.get("booking_rate") is not None
                and isinstance(r.get("booking_rate"), (int, float))
            ]
            if br_pairs:
                best_val, best_label = max(br_pairs, key=lambda p: p[0])
                cards.append(
                    self._kpi_card(
                        "Best Week",
                        f"{best_val * 100:.2f}%",
                        html.escape(str(best_label)),
                    )
                )
            else:
                cards.append(self._kpi_card("Best Week", "n/a", "Awaiting data"))
        else:
            cards.append(self._kpi_card("Best Week", "n/a", "Awaiting data"))

        # Card 6: Spend Trend
        if week_rows:
            spend_values = self._extract_numeric_values(week_rows, "spend")
            if len(spend_values) >= 2:
                recent = spend_values[-12:] if len(spend_values) > 12 else spend_values
                prior_start = max(0, len(spend_values) - 24)
                prior_end = max(0, len(spend_values) - 12)
                prior = spend_values[prior_start:prior_end] if prior_end > prior_start else []
                recent_sum = sum(recent)
                prior_sum = sum(prior) if prior else 0

                if prior_sum > 0:
                    pct_change = (recent_sum - prior_sum) / prior_sum
                    if pct_change > 0.05:
                        arrow = "&uarr;"
                        css_class = "trend-up"
                    elif pct_change < -0.05:
                        arrow = "&darr;"
                        css_class = "trend-down"
                    else:
                        arrow = "&rarr;"
                        css_class = ""
                    cards.append(
                        self._kpi_card(
                            "Spend Trend",
                            f'<span class="{css_class}">{arrow}</span>',
                            "vs prior 12 weeks",
                        )
                    )
                else:
                    cards.append(self._kpi_card("Spend Trend", "n/a", "Awaiting data"))
            else:
                cards.append(self._kpi_card("Spend Trend", "n/a", "Awaiting data"))
        else:
            cards.append(self._kpi_card("Spend Trend", "n/a", "Awaiting data"))

        return '<div class="kpi-grid">\n' + "\n".join(cards) + "\n</div>"

    def _kpi_card(
        self,
        label: str,
        value: str,
        subtitle: str,
        sparkline: str = "",
    ) -> str:
        parts = [
            '<div class="kpi-card">',
            f'<div class="kpi-label">{html.escape(label)}</div>',
            f'<div class="kpi-value">{value}</div>',
            f'<div class="kpi-sub">{subtitle}</div>',
        ]
        if sparkline:
            parts.append(f'<div class="kpi-sparkline">{sparkline}</div>')
        parts.append("</div>")
        return "\n".join(parts)

    def _render_sparkline(self, values: list[float]) -> str:
        if not values:
            return ""
        width = 140
        height = 36
        padding = 2
        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val if max_val != min_val else 1.0

        points: list[str] = []
        n = len(values)
        for i, v in enumerate(values):
            x = padding + (i / max(n - 1, 1)) * (width - 2 * padding)
            y = height - padding - ((v - min_val) / val_range) * (height - 2 * padding)
            points.append(f"{x:.1f},{y:.1f}")

        polyline_points = " ".join(points)
        return (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<polyline points="{polyline_points}" fill="none" '
            f'stroke="var(--accent)" stroke-width="1.5" />'
            f"</svg>"
        )

    def _render_table_section(self, section: DataSection) -> str:
        rows = section.rows or []
        columns = _discover_columns(rows)
        columns = _reorder_columns(columns, COLUMN_ORDER.get(section.name))

        if not columns:
            return self._render_empty_section(section)

        # Pre-compute alignment class per column (O(columns) instead of O(rows*columns))
        align_by_col = {col: _column_align_class(rows, col) for col in columns}

        sid = _slugify(section.name)
        is_expanded = section.name in _DEFAULT_EXPANDED_SECTIONS
        collapsed_class = "" if is_expanded else " collapsed"

        # Build header cells with sort, tooltips, and alignment
        header_cells: list[str] = []
        for col_idx, col in enumerate(columns):
            align_cls = align_by_col[col]
            tooltip = _COLUMN_TOOLTIPS.get(col)
            title_attr = f' title="{html.escape(tooltip)}"' if tooltip else ""
            display_label = html.escape(_to_title_case(col))
            cls = align_cls
            header_cells.append(
                f"<th onclick=\"sortTable('{sid}',{col_idx})\""
                f"{title_attr}"
                f' class="{cls}">'
                f"{display_label}"
                f'<span class="sort-icon"></span></th>'
            )

        # Build body rows with alignment + conditional formatting
        body_rows: list[str] = []
        for row in rows:
            cells: list[str] = []
            for col in columns:
                value = row.get(col)
                align_cls = align_by_col[col]
                cond_cls = _conditional_format_class(value, col)
                # Date columns
                date_cls = ""
                if "period_start" in col or "period_end" in col:
                    date_cls = " date-cell"
                td_class = f"{align_cls} {cond_cls}{date_cls}".strip()
                cell_html = _format_cell_html(value, col)
                cells.append(f'<td class="{td_class}">{cell_html}</td>')
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

        # Subtitle (+ live asOf stamp) + provenance line (Sprint 1, H7)
        subtitle_html = _section_disclosure_html(section)

        # Embedded JSON for Copy TSV (with PII masking)
        json_rows = section.full_rows if section.full_rows is not None else (section.rows or [])
        json_data = json.dumps(_mask_pii_rows(json_rows), default=str)

        parts = [
            f'<section id="{sid}" class="table-section">',
            f'<div class="section-header" onclick="toggleSection(\'{sid}\')">',
            f'<h2>{html.escape(section.name)} <span class="badge">{section.row_count}</span></h2>',
            '<div class="section-controls">',
            f'<button class="copy-btn" onclick="event.stopPropagation();copyTable(\'{sid}\')">Copy TSV</button>',
            f'<span class="toggle-icon{collapsed_class}" id="toggle-{sid}">\u25bc</span>',
            "</div>",
            "</div>",
            f'<div class="section-body{collapsed_class}" id="body-{sid}">',
            subtitle_html,
            '<div class="table-scroll">',
            f'<table class="data-table" id="tbl-{sid}">',
            f"<thead><tr>{''.join(header_cells)}</tr></thead>",
            "<tbody>",
            "\n".join(body_rows),
            "</tbody>",
            "</table>",
            "</div>",
        ]

        if section.truncated and section.total_rows is not None:
            parts.append(
                f'<p class="truncation-note">Showing {section.row_count} '
                f"of {section.total_rows} rows</p>"
            )

        # Embedded JSON data script
        parts.append(f'<script type="application/json" id="data-{sid}">{json_data}</script>')
        parts.append("</div>")
        parts.append("</section>")
        return "\n".join(parts)

    def _render_section_with_body(self, section: DataSection, body_content: str) -> str:
        """Render a section scaffold with the given body_content string."""
        sid = _slugify(section.name)
        is_expanded = section.name in _DEFAULT_EXPANDED_SECTIONS
        collapsed_class = "" if is_expanded else " collapsed"
        subtitle_html = _section_disclosure_html(section)
        return (
            f'<section id="{sid}" class="table-section">\n'
            f'<div class="section-header" onclick="toggleSection(\'{sid}\')">\n'
            f"<h2>{html.escape(section.name)}</h2>\n"
            f'<div class="section-controls">'
            f'<span class="toggle-icon{collapsed_class}" id="toggle-{sid}">\u25bc</span>'
            f"</div>\n"
            "</div>\n"
            f'<div class="section-body{collapsed_class}" id="body-{sid}">\n'
            f"{subtitle_html}\n"
            f"{body_content}\n"
            "</div>\n"
            "</section>"
        )

    def _render_empty_section(self, section: DataSection) -> str:
        message = section.empty_message or "No data available"
        body = f'<p class="empty">{html.escape(message)}</p>'
        return self._render_section_with_body(section, body)

    def _render_error_section(self, section: DataSection) -> str:
        error_text = section.error or "Unknown error"
        body = f'<div class="error-box">{html.escape(error_text)}</div>'
        return self._render_section_with_body(section, body)

    def _render_footer(self, footer: dict[str, str]) -> str:
        items = " &nbsp;&bull;&nbsp; ".join(
            f'<span class="footer-item"><strong>{html.escape(k)}:</strong> {html.escape(v)}</span>'
            for k, v in footer.items()
        )
        return f'<footer class="report-footer">\n{items}\n</footer>'


# ---------------------------------------------------------------------------
# compose_report -- public API (unchanged signature)
# ---------------------------------------------------------------------------

_renderer = HtmlRenderer()


def compose_report(data: InsightsReportData) -> str:
    """Compose a full HTML report from table results.

    Per FR-06: Iterates TABLE_SPECS and applies spec-driven transforms.
    No table-name branching in the main loop body (per D-07).
    """
    masked = mask_phone_number(data.office_phone)
    timestamp = datetime.now(UTC).isoformat()
    metadata: dict[str, str] = {
        "Phone": masked,
        "Vertical": data.vertical,
        "Generated": timestamp,
        "Period": "Daily insights report",
    }
    if data.offer_gid:
        metadata["Offer"] = data.offer_gid

    sections: list[DataSection] = []

    for spec in TABLE_SPECS:
        result = data.table_results.get(spec.table_name)

        # --- Step 1: Validate result (missing / error / empty) ---
        if result is None:
            sections.append(
                DataSection(
                    name=spec.table_name,
                    rows=None,
                    error="[ERROR] missing: Table result not available",
                )
            )
            continue

        if not result.success:
            error_type = result.error_type or "unknown"
            error_msg = result.error_message or "Unknown error"
            sections.append(
                DataSection(
                    name=spec.table_name,
                    rows=None,
                    error=f"[ERROR] {error_type}: {error_msg}",
                )
            )
            continue

        if not result.data:
            sections.append(
                DataSection(
                    name=spec.table_name,
                    rows=[],
                    empty_message=spec.empty_message,
                    # asOf carried even for an empty served section so a
                    # snapshot-grain empty table still stamps its query date; a
                    # genuinely-empty table is never weighted, so weights_version is
                    # None here (the C2 badge is absent, correctly).
                    synced_at=result.synced_at,
                    # Coverage carried for an empty SERVED section too (Sprint 4):
                    # an empty OFFER TABLE window still owes its spend-attribution
                    # disclosure (typically the no_data / not-measured face).
                    coverage=result.coverage,
                    coverage_expected=result.coverage_expected,
                )
            )
            continue

        # --- Step 2: Reconciliation pending detection (per FR-11) ---
        if spec.dispatch_type == DispatchType.RECONCILIATION and _is_payment_data_pending(
            result.data
        ):
            sections.append(
                DataSection(
                    name=spec.table_name,
                    rows=[],
                    empty_message=_RECONCILIATION_PENDING_MESSAGE,
                    synced_at=result.synced_at,
                )
            )
            continue

        # --- Step 3: Start with full data; display_rows diverges ---
        all_rows = result.data
        display_rows = list(all_rows)

        # --- Step 4: Sort (spec.sort_key) ---
        if spec.sort_key is not None:
            _sort_key: str = spec.sort_key
            display_rows = sorted(
                display_rows,
                key=lambda r: r.get(_sort_key) or 0,
                reverse=spec.sort_desc,
            )

        # --- Step 5: Row limit (runtime override > spec default) ---
        row_limit = data.row_limits.get(spec.table_name) or spec.default_limit
        total_rows = len(display_rows)
        if row_limit:
            display_rows = display_rows[:row_limit]
        truncated = row_limit is not None and total_rows > row_limit

        # --- Step 6: Exclude columns (spec.exclude_columns) ---
        if spec.exclude_columns is not None:
            display_rows = [
                {k: v for k, v in row.items() if k not in spec.exclude_columns}
                for row in display_rows
            ]

        # --- Step 7: Display columns whitelist (spec.display_columns) ---
        if spec.display_columns is not None:
            available = [c for c in spec.display_columns if any(c in r for r in display_rows)]
            display_rows = [
                {k: v for k, v in row.items() if k in available} for row in display_rows
            ]

        # --- Step 8: Emit DataSection ---
        # Provenance carried from the TableResult onto the rendered section (H7):
        # weights_version drives the C2 badge (present for weighted sections;
        # guaranteed present by the C2 guard, which refuses a weighted table
        # lacking it BEFORE it reaches here), synced_at stamps the subtitle asOf.
        # Sprint 4: coverage rides the same hop; the OFFER TABLE render discloses
        # the spend-attribution face from it (_coverage_line_html).
        # Sprint 5: the weight-ignorance band rides the same hop, exactly where
        # weights_version rides; it SURFACES only behind the GATE-B flag
        # (_band_line_html, render_nsr_band lands OFF).
        sections.append(
            DataSection(
                name=spec.table_name,
                rows=display_rows,
                row_count=len(display_rows),
                truncated=truncated,
                total_rows=total_rows if truncated else None,
                full_rows=all_rows,
                weights_version=result.weights_version,
                synced_at=result.synced_at,
                coverage=result.coverage,
                coverage_expected=result.coverage_expected,
                band=result.band,
            )
        )

    # Build footer (unchanged)
    elapsed = time.monotonic() - data.started_at
    tables_succeeded = sum(1 for r in data.table_results.values() if r.success)
    tables_failed = len(TABLE_SPECS) - tables_succeeded
    total_tables = tables_succeeded + tables_failed

    footer: dict[str, str] = {
        "Duration": f"{elapsed:.2f}s",
        "Tables": f"{tables_succeeded}/{total_tables}",
    }
    if tables_failed > 0:
        footer["Errors"] = str(tables_failed)
    footer["Version"] = data.version

    title = f"Insights Export: {data.business_name}"

    return _renderer.render_document(
        title=title,
        metadata=metadata,
        sections=sections,
        footer=footer,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Payment indicator columns for reconciliation tables.
# When ALL of these are null across all rows, payment data is pending.
_PAYMENT_INDICATOR_COLUMNS = frozenset(
    {
        "collected",
        "num_invoices",
        "variance",
        "expected_collection",
        "expected_variance",
    }
)

_RECONCILIATION_PENDING_MESSAGE = (
    "Payment reconciliation data is pending Stripe integration. "
    "Spend and budget data is available below."
)


def _is_payment_data_pending(rows: list[dict[str, Any]]) -> bool:
    """Check if all payment indicator columns are null across all rows.

    Returns True when every value for every payment indicator column
    is None (or the column is absent) in every row. This signals that
    Stripe REC-8 has not shipped and payment data is unavailable.
    """
    if not rows:
        return False
    for row in rows:
        for col in _PAYMENT_INDICATOR_COLUMNS:
            if row.get(col) is not None:
                return False
    return True


def _to_title_case(column_name: str) -> str:
    """Convert snake_case column name to display label.

    Checks _DISPLAY_LABELS first for known abbreviations/acronyms,
    then falls back to title-casing.
    """
    label = _DISPLAY_LABELS.get(column_name)
    if label:
        return label
    return column_name.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Field format categories for type-aware cell rendering.
# Maps column names to display format: currency ($12,847.50), rate (3.42%),
# percentage (42.50%), ratio (3.50x), per20k (12.50).
# Fields not listed fall through to comma-grouped int/float defaults.
# Source of truth: autom8y-data InsightsService._PRECISION_RULES + EntityMetrics.
# ---------------------------------------------------------------------------
_FIELD_FORMAT: dict[str, str] = {
    # CURRENCY — $12,847.50
    "spend": "currency",
    "cpl": "currency",
    "cps": "currency",
    "ecps": "currency",
    "cpc": "currency",
    "ltv": "currency",
    "avg_conv": "currency",
    "collected": "currency",
    "variance": "currency",
    "expected_collection": "currency",
    "expected_variance": "currency",
    "offer_cost": "currency",
    "budget": "currency",
    "expected_spend": "currency",
    "projected_spend": "currency",
    "budget_variance": "currency",
    # RATE — stored as decimal ratio 0-1, display as ×100 percent (0.0342 → 3.42%)
    # Aligned with upstream _PRECISION_RULES RATE category (2026-02-22).
    "booking_rate": "rate",
    "sched_rate": "rate",
    # PERCENTAGE — already in percent units (18.36 → 18.36%), do NOT multiply
    # Upstream PercentageFormula outputs 0-100 directly for these fields.
    "ctr": "percentage",
    "lctr": "percentage",
    "conversion_rate": "percentage",
    "ns_rate": "percentage",
    "nc_rate": "percentage",
    "conv_rate": "percentage",
    "nsr_ncr": "percentage",
    "variance_pct": "percentage",
    # RATIO — multiplier notation (3.5 → 3.50x), unbounded
    "roas": "ratio",
    "pacing_ratio": "ratio",
    # PER_20K — comma-grouped decimal, no symbol
    "lp20m": "per20k",
    "sp20m": "per20k",
    "esp20m": "per20k",
    "ltv20m": "per20k",
}


def _format_cell_html(value: Any, column: str = "") -> str:
    """Format a single cell value for HTML table display.

    Applies type-aware formatting based on column name:
    - Currency fields: $12,847.50
    - Rate fields (stored as decimal): 3.42%
    - Percentage fields (already in %): 42.50%
    - Ratio fields: 3.50x
    - Per-20k fields: 12.50
    - Other integers: comma-grouped (45,000)
    - Other floats: comma-grouped 2dp (123.46)

    None values render as a styled dash indicator.
    All output is HTML-escaped to prevent XSS.

    Args:
        value: Cell value (may be None).
        column: Column name for format lookup (default "" for backward compat).

    Returns:
        HTML-safe string for table cell content.
    """
    if value is None:
        return '<span class="dash">\u2014</span>'

    # PII: mask phone columns before any other formatting
    if column in _PII_PHONE_COLUMNS and isinstance(value, str):
        return html.escape(mask_phone_number(value))

    fmt = _FIELD_FORMAT.get(column, "")

    if isinstance(value, (int, float)):
        if fmt == "currency":
            return html.escape(f"${value:,.2f}")
        if fmt == "rate":
            return html.escape(f"{value * 100:.2f}%")
        if fmt == "percentage":
            return html.escape(f"{value:.2f}%")
        if fmt == "ratio":
            return html.escape(f"{value:.2f}x")
        if fmt == "per20k":
            return html.escape(f"{value:,.2f}")
        # Fallback: comma-grouped int or 2dp float
        if isinstance(value, int):
            return html.escape(f"{value:,}")
        return html.escape(f"{value:,.2f}")

    return html.escape(str(value))


def _mask_pii_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a shallow copy of *rows* with PII phone columns masked."""
    if not rows:
        return rows
    # Fast path: check if any PII columns are present in the first row
    pii_cols = _PII_PHONE_COLUMNS & rows[0].keys()
    if not pii_cols:
        return rows
    masked: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        for col in pii_cols:
            val = r.get(col)
            if isinstance(val, str):
                r[col] = mask_phone_number(val)
        masked.append(r)
    return masked


def _discover_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Discover all column names from rows, preserving first-seen order.

    Handles heterogeneous rows where different rows may have different
    key sets. Returns the union of all keys.
    """
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                columns.append(key)
                seen.add(key)
    return columns


def _reorder_columns(
    columns: list[str],
    preferred_leading: list[str] | None = None,
) -> list[str]:
    """Reorder *columns* so that *preferred_leading* entries come first.

    Preferred columns that do not appear in *columns* are silently
    skipped.  The relative order of remaining columns is preserved.

    Args:
        columns: Column names in their current order.
        preferred_leading: Columns to move to the front (if present).

    Returns:
        New list with leading columns first, then the rest.
    """
    if not preferred_leading:
        return columns
    leading = [c for c in preferred_leading if c in columns]
    remaining = [c for c in columns if c not in preferred_leading]
    return leading + remaining


def _slugify(name: str) -> str:
    """Convert a section name to a URL-safe ID slug.

    E.g., "BY QUARTER" -> "by-quarter", "ASSET TABLE" -> "asset-table"
    """
    return name.lower().replace(" ", "-")


def _column_align_class(rows: list[dict[str, Any]], column: str) -> str:
    """Determine CSS alignment class for a column based on value types.

    Numeric columns (int/float) get right alignment; text columns get left.
    Checks the first non-None value in the column to determine type.
    """
    for row in rows:
        val = row.get(column)
        if val is not None:
            if isinstance(val, (int, float)):
                return "num"
            return ""
    return ""


def _conditional_format_class(value: Any, column: str) -> str:
    """Return CSS class for conditional formatting based on threshold rules.

    Returns 'br-green', 'br-yellow', 'br-red', or '' (no formatting).
    """
    thresholds = _CONDITIONAL_FORMAT_THRESHOLDS.get(column)
    if thresholds is None or not isinstance(value, (int, float)):
        return ""
    green_threshold, yellow_threshold = thresholds
    if value >= green_threshold:
        return "br-green"
    if value >= yellow_threshold:
        return "br-yellow"
    return "br-red"


# ---------------------------------------------------------------------------
# Static assets -- loaded once at import time, inlined into generated HTML
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parent / "static"
_CSS = (_STATIC_DIR / "insights_report.css").read_text(encoding="utf-8").rstrip("\n")
_JS = (_STATIC_DIR / "insights_report.js").read_text(encoding="utf-8").rstrip("\n")
