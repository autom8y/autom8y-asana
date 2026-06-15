---
type: review
status: draft
role: structure-evaluator
depth: DEEP-DIVE
upstream:
  - fpc-topology-inventory-2026-06-09.md
  - fpc-dependency-map-2026-06-09.md
date: 2026-06-09
head: 50ebfe3381a627df868887ca3cdf9e223e1f9a90
---

# FPC Architecture Assessment — Anti-Pattern × Cell × Severity Risk Register

> **Role**: structure-evaluator (DEEP-DIVE). Renders judgment on structural health of the
> data-plane field-resolution lattice. Evaluates anti-patterns ACROSS the (entity,field)
> matrix; does NOT prescribe fixes (remediation-planner) nor re-trace cascades (dependency-analyst).
> **Scope**: READ-ONLY over origin/main + S3 + /tmp/u8o,/tmp/u8u parquet. No src/ edits.
> **HEAD**: `origin/main = 50ebfe3381a627df868887ca3cdf9e223e1f9a90` (verified `git rev-parse origin/main`).
> **G-THEATER canary (re-run THIS pass)**: coherence invariant `offer.mrr[phone] == unit.mrr[phone]`
> fires **RED = 571** (`gun=571`, `total_joined=2001`; `unit.mrr` 0/3021 nonnull; `offer.mrr` 1325/4070).
> The map is credible because the headline coupling edge carries this live RED.
> **Rung**: MAPPED + ranked. This artifact maps the opportunity matrix and ranks by leverage. It
> rebinds no consumer and lands no fix.

---

## 0. Provenance Verification & Premise Corrections (G-PREMISE)

I defaulted every upstream citation to REFUTED and re-verified against origin/main. Two
**path-citation drifts** in the upstream artifacts were caught and corrected (line numbers held;
path prefixes were wrong):

| upstream cited path | actual origin/main path | receipt |
|---|---|---|
| `entity_registry.py` / `dataframes/...entity_registry.py` (topology §3.x; dep-map §1,§2) | **`src/autom8_asana/core/entity_registry.py`** | `git ls-tree -r origin/main` → no `dataframes/entity_registry.py`; `git grep -n 'warm_priority='` resolves to `core/entity_registry.py:449,476,502,521,545,...` (line numbers MATCH upstream) |
| (implicit) schema/cf extraction in `views/cf_utils.py` | confirmed present at that path | `git show origin/main:src/autom8_asana/dataframes/views/cf_utils.py:21-117` |

The line numbers cited by both upstream artifacts are accurate; only the registry path prefix is
mislabeled. This does not invalidate their findings — every descriptor I re-pulled
(`warm_priority`, `key_columns`, `holder_for`, `body_parameterized`) matched their line citations
once the path was corrected. **Correction recorded for remediation-planner: use
`src/autom8_asana/core/entity_registry.py`.**

Receipts I re-ran live this pass (not inherited):
- Canary RED=571: `duckdb` join offer↔unit on office_phone over /tmp/u8o + /tmp/u8u → `gun=571, total_joined=2001`.
- `unit.mrr` 0/3021; `offer.mrr` 1325/4070 (`read_parquet` counts).
- `extract_cf_value` number-branch dispatch (`cf_utils.py:46-50`): `case "number": return cf_data.get("number_value")`.
- opt_fields symmetry: LIST path `builders/fields.py:69` `"custom_fields.number_value"`; GET path `cache/integration/hierarchy_warmer.py:43` `"custom_fields.number_value"`.
- No null-recovery backstop **[CH-01 CORRECTED — Potnia post-adversary]**: the broad grep `recover|repair_null|refetch_via_get|number.*fallback` returns 6 hits, but ALL are circuit-breaker `recovery_timeout`/HALF_OPEN in `storage.py:284,313,546,547,614,615` (unrelated to number-cell recovery). The **correctly-scoped** receipt is EMPTY: `git grep -nE 'repair_null|refetch_via_get|number_value.*(recover|refetch|fallback)|display_value.*fallback|fallback.*display_value' origin/main -- 'src/autom8_asana/dataframes/**'` → **no matches**. Keystone HOLDS: `cf_utils.py:49` + `default.py:255` number-branches `return number_value` bare (the `case _` display fallback is unreachable for a known `"number"` subtype); the display_value fallback exists ONLY in the *unmerged* cell-0 worktree.

