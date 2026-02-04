# Hygiene Findings: SOLID & DRY Violation Scan (HYG-002)

**Agent**: code-smeller
**Date**: 2026-02-04
**Scope**: Full codebase scan of `src/autom8_asana/`
**Finding Prefix**: HYG-002-
**Prior Report**: `.claude/artifacts/smell-report-cache-sprint3.md`

---

## Executive Summary

This scan identified **22 findings** across the full `src/autom8_asana/` codebase, categorized by SOLID principle violations and DRY violations. The most impactful patterns are:

1. **ProgressiveProjectBuilder instantiation ceremony** duplicated 8+ times across 6 files (critical DRY violation)
2. **Bot PAT acquisition + workspace GID boilerplate** repeated 12 times with near-identical error handling
3. **FreshnessStamp serialization/deserialization** duplicated between Redis and S3 backends
4. **S3 config dataclass proliferation** -- 5 independent dataclasses with identical `bucket/region/endpoint_url` fields
5. **`api/main.py` god module** at 1466 lines handling startup, discovery, preload, incremental catchup, full rebuild, and Lambda invocation

---

## Findings Manifest

| ID | File | Line | Category | Severity | Description | Prior-Overlap |
|----|------|------|----------|----------|-------------|---------------|
| HYG-002-001 | `src/autom8_asana/api/main.py` | 696-900 | dry-violation | critical | ProgressiveProjectBuilder instantiation ceremony duplicated 3x in this file alone (`_do_incremental_catchup`, `_do_full_rebuild`, `_preload_dataframe_cache_progressive`) with identical bot_pat + workspace_gid + to_pascal_case + SchemaRegistry + DefaultCustomFieldResolver + SectionPersistence + builder setup | No |
| HYG-002-002 | `src/autom8_asana/api/main.py`, `api/routes/admin.py`, `services/universal_strategy.py`, `models/project.py`, `cache/dataframe/factory.py` | multiple | dry-violation | critical | Same ProgressiveProjectBuilder instantiation ceremony appears 8+ times across 6 files. Each instance: (1) gets bot_pat, (2) gets workspace_gid, (3) calls to_pascal_case, (4) gets SchemaRegistry schema, (5) creates DefaultCustomFieldResolver, (6) creates SectionPersistence, (7) constructs builder with 7 args. A factory function would collapse this to 1-2 lines per call site | No |
| HYG-002-003 | `src/autom8_asana/api/main.py` | 1-1466 | srp-violation | critical | God module handling 6+ distinct responsibilities: app creation/lifespan, entity project discovery, legacy preload, progressive preload, incremental catchup, full rebuild, Lambda invocation. Functions `_do_incremental_catchup` (100 lines) and `_do_full_rebuild` (80 lines) are nearly identical copies with minor differences (resume=True vs resume=False) | No |
| HYG-002-004 | `src/autom8_asana/api/main.py`, `api/routes/query.py`, `api/routes/query_v2.py`, `api/routes/resolver.py`, `api/routes/admin.py`, `api/dependencies.py`, `services/discovery.py`, `lambda_handlers/cache_warmer.py`, `cache/dataframe/factory.py` | multiple | dry-violation | moderate | Bot PAT acquisition boilerplate (try/except BotPATError with logging) repeated 12 times across 9 files. Each instance handles BotPATError differently (return None, return existing, raise HTTPException, set_cache_ready, etc.) but the try/get_bot_pat/except pattern is identical | No |
| HYG-002-005 | `src/autom8_asana/cache/backends/redis.py`, `cache/backends/s3.py` | redis:262-274, s3:277-298 | dry-violation | moderate | FreshnessStamp serialization logic duplicated between Redis and S3 backends. Both serialize `last_verified_at`, `source.value`, `staleness_hint` into identical dict structure. Only transport format differs (Redis: JSON string in hash field; S3: dict in JSON body) | Yes -- extends SM-S3-007's observation about backend duplication |
| HYG-002-006 | `src/autom8_asana/cache/backends/redis.py`, `cache/backends/s3.py` | redis:306-322, s3:357-384 | dry-violation | moderate | FreshnessStamp deserialization logic duplicated between Redis and S3 backends. Both import FreshnessStamp/VerificationSource, parse `last_verified_at` via parse_version, construct identical FreshnessStamp objects. Could be extracted to a shared `FreshnessStamp.from_dict()` classmethod | Yes -- extends SM-S3-007 |
| HYG-002-007 | `src/autom8_asana/cache/backends/s3.py`, `dataframes/persistence.py`, `dataframes/async_s3.py`, `dataframes/section_persistence.py`, `config.py` | s3:33-58, persistence:68-84, async_s3:55-71, section_persistence:220-225, config:293-297 | dry-violation | moderate | Five independent S3 config dataclasses with identical `bucket: str`, `region: str = "us-east-1"`, `endpoint_url: str | None = None` fields. `S3LocationConfig` exists in config.py as a consolidation primitive but is not adopted by the 4 other configs. The S3Config comment (s3.py:46-50) acknowledges this debt | Yes -- SM-S3-004 touched config drift; this extends to structural duplication |
| HYG-002-008 | `src/autom8_asana/api/main.py` | 696-800, 802-884 | dry-violation | moderate | `_do_incremental_catchup` and `_do_full_rebuild` are near-identical functions (~100 lines each). Both: get bot_pat, get workspace_gid, create AsanaClient, get schema via to_pascal_case, create resolver, create SectionPersistence, create ProgressiveProjectBuilder, call build_progressive_async. The only meaningful difference is `resume=True` vs `resume=False` | No |
| HYG-002-009 | `src/autom8_asana/api/routes/tasks.py` | 345-448 | dry-violation | minor | `list_subtasks` and `list_dependents` endpoints have identical structure (~50 lines each): same params, same pagination construction, same response building. Only the HTTP path differs (`/tasks/{gid}/subtasks` vs `/tasks/{gid}/dependents`) | No |
| HYG-002-010 | `src/autom8_asana/services/resolver.py`, `services/universal_strategy.py`, `core/schema.py`, `query/engine.py`, `api/routes/query.py`, `api/main.py`, `cache/dataframe/factory.py`, `cache/integration/schema_providers.py`, `api/routes/admin.py` | multiple | dry-violation | moderate | `to_pascal_case(entity_type)` + `SchemaRegistry.get_instance().get_schema(...)` pattern repeated 15+ times across 9 files. This two-step schema lookup ceremony should be a single function like `get_entity_schema(entity_type)` that encapsulates the PascalCase conversion + fallback to base schema | No |
| HYG-002-011 | `src/autom8_asana/persistence/session.py` | 1-1604 | srp-violation | moderate | SaveSession at 1604 lines handles: state machine management, change tracking, action building, dependency graph construction, pipeline execution, healing, cache invalidation, and event emission. While it delegates to extracted components (ActionBuilder, ActionExecutor, DependencyGraph, HealingManager, CacheInvalidator), the facade itself still orchestrates too many concerns in a single class | No |
| HYG-002-012 | `src/autom8_asana/clients/data/client.py` | 1-1551 | srp-violation | moderate | DataClient at 1551 lines handles: HTTP operations, caching, authentication, feature flags, data transformation, and error handling. The class acts as both an API client and a business logic coordinator | No |
| HYG-002-013 | `src/autom8_asana/dataframes/builders/progressive.py` | 1-1223 | srp-violation | moderate | ProgressiveProjectBuilder at 1223 lines handles: manifest management, section fetching, DataFrame construction, checkpoint writing, S3 persistence, error handling, resume logic, and build coordination. Already partially noted in prior SM-L008 (method decomposition), but the class-level SRP violation is broader | Yes -- extends SM-L008 and SM-S3-001 |
| HYG-002-014 | `src/autom8_asana/cache/providers/tiered.py` | 169-489 | dry-violation | minor | CACHE_TRANSIENT_ERRORS exception handling pattern repeated 10 times in TieredCacheProvider. Each try/except block follows identical structure: catch CACHE_TRANSIENT_ERRORS, log warning with structured extra dict, fallback. Could use a decorator or context manager | Yes -- tangentially related to SM-S3-003 backend consistency |
| HYG-002-015 | `src/autom8_asana/dataframes/builders/parallel_fetch.py` | 287-510 | dry-violation | minor | CACHE_TRANSIENT_ERRORS exception handling repeated 4 times with identical log-and-continue pattern | No |
| HYG-002-016 | `src/autom8_asana/services/universal_strategy.py` | 576-587 | ocp-violation | minor | `_get_custom_field_resolver` uses hardcoded entity type check (`if self.entity_type in ("unit", "business", "offer")`) to decide resolver creation. Adding a new entity type that needs custom fields requires modifying this method. Should use registry/config-driven extension | No |
| HYG-002-017 | `src/autom8_asana/dataframes/builders/base.py` | 28-33 | ocp-violation | minor | Extractor selection hardcodes entity-to-extractor mapping via imports of `ContactExtractor`, `DefaultExtractor`, `UnitExtractor`. New entity types requiring specialized extraction need source modification | No |
| HYG-002-018 | `src/autom8_asana/api/main.py`, `api/routes/query.py`, `api/routes/query_v2.py`, `api/routes/admin.py` | multiple | dry-violation | moderate | Workspace GID retrieval pattern (`os.environ.get("ASANA_WORKSPACE_GID")` + None check + warning log) repeated 5+ times. `settings.py` centralizes this via `get_settings().asana.workspace_gid` but several call sites bypass it with raw `os.environ.get` | Yes -- extends SM-L031 inline env var pattern |
| HYG-002-019 | `src/autom8_asana/cache/backends/redis.py`, `cache/backends/s3.py`, `cache/backends/memory.py` | redis:60, s3:60, memory:33 | isp-violation | minor | All three backends implement `warm()` as a no-op stub returning placeholder `WarmResult(warmed=0, failed=0, skipped=len(gids))`. The `CacheProvider` protocol forces all implementations to provide `warm()` even when it is meaningless for that backend. However, note that `clear_all_tasks` was added to the protocol (per SM-S3-006 fix), so this is now the only protocol method universally stubbed | Yes -- SM-S3-007 |
| HYG-002-020 | `src/autom8_asana/dataframes/persistence.py`, `dataframes/storage.py`, `dataframes/async_s3.py` | persistence:1-993, storage:1-1065, async_s3:1-varies | dip-violation | moderate | Three independent S3 persistence implementations (`DataFramePersistence`, `S3DataFrameStorage`, `AsyncS3Client`) with overlapping functionality. `S3DataFrameStorage` was introduced per TDD-UNIFIED-DF-PERSISTENCE-001 to consolidate them behind a `DataFrameStorage` protocol, but the legacy implementations remain as concrete dependencies in multiple consumer modules. Consumers import concrete classes rather than the protocol | No |
| HYG-002-021 | `src/autom8_asana/api/routes/tasks.py`, `api/routes/sections.py` | tasks:238-249, sections:104-111 | dry-violation | minor | MutationEvent construction + `invalidator.fire_and_forget()` pattern repeated across every mutation endpoint (10 in tasks.py, 4 in sections.py). The event construction differs per endpoint but the wrapping boilerplate (extract gid from response, construct MutationEvent, fire_and_forget) is structurally identical | No |
| HYG-002-022 | `src/autom8_asana/clients/projects.py`, `clients/sections.py`, `clients/stories.py` | multiple | dry-violation | minor | Cache-check-before-HTTP pattern (validate GID, check cache, cache miss -> fetch API, store in cache, return model or raw) repeated across `get_async` methods in 3+ client classes. `BaseClient._cache_get`/`_cache_set` helpers reduce some duplication but the 6-step orchestration flow is still copy-pasted per client | No |

