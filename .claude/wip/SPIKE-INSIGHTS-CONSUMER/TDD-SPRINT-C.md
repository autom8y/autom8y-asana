# TDD: Sprint C -- Insights Export Structural Improvements

## Overview

Refactor three structural findings (F-03, F-04, F-07) into a declarative, spec-driven design. A new `insights_tables.py` module introduces a `TableSpec` frozen dataclass and a `DispatchType` enum. The 12-table fetch monolith in `insights_export.py` becomes a loop over `TABLE_SPECS`. The interleaved display logic in `insights_formatter.py` becomes a sequential spec-driven transform pipeline. The 29 inline ResolutionContext mock blocks in `test_insights_export.py` consolidate into a shared fixture in `conftest.py`.

## Context

| Artifact | Location |
|----------|----------|
| PRD (binding) | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/PRD-SPRINT-C.md` |
| Export flow review | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/EXPORT-FLOW-REVIEW.md` |
| Sprint A+B commit | `5092d2d` |
| Source: fetch monolith | `src/autom8_asana/automation/workflows/insights_export.py` (lines 717-987) |
| Source: compose_report | `src/autom8_asana/automation/workflows/insights_formatter.py` (lines 749-882) |
| Source: test file | `tests/unit/automation/workflows/test_insights_export.py` (29 inline mock blocks) |

All 10 interview decisions (D-01 through D-10) are binding. This TDD does not re-litigate any of them.

---

## 1. TableSpec Contract

### 1.1 DispatchType Enum (FR-02)

```python
from enum import Enum

class DispatchType(Enum):
    """Discriminator for _fetch_table dispatch routing.

    Each value maps to a distinct DataServiceClient method call.
    Used in a match statement inside _fetch_table to eliminate
    the if/elif chain (per D-04).
    """

    INSIGHTS = "insights"
    """Standard POST /insights call via get_insights_async.
    Parameterized by factory, period, include_unused."""

    APPOINTMENTS = "appointments"
    """GET /appointments via get_appointments_async.
    Parameterized by days, limit."""

    LEADS = "leads"
    """GET /leads via get_leads_async.
    Parameterized by days, limit, exclude_appointments."""

    RECONCILIATION = "reconciliation"
    """GET /reconciliation via get_reconciliation_async.
    Parameterized by period, window_days. Phone filtering
    stays in the dispatcher (per D-02)."""
```

### 1.2 TableSpec Frozen Dataclass (FR-01)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class TableSpec:
    """Declarative specification for a single insights table.

    Unifies fetch dispatch configuration (F-03) and display
    preparation rules (F-04) on a single frozen dataclass (per D-05).
    The D-08 stakeholder override explicitly couples fetch and display
    on one type.

    Fields are divided into four groups:
    - Identity: table_name
    - Fetch: dispatch_type, factory, period, days, limit, exclude_appointments,
             window_days, include_unused
    - Limits: default_limit
    - Display: sort_key, sort_desc, exclude_columns, display_columns, empty_message
    """

    # --- Identity ---
    table_name: str
    """Human-readable table name. Must match TABLE_ORDER names exactly."""

    # --- Fetch configuration ---
    dispatch_type: DispatchType
    """Routing discriminator for _fetch_table (per D-04)."""

    factory: str = "base"
    """Factory parameter for get_insights_async. Only used when
    dispatch_type is INSIGHTS."""

    period: str | None = None
    """Period parameter. For INSIGHTS: passed to get_insights_async.
    For RECONCILIATION: passed to get_reconciliation_async.
    None means omit (APPOINTMENTS, LEADS do not use period)."""

    days: int | None = None
    """Lookback window in days. Used by APPOINTMENTS and LEADS."""

    exclude_appointments: bool = False
    """Exclude appointment leads. Used by LEADS dispatch only."""

    window_days: int | None = None
    """Rolling window size in days for RECONCILIATION dispatch."""

    include_unused: bool = False
    """Include zero-activity assets. Used by INSIGHTS dispatch with
    factory='assets'."""

    # --- Limits ---
    default_limit: int | None = None
    """Default row limit for this table.
    - APPOINTMENTS/LEADS: applied server-side via the limit parameter (per D-03).
    - All others: applied client-side during compose_report display preparation.
    - Runtime row_limits dict overrides this value when provided."""

    # --- Display configuration ---
    sort_key: str | None = None
    """Column name to sort display rows by. None = no sort."""

    sort_desc: bool = True
    """Sort direction. True = descending. Only meaningful when sort_key is set."""

    exclude_columns: frozenset[str] | None = None
    """Columns to exclude from display rows. None = no exclusion.
    Applied after sort and limit. Copy TSV (full_rows) is NOT affected."""

    display_columns: list[str] | None = None
    """Whitelist of columns to show in display. None = show all.
    Applied after exclude_columns. Copy TSV (full_rows) is NOT affected.
    Columns not present in any row are silently omitted."""

    empty_message: str = "No data available"
    """Message shown when the table has zero rows."""
