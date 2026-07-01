---
type: spike
status: draft
initiative: gfr-dynvocab
title: GFR Dynamic-Vocabulary Paradigm — Integration Map (live substrate)
authored_at: 2026-06-25
authored_by: integration-researcher (rnd rite)
rite: rnd
g_rung: feasibility-mapping (CANNOT build/merge/lock — 10x-dev + MINE)
self_grade: "[STRUCTURAL | MODERATE]"  # self-ref cap; STRONG needs the rite-disjoint transfer-seam corroboration
grandeur_anchor: >
  gfr-dynvocab makes any fleet caller resolve a gid to ANY field the entity
  actually carries — reflectively, heuristically-typed from cf-type metadata,
  governed-strict (so 'unknown' means genuinely absent) — on top of the
  STRONG-certified identity spine, never regressing it.
certified_base:
  worktree: /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr
  branch: feat/gfr-engine
  tip: 2092f771
  status: FROZEN CLEAN; 105 tests GREEN
  do_not_touch: the STRONG-certified identity spine (CERT-1 guard, CERT-3 round-trip)
sources:
  - .ledge/specs/gfr-dynvocab-alignment-brief.md   # LOCKED INCEPTION (12 decisions)
  - .ledge/specs/gfr-tdd.md                          # certified engine TDD v2
  - .ledge/reviews/gfr-certification-case-file.md    # certs (never regress)
---

# GFR Dynamic-Vocabulary — Integration Map

> Maps the favored dynvocab paradigm (heuristically-typed tail off the hydrated
> entry task + dataframe-layer model↔schema coherence governance) onto the real
> codebase. Every touchpoint carries a `file:line` anchor. Platform-behavior
> claims are SVR-labelled; unconfirmable claims are UV-P.

## 0. G-PROVE posture (what this artifact can and cannot earn)

This is an rnd feasibility-mapping artifact. It surfaces touchpoints, hidden
deps, effort, migration, and rollback. It does **NOT** build, merge, or lock the
paradigm — those are 10x-dev + MINE (user-gated). The FEASIBILITY-PROVEN rung is
earned only by the prototype-engineer's WORKING throwaway prototype resolving
`asset_id` as a set off the real hydrated canary task (`b167331c-…`) and settling
HYP-1/HYP-2 LIVE. This map is the prototype-engineer's input, not a substitute
for it.

---

## 1. Composition seams (file:line for every touchpoint)

### 1.1 The certified engine composition surface (feat/gfr-engine, worktree)

The certified engine is 8 modules under `resolution/gfr/`. The dynvocab tail
composes at exactly ONE seam without touching the company_id identity path:

| Module | Anchor (worktree) | Role | Tail composition point |
|--------|-------------------|------|------------------------|
| `entry.py` | `resolution/gfr/entry.py:66` `_fetch_and_anchor_async` | the SINGLE Asana-API read; hydrates task, detects type, anchors business_gid | **THE SEAM.** Returns `EntryAnchor(gid, entity_type, business_gid, path_len)` — and **DISCARDS the hydrated task's custom_fields** (`entry.py:111-116` builds the anchor from `result.business`/`result.entry_type` only). The tail's free custom-field set is fetched here then dropped. |
| `engine.py` | `resolution/gfr/engine.py:166` `resolve_async` | thin orchestration spine | the tail is a NEW plan-element class resolved AFTER the identity plan (`engine.py:229-247`), never inside `_resolve_identity_plan_async`. |
| `engine.py` | `resolution/gfr/engine.py:230-235` | `if not identity_plans: raise no-identity-path` | **today asset_id dies HERE** (or earlier at the planner). This is the stub the case-file flagged (`gfr-certification-case-file.md:94,123`). |
| `planner.py` | `resolution/gfr/planner.py:55` `_owning_entity` → `schema.get_column(field)` | field→owner partition; FM5 unknown-field gate | **THE BOUND.** A field resolves ONLY if `SchemaRegistry` schema declares it. `asset_id` is not in OFFER_SCHEMA → `UnresolvedError(unknown-field)` at `planner.py:127-129`. This IS the smell, structurally. |
| `guard.py` | `resolution/gfr/guard.py:158` `assert_plan_identity_pure` | identity-purity (INVARIANT I1) | the tail plan elements are `is_identity=False`; the guard only inspects `plan.identity_plans` (`guard.py:167`), so a non-identity tail element is **invisible to the certified guard** — it cannot regress it. |
| `guard.py` | `resolution/gfr/guard.py:183` `assert_rows_tenant_identity` | post-execute Vector-A guard (GAP-1) | operates ONLY on the gid-exact identity read's rows (`engine.py:138`). The tail never calls this. No regression surface. |
| `models.py` | `resolution/gfr/models.py:114` `FieldPlan`, `:134` `ResolutionPlan` | plan data types | `FieldPlan.is_identity` already partitions identity vs non-identity. The tail rides the `is_identity=False` partition. `FieldWithProvenance` (`:64`) is the provenance carrier the typing-origin tag extends. |