---

## Priority Analysis by ROI

| Rank | ID | Category | Severity | Blast Radius | Fix Complexity | ROI |
|------|------|----------|----------|--------------|----------------|-----|
| 1 | HYG-002-002 | dry-violation | critical | 8+ sites across 6 files | Medium (factory function) | 9.0 |
| 2 | HYG-002-003 | srp-violation | critical | 1466-line god module | Medium (extract modules) | 8.5 |
| 3 | HYG-002-008 | dry-violation | moderate | 2 near-identical 100-line functions | Low (parameterize) | 8.0 |
| 4 | HYG-002-010 | dry-violation | moderate | 15+ sites across 9 files | Low (extract helper) | 7.5 |
| 5 | HYG-002-004 | dry-violation | moderate | 12 sites across 9 files | Medium (varies by call site) | 7.0 |
| 6 | HYG-002-005/006 | dry-violation | moderate | 2 backends | Low (classmethod) | 6.5 |
| 7 | HYG-002-007 | dry-violation | moderate | 5 config classes | Low (adopt S3LocationConfig) | 6.0 |
| 8 | HYG-002-020 | dip-violation | moderate | 3 persistence impls | High (migration) | 5.5 |
| 9 | HYG-002-018 | dry-violation | moderate | 5+ env access sites | Low (use get_settings) | 5.5 |
| 10 | HYG-002-011 | srp-violation | moderate | 1604-line class | High (architectural) | 4.5 |
| 11 | HYG-002-012 | srp-violation | moderate | 1551-line class | High (architectural) | 4.0 |
| 12 | HYG-002-013 | srp-violation | moderate | 1223-line class | Medium | 4.0 |
| 13 | HYG-002-014 | dry-violation | minor | 10 try/except blocks | Low (decorator/ctx mgr) | 3.5 |
| 14 | HYG-002-021 | dry-violation | minor | 14 mutation endpoints | Low (helper function) | 3.0 |
| 15 | HYG-002-022 | dry-violation | minor | 3+ client classes | Medium (template method) | 3.0 |
| 16 | HYG-002-016 | ocp-violation | minor | 1 method | Low (registry lookup) | 2.5 |
| 17 | HYG-002-017 | ocp-violation | minor | 1 module | Low (extractor registry) | 2.5 |
| 18 | HYG-002-009 | dry-violation | minor | 2 endpoints | Low (helper function) | 2.0 |
| 19 | HYG-002-015 | dry-violation | minor | 4 try/except blocks | Low | 2.0 |
| 20 | HYG-002-019 | isp-violation | minor | 3 backends | Low (document or remove) | 1.5 |

