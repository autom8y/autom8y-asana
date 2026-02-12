# Smell Report -- Phase 1 (WS-1, WS-2, WS-3)

**Session**: session-20260210-230114-3c7097ab
**Initiative**: Deep Code Hygiene -- autom8_asana
**Phase**: 1 -- Duplication and Complexity
**Date**: 2026-02-10
**Agent**: code-smeller

---

## Pre-Analysis Corrections

Before presenting findings, the following Prompt 0 claims require correction:

| Claim | Actual Finding |
|---|---|
| WS-1: 44+ sync/async method pairs | **CORRECTED**: ~38 sync/async pairs across 12 Asana client modules. DataServiceClient has 2 manual pairs (not using shared infrastructure). See SM-001 for detail. |
| WS-1: ~600 lines recoverable | **CORRECTED**: ~1,800+ lines of sync boilerplate (overloads + `_sync` wrapper + delegation). The 600-line estimate was far too conservative. |
| WS-2: `cache/providers/s3.py` (990 lines) and `cache/providers/redis.py` (894 lines) | **CORRECTED**: Files are at `cache/backends/s3.py` (990 lines) and `cache/backends/redis.py` (894 lines). The `providers/` directory contains `tiered.py` (563 lines) and `unified.py` (909 lines) which are composition layers, not backend implementations. |
| WS-2: ~60% overlap between S3 and Redis | **VALIDATED**: Confirmed. 10 of 13 protocol methods share identical structure (degraded check, get client/conn, serialize, metrics, error handling). True backend-specific logic is confined to ~200 lines per provider. |
| WS-3: decorator.py is 226 lines with 8-level nesting | **CORRECTED**: File is 251 lines. The `cached_resolve` inner function runs lines 75-246 (172 lines of logic). Nesting depth peaks at 5 levels (decorator > inner > if-acquired > try > if-isinstance), not 8. |

---

## Summary Table (All Findings Ranked by ROI)

| ID | Category | Severity | ROI | Title | Lines Affected |
|---|---|---|---|---|---|
| SM-001 | DRY Violation | HIGH | 9.0 | Sync wrapper boilerplate explosion across Asana clients | ~1,800 lines across 12 files |
| SM-002 | DRY Violation | HIGH | 8.5 | Redis/S3 backend structural duplication | ~600 lines across 2 files |
| SM-003 | DRY Violation | MEDIUM | 7.5 | DataServiceClient manual sync/async pair (not using shared infra) | ~120 lines in 1 file |
| SM-004 | Complexity | MEDIUM | 7.0 | DataServiceClient retry loop duplication (insights vs export) | ~200 lines in 1 file |
| SM-005 | Complexity | MEDIUM | 6.5 | `cached_resolve` inner function -- monolithic build-or-wait logic | 172 lines in 1 file |
| SM-006 | DRY Violation | MEDIUM | 6.0 | Overload declaration repetition pattern across clients | ~2,400 lines across 12 files |
| SM-007 | DRY Violation | LOW | 5.5 | Serialize/deserialize freshness stamp duplication across backends | ~50 lines across 2 files |
| SM-008 | DRY Violation | LOW | 5.0 | Degraded mode / reconnect boilerplate duplication in backends | ~80 lines across 2 files |
| SM-009 | Naming | LOW | 3.5 | Inconsistent sync wrapper mechanism across client modules | 3 mechanisms across 12 files |

---

## WS-1: Sync/Async Client Duplication

### SM-001: Sync wrapper boilerplate explosion across Asana clients (HIGH)

**Category**: DRY Violation
**Severity**: HIGH | **Frequency**: Every CRUD method in every Asana client | **Blast Radius**: 12 files, ~1,800 lines
**Fix Complexity**: Medium (systematic conversion to `@async_method` descriptor)
**ROI Score**: 9.0/10

**Problem**: Each Asana resource client (tasks, projects, sections, goals, webhooks, users, custom_fields, tags, stories, portfolios, attachments, teams, workspaces) implements sync/async pairs using a 3-part boilerplate pattern for every method:

