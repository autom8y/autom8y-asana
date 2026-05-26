---
type: spec
artifact_kind: TDD
id: TDD-G2RECV-001
title: G2-RECV — make the A1 body-parameterized query path reachable for project/section
status: accepted
lifecycle_note: Ready for Implementation
date: 2026-05-26
author: architect (10x-dev)
complexity: MODULE
gate_anchor: G2-RECV
adr: .ledge/decisions/ADR-G2RECV-body-parameterized-entity-resolvability.md
self_ref_ceiling: STRONG (live prod-log + ECS + git tree + direct code anchors @ origin/main)
traces_to:
  - AC-G2R-3
  - AC-G2R-4
  - AC-G2R-5
disciplines:
  - structural-verification-receipt
  - option-enumeration-discipline
  - authoritative-source-integrity
---

# TDD-G2RECV-001 — Reachable A1 body-parameterized query path for project/section

> Implements **Option A** of `ADR-G2RECV-001`. All code anchors below were re-read
> on `origin/main` this session (squash merges make SHA-ancestry lie — verified by
> `git diff origin/main HEAD -- src/` = empty + direct Read of each file).

## 1. Acceptance criteria (restated verbatim)

- **AC-G2R-3**: available_types at `/v1/query` includes `project` + `section`.
- **AC-G2R-4**: lifespan discovery no longer the blocker for these types (decide: do we
  still attempt discovery for them, or is reachability now independent of registration?).
- **AC-G2R-5**: `POST /v1/query/project/rows` with a body `project_gid` → HTTP 200 +
  RowsResponse (double-envelope per B1).

## 2. Root cause (verified)

`project`/`section` are body-parameterized (A1, `4822eaad`): GID arrives per-request in
the POST body. Their descriptors carry `primary_project_gid=None` (S-06),
`warmable=False`. The resolvability gate rejects them before the A1 body-precedence
branch runs:

| Gate | Anchor | Behavior for project/section |
|------|--------|------------------------------|
| Resolvability predicate | `src/autom8_asana/services/resolver.py:347` | `get_project_gid(entity) is None` → not added to resolvable set |
| GATE 1 (queryable) | `src/autom8_asana/services/entity_service.py:99-101` | not in queryable → `UnknownEntityError` → 404 UNKNOWN_ENTITY_TYPE |
| GATE 2 (configured) | `src/autom8_asana/services/entity_service.py:106-107` | `project_gid is None` → `ServiceNotConfiguredError` |
| A1 body-precedence (dead code) | `src/autom8_asana/api/routes/query.py:433` | never reached |

**Both gates must be addressed** — fixing only GATE 1 leaves GATE 2 raising
`ServiceNotConfiguredError` because `get_project_gid("project")` is still `None`.

## 3. Row-model verdict (the two source artifacts disagree — RESOLVED)

**Verdict: the `schema_without_row_model` warning is a RED HERRING. No second fix
(row model) is required.** The evidence file §4 raised it as a potential AC-G2R-5
blocker; the handoff §2 called it a red herring. The handoff is correct. Anchors:

- **Read path builds from the DataFrame, not a row model.** `engine.execute_rows`
  (`src/autom8_asana/query/engine.py:128-249`) loads `df = await self.provider.get_dataframe(...)`
  (line 129), validates fields against `SchemaRegistry.get_schema(...)` (line 137), and
  builds `RowsResponse(data=df.to_dicts(), meta=RowsMeta(...))` (lines 222, 235-249).
  No `row_model_class_path` is dereferenced.
- **Provider build path is schema-driven.** `EntityQueryService.get_dataframe`
  (`src/autom8_asana/services/query_service.py:587`) → `strategy._get_dataframe`
  (`src/autom8_asana/services/universal_strategy.py:727`); the build
  (`_build_entity_dataframe`, `universal_strategy.py:812-889`) uses
  `self._get_entity_schema()` (line 836) and `ProgressiveProjectBuilder` with that
  schema. No row model referenced.