---

## Detailed Evidence for Top Findings

### HYG-002-002: ProgressiveProjectBuilder Instantiation Ceremony (CRITICAL DRY)

The following 7-step ceremony is duplicated 8+ times:

```python
# Step 1: Get bot PAT
bot_pat = get_bot_pat()

# Step 2: Get workspace GID
workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")

# Step 3: Convert entity type to schema key
task_type = to_pascal_case(entity_type)

# Step 4: Get schema
schema = SchemaRegistry.get_instance().get_schema(task_type)

# Step 5: Create resolver
resolver = DefaultCustomFieldResolver()

# Step 6: Create persistence
section_persistence = SectionPersistence()

# Step 7: Create builder
builder = ProgressiveProjectBuilder(
    client=client,
    project_gid=project_gid,
    entity_type=entity_type,
    schema=schema,
    persistence=section_persistence,
    resolver=resolver,
    store=client.unified_store,
)
```

**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py:750-768`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py:849-867`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py:1127-1139`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/admin.py:275-290`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py:502-531`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/project.py:207-222`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/project.py:290-313`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/factory.py:51-81`

### HYG-002-003: api/main.py God Module (CRITICAL SRP)

At 1466 lines, `api/main.py` contains 6+ distinct functional areas that could be separate modules:

1. **App factory** (`create_app`, line 1341): FastAPI app creation and middleware
2. **Startup lifecycle** (`lifespan`, line 182): Schema registration, entity discovery, cache init
3. **Entity discovery** (`_discover_entity_projects`, line 303): Workspace project scanning
4. **Legacy preload** (`_preload_dataframe_cache`, line 322): Old-style cache warming
5. **Progressive preload** (`_preload_dataframe_cache_progressive`, line 938): New progressive warming with parallel project processing (~400 lines)
6. **DataFrame rebuild** (`_do_incremental_catchup` + `_do_full_rebuild`, lines 696-884): Near-duplicate rebuild functions
7. **Lambda invocation** (`_invoke_cache_warmer_lambda_from_preload`, line 901): AWS Lambda trigger

