---
type: spec
status: accepted
---

# Dynamic Field Vocabulary & Coherence — Alignment Brief

- **Status:** Aligned (human-confirmed via 3-phase structured interview, 2026-06-25)
- **Slug:** gfr-dynvocab
- **Relationship:** **Sibling initiative** to GFR (the certified gid→fields engine). Own frame/shape/telos; implemented on the same `feat/gfr-engine` branch as a **strictly-additive layer** that does NOT re-open the STRONG/PROVEN-candidate certs (CERT-1 guard, CERT-3 round-trip). The certified GFR engine *consumes* this; the GFR telos (cross-tenant company_id round-trip) stays clean and separate.
- **Origin:** the `asset_id` smell — `asset_id` is a field on the Offer **task model** (`models/business/offer.py:144` `TextField("Asset ID")`) but absent from the Offer **dataframe schema** (`dataframes/schemas/offer.py`), so GFR's "open-by-declaration / dynamic" promise silently couldn't resolve it. The canary for a deeper truth: **GFR's vocabulary is bounded by a hand-curated schema subset of the entity's real fields.**

## North-star

A **hybrid vocabulary**: a typed, cascade-aware, cross-tenant-certified **core** (company_id et al. — untouched) **+ a heuristically-typed dynamic tail** that reflects the entity's actual custom fields. The vocabulary reflects what the entity *really has*; "unknown" means *genuinely absent*; load-bearing fields stay typed and certified.

## Locked decisions (interview, 3 phases / 12 forks)

**Vision (Phase 1)**
- **Dynamism:** hybrid — typed core + heuristically-typed dynamic tail (NOT raw/untyped; the tail is coerced from Asana cf-type metadata).
- **Source of truth:** open to a **dynamic-schema paradigm shift**, meta-optimal per industry best-practice — to be grounded by the rnd inquisition (below), not pre-locked.
- **Unknown-field posture:** **governed-strict** — `UnresolvedError(unknown-field)` is *truthful* because the vocabulary ≡ the entity's real fields (a completeness guarantee, not a silent curation gap).
- **Blast radius:** **BOTH** the GFR-layer dynamic tail **AND** the dataframe-layer model↔schema coherence governance (root-cause; every dataframe consumer benefits, not just GFR).

