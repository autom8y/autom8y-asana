---
domain: feat/resource-clients
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/clients/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# Asana Resource Clients

## Purpose and Design Rationale

The resource clients subsystem (`src/autom8_asana/clients/`) is the Infrastructure layer's primary abstraction over the Asana REST API. It translates raw HTTP exchanges into typed Python operations, shields the rest of the codebase from Asana API specifics, and enforces cross-cutting behaviors (caching, retry, rate limiting, error handling) on every outbound call.

**Core design decisions:**

- **Typed-by-default with raw=True opt-out (TRADE-001)**: All `get`, `create`, `update`, `delete` methods return Pydantic models by default. Pass `raw=True` to receive a plain `dict[str, Any]`. This dual-return contract is implemented via `@overload` annotations with `Literal[True]`/`Literal[False]` type narrowing. The pattern exists for backward-compat: legacy automation callers consume raw dicts. 115 occurrences of `raw: bool` across clients. No ADR; no planned removal.
- **Async-primary with sync twin via `@async_method`**: Every method exists in both async (`get_async`) and sync (`get`) variants. The `@async_method` decorator in `patterns/async_method.py` generates the sync wrapper at decoration time. The decorator is outermost in the stack.
- **Check-before-HTTP / store-on-miss cache pattern (ADR-0127, ADR-0119)**: Tier 1 clients validate the GID, check the `CacheProvider` via `_cache_get()`, return the hit if valid, otherwise fetch the Asana HTTP API and call `_cache_set()`. Cache failures always degrade gracefully (log + continue) per NFR-DEGRADE-001/004.
- **GID validation before network calls**: `validate_gid()` from `persistence/validation.py` is called on every `get()` / `update()` entrypoint. Raises `GidValidationError` / `ValidationError` pre-network for malformed GIDs.
- **`PageIterator[T]` for all list operations**: List endpoints return a typed `PageIterator[T]` (from `models/__init__.py`) for automatic pagination. `opt_fields` are carried universally; `parent.gid` inclusion is enforced via `_MINIMUM_OPT_FIELDS`.
- **SRP extraction via helper classes (ADR-0059)**: `TasksClient` delegates P1 convenience methods to `TaskOperations` (lazy-loaded property `.operations`) and TTL resolution to `TaskTTLResolver` (lazy-loaded property `.ttl_resolver`). `GoalsClient` similarly delegates hierarchy/follower management to `GoalRelationships` and `GoalFollowers`.
- **Per-session name resolution (ADR-0060)**: `NameResolver` provides polymorphic name-to-GID resolution with an in-memory per-`SaveSession` cache (key: `f"{type}:{scope}:{name.lower()}"`, value: GID). Achieves 5–10× API reduction per session. Supports tags, sections, projects, and users.

## Conceptual Model

### Three Tiers

**Tier 1 — Core resources with full cache integration:**
`TasksClient`, `ProjectsClient`, `SectionsClient`, `UsersClient`, `WorkspacesClient`, `CustomFieldsClient`

These six clients apply the full 6-step cache pattern: validate GID → check cache (`_cache_get`) → return hit → fetch API → store (`_cache_set`) → return model. They all import `error_handler` from `observability/`.

**Tier 2 — Auxiliary resources:**
`WebhooksClient`, `GoalsClient`, `PortfoliosClient`, `TagsClient`, `StoriesClient`, `AttachmentsClient`, `TeamsClient`

Tier 2 clients generally do not integrate the `BaseClient` cache helpers. `WebhooksClient`, `GoalsClient`, `TagsClient`, `TeamsClient` import `@error_handler`. `StoriesClient`, `PortfoliosClient`, `AttachmentsClient` do NOT import `@error_handler` — transport errors propagate raw from these three. `StoriesClient` has a bespoke incremental-fetch pattern (`load_stories_incremental()`).