---

## 1. The Mechanism That Makes the Anti-Patterns Structural (root grounding)

Every number-cell defect in this lattice traces to ONE extraction function and its fetch-path
substrate. This is the load-bearing structural fact the register rests on:

**`extract_cf_value(cf_data)` dispatches on `cf_data["resource_subtype"]`**
(`git show origin/main:src/autom8_asana/dataframes/views/cf_utils.py:46-50`):

```python
match resource_subtype:
    case "number":
        return cf_data.get("number_value")
```

A number cell resolves to a value **iff** the fetched custom-field dict carries both
`resource_subtype == "number"` AND a populated `number_value`. Both fetch paths request
`number_value` symmetrically (LIST `fields.py:69`; GET `hierarchy_warmer.py:43`), so when a number
cell lands null it is **NOT** an opt_fields omission — it is a server-side divergence between the
**section-list path** (`builders/parallel_fetch.py:576-578` `list_async(section, opt_fields=self.opt_fields)`)
and the **per-task-GET path** (`hierarchy_warmer.py:93` `get_async(gid, opt_fields=_HIERARCHY_OPT_FIELDS)`).

**Structural consequence (the keystone judgment):** the FPC cannot close the null-number class by
adding opt_fields — the opt_fields are already symmetric. It must add a *recovery contract*
(a GET-path backstop for null number cells). The grep for any such backstop in `dataframes/` is
empty — **the lattice has zero recovery path for a list-path number drop.** Every number cell is a
single-fetch-path SPOF unless it happens to ride the cascade-ancestor GET path.

---

## 2. Risk Register — Anti-Pattern × Affected Cells × Severity × Leverage

Leverage = impact / effort (`[PLATFORM-HEURISTIC: Leverage formula]`, impact & effort on 1-5).
Quick win ≥3; strategic 1-3 w/ impact ≥4; long-term <1. Severity weights cumulative anti-pattern
count per cell `[AQ:SRC-004 Mo et al. 2019] [STRONG]`. Every entry passed the three-check
false-positive gate (intentional? bounded-context-aligned? evidence-sufficient?) before entry.

### AP-1 — Path-Dependent Resolution (single-fetch-path number drop) [STRUCTURAL | HIGH]

**Construct measured** (per `[AV:SRC-001 Messick 1989]`): the count of (entity, number-field) cells
whose value can silently become null because the section-list path returns a cf dict without a
resolvable `number_value`, with no GET-path recovery.

**Affected cells (the path-dependent cell set — 10 schema-projected number cells):**

| cell | dtype | source | on cascade-GET backstop? | exposure |
|---|---|---|---|---|
| `unit.mrr` | Decimal | `cf:MRR` (`schemas/unit.py:10-13`) | NO (built on its own LIST frame) | **PROVEN RED — 0/3021** |
| `unit.weekly_ad_spend` | Decimal | `cf:Weekly Ad Spend` (`unit.py:17-20`) | NO | exposed, untested |
| `unit.discount` | Decimal | `cf:Discount` (`unit.py:38-41`) | NO | exposed + ALSO drift (AP-2) |
| `offer.cost` | Utf8(!) | `cf:Cost` Number (`offer.py:70-73`) | NO | exposed + ALSO drift (AP-2) |
| `offer.mrr` | Decimal | `cascade:MRR` (`offer.py:77-80`) | YES (rides ancestor GET) | **1325/4070 — partial; the 571 face** |
| `offer.weekly_ad_spend` | Decimal | `cascade:Weekly Ad Spend` (`offer.py:84-87`) | YES (cascade) | exposed, untested |
| `asset_edit.offer_id` | Int64 | `cf:Offer ID` (`asset_edit.py:126-130`) | NO | exposed |
| `asset_edit.score` | Float64 | `cf:Score` (`asset_edit.py:147-151`) | NO | exposed + ALSO drift (AP-2) |
| `asset_edit.template_id` | Int64 | `cf:Template ID` (`asset_edit.py:162-165`) | NO | exposed |
| `asset_edit.videos_paid` | Int64 | `cf:Videos Paid` (`asset_edit.py:168-172`) | NO | exposed |

