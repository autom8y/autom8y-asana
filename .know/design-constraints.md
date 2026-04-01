---
domain: design-constraints
generated_at: "2026-04-01T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "24d8e44"
confidence: 0.82
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "ccac1bdf21a076abac37f960cd0d2210bee78a023d780c7374cb6d5c087c9c5b"
---

# Codebase Design Constraints

## Tension Catalog

### TENSION-001: Legacy Cache Layer Coexists with Unified Cache

**Type**: Dual-system pattern
**Location**: `src/autom8_asana/client.py:254,692`, `src/autom8_asana/cache/integration/autom8_adapter.py`, `src/autom8_asana/cache/__init__.py:266`
**Current state**: `AsanaClient` has both `_cache_provider` (legacy) and `_unified_store` (`UnifiedTaskStore`). `MIGRATION-PLAN-legacy-cache-elimination` referenced at 4 call sites but not completed.
**Why it persists**: Big-bang cutover deferred. `autom8_adapter.py` smooths migration from S3 legacy to Redis.
**Resolution cost**: HIGH. Two cache invalidation paths operate in parallel.

### TENSION-002: Dual Preload Strategy -- Progressive vs. Legacy Fallback

**Type**: Dual-system pattern
**Location**: `src/autom8_asana/api/preload/progressive.py:329-344`, `src/autom8_asana/api/preload/legacy.py`
**Current state**: Progressive preload is active. Legacy fallback when S3 unavailable. Legacy contains "12 bare-except sites preserved as-is."
**Why it persists**: Retirement criteria: "S3 >= 99.9% for 90 days, this event unfired 90 days." Per ADR-011.
**Resolution cost**: MEDIUM. Any DataFrame warm path change must validate both branches.

### TENSION-003: CascadingFieldResolver Null Rate -- Persistent Production Risk

**Type**: Data model coupling
**Location**: `src/autom8_asana/dataframes/builders/cascade_validator.py:29-32`, `src/autom8_asana/services/universal_strategy.py:570,627,669`
**Current state**: `CASCADE_NULL_WARN_THRESHOLD = 0.05` and `CASCADE_NULL_ERROR_THRESHOLD = 0.20` calibrated against SCAR-005's 30% production incident. Two sessions recorded 30-40% null rates.
**Why it persists**: Structural coupling between Asana parent-child hierarchy and cascade field model. Validator/auditor approach is mitigation, not fix.
**Resolution cost**: HIGH. Schema redesign required.

### TENSION-004: Deprecated Query Endpoint Still Serving Traffic

**Type**: Backward compatibility
**Location**: `src/autom8_asana/api/routes/query.py:7,524-646`
**Current state**: `POST /v1/query/{entity_type}` marked deprecated, sunset 2026-06-01. Co-exists with active replacement.
**Why it persists**: Callers not yet migrated.
**Resolution cost**: LOW after 2026-06-01. Route cannot be deleted before sunset date.

### TENSION-005: `source=None` Schema Columns Require Hand-Coded Extractors

**Type**: Architecture constraint
**Location**: `src/autom8_asana/dataframes/extractors/schema.py:7-10`, `src/autom8_asana/dataframes/schemas/`
**Current state**: `SchemaExtractor` handles `cf:`, `cascade:`, `gid:` sources automatically. `source=None` columns bypass it and require dedicated extractor classes.
**Why it persists**: Some derived fields require multi-step resolution logic with no single source column.
**Resolution cost**: STRUCTURAL. The safety valve is by design.

### TENSION-006: Section GIDs Hardcoded as Unverified Placeholders

**Type**: Phantom abstraction
**Location**: `src/autom8_asana/reconciliation/section_registry.py:19-69`
**Current state**: `EXCLUDED_SECTION_GIDS` and `UNIT_SECTION_GIDS` are placeholder strings. Two TODOs acknowledge this. Name-based fallback (`EXCLUDED_SECTION_NAMES`) is the operational path.
**Why it persists**: Live API verification not yet performed.
**Resolution cost**: LOW. Verify GIDs or remove constants.

### TENSION-007: Dual Authentication Mode -- JWT vs. PAT Token Detection

**Type**: By-design complexity
**Location**: `src/autom8_asana/auth/dual_mode.py`, 15 usages in `api/routes/tasks.py`, 7 in `sections.py`
**Current state**: `detect_token_type()` uses dot-counting heuristic (JWT = 2 dots, PAT = 0). Per ADR-S2S-001.
**Why it persists**: External routes need PAT pass-through; internal routes use JWT. The API bridges both worlds.
**Resolution cost**: N/A (intentional design).

