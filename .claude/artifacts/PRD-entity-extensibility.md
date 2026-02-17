# PRD: Entity DataFrame Completeness & Extensibility

```yaml
id: PRD-ENTITY-EXT-001
status: DRAFT
date: 2026-02-17
author: requirements-analyst
impact: high
impact_categories: [data_model, api_contract]
```

---

## 1. Problem Statement

4 of 6 entity DataFrame schemas crash when a consumer calls `to_dataframe()`. The crash mechanism is deterministic and identical across all four:

1. `SchemaRegistry` returns the entity's schema (e.g., `OFFER_SCHEMA` with 23 columns)
2. `_create_extractor()` has no `case` branch for the entity type, falling through to `DefaultExtractor`
3. `DefaultExtractor._create_row()` calls `TaskRow.model_validate(data)`
4. `TaskRow` is configured with `extra="forbid"` and rejects the entity-specific columns
5. Pydantic raises `ValidationError` with N validation errors (one per extra column)

This was discovered during SPIKE-offer-query-canary-bugs (bugs B1 through B5). The root cause is a structural wiring gap: `SchemaRegistry._ensure_initialized()` registers schemas via hardcoded imports, while `_create_extractor()` routes extractors via a separate hardcoded `match/case` statement. These two registrations share no enforcement mechanism, so adding a schema without adding a corresponding extractor and row model compiles and deploys without error.

### Affected Schemas

| Entity | Schema | Total Columns | Extra (beyond base 12) | Source Types in Extra | Crash? |
|--------|--------|--------------|----------------------|----------------------|--------|
| Offer | `OFFER_SCHEMA` | 23 | 11 | 4 cascade, 5 cf, 2 derived (source=None) | YES |
| Business | `BUSINESS_SCHEMA` | 18* | 6* | 5 cf, 1 derived | YES |
| AssetEdit | `ASSET_EDIT_SCHEMA` | 33 | 21 | 2 cascade, 19 cf | YES |
| AssetEditHolder | `ASSET_EDIT_HOLDER_SCHEMA` | 13 | 1 | 1 cascade | YES |
| Contact | `CONTACT_SCHEMA` | 25 | 13 | 2 cascade, 10 cf, 1 derived | NO (has ContactExtractor) |
| Unit | `UNIT_SCHEMA` | 23 | 11 | 1 cascade, 5 cf, 5 derived | NO (has UnitExtractor) |

*BUSINESS_SCHEMA contains a duplicate `name` column (base `name` with source="name" AND business `name` with source=None) due to the schema's dedup filter using `c not in BASE_COLUMNS` (object equality on ColumnDef) rather than name-based dedup. This is a latent bug to address during implementation -- the schema should use name-based dedup like OFFER_SCHEMA does.

### Working Entities (Reference)

Unit and Contact have complete extraction stacks: dedicated `{Type}Row(TaskRow)` subclasses, dedicated `{Type}Extractor(BaseExtractor)` subclasses, and `case` branches in `_create_extractor()`. These continue working correctly and must not be disturbed.

### Key Observation

The extraction logic in `BaseExtractor` is already generic for all source types except `source=None` (derived fields). The `_extract_column()` and `_extract_column_async()` methods dispatch on `cf:`, `gid:`, `cascade:`, and direct-attribute prefixes without any type-specific knowledge. Custom extractors exist only to (a) call the correct `{Type}Row.model_validate()` and (b) implement derived field methods. For entities whose schemas have zero `source=None` columns (AssetEdit, AssetEditHolder), a custom extractor is pure boilerplate.

---

## 2. Stakeholders

| Stakeholder | Impact | Interest |
|-------------|--------|----------|
| Query API consumers | Cannot call `to_dataframe()` for 4 entity types | Unblocked DataFrame access for Offer, Business, AssetEdit, AssetEditHolder |
| Cache warming pipeline (Lambda) | Warm DataFrames for all schema-bearing entities | No crash during cache rebuild cycles |
| Future entity authors | Must know what to implement for full DataFrame support | Clear contract enforced by test and import-time warning |
| Architect (Phase 2) | Must choose wiring architecture | Evaluation criteria defined, not pre-decided |
| QA Adversary (Phase 4) | Must verify all acceptance criteria | Testable, measurable success metrics |

