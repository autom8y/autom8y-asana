# PRD: Structured Dataframe Layer

## Metadata
- **PRD ID**: PRD-0003
- **Status**: In Review
- **Version**: 2.0
- **Author**: Requirements Analyst
- **Created**: 2025-12-09
- **Last Updated**: 2025-12-09
- **Stakeholders**: autom8 team, SDK consumers, data analysts
- **Related PRDs**:
  - [PRD-0001](PRD-0001-sdk-extraction.md) (SDK Extraction - prerequisite)
  - [PRD-0002](PRD-0002-intelligent-caching.md) (Intelligent Caching - dependency for struc caching)
- **Related ADRs**:
  - [ADR-0021](../decisions/ADR-0021-dataframe-caching-strategy.md) (Dataframe Caching Strategy)
  - [ADR-0027](../decisions/ADR-0027-dataframe-layer-migration-strategy.md) (Migration Strategy)

## Problem Statement

The autom8_asana SDK currently provides raw Asana task data as dictionaries or Pydantic models, requiring consumers to manually extract, transform, and structure this data for analysis. The legacy autom8 monolith contains a battle-tested `struc()` method (~1,000 lines at `project/main.py:793-1225`) that transforms task hierarchies into analyzable dataframes, but this code is tightly coupled to the monolith's business logic, SQL integrations, and threading infrastructure.

**Current State**:
- SDK returns tasks as `AsanaTask` Pydantic models or raw dicts
- No standardized way to extract custom field values into typed columns
- No support for flattening task hierarchies into tabular format
- Consumers must write custom extraction logic for each use case
- Legacy `struc()` uses `pandas.DataFrame` with ThreadManager (10 concurrent workers)

**Legacy System (autom8)**:
- `struc()` method processes entire projects/sections into dataframes
- Each task subclass defines `STRUC_COLS` for subclass-specific columns (e.g., Unit has 5, Contact has 9)
- Uses `ThreadManager` for concurrent task processing with controlled concurrency
- Caches computed struc data via S3 with per-task versioning
- Generates 30+ fields per task including custom field extraction

**Impact of Not Solving**:
1. SDK consumers must replicate complex transformation logic
2. No type safety for extracted values (custom fields return `Any`)
3. Performance penalty from serial processing without concurrency control
4. Inconsistent field naming across different consumers
5. Cannot migrate legacy autom8 dataframe features to extracted SDK
6. Data analysts cannot efficiently query Asana data

## Goals & Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Dataframe generation time | 20-30% faster than legacy struc() | Benchmark same project with both methods |
| Type coverage | 100% of MVP fields have defined types | Static analysis of DataFrame schema |
| Field parity | All 32 MVP fields supported (12 base + 11 Unit + 9 Contact) | Feature matrix comparison |
| Memory efficiency | <= 1.5x raw task memory footprint | Memory profiler on 1,000 tasks |
| API ergonomics | Single method call for dataframe generation | Code review of public API |
| Cache integration | Uses TDD-0008 struc caching | Verify cache hits on repeated calls |

## Scope

### In Scope

**MVP Task Types (Session 6-7)**:
- **Unit**: Business unit representation with 11 custom fields
- **Contact**: Person/contact representation with 9 custom fields

**MVP Field Set (32 Total)**:

Base Fields (12 - all task types):
- `gid`: Task identifier (str)
- `name`: Task name (str)
- `type`: Task type discriminator (str)
- `date`: Primary date field (date | None)
- `created`: Task creation timestamp (datetime)
- `due_on`: Due date (date | None)
- `is_completed`: Completion status (bool)
- `completed_at`: Completion timestamp (datetime | None)
- `url`: Asana task URL (str)
- `last_modified`: Last modification timestamp (datetime)
- `section`: Section name (str | None)
- `tags`: Tag names (list[str])

Unit-specific Fields (11):
- `mrr`: Monthly recurring revenue (Decimal | None)
- `weekly_ad_spend`: Weekly advertising spend (Decimal | None)
- `products`: Product list (list[str])
- `languages`: Supported languages (list[str])
- `discount`: Discount percentage (Decimal | None)
- `office`: Office location (str | None) - derived from business.office_phone lookup
- `office_phone`: Office phone number (str | None) - derived from business
- `vertical`: Business vertical (str | None)
- `vertical_id`: Vertical identifier (str | None) - derived from Vertical model
- `specialty`: Business specialty (str | None)
- `max_pipeline_stage`: Maximum pipeline stage reached (str | None)

Contact-specific Fields (9):
- `full_name`: Contact full name (str | None)
- `nickname`: Contact nickname (str | None)
- `contact_phone`: Contact phone number (str | None)
- `contact_email`: Contact email address (str | None)
- `position`: Job position/title (str | None)
- `employee_id`: Employee identifier (str | None)
- `contact_url`: Contact URL/website (str | None)
- `time_zone`: Contact time zone (str | None)
- `city`: Contact city (str | None)

**Core Capabilities**:
- `TaskRow` Pydantic model for type-safe row representation
- `to_dataframe()` method on Project and Section classes
- Polars DataFrame output (not pandas)
- Schema definitions with explicit types
- Custom field extraction with type coercion
- Concurrent task processing with configurable concurrency
- Integration with TDD-0008 struc caching (STRUC entry type)
- Deprecation wrapper for legacy `struc()` method

**Public API**:
- `Project.to_dataframe(task_type: str | None = None) -> pl.DataFrame`
- `Section.to_dataframe(task_type: str | None = None) -> pl.DataFrame`
- `DataFrame.schema` property for type introspection
- Schema registry for extensibility

### Out of Scope

**Task Types (Post-MVP)**:
- Task (generic base class)
- Project (project-level dataframes)
- Portfolio (portfolio-level aggregation)
- Offer (legacy business type)
- All 50+ other task subclasses

**Features (Post-MVP)**:
- Pandas DataFrame output option
- Real-time streaming dataframe updates
- Cross-project aggregation
- Custom schema registration at runtime
- SQL/database export integrations
- Visualization helpers (charts, dashboards)

**Explicitly Excluded**:
- Breaking changes to existing SDK API
- Modifications to `AsanaTask` model structure
- Direct database writes from dataframe layer
- Custom field schema auto-discovery (schemas are predefined)

