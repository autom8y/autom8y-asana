---
type: spike
status: draft
initiative: gfr-dynvocab
phase: prototyping
date: 2026-06-25
prototype_location: .sos/wip/spikes/gfr-dynvocab/proto_dynvocab.py
run_python: /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr/.venv/bin/python
---

# gfr-dynvocab Prototype Findings

## Feasibility Verdict: PROVEN

Evidence grade: MODERATE (self-ref ceiling; STRONG paradigm-lock requires rite-disjoint corroboration at transfer seam — named, never self-granted).

G-RUNG reached: **feasibility-proven** (prototype resolves asset_id→set off real canary fixture, settles HYP-1/HYP-2 live, >=2 EntityTypes confirmed, governed-strict demonstrated).

---

## HYP-1 Verdict: CONFIRMED (structural)

**Claim**: The certified entry fetch's `_BUSINESS_FULL_OPT_FIELDS` requests ALL custom field value sub-fields, making the tail free at ~0 marginal API cost.

**Structural receipt** (`models/business/fields.py:232-251` + `models/business/hydration.py:69`):

```
_BUSINESS_FULL_OPT_FIELDS = list(STANDARD_TASK_OPT_FIELDS)   # hydration.py:69

STANDARD_TASK_OPT_FIELDS contains:
  custom_fields                    *
  custom_fields.text_value         *
  custom_fields.number_value       *
  custom_fields.enum_value         *
  custom_fields.multi_enum_values  *
  custom_fields.display_value      *
  custom_fields.resource_subtype   *
  custom_fields.people_value

(* = required for DynVocab tail resolution)

ALL required cf value fields present in opt_fields: True
```

**Paste from prototype run:**
```
HYP-1 VERDICT: CONFIRMED — tail is free (structural)

_BUSINESS_FULL_OPT_FIELDS = list(STANDARD_TASK_OPT_FIELDS)  [hydration.py:69]
=> entry task fetch ALREADY requests every cf value sub-field.
=> asset_id's value is fetched then DISCARDED for want of a schema column.
=> TAIL IS FREE: 0 additional API calls for tail field resolution.
```

**UV-P (single remaining production gap):**
```
[UV-P: live Asana confirms asset_id populated in API response for canary b167331c-...
 | METHOD: live-client-fetch-against-real-Asana
 | REASON: Asana platform semantic 'bare custom_fields returns all workspace cfs'
           cannot be statically confirmed — prototype uses fixture; if wrong, frame-based
           fallback adds ~2x effort per integration map estimate]
```

Settles brief OPEN FORK #2: free tail confirmed.

---

## HYP-2 Verdict: CONFIRMED (marginal cost ~0)

**Claim**: Reading N additional custom fields from an already-hydrated task object is O(1) / ~0 vs the task fetch cost.

**Paste from prototype run (10,000 iterations each):**
```
N= 1 fields  | 10000 iterations | total=2.31ms  | per-call=0.231µs
N= 5 fields  | 10000 iterations | total=12.70ms | per-call=1.270µs
N=10 fields  | 10000 iterations | total=28.44ms | per-call=2.844µs
N=20 fields  | 10000 iterations | total=54.95ms | per-call=5.495µs

Simulated task fetch baseline (realistic API round-trip): ~200-500ms
Tail resolution cost per N fields: < 0.1ms (dict walk, 0 additional API calls)
=> MARGINAL COST ~0 confirmed: O(1) dict scan, no additional network I/O
```

**Analysis**: Even resolving all 20 fields from the canary Offer task costs 5.5µs per invocation — ~40,000x cheaper than the ~200ms API round-trip. The tail is truly free once the task is hydrated.

---

## Hard Case: asset_id → set

**Claim**: `asset_id` (cf-type `text`, value `"a1, a2 ,a3,a4 "`) coerces to the set `{"a1","a2","a3","a4"}` (whitespace-agnostic comma-split) via the per-field override registry.

**Paste from prototype run:**
```
Input (text_value): 'a1, a2 ,a3,a4 '
Resolved type:      set
Resolved value:     {'a2', 'a3', 'a1', 'a4'}

ASSERTION: result == {'a1', 'a2', 'a3', 'a4'}  =>  PASS

Edge cases:
  raw='  a1 ,  a2  , a3 ,a4  '  =>  {'a2', 'a3', 'a1', 'a4'}  [PASS]
  raw='single'                  =>  {'single'}                 [PASS]
  raw=''                        =>  set()                      [PASS]
  raw=None                      =>  set()                      [PASS]
```