---

## 3. User Stories

### US-1: Offer DataFrame Works

**As** a query API consumer,
**I want** `SectionDataFrameBuilder(task_type="Offer").build(tasks)` to return a valid `pl.DataFrame`,
**so that** I can query, aggregate, and join Offer data programmatically.

| AC | Criterion | Testable Assertion |
|----|-----------|-------------------|
| AC-1.1 | Build succeeds without crash | `SectionDataFrameBuilder(task_type="Offer").build(tasks)` returns `pl.DataFrame`, not `ValidationError` |
| AC-1.2 | Column count matches schema | `len(df.columns) == len(OFFER_SCHEMA.columns)` (23 columns) |
| AC-1.3 | Column names match schema | `set(df.columns) == set(OFFER_SCHEMA.column_names())` |
| AC-1.4 | Custom fields extracted | `cf:Offer ID`, `cf:Specialty`, `cf:Platforms`, `cf:Language`, `cf:Cost` columns populated from task custom_fields |
| AC-1.5 | Cascade fields handled | `cascade:Office Phone`, `cascade:Vertical`, `cascade:MRR`, `cascade:Weekly Ad Spend` columns present (values may be None if no client provided for sync extraction) |
| AC-1.6 | Derived fields return None | `office`, `vertical_id`, `name` columns present with `None` values (traversal logic deferred) |

### US-2: Business DataFrame Works

**As** a query API consumer,
**I want** `SectionDataFrameBuilder(task_type="business").build(tasks)` to return a valid `pl.DataFrame`,
**so that** I can query Business-level data.

| AC | Criterion | Testable Assertion |
|----|-----------|-------------------|
| AC-2.1 | Build succeeds without crash | Returns `pl.DataFrame` with 18 columns matching `BUSINESS_SCHEMA` |
| AC-2.2 | Custom fields extracted | `cf:Company ID`, `cf:Office Phone`, `cf:Stripe ID`, `cf:Booking Type`, `cf:Facebook Page ID` columns populated |
| AC-2.3 | Derived `name` returns None | `name` column from BUSINESS_COLUMNS (source=None) returns None via SchemaExtractor |

### US-3: AssetEdit DataFrame Works

**As** a query API consumer,
**I want** `SectionDataFrameBuilder(task_type="AssetEdit").build(tasks)` to return a valid `pl.DataFrame`,
**so that** I can query and report on asset editing workflows.

| AC | Criterion | Testable Assertion |
|----|-----------|-------------------|
| AC-3.1 | Build succeeds without crash | Returns `pl.DataFrame` with 33 columns matching `ASSET_EDIT_SCHEMA` |
| AC-3.2 | All 19 cf: fields extracted | Every `cf:` source column populated from task custom_fields |
| AC-3.3 | Cascade fields handled | `cascade:Vertical`, `cascade:Office Phone` columns present |
| AC-3.4 | No derived fields required | ASSET_EDIT_SCHEMA has zero `source=None` columns -- all fields are `cf:` or `cascade:` |

### US-4: AssetEditHolder DataFrame Works

**As** a query API consumer,
**I want** `SectionDataFrameBuilder(task_type="AssetEditHolder").build(tasks)` to return a valid `pl.DataFrame`,
**so that** I can query holder-level data with cascaded office_phone.

| AC | Criterion | Testable Assertion |
|----|-----------|-------------------|
| AC-4.1 | Build succeeds without crash | Returns `pl.DataFrame` with 13 columns matching `ASSET_EDIT_HOLDER_SCHEMA` |
| AC-4.2 | Cascade field handled | `cascade:Office Phone` column present |

### US-5: SchemaExtractor as Generic Fallback