- **`row_model_class_path` is used in exactly two places, neither on the query path**:
  (a) registry validation syntax-check + the `schema_without_row_model` WARNING
  (`src/autom8_asana/core/entity_registry.py:1043-1075`, rule 6e at :1067-1075 is a
  `logger.warning`, not a raise); (b) the offer-domain typed-row convenience used by
  warming/extraction for those entities. project/section have schema + a generic
  `SchemaExtractor` (`entity_registry.py:874-877, 889-892`) and **no row model — by
  design**, and that is fine.
- **Empirical corroboration in the existing test**: the Sprint-2 test mocks
  `UniversalResolutionStrategy._get_dataframe` to return a plain polars DataFrame and
  asserts HTTP 200 + RowsResponse with NO row model present
  (`tests/unit/api/test_routes_query_project_section_rows_sprint2.py:50-60, 100-110`).
  The rows path provably builds for project from a bare DataFrame.

**Conclusion**: once project/section are reachable, the rows path builds for them with
no row-model change. Scope of second fix: **none**.

## 4. System design — components and change surface

### 4.1 Change surface (exact files:functions)

| # | File:anchor | Change |
|---|-------------|--------|
| C1 | `src/autom8_asana/core/entity_registry.py` — `EntityDescriptor` (class @ :~136, fields @ :143-179) | Add field `body_parameterized: bool = False` in the "Asana Project" section, next to `primary_project_gid`. Document in the docstring (:108-134). |
| C2 | `src/autom8_asana/core/entity_registry.py:862-878` (`project` descriptor) and `:879-893` (`section` descriptor) | Set `body_parameterized=True`. |
| C3 | `src/autom8_asana/services/resolver.py:338-369` (`get_resolvable_entities`) | In the per-task-type loop (:341-355), add an entity to `resolvable` when `(descriptor.body_parameterized is True) OR (project_registry.get_project_gid(entity_type) is not None)`. Read the descriptor via `get_registry().get(entity_type)`. Preserve the existing cache (:319-329, 365-367) — note the cache is keyed only on singleton use; descriptor flags are static, so cache validity is unaffected. |
| C4 | `src/autom8_asana/services/entity_service.py:99-124` (`validate_entity_type`) | After GATE 1 passes, look up the descriptor. If `descriptor.body_parameterized` AND `project_gid is None`: SKIP GATE 2 (`ServiceNotConfiguredError`) and construct `EntityContext` with `project_gid=None`. Offer-domain (`body_parameterized=False`) keeps GATE 2 unchanged. |
| C5 | `src/autom8_asana/services/entity_context.py:21-38` (`EntityContext`) | Widen `project_gid: str` → `project_gid: str \| None`. Update docstring (:28-32). This is the only type-level ripple; see §risk-1 for the route obligation. |

### 4.2 Predicate design (offer-domain preservation is provable)

```python
# resolver.py get_resolvable_entities() — per task_type loop
from autom8_asana.core.entity_registry import get_registry
entity_registry = get_registry()
...
for task_type in schema_registry.list_task_types():
    schema = schema_registry.get_schema(task_type)
    entity_type = schema.name
    descriptor = entity_registry.get(entity_type)
    is_body_param = bool(descriptor and descriptor.body_parameterized)
    has_registry_gid = project_registry.get_project_gid(entity_type) is not None
    if is_body_param or has_registry_gid:
        resolvable.add(entity_type)
```

**Offer-domain gate preservation proof**: every offer-domain descriptor
(`unit`, `unit_holder`, `business`, `offer`, `contact`, `asset_edit`,
`asset_edit_holder`) has `body_parameterized=False` (the default — they do not set it),
so `is_body_param` is `False` and the predicate reduces to the *exact pre-existing*
`has_registry_gid` condition. The relaxation is reachable ONLY for descriptors that opt
in. A test (T3 below) asserts an offer-domain type with no registry GID stays
non-resolvable.