```

### 1.3 TABLE_SPECS Constant (FR-03)

The complete ordered list of 12 `TableSpec` instances, extracted from the current `_fetch_all_tables` parameter combinations and `compose_report` display logic.

```python
TABLE_SPECS: list[TableSpec] = [
    # --- 1. SUMMARY ---
    TableSpec(
        table_name="SUMMARY",
        dispatch_type=DispatchType.INSIGHTS,
        factory="base",
        period="lifetime",
    ),
    # --- 2. APPOINTMENTS ---
    TableSpec(
        table_name="APPOINTMENTS",
        dispatch_type=DispatchType.APPOINTMENTS,
        days=90,
        default_limit=100,
    ),
    # --- 3. LEADS ---
    TableSpec(
        table_name="LEADS",
        dispatch_type=DispatchType.LEADS,
        days=30,
        exclude_appointments=True,
        default_limit=100,
    ),
    # --- 4. LIFETIME RECONCILIATIONS ---
    TableSpec(
        table_name="LIFETIME RECONCILIATIONS",
        dispatch_type=DispatchType.RECONCILIATION,
    ),
    # --- 5. T14 RECONCILIATIONS ---
    TableSpec(
        table_name="T14 RECONCILIATIONS",
        dispatch_type=DispatchType.RECONCILIATION,
        window_days=14,
    ),
    # --- 6. BY QUARTER ---
    TableSpec(
        table_name="BY QUARTER",
        dispatch_type=DispatchType.INSIGHTS,
        factory="base",
        period="quarter",
        display_columns=[
            "period_label", "period_start", "period_end",
            "spend", "leads", "cpl", "scheds", "booking_rate",
            "cps", "conv_rate", "ctr", "ltv",
        ],
    ),
    # --- 7. BY MONTH ---
    TableSpec(
        table_name="BY MONTH",
        dispatch_type=DispatchType.INSIGHTS,
        factory="base",
        period="month",
        display_columns=[
            "period_label", "period_start", "period_end",
            "spend", "leads", "cpl", "scheds", "booking_rate",
            "cps", "conv_rate", "ctr", "ltv",
        ],
    ),
    # --- 8. BY WEEK ---
    TableSpec(
        table_name="BY WEEK",
        dispatch_type=DispatchType.INSIGHTS,
        factory="base",
        period="week",
        display_columns=[
            "period_label", "period_start", "period_end",
            "spend", "leads", "cpl", "scheds", "booking_rate",
            "cps", "conv_rate", "ctr", "ltv",
        ],
    ),
    # --- 9. AD QUESTIONS ---
    TableSpec(
        table_name="AD QUESTIONS",
        dispatch_type=DispatchType.INSIGHTS,
        factory="ad_questions",
        period="lifetime",
    ),
    # --- 10. ASSET TABLE ---
    TableSpec(
        table_name="ASSET TABLE",
        dispatch_type=DispatchType.INSIGHTS,
        factory="assets",
        period="t30",
        default_limit=150,
        sort_key="spend",
        sort_desc=True,
        exclude_columns=frozenset({
            "offer_id", "office_phone", "vertical", "transcript",
            "is_raw", "is_generic", "platform_id", "disabled",
        }),
    ),
    # --- 11. OFFER TABLE ---
    TableSpec(
        table_name="OFFER TABLE",
        dispatch_type=DispatchType.INSIGHTS,
        factory="business_offers",
        period="t30",
    ),
    # --- 12. UNUSED ASSETS ---
    TableSpec(
        table_name="UNUSED ASSETS",
        dispatch_type=DispatchType.INSIGHTS,
        factory="assets",
        period="t30",
        include_unused=True,
        empty_message="No unused assets found",
    ),
]
```

**Derivation notes** (how current source maps to spec fields):

| Table | Source location | Key observations |
|-------|---------------|------------------|
| SUMMARY | `insights_export.py:742-749` | `factory="base"`, `period="lifetime"` |
| APPOINTMENTS | `insights_export.py:750-758` | `method="appointments"` -> `DispatchType.APPOINTMENTS`, `days=90`, `limit=row_limits.get("APPOINTMENTS", 100)` -> `default_limit=100` |
| LEADS | `insights_export.py:759-768` | `method="leads"` -> `DispatchType.LEADS`, `days=30`, `exclude_appointments=True`, `limit=row_limits.get("LEADS", 100)` -> `default_limit=100` |
| LIFETIME RECON | `insights_export.py:769-775` | `method="reconciliation"` -> `DispatchType.RECONCILIATION`, no `window_days` |
| T14 RECON | `insights_export.py:776-783` | `method="reconciliation"`, `window_days=14` |
| BY QUARTER | `insights_export.py:784-792` | `factory="base"`, `period="quarter"`. Display columns from `_PERIOD_DISPLAY_COLUMNS` (line 154-167 of formatter) |
| BY MONTH | `insights_export.py:793-799` | Same as BY QUARTER with `period="month"` |
| BY WEEK | `insights_export.py:800-807` | Same as BY QUARTER with `period="week"` |
| AD QUESTIONS | `insights_export.py:808-815` | `factory="ad_questions"`, `period="lifetime"` |
| ASSET TABLE | `insights_export.py:816-823` | `factory="assets"`, `period="t30"`. Sort: `key=lambda r: r.get("spend") or 0, reverse=True` (formatter line 818-822). Exclude: `_ASSET_EXCLUDE_COLUMNS` (formatter line 140-151). Limit: `DEFAULT_ROW_LIMITS["ASSET TABLE"] = 150` |
| OFFER TABLE | `insights_export.py:824-831` | `factory="business_offers"`, `period="t30"` |
| UNUSED ASSETS | `insights_export.py:832-840` | `factory="assets"`, `period="t30"`, `include_unused=True`. Empty message: `"No unused assets found"` (formatter line 787-790) |

---

## 2. Module Structure (FR-06)

### 2.1 New File: `insights_tables.py`

**Path**: `src/autom8_asana/automation/workflows/insights_tables.py`

**Exports** (via `__all__`):
```python
__all__ = [
    "DispatchType",
    "TableSpec",
    "TABLE_SPECS",
]
```

**Import graph changes**:

```
Before:
  insights_export.py --imports--> insights_formatter.py (TABLE_ORDER, compose_report, ...)