**As** a future entity author,
**I want** any new schema registered in `SchemaRegistry` (with only `cf:`, `cascade:`, direct-attribute, and `gid:` sources) to produce a valid DataFrame without writing a dedicated extractor,
**so that** I do not need to create boilerplate extractor and row model classes for entities with no custom derived logic.

| AC | Criterion | Testable Assertion |
|----|-----------|-------------------|
| AC-5.1 | Generic fallback works | Adding a test schema with 3 `cf:` columns and 1 `cascade:` column to `SchemaRegistry`, then calling `_create_extractor()`, returns a `SchemaExtractor` (not `DefaultExtractor`) |
| AC-5.2 | Dynamic row model accepts extra fields | The dynamically generated Pydantic model includes all schema columns and passes `model_validate()` without `extra="forbid"` rejection |
| AC-5.3 | Derived fields return None | Columns with `source=None` return `None` when no `_extract_{name}` method exists on the extractor |
| AC-5.4 | Existing extractors preserved | `_create_extractor("Unit")` returns `UnitExtractor`, `_create_extractor("Contact")` returns `ContactExtractor` -- hand-coded extractors take precedence |
| AC-5.5 | DefaultExtractor preserved for unknown types | `_create_extractor("*")` and `_create_extractor("SomeUnregisteredType")` return `DefaultExtractor` for task types with no schema |
| AC-5.6 | Dynamic model cached | The `pydantic.create_model()` call for a given schema type happens once and is reused across extraction calls (not regenerated per task) |
| AC-5.7 | Thread safety | Concurrent calls to `SchemaExtractor._build_dynamic_row_model()` from multiple threads do not produce race conditions or duplicate model classes |

### US-6: Completeness Test Catches Triad Gaps

**As** a developer adding a new entity schema,
**I want** a parametrized test that iterates all registered schemas and verifies each can produce a DataFrame without crashing,
**so that** the B1-class wiring gap (schema registered without capable extractor) is caught in CI before deployment.

| AC | Criterion | Testable Assertion |
|----|-----------|-------------------|
| AC-6.1 | Test iterates all schemas | Test is parametrized over `SchemaRegistry.list_task_types()` |
| AC-6.2 | Each schema extracts without crash | For each task type, `_create_extractor(task_type)` returns an extractor whose `_create_row()` accepts a dict with all schema column names as keys |
| AC-6.3 | Extra-column schemas do not use DefaultExtractor | For schemas with columns beyond the base 12, the extractor is NOT `DefaultExtractor` (which would crash on `TaskRow(extra="forbid")`) |
| AC-6.4 | Test is additive | Adding a new schema to `SchemaRegistry` automatically includes it in the completeness test with zero test code changes |

### US-7: Import-Time Validation Warns on Incomplete Wiring

**As** a system operator,
**I want** the application to emit structured log warnings at startup when a schema is registered without a capable extractor,
**so that** incomplete wiring is visible in Lambda/API startup logs without crashing the application.

| AC | Criterion | Testable Assertion |
|----|-----------|-------------------|
| AC-7.1 | Warning emitted, not error | A schema registered without a matching extractor produces a `logger.warning()` call, not an exception |
| AC-7.2 | Warning is structured | The warning includes the entity name and schema identifier in the log `extra` dict |
| AC-7.3 | Application starts normally | Even with incomplete wiring, the application initializes and serves requests for fully-wired entities |
| AC-7.4 | No warning for complete wiring | Entities with full extractor support (Unit, Contact) produce no import-time warnings |

### US-8: Wiring Architecture Reduces Shotgun Surgery

**As** a future entity author,
**I want** the number of files I must touch to add full DataFrame support for a new entity to be minimized,
**so that** I can add entities without coordinating changes across disconnected subsystems.