---

## Requirements

### Functional Requirements

#### Model Requirements (FR-MODEL-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-MODEL-001 | SDK shall define `DataFrameSchema` class for type-safe column definitions | Must | Schema specifies column name, type (Polars dtype), nullability, and source field |
| FR-MODEL-002 | SDK shall provide `BaseSchema` with 12 common fields applicable to all tasks | Must | Schema includes gid, name, type, date, created, due_on, is_completed, completed_at, url, last_modified, section, tags |
| FR-MODEL-003 | SDK shall support schema inheritance for type-specific extensions | Must | UnitSchema and ContactSchema inherit from BaseSchema without field duplication |
| FR-MODEL-004 | SDK shall provide schema registry for type-to-schema mapping | Must | `SchemaRegistry.get_schema(task_type: str) -> DataFrameSchema` returns appropriate schema |
| FR-MODEL-005 | SDK shall validate that extracted values match declared types | Should | Type mismatches logged as warnings; values coerced or set to null |
| FR-MODEL-006 | SDK shall expose schema definitions for external tooling | Should | `schema.to_dict()` returns JSON-serializable schema definition |
| FR-MODEL-007 | SDK shall support optional fields with explicit null handling | Must | Schema declares which fields are nullable; non-null violations raise errors |
| FR-MODEL-008 | SDK shall extract base fields from `AsanaTask` attributes | Must | All 12 base fields extracted correctly from task model |
| FR-MODEL-009 | SDK shall extract section name from task's section membership | Must | Section extracted from task's memberships for the target project |
| FR-MODEL-010 | SDK shall extract tag names as list | Must | Tags extracted as `list[str]` of tag names |
| FR-MODEL-011 | SDK shall construct task URL from GID | Must | URL format: `https://app.asana.com/0/0/{gid}` |
| FR-MODEL-012 | SDK shall parse datetime strings to Python datetime objects | Must | ISO 8601 strings converted to datetime; dates to date objects |
| FR-MODEL-020 | SDK shall define `TaskRow` as a Pydantic model representing a single extracted row | Must | TaskRow has typed fields matching schema, validates on construction |
| FR-MODEL-021 | TaskRow shall support all 12 base fields with proper types | Must | Fields: gid (str), name (str), type (str), date (date\|None), created (datetime), due_on (date\|None), is_completed (bool), completed_at (datetime\|None), url (str), last_modified (datetime), section (str\|None), tags (list[str]) |
| FR-MODEL-022 | TaskRow shall support extension fields via schema-driven approach | Must | Unit and Contact fields added dynamically based on task type |
| FR-MODEL-023 | TaskRow shall be frozen (immutable) after construction | Should | Pydantic model with `frozen=True` |
| FR-MODEL-024 | TaskRow shall provide `to_dict()` method for Polars compatibility | Must | Returns dict suitable for `pl.DataFrame` construction |
| FR-MODEL-025 | TaskRow shall track extraction metadata (source task GID, extraction time) | Should | Metadata fields available but excluded from dataframe output |
| FR-MODEL-030 | Schema registry shall be a singleton with lazy initialization | Must | Single instance, schemas loaded on first access |
| FR-MODEL-031 | Schema registry shall support runtime schema registration (post-MVP) | Could | `registry.register(task_type, schema)` for post-MVP types |
| FR-MODEL-032 | Schema registry shall validate schema compatibility on registration | Should | Conflicting schemas rejected with clear error |
| FR-MODEL-033 | Schema registry shall support schema versioning | Must | Each schema has version string for cache compatibility |

#### Project Requirements (FR-PROJECT-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-PROJECT-001 | SDK shall provide `to_dataframe()` method on Project class | Must | Method signature: `to_dataframe(task_type: str \| None = None, concurrency: int = 10) -> pl.DataFrame` |
| FR-PROJECT-002 | SDK shall filter tasks by type when `task_type` parameter provided | Must | Only tasks matching specified type included in dataframe |
| FR-PROJECT-003 | SDK shall process tasks concurrently with configurable limit | Must | Default concurrency of 10; configurable via parameter |
| FR-PROJECT-004 | SDK shall include task type column for mixed-type dataframes | Must | When `task_type=None`, include `type` column with discriminator |
| FR-PROJECT-005 | SDK shall handle empty task lists gracefully | Must | Empty input returns empty DataFrame with correct schema |
| FR-PROJECT-006 | SDK shall provide sync and async variants of to_dataframe | Must | `to_dataframe()` (sync) and `to_dataframe_async()` (async) |
| FR-PROJECT-010 | ProjectDataFrame shall support section filtering | Should | `project.to_dataframe(sections=["Active"])` filters by section |
| FR-PROJECT-011 | ProjectDataFrame shall support completion status filtering | Should | `project.to_dataframe(completed=False)` excludes completed |
| FR-PROJECT-012 | ProjectDataFrame shall support date range filtering | Could | `project.to_dataframe(since=date)` filters by modified_at |
| FR-PROJECT-013 | ProjectDataFrame shall expose row count without full extraction | Should | `project.estimate_dataframe_size()` returns task count |

#### Section Requirements (FR-SECTION-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SECTION-001 | SDK shall provide `to_dataframe()` method on Section class | Must | Method signature: `to_dataframe(task_type: str \| None = None, concurrency: int = 10) -> pl.DataFrame` |
| FR-SECTION-002 | SectionDataFrame shall filter tasks by section membership | Must | Only tasks belonging to target section included |
| FR-SECTION-003 | SectionDataFrame shall inherit from common DataFrame builder | Must | Shared logic with ProjectDataFrame |
| FR-SECTION-004 | SectionDataFrame shall support task type filtering | Must | `section.to_dataframe(task_type="Unit")` works |
| FR-SECTION-005 | SectionDataFrame shall use project context for cache keys | Must | Cache key includes project GID for section operations |

