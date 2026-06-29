---
type: spec
subtype: tdd
title: Field-Provenance-&-Population-Contract (FPC)
initiative: field-provenance-population-contract
status: draft
rung: design-ratified-pending  # NOT built / NOT live / NOT verified-realized (G-RUNG)
date: 2026-06-09
author: architect (10x-dev)
head: 50ebfe3381a627df868887ca3cdf9e223e1f9a90
evidence_grade: MODERATE  # self-ref ceiling per self-ref-evidence-grade-rule; STRONG = eunomia rite-disjoint (HELD)
impact: high  # categories: data-migration (Phase-2 fetch path), breaking-change (Phase-3 schema/model derivation)
upstream:
  - .ledge/reviews/fpc-architecture-report-2026-06-09.md
  - .ledge/reviews/fpc-architecture-assessment-2026-06-09.md
  - .ledge/reviews/ADVERSARY-REPORT-fpc-architecture-report-1.md
companions:
  - .ledge/decisions/ADR-field-provenance-population-contract-2026-06-09.md
  - .sos/wip/frames/field-provenance-population-contract.shape.md
---

# TDD — Field-Provenance-&-Population-Contract

> **Construct (the thing the design measures and seals)**: for every
> (entity, field) cell in the data-plane lattice, the field's *resolution
> contract* — its canonical source, its value type, the fetch path that
> populates it, the recovery available on a null, and the population policy that
> guarantees its presence — must be **declared once, derived everywhere, and
> verified by a generated test.** Today the contract is implicit and split
> across two unbound layers (schema files + model files), producing four defect
> faces. The FPC makes the contract EXPLICIT · ENFORCED · GENERATED-VERIFIED ·
> OBSERVED.

> **Rung (G-RUNG)**: This is a design. It is not built, not live, not
> verified-realized. The only live receipts are the diagnostic ones (§2): the
> RED 571-gun and the verified source citations at origin/main.

---

## 1. System Context & Requirements

### 1.1 The lattice under design

10 materialized schema entities × variable fields = **82 (entity, field) cells**
(57 Direct / 17 Cascade / 8 Derived; 10 number-typed). Of 82 cells, **80 have NO
population policy** — the floor dict is `{"offer": ("mrr", "offer_id")}` only.

Receipt (origin/main `50ebfe33…`,
`src/autom8_asana/dataframes/builders/post_build_population_receipt.py:54-61`):

```python
POPULATION_WARN_THRESHOLD = 0.80
# ... "Kept local to the receipt's concern (single responsibility) rather than
#      mutating the frozen schema model."
_VALUE_COLUMNS_BY_ENTITY: dict[str, tuple[str, ...]] = {
    "offer": ("mrr", "offer_id"),
}
```

The primitive is entity-generic by construction (`.get(entity_type, ())`), so the
gap is un-extended coverage, not a wrong design.

### 1.2 Functional requirements

- **FR-1 (drift impossible)**: schema dtype and model field-class for the same
  cell MUST NOT disagree. Today 3 cells drift (D1/D2/D3) + 1 cross-frame
  (`offer_id` Utf8↔Int64).
- **FR-2 (path-independent presence)**: a number cell's *presence* MUST NOT
  depend on which Asana fetch path materialized the parent frame.
- **FR-3 (population guaranteed)**: every value-bearing non-sparse cell MUST have
  a declared floor policy; a frame that publishes with a below-floor value column
  MUST be observable.
- **FR-4 (coherence)**: for every `cascade:F` cell, the consumer MUST NOT be
  non-null where the source is null (the 571-gun invariant).
- **FR-5 (single propagation point, G-PROPAGATE)**: schema dtype, model
  field-class, opt_fields, floor set, and the verification matrix MUST all derive
  from ONE `FieldContract`. No per-field orphan fixes.

### 1.3 Non-functional requirements (measurable)