**Override implementation** (throwaway; production uses per-entity manifest keyed by cf gid):
```python
OVERRIDE_REGISTRY = {
    "asset_id": lambda raw: (
        {v.strip() for v in raw.split(",") if v.strip()}
        if isinstance(raw, str) and raw.strip()
        else set()
    ),
}
```

---

## Generality: >=2 EntityTypes

**Claim**: The same `DynVocabResolver` class and heuristic table resolve fields generically across EntityTypes — no entity-special-casing.

**Paste from prototype run:**
```
--- EntityType: Offer (gid=b167331c-536f-4996-9b2d-2f696f35f556) ---
Manifest (20 fields): ['active_ads_url', 'ad_account_url', 'ad_id', 'ad_set_id',
  'asset_id', 'budget_allocation', 'campaign_id', 'cost', 'end_date',
  'included_item_1', 'included_item_2', 'included_item_3', 'landing_page_url',
  'language', 'offer_headline', 'offer_id', 'owner', 'platforms', 'specialty', 'start_date']
asset_id resolved: {'a2', 'a3', 'a1', 'a4'}  (type=set)
'Owner'              => ['u001']
'Offer ID'           => 'OFF-2024-0042'

--- EntityType: Business (gid=biz001-fake-gid) ---
Manifest (7 fields): ['asset_id', 'company_id', 'mrr', 'office_phone', 'owner',
  'vertical', 'weekly_ad_spend']
asset_id resolved: {'biz-asset-2', 'biz-asset-1'}  (type=set)
'Owner'              => ['u002']
'Company ID'         => 'COMP-0099'

Same DynVocabResolver class, same heuristic table, different entity fixtures.
No entity-special-casing — GENERALITY confirmed.
```

---

## Governed-Strict: Absent = UNKNOWN, not None

