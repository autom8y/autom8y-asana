---
type: review
status: draft
role: remediation-planner
depth: DEEP-DIVE
upstream:
  - fpc-topology-inventory-2026-06-09.md
  - fpc-dependency-map-2026-06-09.md
  - fpc-architecture-assessment-2026-06-09.md
date: 2026-06-09
head: 50ebfe3381a627df868887ca3cdf9e223e1f9a90
rung: MAPPED+ranked
---

# FPC Architecture Report — Opportunity Matrix + Phased Roadmap

> **Rung (G-RUNG)**: MAPPED + ranked. This report maps the opportunity matrix and
> ranks remediations by leverage. It does NOT claim designed/built/live/verified-realized.
> No src/ edits. No consumer rebinds. No fixes land here.
>
> **G-THEATER receipt (mandatory — RE-RUN this pass)**:
> Coherence invariant `offer.mrr[phone] == unit.mrr[phone]` fires **RED = 571**.
> Full DuckDB output pasted in §3.
>
> **HEAD**: `origin/main = 50ebfe3381a627df868887ca3cdf9e223e1f9a90`
> (benign #113 telemetry bump; dataframes corpus unchanged from e686ba06).

---

## Executive Summary

The autom8y-asana data plane exposes an 82-cell (entity, field) lattice across 10
materialized schema entities. Three structural contracts are absent from the current
architecture: a type contract binding schema dtype to model field-class, a population
contract guaranteeing value-bearing cells are non-null before a frame is published, and
a fetch-path contract ensuring number-valued custom fields resolve consistently
regardless of which Asana API path materialized the parent frame.

The consequence is measurable and live. 571 business phone numbers have
`offer.mrr` present but `unit.mrr` NULL — the canonical source of the cascade is
zero-populated (0 out of 3,021 non-null) while the downstream consumer is 32%
populated (1,325 out of 4,070 non-null). The coherence invariant fires RED on every
single phone in the joined corpus where offer reports an MRR value: coherent = 0.
This is not a latent risk. It is a live defect in production economics data.

SEAM-1 closed one of four defect faces (FM-2: `status` cells with `source=None`).
The remaining three faces — path-dependent number resolution (FM-1), schema/model
type-drift (FM-3), and presence-not-equal-population (FM-4) — are open across the
corpus with no repair mechanism.

The five FPC pillars, ranked by leverage, offer a sequenced path from the current
state to a structurally sound data plane: (1) declarative FieldContract as the single
source of truth, (2) schema/model drift eradication via generated parity checks,
(3) population-floor extension to all value-bearing cells, (4) path-canonicalization
for number cells, and (5) a per-field coherence observatory. The first three pillars
are quick-wins or strategic investments with leverage >= 2.5. Pillars 4 and 5 are
necessary long-term completions that cannot be decomposed into higher-leverage steps
because they require cross-cutting infrastructure changes.

---

## 1. Provenance Corrections (Inherited from Structure-Evaluator)

One path-citation drift in the upstream artifacts must be carried forward into all
recommendations. Every reference to `entity_registry.py` throughout the topology and
dependency artifacts uses a wrong path prefix. The correct path is:

**`src/autom8_asana/core/entity_registry.py`** (not `dataframes/entity_registry.py`)

All file:line citations in this report use the corrected path. The line numbers cited
by upstream artifacts are accurate once the prefix is corrected. This does not
invalidate any upstream findings.

---

## 2. The Opportunity Matrix — Five FPC Pillars Ranked by Leverage

Leverage formula: `leverage = impact / effort` (1–5 scales).
Quick win: leverage >= 3.0. Strategic investment: leverage 1.0–3.0 with impact >= 4.
Long-term transformation: leverage < 1.5 but structurally necessary.

Leverage scores are inherited from `fpc-architecture-assessment-2026-06-09.md §6`
(structure-evaluator produced them; they are not re-derived here).

### Pillar Rankings

| rank | pillar | maps to | impact | effort | leverage | class | confidence |
|---|---|---|---|---|---|---|---|
| **1** | Schema/model drift eradication (FPC Pillar: generated verification matrix — type-parity subset) | AP-2 (D1/D2/D3) | 4 | 1 | **4.0** | QUICK WIN | HIGH |
| **2** | Cross-frame shared-contract alignment (offer_id Utf8↔Int64) | AP-5 | 3 | 1 | **3.0** | QUICK WIN (conditional UK-3) | MEDIUM |
| **3** | Population-floor extension (FPC Pillar: population/coherence observatory — floor subset) | AP-3 | 5 | 2 | **2.5** | STRATEGIC | HIGH |
| **3** | Path-dependent number recovery (FPC Pillars: path-canonicalization + declarative FieldContract) | AP-1 + AP-4 | 5 | 2 | **2.5** | STRATEGIC | HIGH |
| **5** | Single-fetch-path SPOF elimination (FPC Pillar: path-canonicalization — full) | AP-4 isolated | 5 | 4 | **1.25** | LONG-TERM | HIGH |

Pillars 1 and 2 are the top leverage moves. They are low-effort, scoped, and address
cells with confirmed type-contract failures. Pillars 3 and 4 tie at 2.5 because
extending the population floor (effort=2) and adding a number-cell recovery contract
(effort=2) are comparably scoped. Pillar 5 is the complete SPOF elimination — it
subsumes Pillar 4 but requires CR-3-budget-aware warm-path wiring, pushing effort to 4.

### Per-Anti-Pattern Disposition

Every finding from the architecture assessment appears below. No finding is silently
dropped.

**AP-1 (Path-Dependent Resolution) — RECOMMEND: recovery contract on number cells.**
The 10 path-dependent cells need a targeted null-recovery path: when the LIST frame
yields a null for a Number custom field, a GET-path refetch populates it. This is the
unit-MRR cure. Acceptance of the list-first efficiency design (AP-4 note) is preserved
— the recovery fires only on null, not on every task. Impact 5 / Effort 2 = Leverage 2.5.

**AP-2 (Schema/Model Type-Drift) — RECOMMEND: reconcile 3 drift cells + add generated
parity test.** D1 (`unit.discount` Decimal/Enum), D2 (`offer.cost` Utf8/Number), D3
(`asset_edit.score` Float64/Decimal). Each is a line-level fix once the canonical
direction is determined (UK-2 for D1/D2). D3 direction is clear: Float64 schema vs
Decimal model means precision drift; Decimal is more precise. The generated parity test
is the structural seal — once the FPC FieldContract exists it derives both schema dtype
and model field-class from one source, making future drift impossible by construction.
Impact 4 / Effort 1 = Leverage 4.0.

**AP-3 (Presence != Population) — RECOMMEND: extend population floor to 8+ unguarded
number cells and critical identity keys.** The existing `_VALUE_COLUMNS_BY_ENTITY` dict
at `src/autom8_asana/dataframes/builders/post_build_population_receipt.py:60-61` is
entity-generic by construction. Adding `unit: ("mrr", "weekly_ad_spend")` and the
remaining economics cells closes the gap. Per G-DENOM: each cell needs a policy of
`ActiveSubset`, `Total`, or `LegitimatelySparse` — not blanket null-fill. Impact 5 /
Effort 2 = Leverage 2.5.

**AP-4 (Single-Fetch-Path SPOF) — RECOMMEND: accept as structural constraint for the
near term, address via path-canonicalization in Phase 2.** The list-first design is an
accepted CR-3 API-budget trade-off. The SPOF cannot be eliminated without a targeted
null-recovery contract (AP-1 cure) plus warm-path wiring. Phase 2 work. Impact 5 /
Effort 4 = Leverage 1.25. This is the one finding that is ACCEPT-FOR-NOW with a
Phase-2 gate, not accept-as-is permanently.

**AP-5 (Cross-Frame Shared-Contract Divergence, offer_id Utf8↔Int64) — RECOMMEND:
normalize to a single dtype, contingent on UK-3 resolution.** If offer↔asset_edit is
never joined on offer_id at the DataFrame level (UK-3 confirms benign), a cosmetic
schema alignment suffices. If a DataFrame-level join exists or is planned, this becomes
HIGH severity and must be resolved before that join ships. Conditional quick win.
Impact 3 / Effort 1 = Leverage 3.0 (MEDIUM confidence pending UK-3).

---

## 3. Coherence-Invariant Spec + G-THEATER Demo (MANDATORY)

### 3.1 Invariant Specification

The cross-entity coherence invariant for waterfall fields is:

> For every field F where entity B carries `source="cascade:F"` from entity A (i.e., B.F
> cascades from A.F), and both A and B are warmed with at least one record keyed on the
> same join key K: `B.F[K] must not be non-null when A.F[K] is null`.
>
> Formally: `NOT (B.F IS NOT NULL AND A.F IS NULL)` for each join-key value K present
> in both frames.

For the mrr waterfall specifically:

> `offer.mrr[office_phone] IS NOT NULL` IMPLIES `unit.mrr[office_phone] IS NOT NULL`
>
> Equivalently: `count(*) WHERE offer.mrr IS NOT NULL AND unit.mrr IS NULL = 0`

Any non-zero count is a RED (coherence violation). A zero count is GREEN (coherent).

This invariant must hold for every `cascade:X` field, not just mrr. The mrr invariant
is the first instantiation because it has a live RED with a known root cause. The
generalization covers `cascade:Weekly Ad Spend` (offer.weekly_ad_spend ← unit.weekly_ad_spend,
currently untested) and `cascade:Vertical` (once source-precedence U-3/UK-5 is confirmed).

### 3.2 G-THEATER Demo — RED on the 571-gun (re-run this pass)

```sql
WITH u AS (
  SELECT office_phone, max(mrr) um
  FROM read_parquet('/tmp/u8u/*.parquet')
  WHERE office_phone IS NOT NULL
  GROUP BY 1
),
o AS (
  SELECT office_phone, max(mrr) om
  FROM read_parquet('/tmp/u8o/*.parquet')
  WHERE office_phone IS NOT NULL
  GROUP BY 1
)
SELECT
  count(*) total_joined,
  count(*) FILTER(WHERE o.om IS NOT NULL AND u.um IS NULL) gun,
  count(*) FILTER(WHERE o.om IS NOT NULL AND u.um IS NOT NULL) coherent
FROM u JOIN o USING(office_phone);
```

**Live output (re-run 2026-06-09, this pass):**

```
┌──────────────┬───────┬──────────┐
│ total_joined │  gun  │ coherent │
│    int64     │ int64 │  int64   │
├──────────────┼───────┼──────────┤
│         2001 │   571 │        0 │
└──────────────┴───────┴──────────┘
```

**RED confirmed: gun = 571. coherent = 0.**

Every phone in the joined corpus where offer reports an MRR value has unit.mrr NULL.
There is not a single coherent phone pair. The invariant fires maximally RED.

### 3.3 GREEN Demo — Synthetic Coherent Pair Passes

```sql
WITH u AS (SELECT '555-TEST' AS office_phone, 5000.00 AS um),
     o AS (SELECT '555-TEST' AS office_phone, 5000.00 AS om)
SELECT
  count(*) FILTER(WHERE o.om IS NOT NULL AND u.um IS NULL) gun_on_coherent_pair,
  count(*) FILTER(WHERE o.om IS NOT NULL AND u.um IS NOT NULL AND o.om = u.um) coherent_pass
FROM u JOIN o USING(office_phone);
```

**Live output (re-run 2026-06-09, this pass):**

```
┌──────────────────────┬───────────────┐
│ gun_on_coherent_pair │ coherent_pass │
│        int64         │     int64     │
├──────────────────────┼───────────────┤
│                    0 │             1 │
└──────────────────────┴───────────────┘
```

**GREEN confirmed: gun = 0, coherent = 1.** The invariant passes on a phone where both
offer.mrr and unit.mrr carry the same value (5,000.00). The invariant correctly
distinguishes coherent from incoherent pairs.

### 3.4 Why coherent = 0 Matters

The dependency-map (§3, rank 3) describes unit.mrr as the "highest economic blast
radius" coupling hotspot. The canary confirms this is not a partial failure: there is
no phone in the current corpus where unit.mrr is populated and offer.mrr agrees. The
unit frame's mrr column is 0/3,021 non-null (topology §3.2). The cascade mechanism
correctly reads from the ancestor; the ancestor is empty. This confirms AP-1 (fetch
path drops number_value at the LIST path for unit) is the root cause, not AP-2 (type
drift) — the mixin type alignment was verified as correct (Decimal ↔ NumberField).

---

## 4. Phased Remediation Roadmap

### Sequencing argument: why Pillar ordering matters

The FPC vision is a single `FieldContract` per (entity, field) that is the sole
propagation point for schema dtype, model field-class, opt_fields, recovery[], and
population-floor policy. This is a Phase 3 north-star. Attempting to build it first
is a long-term transformation (effort=5) before the quick-wins are captured.

The correct sequence is: capture the quick-wins (schema/model drift fixes) in Phase 1
with no structural dependency on the full FPC; extend the population floor in Phase 1
with no structural dependency; then in Phase 2 build the path-canonicalization
recovery contract (the unit-MRR cure) which requires fetch-path infrastructure; then
in Phase 3 build the declarative FieldContract from which all prior fixes derive,
plus the coherence observatory. This bottom-up sequence means Phase 1 delivers
measurable value (drift closed, floor extended, some unit-MRR cells cure-able) while
Phase 3 delivers the north-star structural seal.

**Phase 1 entry criterion**: all three prior phase artifacts confirmed at origin/main;
UK-2 (discount/cost canonical direction) resolved by PRD-0024 owner.
**Phase 1 exit criterion**: D1/D2/D3 drift cells reconciled (file:line receipts);
population floor extended to >= 8 number cells (dict extended with receipts);
offer_id dtype normalized (UK-3 confirmed benign or fix landed); coherent pair count
> 0 for any newly cured cell.

### Phase 1 — Quick Wins + Floor Extension (QUICK WIN, leverage >= 2.5)

**Scope**: AP-2 (3 drift cells), AP-5 (offer_id conditional), AP-3 (floor extension
to 8+ number cells). No fetch-path infrastructure changes. No new API calls.
CR-3 safe.

**Actions (ordered by leverage):**

1. **Reconcile D1 (`unit.discount`)**: pending UK-2 resolution — if PRD-0024 endorses
   Enum as canonical, change `schemas/unit.py:38-41` dtype from Decimal to Utf8 (or
   remove from numeric FPC scope). If schema is canonical, change
   `models/business/unit.py:118` from EnumField to NumberField.

2. **Reconcile D2 (`offer.cost`)**: `schemas/offer.py` declares `dtype="Utf8"` for a
   Number field. If downstream consumers expect text, the schema is correct but the
   comment "Number field" is misleading. If numeric is needed, change schema to Decimal.
   Pending UK-2.

3. **Reconcile D3 (`asset_edit.score`)**: `schemas/asset_edit.py:147-151` declares
   Float64; `models/business/asset_edit.py:192-194` returns Decimal. Change schema to
   Decimal (more precise; model is already correct; the docstring at `asset_edit.py:58`
   compares `score > Decimal("90")` confirming Decimal is the intended type).

4. **Add generated parity test** (the structural seal): a pytest fixture that imports
   every schema file and every model class, extracts the dtype and field-class for each
   ColumnDef, and asserts they agree. This test fails immediately on D1/D2/D3 (before
   the fixes), then passes after. It is the fitness function that prevents future drift
   [AQ:SRC-008 Ford et al. 2017] [MODERATE].

5. **Extend `_VALUE_COLUMNS_BY_ENTITY`** at
   `src/autom8_asana/dataframes/builders/post_build_population_receipt.py:60-61`:
   add `"unit": ("mrr", "weekly_ad_spend")` at minimum. Add `"asset_edit": ("offer_id",)`
   if offer_id is confirmed as a required key. Per G-DENOM: policy for each must be
   declared as `ActiveSubset` (assert > 0 for the active warm population) not
   `Total` (which would fire on legitimately sparse entities).

6. **Normalize offer_id dtype** (conditional UK-3): if no DataFrame-level
   offer↔asset_edit join exists or is planned, align `schemas/offer.py:42-45` to
   Int64 (matching asset_edit's more precise declaration). If a join is planned,
   this is blocking-HIGH and must be resolved before the join ships.

**Phase 1 deliverable**: zero drift cells, floor extended, parity test green. The
571-gun is NOT cured in Phase 1 (that requires AP-1 fetch-path work in Phase 2).

### Phase 2 — Path-Canonicalization + Recovery Contract (STRATEGIC, leverage 2.5)

**Entry criterion**: Phase 1 complete; UK-4 (monolith consumer path) resolved by
cross-rite referral; CR-3 soak confirmed stable; single-worker constraint understood
(from memory: single uvicorn worker + SlowAPI rate limit; the recovery contract must
not add bulk GET calls that push past the rate limit).

**Scope**: AP-1 + AP-4 (the unit-MRR cure and its generalization to all 8 backstop-less
number cells). This is the fix that moves `coherent` from 0 to non-zero.

**The unit-MRR cure:**
The root cause confirmed by the canary: unit builds its frame on the LIST path
(`builders/parallel_fetch.py:576-578`) which drops `number_value` for MRR on the
server side. The cascade resolver reads the ancestor via the GET path
(`hierarchy_warmer.py:93`) which succeeds sometimes (hence offer.mrr 1325/4070) but
the unit frame itself is 0/3,021.

The recovery contract is: after `_fetch_section` builds the unit frame, for any row
where a number-typed ColumnDef is null, issue a targeted `get_async(task_gid,
opt_fields=["custom_fields.gid","custom_fields.number_value"])` for that task only.
This is a null-targeted GET, not a blanket re-fetch — preserving the list-first
efficiency for non-null rows.

**Constraint (G-PROPAGATE)**: the recovery must be wired through a single shared
contract point — not per-field orphan patches. The FPC's FieldContract `fetch_requirement`
field is the correct propagation point. All 8 number cells declare
`fetch_requirement="may_need_get_recovery"` in one place; the warmer reads this and
applies the null-targeted GET backstop.

**Path-canonicalization** (FPC sub-pillar): one maximal-completeness materialization
per Source node means the unit frame for number cells is always built with the GET path
available as a null-recovery backstop. Zero new Asana API calls for already-populated
cells (CR-3 safe). Additional calls only for null number cells, bounded by the
number of actually-null rows (not the total task count).

**N>=2 throughline-promotion trigger**: if after Phase 2 deploy the coherent count
moves from 0 to >= 100 phones (i.e., >= 100 office phones have both unit.mrr and
offer.mrr non-null and equal), this constitutes empirical evidence that the recovery
contract works. That is the Phase 2 exit criterion. Re-run the canary after deploy.

**Phase 2 deliverable**: `unit.mrr` non-null for the active warm population;
coherent > 0 (target: coherent >> 571, gun approaches 0); population floor extended
to include the recovery-cured cells. The 571 defect is structurally cured.

### Phase 3 — Declarative FieldContract + Coherence Observatory (LONG-TERM)

**Entry criterion**: Phase 2 complete; coherence invariant passes GREEN for mrr;
cross-rite SRE referral (§5) actioned (per-field SLIs designed).

**Scope**: FPC Pillars 1+5 — the declarative FieldContract schema and the per-field
coherence observatory. This is the north-star architecture that makes Phases 1+2
fixes structurally permanent by deriving them from a single contract.

**FieldContract schema (north-star spec):**

```python
@dataclass
class FieldContract:
    name: str
    value_type: type           # canonical Python type (Decimal, str, int, bool, ...)
    canonical_source: str      # "cf:X", "cascade:X", "derived:fn", "base:attr"
    resolution: dict[str, ResolutionMode]  # per-entity: Direct / Cascade / Derived
    fetch_requirement: FetchRequirement    # list_ok / needs_get / may_need_get_recovery
    recovery: list[RecoveryStrategy]       # [] or [NullGetRetry(opt_fields=[...])]
    population_policy: PopulationPolicy    # ActiveSubset / Total / LegitimatelySparse
```

From this contract, DERIVED:
- Schema `ColumnDef(dtype=...)` — the dtype derives from `value_type`; no independent schema dtype declaration.
- Model field-class — derives from `value_type` + `resolution.mode`; no independent model declaration.
- `opt_fields` set — derives from `fetch_requirement` + `resolution`; no per-entity orphan opt_fields.
- `_VALUE_COLUMNS_BY_ENTITY` entries — derive from `population_policy != LegitimatelySparse`.
- Verification test matrix — generated: one coherence test per cascade field, one parity test per (schema, model) pair, one population test per non-sparse cell.

**G-PROPAGATE compliance**: the FPC shared contract IS the sole propagation point. There
are no per-field orphan patches. Every downstream artifact (schema, model, warmer,
floor) is generated or derived.

**Coherence observatory (FPC Pillar 5):**
Per-field SLIs derived from the FieldContract's population_policy. For each cell
declared `ActiveSubset`:

```
SLI: nonnull_count(entity.field, active_warm_subset) / active_warm_count >= threshold
```

The threshold is entity-specific (offer.mrr has a known floor: 62 records / $79,485
per SEAM-1 heal). The observatory emits a CloudWatch metric per field per warm cycle,
alerting when a field drops below its SLI threshold. This is the observability half of
the availability-first philosophy (structure-evaluator §5: "if you will always serve,
you must always observe").

**Phase 3 deliverable**: all Phases 1+2 fixes are re-derived from the FieldContract
(no logic duplication); the coherence observatory emits per-field SLIs; the parity
test suite is fully generated from the contract. Future schema/model drift is
structurally impossible (it would require editing the contract, which has one change
point, not two diverging files).

---

## 5. North-Star — "Dataflow Type System for the Data Plane"

### The Vision

The FPC is a dataflow type system with two axes:

**Provenance types** (how a value arrives):
- `Source` — Direct cf: extraction; the value originates here.
- `Cascade` — value propagated from an ancestor Source node via join key.
- `Aggregate` — value rolled up from child records (HOLDER frames).
- `Derived` — computed from other fields; no Asana extraction.

**Population types** (what guarantees the value's presence):
- `Total` — present for every record in the entity's warm population.
- `ActiveSubset` — present for the active business subset (e.g., offer.mrr: 62
  records out of a larger raw set; the denominator is active businesses, not all tasks).
- `LegitimatelySparse` — intentionally null for many records (e.g., specialty when
  not applicable); no floor needed; SLI is "not suspiciously sparser than baseline."

The cross-product of these two axes gives the policy for every cell. A Source/ActiveSubset
cell like `unit.mrr` must have: a fetch_requirement that includes GET recovery for nulls,
a population floor set at the ActiveSubset threshold, and a coherence test asserting its
cascade consumers match it. A Cascade/ActiveSubset cell like `offer.mrr` inherits its
floor from the source (`unit.mrr`), and the coherence invariant is the test.

### Failure Modes and Leaky Surfaces (G-RUNG pressure-test — not endorsement)

The FPC vision has the following structural failure modes:

**FM-A: Asana server non-determinism is not contractable.** The path-asymmetry defect
(AP-1) is server-side — opt_fields are already symmetric. The FieldContract's
`fetch_requirement` can declare that a number cell needs GET recovery, but if the Asana
server returns different values on different calls for the same task (not just list vs
get, but temporal non-determinism), the contract cannot enforce consistency. The FPC
assumes server-side determinism for the same task + same opt_fields; if that assumption
fails, the recovery contract is a mitigation, not a guarantee.

**FM-B: The cascade resolver's traversal order is not specified for dual-source fields.**
`cascade:Vertical` resolves from "Unit OR Business ancestor" with "first-ancestor-wins"
implied but unconfirmed (UK-5/U-3). The FieldContract's `resolution: dict[str, ResolutionMode]`
must specify the precedence per entity, not just "cascade." Until the traversal order
is confirmed and encoded, the vertical coherence invariant cannot be formalized. This
is a leaky surface in the north-star: the contract schema assumes deterministic source
precedence; the lattice has at least one cell where that is ambiguous.

**FM-C: Model-only NumberFields are invisible to the FPC.** `unit.meta_spend`,
`unit.tiktok_spend`, `offer.voucher_value`, `offer.budget_allocation` are NumberField
in models but have no schema cell (topology §4, Unknown UK-1). The FieldContract
schema registry starts from schema files; model-only fields are outside its purview.
If these are materialized without a FieldContract entry, they inherit AP-1+AP-3 with
no floor and no recovery. The FPC is only as complete as its registry coverage.

**FM-D: The population-floor is a post-build receipt, not a pre-publish gate.** The
current `post_build_population_receipt.py` fires AFTER the frame is built. If the
frame is published (S3 upload) before the floor check fires, a null-economic frame
is live. The FPC observatory is an observer, not a publish gate. Making it a
pre-publish gate requires build-path wiring that is an AP-4 class effort change. The
FPC does not automatically become a gate; that requires explicit design.

**FM-E: Holder frames (5 un-warmed entities) are outside the live coherence surface.**
`offer_holder`, `unit_holder`, `contact_holder`, `location`, `hours` have S3 census = 0.
The FieldContract can declare their cells and policies, but the coherence observatory
cannot observe them until they are warmed. The 571-gun's blast radius may extend to
`offer_holder` (which aggregates offer.mrr) once warming begins — that transition
should be gated on Phase 2 completion (mrr cured before aggregating nulls into holders).

---

## 6. Unknowns Registry (consolidated from all three upstream artifacts)

All unknowns from topology, dependency, and assessment phases, deduplicated and
ranked by impact severity.

### HIGH impact (block or bound a Phase 1/2 action)

### Unknown UK-2: discount/cost drift — which layer is canonical?
- **Question**: For `unit.discount` (schema Decimal / model EnumField) and `offer.cost`
  (schema Utf8 / model NumberField), which declaration is the intended source of truth?
- **Why it matters**: Determines drift-repair direction for D1/D2 (Phase 1 actions 1 and 2).
  `discount` has a PRD-0024 comment endorsing Enum; schema says Decimal. Ambiguous.
- **Evidence**: `src/autom8_asana/dataframes/schemas/unit.py:38-41` vs
  `src/autom8_asana/models/business/unit.py:118` ("Per PRD-0024: Enum with values like 10%").
- **Suggested source**: PRD-0024 owner. Blocks Phase 1 actions 1-2.

### Unknown UK-3: offer_id Utf8↔Int64 — is offer↔asset_edit joined on offer_id at DataFrame level?
- **Question**: Is there a live DataFrame join keyed on offer_id across offer and asset_edit
  frames (which would null-on-cast Utf8↔Int64), or is offer_id only used via the model's
  string-converting EXPLICIT_OFFER_ID API path?
- **Why it matters**: Decides whether AP-5 is active join-hazard (HIGH, blocking) or
  benign cross-frame cosmetic (LOW, quick cosmetic fix).
- **Evidence**: `schemas/offer.py:42-45` (Utf8) vs `schemas/asset_edit.py:126-130` (Int64);
  `src/autom8_asana/models/business/asset_edit.py:633` `str(offer_id_int)`.
- **Suggested source**: query/join layer owner. Conditions Phase 1 action 6.

### Unknown UK-4: Monolith consumer coherence inheritance (cross-repo)
- **Question**: Do payments/ad_reporting monoliths read `offer.mrr` (cascade output,
  1325/4070) or `unit.mrr` (0/3021) from S3? Either way they inherit the coherence
  break, but the economic blast radius differs.
- **Why it matters**: The Phase 2 cure scope depends on which frame the monolith reads.
  If it reads unit.mrr directly, curing unit.mrr automatically heals the monolith.
  If it reads offer.mrr, the monolith is already partially healed (1325/4070) but still
  carries 571 incoherent phones.
- **Evidence**: dependency-map EM1/EM2 (LOW confidence); no in-repo manifest for cross-repo
  consumer. Routed to cross-rite referral CRR-002.
- **Suggested source**: payments/ad_reporting repo manifests (cross-repo).

### MEDIUM impact (inform Phase 2/3 design)

### Unknown UK-5 / U-3: vertical cascade source-precedence (Unit vs Business)
- **Question**: When both Unit and Business ancestors carry Vertical, which wins in the
  cascade resolver traversal?
- **Why it matters**: Determines whether the FPC coherence invariant for `cascade:Vertical`
  cells is single-source (testable with a simple invariant) or multi-source (requires
  precedence-aware invariant).
- **Evidence**: `schemas/offer.py` vertical block "Cascades from Unit or Business ancestor";
  `src/autom8_asana/dataframes/resolver/cascading.py:199-269` "traverse parent chain until
  field found" (first-ancestor-wins implied, not confirmed for dual-key case).
- **Suggested source**: `cascading.py` traversal-order test or code inspection.

### Unknown UK-1: Model-only NumberFields — materialize or intentionally omit?
- **Question**: Are `unit.meta_spend`, `unit.tiktok_spend` (`models/business/unit.py:119,121`),
  `offer.voucher_value`, `offer.budget_allocation` (`models/business/offer.py:137-138`)
  — all NumberField in models, no schema cell — intentional omissions or un-materialized?
- **Why it matters**: If materialized later, they inherit AP-1 (no backstop) and AP-3
  (no floor) with no FPC coverage. Pre-registering their FieldContracts in Phase 3
  prevents silent inheritance.
- **Evidence**: model files at the cited lines; no matching ColumnDef in schemas/unit.py
  or schemas/offer.py.
- **Suggested source**: dataframe-layer owner / PRD-0024 scope.

### LOW impact (Phase 3 or accept)

### Unknown U-4 / UK-4b: process base (S3=0) and 5 un-warmed entities
- **Question**: offer_holder/unit_holder/contact_holder/location/hours have descriptors
  and Aggregate edges but S3 census = 0. Deliberate (lazy) or warming gap?
- **Why it matters**: These entities are outside the current coherence surface. The
  offer_holder edge (E21) aggregates offer.mrr — activating it before Phase 2 cure
  would aggregate nulls into holders. Sequencing: warm holders AFTER unit.mrr is cured.
- **Evidence**: `src/autom8_asana/core/entity_registry.py:830-839` offer_holder descriptor;
  S3 census 0 per LIVE CORPUS.
- **Suggested source**: hierarchy_warmer warm-set config / warm_priority gaps.

---

## 7. Cross-Rite Referrals

### Cross-Rite Referral: CRR-001
- **Target Rite**: 10x-dev
- **Concern**: The FieldContract declarative schema (Phase 3 north-star) requires new
  shared library primitives: a `FieldContract` dataclass, a contract registry loader,
  a schema/model parity test generator, and a coherence test generator. None of these
  exist in origin/main. This is a feature build, not a refactor.
- **Evidence**: `src/autom8_asana/dataframes/builders/post_build_population_receipt.py:60-61`
  shows the existing entity-generic primitive (dict-based). The FPC extends this to a
  full dataclass with derived generation. No FPC contract registry file exists in
  `git ls-tree origin/main src/autom8_asana/dataframes/`.
- **Suggested Scope**: Phase 3. Design the FieldContract dataclass schema; implement
  the registry loader; wire the parity + coherence test generators. This is a full
  sprint of 10x-dev work, not a patch.
- **Priority**: Deferred until Phase 1+2 are complete. Phase 1 quick-wins are
  independent of the FieldContract; building the contract first before understanding
  which cells drift is backward.

### Cross-Rite Referral: CRR-002
- **Target Rite**: 10x-dev (cross-repo investigation, possible operator routing)
- **Concern**: Unknown UK-4 — monolith consumers (payments/ad_reporting) reading
  warmed S3 frames for `unit.mrr` / `offer.mrr` / `weekly_ad_spend`. These are LOW-confidence
  inferred edges (dependency-map EM1/EM2). The economic blast radius of the 571-gun
  depends on whether the monolith reads `unit.mrr` (0/3021 = fully null) or `offer.mrr`
  (1325/4070 = partially populated). The Phase 2 cure scope is gated on this knowledge.
- **Evidence**: `src/autom8_asana/dataframes/builders/post_build_population_receipt.py:60-61`
  offer-only population floor implies a downstream economic consumer; no in-repo manifest
  in autom8y-asana declares the cross-repo consumption path.
- **Suggested Scope**: Inspect payments and ad_reporting repo manifests for S3 frame
  reads keyed on `unit.mrr` or `offer.mrr`. Produce a one-paragraph cross-repo consumer
  map. This is a discovery task (hours), not a sprint.
- **Priority**: HIGH — blocks Phase 2 cure scope determination. Should run in parallel
  with Phase 1.

### Cross-Rite Referral: CRR-003
- **Target Rite**: sre
- **Concern**: AP-3 (presence-not-equal-population) is fundamentally an observability
  gap. The FPC Phase 3 observatory requires per-field SLIs: `nonnull_count(entity.field)
  / active_warm_count >= threshold` emitted as a CloudWatch metric per warm cycle. This
  is SRE domain work (alarm design, threshold calibration, dashboard). The arch rite
  maps the cell-level population policies; SRE designs the alarm predicates and
  threshold baselines.
- **Evidence**: AP-3 finding in `fpc-architecture-assessment-2026-06-09.md §2`;
  structure-evaluator §5 "if you will always serve, you must always observe";
  existing observability infrastructure: ECS+Lambda dual-mode (from memory), CW alarms
  in autom8y TF.
- **Suggested Scope**: Design per-field population SLIs for the 10 number cells (minimum:
  `unit.mrr`, `offer.mrr`, `unit.weekly_ad_spend`, `offer.weekly_ad_spend`). Define
  alarm thresholds using the G-DENOM anchor: offer.mrr active subset = 62 records /
  $79,485. Baseline `unit.mrr` at zero today; alarm fires if it remains zero post-Phase-2
  deploy. This is a Phase 3 prereq.
- **Priority**: MEDIUM — Phase 3 prereq. Should be scoped in parallel with Phase 2 work,
  not blocking it.

---

## 8. Scope and Limitations

This analysis covers the structural properties of the data-plane field-resolution
lattice as represented in schema files, model files, resolver code, entity registry
declarations, and live S3 / DuckDB parquet at origin/main HEAD.

**This analysis does NOT cover:**

- **Runtime behavior under load**: latency, throughput, failure modes when the Asana
  API rate-limits the null-targeted GET backstop (Phase 2). The SlowAPI 100/min limit
  and single-worker constraint (from memory) are noted as constraints but not
  load-tested here.
- **Data architecture governance**: data flow ownership, retention policies, who is
  responsible for the unit.mrr field in Asana (the server-side divergence may have an
  Asana configuration root cause — out of scope for arch).
- **Operational deployment sequencing**: the 2-stage deploy constraint (from memory,
  CR-3 receiver bulk-fanout design), warm-set reconciliation, and soak gate sequences
  are not re-analyzed here. The Phase 2 recovery contract must be CR-3-budget-aware;
  the deployment plan is operator/SRE domain.
- **Organizational alignment**: team cognitive load for maintaining a FieldContract
  registry vs the current ad-hoc schema files. Conway's Law effects (who owns the
  schema vs model vs warmer layers).
- **Evolutionary architecture**: fitness function design beyond the parity test noted
  in Phase 1 action 4. The full FPC test suite generation is a Phase 3 design artifact.
- **Cross-repo consumer correctness**: whether payments/ad_reporting correctly handle
  null MRR values today (UK-4). This is CRR-002 scope.
- **Asana API behavior contracts**: the server-side divergence between list and GET
  paths for `number_value` is an Asana platform behavior. This analysis treats it as
  an environmental constraint; root-cause investigation of the Asana server is outside
  arch scope.

---

## 9. Migration Readiness Assessment (DEEP-DIVE)

### Decomposition health score

| dimension | score | evidence |
|---|---|---|
| Entity ↔ canonical project alignment | 5/5 | One GID per entity, `project_registry.py:21-50`; no entity straddles two projects |
| Holder/leaf ↔ aggregation domain | 5/5 | `category` + `holder_for` unidirectional, acyclic (dep-map §4) |
| Schema dtype ↔ model field-class | 2/5 | 3 drift cells (D1/D2/D3); no parity binding |
| Value-presence ↔ fetch-path independence | 1/5 | FM-1 open; presence is path-dependent; 0/3021 unit.mrr |
| Population-policy ↔ value-bearing cells | 1/5 | Only offer guarded; 14 unguarded value cells |
| **Overall** | **14/25** | Entity decomposition is excellent; type and population contracts are absent |

**Readiness verdict**: Phase 1 can begin immediately — it requires no infrastructure
changes, only line-level dtype reconciliations and a dict extension. Phase 2 readiness
requires: UK-2 resolved, UK-4 scoped, CR-3 soak confirmed stable (confirmed 2026-06-04
per memory), single-worker API budget understood. Phase 3 readiness requires: Phase 2
complete, SRE CRR-003 scoped, FieldContract schema design reviewed by PRD-0024 owner.

### Effort estimates per phase

| phase | scope | effort estimate | blocking unknowns |
|---|---|---|---|
| Phase 1 | D1/D2/D3 drift reconcile + parity test + floor extension + offer_id normalize | 3–5 days (10x-dev sprint) | UK-2 (D1/D2 direction) |
| Phase 2 | AP-1 recovery contract + path-canonicalization + warm-path wiring | 1–2 weeks (includes CR-3-budget testing) | UK-4 (blast radius), CR-3 soak pass |
| Phase 3 | FieldContract schema + registry + generated test matrix + coherence observatory | 3–4 weeks (new shared library primitives) | Phase 2 complete; CRR-003 SLI design |

---

## 10. Findings Disposition Checklist

Verification that every finding from the architecture assessment has a disposition.

| finding | disposition | phase |
|---|---|---|
| AP-1 Path-Dependent Resolution (10 cells, 8 backstop-less) | RECOMMEND: recovery contract (Phase 2) | 2 |
| AP-2 Schema/Model Type-Drift D1 unit.discount | RECOMMEND: reconcile pending UK-2 | 1 |
| AP-2 Schema/Model Type-Drift D2 offer.cost | RECOMMEND: reconcile pending UK-2 | 1 |
| AP-2 Schema/Model Type-Drift D3 asset_edit.score | RECOMMEND: schema → Decimal | 1 |
| AP-3 Presence != Population (14 unguarded cells) | RECOMMEND: extend floor to 8+ number cells | 1 |
| AP-4 Single-Fetch-Path SPOF (no GET recovery) | ACCEPT-FOR-NOW (CR-3 budget trade-off); address in Phase 2 via AP-1 cure | 2 |
| AP-5 Cross-Frame offer_id Utf8↔Int64 | RECOMMEND: normalize conditional UK-3 | 1 |
| FM-2 status source=None | ACCEPT-AS-IS — CLOSED by SEAM-1 | closed |
| FM-1 path-dependent number drop | RECOMMEND: recovery contract (maps to AP-1) | 2 |
| FM-3 schema/model type-drift | RECOMMEND: reconcile D1/D2/D3 (maps to AP-2) | 1 |
| FM-4 presence!=population | RECOMMEND: floor extension (maps to AP-3) | 1 |
| UK-1 model-only NumberFields | ACCEPT: flag for pre-registration if materialized | 3 |
| UK-2 discount/cost canonical direction | ESCALATE to PRD-0024 owner (blocks Phase 1) | pre-1 |
| UK-3 offer_id join activation | ESCALATE to query/join layer owner (conditions Phase 1) | pre-1 |
| UK-4 monolith consumer path | ROUTE to CRR-002 (scopes Phase 2) | pre-2 |
| UK-5 vertical cascade precedence | ACCEPT: Phase 3 coherence invariant scope | 3 |
| asset_edit_holder 100% cascade SPOF | ACCEPT-AS-IS for keystone risk (structural design, not defect); note in Phase 3 observatory | 3 |
| Boundary 4.3 schema/model boundary leak | RECOMMEND: sealed by Phase 3 FieldContract | 3 |
| Boundary 4.4 fetch-path boundary leak | RECOMMEND: sealed by Phase 2 path-canonicalization | 2 |

No finding is orphaned.
