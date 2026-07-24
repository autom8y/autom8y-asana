---
type: decision
status: accepted
---

# ADR — Entity-resolution primitive: hierarchy-first, phone-as-fallback (office-guid / task->business)

- Date: 2026-07-08
- Rite: arch (autom8y) -> handoff to 10x-dev (autom8y-asana)
- Slug: entity-resolution-primitive
- Self-assessment ceiling: **MODERATE** (design-reasoning over a self-authored option slate;
  the only live proof is the spike's own monkeypatch driver — corroborating, not independent.
  STRONG requires an independent build + 2-sided QA receipt. Per `self-ref-evidence-grade-rule`.)

## Context

The onboarding_walkthrough resolves a PLAY task's owning business (and its office guid = the
`Company ID` custom field) by a **lossy office_phone search**, when the platform already ships an
**authoritative ownership relation** — the Asana parent chain — and already reuses it live in
`cascade_validator`. This is a **re-mint** of resolution that should have been an **integration**.

### The felt bug (client-held)

Total Wellness Center PLAY `1215766139321621` refused with `ContactCardBusinessAmbiguous` because
`+13036277995` aliases the practice's BUSINESS card `1214127219419742` AND its opportunity/lead
card `1214420107547660` ("Holly R. Geersen, DC") — same practice, two Business-project matches
after the discriminator, correct fail-closed refuse (SVR
`.ledge/spikes/SPIKE-office-guid-resolution-hierarchy-vs-phone-2026-07-08.md:9-19`).
The office is **held** by the current phone resolver.

### The re-mint debt (phone resolution sites — verified at origin/main)

- `onboarding_walkthrough/template_comment.py:232-261` `_resolve_office_guid` — PLAY -> `_read_office_phone` -> `_business_gid_by_phone` (:245) -> `_company_id_from_task` (:255).
- `onboarding_walkthrough/contact_synthesis.py:374-414` `_business_gid_by_phone` — workspace `/tasks/search` by Office Phone CF, filter to Businesses-project members, raise `ContactCardBusinessAmbiguous` on >1 (:406-410); called by `resolve_ranked_cards` (:434) and (via it) `post_contact_card` (:503).
- `api/routes/intake_resolve.py:69-157` `resolve_business` — S2S POST, phone-only via `GidLookupIndex` O(1) (`services/intake_resolve_service.py:56-97`). Same lossiness class, separate process/store.

### The canonical substrate to integrate (shipped, verified)

- `cache/policies/hierarchy.py:160-182` `get_ancestor_chain(gid, max_depth)` and `:202-215` `get_root_gid` — thin Asana wrappers over `autom8y_cache.HierarchyTracker` (`:87-90`), fed by `register()` (`:96`). **Returns `[]` for an unregistered gid** (`:175` doc).
- `cache/providers/unified.py:709-769` `get_parent_chain_async` — the WARM-path ordered chain (store-backed, gap-resilient).
- `dataframes/builders/cascade_validator.py:102-107` — the LIVE exemplar pairing (ancestor chain + parent-chain fetch), works ONLY inside an already-warmed DataFrame build.
- `core/project_registry.py:21` `BUSINESS_PROJECT = "1200653012566782"`; `core/entity_registry.py:299` `get_by_gid(project_gid) -> EntityDescriptor | None`; `:445-446` BUSINESS descriptor `category=EntityCategory.ROOT`, `primary_project_gid="1200653012566782"` (**literal parity** with `contact_synthesis.py:103` `_BUSINESSES_PROJECT_GID` and `project_registry.py:21`).

### The decisive constraint (verified at origin/main)

The walkthrough constructs **plain `AsanaClient()`** at every site — NO `UnifiedTaskStore`, NO
`get_parent_chain_async` handle (SVR: `contact_synthesis.py:591`, `template_comment.py:432`,
`link_on_play.py:305`, `floodgates/batch.py:276`). `git grep get_ancestor_chain|get_parent_chain_async`
over `onboarding_walkthrough/` returns **ZERO** hits. On the felt path the warm-index chain is
therefore **structurally unavailable** — any design MUST self-warm via live `parent.gid` reads.