### TENSION-008: Freshness Enum Consolidation -- Type Aliases at Old Locations

**Type**: Migration in progress
**Location**: `src/autom8_asana/cache/models/freshness_unified.py:1-25`
**Current state**: Four legacy enums consolidated into two. Type aliases remain for backward compatibility per `SPIKE-cache-freshness-consolidation.md`.
**Why it persists**: Callers spread across codebase imported old names.
**Resolution cost**: MEDIUM. Import sweep across codebase.

### TENSION-009: Two Names for the Same Auth Env Var

**Type**: Deployment coupling
**Location**: `src/autom8_asana/services/gid_push.py:126`, `src/autom8_asana/api/dependencies.py:502-509`, `src/autom8_asana/clients/data/config.py:242`
**Current state**: `SERVICE_API_KEY` (new standard) with fallback to `AUTOM8Y_DATA_API_KEY` (Lambda/ECS deployed).
**Why it persists**: Changing all deployment configs simultaneously is risky.
**Resolution cost**: COORDINATED. Code + deployment must move together.

### TENSION-010: SystemContext Reset Pattern -- Module Side-Effects at Import

**Type**: Test infrastructure coupling
**Location**: `src/autom8_asana/core/system_context.py`, 12 files using `register_reset`
**Current state**: Singleton modules register reset functions via module-level side effects. `_repopulate_from_imported_modules()` works around Python module caching.
**Why it persists**: Test isolation requires `SystemContext.reset_all()` without re-importing.
**Resolution cost**: HIGH. Changing requires rethinking test singleton isolation.

### TENSION-011: Temp GID Placeholder System in Persistence Pipeline

**Type**: Architecture constraint
**Location**: `src/autom8_asana/persistence/pipeline.py:195-196`, `graph.py:228`, `action_executor.py:158`
**Current state**: `temp_xxx` placeholder GIDs for forward references resolved via `gid_map` after Asana assigns real GIDs.
**Why it persists**: Asana does not provide transactional multi-entity creation.
**Resolution cost**: STRUCTURAL. Any persistence change must preserve two-phase GID resolution.

## Abstraction Gap Mapping

### GAP-001: No Abstraction Over Dual Preload Paths
**Location**: `src/autom8_asana/api/preload/progressive.py`, `legacy.py`
**Impact**: Bug fixes to watermark handling, index recovery, or cache coordination must be applied twice. Two 600+ line functions with nearly identical inner loops.

### GAP-002: `SchemaExtractor` Cannot Handle Computed Fields
**Location**: `src/autom8_asana/dataframes/extractors/schema.py`
**Impact**: Each new entity with derived fields adds a full extractor class. No extension point for custom field logic.

### GAP-003: Reconciliation Section GIDs Are a Phantom Abstraction
**Location**: `src/autom8_asana/reconciliation/section_registry.py`
**Impact**: Future callers may trust GID constants without reading the TODOs, causing silent reconciliation failures.

### GAP-004: `FieldWriteService` Has No Retry or Idempotency on Asana Write
**Location**: `src/autom8_asana/services/field_write_service.py`
**Impact**: Partial failure between write and cache invalidation leaves cache stale. FQ write hardening (WS-4) still pending.

## Load-Bearing Code

### LB-001: `SystemContext.reset_all()` + `register_reset` Chain
**Location**: `src/autom8_asana/core/system_context.py`, 12 consuming modules
**Callers**: Every test fixture calling `SystemContext.reset_all()`. Breaking any `register_reset()` call leaves singleton state across tests.
**Hot path**: No (test-only). But failure produces non-deterministic test results.

### LB-002: CascadingFieldResolver + CascadeViewPlugin Integration
**Location**: `src/autom8_asana/dataframes/resolver/cascading.py`, `views/cascade_view.py`, `builders/cascade_validator.py`
**Callers**: 15 files, 61 usages. Load path for all `cascade:` schema columns.
**Hot path**: Yes. Runs on every DataFrame build. Changing parent chain traversal without updating cascade column set silently produces nulls (SCAR-005 failure mode).