| AC | Criterion | Testable Assertion |
|----|-----------|-------------------|
| AC-8.1 | Fewer touch points | The number of files requiring modification to add a new entity's DataFrame support is reduced from the current 5+ (row model, extractor, extractor factory, extractor __init__, cascading fields) |
| AC-8.2 | No match/case maintenance | The `_create_extractor()` fallback to `SchemaExtractor` eliminates the need for a new `case` branch for entities without custom derived logic |
| AC-8.3 | Architecture decision deferred | Specific architecture (descriptor-driven, triad-based, or test-only enforcement) is decided by Architect in Phase 2 based on evaluation criteria in Section 7 |

---

## 4. Functional Requirements

### Must Have (M)

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-1 | `SchemaExtractor(BaseExtractor)` class that dynamically generates a Pydantic row model from any `DataFrameSchema` using `pydantic.create_model()` | M | User Decision #2 |
| FR-2 | `SchemaExtractor._create_row()` calls `model_validate()` on the dynamically generated model, not `TaskRow` | M | B1 root cause |
| FR-3 | `_create_extractor()` returns `SchemaExtractor` for task types with registered schemas that have extra columns beyond base 12, when no dedicated extractor exists | M | User Decision #2 |
| FR-4 | `_create_extractor("Unit")` returns `UnitExtractor`; `_create_extractor("Contact")` returns `ContactExtractor` | M | User Decision #2 |
| FR-5 | `DefaultExtractor` remains the fallback for task types with no registered schema (the `"*"` wildcard case and truly unknown types) | M | Backward compat |
| FR-6 | Derived fields (`source=None`) return `None` in `SchemaExtractor` -- no traversal logic | M | User Decision #5 |
| FR-7 | Parametrized completeness test iterating `SchemaRegistry.list_task_types()` | M | User Decision #6 |
| FR-8 | Import-time warning (not error) for schemas without capable extractors | M | User Decision #6 |
| FR-9 | All 4 broken schemas (Offer, Business, AssetEdit, AssetEditHolder) produce valid DataFrames; Contact and Unit verified as still working | M | User Decision #7 |
| FR-10 | Dynamic row model generation cached per schema type (not per extraction call) | M | Performance |

### Should Have (S)

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-11 | Dtype-to-Python-type mapping covers all types in existing schemas: Utf8, Int64, Float64, Date, Datetime, Decimal, Boolean, List[Utf8] | S | Correctness |
| FR-12 | List-type fields default to `[]` when None (matching existing UnitRow/ContactRow behavior) | S | Consistency |
| FR-13 | `SchemaExtractor._extract_type()` returns `schema.task_type` | S | Consistency with BaseExtractor |
| FR-14 | Schema audit discovers any schemas not in the known list of 7 (including `"*"` base) | S | User Decision #7 |

### Could Have (C)

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-15 | `SchemaExtractor` handles `_extract_{name}()` method delegation for derived fields on subclasses (allowing future opt-in derived logic) | C | Extensibility |
| FR-16 | Deferred work items logged to `.claude/wip/TODO.md` | C | User Decision #9 |

### Won't Have (W) -- This Sprint

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-17 | `cascade:MRR` source annotation change | W | User Decision #4 (deferred) |
| FR-18 | Traversal unification for derived fields | W | User Decision #5 (deferred) |
| FR-19 | Query CLI utility | W | Out of scope |
| FR-20 | MRR deduplication documentation | W | Out of scope |

---

## 5. Non-Functional Requirements

| ID | Requirement | Target | Rationale |
|----|-------------|--------|-----------|
| NFR-1 | Thread safety | `SchemaExtractor._build_dynamic_row_model()` must be safe for concurrent use | Cache warming runs multi-threaded via `ThreadPoolExecutor` |
| NFR-2 | Model caching | Dynamic model generated once per schema type, stored as instance attribute | `pydantic.create_model()` is not free; cache prevents per-task overhead |
| NFR-3 | Startup time | No startup time regression > 100ms from import-time validation | Lambda cold starts are latency-sensitive |
| NFR-4 | Backward compatibility | `UnitExtractor` and `ContactExtractor` behavior unchanged | Existing consumers must not observe behavior differences |
| NFR-5 | Backward compatibility | `DefaultExtractor` still works for `"*"` (BASE_SCHEMA) task type | Query engine uses `"*"` for ad-hoc queries |
| NFR-6 | Test suite stability | All existing tests (8588+) continue to pass | Zero regressions |
| NFR-7 | Import-time safety | Malformed validation paths produce warnings, never crash startup | Risk R1.1 mitigation |

