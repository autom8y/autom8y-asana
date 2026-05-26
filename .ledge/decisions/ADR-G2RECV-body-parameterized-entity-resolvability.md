---
type: decision
artifact_kind: ADR
id: ADR-G2RECV-001
title: Body-parameterized entity types are queryable on schema presence alone
status: proposed
date: 2026-05-26
deciders: architect (10x-dev), rnd receiver-owner (autom8y-asana)
complexity: MODULE
gate_anchor: G2-RECV
supersedes: none
related:
  - .ledge/spikes/HANDOFF-rnd-to-10x-dev-g2-recv-CORRECTION-2026-05-26.md
  - .sos/wip/G2-RECV-finding-receiver-already-current-2026-05-26.md
  - A1+B1 receiver-surface contracts @ commit 4822eaad
self_ref_ceiling: STRONG (live prod-log + ECS + git tree + direct code anchors)
disciplines:
  - option-enumeration-discipline
  - structural-verification-receipt
  - authoritative-source-integrity
---

# ADR-G2RECV-001 — Body-parameterized entity types are queryable on schema presence alone

## Status

Proposed — pending principal-engineer implementation under the TDD of the same slug.

## Context

### The contradiction

`project` and `section` are **body-parameterized** entity types by design (A1
contract, commit `4822eaad`): the caller supplies `project_gid` per-request in the
`POST /v1/query/{entity}/rows` body rather than the receiver routing to a
statically-registered project. This is why their descriptors carry
`primary_project_gid=None` (S-06) and `warmable=False` — they are loaded on demand
against a body-supplied GID, not warmed from a fixed workspace project.

But the resolvability gate, written for the offer-domain (container-backed) entity
model, rejects them **before** the A1 body-precedence branch can ever run. The
result is that the A1 body-precedence branch is **unreachable dead code in
production**.

### Verified call path (all anchors re-read on origin/main this session)

```
POST /v1/query/project/rows  {"project_gid": "1203404998225231"}
  └─ query_rows()                                    src/autom8_asana/api/routes/query.py:403
       └─ entity_service.validate_entity_type("project")
            │                                          src/autom8_asana/services/entity_service.py:80
            ├─ GATE 1 (line 99-101): "project" not in get_queryable_entities()
            │     → raise UnknownEntityError → 404 UNKNOWN_ENTITY_TYPE     ← FIRES IN PROD
            │        get_queryable_entities() → get_resolvable_entities()
            │            src/autom8_asana/services/resolver.py:347:
            │            resolvable IFF schema present AND registry project_gid present
            │            project/section: schema YES, registry GID NO  → NOT resolvable
            │
            └─ GATE 2 (line 106-107): project_gid is None
                  → raise ServiceNotConfiguredError                       ← WOULD ALSO FIRE
       [the A1 body-precedence branch is never reached]
       └─ if request_body.project_gid is not None:    src/autom8_asana/api/routes/query.py:433
            resolved_project_gid = request_body.project_gid   ← DEAD CODE in prod
```

Live prod evidence (image `2d206e2`, ECS rev 420): `entity_resolver_discovery_complete
registered_types=[unit,unit_holder,business,offer,contact,asset_edit,asset_edit_holder]`
— project/section absent; `entity_project_section_discovery_missing` for both.

### Why discovery cannot fix this (AC-G2R-4)

The lifespan discovery (Phase-3 name-match) looks for a workspace project literally
named "Asana Projects"/"Projects"/"Asana Sections"/"Sections" among the 89 discovered.
None match, so no registry GID is ever assigned. **Discovery is the wrong mechanism
for body-parameterized types** — their GID is intrinsically per-request, not a fixed
workspace project. The correct answer is to make reachability **independent of
registration** for these types.

### Locked constraints (REJECT conditions if violated)

- A1+B1 contracts @ `4822eaad` — the fix IMPLEMENTS A1 intent; must not alter it.
- `require_business_scope=True` @ `src/autom8_asana/api/main.py:395`.
- Offer-domain entities (`unit`, `unit_holder`, `business`, `offer`, `contact`,
  `asset_edit`, `asset_edit_holder`) MUST STILL require a registry `project_gid`.
  A **global** loosening of the resolvability predicate is a REJECT condition.

## Decision

**Adopt Option A: a descriptor-level `body_parameterized` capability flag.**

