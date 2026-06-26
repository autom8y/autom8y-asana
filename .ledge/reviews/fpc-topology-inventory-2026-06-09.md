---
type: review
status: draft
---

# FPC Topology Inventory — The (entity, field) Cell Lattice

> **Role**: topology-cartographer (DEEP-DIVE). Records WHAT IS, not whether it is good.
> **Scope**: READ-ONLY over origin/main + S3 + /tmp/u8o,/tmp/u8u parquet. No src/ edits.
> **HEAD**: `origin/main = 50ebfe3381a627df868887ca3cdf9e223e1f9a90` (verified `git rev-parse origin/main`).
> **Canary (G-THEATER)**: coherence invariant `offer.mrr[phone] == unit.mrr[phone]` fires **RED = 571** (re-run confirmed this pass).
> **Unit of analysis**: the (entity, field) cell. Every schema column is one row.
> **Date**: 2026-06-09.

---

## 1. Method & Provenance

Every cell below is derived from a ColumnDef `source=` line read from a schema file at
origin/main via `git show origin/main:<path>`. Mode classification is mechanical from the
`source=` prefix:

| `source=` literal form | Resolution-mode | Schema receipt (representative) |
|---|---|---|
| `source="cf:X"` | **Direct** (custom-field extract) | `schemas/business.py` `office_phone` → `source="cf:Office Phone"` |
| `source="cascade:X"` | **Cascade** (from ancestor via join key) | `schemas/unit.py:53-58` `office_phone` → `source="cascade:Office Phone"` |
| `source=None` | **Derived** (computed; no Asana field) | `schemas/base.py` `type` → `source=None  # Derived via _extract_type()` |
| `source="<bare>"` (gid/name/etc.) | **Direct-base** (top-level task attr) | `schemas/base.py` `gid` → `source="gid"` |

NUMBER-typed cells (the path-asymmetry-vulnerable class, per LIVE CORPUS defect-face (a):
list-`number_value` vs get-`number_value` server divergence) = any cell whose schema `dtype`
∈ {`Decimal`, `Int64`, `Float64`} OR whose underlying Asana field is a Number custom field.
Cascade cells (the waterfall class) = any cell with `source="cascade:..."`.

The 10 materialized schema files are the cell-bearing entities. BASE_SCHEMA's 13 columns are
**inherited by all 10** (each entity = `[*BASE_COLUMNS, *entity-specific]`), so BASE cells are
counted **once** as a shared row-set and the per-entity counts below report entity-specific
columns + the shared 13.

---

## 2. BASE cell-set (13 columns — inherited by ALL 10 entities)

Receipt: `git show origin/main:src/autom8_asana/dataframes/schemas/base.py` (BASE_COLUMNS, 13 entries).

| # | entity | field | dtype | mode | canonical-source-entity | required-fetch-path | population-policy | S3-warmed? |
|---|---|---|---|---|---|---|---|---|
| B1 | *(all)* | gid | Utf8 | Direct-base | self (task) | list-ok | none | n/a (key) |
| B2 | *(all)* | name | Utf8 | Direct-base (`source="name"`) | self | list-ok | none | n/a |
| B3 | *(all)* | type | Utf8 | **Derived** (`source=None`) | self (computed) | list-ok | none | n/a |
| B4 | *(all)* | date | Date | **Derived** (`source=None`) | self (computed) | list-ok | none | n/a |
| B5 | *(all)* | created | Datetime | Direct-base (`created_at`) | self | list-ok | none | n/a |
| B6 | *(all)* | due_on | Date | Direct-base | self | list-ok | none | n/a |
| B7 | *(all)* | is_completed | Boolean | Direct-base (`completed`) | self | list-ok | none | n/a |
| B8 | *(all)* | completed_at | Datetime | Direct-base | self | list-ok | none | n/a |
| B9 | *(all)* | url | Utf8 | **Derived** (`source=None`, gid-constructed) | self (computed) | list-ok | none | n/a |
| B10 | *(all)* | last_modified | Datetime | Direct-base (`modified_at`) | self | list-ok | none | n/a |
| B11 | *(all)* | section | Utf8 | **Derived** (`source=None`, from memberships) | self (computed) | list-ok | none | n/a |
| B12 | *(all)* | tags | List[Utf8] | Direct-base | self | list-ok | none | n/a |
| B13 | *(all)* | parent_gid | Utf8 | **Derived** (`source=None`, `_extract_parent_gid()`) | self (computed) | list-ok | none | n/a |