**Utilities / Helpers (not `BaseClient` subclasses, except `BatchClient` and `NameResolver`):**
- `BaseClient` — template-method ABC providing `_cache_get`, `_cache_set`, `_cache_invalidate`, `_build_opt_fields`, `_log_operation`, `_parse_modified_at`
- `NameResolver` — polymorphic name→GID with per-session cache; initialized by `AsanaClient.save()` context
- `TaskOperations` — P1 convenience wrappers (add/remove tag, move section, set assignee, add/remove from project); each wraps an internal `SaveSession`
- `TaskTTLResolver` — entity-type-aware TTL: Business 3600s, Contact/Unit 900s, Offer 180s, Process 60s, generic 300s. Falls back to `DEFAULT_ENTITY_TTLS` constants from `config.py` when `CacheConfig` is unavailable.
- `GoalFollowers` — follower add/remove for goals (extracted from `GoalsClient` per ADR-0059)
- `GoalRelationships` — subgoal and supporting-work hierarchy management (extracted from `GoalsClient` per ADR-0059)
- `BatchClient` — Asana Batch API; extends `BaseClient`; chunks into groups of 10 (Asana limit) with sequential execution for rate-limit compliance; partial failure tolerant per ADR-0010
- `clients/utils/pii.py` — **NEW (since prior observation)**: public re-export of `mask_phone_number`, `mask_canonical_key`, `mask_pii_in_string` from `clients/data/_pii.py`. Per ADR-bridge-validate-extraction Decision 3 / Obligation 7 (PII Contract). Provides PII masking for consumers that must not reach into `data/` internals.

### Decorator Stack Pattern

```python
@async_method     # outermost: generates sync wrapper
@error_handler    # inner: translates transport errors to AsanaError hierarchy
async def get(self, ...) -> Model | dict[str, Any]:
```

`@async_method` must be outermost. `@error_handler` is present on Tier 1 clients and on `WebhooksClient`, `GoalsClient`, `TagsClient`, `TeamsClient`. Missing on `StoriesClient`, `PortfoliosClient`, `AttachmentsClient`.

### Cache Integration 6-Step Pattern

1. Validate GID with `validate_gid(gid, "field_name")` — raises `GidValidationError` on malformed input
2. `_cache_get(gid, EntryType.TASK)` → returns `CacheEntry | None`
3. If cache hit and `not entry.is_expired()` → return `entry.data` (raw) or `Model.model_validate(entry.data)`
4. On cache miss: `await self._http.get(f"/{resource}/{gid}", params=params)`
5. Resolve TTL (TasksClient delegates to `TaskTTLResolver.resolve(data)`)
6. `_cache_set(gid, data, EntryType.X, ttl=ttl)` → stores `CacheEntry` with version from `modified_at`

### `clients/utils/` Sub-package (NEW at 8980bcd7)

One file: `utils/pii.py`. Re-exports three PII masking functions from `clients/data/_pii` as a public surface so bridge workflows and other consumers can mask phone numbers and canonical keys without importing from the private `data/` sub-package. This sub-package did not exist in the prior observation (`c213958`).

### Inter-Feature Relationships

- **Provides to**: `services/`, `api/routes/` (via `AsanaClient` facade in `client.py`), `automation/`, `lifecycle/`, `persistence/`
- **Consumes from**: `transport/asana_http.py` (`AsanaHttpClient`), `cache/` (`CacheProvider` protocol), `models/` (Pydantic types), `protocols/` (auth, cache, log), `core/errors.py` (`CACHE_TRANSIENT_ERRORS`), `persistence/validation.py` (`validate_gid`)
- **`AsanaClient` facade** (`client.py`) aggregates all resource clients into a single SDK entry point; initializes `BatchClient` lazily

## Implementation Map

### File Inventory (20 direct files + `data/` sub-package + `utils/` sub-package)