**Composition finding (SVR — file-read, worktree):** the certified identity path
is `entry → plan → assert_plan_identity_pure → _resolve_identity_plan_async
(gid-exact, post-execute guard) → posture`. The tail is strictly additive: it
attaches to the `EntryAnchor` (needs the entry task's `custom_fields`, currently
discarded) and resolves under the `is_identity=False` branch the engine today
stubs as `no-identity-path`. **It never enters `_resolve_identity_plan_async`,
never touches `assert_rows_tenant_identity`, never builds a RowsRequest for
identity.** The 105-test regression gate is the structural proof.

```yaml
structural_verification_receipt:
  claim: "the certified entry phase fetches the full custom-field set on the entry task but discards it: _fetch_and_anchor_async builds EntryAnchor from result.business/result.entry_type/result.path only, keeping no custom_fields, so the dynvocab tail's marginal-cost insight requires threading the entry task (or its custom_fields) through this seam"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr/src/autom8_asana/resolution/gfr/entry.py"
    line_range: "L66-L126"
    marker_token: "anchor = EntryAnchor("
    claim: "EntryAnchor is a frozen 4-field dataclass (gid, entity_type, business_gid, path_len); the hydrated entry task with its custom_fields is consumed by hydrate_from_gid_async and never surfaced past this function — the tail must additively carry the task/custom_fields forward"
```

### 1.2 HYP-1 — does the entry fetch already pull ALL custom fields with values?

**STRUCTURALLY SETTLED: YES — the tail is FREE.**

The entry fetch at `hydration.py:283` requests `opt_fields=_BUSINESS_FULL_OPT_FIELDS`.
`_BUSINESS_FULL_OPT_FIELDS = list(STANDARD_TASK_OPT_FIELDS)` (`hydration.py:69`).
`STANDARD_TASK_OPT_FIELDS` (`models/business/fields.py:232-251`) requests the
**bare `custom_fields` opt-field** (`fields.py:240`) PLUS per-subfield value
projections: `custom_fields.name`, `.enum_value`, `.enum_value.name`,
`.multi_enum_values`, `.multi_enum_values.name`, `.display_value`,
`.number_value`, `.text_value`, `.resource_subtype`, `.people_value`
(`fields.py:241-250`).

In the Asana API the bare `custom_fields` opt-field returns the **complete set**
of custom fields present on the task with their values; the `.subfield`
projections widen each field's value payload. The in-code comment confirms intent:
`hydration.py:66-68` — "the task already has custom_fields populated for field
cascading (Office Phone, Company ID, etc.)". So the hydrated entry task carries
EVERY custom field the entity has, with values, including `asset_id` — at **~0
marginal cost** (no new Asana call; it is the certified, accounted entry read).