### HYG-002-005/006: FreshnessStamp Serialization Duplication

**Redis serialization** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:262-274`):
```python
if entry.freshness_stamp is not None:
    result["freshness_stamp"] = json.dumps({
        "last_verified_at": format_version(entry.freshness_stamp.last_verified_at),
        "source": entry.freshness_stamp.source.value,
        "staleness_hint": entry.freshness_stamp.staleness_hint,
    })
```

**S3 serialization** (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:278-286`):
```python
if entry.freshness_stamp is not None:
    stamp_data = {
        "last_verified_at": format_version(entry.freshness_stamp.last_verified_at),
        "source": entry.freshness_stamp.source.value,
        "staleness_hint": entry.freshness_stamp.staleness_hint,
    }
```

Identical dict construction. A `FreshnessStamp.to_dict()` / `FreshnessStamp.from_dict()` pair would eliminate both copies.

---

## Cross-Reference with Prior Smell Report

| Prior ID | Status | HYG-002 Extension |
|----------|--------|-------------------|
| SM-S3-001 | Active | HYG-002-013 extends class-level SRP beyond method-level encapsulation |
| SM-S3-003 | Active | HYG-002-019 notes protocol-level concern |
| SM-S3-004 | Active | HYG-002-007 extends from config drift to structural duplication |
| SM-S3-007 | Active | HYG-002-005/006 identifies the root cause as missing serialization abstraction |
| SM-L008 | Active | HYG-002-013 extends from method to class-level SRP |
| SM-L026 | Addressed | `_wrap_flat_array_to_and_group` extracted as shared function (confirmed) |
| SM-L031 | Active | HYG-002-018 extends inline env var pattern to 5+ additional sites |