#### Custom Field Requirements (FR-CUSTOM-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CUSTOM-001 | SDK shall document expected Asana custom field names for each schema field | Must | Each schema field specifies source custom field GID or attribute path |
| FR-CUSTOM-002 | SDK shall extract custom field values by custom field GID | Must | Custom fields resolved by GID, not name (names can change) |
| FR-CUSTOM-003 | SDK shall coerce custom field values to schema-defined types | Must | Enum fields return display_value, number fields return Decimal, etc. |
| FR-CUSTOM-004 | SDK shall handle multi-enum custom fields as lists | Must | Multi-select fields extracted as `list[str]` of display values |
| FR-CUSTOM-005 | SDK shall handle missing custom fields gracefully | Must | Missing fields return None, not raise exceptions |
| FR-CUSTOM-010 | MVP custom field GIDs shall be hardcoded constants | Must | No runtime configuration needed |
| FR-CUSTOM-011 | Custom field GID constants shall be documented with source | Must | Comments with Asana field names |
| FR-CUSTOM-012 | Post-MVP shall support configurable field GIDs | Could | Config file support |

#### Subclass Requirements (FR-SUBCLASS-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SUBCLASS-001 | SDK shall provide `UnitSchema` extending BaseSchema with 11 Unit-specific fields | Must | Schema includes mrr, weekly_ad_spend, products, languages, discount, office, office_phone, vertical, vertical_id, specialty, max_pipeline_stage |
| FR-SUBCLASS-002 | SDK shall provide `ContactSchema` extending BaseSchema with 9 Contact-specific fields | Must | Schema includes full_name, nickname, contact_phone, contact_email, position, employee_id, contact_url, time_zone, city |
| FR-SUBCLASS-003 | SDK shall handle type-specific extraction logic per task type | Must | Unit extraction differs from Contact extraction based on schema |

#### Cache Requirements (FR-CACHE-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-001 | SDK shall cache computed row data using STRUC entry type from TDD-0008 | Must | Extracted row cached under `asana:struc:{task_gid}:{project_gid}` |
| FR-CACHE-002 | SDK shall check cache before extracting each task | Must | Cache hit skips extraction; cache miss triggers extraction and cache write |
| FR-CACHE-003 | SDK shall invalidate struc cache when task modified_at changes | Must | Stale cache entries detected via version comparison |
| FR-CACHE-004 | SDK shall use batch cache retrieval for efficiency | Should | `get_batch()` for multiple task strucs in single Redis call |
| FR-CACHE-005 | SDK shall respect overflow thresholds for struc caching | Should | Tasks exceeding relationship thresholds skip struc caching |
| FR-CACHE-006 | SDK shall support cache bypass for debugging | Should | `to_dataframe(use_cache=False)` forces re-extraction |
| FR-CACHE-007 | SDK shall include struc version in cached data | Must | Cached struc includes schema version for migration support |
| FR-CACHE-008 | SDK shall handle cache failures gracefully | Must | Cache errors logged; extraction proceeds without caching |
| FR-CACHE-009 | SDK shall support struc cache warming | Should | `warm_struc(project_gid, task_gids)` pre-populates cache |
| FR-CACHE-010 | SDK shall emit cache events for struc operations | Should | Cache hit/miss/write events emitted via LogProvider |
| FR-CACHE-020 | Incremental refresh shall use story-based change detection | Should | Check stories since cache timestamp |
| FR-CACHE-021 | Story types triggering refresh: `*_changed` except `notes_changed`, `dependency_due_date_changed` | Should | Specific story type filtering implemented |
| FR-CACHE-022 | `*_from_tag` stories shall trigger refresh for non-automation projects | Should | Automation projects excluded from tag-based refresh |
| FR-CACHE-023 | Incremental refresh shall be disabled for projects > 50 tasks (use batch check instead) | Should | Threshold-based behavior switching |
| FR-CACHE-024 | Incremental refresh shall be opt-in via `to_dataframe(incremental=True)` | Should | Default is full refresh |

#### Export Requirements (FR-EXPORT-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-EXPORT-001 | SDK shall use Polars DataFrame as output format | Must | Return type is `polars.DataFrame`, not pandas |
| FR-EXPORT-002 | SDK shall generate dataframe with schema-defined column order | Should | Columns appear in schema-defined order for consistency |
| FR-EXPORT-003 | SDK shall support incremental dataframe building | Should | `append_to_dataframe(df, tasks)` adds rows without full rebuild |
| FR-EXPORT-004 | SDK shall support pandas conversion for gradual migration | Should | `to_dataframe().to_pandas()` returns pandas.DataFrame |
| FR-EXPORT-005 | SDK shall support legacy column ordering option | Could | `to_dataframe(legacy_order=True)` matches struc() column order |

#### Compatibility Requirements (FR-COMPAT-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-COMPAT-001 | SDK shall provide `struc()` method as deprecated alias | Must | `struc()` calls `to_dataframe()` internally with deprecation warning |
| FR-COMPAT-002 | SDK shall emit deprecation warning on `struc()` calls | Must | Warning includes migration path to `to_dataframe()` |
| FR-COMPAT-003 | SDK shall maintain field name compatibility for migrated consumers | Should | Column names match legacy struc output where possible |
| FR-COMPAT-004 | SDK shall document migration guide from struc() to to_dataframe() | Must | Documentation explains differences and migration steps |
| FR-COMPAT-005 | SDK shall preserve struc() behavior for at least 2 minor versions | Must | Deprecation period before removal |
| FR-COMPAT-006 | SDK shall log struc() usage for migration tracking | Should | Log includes caller location for identifying migration needs |
| FR-COMPAT-007 | SDK shall handle legacy callers expecting pandas DataFrame | Should | Detect pandas expectation and warn about breaking change |
| FR-COMPAT-008 | SDK shall provide struc() signature compatibility | Must | Parameters match legacy struc() where applicable |