---

## 6. Out of Scope

The following items are explicitly excluded from this sprint. They are documented here to prevent scope creep and to provide traceability for future work.

| Item | Reason | Tracking |
|------|--------|----------|
| `cascade:MRR` source annotation change (B2) | User Decision #4: "this is nuanced because MRR is often directly populated, but we also need enforcement of cascade logic in unit-of-work save pattern for field overwrites when parent value changes" | Deferred to backlog |
| Traversal unification for derived fields | User Decision #5: "this needs to be generalized much better with its own sprint. Your proposition fails to capture the relevant nuance. Asset_edit might need to walk [office_phone, vertical, offer_id] -> ... -> unit -> offer with all 3 fields" | Separate initiative |
| Query CLI utility (B4) | Developer convenience, not blocking production | Backlog |
| MRR deduplication by (office_phone, vertical) documentation (B3) | Data aggregation guidance, not a code change | Backlog |
| `is_completed` naming documentation (B6) | Minor naming documentation, not a functional issue | Backlog |
| Script-level query entry point | Not a production requirement | Backlog |

---

## 7. Architecture Decision Criteria

The Phase 2 Architect must select a wiring architecture from three candidates:

- **(a) Descriptor-driven auto-wiring**: Add 3-4 fields to `EntityDescriptor`, rewire consumers to read from descriptors
- **(b) DataFrameTriad co-location**: Create `DataFrameTriad` dataclass binding schema+extractor+row, with `TriadRegistry` in `dataframes/`
- **(c) Test-only enforcement**: Completeness test + `SchemaExtractor` fallback, no wiring architecture changes

The Architect MUST evaluate each candidate against these criteria. The criteria are ordered by importance (MUST-pass criteria first).

### MUST-PASS Criteria

| # | Criterion | Description | How to Evaluate |
|---|-----------|-------------|----------------|
| C1 | Circular import safety | No circular imports introduced between `core/` and `dataframes/` | Import `core.entity_registry` and `dataframes.builders.base` in both orders; verify no `ImportError`. Run `python -c "import autom8_asana"` cleanly. |
| C2 | All existing tests pass | 8588+ tests pass with zero regressions | `.venv/bin/pytest tests/ -x -q --timeout=60` |
| C3 | All 5 broken schemas work | `to_dataframe()` succeeds for Offer, Business, AssetEdit, AssetEditHolder (Contact already works) | Unit tests with mock tasks for each schema type |

### EVALUATION Criteria (Weighted)

| # | Criterion | Weight | Description |
|---|-----------|--------|-------------|
| C4 | Startup time impact | HIGH | Import-time validation must not regress startup by > 100ms. Lambda cold starts are latency-sensitive. Measure with `time python -c "from autom8_asana.core.entity_registry import get_registry"` before and after. |
| C5 | IDE refactoring support | MEDIUM | Can a developer rename an extractor class and have their IDE find all references? Real imports score higher than dotted-path strings. |
| C6 | God-object trajectory | MEDIUM | Does the approach add fields to `EntityDescriptor` (currently 21 fields)? At what field count does the descriptor become a maintenance liability? What precedent does it set for future subsystem wiring? |
| C7 | Test isolation | MEDIUM | Can DataFrame unit tests run without initializing the entity registry? Can extractor tests import their class directly without fixtures? |
| C8 | Incremental deployability | LOW | Can each phase be deployed independently? Can it be rolled back without coordinated changes? |
| C9 | Matches existing codebase patterns | LOW | Does the approach extend proven patterns (`model_class_path`, `SchemaRegistry` singleton) or introduce new abstractions (`TriadRegistry`, metaclasses)? |

### Decision Format