Add a `body_parameterized: bool = False` field to `EntityDescriptor`. Set it `True`
on the `project` and `section` descriptors. The resolvability predicate
(`get_resolvable_entities`) treats an entity as resolvable when:

```
(schema present) AND ( descriptor.body_parameterized
                       OR registry.get_project_gid(entity) is not None )
```

`validate_entity_type` is amended so that for a `body_parameterized` entity it does
NOT raise `ServiceNotConfiguredError` when the registry GID is `None`; instead it
returns an `EntityContext` whose `project_gid` is `None` (a new sentinel state — see
TDD §EntityContext change), and the route's existing A1 body-precedence branch
(`query.py:433`) supplies the GID from the request body. Offer-domain entities are
untouched: with `body_parameterized=False`, the registry-GID requirement is preserved
exactly.

The flag is inherited by any future body-parameterized type by simply setting one
boolean on its descriptor — no predicate edits required.

## Options Considered

### Option A — Descriptor-level `body_parameterized` capability flag (CHOSEN)

A `body_parameterized: bool` on `EntityDescriptor`; the resolvability predicate and
`validate_entity_type` branch on it.

- **(+)** The capability is declared once, at the entity's single source of truth
  (the descriptor), alongside the related `warmable`/`primary_project_gid` fields it
  semantically co-varies with. A future body-parameterized type inherits the behavior
  by setting one boolean — zero predicate edits (Open/Closed: the predicate is closed
  to modification, open to extension via data) [DP:SRC-002 Martin 2003] [MODERATE | 0.70].
- **(+)** The offer-domain gate is **provably preserved**: the relaxation is gated on
  `descriptor.body_parameterized`, which is `False` for every offer-domain descriptor.
  A non-regression test asserting offer-domain still 404/ServiceNotConfigured without a
  registry GID locks this.
- **(+)** Discoverable: a reader scanning the descriptors sees `body_parameterized=True`
  next to `primary_project_gid=None` and understands the design intent without tracing
  the predicate.
- **(−)** Touches the `EntityDescriptor` dataclass (a widely-imported core type) — but
  additively, with a defaulted field; no existing call site changes.
- **(−)** Requires the predicate to consult the descriptor registry, a dependency
  `get_resolvable_entities` already has transitively (it reads schemas + project
  registry; adding the entity registry is the same altitude).

### Option B — Special-case `project`/`section` in the predicate / validate_entity_type

Hard-code the two names (`if entity_type in {"project", "section"}: ...`) inside
`get_resolvable_entities` and `validate_entity_type`.

- **(+)** Smallest diff; touches no shared type; fastest to land.
- **(+)** Trivially obvious what it does for exactly these two types.
- **(−)** **First-class anti-pattern**: the capability ("this type is body-parameterized")
  is encoded as a literal name-set in two procedural locations rather than as a property
  of the entity. The next body-parameterized type (e.g. a future `tag` or `portfolio`)
  requires editing both procedural sites again, and the maintainer must *know* both
  exist. This is the dependency pointing the wrong way — policy (the predicate) depends
  on a hard-coded detail (the name list) instead of on an abstraction
  [DP:SRC-003 Martin 2017] [MODERATE | 0.70].
- **(−)** The two name-sets drift independently over time (one gets a new type, the
  other is forgotten) — a latent re-ship of exactly the present class of bug.
- **(−)** Obscures intent: a reader of the `project` descriptor sees nothing indicating
  it is body-parameterized; the fact lives in a remote predicate's literal set.

### Option C — Auto-register a placeholder/sentinel registry GID for project/section at lifespan

Make discovery (or bootstrap) register a sentinel GID (e.g. the string `"__body__"`)
for project/section so the existing predicate passes unchanged.

- **(+)** Zero change to the resolvability predicate or `validate_entity_type`.
- **(−)** Pollutes the `EntityProjectRegistry` with a non-GID sentinel that violates
  the registry's invariant (values are real Asana project GIDs). Downstream readers of
  the registry GID (e.g. section-manifest lookups, freshness keys) would receive the
  sentinel and must each special-case it — pushing the special-case *further* downstream
  than Option B, into more sites.
- **(−)** The `query.py:433` body-precedence branch still must override the sentinel,
  so the A1 path is still load-bearing — but now there is *also* a fake registry entry,
  i.e. two sources of truth for the GID. Construct-validity hazard: the registry no
  longer means "this entity routes to this fixed project."