| File | Lines | Purpose |
|------|-------|---------|
| `base.py` | 231 | `BaseClient` ABC: constructor, cache helpers, opt_fields, log_operation |
| `tasks.py` | 924 | `TasksClient`: Tier 1 CRUD + pagination + list + update + P1 delegation |
| `projects.py` | 548 | `ProjectsClient`: Tier 1 project CRUD, sections list, membership ops |
| `sections.py` | 437 | `SectionsClient`: Tier 1 section CRUD, task enumeration |
| `users.py` | 227 | `UsersClient`: Tier 1 user lookup, workspace members |
| `workspaces.py` | 129 | `WorkspacesClient`: workspace listing |
| `custom_fields.py` | 710 | `CustomFieldsClient`: Tier 1 custom field schema + enum option CRUD |
| `webhooks.py` | 369 | `WebhooksClient`: webhook registration/deletion/listing |
| `goals.py` | 481 | `GoalsClient`: goal CRUD + metric + relationships + followers delegation |
| `portfolios.py` | 580 | `PortfoliosClient`: portfolio CRUD + project membership |
| `tags.py` | 376 | `TagsClient`: tag CRUD + task enumeration |
| `stories.py` | 596 | `StoriesClient`: story list, create, incremental pagination |
| `attachments.py` | 487 | `AttachmentsClient`: multipart upload, streaming download |
| `teams.py` | 298 | `TeamsClient`: team lookup, membership |
| `task_operations.py` | 333 | `TaskOperations`: P1 convenience wrappers (add/remove tag/assignee/project, move section) |
| `task_ttl.py` | 106 | `TaskTTLResolver` + `TTLResolverProtocol`: entity-type TTL selection |
| `name_resolver.py` | 287 | `NameResolver`: polymorphic name→GID with per-session cache |
| `goal_followers.py` | 193 | `GoalFollowers`: add/remove followers from goals |
| `goal_relationships.py` | 298 | `GoalRelationships`: subgoals + supporting-work hierarchy |
| `utils/pii.py` | ~25 | **NEW**: public PII masking re-export surface |
| `__init__.py` | 40 | Public `__all__` for all 13 `*Client` classes + `BaseClient` |

Total non-init lines in direct files: ~7,650 (wc confirmed)

### Key Types and Entry Points

**`BaseClient.__init__(http, config, auth_provider, cache_provider=None, log_provider=None)`** — All resource clients call `super().__init__(...)`. `cache_provider` is optional; its absence degrades cache helpers to no-ops.

**`TasksClient.get(task_gid, *, raw=False, opt_fields=None) -> Task | dict`** — Primary Tier 1 entry point. Full 6-step cache pattern. Decorated `@async_method @error_handler`.

**`TasksClient._resolve_opt_fields(opt_fields, *, include_standard=True)`** — Merges caller-provided `opt_fields` with `_MINIMUM_OPT_FIELDS` (`frozenset{"parent.gid"}`). Ensures cascade resolution always receives the parent GID. When `opt_fields=None` and `include_standard=True` (default), returns `STANDARD_TASK_OPT_FIELDS` from `models/business/`.

**`NameResolver.resolve_tag / resolve_section / resolve_project / resolve_user`** — Polymorphic pattern: if input looks like a GID (20+ alphanum chars) return as-is; otherwise list resources, match by name, cache GID.

**`BatchClient.execute_async(requests: list[BatchRequest]) -> list[BatchResult]`** — Chunks into 10-item groups, executes sequentially, returns correlated results with per-item `success: bool` and `error`.

### Data Flow (primary path)

```
AsanaClient.tasks.get(gid)
  → TasksClient.get(gid, raw=False)
  → validate_gid(gid, "task_gid")           [persistence/validation.py]
  → _cache_get(gid, EntryType.TASK)          [BaseClient → CacheProvider.get_versioned]
  → HIT: Task.model_validate(entry.data)
  → MISS: AsanaHttpClient.get("/tasks/{gid}")  [transport/asana_http.py]
         → TaskTTLResolver.resolve(data)     [detect entity type → TTL seconds]
         → _cache_set(gid, data, EntryType.TASK, ttl)
         → Task.model_validate(data)
```

### Public API Surface (consumed by other packages)

- `AsanaClient` in `client.py` exposes `.tasks`, `.projects`, `.sections`, `.users`, `.workspaces`, `.custom_fields`, `.webhooks`, `.goals`, `.portfolios`, `.tags`, `.stories`, `.attachments`, `.teams`, `.batch` (all lazy-initialized)
- All 13 `*Client` classes exported from `clients/__init__.py`
- `clients/utils/pii.py`: `mask_phone_number`, `mask_canonical_key`, `mask_pii_in_string` (public re-export surface)
- Consuming packages: `services/` (via `AsanaClient`), `api/dependencies.py` (`ClientPool`), `cache/integration/`, `lifecycle/`, `persistence/`, `automation/workflows/`