#### Error Handling Requirements (FR-ERROR-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ERROR-001 | SDK shall define `DataFrameError` base exception | Must | All dataframe-related exceptions inherit from DataFrameError |
| FR-ERROR-002 | SDK shall define `SchemaNotFoundError` for unknown task types | Must | Raised when task_type has no registered schema |
| FR-ERROR-003 | SDK shall define `ExtractionError` for field extraction failures | Must | Includes task GID, field name, and original exception |
| FR-ERROR-004 | SDK shall define `TypeCoercionError` for type conversion failures | Must | Includes expected type, actual value, and field name |
| FR-ERROR-005 | SDK shall continue processing on individual task extraction failures | Must | Failed tasks logged; other tasks still included in result |
| FR-ERROR-006 | SDK shall provide extraction error summary in result | Should | `DataFrameResult` includes list of extraction errors |
| FR-ERROR-007 | SDK shall validate schema consistency before extraction | Should | Detect schema mismatches early with clear error messages |
| FR-ERROR-008 | SDK shall handle Asana API errors during task loading | Must | API errors wrapped in DataFrameError with context |
| FR-ERROR-009 | SDK shall timeout long-running extractions | Should | Configurable timeout; TimeoutError raised if exceeded |
| FR-ERROR-010 | SDK shall provide partial results on interruption | Could | Keyboard interrupt returns partial dataframe |

---

### Non-Functional Requirements

#### Performance Requirements (NFR-PERF-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Dataframe generation time | 20-30% faster than legacy struc() | Benchmark identical project with both methods |
| NFR-PERF-002 | Per-task extraction time (cached) | < 5ms per task | Profiler measurement |
| NFR-PERF-003 | Per-task extraction time (uncached) | < 50ms per task | Profiler measurement |
| NFR-PERF-004 | Memory footprint | <= 1.5x raw task data size | Memory profiler on 1,000 tasks |
| NFR-PERF-005 | Concurrent extraction throughput | >= 100 tasks/second | Throughput test with 10 workers |
| NFR-PERF-006 | DataFrame construction overhead | < 100ms for 1,000 rows | Time from extracted data to DataFrame |
| NFR-PERF-007 | Cache hit improvement | >= 50% reduction in extraction time | Compare cached vs uncached benchmarks |
| NFR-PERF-008 | Startup overhead | < 50ms for schema initialization | Import time measurement |
| NFR-PERF-009 | Large project support | 10,000 tasks without OOM | Memory test with large project |
| NFR-PERF-010 | Polars operation efficiency | Use lazy evaluation where beneficial | Code review of Polars usage |
| NFR-PERF-020 | SDK shall use lazy evaluation for projects with > 100 tasks | Should | LazyFrame for large projects |
| NFR-PERF-021 | Lazy evaluation threshold shall be configurable | Could | Parameter or env var |
| NFR-PERF-022 | `to_dataframe(lazy=True)` shall force lazy evaluation regardless of size | Could | Override threshold |

#### Reliability Requirements (NFR-REL-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-REL-001 | Extraction success rate | >= 99.9% for valid tasks | Error rate in production logs |
| NFR-REL-002 | Type coercion success rate | >= 99% with graceful fallback | Coercion failure rate |
| NFR-REL-003 | Cache consistency | No stale data returned in strict mode | Integration tests |
| NFR-REL-004 | Thread safety | Zero race conditions | Concurrent test suite |
| NFR-REL-005 | Graceful degradation | Continue without cache on Redis failure | Degradation test |
| NFR-REL-006 | Idempotent extraction | Same input produces identical output | Determinism test |
| NFR-REL-007 | Error isolation | Single task failure doesn't fail batch | Fault injection test |
| NFR-REL-008 | Resource cleanup | No connection/memory leaks | 24-hour stability test |
| NFR-REL-009 | Timeout enforcement | Long operations terminate cleanly | Timeout test |
| NFR-REL-010 | Recovery from partial failure | Retry-safe operations | Recovery test |

#### Compatibility Requirements (NFR-COMPAT-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | Polars version support | >= 0.20.0 | CI matrix testing |
| NFR-COMPAT-002 | Python version support | 3.12+ | CI matrix testing |
| NFR-COMPAT-003 | Pandas interoperability | Seamless .to_pandas() conversion | Integration test |
| NFR-COMPAT-004 | Existing SDK compatibility | No breaking changes to public API | API diff analysis |
| NFR-COMPAT-005 | struc() deprecation timeline | Minimum 2 minor versions | Release notes |
| NFR-COMPAT-006 | Schema versioning | Support reading older cached schemas | Migration test |
| NFR-COMPAT-007 | Column name stability | No renames without deprecation | Schema diff analysis |
| NFR-COMPAT-008 | Type annotation coverage | 100% public API typed | mypy strict mode |
| NFR-COMPAT-009 | Serialization compatibility | DataFrame serializable to Parquet/Arrow | Serialization test |
| NFR-COMPAT-010 | Cache format stability | Cached struc readable across SDK versions | Version compatibility test |

#### Observability Requirements (NFR-OBS-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-OBS-001 | Extraction metrics | Emit per-task extraction latency | LogProvider integration |
| NFR-OBS-002 | Error logging | All extraction errors logged with context | Log audit |
| NFR-OBS-003 | Cache performance visibility | Hit/miss rates for struc cache | CacheMetrics integration |
| NFR-OBS-004 | Deprecation tracking | Log struc() usage with caller info | Log analysis |
| NFR-OBS-005 | Progress indication | Emit progress events for large extractions | Callback support |
| NFR-OBS-006 | Schema usage tracking | Log which schemas are used | Structured logging |
| NFR-OBS-007 | Performance profiling hooks | Support profiler attachment | Profiler integration |
| NFR-OBS-008 | Debug mode | Verbose logging option for troubleshooting | Configuration option |
| NFR-OBS-009 | Correlation ID propagation | Link extraction events to originating request | Context propagation |
| NFR-OBS-010 | Timing breakdown | Log time spent in extraction vs cache vs construction | Detailed timing |

---

## Design Decisions

This section documents key design decisions made during requirements analysis. These decisions guide the architect in TDD-0009 design.

### Decision 1: MVP vs. Nice-to-Have Fields

**Decision**: MVP includes 32 fields (12 base + 11 Unit + 9 Contact), including derived fields.

**Rationale**: Analysis of legacy `struc()` usage shows these fields cover the primary use cases. The legacy `struc()` also extracts derived fields that must be included:

| Field | Type | Source | Category |
|-------|------|--------|----------|
| office | str | Derived from business.office_phone lookup | Unit - Derived |
| office_phone | str | Derived from business | Unit - Derived |
| vertical | str | Unit custom field | Unit - Direct |
| vertical_id | str | Derived from Vertical model | Unit - Derived |
| specialty | str | Unit custom field | Unit - Direct |
| max_pipeline_stage | int | Derived from UnitHolder (for Contact) | Contact - Derived |

