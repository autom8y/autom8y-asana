# PRD: Sprint C -- Insights Export Structural Improvements

## Overview

Refactor three structural findings (F-03, F-04, F-07) from the insights export pipeline review into a declarative, spec-driven design. The 12-table fetch routing monolith becomes a `TableSpec` frozen dataclass with both fetch and display configuration. The `compose_report` function becomes a generic loop applying spec-driven transforms. The ResolutionContext test mock boilerplate (29 occurrences) consolidates into a shared pytest fixture.

## Impact Assessment

impact: low
impact_categories: []

Rationale: Internal structural refactoring only. No API contract changes, no schema changes, no security implications. All changes are isolated to `automation/workflows/` source files and their tests. External behavior is byte-for-byte preserved.

## Background

An architectural review (`EXPORT-FLOW-REVIEW.md`) produced 17 findings across the insights export pipeline. Sprints A and B resolved 10 quick-win and robustness findings (commit `5092d2d`, 347 workflow tests passing, mypy clean). Three P2 STRUCTURAL findings remain. This sprint addresses them.

### Prior Art

| Artifact | Location |
|----------|----------|
| Export flow review (17 findings) | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/EXPORT-FLOW-REVIEW.md` |
| Sprint C frame document | `.claude/wip/frames/sprint-c-export-structural.md` |
| Sprint A+B commit | `5092d2d` |

## User Stories

- As a **developer adding a 13th table**, I want table configuration declared in a single place, so that I do not need to understand the interaction between `_fetch_all_tables`, `_fetch_table`, and `compose_report` to add one table.
- As a **developer maintaining the formatter**, I want per-table display rules (sort, column filter, exclusions) declared on the spec rather than hardcoded in branching logic, so that `compose_report` does not grow in cyclomatic complexity with each table-specific behavior.
- As a **developer writing export workflow tests**, I want ResolutionContext mock setup available as a fixture, so that interface changes to ResolutionContext require updating one fixture instead of 29 test methods.

## Interview Decisions

The following decisions were made during stakeholder interview and are binding for the architect.

### D-01: Table Set Stability (F-03)

Schema changes within tables are more common than table additions, but both occur. Design for **moderate extensibility** -- adding a table should be a one-liner spec addition, but do not build a plugin/registry system. A flat list of `TableSpec` instances is sufficient.

### D-02: Reconciliation Phone Filtering (F-03)

The reconciliation phone-filtering logic (lines 909-935 of `insights_export.py`) is a data-correctness concern that **should eventually move to `DataServiceClient`**. For this sprint, it stays in the dispatcher. Document as a deferred item.

**Rationale**: Moving it to the client would cross the file-scope boundary of this sprint and require changes to `clients/data/client.py` (out of scope per frame Section 3).

### D-03: Row Limits (F-03 + F-04)

Unified limit mechanism. All 12 tables get a `default_limit` field on the spec:
- Tables with API-capable limiting (APPOINTMENTS, LEADS) apply `default_limit` server-side via the `limit` parameter.
- All other tables apply `default_limit` client-side during `compose_report` display preparation.
- Runtime `row_limits` dict overrides `default_limit` when provided (existing behavior preserved).

### D-04: Dispatch Pattern (F-03)

Replace the 4-branch `if/elif` chain with a **`DispatchType` enum** discriminator on the spec. The dispatcher uses a `match` statement on `spec.dispatch_type`. Enum values: `INSIGHTS`, `APPOINTMENTS`, `LEADS`, `RECONCILIATION`.

### D-05: Spec Shape (F-03 + F-04)

Single frozen dataclass (`@dataclass(frozen=True)`) named `TableSpec` with approximately 14 fields spanning both fetch and display configuration. No composition, no nesting, no inheritance. A flat structure for a finite set of 12 tables.

Fields will include (architect determines exact names and types):
- **Identity**: table name
- **Fetch**: dispatch type, factory, period, days, exclude_appointments, window_days, include_unused
- **Limits**: default_limit
- **Display**: sort_key, sort_desc, exclude_columns, display_columns, empty_message

### D-06: File Location (F-03)

New module: `src/autom8_asana/automation/workflows/insights_tables.py`

This module contains `DispatchType`, `TableSpec`, and the `TABLE_SPECS` constant (list of 12 specs). Both `insights_export.py` and `insights_formatter.py` import from it. The `TABLE_ORDER` list in `insights_formatter.py` is replaced by the ordering of `TABLE_SPECS`.

### D-07: compose_report Decomposition (F-04)

Display preparation logic moves into spec-driven transforms. The `TableSpec` carries display fields (`sort_key`, `sort_desc`, `exclude_columns`, `display_columns`, `empty_message`). `compose_report` becomes a generic loop:

1. Iterate `TABLE_SPECS` (replaces `TABLE_ORDER`)
2. Validate result (missing / error / empty) -- unchanged
3. Check reconciliation pending -- driven by a spec flag or table name membership (architect decides)
4. Apply `sort_key` + `sort_desc` if present
5. Apply `default_limit` (or runtime override)
6. Apply `exclude_columns` if present
7. Apply `display_columns` if present
8. Emit `DataSection`

The five interleaved concerns (validation, pending detection, sort + exclusion, row limit, column filter) become sequential spec-driven steps with no table-name branching in the loop body.

### D-08: Coupling F-03 and F-04 (Stakeholder Override)

The frame document (Section 7, bullet 3) warned against coupling F-03 and F-04 into a single abstraction. The stakeholder explicitly chose to unify fetch and display configuration on a single `TableSpec`. This is a documented override of the frame's anti-pattern guidance.

**Rationale**: The 12 tables are a fixed domain. Separating fetch spec from display spec would create two parallel lists that must stay in sync. A single spec is simpler to maintain and reason about.

**Consequence**: F-03 and F-04 are no longer independently committable. The architect should plan a single commit for `insights_tables.py` (the shared spec), then separate commits for the fetch refactor and the display refactor, both depending on the spec commit.

### D-09: ResolutionContext Fixture Pattern (F-07)

Shared pytest fixture using the **factory fixture pattern**:
- A `mock_resolution_context` fixture yields a pre-configured patch with the default `_make_mock_business()` result.
- Tests that need to vary business attributes call `_make_mock_business(office_phone=None)` and reconfigure the fixture's mock after receiving it, OR use a parameterized factory callable yielded by the fixture.
- The `_make_mock_business()` helper is **composed with** (not replaced by) the fixture.

### D-10: Fixture Location (F-07)

File: `tests/unit/automation/workflows/conftest.py`

The fixture lives at the `workflows/` conftest level, making it available to both `test_insights_export.py` and `test_conversation_audit.py` (and any future workflow test modules).

## Functional Requirements

### Must Have

- **FR-01**: `TableSpec` frozen dataclass in `insights_tables.py` with fields covering fetch dispatch (dispatch type, factory, period, days, limit, flags) and display preparation (sort key, exclude columns, display columns, empty message).
- **FR-02**: `DispatchType` enum with four values: `INSIGHTS`, `APPOINTMENTS`, `LEADS`, `RECONCILIATION`.
- **FR-03**: `TABLE_SPECS` module constant -- ordered list of 12 `TableSpec` instances encoding current behavior exactly.
- **FR-04**: `_fetch_all_tables` replaced by a loop over `TABLE_SPECS` feeding `asyncio.gather()`.
- **FR-05**: `_fetch_table` dispatch uses `match` statement on `spec.dispatch_type`.
- **FR-06**: `compose_report` iterates `TABLE_SPECS` and applies spec-driven transforms (sort, limit, column filter, exclusion) with no table-name branching.
- **FR-07**: `TABLE_ORDER` in `insights_formatter.py` replaced by `TABLE_SPECS` ordering.
- **FR-08**: `mock_resolution_context` fixture in `tests/unit/automation/workflows/conftest.py`.
- **FR-09**: All 29 inline ResolutionContext mock blocks migrated to use the fixture. Zero half-migrations.

### Should Have

- **FR-10**: `full_rows` for Copy TSV must bypass display filtering but still receive the correct (unfiltered, unsorted-if-applicable) data. The spec-driven loop must preserve this dual-path.
- **FR-11**: Reconciliation pending detection should be expressible via the spec (flag or table-name set) rather than hardcoded in `compose_report`.

### Could Have

- **FR-12**: `TABLE_SPECS` could carry `subtitle` and `column_order` fields, consolidating `_SECTION_SUBTITLES` and `COLUMN_ORDER` dicts. Architect decides whether to include or defer.

## Non-Functional Requirements

- **NFR-01**: Behavior preservation -- all 12 tables must produce identical HTML output. Byte-for-byte equality is the gold standard; semantic equivalence with documented delta is acceptable.
- **NFR-02**: Test baseline -- 347 workflow tests passing before and after. Full test suite green-to-green.
- **NFR-03**: No new dependencies -- stdlib + existing project patterns only.
- **NFR-04**: mypy clean -- no new type errors introduced.
- **NFR-05**: Concurrent fetch -- all 12 tables remain dispatched concurrently via `asyncio.gather()`. No sequential degradation.

## Edge Cases

| Case | Expected Behavior |
|------|------------------|
| Table with no `default_limit` and no runtime override | No truncation applied. All rows displayed. |
| Runtime `row_limits` entry for a table that also has `default_limit` | Runtime override takes precedence over spec default. |
| `display_columns` specified but none of those columns exist in data | Empty display rows (current behavior for period tables when columns are absent). |
| Reconciliation response returns single phone | Phone filtering is a no-op (current behavior, lines 921-922). |
| `_make_mock_business()` called with non-default args after fixture setup | Test overrides the fixture's mock_business on the yielded mock_ctx. |
| Table spec ordering differs from current TABLE_ORDER | Would change report section order. TABLE_SPECS must match current TABLE_ORDER exactly. |

## Success Criteria

### F-03: TableSpec + Fetch Refactor
- [ ] `insights_tables.py` exists with `DispatchType` enum, `TableSpec` dataclass, and `TABLE_SPECS` constant
- [ ] `_fetch_all_tables` iterates `TABLE_SPECS` instead of 12 hand-written calls
- [ ] `_fetch_table` uses `match` statement on `spec.dispatch_type`
- [ ] All 12 tables fetch identically (same API calls, same parameters, same concurrency)
- [ ] Reconciliation phone filtering remains in the dispatcher (not on the spec)

### F-04: compose_report Decomposition
- [ ] `compose_report` has no table-name branching in its main loop body
- [ ] Sort, limit, column filter, and exclusion are driven by `TableSpec` fields
- [ ] `full_rows` (Copy TSV) bypasses display filtering
- [ ] `TABLE_ORDER` removed from `insights_formatter.py` (replaced by spec ordering)
- [ ] Period table column filtering uses `display_columns` from spec (not `_PERIOD_DISPLAY_COLUMNS` inline list)
- [ ] Asset table sort + exclusion uses `sort_key` / `exclude_columns` from spec (not inline branching)

### F-07: ResolutionContext Fixture
- [ ] `tests/unit/automation/workflows/conftest.py` contains `mock_resolution_context` fixture
- [ ] All 29 inline mock blocks in `test_insights_export.py` migrated to use fixture
- [ ] Zero occurrences of `mock_rc.return_value.__aenter__` remain in `test_insights_export.py`
- [ ] Tests that need non-default business attributes can customize via factory pattern
- [ ] `_make_mock_business()` helper retained (composed with, not replaced by, fixture)

## Out of Scope

| Item | Reason |
|------|--------|
| Reconciliation phone-filtering migration to DataServiceClient | Deferred (see D-02). Crosses file-scope boundary. |
| F-11 (column_align_class performance) | Sprint D backlog, P3. |
| F-12 (inline CSS/JS extraction) | Sprint D backlog, P3. |
| F-17 (renderer singleton reset) | Sprint D backlog, P3. |
| ResolutionContext source code changes | Only the test mock is in scope. |
| DataServiceClient endpoint changes | Consumed, not modified. |
| HtmlRenderer internals | Called by compose_report but not restructured. |
| `_SECTION_SUBTITLES`, `COLUMN_ORDER`, `_DISPLAY_LABELS`, `_COLUMN_TOOLTIPS` consolidation | FR-12 (Could Have). Architect decides. |

## Deferred Items

| Item | Trigger | Notes |
|------|---------|-------|
| Recon phone filter to DataServiceClient | Next DataServiceClient initiative or production incident from multi-phone responses | Currently defensive filter in `_fetch_table` lines 909-935. API may return all businesses for the vertical. |

## Open Questions

None. All design decisions resolved during interview.

## Commit Strategy

The coupling of F-03 and F-04 via unified `TableSpec` (D-08) means the following commit order:

1. **Commit 1**: `insights_tables.py` -- new module with `DispatchType`, `TableSpec`, `TABLE_SPECS`
2. **Commit 2**: F-03 fetch refactor -- `insights_export.py` consumes `TABLE_SPECS` for fetch
3. **Commit 3**: F-04 display refactor -- `insights_formatter.py` consumes `TABLE_SPECS` for compose_report
4. **Commit 4**: F-07 test fixture -- `conftest.py` + migration of 29 inline blocks

Commits 2 and 3 depend on Commit 1. Commit 4 is independent. Architect confirms or adjusts.