```yaml
structural_verification_receipt:
  claim: "the certified entry fetch requests the bare custom_fields opt-field plus all per-subfield value projections, so the hydrated entry task carries every custom field the entity has WITH values (asset_id included) at zero marginal Asana cost — the dynvocab tail is free off the already-accounted entry read"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/models/business/fields.py"
    line_range: "L232-L251"
    marker_token: "\"custom_fields\","
    claim: "STANDARD_TASK_OPT_FIELDS (the constant _BUSINESS_FULL_OPT_FIELDS aliases at hydration.py:69, used at hydration.py:283) requests the parent 'custom_fields' opt-field — which the Asana API expands to the full custom-field set — plus text_value/number_value/enum_value/multi_enum_values/display_value/resource_subtype/people_value projections; HYP-1 is YES at the schema-request layer"
```

**SVR-CAVEAT (platform-behavior — NOT statically confirmable from this repo):**
the claim "the Asana API returns ALL custom fields (not a curated subset) when
the bare `custom_fields` opt-field is requested" is an **Asana platform semantic**.
The opt-fields list is necessary-and-correct at the request layer; whether the
live API returns every field present on the task vs only a workspace-curated
subset is a runtime fact. **UV-P → this is exactly what the prototype-engineer's
canary run settles (HYP-1 LIVE):** hydrate `b167331c-…`, assert `asset_id` is
present in the returned `custom_fields` with a value. If present → tail is free,
favored task-based source confirmed. If absent → fall back to OPEN FORK 1's
frame-based wide-select. **This is the single highest-leverage prototype probe.**

### 1.3 The cf-type heuristic-table source (TWO independent sources — both live)

| Source | Anchor | Shape | Use |
|--------|--------|-------|-----|
| **Runtime** (per-field, off the fetched task) | `dataframes/resolver/default.py:250-287` `_extract_raw_value` + `core/field_utils.py:60-73` | `resource_subtype` ∈ {text, number, enum, multi_enum, date, people} → typed value via `text_value`/`number_value`/`enum_value`/`multi_enum_values`/`date_value`/`people_value`/`display_value` | the heuristic table the brief wants; **already implemented** as a match-statement at `default.py:252-287`. |
| **Static** (per-field, off the model descriptor) | `models/business/descriptors.py:445` `TextField`, `:501` `EnumField`, `:532` `MultiEnumField`, `:579` `NumberField`, `:614` `IntField` (+ Date/People) | descriptor SUBCLASS ≡ cf-type; `field_name` (`:338`) ≡ Asana cf name | a model-side typing-origin source: `asset_id = TextField(field_name="Asset ID")` (`offer.py:144`) statically declares asset_id is cf-type `text`. |

**Finding:** the heuristic table the brief calls for is **NOT net-new** — it is
`DefaultCustomFieldResolver._extract_raw_value` (`default.py:234-287`), a
resource_subtype match-statement that already maps every Asana cf-type to a typed
value. The dynvocab tail can REUSE it directly (text→str, number→float-ish,
enum→label, multi_enum→list[str], date→date, people→list[gid], fallback→
display_value). The per-field override registry (e.g. `asset_id` text→set) is the
genuine new surface and is a thin wrapper over this.

### 1.4 The entity_registry hook + SEAM1 key shape

- `core/entity_registry.py:136-139` `custom_field_resolver_class_path` — per-entity
  hook; every dataframe entity points at `…resolver.DefaultCustomFieldResolver`
  (`entity_registry.py:461,487,509,…`). The tail's resolver is injectable per
  EntityType through this same hook (generality-by-design, brief §36).
- `core/entity_registry.py:151` `body_parameterized: bool = False` — offer-domain
  cache-only HARD line; the tail inherits it (no new Asana call beyond entry).
- SEAM1 key shape `dataframes/{project_gid}/{entity_type}/…` — the tail does not
  touch storage keys; it reads off the in-memory hydrated task, not a frame.

