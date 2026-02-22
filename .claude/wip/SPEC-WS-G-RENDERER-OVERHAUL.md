# WS-G Spec: Insights Export Renderer Overhaul

**Status**: APPROVED (2026-02-20)
**Scope**: Rewrite HtmlRenderer to spike fidelity with interactive features
**Absorbs**: WS-C (display labels), WS-D (ASSET TABLE caps + transcript overflow)

---

## Personas & Usage Context

- **Multiple personas**: scanners (KPIs), divers (sort/filter), exporters (Copy TSV)
- **All 3 action paths**: flag in Asana, dig into tables, export to spreadsheets
- **50-200 offers daily**, wide data variance (sparse new offers to 300+ asset mature offers)
- **File size**: ~200KB per report, not a concern. JS/CSS as template constants for CPU efficiency.

---

## KPI Cards (6 cards, 2 rows of 3)

| Card | Source | Display | Null State |
|------|--------|---------|------------|
| CPL | SUMMARY.cpl | $XX.XX | "n/a" + "Awaiting data" |
| Booking Rate | SUMMARY.booking_rate | XX.X% + sparkline (BY WEEK series) | "n/a" + "Awaiting data" |
| CPS | SUMMARY.cps | $XX.XX | "n/a" + "Awaiting data" |
| ROAS | SUMMARY.roas | X.XXx | "n/a" + "Awaiting data" |
| Best Week | max(BY WEEK.booking_rate) | XX.X% + date | "n/a" + "Awaiting data" |
| Spend Trend | BY WEEK last 12 vs prior 12 | arrow (up/down/flat) | "n/a" + "Awaiting data" |

### Sparkline Spec
- Source: BY WEEK rows, booking_rate values
- SVG polyline, ~140x36px
- Stroke color: accent color (theme-aware)

### Spend Trend Calculation
- Compare sum of spend for most recent 12 weeks vs prior 12 weeks
- Up arrow if recent > prior by >5%, down if <-5%, flat otherwise

---

## Period Table Columns (12 visible of 24 total)

Display columns (BY WEEK, BY MONTH, BY QUARTER):
```
period_label, period_start, period_end, spend, leads, cpl, scheds,
booking_rate, cps, conv_rate, ctr, ltv
```

Copy TSV exports ALL 24 columns from underlying data.

---

## ASSET TABLE Column Policy

**Keep**: `asset_id`, `asset_name` + all metric columns (spend, imp, ctr, leads, cpl, booking_rate, etc.)
**Exclude**: `offer_id`, `office_phone`, `vertical`, `transcript`, `is_raw`, `is_generic`, `platform_id`, `disabled`
**Row cap**: 150, sorted by spend desc
**UNUSED ASSETS**: Derived from FULL asset data (before display truncation)

---

## Conditional Formatting (hardcoded universal thresholds)

| Column | Green | Yellow | Red |
|--------|-------|--------|-----|
| booking_rate | >= 0.40 | 0.20-0.40 | < 0.20 |
| conv_rate | >= 0.40 | 0.20-0.40 | < 0.20 |

CSS classes: `.br-green`, `.br-yellow`, `.br-red`

---

## Layout Decisions

| Decision | Choice |
|----------|--------|
| SUMMARY section | Collapsed by default. Note: "See KPI cards above". Raw data via Copy TSV. |
| Default expanded sections | SUMMARY + BY WEEK only |
| Theme | `prefers-color-scheme` media query + manual toggle override |
| Column key | Tooltips on column headers (title attr with full name + definition) |
| Section subtitles | Below header bar, above table content, muted text |
| Copy TSV | Exports ALL columns (full row data), not just visible columns |
| Traceability | Asana offer hyperlink in header metadata |
| Null KPI cards | Show card with "n/a" value + "Awaiting data" subtitle |
| Null table cells | Muted em dash: `<td class="muted"><span class="dash">—</span></td>` |

---

## Interactive Features (from spike)

All implemented as inline JS, no external dependencies:

- **Theme toggle**: CSS custom properties for light/dark, `toggleTheme()`, `prefers-color-scheme` detection
- **Sidebar nav**: Sticky 200px left sidebar with section links + row count badges, scroll spy for active state
- **Collapsible sections**: Click header to toggle, Expand All / Collapse All buttons
- **Sort**: Click column headers, numeric-aware sort (`sortTable()`), sort direction indicators
- **Search**: Global search input with debounce, row filtering, `<mark class="search-hl">` highlighting
- **Copy TSV**: Per-section button, copies FULL row data (all columns), toast notification
- **Print**: `@media print` hides sidebar/controls, expands all collapsed sections, 9px font