BASE contributes 0 Number-typed cells and 0 Cascade cells. 5 of 13 are Derived (`source=None`).

---

## 3. Entity-specific cell lattice

> **★ = NUMBER-typed** (path-asymmetry-vulnerable). **⟂ = CASCADE** (waterfall class). **∅ = no population policy** (every cell except offer.mrr/offer.offer_id).

### 3.1 business (ROOT, warmable, warm_priority=1, S3=9) — 6 specific cells

Receipt: `schemas/business.py`; descriptor `entity_registry.py:439-456` (`category=ROOT`, `warmable=True`, `warm_priority=1`, `key_columns=("office_phone",)`).

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| company_id | Utf8 | Direct (`cf:Company ID`) | business | list-ok | ∅ | yes (9) |
| name | Utf8 | Derived (`source=None`) | business | list-ok | ∅ | yes |
| office_phone | Utf8 | Direct (`cf:Office Phone`) | business | list-ok | ∅ | yes |
| stripe_id | Utf8 | Direct (`cf:Stripe ID`) | business | list-ok | ∅ | yes |
| booking_type | Utf8 | Direct (`cf:Booking Type`, enum) | business | list-ok | ∅ | yes |
| facebook_page_id | Utf8 | Direct (`cf:Facebook Page ID`) | business | list-ok | ∅ | yes |

business is the cascade ROOT source for `office_phone` (every `cascade:Office Phone` cell resolves here).

### 3.2 unit (COMPOSITE, warmable, warm_priority=2, S3=17) — 9 specific cells

Receipt: `schemas/unit.py`; descriptor `entity_registry.py:466-482` (`category=COMPOSITE`, `key_columns=("office_phone","vertical")`).

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| ★ mrr | Decimal | Direct (`cf:MRR`) | unit | **needs-per-task-GET** (live: 0/3021 nonnull) | ∅ | yes (17) |
| ★ weekly_ad_spend | Decimal | Direct (`cf:Weekly Ad Spend`) | unit | needs-per-task-GET | ∅ | yes |
| products | List[Utf8] | Direct (`cf:Products`, multi-enum) | unit | list-ok | ∅ | yes |
| languages | List[Utf8] | Direct (`cf:Languages`, multi-enum) | unit | list-ok | ∅ | yes |
| ★ discount | Decimal | Direct (`cf:Discount`) | unit | needs-per-task-GET | ∅ | yes |
| ⟂ office | Utf8 | **Cascade** (`cascade:Business Name`) | business (.name) | cascade-from business | ∅ | yes |
| ⟂ office_phone | Utf8 | **Cascade** (`cascade:Office Phone`) | business | cascade-from business | ∅ | yes |
| vertical | Utf8 | Direct (`cf:Vertical`) | unit | list-ok | ∅ | yes |
| specialty | Utf8 | Direct (`cf:Specialty`) | unit | list-ok | ∅ | yes |

`unit.mrr` is the **source of the 571-gun**: schema declares `dtype="Decimal"`/`source="cf:MRR"`,
but model declares `discount = EnumField()` (drift, §5) and live `mrr` = **0/3021 nonnull**
(`duckdb read_parquet('/tmp/u8u/*.parquet')`). Offer's `mrr` cascades FROM unit.mrr → null in → null out.

### 3.3 offer (LEAF, warmable, warm_priority=3, S3=15) — 11 specific cells