**Nice-to-Have (Post-MVP)**:
- Additional Unit fields from ASANA_FIELDS not in STRUC_COLS
- Additional Contact fields from ASANA_FIELDS not in STRUC_COLS
- Computed fields (e.g., age calculations, derived metrics)

### Decision 2: Custom Field Typing Approach

**Decision**: MVP uses static/hardcoded GIDs (Option A). Post-MVP supports hybrid with configurable extensions (Option C).

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Static (MVP)** | Type safety, IDE support, faster extraction | Requires code change for new fields |
| **Dynamic** | Flexibility, no code changes | Runtime type ambiguity, testing complexity |
| **Hybrid (Post-MVP)** | Best of both for extensibility | Implementation complexity |

The MVP prioritizes type safety and development velocity. The known custom field GIDs are stable in Asana, and schema changes are infrequent enough to warrant code changes.

### Decision 3: Lazy Evaluation Threshold

**Decision**: Use lazy evaluation (Polars LazyFrame) for projects with > 100 tasks.

**Rationale**:
- Polars LazyFrame benefits: query optimization, memory efficiency, parallel execution
- Threshold aligned with 10 workers x 10 tasks per worker
- Below threshold: Eager DataFrame construction for simpler debugging
- Above threshold: LazyFrame with `collect()` at end for performance
- Legacy struc() processes up to 50 tasks before enabling story-based change detection (reference: line 880)

**Implementation Notes**:
- Threshold is configurable via NFR-PERF-021
- `lazy=True` parameter overrides threshold (NFR-PERF-022)

### Decision 4: Incremental Refresh Mechanism

**Decision**: Story-based change detection, opt-in via `incremental=True`, disabled for projects > 50 tasks.

**Rationale** (from legacy `struc()` lines 880-937):
1. Check cached version timestamp
2. Fetch stories since cached version
3. Filter for `*_changed` story types (except `notes_changed`, `dependency_due_date_changed`)
4. If no changes, return cached data
5. If changes, re-extract full task

**Story Types Triggering Refresh**:
- All `*_changed` events (except `notes_changed`, `dependency_due_date_changed`)
- `*_from_tag` stories for non-automation projects only

**Threshold Behavior**:
- Projects with <= 50 tasks: Use incremental story-based detection
- Projects with > 50 tasks: Use batch modification check instead (more efficient)

---

## User Stories / Use Cases

### US-1: Data Analyst Generates Project Report

As a data analyst, I want to generate a typed dataframe from an Asana project so that I can create reports and visualizations without manual data transformation.

**Scenario**:
1. Analyst has Project object for "Q4 Sales Pipeline"
2. Analyst calls `project.to_dataframe(task_type="Unit")`
3. SDK fetches tasks, extracts fields per UnitSchema
4. SDK returns Polars DataFrame with typed columns
5. Analyst filters, aggregates, and exports to Excel

**Acceptance**: DataFrame has 23 typed columns (12 base + 11 Unit); ready for analysis.

### US-2: Developer Migrates from Legacy struc()

As a developer maintaining autom8, I want to migrate from struc() to to_dataframe() incrementally so that I can adopt the new SDK without breaking existing code.

**Scenario**:
1. Developer has code calling `project.struc()`
2. Developer updates to use new SDK version
3. `struc()` continues working with deprecation warning
4. Developer sees warning with migration instructions
5. Developer updates code to use `to_dataframe()`
6. Developer converts result to pandas if needed: `df.to_pandas()`

**Acceptance**: Legacy code works; deprecation visible; migration path clear.

### US-3: Service Builds Contact Directory

As a microservice developer, I want to extract Contact information into a dataframe so that I can build a contact directory feature.

**Scenario**:
1. Service has Section object for "Active Contacts"
2. Service calls `section.to_dataframe(task_type="Contact")`
3. SDK extracts 21 fields (12 base + 9 Contact)
4. Service filters by city, exports to JSON API response

**Acceptance**: Contact-specific fields (phone, email, position) correctly extracted.

### US-4: Operator Monitors Extraction Performance

As an operations engineer, I want extraction metrics emitted so that I can monitor dataframe generation performance in production.

**Scenario**:
1. Operator configures LogProvider with CloudWatch callback
2. Service calls `to_dataframe()` on large project
3. SDK emits extraction_latency, cache_hit_rate metrics
4. CloudWatch receives metrics; dashboards show performance
5. Operator sets alert for extraction_latency > 1s

**Acceptance**: Metrics emitted via LogProvider; include task count, latency, cache stats.

### US-5: Developer Uses Cached Struc Data

As a developer, I want repeated dataframe generation to be fast so that my service responds quickly to user requests.

**Scenario**:
1. First request: `to_dataframe()` takes 10s (cold cache)
2. SDK caches extracted data per task (STRUC entry type)
3. Second request: `to_dataframe()` takes 2s (warm cache)
4. Task modified in Asana
5. Third request: Modified task re-extracted; others from cache

**Acceptance**: 80%+ cache hit rate; 5x speedup on warm cache.

### US-6: Analyst Handles Mixed Task Types

As a data analyst, I want to generate a dataframe with multiple task types so that I can analyze Units and Contacts together.

**Scenario**:
1. Project contains both Unit and Contact tasks
2. Analyst calls `project.to_dataframe()` (no task_type filter)
3. SDK extracts all tasks using appropriate schemas
4. DataFrame includes union of all columns
5. Type-specific columns are null for non-matching types

