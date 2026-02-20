# SPIKE: Formatter Protocol -- The Moonshot Perspective

```yaml
id: SPIKE-FORMATTER-PROTOCOL-MOONSHOT
status: COMPLETE
date: 2026-02-20
timebox: 2h
author: claude (native mode)
relates_to: [SPIKE-ATTACHMENT-FORMAT-EVAL, INTEGRATE-HTML-REPORTS]
challenges: integration-researcher evaluation of Option B (Formatter Protocol)
```

---

## Question

The integration researcher evaluated three options for the insights_export format change and dismissed Option B (Formatter Protocol) as "premature abstraction" with 6/10 confidence. The specific claim was:

> "There is no evidence of a second output format need. The spike explicitly stated: 'CSV is the correct format for conversation_audit (single table, opens in Excel). No change needed there.' A formatter protocol would serve exactly one implementation."

**This spike pushes back on that evaluation.** The question is not "do we have a second format today?" but rather: **what value surfaces emerge when we treat structured data presentation as a first-class platform concern?**

### What We're Trying to Learn

1. How many data surfaces exist in autom8y-asana that produce structured data for human consumption?
2. What does a Formatter protocol look like when scoped to the full system, not just insights_export?
3. Does the moonshot architecture (2027 platform primitives) suggest a formatting abstraction?
4. What is the real cost delta between Option A (in-place replacement) and a well-scoped protocol?

### What Decision This Informs

Whether to adopt a Formatter protocol as part of the HTML migration, or to do in-place replacement now and potentially extract a protocol later.

---

## Findings

### 1. Complete Data Surface Inventory

The integration researcher scoped narrowly: insights_export produces markdown, conversation_audit produces CSV. Only two workflows, only two formats. But that framing misses the full picture.

Here is every data surface in autom8y-asana that produces structured data for consumption:

| # | Surface | Output Format | Consumer | Data Shape |
|---|---------|--------------|----------|------------|
| 1 | **insights_export** workflow | `.md` attachment (migrating to `.html`) | Human (download from Asana) | Header + 10 tables + footer |
| 2 | **conversation_audit** workflow | `.csv` attachment | Human (download from Asana, open in Excel) | Flat CSV rows |
| 3 | **section_timelines** endpoint | JSON API response | Machine (downstream service) | `list[OfferTimelineEntry]` |
| 4 | **dataframes** endpoint | JSON or Polars-JSON | Machine (downstream service) | `list[dict]` with pagination |
| 5 | **query/rows** endpoint | JSON API response | Machine (downstream service) | Filtered row dicts |
| 6 | **query/aggregate** endpoint | JSON API response | Machine (downstream service) | Grouped aggregates |
| 7 | **WorkflowResult.to_response_dict()** | JSON Lambda response | Machine (scheduler/API) | Summary counts + metadata |
| 8 | **Dry-run report_preview** | Truncated string in metadata | Human (API response inspection) | First 2000 chars of report |

Surfaces 1-2 are human-facing with file attachments. Surfaces 3-7 are machine-facing JSON APIs. Surface 8 is a hybrid.

**Critical observation**: The integration researcher was correct that only surfaces 1-2 produce file attachments. But the evaluation question was framed too narrowly. The question is not "how many file formats do we need?" but "how many ways does this system present structured data to humans?"

### 2. The Hidden Second Consumer: Section Timelines

The section_timelines endpoint (surface 3) returns structured data via JSON API today. But consider the use case: it computes `active_section_days` and `billable_section_days` for every offer in the Business Offers project across a date range. This is **billing data**.

Who consumes billing data? Ultimately, a human looks at it. The current flow is:

```
section_timelines JSON API
    -> downstream service consumes
    -> (presumably) renders in some UI or report
```

What if the downstream consumer wants this data as a downloadable report? An Excel export? A PDF invoice? The data is already computed by `SectionTimeline.active_days_in_period()` and `SectionTimeline.billable_days_in_period()`. The only missing piece is a presentation layer.

This is not speculative. The section timeline feature was shipped 2026-02-19 (yesterday). The data model (`OfferTimelineEntry`) has `offer_gid`, `office_phone`, `active_section_days`, `billable_section_days`. This is a natural candidate for a formatted export -- a billing summary attachment on a Business task, for example.

### 3. The Real Cost of "Premature Abstraction"

The integration researcher estimated Option B at 4-5 days, 6/10 confidence. That estimate included:

- 0.5 day: Design + implement protocol
- 0.5 day: Keep + refactor markdown formatter (dead code)
- 0.5 day: Config/selection mechanism
- 1-1.5 days: Test suite for both formatters + protocol conformance
- Total overhead vs Option A: ~2 extra days

But that estimate was based on the wrong protocol design. The researcher proposed:

```python
class ReportFormatter(Protocol):
    def compose_report(self, data: InsightsReportData) -> str: ...
    @property
    def content_type(self) -> str: ...
    @property
    def file_extension(self) -> str: ...
    @property
    def attachment_pattern(self) -> str: ...
```