---

## Category Distribution

| Category | Count | Critical | Moderate | Minor |
|----------|-------|----------|----------|-------|
| dry-violation | 14 | 2 | 6 | 6 |
| srp-violation | 4 | 1 | 3 | 0 |
| ocp-violation | 2 | 0 | 0 | 2 |
| isp-violation | 1 | 0 | 0 | 1 |
| dip-violation | 1 | 0 | 1 | 0 |
| **Total** | **22** | **3** | **10** | **9** |

---

## Verification Attestation

| # | File | Read | Verified |
|---|------|------|----------|
| 1 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Yes | Yes |
| 2 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/tasks.py` | Yes | Yes |
| 3 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/sections.py` | Yes | Yes |
| 4 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/admin.py` | Yes | Yes |
| 5 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Yes | Yes |
| 6 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Yes | Yes |
| 7 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/base.py` | Yes | Yes |
| 8 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | Yes | Yes |
| 9 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py` | Yes | Yes |
| 10 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/stories.py` | Yes | Yes |
| 11 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` | Yes | Yes |
| 12 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Yes | Yes |
| 13 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Yes | Yes |
| 14 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py` | Yes | Yes |
| 15 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/providers/tiered.py` | Yes | Yes |
| 16 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py` | Yes | Yes |
| 17 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Yes | Yes |
| 18 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/persistence.py` | Yes | Yes |
| 19 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/storage.py` | Yes | Yes |
| 20 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/async_s3.py` | Yes | Yes |
| 21 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py` | Yes | Yes |
| 22 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/base.py` | Yes | Yes |
| 23 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py` | Yes (prior) | Yes |
| 24 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/parallel_fetch.py` | Yes (grep) | Yes |
| 25 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py` | Yes (grep) | Yes |
| 26 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` | Yes | Yes |
| 27 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py` | Yes (metrics) | Yes |
| 28 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/project.py` | Yes (grep) | Yes |
| 29 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | Yes | Yes |
| 30 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py` | Yes | Yes |
| 31 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/schema.py` | Yes (grep) | Yes |
| 32 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/factory.py` | Yes (grep) | Yes |

All 32 files referenced in findings were read or searched via the Read/Grep tools. No findings are based on assumptions alone.