The Architect's TDD must include:
1. A scored matrix rating each candidate (a/b/c) against C4-C9
2. A circular import analysis for the chosen approach
3. An explicit GO/NO-GO verdict for each MUST-PASS criterion

---

## 8. Risk Register

| ID | Risk | Likelihood | Impact | Severity | Mitigation |
|----|------|-----------|--------|----------|------------|
| R1.1 | Import-time validation crash | Medium | Critical | CRITICAL | FR-8: Warnings only (`try/except` + `logger.warning()`), never crash startup. NFR-7 enforces this. |
| R1.2 | Dynamic `create_model()` produces invalid Pydantic model | Low | High | HIGH | Unit tests for each dtype mapping (FR-11). Test with all 8 dtype strings present in existing schemas. |
| R2.1 | SchemaExtractor row model not accepted by Polars DataFrame builder | Low | High | HIGH | `to_dict()` method inherited from `TaskRow` converts Decimals to floats. Test end-to-end: extract -> to_dict -> `pl.DataFrame`. |
| R3.1 | Dual-wiring divergence during architecture migration | Medium | Medium | HIGH | If descriptor or triad approach selected: atomic cutover per consumer with cross-reference tests verifying old and new paths produce identical results. |
| R4.1 | Circular import deadlock between `core/` and `dataframes/` | Low | Critical | HIGH | All cross-boundary imports deferred to function scope (not module scope). CI lint check: no module-level imports from `dataframes/` in `core/entity_registry.py`. |
| R5.1 | SchemaExtractor `_extract_{name}()` delegation conflicts with `BaseExtractor` base methods | Low | Medium | MEDIUM | `BaseExtractor` already defines `_extract_name()`, `_extract_type()`, etc. for the base 12 fields. SchemaExtractor must NOT shadow these. Only delegate for columns NOT in the base 12. |
| R6.1 | Thread-unsafe dynamic model cache | Low | Medium | MEDIUM | Use `threading.Lock` or `functools.lru_cache` for model generation. Test with concurrent extraction from 4 threads. |
| R7.1 | BUSINESS_SCHEMA duplicate `name` column | High | Medium | MEDIUM | `business.py` schema uses `c not in BASE_COLUMNS` (object equality) instead of name-based dedup, producing two `name` columns. Fix dedup filter to match OFFER_SCHEMA/ASSET_EDIT_SCHEMA pattern: `c.name not in {col.name for col in BASE_COLUMNS}`. |

---

## 9. Success Metrics

| # | Metric | Target | Measurement |
|---|--------|--------|-------------|
| SM-1 | Schema crash rate | 0 schemas crash on `to_dataframe()` | Completeness test (US-6) passes for all `SchemaRegistry.list_task_types()` |
| SM-2 | Completeness test coverage | 100% of registered schemas covered | Test is parametrized over `list_task_types()` -- adding a schema automatically adds a test case |
| SM-3 | Import-time warning fires | Warnings emitted for schemas without dedicated extractors | Structured log assertion in test |
| SM-4 | Existing test stability | 8588+ tests pass | `.venv/bin/pytest tests/ -x -q --timeout=60` returns 0 exit code |
| SM-5 | Startup time regression | < 100ms regression | `time python -c "from autom8_asana.core.entity_registry import get_registry"` before/after comparison |
| SM-6 | Backward compatibility | UnitExtractor, ContactExtractor, DefaultExtractor behavior unchanged | Existing unit/contact/default extractor tests pass without modification |

---

## 10. Schema Column Inventory

This section documents every column in every broken schema for implementer reference. The Architect and Principal Engineer use this to verify dtype mappings and source dispatch coverage.

### OFFER_SCHEMA (23 columns: 12 base + 11 extra)