| NFR | metric | target | method | environment |
|---|---|---|---|---|
| NFR-1 (CR-3 budget) | new Asana API calls per warm cycle introduced by recovery | 0 for non-null cells; ≤ (count of actually-null number rows) for null cells | count `get_async` calls in a warm trace | single uvicorn worker, SlowAPI 100/min |
| NFR-2 (coherence cure) | `coherent` count post-Phase-2 deploy | ≥ 100 office phones (from 0 today) | re-run §2 canary post-deploy | live S3 parquet |
| NFR-3 (parity completeness) | generated parity tests | 1 per (schema, model) cell pair; 0 un-covered drift-eligible cells | count generated tests vs cell count | CI |
| NFR-4 (floor observability) | population WARN fires on below-floor `ActiveSubset` cell | within 1 warm cycle | inject below-floor fixture | CI + CloudWatch |

---

## 2. G-THEATER Diagnostic Receipts (live, re-fired this pass)

A design is credible ONLY if its first generated coherence test fails RED on the
known live defect. Re-fired 2026-06-09 via DuckDB CLI v1.5.3 over the live
parquet `/tmp/u8u` (unit) + `/tmp/u8o` (offer):

```sql
WITH u AS (SELECT office_phone, max(mrr) um FROM read_parquet('/tmp/u8u/*.parquet')
           WHERE office_phone IS NOT NULL GROUP BY 1),
     o AS (SELECT office_phone, max(mrr) om FROM read_parquet('/tmp/u8o/*.parquet')
           WHERE office_phone IS NOT NULL GROUP BY 1)
SELECT count(*) total_joined,
  count(*) FILTER(WHERE o.om IS NOT NULL AND u.um IS NULL)     gun,
  count(*) FILTER(WHERE o.om IS NOT NULL AND u.um IS NOT NULL) coherent
FROM u JOIN o USING(office_phone);
```

Output (this pass):

```
┌──────────────┬─────┬──────────┐
│ total_joined │ gun │ coherent │
├──────────────┼─────┼──────────┤
│ 2001         │ 571 │ 0        │
└──────────────┴─────┴──────────┘
```

mrr population census (this pass): `unit.mrr` **0/3021**, `offer.mrr` **1325/4070**.

**RED confirmed: gun=571, coherent=0.** Every joined phone where offer reports
MRR has unit.mrr NULL. The cascade reads the ancestor correctly; the ancestor is
empty (AP-1 root cause, not AP-2 — the mrr mixin types are aligned).

**CH-01 disposition (adversary BLOCKING, now CLEARED).** The keystone "zero
number-recovery path" rests on a negative grep. The broad grep is contaminated:

```
$ git grep -nE 'recover|repair_null|refetch_via_get|number.*fallback' origin/main -- 'src/autom8_asana/dataframes/**'
src/autom8_asana/dataframes/storage.py:284:  recovery_timeout=60.0,
storage.py:313,546,547,614,615  (circuit-breaker recovery prose)   → 6 hits
```

The correctly-scoped grep is genuinely EMPTY (re-fired this pass):

```
$ git grep -nE 'repair_null|refetch_via_get|number_value.*(recover|refetch|fallback)|display_value.*fallback|fallback.*display_value' origin/main -- 'src/autom8_asana/dataframes/**'
  (no matches)
```

The 6 hits are circuit-breaker `recovery_timeout`/HALF_OPEN, unrelated to number
cells. The keystone HOLDS: `cf_utils.py:46-50` number-branch returns
`number_value` bare with no fallback; no GET-path backstop exists in
`dataframes/`. **The recovery contract is a feature build, not the re-wiring of
an existing path.**

---

## 3. The FieldContract — Single Source of Truth (the SSOT dataclass)

