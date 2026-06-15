---
type: review
status: draft
role: dependency-analyst
depth: DEEP-DIVE
upstream: fpc-topology-inventory-2026-06-09.md
date: 2026-06-09
head: 50ebfe3381a627df868887ca3cdf9e223e1f9a90
---

# FPC Dependency Map — The Field-Cascade Waterfall Graph

> **Role**: dependency-analyst (DEEP-DIVE). Maps the WATERFALL dependency graph of field
> resolution across entity-frames. Records what IS coupled and how widely it fans out;
> does NOT judge whether coupling is acceptable (structure-evaluator) nor propose decoupling
> (remediation-planner).
> **Scope**: READ-ONLY over origin/main + S3 + /tmp/u8o,/tmp/u8u parquet. No src/ edits.
> **HEAD**: `origin/main = 50ebfe3381a627df868887ca3cdf9e223e1f9a90` (verified `git rev-parse origin/main`).
> **G-THEATER canary**: coherence invariant `offer.mrr[phone] == unit.mrr[phone]` fires **RED = 571**
> (re-run THIS pass: `gun=571`, `total_joined_phones=2001`). The map is credible only because
> the headline coupling edge (offer.mrr ⟵cascade⟵ unit.mrr) carries this live RED.
> **Unit of analysis**: the field-resolution edge — a directed `(consumer-cell) ⟵ (source-cell)` arc.

---

## 0. Method & Provenance (how the graph was constructed)

The dependency graph is **field-cascade-shaped**, not repo-shaped. The "repos" of the arch
taxonomy map onto **entity-frames** (materialized DataFrame schemas) within the data plane,
plus the cross-repo **monolith consumers** (payments / ad_reporting) that read the warmed
frames downstream. Edges are derived mechanically:

- **Cascade edge** `consumer.field ⟵ source.field`: every ColumnDef with `source="cascade:X"`
  creates a directed edge from the consuming entity-cell to the canonical Source node, traversed
  by `CascadingFieldResolver.resolve_async()` up the parent task chain
  (`git show origin/main:src/autom8_asana/dataframes/resolver/cascading.py:199-269`,
  "Traverse parent chain to find field value").
- **Aggregate edge** `holder ⟵ leaf`: every HOLDER descriptor with `holder_for="X"` depends on
  the leaf entity's cells (`entity_registry.py` HOLDER blocks).
- **Join edge** (the materialization-time coupling): `entity_registry.py` `join_keys` declares
  which entity-frames are joined on which key — this is the structural channel the cascade rides.
- **Monolith-consumer edge**: payments/ad_reporting read the warmed S3 frames (cross-repo) — these
  are NOT in this repo's manifests, so they are LOW-confidence (inferred from the financial column
  set + warm config), flagged as Unknowns for cross-repo confirmation.

Confidence rating per `[PLATFORM-HEURISTIC: Confidence rating thresholds]`:
- **HIGH** = explicit declaration: `source="cascade:X"` line, `join_keys` tuple, `holder_for` field.
- **MEDIUM** = pattern match + structural corroboration (e.g. dual-source `cascade:Vertical`
  resolution precedence inferred from warm_priority).
- **LOW** = text/inference only (cross-repo monolith consumers; no manifest in this repo).

---

## 1. Source Nodes (where each field's canonical value originates)

A **Source node** is the (entity, field) cell that is the canonical origin of a value — i.e.
a `source="cf:X"` Direct cell that one or more `cascade:X` cells resolve back to. Receipts are
schema `source=` lines at origin/main.

| Source node (entity.field) | mode at source | canonical-source receipt | downstream consumers (cascade/aggregate) |
|---|---|---|---|
| **business.office_phone** | Direct `cf:Office Phone` | `schemas/business.py:24-27` (`source="cf:Office Phone"`) | unit, offer, contact, project, section, asset_edit, asset_edit_holder, process (+9 pipeline variants) |
| **business.name** (→ `office`) | Derived `source=None` (.name) | `schemas/business.py:17-20` | unit.office, offer.office (`cascade:Business Name`) |
| **unit.vertical** | Direct `cf:Vertical` | `schemas/unit.py:60-64` (`source="cf:Vertical"`) | offer, contact, project, section, asset_edit, process (`cascade:Vertical`) |
| **unit.mrr** ★ | Direct `cf:MRR` | `schemas/unit.py:11-16` (`source="cf:MRR"`) | offer.mrr (`cascade:MRR`), offer_holder (Aggregate), + monolith payments/ad_reporting (LOW) |
| **unit.weekly_ad_spend** ★ | Direct `cf:Weekly Ad Spend` | `schemas/unit.py:17-22` (`source="cf:Weekly Ad Spend"`) | offer.weekly_ad_spend (`cascade:Weekly Ad Spend`), + monolith ad_reporting (LOW) |

