---
type: decision
subtype: adr
title: Single Declarative FieldContract as SSOT for the Data-Plane Field-Resolution Lattice
initiative: field-provenance-population-contract
status: proposed  # NOT accepted-and-built; design-ratified-pending (G-RUNG)
date: 2026-06-09
author: architect (10x-dev)
head: 50ebfe3381a627df868887ca3cdf9e223e1f9a90
evidence_grade: MODERATE  # self-ref ceiling; STRONG requires eunomia rite-disjoint critic (HELD operator lever)
companions:
  - .ledge/specs/TDD-field-provenance-population-contract-2026-06-09.md
  - .sos/wip/frames/field-provenance-population-contract.shape.md
supersedes: []
relates_to:
  - .worktrees/cr3-dfr-seam1/.ledge/decisions/ADR-seam1-entity-identity-key.md  # N=1 of the same throughline
---

# ADR — Single Declarative FieldContract as SSOT

## Status

**PROPOSED** (design-ratified-pending). Not accepted, not built. STRONG ratification
is gated on the eunomia rite-disjoint critic (operator lever, HELD); self-assessment
caps at MODERATE per `self-ref-evidence-grade-rule`.

## Context

The data-plane field-resolution lattice has 82 (entity, field) cells across 10
entities. Verified at origin/main `50ebfe33…`, the lattice exhibits four defect
faces that are projections of ONE structural absence — the field's resolution
contract is implicit and split across two unbound layers (schema files
`dataframes/schemas/`, model files `models/business/`):

1. **Schema/model drift** (AP-2): dtype declared twice, nothing binds them. Three
   live drift cells — D1 `unit.discount` (schema `dtype="Decimal"` @
   `schemas/unit.py:38-41` vs model `discount = EnumField()` @
   `models/business/unit.py:118`); D2 `offer.cost` (`Utf8` @ `schemas/offer.py:70-73`
   vs `NumberField()` @ `models/business/offer.py:136`); D3 `asset_edit.score`
   (`Float64` @ `schemas/asset_edit.py:147-151` vs Decimal accessor). Plus
   `offer_id` Utf8↔Int64 cross-frame (`schemas/offer.py:42-45` vs
   `schemas/asset_edit.py:126-130`).
2. **Path-dependent value** (AP-1/AP-4): section-LIST drops `number_value`,
   per-task-GET carries it; opt_fields ALREADY symmetric; ZERO number-recovery
   backstop (number-scoped grep EMPTY, verified this pass).
3. **Present-but-null** (AP-3): only `offer` has a population floor
   (`post_build_population_receipt.py:60-61`); 80/82 cells unguarded.
4. **Coherence break** (the live consequence): `offer.mrr[phone] IS NOT NULL AND
   unit.mrr[phone] IS NULL` for **571** phones; `coherent=0` (re-fired this pass:
   `gun=571, total_joined=2001`; `unit.mrr 0/3021`, `offer.mrr 1325/4070`).

SEAM-1 closed the IDENTITY + POPULATION-detector faces (entity-keyed S3 key + the
WARN-first `post_build_population_receipt`). The TYPE and PATH faces remain open
with no repair mechanism. The question: **what single structural change makes
"wrong entity", "present-but-null", "path-dependent value", and "schema/model
drift" impossible by construction, rather than patched per-instance?**

## Decision Drivers

- G-PROPAGATE: the fix must propagate from ONE shared point; per-field orphan
  fixes are rejected (they re-drift).
- G-DENOM: per-field population policy (`ActiveSubset` / `Total` /
  `LegitimatelySparse`); never blanket null-fill.
- CR-3-safe: no new Asana API fan-out (single uvicorn worker, SlowAPI 100/min).
- Reversibility awareness: schema-derivation is a one-way door; flag it.
- The schema layer is ALREADY half-declarative (`ColumnDef(source="cf:X")`).

## Options Considered

### Option A — Status-quo two-layer + parity test only (do-minimum)

Keep schema files and model files as independent declarations. Add ONLY a
generated parity test that reads both and asserts agreement. Reconcile the 3 drift
cells by hand.