```python
from dataclasses import dataclass, field as dc_field
from decimal import Decimal
from enum import Enum

class Provenance(Enum):
    SOURCE    = "source"     # Direct cf: extraction; value originates here
    CASCADE   = "cascade"    # propagated from an ancestor SOURCE via join key
    AGGREGATE = "aggregate"  # rolled up from child records (HOLDER frames)
    DERIVED   = "derived"    # computed; no Asana extraction
    BASE      = "base"       # base task attribute (gid, name, ...)

class FetchRequirement(Enum):
    LIST_OK              = "list_ok"               # list path is sufficient
    NEEDS_GET            = "needs_get"             # must be fetched via per-task GET
    MAY_NEED_GET_RECOVERY = "may_need_get_recovery" # list-first; GET backstop on null

class PopulationPolicy(Enum):
    TOTAL              = "total"               # present for every warm record
    ACTIVE_SUBSET      = "active_subset"       # present for the active business subset
    LEGITIMATELY_SPARSE = "legitimately_sparse" # intentionally null for many; no floor

@dataclass(frozen=True)
class ResolutionMode:
    provenance: Provenance
    cascade_source_field: str | None = None   # for CASCADE: the ancestor field
    cascade_precedence: tuple[str, ...] = ()  # ordered ancestor entity types (FM-B)
    derived_fn: str | None = None             # for DERIVED: the function name

@dataclass(frozen=True)
class RecoveryStrategy:
    kind: str                       # "null_get_retry"
    opt_fields: tuple[str, ...]     # e.g. ("custom_fields.gid","custom_fields.number_value")
    cache_reuse: bool = True        # MUST be True for CR-3 safety (no new fan-out)

@dataclass(frozen=True)
class FieldContract:
    # --- identity ---
    entity: str                     # e.g. "unit"
    name: str                       # column name, e.g. "mrr"
    # --- the canonical declaration (the SSOT axis) ---
    value_type: type                # Decimal | str | int | bool | float | Enum-subclass
    canonical_source: str           # "cf:MRR" | "cascade:MRR" | "derived:fn" | "base:gid"
    resolution: dict[str, ResolutionMode]   # per-entity resolution (usually 1 key = entity)
    # --- the fetch/recovery axis (seals AP-1/AP-4) ---
    fetch_requirement: FetchRequirement
    recovery: tuple[RecoveryStrategy, ...] = ()
    # --- the population axis (seals AP-3) ---
    population_policy: PopulationPolicy = PopulationPolicy.LEGITIMATELY_SPARSE
    active_subset_floor: int | None = None   # for ACTIVE_SUBSET: the threshold (e.g. offer.mrr=62)
    # --- coherence axis (seals FR-4) ---
    coherence_consumers: tuple[str, ...] = () # cells that cascade FROM this one; generates 571-class tests
```

### 3.1 Worked instances (the corpus anchors)

```python
UNIT_MRR = FieldContract(
    entity="unit", name="mrr", value_type=Decimal,
    canonical_source="cf:MRR",
    resolution={"unit": ResolutionMode(Provenance.SOURCE)},
    fetch_requirement=FetchRequirement.MAY_NEED_GET_RECOVERY,   # the AP-1 cure, declared ONCE
    recovery=(RecoveryStrategy("null_get_retry",
              ("custom_fields.gid","custom_fields.number_value"), cache_reuse=True),),
    population_policy=PopulationPolicy.ACTIVE_SUBSET, active_subset_floor=62,
    coherence_consumers=("offer.mrr",),   # GENERATES the 571-gun coherence test
)

OFFER_MRR = FieldContract(
    entity="offer", name="mrr", value_type=Decimal,
    canonical_source="cascade:MRR",
    resolution={"offer": ResolutionMode(Provenance.CASCADE, cascade_source_field="unit.mrr",
                                        cascade_precedence=("unit",))},
    fetch_requirement=FetchRequirement.LIST_OK,   # inherits source's recovery via ancestor
    population_policy=PopulationPolicy.ACTIVE_SUBSET, active_subset_floor=62,  # inherits source floor
)

# G-DENOM: these are LegitimatelySparse — do NOT floor them
UNIT_WEEKLY_AD_SPEND = FieldContract(
    entity="unit", name="weekly_ad_spend", value_type=Decimal,
    canonical_source="cf:Weekly Ad Spend",
    resolution={"unit": ResolutionMode(Provenance.SOURCE)},
    fetch_requirement=FetchRequirement.MAY_NEED_GET_RECOVERY,
    recovery=(RecoveryStrategy("null_get_retry",
              ("custom_fields.gid","custom_fields.number_value")),),
    population_policy=PopulationPolicy.LEGITIMATELY_SPARSE,   # NOT floored per G-DENOM
)
```