---

## CSS Design System (from spike)

### Theme Variables
```
Light: --bg: #fafafa, --surface: #fff, --text: #1a1a1a, --accent: #4a7bb5
Dark:  --bg: #1a1a1a, --surface: #242424, --text: #e8e8e8, --accent: #6fa0d4
```

### Cell Styling
- Numeric: `.num` — `text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono)`
- Date: `.date-cell` — `text-align: center; font-family: var(--mono); color: var(--text-muted)`
- Null: `.muted .dash` — `color: var(--text-dim)`
- Row hover: `color-mix(in srgb, var(--accent) 8%, transparent)`
- Overflow: `td { max-width: 300px; overflow: hidden; text-overflow: ellipsis }`

---

## Section Subtitles

| Section | Subtitle |
|---------|----------|
| SUMMARY | Lifetime performance metrics across all campaigns for this business. |
| APPOINTMENTS | Scheduled appointments from the last 90 days. |
| LEADS | Incoming leads from the last 30 days, excluding those with appointments. |
| LIFETIME RECONCILIATIONS | Financial reconciliation across all time periods. |
| T14 RECONCILIATIONS | Rolling 14-day financial reconciliation windows. |
| BY QUARTER | Quarterly performance trends with key efficiency metrics. |
| BY MONTH | Monthly performance trends with key efficiency metrics. |
| BY WEEK | Weekly performance trends with key efficiency metrics. |
| AD QUESTIONS | Lead-qualifying questions and their conversion impact. |
| ASSET TABLE | Creative performance by individual ad asset over the last 30 days. |
| OFFER TABLE | Offer-level performance metrics over the last 30 days. |
| UNUSED ASSETS | Ad assets with zero spend and zero impressions in the last 30 days. |

---

## Display Labels (_DISPLAY_LABELS)

```python
_DISPLAY_LABELS: dict[str, str] = {
    "n_distinct_ads": "Distinct Ads",
    "cpl": "CPL",
    "cps": "CPS",
    "ecps": "Expected CPS",
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
```

---

## Column Tooltips (_COLUMN_TOOLTIPS)

```python
_COLUMN_TOOLTIPS: dict[str, str] = {
    "cpl": "Cost Per Lead: Total spend ÷ total leads",
    "cps": "Cost Per Show: Total spend ÷ scheduled appointments",
    "booking_rate": "Booking Rate: Scheduled appointments ÷ total leads",
    "roas": "Return on Ad Spend: Revenue ÷ ad spend",
    "ctr": "Click-Through Rate: Clicks ÷ impressions",
    "ltv": "Lifetime Value: Estimated revenue per customer",
    "conv_rate": "Conversion Rate: Conversions ÷ total leads",
    "ns_rate": "No-Show Rate: No-shows ÷ scheduled appointments",
    "nc_rate": "No-Close Rate: No-closes ÷ shown appointments",
    "variance_pct": "Variance %: (Collected - Spend) ÷ Spend × 100",
    # Extend as needed
}
```

---

## Deferred to Phase 2

- **Activity tiles**: n_current_scheduled, booked_t7, leads_t7 (requires data service review)
- **Dynamic metric tooltips**: Tie into autom8y-data metric/dimension registry
- **Per-vertical conditional formatting**: Thresholds by vertical once data supports it
- **Vertical SUMMARY layout**: Key-value definition list presentation

---

## Implementation Notes

### compose_report() Changes Required
- Accept `offer_gid` parameter for Asana link construction
- Sort ASSET TABLE by spend desc before truncation
- Apply `_ASSET_EXCLUDE_COLUMNS` filter
- Apply `_PERIOD_DISPLAY_COLUMNS` filter (display only, Copy TSV gets full data)
- Detect pending reconciliation (already done in WS-A)

### HtmlRenderer Changes
- Complete rewrite of `_render_doctype_and_head()` (theme CSS + JS)
- New `_render_sidebar()` method
- New `_render_kpi_cards()` method
- Rewrite `_render_table_section()` (sort headers, copy TSV, collapse, subtitles)
- New `_render_document()` layout (sidebar + main content flex)
- `_format_cell_html()` null rendering change (em dash)
- Conditional formatting in cell rendering for rate columns

### Data Flow for Copy TSV (All Columns)
- Embed full row data as `<script type="application/json" id="data-{section_id}">` per table
- Copy TSV reads from embedded JSON, not from visible table cells
