---
type: spec
status: accepted
---

# GID Field Resolver (GFR) — Design-Alignment Brief

- **Status:** Aligned (human-confirmed via structured interview) — ready for ultracode build
- **Date:** 2026-06-25
- **Owner:** Tom Tenuta
- **Working name:** GFR (GID Field Resolver)
- **Provenance:** Decisions below were each confirmed in a phased requirements interview. They are alignment constraints for the ultracode workflow (architect → principal-engineer → adversarial qa-adversary), not implementation prescriptions. Where a decision was deliberately left open, it is marked **LATITUDE**.

---

## One line

A gid-first, field-declarative **read** façade over the existing query layer — `resolve(gid, fields) → values` — that hides entity-tree topology from callers. An **interface**, not a new engine.

## Why this is mostly assembly, not invention

An Explore swarm confirmed ~80% of the substrate already exists. The build must **reuse**, not rebuild:

| Existing primitive | Location | Role in GFR |
|---|---|---|
| Query DSL (predicates, `RowsRequest.select`, Polars compile, `JoinSpec`) | `query/{models,engine,compiler}.py` | The projection + join substrate GFR plans onto |
| Entity graph (`join_keys`, `default_projection`, `get_join_key`) | `core/entity_registry.py` | The relationship hierarchy as data — GFR's join planner |
| Schema registry (`ColumnDef`, dtype/source/cascade) | `dataframes/models/{schema,registry}.py` | The field vocabulary (open-by-declaration) |
| gid → tree hydration (type-detect + up-traversal) | `models/business/hydration.py` | Topology detection for an arbitrary gid |
| criteria → gid (O(1) `DynamicIndex`) | `services/{universal_strategy,dynamic_index}.py` | The **reverse** verb — stays separate |
| Persisted lookup index | `services/gid_lookup.py` | Prior art for the warm-lookup path |

The genuine new surface is a thin (~order-of-200-line) orchestration layer: **entity-type detect → registry join-path lookup → single planned projection+join over the minimal frames → typed result.** Its value is the *interface*, not algorithmic cleverness. Polars already does projection/predicate pushdown — do **not** build a bespoke query optimizer.

---

## Vision & principles (ranked — use for tie-breaking)

1. **Interface decoupling** *(north star)* — callers ask for fields by name and never learn the topology (Business vs Offer vs Contact, up-traversal vs down-join, which S3 frame).
2. **Speed** — close second; runtime is availability-first.
3. **Correctness** — yields to the above **except** where a guardrail makes it inviolable.
4. **Fleet reach** — earned later, not forced now.

## The contract

- **Verb:** read-only field hydration — *one* verb. Reverse (`DynamicIndex`) and writes (`FieldResolver`) stay separate, untouched.
- **Cardinality:** **row-set native** — `gid → 1..N rows`. Provide **scalar sugar** only when the result is provably unambiguous; **never silently collapse N→1**. (A Business gid asking for `offer_id` legitimately returns N rows.)
- **Field vocabulary:** **open by declaration** — any `ColumnDef` present in the schema/`EntityRegistry` is automatically resolvable, no per-field code. A central guard enforces the cache-only + entity_type rules so openness can't bypass them.
- **Completeness:** **strict all-or-nothing** — if any *requested* field is genuinely unresolvable (unknown field, or truly-empty frame), the whole call fails with structured `UnresolvedError(fields=[…], reason=…)`.
- **Provenance:** every resolved field carries `{value, status, source, as_of}`. Completeness of the *set* is strict; *freshness* is surfaced, not gated.

## Runtime posture (availability-first, honest about age)

- **Stale = resolved.** A present value satisfies the contract regardless of age; an async refresh is triggered; staleness shows in provenance (`status: 'stale'`).
- **Cold miss → serve-stale-if-any + async rebuild.** Only when *truly nothing* is cached does the field count as unresolved (→ trips all-or-nothing). Reuse existing singleflight/coalesce machinery for the rebuild.
- **Coherence note:** stale-counts-resolved + serve-stale + all-or-nothing compose cleanly — the call effectively fails only on a genuinely-unknown field or a never-warmed-empty frame. That tiny failure surface is the intended "never lie" boundary, and it resolves the only apparent tension (decoupling/speed north star vs. strict all-or-nothing).