```yaml
structural_verification_receipt:
  claim: "the Asana cf-type heuristic table the dynvocab brief calls for already exists as DefaultCustomFieldResolver._extract_raw_value, a resource_subtype match-statement mapping text/number/enum/multi_enum/date/people to typed values, so the tail REUSES it rather than authoring a net-new table; the per-field override (asset_id text->set) is the only genuinely new typing surface"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/dataframes/resolver/default.py"
    line_range: "L250-L287"
    marker_token: "match resource_subtype:"
    claim: "_extract_raw_value already coerces by resource_subtype across all six Asana cf-types with a display_value fallback; field_utils.py:60-73 exposes the same metadata surface; the heuristic-table feasibility is CONFIRMED present"
```

---

## 2. The minimal additive GFR-tail surface

The tail is a **separate non-regressing layer** under `resolution/gfr/` (sibling
modules, zero edits to the 8 certified files except the one additive seam thread).

### 2.1 New surface (additive)

| New module / change | What | Composes with certified via |
|---------------------|------|------------------------------|
| `resolution/gfr/dynvocab.py` (NEW) | `resolve_tail(entry_task, requested_fields) -> dict[str, FieldWithProvenance]`: build the manifest from the entry task's `custom_fields`, coerce via the existing heuristic table, apply per-field overrides, stamp typing-origin. | reads the entry task's `custom_fields`; returns `FieldWithProvenance` (existing model). |
| `resolution/gfr/heuristic_table.py` (NEW, thin) | wraps `DefaultCustomFieldResolver._extract_raw_value` cf-type→typed-value; ~0 new logic. | reuse, not reimplement. |
| `resolution/gfr/overrides.py` (NEW) | per-field override registry; **PROOF OVERRIDE from the outset:** `asset_id` text → whitespace-agnostic comma-split → `set` (`"a, b ,c"`→`{a,b,c}`). | pure function registry keyed by field name. |
| `EntryAnchor` +1 field (additive) | carry `entry_task` (or its `custom_fields`) forward past `entry.py:111`. ONE additive field on a frozen dataclass. | the SINGLE certified-file thread; everything else is new modules. |
| `FieldWithProvenance` +1 field (additive, optional) | typing-origin tag `{typed: 'schema'\|'heuristic', cf_type}` alongside `{value,status,source,as_of}`. `extra="forbid"` means this is an additive model field, not a breaking change. | brief §29 typing-provenance. |
| `engine.resolve_async` tail branch | replace the `is_identity=False`→`no-identity-path` stub (`engine.py:230-235`) with: resolve identity plans (unchanged) THEN resolve tail plans off the entry task. | additive branch; identity path byte-identical. |

### 2.2 How it composes WITHOUT regressing the certified spine

1. **company_id stays on the certified frame path.** The tail reads off the
   entry TASK's custom_fields (in-memory), never the Business frame, never
   `_resolve_identity_plan_async`, never a RowsRequest. `company_id` is
   `is_identity=True` and continues through `guard.assert_plan_identity_pure` +
   `assert_rows_tenant_identity` byte-identically.
2. **The GAP-1 guard is untouched.** `assert_rows_tenant_identity` (`guard.py:183`)
   only runs on identity-read rows; the tail produces no such rows.
3. **The 105 tests are the regression gate.** Any tail change that perturbs the
   identity path fails them. The grandeur anchor's "never regressing it" ≡ "105
   GREEN" mechanically.
4. **governed-strict unknown.** The planner's FM5 (`planner.py:127-129`) currently
   means "unknown-field = not in curated schema". With the tail, the manifest IS
   the entity's real custom-field set, so `unknown-field` becomes truthful
   (genuinely absent), satisfying the brief's governed-strict posture (§22).

---

## 3. Dataframe-layer coherence — drift quantification + mechanism options

### 3.1 Drift quantification: SYSTEMIC, not asset_id-only

Model `*Field()` descriptor count (grep `models/business/`) vs dataframe schema
entity-specific ColumnDef count (BASE_COLUMNS excluded):

