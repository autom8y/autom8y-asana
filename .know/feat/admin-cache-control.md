---
domain: feat/admin-cache-control
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/admin.py"
  - "./src/autom8_asana/api/routes/internal.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.92
format_version: "1.0"
---

# Feature Knowledge: Admin Cache Control API (Force-Rebuild / Incremental-Rebuild)

## Purpose

The Admin Cache Control API provides a single operational endpoint — `POST /v1/admin/cache/refresh` — that allows super-admin service accounts to manually trigger cache invalidation and rebuild for one or all entity types. It solves the operational problem of stale DataFrame caches that cannot be cleared through the normal webhook-driven invalidation path (e.g., after bulk Asana data migrations, Lambda warmer failures, or cache corruption).

### Why It Exists

The standard cache invalidation path (`webhooks/inbound` → `MutationInvalidator`) handles per-task delta events. It cannot handle fleet-wide corruption or force-rebuild scenarios. The endpoint was introduced as **TDD-cache-freshness-remediation Fix 4** during the cache freshness remediation sprint (documented in CHANGELOG.md and referenced throughout `admin.py` and `test_routes_admin.py`). The parent initiative is `verify-active-mrr-provenance`.

### Why It Is Hidden from OpenAPI

The router is created with `include_in_schema=False` (`admin.py:30`). This is an intentional security posture: the endpoint is an operational lever intended only for internal fleet use by provisioned ServiceAccounts. Exposing it in the public OpenAPI spec would advertise a destructive, side-effectful endpoint to API consumers and violate the principle of minimal surface area for privileged operations.

### Security Constraints

**Bedrock W4C-P3 / SEC-DT-10 / D-017** — A super-admin gate is required because the endpoint can purge the fleet-wide cache, creating a denial-of-service window and an invalidation-timing leak if reachable by any ServiceJWT. The constraint is documented inline at `admin.py:34-39`:

> Without this gate the endpoint is reachable by any ServiceJWT, exposing a documented MEDIUM-severity DOS + invalidation-timing leak.

The canonical permission is `admin:access`. The constant `SUPER_ADMIN_PERMISSION = "admin:access"` is defined at module level so regression tests can assert it hasn't changed (`test_routes_admin.py:527-529`).

---

## Conceptual Model

### Permission Model

Two tiers of S2S caller:

| Tier | Permission | Result |
|------|-----------|--------|
| Super-admin ServiceAccount | `admin:access` in `ServiceClaims.permissions` | 202 Accepted, background task scheduled |
| Any other S2S caller (no `admin:access`) | — | 403 `INSUFFICIENT_PRIVILEGE` |
| PAT bearer | — | 401 `SERVICE_TOKEN_REQUIRED` (rejected by `require_service_claims`) |
| Unauthenticated | — | 401 `MISSING_AUTH` (rejected by `require_service_claims`) |

The permission check at `admin.py:436-454` fires **before** any cache or registry access. The adversarial test suite (`test_routes_admin.py:459-471`) explicitly patches the collaborators to raise `AssertionError` to prove no side effects leak past a rejected call.

### Two Rebuild Modes

**Force-Full-Rebuild** (`force_full_rebuild=True`):
- Deletes the in-process memory cache entry, the S3 manifest, all S3 section parquets, the merged `dataframe.parquet`, and the `watermark.json` for each entity type.
- Does NOT perform an in-process DataFrame build (avoids OOM; the 1024 MB container limit is called out explicitly at `admin.py:88-90`).
- Optionally invokes the `CACHE_WARMER_LAMBDA_ARN` Lambda asynchronously (InvocationType=Event, fire-and-forget). If the env var is absent, logs `no_lambda_arn_configured` and the cache rebuilds on the next container restart.
- Clears `watermark.json` (per `ADR-HOTFIX-002`, `admin.py:176-179`) to prevent `ProgressiveTier` from re-hydrating stale data.

**Incremental-Rebuild** (`force_full_rebuild=False`, the default):
- Invalidates the memory cache entry.
- Runs `ProgressiveProjectBuilder.build_progressive_async(resume=True)` in-process, which resumes from existing S3 manifests (fetches only changed sections).
- Updates the memory cache and watermark on completion.
- Requires a valid bot PAT (`BotPATError` → early return with error log) and `ASANA_WORKSPACE_GID` (`get_workspace_gid()` → early return with error log).