**Acceptance**: Mixed dataframe has `type` column; schema-specific columns nullable.

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Polars is acceptable replacement for pandas | User decision: Polars preferred for performance |
| 32 fields (12 base + 11 Unit + 9 Contact) cover 80% of use cases | Analysis of legacy struc() usage patterns |
| Custom field GIDs are stable identifiers | Asana API guarantees GID stability |
| Big-bang struc() replacement is acceptable | User decision: interface evolution with deprecation |
| TDD-0008 caching infrastructure is available | PRD-0002 complete; TDD-0008 implemented |
| 20-30% performance improvement is achievable | Polars benchmarks vs pandas; concurrent extraction |
| Python 3.12+ is minimum version | Project constraint from PRD-0001 |
| Schema definitions can be hardcoded for MVP | Custom field GIDs known; runtime discovery post-MVP |
| Derived fields (office, vertical_id, max_pipeline_stage) can be computed | Legacy implementation exists in struc() |

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| PRD-0002 Intelligent Caching | autom8 team | Complete | STRUC entry type for struc caching |
| TDD-0008 Implementation | autom8 team | Complete | Cache infrastructure required |
| Polars library | Polars team | Available | Add to pyproject.toml |
| Legacy struc() analysis | autom8 team | Complete | Field mappings documented |
| Custom field GID mapping | autom8 team | Required | Unit and Contact field GIDs needed |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Exact custom field GIDs for Unit STRUC_COLS | autom8 team | Before implementation | Required for schema definition |
| Exact custom field GIDs for Contact STRUC_COLS | autom8 team | Before implementation | Required for schema definition |

### Resolved Questions

| Question | Owner | Resolution |
|----------|-------|------------|
| Should to_dataframe() support lazy Polars frames? | Architect | Yes, for projects > 100 tasks (see Design Decision 3) |
| Schema versioning format for cached struc | Architect | Semver string included in cached data (FR-CACHE-007, FR-MODEL-033) |
| Migration strategy for struc() | User | Big-bang with interface evolution (see ADR-0027) |
| Custom field typing approach | Requirements Analyst | Static for MVP, hybrid post-MVP (see Design Decision 2) |

### User Decisions (Previously Resolved)

The following design questions were resolved by the user prior to PRD creation:

1. **Migration Strategy**: Big-bang (replace struc() entirely with deprecation wrapper)
2. **MVP Scope**: Unit + Contact task types (32 fields total)
3. **Compatibility**: Interface Evolution (new `to_dataframe()` API; struc() deprecated but callable)
4. **Performance Target**: 20-30% improvement over current struc()
5. **Testing**: Integration tests + mocked Asana API
6. **DataFrame Library**: Polars (not pandas)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-09 | Requirements Analyst | Initial draft with 60 functional requirements, 40 NFRs |
| 2.0 | 2025-12-09 | Requirements Analyst | Restructured requirements with domain-specific prefixes (FR-MODEL, FR-PROJECT, FR-SECTION, FR-CUSTOM, FR-SUBCLASS, FR-CACHE, FR-EXPORT, FR-COMPAT, FR-ERROR, NFR-PERF, NFR-REL, NFR-COMPAT, NFR-OBS); added TaskRow class requirements (FR-MODEL-020 to FR-MODEL-025); added SectionDataFrame requirements (FR-SECTION-002 to FR-SECTION-005); added ProjectDataFrame requirements (FR-PROJECT-010 to FR-PROJECT-013); added Schema Registry requirements (FR-MODEL-030 to FR-MODEL-033); added Custom Field requirements (FR-CUSTOM-010 to FR-CUSTOM-012); added Lazy Evaluation requirements (NFR-PERF-020 to NFR-PERF-022); added Incremental Refresh requirements (FR-CACHE-020 to FR-CACHE-024); documented 4 design decisions; resolved open questions |

---

## Appendix A: MVP Field Mapping

### Base Fields (All Task Types)

| Field | Source | Type | Nullable |
|-------|--------|------|----------|
| gid | `task.gid` | str | No |
| name | `task.name` | str | No |
| type | `task.resource_subtype` or custom | str | No |
| date | Custom field or `task.due_on` | date | Yes |
| created | `task.created_at` | datetime | No |
| due_on | `task.due_on` | date | Yes |
| is_completed | `task.completed` | bool | No |
| completed_at | `task.completed_at` | datetime | Yes |
| url | `f"https://app.asana.com/0/0/{task.gid}"` | str | No |
| last_modified | `task.modified_at` | datetime | No |
| section | `task.memberships[project].section.name` | str | Yes |
| tags | `[tag.name for tag in task.tags]` | list[str] | No |

### Unit-specific Fields

| Field | Source Custom Field | Type | Nullable | Notes |
|-------|---------------------|------|----------|-------|
| mrr | `{MRR_CUSTOM_FIELD_GID}` | Decimal | Yes | Direct |
| weekly_ad_spend | `{WEEKLY_AD_SPEND_GID}` | Decimal | Yes | Direct |
| products | `{PRODUCTS_GID}` (multi-enum) | list[str] | Yes | Direct |
| languages | `{LANGUAGES_GID}` (multi-enum) | list[str] | Yes | Direct |
| discount | `{DISCOUNT_GID}` | Decimal | Yes | Direct |
| office | `{OFFICE_GID}` | str | Yes | Derived from business.office_phone lookup |
| office_phone | `{OFFICE_PHONE_GID}` | str | Yes | Derived from business |
| vertical | `{VERTICAL_GID}` (enum) | str | Yes | Direct |
| vertical_id | `{VERTICAL_ID_GID}` | str | Yes | Derived from Vertical model |
| specialty | `{SPECIALTY_GID}` | str | Yes | Direct |
| max_pipeline_stage | `{MAX_PIPELINE_STAGE_GID}` (enum) | str | Yes | Derived from UnitHolder |

### Contact-specific Fields

| Field | Source Custom Field | Type | Nullable |
|-------|---------------------|------|----------|
| full_name | `{FULL_NAME_GID}` | str | Yes |
| nickname | `{NICKNAME_GID}` | str | Yes |
| contact_phone | `{CONTACT_PHONE_GID}` | str | Yes |
| contact_email | `{CONTACT_EMAIL_GID}` | str | Yes |
| position | `{POSITION_GID}` | str | Yes |
| employee_id | `{EMPLOYEE_ID_GID}` | str | Yes |
| contact_url | `{CONTACT_URL_GID}` | str | Yes |
| time_zone | `{TIME_ZONE_GID}` | str | Yes |
| city | `{CITY_GID}` | str | Yes |

## Appendix B: Legacy struc() Method Summary

The legacy `struc()` method at `project/main.py:793-1225` (~1,000 lines):