---

## 4. The Derivation Model — what derives from the ONE contract (G-PROPAGATE)

The contract is the **sole** propagation point. Every downstream artifact is
generated or derived; nothing is independently declared. This is what makes
schema/model drift impossible *by construction*.

```
                         ┌──────────────────────┐
                         │    FieldContract      │  ← THE SINGLE WRITE POINT
                         │  (entity, name, ...)  │
                         └──────────┬───────────┘
            ┌───────────────┬───────┼────────┬──────────────┬───────────────┐
            ▼               ▼       ▼        ▼              ▼               ▼
     schema ColumnDef   model     opt_fields  _VALUE_       coherence    population/
       (.dtype)       field-class   set      COLUMNS_      test (571)    parity test
                                            BY_ENTITY      generated     generated
```

| derived artifact | derivation rule | seals |
|---|---|---|
| schema `ColumnDef(dtype=…)` | `dtype = DTYPE_MAP[value_type]` (Decimal→"Decimal", int→"Int64", str→"Utf8", float→"Float64", bool→"Boolean") | AP-2 |
| model field-class | `field_class = FIELDCLASS_MAP[(value_type, resolution.provenance)]` (Decimal+SOURCE→NumberField; Enum-subclass→EnumField; int→`_get_int_field`) | AP-2 |
| `opt_fields` set | union over contracts of `OPT_FIELDS_FOR[fetch_requirement]` + cascade-source opt_fields | AP-1 (symmetric by construction) |
| `_VALUE_COLUMNS_BY_ENTITY` | `{e: tuple(c.name for c in contracts[e] if c.population_policy != LEGITIMATELY_SPARSE)}` | AP-3 |
| coherence test | for each contract with `coherence_consumers`, emit the `NOT (consumer NOT NULL AND source NULL)` assertion | FR-4 / 571 |
| parity test | for each contract, assert `schema.dtype == DTYPE_MAP[value_type]` AND `model.field_class == FIELDCLASS_MAP[...]` | AP-2 |
| population test | for each `ACTIVE_SUBSET` contract, assert `nonnull_count / active_count ≥ floor-ratio` | AP-3 |

**Key invariant**: there is exactly ONE write point per cell. Editing the
contract changes all derivations atomically; there is no second file to keep in
sync. The drift class (D1/D2/D3) becomes unrepresentable — you cannot declare a
schema dtype that disagrees with the model field-class because neither is
independently declared.

### 4.1 The generated verification matrix

From the corpus of contracts, the generator emits (NFR-3):

- **N coherence tests** = count of contracts with non-empty `coherence_consumers`
  (currently: `unit.mrr`→`offer.mrr`, `unit.weekly_ad_spend`→`offer.weekly_ad_spend`,
  and `*.vertical` once FM-B precedence is confirmed).
- **N parity tests** = count of (schema, model) cell pairs (one per Direct/Cascade
  cell — currently 82 minus Derived/base).
- **N population tests** = count of `ACTIVE_SUBSET` contracts.

**G-THEATER mandate for the generated matrix**: each generated test class MUST be
proven by a broken-fixture-RED, never green-run-alone. The parity generator is
proven by mutating a contract's `value_type` to a wrong type and observing the
generated parity test fire RED (synthetic drift cell). The coherence generator is
proven by the live 571-gun (§2). The population generator is proven by injecting
a below-floor `ActiveSubset` fixture and observing WARN.

---

## 5. The Path-Canonicalization Mechanism (the spike target — riskiest pillar)