> ★ = NUMBER-typed Source node — the path-asymmetry-vulnerable class (server returns
> `number_value` differently on the list-fetch path vs the per-task-GET path; see §5).

**Note on `vertical` dual-source.** `offer.vertical` and the LEAF `cascade:Vertical` cells carry
the schema comment "Cascades from Unit **or** Business ancestor (warm_priority=2/1)"
(`schemas/offer.py` vertical block; `entity_registry.py:451-456` business + `:478-482` unit
both declare `office_phone`/`vertical`-bearing key sets). Source node assigned to **unit.vertical**
(Direct `cf:Vertical` lives on unit; business has no `vertical` ColumnDef in `schemas/business.py`).
Resolution precedence (which ancestor wins) is resolver behavior — carried forward as Unknown U-3.

---

## 2. Adjacency Table (the full waterfall graph)

Directed edge = `consumer.cell ⟵ source.cell`. Edge-kind: **C**=Cascade (parent-chain traversal),
**A**=Aggregate (holder-of-leaf), **J**=Join-only (materialization join, no field cascade).
Join-key column carried on every edge. Confidence per §0.

| # | consumer (entity.field) | ⟵ source (entity.field) | kind | join key | edge receipt | conf |
|---|---|---|---|---|---|---|
| E1 | unit.office_phone | business.office_phone | C | office_phone | `schemas/unit.py:51-58` `cascade:Office Phone`; `entity_registry.py:478` `("business","office_phone")` | HIGH |
| E2 | unit.office | business.name | C | office_phone | `schemas/unit.py:45-50` `cascade:Business Name` | HIGH |
| E3 | offer.office_phone | business.office_phone | C | office_phone | `schemas/offer.py` office_phone block `cascade:Office Phone`; `entity_registry.py:525` `("business","office_phone")` | HIGH |
| E4 | offer.office | business.name | C | office_phone | `schemas/offer.py` office block `cascade:Business Name` | HIGH |
| E5 | offer.vertical | unit.vertical (or business) | C | office_phone | `schemas/offer.py` vertical block `cascade:Vertical` "from Unit or Business" | MEDIUM |
| **E6** | **offer.mrr** ★ | **unit.mrr** ★ | **C** | **office_phone** | `schemas/offer.py` mrr block `cascade:MRR` "Cascades from Offer's ancestor Unit"; `entity_registry.py:523` `("unit","office_phone")` | **HIGH** |
| E7 | offer.weekly_ad_spend ★ | unit.weekly_ad_spend ★ | C | office_phone | `schemas/offer.py` weekly_ad_spend block `cascade:Weekly Ad Spend` | HIGH |
| E8 | contact.office_phone | business.office_phone | C | office_phone | `schemas/contact.py:77-80`; `entity_registry.py:504` `("business","office_phone")` | HIGH |
| E9 | contact.vertical | unit.vertical | C | office_phone | `schemas/contact.py:84-87` `cascade:Vertical` | MEDIUM |
| E10 | project.office_phone | business.office_phone | C | office_phone | `schemas/project.py:31-34` `cascade:Office Phone` | HIGH |
| E11 | project.vertical | unit.vertical | C | office_phone | `schemas/project.py:38-41` `cascade:Vertical` | MEDIUM |
| E12 | section.office_phone | business.office_phone | C | office_phone | `schemas/section.py:34-37` `cascade:Office Phone` | HIGH |
| E13 | section.vertical | unit.vertical | C | office_phone | `schemas/section.py:41-44` `cascade:Vertical` | MEDIUM |
| E14 | asset_edit.office_phone | business.office_phone | C | office_phone | `schemas/asset_edit.py:80-83` `cascade:Office Phone` | HIGH |
| E15 | asset_edit.vertical | unit.vertical | C | office_phone | `schemas/asset_edit.py:71-74` `cascade:Vertical` | MEDIUM |
| E16 | asset_edit_holder.office_phone | business.office_phone | C | office_phone | `schemas/asset_edit_holder.py:19-22` `cascade:Office Phone` (SOLE key — "100% cascade dependency") | HIGH |
| E17 | process.office_phone | business.office_phone | C | office_phone | `schemas/process.py:18-21` `cascade:Office Phone` | HIGH |
| E18 | process.vertical | unit.vertical | C | office_phone | `schemas/process.py:27-30` `cascade:Vertical` | MEDIUM |
| E19 | process_{sales,outreach,onboarding,implementation,month1,retention,reactivation,account_error,expansion}.office_phone | business.office_phone | C | office_phone | 9 pipeline variants share `process.py` schema; `entity_registry.py:572-692` `key_columns=("office_phone","vertical")` | HIGH |
| E20 | process_{…9 variants}.vertical | unit.vertical | C | office_phone | same 9 variants | MEDIUM |
| **E21** | **offer_holder** (Aggregate) | **offer** (incl. offer.mrr) | **A** | office_phone (parent_entity=unit) | `entity_registry.py:830-839` `parent_entity="unit"`, `holder_for="offer"` | HIGH |
| E22 | unit_holder (Aggregate) | unit (incl. unit.mrr) | A | office_phone (parent_entity=business) | `entity_registry.py:735-744` `parent_entity="business"`, `holder_for="unit"` | HIGH |
| E23 | contact_holder (Aggregate) | contact | A | office_phone (parent_entity=business) | `entity_registry.py:721-730` `holder_for="contact"` | HIGH |
| E24 | process_holder (Aggregate) | process | A | (parent_entity=unit) | `entity_registry.py:844-853` `holder_for="process"` | HIGH |
| E25 | location_holder (Aggregate) | location | A | (parent_entity=business) | `entity_registry.py:749-758` `holder_for="location"` | HIGH |
| **EM1** | **payments-monolith.\*** | **unit.mrr / offer.mrr** ★ | C (cross-repo read) | office_phone (S3 frame) | financial column set + offer-only population floor `post_build_population_receipt.py:60-62` `{"offer":("mrr","offer_id")}` | **LOW** |
| **EM2** | **ad_reporting-monolith.\*** | **unit.weekly_ad_spend / offer.weekly_ad_spend** ★ | C (cross-repo read) | office_phone (S3 frame) | weekly_ad_spend column set; no in-repo manifest | **LOW** |

