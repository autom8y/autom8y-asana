---
type: spec
artifact_kind: tdd
initiative: gfr
title: GID Field Resolver (GFR) — Technical Design Document
status: draft
version: v2
revision: round-2 (post QA re-review GO-WITH-FIXES; residual_blocking + new_holes discharged as build-gate conditions)
sprint: sprint-0
created: 2026-06-25
revised: 2026-06-25
author: architect (10x-dev)
rite: 10x-dev
source_hash: f4f924d2684386093ef656ecde5e98613cdffce8
frame: .sos/wip/frames/gfr.md
shape: .sos/wip/frames/gfr.shape.md
brief: .ledge/specs/gfr-alignment-brief.md
telos: .know/telos/gfr.md
supersedes: gfr-tdd v1 (NO-GO on CRITICAL cross-tenant collision — office_phone identity-join, Vectors B1/B2/B3/B4/B5)
realization_predicate: >
  An Offer gid resolves company_id (== chiropractors.guid) BY GID-EXACT
  parent-chain identity (NOT an office_phone value-join) AND the minted
  {guid}@appointments.contenteapp.com address round-trips through the INBOUND
  office-resolution path (email-booking-intake resolve_office_stage) to the
  CORRECT tenant — asserted on the GUID-BOUND identity ctx.chiropractor_guid
  (resolve_office.py:92), NOT on the phone-fallback DISPLAY fields office_name/
  office_phone (:141/:169-170) — proven ONLY by a live tenant-identity
  integration test on a positively-selected real tenant with a known-a-priori
  guid PLUS a deliberately-broken cross-tenant fixture (B as keep='first'
  dedup-winner through join.py:157) firing RED, independently verified by the
  rite-disjoint PT-05 critic. NOT "resolver merged", NOT "PRs green", NOT a
  synthetic blanket pass. NOT earnable at this design altitude — nothing is built
  at HEAD (resolution/gfr/ empty); see TDD §0.2.
self_grade: "[STRUCTURAL | MODERATE]"  # self-ref cap; STRONG requires the PT-01/PT-05 review-rite disjoint critic; design-only at HEAD (§0.2)
adrs:
  - .ledge/decisions/ADR-gfr-seam1-ride-options.md  # SEAM1 ride: Option E adopted PROPOSED, pending PT-01 critic
  - .ledge/decisions/ADR-G2RECV-body-parameterized-entity-resolvability.md  # cache-only HARD line (consumed)
  - .ledge/decisions/ADR-seam1-entity-identity-key.md  # entity-partitioned key shape (consumed)
---

# Technical Design Document — GID Field Resolver (GFR) — v2

> **Sprint-0 design spine (v2).** Architect the thin orchestration interface
> `resolve(gid, fields) -> typed result` over the **verified** reuse substrate.
> **v2 closes the v1 NO-GO**: GFR resolves IDENTITY by gid + parent-chain edges
> and reads tenant-identity fields (`company_id` above all) off the GID-EXACT
> owning row. `office_phone` is NEVER the spine of identity resolution.
>
> **Self-grade capped MODERATE** per `self-ref-evidence-grade-rule`. The
> tenant-correctness STRONG attestation belongs to the rite-disjoint review
> critic at PT-05, not to this author.

## v2 changelog

The v1 NO-GO was a CRITICAL cross-tenant collision: v1 reached `company_id`
through the query-layer `office_phone` data-service join, which dedups
`keep='first'` then `how='left'` (`query/join.py:157`) — a phone collision
SILENTLY selects the wrong tenant. v2 rebuilds the identity path on gid +
parent-chain edges. Each change below maps to the closed v1 vector (B1–B5).

| # | v1 defect (vector) | v2 fix | Where |
|---|---|---|---|
| **B1** | `company_id` reached via `office_phone` value-join (collision-prone) | Identity path = entry-fetch -> `_traverse_upward_async` parent chain -> Business gid -> GID-EXACT row read of `company_id`. NO value-join on `office_phone` in the identity path. | §3, §4, §5 |
| **B2** | "wrong-row within project" (Vector A) un-guarded — phone match could surface another tenant's row | Business frames are MULTI-TENANT; the row lookup is GID-EXACT (`gid == business_gid` predicate), never a phone match. SEAM1 ride Option E re-asserts gid-identity on any legacy fallback. | §5.3, §10, §11 |
| **B3** | Negative test was a generic phone-collision fixture, not bound to a known tenant | Positively-selected REAL tenant with known-a-priori guid; dedup-loser seeding so the WRONG tenant would win under the OLD path; known-correct-guid binding; override-key defense. | §12 |
| **B4** | tier-2 "verify" used the `office_phone` analytics join (no guid/company_id column there) | tier-2 verify = `DataReadClient.get_business_by_guid_async(guid)` (by-guid), the same authoritative record the inbound resolver consumes. | §7 |
| **B5** | cache-only RED proof was scoped loosely; the entry fetch looked like a violation | The entry hydration fetch is modeled EXPLICITLY (triple duty) and ACCOUNTED. The cache-only RED proof is scoped precisely to "zero Asana-API calls on the offer-domain DATA-FRAME miss" — the entry fetch is a separate, counted read, not a cache-only violation. | §4.1, §6, §9 |

Also in v2:
- **THE CORE REDESIGN INVARIANT** (§0.1) stated as an explicit, tested design invariant.
- **Planner generalized** (§5): identity hops use in-frame `parent_gid` where the
  schema's immediate parent IS/reaches the owner (business/unit/contact/asset_edit),
  or the LIVE parent chain (offer — `parent_gid` in-frame points to OfferHolder, NOT
  Business). Latency/cost consequence documented.
- **SEAM1 ride Option E** (dual-read + on-fallback gid-identity re-assertion) ADOPTED,
  marked PROPOSED pending the rite-disjoint critic at PT-01. Option E closes Vector A only.
- **Vector B certification stub** (§11.5): the gid->project_gid discriminator owner
  is PINNED (`detection/tier1.py:38/117`); it maps gid->entity-TYPE, NOT gid->tenant;
  certified separately; the ride must NOT claim cross-tenant safety on it alone.

builds_on_top stays **YES** by construction (consume `hydration._traverse_upward_async`
+ gid-exact frame row lookup; do NOT edit `query/join.py` dedup or any frozen range or
scar test).

### v2-round-2 delta (post QA re-review GO-WITH-FIXES)

The round-1 v2 design CLOSED the v1 cross-tenant NO-GO at SPEC altitude (B1–B5
structurally closed, verified against HEAD f4f924d2 by the QA critic). Round-2
discharges the QA verdict's residual_blocking + new_holes as **gate conditions
carried into the build** — it does NOT reopen the collision:

| Item | Round-2 change | Where |
|---|---|---|
| residual_blocking #1 — PT-05 RED UNATTESTED | Added §0.2: this is a DESIGN artifact; nothing is built at HEAD (`resolution/gfr/` and `tests/.../gfr/` empty — SVR-confirmed); "PROVEN" is NOT earnable by this TDD, only by sprint-F build + PT-05 rite-disjoint critic. | §0.2, §12.4 |
| residual_blocking #2 — broken-fixture anti-vacuity | §12.2 step 4 now specifies B as the positively-constructed `keep='first'` dedup-WINNER through `join.py:157`, and a QA build-pass gate that INSPECTS the fixture's dedup ordering (not just the assertion text). | §12.2 |
| new_hole 1 — inbound phone-fallback | Added §11.6: routing is guid-exact (`resolve_office.py:92`); the `:141` phone-fallback enriches DISPLAY only (LOW); positive test asserts on `ctx.chiropractor_guid`, NEVER on `office_name`/`office_phone`. | §11.6, §12.1 |
| new_hole 2 — injected override/mapping params | §12.1 override-key defense now covers BOTH `_DEFAULT_OVERRIDES` AND injected `guid_overrides` (`:55/:72`); positive test asserts a clean by-guid HIT (`:111`), NOT the `:121` `guid_phone_mapping` fallback. | §12.1 |
| new_hole 3 — PT-03 call-count scoping | §4.1/§6.1/§9.3 now scope the cache-only delta to steps 5-8 ONLY; the legitimate 1+≤3 entry+chain reads (`hydration.py:670`) are EXCLUDED and the build must not conflate them with a cache-only violation. | §4.1, §6.1, §9.3 |
| open deps (SEAM1 Option E, Vector B) | Re-affirmed as honestly-scoped, genuinely-open release-gate dependencies pending rite-disjoint certs (PT-01, separate Vector-B cert). | §10, §11.5, §14 |

## 0.2 Attestation altitude — what this TDD is and is NOT (residual_blocking #1)

> **This is a DESIGN artifact at SPEC altitude.** The QA re-review verdict is
> **GO-WITH-FIXES** — a verdict on the SPECIFICATION's correctness, NOT an
> attestation that tenant-correctness is PROVEN.

**Nothing is built at HEAD f4f924d2.** Verified by direct inspection this pass
(SVR `git-ls-files`/`bash-probe`):

```yaml
structural_verification_receipt:
  claim: "no GFR package and no GFR tests exist at HEAD: src/autom8_asana/resolution/gfr/, tests/unit/resolution/gfr/, and tests/integration/test_gfr_tenant_roundtrip.py are all absent, so the realization-predicate RED proof cannot be discharged by this design-time TDD"
  verification_method: bash-probe
  verification_anchor:
    source: "ls -la src/autom8_asana/resolution/gfr/ tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py"
    command_output_verbatim: "\"src/autom8_asana/resolution/gfr/\": No such file or directory (os error 2)"
    exit_code: 2
    claim: "the GFR layer is unbuilt at HEAD; PT-05's live-positive + deliberately-broken-fixture-RED realization proof is a sprint-F build-time obligation, NOT something this TDD can claim closed"
```

**Therefore:**
- The realization predicate (`PROVEN`) is **NOT** earnable by ANY means at this
  altitude — not a green suite, not a passing merge, and not this design review.
  The grandeur anchor forbids exactly that green-dashboard fallacy.
- The B1–B5 closures are SPEC-altitude structural closures (the collision is
  bypassed BY CONSTRUCTION — gid-exact reads never touch `join.py:157`), verified
  by the QA critic against HEAD. That is a strong design result. It is NOT a
  tenant-correctness attestation.