## Home & evolution

- **Engine in `autom8y-asana`** (iterates freely) **+ thin typed client in `autom8y-core`** (stable surface from day one). Engine and contract decoupled so the cross-fleet entry point exists immediately without freezing the implementation.

## Dogfood caller (the shaping force)

- **Send-origination / workstream-D**: `gid → company_id (== chiropractors.guid)` for the `{guid}@appointments.contenteapp.com` routing address. This is the concrete first consumer (identified in the 2026-06-24 send-origination review as the unbuilt "GID→guid" resolver). Shape the interface to this real caller, **then** generalize — not speculative generality.
- **POC field set:** `gid → (office_phone, company_id, vertical, offer_id, asset_id)`. Note these span tree levels: `office_phone`/`company_id`/`vertical` live on / cascade from **Business**; `offer_id`/`asset_id` live on **Offer/AssetEdit**. The tuple is only fully well-defined when gid is at/below Offer level — above it, it's a row-set (see Cardinality). Scoping the POC to gid-at-Offer-level is the fast path to first value.

## Truth-source (cross-service ownership)

- `company_id` is **owned by `autom8y-data`** (`chiropractors.guid`); asana holds a cached `Company ID` custom field.
- **Tiered**, riding the **existing asana↔data-service field hooks**: serve the fast local copy by default (provenance-tagged `source: 'asana-cache'`); high-stakes callers (send-origination) can force authoritative verification through the data-service path.

---

## Autonomy envelope — HARD lines (stop-and-ask; require an ADR to cross)

1. **No Asana API fallback on an offer-domain miss** — respect ADR-G2RECV-002 cache-only. A miss returns unresolved; it never silently calls the Asana API.
2. **Don't touch frozen query ranges (P1-C-04: `query/{engine,join,compiler}.py`) or the 35 `@pytest.mark.scar` tests** — GFR is a new layer *on top*, never an edit to these.
3. **No freezing the `autom8y-core` client contract without explicit human sign-off** — iterate the asana engine freely; propose the core surface but STOP before locking the fleet-binding API.

## Deliberate LATITUDE (build decides, QA hardens)

- **ADR-SEAM1 entity_type threading / dual-read was NOT marked inviolable.** The resolver should still use the entity-partitioned key shape (`dataframes/{project_gid}/{entity_type}/…`), but the build has latitude on *how* it rides the in-flight storage migration rather than treating it as a stop-and-ask gate. The adversarial /qa pass must pressure-test whatever choice is made here.

## Out of scope (v1)

- Reverse resolution (`fields → gid`) — exists as `DynamicIndex`.
- Writes / write-back — exists as `FieldResolver`.
- A bespoke query optimizer — Polars + the existing compiler already pushdown.

---

## Build obligations (carried from `.know`)

- Test coverage floor ≥80%; **service-layer unit tests** for the resolver, not just route-level integration.
- Any test with state singletons (e.g. a warm index cache) uses `pytest.mark.xdist_group(...)`.
- New entity classes (if any) must declare `PRIMARY_PROJECT_GID` (SCAR-001).
- If any resolved field depends on parent state, honor the 4-layer cascade defense (schema enforcement, warm-up ordering guard, null-rate audit, gap-skip).

## Open questions for the architect (non-blocking)

1. Persistent gid→fields index on S3 (the `gid_lookup_index.json` path) vs. on-demand projection from frames — the speed enabler; size against the cold-frame cost (0.5–120s build).
2. Exact provenance/freshness schema and where `as_of` is sourced (frame watermark vs. data-service hook timestamp).
3. SEAM1 ride strategy (see LATITUDE).