**Design (Phase 2)**
- **Tail timing/home:** hybrid manifest + lazy value, favored at the **GFR-layer off the already-hydrated entry task** — leveraging the **~0 marginal cost** of reading more custom fields from a task already fetched in the certified entry phase. Preserves the certified **cache-only** contract (no new Asana call; the entry fetch is the accounted read). *(Frame-based wide-select remains the architect's alternative — see OPEN FORK.)*
- **Tail typing:** Asana cf-type → typed-value **heuristic table** (text→str, number→float, enum→label, multi_enum→list[str], date→date, people→list[gid], …) **+ per-field override registry**.
  - **PROOF OVERRIDE (from the outset):** `asset_id` — cf-type `text`, override to a **whitespace-agnostic comma-split → set** (`"a, b ,c"` → `{a,b,c}`). This is the worked example that validates the override mechanism on the field that started the initiative.
- **Typing provenance:** per-field **typing-origin tag** — `{typed: 'schema'|'heuristic', cf_type, …}` alongside `{value,status,source,as_of}`. A caller can tell a schema-validated value from a heuristically-coerced one.
- **Spine safety:** **strictly additive** — the certified identity/company_id path + GAP-1 guard are NOT modified; the tail is a separate non-regressing layer; the **105 certified tests are the regression gate**; company_id stays on the certified frame path.

**Scope/ambition (Phase 3)**
- **Initiative shape:** new sibling initiative, own frame/shape/telos, same branch, strictly-additive.
- **Coherence scope:** BOTH layers (GFR tail + dataframe model↔schema coherence governance — e.g. schema-derivation-from-model or a drift CI gate so the schema cannot silently diverge from the model).
- **Paradigm grounding:** via the **rnd-rite pantheon inquisition** — look outward first for the meta-optimal paradigm (named industry prior-art, evidence-graded) BEFORE framing. This is an upstream rite in the procession.
- **Generality:** **all-entities by design** — the tail mechanism is generic over `EntityType` (Business, Unit, Contact, Offer, AssetEdit, Process); Offer + `asset_id` is the proving ground, not a special case. Matches the "any gid → any field" north-star.

## Realization predicate (DRAFT — telos is user-sovereign; ratify before close)

`resolve(gid, fields)` returns, for any field the entity's task actually carries, a **correctly-typed** value with a **typing-origin provenance tag**; **`asset_id` resolves as a set** via the comma-split override; a requested-but-absent field returns a **truthful** `UnresolvedError(unknown-field)` backed by the manifest; the **dataframe schema is provably coherent with the task model** (drift gate); and the **105 certified GFR tests stay green** (spine unregressed). Proven generically across ≥2 EntityTypes, not Offer-only. NOT "merged", NOT "PRs green".

## Deliberately-OPEN forks (for rnd/architect + adversarial /qa — NOT pre-picked)

1. **Tail source:** task-based (off the hydrated entry task; favored by the marginal-cost insight) vs frame-based (wide-select / extract-all on the entity frame). Reconcile the freshness/consistency seam of serving the tail off the task while company_id comes off the cache frame.
2. **Entry-fetch completeness:** does the certified entry hydration already pull *all* custom fields (free tail), or is a wider opt-fields spec needed? (Cheap either way; verify live.)
3. **Dataframe-coherence mechanism:** schema-derivation/codegen-from-model vs a drift CI gate vs full reflective schema — the paradigm the rnd inquisition surfaces.
4. **Manifest source:** task cf keys vs a per-entity field registry.

## Out of scope / deferred
- Reverse resolution (DynamicIndex), writes (FieldResolver), bespoke query optimizer — permanent.
- Re-opening the certified identity spine (strictly-additive forbids it).
- The live-against-prod PROVEN-attested run + the unbuilt mint producer (GFR's, not this initiative's).

## Post-inquisition CORRECTION (2026-06-25, operator-directed): keying axis = NAME, not gid

The rnd inquisition's recon recommended keying the override registry + coherence layer by **cf `gid` not name** (Iceberg field-ID discipline). **The operator overturned this on domain evidence — it is a misfit here.** Authoritative correction (supersedes the gid-keying in the rnd recon/integration/handoff §1.1(b), GAP-4, FRAME-002):

- **The vocabulary identity axis is the canonical business-field NAME** — the model's `field_name="..."` / `NameNormalizer.normalize(cf.name)`. The entire codebase already keys by name end-to-end: `models/business/offer.py:144` `TextField(field_name="Asset ID")`; `dataframes/schemas/offer.py` `source="cf:Offer ID"`; `resolution/field_resolver.py:61` `name_to_gid`; `dataframes/resolver/default.py:92` `_index[normalize(cf.name)] = cf.gid`. The business meaning lives in the name.
- **cf `gid` is a runtime intra-task value HANDLE only** (name→gid→value within one hydrated task), **not** the identity/registry key. cf gids are opaque + per-workspace + **non-portable** across Asana projects/environments — keying by gid would defeat the portable, dynamic, fleet-generic goal. (The prototype already name-keyed; only the "switch to gid in prod" refinement is dropped.)
- **Iceberg's valid kernel (rename-stability)** is preserved differently: the model `field_name` is the canonical stable name (source of truth), and the **coherence drift-gate** flags model↔live-cf-name divergence. `DefaultCustomFieldResolver.build_index` already detects name collisions (`default.py:85-90`). We accept mild rename-fragility for portability + business-alignment; the gate mitigates.
- **The dataframe-coherence drift gate keys by name** (model `field_name` ↔ schema `cf:Name`) — it cannot key by gid (static declarations carry no runtime gids).
- **Strengthens the fleet path:** a NAME-keyed fleet contract registry (the moonshot Future-4 item) is portable across services; a gid-keyed one would not be.
- **Unchanged:** hybrid core+tail, HYP-1/HYP-2, asset_id→set, governed-strict, generality, strictly-additive, the certs, the ratified telos predicate (keying-axis-agnostic).

## Procession precedence (per operator)
**rnd-rite paradigm-optima inquisition** (look outward, meta-optimal, evidence-graded) → **myron `/frame`** (dynvocab envelope) → **pythia `/shape`** (sprint DAG + checkpoints) → **10x-dev build** (strictly-additive, adversarial /qa throughout) → **review-rite certs** (rite-disjoint). Each rite-switch is the operator's (MINE lever). Engine branch: `feat/gfr-engine` (currently at the rebased tip atop origin/main `376e1edd`).
