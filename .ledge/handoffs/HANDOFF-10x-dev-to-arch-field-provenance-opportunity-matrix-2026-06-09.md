---
type: handoff
handoff_type: assessment            # 10x-dev (build, paused) → arch (topology/opportunity-matrix analysis)
station: rite-switch seam (10x-dev → arch)
source_rite: 10x-dev
target_rite: arch
date: 2026-06-09
initiative: field-provenance-&-population-contract (generalization of dataframe-resolution-coherence)
supersedes: none  # extends .know/telos/dataframe-resolution-coherence.md to the resolution/provenance layer
evidence_grade: STRONG-on-substrate (first-party live S3/git/DuckDB receipts) ; opportunity-matrix = TO-BE-MAPPED by arch
status: proposed
discipline: >
  Deliberate pause of the unit-MRR point-fix BEFORE over-commitment, to map the corpus-wide
  opportunity matrix first. Every load-bearing premise below carries a first-party live receipt from
  this session. The local checkout is the STALE cr3/gate2 branch — re-verify origin/main (e686ba06).
  No production code landed; the cure is an unmerged worktree (FPC cell-0 candidate). Production levers
  (re-warm, merge) stay the operator's.
---

# Field-Provenance & Population Contract — Topological Opportunity-Matrix HANDOFF (10x-dev → arch)

## Why this handoff exists

The unit-MRR null is **one cell of a corpus-wide class**: *field resolution is path-dependent, source-dependent, and uncontracted.* Rather than ship a point-fix and re-bite on the next cascade field, we hand to **arch** to paint the **topological opportunity matrix** — the full `entity × field × resolution-mode × fetch-path` lattice — and rank the generalization (the **Field Provenance & Population Contract / FPC**) by leverage. The point-fix resumes afterward as a *deliberate, mapped cell*, not a reflex.

## Rung statement (G-RUNG — not rounded up)

| Element | Rung | Receipt |
|---|---|---|
| SEAM-1 entity-identity contract | **live** | origin/main `e686ba06`, td `autom8y-asana-service:494` (2048/8192, image `e686ba0`), 1/1 |
| active_mrr (offer) | **realized-live** | 62 / $79,485 (offer prefix; eunomia rite-disjoint same-HEAD) |
| SEAM-2 substrate PV | **offer-ready / unit-hollow** | `.ledge/specs/SEAM-2-PREMISE-VALIDATION-AND-REQUIREMENTS-2026-06-09.md` |
| unit-MRR cure (FPC cell-0) | **authored, UNMERGED** | worktree `/Users/tomtenuta/Code/a8/repos/seam2-unit-econ` (branch `cr3-dfr/seam2-unit-economics-population`); 1355 tests pass; sufficiency UNPROVEN |
| FPC generalization | **conceived, not designed** | this handoff + the /consult synthesis below |
| topological opportunity matrix | **TO-BE-MAPPED** | arch's charge |

## Load-bearing premises (first-party live receipts this session — re-assert before design-lock)

1. **Single-canonical-project per entity** — `core/project_registry.py:24-28`: `OFFER_PROJECT=1143843662099250`, `UNIT_PROJECT=1201081073731555`, `OFFER_HOLDER_PROJECT=1210679066066870`, `UNIT_HOLDER_PROJECT=1204433992667196`, + business/contact/asset_edit/location/hours. Each entity-type = one project holding its entities as sections.
2. **Resolution modes are heterogeneous** — `schemas/*.py`: `Direct` (`source="cf:X"`), `Cascade` (`source="cascade:X"` from an ancestor via a join key office_phone/vertical), `Derived` (`.name`), and Holder `Aggregate`. The SAME logical field (MRR) resolves differently per consuming entity (unit=Direct, offer=Cascade-from-unit, offer_holder=sub-model).
3. **Fetch-path asymmetry (the unit-MRR root)** — unit v2-build fetches via `parallel_fetch._fetch_section → tasks_client.list_async(section,…)`; offer-cascade reads the unit ancestor via `hierarchy_warmer` per-task `get_async`. **Same unit, two paths, divergent `number_value`** — per-task GET carries it (offer mrr populated $1.3M raw), section list does not (unit mrr null). SDK opt_fields are symmetric (`BASE_OPT_FIELDS:69` + `_HIERARCHY_OPT_FIELDS:43` both request number_value) → the divergence is server-side Asana behavior, undocumented.
4. **The 571-unit smoking gun** — DuckDB join offer↔unit on office_phone: 2001 phones in both; **offer-mrr present for 571, unit-mrr null for ALL 571** (unit frame mrr = 0/3021). Source HAS the value; the unit-axis frame drops it. (NB: a residual fraction may be genuinely null-at-source / un-entered in Asana — the live Asana probe / re-warm is the discriminator, an operator lever.)
5. **Two NEW defect faces beyond FM-1/3/4** — (a) **path-dependent resolution** (premise 3); (b) **schema/model type-drift** — `discount` is `EnumField` in `models/business/unit.py:118` but `dtype="Decimal"` in `schemas/unit.py:38-43` → silent-null. *There are likely MORE discount-class drifts lurking — a parity sweep is part of the matrix.*
6. **The generalization seed exists** — `dataframes/builders/post_build_population_receipt.py` (the population-floor receipt) is entity-generic but populated for `offer` only (`_VALUE_COLUMNS_BY_ENTITY={"offer":(...)}`). The FPC generalizes this from one cell to the corpus.