- **(−)** Hides the design intent behind a magic string; worst discoverability of the three.

### Decision rationale

Option A is selected over B because the search space here is **not** singular: the
codebase already anticipates additional dynamically-GID'd types (the descriptors carry
`primary_project_gid: str | None` and `warmable: bool` precisely to express on-demand
loading). Encoding the capability as descriptor data rather than as a procedural
name-set is the difference between a fix that holds in 18 months and one that re-ships
the bug the next time a body-parameterized type is added. Option A's marginal cost (one
defaulted field on a core dataclass) is small and additive. Option C is rejected on
construct-validity grounds — a sentinel GID corrupts the registry's meaning and spreads
special-casing downstream.

## Reversibility Assessment

**Two-way door.** `body_parameterized` is an additive, defaulted (`False`) field on an
internal dataclass; no schema migration, no public API contract change, no data
migration. The A1+B1 request/response contracts are untouched (the fix makes the
existing A1 branch reachable — it does not change the wire contract). Reverting is a
field removal plus predicate revert. No stakeholder sign-off required beyond normal
code review. The `/v1/query/{entity}/rows` response shape (double-envelope per B1) is
unchanged.

## Consequences

### Positive
- AC-G2R-3 (available_types includes project+section) and AC-G2R-5 (rows → 200 with body
  GID) become satisfiable; the A1 body-precedence path is reachable.
- The body-parameterized capability is reusable: future types opt in via one flag.
- Offer-domain registry-GID requirement is preserved and test-locked.

### Negative / risks (flagged for QA)
- `EntityContext.project_gid` must now admit `None` for body-parameterized entities (it
  is currently typed `str`). The route MUST resolve the body GID before passing it to the
  engine; a body request that omits `project_gid` for a body-parameterized type must
  fail-fast with a clear 422/400, NOT pass `None` into the query engine. See TDD §risk-1.
- AC-G2R-4: discovery will still emit `entity_project_section_discovery_missing` for these
  types (harmless now), OR the discovery attempt should be suppressed for
  `body_parameterized` types. The TDD scopes this as a log-noise decision, not a
  reachability dependency.
- Cache warmth: project/section are `warmable=False`; the rows path returns
  `CacheNotWarmError` (503) on cache miss because `_get_dataframe` does not build on miss.
  Whether a body-GID first-request triggers an on-demand build (via `@dataframe_cache`
  decorator) vs returns 503 is a residual behavior to confirm in QA — it does NOT block
  the resolvability fix but bears on the AC-G2R-5 happy-path under a cold cache. See TDD
  §risk-2.

## Compliance with locked constraints

- A1+B1 @ `4822eaad`: IMPLEMENTED, not altered (the A1 branch becomes reachable).
- `require_business_scope=True` @ `api/main.py:395`: untouched.
- Offer-domain registry-GID requirement: preserved by `body_parameterized=False` default
  and locked by non-regression test.

---

# ADR-G2RECV-002 (Addendum) — Request-time build-on-demand for body-parameterized entities

> Appended 2026-05-26. Closes ADR-G2RECV-001 §risk-2 (cold-cache 503 on AC-G2R-5).
> Status: Proposed — pending principal-engineer implementation under TDD-G2RECV §10-12.
> complexity: MODULE. Disciplines: option-enumeration-discipline, structural-verification-receipt, assessment-methodology (P-06 weighting / P-07 proxy).

## Context

ADR-G2RECV-001 made `POST /v1/query/{project|section}/rows` **reachable** (the A1
body-precedence branch is no longer dead code). But a cold request now returns
**503 CACHE_NOT_WARMED** rather than the 200 RowsResponse that AC-G2R-5 requires.

### Verified root cause (anchors re-read on `fix/g2-recv-body-parameterized-resolvability` @ 9fbfd766)

The rows path is cache-only and never builds on the request path:

```
POST /v1/query/project/rows {"project_gid": "<body gid>"}
  └─ query_rows()                                  api/routes/query.py:403
       └─ EntityQueryService.query(...)            services/query_service.py:337
            └─ strategy._get_dataframe(project_gid, client)   query_service.py:387
                 │   universal_strategy.py:727 — returns None on miss BY DESIGN
                 │   (:737-738 "DataFrame builds happen at warmup, not request-time;
                 │    This method does NOT trigger builds on cache miss.")
                 └─ None
            └─ df is None → raise CacheNotWarmError  query_service.py:389-404
       └─ except CacheNotWarmError → 503 CACHE_NOT_WARMED  query.py:486-493
```