### Asynchronous Execution Pattern

The route handler returns `202 Accepted` immediately and schedules the actual work via FastAPI `BackgroundTasks`. This is the standard fleet pattern for long-running operational triggers. The `refresh_id` (UUID4) is generated at request time and threaded through all log events for correlation.

### ServiceClaims Auth Pattern

`require_service_claims` (`internal.py:83-162`) is a FastAPI dependency shared by 11 route files (44 total usages in source). It:
1. Extracts `Authorization: Bearer <token>`.
2. Calls `detect_token_type(token)` — rejects PAT tokens with 401.
3. Calls `validate_service_token(token)` from `autom8y_auth`.
4. Returns `ServiceClaims(sub, service_name, scope, permissions)`.

`ServiceClaims.permissions` is populated from the ServiceAccount's scopes. The admin endpoint then performs a second-layer check on `permissions` for `admin:access`. This is a two-layer auth model: S2S JWT validity check (in `require_service_claims`) followed by fine-grained permission check (in the route handler).

### Entity Type Scope

Valid entity types are derived from `ENTITY_TYPES` (imported from `autom8_asana.core.entity_types`) and frozen into `VALID_ENTITY_TYPES` at module load. From the adversarial test (`test_routes_admin_edge_cases.py:218-230`), the current set is 14 types: `unit`, `business`, `offer`, `contact`, `asset_edit`, `process_sales`, `process_outreach`, `process_onboarding`, `process_implementation`, `process_month1`, `process_retention`, `process_reactivation`, `process_account_error`, `process_expansion`. Holder types (`asset_edit_holder`, `unit_holder`) are excluded — they are not directly refreshable.

---

## Implementation Map

### Primary Route File

**`src/autom8_asana/api/routes/admin.py`** — 522 LOC. Contains everything for the feature:
- `CacheRefreshRequest` (Pydantic model, `extra="forbid"`)
- `CacheRefreshResponse` (Pydantic model)
- `refresh_cache` — route handler at `POST /v1/admin/cache/refresh` (status 202)
- `_perform_cache_refresh` — background task dispatcher
- `_perform_force_rebuild` — force-full-rebuild implementation (memory purge + S3 purge + Lambda trigger)
- `_perform_incremental_rebuild` — incremental rebuild implementation (ProgressiveProjectBuilder)
- `_invoke_cache_warmer_lambda` — fire-and-forget boto3 Lambda invocation

Router created via `s2s_router(prefix="/v1/admin", tags=["admin"], include_in_schema=False)` from `api/routes/_security.py`.

### Auth Dependency

**`src/autom8_asana/api/routes/internal.py`** — 173 LOC. Defines the shared S2S auth primitives:
- `ServiceClaims` (Pydantic model) — validated claims including `permissions: list[str]`
- `require_service_claims` — FastAPI dependency (11 importing source files)
- `_extract_bearer_token` — raw header extraction

`internal.py` exports via `__all__`: `router`, `ServiceClaims`, `require_service_claims`.

### Router Registration

In `api/main.py`, `admin_router` is mounted with auth `S2S` at namespace `/v1/admin` (architecture seed, router inventory table). Mount order relative to other S2S routers is not critical for this prefix (no wildcard conflicts).

### Key Collaborator Imports (lazy, inside functions)

Force-rebuild path imports:
- `autom8_asana.cache.dataframe.factory.get_dataframe_cache`
- `autom8_asana.dataframes.section_persistence.create_section_persistence`
- `autom8_asana.services.resolver.EntityProjectRegistry`
- `boto3` (for Lambda invocation)

Incremental-rebuild path imports:
- `autom8_asana.AsanaClient`
- `autom8_asana.auth.bot_pat.get_bot_pat` / `BotPATError`
- `autom8_asana.dataframes.builders.progressive.ProgressiveProjectBuilder`
- `autom8_asana.dataframes.models.registry.get_schema`
- `autom8_asana.dataframes.resolver.DefaultCustomFieldResolver`
- `autom8_asana.dataframes.watermark.get_watermark_repo`
- `autom8_asana.services.gid_lookup.build_gid_index_data`

All imports are deferred to function scope (not module-level) to avoid import-time side effects and allow test patching.

### Data Flow: Force-Full-Rebuild