### 4.3 GID resolution from the request body (where the body GID enters)

The body GID flow is already wired and correct — it was simply unreachable:

```
query_rows()  query.py:403
  ctx = validate_entity_type("project")     # now returns ctx.project_gid = None (body-param)
  if request_body.project_gid is not None:   # query.py:433 — A1 branch, NOW REACHABLE
      resolved_project_gid = request_body.project_gid
  else:
      resolved_project_gid = ctx.project_gid  # None for body-param → must fail-fast (risk-1)
  ... engine.execute_rows(project_gid=resolved_project_gid, ...)   # query.py:457
```

`EntityContext` carries `project_gid=None` for body-parameterized types; the route's
existing A1 branch supplies the real GID from `request_body.project_gid`. Downstream,
`engine.execute_rows(project_gid=...)` (engine.py:457→129) and the cache key
(`universal_strategy._get_dataframe(project_gid, ...)`, :768 `cache.get_async(project_gid,
entity_type)`) use the body-supplied GID directly — no registry consult needed.

## 5. AC-G2R-4 decision (discovery vs. registration independence)

**Decision: reachability is INDEPENDENT of registration for body-parameterized types.**
Discovery is the wrong mechanism for them (their GID is per-request, not a fixed
workspace project). We do NOT make registration a precondition.

- **Required**: the resolvability fix (C3) makes them queryable on schema presence +
  `body_parameterized` flag, with zero dependency on discovery succeeding.