Offer-domain entities only return 200 because a scheduled `cache_warmer` lambda
pre-populates them (`warmable=True`). `project`/`section` are `warmable=False`
(entity_registry.py:881,899 — `body_parameterized=True`) and take ARBITRARY
body-supplied GIDs, so they are **never warmed** → always cold → always 503.

### Build machinery already exists, but is NOT on this path

- `_build_dataframe` (universal_strategy.py:788) → `_build_entity_dataframe`
  (:812) → `ProgressiveProjectBuilder.build_progressive_async(resume=True)`
  (dataframes/builders/progressive.py:446). VERIFIED present.
- The `@dataframe_cache` class decorator (cache/dataframe/decorator.py:27)
  implements the **full** build-on-miss flow: cache-hit → lock-acquire →
  build+put → release, with coalescer-based dedup (`acquire_build_lock_async`,
  `wait_for_build_async(timeout_seconds=30.0)`, `release_build_lock_async`) and
  circuit-breaker integration. VERIFIED at decorator.py:99-285 and
  cache/integration/dataframe_cache.py:734-803.
- **But the decorator wraps `resolve()`, NOT `_get_dataframe()`.** The rows query
  path calls `_get_dataframe()` (query_service.py:387), so the decorator's
  build-on-miss is not reachable from the rows endpoint. `get_universal_strategy`
  (universal_strategy.py:956) returns an UNDECORATED strategy. VERIFIED: no class
  in src/ carries `@dataframe_cache` (grep-zero on `@dataframe_cache` class
  applications).

## Decision

**Adopt Option (i): synchronous build-on-request, inside `_get_dataframe`, strictly
gated on `descriptor.body_parameterized`, reusing the cache's existing coalescer
lock primitives for concurrency dedup, and wrapping the build in an explicit
`asyncio.wait_for(...)` timeout guard.**

On a cache miss in `_get_dataframe`, when (and only when) the strategy's entity
descriptor is `body_parameterized`, the strategy:

1. attempts to acquire the build lock (`acquire_build_lock_async`);
2. if NOT acquired (another request is building the same GID), waits via
   `wait_for_build_async(timeout_seconds=BUILD_WAIT_SECONDS)` and returns the
   warm result, or raises a typed build-timeout error on wait timeout;
3. if acquired, runs `_build_dataframe(project_gid, client)` under
   `asyncio.wait_for(..., timeout=BUILD_TIMEOUT_SECONDS)`, writes the result to
   the DataFrameCache (`put_async`), releases the lock (success=True), and
   returns the built DataFrame;
4. on build returning `None`, build raising, or build timing out: releases the
   lock (success=False, which records a circuit-breaker failure) and raises a
   typed error that maps to a clean 503 (`DATAFRAME_BUILD_*`) — NOT a 500, NOT a
   silent empty-rows 200.

A **legitimately empty** project (build succeeded, zero rows) returns a built,
empty DataFrame → 200 with `data: []` and `total_count: 0` (a real empty result,
distinguished from build-failure by the fact that `put_async` was called and the
DataFrame is non-`None`).

Offer-domain entities (`body_parameterized=False`) are **untouched**: the miss
path returns `None` exactly as today (cache-only), preserving the warmed/cache-only
serving contract. This is the hard non-regression from ADR-G2RECV-001.

### Why the build-on-miss branch lives in `_get_dataframe` (not the decorator)

The rows query path calls `_get_dataframe()` directly (query_service.py:387). The
decorator wraps `resolve()` and is therefore off-path. Three sub-options were
considered for WHERE the build lives (see Options Considered §Wiring); the chosen
wiring adds a private helper invoked from `_get_dataframe`'s miss branch, gated on
the descriptor flag, so the offer-domain `return None` path is provably preserved
(it is the `else` of an `if descriptor.body_parameterized` branch).

## Options Considered

### Option (i) — SYNC build-on-request inside `_get_dataframe` (CHOSEN)

Build the DataFrame inline on the request path on miss; cache it; return 200 with
rows on the **first** hit.