```
POST /v1/admin/cache/refresh {force_full_rebuild: true}
  → require_service_claims (S2S JWT validation)
  → refresh_cache handler
    → SUPER_ADMIN_PERMISSION check → 403 if absent
    → entity_type validation → 400 if invalid
    → get_dataframe_cache() → 503 if None
    → EntityProjectRegistry.get_instance().is_ready() → 503 if not ready
    → generate refresh_id (UUID4)
    → background_tasks.add_task(_perform_cache_refresh, ..., force_full_rebuild=True)
    → 202 CacheRefreshResponse (immediate)
  → [background] _perform_force_rebuild(entity_types, refresh_id)
    → for each entity_type:
        → registry.get_project_gid(entity_type)
        → dataframe_cache.invalidate(project_gid, entity_type)  [memory]
        → async with persistence:
            persistence.delete_manifest_async(project_gid)
            persistence.delete_section_files_async(project_gid)
            persistence.storage.delete_dataframe(project_gid)  [merged + watermark]
    → if CACHE_WARMER_LAMBDA_ARN env var set:
        → boto3 client.invoke(InvocationType="Event", ...)  [fire-and-forget]
    → else: log "cache will rebuild on next restart"
```

### Data Flow: Incremental-Rebuild

```
POST /v1/admin/cache/refresh {force_full_rebuild: false}
  → [same auth and validation as above]
  → [background] _perform_incremental_rebuild(entity_types, refresh_id)
    → get_bot_pat() → early return on BotPATError
    → get_workspace_gid() → early return if absent
    → for each entity_type:
        → registry.get_project_gid(entity_type)
        → dataframe_cache.invalidate(project_gid, entity_type)  [memory]
        → async with AsanaClient(...) as client:
            → ProgressiveProjectBuilder.build_progressive_async(resume=True)
            → build_result.dataframe + build_result.watermark
        → dataframe_cache.put_async(project_gid, entity_type, df, watermark)
        → watermark_repo.set_watermark(project_gid, watermark)
```

### Test Coverage

- **`tests/unit/api/test_routes_admin.py`** — 543 lines. Covers: auth rejection (missing/PAT), super-admin gate (both pass + reject paths), entity type validation, 202 happy path (single + all types), 503 for cache not initialized / registry not ready, Pydantic model defaults, static source inspection guard (regression prevention for W4C-P3).
- **`tests/unit/api/test_routes_admin_edge_cases.py`** — 243 lines. Covers: adversarial inputs (SQL injection, path traversal, extremely long strings, null bytes, extra fields → 422, invalid JSON → 422), concurrency (5 rapid requests get unique refresh_ids), `VALID_ENTITY_TYPES` membership assertions.

---

## Boundaries

### IN Scope

- Fleet-wide operational cache control (force-full-rebuild and incremental-rebuild)
- Super-admin permission enforcement (Bedrock W4C-P3 / SEC-DT-10 / D-017)
- Lambda cache warmer invocation (fire-and-forget, conditional on `CACHE_WARMER_LAMBDA_ARN`)
- Per-entity-type scoping (single entity or all ENTITY_TYPES)

### OUT of Scope

- **Data mutation**: The endpoint does not modify any Asana tasks or entities. It only purges and/or rebuilds cache data derived from Asana.
- **Regular user surface**: PAT-authenticated callers cannot reach this endpoint. It is S2S-only.
- **Public API surface**: `include_in_schema=False` means it does not appear in OpenAPI docs or SDK generation.
- **Cache warmer scheduling**: Lambda schedule is managed by IaC (`ADR-004-iac-engine-cache-warmer-schedule.md`), not this endpoint.
- **Idempotency**: The endpoint is explicitly non-idempotent (`x-fleet-idempotency: {idempotent: false, key_source: null}` in route decorator).

### Failure Modes