| Column | Dtype | Source | Source Type |
|--------|-------|--------|-------------|
| office | Utf8 | None | derived |
| office_phone | Utf8 | cascade:Office Phone | cascade |
| vertical | Utf8 | cascade:Vertical | cascade |
| vertical_id | Utf8 | None | derived |
| specialty | Utf8 | cf:Specialty | cf |
| offer_id | Utf8 | cf:Offer ID | cf |
| platforms | List[Utf8] | cf:Platforms | cf |
| language | Utf8 | cf:Language | cf |
| cost | Utf8 | cf:Cost | cf |
| mrr | Utf8 | cascade:MRR | cascade |
| weekly_ad_spend | Utf8 | cascade:Weekly Ad Spend | cascade |

Note: OFFER_COLUMNS declares a `name` column with `source=None`, but the schema construction filter (`c.name not in {col.name for col in BASE_COLUMNS}`) correctly deduplicates it, keeping only the base `name` column (source="name"). The offer-specific `name` override is filtered out. This means OFFER_SCHEMA's `name` column uses direct attribute access, not derived logic.

### BUSINESS_SCHEMA (18 columns: 12 base + 6 extra -- but includes duplicate `name`)

| Column | Dtype | Source | Source Type |
|--------|-------|--------|-------------|
| company_id | Utf8 | cf:Company ID | cf |
| name | Utf8 | None | derived (DUPLICATE -- see note) |
| office_phone | Utf8 | cf:Office Phone | cf |
| stripe_id | Utf8 | cf:Stripe ID | cf |
| booking_type | Utf8 | cf:Booking Type | cf |
| facebook_page_id | Utf8 | cf:Facebook Page ID | cf |

**Latent Bug**: BUSINESS_SCHEMA's dedup filter uses `c not in BASE_COLUMNS` (ColumnDef object equality), not name-based dedup. Since the business `name` ColumnDef (source=None) is not equal to the base `name` ColumnDef (source="name"), BOTH pass through. The schema has two columns named `name` -- the base one at position 1 (source="name") and the business one at position 13 (source=None). When Polars builds a DataFrame from this schema, the second `name` column will shadow the first. The Principal Engineer should fix this dedup filter to use name-based dedup (`c.name not in {col.name for col in BASE_COLUMNS}`) matching the pattern used by OFFER_SCHEMA and ASSET_EDIT_SCHEMA.

### ASSET_EDIT_SCHEMA (33 columns: 12 base + 21 extra)

| Column | Dtype | Source | Source Type |
|--------|-------|--------|-------------|
| started_at | Utf8 | cf:Started At | cf |
| process_completed_at | Utf8 | cf:Process Completed At | cf |
| process_notes | Utf8 | cf:Process Notes | cf |
| status | Utf8 | cf:Status | cf |
| priority | Utf8 | cf:Priority | cf |
| process_due_date | Utf8 | cf:Due Date | cf |
| assigned_to | Utf8 | cf:Assigned To | cf |
| vertical | Utf8 | cascade:Vertical | cascade |
| office_phone | Utf8 | cascade:Office Phone | cascade |
| specialty | List[Utf8] | cf:Specialty | cf |
| asset_approval | Utf8 | cf:Asset Approval | cf |
| asset_id | Utf8 | cf:Asset ID | cf |
| editor | Utf8 | cf:Editor | cf |
| reviewer | Utf8 | cf:Reviewer | cf |
| offer_id | Int64 | cf:Offer ID | cf |
| raw_assets | Utf8 | cf:Raw Assets | cf |
| review_all_ads | Boolean | cf:Review All Ads | cf |
| score | Float64 | cf:Score | cf |
| asset_edit_specialty | List[Utf8] | cf:Specialty | cf |
| template_id | Int64 | cf:Template ID | cf |
| videos_paid | Int64 | cf:Videos Paid | cf |

Note: AssetEdit has ZERO `source=None` columns. All 21 extra columns are `cf:` or `cascade:`. This is the ideal candidate for SchemaExtractor -- no custom derived logic needed at all.

### ASSET_EDIT_HOLDER_SCHEMA (13 columns: 12 base + 1 extra)

| Column | Dtype | Source | Source Type |
|--------|-------|--------|-------------|
| office_phone | Utf8 | cascade:Office Phone | cascade |