- **(+)** Satisfies AC-G2R-5 literally: the cold probe returns **200** (real rows
  or a legit empty-but-built result), not a 503-then-retry. The consumer's
  documented behavior is to fall back to legacy on any non-200 — a 503 on the
  probe defeats the receiver. One-shot 200 is the only behavior that closes
  AC-G2R-5 without a consumer change.
- **(+)** Reuses the EXACT proven primitives the decorator already uses
  (`acquire_build_lock_async` / `wait_for_build_async` / `release_build_lock_async`
  / `put_async` + circuit breaker). No new concurrency machinery; we lift the
  decorator's well-tested control flow into the `_get_dataframe` miss branch.
- **(+)** `_build_entity_dataframe` already routes through
  `ProgressiveProjectBuilder(resume=True)`, which uses manifest tracking and
  section-level persistence — a re-run after a partial build resumes rather than
  refetching, bounding the practical cost of the cold path.
- **(−)** A cold build is a synchronous Asana fetch + progressive build on the
  request path. uvicorn (entrypoint: `scripts/entrypoint.sh:53` — `python -m
  uvicorn ... --factory`, NO `--timeout-keep-alive` / no request-processing
  timeout) imposes no server-side hard limit, so a pathological large project
  could hang the worker. **Mitigation: mandatory `asyncio.wait_for` guard**
  (BUILD_TIMEOUT_SECONDS) — this is the load-bearing reason the timeout guard is
  not optional. There is no ALB/ECS request-timeout config in this repo (infra is
  external); the application MUST self-bound.
- **(−)** Holds a worker for the build duration. Acceptable for body-parameterized
  types: they are low-frequency, S2S, per-GID, and the lock coalesces concurrent
  duplicates so only one worker builds per (GID, entity).

### Option (ii) — ASYNC warm-then-retry (kick off build on 503, consumer retries)

503 triggers a background build; the consumer retries and gets 200 once warm.

- **(+)** Lowest request latency on the cold path; no worker held for the build.
- **(+)** Matches the existing decorator's "in-progress → 503 retry-after"
  semantics for the second concurrent caller.
- **(−)** **Fails AC-G2R-5 as written**: the AC wants a **200** on the probe. The
  consumer falls back to legacy on a non-200 (verified intent in the G2-RECV
  handoff), so a first-request 503 means the receiver path is never exercised on
  the probe — the AC's user-visible outcome (200 RowsResponse, cold) is not
  realized on the first call.
- **(−)** Requires the consumer to implement retry/backoff specifically for these
  types, OR a probe-warm step — a cross-surface change beyond this MODULE's scope
  and beyond the locked A1+B1 contract.
- **(−)** Background-build orchestration on a request thread (fire-and-forget
  task) is fragile under ECS task recycling; the build can be lost mid-flight with
  no caller awaiting it.

### Option (iii) — Apply `@dataframe_cache` decorator (or a `build_on_miss` flag) to the strategy

Decorate `UniversalResolutionStrategy` (or set a flag) so the decorator's existing
build-on-miss fires.

- **(+)** Zero new build/concurrency code — the decorator already does all of it.
- **(−)** **Off-path**: the decorator wraps `resolve()`, but the rows query path
  calls `_get_dataframe()` (query_service.py:387), not `resolve()`. Decorating the
  class does not put build-on-miss on the rows path without ALSO rerouting
  query_service to `resolve()` — a larger, riskier change that touches the
  offer-domain serving path (REJECT: offer-domain is FROZEN).
- **(−)** Decorating globally would change offer-domain `resolve()` behavior
  (currently undecorated). Gating the decorator per-entity is not expressible —
  the decorator is a class decorator, applied at class-definition time, not
  per-instance/per-entity. A factory that conditionally decorates per entity_type
  is possible but reintroduces the very name-set special-casing ADR-G2RECV-001
  Option B rejected.
- **(−)** The decorator's miss path raises `CACHE_BUILD_IN_PROGRESS` (503) for the
  **building** request too unless a hit follows — it is designed around
  warm-then-retry for offer-domain. Re-targeting it for first-hit-200 needs the
  build to be awaited inline anyway, which is Option (i) by another name.

**Wiring sub-decision (where the branch lives):** inside `_get_dataframe`'s miss
branch, after the DataFrameCache `get_async` miss, as
`if descriptor.body_parameterized: return await self._build_on_miss(...)`. The
descriptor is fetched via `get_registry().get(self.entity_type)` — the same
lookup `_get_custom_field_resolver` (universal_strategy.py:919) already performs,
so no new dependency. The offer-domain path is the untouched `return None` that
follows the branch.