| Condition | Behavior |
|-----------|----------|
| Missing `Authorization` header | 401 `MISSING_AUTH` (from `require_service_claims`) |
| PAT token (non-JWT) | 401 `SERVICE_TOKEN_REQUIRED` |
| Invalid / expired JWT | 401 with `error_code` from `autom8y_auth` exception |
| `autom8y_auth` not installed | 503 `S2S_NOT_CONFIGURED` |
| Valid JWT but no `admin:access` permission | 403 `INSUFFICIENT_PRIVILEGE` |
| Invalid `entity_type` value | 400 `INVALID_ENTITY_TYPE` |
| Extra unknown fields in request body | 422 Unprocessable Entity (Pydantic `extra="forbid"`) |
| `DataFrameCache` not initialized | 503 `CACHE_NOT_INITIALIZED` |
| `EntityProjectRegistry` not ready | 503 `REGISTRY_NOT_READY` |
| No project GID for entity type (background) | Warning logged, entity skipped; no HTTP error (already 202) |
| Memory cache invalidation error (background) | Warning logged, degraded continue (BROAD-CATCH) |
| S3 purge failure (background) | Warning logged, degraded continue (BROAD-CATCH) |
| Lambda invocation failure (background) | Error logged, no retry; cache rebuilds on restart |
| `BotPATError` in incremental mode (background) | Error logged, early return for that entity |
| Missing `ASANA_WORKSPACE_GID` in incremental mode (background) | Error logged, early return |
| Per-entity unhandled exception (background) | Error logged with `error_type`, entity skipped, others proceed (BROAD-CATCH isolation) |

### Critical Invariant: Gate-Before-Side-Effects

The super-admin permission check MUST fire before any call to `get_dataframe_cache()` or `EntityProjectRegistry.get_instance()`. This ordering is enforced in the route handler (`admin.py:436` check precedes `admin.py:466` cache lookup) and regression-tested by `TestAdminRefreshSuperAdminGate.test_admin_cache_refresh_non_super_admin_rejected` which patches both collaborators to raise `AssertionError` on access.

### Interaction Points / Boundaries with Other Features

| Feature | Relationship |
|---------|-------------|
| `cache-subsystem` | Force-rebuild purges memory + S3 tiers; incremental-rebuild uses `ProgressiveProjectBuilder` |
| `lambda-handlers` (`cache_warmer`) | Force-rebuild optionally triggers via `_invoke_cache_warmer_lambda`; Lambda owns the actual rebuild |
| `authentication` (`require_service_claims`) | Load-bearing dep; 11 other route files also depend on it — changes to `ServiceClaims.permissions` field propagate here |
| `entity-registry` | `VALID_ENTITY_TYPES` derived from `ENTITY_TYPES` constant at module load time |
| `dataframe-layer` | `ProgressiveProjectBuilder`, `section_persistence`, `watermark_repo` all called in incremental path |

### Configuration Boundaries

| Env Var | Required | Effect if Absent |
|---------|----------|-----------------|
| `CACHE_WARMER_LAMBDA_ARN` | No | Force-rebuild completes purge but does not trigger Lambda; logs `no_lambda_arn_configured`; cache rebuilds on next container restart |
| `ASANA_BOT_PAT` (via `get_bot_pat()`) | Incremental only | Incremental-rebuild fails early with `BotPATError`; force-rebuild unaffected |
| `ASANA_WORKSPACE_GID` (via `get_workspace_gid()`) | Incremental only | Incremental-rebuild fails early; force-rebuild unaffected |

---

```metadata
source_files_read:
  - src/autom8_asana/api/routes/admin.py  # 522 LOC, primary implementation
  - src/autom8_asana/api/routes/internal.py  # 173 LOC, ServiceClaims + require_service_claims
  - src/autom8_asana/api/routes/_security.py  # s2s_router factory
  - tests/unit/api/test_routes_admin.py  # 543 LOC, primary tests
  - tests/unit/api/test_routes_admin_edge_cases.py  # 243 LOC, adversarial tests
  - .know/architecture.md  # architecture seed (pre-loaded)
  - .know/telos/cache-freshness-procession-2026-04-27.md  # initiative context
  - .ledge/specs/cache-freshness-architecture.tdd.md  # partial; Fix 4 not in this doc
  - CHANGELOG.md  # W4C-P3 / SEC-DT-10 mention confirmed
decision_records_found:
  - TDD-cache-freshness-remediation (referenced in admin.py/tests but not found as standalone file; likely in worktree history or .ledge/specs under different name)
  - ADR-HOTFIX-002 (referenced in admin.py:177; delete merged dataframe + watermark)
  - ADR-004-iac-engine-cache-warmer-schedule (IaC scheduling, out of scope)
confidence_basis:
  - Route implementation read directly: complete
  - Auth dependency read directly: complete
  - Test coverage read directly: complete
  - Security constraint inline comments: confirmed
  - Lambda invocation code: complete
  - TDD source doc not found as standalone file (confidence docked from 0.95 to 0.92)
```