| Entity | Model `*Field()` descriptors | Schema entity-specific columns | Schema anchor | Drift (model fields absent from schema) |
|--------|------------------------------|--------------------------------|---------------|------------------------------------------|
| **Offer** | **35** (`offer.py`) | **11** (office, office_phone, vertical, specialty, offer_id, platforms, language, name, cost, mrr, weekly_ad_spend) | `schemas/offer.py:8-90` | **~24 fields drifted** — incl. `asset_id`, ad_id, ad_set_id, campaign_id, ad_account_url, active_ads_url, offer_headline, included_item_1/2/3, landing_page_url, preview_link, lead_testing_link, num_ai_copies, form_id, targeting, targeting_strategies, optimize_for, campaign_type, appt_duration, calendar_duration, custom_cal_url, offer_schedule_link, internal_notes, external_notes, voucher_value, budget_allocation, algo_version, triggered_by |
| **Process** | **59** (`process.py`) | **3** (office_phone, vertical, pipeline_type) | `schemas/process.py:14-42` | **LARGE** — Process model is the widest; schema is 2 cascades + 1 derived. AssetEdit (a Process subtype) gets the richer schema below. |
| **Contact** | **19** (`contact.py`) | **12** (full_name, nickname, contact_phone, contact_email, position, employee_id, contact_url, time_zone, city, office_phone, vertical, dashboard_uuid) | `schemas/contact.py:8-97` | **~7 fields drifted** |
| **Unit** | **28** (`unit.py`) | **9** (mrr, weekly_ad_spend, products, languages, discount, office, office_phone, vertical, specialty) | `schemas/unit.py:8-74` | **~19 fields drifted** |
| **AssetEdit** | (Process model + AssetEdit.Fields) | **21** (10 Process + 11 AssetEdit-specific, incl. `asset_id` `cf:Asset ID`) | `schemas/asset_edit.py:178-193` | partial — AssetEdit is the **best-covered**; notably **`asset_id` IS in the AssetEdit schema** (`asset_edit.py:106-111`) but ABSENT from the OFFER schema. asset_id drift is **Offer-specific**, not global. |
| **Business** | **14** (`business.py`) | **6** (company_id, name, office_phone, stripe_id, booking_type, facebook_page_id) | `schemas/business.py:8-51` | **~8 fields drifted** |

**Quantification verdict: the model↔schema drift is SYSTEMIC across every
entity.** `asset_id` is not the only drifted field — it is the *canary* for a
fleet-wide pattern where the hand-curated dataframe schema is a strict, narrow
subset of the model's declared fields. Notable nuance: `asset_id` IS declared on
the AssetEdit schema (`asset_edit.py:106`) but NOT the Offer schema — so the smell
is "asset_id is absent from the OFFER schema specifically", while the broader
truth is "every entity's schema is a curated subset of its model".

```yaml
structural_verification_receipt:
  claim: "model<->schema drift is systemic: every entity's dataframe schema declares far fewer columns than its task model declares Field descriptors (Offer 35 model vs 11 schema; Process 59 vs 3; Unit 28 vs 9; Contact 19 vs 12; Business 14 vs 6); asset_id is the canary not the sole instance, and is present on the AssetEdit schema but absent from the Offer schema"
  verification_method: bash-probe
  verification_anchor:
    source: "grep -c '= (Text|Number|Int|Enum|MultiEnum|Date|People|Bool|Float)Field(' models/business/*.py  vs  ColumnDef count in dataframes/schemas/*.py"
    command_output_verbatim: "offer.py:35 contact.py:19 unit.py:28 business.py:14 process.py:59 ; schema columns offer=11 contact=12 unit=9 business=6 process=3 asset_edit=21"
    claim: "the field-count asymmetry is large and present on every entity; the schema is a hand-curated subset of the model — the brief's root-cause framing (blast radius = BOTH layers) is structurally confirmed"
```

### 3.2 Coherence mechanism options (grounded in actual code, with tradeoffs)