### Required Dtype-to-Python Mappings (for `create_model()`)

| Schema Dtype | Python Type | Default | Appears In |
|-------------|-------------|---------|------------|
| Utf8 | `str` | `None` | All schemas |
| Int64 | `int` | `None` | AssetEdit (offer_id, template_id, videos_paid) |
| Float64 | `float` | `None` | AssetEdit (score) |
| Boolean | `bool` | `None` | AssetEdit (review_all_ads) |
| Date | `datetime.date` | `None` | Base (date, due_on) |
| Datetime | `datetime.datetime` | `None` | Base (created, completed_at, last_modified) |
| Decimal | `float` | `None` | Unit (mrr, weekly_ad_spend, discount) |
| List[Utf8] | `list[str]` | `[]` | Offer (platforms), AssetEdit (specialty, asset_edit_specialty), Unit (products, languages) |

---

## 11. Dependency Map

```
SchemaExtractor (NEW)
  inherits: BaseExtractor (extractors/base.py)
  uses: pydantic.create_model()
  uses: DataFrameSchema (models/schema.py)
  uses: ColumnDef (models/schema.py)
  uses: TaskRow (models/task_row.py) as base class for dynamic models

_create_extractor() modification (builders/base.py)
  imports: SchemaExtractor (NEW)
  preserves: UnitExtractor, ContactExtractor (existing)
  preserves: DefaultExtractor (existing, for "*" and unknown types)

Completeness test (NEW)
  imports: SchemaRegistry (models/registry.py)
  imports: _create_extractor (builders/base.py) or equivalent
  parametrized over: SchemaRegistry.list_task_types()

Import-time validation (location TBD by Architect)
  reads: SchemaRegistry or EntityDescriptor metadata
  emits: logger.warning() for incomplete wiring
  MUST NOT: raise exceptions or crash startup
```

---

## 12. Handoff Checklist

- [x] All user stories complete with testable acceptance criteria
- [x] Functional requirements prioritized (MoSCoW)
- [x] Non-functional requirements have specific, measurable targets
- [x] Edge cases enumerated (see Risk Register, Schema Column Inventory, and `name` column override note)
- [x] No unresolved stakeholder conflicts (all 9 user decisions locked)
- [x] Open questions list empty (cascade:MRR and traversal unification explicitly deferred)
- [x] Success criteria testable by QA Adversary
- [x] Out of scope documented to prevent scope creep
- [x] Impact assessment included (high: data_model, api_contract)
- [x] All artifacts verified via Read tool
- [x] Attestation table included (below)

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/PRD-entity-extensibility.md` | Pending (this file) |
| Canary bugs spike | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-offer-query-canary-bugs.md` | Read |
| Extensibility spike | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-entity-extensibility-architecture.md` | Read |
| First-principles analysis | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/ANALYSIS-entity-extensibility-first-principles.md` | Read |
| Counter-proposal | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/COUNTER-entity-extensibility-plugin-architecture.md` | Read |
| Option A steel-man | `/Users/tomtenuta/Code/autom8_asana/docs/design/ARCH-descriptor-driven-auto-wiring.md` | Read |
| Sprint plan | `/Users/tomtenuta/.claude/plans/jaunty-zooming-star.md` | Read |
| BaseExtractor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/base.py` | Read |
| TaskRow / UnitRow / ContactRow | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/task_row.py` | Read |
| SchemaRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Read |
| _create_extractor() | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/base.py` (lines 509-542) | Read |
| OFFER_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/offer.py` | Read |
| UNIT_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/unit.py` | Read |
| BUSINESS_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/business.py` | Read |
| ASSET_EDIT_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/asset_edit.py` | Read |
| ASSET_EDIT_HOLDER_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/asset_edit_holder.py` | Read |
| BASE_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/base.py` | Read |
| CONTACT_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/contact.py` | Read |
| EntityDescriptor / EntityRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_registry.py` | Read |
| DataFrameSchema / ColumnDef | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | Read |
