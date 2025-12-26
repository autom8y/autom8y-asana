# PRD-02: Data Layer Architecture

> Consolidated PRD for Polars dataframes, schema design, and custom field resolution.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: PRD-0003 (Structured Dataframe Layer), PRD-0003.1 (Dynamic Custom Field Resolution)
- **Related TDD**: TDD-02-data-layer
- **Stakeholders**: autom8 team, SDK consumers, data analysts

---

## Executive Summary

The data layer provides type-safe dataframe generation from Asana tasks. It transforms raw API responses into Polars DataFrames with typed columns, enabling efficient analysis without manual data transformation. The layer includes schema definitions for task types, custom field resolution by name, and integration with the caching infrastructure.

**Key capabilities**:
- `Project.to_dataframe()` and `Section.to_dataframe()` methods returning typed Polars DataFrames
- Schema-driven extraction with 32 typed fields (12 base + 11 Unit + 9 Contact)
- Dynamic custom field resolution eliminating hardcoded GIDs
- Concurrent task processing with configurable concurrency
- Cache integration for extracted row data (STRUC entry type)
- Backward-compatible `struc()` wrapper with deprecation path

---

## Problem Statement

### Current State

The SDK returns tasks as `AsanaTask` Pydantic models or raw dictionaries. Consumers must manually extract, transform, and structure this data for analysis. The legacy autom8 monolith contains a battle-tested `struc()` method (~1,000 lines) that handles this transformation, but it is tightly coupled to business logic, SQL integrations, and threading infrastructure.

**Specific issues**:

1. **No standardized extraction**: Each consumer writes custom logic to extract custom field values
2. **No type safety**: Custom fields return `Any`; no schema enforcement
3. **No workspace portability**: Static GID constants require code changes per environment
4. **Performance penalty**: Serial processing without concurrency control
5. **Inconsistent field naming**: Different consumers use different column names
6. **Scale problem**: 16 placeholder GIDs for 2 task types; legacy has 50+ types

### Impact of Not Solving

| Impact | Consequence |
|--------|-------------|
| SDK consumers replicate complex transformation logic | Duplicated effort, inconsistent results |
| No type safety for extracted values | Runtime errors, data quality issues |
| Cannot migrate legacy dataframe features | Technical debt remains |
| Data analysts cannot efficiently query Asana data | Manual Excel workflows persist |
| Environment-specific code | 3x maintenance burden across dev/staging/prod |

---

## Goals and Non-Goals

### Goals

| Goal | Success Metric |
|------|----------------|
| 20-30% faster than legacy struc() | Benchmark same project with both methods |
| 100% of MVP fields have defined types | Static analysis of DataFrame schema |
| Zero placeholder GID constants | `grep -r "PLACEHOLDER_" src/` returns 0 results |
| Same schema works across workspaces | Integration test with different workspace GIDs |
| Single method call for dataframe generation | `project.to_dataframe()` returns complete result |
| Cache integration reduces repeated extraction time by 50%+ | Warm cache benchmark |

### Non-Goals

- **Pandas DataFrame output**: Polars only; use `.to_pandas()` for conversion
- **Real-time streaming updates**: Batch extraction only
- **Cross-project aggregation**: Single project/section scope
- **Custom field creation in Asana**: Read-only operations
- **Multi-workspace simultaneous use**: One workspace per SDK session
- **50+ task types in MVP**: Unit and Contact only; others post-MVP

---

## Requirements

### Schema Definition Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-MODEL-001 | Define `DataFrameSchema` class with column name, Polars dtype, nullability, and source field | Must |
| FR-MODEL-002 | Provide `BaseSchema` with 12 common fields: gid, name, type, date, created, due_on, is_completed, completed_at, url, last_modified, section, tags | Must |
| FR-MODEL-003 | Support schema inheritance for type-specific extensions | Must |
| FR-MODEL-004 | Provide schema registry with `get_schema(task_type: str)` lookup | Must |
| FR-MODEL-005 | Validate extracted values match declared types; log warnings on mismatch | Should |
| FR-MODEL-020 | Define `TaskRow` Pydantic model representing extracted row; frozen after construction | Must |
| FR-MODEL-033 | Include schema version string for cache compatibility | Must |