Receipt: `schemas/offer.py`; descriptor `entity_registry.py:511-527` (`key_columns=("office_phone","vertical","offer_id")`). **Only entity with a population policy** (`post_build_population_receipt.py:60-62` `_VALUE_COLUMNS_BY_ENTITY = {"offer": ("mrr","offer_id")}`).

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| ⟂ office | Utf8 | **Cascade** (`cascade:Business Name`) | business (.name) | cascade-from business | ∅ | yes (15) |
| ⟂ office_phone | Utf8 | **Cascade** (`cascade:Office Phone`) | business | cascade-from business | ∅ | yes |
| ⟂ vertical | Utf8 | **Cascade** (`cascade:Vertical`) | unit→business | cascade-from unit/business | ∅ | yes |
| specialty | Utf8 | Direct (`cf:Specialty`) | offer | list-ok | ∅ | yes |
| offer_id | Utf8 | Direct (`cf:Offer ID`) | offer | list-ok | **floor (in _VALUE_COLUMNS)** | yes |
| platforms | List[Utf8] | Direct (`cf:Platforms`, multi-enum) | offer | list-ok | ∅ | yes |
| language | Utf8 | Direct (`cf:Language`, enum) | offer | list-ok | ∅ | yes |
| name | Utf8 | Derived (`source=None`) | offer | list-ok | ∅ | yes |
| ★ cost | Utf8 | Direct (`cf:Cost`, Number field — **dtype/field drift**, §5) | offer | needs-per-task-GET | ∅ | yes |
| ★ ⟂ mrr | Decimal | **Cascade** (`cascade:MRR`) | unit | cascade-from unit (live: 1325/4070 nonnull) | **floor (in _VALUE_COLUMNS)** | yes |
| ★ ⟂ weekly_ad_spend | Decimal | **Cascade** (`cascade:Weekly Ad Spend`) | unit | cascade-from unit | ∅ | yes |

`offer.mrr` is BOTH ★(number) AND ⟂(cascade) AND the population-floor anchor — the single
most-instrumented cell. Its cascade source `unit.mrr` is 0/3021 → the 571 phones where
offer.mrr is present-but-unit.mrr-null is the coherence violation.

### 3.4 contact (LEAF, warmable, warm_priority=4, S3=8) — 12 specific cells

Receipt: `schemas/contact.py`; descriptor `entity_registry.py:492-505` (`key_columns=("office_phone","contact_phone","contact_email")`).

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| full_name | Utf8 | Direct (`cf:Full Name`) | contact | list-ok | ∅ | yes (8) |
| nickname | Utf8 | Direct (`cf:Nickname`) | contact | list-ok | ∅ | yes |
| contact_phone | Utf8 | Direct (`cf:Contact Phone`) | contact | list-ok | ∅ | yes |
| contact_email | Utf8 | Direct (`cf:Contact Email`) | contact | list-ok | ∅ | yes |
| position | Utf8 | Direct (`cf:Position`) | contact | list-ok | ∅ | yes |
| employee_id | Utf8 | Direct (`cf:Employee ID`) | contact | list-ok | ∅ | yes |
| contact_url | Utf8 | Direct (`cf:Contact URL`) | contact | list-ok | ∅ | yes |
| time_zone | Utf8 | Direct (`cf:Time Zone`) | contact | list-ok | ∅ | yes |
| city | Utf8 | Direct (`cf:City`) | contact | list-ok | ∅ | yes |
| ⟂ office_phone | Utf8 | **Cascade** (`cascade:Office Phone`) | business | cascade-from business | ∅ | yes |
| ⟂ vertical | Utf8 | **Cascade** (`cascade:Vertical`) | unit→business | cascade-from unit/business | ∅ | yes |
| dashboard_uuid | Utf8 | Direct (`cf:Dashboard UUID`) | contact | list-ok | ∅ | yes |

### 3.5 project (LEAF, body_parameterized=True, warmable=False, S3=319) — 3 specific cells

Receipt: `schemas/project.py`; descriptor `entity_registry.py` ~L885-905 (`body_parameterized=True`, `warmable=False`). S3 census: 319 (highest — query-path materialized on demand).

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| status | Utf8 | Direct (`cf:Status`, FM-2 fix from `source=None`) | project | list-ok | ∅ | yes (319, on-demand) |
| ⟂ office_phone | Utf8 | **Cascade** (`cascade:Office Phone`) | business | cascade-from business | ∅ | yes |
| ⟂ vertical | Utf8 | **Cascade** (`cascade:Vertical`) | unit→business | cascade-from unit/business | ∅ | yes |

### 3.6 section (Section, S3=319 + legacy "sections"=192) — 3 specific cells

Receipt: `schemas/section.py` (structurally identical to project: status + office_phone⟂ + vertical⟂).

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| status | Utf8 | Direct (`cf:Status`, FM-2 fix from `source=None`) | section | list-ok | ∅ | yes (319) |
| ⟂ office_phone | Utf8 | **Cascade** (`cascade:Office Phone`) | business | cascade-from business | ∅ | yes |
| ⟂ vertical | Utf8 | **Cascade** (`cascade:Vertical`) | unit→business | cascade-from unit/business | ∅ | yes |