```python
def struc(self, ...) -> pd.DataFrame:
    """Generate structured dataframe from project tasks.

    Uses ThreadManager with 10 concurrent workers.
    Caches results via S3 (EntryType.STRUC).
    Each task subclass defines STRUC_COLS.
    """
    # Key operations:
    # 1. Load tasks from section/project
    # 2. Check struc cache for each task
    # 3. Extract fields per STRUC_COLS + base fields
    # 4. Build pandas DataFrame
    # 5. Cache computed struc per task
```

### Task Subclass STRUC_COLS Examples

```python
class Unit(Task):
    STRUC_COLS = [
        "mrr",
        "weekly_ad_spend",
        "products",
        "languages",
        "discount",
    ]
    # Plus derived: office, office_phone, vertical, vertical_id, specialty, max_pipeline_stage
    # (Additional fields extracted via get_office(), get_vertical(), etc.)


class Contact(Task):
    STRUC_COLS = [
        "full_name",
        "nickname",
        "contact_phone",
        "contact_email",
        "position",
        "employee_id",
        "contact_url",
        "time_zone",
        "city",
    ]
```

## Appendix C: DataFrameSchema Draft

```python
from dataclasses import dataclass, field
from typing import Any, Callable
import polars as pl


@dataclass(frozen=True)
class ColumnDef:
    """Definition of a single DataFrame column."""
    name: str
    dtype: pl.DataType
    nullable: bool = True
    source: str | None = None  # Attribute path or custom field GID
    extractor: Callable[[Any], Any] | None = None  # Custom extraction function


@dataclass
class DataFrameSchema:
    """Schema definition for typed DataFrame generation."""
    name: str
    columns: list[ColumnDef]
    version: str = "1.0"

    def get_column(self, name: str) -> ColumnDef | None:
        """Get column definition by name."""
        return next((c for c in self.columns if c.name == name), None)

    def to_polars_schema(self) -> dict[str, pl.DataType]:
        """Convert to Polars schema dict."""
        return {col.name: col.dtype for col in self.columns}

    def to_dict(self) -> dict[str, Any]:
        """Export schema as JSON-serializable dict."""
        return {
            "name": self.name,
            "version": self.version,
            "columns": [
                {
                    "name": col.name,
                    "dtype": str(col.dtype),
                    "nullable": col.nullable,
                    "source": col.source,
                }
                for col in self.columns
            ],
        }


# Example schema instances (actual GIDs TBD)
BASE_COLUMNS = [
    ColumnDef("gid", pl.Utf8, nullable=False, source="gid"),
    ColumnDef("name", pl.Utf8, nullable=False, source="name"),
    ColumnDef("type", pl.Utf8, nullable=False, source="resource_subtype"),
    ColumnDef("date", pl.Date, nullable=True),
    ColumnDef("created", pl.Datetime, nullable=False, source="created_at"),
    ColumnDef("due_on", pl.Date, nullable=True, source="due_on"),
    ColumnDef("is_completed", pl.Boolean, nullable=False, source="completed"),
    ColumnDef("completed_at", pl.Datetime, nullable=True, source="completed_at"),
    ColumnDef("url", pl.Utf8, nullable=False),
    ColumnDef("last_modified", pl.Datetime, nullable=False, source="modified_at"),
    ColumnDef("section", pl.Utf8, nullable=True),
    ColumnDef("tags", pl.List(pl.Utf8), nullable=False),
]
```

## Appendix D: Requirement ID Mapping

This appendix documents the mapping from v1.0 flat IDs to v2.0 domain-specific IDs.

### Functional Requirements Mapping

| v1.0 ID | v2.0 ID | Domain |
|---------|---------|--------|
| FR-DF-001 | FR-MODEL-001 | Schema Definition |
| FR-DF-002 | FR-MODEL-002 | Schema Definition |
| FR-DF-003 | FR-SUBCLASS-001 | UnitSchema |
| FR-DF-004 | FR-SUBCLASS-002 | ContactSchema |
| FR-DF-005 | FR-MODEL-003 | Schema Inheritance |
| FR-DF-006 | FR-MODEL-004 | Schema Registry |
| FR-DF-007 | FR-MODEL-005 | Value Validation |
| FR-DF-008 | FR-MODEL-006 | Schema Export |
| FR-DF-009 | FR-CUSTOM-001 | Custom Field Documentation |
| FR-DF-010 | FR-MODEL-007 | Nullable Field Handling |
| FR-DF-011 | FR-MODEL-008 | Base Field Extraction |
| FR-DF-012 | FR-CUSTOM-002 | Custom Field by GID |
| FR-DF-013 | FR-CUSTOM-003 | Type Coercion |
| FR-DF-014 | FR-CUSTOM-004 | Multi-enum Handling |
| FR-DF-015 | FR-CUSTOM-005 | Missing Field Handling |
| FR-DF-016 | FR-MODEL-009 | Section Extraction |
| FR-DF-017 | FR-MODEL-010 | Tag Extraction |
| FR-DF-018 | FR-MODEL-011 | URL Construction |
| FR-DF-019 | FR-MODEL-012 | Datetime Parsing |
| FR-DF-020 | FR-SUBCLASS-003 | Type-specific Extraction |
| FR-DF-021 | FR-PROJECT-001 | Project.to_dataframe |
| FR-DF-022 | FR-SECTION-001 | Section.to_dataframe |
| FR-DF-023 | FR-PROJECT-002 | Task Type Filtering |
| FR-DF-024 | FR-EXPORT-001 | Polars Output |
| FR-DF-025 | FR-PROJECT-003 | Concurrent Processing |
| FR-DF-026 | FR-EXPORT-002 | Column Ordering |
| FR-DF-027 | FR-PROJECT-004 | Type Column for Mixed |
| FR-DF-028 | FR-PROJECT-005 | Empty List Handling |
| FR-DF-029 | FR-EXPORT-003 | Incremental Building |
| FR-DF-030 | FR-PROJECT-006 | Sync/Async Variants |
| FR-DF-031 | FR-CACHE-001 | STRUC Cache Type |
| FR-DF-032 | FR-CACHE-002 | Cache Check |
| FR-DF-033 | FR-CACHE-003 | Cache Invalidation |
| FR-DF-034 | FR-CACHE-004 | Batch Cache Retrieval |
| FR-DF-035 | FR-CACHE-005 | Overflow Threshold |
| FR-DF-036 | FR-CACHE-006 | Cache Bypass |
| FR-DF-037 | FR-CACHE-007 | Schema Version in Cache |
| FR-DF-038 | FR-CACHE-008 | Cache Failure Handling |
| FR-DF-039 | FR-CACHE-009 | Cache Warming |
| FR-DF-040 | FR-CACHE-010 | Cache Events |
| FR-DF-041 | FR-COMPAT-001 | struc() Deprecated Alias |
| FR-DF-042 | FR-COMPAT-002 | Deprecation Warning |
| FR-DF-043 | FR-COMPAT-003 | Field Name Compatibility |
| FR-DF-044 | FR-EXPORT-004 | Pandas Conversion |
| FR-DF-045 | FR-COMPAT-004 | Migration Guide |
| FR-DF-046 | FR-COMPAT-005 | 2-version Deprecation |
| FR-DF-047 | FR-COMPAT-006 | Usage Logging |
| FR-DF-048 | FR-EXPORT-005 | Legacy Column Ordering |
| FR-DF-049 | FR-COMPAT-007 | Pandas Expectation Detect |
| FR-DF-050 | FR-COMPAT-008 | struc() Signature Compat |
| FR-DF-051 | FR-ERROR-001 | DataFrameError Base |
| FR-DF-052 | FR-ERROR-002 | SchemaNotFoundError |
| FR-DF-053 | FR-ERROR-003 | ExtractionError |
| FR-DF-054 | FR-ERROR-004 | TypeCoercionError |
| FR-DF-055 | FR-ERROR-005 | Continue on Task Failure |
| FR-DF-056 | FR-ERROR-006 | Error Summary in Result |
| FR-DF-057 | FR-ERROR-007 | Schema Consistency Validation |
| FR-DF-058 | FR-ERROR-008 | API Error Handling |
| FR-DF-059 | FR-ERROR-009 | Timeout Handling |
| FR-DF-060 | FR-ERROR-010 | Partial Results on Interrupt |