### 5.1 The mechanism (cache-reuse, ZERO new API calls)

The defect: section-LIST path (`builders/parallel_fetch.py:576-578`
`list_async(section, opt_fields=…)`) returns cf dicts whose `number_value` is
dropped server-side; the per-task-GET path (`hierarchy_warmer.py:93`
`get_async(gid, opt_fields=_HIERARCHY_OPT_FIELDS)`) carries it. opt_fields are
ALREADY symmetric (`fields.py:69` ∧ `hierarchy_warmer.py:43` both request
`custom_fields.number_value`) — so this is server-side, not an opt_fields omission.

**Maximal-completeness Source materialization via cache-reuse**: the hierarchy
warmer ALREADY performs a per-task GET for cascade-ancestor resolution. That GET
copy carries `number_value`. The recovery contract reuses THAT cached copy as the
null-recovery backstop for the list-path frame — it does NOT issue a fresh GET.

```
for each row in unit LIST frame:
    for each number ColumnDef where row[col] IS NULL:
        cached_get = hierarchy_warm_cache.get(row.task_gid)   # ALREADY fetched
        if cached_get is not None:
            row[col] = extract_cf_value(cached_get.custom_fields[col.source])  # reuse, no API call
        # else: row stays null; recovery declared but cache miss → still null (honest)
```

### 5.2 The rejected design (contrast — explicit per G-PROVE)

**REJECTED: per-row N+1 GET fan-out.** A naive recovery would issue
`get_async(task_gid, …)` for every null row at build time. This is a per-task-GET-
per-row fan-out that would REGRESS CR-3: the receiver is single uvicorn worker +
SlowAPI 100/min with no SA exemption; a bulk null-recovery fan-out over 3021 unit
rows would blow the rate limit and the single-worker budget. The CR-3 receiver
substrate was stabilized precisely to avoid this fan-out (per memory: receiver
bulk-fanout reliability). **The spike MUST prove cache-reuse (the cached GET copy
already exists), NOT N+1 GETs.** If the spike finds the hierarchy-warm cache does
NOT carry the number_value for the null rows (cache miss for non-ancestor units),
the mechanism degrades to "declared recovery, cache-miss → honest null" — it does
NOT silently fall back to N+1.

### 5.3 Spike acceptance (N≥2 proof, CR-3-safe)

1. **N=1**: on a unit frame with ≥ 1 null `mrr` row whose task IS in the
   hierarchy-warm cache, the recovery populates `mrr` from the cached GET copy
   with ZERO new `get_async` calls (instrument the call count).
2. **N=2**: the coherence canary, re-run after a cache-reuse recovery pass over
   the live corpus, shows `coherent > 0` (the 571 begins to fall) with new API
   calls = 0.
- **CR-3-safe gate**: assert `get_async` call delta = 0 for the recovery pass.
  If non-zero, the spike FAILS — the mechanism is N+1, not cache-reuse.

---

## 6. Registry & Loader

```python
class FieldContractRegistry:
    def __init__(self) -> None:
        self._by_cell: dict[tuple[str, str], FieldContract] = {}
    def register(self, c: FieldContract) -> None:
        key = (c.entity, c.name)
        if key in self._by_cell:
            raise ValueError(f"duplicate contract {key}")  # one write point invariant
        self._by_cell[key] = c
    def for_entity(self, entity: str) -> list[FieldContract]: ...
    def derive_schema(self, entity: str) -> list["ColumnDef"]: ...   # §4 derivation
    def derive_value_columns(self) -> dict[str, tuple[str, ...]]: ...
    def generate_tests(self) -> "VerificationMatrix": ...            # §4.1
```

Contracts are authored in one module per entity (`contracts/unit.py`, …) and
registered at import. The schema files and model files become DERIVED (Phase-3)
or, transitionally (Phase-1), asserted-consistent-with the contract by the
generated parity test (the contract exists; schema/model are checked against it,
not yet generated from it). This is the bottom-up rollout (§8).

---