There is a **load-bearing prior decision** to weigh: `entity_registry.py:430-432`
cites **ADR-S4-001** — schemas are KEPT as separate files "rather than generating
them from descriptor metadata", with a "Validation check 6a catches mismatches at
import time". And `_validate_extractor_coverage` (`registry.py:168-207`) is an
EXISTING import-time, non-crashing, structured-warning validator — the natural
host for a drift check.

| Option | Mechanism | Grounded in | Risk | Effort | Reversible? |
|--------|-----------|-------------|------|--------|-------------|
| **A — Drift CI gate (additive, LOW risk)** | extend `_validate_extractor_coverage` (`registry.py:168`) or a new test to assert every model `*Field()` descriptor has a schema ColumnDef (or is explicitly allow-listed as intentionally-omitted). The descriptor `_pending_fields` registry (`descriptors.py:49`) + `Fields` auto-gen (ADR-0082) gives the model-side field list mechanically. | `descriptors.py:49,52`, `registry.py:168-207`, ADR-0082 | LOW — pure additive observability; no runtime behavior change | S–M | YES — delete the check |
| **B — Schema-derivation/codegen FROM model descriptors** | generate `ColumnDef`s from the `_pending_fields`/`Fields` registry; cf-type→dtype via descriptor subclass. | `descriptors.py:300-740` (subclass≡cf-type), `_pending_fields` | **MED-HIGH — directly contradicts ADR-S4-001's explicit "do not generate schemas from descriptor metadata" decision.** Also: schemas carry cascade/derived sources (`cascade:`, `source=None`) the model does NOT (e.g. offer `office` cascades from Business Name; `pipeline_type` is derived) — codegen cannot synthesize these. | L | PARTIAL — one-way once consumers depend on generated shapes |
| **C — Reflective extract-all (no schema for the tail)** | the GFR tail bypasses the schema entirely, reading the manifest off the live task's `custom_fields` (the §1.2 free set). Dataframe schemas stay curated for the dataframe/query layer; the tail is the dynamic surface. | `default.py:234-287`, §1.2 free custom-field set | LOW for the tail; does NOT fix the dataframe-layer drift for non-GFR consumers | S | YES |

**Recommended pairing (two approaches, different risk/effort):**
- **Tail layer:** Option **C** (reflective extract-all off the entry task) — this
  is what makes `asset_id` resolvable for GFR callers at ~0 cost, governed-strict.
- **Dataframe layer:** Option **A** (drift CI gate) — surfaces the systemic drift
  as a visible, allow-listable signal WITHOUT fighting ADR-S4-001. Option B is the
  higher-ambition alternative but should be ESCALATED (it reverses a documented
  ADR and cannot synthesize cascade/derived columns).

**ADR-S4-001 is a one-way-door flag.** Option B reverses an explicit architecture
decision; recommend the prototype-engineer spike Option A + C, and route any
Option-B ambition to moonshot-architect / user as a deliberate ADR re-litigation,
NOT an implementation default.

---

## 4. Hidden dependencies, effort, migration, rollback

### 4.1 Hidden dependencies (NOT in the brief / NOT documented)

1. **The entry task is fetched-then-discarded (HIDDEN).** `entry.py:111-116` keeps
   only 4 anchor fields; the custom-field-bearing task is dropped at the seam. The
   "free tail" insight REQUIRES additively threading the task/custom_fields past
   this point. Discovery: file-read of the certified `entry.py`. Coupling: the tail
   is coupled to the `EntryAnchor` shape — one additive field on a frozen dataclass.
2. **`hydrate_full=False` (HIDDEN freshness seam).** `entry.py:93` calls
   `hydrate_from_gid_async(..., hydrate_full=False)` — locates the Business root but
   does NOT hydrate the downward hierarchy. The entry task's OWN custom_fields are
   present (it was fetched at `hydration.py:283`); but for a NON-entry entity's
   fields the tail would need its task too. For `asset_id` on an Offer entry gid
   this is fine (asset_id is on the Offer task itself). OPEN FORK 1's freshness seam
   (tail off task vs company_id off frame) lands here.