### Test Coverage Locations

- `tests/unit/clients/test_tasks_client.py` — TasksClient core CRUD
- `tests/unit/clients/test_tasks_cache.py` — cache integration (hit/miss/degrade)
- `tests/unit/clients/test_tasks_duplicate.py` — deduplication edge cases
- `tests/unit/clients/test_tasks_dependents.py` — dependent task operations
- `tests/unit/clients/test_projects_cache.py` — ProjectsClient cache
- `tests/unit/clients/test_sections_cache.py` — SectionsClient cache
- `tests/unit/clients/test_users_cache.py` — UsersClient cache
- `tests/unit/clients/test_stories_cache.py` — StoriesClient incremental pattern
- `tests/unit/clients/test_tier1_clients.py` — cross-Tier 1 behavioral coverage
- `tests/unit/clients/test_tier2_clients.py` — cross-Tier 2 behavioral coverage
- `tests/unit/clients/test_base_cache.py` — BaseClient cache helpers
- `tests/unit/clients/test_client_warm_cache.py` — AsanaClient warm-up
- `tests/unit/clients/test_coverage_gap.py` — gap detection for missing coverage
- `tests/unit/clients/test_client.py` — AsanaClient facade
- `tests/unit/clients/conftest.py` — shared fixtures
- `tests/unit/test_tier1_adversarial.py` — adversarial Tier 1 edge cases
- `tests/unit/test_tier2_adversarial.py` — adversarial Tier 2 edge cases
- `tests/integration/test_stories_cache_integration.py` — stories cache integration
- `tests/integration/test_gid_validation_edge_cases.py` — GID validation integration

## Boundaries and Failure Modes

### Explicit Scope Boundaries

This subsystem does NOT:
- Implement business logic (that lives in `services/`)
- Own Pydantic model definitions (those live in `models/`)
- Implement transport-level retry or rate limiting (that is `transport/asana_http.py` + `transport/adaptive_semaphore.py`)
- Manage cache warmup orchestration (that is `cache/integration/` + `api/lifespan.py`)
- Access `clients/data/` internals directly — `utils/pii.py` is the only cross-package boundary, and it re-exports rather than reaching into private symbols
- Implement SaveSession lifecycle (that is `persistence/session.py`); `TaskOperations` wraps `SaveSession` but does not own it

### Known Failure Modes

**Cache degradation (NFR-DEGRADE-001/004):**
`_cache_get` and `_cache_set` catch `CACHE_TRANSIENT_ERRORS` (from `core/errors.py`), log a warning, and continue. Cache unavailability never raises; the method falls through to HTTP. This is correct behavior, but means a degraded cache silently increases Asana API call volume.

**Rate limiting:**
`RateLimitError` (from `errors.py`) propagates from `AsanaHttpClient` after the AIMD adaptive semaphore (`transport/adaptive_semaphore.py`) is exhausted. No retry in clients themselves; callers must handle or retry at the service layer.

**`@error_handler` absent on StoriesClient, PortfoliosClient, AttachmentsClient:**
These three Tier 2 clients do not import or apply `@error_handler`. Transport errors (`httpx` exceptions, HTTP 4xx/5xx) propagate as raw exceptions rather than being translated into `AsanaError` hierarchy. Callers relying on `except AsanaError` will miss exceptions from these clients. This was noted in the prior observation and remains unresolved at `8980bcd7`.

**`add_members` serialization bug (UNRESOLVED at 8980bcd7):**
`ProjectsClient.add_members()` at line 431 and 502, `PortfoliosClient.add_members()` at lines 458 and 529, and `GoalFollowers` at lines 115 and 188 serialize membership lists as `",".join(members)` (a comma-delimited string). The Asana API expects `members` as a JSON array of GID strings. This is a serialization mismatch. Status: present in prior observation, unresolved and confirmed present at `8980bcd7`.

**GID validation boundary:**
`validate_gid()` is called in `TasksClient.get`, `TasksClient.update`, `TasksClient.get_dependent_tasks_async`, and `ProjectsClient.get`, but is not applied uniformly across all Tier 2 client entry points. Malformed GIDs on Tier 2 clients propagate to the Asana HTTP API and return HTTP 404/400 rather than a local `GidValidationError`.