## 7. Pressure-Test the North-Star — FM-A..FM-E Dispositioned (G-RUNG, not endorsement)

The design is leaky in five named places. Honesty about leakiness is the design's
credibility, not its weakness.

### FM-A — Asana server non-determinism is not contractable. [LEAKY — MITIGATION not GUARANTEE]
The path-asymmetry is server-side (opt_fields symmetric). `fetch_requirement` can
declare a number cell needs GET recovery, but if the Asana server returns
different values for the *same task + same opt_fields* across calls (temporal
non-determinism, not just list-vs-get), the contract cannot enforce consistency.
**Disposition**: the FPC assumes same-task+same-opt_fields determinism. The
recovery is a MITIGATION (recover the list-drop from the GET copy), explicitly NOT
a guarantee against temporal server drift. The TDD states this assumption; it is
NOT silently buried. Spike §5.3 instruments the cached GET copy; if the cached
value itself is non-deterministic across warm cycles, that is an out-of-scope
Asana-platform root cause (report §8).

### FM-B — Cascade dual-source precedence is unspecified. [LEAKY — DESIGN-COMPLETION REQUIRED]
`cascade:Vertical` resolves "from Unit OR Business ancestor" with first-ancestor-
wins implied. Verified: `cascading.py:199+` is "traverse parent chain until field
found, max_depth=5" — first-found-wins by traversal order, but the ORDER for a
dual-key (Unit AND Business both carry Vertical) is not specified in code.
**Disposition**: the `ResolutionMode.cascade_precedence: tuple[str,...]` field
EXISTS in the dataclass precisely to encode this (e.g. `("unit","business")`).
Until UK-5 confirms the live traversal order, the `cascade:Vertical` coherence
test CANNOT be generated (it would assume a precedence that may be wrong). The
contract schema is precedence-aware; the DATA (which precedence) is operator-gated.
The mrr coherence test is single-source and ships first; vertical waits on UK-5.

### FM-C — Model-only NumberFields are invisible to a schema-derived registry. [LEAKY — COVERAGE BOUND]
Verified at origin/main: `unit.meta_spend`, `unit.tiktok_spend`
(`models/business/unit.py:119,121`), `offer.voucher_value`,
`offer.budget_allocation` (`models/business/offer.py:137-138`) are `NumberField()`
in models with NO schema `ColumnDef`. A registry seeded FROM schema files cannot
see them.
**Disposition**: the FPC is only as complete as its registry coverage. The Phase-3
generator MUST seed from BOTH schema files AND model field-class introspection,
emitting a **coverage-gap test**: any model `NumberField` with no `FieldContract`
fires RED. This converts FM-C from a silent gap into a loud one. Until then (UK-1),
these 4 cells are flagged for pre-registration; if materialized without a contract
they inherit AP-1 (no backstop) + AP-3 (no floor) — the coverage-gap test is the
seal.

### FM-D — The population floor is a post-build receipt, NOT a pre-publish gate. [LEAKY — BY PHILOSOPHY]
`post_build_population_receipt.py` fires AFTER the frame is built. If the frame is
S3-published before/independent of the floor check, a null-economic frame is live.
**Disposition**: this is the availability-first philosophy operating as designed
(`LKG_MAX_STALENESS_MULTIPLIER=0.0`, serve-stale — per memory). The system WILL
serve the null rather than refuse. The FPC observatory is therefore an OBSERVER
(emit a WARN/metric), explicitly NOT a publish GATE. Making it a pre-publish gate
is an AP-4-class build-path wiring change with its own availability trade-off
(refusing to serve a partially-null frame) — that is a SEPARATE design decision
the FPC does NOT smuggle in. The TDD names the observer-not-gate boundary; the ADR
records it as a deliberate consequence, not an oversight.