- **Optional log-hygiene (implementer's discretion, non-blocking)**: suppress the
  `entity_project_section_discovery_missing` warning for `body_parameterized` types in
  the discovery routine, since the "missing" registration is expected-and-correct, not
  an error. This is cosmetic; it does NOT gate any AC. If deferred, the warning remains a
  benign log line.

## 6. AC-G2R-3 surface note (two distinct "available types" surfaces)

`AC-G2R-3` is satisfied via the **queryable/resolvable set**, which is what
`UnknownEntityError.available_types` reports (`entity_service.py:101` → `get_queryable_entities`
→ `get_resolvable_entities`; payload at `src/autom8_asana/services/errors.py:103`). After
C3, `project`/`section` join that set. ✅

**Flag for QA (separate surface)**: the introspection endpoint `GET /v1/query/entities`
(`query.py:204-216` → `introspection.list_entities`, `src/autom8_asana/query/introspection.py:26`)
is keyed on `registry.warmable_entities()` — and project/section are `warmable=False`, so
they will NOT appear there. If a consumer reads `GET /v1/query/entities` (not the error
payload) to determine availability, project/section stay invisible. This is OUT OF SCOPE
for AC-G2R-3 as worded ("available_types at /v1/query", i.e. the resolvable set), but the
implementer should confirm which surface the G2 consumer probe actually reads. If it reads
the introspection list, a follow-up is required (either include body-parameterized types in
`list_entities` or point the probe at the resolvable set).

## 7. Test plan (handoff-mandated regression on the UNREGISTERED path)

The existing test masks the prod path: `register_project_gids_sprint2`
(`tests/unit/api/test_routes_query_project_section_rows_sprint2.py:63-81`) is
`autouse=True` and pre-registers a GID for project+section, so GATE 1/GATE 2 never fire
in test. Any fix that passes ONLY with that fixture re-ships the gap.

| # | Test | Asserts | Runs WITHOUT autouse fixture? |
|---|------|---------|-------------------------------|
| T1 | `test_unregistered_project_rows_200_with_body_gid` | `POST /v1/query/project/rows` `{"project_gid": <valid>}` with NO `EntityProjectRegistry.register("project", ...)` → **200** + RowsResponse double-envelope; `meta.project_gid == body GID`. | **YES — must NOT use `register_project_gids_sprint2`.** Put in a new test module or a class that overrides/omits the autouse fixture. |
| T2 | `test_unregistered_project_in_resolvable_set` | `get_resolvable_entities()` (or `get_queryable_entities()`) includes `"project"` and `"section"` with NO registry GID registered. | YES |
| T3 | `test_offer_domain_still_requires_registry_gid` (NON-REGRESSION) | An offer-domain type (e.g. `"unit"`) with NO registry GID is NOT in `get_resolvable_entities()`; `validate_entity_type("unit")` with no registry GID raises `UnknownEntityError` (GATE 1) or `ServiceNotConfiguredError` (GATE 2). Locks ADR REJECT condition. | YES |
| T4 | `test_body_param_entity_context_project_gid_none` | `validate_entity_type("project")` (unregistered) returns `EntityContext` with `project_gid is None` and does NOT raise `ServiceNotConfiguredError`. | YES |
| T5 | `test_body_param_missing_body_gid_fails_fast` (risk-1 guard) | `POST /v1/query/project/rows` with EMPTY body (no `project_gid`) for an unregistered body-param type → fail-fast 4xx (NOT a 500 / NOT `None` into the engine). | YES |
| T6 | Retain existing AC-R1 tests | The 5 AC-R1 tests (`test_routes_query_project_section_rows_sprint2.py`) still pass (they exercise the registered + body-override paths). | (keeps autouse fixture — by design) |

**Fixture discipline**: T1-T5 MUST live where `register_project_gids_sprint2` does NOT
apply (separate module, or explicit `monkeypatch`/registry-reset to clear it). If a
reviewer sees these passing under the autouse fixture, the fidelity gap is not closed.

## 8. Risk areas (flagged for QA)

- **risk-1 (HIGH) — `None` GID into the engine.** Widening `EntityContext.project_gid`
  to `str | None` creates a path where a body-parameterized request that OMITS
  `project_gid` falls into the `else` at `query.py:445` (`resolved_project_gid =
  ctx.project_gid` = `None`) and passes `None` to `engine.execute_rows`. The
  implementer MUST add a fail-fast guard in `query_rows` (after the A1 branch): if the
  entity is body-parameterized AND `resolved_project_gid is None`, raise a clear
  400/422 (e.g. `ServiceNotConfiguredError`-equivalent "body project_gid required for
  body-parameterized entity"), NOT proceed. Locked by T5. The `aggregate` and legacy
  query endpoints (`query.py:494+`, `:571+`) share `validate_entity_type` — confirm they
  either reject body-parameterized types or apply the same body-GID precedence + guard.
- **risk-2 (MEDIUM) — cold-cache 503 on AC-G2R-5 happy path.** project/section are
  `warmable=False`; `_get_dataframe` (`universal_strategy.py:727-786`) does NOT build on
  miss ("DataFrame builds happen at warmup, not request-time", :737), returning `None` →
  `CacheNotWarmError` → 503. Whether a first body-GID request triggers an on-demand build
  via the `@dataframe_cache` decorator (`_cached_dataframe` injection, :132-133, :747-758)
  depends on decorator wiring not on the resolvability fix. QA must confirm the AC-G2R-5
  prod happy-path under a cold cache: does the first request 503 (then succeed on retry
  after warm) or build-on-demand? This does NOT block the resolvability fix but determines
  whether AC-G2R-5 needs a warm-up step or a build-on-miss change. Scope a follow-up only
  if QA shows a persistent 503.
- **risk-3 (LOW) — resolvable-entities cache.** `get_resolvable_entities` memoizes via
  `_cached_entities` (resolver.py:319-329). `body_parameterized` is static descriptor
  data, so the cache stays valid; but confirm the cache is populated AFTER descriptors are
  bound (`_bind_entity_types`, entity_registry.py:904) — it is, since discovery runs at
  lifespan after module load. No change needed; noted for QA awareness.

## 9. Handoff to principal-engineer

Implement Option A per §4 change surface (C1-C5), the §4.2 predicate, the §5 AC-G2R-4
decision (registration-independent + optional log-hygiene), and the §7 test plan with
T1-T5 on the **unregistered** path. Honor the §8 risk-1 fail-fast guard (mandatory) and
investigate risk-2 (report finding; fix only if QA shows persistent 503). Do NOT modify
A1+B1 (`4822eaad`), `require_business_scope` (`api/main.py:395`), or relax the
offer-domain registry-GID requirement (T3 locks this).

---

## 10. Build-on-demand component (closes risk-2 → AC-G2R-5 cold 200)

> Added 2026-05-26 on `fix/g2-recv-body-parameterized-resolvability` @ 9fbfd766.
> Design decision: ADR-G2RECV-002 (Option (i) SYNC build-on-request). This section
> is the implementation spec for principal-engineer. All anchors re-read this session.

### 10.1 The gap risk-2 left open

The resolvability fix made the rows endpoint REACHABLE; it returns 503
CACHE_NOT_WARMED cold because `_get_dataframe` (universal_strategy.py:727) is
cache-only by design (:737-738) and project/section are never warmed
(`warmable=False`, entity_registry.py:881,899). The rows path
(query_service.py:387) calls `_get_dataframe`, NOT the decorated `resolve()`, so
the existing `@dataframe_cache` build-on-miss never fires here.

### 10.2 Change surface (exact files:functions)

| # | File:anchor | Change |
|---|-------------|--------|
| C6 | `services/universal_strategy.py` `_get_dataframe` (:727-786) | After the DataFrameCache `get_async` miss (the final `return None` at :786), insert a gate: resolve `descriptor = get_registry().get(self.entity_type)`; `if descriptor and descriptor.body_parameterized: return await self._build_on_miss(project_gid, client)`. Offer-domain falls through to the unchanged `return None`. |
| C7 | `services/universal_strategy.py` NEW `_build_on_miss(self, project_gid, client) -> pl.DataFrame \| None` | Private method implementing the lock→build→put→release flow (§10.3). Reuses cache primitives `acquire_build_lock_async` / `wait_for_build_async` / `release_build_lock_async` / `put_async` (dataframe_cache.py:734-803). Build wrapped in `asyncio.wait_for(self._build_dataframe(...), timeout=BUILD_TIMEOUT_SECONDS)`. |
| C8 | `settings.py` | Two settings-backed constants: `dataframe_build_timeout_seconds: float = 25.0` (inline build cap) and `dataframe_build_wait_seconds: float = 30.0` (waiter cap, matches decorator default). Env: `ASANA_DF_BUILD_TIMEOUT_SECONDS`, `ASANA_DF_BUILD_WAIT_SECONDS`. |
| C9 | `api/exception_types.py` `ApiDataFrameBuildError` (:121) | Add documented error code `DATAFRAME_BUILD_TIMEOUT` to the docstring enum (no new class; reuse the 503 carrier with `retry_after_seconds`). |
| C10 | `api/routes/query.py` `query_rows` (:484-493 region) | Add `except ApiDataFrameBuildError as e:` arm mapping `e.code`/`e.status_code`/`e.details` to the API error envelope (the error already carries status 503 + retry_after). Confirm `aggregate` (:494+) and legacy (:571+) endpoints either reject body-parameterized types or share this mapping. |

No change to `_build_dataframe` / `_build_entity_dataframe` / `ProgressiveProjectBuilder` — they are reused as-is.

### 10.3 `_build_on_miss` control flow (lifted from decorator.py:279-285, +timeout guard)

```
async def _build_on_miss(self, project_gid, client) -> pl.DataFrame | None:
    cache = get_dataframe_cache_provider()
    if cache is None:                       # no cache configured → build raw, no lock
        return await _guarded_build(project_gid, client)   # asyncio.wait_for(_build_dataframe)

    acquired = await cache.acquire_build_lock_async(project_gid, self.entity_type)
    if not acquired:
        # another request is building THIS (gid, entity) → wait, return its result
        entry = await cache.wait_for_build_async(project_gid, self.entity_type,
                                                 timeout_seconds=BUILD_WAIT_SECONDS)
        if entry is not None:
            return entry.dataframe
        raise ApiDataFrameBuildError("CACHE_BUILD_IN_PROGRESS",
            "DataFrame build in progress, retry shortly", retry_after_seconds=5)

    # this request builds
    try:
        df, watermark = await asyncio.wait_for(
            self._build_dataframe(project_gid, client),  # returns (df, watermark)
            timeout=BUILD_TIMEOUT_SECONDS,
        )
        if df is None:
            await cache.release_build_lock_async(project_gid, self.entity_type, success=False)
            raise ApiDataFrameBuildError("DATAFRAME_BUILD_FAILED",
                "Failed to build DataFrame", retry_after_seconds=30)
        await cache.put_async(project_gid, self.entity_type, df, watermark)
        await cache.release_build_lock_async(project_gid, self.entity_type, success=True)
        return df                                  # may be an EMPTY frame → legit 200
    except asyncio.TimeoutError:
        await cache.release_build_lock_async(project_gid, self.entity_type, success=False)
        raise ApiDataFrameBuildError("DATAFRAME_BUILD_TIMEOUT",
            "DataFrame build exceeded time budget", retry_after_seconds=30)
    except ApiDataFrameBuildError:
        raise
    except Exception as e:   # BROAD-CATCH at build boundary → typed 503
        await cache.release_build_lock_async(project_gid, self.entity_type, success=False)
        raise ApiDataFrameBuildError("DATAFRAME_BUILD_ERROR",
            f"Build failed: {type(e).__name__}", retry_after_seconds=30)
```

Note `_build_dataframe` (universal_strategy.py:788) returns a `(df, watermark)`
tuple — `_build_on_miss` unpacks it; `put_async` takes `(project_gid, entity_type,
df, watermark)` (dataframe_cache.py:590).

### 10.4 Concurrency

Dedup, not double-build. Lock key is per `(project_gid, entity_type)` via the
coalescer (dataframe_cache.py:751 `_build_key`). One worker builds a given GID;
concurrent same-GID requests wait. Distinct GIDs build in parallel (no false
contention). This is the decorator's verified pattern — no new concurrency code.

### 10.5 Timeout

uvicorn runs with NO request-processing timeout (verified `scripts/entrypoint.sh:53`
— `python -m uvicorn ... --factory`, no `--timeout-keep-alive`); no ALB/ECS request
timeout is configured in-repo. The `asyncio.wait_for(BUILD_TIMEOUT_SECONDS)` guard
is therefore the ONLY bound on a pathological build and is mandatory, not optional.
Waiter bounded by `BUILD_WAIT_SECONDS`. Both settings-backed (C8). On timeout the
lock is released `success=False`, recording a circuit-breaker failure
(dataframe_cache.py:778-779) so a repeatedly slow GID fast-fails subsequent calls.

### 10.6 Error mapping (200 vs 503 — the construct-validity line)

| Outcome | HTTP | Code |
|---------|------|------|
| Build OK, rows > 0 | 200 | RowsResponse (B1 double-envelope) |
| Build OK, **zero rows** (legit empty project) | **200** | RowsResponse, `data: []`, `total_count: 0` |
| Build returned `None` | 503 | `DATAFRAME_BUILD_FAILED` |
| Build raised | 503 | `DATAFRAME_BUILD_ERROR` |
| Inline build exceeded `BUILD_TIMEOUT_SECONDS` | 503 | `DATAFRAME_BUILD_TIMEOUT` |
| Waiting on another build, exceeded `BUILD_WAIT_SECONDS` | 503 | `CACHE_BUILD_IN_PROGRESS` |

"Empty project" (200) vs "build failed" (503) is distinguished by `df is not None`
— a built empty frame is `put_async`'d and returned; a failed build returns `None`
or raises. NEVER a silent empty-rows 200 masking a failure, NEVER a 500.

## 11. Subsequent-request warmth

After a successful `_build_on_miss`, the frame is written via `put_async` (C7), so
the next request for the same (GID, entity) hits warm in `_get_dataframe`'s existing
DataFrameCache `get_async` branch (universal_strategy.py:768) and returns 200
without rebuilding. TTL/eviction follows the existing DataFrameCache policy
(unchanged). No per-GID warming registration is created — warmth is request-driven
and ephemeral, which is correct for arbitrary body-supplied GIDs.

## 12. Test plan (build-on-demand)

Extends §7 (T1-T5 resolvability tests, unchanged). New tests:

| ID | Scenario | Assert |
|----|----------|--------|
| **T-BOD-1** | Cold cache → first `POST /v1/query/project/rows` with valid body `project_gid` | 200; RowsResponse; `_build_dataframe` invoked once; result written to cache (`put_async` called). **This is AC-G2R-5.** |
| **T-BOD-2** | Warm second hit (same GID, immediately after T-BOD-1) | 200; `_build_dataframe` NOT invoked again (served from cache `get_async`). |
| **T-BOD-3** | **Offer-domain non-regression** — cold `offer`/`unit` query with no warm cache | Behavior UNCHANGED: `_get_dataframe` returns `None` → `CacheNotWarmError` → 503 CACHE_NOT_WARMED. `_build_on_miss` NOT invoked (descriptor `body_parameterized=False`). Hard gate from ADR-G2RECV-002. |
| **T-BOD-4** | Concurrency — two simultaneous cold requests, SAME GID | `_build_dataframe` invoked exactly ONCE; both requests get 200 with identical rows (one builds, one waits via `wait_for_build_async`). No double-build. |
| **T-BOD-4b** | Concurrency — two simultaneous cold requests, DIFFERENT GIDs | Both build (no false contention); both 200. |
| **T-BOD-5** | Build failure — `_build_dataframe` returns `None` | 503 `DATAFRAME_BUILD_FAILED`; lock released `success=False`; circuit-breaker failure recorded. NOT 500, NOT empty 200. |
| **T-BOD-5b** | Build raises | 503 `DATAFRAME_BUILD_ERROR`; lock released `success=False`. |
| **T-BOD-6** | Timeout — `_build_dataframe` exceeds `BUILD_TIMEOUT_SECONDS` (inject slow build) | 503 `DATAFRAME_BUILD_TIMEOUT` within ~budget; request does NOT hang; lock released `success=False`. |
| **T-BOD-7** | **Legit empty project** — build succeeds, zero rows | **200**; `data: []`; `total_count: 0`; frame written to cache (warm on retry). Distinguished from T-BOD-5. |
| **T-BOD-8** | Waiter timeout — second request waits, builder exceeds `BUILD_WAIT_SECONDS` | Second request 503 `CACHE_BUILD_IN_PROGRESS` with `retry_after_seconds`. |

## 13. Handoff delta to principal-engineer (build-on-demand)

Implement C6-C10 per §10.2, the §10.3 `_build_on_miss` flow, the §10.5 mandatory
`asyncio.wait_for` guard, and §12 T-BOD-1..8. The build-on-miss branch MUST be
gated strictly on `descriptor.body_parameterized` (T-BOD-3 locks offer-domain
non-regression — this is a REJECT condition if violated). Reuse the existing cache
coalescer primitives and `_build_dataframe`/`ProgressiveProjectBuilder` as-is — do
NOT write new concurrency or build machinery. Do NOT decorate the strategy class
with `@dataframe_cache` (off-path; would touch offer-domain `resolve()`). Do NOT
modify A1+B1 (`4822eaad`), `require_business_scope` (`api/main.py:395`), or the
offer-domain `return None` cache-only path.
