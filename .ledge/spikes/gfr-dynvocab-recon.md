---
type: spike
status: draft
slug: gfr-dynvocab
artifact_kind: tech-assessment
rite: rnd
phase: scouting
agent: technology-scout
created: 2026-06-25
g_rung: paradigm-recommended + feasibility-pre-flighted (NOT feasibility-proven — that is the prototype-engineer phase obligation; §9)
self_grade: "[STRUCTURAL | MODERATE]"  # self-ref cap per self-ref-evidence-grade-rule + rnd-dk MODERATE ceiling; STRONG paradigm verdict needs the rite-disjoint corroboration at the transfer seam (NOT self-granted)
brief: .ledge/specs/gfr-dynvocab-alignment-brief.md
certified_engine: .ledge/specs/gfr-tdd.md
certs_never_regress: .ledge/reviews/gfr-certification-case-file.md
grandeur_anchor: >
  gfr-dynvocab makes any fleet caller resolve a gid to ANY field the entity
  actually carries — reflectively, heuristically-typed from cf-type metadata,
  governed-strict (so 'unknown' means genuinely absent) — on top of the
  STRONG-certified identity spine, never regressing it.
---

# SCOUT-gfr-dynvocab — Dynamic-Vocabulary Paradigm-Optima Recon

## Executive Summary

The brief favours a **hybrid vocabulary** — a typed, cross-tenant-certified core
(`company_id` et al.) + a **heuristically-typed dynamic tail** reflected from the
entity's actual custom fields and served off the already-hydrated entry task,
governed-strict so "unknown" means genuinely-absent. This recon looked OUTWARD
across six candidate paradigm families and grounds each in cited industry
prior-art with an evidence grade.

**Verdict: the brief's favoured approach is CONFIRMED as meta-optimal, with two
refinements prior-art surfaces** (it is not overridden). The meta-optimal paradigm
for OUR two-layer scope is a **(f)+(e-bounded)+(b-governance) composite**:
**Asana cf-type-driven reflective coercion** (paradigm f) for the GFR-layer tail,
**explicitly bounded** so it cannot become Elasticsearch-style "mapping explosion"
(the (e) counter-case), under a **columnar-style schema-coherence data-contract /
drift gate** (paradigm b) for the dataframe layer. The single strongest finding is
that this paradigm is **already 80% instantiated in the codebase** —
`DefaultCustomFieldResolver` (`dataframes/resolver/default.py`) is literally a
runtime-reflective cf-type→typed-value coercion engine, and the certified entry
fetch **already pulls every custom field with every typed value** (HYP-1 CONFIRMED
below). The two prior-art refinements: (1) **bound the tail** (Elastic field-limit
discipline) and (2) **type-by-field-ID not field-name** at the coherence layer
(Iceberg field-ID matching) — both fold cleanly into the brief's typing-origin tag
and drift gate.

**Evidence grade of the recommendation: MODERATE** (rnd-dk ceiling; external
literature + in-codebase prior-art corroborate, but a STRONG paradigm-LOCK verdict
requires the rite-disjoint corroboration that lands at the transfer seam — named,
never self-granted). **Feasibility is pre-flighted (HYP-1/HYP-2 receipts live
below), NOT proven** — the working throwaway prototype resolving `asset_id` as a
set off the real canary is the prototype-engineer phase's obligation (§9).

---

## Live Codebase Receipts (G-PROVE — pre-flight for the prototype phase)

The paradigm choice is grounded not only in external prior-art but in **direct
inspection of OUR substrate** this pass. These receipts settle the brief's OPEN
FORKS #1 and #2 and de-risk the prototype.