### 3.7 asset_edit (LEAF, warmable, warm_priority=5, S3=4) — 21 specific cells (10 Process + 11 AssetEdit)

Receipt: `schemas/asset_edit.py` (PROCESS_COLUMNS 10 + ASSET_EDIT_SPECIFIC_COLUMNS 11); descriptor `entity_registry.py:535-547`.

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| started_at | Utf8 | Direct (`cf:Started At`) | asset_edit | list-ok | ∅ | yes (4) |
| process_completed_at | Utf8 | Direct (`cf:Process Completed At`) | asset_edit | list-ok | ∅ | yes |
| process_notes | Utf8 | Direct (`cf:Process Notes`) | asset_edit | list-ok | ∅ | yes |
| status | Utf8 | Direct (`cf:Status`, enum) | asset_edit | list-ok | ∅ | yes |
| priority | Utf8 | Direct (`cf:Priority`, enum) | asset_edit | list-ok | ∅ | yes |
| process_due_date | Utf8 | Direct (`cf:Due Date`) | asset_edit | list-ok | ∅ | yes |
| assigned_to | Utf8 | Direct (`cf:Assigned To`, people) | asset_edit | list-ok | ∅ | yes |
| ⟂ vertical | Utf8 | **Cascade** (`cascade:Vertical`) | unit→business | cascade-from unit/business | ∅ | yes |
| ⟂ office_phone | Utf8 | **Cascade** (`cascade:Office Phone`) | business | cascade-from business | ∅ | yes |
| specialty | List[Utf8] | Direct (`cf:Specialty`, multi-enum) | asset_edit | list-ok | ∅ | yes |
| asset_approval | Utf8 | Direct (`cf:Asset Approval`, enum) | asset_edit | list-ok | ∅ | yes |
| asset_id | Utf8 | Direct (`cf:Asset ID`) | asset_edit | list-ok | ∅ | yes |
| editor | Utf8 | Direct (`cf:Editor`, people) | asset_edit | list-ok | ∅ | yes |
| reviewer | Utf8 | Direct (`cf:Reviewer`, people) | asset_edit | list-ok | ∅ | yes |
| ★ offer_id | Int64 | Direct (`cf:Offer ID`, integer key) | asset_edit | needs-per-task-GET | ∅ | yes |
| raw_assets | Utf8 | Direct (`cf:Raw Assets`) | asset_edit | list-ok | ∅ | yes |
| review_all_ads | Boolean | Direct (`cf:Review All Ads`, Yes/No enum) | asset_edit | list-ok | ∅ | yes |
| ★ score | Float64 | Direct (`cf:Score`, number) | asset_edit | needs-per-task-GET | ∅ | yes |
| asset_edit_specialty | List[Utf8] | Direct (`cf:Specialty`, multi-enum) | asset_edit | list-ok | ∅ | yes |
| ★ template_id | Int64 | Direct (`cf:Template ID`, integer) | asset_edit | needs-per-task-GET | ∅ | yes |
| ★ videos_paid | Int64 | Direct (`cf:Videos Paid`, integer) | asset_edit | needs-per-task-GET | ∅ | yes |

### 3.8 asset_edit_holder (HOLDER, warmable, warm_priority=6, S3=5) — 1 specific cell

Receipt: `schemas/asset_edit_holder.py`; descriptor `entity_registry.py:792-808` (`category=HOLDER`, `parent_entity="business"`, `holder_for="asset_edit"`, `key_columns=("office_phone",)`).

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| ⟂ office_phone | Utf8 | **Cascade** (`cascade:Office Phone`, **SOLE key — 100% cascade dependency**) | business | cascade-from business | ∅ | yes (5) |

Schema comment (verbatim): "Sole key column (100% cascade dependency): if cascade fails, this entity is entirely unlookable."

### 3.9 process (LEAF, S3=0 — UN-WARMED as base "process"; pipeline variants warmed) — 3 specific cells

Receipt: `schemas/process.py`; descriptor `entity_registry.py:554-560` (base `process`, `primary_project_gid=None` dynamic). 9 pipeline variants (process_sales..process_expansion, warm_priority 10-18) share this schema.