## The arch charge — paint the topological opportunity matrix

Map the corpus lattice and rank the FPC by leverage. Concretely, the arch pantheon should produce:

- **topology-inventory** — the catalog: every entity (project_registry) × every field (schemas) × resolution-mode × required fetch-path × current population policy. The `(entity, field)` matrix is the unit of analysis.
- **dependency-map** — the **cascade/waterfall graph**: which fields originate where (Source nodes) and flow to which consumers (Cascade/Aggregate edges via join keys); coupling hotspots; the fan-out blast radius of each Source field.
- **architecture-assessment** — anti-patterns across the matrix: path-dependent-resolution cells, schema/model-drift cells (the discount-class sweep), presence≠population blind spots (which value fields have NO floor), single-fetch-path SPOFs, the FM-1/3/4 face coverage. Boundary alignment: does the entity/field decomposition match the domain?
- **architecture-report** — the **FPC opportunity matrix** ranked by leverage (impact ÷ effort): the 5 pillars (declarative FPC · path-canonicalization · generated verification matrix · cross-entity coherence invariant · population/coherence observatory) sequenced into a phased roadmap; the "dataflow type system for the data plane" reframe as the north-star architecture; cross-rite referrals (the build → 10x-dev; the live-probe/re-warm → operator).

## The FPC vision (from the /consult — carry as the design north-star, arch to pressure-test/refine)

A single declarative `FieldContract(name, value_type, canonical_source, resolution{mode per entity}, fetch_requirement, recovery[], population_policy)` per `(entity,field)`, from which schema dtype, resolver fallback, population-floor set + per-field policy, required opt_fields, and a **generated** verification matrix (resolution + coherence + schema/model-parity tests) are all DERIVED. Plus **path-canonicalization** (one maximal-completeness materialization per Source node — the cure cell-0 generalized, ZERO new API calls / CR-3-safe) and a **population/coherence observatory** (per-field SLIs). It **dissolves the A-vs-B dilemma**: canonicalize the path (fixes the list-vs-get strip) and observe the residual (makes genuine null-at-source honest, not a silent $0).

## DEFER / watch-registered (do NOT scope-creep into the arch map)

- **DEFER-UNIT-MRR-CELL0-LAND** — the cure worktree (cache-reuse + defense-parity + discount→Utf8 + guard) is authored, unmerged; land + live re-warm gated on the arch map + operator levers.
- **DEFER-LIVE-ASANA-PROBE** — qa-A's 6-call list-vs-get diff (needs `ASANA_PAT`); the discriminator for A-vs-B; operator lever.
- **DEFER-SEAM2-CONSUMER-REBIND** — autom8 monolith Consumer-1/2/3 (cross-repo); downstream of SEAM-1+unit-econ; `autom8/framing`.
- **DEFER-06-11-SOAK-TAIL** — CR-3 soak ~2026-06-11T12:25Z; Stage-B→Secret-2 (operator/IC).
- **DEFER-AMBER-OBS** — OK-on-absence g2 guards + dark receiver SLI/EMF (sre/observability).

## Referenced artifacts

| Artifact | Purpose |
|---|---|
| `.ledge/specs/SEAM-2-PREMISE-VALIDATION-AND-REQUIREMENTS-2026-06-09.md` | SEAM-2 substrate PV + N4 adversarial outcome (offer-ready/unit-hollow) |
| `.ledge/handoffs/HANDOFF-10x-dev-to-autom8-seam2-pv-complete-2026-06-09.md` | SEAM-2 consumer-rebind handoff (corrected premise) |
| `.ledge/handoffs/HANDOFF-eunomia-strong-cert-pt05-2026-06-09.md` | eunomia STRONG cert (receiver-side verified_realized) |
| `.know/telos/dataframe-resolution-coherence.md` | campaign telos + DEFER manifest (the FPC extends this) |
| `.know/scar-tissue.md` SCAR-DFR-001 | entity-identity defect-class record |
| `.know/design-constraints.md` GAP-011 / EC-020 | the cross-repo gap |
| worktree `/Users/tomtenuta/Code/a8/repos/seam2-unit-econ` | the unmerged FPC cell-0 cure |

## Routing

- **arch produces the opportunity matrix** (topology-inventory → dependency-map → architecture-assessment → architecture-report), challenged by **arch-adversary** at the outbound-HANDOFF gate.
- **Rite-switch seam back:** when the map is painted, HANDOFF → **10x-dev/framing** for the FPC build (architect TDD/ADR → spike path-canonicalization for N≥2 → eunomia rite-disjoint design critique → phased /sprint). The unit-MRR cell-0 lands within that framed build.
- Production-mutating levers (merge, prod re-warm, live Asana probe) stay the operator's throughout.

*10x-dev → arch, 2026-06-09. The point-fix is paused, not abandoned; arch maps the corpus so the fix lands as a deliberate cell. Every premise carries a live receipt; the stale local checkout was never trusted.*