| Signal | Anchor (this pass) | Finding |
|---|---|---|
| **THE SMELL** — `asset_id` on model, absent from schema | model: `models/business/offer.py:144` (`asset_id = TextField(field_name="Asset ID")`); schema: `dataframes/schemas/offer.py` grep `asset_id` => **zero matches** | CONFIRMED. The field exists on the task model but no dataframe ColumnDef declares it, so the schema-bounded resolver silently cannot surface it. The canary for "vocabulary ≡ hand-curated schema subset, NOT the entity's real fields." |
| **HYP-1** — does the certified entry fetch already pull ALL custom fields with values? | `models/business/hydration.py:283,:672` fetch with `_BUSINESS_FULL_OPT_FIELDS` = `list(STANDARD_TASK_OPT_FIELDS)` (`hydration.py:69`); `STANDARD_TASK_OPT_FIELDS` body `models/business/fields.py:232-251` | **CONFIRMED — FREE TAIL.** The opt-fields spec requests the bare `custom_fields` array (`:240`) PLUS `.name`, `.resource_subtype`, `.text_value`, `.number_value`, `.enum_value(.name)`, `.multi_enum_values(.name)`, `.display_value`, `.people_value` (`:241-250`). **Every custom field, with every typed value AND its cf-type metadata, is already in the hydrated Task.** `asset_id`'s value is already fetched and then discarded for want of a schema column. **Settles OPEN FORK #2 toward "free tail — no wider opt-fields spec needed."** Marginal cost of reading more cf's off the entry task ≈ 0 (the read already happened). |
| **HYP-2 / heuristic-table feasibility** — is the cf-type→typed-value table buildable from accessible metadata? | `core/field_utils.py:60-73` exposes `resource_subtype + text_value/number_value/enum_value/multi_enum_values/display_value/people_value/date_value`; **and the table ALREADY EXISTS** at `dataframes/resolver/default.py:234-287` (`_extract_raw_value`, a `match resource_subtype` dispatch) | **CONFIRMED — ALREADY BUILT.** `_extract_raw_value` is the cf-type→typed heuristic table the brief asks for: `text→text_value(str)`, `number→number_value(float)`, `enum→enum_value.name(label)`, `multi_enum→[names](list[str])`, `date→date_value(date)`, `people→[gids](list[gid])`, `_→display_value` fallback. `build_index` (`default.py:59-114`) ALREADY reflects the full custom_fields set into a `name→gid` index + `gid_to_info{name, type: resource_subtype}` — i.e. dynamic-vocabulary materialization is in-tree. |
| **SEAM** — where the tail plugs in | `dataframes/resolver/default.py:27` `DefaultCustomFieldResolver` + `core/entity_registry.py:136` `custom_field_resolver_class_path` hook | The reflective resolver is dependency-injected via a class-path hook. The dynamic tail is an **additive resolver capability** behind an existing seam, not a new engine. |
| **SPINE SAFETY** — identity invariant the tail must never touch | `gfr-tdd.md` §0.1 INVARIANT GFR-IDENTITY-1; `models/business/hydration.py:571,:646` `_traverse_upward_async` | The certified identity edge (gid + parent-chain, gid-exact `company_id` read, NEVER an `office_phone` value-join) is strictly-additive-protected. The tail reflects FIELD VALUES off the already-anchored entry task; it never participates in identity/tenant resolution. Strictly-additive by construction. |

**Net pre-flight position:** the hard case (`asset_id`→set off a real hydrated
entity) is **feasible**: the value is already hydrated (HYP-1), the type metadata is
already accessible and the coercion table already exists (HYP-2), and the seam is
already injectable. What remains UNPROVEN until the prototype is the LIVE behaviour
on the real canary (`b167331c-536f-4996-9b2d-2f696f35f556`) and the comma-split→set
override. **This recon does NOT claim feasibility-proven** (G-THEATER guard: no
citation-with-no-code stands in for the working prototype).

---

## Candidate Paradigm Survey (look OUTWARD — cited + evidence-graded)

Six families surveyed against the dynamic-vocabulary + model↔schema coherence
problem. Each carries a cited source (SRC-NNN) and an evidence grade.