**Reverse-join note (directionality, E6/E21).** `entity_registry.py` declares `offer.join_keys`
contains `("unit","office_phone")` (`:523`) AND `unit.join_keys` contains `("offer","office_phone")`
(`:480`). This is a **bidirectional join declaration** on `office_phone`. The *field cascade*
(E6 offer.mrr ⟵ unit.mrr) is **unidirectional** (offer reads unit; unit does not read offer.mrr).
The reverse arc `unit→offer` in join_keys is the offer_holder aggregation path (E21:
offer_holder.parent_entity=unit), NOT a value-cascade. Directionality check (§4) resolves this:
the *cascade graph* is acyclic; the *join declaration* is symmetric-by-design for holder rollup.
No value-resolution cycle exists.

---

## 3. Ranked Fan-Out / Blast Radius (coupling hotspots)

Blast radius = number of distinct consuming entity-frames that depend (transitively, via cascade
or aggregate) on a Source node. This is the leverage metric: **fix the Source once → all consumers
heal**; **leave it broken → every consumer carries the null**. Highest fan-out = highest-leverage
coupling hotspot.

| rank | Source node | direct consumers | transitive (incl. holders + monolith) | blast radius | edges | hotspot class |
|---|---|---|---|---|---|---|
| **1** | **business.office_phone** | unit, offer, contact, project, section, asset_edit, asset_edit_holder, process | + 9 process-pipeline variants + every HOLDER (keyed on office_phone) + monolith frames | **~26 frames** | E1,E3,E8,E10,E12,E14,E16,E17,E19,+holders | **STRUCTURAL keystone** — the universal join key; the single most-depended-on cell in the lattice |
| **2** | **unit.vertical** | offer, contact, project, section, asset_edit, process | + 9 process-pipeline variants | **~16 frames** | E5,E9,E11,E13,E15,E18,E20 | dual-source cascade (Unit-or-Business); 2nd-widest |
| **3** | **unit.mrr** ★ | offer.mrr (E6) | + offer_holder Aggregate (E21) + payments/ad_reporting monolith (EM1) | **3+ frames (1 in-repo cascade, 1 holder, ≥1 monolith)** | **E6, E21, EM1** | **THE HEADLINE — the 571-gun.** Highest *economic* leverage despite narrower frame-count; carries live RED |
| 4 | business.name (→office) | unit.office, offer.office | — | 2 frames | E2, E4 | low; cosmetic-string cascade |
| 5 | unit.weekly_ad_spend ★ | offer.weekly_ad_spend (E7) | + monolith ad_reporting (EM2) | 2+ frames | E7, EM2 | sibling of #3; same number+cascade defect shape, no population floor |