- **+** Lowest effort (leverage 4.0 — the Phase-1 quick-win on its own). CR-3-safe.
  No new primitives. Immediately catches D1/D2/D3 and any future drift via CI.
- **+** Reversible (two-way door): a test is additive; line reconciles are local.
- **−** Does NOT make drift *impossible* — it makes drift *detectable*. The two
  declarations still exist; a developer can still write divergent dtypes and the
  test catches it only at CI time, not at authoring time.
- **−** Does NOT address AP-1 (path) or AP-3 (floor) at all. Solves 1 of 4 faces.
- **−** No single propagation point — opt_fields, floor set, recovery remain
  scattered. Fails G-PROPAGATE for everything except the parity check.

### Option B — Generate schema FROM model annotations (no separate contract)

Make the model layer the SSOT. Derive schema `ColumnDef` dtype from the model's
field-class (NumberField→Decimal, EnumField→Utf8, etc.). Delete the independent
schema dtype declaration.

- **+** Eliminates the drift class structurally (one declaration → no second to
  diverge). Reuses the existing model layer as the source. No new dataclass.
- **+** Fewer moving parts than Option C (no new contract type to maintain).
- **−** The model layer is the WRONG SSOT for the *fetch/population/coherence*
  axes. Model field-classes describe value extraction, not fetch_requirement,
  recovery, or population_policy. Encoding those on model fields overloads the
  model layer with data-plane concerns it does not own (violates SRP /
  bounded-context separation — the model is the Asana-object abstraction, not the
  data-plane materialization policy).
- **−** FM-C asymmetry: model-only NumberFields (`meta_spend`, `voucher_value`, …)
  would auto-materialize as schema cells, possibly materializing fields that were
  intentionally omitted (UK-1) — the wrong default direction.
- **−** Cascade/Derived/Aggregate provenance is a data-plane concept with no
  natural home on a model field. `offer.mrr` is `cascade:MRR` — there is no model
  field-class that expresses "this value cascades from the unit ancestor."
- **−** Still does not address AP-1 (path recovery) or AP-3 (floor) — those have
  no model-layer representation at all.

### Option C — Full declarative FieldContract as SSOT (CHOSEN)

Introduce one `FieldContract` per (entity, field) carrying all five axes
(identity, value_type, fetch/recovery, population, coherence). Derive schema
dtype, model field-class, opt_fields, floor set, AND the generated verification
matrix from it. The contract is the SOLE write point.

- **+** Makes ALL FOUR faces impossible by construction: drift (one value_type →
  both dtype and field-class), path (one fetch_requirement → recovery), floor
  (one population_policy → floor set), coherence (one coherence_consumers → the
  571-class test). Full G-PROPAGATE.
- **+** Completes the *already-declarative* direction (`ColumnDef(source=…)` is
  already a partial contract). Not a new paradigm — the philosophy already wants
  a declarative contract (assessment §5).
- **+** Provenance (Source/Cascade/Aggregate/Derived) has a first-class home; the
  cascade precedence (FM-B) and the recovery (AP-1) and the floor (AP-3) all live
  in ONE place.
- **+** The verification matrix is GENERATED, not hand-maintained — the test count
  tracks the cell count automatically.
- **−** Highest effort (Phase-3, a feature build — CRR-001; none of the primitives
  exist on origin/main). Cannot be the first thing built.
- **−** Schema-derivation (flipping schema dtype from declared to derived) is a
  one-way door (see Consequences/Reversibility).
- **−** FM-A (server non-determinism), FM-D (observer-not-gate), FM-E (un-warmed
  holders) remain leaky surfaces the contract cannot fully close (TDD §7).

### Option D — Runtime null-fill / coercion-fixup (REJECTED outright)

Patch nulls at serve time (zero-fill economics, coerce mismatched types). Rejected
because it violates G-DENOM (blanket null-fill produces fabricated economics — the
$8,775/7-row fossil class) and hides the defect rather than curing it. Documented
here so the option is on the record as considered-and-refused.

## Decision