| field | dtype | mode | canonical-source | fetch-path | pop-policy | warmed |
|---|---|---|---|---|---|---|
| ⟂ office_phone | Utf8 | **Cascade** (`cascade:Office Phone`) | business | cascade-from business | ∅ | no (base process S3=0) |
| ⟂ vertical | Utf8 | **Cascade** (`cascade:Vertical`) | unit→business | cascade-from unit/business | ∅ | no |
| pipeline_type | Utf8 | **Derived** (`source=None`, set by aggregator) | computed | n/a (aggregator) | ∅ | no |

---

## 4. Summary Census

| Metric | Count | Receipt |
|---|---|---|
| **Entities (materialized schema files)** | 10 | `git ls-tree origin/main` schemas/ (base,business,unit,offer,contact,project,section,asset_edit,asset_edit_holder,process) |
| **Entity descriptors in registry** | 29 | `entity_registry.py` `grep -c 'EntityDescriptor('` = 29 (10 schemas + 9 process-pipeline variants sharing process.py + holders/observation w/o own schema) |
| **BASE shared cells** | 13 | `schemas/base.py` BASE_COLUMNS |
| **Entity-specific cells** | 69 | business 6 + unit 9 + offer 11 + contact 12 + project 3 + section 3 + asset_edit 21 + asset_edit_holder 1 + process 3 |
| **Total distinct schema cells** | **82** | 13 BASE + 69 specific |
| **Total cells if BASE counted per-entity** | **199** | (13 × 9 non-base entities) + 69 + 13 BASE-as-own = 117 + 69 + 13; effective lattice 10 entities × (13 + specific) |
| **NUMBER-typed cells ★** | **11** | unit{mrr,weekly_ad_spend,discount}, offer{cost,mrr,weekly_ad_spend}, asset_edit{offer_id,score,template_id,videos_paid} (10 in schema) + note on model-only number fields |
| **CASCADE cells ⟂** | **17** | unit 2, offer 3, contact 2, project 2, section 2, asset_edit 2, asset_edit_holder 1, process 2; (unit.office is a 3rd unit cascade → 18 if office counted as cascade) |
| **Cells with NO population policy ∅** | **80 of 82** | only offer.mrr + offer.offer_id are in `_VALUE_COLUMNS_BY_ENTITY` |
| **Derived cells (source=None)** | **8** | BASE: type,date,url,section,parent_gid (5) + offer.name + business.name + process.pipeline_type |
| **Un-warmed entities (S3 census = 0)** | **5+** | offer_holder, unit_holder, contact_holder, location, hours (per LIVE CORPUS census) + base process |

### Number-typed cell roster (the path-asymmetry class)

The path-asymmetry vulnerability (LIVE CORPUS defect-face (a): list-`number_value` vs
per-task-GET-`number_value` server divergence) applies to every cell backed by an Asana
Number custom field. Confirmed schema-projected numeric cells:

1. `unit.mrr` (Decimal, `cf:MRR`) — **the 571-gun source; live 0/3021 nonnull**
2. `unit.weekly_ad_spend` (Decimal, `cf:Weekly Ad Spend`)
3. `unit.discount` (Decimal schema / **EnumField model — drift**)
4. `offer.cost` (Utf8 schema / **NumberField model — drift**)
5. `offer.mrr` (Decimal, `cascade:MRR` from unit) — **cascade + number + floor**
6. `offer.weekly_ad_spend` (Decimal, `cascade:Weekly Ad Spend` from unit)
7. `asset_edit.offer_id` (Int64, `cf:Offer ID`)
8. `asset_edit.score` (Float64, `cf:Score`)
9. `asset_edit.template_id` (Int64, `cf:Template ID`)
10. `asset_edit.videos_paid` (Int64, `cf:Videos Paid`)

(Note: `unit`/`offer` also carry Number-typed fields ONLY in the model layer that are NOT
projected into the materialized schema — e.g. `unit.meta_spend`/`tiktok_spend` = `NumberField()`
at `models/business/unit.py:119-121`, `offer.voucher_value`/`budget_allocation` at
`models/business/offer.py:137-138` — with NO schema cell. These are model-only un-materialized
number fields — flagged in §6 Unknowns as candidate schema cells.)

---

## 5. Schema/Model Type-Drift Sweep (defect-face (b): silent-null risk)