After:
  insights_tables.py   (new: DispatchType, TableSpec, TABLE_SPECS)
       ^        ^
       |        |
  insights_export.py   insights_formatter.py
       |                    |
       +-- imports ----------+ (both import TABLE_SPECS from insights_tables)
```

- `insights_export.py` imports `DispatchType`, `TableSpec`, `TABLE_SPECS` from `insights_tables`
- `insights_formatter.py` imports `TABLE_SPECS` from `insights_tables`
- `insights_formatter.py` removes `TABLE_ORDER` (replaced by `TABLE_SPECS` ordering)
- `insights_export.py` updates its `TABLE_ORDER` import: changes from `insights_formatter.TABLE_ORDER` to `insights_tables.TABLE_SPECS`
- The public alias `TABLE_NAMES` in `insights_export.py` becomes `[s.table_name for s in TABLE_SPECS]`
- No circular import risk: `insights_tables.py` imports only from stdlib (`enum`, `dataclasses`)

### 2.2 Constants Relocated

| Constant | Current location | After |
|----------|-----------------|-------|
| `TABLE_ORDER` | `insights_formatter.py:34-47` | **Deleted**. Replaced by `[s.table_name for s in TABLE_SPECS]`. |
| `_PERIOD_DISPLAY_COLUMNS` | `insights_formatter.py:154-167` | **Deleted**. Values moved to `display_columns` field on BY QUARTER/MONTH/WEEK specs. |
| `_ASSET_EXCLUDE_COLUMNS` | `insights_formatter.py:140-151` | **Deleted**. Values moved to `exclude_columns` field on ASSET TABLE spec. |
| `DEFAULT_ROW_LIMITS` | `insights_export.py:69-73` | **Retained** as runtime override dict. The `default_limit` spec field encodes the same defaults structurally. `DEFAULT_ROW_LIMITS` is still used as the default value for the `row_limits` parameter in `execute_async`. |
| `COLUMN_ORDER` | `insights_formatter.py:51-76` | **Retained** in `insights_formatter.py`. Used by `HtmlRenderer._render_table_section` for column ordering within rendered HTML tables. Not part of `compose_report` display filtering. |
| `_SECTION_SUBTITLES` | `insights_formatter.py:124-137` | **Retained** in `insights_formatter.py`. Used by `HtmlRenderer._render_table_section`. |
| `_DISPLAY_LABELS` | `insights_formatter.py:79-107` | **Retained** in `insights_formatter.py`. Used by `_to_title_case`. |
| `_COLUMN_TOOLTIPS` | `insights_formatter.py:110-121` | **Retained** in `insights_formatter.py`. Used by `HtmlRenderer`. |

---

## 3. Refactored Signatures

### 3.1 `_fetch_all_tables` (Before / After)

**Before** (lines 717-847):
```python
async def _fetch_all_tables(
    self,
    office_phone: str,
    vertical: str,
    row_limits: dict[str, int],
    offer_gid: str,
) -> dict[str, TableResult]:
    results = await asyncio.gather(
        self._fetch_table("SUMMARY", offer_gid, office_phone, vertical, factory="base", period="lifetime"),
        self._fetch_table("APPOINTMENTS", offer_gid, office_phone, vertical, method="appointments", days=90, limit=row_limits.get("APPOINTMENTS", 100)),
        # ... 10 more hand-written calls ...
    )
    table_map: dict[str, TableResult] = {}
    for r in results:
        table_map[r.table_name] = r
    return table_map
```

**After**:
```python
async def _fetch_all_tables(
    self,
    office_phone: str,
    vertical: str,
    row_limits: dict[str, int],
    offer_gid: str,
) -> dict[str, TableResult]:
    """Fetch all tables concurrently using TABLE_SPECS.

    Per FR-04: Iterates TABLE_SPECS and dispatches via asyncio.gather().
    Signature unchanged (per NFR-05: concurrent fetch preserved).
    """
    results = await asyncio.gather(
        *(
            self._fetch_table(
                spec=spec,
                offer_gid=offer_gid,
                office_phone=office_phone,
                vertical=vertical,
                row_limits=row_limits,
            )
            for spec in TABLE_SPECS
        )
    )
    return {r.table_name: r for r in results}