**TaskTTLResolver entity detection dependency:**
`TaskTTLResolver._detect_entity_type()` calls `detect_entity_type_from_dict()` from `models/business/`. This creates a client-layer dependency on the business model bootstrap sequence. Per TDD-registry-consolidation comment: "Import from package to ensure bootstrap runs." If called before `models/business/_bootstrap.bootstrap()` has executed, entity type detection returns `None` and TTL falls back to the 300s generic default (safe, not a hard failure).

**`opt_fields` + `parent.gid` contract:**
`TasksClient._resolve_opt_fields()` enforces `_MINIMUM_OPT_FIELDS = frozenset({"parent.gid"})` per TDD-sdk-cascade-resolution §3.1. This is only implemented in `TasksClient`. Other clients that return hierarchical resources do not enforce minimum field inclusion — callers may receive responses without fields needed for cascade resolution.

### Configuration Boundaries

- `AsanaConfig.cache.ttl.default_ttl` — fallback TTL used by `_cache_set` when no `ttl` argument is provided
- `AsanaConfig.cache.get_entity_ttl(entity_type)` — CacheConfig-based TTL override; takes priority over `TaskTTLResolver` detection defaults (FR-TTL-006)
- `CACHE_TRANSIENT_ERRORS` tuple in `core/errors.py` — defines which exceptions trigger graceful degradation in `_cache_get` / `_cache_set` / `_cache_invalidate`
- `BATCH_SIZE_LIMIT = 10` in `batch/client.py` — hard limit from Asana Batch API; not configurable

### Interaction Points with Other Features

- **`cache/` subsystem**: `BaseClient` calls `CacheProvider.get_versioned` / `set_versioned` / `invalidate`. The cache provider is injected at construction and optional; the full `CacheProvider` protocol is in `protocols/cache.py`. Cache invalidation for webhooks flows through `persistence/cache_invalidator.py` → `CacheProvider.invalidate`, not through clients.
- **`transport/`**: `AsanaHttpClient` wraps `autom8y_http.Autom8yHttpClient` with Asana response unwrapping. All clients share a single `AsanaHttpClient` instance injected via `_http`. Rate limiting and circuit breaking live in transport; clients are unaware of them.
- **`persistence/`**: `TaskOperations` imports `SaveSession` lazily at call time to avoid circular imports (per ADR-0059). Clients do not call `SaveSession` directly; `TaskOperations` wraps it.
- **`models/business/`**: `TaskTTLResolver` depends on `detect_entity_type_from_dict` for entity-type-aware TTL; this bridges Infrastructure ↔ Domain layers.
- **`clients/utils/pii.py` ↔ `clients/data/_pii.py`**: The `utils/pii.py` public surface was introduced to satisfy ADR-bridge-validate-extraction Decision 3 + Obligation 7 PII Contract. Bridge workflows MUST use `clients.utils.pii` for phone number masking, not `clients.data._pii` directly.

```metadata
{
  "domain": "feat/resource-clients",
  "generated_at": "2026-05-08T00:00Z",
  "source_hash": "8980bcd7",
  "confidence": 0.95,
  "key_changes_from_prior": [
    "New clients/utils/pii.py sub-package documented (ADR-bridge-validate-extraction, Obligation 7)",
    "clients/__init__.py confirmed at 13 exported client classes",
    "Line counts refreshed: tasks.py 924, projects.py 548, stories.py 596, custom_fields.py 710",
    "Confirmed @error_handler absent on StoriesClient, PortfoliosClient, AttachmentsClient (was documented as gap, now count-verified)",
    "BatchClient interface documented (previously gap)",
    "clients/utils/ sub-package documented (previously absent from scope)",
    "add_members serialization bug confirmed unresolved at 8980bcd7",
    "TaskTTLResolver bootstrap dependency and fallback behavior clarified",
    "_resolve_opt_fields parent.gid minimum-fields contract documented",
    "Source hash updated from c213958 to 8980bcd7"
  ]
}
```