### Custom Field Resolution Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-NORM-001 | Normalize schema field names from snake_case for matching | Must |
| FR-NORM-002 | Normalize Asana custom field names to same canonical form | Must |
| FR-NORM-003 | Case-insensitive normalization: `MRR` == `mrr` == `Mrr` | Must |
| FR-NORM-004 | Treat underscores, spaces, and absent separators equivalently | Must |
| FR-RESOLVE-001 | Resolve schema field names to GIDs at extraction time | Must |
| FR-RESOLVE-002 | Use task's `custom_fields` list as source of truth (no extra API calls) | Must |
| FR-RESOLVE-004 | Store resolved GIDs in session-scoped cache | Must |
| FR-RESOLVE-005 | Support explicit GID override via `ColumnDef.source` | Must |
| FR-AMBIG-001 | Detect when multiple custom fields match a schema field name | Must |
| FR-AMBIG-002 | Raise `AmbiguousFieldError` with candidates and GIDs | Must |
| FR-AMBIG-005 | Prefer exact case-sensitive match over normalized match | Must |
| FR-MISSING-001 | Handle unresolved fields gracefully (return None, no exception) | Must |
| FR-MISSING-003 | Support strict mode via `strict=True` to raise on unresolved | Should |

### Extraction Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-PROJECT-001 | Provide `to_dataframe(task_type, concurrency=10)` on Project class | Must |
| FR-SECTION-001 | Provide `to_dataframe(task_type, concurrency=10)` on Section class | Must |
| FR-PROJECT-002 | Filter tasks by type when `task_type` parameter provided | Must |
| FR-PROJECT-003 | Process tasks concurrently with configurable limit | Must |
| FR-PROJECT-006 | Provide sync and async variants: `to_dataframe()` and `to_dataframe_async()` | Must |
| FR-CUSTOM-002 | Extract custom field values by resolved GID | Must |
| FR-CUSTOM-003 | Coerce values to schema-defined types (enum -> display_value, number -> Decimal) | Must |
| FR-CUSTOM-004 | Handle multi-enum fields as `list[str]` | Must |
| FR-CUSTOM-005 | Missing custom fields return None without exception | Must |

### Cache Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CACHE-001 | Cache extracted row data using STRUC entry type | Must |
| FR-CACHE-002 | Check cache before extracting each task | Must |
| FR-CACHE-003 | Invalidate cache when task modified_at changes | Must |
| FR-CACHE-006 | Support cache bypass via `use_cache=False` | Should |
| FR-CACHE-008 | Handle cache failures gracefully; log and continue | Must |
| FR-RES-CACHE-001 | Cache name-to-GID mappings in memory | Must |
| FR-RES-CACHE-002 | Resolution cache is session-scoped | Must |
| FR-RES-CACHE-003 | Resolution cache is thread-safe | Must |

### Compatibility Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-COMPAT-001 | Provide `struc()` method as deprecated alias | Must |
| FR-COMPAT-002 | Emit deprecation warning on `struc()` calls | Must |
| FR-COMPAT-005 | Preserve `struc()` behavior for at least 2 minor versions | Must |
| FR-EXPORT-001 | Use Polars DataFrame as output format | Must |
| FR-EXPORT-004 | Support pandas conversion via `.to_pandas()` | Should |

### Error Handling Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ERROR-001 | Define `DataFrameError` base exception | Must |
| FR-ERROR-002 | Define `SchemaNotFoundError` for unknown task types | Must |
| FR-ERROR-003 | Define `ExtractionError` with task GID, field name, original exception | Must |
| FR-ERROR-005 | Continue processing on individual task failures | Must |
| FR-TEST-001 | Support mock resolver injection for testing | Must |
| FR-TEST-003 | Support resolution from fixture data without API | Must |

---

## User Stories

### US-1: Data Analyst Generates Project Report

**As a** data analyst
**I want to** generate a typed dataframe from an Asana project
**So that** I can create reports without manual data transformation

```python
df = project.to_dataframe(task_type="Unit")
# Returns Polars DataFrame with 23 typed columns (12 base + 11 Unit)
filtered = df.filter(pl.col("mrr") > 1000)
filtered.write_excel("high_value_units.xlsx")
```

### US-2: Developer Migrates from Legacy struc()

**As a** developer maintaining autom8
**I want to** migrate from `struc()` to `to_dataframe()` incrementally
**So that** I can adopt the new SDK without breaking existing code

```python
# Old code continues working with deprecation warning
df = project.struc()  # DeprecationWarning: use to_dataframe()

# Migration path
df = project.to_dataframe()
pandas_df = df.to_pandas()  # If pandas needed
```

### US-3: Developer Adds New Custom Field

**As a** developer
**I want to** add a new custom field to a schema without looking up GIDs
**So that** I can quickly extend the data model

```python
# Just add the field definition - no GID required
ColumnDef(name="renewal_date", dtype="Date", nullable=True)

# SDK automatically resolves "renewal_date" to Asana's "Renewal Date" field
```

### US-4: SDK Used Across Workspaces

**As a** team lead
**I want to** use the same SDK in staging and production workspaces
**So that** I can test without environment-specific code

```python
# Same schema code works in both environments
# Production: "MRR" field has GID 1111111111111111
# Staging: "MRR" field has GID 2222222222222222
# Resolution happens automatically per workspace
```

### US-5: Debugging Resolution Failures

