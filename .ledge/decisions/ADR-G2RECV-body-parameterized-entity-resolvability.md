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