```

### 3.2 `_fetch_table` (Before / After)

**Before** (lines 849-987):
```python
async def _fetch_table(
    self,
    table_name: str,
    offer_gid: str,
    office_phone: str,
    vertical: str,
    *,
    factory: str = "base",
    period: str | None = None,
    method: str | None = None,
    days: int | None = None,
    limit: int | None = None,
    exclude_appointments: bool = False,
    window_days: int | None = None,
    include_unused: bool = False,
) -> TableResult:
    # 4-branch if/elif on method
    if method == "appointments": ...
    elif method == "leads": ...
    elif method == "reconciliation": ...
    else: ...  # standard insights
```

**After**:
```python
async def _fetch_table(
    self,
    spec: TableSpec,
    offer_gid: str,
    office_phone: str,
    vertical: str,
    row_limits: dict[str, int],
) -> TableResult:
    """Fetch a single table with error isolation.

    Per FR-05: Uses match statement on spec.dispatch_type (D-04).
    Reconciliation phone filtering stays in the dispatcher (D-02).
    """
    fetch_start = time.monotonic()

    try:
        # Resolve effective limit: runtime override > spec default > None
        effective_limit = row_limits.get(spec.table_name) or spec.default_limit

        match spec.dispatch_type:
            case DispatchType.APPOINTMENTS:
                response = await self._data_client.get_appointments_async(
                    office_phone,
                    days=spec.days or 90,
                    limit=effective_limit or 100,
                )
            case DispatchType.LEADS:
                response = await self._data_client.get_leads_async(
                    office_phone,
                    days=spec.days or 30,
                    exclude_appointments=spec.exclude_appointments,
                    limit=effective_limit or 100,
                )
            case DispatchType.RECONCILIATION:
                response = await self._data_client.get_reconciliation_async(
                    office_phone,
                    vertical,
                    period=spec.period,
                    window_days=spec.window_days,
                )
                # Defensive phone filtering stays in dispatcher (per D-02).
                # Uses local variable to avoid mutating response (per F-08).
                filtered_data: list[dict[str, Any]] | None = None
                if hasattr(response, "data") and response.data:
                    phones_in_data = {
                        r.get("office_phone")
                        for r in response.data
                        if r.get("office_phone") is not None
                    }
                    if len(phones_in_data) > 1:
                        pre_filter = len(response.data)
                        filtered_data = [
                            r for r in response.data
                            if r.get("office_phone") == office_phone
                        ]
                        logger.info(
                            "insights_export_recon_filtered",
                            offer_gid=offer_gid,
                            table_name=spec.table_name,
                            pre_filter=pre_filter,
                            post_filter=len(filtered_data),
                            unique_phones=len(phones_in_data),
                        )
            case DispatchType.INSIGHTS:
                response = await self._data_client.get_insights_async(
                    factory=spec.factory,
                    office_phone=office_phone,
                    vertical=vertical,
                    period=spec.period or "lifetime",
                    include_unused=spec.include_unused,
                )

        elapsed_ms = (time.monotonic() - fetch_start) * 1000
        # Use filtered_data if reconciliation phone filtering was applied
        if spec.dispatch_type == DispatchType.RECONCILIATION and filtered_data is not None:
            data = filtered_data
        else:
            data = response.data if hasattr(response, "data") else []

        logger.info(
            "insights_export_table_fetched",
            offer_gid=offer_gid,
            table_name=spec.table_name,
            row_count=len(data),
            duration_ms=elapsed_ms,
        )

        return TableResult(
            table_name=spec.table_name,
            success=True,
            data=data,
            row_count=len(data),
        )

    except Exception as exc:
        elapsed_ms = (time.monotonic() - fetch_start) * 1000
        error_type = type(exc).__name__

        logger.warning(
            "insights_export_table_failed",
            offer_gid=offer_gid,
            table_name=spec.table_name,
            error_type=error_type,
            error_message=str(exc),
            duration_ms=elapsed_ms,
        )

        return TableResult(
            table_name=spec.table_name,
            success=False,
            error_type=error_type,
            error_message=str(exc),
        )