**PATH-DEPENDENT CELL COUNT = 10** schema cells. Of these, **8 have NO cascade-GET backstop**
(only `offer.mrr` and `offer.weekly_ad_spend` ride the ancestor GET path, and even those inherit the
ancestor's null). The unit-MRR class generalizes to **all 8 backstop-less number cells**:
`unit.mrr`, `unit.weekly_ad_spend`, `unit.discount`, `offer.cost`, `asset_edit.{offer_id, score, template_id, videos_paid}`.

**+4 latent model-only number cells** (NumberField in model, no schema cell yet — would inherit the
defect with no floor if materialized): `unit.meta_spend`, `unit.tiktok_spend`
(`models/business/unit.py:119,121`), `offer.voucher_value`, `offer.budget_allocation`
(`models/business/offer.py:137-138`). Flagged Unknown UK-1.

- **Severity: HIGH.** `unit.mrr` carries the live RED; the class is the economic spine (MRR/ad-spend).
- **False-positive gate**: NOT intentional (the symmetric opt_fields show intent was to fetch the number); bounded-context-aligned (all within the offer-economics context) but the defect is population, not coupling; evidence is live-RED for the anchor cell, schema+mechanism for the rest.
- **Impact 5 / Effort 2** (one recovery contract covers all 8) → **Leverage 2.5 — STRATEGIC (impact≥4)**.

### AP-2 — Schema/Model Type-Drift (silent-null on coerce) [STRUCTURAL | HIGH]

**Construct measured**: cells where the schema `dtype`/`source` and the model field-class disagree
on value type, so the coercer casts a value of the wrong shape → silent null or wrong-type.

**DRIFT SWEEP — every (entity,field) schema dtype vs model field class compared. HITS = 3** (the
known `discount` PLUS **2 new ones beyond it**):

| # | cell | schema (receipt) | model (receipt) | drift class | status |
|---|---|---|---|---|---|
| D1 | `unit.discount` | `dtype="Decimal"`, `source="cf:Discount"` (`schemas/unit.py:38-41`) | `discount = EnumField()` (`models/business/unit.py:118`) | **Decimal ↔ Enum** — model extracts enum string ("10%","20%","None"); schema expects Decimal → coercer null-on-cast | KNOWN |
| **D2** | **`offer.cost`** | `dtype="Utf8"`, `source="cf:Cost  # Number field"` (`schemas/offer.py:70-73`) | `cost = NumberField()` (`models/business/offer.py:136`) | **Utf8 ↔ Number** — schema declares TEXT for a Number field; number_value stringified, loses numeric type for any downstream arithmetic | **NEW** |
| **D3** | **`asset_edit.score`** | `dtype="Float64"`, `source="cf:Score"` (`schemas/asset_edit.py:147-151`) | `score` accessor `_get_number_field()` → **`Decimal`** (`models/business/asset_edit.py:192-194,263-269`) | **Float64 ↔ Decimal** — model returns `Decimal(str(value))`; schema declares Float64. Decimal→Float64 coerce is lossy/precision-divergent; the model's own docstring at `asset_edit.py:58` compares `score > Decimal("90")` | **NEW** |

**Drift hits beyond `discount` = 2** (`offer.cost` D2, `asset_edit.score` D3).

**Adjacent-but-NOT-drift (verified aligned, false-positive gate rejected them):**
- `unit.mrr`/`offer.mrr` Decimal ↔ `NumberField(field_name="MRR")` (`models/business/mixins.py:95`) — **type-aligned**; the mrr null is AP-1 (path), not AP-2. Confirms two distinct null mechanisms coexist.
- `asset_edit.offer_id` Int64 ↔ `_get_int_field()`→`int` (`asset_edit.py:150-157,256-261`) — aligned.
- `asset_edit.{template_id,videos_paid}` Int64 ↔ `_get_int_field()`→`int` — aligned.

- **Severity: HIGH** for D1 (live: `unit.discount` is in the 0-population unit frame); **MEDIUM** for D2/D3 (type-lossy, not necessarily fully-null; D3 is precision-drift not null-drift).
- **False-positive gate**: D1 has an explicit PRD-0024 comment ("Enum with values like 10%") — this is an *intentional model choice* that the schema did NOT follow; the drift is real and the schema is the stale side. NOT an accepted trade-off — escalated as UK-2 (which side is canonical?). D2/D3 are unflagged divergences, no ADR.
- **Impact 4 / Effort 1** (3 line-level dtype/field reconciliations) → **Leverage 4.0 — QUICK WIN**.

### AP-3 — Presence ≠ Population (unguarded value fields) [STRUCTURAL | HIGH]

**Construct measured**: value-bearing cells (economics + identity keys) that have NO population-floor
policy, so a frame can publish "successfully" while a value column is silently 100% null (the
active_mrr fossil class).

**Receipt**: `git show origin/main:src/autom8_asana/dataframes/builders/post_build_population_receipt.py:60-61`:
```python
_VALUE_COLUMNS_BY_ENTITY: dict[str, tuple[str, ...]] = {
    "offer": ("mrr", "offer_id"),
}
```
**Only `offer` has a floor. Only 2 columns (`mrr`, `offer_id`) are guarded.**

**UNGUARDED VALUE-FIELD COUNT.** Counting value-bearing cells (number/economic + identity-key cells
that downstream economics depend on) NOT in `_VALUE_COLUMNS_BY_ENTITY`:

| entity | unguarded value cells | count |
|---|---|---|
| unit | mrr, weekly_ad_spend, discount | 3 |
| offer | cost, weekly_ad_spend | 2 (mrr+offer_id ARE guarded) |
| asset_edit | offer_id, score, template_id, videos_paid | 4 |
| business | company_id, stripe_id (identity keys) | 2 |
| contact | employee_id, contact_phone, contact_email (keys) | 3 |
| (project/section/process/holders) | status + cascade keys | (cascade-keys counted under AP-1/keystone) |

**UNGUARDED VALUE-FIELD COUNT = 14** value/identity cells across 5 entities (strict number+key
reading). If the floor were extended only to number-economic cells, the minimum is the **10
number cells of AP-1 minus the 2 guarded = 8 unguarded number cells**. Headline number: **80 of 82
total schema cells have ∅ population policy** (topology §4); the *value-bearing* unguarded subset is
**14** (or 8 if restricted to numerics).

- **Severity: HIGH** — this is the structural reason the 571-gun and the active_mrr fossil could ship undetected: no floor fires RED on null economics for any entity except offer.
- **False-positive gate**: offer-only floor is an *intentional MVP seed* (`post_build_population_receipt.py` is entity-generic by construction — `_VALUE_COLUMNS_BY_ENTITY.get(entity_type, ())`), so the primitive is designed to generalize; the gap is un-extended coverage, not a wrong design. Bounded-context-aligned. Evidence: the dict literal is the receipt.
- **Impact 5 / Effort 2** (extend the existing dict + per-field policy ActiveSubset/Total/Sparse per G-DENOM) → **Leverage 2.5 — STRATEGIC**.

### AP-4 — Single-Fetch-Path SPOF (no GET/cascade backstop for own economics) [STRUCTURAL | HIGH]

**Construct measured**: entities whose economic/number cells depend SOLELY on the section-list path
with no per-task-GET or cascade backstop, so a list-path number drop is unrecoverable.

**Receipt (negative) [CH-01 CORRECTED — Potnia post-adversary]**: the broad pattern `recover|…` returns 6 circuit-breaker `recovery_timeout` hits in `storage.py` (NOT number-cell recovery). The correctly-scoped negative receipt is genuinely EMPTY: `git grep -nE 'repair_null|refetch_via_get|number_value.*(recover|refetch|fallback)|display_value.*fallback' origin/main -- 'src/autom8_asana/dataframes/**'` → **no matches**; `cf_utils.py:49` / `default.py:255` number-branches `return number_value` bare (no display_value fallback on origin/main). Conclusion HOLDS — no number-cell recovery path exists; the cell-0 cure that adds one is unmerged.

| entity | own number cells | fetch path | backstop? | SPOF? |
|---|---|---|---|---|
| **unit** | mrr, weekly_ad_spend, discount | LIST (`parallel_fetch._fetch_section`) | NONE | **YES — the 571-gun root SPOF** (unit.mrr 0/3021) |
| **asset_edit** | offer_id, score, template_id, videos_paid | LIST | NONE | YES |
| offer | cost (own); mrr/weekly_ad_spend (cascade) | LIST own; GET ancestor for cascade | cascade-GET for mrr/ad_spend ONLY | PARTIAL — own `cost` is SPOF; cascade cells inherit ancestor SPOF |

**Cascade cells are NOT a true backstop** — they read the ancestor via GET, but if the ancestor
(`unit.mrr`) is itself a list-path SPOF at 0/3021, the GET path reads the same null. The cascade
*moves* the SPOF up to `unit.mrr`; it does not eliminate it. Hence offer.mrr 1325/4070 (partial) is
*better* than unit.mrr 0/3021 only because the GET-path ancestor sometimes succeeds where the unit
LIST frame failed — confirming the recovery contract must live at the unit source.

- **Severity: HIGH.** unit is the keystone economic source; its number cells have no backstop.
- **Cascade SPOF — `asset_edit_holder.office_phone`** is the SOLE key (100% cascade dependency; schema comment "if cascade fails, this entity is entirely unlookable", `schemas/asset_edit_holder.py:18-22`). A non-economic but total-availability SPOF.
- **False-positive gate**: list-first is an *intentional CR-3 efficiency design* (`parallel_fetch` doc "more efficient than N get_async calls", `:595`); a per-task-GET-for-everything would violate the CR-3 API-budget constraint. So the SPOF is a real consequence of an accepted performance trade-off — the gap is the *absence of a targeted null-only recovery*, not the list-first choice. Escalated as a trade-off for remediation-planner.
- **Impact 5 / Effort 4** (recovery contract + warm-path wiring, CR-3-budget-aware) → **Leverage 1.25 — STRATEGIC/long-term boundary**.

### AP-5 — Cross-Frame Shared-Contract Divergence (offer_id Utf8↔Int64) [STRUCTURAL | MEDIUM]

**Construct measured**: a single Asana field (`cf:Offer ID`) materialized as two different dtypes
across frames, silently failing any cross-frame join keyed on it.

**Receipt**: `offer.offer_id` `dtype="Utf8"` (`schemas/offer.py:42-45`) vs `asset_edit.offer_id`
`dtype="Int64"` (`schemas/asset_edit.py:126-130`) — same `source="cf:Offer ID"`. `asset_edit.key_columns`
includes `offer_id` (`core/entity_registry.py:547`), and `asset_edit` has an `EXPLICIT_OFFER_ID`
resolution strategy that navigates via offer_id (`models/business/asset_edit.py:340,609-633`,
"Per PRD-0024: offer_id is now int, convert to str for API calls").

- **Severity: MEDIUM** — the model already string-converts at the API boundary (`offer_gid = str(offer_id_int)`, `asset_edit.py:633`), so the live resolution path may dodge it; but any DataFrame-level join offer↔asset_edit on offer_id would null-on-cast (Utf8 vs Int64).
- **False-positive gate**: dependency-map flagged this as U-2 (active or benign?). Evidence is HIGH (both dtypes declared) but the *join-hazard activation* is unconfirmed — recorded as MEDIUM with escalation UK-3.
- **Impact 3 / Effort 1** → **Leverage 3.0 — QUICK WIN** (conditional on UK-3).

---

## 3. FM-1/3/4 Face Coverage (closed vs open across the corpus)

The dispatch asks which FM faces are closed (SEAM-1) vs open. Mapping the FM nomenclature to the
mechanically-grounded defect faces:

| face | description | status | receipt |
|---|---|---|---|
| **FM-2** | `status` cells `source=None` → 100% null | **CLOSED (SEAM-1)** | `schemas/project.py:23-27` + `section.py:23-30` now `source="cf:Status"`, version bumped `1.1.0` "was source=None -> 100% null" |
| **FM-1** (path-dependent number resolution) | list-path drops `number_value` | **OPEN** — 8 backstop-less cells (AP-1); `unit.mrr` 0/3021 live RED | `cf_utils.py:46-50` + empty recovery grep |
| **FM-3** (schema/model type-drift) | dtype↔field-class disagree | **OPEN** — 3 hits D1/D2/D3 (AP-2) | `schemas/unit.py:38-41` vs `models/business/unit.py:118`; +2 new |
| **FM-4** (presence≠population) | no floor → silent-null economics | **OPEN** — only offer guarded (AP-3) | `post_build_population_receipt.py:60-61` |

**SEAM-1 closed exactly ONE face (FM-2, the `source=None` status class). FM-1, FM-3, FM-4 remain
open across the corpus.** The two NEW defect faces in the LIVE CORPUS brief — (a) path-dependent
resolution and (b) schema/model type-drift — are AP-1/FM-1 and AP-2/FM-3 respectively, both OPEN.

---

## 4. Boundary Alignment Assessment [STRUCTURAL | HIGH]

Per `[DP:SRC-005 Evans 2003]` (bounded contexts) and `[AQ:SRC-006 Martin 2002]` (ADP/instability).
Evaluated against topology classifications + dependency-map coupling.

**4.1 Entity decomposition matches domain — STRONG alignment.**
- Canonical-project-per-entity is clean: each entity = one Asana project GID (`core/project_registry.py:21-50`; single-canonical-project per entity, confirmed by LIVE CORPUS). No entity straddles two projects. This is correct bounded-context decomposition.
- Holder-vs-leaf split is principled: `category=ROOT/COMPOSITE/LEAF/HOLDER` (`entity_registry.py:444,471,497,516,540,726+`). HOLDER frames aggregate leaves under a parent (`holder_for`/`parent_entity`); LEAF frames carry direct cells. The aggregation direction is unidirectional (holder←leaf), confirmed acyclic by dependency-map §4.

**4.2 The universal `office_phone` join key — INTENTIONAL keystone, NOT an anti-pattern.**
- Every descriptor is keyed on `office_phone` (`key_columns=("office_phone",...)` on all entities). Fan-out ~26 frames (dep-map §3 rank 1). Per the three-check gate this is **domain cohesion, not incidental coupling** — the entire lattice is deliberately business-phone-keyed. Recorded as the structural keystone. The structural RISK is concentration: a single key means a single point of join failure (`asset_edit_holder` 100%-cascade-dependency is the extreme). Recorded, not flagged as anti-pattern.

**4.3 Leaking abstraction — the schema/model boundary leaks (the drift class).**
- The schema layer (`dataframes/schemas/`) and the model layer (`models/business/`) are TWO independent declarations of the same field's type, with no generated parity check. D1/D2/D3 are the leaks. This is the boundary the FPC's "generated verification matrix" would seal — the **structural argument FOR a single FieldContract source-of-truth** from which both schema dtype and model field-class derive. Currently they drift because nothing binds them.

**4.4 The fetch-path boundary leaks into the value layer.**
- Whether a cell is populated depends on WHICH fetch path materialized it (list vs get) — an
  infrastructure concern leaking into the data-correctness layer. A value's *presence* should not
  be path-dependent; that it IS is the FM-1 structural defect. The FPC's path-canonicalization
  (one maximal-completeness materialization per Source node) is the boundary repair.

**4.5 Module-to-domain alignment score (DEEP-DIVE):**

| dimension | alignment | evidence |
|---|---|---|
| entity ↔ canonical project | **5/5 aligned** | one GID per entity, `project_registry.py:21-50` |
| holder/leaf ↔ aggregation domain | **5/5 aligned** | `category` + `holder_for` unidirectional, acyclic |
| schema dtype ↔ model field-class | **2/5 — LEAKS** | 3 drift cells, no parity binding (D1/D2/D3) |
| value-presence ↔ fetch-path independence | **1/5 — LEAKS** | FM-1; presence is path-dependent, no recovery |
| population-policy ↔ value-bearing cells | **1/5 — LEAKS** | only offer guarded; 14 unguarded value cells |

The entity/holder decomposition is excellent; the **type-contract and population-contract boundaries
are absent**, which is precisely the gap a declarative FieldContract closes.

---

## 5. Architectural Philosophy Extraction (DEEP-DIVE)

**Implicit philosophy: availability-first, schema-declarative, cascade-keyed data plane.**
- *Availability-first*: `LKG_MAX_STALENESS_MULTIPLIER=0.0` (unlimited staleness, per memory) + serve-stale + offer-only floor → the system prefers serving *some* data over failing. The number-null class is the cost: a null MRR is served rather than refused. This is consistent — but it means **correctness invariants must be EXTERNAL observers (the FPC observatory), because the serving path will never refuse a null.**
- *Schema-declarative*: cells are `ColumnDef(source="cf:X"/"cascade:X")` — declarative provenance. This is the right substrate for the FPC; the philosophy already wants a declarative contract. The FPC is the *completion* of the existing direction, not a new paradigm.
- *Cascade-keyed*: office_phone as universal key; cascade-from-ancestor for shared fields. Coherent and acyclic.

**Where practice diverges from philosophy:**
1. The declarative schema is **half-declarative**: `source=` declares provenance but NOT value_type-contract, recovery, or population-policy. The model layer re-declares type independently → drift. Philosophy says "declarative"; practice splits the declaration across two unbound layers.
2. Availability-first WITHOUT a coherence observatory means the 571-gun ships silently. The philosophy needs its dual: if you will always serve, you must always *observe*. Only offer has the observer (the floor). Practice has the serving half, not the observing half.

**The FPC as philosophy-completion** (pressure-tested, not endorsed — that is remediation-planner's call):
a single `FieldContract(name, value_type, canonical_source, resolution{per-entity}, fetch_requirement, recovery[], population_policy)` per (entity,field) makes the *already-declarative* schema *fully* declarative, and from it derives schema dtype + model field-class (sealing AP-2), opt_fields + recovery (sealing AP-1/AP-4), population-floor set (sealing AP-3), and a generated coherence/parity matrix (the observer half). **G-THEATER check**: the proposed coherence invariant `offer.mrr[phone]==unit.mrr[phone]` fires RED=571 on the known gun — the FPC's verification matrix is credible because its first generated test fails on the live defect.

---

## 6. Top Structural Risks (ranked by leverage)

| rank | risk | anti-patterns stacked | severity | leverage | class |
|---|---|---|---|---|---|
| 1 | **Schema/model type-drift (D1/D2/D3)** | AP-2 | HIGH/MED | **4.0** | QUICK WIN |
| 2 | **offer_id Utf8↔Int64 cross-frame** | AP-5 | MEDIUM | **3.0** | QUICK WIN (cond. UK-3) |
| 3 | **Path-dependent number drop (8 cells)** | AP-1 + AP-4 stacked on unit.mrr | HIGH | **2.5** | STRATEGIC |
| 4 | **Presence≠population (14 unguarded value cells)** | AP-3 | HIGH | **2.5** | STRATEGIC |
| 5 | **Single-fetch-path SPOF (no recovery)** | AP-4 + AP-1 | HIGH | **1.25** | STRATEGIC/long-term |

**Cumulative anti-pattern multiplier** `[AQ:SRC-004 Mo et al. 2019] [STRONG]`: `unit.mrr` carries the
most stacked anti-patterns (AP-1 path + AP-4 SPOF + AP-3 unguarded-at-source) → highest error-proneness;
it is the single most-error-prone cell and the live-RED anchor. `offer.cost` stacks AP-1 + AP-2 + AP-3.
`unit.discount` stacks AP-1 + AP-2 + AP-3. These three are the triple-stacked cells.

---

## 7. Unknowns (structural decisions requiring human/cross-repo context)

### Unknown UK-1: Model-only NumberFields — materialize or intentionally omit?
- **Question**: `unit.meta_spend`, `unit.tiktok_spend`, `offer.voucher_value`, `offer.budget_allocation` are `NumberField()` in models with NO schema cell. Intentional omission or un-materialized?
- **Why it matters**: If materialized later they inherit AP-1 (no backstop) AND AP-3 (no floor) silently.
- **Evidence**: `models/business/unit.py:119,121`; `models/business/offer.py:137-138`; no matching ColumnDef.
- **Suggested source**: dataframe-layer owner / PRD-0024 scope.

### Unknown UK-2: discount/cost drift — which layer is canonical?
- **Question**: For `unit.discount` (schema Decimal / model Enum) and `offer.cost` (schema Utf8 / model Number), which declaration is the intended source of truth?
- **Why it matters**: Determines drift-repair direction (fix schema or fix model). `discount` has a PRD-0024 comment endorsing the Enum model side, contradicting the Decimal schema.
- **Evidence**: `schemas/unit.py:38-41` vs `models/business/unit.py:118` ("Per PRD-0024: Enum with values like 10%").
- **Suggested source**: PRD-0024 owner.

### Unknown UK-3: offer_id Utf8↔Int64 — is offer↔asset_edit joined on offer_id?
- **Question**: Is there a live DataFrame join keyed on offer_id across these two frames (would null-on-cast), or is offer_id only used via the model's string-converting EXPLICIT_OFFER_ID API path?
- **Why it matters**: Decides whether AP-5 is an active join-hazard (HIGH) or benign cross-frame cosmetic (LOW).
- **Evidence**: `schemas/offer.py:42-45` (Utf8) vs `schemas/asset_edit.py:126-130` (Int64); `models/business/asset_edit.py:633` `str(offer_id_int)`.
- **Suggested source**: query/join layer owner; structure-evaluator could not find a DataFrame-level offer↔asset_edit join in dataframes/.

### Unknown UK-4: Monolith consumer coherence inheritance (cross-repo)
- **Question**: Do payments/ad_reporting monoliths read `offer.mrr` (cascade output, 1325/4070) or `unit.mrr` (0/3021) from S3? Either way they inherit the coherence break, but the blast radius differs.
- **Why it matters**: The economic blast radius of the 571-gun depends on which value the monolith consumes.
- **Evidence**: dependency-map U-1 (EM1/EM2, LOW confidence); offer-only floor implies a downstream economic consumer; no in-repo manifest.
- **Suggested source**: payments/ad_reporting repo manifests (cross-repo — note for remediation-planner cross-rite routing).

### Unknown UK-5: vertical cascade source-precedence (Unit vs Business)
- **Question**: When both Unit and Business ancestors carry Vertical, which wins?
- **Why it matters**: Determines whether the FPC coherence invariant for `vertical` is single- or multi-source.
- **Evidence**: cascade comments "from Unit or Business ancestor (warm_priority=2/1)" in offer/process/section/contact/asset_edit schemas; resolver traversal order (dependency-map U-3).
- **Suggested source**: `dataframes/resolver/cascading.py` traversal-order test.

---

## 8. Cross-Rite Observations (for remediation-planner to convert to referrals)

- **SRE/observability**: AP-3 (presence≠population) is fundamentally an observability gap — the FPC's "population/coherence observatory (per-field SLIs)" is an SRE-domain artifact. Note for sre referral.
- **No security implications surfaced** in this lattice (no auth/secret/PII boundary touched by the field-resolution defects).

---

## 9. Confidence Ratings (per finding)

- **HIGH** (multi-artifact + live corroboration): AP-1 anchor `unit.mrr` (live RED 571 + 0/3021 + cf_utils mechanism + empty-recovery grep); AP-2 D1/D2/D3 (schema line + model line both pasted); AP-3 (the floor dict literal pasted); FM-2 closed (schema version-bump + source line); boundary 4.1/4.2 (registry descriptors).
- **HIGH** (structural + mechanism): AP-4 SPOF (negative grep + symmetric opt_fields proving server-side divergence); cumulative-stacking on unit.mrr/offer.cost/unit.discount.
- **MEDIUM**: AP-5 offer_id join-hazard *activation* (both dtypes HIGH, but live join unconfirmed — UK-3); AP-1 exposure of the 7 non-anchor number cells (schema+mechanism, not individually live-tested); the 14-vs-8 unguarded-count boundary (depends on value-cell definition).
- **LOW**: monolith consumer inheritance (UK-4, cross-repo, no in-repo manifest).

---

## 10. Acid-Test Self-Check

*Can remediation-planner rank and prioritize using only this assessment + prior artifacts, without
re-evaluating any structural concern?* — YES. Every risk register entry (AP-1..AP-5) has: stacked
anti-pattern count, severity, impact/effort leverage with class (quick-win/strategic/long-term),
file:line evidence, and a false-positive-gate disposition. The path-dependent cell count (10 schema,
8 backstop-less), drift-sweep hits (3: discount + 2 new), and unguarded value-field count (14, or 8
numeric) are enumerated with receipts. Open decisions are isolated as UK-1..UK-5. The G-THEATER
canary fires RED=571 on the headline edge — the assessment is grounded, not theatrical. The proposed
FPC coherence invariant fires RED on the 571-gun, satisfying the GRANDEUR ANCHOR's proof condition.