### FM-E — Holder frames (5 un-warmed entities) are outside the live coherence surface. [LEAKY — SEQUENCING]
`offer_holder`, `unit_holder`, `contact_holder`, `location`, `hours` have S3
census = 0. The contract can declare their cells, but the observatory cannot
observe them until warmed. `offer_holder` AGGREGATES `offer.mrr`.
**Disposition**: warming `offer_holder` BEFORE the Phase-2 mrr cure would aggregate
nulls into holders — a blast-radius extension. **Sequencing rule**: holder warming
is gated on Phase-2 completion (mrr cured before aggregating into holders). The
`Provenance.AGGREGATE` mode + the population test on the holder cell make a
"holder aggregating nulls" condition observable once warming begins.

---

## 8. Migration / Rollout (bottom-up: quick-wins → path-canon → contract-derives-all)

The full SSOT (Phase-3) is the north-star. Building it FIRST is a long-term
transformation before the quick-wins are captured. Correct sequence:

1. **Phase 1 (contract-independent quick-wins)**: reconcile D1/D2/D3 at the line
   level (UK-2 gates D1/D2 direction; D3 = schema→Decimal, direction clear);
   extend `_VALUE_COLUMNS_BY_ENTITY` with G-DENOM per-cell policy; add the
   generated parity test as a standalone fitness function (it reads schema + model
   and asserts agreement — it does NOT yet require the full contract). The parity
   test fires RED on D1/D2/D3 BEFORE the fixes (broken-fixture-RED), GREEN after.
   No fetch-path change. CR-3-safe.
2. **Phase 2 (path-canon recovery)**: the `fetch_requirement="may_need_get_recovery"`
   + cache-reuse backstop (§5), wired through the single warmer read-point. Moves
   `coherent` off 0. Spike-gated (N≥2, CR-3-safe). 2-stage durable-first deploy.
3. **Phase 3 (contract-derives-all)**: introduce the `FieldContract` dataclass +
   registry + generators; flip schema dtype + model field-class + opt_fields +
   floor set from independently-declared to DERIVED. The Phase-1 parity test is
   then SUBSUMED (parity is structural — both sides derive from one source).
   Add the coverage-gap test (FM-C) and the coherence observatory (FM-E-aware
   sequencing). This is CRR-001 (a feature build, not a refactor — none of these
   primitives exist on origin/main).

Each phase delivers value independently; no phase requires a later phase to be
non-regressive. Phase 1 + 2 are reversible (line-level reconciles, additive
recovery); Phase 3 schema-derivation is a one-way door (see ADR §Reversibility).

---

## 9. Error Handling, Security, Performance

- **Error handling**: a recovery cache-miss yields an HONEST null (the value
  stays null, the population test fires WARN), never a fabricated/zero-filled
  value (G-DENOM: never blanket null-fill).
- **Security**: no auth/crypto/PII boundary is touched by field-resolution
  (assessment §8 confirms). No threat-modeler consult required for the contract
  design itself. Phase-2 fetch-path changes touch the Asana API integration
  surface — if Phase-2 implementation adds new outbound call patterns, that
  implementation crosses the FEATURE×external-integration gate and is the
  security-gate invocation point at IMPLEMENTATION time, not design time.
- **Performance**: NFR-1 (zero new API calls for non-null cells) is the binding
  constraint. The recovery is O(null-rows), not O(total-rows).

---

## 10. Open Decisions (operator-gated — surfaced, NOT resolved)

| id | decision | owner | blocks |
|---|---|---|---|
| UK-2 | discount/cost canonical direction (schema vs model) | PRD-0024 owner | Phase-1 D1/D2 |
| UK-3 | is offer↔asset_edit joined on offer_id at DataFrame level? | query/join owner | AP-5 severity |
| UK-4 | monolith reads unit.mrr vs offer.mrr | CRR-002 cross-repo | Phase-2 blast radius |
| UK-5 | vertical cascade precedence (Unit vs Business) | cascading.py test | FM-B coherence test |
| UK-1 | model-only NumberFields: materialize or omit | dataframe-layer owner | FM-C coverage |
| — | eunomia STRONG critique of THIS design | operator | MODERATE→STRONG rung |