3. **Asana API custom_fields-completeness (HIDDEN platform semantic, UV-P).** §1.2 —
   whether the live API returns ALL fields for the bare `custom_fields` opt-field is
   unconfirmable statically. **This is the prototype's HYP-1 probe.** If the API
   curates, the free-tail premise weakens and OPEN FORK 1 (frame-based wide-select)
   reactivates.
4. **`name` collision (HIDDEN).** Multiple schemas declare a `name` column with
   `source=None` (derived from `.name`), distinct from custom-field `name`. The
   planner's `_owning_entity` first-owner-wins (`planner.py:62-66`) could mis-route a
   tail field colliding with a base/derived column. The override registry must guard
   reserved names.
5. **Duplicate-cf-name-after-normalization (HIDDEN, already handled upstream).**
   `default.py:84-90,99-108` first-match-wins + warns on normalized-name duplicates.
   The tail inherits this; a tenant with two fields normalizing identically resolves
   the first. Document as a known tail limitation.
6. **AssetEdit vs Offer asset_id dtype divergence (HIDDEN).** AssetEdit schema types
   `offer_id` as `Int64` (`asset_edit.py:127`) while Offer schema types `offer_id`
   as `Utf8` (`offer.py:42`). The same Asana cf name maps to different dtypes per
   entity — the heuristic table is per-entity-context, not global. The override
   registry must be EntityType-aware.

### 4.2 Effort estimate (per layer, with confidence + assumptions)

| Layer / item | Estimate | Confidence | Key assumptions | "if wrong" multiplier |
|--------------|----------|------------|-----------------|-----------------------|
| **GFR tail** — dynvocab.py + heuristic_table.py (reuse) + overrides.py + EntryAnchor thread + engine branch | **3–5 dev-days** | **MEDIUM** | (a) HYP-1 LIVE confirms API returns asset_id on the entry task; (b) heuristic table reuses `_extract_raw_value` unchanged; (c) EntryAnchor +1 field passes all 105 tests | if HYP-1 fails (API curates) → +5–8 days for frame-based wide-select fallback (OPEN FORK 1) → ~2x |
| **typing-origin provenance tag** (FieldWithProvenance +1 field) | **0.5–1 day** | **HIGH** | `extra="forbid"` additive field is non-breaking; no consumer asserts the closed shape | low |
| **Dataframe drift CI gate (Option A)** | **2–3 dev-days** | **MEDIUM** | (a) `_pending_fields`/`Fields` registry exposes the model field list mechanically; (b) an allow-list for intentionally-omitted fields is acceptable to the user | if the allow-list must be hand-curated per-entity for ~60 drifted fields → +2 days |
| **Schema-derivation codegen (Option B)** | **8–15 dev-days** | **LOW** | requires reversing ADR-S4-001 AND synthesizing cascade/derived columns codegen cannot infer | if cascade-source semantics must be hand-modeled → ~2x; ESCALATE before committing |
| **Generality across ≥2 EntityTypes** (G-DENOM) | **+2 days** on top of Offer | **MEDIUM** | the tail is generic over EntityType via the resolver hook (`entity_registry.py:136`); proving on Offer + AssetEdit (both carry asset_id) is the cheapest 2nd entity | low if hook is truly generic |

**Total favored path (Tail Option C + Dataframe Option A + provenance + 2-entity
generality): ~8–12 dev-days at MEDIUM confidence.** The dominant risk is HYP-1
(the one platform-behavior UV-P). The prototype settles it in <1 day.

### 4.3 Phased migration path (with rollback points)