### Hotspot interpretation (coupling-context three-check gate applied)

Per `[PLATFORM-HEURISTIC: Coupling context checks]` — bounded-context, intentionality, and
directionality evaluated BEFORE flagging severity:

- **#1 business.office_phone — bounded-context-aligned, INTENTIONAL, unidirectional.** This is the
  designed universal join key (`key_columns=("office_phone",...)` on every descriptor). High fan-out
  here is **domain cohesion**, not incidental coupling — the entire lattice is deliberately keyed on
  the business phone. Recorded as the structural keystone; coupling is by-design. (Whether the
  single-key design is *acceptable* is structure-evaluator's call, not mine.)
- **#2 unit.vertical — INTENTIONAL but dual-source (MEDIUM directionality flag).** The "Unit OR
  Business ancestor" resolution introduces a precedence ambiguity (U-3). Cascade itself is
  unidirectional and designed.
- **#3 unit.mrr — INTENTIONAL cascade, unidirectional, but EMPIRICALLY BROKEN at the source.**
  The coupling is designed (offer.mrr is explicitly `cascade:MRR` "from ancestor Unit"). It is the
  hotspot of record not because the coupling is incidental but because the **Source cell is
  0/3021 nonnull** (`read_parquet('/tmp/u8u/*.parquet')`: total=3021, nonnull_mrr=0) while the
  consumer offer.mrr is **1325/4070 nonnull** — the cascade reads null-from-source for the 571
  phones where offer has a value the unit source lacks. This is the coherence violation the canary
  fires on. Leverage: a single Source-cell fix (unit.mrr fetch/path) propagates to offer.mrr +
  offer_holder + every monolith consumer. **Narrowest frame-count, highest economic blast radius.**

---

## 4. Coupling-Context Three-Check Gate (per repo-pair / edge class)

| edge class | (1) bounded-context | (2) intentionality | (3) directionality | coupling verdict (descriptive) |
|---|---|---|---|---|
| office_phone cascade (E1,E3,E8,E10,E12,E14,E16,E17,E19) | YES — all share the business-keyed bounded context | DESIGNED (`cascade:Office Phone` explicit contract) | UNIDIRECTIONAL (leaf→business) | intentional-cohesion cascade; data-coupling on a shared key |
| vertical cascade (E5,E9,E11,E13,E15,E18,E20) | YES (same context) | DESIGNED but DUAL-SOURCE | UNIDIRECTIONAL, precedence-ambiguous | intentional; directionality flag on source-precedence (U-3) |
| **mrr cascade (E6)** | YES (unit↔offer share office_phone context) | **DESIGNED** (`cascade:MRR` explicit) | **UNIDIRECTIONAL** (offer←unit; join symmetric for holder only, NO value cycle) | **intentional cascade, source-broken** — coupling is correct-by-design; the defect is population, not coupling shape |
| weekly_ad_spend cascade (E7) | YES | DESIGNED | UNIDIRECTIONAL | same shape as E6 |
| Aggregate / holder (E21–E25) | YES (holder-of-leaf same context) | DESIGNED (`holder_for`) | UNIDIRECTIONAL (holder←leaf); registry join_keys reverse-arc is the rollup channel, not a cycle | intentional aggregation; stamp-coupling (whole-frame rollup) |
| monolith reads (EM1,EM2) | UNKNOWN (cross-repo; cannot confirm bounded context from this repo) | UNKNOWN | presumed unidirectional (monolith reads warmed frame) | **LOW-confidence; flagged U-1** |

**Cycle check (Acyclic Dependencies Principle).** No value-resolution cycle exists in the cascade
graph. The only bidirectional declaration is `unit↔offer` in `join_keys` (`entity_registry.py:480`
+ `:523`), which the directionality check resolves as: forward arc = E6 value cascade (offer←unit);
reverse arc = E21 holder aggregation (offer_holder←offer, parented at unit). Distinct channels;
**no circular field dependency.** [No structural-risk cycle to flag.]

---

## 5. Path-Asymmetry-Exposed Edge Set (the list-vs-get fetch boundary)

LIVE CORPUS defect-face (a): the same Asana custom field returns `number_value` differently on the
**list-fetch path** (`tasks_client.list_async(section, opt_fields=BASE_OPT_FIELDS)` →
`builders/parallel_fetch.py:576-578` `_fetch_section`) vs the **per-task-GET path**
(`tasks_client.get_async(gid, opt_fields=_HIERARCHY_OPT_FIELDS)` →
`cache/integration/hierarchy_warmer.py:93`). Both request `custom_fields.number_value`
**symmetrically** (list: `builders/fields.py:69`; get: `hierarchy_warmer.py:43`) — so the
divergence is **server-side**, NOT a missing opt_field. The exposed edges are exactly the
**NUMBER-typed Source cells AND any cascade edge whose source is a NUMBER-typed cell**, because the
cascade resolver fetches the ancestor via the **GET path** (`hierarchy_warmer._fetch_parent`) while
the entity's own frame is built via the **LIST path** (`parallel_fetch._fetch_section`).

### Path-asymmetry-exposed edges (the edges that cross the fetch boundary)

| edge | source cell (★number) | source fetched via | consumer built via | asymmetry exposure | conf |
|---|---|---|---|---|---|
| **E6 offer.mrr ⟵ unit.mrr** | unit.mrr (Decimal `cf:MRR`) | unit-frame: LIST path; cascade-ancestor: GET path (`hierarchy_warmer:93`) | offer-frame: LIST | **PRIMARY exposed edge** — unit.mrr live 0/3021 on its own LIST frame; offer.mrr cascade pulls the GET-path ancestor and lands 1325/4070. The 571 mismatch is this boundary | HIGH |
| E7 offer.weekly_ad_spend ⟵ unit.weekly_ad_spend | unit.weekly_ad_spend (Decimal) | LIST (frame) / GET (cascade) | LIST | exposed — same shape as E6, untested by canary | HIGH |
| E21 offer_holder ⟵ offer.mrr | offer.mrr (cascade Decimal) | aggregates the already-cascaded offer.mrr | A | TRANSITIVELY exposed (inherits E6) | MEDIUM |
| EM1 payments ⟵ unit.mrr/offer.mrr | ★ | reads warmed S3 frame (whichever path wrote it) | cross-repo | exposed downstream; consumes whichever value the warm path materialized | LOW |

### Same-field NUMBER cells NOT on a cascade boundary (exposed at frame-build, single-path)

These are NUMBER-typed Direct cells whose value comes from ONE path (the frame's own LIST build);
they are path-asymmetry-*vulnerable* (a future GET-path read would diverge) but not currently
*cascade-boundary-crossing*. Recorded for completeness (the FPC opt_fields derivation must cover them):

- `unit.mrr` ★ (Direct `cf:MRR`, `schemas/unit.py:11-16`) — the Source cell; vulnerable at its own build.
- `unit.weekly_ad_spend` ★, `unit.discount` ★ (`schemas/unit.py`).
- `offer.cost` ★ (`schemas/offer.py` cost block, `cf:Cost` Number — note schema dtype=Utf8 type-drift).
- `asset_edit.{offer_id, score, template_id, videos_paid}` ★ (`schemas/asset_edit.py:127,148,162,169`) —
  all Int64/Float64 Number cells; needs-per-task-GET per topology §3.7. No cascade edge, so not
  boundary-crossing, but path-asymmetry-vulnerable.

---

## 6. Shared Model Registry (cells/contracts appearing in ≥2 entity-frames)

A field that appears in multiple schemas is a **shared contract**. Divergence between its
appearances is a coherence risk. Source of truth = the canonical Source node (§1).

| shared field | appears in (frames) | shape | shared-or-diverged | receipt |
|---|---|---|---|---|
| **office_phone** | business (Direct), unit, offer, contact, project, section, asset_edit, asset_edit_holder, process (+9 variants) — Cascade in all but business | Utf8 everywhere | **SHARED, aligned** (single Source: business.office_phone) | all `cascade:Office Phone` + `schemas/business.py:24-27` |
| **vertical** | unit (Direct `cf:Vertical`), offer/contact/project/section/asset_edit/process (Cascade) | Utf8 everywhere | **SHARED, aligned dtype; AMBIGUOUS source** (Unit-or-Business) | `schemas/unit.py:60-64` + cascade blocks |
| **mrr** ★ | unit (Direct, Decimal `cf:MRR`), offer (Cascade, Decimal `cascade:MRR`) | Decimal both | **SHARED dtype-aligned; DIVERGED population** (unit 0/3021, offer 1325/4070) | `schemas/unit.py:11-16` + `schemas/offer.py` mrr block |
| **weekly_ad_spend** ★ | unit (Direct), offer (Cascade) | Decimal both | SHARED dtype-aligned; population untested | `schemas/unit.py:17-22` + offer block |
| **office** | unit (Cascade `cascade:Business Name`), offer (Cascade) | Utf8 both | SHARED (Source: business.name) | `schemas/unit.py:45-50` + `schemas/offer.py` office block |
| **offer_id** | offer (Direct Utf8 `cf:Offer ID`), asset_edit (Direct Int64 `cf:Offer ID`) | **Utf8 vs Int64 — DTYPE DIVERGENCE** | **DIVERGED type** — same `cf:Offer ID` field, two dtypes across frames | `schemas/offer.py` offer_id block (Utf8) + `schemas/asset_edit.py:127-130` (Int64) |
| **specialty** | unit, offer, contact, asset_edit (+asset_edit_specialty) | Utf8 / List[Utf8] mixed | DIVERGED cardinality (scalar vs list) | per-schema specialty blocks |
| **status** | project, section, asset_edit | Utf8; project/section `cf:Status` (FM-2 fix), asset_edit `cf:Status` enum | SHARED name, different source-field semantics | `schemas/project.py:27`, `section.py:30`, `asset_edit.py:44` |

**Headline shared-model coherence break**: `mrr` is the shared contract whose two appearances
(unit Direct, offer Cascade) DIVERGE in population — the exact substrate of the 571-gun. The
`offer_id` Utf8↔Int64 divergence is a second, independent shared-model drift (cross-frame dtype).

---

## 7. Integration Pattern Catalog (how the cascade communicates)

| pattern | mechanism | edges | receipt |
|---|---|---|---|
| **Parent-chain cascade (synchronous resolve)** | `CascadingFieldResolver.resolve_async()` traverses parent task chain up to max_depth=5 | all C edges (E1–E20) | `resolver/cascading.py:199-269` |
| **Pre-warmed parent cache (batch)** | `hierarchy_resolver` pre-fetches parent chains via `hierarchy_warmer` GET path; cascade reads cache instead of N+1 GETs | E6,E7 (number cascades ride this) | `hierarchy_warmer.py:93` `get_async`; `cascading.py:146-191` |
| **Unified-cache plugin delegation** | when `cascade_plugin` present, `resolve_async` delegates to `CascadeViewPlugin.resolve_async()` | all C edges (alt path) | `cascading.py:228-238` |
| **Holder aggregation (rollup)** | HOLDER frame aggregates leaf rows under a parent entity | A edges (E21–E25) | `entity_registry.py` `holder_for`/`parent_entity` |
| **Join-on-key materialization** | frames joined on `join_keys` at build time | all (the channel cascades ride) | `entity_registry.py` `join_keys` tuples |
| **Warmed-S3-frame read (cross-repo, async/batch)** | monolith consumers read materialized parquet from S3 | EM1,EM2 | LOW — inferred; no in-repo manifest |
| **Population-floor receipt** | post-build floor populates declared value columns (offer-only) | guards E6 consumer side | `builders/post_build_population_receipt.py:60-62` `{"offer":("mrr","offer_id")}` |

---

## 8. Unknowns (dependency-analyst flags; downstream to resolve)

### Unknown U-1: Monolith consumer edges (EM1/EM2) cannot be confirmed from this repo
- **Question**: Do payments / ad_reporting monoliths read `unit.mrr`/`offer.mrr`/`weekly_ad_spend`
  directly from the warmed S3 frames, and via which key/path?
- **Why it matters**: These are the widest *economic* blast-radius edges for the 571-gun — if they
  read offer.mrr (cascade output) they inherit the coherence break; the fan-out rank of unit.mrr
  depends on their count.
- **Evidence**: financial column set + offer-only population floor (`post_build_population_receipt.py:60-62`)
  implies a downstream economic consumer; NO manifest/import in autom8y-asana declares it.
- **Confidence**: LOW (inference only). **Suggested source**: payments/ad_reporting repo manifests
  (cross-repo); per cross-rite routing, noted for remediation-planner to route.

### Unknown U-2: offer_id Utf8↔Int64 cross-frame dtype divergence (active or benign?)
- **Question**: Is `offer.offer_id` (Utf8) ⟷ `asset_edit.offer_id` (Int64) a join hazard, or are
  these never joined on offer_id?
- **Why it matters**: A shared `cf:Offer ID` field materialized as two dtypes silently fails any
  cross-frame join keyed on offer_id (coercer null-on-cast).
- **Evidence**: `schemas/offer.py` offer_id (Utf8) vs `schemas/asset_edit.py:127-130` (Int64);
  `asset_edit.key_columns` includes `offer_id` (`entity_registry.py:547`).
- **Confidence**: HIGH (both dtypes declared). **Suggested source**: structure-evaluator (boundary
  alignment) — is offer↔asset_edit an intended join edge?

### Unknown U-3: vertical cascade source-precedence (Unit vs Business)
- **Question**: When both a Unit ancestor and a Business ancestor carry `Vertical`, which wins?
- **Why it matters**: Determines whether the FPC coherence invariant for `vertical` is single- or
  multi-source; affects fan-out #2's source-node assignment.
- **Evidence**: `schemas/offer.py` vertical block "Cascades from Unit or Business ancestor"; resolver
  traverses parent chain "until field found" (`cascading.py:205-219`) — first-ancestor-wins is
  *implied* but not confirmed for the dual-key case.
- **Confidence**: MEDIUM. **Suggested source**: `resolver/cascading.py` traversal-order test.

### Unknown U-4: process base (S3=0) and 5 un-warmed entities — edges present, cells un-materialized
- **Question**: offer_holder/unit_holder/contact_holder/location/hours have descriptors + Aggregate
  edges (E21–E25) but S3 census=0 — are these edges live-but-cold or dead?
- **Why it matters**: The offer_holder Aggregate edge (E21) is in the unit.mrr blast radius; if it
  is never warmed, the economic blast radius of unit.mrr is currently *latent* (would activate on
  warm). Affects whether the 571-gun has reached the holder consumer.
- **Evidence**: `entity_registry.py:830-839` offer_holder descriptor present; topology §6 S3 census=0
  for these entities.
- **Confidence**: HIGH (descriptors) / MEDIUM (warm-state). **Suggested source**: hierarchy_warmer
  warm-set config / warm_priority gaps.

---

## 9. Confidence Ratings (per finding class)

- **HIGH** — all Cascade edges with an explicit `source="cascade:X"` line + a `join_keys` tuple
  (E1–E4, E6, E7, E8, E10, E12, E14, E16, E17, E19, E21–E25); the office_phone keystone fan-out;
  the mrr shared-model divergence; the offer_id dtype divergence; the symmetric `number_value`
  opt_field on both fetch paths.
- **HIGH (live)** — the 571-gun (`gun=571`, 2001 joined phones), unit.mrr 0/3021, offer.mrr
  1325/4070 — DuckDB receipts re-run THIS pass over /tmp/u8u + /tmp/u8o.
- **MEDIUM** — `cascade:Vertical` edges (E5, E9, E11, E13, E15, E18, E20) — dual-source precedence
  unconfirmed; offer_holder transitive exposure (E21).
- **LOW** — monolith consumer edges (EM1, EM2) — inferred from financial column set + offer-only
  population floor; no in-repo manifest. Flagged U-1.

---

## 10. Acid-Test Self-Check

*Can structure-evaluator assess boundary alignment + anti-patterns using only this map + the
topology-inventory, without re-tracing any cross-entity relationship?* — YES: every cascade/aggregate
edge has a classified integration pattern (§7), a coupling verdict via the three-check gate (§4), a
fan-out rank (§3), and a confidence rating (§9). The path-asymmetry boundary (§5) is enumerated.
Open boundary questions are isolated as U-1..U-4 (§8). The G-THEATER canary fires RED on the headline
edge (E6), so the map is grounded, not theatrical.