**As a** developer
**I want to** see which GIDs were resolved
**So that** I can debug field mapping issues

```python
info = resolver.get_resolution_info("discount")
# {"status": "unresolved", "reason": "no match",
#  "available_fields": ["Discount %", "MRR", ...]}
```

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| Dataframe generation time | 20-30% faster than legacy | Benchmark identical project |
| Type coverage | 100% of 32 MVP fields typed | Static analysis |
| Field parity | All 32 MVP fields supported | Feature matrix |
| Memory efficiency | <= 1.5x raw task footprint | Memory profiler |
| GID constants | Zero placeholder constants | Grep codebase |
| Workspace portability | Same code works in 2+ workspaces | Integration test |
| Resolution latency (cold) | < 50ms for 20 fields | pytest-benchmark |
| Resolution latency (warm) | < 1ms per field | pytest-benchmark |
| Cache hit improvement | >= 50% extraction time reduction | Benchmark comparison |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| PRD-0002 Intelligent Caching | Complete | STRUC entry type |
| Polars library | Available | Add to pyproject.toml |
| ColumnDef.source field | Complete | Supports explicit GID override |
| Task.custom_fields populated | Complete | CustomField model exists |
| Python 3.12+ | Required | Project constraint |

---

## Appendix A: MVP Field Mapping

### Base Fields (12 - All Task Types)

| Field | Source | Type | Nullable |
|-------|--------|------|----------|
| gid | `task.gid` | str | No |
| name | `task.name` | str | No |
| type | `task.resource_subtype` | str | No |
| date | Custom field or `task.due_on` | date | Yes |
| created | `task.created_at` | datetime | No |
| due_on | `task.due_on` | date | Yes |
| is_completed | `task.completed` | bool | No |
| completed_at | `task.completed_at` | datetime | Yes |
| url | Constructed from GID | str | No |
| last_modified | `task.modified_at` | datetime | No |
| section | `task.memberships[project].section.name` | str | Yes |
| tags | `[tag.name for tag in task.tags]` | list[str] | No |

### Unit-specific Fields (11)

| Field | Type | Notes |
|-------|------|-------|
| mrr | Decimal | Monthly recurring revenue |
| weekly_ad_spend | Decimal | Weekly advertising spend |
| products | list[str] | Multi-enum |
| languages | list[str] | Multi-enum |
| discount | Decimal | Discount percentage |
| office | str | Derived from business lookup |
| office_phone | str | Derived from business |
| vertical | str | Enum custom field |
| vertical_id | str | Derived from Vertical model |
| specialty | str | Custom field |
| max_pipeline_stage | str | Derived from UnitHolder |

### Contact-specific Fields (9)

| Field | Type | Notes |
|-------|------|-------|
| full_name | str | Contact full name |
| nickname | str | Contact nickname |
| contact_phone | str | Phone number |
| contact_email | str | Email address |
| position | str | Job title |
| employee_id | str | Employee identifier |
| contact_url | str | Website/URL |
| time_zone | str | Time zone |
| city | str | City location |

## Appendix B: Normalization Truth Table

All inputs in each row produce identical canonical output:

| Input Variations | Canonical Output |
|------------------|------------------|
| `mrr`, `MRR`, `Mrr` | `mrr` |
| `weekly_ad_spend`, `Weekly Ad Spend`, `WeeklyAdSpend` | `weekly_ad_spend` |
| `discount`, `Discount`, `DISCOUNT` | `discount` |
| `office_phone`, `Office Phone`, `OfficePhone` | `office_phone` |
| `vertical_id`, `Vertical ID`, `VerticalID` | `vertical_id` |
| `contact_email`, `Contact Email`, `ContactEmail` | `contact_email` |
| `full_name`, `Full Name`, `FullName` | `full_name` |

## Appendix C: Source Document Traceability

| Consolidated Section | Source PRD | Original IDs |
|---------------------|------------|--------------|
| Schema Definition | PRD-0003 | FR-MODEL-001 to FR-MODEL-033 |
| Custom Field Resolution | PRD-0003.1 | FR-NORM-*, FR-RESOLVE-*, FR-AMBIG-*, FR-MISSING-* |
| Extraction | PRD-0003 | FR-PROJECT-*, FR-SECTION-*, FR-CUSTOM-* |
| Cache (Struc) | PRD-0003 | FR-CACHE-001 to FR-CACHE-010 |
| Cache (Resolution) | PRD-0003.1 | FR-CACHE-001 to FR-CACHE-006 |
| Compatibility | PRD-0003 | FR-COMPAT-*, FR-EXPORT-* |
| Error Handling | PRD-0003, PRD-0003.1 | FR-ERROR-*, FR-TEST-* |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Consolidated from PRD-0003 v2.0 and PRD-0003.1 v1.0 |