| Phase | Scope | Rollback point | Reversible? |
|-------|-------|----------------|-------------|
| **P0 — Prototype (rnd → prototype-engineer)** | throwaway: thread entry task forward, resolve `asset_id` as a set off the real canary `b167331c-…`; settle HYP-1/HYP-2 LIVE. NEVER commit to feat/gfr-engine. | discard the throwaway branch | YES (throwaway) |
| **P1 — Tail layer (10x-dev, additive)** | dynvocab.py + heuristic_table + overrides + EntryAnchor +1 field + engine `is_identity=False` branch. company_id path byte-identical; 105 tests GREEN gate. | feature-off = the certified `no-identity-path` stub (`engine.py:230-235`) still in place behind a flag; tail modules unimported | YES — delete new modules, revert one EntryAnchor field |
| **P2 — Typing-origin provenance** | FieldWithProvenance +1 additive field. | additive field defaults; remove if unused | YES |
| **P3 — Dataframe drift CI gate (Option A)** | extend `_validate_extractor_coverage` / new test; allow-list intentional omissions. | the check is warn-only first (matches `registry.py:158-166` non-crash discipline), promoted to gate later | YES — demote to warn / delete |
| **P4 — Generality (≥2 EntityTypes)** | prove tail on Offer + AssetEdit via the resolver hook. | per-entity resolver class path is already per-descriptor (`entity_registry.py:136`); revert one descriptor | YES |
| **P5 (ESCALATE, OPTIONAL) — Schema codegen (Option B)** | reverses ADR-S4-001. | **ONE-WAY DOOR** once consumers depend on generated shapes | NO — escalate to user/moonshot-architect first |

**Natural rollback points:** P1–P4 are each additive and independently
revertible; the 105-test gate is the continuous rollback trigger (any RED =
revert the offending phase). P5 is the only one-way door and is explicitly
escalated, not defaulted.

### 4.4 Two integration approaches (risk/effort tradeoff)

- **Approach 1 (RECOMMENDED — low risk, additive):** Tail Option C + Dataframe
  Option A. ~8–12 days, MEDIUM confidence. Honors ADR-S4-001. Tail is free off the
  entry task (HYP-1-gated). Drift made visible without codegen. All phases
  reversible.
- **Approach 2 (higher ambition — escalate):** Tail Option C + Dataframe Option B
  (schema codegen from descriptors). ~16–25 days, LOW confidence. Reverses
  ADR-S4-001, fixes drift for ALL dataframe consumers (not just GFR), but cannot
  synthesize cascade/derived columns and introduces a one-way door. Route the
  Option-B decision to user/moonshot-architect as a deliberate ADR re-litigation.

---

## 5. Handoff to prototype-engineer (POC scope + success criteria)

**POC scope (throwaway, NEVER on feat/gfr-engine):**
1. Thread the hydrated entry task's `custom_fields` past the `entry.py:111` seam.
2. Resolve `asset_id` as a `set` via the comma-split override off a REAL hydrated
   canary task (`b167331c-536f-4996-9b2d-2f696f35f556`).
3. Settle **HYP-1 LIVE**: assert `asset_id` is present in the canary's returned
   `custom_fields` with a value (the API-completeness UV-P).
4. Settle **HYP-2** (freshness seam, OPEN FORK 1): the tail off the task is
   consistent with company_id off the frame for the same gid.
5. **G-DENOM generality:** resolve a tail field on a 2nd EntityType (AssetEdit
   carries asset_id natively) — never a synthetic single-field demo.

**Success criteria (FEASIBILITY-PROVEN inputs):**
- pasted prototype run showing `resolve(asset_id off canary) == {a,b,c}` (a set).
- HYP-1 receipt: `asset_id` present in live `custom_fields`.
- the 105 certified tests stay GREEN on the certified branch (untouched).
- generality demonstrated across ≥2 EntityTypes.

**Risk areas for hands-on validation:** HYP-1 API-completeness (§4.1.3); the
freshness seam (§4.1.2); per-entity dtype divergence of shared cf names (§4.1.6).

---

*rnd integration-map | self-grade [STRUCTURAL | MODERATE] (self-ref cap) | STRONG
needs the rite-disjoint transfer-seam corroboration — named, never self-granted.
This rite CANNOT build/merge/lock the paradigm (10x-dev + MINE).*