**Adopt Option C (full declarative FieldContract SSOT) as the north-star, reached
bottom-up via a phased rollout that captures Option A's parity test as a Phase-1
quick-win.** Option A is NOT a competing alternative — it is the first step toward
Option C. The parity test built in Phase 1 (Option A's deliverable) is SUBSUMED in
Phase 3 when both schema dtype and model field-class derive from the contract
(parity becomes structural, not asserted). Option B is rejected: the model layer is
the wrong SSOT for the fetch/population/coherence axes and the wrong default for
FM-C materialization. Option D is rejected on G-DENOM grounds.

The sequencing (TDD §8): Phase 1 = Option-A parity test + drift reconcile + floor
extension (contract-independent, CR-3-safe); Phase 2 = path-canon recovery (the
571 cure, spike-gated); Phase 3 = the full Option-C contract from which all prior
fixes re-derive.

## Consequences

### Positive
- Drift becomes unrepresentable (one value_type, no second declaration).
- The 571-gun is structurally cured (Phase 2) and the cure cannot silently regress
  (the generated coherence test fires RED on regression).
- Population is contracted per-cell with G-DENOM policy; `weekly_ad_spend` and
  `discount` stay `LegitimatelySparse` (NOT floored).
- The verification matrix scales with the lattice automatically.

### Negative / costs
- Phase 3 is a feature build (3–4 weeks, CRR-001), not a refactor.
- Three leaky surfaces remain (FM-A/FM-D/FM-E) — named and bounded, not hidden.

### Reversibility (one-way vs two-way doors)
- **Phase 1 (two-way door)**: parity test is additive; drift reconciles are
  line-level; floor extension is dict-additive. Fully reversible.
- **Phase 2 (mostly two-way)**: the recovery contract is additive (fires only on
  null). Reversible by removing the recovery declaration. The 2-stage deploy is
  the operational risk, not the design.
- **Phase 3 schema-derivation (ONE-WAY DOOR)**: flipping schema dtype from
  independently-declared to contract-derived deletes the independent declaration.
  Reverting requires re-materializing the schema files. **This requires explicit
  stakeholder acknowledgment before Phase-3 implementation begins** (dataframe-layer
  owner sign-off). Flagged per one-way-door discipline.

## Open Decisions (operator-gated — NOT resolved in this ADR)

- **UK-2** (BLOCKS Phase-1 D1/D2): for `unit.discount` and `offer.cost`, which
  layer is canonical? `discount` has a PRD-0024 comment endorsing Enum; schema
  says Decimal. **Owner: PRD-0024 owner.** D3 (`asset_edit.score` → Decimal) is
  NOT blocked — direction is clear (model docstring compares `score > Decimal("90")`).
- **UK-3** (conditions AP-5): is offer↔asset_edit joined on `offer_id` at the
  DataFrame level? If yes → HIGH/blocking before that join ships; if no → LOW
  cosmetic. **Owner: query/join layer owner.**
- **UK-4** (scopes Phase-2): does the monolith read `unit.mrr` (0/3021) or
  `offer.mrr` (1325/4070)? Determines cure blast radius. **Owner: CRR-002 cross-repo.**
- **UK-5** (FM-B): vertical cascade precedence (Unit vs Business). **Owner:
  `cascading.py` traversal-order test.**
- **UK-1** (FM-C): materialize or omit the 4 model-only NumberFields. **Owner:
  dataframe-layer owner.**
- **eunomia STRONG**: this ADR self-assesses at MODERATE. STRONG ratification is
  the rite-disjoint eunomia critic — an operator lever, HELD, not run here.

## N≥2 Throughline-Promotion Note

This is the **N=2 instance** of the "identity-and-population (here: type-and-path)
contracted at the data plane" throughline. **N=1** is SEAM-1
(`ADR-seam1-entity-identity-key.md`, telos `dataframe-resolution-coherence`,
eunomia-certified receiver-side STRONG 2026-06-09 PT-05) — which contracted the
IDENTITY and POPULATION faces at the storage seam. The FPC contracts the TYPE and
PATH faces at the resolution seam. Same throughline (a contract the data plane was
missing), different face. Throughline promotion to STRONG requires: (1) the
eunomia rite-disjoint critic at design altitude (HELD), AND (2) a Phase-2 deploy
producing the `coherent ≥ 100` empirical receipt. Until both: MODERATE ceiling
holds regardless of how many internal activations accrue.