1. `get_async()` -- the real async implementation
2. `get()` -- a sync facade that delegates to `_get_sync()`
3. `_get_sync()` -- an `@sync_wrapper` decorated async function that calls `get_async()`

For methods with `raw` parameter, this additionally requires 4 `@overload` declarations (2 async + 2 sync).

**Evidence**: A single `get` method with `raw` parameter requires ~80 lines of boilerplate (tasks.py pattern):

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py:109-301`
```
Lines 109-130:  2 async overloads for get_async
Lines 131-197:  get_async implementation (the real logic)
Lines 248-269:  2 sync overloads for get
Lines 270-287:  get() sync facade
Lines 289-301:  _get_sync() wrapper that calls get_async
```

This pattern repeats for get/create/update/delete/duplicate across tasks.py alone (1120 lines total, of which ~600 are sync boilerplate and overloads).

**Affected Files (with sync pair counts)**:

| File | Lines | Sync Pairs | Approx Boilerplate Lines |
|---|---|---|---|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` | 1120 | 5 (get, create, update, delete, duplicate) + 6 P1 delegates | ~600 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py` | 758 | 6 (get, create, update, delete, add_members, remove_members) | ~400 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/custom_fields.py` | 1064 | 8 (get, create, update, delete, enum_option CRUD, project settings) | ~550 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/goals.py` | 654 | 4 (get, create, update, delete) | ~350 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/webhooks.py` | 479 | 4 (get, create, update, delete) | ~250 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py` | 288 | 3 (get, me, list_for_workspace) | ~150 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/stories.py` | 761 | est. 4-5 | ~400 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/portfolios.py` | 905 | est. 5-6 | ~500 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tags.py` | 531 | est. 3-4 | ~250 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/attachments.py` | 672 | est. 3-4 | ~300 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/teams.py` | 378 | est. 3 | ~200 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/workspaces.py` | 159 | est. 1-2 | ~80 |

**Existing Solution**: The `@async_method` descriptor at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/patterns/async_method.py` already solves this problem. `SectionsClient` (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py`) demonstrates the correct pattern -- it uses `@async_method` and eliminates the 3-part boilerplate entirely:

```python
# sections.py (correct pattern) -- ~15 lines per CRUD method
@async_method
@error_handler
async def get(self, section_gid: str, *, raw: bool = False, ...) -> Section | dict[str, Any]:
    # One implementation, two methods generated automatically
```

vs.

```python
# tasks.py (boilerplate pattern) -- ~80 lines per CRUD method
async def get_async(...):     # implementation
def get(...):                  # sync facade
    return self._get_sync(...)
@sync_wrapper("get_async")
async def _get_sync(...):     # wrapper that calls get_async
```

**Note for Architect Enforcer**: The `@async_method` pattern is already proven in sections.py. The remaining 11 clients using the `@sync_wrapper` 3-part pattern can be systematically converted. The overload declarations must be preserved for IDE/mypy support but the _sync wrapper methods and sync facade methods are entirely eliminable.

---

### SM-003: DataServiceClient manual sync/async pair (not using shared infra) (MEDIUM)

**Category**: DRY Violation
**Severity**: MEDIUM | **Frequency**: 2 method pairs | **Blast Radius**: 1 file, ~120 lines
**Fix Complexity**: Low
**ROI Score**: 7.5/10

**Problem**: `DataServiceClient.get_insights()` (the sync variant) manually reimplements the event-loop detection and `asyncio.run()` wrapping that `sync_wrapper` and `@async_method` already provide.

**Evidence**:

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py:854-942`
```python
def get_insights(self, factory: str, ...):
    # Manual event loop check (lines 912-924)
    running_loop = None
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        pass
    if running_loop is not None:
        raise SyncInAsyncContextError(...)
    # Manual asyncio.run (lines 927-942)
    return asyncio.run(self.get_insights_async(...))
```

This same loop-check + asyncio.run pattern is what `sync_wrapper` (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/sync.py:15-69`) and `@async_method` (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/patterns/async_method.py:114-137`) encapsulate. The `__exit__` method at lines 274-304 has the same manual duplication.

**Additional Locations**:
- `__exit__` sync context manager: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py:274-304`
- `get_insights` sync: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py:854-942`

**Note**: DataServiceClient is in a different module hierarchy (clients/data/) with different base class (no BaseClient). This is intentional -- it wraps httpx, not AsanaHttpClient. The fix should use `sync_wrapper` or `@async_method` while preserving this architectural boundary.

---

### SM-004: DataServiceClient retry loop duplication (insights vs export) (MEDIUM)

**Category**: DRY Violation / Complexity
**Severity**: MEDIUM | **Frequency**: 2 occurrences | **Blast Radius**: 1 file, ~200 lines
**Fix Complexity**: Medium (requires abstracting retry+circuit-breaker coordination)
**ROI Score**: 7.0/10

**Problem**: The retry-with-circuit-breaker loop is implemented twice in DataServiceClient with near-identical structure:

1. `_execute_insights_request()`: lines 1254-1398 (~145 lines of retry logic)
2. `get_export_csv_async()`: lines 1732-1774 (~43 lines, same pattern but less error handling)

Both follow the same structure:
- Check circuit breaker
- while-True retry loop
- Handle retryable status codes with backoff
- Handle TimeoutException with retry
- Handle HTTPError without retry
- Record circuit breaker success/failure

**Evidence**:

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py:1258-1294` (insights retry):
```python
while True:
    try:
        response = await client.post(path, json=request_body, ...)
        status = response.status_code
        if status in self._config.retry.retryable_status_codes:
            if self._retry_handler.should_retry(status, attempt):
                ...
                await self._retry_handler.wait(attempt, retry_after)
                attempt += 1
                continue
        break
    except httpx.TimeoutException as e:
        if attempt < self._config.retry.max_retries:
            await self._retry_handler.wait(attempt, None)
            attempt += 1
            continue
        ...
```

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py:1732-1774` (export retry):
```python
while True:
    try:
        response = await client.get(path, params=params, ...)
        status = response.status_code
        if status in self._config.retry.retryable_status_codes:
            if self._retry_handler.should_retry(status, attempt):
                ...
                await self._retry_handler.wait(attempt, retry_after)
                attempt += 1
                continue
        break
    except httpx.TimeoutException as e:
        if attempt < self._config.retry.max_retries:
            await self._retry_handler.wait(attempt, None)
            attempt += 1
            continue
        ...
```

The structural skeleton is identical; only the HTTP method (POST vs GET), request parameters, and post-retry error handling differ.

---

### SM-006: Overload declaration repetition pattern across clients (MEDIUM)

**Category**: DRY Violation (Structural)
**Severity**: MEDIUM | **Frequency**: Every CRUD method with `raw` parameter | **Blast Radius**: 12 files, ~2,400 lines
**Fix Complexity**: High (requires type system tooling or codegen approach)
**ROI Score**: 6.0/10

**Problem**: Every client method that supports `raw: bool` requires 4 `@overload` declarations (async False, async True, sync False, sync True) that are structurally identical across all resource clients. Only the resource name, GID parameter name, and return Model type change.

**Evidence**: Compare the overload pattern in 3 different clients:

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py:109-130` (tasks get):
```python
@overload
async def get_async(self, task_gid: str, *, raw: Literal[False] = ..., opt_fields: list[str] | None = ...) -> Task: ...
@overload
async def get_async(self, task_gid: str, *, raw: Literal[True], opt_fields: list[str] | None = ...) -> dict[str, Any]: ...
```

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/webhooks.py:34-55` (webhooks get):
```python
@overload
async def get_async(self, webhook_gid: str, *, raw: Literal[False] = ..., opt_fields: list[str] | None = ...) -> Webhook: ...
@overload
async def get_async(self, webhook_gid: str, *, raw: Literal[True], opt_fields: list[str] | None = ...) -> dict[str, Any]: ...
```

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py:30-50` (users get):
```python
@overload
async def get_async(self, user_gid: str, *, raw: Literal[False] = ..., opt_fields: list[str] | None = ...) -> User: ...
@overload
async def get_async(self, user_gid: str, *, raw: Literal[True], opt_fields: list[str] | None = ...) -> dict[str, Any]: ...
```

The only tokens that change are the GID parameter name and the return Model type. This is ~40 lines per CRUD method across all clients, totaling approximately 2,400 lines.

**Note for Architect Enforcer**: This is a mypy/typing constraint. Overloads cannot be generated by a descriptor at runtime -- they are static analysis artifacts. Solutions include: (a) accept the repetition as a cost of type safety, (b) code generation via a script, (c) a Protocol-based generic base that defines the overloads once. Option (a) may be the pragmatic choice. This finding is informational -- fixing SM-001 alone recovers the runtime boilerplate, which is more impactful.

---

### SM-009: Inconsistent sync wrapper mechanism across client modules (LOW)

**Category**: Naming / Consistency
**Severity**: LOW | **Frequency**: 3 distinct patterns | **Blast Radius**: 12+ files
**Fix Complexity**: Low (standardize during SM-001 remediation)
**ROI Score**: 3.5/10

**Problem**: Three different sync wrapper mechanisms coexist in the clients directory:

1. **`@sync_wrapper("method_async")`** -- `transport/sync.py:15-69` -- Used by tasks, projects, goals, webhooks, users, custom_fields, portfolios, stories, tags, attachments, teams, workspaces
2. **`@async_method`** -- `patterns/async_method.py:183-228` -- Used by sections only
3. **Manual asyncio.run()** -- DataServiceClient (data/client.py)

**Evidence**:

- Pattern 1 location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/sync.py`
- Pattern 2 location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/patterns/async_method.py`
- Pattern 3 location: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py:912-942`

All three implement the same behavior (check for running event loop, raise SyncInAsyncContextError, call asyncio.run). Having three mechanisms makes it unclear which to use for new code.

---

## WS-2: Cache Backend Duplication

### SM-002: Redis/S3 backend structural duplication (HIGH)

**Category**: DRY Violation
**Severity**: HIGH | **Frequency**: 10 of 13 protocol methods | **Blast Radius**: 2 files, ~600 shared-structure lines
**Fix Complexity**: Medium (template method or strategy extraction)
**ROI Score**: 8.5/10

**Problem**: `S3CacheProvider` (990 lines) and `RedisCacheProvider` (894 lines) implement the `CacheProvider` protocol with near-identical structural patterns. The per-method overhead of degraded-mode checking, metrics recording, error handling, and serialization scaffolding dwarfs the actual backend-specific logic.

**Method-by-Method Overlap Analysis**:

| Method | S3 Lines | Redis Lines | Structural Match | Backend-Specific Logic |
|---|---|---|---|---|
| `get()` | 413-455 | 364-398 | ~85% | S3: get_object + decompress; Redis: conn.get + decode |
| `set()` | 457-498 | 400-427 | ~80% | S3: put_object + compress; Redis: conn.setex/set |
| `delete()` | 500-521 | 429-447 | ~90% | S3: delete_object; Redis: conn.delete |
| `get_versioned()` | 525-595 | 451-518 | ~80% | S3: get_object + metadata; Redis: hgetall |
| `set_versioned()` | 597-642 | 520-566 | ~80% | S3: put_object + metadata; Redis: pipeline hset+expire |
| `get_batch()` | 644-673 | 568-618 | ~70% | S3: loop of get_versioned; Redis: pipeline hgetall |
| `set_batch()` | 675-696 | 620-660 | ~70% | S3: loop of set_versioned; Redis: pipeline hset |
| `warm()` | 698-721 | 662-685 | ~95% | Both return placeholder |
| `check_freshness()` | 723-765 | 687-721 | ~85% | S3: head_object; Redis: hget meta |
| `invalidate()` | 767-809 | 723-761 | ~75% | S3: delete per type; Redis: pipeline delete + hdel |
| `is_healthy()` | 811-834 | 763-789 | ~80% | S3: head_bucket; Redis: ping |
| `clear_all_tasks()` | 921-990 | 839-894 | ~60% | S3: paginate+delete_objects; Redis: scan+pipeline |

**Shared Structure Pattern** (present in every method):

```python
def method(self, key: str, ...) -> ...:
    start = time.perf_counter()          # [shared] timing
    try:
        if self._degraded:               # [shared] degraded check
            self._metrics.record_miss(...)  # [shared] metrics
            return None
        client = self._get_client()      # [shared] client acquisition
        # ... BACKEND-SPECIFIC: 3-8 lines ...
        latency = (...)                  # [shared] latency calc
        self._metrics.record_hit(...)    # [shared] metrics
        return entry
    except TRANSPORT_ERRORS as e:        # [shared] error handling
        self._metrics.record_error(...)  # [shared] metrics
        self._handle_error(...)          # [shared] degraded mode entry
        return None
```

**Evidence** -- Comparing `get_versioned()`:

S3 at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:525-595`:
```python
def get_versioned(self, key, entry_type, freshness=None):
    if freshness is None:
        freshness = Freshness.EVENTUAL
    start = time.perf_counter()
    entry_type_str = entry_type.value
    try:
        if self._degraded:
            self._metrics.record_miss(0.0, key=key, entry_type=entry_type_str)
            return None
        client = self._get_client()
        s3_key = self._make_key(key, entry_type)
        response = client.get_object(Bucket=self._config.bucket, Key=s3_key)
        body = response["Body"].read()
        metadata = response.get("Metadata", {})
        latency = (time.perf_counter() - start) * 1000
        entry = self._deserialize_entry(body, metadata, key)
        if entry is None:
            self._metrics.record_miss(latency, ...)
            return None
        if entry.is_expired():
            ...  # delete expired
            return None
        self._metrics.record_hit(latency, ...)
        return entry
    except S3_TRANSPORT_ERRORS as e:
        ...
```

Redis at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:451-518`:
```python
def get_versioned(self, key, entry_type, freshness=None):
    if freshness is None:
        freshness = Freshness.EVENTUAL
    start = time.perf_counter()
    entry_type_str = entry_type.value
    try:
        if self._degraded:
            self._metrics.record_miss(0.0, key=key, entry_type=entry_type_str)
            return None
        conn = self._get_connection()
        try:
            redis_key = self._make_key(key, entry_type)
            data = conn.hgetall(redis_key)
            latency = (time.perf_counter() - start) * 1000
            if not data:
                self._metrics.record_miss(latency, ...)
                return None
            entry = self._deserialize_entry(data, key)
            if entry is None:
                self._metrics.record_miss(latency, ...)
                return None
            if entry.is_expired():
                conn.delete(redis_key)
                ...
                return None
            self._metrics.record_hit(latency, ...)
            return entry
        finally:
            conn.close()
    except REDIS_TRANSPORT_ERRORS as e:
        ...
```

The structure is line-for-line parallel. Redis adds a `try/finally conn.close()` wrapper and uses `hgetall` instead of `get_object`, but the flow is identical.

**Cross-Reference**: SM-007 and SM-008 are sub-patterns within this broader finding.

**Note for Architect Enforcer**: DegradedModeMixin (`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/errors.py:113`) already exists as a shared mixin. A template method base class could extract the shared scaffolding (degraded check, timing, metrics, error handling) while delegating backend-specific operations to abstract methods. The `TieredCacheProvider` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/providers/tiered.py` already demonstrates the composition approach for the coordination layer.

---

### SM-007: Serialize/deserialize freshness stamp duplication across backends (LOW)

**Category**: DRY Violation (sub-pattern of SM-002)
**Severity**: LOW | **Frequency**: 2 occurrences | **Blast Radius**: 2 files, ~50 lines
**Fix Complexity**: Low
**ROI Score**: 5.5/10

**Problem**: Freshness stamp serialization/deserialization is copy-pasted between S3 and Redis backends.

**Evidence**:

S3 serialization at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:298-307`:
```python
stamp_data = None
if entry.freshness_stamp is not None:
    stamp_data = {
        "last_verified_at": format_version(entry.freshness_stamp.last_verified_at),
        "source": entry.freshness_stamp.source.value,
        "staleness_hint": entry.freshness_stamp.staleness_hint,
    }
```

Redis serialization at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:283-294`:
```python
if entry.freshness_stamp is not None:
    result["freshness_stamp"] = json.dumps({
        "last_verified_at": format_version(entry.freshness_stamp.last_verified_at),
        "source": entry.freshness_stamp.source.value,
        "staleness_hint": entry.freshness_stamp.staleness_hint,
    })
```

Deserialization is also duplicated:
- S3: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:379-391`
- Redis: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:329-342`

Both import the same types (`FreshnessStamp`, `VerificationSource`) and construct the same objects.

---

### SM-008: Degraded mode / reconnect boilerplate duplication in backends (LOW)

**Category**: DRY Violation (sub-pattern of SM-002)
**Severity**: LOW | **Frequency**: 2 occurrences | **Blast Radius**: 2 files, ~80 lines
**Fix Complexity**: Low
**ROI Score**: 5.0/10

**Problem**: Both backends have nearly identical `__init__` / `_attempt_reconnect` / `_get_client` patterns despite both inheriting `DegradedModeMixin`.

**Evidence**:

S3 `__init__` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py:100-185`:
```python
self._metrics = CacheMetrics()
self._client: Any = None
self._client_lock = Lock()
self._degraded = False
self._last_reconnect_attempt = 0.0
self._reconnect_interval = float(self._settings.reconnect_interval)
# ... import optional dependency, initialize client
```

Redis `__init__` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py:95-158`:
```python
self._metrics = CacheMetrics()
self._pool: Any = None
self._pool_lock = Lock()
self._degraded = False
self._last_reconnect_attempt = 0.0
self._reconnect_interval = float(self._settings.reconnect_interval)
# ... import optional dependency, initialize pool
```

The initialization pattern (metrics, lock, degraded state, reconnect interval, optional dependency import, try/except import) is structurally identical. `DegradedModeMixin` provides the reconnect check methods but not the initialization boilerplate.

---

## WS-3: Dataframe Cache Decorator

### SM-005: `cached_resolve` inner function -- monolithic build-or-wait logic (MEDIUM)

**Category**: Complexity
**Severity**: MEDIUM | **Frequency**: 1 occurrence | **Blast Radius**: 1 file, 172 lines
**Fix Complexity**: Low-Medium (clear decomposition seams exist)
**ROI Score**: 6.5/10

**Problem**: The `cached_resolve` function inside `dataframe_cache` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py:75-246` handles 4 distinct responsibilities in a single function with 5 levels of nesting:

1. **Bypass check** (lines 82-93): Check env var, call original if bypassed
2. **Cache hit path** (lines 95-116): Get cache, inject DataFrame, resolve
3. **Build-or-wait path** (lines 118-149): Acquire lock, wait for in-progress build, timeout handling
4. **Build path** (lines 151-246): Find build method, execute build, handle tuple/single return, store in cache, error handling

**Evidence** -- nesting depth trace:

```
def dataframe_cache(...)           # Level 0
  def decorator(cls):              # Level 1
    async def cached_resolve():    # Level 2
      if not acquired:             # Level 3
        if entry is not None:      # Level 4
      try:                         # Level 3
        if build_func is None:     # Level 4
        if isinstance(...):        # Level 4
          df, watermark = ...      # Level 5
```

Peak nesting: 5 levels (not 8 as claimed).

**Natural Decomposition Seams**:

1. Lines 82-93 could be `_check_bypass()`
2. Lines 95-116 could be `_try_cache_hit()`
3. Lines 118-149 could be `_wait_for_build()`
4. Lines 151-246 could be `_execute_build_and_cache()`

Each seam corresponds to a clear decision point:
- Bypass? -> call original
- Cache hit? -> inject and resolve
- Lock not acquired? -> wait for other builder
- Lock acquired -> build, cache, and resolve

**Additional Observation**: The `import polars as pl` at line 179 and `from datetime import datetime` at line 189 are deferred imports inside the function body. The polars import makes sense (heavy dependency), but the datetime import is already available from the module level (line 9 imports `UTC` from datetime, though not `datetime` itself). This is a minor inconsistency.

---

## Cross-Workstream Observations

### Pattern: Retry/Resilience Logic Duplication

SM-002 (cache backends) and SM-004 (DataServiceClient) both exhibit the same meta-pattern: resilience infrastructure (degraded mode, retries, circuit breakers) is copy-pasted into business logic rather than being composed as a reusable wrapper.

The codebase already has the right building blocks:
- `DegradedModeMixin` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/errors.py:113`
- `RetryableErrorMixin` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/patterns/error_classification.py:33`
- `CircuitBreaker` from `autom8y_http`
- `ExponentialBackoffRetry` from `autom8y_http`

But these are used as implementation details inside copy-pasted method structures rather than being composed via template method or middleware patterns.

**Flag for Architect Enforcer**: This cross-cutting resilience pattern duplication suggests a boundary violation -- resilience concerns are leaking into business method implementations rather than being handled at a layer boundary.

### Pattern: `@async_method` Adoption Gap

The `@async_method` descriptor at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/patterns/async_method.py` was clearly designed to solve SM-001, but only `SectionsClient` has adopted it. The remaining 11 Asana clients still use the older `@sync_wrapper` 3-part pattern. This suggests the descriptor was created during or after the sections client implementation but was never backported to existing clients.

---

## Scope Exclusion Compliance

The following items were encountered during analysis but NOT flagged per scope exclusions:

- `api/main.py` backward-compat shims: Not examined
- Broad catches: The `except Exception` at decorator.py:224 has the `BROAD-CATCH: boundary` annotation and is correctly scoped
- TYPE_CHECKING guards: Present in all client files; recognized as intentional circular import mitigation
- Unit extractor TODOs: Not examined
- Public API surfaces: Not flagged for change

---

## Attestation Table

| Artifact | Verified Via | Status |
|---|---|---|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` | Read tool | Lines 109-1120 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | Read tool | Lines 1-443 examined (reference pattern) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py` | Read tool | Lines 1-758 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/goals.py` | Read tool | Lines 1-654 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/webhooks.py` | Read tool | Lines 1-479 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py` | Read tool | Lines 1-288 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/custom_fields.py` | Read tool | Lines 1-1064 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py` | Read tool | Lines 1-1844 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Read tool | Lines 1-990 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Read tool | Lines 1-894 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/providers/tiered.py` | Read tool | Lines 1-563 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/providers/unified.py` | Read tool | Lines 1-909 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` | Read tool | Lines 1-251 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/patterns/async_method.py` | Read tool | Lines 1-231 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/sync.py` | Read tool | Lines 1-69 examined |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/base.py` | Read tool | Lines 1-236 examined |
| Line counts (wc -l) | Bash tool | All file sizes confirmed |

---

## Handoff Readiness Checklist

- [x] All major codebase areas scanned (clients/, cache/backends/, cache/dataframe/, patterns/, transport/)
- [x] Each smell has severity, location, evidence with file:line references
- [x] Findings ranked by cleanup ROI (summary table above)
- [x] Related smells grouped (SM-007/SM-008 as sub-patterns of SM-002) and cross-referenced
- [x] Boundary concerns flagged for Enforcer (resilience pattern leakage, @async_method adoption gap)
- [x] Artifacts verified via Read tool with attestation table
- [x] Pre-analysis claims validated and corrected where inaccurate
- [x] No scope-excluded items flagged