### Decision rationale

Option (i) is selected because AC-G2R-5 demands a **cold 200**, and only an inline
build produces a 200 on the first request without a consumer-side change (the
consumer falls back to legacy on non-200, per the locked receiver contract). The
search space is genuinely constrained by the AC's "200 on probe, cold" wording:
Option (ii) is eliminated by the consumer fallback semantics, Option (iii) by the
decorator being off the `_get_dataframe` path and not per-entity gateable. Option
(i) reuses the decorator's proven lock/wait/release/circuit-breaker primitives
(so we inherit its concurrency correctness) and adds the one thing the decorator
lacks for this surface — an explicit build **timeout guard** — which the cold,
arbitrary-GID, server-timeout-free context makes mandatory.

The offer-domain non-regression is structurally guaranteed: build-on-miss is the
`if descriptor.body_parameterized` true-branch; offer-domain (`False`) falls
through to the unchanged `return None`.

## Concurrency, Timeout, Error mapping

- **Concurrency (dedup, not double-build):** reuse the coalescer. The first
  request for an uncached (GID, entity) acquires the lock and builds; concurrent
  requests for the SAME (GID, entity) get `acquired=False` and
  `wait_for_build_async` the result. Distinct GIDs do not contend (the lock key is
  per `(project_gid, entity_type)`). This is the decorator's exact pattern
  (decorator.py:279-285), lifted.
- **Timeout (mandatory):** `BUILD_TIMEOUT_SECONDS` (proposed default 25s, settings-
  backed) wraps the inline build via `asyncio.wait_for`. `BUILD_WAIT_SECONDS`
  (proposed default 30s — matches the decorator's `wait_for_build_async` default)
  bounds the waiter. On either timeout: typed 503 with `retry_after_seconds`, lock
  released `success=False` (circuit-breaker records the failure, so a repeatedly
  pathological GID trips the breaker and fast-fails subsequent requests). uvicorn
  imposes no request timeout (verified: no `--timeout-keep-alive` in
  `scripts/entrypoint.sh:53`), so the app-level guard is the only bound.
- **Error mapping (clean, not 500, not silent empty):**
  - build returns `None` → 503 `DATAFRAME_BUILD_FAILED` (existing code, exception_types.py:130).
  - build raises → 503 `DATAFRAME_BUILD_ERROR` (existing code).
  - `asyncio.wait_for` TimeoutError → 503 `DATAFRAME_BUILD_TIMEOUT` (new code on
    `ApiDataFrameBuildError`, or reuse `CACHE_BUILD_IN_PROGRESS` with retry_after).
  - wait-for-other-build timeout → 503 `CACHE_BUILD_IN_PROGRESS` (existing).
  - build succeeds with zero rows → **200**, `data: []`, `total_count: 0` (legit
    empty; distinguished because the DataFrame is non-`None` and was `put_async`'d).
  The route maps these via the existing `except CacheNotWarmError` plus a new
  `except ApiDataFrameBuildError` arm (query.py:486 region). Distinguishing
  "empty project" (200) from "build failed" (503) is the construct-validity line
  [assessment-methodology P-07]: the proxy for "real result" is "build completed
  and returned a non-None frame", not "rows > 0".

## Reversibility Assessment

**Two-way door.** The change is additive: a new private `_build_on_miss` branch in
`_get_dataframe` gated on a defaulted descriptor flag that is already `False` for
all offer-domain types, plus two settings-backed timeout constants and one new
error code. No schema migration, no wire-contract change (B1 double-envelope
response is unchanged — a built 200 has the same shape as a warmed 200). Reverting
is deleting the branch; offer-domain behavior is untouched throughout. No
stakeholder sign-off beyond code review.

## Compliance with locked constraints

- A1+B1 @ `4822eaad`: untouched. The 200 RowsResponse shape is identical for built
  vs warmed results.
- `require_business_scope=True` @ `api/main.py:395`: untouched.
- Offer-domain serving FROZEN (cache-only/warmed): preserved by the
  `if descriptor.body_parameterized` gate — offer-domain falls through to the
  unchanged `return None`. Locked by non-regression test (TDD §12 T-BOD-3).