This is tightly coupled to insights_export. It takes `InsightsReportData` as input -- a type that only exists for the insights workflow. No other surface could use this protocol. The researcher was right to dismiss THIS protocol as premature.

### 4. A Better Protocol: Structured Data Renderer

Instead of a protocol tied to InsightsReportData, consider one tied to the universal shape that ALL data surfaces already share: `list[dict[str, Any]]` with metadata.

```python
from typing import Any, Protocol


class StructuredDataRenderer(Protocol):
    """Renders tabular data sections into a formatted document."""

    @property
    def content_type(self) -> str:
        """MIME type of the rendered output (e.g., 'text/html', 'text/csv')."""
        ...

    @property
    def file_extension(self) -> str:
        """File extension without dot (e.g., 'html', 'csv', 'txt')."""
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


@dataclass(frozen=True)
class DataSection:
    """A named section containing tabular data or a status message."""

    name: str
    rows: list[dict[str, Any]] | None  # None = error/empty
    row_count: int = 0
    truncated: bool = False
    total_rows: int | None = None  # If truncated, the full count
    error: str | None = None  # If failed, the error message
    empty_message: str | None = None  # Custom empty state text
```

This protocol:
- Takes `list[dict[str, Any]]` -- the universal data shape from `InsightsResponse.data`, `ExportResult.csv_content` (after parsing), and `OfferTimelineEntry.model_dump()`
- Is not coupled to any specific workflow
- Can be implemented for HTML, plain text, CSV, and (eventually) XLSX
- Matches the exact data flow that `compose_report()` already uses internally

### 5. What This Enables (The Moonshot View)

With `StructuredDataRenderer` as a platform concern:

**Near-term (the HTML migration itself)**:
- `HtmlRenderer` implements `StructuredDataRenderer` for insights_export
- `compose_report()` becomes a thin adapter: unpack `InsightsReportData` into `DataSection` list, call `renderer.render_document()`
- insights_export gains format flexibility via dependency injection, not if/else

**Medium-term (next 3-6 months)**:
- Section timeline billing exports: feed `list[OfferTimelineEntry]` through `HtmlRenderer` or a `CsvRenderer` and attach to Business tasks
- Workflow result summaries: render `WorkflowResult` metadata as a formatted report attachment for audit trail
- Dry-run previews: use a `PlainTextRenderer` for the 2000-char `report_preview` field instead of truncating raw markdown/HTML

**Long-term (aligned with MOONSHOT-autom8y 2027 vision)**:
- Extract `StructuredDataRenderer` + `HtmlRenderer` into `autom8y-reports` package
- Any satellite can generate formatted attachments for any Asana task
- Consistent presentation layer across all autom8 services
- Dashboard/report generation becomes a platform primitive

### 6. Implementation Cost Delta: Actually Small

Here is the real cost comparison:

**Option A (In-Place HTML Replacement): 2-3 days**
- Rewrite `insights_formatter.py` to emit HTML: 1 day
- CSS template: 0.5 day
- Rewrite tests: 0.5-1 day
- Update references: 0.5 day

**Option A+ (In-Place HTML + Protocol extraction): 2.5-3.5 days**
- Define `StructuredDataRenderer` protocol + `DataSection` dataclass: 2 hours
- Implement `HtmlRenderer` (same HTML as Option A): 1 day
- Write `compose_report()` adapter (unpack InsightsReportData -> DataSections): 2 hours
- CSS template: 0.5 day
- Rewrite tests (same as Option A, plus 3-4 protocol conformance tests): 0.5-1 day
- Update references: 0.5 day

**Delta: 0.5 days** (half a day, not the 2 days the integration researcher estimated)

