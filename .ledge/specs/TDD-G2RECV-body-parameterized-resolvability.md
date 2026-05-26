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