- **`PROVEN` is earned ONLY at sprint-F** when (a) the live positive test passes
  on a positively-selected real tenant, AND (b) the deliberately-broken
  cross-tenant fixture fires RED, AND (c) the **rite-disjoint PT-05 review
  critic** independently verifies both (`self-ref-evidence-grade-rule`:
  self-assessment caps MODERATE; STRONG is the disjoint critic's). Anyone reading
  GO-WITH-FIXES as "collision closed, ship it" is committing the fallacy the
  grandeur anchor names.
- The residual_blocking items below are **gate conditions on the build**, not
  optional polish. The release gate holds the three open rite-disjoint certs
  (PT-01 SEAM1, PT-05 tenant-correctness, separate Vector-B cert) before the
  SEAM1 read path / tenant-identity claim is trusted cross-tenant.

## 0. Live-Verified Grounding (G-PROVE — re-fired this session at f4f924d2)

Every load-bearing substrate claim re-confirmed by direct inspection this pass
(SVR `verification_method: file-read` / `bash-probe`). This corrects
`code_verbatim_match: false` in the telos for the architect's own claim surface.

| Symbol / fact | Anchor (re-fired) | Role in GFR v2 |
|---|---|---|
| `_traverse_upward_async(entity, client, max_depth=10)` | `models/business/hydration.py:571` | the IDENTITY edge — walks `current.parent.gid` to the Business root |
| up-walk follows `current.parent.gid` | `hydration.py:646` | ONE parent per task => collision-free identity edge |
| cycle detection in up-walk | `hydration.py:649-656` | bounded, safe traversal (HydrationError on cycle/root/depth) |
| `hydrate_from_gid_async(gid,...)` | `models/business/hydration.py:208` | the ENTRY FETCH (triple duty: hydrate + type-detect + parent chain) |
| `detect_entity_type_async(task, client,...)` requires a hydrated Task | `models/business/detection/facade.py:405` | type-detect runs on the fetched Task, NOT a bare gid (forces the entry fetch) |
| `detect_entity_type(task,...)` (sync, Tiers 1-3, zero-API) | `models/business/detection/facade.py:356` | the O(1) entity-type discriminator (NOT model_validate — §6.3) |
| Vector-B discriminator: `_extract_project_gid` -> `registry.lookup` | `detection/tier1.py:38`, `:117` (`models/business/registry.py`) | gid -> project_gid -> entity-TYPE (NOT tenant). ADR-0101. See §11.5 |
| `company_id` ColumnDef `source="cf:Company ID"`, Business-ONLY | `dataframes/schemas/business.py:8-13` | the tenant-identity field; lives ONLY on Business |
| OFFER schema non-base columns (NO company_id) | `dataframes/schemas/offer.py:10-88` | office, office_phone, vertical, specialty, offer_id, platforms, language, name, cost, mrr, weekly_ad_spend |
| `parent_gid` ColumnDef is in BASE_COLUMNS (so ALL frames carry it) | `dataframes/schemas/base.py:98` | in-frame hierarchy column |
| `_extract_parent_gid` returns IMMEDIATE parent (`task.parent.gid`) | `dataframes/extractors/base.py:531` | offer's in-frame parent_gid = OfferHolder, NOT Business (§5.2) |
| Business frames are MULTI-TENANT (`primary_project_gid` shared) | `core/entity_registry.py:445` (`1200653012566782`) | Vector A: gid-exact row lookup MANDATORY (§5.3) |
| `office_phone` join_keys (business/offer/unit) — QUERY-LAYER, not identity | `core/entity_registry.py:451-455,523-526,504` | enrichment joins only; NEVER the identity spine (§0.1) |
| `execute_join` dedups `keep='first'` then `how='left'` | `query/join.py:157` | a phone collision silently selects a tenant with NO error/flag (the v1 trap) |
| `_execute_data_service_join` defaults `join_key="office_phone"`, returns METRICS | `query/engine.py:669`, default at `:701` | NO guid/company_id column here => NOT a tier-2 identity verify (§7) |
| data-service join hook (enrichment surface, used by tier-2-METRICS only) | `query/engine.py:174` -> `:176` | NOT GFR's company_id verify path in v2 |
| `get_business_by_guid_async(guid) -> BusinessRecord | None` | `…/autom8y-core/src/autom8y_core/clients/data_service.py:434` | tier-2 BY-GUID identity verify (B4) + the inbound resolver's lookup |
| INBOUND round-trip terminus `resolve_office_stage` | `…/email-booking-intake/.../pipeline/stages/resolve_office.py:53` | the REAL gid->guid->tenant inbound resolver (§11) |
| `_DEFAULT_OVERRIDES` (+ injected `guid_overrides`) merged then applied to FULL to-address BEFORE `@`-split | `…/resolve_office.py:46-50` (default), `:55` (injected), merged `:72`, applied `:80`, split `:84` | override-key defense for the positive round-trip (§12.1) — BOTH override surfaces |
| Inbound by-guid PRIMARY bind / phone DISPLAY fallback | `…/resolve_office.py:92` (`ctx.chiropractor_guid`), `:111` (clean by-guid HIT), `:121` (`guid_phone_mapping` fallback), `:141` (`get_business_by_phone_async`, DISPLAY only) | routing is guid-exact; DISPLAY is phone-collidable (§11.6, R-10) |
| `QueryEngine.execute_rows(...)` | `query/engine.py:77` | the projection+join executor GFR consumes (for FIELD reads, not identity) |
| FROZEN inner ranges | `query/engine.py:139-178,181`; `query/compiler.py:53-63,192-241`; `query/join.py` (whole) | NEVER edit — consume as client |
| `body_parameterized: bool = False` (default) | `core/entity_registry.py:151` | offer-domain descriptors default cache-only (HARD #1) |
| `legacy_fallback_enabled: bool = True` + 4 read-gates | `dataframes/storage.py:352`; `:1010,1195,1291,1372` | SEAM1 dual-read LIVE; the PT-01 fork |
| 42 `@pytest.mark.scar` markers / **12** files | `bash-probe` `grep -rc pytest.mark.scar tests/` (DRIFT-1) | the zero-diff regression guard |

**SVR receipts (mechanical, co-emitted with the v2 identity-redesign claims):**

```yaml
structural_verification_receipt:
  claim: "_traverse_upward_async is a collision-free identity edge: it follows current.parent.gid (one parent per task) with cycle detection, walking Offer->Business; GFR reuses it so company_id is reached by gid-exact parent chain, never by an office_phone value-join"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/models/business/hydration.py"
    line_range: "L644-L656"
    marker_token: "parent_gid = current.parent.gid"
    claim: "the up-walk advances strictly along the single parent reference and aborts on a revisited gid, so the path from an Offer to its Business root is unique and tenant-stable — GFR's identity spine consumes this, not the deduped phone join"
```

```yaml
structural_verification_receipt:
  claim: "company_id lives ONLY on the Business schema (source cf:Company ID); the Offer schema carries none of it, so Offer->Business traversal is mandatory and cannot be done in-frame from the offer row"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/dataframes/schemas/business.py"
    line_range: "L8-L13"
    marker_token: "name=\"company_id\","
    claim: "the company_id ColumnDef is declared on BUSINESS_COLUMNS with source cf:Company ID; grep of offer.py shows no company_id column, so the identity field is reachable only by reaching the Business row"
```

```yaml
structural_verification_receipt:
  claim: "the in-frame parent_gid column resolves to the IMMEDIATE parent gid (task.parent.gid), so an offer-frame parent_gid points at OfferHolder, not Business — reaching Business from offer requires the live multi-level parent chain, not an in-frame hop"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/dataframes/extractors/base.py"
    line_range: "L543-L545"
    marker_token: "if task.parent and task.parent.gid:"
    claim: "_extract_parent_gid returns only the immediate parent gid; the offer's immediate parent is OfferHolder (not in a queryable Business frame), so the offer->business identity hop is a live parent-chain traversal, distinct from the in-frame parent_gid hops available to business/unit/contact/asset_edit"
```

```yaml
structural_verification_receipt:
  claim: "the data-service join defaults its key to office_phone and returns analytics metrics with no guid/company_id column, so it cannot serve a tier-2 identity verify; the by-guid lookup get_business_by_guid_async is the authoritative identity record instead"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/query/engine.py"
    line_range: "L699-L702"
    marker_token: "entity_info.join_key if entity_info else \"office_phone\""
    claim: "_execute_data_service_join keys on office_phone by default and fetches metrics; tier-2 identity verify in v2 routes to autom8y-core get_business_by_guid_async (data_service.py:434), the same by-guid record the inbound resolver consumes — not this phone-keyed metrics join"
```

```yaml
structural_verification_receipt:
  claim: "the inbound resolver applies _DEFAULT_OVERRIDES to the full to-address before splitting on @, so a positive round-trip must assert the chosen guid is not an override key/value or the override would rewrite the address and mask a failure as a pass"
  verification_method: file-read
  verification_anchor:
    source: "…/autom8y/services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py"
    line_range: "L78-L88"
    marker_token: "to_address = overrides.get(to_address, to_address)"
    claim: "overrides are applied to the full to-address before the @-split that extracts the guid; the override-key defense in the positive test asserts the selected tenant's guid is not an override key/value, preventing a rewritten-address false pass"
```

```yaml
structural_verification_receipt:
  claim: "the inbound resolver binds tenant identity by-guid (ctx.chiropractor_guid = guid) BEFORE any phone lookup; the later get_business_by_phone_async call enriches DISPLAY fields only, so a phone collision there is a display mismatch, not a routing/PHI leak — the positive round-trip must assert on ctx.chiropractor_guid, never on office_name/office_phone (QA new_hole 1)"
  verification_method: file-read
  verification_anchor:
    source: "…/autom8y/services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py"
    line_range: "L92-L141"
    marker_token: "full_business = await data_read_client.get_business_by_phone_async(office_phone)"
    claim: "ctx.chiropractor_guid is set at :92 from the guid-exact primary lookup; the get_business_by_phone_async call at :141 runs AFTER and only fills office_name/office_phone (:169-170), so tenant routing is guid-exact on both sides and the phone-fallback cannot re-open the leak — only a LOW-severity display collision (R-10)"
```

```yaml
structural_verification_receipt:
  claim: "resolve_office_stage accepts TWO injectable override surfaces (guid_phone_mapping and guid_overrides) and merges guid_overrides into _DEFAULT_OVERRIDES, so the positive round-trip's override-key defense must cover BOTH, and must assert a clean by-guid HIT rather than the guid_phone_mapping fallback (QA new_hole 2)"
  verification_method: file-read
  verification_anchor:
    source: "…/autom8y/services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py"
    line_range: "L53-L73"
    marker_token: "overrides = {**_DEFAULT_OVERRIDES, **(guid_overrides or {})}"
    claim: "guid_phone_mapping (:54) and guid_overrides (:55) are injectable params; guid_overrides is merged over _DEFAULT_OVERRIDES at :72; the positive test must defend against both override sources and assert business is not None (:111 clean by-guid HIT) rather than the :121 guid_phone_mapping fallback"
```

```yaml
structural_verification_receipt:
  claim: "no GFR package or tests exist at HEAD f4f924d2; the realization-predicate RED proof is a sprint-F build obligation, so this TDD's GO-WITH-FIXES is a DESIGN verdict and cannot claim PROVEN (residual_blocking #1)"
  verification_method: bash-probe
  verification_anchor:
    source: "ls -la src/autom8_asana/resolution/gfr/ tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py"
    command_output_verbatim: "\"src/autom8_asana/resolution/gfr/\": No such file or directory (os error 2)"
    exit_code: 2
    claim: "the GFR layer is unbuilt at HEAD; PT-05's live-positive + deliberately-broken-fixture-RED proof, verified by the rite-disjoint critic, is what earns PROVEN — not this design review (§0.2)"
```

```yaml
structural_verification_receipt:
  claim: "the scar-test regression guard is 42 markers across 12 files at HEAD (DRIFT-1: 12 files, not the frame's 11); GFR edits none of them"
  verification_method: bash-probe
  verification_anchor:
    source: "grep -rln pytest.mark.scar tests/ | wc -l ; grep -rc pytest.mark.scar tests/ | grep -v ':0' | awk -F: '{s+=$2} END{print s}'"
    command_output_verbatim: "12\n42"
    exit_code: 0
    claim: "12 files, 42 markers — GFR's zero-diff obligation covers all 12 files; none are edited because GFR is a new sibling layer under resolution/gfr/"
```

---

## 0.1 THE CORE REDESIGN INVARIANT (non-negotiable, tested)

> **INVARIANT GFR-IDENTITY-1.** GFR resolves IDENTITY by `gid` + parent-chain
> edges, and reads tenant-identity fields (`company_id` above all) off the
> GID-EXACT owning row. `office_phone` (and any non-unique business attribute)
> is **NEVER** the spine of identity resolution. The query-layer `office_phone`
> joins are permitted ONLY for genuinely phone-scoped *enrichment*, never to
> reach a tenant-identity field.

**Why this is load-bearing.** Business frames are MULTI-TENANT — many tenants'
Business rows sit as ROWS in one project frame (`entity_registry.py:445`). The
existing query-layer join dedups `keep='first'` then `how='left'`
(`query/join.py:157`): a phone collision silently selects A tenant — the wrong
one — with NO error and NO flag. That is the v1 NO-GO. The only collision-free
edge to a tenant's identity is the parent reference itself: each task has
exactly ONE `parent.gid` (`hydration.py:646`), so the Offer->Business walk is
unique per tenant.

**How it is tested (the invariant is not prose):**
1. **Positive (live):** an Offer gid resolves to its OWN tenant's `company_id`
   via the parent chain + gid-exact row read (§12.1).
2. **Negative-by-construction (RED):** a regression fixture that re-introduces a
   `office_phone` value-join on the identity path must fire RED — a phone
   collision must NOT silently yield a tenant (§12.3). This is an
   anti-regression guard on the invariant itself.
3. **Structural (lint):** no `JoinSpec(... on="office_phone")` and no
   `_execute_data_service_join` appears anywhere on the `company_id` /
   identity code path in `resolution/gfr/`. The identity path's only
   cross-task edge is `_traverse_upward_async`. (PT-03 grep-zero assertion.)

---

## 1. System Context & Scope

### 1.1 What GFR is

A **gid-first, field-declarative READ facade** over the existing substrate.
One verb: `resolve(gid, fields) -> values`. The caller passes a gid and a list
of schema-declared field names; GFR returns the values with per-field
provenance, **hiding entity-tree topology entirely** (the caller never learns
whether the gid is a Business / Unit / Offer / Contact, whether resolution was
an up-traversal or a down-join, or which S3 frame served it).

GFR is an **interface, not a new engine**. ~80% of the substrate exists
(`gfr-alignment-brief.md:22`); the genuine new surface is a thin orchestration
layer that ASSEMBLES existing primitives — now including
`_traverse_upward_async` as the identity spine. **No bespoke query optimizer.**

### 1.2 Ranked vision (tie-breaking, from the brief §37-42)

1. **Interface decoupling** *(north star)* — topology fully hidden.
2. **Speed** — close second; runtime is availability-first.
3. **Correctness** — yields to the above **except** where a guardrail makes it
   inviolable (INVARIANT GFR-IDENTITY-1 §0.1; the central guard §6).
4. **Fleet reach** — earned later, not forced now.

### 1.3 Scope boundary

| In scope (v1) | Out of scope (v1) — already exists |
|---|---|
| Forward read: `gid -> fields` (identity by parent-chain) | Reverse: `fields -> gid` (`services/dynamic_index.py`, `universal_strategy.py`) |
| Provenance-tagged field hydration | Writes / write-back (`resolution/field_resolver.py`) |
| Tiered truth-source (cache default, by-guid verify on demand) | Bespoke optimizer (Polars + compiler pushdown) |
| Thin `autom8y-core` client **PROPOSE** | Freezing the core contract (human sign-off, PT-06) |
| Vector-A defense (gid-exact row, Option E) | Vector-B certification (gid->project_gid owner; §11.5, separate cert) |

---

## 2. Module Decomposition — `src/autom8_asana/resolution/gfr/`

New package, **sibling** to the existing `resolution/field_resolver.py`. Every
module is a NEW layer ON TOP; **zero** edits to frozen ranges or scar tests.
Conventions inherited from `resolution/` (domain-specific error subclasses;
`from autom8y_log import get_logger`; `_async` suffix; package exports in
`__init__.py`).

| Module | Responsibility (single, bounded) |
|---|---|
| `__init__.py` | Public facade re-export: `resolve_async`, `ResolvedFields`, `FieldWithProvenance`, `UnresolvedError`. The ONLY surface fleet callers import. Topology types (`EntityType`, `JoinSpec`, identity-path internals) are NOT re-exported — they stay hidden. |
| `entry.py` | **The ENTRY FETCH (workstream A).** `_fetch_and_anchor_async(gid, client)`: ONE `hydrate_from_gid_async` call (`hydration.py:208`) doing TRIPLE DUTY — (1) hydrate the Task, (2) `detect_entity_type_async` the entity_type, (3) obtain the parent chain to the Business root via `_traverse_upward_async`. Returns an `EntryAnchor(task, entity_type, business_gid, path)`. This is the ONLY Asana-API read GFR itself originates; it is accounted (§4.1, §6, B5), NOT a cache-only violation. |
| `engine.py` | Thin orchestration spine (workstream A). `resolve_async(gid, fields)`: entry-fetch -> partition fields by owner -> identity reads (gid-exact, off the parent-chain-anchored Business gid) + enrichment reads (CONSUME `QueryEngine.execute_rows`) -> hand rows to `posture`. Holds NO field-specific code and NO query logic. |
| `planner.py` | **Identity-vs-enrichment hop planning (workstream A+B).** Given (entity_type, requested fields), partition fields by owning entity via `SchemaRegistry`. For each owner, decide the hop CLASS: **identity hop** (in-frame `parent_gid` where the immediate parent IS/reaches the owner — business/unit/contact/asset_edit) vs **live parent-chain hop** (offer, whose in-frame `parent_gid` points to OfferHolder, not Business — §5.2). Emits a `ResolutionPlan`. Pure/synchronous; no I/O. |
| `guard.py` | The CENTRAL GUARD (workstream B + D policy seam). Checks BEFORE any frame access: (1) **field-legality / FM5**; (2) **cache-only on offer-domain** (reads `body_parameterized`); (3) **entity_type key-shape** (SEAM1); (4) **NEW — identity-path purity**: rejects any attempt to reach a tenant-identity field (`company_id`) via a `office_phone` join (INVARIANT GFR-IDENTITY-1, defense in depth). |
| `posture.py` | Runtime posture + provenance assembly (workstream C). Maps the upstream `RowsMeta` freshness side-channel into per-field `status`/`as_of`; applies stale=resolved + serve-stale-if-any + async-rebuild; enforces strict all-or-nothing on the field SET. |
| `truth_source.py` | Tiered truth-source policy (workstream D). Default tier-1 = local asana-cache `company_id` (`source='asana-cache'`) off the gid-exact Business row. Tier-2 = on-demand authoritative verify via `get_business_by_guid_async(guid)` (BY-GUID, §7) — NOT the office_phone analytics join. |
| `models.py` | Result types: `FieldWithProvenance`, `ResolvedFields`, `FieldStatus`, `TruthTier`, `ResolutionPlan`, `EntryAnchor`, `HopClass` enum. Pydantic, `extra="forbid"`. |
| `errors.py` | `GfrError(Exception)` base; `UnresolvedError(GfrError)` carrying `fields` + `reason`; `GuardViolationError(GfrError)` for the never-should-happen identity-via-phone attempt (defense in depth); `AmbiguousCardinalityError(GfrError)`. No bare `Exception`. |

**Why this decomposition (DIP / Clean Architecture Dependency Rule):** the
domain policy (`engine`, `planner`, `posture`, `guard`) depends on the substrate
only through stable abstractions — `_traverse_upward_async` (identity edge),
`RowsRequest`/`JoinSpec`/`execute_rows` (enrichment reads), and the
`get_business_by_guid_async` port (tier-2). Source dependencies point INWARD
toward the facade, never into frozen executor internals [DP:SRC-003 Martin
2017]. The new `entry.py` makes the single I/O-originating read explicit and
testable in isolation, satisfying B5's accounting requirement structurally.

---

## 3. The `resolve()` Facade — Signature & Result Types

### 3.1 Signature

```python
async def resolve_async(
    gid: str,
    fields: Sequence[str],
    *,
    client: AsanaClient,
    truth_tier: TruthTier = TruthTier.CACHE,   # CACHE (default) | VERIFIED (by-guid data-service)
    scalar: bool = False,                       # opt-in scalar sugar; default row-set native
) -> ResolvedFields:
    """Resolve schema-declared fields for a gid, topology hidden.

    Identity is resolved by gid + parent-chain (INVARIANT GFR-IDENTITY-1):
    the single entry fetch hydrates the task, detects its type, and walks the
    parent chain to the Business root; tenant-identity fields (company_id) are
    read off the GID-EXACT Business row, never via an office_phone value-join.

    Row-set native: gid -> 1..N rows. `scalar=True` raises
    AmbiguousCardinalityError if the result is not provably a single row.
    Strict all-or-nothing: if ANY requested field is genuinely unresolvable
    the WHOLE call raises UnresolvedError(fields=[...], reason=...). Stale-but-
    present counts as resolved. Never calls the Asana API on an offer-domain
    DATA-FRAME miss (HARD line #1); the entry fetch is a separate accounted read.
    """
```

`client: AsanaClient` is keyword-only and threaded to BOTH the entry fetch
(`hydrate_from_gid_async`) and `execute_rows`. It is NOT a topology leak — the
caller already holds a client; GFR never exposes entity_type / parent chain /
join-path back to the caller.

### 3.2 Result types (`models.py`)

```python
class FieldStatus(StrEnum):
    FRESH = "fresh"        # within TTL
    STALE = "stale"        # past TTL, served stale-within-bound; async refresh triggered
    # (no UNRESOLVED member — unresolved fields raise UnresolvedError, all-or-nothing)

class TruthTier(StrEnum):
    CACHE = "asana-cache"          # tier-1: local cached copy off the gid-exact row (default)
    VERIFIED = "data-verified"     # tier-2: data-service authoritative BY-GUID (get_business_by_guid_async)

class HopClass(StrEnum):
    LOCAL = "local"                # field on the entry entity's own frame row
    IN_FRAME_PARENT = "in-frame"   # owner reachable via in-frame parent_gid (business/unit/contact/asset_edit)
    PARENT_CHAIN = "parent-chain"  # owner reachable only via live _traverse_upward_async (offer->business)

class FieldWithProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: object | None
    status: FieldStatus
    source: TruthTier
    as_of: datetime | None

class ResolvedFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gid: str
    rows: list[dict[str, FieldWithProvenance]]   # ROW-SET NATIVE: 1..N rows
    row_count: int

    def scalar(self) -> dict[str, FieldWithProvenance]:
        """Scalar sugar. Raises AmbiguousCardinalityError if row_count != 1."""
        ...
```

**Strict all-or-nothing:** `reason` ∈ {`unknown-field`, `empty-frame`,
`entity-type-undetectable`, `no-identity-path`, `business-row-not-found`}. The
last two are NEW in v2: they fire when the parent chain cannot reach a Business
(`HydrationError` from `_traverse_upward_async`) or when the resolved
`business_gid` has no gid-exact row in the Business frame — both are
identity-resolution failures, surfaced explicitly rather than silently
falling back to a phone match.

---

## 4. The Algorithm

```
resolve_async(gid, fields, truth_tier, scalar):

  1. GUARD — FIELD LEGALITY (guard.py)
     for f in fields:
        if SchemaRegistry has no ColumnDef named f (across resolvable schemas):
           raise UnresolvedError(fields=[f], reason="unknown-field")

  2. ENTRY FETCH — the SINGLE accounted I/O read (entry.py)        # B5
     anchor = await _fetch_and_anchor_async(gid, client)
        # ONE hydrate_from_gid_async (hydration.py:208) doing triple duty:
        #   (a) task         = the hydrated Task
        #   (b) entity_type  = detect_entity_type_async(task, client)  (facade.py:405)
        #   (c) business_gid, path = _traverse_upward_async(task, client)  (hydration.py:571)
        # If detect -> UNKNOWN: raise UnresolvedError(reason="entity-type-undetectable")
        # If _traverse_upward_async raises HydrationError (no Business / cycle / depth):
        #   raise UnresolvedError(reason="no-identity-path")
     # NOTE: this is the ONLY Asana-API read GFR originates. It is ACCOUNTED,
     # NOT a cache-only violation. The cache-only guarantee (HARD #1) is scoped
     # to the offer-domain DATA-FRAME miss in step 5/6, where ZERO further API
     # calls fire.

  3. PLAN (planner.py — pure, synchronous)
     owners = { field -> owning_entity_type }                  # schema-driven
     for owner in distinct(owners.values()):
        hop = classify_hop(anchor.entity_type, owner)          # HopClass
          # LOCAL          : field on the entry entity's own row
          # IN_FRAME_PARENT: owner reachable via in-frame parent_gid
          #                  (business/unit/contact/asset_edit carry a parent_gid
          #                   that IS / is one in-frame hop from the owner)
          # PARENT_CHAIN   : owner reachable only via the live parent chain
          #                  (offer: in-frame parent_gid = OfferHolder, NOT Business)
        if hop is None: raise UnresolvedError(reason="no-identity-path")
     => ResolutionPlan(local_project=..., in_frame_hops=[...], parent_chain_owners=[...])

  4. GUARD — CACHE-ONLY + KEY-SHAPE + IDENTITY-PURITY (guard.py)
     # body_parameterized read off the descriptor (entity_registry.py:151):
     #   offer-domain (False) => registry-GID-required => cache-only DATA-FRAME read.
     # entity-partitioned key shape enforced: dataframes/{project_gid}/{entity_type}/…
     # IDENTITY-PURITY (NEW, INVARIANT GFR-IDENTITY-1): assert no plan element
     #   reaches a tenant-identity field (company_id) via an office_phone join.
     #   The identity reach is the parent chain + gid-exact row ONLY.

  5. IDENTITY READS — gid-exact, off the parent-chain anchor (engine.py)
     # For tenant-identity fields (company_id) the OWNER is always Business.
     # Read the Business row by GID-EXACT predicate against anchor.business_gid:
     id_req = RowsRequest(select=fields_on(Business),
                          where=PredicateNode(gid == anchor.business_gid))   # gid-exact, NOT phone
     id_resp = await query_engine.execute_rows("business", project_gid, client, id_req)
     # exactly one row by gid-exactness; if zero rows -> reason="business-row-not-found"
     # (Vector A closed by construction: gid-exact, never keep='first' phone dedup.)

  6. ENRICHMENT READS — phone-scoped fields ONLY (engine.py)
     # Non-identity, genuinely phone-scoped enrichment may use the existing
     # query-layer joins. These NEVER touch company_id (guard step 4 forbids it).
     # offer-domain DATA-FRAME miss here returns unresolved with ZERO API calls.
     enr_resp = await query_engine.execute_rows(entity_type, project_gid, client, enr_req)

  7. POSTURE + PROVENANCE (posture.py)
     for each field, derive status from resp.meta (freshness/stale_served/data_age):
        present + within TTL -> FRESH ; present + past TTL -> STALE + async rebuild
        absent because frame truly empty -> contributes to all-or-nothing failure
     if any requested field is empty-frame-unresolved:
        raise UnresolvedError(fields=[...empty...], reason="empty-frame")
     assemble ResolvedFields(rows=[{f: FieldWithProvenance(value,status,source,as_of)}...])

  8. CARDINALITY (models.py)
     if scalar: return result.scalar()   # raises AmbiguousCardinalityError if row_count != 1
     return result
```

### 4.1 The entry fetch — modeled explicitly (B5)

The entry fetch (step 2) is the load-bearing v2 change and is modeled as a
first-class, isolated unit (`entry.py`) for three reasons:

1. **It is mandatory.** `detect_entity_type_async` (`facade.py:405`) requires a
   *hydrated Task*, not a bare gid; and `_traverse_upward_async`
   (`hydration.py:571`) needs the Task to read `current.parent`. A bare gid
   cannot be type-detected or parent-walked. So a fetch is unavoidable for any
   gid GFR has not seen.
2. **It does triple duty in ONE round-trip.** `hydrate_from_gid_async`
   (`hydration.py:208`) already fetches with the full field set (the docstring
   notes "Use full field set so no re-fetch is needed when Business is found"),
   so hydrate + type-detect + parent chain are one fetch, not three.
3. **It is ACCOUNTED, not a cache-only violation (B5).** HARD line #1 (cache-only
   on offer-domain) is scoped precisely to the **offer-domain DATA-FRAME miss**
   (steps 5/6): on such a miss, ZERO *further* Asana-API calls fire. The entry
   fetch is a separate, named, counted read that happens BEFORE any frame
   access. The PT-03 RED test asserts: after the entry fetch, an offer-domain
   data-frame miss triggers ZERO additional Asana-API calls (mocked-client
   call-count delta == 0 across steps 5-8).

**The entry-phase read budget is bounded, named, and EXCLUDED from the cache-only
assertion (QA new_hole 3 — call-count scoping).** `_traverse_upward_async`
fetches each parent task with full `opt_fields` via `client.tasks.get_async`
(`hydration.py:670`) — so an offer chain is **1 entry hydrate** (`:208`) **+ up
to 3 per-level parent reads** (Offer -> OfferHolder -> Unit -> UnitHolder ->
Business, path length 3 per the `hydration.py` docstring). These 1+≤3 reads are
LEGITIMATE and happen INSIDE the entry phase (step 2). The PT-03 cache-only RED
proof MUST assert `delta == 0` over steps **5-8 ONLY** (the post-entry data-frame
phase). The build must **NOT** conflate the chain reads (legitimate, inside the
entry phase) with a cache-only violation: a test that counts ALL Asana reads
(entry + chain + frame) and expects 0 would FALSE-FAIL on the legitimate entry
budget. The correct assertion baselines the call count AFTER `_fetch_and_anchor_async`
returns, then asserts no further client call fires through steps 5-8.

**Could a `gid -> entity_type` index avoid even the entry fetch?** Considered
and REJECTED for v1:
- A `gid -> entity_type` index (cf. `tier1.py` registry maps *project_gid* ->
  entity_type, NOT gid -> entity_type) could short-circuit step 2(b) — but it
  CANNOT supply step 2(c), the parent chain. `company_id` lives on Business; an
  Offer gid still needs the Offer->Business walk to know WHICH Business, and the
  walk reads `current.parent.gid` off the live Task at each level. No persisted
  gid->entity_type index removes the need to traverse parents for the identity
  edge.
- A fuller `gid -> {entity_type, business_gid}` *identity index* COULD avoid the
  fetch — but building it correctly is itself the hard tenant-identity problem
  (it must be populated by the same parent-walk, and kept consistent as the tree
  changes). That is a v2-of-GFR optimization, explicitly deferred (Open question
  1, §14). For v1 the single accounted entry fetch is the correct,
  collision-free, lowest-risk design. The latency consequence is documented in
  §5.4.

---

## 5. The Generalized Planner — Identity Hops vs Enrichment (workstream A+B)

### 5.1 Hop classification

The planner partitions requested fields by owning entity (via `SchemaRegistry`),
then classifies each owner's hop:

| HopClass | When | Mechanism | Cost |
|---|---|---|---|
| **LOCAL** | field is on the entry entity's own schema | read the entry entity's own frame row (gid-exact) | cheapest |
| **IN_FRAME_PARENT** | entry entity is business/unit/contact/asset_edit AND owner is reachable via the in-frame `parent_gid` | the frame row already carries `parent_gid` (`base.py:98`); resolve the owner row by that gid (gid-exact) — at most one in-frame hop per `MAX_JOIN_DEPTH=1` | cheap (in-frame) |
| **PARENT_CHAIN** | entry entity is offer (or any entity whose in-frame `parent_gid` does NOT reach the owner) | the LIVE parent chain via `_traverse_upward_async` (entry fetch step 2c) — the only path to Business from offer | costs the entry fetch + per-level parent fetches |

### 5.2 Why offer is PARENT_CHAIN, not IN_FRAME_PARENT (the v2 nuance)

`parent_gid` IS a column on every frame (it is in `BASE_COLUMNS`,
`base.py:98`, spread into all schemas). But `_extract_parent_gid`
(`extractors/base.py:531`) returns the IMMEDIATE parent (`task.parent.gid`). For
an **offer**, the immediate parent is the **OfferHolder** — not Business, and
OfferHolder is NOT a queryable Business frame. The Offer->Business path is FOUR
levels (Offer -> OfferHolder -> Unit -> UnitHolder -> Business; path length 3
per the `hydration.py` docstring). So:

- **business / unit / contact / asset_edit:** the in-frame `parent_gid` either
  IS the Business gid (contact's holder chain is shallow) or is one in-frame
  gid-exact hop from the owner — IN_FRAME_PARENT is available and cheaper.
- **offer:** the in-frame `parent_gid` points at OfferHolder. There is NO
  in-frame column that carries the Business gid. The ONLY collision-free path to
  `company_id` is the live `_traverse_upward_async` chain. PARENT_CHAIN is
  MANDATORY for offer-rooted identity.

This is exactly why the entry fetch (which performs the parent walk) is
non-optional for an offer gid resolving `company_id`.

### 5.3 Vector A closed by GID-EXACT row read

Whichever hop class supplies the owner gid, the OWNER ROW is read by a
**gid-exact predicate** (`gid == owner_gid`), never by a phone match. Business
frames are multi-tenant (`entity_registry.py:445`); a phone match would risk
the wrong tenant's row (the `keep='first'` dedup trap, `join.py:157`). The
gid-exact read returns at most one row, deterministically the correct tenant.
If zero rows: `UnresolvedError(reason="business-row-not-found")` — explicit, not
a silent phone fallback.

### 5.4 Cost / latency consequence (documented, per directive #2)

PARENT_CHAIN for offer costs the entry fetch PLUS up to 3 per-level parent
fetches inside `_traverse_upward_async` (it fetches each parent task with full
fields, `hydration.py` per-level fetch). For a cold offer gid resolving
`company_id`, the identity edge is therefore ~1 (entry) + up-to-3 (chain) Asana
reads — bounded by `max_depth=10` but realistically ≤4. This is the price of
collision-free identity. Mitigations: (a) `_traverse_upward_async` is reused, so
once the chain is walked the Business gid is in-hand for the gid-exact field
read; (b) the persistent gid->{entity_type, business_gid} identity index (§4.1,
§14 Open question 1) is the documented future optimization if this latency
proves prohibitive; (c) tier-1 `company_id` reads then hit the warm Business
frame (fast). The north-star speed ranking (§1.2) yields to INVARIANT
GFR-IDENTITY-1 here: a fast wrong tenant is the failure the realization
predicate forbids.

---

## 6. Central Guard + Runtime Posture (workstreams B, C)

### 6.1 The central guard checks

| Check | Mechanism | Anchor | Failure mode |
|---|---|---|---|
| **FM5 field-legality** | requested field ∈ `SchemaRegistry` ColumnDefs | `dataframes/models/schema.py:108` | `UnresolvedError(reason="unknown-field")` |
| **Cache-only (HARD #1)** | read `body_parameterized` off descriptor; offer-domain ⇒ cache-only DATA-FRAME read; NO Asana-API fallback wired for frame misses | `core/entity_registry.py:151` | offer-domain data-frame miss -> `None`/unresolved, ZERO further API calls |
| **entity_type key-shape** | enforce `dataframes/{project_gid}/{entity_type}/…` (SEAM1) | `dataframes/storage.py` key shape | wrong key shape -> reject |
| **Identity-path purity (NEW)** | no plan element reaches `company_id` (or any tenant-identity field) via an `office_phone` join; identity reach = parent chain + gid-exact row ONLY | INVARIANT GFR-IDENTITY-1 §0.1 | `GuardViolationError` (defense in depth) |

**HARD line #1 is enforced by ABSENCE, proven by RED, and SCOPED to the
data-frame miss (B5).** There is no Asana-API frame-fallback path in
`resolution/gfr/`. The entry fetch (step 2) is a separate, accounted read. The
PT-03 RED test asserts an offer-domain data-frame miss returns
`UnresolvedError`/`None` with ZERO API calls AFTER the entry fetch (call-count
delta over steps 5-8 == 0). **The legitimate entry-phase budget (1 entry hydrate
+ ≤3 parent-chain reads, `hydration.py:670`) is EXCLUDED from this delta — the
count is baselined AFTER `_fetch_and_anchor_async` returns (new_hole 3); a test
that counts total reads and expects 0 would FALSE-FAIL on the legitimate chain.**

### 6.2 Runtime posture (unchanged from v1 — composes cleanly)

1. **Stale = resolved.** Present value satisfies the contract; `status='stale'`,
   async refresh triggered.
2. **Serve-stale-if-any + async rebuild** via the EXISTING singleflight/coalesce.
3. **Strict all-or-nothing on the SET.** Failure surface is exactly:
   {unknown-field, empty-frame, entity-type-undetectable, no-identity-path,
   business-row-not-found}.
4. **Per-field provenance** `{value, status, source, as_of}` from `RowsMeta`
   (`query/models.py:397-417`) — never fabricated.

### 6.3 The `model_validate` anti-pattern guard (carried from architect memory)

Type detection MUST use `detect_entity_type_async` (`facade.py:405`), the O(1)
`ProjectTypeRegistry` discriminator — **never** `Model.model_validate()`.
Pydantic `extra="allow"` means ANY task validates as Business; `model_validate`
is NOT a type discriminator. Documented systemic vulnerability
(`HierarchyTraversalStrategy`, `DependencyShortcutStrategy._try_cast`); GFR must
not reintroduce it. The parent walk in `_traverse_upward_async` ALSO uses type
detection (not model_validate) to recognize the Business root — GFR inherits
that correct discriminator by reusing the function.

---

## 7. Tiered Truth-Source (workstream D) — BY-GUID verify (B4)

### 7.1 The two tiers

| Tier | Source | Provenance `source` | When |
|---|---|---|---|
| **Tier-1 (default)** | local asana-cache `company_id` (`cf:Company ID`, `business.py:8-13`) read off the GID-EXACT Business row | `asana-cache` | `truth_tier=CACHE` (default); fast path |
| **Tier-2 (on demand)** | autom8y-data authoritative via `get_business_by_guid_async(guid)` (`autom8y-core data_service.py:434`) | `data-verified` | `truth_tier=VERIFIED`; forced for send-origination |

### 7.2 Tier-2 is a BY-GUID lookup, NOT the office_phone analytics join (B4)

The v1 design routed tier-2 through `JoinSpec(source="data-service")` ->
`_execute_data_service_join` (`engine.py:669`). v2 REMOVES that for identity
verify: that join DEFAULTS its key to `office_phone` (`engine.py:701`) and
returns ANALYTICS METRICS — there is **no guid/company_id column** in its result
(`_execute_data_service_join` fetches metrics, not the business identity
record). It cannot verify `company_id`.

Tier-2 instead calls `get_business_by_guid_async(guid)`
(`data_service.py:434`), which returns the authoritative `BusinessRecord` keyed
BY GUID — the SAME record the inbound resolver consumes (§11). The flow:
tier-1 gives `company_id` off the gid-exact Business row; tier-2 treats that
`company_id` as the candidate guid and asserts the authoritative
`get_business_by_guid_async(company_id)` returns a record whose identity matches
the anchored Business. The `as_of` for a tier-2 field is the data-service
response timestamp; for tier-1 it is the frame watermark.

GFR adds **no new** cross-service client — `get_business_by_guid_async` already
exists in autom8y-core. The `office_phone` analytics join remains available for
*genuinely phone-scoped enrichment metrics*, never for identity (§0.1).

---

## 8. Thin `autom8y-core` Client Surface — PROPOSE Only (workstream E, PT-06)

**HARD line #3: PROPOSE, do not freeze.** Separate repo
(`/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core`,
SVR-confirmed present — discharges R-5's UV-P), separate PR boundary.

- **Surface (proposed, draft):** a typed `GfrClient` exposing
  `resolve_async(gid, fields, *, truth_tier, scalar) -> ResolvedFields` — the
  same shape as the asana engine facade, decoupled from its implementation.
- **STOP gate:** the API is NOT frozen. The draft PR explicitly requests human
  sign-off before any freeze (PT-06 hard gate).
- **Reuse anchor:** the `company_id` semantic and the by-guid record already
  live in core (`BusinessResolveResponse.company_id` = "UUID before @ in
  appointments.contenteapp.com"; `get_business_by_guid_async`,
  `data_service.py:434`) — the proposed `GfrClient` aligns to existing models.
- **Non-blocking:** E does NOT block F or the realization predicate (R-5 low).

---

## 9. Test Plan

### 9.1 Locations & discipline

- **Service-layer unit tests** under `tests/unit/resolution/gfr/`: one file per
  module (`test_entry.py`, `test_engine.py`, `test_planner.py`, `test_guard.py`,
  `test_posture.py`, `test_truth_source.py`, `test_models.py`).
- **Coverage floor ≥80%** (brief §94).
- **Stateful tests** carry `pytestmark = [pytest.mark.xdist_group("gfr_resolver")]`.
- **Integration / live** tenant round-trip at
  `tests/integration/test_gfr_tenant_roundtrip.py` (sprint-F, §12).

### 9.2 Zero-diff obligation (HARD line #2 — PT-02 gate)

- **0 diffs** to `query/engine.py:139-178,181`, `query/compiler.py:53-63,192-241`,
  `query/join.py` (whole — INCLUDING the `keep='first'` dedup at `:157`; v2 does
  NOT touch it, it routes AROUND it via gid-exact reads).
- **0 diffs** to `models/business/hydration.py` (consume `_traverse_upward_async`
  and `hydrate_from_gid_async`, never edit).
- **0 diffs** to the **42 `@pytest.mark.scar` tests across 12 files** (DRIFT-1).
- A CI assertion (`git diff --name-only` against frozen paths + scar files) is
  the mechanical proof at PT-02.

### 9.3 Test matrix (per module)

| Module | Key cases |
|---|---|
| `entry.py` | one `hydrate_from_gid_async` call (`:208`) + up to 3 per-level `_traverse_upward_async` parent reads (`hydration.py:670`) for an offer chain — assert the entry-phase budget is `1 + ≤3` and is counted SEPARATELY from frame reads (the PT-03 baseline is taken AFTER `_fetch_and_anchor_async` returns); `_traverse_upward_async` HydrationError (no Business/cycle/depth) -> `UnresolvedError(no-identity-path)`; UNKNOWN type -> `UnresolvedError(entity-type-undetectable)`. |
| `planner.py` | hop classification: offer->Business is PARENT_CHAIN (NOT in-frame); business/unit/contact/asset_edit owner is IN_FRAME_PARENT; LOCAL when field on entry entity; `no-identity-path` when no hop exists; `MAX_JOIN_DEPTH=1` respected per in-frame hop. |
| `guard.py` | **RED proof (B5, new_hole 3 scoping)**: offer-domain DATA-FRAME miss -> `UnresolvedError`/`None`, mocked-client API call-count delta over **steps 5-8 ONLY** == 0 — baseline the count AFTER the entry fetch returns; the legitimate 1+≤3 entry+chain reads are EXCLUDED and the test must NOT expect total-reads==0; **identity-purity**: any `company_id`-via-`office_phone` plan -> `GuardViolationError`; unknown field -> `UnresolvedError(unknown-field)`; newly-declared ColumnDef resolves with zero new code. |
| `posture.py` | stale=resolved; serve-stale-if-any; all-or-nothing fires ONLY on the five reasons; provenance round-trips `{value,status,source,as_of}` from `RowsMeta`. |
| `truth_source.py` | tier-1 default `source='asana-cache'` off the gid-exact Business row; tier-2 forced -> `get_business_by_guid_async(guid)` called (assert the office_phone analytics join is NOT invoked for identity); `as_of` sourced from the serving tier. |
| `engine.py` | identity read is a gid-exact `RowsRequest(where=gid==business_gid)` (assert predicate is gid-exact, NOT phone); row-set native (no N->1 collapse); scalar sugar raises `AmbiguousCardinalityError`; end-to-end consume of `execute_rows` (no frozen-range edit). |
| `models.py` | `extra="forbid"` rejects unknown keys; `.scalar()` view semantics. |

### 9.4 qa-adversary rides throughout

qa-adversary pressure-tests the **design** (this TDD: INVARIANT GFR-IDENTITY-1,
the SEAM1 Option E fallback path, the all-or-nothing surface, cardinality
collapse, the entry-fetch accounting boundary) AND the build. Adversarial seeds:
the dedup-loser cross-tenant fixture (§12); a never-warmed-empty frame; a field
on two schemas (owner-ambiguity); a fixture that re-introduces an office_phone
identity join (must fire RED, §12.3).

---

## 10. SEAM1 Ride — Option E ADOPTED (PROPOSED, pending PT-01 critic)

Per directive #6, v2 ADOPTS **SEAM1 Option E — dual-read + on-fallback
gid-identity re-assertion** in the companion ADR, status **PROPOSED**, pending
the rite-DISJOINT review critic at PT-01. The ride decides HOW GFR reads across
the in-flight entity-partitioned storage migration
(`dataframes/{project_gid}/{entity_type}/…`, `storage.py:352`
`legacy_fallback_enabled=True`, read-gates `:1010,1195,1291,1372`). All options
SUPPORT the migration; none EXECUTE it (`ADR-SEAM1:103-104`).

**Option E in one line:** read the entity-partitioned key first; on miss, fall
back to the legacy partition (consuming `legacy_fallback_enabled`) BUT re-assert
the gid-identity on the fallback result — the served row's gid MUST equal the
anchored `business_gid` (or the requested entity gid), else reject. This closes
the medium-cross-tenant-risk cell that plain dual-read (old Option B) carried:
the legacy project-only partition cannot surface the wrong tenant's row because
the gid-exact re-assertion rejects any row whose gid ≠ the parent-chain-anchored
gid.

| Option | One-line | Cross-tenant risk | Coldframe cost | Migration safety |
|---|---|---|---|---|
| A build-on-miss | build entity-partitioned frame on miss, then read | low | high | medium |
| B dual-read | read new shape, fall back to legacy on miss | **medium** | low | high |
| C hybrid | dual-read serve + async build-on-miss | low | medium | high |
| D partition-pinned | entity-partitioned only; legacy miss = unresolved | low | low | low |
| **E dual-read + gid re-assertion (ADOPTED, PROPOSED)** | B's read path, but re-assert served gid == anchored gid on the legacy fallback | **low** | low | high |

**Option E closes Vector A only.** It does NOT close Vector B
(gid->project_gid->entity_type discriminator), which is a separate certification
(§11.5). The ride must NOT claim cross-tenant safety on its own.

PT-01 confirms Option E (or picks otherwise), hardened by the rite-DISJOINT
review critic (`.ledge/reviews/gfr-seam1-critic-verdict.md`) for cross-tenant
key-collision risk — the author cannot critique their own ride from inside their
vantage. Full slate + tradeoffs in the companion ADR.

---

## 11. Round-Trip Reconciliation (CORRECTED P5/P6 — load-bearing)

### 11.1 The real inbound target

The telos round-trip target is the **INBOUND** resolver, NOT asana's
`_resolve_office_phone`:

```
…/email-booking-intake/.../pipeline/stages/resolve_office.py:53  resolve_office_stage
  -> overrides = {**_DEFAULT_OVERRIDES, **(guid_overrides or {})}  (:72)  ◄── BOTH override surfaces (§12.1)
  -> to_address = overrides.get(to_address, to_address)  (:80)   ◄── applied to FULL to-address FIRST
  -> cleaned = to_address.replace("​","")   (:83)
  -> parts = cleaned.split("@") ; guid = parts[0].strip()  (:84-88)
  -> ctx.chiropractor_guid = guid  (:92)   ◄── TENANT ROUTING bound by-guid HERE (§11.6)
  -> business = await data_read_client.get_business_by_guid_async(guid)  (:105)
  -> business is not None => clean HIT  (:111)  ; elif guid in mapping => phone fallback  (:121)
  -> get_business_by_phone_async(office_phone) => office_name/office_phone DISPLAY only  (:141, :169-170)
  -> raise OfficeResolutionError("…not found…") on miss
  -> _DEFAULT_OVERRIDES safety-net map  (:46-50)
```

**The telos chain:**
```
GFR(Offer gid)
  -> company_id (== chiropractors.guid)   [GFR forward identity, this repo, by parent-chain]
  -> mint {guid}@appointments.contenteapp.com   [PRODUCER — UNBUILT, §11.3]
  -> email-booking-intake resolve_office_stage  [INBOUND terminus]
  -> resolves back to the SAME tenant   [POSITIVE]
```
A DIFFERENT tenant's gid must NEVER mint THIS tenant's address (NEGATIVE — must
fire RED). `company_id == chiropractors.guid == the UUID before @` is the pivot
(`autom8y-core .know/feat/ads-asana-clients.md:84`).

### 11.2 The outbound resolver is a DIFFERENT resolver — reconcile, do not bind

`asana _resolve_office_phone` (`conversation_audit/workflow.py:547`) resolves
`ContactHolder -> parent Business -> office_phone` — an OUTBOUND resolver in the
OPPOSITE direction. The telos round-trip is NOT bound to it. The binding inbound
target is `resolve_office_stage`. This TDD records the correction; the telos YAML
line-52 anchor is superseded (recommend amendment at next `/frame`).

### 11.3 Producer status: UNBUILT

The `{guid}@appointments.contenteapp.com` MINTING surface is unbuilt (no minting
code in `src/autom8_asana` at HEAD). GFR supplies `gid->guid`; the mint is
downstream and out of GFR's build scope. **GFR's half (`gid -> company_id ->
guid`) MUST be live** even if the mint is stubbed at the known boundary
(sprint-F entry criterion, R-6 mitigation).

### 11.4 GFR's forward identity vs the inbound reverse lookup (asymmetry)

GFR's forward path is `Offer gid -> Business (parent chain) -> company_id (guid)`
— gid-exact, parent-chain identity (§4, §5). The inbound resolver's path is
`guid -> get_business_by_guid_async(guid) -> BusinessRecord` — the REVERSE
lookup. They MEET at the guid: GFR produces it; the inbound consumes it. tier-2
verify (§7) uses the SAME `get_business_by_guid_async`, so a tier-2-VERIFIED
forward resolution and the inbound resolution consult the identical
authoritative record — the round-trip is closed on one source of truth.

### 11.5 Vector B certification stub (gid->project_gid discriminator — PINNED)

Per directive #7, Vector B is the gid->project_gid->entity_type discriminator.
It is PINNED at HEAD (it did NOT grep-confirm at the previously-cited path in the
stale prose, but DOES confirm now):

- `detection/tier1.py:38` `_extract_project_gid(task)` reads
  `task.memberships[0].project.gid`.
- `detection/tier1.py:117` `registry.lookup(project_gid)` maps `project_gid` ->
  entity_type via `models/business/registry.py` (ADR-0101: "Only
  ProjectTypeRegistry is used for entity type detection").

**Critical scoping:** this discriminator maps gid -> entity **TYPE** (the class:
Business / Unit / Offer / Contact), NOT gid -> **tenant**. `project_gid` is
SHARED across tenants (many tenants' Business rows live in the one Business
project `1200653012566782`, `entity_registry.py:445`). Therefore Vector B
establishes WHAT KIND of entity a gid is, not WHICH tenant. The tenant identity
is established ONLY by the parent-chain + gid-exact row read (Vector A defense,
§5.3) — NOT by Vector B.

**Certification requirement (separate):** the Vector-B discriminator owner must
be certified separately (its correctness under multi-tenant project frames, lazy
workspace discovery `ADR-0109`, and registry bootstrap). **The GFR ride MUST NOT
claim cross-tenant safety on Vector B alone.** Owner to pin: the detection-rite /
registry maintainer; certification artifact:
`.ledge/reviews/gfr-vectorB-discriminator-cert.md` (separate from the SEAM1 and
tenant-correctness critics). Until certified, GFR's cross-tenant safety claim
rests on Vector A (gid-exact) + Option E (gid re-assertion on fallback) ONLY.

### 11.6 Inbound phone-fallback: routing is guid-exact, DISPLAY is phone-collidable (QA new_hole 1)

The inbound resolver `resolve_office_stage` has TWO lookups, and the round-trip
test must understand which one carries tenant identity:

| Step | Anchor | What it binds | Tenant-routing? |
|---|---|---|---|
| by-guid PRIMARY | `resolve_office.py:92` `ctx.chiropractor_guid = guid`; `:105/:111` `get_business_by_guid_async(guid)` | the TENANT identity (guid-exact, both sides) | **YES — this is the routing spine** |
| phone-mapping FALLBACK | `:121` `elif guid in mapping:` (injected `guid_phone_mapping`) | a phone for a guid-MISS | only on a by-guid miss; defended in §12.1 step 4a |
| phone DISPLAY lookup | `:141` `get_business_by_phone_async(office_phone)`; sets `:169-170` `ctx.office_name`/`ctx.office_phone` | DISPLAY fields only (office_name shown downstream) | **NO** |

**The leak is NOT re-opened by the `:141` phone-fallback.** `ctx.chiropractor_guid`
is bound by-guid at `:92` BEFORE any phone lookup; routing is guid-exact on both
sides (GFR's forward gid->guid is gid-exact; the inbound guid->record is
by-guid). The `:141` phone lookup runs AFTER the guid is already bound and only
populates the `office_name`/`office_phone` DISPLAY fields.

**There IS a residual DISPLAY-collision (LOW, not PHI-routing).** Because `:141`
keys on `office_phone`, a phone collision could surface the WRONG office's
`office_name` for display (`get_business_by_phone_async` is not gid-disambiguated).
Severity LOW — it is a display mismatch, not a routing decision and not a
PHI-tenant leak. **Consequence for the test (load-bearing):** the positive
round-trip (§12.1 step 4) asserts on `ctx.chiropractor_guid == G_correct`, NEVER
on `office_name`/`office_phone`, so a display-collision can never be mistaken for
a routing pass. This DISPLAY-collision is OUT of GFR's build scope (it is in the
inbound resolver, a different service) and is recorded here only so the test
asserts on the correct identity surface; if the display mismatch is to be closed,
that is an `email-booking-intake` change, flagged for that owner — not GFR's.

---

## 12. Negative Test Design (B3 closed — sprint-F)

Per directive #5, the negative test is positively-selected, dedup-loser-seeded,
known-correct-guid-bound, and override-key-defended. It is the heart of the
realization predicate.

### 12.1 POSITIVE — live tenant identity, real tenant, known guid

> **v2-round-2 correction (QA new_hole 1+2 closed).** The positive round-trip
> MUST assert on the **GUID-BOUND identity** (`ctx.chiropractor_guid`), NOT on
> the DISPLAY fields (`ctx.office_name` / `ctx.office_phone`). The inbound
> resolver binds the tenant by-guid at `resolve_office.py:92` BEFORE it ever
> consults a phone, then a SEPARATE phone-fallback (`:141`
> `get_business_by_phone_async(office_phone)`) populates only the
> `office_name`/`office_phone` DISPLAY fields (`:169-170`). Asserting on the
> display fields would let a phone-collision display-mismatch (LOW severity, NOT
> a routing/PHI leak — see §11.6) masquerade as a pass. The identity assertion
> is `ctx.chiropractor_guid == G_correct`.

1. **Positively select a REAL tenant** with a known-a-priori guid `G_correct`
   (read from the live data-service or a committed fixture of a real tenant —
   NOT synthetic). Record its Offer gid `O_correct` and its Business gid
   `B_correct`.
2. Drive `resolve_async(O_correct, ["company_id"], truth_tier=VERIFIED)`.
3. Assert the resolved `company_id == G_correct` (the parent-chain + gid-exact
   path yields the KNOWN-CORRECT tenant's guid).
4. Format `{G_correct}@appointments.contenteapp.com`, feed `resolve_office_stage`
   (or its `get_business_by_guid_async` seam), and assert on the **guid-bound
   identity**: `ctx.chiropractor_guid == G_correct` (`resolve_office.py:92`).
   Do **NOT** assert on `ctx.office_name`/`ctx.office_phone` — those transit the
   `:141` phone-fallback and are display-collidable (§11.6).
4a. **Clean by-guid HIT defense (new_hole 2).** Assert the inbound resolution is
    a clean data-service HIT — `get_business_by_guid_async(G_correct)` returns a
    non-null `business` (`resolve_office.py:111` `business is not None`),
    exercising the by-guid identity path — NOT the `:121` `elif guid in mapping`
    phone-mapping fallback. Construct the test with an EMPTY (or
    `G_correct`-absent) `guid_phone_mapping` so a guid-miss cannot be silently
    rescued by a phone, which would route through a phone-collidable office
    lookup and mask a real by-guid miss as a pass.
5. **Override-key defense (BOTH override surfaces — new_hole 2).** The inbound
   resolver merges TWO override sources at `resolve_office.py:72`
   (`overrides = {**_DEFAULT_OVERRIDES, **(guid_overrides or {})}`) and applies
   them to the FULL to-address BEFORE the `@`-split (`:80`). Assert `G_correct`
   is NOT a key OR value of EITHER:
   - the module-level `_DEFAULT_OVERRIDES` (`resolve_office.py:46-50`, the real
     `​33e3a930-...` key), AND
   - any injected `guid_overrides` param the test passes to
     `resolve_office_stage` (`:55`).
   Also assert the formatted `{G_correct}@…` address is not rewritten by
   `overrides.get(to_address, to_address)` (`:80`). If it were, the override
   would silently substitute a different address and the round-trip would pass
   for the WRONG reason. (If the only available real tenant happens to be the
   override key `33e3a930-...`, select a different real tenant —
   denominator-integrity: never let the override mask the test.)

### 12.2 NEGATIVE — dedup-loser seeding, the deliberately-broken cross-tenant fixture

1. **Seed a phone collision** where two real-shaped tenants A and B share an
   `office_phone`, and B is the **dedup-WINNER** under the OLD path
   (`keep='first'`, `join.py:157`) — i.e., the v1 office_phone join would have
   returned B's row for A's gid.
2. Drive `resolve_async(A_offer_gid, ["company_id"])` through the v2 identity
   path.
3. Assert BOTH:
   - (a) the v2 result is `A`'s KNOWN-CORRECT guid `G_A` (the parent chain +
     gid-exact read selects A's Business row, immune to the phone collision),
     OR — if A's frame is genuinely absent — `UnresolvedError`; it is NEVER
     `B`'s guid `G_B`.
   - (b) feeding the minted `{G_A}@appointments.contenteapp.com` to the inbound
     resolver NEVER resolves to B's tenant.
4. **Deliberately-broken cross-tenant fixture fires RED — the anti-vacuity
   hinge (residual_blocking #2).** A companion fixture that forces the OLD
   office_phone-join behavior on the identity path MUST produce B's guid for A's
   gid, and the test asserts THAT is RED (the broken path is detectably wrong).
   This proves the negative genuinely fails on wrong-tenant, not vacuously.

   **BUILD-TIME OBLIGATION (the TDD specifies; sprint-F must wire and the QA
   build pass must INSPECT):** the broken fixture is only non-vacuous if the
   dedup ordering is constructed so B is the `keep='first'` WINNER for A's gid.
   Concretely:
   - The broken fixture routes `company_id` through `execute_join`
     (`query/join.py:157`, `unique(keep='first')` then `how='left'`) keyed on the
     shared `office_phone` — i.e., it RE-INTRODUCES the v1 trap on the identity
     path on purpose.
   - The collision frame MUST be ordered so that B's row precedes A's row for the
     shared phone key, making B the `keep='first'` survivor of the dedup. If A
     were the survivor, the broken path would coincidentally return A's guid and
     the negative would pass VACUOUSLY — proving nothing.
   - The test asserts the broken path returns `G_B` (RED), and the v2 path returns
     `G_A` (GREEN). The DELTA between the two is the proof the gid-exact identity
     path actually defeats the collision.

   **§12.2-step-4 QA verification gate (anti-theater, residual_blocking #2):** the
   QA build pass MUST inspect the constructed fixture and confirm B is positively
   the `keep='first'` dedup-winner for A's gid — NOT merely that the assertion
   text names `G_A`/`G_B`. Reason: in v2 the gid-exact identity path
   STRUCTURALLY never consults the phone join, so step 3's `result == G_A`
   passes trivially even if the collision protection were absent. Step 3 alone is
   coverage theater; the test proves something ONLY if the broken-path companion
   fixture demonstrably fires RED through `join.py:157` with B as the survivor.
   A suite that ships step 3 without a verified-ordering step 4 is REJECTED.

### 12.3 INVARIANT regression guard (anti-re-introduction)

A unit-level RED test (`test_guard.py`): any plan that reaches `company_id` via a
`JoinSpec(... on="office_phone")` or via `_execute_data_service_join` raises
`GuardViolationError`. Plus a grep-zero structural assertion (PT-03): no
`office_phone` literal appears on the identity code path in `resolution/gfr/`.
This guards INVARIANT GFR-IDENTITY-1 against future drift.

### 12.4 Attestation (denominator-integrity)

PT-05 telos gate; the rite-DISJOINT review critic
(`.ledge/reviews/gfr-tenant-correctness-critic-verdict.md`) independently
verifies ALL of:
- **(a) Positive is real & by-guid-clean.** The positive round-trip is a live
  test on a positively-selected real tenant (NOT a synthetic blanket pass), it
  asserts on `ctx.chiropractor_guid == G_correct` (the guid-bound identity, NOT
  the `office_name`/`office_phone` DISPLAY fields — §11.6), and `G_correct`
  resolves as a clean `get_business_by_guid_async` HIT (`resolve_office.py:111`),
  NOT via the `:121` `guid_phone_mapping` fallback (§12.1 step 4a).
- **(b) Negative genuinely fails on wrong-tenant.** The deliberately-broken
  companion fixture is RED, and the critic confirms B is positively the
  `keep='first'` dedup-WINNER for A's gid through `join.py:157` (§12.2 step 4) —
  not a vacuous pass.
- **(c) Override-key defense holds on BOTH surfaces.** `G_correct` is neither a
  key nor a value of `_DEFAULT_OVERRIDES` NOR of any injected `guid_overrides`
  (`resolve_office.py:46-50`, `:55/:72`), and the formatted address is not
  rewritten by `overrides.get(...)` (`:80`) (§12.1 step 5).
- **(d) Cache-only delta is correctly scoped.** The PT-03 call-count RED asserts
  `delta == 0` over steps 5-8 ONLY (entry+chain reads excluded — §4.1, new_hole 3).

**`PROVEN` is NOT earnable until (a)-(d) pass AND this critic concurs.**
**Self-assessment caps MODERATE** (`self-ref-evidence-grade-rule`); the disjoint
critic's STRONG attestation is required for the telos claim (G-RUNG: this drives
toward PROVEN; merged/live/protecting-prod stay user-gated). This TDD's
GO-WITH-FIXES is a DESIGN verdict and does NOT attest tenant-correctness PROVEN
(§0.2).

---

## 13. Risk Map (centered on cross-tenant correctness)

| ID | Risk | Impact | Design mitigation (where) |
|---|---|---|---|
| **R-1** | Cross-tenant correctness — an Offer gid resolves the WRONG tenant's company_id -> PHI leak | **critical** | INVARIANT GFR-IDENTITY-1 (§0.1); parent-chain + gid-exact row (§5.3); SEAM1 Option E gid re-assertion (§10); tier-2 by-guid verify (§7); PT-05 live positive + dedup-loser NEGATIVE RED (§12); rite-disjoint critic |
| **R-1b** | Re-introduction of an office_phone identity join over time (drift) | critical | identity-purity guard + `GuardViolationError` + grep-zero PT-03 (§6.1, §12.3) |
| **R-2** | Cold-frame latency, AND the parent-chain entry-fetch cost (≤4 reads for offer) | medium | stale=resolved + serve-stale-if-any (§6.2); single accounted entry fetch (§4.1); identity-index future optimization (§5.4, §14) |
| **R-3** | `company_id` staleness — asana-cache drifts from data-service truth | high | tiered truth-source (§7); high-stakes forces tier-2 by-guid; provenance `source` tag makes drift visible |
| **R-4** | Accidental edit to a frozen range, hydration, or scar test | critical | NEW sibling layer (§2); consume `_traverse_upward_async`/`execute_rows`; PT-02 CI diff over frozen paths + hydration + 12 scar files |
| **R-5** | autom8y-core not co-located | low | SVR-confirmed PRESENT; `get_business_by_guid_async` at `data_service.py:434`; E is PROPOSE-only |
| **R-6** | appointments-minting site UNBUILT/external | high | §11.3; GFR's gid->guid half MUST be live; mint stubbed at known boundary only |
| **R-7** | Owner-ambiguity — a field on two schemas resolves to the wrong owner | medium | planner partitions by `SchemaRegistry` owning schema deterministically; qa-adversary seed (§9.4); `UnresolvedError(no-identity-path)` over a silent wrong-owner pick |
| **R-8** | Cardinality collapse — N rows silently flattened to scalar | high | row-set native by default; `scalar()` raises `AmbiguousCardinalityError` (§3.2) |
| **R-9** | Vector B (gid->project_gid) wrongly trusted for tenant identity | high | §11.5 — Vector B maps gid->TYPE not gid->tenant; certified separately; ride claims NO cross-tenant safety on it alone |
| **R-10** | Inbound DISPLAY-collision — `:141` phone-fallback shows the WRONG office_name for a colliding tenant | **low** (display, not routing/PHI) | §11.6 — routing is guid-exact (`:92`); positive test asserts on `ctx.chiropractor_guid`, NEVER on `office_name`/`office_phone`; OUT of GFR build scope (email-booking-intake owner) — recorded so the test asserts the right surface |
| **R-11** | Positive round-trip passes via injected `guid_phone_mapping` / `guid_overrides` instead of the clean by-guid path | medium | §12.1 step 4a/5 — assert clean `business is not None` HIT (`:111`), empty `guid_phone_mapping`, `G_correct` not an override key/value on BOTH override surfaces (`:46-50`, `:55/:72`) |
| **R-12** | Negative test passes VACUOUSLY (broken fixture has A as `keep='first'` winner) | critical | §12.2 step 4 — B positively constructed as the `keep='first'` survivor through `join.py:157`; QA build-pass INSPECTS the dedup ordering, not just the assertion text |

---

## 14. Frozen-Compliance & Open Risks

### Frozen-compliance summary

- **builds_on_top:** YES — `resolution/gfr/` is a NEW sibling package; the
  identity edge CONSUMES `hydration._traverse_upward_async` /
  `hydrate_from_gid_async`; field reads CONSUME `execute_rows` /
  `RowsRequest`/`JoinSpec`; tier-2 CONSUMES `get_business_by_guid_async`.
- **touches_frozen_ranges:** NO — `query/engine.py:139-178,181`,
  `query/compiler.py:53-63,192-241`, `query/join.py` (whole, including the
  `keep='first'` dedup at `:157`), and `hydration.py` are called, never edited.
  v2 routes AROUND the dedup via gid-exact reads rather than editing it.
- **touches_scar_tests:** NO — the 42 markers / 12 files are untouched.

### Open risks / carried flags

- **DRIFT-1** — scar cluster is 42 markers / **12** files at HEAD (frame said 11).
  `.know/design-constraints.md` refresh advised.
- **NOTE-3 corrected** — round-trip binds to INBOUND `resolve_office_stage`, NOT
  outbound `_resolve_office_phone:547` (§11.2). Telos YAML line-52 anchor
  superseded; recommend amendment at next `/frame`.
- **NOTE-4** — appointments-mint PRODUCER is UNBUILT; sprint-F stubs at the
  boundary, gid->guid half stays live (§11.3).
- **NOTE-5 (new, QA new_hole 1)** — the inbound `:141` phone-fallback enriches
  `office_name`/`office_phone` DISPLAY fields only; a phone collision there is a
  LOW-severity display mismatch, NOT a routing/PHI leak (§11.6, R-10). If the
  display mismatch is to be closed, that is an `email-booking-intake` change,
  flagged to that owner — OUT of GFR's build scope.
- **PT-05 UNATTESTED (residual_blocking #1)** — nothing is built at HEAD
  (`resolution/gfr/` and `tests/.../gfr/` empty, SVR-confirmed §0.2). `PROVEN` is
  a sprint-F build obligation discharged ONLY by the live positive + RED broken
  fixture + the rite-disjoint PT-05 critic. The release gate holds it.
- **Vector B (R-9)** — gid->project_gid->entity_type discriminator PINNED at
  `tier1.py:38/117`; maps gid->TYPE not gid->tenant; **certified separately**
  (`.ledge/reviews/gfr-vectorB-discriminator-cert.md`). Ride claims NO
  cross-tenant safety on Vector B alone.
- **Open question 1 (brief + §4.1, §5.4)** — persistent gid->{entity_type,
  business_gid} IDENTITY index vs on-demand parent-walk: deferred to sprint-A as
  `emergent` latitude. On-demand parent-walk is the v1 default (collision-free,
  lowest-risk); the index is reconsidered ONLY if the ≤4-read offer entry cost
  proves prohibitive — and an index must be populated/maintained by the SAME
  parent-walk to stay tenant-correct.

---

*Authored by the 10x-dev architect at sprint-0 (v2), f4f924d2. All substrate
anchors re-fired by direct inspection this pass (G-PROVE). v2 closes the v1
cross-tenant NO-GO by resolving identity on gid + parent-chain edges, never on an
office_phone value-join (INVARIANT GFR-IDENTITY-1). Self-grade **[STRUCTURAL |
MODERATE]** per `self-ref-evidence-grade-rule`; the SEAM1-ride and
tenant-correctness STRONG attestations belong to the rite-disjoint review critic
at PT-01 and PT-05, and the Vector-B discriminator to a separate certification.
Build ON TOP; cross a frozen surface ONLY by explicit ADR + rite-disjoint
corroboration.*