The researcher's 2-day overhead estimate included keeping the markdown formatter alive and building a configuration mechanism. Both are unnecessary:
- Drop the markdown formatter entirely (the spike proved it's "strictly worse")
- No configuration mechanism needed -- the renderer is injected via constructor, not configured via env var

### 7. Why the Integration Researcher's Framing Was Wrong

The integration researcher asked: "Do we need the markdown formatter going forward?" and correctly answered "No." They then concluded: "A formatter protocol would serve exactly one implementation."

But the right question is: "Will we ever need to render `list[dict[str, Any]]` into a human-readable document format from a surface other than insights_export?"

The answer to that question is almost certainly yes:
- Section timeline billing exports are a natural next feature
- Workflow audit trails benefit from formatted summaries
- The moonshot platform vision includes portable report generation
- Every workflow that produces structured data is a candidate

The "one implementation" framing counts HTML as the only format. But even within HTML alone, there are distinct renderers: a 10-table insights report looks different from a 4-column billing summary. The protocol enables composition, not just format switching.

---

## Comparison Matrix

| Criterion | Option A (In-Place) | Option A+ (Protocol) |
|-----------|:---:|:---:|
| Implementation effort | 2-3 days | 2.5-3.5 days |
| Immediate value | Full (HTML reports work) | Full (same HTML reports) |
| Code reuse for new surfaces | None | High |
| Testing surface for formatter | Ad-hoc string assertions | Protocol conformance + string assertions |
| Coupling to InsightsReportData | Complete | Adapter only |
| Path to platform extraction | Major refactor | Direct extraction |
| Lines of new abstraction code | 0 | ~40 (protocol + DataSection) |
| Risk of premature abstraction | N/A | Low (protocol is 15 lines, DataSection is 25 lines) |

---

## Recommendation

**Adopt Option A+ (In-Place HTML Replacement with Protocol Extraction).**

### Rationale

1. **The cost delta is 0.5 days, not 2 days.** The integration researcher overestimated by including unnecessary work (keeping markdown alive, building config mechanism).

2. **The protocol is 40 lines of code.** A 15-line Protocol class and a 25-line frozen dataclass. This is not an abstraction layer -- it is a type contract. The cognitive overhead is near zero.

3. **The data shape already exists.** Every data surface in the system already works with `list[dict[str, Any]]`. The protocol formalizes what the code already does informally.

4. **Section timeline exports are a natural next consumer.** The feature shipped yesterday. Billing data in JSON is useful; billing data as a downloadable HTML report attached to a Business task is more useful. The protocol makes this a 2-hour task instead of a 2-day task.

5. **It aligns with the platform vision.** MOONSHOT-autom8y envisions platform primitives that eliminate boilerplate. A `StructuredDataRenderer` protocol in `autom8y-reports` is a natural member of that family (alongside `autom8y-http`, `autom8y-telemetry`, `autom8y-config`).

6. **The real risk of premature abstraction is 40 wasted lines, not 2 wasted days.** If the protocol is never reused, we have a 15-line Protocol class and a 25-line dataclass that are used by exactly one renderer. The cost of being wrong is negligible. The cost of being right is significant reuse across the system.

### What NOT To Do

- Do NOT keep the markdown formatter. It is dead code.
- Do NOT build a format selection mechanism (env var, config). The renderer is injected at construction time -- the workflow knows which renderer it uses.
- Do NOT make the protocol generic or extensible beyond what `DataSection` covers. Start minimal.
- Do NOT extract to a separate package yet. Keep it in `src/autom8_asana/automation/workflows/` until a second satellite needs it.

### Confidence Level

**High (8/10).** The protocol is small enough that the downside of being wrong is negligible. The upside of being right -- reusable rendering across data surfaces -- is substantial. The section timeline billing export is a concrete near-term consumer, not a hypothetical future need.

---

## Follow-Up Actions

1. **During the HTML migration**: Define `StructuredDataRenderer` protocol and `DataSection` dataclass in a new `insights_renderer.py` (or co-locate in `insights_formatter.py`)
2. **Implement `HtmlRenderer`** as the sole implementation
3. **Adapt `compose_report()`** to unpack `InsightsReportData` into `DataSection` list and delegate to `HtmlRenderer`
4. **After migration stabilizes**: Evaluate section timeline billing export as the second consumer
5. **If second consumer materializes**: Consider extracting to `autom8_asana/rendering/` package-level module
6. **If platform extraction is warranted**: Move to `autom8y-reports` package per MOONSHOT timeline

---

## Appendix: Concrete Protocol Usage Sketch

### insights_export (current consumer)

```python
# In insights_export.py _process_offer():
renderer = HtmlRenderer()  # or injected via __init__

# Adapter: unpack InsightsReportData -> DataSection list
sections = [
    DataSection(
        name=table_name,
        rows=result.data,
        row_count=result.row_count,
        error=result.error_message if not result.success else None,
        truncated=(row_limits.get(table_name) is not None
                   and result.row_count > row_limits.get(table_name, 0)),
        total_rows=result.row_count,
    )
    for table_name, result in table_results.items()
]

html_content = renderer.render_document(
    title=f"Insights Export: {business_name}",
    metadata={
        "Phone": masked_phone,
        "Vertical": vertical,
        "Generated": timestamp,
        "Period": "Daily insights report",
    },
    sections=sections,
    footer={
        "Duration": f"{elapsed:.2f}s",
        "Tables": f"{tables_succeeded}/{total_tables}",
        "Version": WORKFLOW_VERSION,
    },
)
```

### section_timeline billing export (future consumer)

```python
# Hypothetical billing_export.py
renderer = HtmlRenderer()

entries = await get_or_compute_timelines(client, project_gid, ...)

sections = [
    DataSection(
        name="Billing Summary",
        rows=[entry.model_dump() for entry in entries],
        row_count=len(entries),
    )
]

html_content = renderer.render_document(
    title=f"Billing Report: {period_start} to {period_end}",
    metadata={
        "Project": "Business Offers",
        "Period": f"{period_start} to {period_end}",
        "Generated": datetime.now(UTC).isoformat(),
    },
    sections=sections,
)
```

The protocol makes the second use case a ~20-line function. Without it, it is a copy of insights_formatter.py with different data unpacking.