```

### 3.3 `compose_report` (Before / After)

**Before** (lines 749-882):
```python
def compose_report(data: InsightsReportData) -> str:
    # ...
    _period_tables = frozenset({"BY QUARTER", "BY MONTH", "BY WEEK"})

    for table_name in TABLE_ORDER:
        result = data.table_results.get(table_name)
        if result is None: ...
        elif not result.success: ...
        elif not result.data: ...
        else:
            # Reconciliation pending check (hardcoded table names)
            if table_name in _RECONCILIATION_TABLES and _is_payment_data_pending(result.data): ...

            all_rows = result.data
            display_rows = all_rows

            # ASSET TABLE: sort by spend desc
            if table_name == "ASSET TABLE":
                display_rows = sorted(display_rows, key=lambda r: r.get("spend") or 0, reverse=True)

            # Apply row limit
            row_limit = data.row_limits.get(table_name)
            total_rows = len(display_rows)
            if row_limit:
                display_rows = display_rows[:row_limit]
            truncated = row_limit is not None and total_rows > row_limit

            # ASSET TABLE: filter excluded columns
            if table_name == "ASSET TABLE":
                display_rows = [{k: v for k, v in row.items() if k not in _ASSET_EXCLUDE_COLUMNS} for row in display_rows]

            # Period tables: filter display columns
            if table_name in _period_tables:
                available = [c for c in _PERIOD_DISPLAY_COLUMNS if any(c in r for r in display_rows)]
                display_rows = [{k: v for k, v in row.items() if k in available} for row in display_rows]

            sections.append(DataSection(name=table_name, rows=display_rows, ..., full_rows=all_rows))