Mechanical comparison of schema `dtype`/`source` vs model field-class declaration. Drift =
schema and model disagree on the value type → coercer silent-null risk.

| cell | schema (receipt) | model (receipt) | drift class |
|---|---|---|---|
| `unit.discount` | `dtype="Decimal"`, `source="cf:Discount"` (`schemas/unit.py:38-43`) | `discount = EnumField()` (`models/business/unit.py:118`) | **Decimal-vs-Enum** — schema expects number, model extracts enum string ("10%","20%","None") → coercer null-on-cast |
| `offer.cost` | `dtype="Utf8"`, `source="cf:Cost  # Number field"` (`schemas/offer.py` cost block) | `cost = NumberField()` (`models/business/offer.py:136`) | **Utf8-vs-Number** — schema declares text for a Number field; number_value coerced to string |
| `unit.mrr` / `offer.mrr` | `dtype="Decimal"` | `mrr = NumberField(field_name="MRR")` (`models/business/mixins.py:95`) | **aligned** (Decimal↔NumberField) — drift NOT the null cause; null cause is path-asymmetry/fetch |

CONFIRMED drift cells: **2** (`unit.discount`, `offer.cost`). The mixin financial fields
(`mrr`,`weekly_ad_spend` = NumberField↔Decimal) are type-aligned, so the unit.mrr 0/3021 null
is a FETCH/PATH defect (face (a)), not a type-drift defect (face (b)). Two distinct null
mechanisms confirmed coexisting in the lattice.

---

## 6. Unknowns (topology-cartographer flags; downstream to resolve)

### Unknown: Model-only Number fields absent from materialized schema
- **Question**: Are `unit.meta_spend`, `unit.tiktok_spend`, `offer.voucher_value`, `offer.budget_allocation` (all `NumberField()` in models, no schema cell) intentional omissions or un-materialized cells?
- **Why it matters**: They are path-asymmetry-vulnerable Number fields invisible to the schema-derived FPC; if added later they inherit the unit.mrr defect with no floor.
- **Evidence**: `models/business/unit.py:119,121`, `models/business/offer.py:137-138` declare NumberField; no matching ColumnDef in schemas/{unit,offer}.py.
- **Suggested source**: dataframe-layer owner / PRD-0024 scope.

### Unknown: Un-warmed cells for 5 registered entities
- **Question**: offer_holder/unit_holder/contact_holder/location/hours have descriptors + GIDs but S3 census = 0. Deliberate (lazy) or warming gap?
- **Why it matters**: Their cells cannot be coherence-observed (no parquet to join); a per-field SLI observatory would show them as null-coverage by absence, not by defect.
- **Evidence**: LIVE CORPUS S3 census (offer_holder/unit_holder/contact_holder/location/hours NOT in `aws s3 ls dataframes/` segment list); `entity_registry.py:735-744` unit_holder.
- **Suggested source**: hierarchy_warmer warm-set config / warm_priority gaps.

### Unknown: Cascade resolution-order for `vertical` (Unit-OR-Business)
- **Question**: `cascade:Vertical` is documented "from Unit or Business ancestor (warm_priority=2/1)" — which wins when both present? Topology records the dual-source; resolution precedence is resolver behavior.
- **Why it matters**: Determines whether the FPC coherence invariant for vertical is single- or multi-source.
- **Evidence**: `schemas/offer.py`/`process.py` vertical block comment "Cascades from Unit or Business ancestor".
- **Suggested source**: `dataframes/resolver/cascading.py` (dependency-analyst territory).

---

## 7. Confidence Ratings

- **HIGH** (build-manifest/schema-derived): all 82 cell classifications, all cascade cells, all mode assignments — each cites a `source=` line from a schema file at origin/main.
- **HIGH**: the 2 confirmed type-drift cells (schema dtype line + model field-class line both pasted).
- **HIGH**: 571-gun, unit.mrr 0/3021, offer.mrr 1325/4070 — live DuckDB receipts this pass.
- **MEDIUM**: number-typed roster boundary (model-only NumberFields) — corroborated by model grep but not schema-projected; flagged as Unknown not asserted as cells.
- **MEDIUM**: S3 warmed-counts — from LIVE CORPUS census handed in, not independently re-counted this pass (re-run `aws s3 ls dataframes/ --recursive` to confirm).