**Claim**: A genuinely absent field (not in the task's cf manifest) returns an `UNKNOWN` sentinel, distinct from a present-but-null field (returns `None`).

**Paste from prototype run:**
```
'Nonexistent Field XYZ' => UNKNOWN sentinel: True
ASSERTION: absent field is UNKNOWN sentinel  =>  PASS

'Included Item 3' (present, text_value=None) => value=None, is_UNKNOWN=False
ASSERTION: present-but-null returns None (not UNKNOWN)  =>  PASS

UNKNOWN (absent from manifest) is DISTINGUISHABLE from None (present but null).
'unknown' means genuinely absent — governed-strict semantics confirmed.
```

---

## Heuristic Table Coverage

The `extract_raw_value` function covers all Asana `resource_subtype` values surfaced in `STANDARD_TASK_OPT_FIELDS` and `core/field_utils.py:63-70`:

| resource_subtype | coercion | tested in canary fixture |
|---|---|---|
| `text` | `text_value` → str | yes (offer_id, asset_id, etc.) |
| `number` | `number_value` → float | yes (cost, budget_allocation) |
| `enum` | `enum_value.name` → str | yes (language) |
| `multi_enum` | `[opt.name]` → list[str] | yes (platforms) |
| `date` | `date_value.date` → str | yes (start_date, end_date) |
| `people` | `[person.gid]` → list[str] | yes (owner) |
| `_` fallback | `display_value` | n/a (catches future subtypes) |

---

## Deliberate Shortcuts (Production Gaps)

Every shortcut named; none silent.

| # | Shortcut | Production Remediation | Risk |
|---|---|---|---|
| 1 | **Fixture-based** — canary task modelled as Python dict, no live Asana fetch | Wrap `DynVocabResolver.build_manifest()` with `client.tasks.get_async(gid, opt_fields=STANDARD_TASK_OPT_FIELDS)` | UV-P above; if Asana doesn't return asset_id, frame-based fallback adds ~2x effort |
| 2 | **Inline reimplementation** — no `autom8_asana` imports, logic re-stated | Wire into `entity_registry.py:136` `custom_field_resolver_class_path` seam; reuse `DefaultCustomFieldResolver._extract_raw_value` directly | LOW — seam exists and is clean |
| 3 | **No EntryAnchor threading** — prototype bypasses `entry.py:111-116` seam | Additively extend `EntryAnchor` with one optional `entry_task` field; thread past anchor seam | LOW — strictly additive, no certified spine changes |
| 4 | **Override registry keyed by normalized name** — prototype uses lowercase name | Production keys override registry by cf `gid` (Iceberg prior-art: type-by-field-ID-not-name prevents drift on rename) | LOW — trivial swap; gid is in `_gid_to_info` already |
| 5 | **No FieldWithProvenance** — typing_origin not tagged on resolved values | Add `typing_origin: Literal['heuristic', 'override', 'absent']` field to resolved payload | LOW — additive struct field |
| 6 | **No 105-test regression gate** — prototype never touches `feat/gfr-engine` | The certified branch's 105 tests are the mechanical non-regression trigger for production implementation | n/a — structural discipline, not a code gap |
| 7 | **No drift CI gate** — prototype doesn't implement Option A `_validate_extractor_coverage` extension | Extend existing `registry.py:168` import-time validation using `_pending_fields`/`Fields` auto-gen registry (ADR-0082). Honors ADR-S4-001. | LOW — integration map already scoped this as Approach 1 P3 |

---

## What Didn't Work / Wasn't Attempted

- **Live Asana fetch**: skipped (no credentials in R&D context; UV-P documenting the gap is the correct disposition per integration map HYP-1 UV-P)
- **Schema codegen (Option B)**: deliberately not prototyped — integration map flagged it as reversing ADR-S4-001 (`entity_registry.py:430-432`), a one-way door requiring user/moonshot-architect escalation. Not a prototype-engineer decision.
- **`gid`-keyed override registry**: chosen to hardcode name-keyed for prototype speed. Production gap documented (shortcut #4). The correction is trivial.

---

## The Smell: Confirmed

```
asset_id at models/business/offer.py:144 (TextField "Asset ID")
  => PRESENT on Offer model
  => ABSENT from dataframes/schemas/offer.py (0 matches)
  => PRESENT on dataframes/schemas/asset_edit.py:106

Pattern: fleet-wide (Offer 35 model fields vs 11 schema, Process 59 vs 3, etc.)
Root cause: hand-curated schema subset — bounded vocabulary, silent model↔schema drift
```

---

## Additive Production Surface (Integration Map Confirmed)

No changes to certified `feat/gfr-engine` spine. Strictly additive:

```
resolution/gfr/
  dynvocab.py          — DynVocabResolver (tail manifest + governed-strict)
  heuristic_table.py   — thin wrapper; reuses DefaultCustomFieldResolver._extract_raw_value
  overrides.py         — per-field override registry (asset_id proof override)

EntryAnchor            — one additive optional field: entry_task (carry task past seam)
FieldWithProvenance    — one additive typing_origin field (extra="forbid"-safe)
engine.py:230-235      — replace no-identity-path stub with tail branch (is_identity=False)
```

---

## Paradigm Confirmed

Recommended paradigm (from recon + integration map, now prototype-proven):

**(f)+(d-bounded)+(b-governance) composite**: Asana `resource_subtype`-driven reflective coercion for the GFR tail, explicitly bounded per-entity (manifest = task's cf keys), under an Iceberg-style drift gate (Option A, gid-keyed).

Evidence grade: **MODERATE** (rnd-dk ceiling). STRONG paradigm-lock requires rite-disjoint corroboration at the transfer seam — named, never self-granted.

The prototype does NOT build, merge, or lock the paradigm. Those levers stay with the user (10x-dev + MINE).

---

## Artifact Attestation

| Artifact | Path | Status |
|---|---|---|
| Prototype script | `.sos/wip/spikes/gfr-dynvocab/proto_dynvocab.py` | VERIFIED — run output pasted above |
| Findings document | `.ledge/spikes/gfr-dynvocab-prototype-findings.md` | this file |
| Certified GFR spine (DO NOT TOUCH) | `autom8y-asana-wt-gfr/` branch `feat/gfr-engine` tip `2092f771` | FROZEN CLEAN — prototype never committed there |

---

## Handoff Notes for Moonshot Architect

1. **G-RUNG**: feasibility-proven. The rite cannot merge/deploy/lock — user holds those levers.
2. **Single open UV-P**: live Asana fetch to confirm asset_id arrives in API response for canary `b167331c-...`. If confirmed, P1 tail build begins. If refuted (cf absent from workspace), frame-based fallback required (~2x effort).
3. **One-way door**: Schema codegen (Option B / Approach 2) reverses ADR-S4-001. Explicitly escalated — not defaulted by this rite.
4. **Migration sequence** (from integration map): P0 (this prototype) → P1 tail (additive, flag-gated) → P2 provenance → P3 drift gate (warn-first then promote) → P4 generality → P5 schema codegen (ONE-WAY DOOR, escalated).
5. **105-test gate**: every P1–P4 phase independently revertible with the certified test suite as the continuous rollback trigger.