### The B5 lesson (why we do NOT re-propose a gid_map path)

`DataServiceClient.get_gid_map()` was ratified then **falsified live at B5**: it returned `None` for
Sand Lake under every vertical — an **external M2M data-export coverage gap**, not a code bug
(SVR `contact_synthesis.py:429` comment; spike). The revert to a pure-Asana phone bridge was
correct at the time. The chosen design reads the **Asana task tree directly** (zero
DataServiceClient / M2M / vertical / export surface), so the B5 failure MODE is **structurally
unreachable**.

## Decision

Adopt **HierarchyFirstOfficeResolver** — a single new shared resolver seam in
`onboarding_walkthrough/` that makes the **ancestor walk PRIMARY** and **phone a labeled
fallback**, GRAFTED with:

1. a **typed frozen-dataclass result** `BusinessResolution(business_gid, company_id, method, ancestor_depth, candidates)` with a `method: Literal["hierarchy","phone"]` **provenance tag** (from Candidate 2 — makes the phone-fallback RATE an observable fleet signal);
2. a **registry-typed discriminator** via `entity_registry.get_registry().get_by_gid(project_gid)` rather than a raw `projects.gid == literal` compare (from Candidate 3 — auto-tracks any future BUSINESS project-GID move; keep `BUSINESS_PROJECT` as the fallback literal);
3. an **assert-at-most-one BUSINESS ancestor** within the walked chain, raising a LOUD `BusinessResolutionAmbiguous` rather than silently first-matching (preserves the phone bridge's "never pick a receiver silently" discipline, `contact_synthesis.py:406-410`);
4. **phone-as-crosscheck OFF by default** (`phone_crosscheck=False`): the phone bridge survives as (a) automatic fallback when the walk returns `None`, and (b) an optional shadow tripwire that raises `DivergentOfficeResolution` on hierarchy!=phone during rollout;
5. **`NullCacheProvider()` pinned on the resolver's read path** until SIBLING-1 (cache hit-path projection-coverage) lands fleet-wide — the walk's `tasks.get_async(opt_fields=[... projects.gid, custom_fields ...])` reads are subject to the cross-reader projection-coverage starvation (`DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md:20-37`; `clients/tasks.py:209-235`).

The resolver is **store-independent by construction**: it walks via `tasks.get_async` following
`parent.gid`, registering each fetched node into a **fresh local `HierarchyIndex()`** (the SAME SDK
primitive `HierarchyIndex` wraps at `hierarchy.py:87-90`) so cycle-detection and the depth bound come
**free** from `HierarchyTracker.get_ancestor_chain` — reuse, not re-mint of traversal.

Ship **BUSINESS-only** with a private `project_gid` parameter seam; do NOT build the
`EntityType|EntityCategory` target generalization speculatively (YAGNI until a second caller ships).

## Litigated options

| # | Option | Score | Spine | Verdict |
|---|--------|-------|-------|---------|
| 1 | **HierarchyFirstOfficeResolver** (surgical, single shared seam) | **8.4** | fresh **local** `HierarchyTracker` fed by live `parent.gid` reads — store-independent as PRIMARY architecture | **CHOSEN (spine)** |
| 2 | canonical-resolver-service (`BusinessResolver` primitive in `services/`) | 7.6 | store warm-path + self-warm via `put_batch_async(warm_hierarchy=True)`; reaches services/ + tier1 + hierarchy_warmer + S2S in one primitive | grafted (typed result + provenance) |
| 3 | EntityAncestorResolver (typed `resolve_owning_entity(target)` platform primitive) | 7.3 | `store.get_parent_chain_async` (unified.py:709) — **which the storeless walkthrough lacks** | grafted (registry-typed discriminator) |

All three agree on the mechanism (walk PLAY ancestors -> first BUSINESS_PROJECT member -> Company ID)
and all three refuse to re-propose the B5-falsified `get_gid_map` path. The **differentiator is the
spine**: Candidates 2 and 3 build on the store's warm-path chain, which the felt surface does not
have, so they degrade to self-warming or a hard SIBLING-1 dependency and widen blast radius.
Candidate 1 alone treats store-independence as PRIMARY. Its only deficits (bare `str` return; raw
literal compare; under-weighted SIBLING-1 coupling) are **cheap grafts** from 2 and 3.

## Why chosen

- **Ships for a FELT bug** (a held client office). Bias per telos (daily client trust; retire-monolith is a MEANS): a right-sized change that ships beats a grand rewrite that stalls.
- **Closes the collision CLASS at the source**: a PLAY has exactly ONE business ancestor (spike:29); the walk is structurally immune to phone aliasing.
- **Reuse, not re-mint**: reuses `HierarchyTracker` traversal, the verified-identical BUSINESS-project discriminator, `_company_id_from_task` (`template_comment.py:217`), and the `cascade_validator` shape — at the identity-resolution altitude.
- **Preserves the crown-jewel guard byte-for-byte**: the `TaskOfficeMismatch` verification (`template_comment.py:319-327`, supplied `office_guid` must EQUAL task-resolved guid) is UNCHANGED — it now compares against the hierarchy-resolved guid, strictly stronger.
- **B5-safe by construction**: pure-Asana tree walk; the coverage-gap failure mode is unreachable.
- **Additive-then-substitutive**: automatic phone fallback means no flag-day; one-line reversible.

## Consequences

### Positive

- The `ContactCardBusinessAmbiguous` HALT that holds TWC (and any practice with an opportunity/lead card sharing the office phone) is resolved for well-parented PLAYs.
- `method="phone"` provenance becomes a fleet signal: a rising phone-fallback rate = hierarchy gaps / mis-parented PLAYs, surfaced not silent.
- The `project_gid` parameter seam makes the future `resolve_owning_entity(target)` generalization a ~15-LOC promotion when a second caller (offer/unit/process) actually ships.
- The registry-typed discriminator auto-tracks any BUSINESS project-GID move.

### Negative / accepted

- **SIBLING-1 coupling (real, contained)**: the resolver is pinned to `NullCacheProvider()` until the cache hit-path projection-coverage check lands. This matches the current floodgates unblock, so it costs nothing today, but leaves the projection-coverage class open for cached callers. **DEFER-WATCH**: switch to cached reads only after SIBLING-1 lands.
- **Ambiguity still reachable on fallback**: an orphan / mis-parented PLAY yields no BUSINESS ancestor -> falls to phone -> the TWC-class collision can reappear as a LOUD refuse (correct fail-closed, not silent). Residual, documented.
- **Extra live reads**: 2-3 `parent.gid` gets vs 1 phone-search + 1 Business get; bounded by `max_depth=5` and short-circuit on first BUSINESS member.
- **S2S `intake_resolve` sibling is out of scope** for this seam (separate process/store). Deferred to a follow-up ticket (additive optional `task_gid`), NOT a gate on shipping the walkthrough fix.

### Open forks (resolved in TDD)

- FORK-1: entity-generality LATER (ship BUSINESS-only, `project_gid` seam).
- FORK-2: SIBLING-1 = contained coupling via `NullCacheProvider` NOW + DEFER-WATCH (not a Phase-0 gate).
- FORK-3: distinct loud refusal codes for depth-exhaustion vs no-business-ancestor; live multi-membership spot-check before build.
- FORK-4: S2S `intake_resolve` explicitly OUT of scope for this seam (follow-up ticket).
- FORK-5: `resolve_ranked_cards` signature migration (add `task_gid`/`play_gid`; retain `office_phone` as deprecation-window fallback + crosscheck); confirm no external caller depends on phone-only entry; crosscheck shadow = one full batch wave with zero divergence before flipping off.

## References

- Spike: `.ledge/spikes/SPIKE-office-guid-resolution-hierarchy-vs-phone-2026-07-08.md`
- Defect (SIBLING-1): `.ledge/reviews/DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md`
- TDD: `.ledge/specs/TDD-entity-resolution-primitive-2026-07-08.md`
- Handoff: `.ledge/reviews/HANDOFF-arch-to-10xdev-entity-resolution-2026-07-08.md`