### LB-003: Two-Router Query Mounting in `api/main.py`
**Location**: `src/autom8_asana/api/main.py:387-388`
**What a naive fix would break**: Reordering router registration can shadow routes. Deprecated route must remain ordered after active routes.

### LB-004: Temp GID Resolution in Persistence Pipeline
**Location**: `src/autom8_asana/persistence/pipeline.py`, `graph.py`, `action_executor.py`
**What a naive fix would break**: Short-circuiting graph traversal executes operations before dependencies have real GIDs, producing broken cross-entity references.

### LB-005: Broad-Catch Exception Boundaries
**Location**: 91 files contain `except Exception` (209 occurrences); concentrated in `api/preload/legacy.py` (6), `progressive.py` (8), `lifecycle/engine.py` (10)
**What a naive fix would break**: Narrowing exceptions prematurely converts silent-degradation into hard service failures. `# BROAD-CATCH: degrade` and `# BROAD-CATCH: isolation` comments are intentional markers.

## Evolution Constraints

| Area | Rating | Condition |
|------|--------|-----------|
| `api/routes/query.py` deprecated endpoint | FROZEN | Until 2026-06-01 sunset date |
| `api/preload/legacy.py` | MIGRATION | Requires 90-day S3 uptime metric |
| `MIGRATION-PLAN-legacy-cache-elimination` | COORDINATED | Multi-file, multi-service migration |
| `source=None` schema columns | SAFE | Provided hand-coded extractor is also written |
| Auth env var fallback chain | COORDINATED | Code + deployment must move together |
| Section GID constants | FROZEN | Not safe for filtering until verified against live API |
| Freshness enum old names | MIGRATION | Type aliases removable after import sweep |

## Risk Zone Mapping

### RISK-001: Reconciliation Section GID Filtering is Silent No-Op
**Location**: `src/autom8_asana/reconciliation/section_registry.py`
**Risk**: GID-based exclusion uses unverified placeholders. Code using `EXCLUDED_SECTION_GIDS` silently passes through all units.
**Cross-reference**: TENSION-006

### RISK-002: Legacy Preload Broad-Catch Silences Data Corruption
**Location**: `src/autom8_asana/api/preload/legacy.py:387-407,528-539,616-625`
**Risk**: Outer `except Exception` always sets `cache_ready = True`. Corrupted data results in service responding 200 with stale cache.
**Cross-reference**: TENSION-002, GAP-001

### RISK-003: Cascade Null Rate Above 20% Raises Unhandled in Production
**Location**: `src/autom8_asana/services/universal_strategy.py:669`
**Risk**: `CascadeNullRateError` propagates to route handler. Production has experienced 30-40% null rates. If unhandled at route boundary, produces 500 for all resolution queries.
**Cross-reference**: TENSION-003

### RISK-004: FQ Write Hardening Pending -- No Idempotency Guard
**Location**: `src/autom8_asana/services/field_write_service.py`
**Risk**: Write succeeds but `MutationEvent` dispatch fails -> cache stale indefinitely. WS-4 started but parked.
**Cross-reference**: GAP-004

### RISK-005: Optional `HierarchyAwareResolver` Falls Back Silently to N+1
**Location**: `src/autom8_asana/dataframes/resolver/cascading.py:24-27`
**Risk**: `try/except ImportError` fallback to `None`. N+1 API calls under load can exhaust rate limits. No log event when fallback is active.
**Cross-reference**: LB-002

### RISK-006: Two-Router Ordering at `POST /v1/query` -- No Code Enforcement
**Location**: `src/autom8_asana/api/main.py:387-388`
**Risk**: Router registration ordering constraint documented in comment only. Refactor could silently shadow active routes.
**Cross-reference**: LB-003, TENSION-004

## Knowledge Gaps

- **Reconciliation executor live API wiring**: `src/autom8_asana/reconciliation/executor.py:94` contains `TODO: Wire up actual Asana API call`. Section moves not yet wired.
- **`CONSULTATION` process type missing**: `src/autom8_asana/services/intake_create_service.py:47` has `TODO(truth-audit)`. Entity registry does not yet model consultation.
- **Architecture Review: Data Attachment Bridge**: Parked at requirements (session-20260318). `DataInsightProtocol` re-export carries `noqa: F401`.
- **FQ Write Hardening (WS-4)**: Started, not completed. No ADR documents the intended mechanism.
- **`CascadeNullRateError` route-level handling**: Whether API routes catch this specifically or allow 500 was not confirmed.