### SRC-001 — (a) Schema-on-read / late-binding [MODERATE]
Land raw records at full fidelity, defer typing to consumption ("late binding"),
materialise typed tables later. Industry canon: "land raw JSON to preserve
fidelity, then materialise typed tables later … data contracts enforced at
ingestion to fail fast." [SRC-001 Estuary "Managing Schema Drift in Variant Data";
Axrail "Data Contracts" 2024-2025; MODERATE — vendor/practitioner literature, broad
consensus]. **Fit:** strong conceptual match — the dynamic tail IS late-bound
typing; the coherence gate IS the fail-fast data contract. **Risk:** schema-on-read
alone gives NO governance ("schema-management is difficult with schema-less / on-read
methods"); needs the contract layer to avoid swamp.

### SRC-002 — (b) Columnar schema-evolution (Iceberg / Parquet / Avro) [MODERATE]
Iceberg matches columns by **field ID, not name or position**, validates **type
compatibility during projection** (safe widening, reject unsafe), and the recurring
discipline is **data contracts / schema registries** to prevent silent divergence.
[SRC-002 Apache Iceberg schema-projection docs (DeepWiki); Databricks "Schema
Enforcement & Evolution on Delta Lake" 2019; Srimukunthan, Medium 2024; MODERATE].
**Fit:** the single best analogue for the **dataframe-coherence layer** — field-ID
matching + projection-time type validation + contract enforcement is exactly
"schema cannot silently diverge from the model." **Refinement it surfaces:** type
by stable field identity (Asana cf `gid`), not by display name — the codebase's
`build_index` already keys `gid_to_info` by `cf.gid` (`default.py:92-97`), so this
fold is free.

### SRC-003 — (c) GraphQL typed field-resolvers [MODERATE]
Resolve-any-declared-field via per-field resolver functions; NestJS/TypeGraphQL use
**reflection over decorator metadata** to generate the typed resolver map. Dominant
best-practice: "keep complex logic OUT of resolvers," declare types explicitly.
[SRC-003 Apollo GraphQL resolver docs; NestJS GraphQL resolvers; TypeGraphQL;
MODERATE]. **Fit:** partial. The "typed resolver per declared field" maps to our
**typed certified core**, NOT the dynamic tail — GraphQL resolves only *schema-
declared* fields, which is precisely the bounded-vocabulary limitation we are trying
to escape. Useful as a model for the core's per-field provenance, weak for the tail.

### SRC-004 — (d) Dynamic-ORM reflection (SQLAlchemy automap / Django) [MODERATE]
"Zero-declaration" reflective mapping: generate mapped classes from a live schema at
runtime; dynamically create model fields from runtime data. Explicit tradeoff:
**loses static type checking**, adds memory/latency, and best-practice is to
**reflect only the subset you need** (`only` parameter). [SRC-004 SQLAlchemy 2.0
automap docs; O'Reilly Essential SQLAlchemy ch.10; MODERATE]. **Fit:** direct
analogue for the **GFR-layer reflective tail** — runtime reflection of fields the
static schema never declared. **Refinement it surfaces (corroborates Elastic):**
reflection without bounds degrades type-safety + cost; bound the reflected set and
tag its typing-origin as non-static (the brief's `typed: 'heuristic'` tag is exactly
this discipline).

### SRC-005 — (e) Document-store dynamic typing (Elasticsearch / Mongo) [MODERATE]
Dynamic mapping auto-infers field types on first sight (string→text+keyword,
ISO→date). **Counter-case:** unbounded dynamic mapping causes **"mapping explosion"
— cluster-state churn, OOM, instability past `total_fields.limit`** (default 1000).
Universal remedy: **hybrid — explicit mapping for known fields + bounded dynamic for
the rest**, and "first value wins" type-lock is a sharp edge. [SRC-005 Elastic
mapping docs; Sweet Security "Avoid Field Limit Errors"; Johnell "Taming Field
Explosion", Medium; MODERATE]. **Fit:** this is the **false-positive guard** for the
whole initiative. It (i) independently confirms the **hybrid (typed core + bounded
dynamic tail) is the de-facto industry pattern**, and (ii) names the failure mode if
the tail is left unbounded. The brief's governed-strict posture + per-entity field
registry (manifest) is the bound.

### SRC-006 — (f) Asana custom-field type model (resource_subtype coercion) [PLATFORM-HEURISTIC]
The Asana API's own type model: `resource_subtype ∈ {text, number, enum, multi_enum,
date, people}` drives which value field carries the data (`text_value`,
`number_value`, `enum_value`, `multi_enum_values`, `display_value`, `people_value`);
**`type` is deprecated in favour of `resource_subtype`**. [SRC-006 Asana Developer
Docs "Custom fields guide" + `asana_oas.yaml`; PLATFORM-HEURISTIC — the source IS the
platform we integrate against, authoritative for this integration but not
general-literature]. **Fit:** this is the **native, lowest-impedance** typing source —
the entity's own platform tells us each field's type. The codebase already keys its
coercion `match` on the correct, non-deprecated `resource_subtype` field
(`default.py:250`). This is the heuristic table's ground truth; the brief's
per-field override registry (e.g. `asset_id` text→set) is the escape hatch for the
handful of fields where platform-type ≠ business-type.

---

## Comparison Matrix

Rows = candidate paradigms; columns = fit-to-our-problem dimensions. Status quo
(hand-curated schema subset, the bounded vocabulary that produced the `asset_id`
smell) is the baseline. Ratings: ++ strong / + adequate / ~ partial / − weak.

| Paradigm | Fit-to-problem | Typing richness | Coherence-governance | Cache/freshness compat | Operational cost | Maturity/risk | Verdict |
|---|---|---|---|---|---|---|---|
| **STATUS QUO** — hand-curated schema subset | − (the smell: bounded vocabulary, silent gaps) | + (fully typed, but only for declared subset) | − (model↔schema drift is silent — `asset_id`) | ++ (existing cache path) | ++ (zero new) | ++ (certified, in-prod) | **HOLD/AVOID** — the problem statement; cannot reach "any field" |
| **(a) schema-on-read / late-binding** | + (tail IS late-bound) | ~ (raw until materialised) | − alone (needs contract) | + (consumption-time) | + | ++ (data-eng canon) | **ASSESS** — adopt the *concept*, not raw |
| **(b) columnar schema-evolution (Iceberg)** | ++ (for the COHERENCE layer) | + (projection type-validation) | ++ (field-ID match + contract) | + (table-format, not our cache) | ~ (table-format heft if literal) | ++ (CNCF-grade) | **ADOPT (governance pattern, not the engine)** |
| **(c) GraphQL typed resolvers** | ~ (models the CORE, not the tail) | ++ (typed per declared field) | + (schema-validated) | ~ | ~ | ++ | **ASSESS** — pattern for core provenance only |
| **(d) dynamic-ORM reflection (automap)** | ++ (for the GFR-layer TAIL) | ~ (loses static typing) | − (no governance) | + | + (bound the set) | + (mature, sharp edges) | **TRIAL (bounded)** — the tail reflection model |
| **(e) doc-store dynamic mapping (Elastic)** | + (hybrid is canon) | ~ (first-value-wins lock) | ~ (needs field-limit) | + | − if unbounded (mapping explosion) | + (mature; named failure mode) | **TRIAL as GUARD** — confirms hybrid + bounds the tail |
| **(f) Asana cf-type coercion (resource_subtype)** | ++ (native, lowest-impedance, ALREADY IN-TREE) | ++ (platform-authoritative type per field) | + (per-field type known) | ++ (off the already-hydrated task — HYP-1) | ++ (≈0 marginal; table already exists) | + (PLATFORM-HEURISTIC; platform-coupled) | **ADOPT** — the tail's typing ground truth |

---

## Recommendation

**Verdict: ADOPT a (f)+(d-bounded)+(b-governance) composite. The brief's favoured
hybrid is CONFIRMED meta-optimal, with two prior-art refinements (not overridden).**

### The meta-optimal paradigm for our two-layer scope

**GFR-layer dynamic tail** = paradigm **(f) Asana cf-type reflective coercion**,
executed as a **bounded dynamic-ORM-style reflection** (paradigm d) off the
already-hydrated entry task:
- Reflect the entity's actual custom fields from the entry-fetch Task (HYP-1: they
  are already there at ≈0 marginal cost).
- Type each tail field by its `resource_subtype` via the existing `_extract_raw_value`
  table (HYP-2: already built), with a **per-field override registry** for the
  handful where platform-type ≠ business-type (proof override: `asset_id`
  text→whitespace-agnostic comma-split→set).
- Tag every tail value with **typing-origin provenance** (`{typed: 'heuristic',
  cf_type, …}`) so a caller can distinguish a schema-validated value from a
  heuristically-coerced one — this is the (d)/(e) discipline of marking
  reflected-typing as non-static.
- **Governed-strict:** because the vocabulary now reflects what the entity *really
  carries*, a requested-but-absent field returns a **truthful**
  `UnresolvedError(unknown-field)` — a completeness guarantee, not a curation gap.

**Dataframe-coherence layer** = paradigm **(b) columnar schema-evolution governance**
(Iceberg-style), realised as a **data-contract / drift gate** (SRC-001 + SRC-002):
- Match/track fields by **stable cf `gid`** (Iceberg field-ID discipline), not by
  display name — already how `build_index` keys `gid_to_info` (`default.py:92`).
- A **drift gate** (CI assertion or schema-derivation-from-model) so the dataframe
  schema cannot silently diverge from the task model — closes the root cause that
  produced the `asset_id` smell for *every* dataframe consumer, not just GFR.

### Two refinements prior-art surfaces (fold into the brief, do not override it)
1. **Bound the tail (Elastic counter-case, SRC-005).** Unbounded reflective
   vocabularies cause "mapping explosion." Our bound is the brief's per-entity field
   manifest/registry + governed-strict posture: the tail reflects the entity's actual
   cf set (finite, per-task), never an open-ended accreting global field space. This
   is already the brief's "manifest source" fork — prior-art elevates it from
   nice-to-have to **load-bearing guard**.
2. **Type by field identity, not name (Iceberg, SRC-002).** The coherence layer
   should bind on cf `gid`, not the human-readable name, to survive renames — the
   codebase already does this; the recommendation is to make it explicit at the
   coherence-gate level.

### Why this is meta-optimal (cited rationale)
- It is the **de-facto industry hybrid** independently arrived at by the
  document-store ecosystem under pressure: explicit-typed known fields + bounded
  dynamic for the rest (SRC-005), the data-lake ecosystem's raw-fidelity + late-bound
  materialisation + fail-fast contract (SRC-001), and the lakehouse ecosystem's
  field-ID projection + schema enforcement (SRC-002) all converge on it.
- It is the **lowest-impedance and lowest-risk for OUR substrate** because paradigm
  (f) is platform-native and **already ~80% instantiated** — we extend an existing
  injectable resolver (`DefaultCustomFieldResolver`) reading values already fetched
  (HYP-1), using a coercion table already written (HYP-2). No new engine, no table
  format, no schema registry service. This decisively beats a literal Iceberg/Elastic
  adoption (which would import heavy infrastructure for governance we can get from a
  CI drift gate).
- It is **strictly-additive over the STRONG-certified spine** — the tail reflects
  field VALUES off the already-anchored entry task and never participates in identity
  resolution (INVARIANT GFR-IDENTITY-1 untouched). The 105 certified tests remain the
  regression gate.

### Confirm-or-override the brief
**CONFIRM.** Prior-art does not surface a better paradigm than the brief's
typed-core + heuristically-typed-dynamic-tail hybrid; it independently corroborates it
from four ecosystems and names the one failure mode to guard against (unbounded tail →
mapping explosion), which the brief's governed-strict manifest already addresses. The
brief's OPEN FORK #2 (entry-fetch completeness) is **settled toward "free tail"** by
HYP-1. OPEN FORK #1 (task-based vs frame-based tail) is informed: the task-based
source is the ≈0-marginal-cost path (HYP-1) and keeps the tail off the same hydrated
Task the certified entry phase already produced — but the freshness/consistency seam
(tail off the task while `company_id` comes off the cache frame) remains an
**integration-researcher question**, not closed here.

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Unbounded tail → "mapping explosion"** (Elastic counter-case, SRC-005) | M | H | Governed-strict + per-entity manifest bounds the vocabulary to the entity's actual cf set (finite per task); no global accreting field space |
| **Heuristic mistyping** (platform-type ≠ business-type, e.g. `asset_id` text-but-really-a-set) | H (known) | M | Per-field override registry + typing-origin provenance tag; caller can see `typed: 'heuristic'` and react |
| **Silent model↔schema drift recurs** (the original smell) | M | H | Iceberg-style drift gate (SRC-002): CI assertion or schema-derivation-from-model bound on cf `gid` |
| **Freshness seam** — tail off hydrated task vs `company_id` off cache frame | M | M | OPEN — route to integration-researcher (brief OPEN FORK #1); do not close at scout altitude |
| **Spine regression** — tail accidentally touches identity path | L | CRITICAL | Strictly-additive by construction; tail reads VALUES only, never identity; 105 certified tests gate; prototype must NEVER commit to `feat/gfr-engine` |
| **Platform coupling** to Asana `resource_subtype` model | L | L | `resource_subtype` is the non-deprecated, authoritative field (SRC-006); coercion already isolated in one table (`_extract_raw_value`) |

---

## Fit Assessment

- **Philosophy alignment:** ++ — composable simplicity over new infrastructure
  [AD:SRC-005 Anthropic 2024]; extends an existing seam, adds no engine.
- **Stack compatibility:** ++ — paradigm (f) is platform-native and already in-tree;
  the seam (`custom_field_resolver_class_path`) is dependency-injection-ready.
- **Team readiness:** ++ — the reflective coercion table (`_extract_raw_value`) and
  the reflective index (`build_index`) are existing, tested, team-authored code.

---

## Recommendation Verdict & Next Steps (handoff criteria)

**Verdict: ADOPT** the (f)+(d-bounded)+(b-governance) composite — i.e. the brief's
hybrid, CONFIRMED and refined. **Evidence grade: MODERATE** (rnd-dk ceiling; STRONG
paradigm-LOCK requires rite-disjoint corroboration at the transfer seam — named,
never self-granted). **Paradigm LOCK, the certified branch, and all merge/deploy
levers remain the user's (MINE).**

**Next steps (route to prototype-engineer for FEASIBILITY-PROVEN):**
1. Build a **throwaway prototype** (NEVER commit to `feat/gfr-engine`) that resolves
   `asset_id` as a **set** off the **real hydrated canary task**
   (`b167331c-536f-4996-9b2d-2f696f35f556`) via the cf-type table + comma-split→set
   override — settling HYP-1/HYP-2 **LIVE** (not by citation).
2. Prove **generality across ≥2 EntityTypes** (G-DENOM: not a synthetic single-field
   demo) — e.g. Offer `asset_id` + one Business/Unit tail field.
3. Hand the freshness-seam question (OPEN FORK #1) and the drift-gate mechanism
   (OPEN FORK #3) to **integration-researcher** for dependency mapping.

## Provenance / Sources

External literature + platform-authoritative sources, evidence-graded per
@evidence-grade-vocabulary; platform-internal anchors per @citation-format-standard.

| ID | Source | Grade | Grounds |
|---|---|---|---|
| SRC-001 | Estuary "Managing Schema Drift in Variant Data"; Axrail "Data Contracts" (2024-25) | MODERATE | (a) schema-on-read / late-binding + fail-fast data contracts |
| SRC-002 | Apache Iceberg schema-projection docs (DeepWiki); Databricks Delta Lake schema enforcement (2019); Srimukunthan, Medium (2024) | MODERATE | (b) columnar schema-evolution; field-ID matching; projection type-validation; data contracts |
| SRC-003 | Apollo GraphQL resolver docs; NestJS GraphQL; TypeGraphQL | MODERATE | (c) typed field-resolvers; reflection over decorator metadata |
| SRC-004 | SQLAlchemy 2.0 automap docs; O'Reilly Essential SQLAlchemy ch.10 | MODERATE | (d) dynamic-ORM reflection; zero-declaration; type-safety tradeoff; reflect-only-subset |
| SRC-005 | Elastic mapping docs; Sweet Security "Avoid Field Limit Errors"; Johnell "Taming Field Explosion" (Medium) | MODERATE | (e) dynamic mapping; mapping-explosion counter-case; hybrid remedy |
| SRC-006 | Asana Developer Docs "Custom fields guide" + `asana_oas.yaml` | PLATFORM-HEURISTIC | (f) resource_subtype type model; `type` deprecated in favour of `resource_subtype` |
| AD:SRC-005 | Anthropic "Building Effective Agents" (2024) (rnd-dk) | MODERATE | composable simplicity over monolithic complexity |

**Platform-internal anchors (this pass):** `models/business/offer.py:144`;
`dataframes/schemas/offer.py` (grep `asset_id` → 0); `models/business/hydration.py:69,:283,:571,:646,:672`;
`models/business/fields.py:232-251`; `core/field_utils.py:60-73`;
`dataframes/resolver/default.py:27,:59-114,:92-97,:234-287`;
`core/entity_registry.py:136`; `gfr-tdd.md` §0.1 (INVARIANT GFR-IDENTITY-1).