### Non-Functional Requirements Mapping

| v1.0 ID | v2.0 ID | Domain |
|---------|---------|--------|
| NFR-DF-001 | NFR-PERF-001 | Performance |
| NFR-DF-002 | NFR-PERF-002 | Performance |
| NFR-DF-003 | NFR-PERF-003 | Performance |
| NFR-DF-004 | NFR-PERF-004 | Performance |
| NFR-DF-005 | NFR-PERF-005 | Performance |
| NFR-DF-006 | NFR-PERF-006 | Performance |
| NFR-DF-007 | NFR-PERF-007 | Performance |
| NFR-DF-008 | NFR-PERF-008 | Performance |
| NFR-DF-009 | NFR-PERF-009 | Performance |
| NFR-DF-010 | NFR-PERF-010 | Performance |
| NFR-DF-011 | NFR-REL-001 | Reliability |
| NFR-DF-012 | NFR-REL-002 | Reliability |
| NFR-DF-013 | NFR-REL-003 | Reliability |
| NFR-DF-014 | NFR-REL-004 | Reliability |
| NFR-DF-015 | NFR-REL-005 | Reliability |
| NFR-DF-016 | NFR-REL-006 | Reliability |
| NFR-DF-017 | NFR-REL-007 | Reliability |
| NFR-DF-018 | NFR-REL-008 | Reliability |
| NFR-DF-019 | NFR-REL-009 | Reliability |
| NFR-DF-020 | NFR-REL-010 | Reliability |
| NFR-DF-021 | NFR-COMPAT-001 | Compatibility |
| NFR-DF-022 | NFR-COMPAT-002 | Compatibility |
| NFR-DF-023 | NFR-COMPAT-003 | Compatibility |
| NFR-DF-024 | NFR-COMPAT-004 | Compatibility |
| NFR-DF-025 | NFR-COMPAT-005 | Compatibility |
| NFR-DF-026 | NFR-COMPAT-006 | Compatibility |
| NFR-DF-027 | NFR-COMPAT-007 | Compatibility |
| NFR-DF-028 | NFR-COMPAT-008 | Compatibility |
| NFR-DF-029 | NFR-COMPAT-009 | Compatibility |
| NFR-DF-030 | NFR-COMPAT-010 | Compatibility |
| NFR-DF-031 | NFR-OBS-001 | Observability |
| NFR-DF-032 | NFR-OBS-002 | Observability |
| NFR-DF-033 | NFR-OBS-003 | Observability |
| NFR-DF-034 | NFR-OBS-004 | Observability |
| NFR-DF-035 | NFR-OBS-005 | Observability |
| NFR-DF-036 | NFR-OBS-006 | Observability |
| NFR-DF-037 | NFR-OBS-007 | Observability |
| NFR-DF-038 | NFR-OBS-008 | Observability |
| NFR-DF-039 | NFR-OBS-009 | Observability |
| NFR-DF-040 | NFR-OBS-010 | Observability |

## Appendix E: Success Criteria Traceability

| Success Criterion | Requirement IDs |
|-------------------|-----------------|
| 20-30% performance improvement | NFR-PERF-001, NFR-PERF-005, NFR-PERF-007 |
| 100% MVP fields typed | FR-MODEL-001 through FR-MODEL-012, FR-SUBCLASS-001, FR-SUBCLASS-002, NFR-COMPAT-008 |
| Cache integration | FR-CACHE-001 through FR-CACHE-010, FR-CACHE-020 through FR-CACHE-024 |
| Backward compatibility | FR-COMPAT-001 through FR-COMPAT-008, NFR-COMPAT-005 |
| Error handling | FR-ERROR-001 through FR-ERROR-010 |
| Observable operations | NFR-OBS-001 through NFR-OBS-010 |
| TaskRow class | FR-MODEL-020 through FR-MODEL-025 |
| Schema registry | FR-MODEL-030 through FR-MODEL-033 |
| Lazy evaluation | NFR-PERF-020 through NFR-PERF-022 |