```

**After**:
```python
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
            sections.append(DataSection(
                name=spec.table_name,
                rows=None,
                error="[ERROR] missing: Table result not available",
            ))
            continue

        if not result.success:
            error_type = result.error_type or "unknown"
            error_msg = result.error_message or "Unknown error"
            sections.append(DataSection(
                name=spec.table_name,
                rows=None,
                error=f"[ERROR] {error_type}: {error_msg}",
            ))
            continue

        if not result.data:
            sections.append(DataSection(
                name=spec.table_name,
                rows=[],
                empty_message=spec.empty_message,
            ))
            continue

        # --- Step 2: Reconciliation pending detection (per FR-11) ---
        if spec.dispatch_type == DispatchType.RECONCILIATION and _is_payment_data_pending(result.data):
            sections.append(DataSection(
                name=spec.table_name,
                rows=[],
                empty_message=_RECONCILIATION_PENDING_MESSAGE,
            ))
            continue

        # --- Step 3: Start with full data; display_rows diverges ---
        all_rows = result.data
        display_rows = list(all_rows)

        # --- Step 4: Sort (spec.sort_key) ---
        if spec.sort_key is not None:
            display_rows = sorted(
                display_rows,
                key=lambda r, k=spec.sort_key: r.get(k) or 0,
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
            available = [
                c for c in spec.display_columns
                if any(c in r for r in display_rows)
            ]
            display_rows = [
                {k: v for k, v in row.items() if k in available}
                for row in display_rows
            ]

        # --- Step 8: Emit DataSection ---
        sections.append(DataSection(
            name=spec.table_name,
            rows=display_rows,
            row_count=len(display_rows),
            truncated=truncated,
            total_rows=total_rows if truncated else None,
            full_rows=all_rows,
        ))

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
```

**Key behavioral equivalence notes**:

1. The `_period_tables` local frozenset is eliminated. Period table behavior is now driven by `spec.display_columns is not None`.
2. The `_RECONCILIATION_TABLES` membership check is replaced by `spec.dispatch_type == DispatchType.RECONCILIATION` (per FR-11). This is equivalent because all and only reconciliation tables have `dispatch_type=RECONCILIATION`.
3. The ASSET TABLE `if table_name == "ASSET TABLE"` branch is replaced by the generic `sort_key` and `exclude_columns` steps. The sort lambda `key=lambda r: r.get("spend") or 0, reverse=True` is exactly preserved via `sort_key="spend", sort_desc=True`.
4. Row limit resolution: `data.row_limits.get(table_name)` becomes `data.row_limits.get(spec.table_name) or spec.default_limit`. For tables with no entry in `row_limits` and no `default_limit`, this is `None` -- same as before (no truncation). For ASSET TABLE: `row_limits` has `"ASSET TABLE": 150`, which matches `spec.default_limit=150`. Runtime override takes precedence.

---

## 4. FR-10 Dual Path: `full_rows` (Copy TSV)

The `full_rows` field on `DataSection` carries the unfiltered, unsorted data for Copy TSV export. This dual path is preserved exactly:

```python
# all_rows = result.data (original, unmodified)
# display_rows = transformed copy (sorted, limited, column-filtered)

sections.append(DataSection(
    name=spec.table_name,
    rows=display_rows,       # <-- display-filtered for HTML tables
    full_rows=all_rows,      # <-- unfiltered for Copy TSV JSON
    ...
))
```

The spec-driven transform pipeline operates on `display_rows` (a `list(all_rows)` shallow copy at Step 3). Steps 4-7 mutate `display_rows` by reassignment (creating new lists), never touching `all_rows`. `full_rows` is always the original `result.data` reference.

**Behavioral guarantee**: Copy TSV always sees all columns, all rows, unsorted (matching current behavior).

---

## 5. FR-12 Decision: `subtitle` and `column_order`

**Decision: DEFER.**

`subtitle` and `column_order` are NOT included on `TableSpec` in this sprint.

**Rationale**:
1. `_SECTION_SUBTITLES` is consumed by `HtmlRenderer._render_table_section` (line 612 and 701 of the formatter), not by `compose_report`. Moving it to the spec would require `HtmlRenderer` to receive `TableSpec` instances, crossing the renderer abstraction boundary.
2. `COLUMN_ORDER` is consumed by `HtmlRenderer._render_table_section` for HTML column reordering within the rendered table. It affects rendered output ordering, not the `compose_report` adapter.
3. Both are renderer-internal concerns, not adapter concerns. Adding them to `TableSpec` would conflate the adapter layer (compose_report) with the renderer layer (HtmlRenderer), violating the existing Protocol boundary.
4. The current dicts (`_SECTION_SUBTITLES`, `COLUMN_ORDER`) work correctly and are not sources of bugs or complexity. Moving them provides no DX improvement for the "add a 13th table" user story.

**Trigger for inclusion**: If `HtmlRenderer` is refactored to accept `TableSpec` directly (e.g., Sprint D+), `subtitle` and `column_order` can be added at that time.

---

## 6. Fixture Design (FR-08, FR-09)

### 6.1 Fixture Code

**File**: `tests/unit/automation/workflows/conftest.py`

```python
"""Shared fixtures for workflow tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.lifecycle.config import LifecycleConfig

# Existing fixtures (unchanged)

@pytest.fixture
def lifecycle_config() -> LifecycleConfig:
    """Lifecycle configuration loaded from YAML."""
    config_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "config"
        / "lifecycle_stages.yaml"
    )
    return LifecycleConfig(config_path)


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock AsanaClient."""
    client = MagicMock()
    client.tasks = MagicMock()
    client.sections = MagicMock()
    return client


# --- New fixture (per D-09, D-10) ---

# Patch target for ResolutionContext in insights_export module
_RC_PATCH_PATH = (
    "autom8_asana.automation.workflows.insights_export.ResolutionContext"
)


def _make_mock_business(
    office_phone: str | None = "+17705753103",
    vertical: str | None = "chiropractic",
    name: str = "Test Business",
) -> MagicMock:
    """Create a mock Business entity returned by ResolutionContext.

    This helper is composed with the mock_resolution_context fixture
    (per D-09). Tests that need non-default business attributes call
    this function and reconfigure the fixture's mock.
    """
    business = MagicMock()
    business.office_phone = office_phone
    business.vertical = vertical
    business.name = name
    return business


@pytest.fixture
def mock_resolution_context():
    """Pre-configured ResolutionContext patch for insights export tests.

    Yields a namespace with:
        .mock_rc: The patched ResolutionContext class mock.
        .mock_ctx: The async context manager instance.
        .mock_business: The default Business mock (phone, vertical, name).
        .set_business(**kwargs): Factory to reconfigure with custom attributes.

    Usage (default business):
        def test_something(self, mock_resolution_context):
            # ResolutionContext is already patched
            result = await _enumerate_and_execute(wf)

    Usage (custom business):
        def test_missing_phone(self, mock_resolution_context):
            mock_resolution_context.set_business(office_phone=None)
            result = await _enumerate_and_execute(wf)
    """
    with patch(_RC_PATCH_PATH) as mock_rc:
        mock_ctx = AsyncMock()
        mock_business = _make_mock_business()
        mock_ctx.business_async = AsyncMock(return_value=mock_business)
        mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

        class _Namespace:
            """Mutable namespace for fixture state."""
            pass

        ns = _Namespace()
        ns.mock_rc = mock_rc
        ns.mock_ctx = mock_ctx
        ns.mock_business = mock_business

        def set_business(**kwargs: Any) -> MagicMock:
            """Reconfigure the mock business with custom attributes.

            Args:
                **kwargs: Passed to _make_mock_business (office_phone, vertical, name).

            Returns:
                The new mock business (also wired into mock_ctx).
            """
            new_business = _make_mock_business(**kwargs)
            ns.mock_business = new_business
            mock_ctx.business_async = AsyncMock(return_value=new_business)
            return new_business

        ns.set_business = set_business

        yield ns
```

### 6.2 Migration Pattern

**Before** (29 occurrences of this 6-line block):
```python
with patch(
    "autom8_asana.automation.workflows.insights_export.ResolutionContext"
) as mock_rc:
    mock_ctx = AsyncMock()
    mock_business = _make_mock_business()
    mock_ctx.business_async = AsyncMock(return_value=mock_business)
    mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await _enumerate_and_execute(wf)
```

**After** (default business):
```python
async def test_something(self, mock_resolution_context) -> None:
    o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
    wf, _, _, _ = _make_workflow(offers=[o1])

    result = await _enumerate_and_execute(wf)

    assert result.succeeded == 1
```

**After** (custom business -- e.g., missing phone):
```python
async def test_skip_missing_phone(self, mock_resolution_context) -> None:
    mock_resolution_context.set_business(office_phone=None)

    o1 = _make_task("o1", "No Phone", parent_gid="biz1")
    wf, _, _, _ = _make_workflow(offers=[o1])

    result = await _enumerate_and_execute(wf)

    assert result.skipped == 1
```

**After** (custom business -- explicit phone/vertical):
```python
async def test_successful_resolution(self, mock_resolution_context) -> None:
    mock_resolution_context.set_business(
        office_phone="+17705753103",
        vertical="chiropractic",
        name="Acme Chiro",
    )

    o1 = _make_task("o1", "Offer 1", parent_gid="biz1")
    wf, _, _, _ = _make_workflow(offers=[o1])

    result = await _enumerate_and_execute(wf)

    assert result.succeeded == 1
```

### 6.3 `_make_mock_business` Retention

Per D-09, `_make_mock_business()` is retained as a standalone helper in `conftest.py` (moved from `test_insights_export.py`). It is composed with the fixture, not replaced by it. The `set_business` factory delegates to it. Tests that need direct access to a mock business outside the fixture context can still call `_make_mock_business()` directly.

The original `_make_mock_business` in `test_insights_export.py` is **deleted** and replaced with an import from `conftest.py` (or, since conftest fixtures and module-level functions are discoverable by pytest, tests simply use the fixture or call the conftest helper).

---

## 7. Commit Plan

### Commit 1: `insights_tables.py` -- New module with shared spec

**Files touched**:
- `src/autom8_asana/automation/workflows/insights_tables.py` (NEW)

**Content**: `DispatchType` enum, `TableSpec` frozen dataclass, `TABLE_SPECS` constant (all 12 entries as specified in Section 1.3).

**Verification**:
```bash
# Type check
python -m mypy src/autom8_asana/automation/workflows/insights_tables.py --strict

# Import test
python -c "from autom8_asana.automation.workflows.insights_tables import DispatchType, TableSpec, TABLE_SPECS; print(f'{len(TABLE_SPECS)} specs, first={TABLE_SPECS[0].table_name}')"

# Existing tests unaffected (module is additive)
python -m pytest tests/unit/automation/workflows/ -x -q
```

### Commit 2: F-03 fetch refactor -- `insights_export.py` consumes TABLE_SPECS

**Files touched**:
- `src/autom8_asana/automation/workflows/insights_export.py`
- `tests/unit/automation/workflows/test_insights_export.py` (4 direct `_fetch_table` call sites in `TestReconPhoneFiltering` updated to new signature)

**Changes**:
- Import `DispatchType`, `TableSpec`, `TABLE_SPECS` from `insights_tables`
- Replace `TABLE_ORDER` import from `insights_formatter` with `TABLE_SPECS` from `insights_tables`
- Update `TABLE_NAMES` to `[s.table_name for s in TABLE_SPECS]`
- Replace `_fetch_all_tables` body with spec loop (Section 3.1)
- Replace `_fetch_table` signature and body with match-based dispatch (Section 3.2)
- Remove now-unused imports of `TABLE_ORDER` from `insights_formatter` (but keep `compose_report`, `InsightsReportData`, `TableResult`, `DataSection` imports)

**Verification**:
```bash
# Type check
python -m mypy src/autom8_asana/automation/workflows/insights_export.py

# Full workflow tests (347 expected)
python -m pytest tests/unit/automation/workflows/ -x -q

# Verify 12 API calls still dispatched
python -m pytest tests/unit/automation/workflows/test_insights_export.py::TestFetchAllTables -x -v
```

### Commit 3: F-04 display refactor -- `insights_formatter.py` consumes TABLE_SPECS

**Files touched**:
- `src/autom8_asana/automation/workflows/insights_formatter.py`

**Changes**:
- Import `TABLE_SPECS`, `DispatchType` from `insights_tables`
- Replace `compose_report` body with spec-driven loop (Section 3.3)
- Delete `TABLE_ORDER` constant
- Delete `_PERIOD_DISPLAY_COLUMNS` constant
- Delete `_ASSET_EXCLUDE_COLUMNS` constant
- Update `_RECONCILIATION_TABLES` usage: replace `table_name in _RECONCILIATION_TABLES` with `spec.dispatch_type == DispatchType.RECONCILIATION` (can also delete `_RECONCILIATION_TABLES` constant since it is now unused)
- Keep `_RECONCILIATION_PENDING_MESSAGE` (still used in compose_report)
- Keep `_is_payment_data_pending` function (still used in compose_report)

**Verification**:
```bash
# Type check
python -m mypy src/autom8_asana/automation/workflows/insights_formatter.py

# Full workflow tests
python -m pytest tests/unit/automation/workflows/ -x -q

# Formatter-specific tests
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -v
```

### Commit 4: F-07 test fixture -- `conftest.py` + migration of 29 inline blocks

**Files touched**:
- `tests/unit/automation/workflows/conftest.py`
- `tests/unit/automation/workflows/test_insights_export.py`

**Changes**:
- Add `_make_mock_business`, `mock_resolution_context` fixture to `conftest.py` (Section 6.1)
- Migrate all 29 inline ResolutionContext mock blocks to use fixture (Section 6.2)
- Delete `_make_mock_business` from `test_insights_export.py` (moved to conftest)
- Remove now-unused `_make_workflow` parameter `mock_business` (the fixture handles mock business configuration separately from workflow construction)

**Verification**:
```bash
# Zero occurrences of inline mock pattern
grep -c "mock_rc.return_value.__aenter__" tests/unit/automation/workflows/test_insights_export.py
# Expected: 0

# Full workflow tests (347 expected)
python -m pytest tests/unit/automation/workflows/ -x -q

# Verify _make_mock_business no longer in test file
grep -c "def _make_mock_business" tests/unit/automation/workflows/test_insights_export.py
# Expected: 0

# Verify it exists in conftest
grep -c "def _make_mock_business" tests/unit/automation/workflows/conftest.py
# Expected: 1
```

### Commit Ordering Constraints

```
Commit 1 (insights_tables.py)
    |
    +---> Commit 2 (fetch refactor, depends on Commit 1)
    |
    +---> Commit 3 (display refactor, depends on Commit 1)
    |
    Commit 4 (test fixture, independent of Commits 2-3)
```

Commits 2 and 3 both depend on Commit 1. They do not depend on each other (they modify different files). Commit 4 is fully independent -- it can be reordered anywhere after Commit 1 if needed, or even executed in parallel.

**Recommended order**: 1, 2, 3, 4 (as proposed in PRD). This allows verifying fetch behavior change (Commit 2) independently before layering display behavior change (Commit 3).

---

## 8. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R-01 | Behavior divergence in compose_report refactor | Medium | High | Byte-for-byte comparison test: render a report with the old code, save the HTML, render with new code, diff. Include this as a manual verification step in Commit 3. |
| R-02 | `match` statement incompatibility with Python < 3.10 | Low | High | Project requires Python 3.11+ (`pyproject.toml`). `match` is safe. |
| R-03 | `_PERIOD_DISPLAY_COLUMNS` list vs `display_columns` field ordering difference | Low | Medium | The `display_columns` field on BY QUARTER/MONTH/WEEK specs uses the exact same list from `_PERIOD_DISPLAY_COLUMNS` (verified in Section 1.3). Column order in the HTML is controlled by `COLUMN_ORDER` in the renderer, not by `display_columns`. |
| R-04 | `row_limits.get(table_name) or spec.default_limit` changes semantics for `row_limits[name] = 0` | Low | Low | Current code uses `if row_limit:` which treats 0 as falsy (no truncation). The new code preserves this behavior: `or spec.default_limit` falls through when `row_limits` returns 0. If 0 were a valid limit, both old and new code would ignore it. No behavior change. |
| R-05 | Tests that directly call `_fetch_table` with positional args will break | Medium | Medium | The signature change (keyword `spec` replaces 8 individual params) will cause 4 test call sites to fail at compile time (immediate detection). Affected: `TestReconPhoneFiltering` (4 methods at lines 1701, 1733, 1763, 1791 of `test_insights_export.py`). These must be updated in Commit 2 to construct a `TableSpec` and pass it as `spec=`. `TestUnusedAssetsApiCall` calls `_fetch_all_tables` (not `_fetch_table`), so it is unaffected. |
| R-06 | Fixture migration misses a mock block | Low | Medium | Automated verification: `grep -c "mock_rc.return_value.__aenter__" test_insights_export.py` must return 0 after Commit 4. This is a commit verification command. |
| R-07 | `DEFAULT_ROW_LIMITS` dict becomes redundant with `default_limit` fields | Low | Low | `DEFAULT_ROW_LIMITS` is retained as the runtime default for `execute_async`'s `row_limits` parameter. It serves as the "external override" layer. The spec's `default_limit` is the "built-in default" layer. Both are needed: the spec default applies when no runtime override exists; the runtime default is what `execute_async` passes when the caller does not specify overrides. The values are consistent by construction. |
| R-08 | `_make_workflow` helper in tests references `mock_business` param | Low | Medium | Commit 4 removes the `mock_business` parameter from `_make_workflow` and the `resolve_returns_none` parameter. Any tests using these params are migrated to use the fixture's `set_business()` method instead. |

---

## 9. Deferred Items

| Item | Sprint | Trigger |
|------|--------|---------|
| Reconciliation phone filter migration to DataServiceClient | Future | Production incident from multi-phone responses, or DataServiceClient initiative (per D-02) |
| `subtitle` and `column_order` on TableSpec (FR-12) | Sprint D+ | HtmlRenderer refactoring to accept TableSpec directly |
| `_DISPLAY_LABELS`, `_COLUMN_TOOLTIPS` consolidation | Sprint D+ | Renderer restructuring |
| `_DEFAULT_EXPANDED_SECTIONS` on TableSpec | Sprint D+ | Renderer restructuring |

---

## Quality Gate Checklist

- [x] TableSpec dataclass is fully specified (all 14 fields, types, defaults) -- Section 1.2
- [x] All 12 TABLE_SPECS entries are enumerated with exact current parameter values -- Section 1.3
- [x] Before/after signatures for all three refactored functions -- Sections 3.1, 3.2, 3.3
- [x] Fixture code is concrete (not pseudocode) -- Section 6.1
- [x] Commit plan with file lists and verification commands -- Section 7
- [x] FR-12 decision documented -- Section 5
- [x] No open design questions remain
