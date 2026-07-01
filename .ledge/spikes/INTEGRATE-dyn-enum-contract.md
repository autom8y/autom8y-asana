---
type: spike
status: draft
slug: dyn-enum-contract
wave: 2 (integration-researcher)
upstream: .ledge/spikes/SCOUT-dyn-enum-contract.md (verdict TRIAL)
downstream: prototype-engineer (Wave 3)
evidence_grade: "[STRUCTURAL | MODERATE]"
---

# INTEGRATE-dyn-enum-contract

> rnd /spike — Wave 2 (integration-researcher). No production code. Integration analysis only.
> Maps the dependency edges, hidden couplings, compatibility/breaking-change surface, and POC
> scope for a **dynamic enum-option-set sync contract** (Asana enum `enum_options` → `autom8y-data`).
> Builds on **SCOUT-dyn-enum-contract.md** (Wave 1, TRIAL). Every platform-behavior claim about a
> named primitive carries a `{path}:{line}` receipt (SVR discipline) or a `[UV-P]` deferred tag.
> Evidence ceiling **MODERATE** — self-referential (assessing the fleet's own seams from inside)
> per `self-ref-evidence-grade-rule`; rnd-dk literature caps at MODERATE.

---

## Overview

**What we are integrating** (carried verbatim from the scout's framing, A.1): not the field-name
vocabulary (that is gfr-dynvocab, MERGED `e49c30d7`) and not the *selected* enum value, but the
enum **OPTION-SET** — the universe of valid option values for an Asana `enum`/`multi_enum` custom
field (canonical example: the `Vertical` option-set) — contractualized as a dynamic relationship
that **"syncs in"** from `autom8y-asana` to the sibling `autom8y-data` service.

**Why** (scout A.5): the option-set vocabulary **already leaks across the asana→data seam untyped**
today (`AccountStatusEntry.vertical: str`, `_account_status_sync.py:44`), pushed by the cache
warmer producer (`gid_push.py:458` emits `"vertical": str(vertical)`). The substrate sync-contract
pattern is in production at N≥2 (account-status + gid-mappings). The contract makes the existing
leak typed, named, and governed.

**The decisive Wave-2 correction to the scout's verdict** (developed in §3 + §Hidden Deps): the
scout proposed an "autom8y-data **snapshot-replace** round-trip." Direct inspection of the data-side
schema shows the sync TARGET — the `verticals` table — is an **FK-parent dimension** referenced by
`campaigns`, `asset_verticals` (43,057 rows), and `offers`. The two existing snapshot-replace
instances both target **leaf stores** (account_status = MySQL leaf, no FK children; gid-mappings =
Redis). **Snapshot-replace (DELETE+INSERT) is structurally unsafe on `verticals`.** The contract
must be **upsert-keyed-on `vertical_key`, additive-only, DELETE-forbidden.** This flips the core POC
assumption and is the highest-value finding of this wave. The TRIAL verdict still holds; the
*mechanism* changes from snapshot-replace to additive-upsert.

---

## Current State

### Architecture (the three-repo seam)

```
  ┌─────────────────────────── autom8y-asana (PRODUCER) ───────────────────────────┐
  │  Asana live enum_options  ──(UN-WIRED to resolution/sync — the gap)──►  ?       │
  │    CustomFieldsClient.get / create_enum_option / update_enum_option             │
  │    CustomField.enum_options: list[CustomFieldEnumOption]   (extra="ignore")     │
  │                                                                                  │
  │  resolution reads only the SELECTED value (enum_value.name), never enum_options  │
  │    _extract_raw_value default.py:257-263                                          │
  │                                                                                  │
  │  schema-discovery route ANTICIPATES values_source:'asana_configured' but wires   │
  │    only the hardcoded SEMANTIC_ANNOTATIONS copy   resolver_schema.py:473         │
  │                                                                                  │
  │  cache-warmer producer  gid_push.py  ──POST /sync (S2S JWT, snapshot,            │
  │    entry_count integrity, every 4h)──────────────────────────┐                  │
  └──────────────────────────────────────────────────────────────┼──────────────────┘
                                                                  │  extra="forbid"
                                                                  ▼
  ┌─────────────────────────── autom8y-data (CONSUMER) ───────────────────────────┐
  │  POST /api/v1/account-status/sync  → snapshot_replace (DELETE WHERE source +    │
  │    INSERT) on account_status  [LEAF table; vertical is a free str, NO FK]       │
  │  POST /api/v1/gid-mappings/sync    → GidMappingStore (Redis) [LEAF]             │
  │                                                                                  │
  │  verticals table  [FK-PARENT DIMENSION — the would-be option-set target]        │
  │    ◄── campaigns.vertical_id      (FK verticals.id; "PRIMARY source for leads")  │
  │    ◄── asset_verticals.vertical_id (FK verticals.id; composite PK; 43,057 rows)  │
  │    ◄── offers.category            (FK verticals.key)                             │
  │    VerticalService: read-heavy, admin-only create, NO update, NO delete         │
  └──────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────── autom8 monorepo (LEGACY — NON-CANONICAL) ──────────────┐
  │  Vertical(Enum)  + _missing_() cascade  [Slack alert + DB lookup + phantom-     │
  │    campaign auto-mint]                          QUARANTINED (no import edge      │
  │  Vertical(EnumField) cf-adapter → VerticalModel.get_vertical → _missing_         │
  │  satellite getdf_signals.py  _CONTRACT_COLUMNS=(office_phone,vertical,gid)       │
  │    structural false-green :282 ; paid_content asset_id KeyError→ColumnContractError│
  └──────────────────────────────────────────────────────────────────────────────┘
```

### Integration Points (verified at source)

| # | System | Interface | Data that flows | Frequency | Anchor |
|---|--------|-----------|-----------------|-----------|--------|
| P1 | autom8y-asana CustomFieldsClient → Asana API | REST GET `/custom_fields/{gid}` / `/enum_options` | live `enum_options` option-set (read); `create/update_enum_option` (mutate) | on-demand / warm cycle | `clients/custom_fields.py:442` (create), `:529` (update) |
| P2 | autom8y-asana resolution layer | in-process | reads SELECTED `enum_value.name` only — NOT the option-set | per resolve | `dataframes/resolver/default.py:257-263` (enum), `:264-271` (multi_enum) |
| P3 | autom8y-asana schema-discovery route | REST GET `/{entity}/schema/enums/{field}` | `EnumDetailResponse.values_source ∈ {hardcoded, asana_configured}` — only `hardcoded` wired | on-demand | `api/routes/resolver_schema.py:366-369` (contract), `:473` (wires `annotation.get("values_source")`) |
| P4 | autom8y-asana cache-warmer producer → autom8y-data | REST POST `/api/v1/{x}/sync` (S2S JWT) | typed snapshot `{source, entries[], source_timestamp, entry_count}` | every 4h | `services/gid_push.py:529` (account-status), `:307` (gid-mappings) |
| C1 | autom8y-data account-status ingest | REST POST `/api/v1/account-status/sync` | `AccountStatusSyncRequest` (extra="forbid"); snapshot-replace | every 4h | `api/routes/account_status.py:50`, `:108` (integrity), `:133` (snapshot_replace) |
| C2 | autom8y-data snapshot store | in-process / MySQL txn | DELETE WHERE source + INSERT (transactional) | per sync | `api/services/account_status_store.py:82-143` (BEGIN/DELETE/INSERT) |
| C3 | autom8y-data VerticalService → MySQL `verticals` | gRPC + SQL | read-heavy; admin-only `create`; **no update, no delete** | runtime (Stripe SDK) | `services/vertical.py:7-10` (design principles), `:149` (create), `:120-147` (get_by_key) |

### Dependencies

- **S2S JWT auth**: every `/sync` endpoint is `Depends(verify_jwt)` — `account_status.py:41`, `gid_mappings.py:38`. A new endpoint inherits this as-is.
- **Rate limiter**: `@limiter.limit("10/minute")` — `account_status.py:85`. Reusable.
- **Fleet OpenAPI envelopes**: `x-fleet-idempotency`, `x-fleet-cross-service-refs` — `account_status.py:66-70`. Convention the new endpoint must carry.
- **Producer feature flag** (HIDDEN — see Hidden Deps HD-4): `_is_status_push_enabled()` gates the push — `gid_push.py:491`.
- **Shared push helper**: `_push_to_data_service(endpoint_path, payload, response_model, …)` — `gid_push.py:528`. A 3rd push function reuses this verbatim.

---

## Target State

### New Integration Points

| System | Interface | Data | Changes from current |
|--------|-----------|------|----------------------|
| autom8y-asana producer | new fn `push_vocab_to_data_service()` in `gid_push.py` | typed option-set snapshot keyed on **normalized option name** | NEW push fn alongside the existing two; reuses `_push_to_data_service` |
| autom8y-asana source-read | `CustomFieldsClient.get(custom_field_gid)` → `.enum_options` | live Asana option-set (NOT the hardcoded `valid_values`) | wires the `'asana_configured'` door the route already left open (`resolver_schema.py:366`) |
| autom8y-data consumer | NEW `POST /api/v1/vocabularies/sync` (or `/enum-options/sync`) | `VocabSyncRequest{ field_key, options[], source_timestamp, entry_count }`, `extra="forbid"` | NEW endpoint — **NOT** an extension of `/account-status/sync` (see Breaking Change BC-1) |
| autom8y-data store | NEW `vocab_upsert()` on `VerticalService` (or sibling) | **UPSERT on `vertical_key`** (insert new keys, update name/enabled), **DELETE forbidden** | **NOT** `snapshot_replace` — `verticals` is FK-parent (see BC-2) |
| drift observer | in-process WARN log + metric | asana-live vs data-side divergence | warn-first, **never codegen** (honors ADR-S4-001) |

**Identity contract (resolves scout R2):** key on the **normalized option name → `vertical_key`**.
- Asana side: `enum_option.gid` is per-workspace, opaque, non-portable — runtime handle only (`custom_field.py:19` `CustomFieldEnumOption(AsanaResource)`; gid via base).
- Data side: `vertical_id` (`_platform.py:145`, DB col `id`) is an **auto-increment local PK that is itself FK-referenced** — also non-portable AND must never be reassigned.
- Portable key: `vertical_key` (`_platform.py:146`, unique, DB col `key`) — already the cross-service business key on both the legacy SQL table and `autom8y-data`. Each service maps the portable name to its own handle (asana → `enum_option.gid` for mutations; data → existing `vertical_id`).

---

## Integration Touchpoint Map (the six sources of truth + the edges)

The scout enumerated six materializations of the `vertical` option-set. Mapped here as data-flow
edges, with the contract's authoritative/derived designation:

| # | Source materialization | Anchor | Under the contract |
|---|------------------------|--------|--------------------|
| 1 | legacy `Vertical(Enum)` (~55 members) | `contente_api/models/vertical/main.py:19` | **NON-CANONICAL** — quarantined; neither synced service imports it (HD-1) |
| 2 | `VERTICAL_NAMES` display map | `contente_api/models/vertical/main.py:261` (scout) | derived/legacy — out of scope |
| 3 | SQL `verticals` (contente) via `db_verticals()` | `contente_api/models/vertical/main.py:12-16` | legacy mirror — out of scope |
| 4 | **Asana live `enum_options`** | `models/custom_field.py:113`; client `:442/:529` | **AUTHORITATIVE source-of-record** (declared; resolves R1) |
| 5 | asana hardcoded `SEMANTIC_ANNOTATIONS.valid_values` | `resolver_schema.py:449,473` | **DERIVED** — the route's `'asana_configured'` path supersedes the hardcoded copy |
| 6 | **`autom8y-data` `verticals` table** | `_platform.py:131-147`; `services/vertical.py` | **DERIVED replica** — ingests #4 via the new contract; upsert-only |

**Edge direction under the contract:** `#4 Asana live enum_options` → (producer projects name-keyed
snapshot) → `#6 autom8y-data verticals` (upsert on vertical_key). `#5` is re-pointed to read `#4`
(closing the `resolver_schema.py:366` door). `#1/#2/#3` stay legacy/quarantined. **One authoritative
source (#4), one governed derived replica (#6), one re-pointed view (#5); three legacy copies frozen.**

---

## Hidden Dependencies

> The couplings NOT in any doc. Discovery method stated per the anti-pattern register
> ("Surface-Only API Analysis" correction).

| ID | Hidden dependency | What breaks | Coupling strength | Discovery method |
|----|-------------------|-------------|-------------------|------------------|
| **HD-1** | Legacy `_missing_()` side-effect cascade | Slack-alert to admin-ops + DB lookup + **phantom-campaign auto-mint** on any unknown value coerced through `Vertical(value)` | **QUARANTINED** (negligible if producer stays in autom8y-asana) | Read `vertical/main.py:82-158`; grep proved **0** `contente_api`/`apis.*` imports in either synced service |
| **HD-2** | `verticals` is an **FK-parent** (not a leaf) | snapshot-replace DELETE orphans 43,057 `asset_verticals` rows + all `campaigns.vertical_id` refs + `offers.category` refs; or FK-blocks the DELETE | **STRONG / load-bearing** | Read `_advertising.py:80,326` + `_platform.py:162` (3 distinct FK edges) |
| **HD-3** | Satellite **structural false-green** | a contract that passes `entry_count` integrity while semantically truncated → downstream `KeyError`→`ColumnContractError` (the asset_id fossil class) | **MODERATE (same family, distinct surface)** | Read `getdf_signals.py:282` (3-col AND), `paid_content/main.py:78-89` |
| **HD-4** | Producer **feature flag** gates the push | `_is_status_push_enabled()` false → push silently no-ops; a new vocab push inherits/needs its own flag, easy to ship dark and never fire | **MODERATE** | Read `gid_push.py:491` |
| **HD-5** | Producer **empty-publish guard is leaf-calibrated** | `if not entries: return True # nothing to push is not a failure` is SAFE for leaf account_status but **wrong** for FK-parent verticals (an empty Asana read must HARD-REFUSE, never reach an upsert/delete) | **STRONG** | Read `gid_push.py:514-519` |
| **HD-6** | No `source` column on `verticals` | the account-status snapshot-replace scopes its DELETE by `source` (`account_status_store.py:89`); `verticals` has only `{id,key,name}` — a snapshot DELETE cannot be source-scoped, it would hit ALL rows | **STRONG** | Read `_platform.py:145-147` vs `account_status_store.py:89` |
| **HD-7** | Producer/consumer `extra=` asymmetry | asana `CustomField` is `extra="ignore"` (forward-compat); data sync models are `extra="forbid"` — adding a field to the *existing* account-status payload is silently accepted producer-side but **rejected** consumer-side | **MODERATE** | Read `custom_field.py:3` (ADR-0005 ignore) vs `_account_status_sync.py:67,102` (forbid) |

### HD-2 structural-verification receipt (the load-bearing claim)

```yaml
structural_verification_receipt:
  claim: "the autom8y-data verticals table is an FK-parent referenced by three distinct tables, so a DELETE+INSERT snapshot-replace would reassign the auto-increment id and orphan the referencing rows"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/repos/autom8y-data/src/autom8_data/core/models/_advertising.py"
    line_range: "L80, L326"
    marker_token: "vertical_id: int = Field(foreign_key=\"verticals.id\")"
    claim: "campaigns.vertical_id and asset_verticals.vertical_id both declare FK to verticals.id; combined with offers.category FK to verticals.key (_platform.py:162), the verticals dimension has three inbound FK edges and cannot be DELETE+INSERT replaced without breaking referential integrity"
```

### HD-1 quarantine receipt (downgrades scout R3)

```yaml
structural_verification_receipt:
  claim: "neither autom8y-asana nor autom8y-data imports the legacy contente_api Vertical enum, so the _missing_ phantom-campaign cascade is unreachable from the sync seam"
  verification_method: bash-probe
  verification_anchor:
    source: "rg -c 'contente_api|from apis\\.|import apis' src  (run in each repo root)"
    command_output_verbatim: "No matches found"
    exit_code: 1
    claim: "zero import edges from either synced service into the autom8 monorepo apis namespace; the _missing_ cascade (vertical/main.py:82-158) is reachable ONLY via the monorepo cf-adapter Vertical(EnumField).get/set -> VerticalModel.get_vertical, which the asana-reads-its-own-enum_options design does not traverse"
```

---

## Gap Analysis

### API Compatibility

| Feature | Current | New | Compatibility | Notes |
|---------|---------|-----|---------------|-------|
| Option-set read | hardcoded `SEMANTIC_ANNOTATIONS.valid_values` | live Asana `enum_options` via `CustomFieldsClient` | **Partial** | model + client already exist (`custom_field.py:113`, `custom_fields.py:442`); only the wire is missing |
| `values_source` field | contract present, only `'hardcoded'` wired | `'asana_configured'` path | **Full (additive)** | route response already declares the enum value (`resolver_schema.py:366-369`); no schema change needed |
| Sync transport | `_push_to_data_service` (account-status, gid-mappings) | same helper, new `endpoint_path` | **Full** | `gid_push.py:528` is endpoint-parameterized |
| Consumer write semantics | `snapshot_replace` (DELETE+INSERT) | **upsert-on-key (additive)** | **None (incompatible)** | the existing store is the wrong mechanism for an FK-parent (HD-2/HD-6) — a new store method is required |
| Identity key | account_status uses free `vertical: str` | `vertical_key` (portable) | **Full** | `vertical_key` already unique on the target (`_platform.py:146`) |
| Pydantic strictness | `extra="forbid"` (data sync models) | `extra="forbid"` (new endpoint) | **Full** | preserve forbid on the new contract; do NOT extend the existing forbid'd contract (BC-1) |

### Breaking Changes

1. **BC-1 — Adding an option-set field to the EXISTING `/account-status/sync` payload is BREAKING.**
   The consumer contract is `model_config = {"extra": "forbid"}` (`_account_status_sync.py:67,102`). A
   new top-level field would be rejected with 422 by the *current* consumer until both sides deploy.
   *Mitigation*: ship a **NEW endpoint** (`/vocabularies/sync`), never extend account-status. Additive
   on the fleet; zero blast radius on the in-flight account-status contract. The producer-side asana
   model is `extra="ignore"` (`custom_field.py:3`) so the asymmetry (HD-7) hides this from producer
   tests — the break only surfaces against the live consumer. Order: deploy consumer endpoint first,
   then enable the producer push behind HD-4's flag.

2. **BC-2 — `snapshot_replace` on `verticals` is BREAKING (referential integrity).**
   `account_status_store.snapshot_replace` does `DELETE … WHERE source = :source` then re-INSERT
   (`account_status_store.py:88-90,130-142`). On `verticals`: (a) there is no `source` column (HD-6,
   `_platform.py:145-147`) so the DELETE is unscopable; (b) even a keyed DELETE+INSERT reassigns the
   auto-increment `id` (`_platform.py:145`), orphaning `campaigns.vertical_id`, the 43,057-row
   `asset_verticals`, and `offers.category` (HD-2). *Mitigation*: **upsert-keyed-on-`vertical_key`**,
   additive-only: INSERT genuinely-new keys, UPDATE name/enabled on existing keys, **never DELETE**.
   This matches the data-side's own stated invariant — "No Delete operation (verticals are
   permanent)" (`services/vertical.py:9`).

3. **BC-3 — Removing/disabling an Asana option must NOT propagate as a DELETE.**
   Operators disable enum options in the Asana UI. Under additive-upsert, a disappeared option is a
   **drift WARN signal**, not a data-side delete (would orphan FK rows). *Mitigation*: carry an
   `enabled` flag (the model already has `CustomFieldEnumOption.enabled`, `custom_field.py:35`);
   soft-disable at most; escalate true removals to the human runbook, never auto-mutate. This is the
   drift-gate-not-codegen discipline (ADR-S4-001 one-way door) applied to the delete direction.

### Data Migration (the transformation pipeline — anti "Data Migration Blindness")

- **Schema compatibility**: Asana `CustomFieldEnumOption{gid,name,enabled,color}` → `verticals{id,key,name}`. Transform: `name` → `normalize(name)` → `vertical_key`; display `name` → `vertical_name`. `gid`/`color`/`enabled` have no column home → carried only in the contract envelope for drift, not persisted (or a soft `enabled` shadow if added — out of POC scope).
- **First-publish reconciliation**: the data-side `verticals` table is already populated (FK-referenced by 43K asset_verticals + campaigns). First sync must **match existing keys, not re-key**. Any Asana option whose `normalize(name)` does not match an existing `vertical_key` is an **INSERT candidate** flagged for review (mirrors the legacy `_missing_` registration intent — but WARN-only, never auto-mint a campaign).
- **Validation criteria**: post-upsert, every pre-existing `vertical_key` referenced by `campaigns`/`asset_verticals`/`offers` MUST still resolve (referential-coverage invariant). A publish that would strand a referenced key is REFUSED at the producer (HD-5 hardened) before transport.
- **Rollback data strategy**: because the contract is additive-upsert (never delete), rollback = stop pushing + revert the producer flag (HD-4). No data reversion needed for inserts/updates of an idempotent name-keyed upsert; the worst case is a stale `enabled`/`name`, self-healed on the next good publish.

---

## Effort Estimate

| Component | Effort | Confidence | Key assumptions ("if wrong" multiplier) |
|-----------|--------|------------|------------------------------------------|
| Wire `CustomFieldsClient.get → enum_options` read for the Vertical cf | 0.5 day | **High** | model+client exist (`custom_field.py:113`, `custom_fields.py:442`). If the cf gid for `Vertical` is not statically known and needs discovery → 1.5x |
| Re-point schema-discovery `values_source:'asana_configured'` | 0.5 day | **High** | route already declares the enum value (`resolver_schema.py:366`). If `SEMANTIC_ANNOTATIONS` consumers depend on the hardcoded shape → 2x |
| New producer `push_vocab_to_data_service()` (reuse `_push_to_data_service`) | 0.5 day | **High** | helper is endpoint-parameterized (`gid_push.py:528`). Low risk. |
| New consumer `POST /vocabularies/sync` endpoint + `extra="forbid"` model | 1 day | **High** | clone account_status route shape. If S2S claims need a new scope → 1.5x |
| **New `vocab_upsert()` store (additive, NOT snapshot_replace)** | 1.5 days | **Medium** | upsert-on-key + referential-coverage guard is NEW code, not a clone. **If MySQL upsert semantics + FK-coverage check are subtler than expected → 2x.** Flagged for prototype validation. |
| Empty/truncated-publish hard-refuse guard (HD-5 hardened, R4) | 1 day | **Medium** | non-empty floor + referenced-key coverage. **If "referenced keys" requires a cross-table query at publish time → 1.5x.** |
| Drift observer (WARN-only, never codegen) | 0.5 day | **High** | log+metric; no mutation. Low risk. |
| Identity round-trip test harness (R2) | 0.5 day | **Medium** | name→key normalization parity across asana/data. If `NameNormalizer` is not importable cross-service → reimplement, 1.5x |

**Total Estimated Effort**: ~6.5 person-days (production-grade). **POC subset (Wave 3): 1–2 days**
(see POC Scope) — proving the upsert-vs-snapshot decision + the two highest-risk guards, not the
full production wiring.

> Confidence note per anti-pattern "Integration Effort Optimism": the two **Medium**-confidence
> components (`vocab_upsert` store, empty-publish guard) are the ones whose "if wrong" multipliers
> double the estimate. Both are routed to prototype-engineer for hands-on validation **before** any
> production commitment.

---

## Risks

> Carried + re-graded from the scout (SCOUT §Risk Analysis). HD-2 forces an up-grade of R4.

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **R1 — Truth-ownership ambiguity** | M | H | Declare Asana live `enum_options` = single upstream source-of-record; data ingests one-way; data-side `create` becomes a drift *signal*, not back-sync. (scout R1, unchanged) |
| **R2 — Identity keyed on gid** | M | H | Key on normalized option name → `vertical_key`; gid is a runtime handle per side. `vertical_id` ALSO non-portable AND FK-referenced → never reassign. (scout R2 + the FK refinement) |
| **R3 — `_missing_` auto-mint contamination** | **L → negligible** | H | **Down-graded**: HD-1 proves 0 import edges; reachable only via the monorepo cf-adapter the design avoids. Quarantine holds as long as the producer reads via `CustomFieldsClient`, never `VerticalModel`. |
| **R4 — Empty/truncated publish blast radius** | **M → H-likelihood** | **H** | **Up-graded** by HD-2/HD-5/HD-6: on an FK-parent, a bad publish is catastrophic, not merely lossy. Hard-refuse empty/truncated at producer (referential-coverage + non-empty floor); additive-upsert means even a *partial* publish cannot delete. The DELETE direction is structurally removed. |
| **R5 — FROZEN cf-type-set pressure** | M | M | Option-set rides as a sidecar to `enum`/`multi_enum` (the route already attaches `valid_values` only to those two — `resolver_schema.py:275`). Set stays FROZEN. (scout R5) |
| **R6 — Scope creep into DEFER-1 registry** | M | M | Scope to the single drift class (enum-option vocab, asana↔data). Registry stays DEFER (moonshot Wave 4's question, not this build). (scout R6) |
| **R7 — Ship-dark via feature flag** (NEW) | M | M | HD-4: a vocab push behind a flag that never flips is silent non-function. Add a canary signal (publish-count metric) + a deploy-gate assertion that the first real publish lands; do not declare done on flag-present alone. |

---

## Integration Approach

### Option A — New additive-upsert vocab contract (RECOMMENDED)

New `POST /api/v1/vocabularies/sync` endpoint; producer reads live Asana `enum_options`; consumer
**upserts on `vertical_key`** (insert new, update name/enabled, never delete); drift observer WARNs.

- **Pros**: honors HD-2 (no FK break); zero blast radius on the in-flight account-status contract
  (BC-1 avoided); reuses S2S/rate-limit/envelope/push-helper as-is; matches the data-side "verticals
  permanent" invariant (`services/vertical.py:9`); strictly-additive to gfr-dynvocab's certified spine.
- **Cons**: the `vocab_upsert` store is new code (not a clone) — the one Medium-confidence component;
  no automatic reconciliation of options *removed* in Asana (handled as WARN, by design).
- **Effort**: ~6.5 person-days production; 1–2 day POC.

### Option B — Extend the existing account-status snapshot-replace

Add `enum_options` to the account-status payload / reuse `snapshot_replace`.

- **Pros**: fewer new surfaces; one endpoint.
- **Cons**: **BC-1 breaking** (extra="forbid" rejects the new field until both deploy); **BC-2
  catastrophic** (snapshot-replace on FK-parent verticals); HD-6 (no source column to scope the
  DELETE). Conflates a leaf-table idiom with an FK-parent dimension. **Rejected.**
- **Effort**: deceptively low up front, unbounded downside.

### Option C — gRPC write path via VerticalService.create

Have the producer call the data-side gRPC `create` per option.

- **Pros**: reuses existing service; per-key validation.
- **Cons**: `create` is admin-only, no update, raises `AlreadyExistsError` on existing keys
  (`services/vertical.py:149,193`) → N round-trips + error-handling for the common (already-exists)
  case; no snapshot/integrity envelope; chattier and harder to make idempotent than one upsert push.
  **Rejected** for the bulk option-set; viable only as the single-key WARN-escalation path.
- **Effort**: comparable, worse ergonomics.

### Recommendation

**Option A.** It is the only approach that respects the FK-parent reality (HD-2), avoids the
breaking extension (BC-1), and keeps the drift-gate-not-codegen discipline (BC-3). It composes the
proven sync-contract substrate (N≥2) while correcting the mechanism from snapshot-replace to
additive-upsert.

---

## Migration Plan (phased, with rollback points)

1. **Phase 0 — Consumer endpoint dark (reversible).** Ship `POST /vocabularies/sync` + `vocab_upsert`
   store on autom8y-data, no producer calling it. **Rollback**: remove route (no data touched).
   *Reversibility: full (one-way risk: none).*
2. **Phase 1 — Producer read-only projection (reversible).** Wire `CustomFieldsClient → enum_options`
   read + name-key projection in autom8y-asana; log the snapshot, do NOT push (flag off, HD-4).
   **Rollback**: flag stays off / revert read. *Reversibility: full.*
3. **Phase 2 — Enable push behind flag, shadow validate (reversible).** Flip HD-4 flag; consumer
   upserts; assert referential-coverage invariant holds post-upsert (no stranded referenced key).
   **Rollback point**: flip flag off; additive-upsert means no data to revert. *Reversibility: full —
   this is the last fully-reversible gate.*
4. **Phase 3 — Re-point schema-discovery `values_source:'asana_configured'` + drift observer ON.**
   Consumers of the discovery route now see live option-sets. **Rollback**: re-point to hardcoded
   annotation. *Reversibility: full (config flip).*
5. **Phase 4 (DEFERRED — Wave 4 question, NOT this build).** Generalize to a fleet cf-contract
   registry. **One-way-door watch**: do not enter without the DEFER-1 N≥3 trigger. Escalate to
   leadership/moonshot-architect.

**Every phase 0–3 has a full rollback (flag or config flip); no one-way door is crossed in this
build.** The only one-way door (codegen-from-model / auto-mint) is the thing being escaped, never
entered (BC-3, HD-1).

---

## POC Scope Definition (for Wave 3 — prototype-engineer)

**The minimal seam to prove** (corrected from the scout's snapshot-replace round-trip):

> asana reads its OWN live `enum_options` (Vertical cf via `CustomFieldsClient`) → projects a typed
> snapshot keyed on **normalized option name** → stub autom8y-data ingest **UPSERTS on `vertical_key`
> (additive: insert-new / update-name-enabled / NEVER delete)** → a drift observation **WARNS (never
> codegens)** when asana-live diverges → with an explicit **empty/truncated-publish hard-refuse** at
> the producer before transport.

**TIME-BOX: 1–2 days.** Throwaway code; deliberate shortcuts allowed (hardcode the Vertical cf gid;
stub the data-side store in-memory or against a scratch table; skip auth). The POC exists to
de-risk, not to ship.

### The ≥2 highest-risk areas the prototype MUST de-risk

1. **RISK AREA 1 — FK-parent write semantics (HD-2 / BC-2 / R4).** Prove, against a scratch
   `verticals`-shaped table *with* FK children, that: (a) DELETE+INSERT snapshot-replace breaks
   referential integrity (the RED — show the orphan/FK-violation), and (b) upsert-on-`vertical_key`
   preserves existing `id`s and all FK references (the GREEN). This is the discriminating canary: the
   broken input (snapshot-replace) is correctly rejected/breaks; the real input (additive-upsert)
   passes. *Success criterion*: existing `asset_verticals`/`campaigns` references still resolve after
   an upsert that adds a new key and updates an existing one.

2. **RISK AREA 2 — Empty/truncated-publish guard (HD-5 / R4).** Prove the producer **refuses** a
   publish whose option-set is empty or fails the referential-coverage check (every currently-FK-
   referenced `vertical_key` present), and that the leaf-calibrated `if not entries: return True`
   short-circuit (`gid_push.py:514-519`) is replaced by a HARD-REFUSE for the FK-parent target.
   *Success criterion*: an empty Asana read produces a refusal + alert, NOT a no-op and NOT a delete.

3. **RISK AREA 3 (if time permits) — Identity round-trip (R2).** asana option `name` → `normalize` →
   `vertical_key` → data lookup → back, with NO `enum_option.gid` leaking into the persisted key.
   *Success criterion*: a name with whitespace/case variance round-trips to the same `vertical_key`
   on both sides.

### POC Success Criteria

- [ ] Snapshot-replace shown UNSAFE on the FK-parent fixture (RED); additive-upsert shown SAFE (GREEN).
- [ ] Empty/truncated publish HARD-REFUSED at producer (not no-op, not delete).
- [ ] Round-trip on `vertical_key` with no gid leakage (R2).
- [ ] Drift divergence emits WARN only — zero auto-mutation (no codegen, no phantom-mint) — BC-3/HD-1.
- [ ] Decision enabled: upsert-on-key vs snapshot-replace settled with evidence for the production build.

---

## Handoff Criteria (→ prototype-engineer)

- [x] Current architecture documented with integration points identified (Touchpoint Map; P1–P4, C1–C3).
- [x] Hidden dependencies surfaced beyond documented APIs (HD-1…HD-7; ≥ the `_missing_` cascade + satellite false-green required by the brief, plus the FK-parent / empty-guard / extra-asymmetry discoveries).
- [x] Effort estimated with confidence levels + key assumptions + "if wrong" multipliers; Medium-confidence items flagged for prototype validation.
- [x] ≥2 integration approaches compared with tradeoffs (A recommended; B/C rejected with concrete disqualifiers).
- [x] Migration phases defined with rollback points (Phase 0–3 fully reversible; one-way door identified and NOT entered).
- [x] Compatibility & breaking-change matrix complete (BC-1/BC-2/BC-3 + data-migration section).
- [x] POC scope + TIME-BOX (1–2 days) + ≥2 highest-risk areas defined and ready to prototype.

## Escalation Note

No escalation triggers fired: the build is <2 weeks of refactoring (~6.5 person-days), depends on no
external team (both repos are in-fleet), and crosses no one-way door (Phases 0–3 reversible). The
DEFER-1 fleet-registry generalization (Phase 4) is the one item carrying business-judgment / one-way
risk — correctly routed to **moonshot-architect (Wave 4)**, not decided here.

---

## Evidence Grade

`[STRUCTURAL | MODERATE]` — ceiling, not floor. Self-referential (mapping the fleet's own seams from
inside) caps at MODERATE per `self-ref-evidence-grade-rule`; rnd-dk literature caps at MODERATE.
Every platform-behavior claim about a named primitive carries a `{path}:{line}` receipt verified by
direct inspection at authoring time (SVR discipline); the two formal SVR tuples (HD-2 FK-parent,
HD-1 quarantine) anchor the two load-bearing structural claims. The realization predicate — that
additive-upsert actually preserves FK integrity in anger — belongs to the Wave-3 prototype + a
rite-disjoint attester, not to this integration pass. No `[UV-P]` tags remain open: all cited
primitives were inspected at source across the three repos.

## Source Anchors (platform-internal, `{path}:{line}` — verified this wave)

**autom8y-asana (producer / cwd):**
- `src/autom8_asana/models/custom_field.py:3` — `extra="ignore"` (ADR-0005, forward-compat) — HD-7
- `src/autom8_asana/models/custom_field.py:19-42,113,117-124` — `CustomFieldEnumOption{gid,name,enabled,color}`, `enum_options`, selected `enum_value`/`multi_enum_values`
- `src/autom8_asana/clients/custom_fields.py:442,529` — `create_enum_option` / `update_enum_option`
- `src/autom8_asana/dataframes/resolver/default.py:257-263,264-271` — enum/multi_enum read the SELECTED value, never the option-set
- `src/autom8_asana/api/routes/resolver_schema.py:275,366-369,449,473` — `'asana_configured'` declared, `values_source`/`valid_values` wired to the hardcoded annotation only
- `src/autom8_asana/services/gid_push.py:307,458,491,514-519,528-529` — producer: gid+account-status pushes, `vertical:str` leak, feature flag (HD-4), leaf-calibrated empty guard (HD-5), shared push helper

**autom8y-data (consumer / sync target):**
- `src/autom8_data/api/routes/account_status.py:41,50,85,108,133` — S2S JWT, `/sync`, rate-limit, integrity check, snapshot_replace call
- `src/autom8_data/api/services/account_status_store.py:82-90,130-143` — DELETE WHERE source + INSERT (the leaf-table snapshot-replace; source-scoped — HD-6)
- `src/autom8_data/api/data_service_models/_account_status_sync.py:44,67,102` — `vertical:str` untyped leak; `extra="forbid"` (BC-1/HD-7)
- `src/autom8_data/api/routes/gid_mappings.py:38,61` — second sync instance (N≥2), S2S, `/sync`
- `src/autom8_data/core/models/_platform.py:131-147,162` — `Vertical{id,key,name}` (no source col); `offers.category` FK→`verticals.key` (HD-2/HD-6)
- `src/autom8_data/core/models/_advertising.py:80,326` — `campaigns.vertical_id` + `asset_verticals.vertical_id` (43,057 rows) FK→`verticals.id` (HD-2)
- `src/autom8_data/services/vertical.py:7-10,48,149,193` — read-heavy, IMMUTABLE `vertical_id`, no delete/update, admin-only create, `AlreadyExistsError` (Option C disqualifier)

**autom8 monorepo (legacy NON-CANONICAL — lessons only):**
- `apis/contente_api/models/vertical/main.py:12-16,19,82-158,261` — `db_verticals`, `Vertical(Enum)`, `_missing_` cascade (Slack `:126` + DB lookup `:102` + phantom-campaign auto-mint `:138-149`)
- `apis/asana_api/objects/custom_field/models/enum/vertical.py:5,19-54` — `Vertical(EnumField)` cf-adapter; imports `VerticalModel`; `get/set` route through `VerticalModel.get_vertical` (the only `_missing_` reach — HD-1)
- `apis/asana_api/satellite/getdf_signals.py:77,282` — `_CONTRACT_COLUMNS=(office_phone,vertical,gid)`; structural false-green (3-col AND; asset_id observed-but-non-failing) — HD-3
- `apis/asana_api/objects/project/models/paid_content/main.py:78-89` — `assert_column_contract(required=("asset_id",), check_all_null=False)`; absence-only, never refuse already-populated (the inverted discipline R4 borrows)
</content>
</invoke>
