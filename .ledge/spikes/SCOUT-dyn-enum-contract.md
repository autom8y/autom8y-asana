---
type: spike
status: draft
---

# SCOUT-dyn-enum-contract

> rnd /spike — Wave 1 (technology-scout). No production code. Assessment prose only.
> Slug: **dyn-enum-contract**. Downstream: integration-researcher → prototype-engineer → moonshot-architect → tech-transfer.
> Evidence grade ceiling: **MODERATE** (self-referential — assessing our own fleet's patterns from inside per `self-ref-evidence-grade-rule`; rnd-dk literature also caps at MODERATE).

---

## Executive Summary

The question: is it feasible to **contractualize a DYNAMIC relationship to Asana custom-field enum-OPTION-SETS** in `autom8y-asana` such that the enum-option vocabulary can **"sync in" cross-service to `../autom8y-data`**?

**Verdict: TRIAL.** The decisive discovery is that this is **not a new paradigm — it is a new instance of an already-in-production, fleet-validated pattern.** `autom8y-data` already ingests typed snapshot sync-contracts pushed by `autom8_asana`'s cache warmer (`POST /api/v1/account-status/sync` at `autom8y-data/src/autom8_data/api/routes/account_status.py:50`; "Mirrors the gid-mappings sync pattern" per `_account_status_sync.py:6`). That contract family is the modern north star the operator points at (`/scheduling-stratum/sync` is the same family, currently nascent/absent — no `scheduling-stratum` surface exists in any of the three repos at HEAD). The `account-status` sync payload *already carries `vertical` as an untyped `str`* (`_account_status_sync.py:44`), so the enum-option vocabulary is *already leaking across the seam* in an un-contractualized form. A dynamic enum-option sync contract simply makes that leak typed, named, and governed — composing an existing snapshot-replace idiom rather than inventing one. This is the calibrated-low-risk path. The realization (and the harder open question of whether it generalizes to the DEFER-1 fleet cf-contract registry) belongs to the downstream waves.

---

# PART A — CURRENT-STATE SYNTHESIS

## A.1 The defining distinction (state this first)

**gfr-dynvocab resolved *which fields exist* and *the selected value of an enum field*. THIS spike is about the enum OPTION-SET — the *universe of valid enum-option values* for an enum/multi_enum field — and contractualizing that option-set as a dynamic, cross-service-synced relationship.**

- gfr-dynvocab (`resolution/gfr/dynvocab.py`, merged to `origin/main` `e49c30d7`, telos CLOSED, realized N=1 2026-06-25 per `.know/telos/gfr-dynvocab.md:59`) keys the dynamic field **NAME** vocabulary, heuristically typing each field over a **FROZEN** cf-type contract set `{text, number, enum, multi_enum, date, people}`, with three-state contract `PRESENT / PRESENT_BUT_NULL / ABSENT` and per-field `typing_origin`.
- The selected-value extraction it relies on is `_extract_raw_value` (`src/autom8_asana/dataframes/resolver/default.py:234-287`). **The `enum` case (lines 257-263) reads `enum_value.name` — the currently-SELECTED option. It does NOT touch `enum_options` (the option-SET).** Same shape in the DRY twin `extract_cf_value` (`src/autom8_asana/dataframes/views/cf_utils.py:51-52`).
- The legacy `Vertical(Enum)` **IS an option-set** — the hand-curated universe of valid verticals. So this spike's subject is **adjacent to but distinct from** gfr-dynvocab: the *value domain* of the two closed-domain cf-types, not the field name vocabulary and not the selected value.

This is a NEW, un-built seam.

## A.2 Where enum option-sets live today — the fragmentation map

The option-set for a single concept (the canonical example: **vertical**) is materialized in **six** independent places across the fleet. The brief names the legacy four; two modern copies make it six. None is authoritative over the others; reconciliation is manual + Slack-nudged.

| # | Location | Form | Identity scheme | Reconciliation |
|---|----------|------|-----------------|----------------|
| 1 | `autom8/apis/contente_api/models/vertical/main.py:19` `Vertical(Enum)` | Hardcoded ~55 enum members | Python attr name + snake value | Hand-edited; `_missing_()` Slack-alerts admin-ops |
| 2 | same file `:261` `VERTICAL_NAMES` dict | Display-name map | keyed by `Vertical` member | Hand-edited (note the "D-6: close the gap" comment `:305` — drift is chronic) |
| 3 | SQL `verticals` table via `db_verticals()` (`:12`) / `sql_verticals` | DB rows `{key, name, id}` | `id` (int PK), `key` (str) | Hand-INSERT per the `_missing_` Slack runbook `:108-114` |
| 4 | **Asana's own live `enum_options`** on the cf | Live option list on the Asana custom field | `enum_option.gid` (per-workspace, opaque) | Operator-edited in Asana UI; bound via `Vertical(EnumField)` adapter (`autom8/apis/asana_api/objects/custom_field/models/enum/vertical.py`) |
| 5 | `autom8y-asana` `SEMANTIC_ANNOTATIONS[entity.field].valid_values` | Hardcoded YAML annotation block | by `entity_type.field_name` | Hand-edited; exposed via schema-discovery route (A.4) |
| 6 | **`autom8y-data` SQL `verticals`** + gRPC `VerticalService` | DB rows, served over gRPC | `vertical_id` (int PK), `vertical_key` (str unique) | "admin-only" `create`, no update/delete — "verticals are permanent" (`autom8y-data/src/autom8_data/services/vertical.py:7-9,48`) |

**The legacy four (1-3 + Asana live #4) are the canonical "three sources of truth + Asana's set = effectively FOUR places" tension the brief names.** The two modern copies (#5 the asana annotation registry, #6 the data-service table) make the true fragmentation **six**. Each copy can silently diverge; the legacy `_missing_()` codepath (A.3) is the worst of them.

## A.3 The legacy anti-pattern (NON-CANONICAL — lessons only, do not extend)

`Vertical._missing_()` (`contente_api/models/vertical/main.py:82-158`) is the option-set escape-hatch from hell, with **three side-effects on an unknown value**:
1. Slack alerts admin-ops with a 3-step manual registration runbook (`:104-126`) — the human reconciliation loop made explicit.
2. DB lookup against `sql_verticals` (`:102`).
3. **AUTO-MINTS a "phantom campaign" row** when the vertical is DB-present-but-Enum-absent (`:138-149`), flagged as a tracked defer-watch (`:122-125`).

This is **codegen-by-side-effect** — the live system mutating reference data as a side-effect of a failed lookup. It is precisely the auto-mutation hazard ADR-S4-001 and the gfr-dynvocab drift-gate discipline exist to escape. **Do not propose extending this.** The cf adapter seam `Vertical(EnumField)` (`.../enum/vertical.py`) marshals str/int ↔ `VerticalModel` via `enum_map` — that is the *binding seam* where Asana's option-set meets the domain vocabulary, and it is the seam a modern contract would replace, not extend.

## A.4 The Asana cf-adapter seam in `autom8y-asana` (the un-wired option-set)

The option-set already exists as typed model surface in `autom8y-asana` but is **not wired to resolution or sync**:

- **Model**: `CustomField.enum_options: list[CustomFieldEnumOption]` (`src/autom8_asana/models/custom_field.py:113`); each option carries `gid` (via `AsanaResource`), `name`, `enabled`, `color` (`:19-42`). `enum_value` / `multi_enum_values` (`:117-124`) are the *selected* values — distinct from the option-set.
- **Client CRUD on the live option-set**: `CustomFieldsClient.create_enum_option` (`src/autom8_asana/clients/custom_fields.py:441`), `update_enum_option` (`:528`) — full read/mutate of the Asana-side option universe by `enum_option_gid`.
- **The gap**: the resolution layer (`_extract_raw_value`, `extract_cf_value`) reads only the *selected* `enum_value.name`. **Nothing consumes `enum_options` for resolution or sync.** The only consumer of an option-SET is the schema-discovery API:
  - `GET /{entity_type}/schema/enums/{field_name}` (`src/autom8_asana/api/routes/resolver_schema.py:375`) returns `EnumDetailResponse` with a **`values_source` field already documented to be `'hardcoded'` or `'asana_configured'`** (`:366-369`).
  - But the values are pulled from **hardcoded** `SEMANTIC_ANNOTATIONS[entity.field].valid_values` (`:427,448-457`), NOT from the live Asana `enum_options`. The `'asana_configured'` source is **anticipated in the response contract but not wired.** The architecture already left the door open.

So: live `enum_options` lives in the model + client; a hardcoded `valid_values` lives in the annotation registry; the discovery route bridges them only via the static copy. The dynamic, Asana-sourced option-set contract is the missing wire.

## A.5 The sync TARGET — `autom8y-data`'s ingestion surface (the seam a "sync-in" lands against)

This is the most consequential current-state finding: **`autom8y-data` already operates a typed cross-service snapshot-sync contract family, in production, pushed by `autom8_asana`'s warmer.**

- **Existing instance — account-status**: `POST /api/v1/account-status/sync` (`autom8y-data/src/autom8_data/api/routes/account_status.py:50`). Contract `AccountStatusSyncRequest` (`_account_status_sync.py:70`): `{source, entries[], source_timestamp, entry_count}`, `model_config = {"extra": "forbid"}`, S2S JWT (`account_status.py:41`), **snapshot-replace semantics** ("BEGIN, DELETE WHERE source, INSERT fresh set, COMMIT" `:77`), **`entry_count` integrity check** (`:107-130`), idempotent (`x-fleet-idempotency.idempotent: True` `:68`), cross-service annotated (`x-fleet-cross-service-refs: {service: autom8y-asana} :69`), pushed every 4h by the cache warmer (`:7-9`).
- **A second instance exists** — gid-mappings sync (`_account_status_sync.py:6` "Mirrors the gid-mappings sync pattern"; `autom8y-data/.../data_service_models/_gid_mapping_sync.py`, route `api/routes/gid_mappings.py`). So the pattern is **N≥2 in production** — it is an established idiom, not a one-off.
- **The vocabulary already leaks across this seam untyped**: `AccountStatusEntry.vertical: str` (`_account_status_sync.py:44`) carries a vertical value with no option-set contract — exactly the un-governed relationship this spike would formalize.
- **The option-set's data-side home**: `VerticalService` / `VerticalAdapter` (gRPC, proto `Vertical`) over the SQL `verticals` table, keyed on `vertical_id` (int PK) + `vertical_key` (str, unique), read-heavy, "verticals are permanent" (`services/vertical.py:7-9,45-48`; `grpc/adapters/vertical.py:75-79`). This is the table a "sync-in" would snapshot-replace or upsert against, and `vertical_key` is the portable cross-service identity (`vertical_id` is a *local* handle, non-portable — see B.3).

**Conclusion of Part A**: the target seam is not greenfield. There is a proven typed-snapshot-sync contract to instantiate, a data-side option-set table to land against with a clean external key, and an architecture (asana schema-discovery `values_source: asana_configured`) that already anticipates Asana-sourced option-sets. The only missing pieces are (a) reading the live Asana `enum_options` instead of a hardcoded copy, and (b) a new typed contract instance carrying the option-set keyed on name.

---

# PART B — FEASIBILITY / BUILD-VS-BUY VERDICT

## Technology Overview
- **Category**: Cross-service reference-data / vocabulary sync contract (typed snapshot-replace), specialized to Asana enum-option-sets.
- **Maturity**: **Mixed.** The *substrate pattern* (typed snapshot sync-contract, asana→data, warmer-pushed) is **Mainstream in-house** — in production, N≥2 instances (account-status, gid-mappings). The *specific application* (enum-option-set vocabulary) is **Early/Experimental** (un-built new seam). The governing precedent (gfr-dynvocab NAME-keying + drift-gate-not-codegen) is **merged, realized N=1**.
- **License / Backing**: Internal fleet pattern; no new third-party dependency required (see Build-vs-Buy).

## Capabilities (what the pattern does well, evidenced)
- Eliminates the 4-6-source hand-reconciliation by designating one upstream source-of-record and pushing a typed snapshot (the `account-status` contract proves this works at the asana→data seam).
- Carries built-in safety: `extra="forbid"`, `entry_count` integrity check, snapshot-replace transactionality, S2S auth (all already in `account_status.py`).
- Fits the gfr-dynvocab governance model: name-keyed contract + drift-gate (warn-first) without codegen.
- The cf-type set stays FROZEN — option-set sync is META to `enum`/`multi_enum`, not a 7th type (see B.2).

## Limitations (what it does not solve)
- It does not resolve **truth-ownership**: who owns the vertical universe — the Asana UI live `enum_options`, or the `autom8y-data` `verticals` table that the Stripe SDK reads? A contract must *declare* the source-of-record; it cannot discover it. (Risk R1.)
- A one-way snapshot push cannot reconcile values *created* on the data side (e.g. `VerticalService.create`) back to Asana without a second contract or a drift-gate escalation.
- It does not by itself discharge the DEFER-1 fleet-wide cf-contract registry — it is one scoped drift class (B.4).

## Ecosystem Assessment
- **Community / adoption**: In-house, N≥2 production instances of the parent pattern; the team already operates the warmer-push cadence and the S2S contract discipline. External corroboration: typed snapshot-replace / CDC reference-data sync is a mainstream industry idiom (Debezium-style snapshots, schema-registry vocabularies) — but those are heavyweight relative to a ~55-row, 4-hourly option-set.
- **Documentation / tooling**: The contract pattern is ADR-backed (`ADR-account-status-state-projection`, `ADR-gid-mapping-*`) and OpenAPI-annotated with fleet envelopes; tooling (S2S JWT, rate-limit, integrity-check) is reusable as-is.
- **Maturity signals**: snapshot-replace + integrity-check already running in prod; gfr-dynvocab's 105-test certified spine is the regression gate the new work must not regress (`.know/telos/gfr-dynvocab.md:51,79`).

## B.2 FROZEN cf-type-set fit (does enum-option sync need a 7th type?)

**No extension needed.** The FROZEN set `{text, number, enum, multi_enum, date, people}` classifies how a field's *value* is typed/coerced. An option-SET is **meta to** the two members that have a closed value domain (`enum`, `multi_enum`) — it enumerates their valid universe; it is not itself a new field type. The schema-discovery route already demonstrates the correct shape: it attaches `valid_values` only to `enum`/`multi_enum` semantic types (`resolver_schema.py:275,438-446`). The contract should therefore ride as a **sidecar to those two cases**, leaving the FROZEN set untouched (this is also Risk R5's mitigation). This preserves gfr-dynvocab's "FROZEN as the contract surface" invariant.

## B.3 Option-identity keying (NAME vs gid vs external key)

gfr-dynvocab's hard constraint: vocabulary/overrides key on canonical field **NAME** (`NameNormalizer.normalize`); cf gid is a runtime intra-task **handle only** (opaque, per-workspace, non-portable) (`.know/telos/gfr-dynvocab.md:47`). The enum-option analogue resolves cleanly:

- `enum_option.gid` is **per-workspace, opaque, non-portable** — the exact disqualifying profile as cf gid. It must NOT be the cross-service key (Risk R2).
- `vertical_id` (data-side int PK) is **also a local handle** — non-portable across services.
- The portable identity is the **normalized option name / external key** — `vertical_key` ("chiropractic") is already the unique business key on both the legacy SQL `verticals` table and the `autom8y-data` table (`services/vertical.py:120-147`).

**Recommendation: key the sync contract on the normalized option name (external key). Each service maps it to its own local handle** (asana → `enum_option.gid` for mutations via `CustomFieldsClient`; data → `vertical_id`). This is the exact parallel of gfr-dynvocab's name-keyed-contract / gid-as-handle split.

## B.4 Drift-gate-not-codegen applicability + DEFER-1 cf-contract-registry relationship

**Drift-gate, not codegen.** ADR-S4-001 is a one-way door: schema codegen-FROM-model is forbidden; the recommended mechanism is a warn-first drift GATE (`.know/telos/gfr-dynvocab.md:78`). The enum-option analogue is direct: do NOT auto-generate the `Vertical(Enum)` (or the data-side table) from Asana's live `enum_options` — that is exactly the legacy `_missing_()` auto-mint anti-pattern (A.3). Instead, the contract **pushes a snapshot** (asana → data, the established warmer direction), and a **drift gate WARNS** when asana-live diverges from the data-side / annotation copy, with no auto-mutation. The snapshot-replace + integrity-check is gate-friendly by construction.

**DEFER-1 assessment (assessed, not assumed).** The gfr-dynvocab moonshot lodged: *fleet-scale coherence wants a cf-contract REGISTRY, not a per-repo drift-gate alone — escalate when a 2nd service binds the drift class* (`.know/telos/gfr-dynvocab.md:77`).

- **The trigger has fired.** `autom8y-data` binds `vertical` (an option-set) across the seam (`_account_status_sync.py:44`), and the cf-contract drift class has already drawn blood in the legacy monorepo: the satellite project-entity arm drops cf columns (`_CONTRACT_COLUMNS=("office_phone","vertical","gid")` `getdf_signals.py:77`), producing the bare `KeyError: 'asset_id'` now wrapped as a typed `ColumnContractError` (`paid_content/main.py:69-84`). The satellite **BULK projection** is a distinct surface from gfr-dynvocab's per-gid resolution — exactly the "2nd service binds the drift class" condition.
- **But the enum-option sync contract is NARROWER than the registry.** It governs ONE drift class (option-set vocabularies) between TWO named services. It realizes the *spirit* of DEFER-1 (a cross-service contract surface beyond a per-repo gate) and is a defensible pilot brick, but the general fleet-wide cf-contract registry remains DEFER until ≥3 drift classes / services accrue. **Recommendation: adopt the scoped sync-contract instance now; keep the general registry DEFER** (the anti-scope-creep stance, R6).

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **R1 — Truth-ownership ambiguity / sync loop** (Asana-live vs data-table both claim authority) | M | H | Declare **Asana live `enum_options` = single upstream source-of-record**; data ingests one-way (matches existing warmer-push direction); never auto-write-back. Data-side `create` becomes a drift-gate *signal*, not a back-sync. |
| **R2 — Identity keyed on `enum_option.gid`** (per-workspace, opaque, non-portable — breaks cross-workspace/cross-service) | M | H | Key the contract on the **normalized option NAME / external key** (`vertical_key`); carry gfr-dynvocab's NAME-keying constraint verbatim (`.know/telos/gfr-dynvocab.md:47`). gid is a runtime handle only on each side (asana `enum_option.gid`; data `vertical_id`). |
| **R3 — Legacy `_missing_` auto-mint contamination** (phantom-campaign side-effect if wired into the legacy path) | L | H | Do NOT extend `Vertical(Enum)`. New contract is a clean parallel surface; legacy auto-mint stays quarantined as the thing being escaped (`vertical/main.py:138-149`). |
| **R4 — Snapshot-replace blast radius** (a truncated/empty Asana read DELETEs the data-side vocabulary) | M | H | Reuse `entry_count` integrity check (`account_status.py:107`) + add a **non-empty floor guard**; mirror the "absence-only, never refuse already-populated" `ColumnContractError` discipline (`paid_content/main.py:69-84`) inverted: refuse the *empty publish*. |
| **R5 — FROZEN cf-type-set pressure** (temptation to add a 7th type for "option-set") | M | M | Keep the set FROZEN. Option-set is a **sidecar** to the two closed-domain members (`enum`, `multi_enum`), exactly as the schema-discovery route already attaches `valid_values` only to those two semantic types (`resolver_schema.py:275,438-446`). |
| **R6 — Scope creep into the full DEFER-1 fleet registry** | M | M | Scope this to the single drift class (enum-option vocabularies, asana↔data). The general cf-contract registry stays DEFER until N≥3 drift classes/services accrue (B.4). |

## Fit Assessment
- **Philosophy alignment (HIGH)**: name-keyed, drift-gate-not-codegen, strictly-additive — identical to the gfr-dynvocab discipline already merged. The modern north star (`custom_cal_url.py` declarative cascade `_resolve_from_cascade :198`, `category` as a *computed projection over typed sources* not a hand-maintained literal) is the value-resolution analogue; the `/sync`-contract family is the cross-service analogue.
- **Stack compatibility (HIGH)**: zero new third-party dependency; instantiates an existing FastAPI S2S snapshot-sync route + a typed Pydantic contract + the existing `CustomFieldsClient` reads of live `enum_options`. The data-side already has the `verticals` table and gRPC service.
- **Team readiness (HIGH)**: the team operates this exact pattern in production (account-status, gid-mappings). Learning curve is near-zero; the J-curve adoption dip is shallow because the idiom is known. **DORA-frame impact**: reduces *change-failure-rate* (removes the 4-6-source reconciliation that produced the `KeyError: 'asset_id'` class) and *MTTR* (typed `ColumnContractError`/integrity-check vs cryptic `KeyError` `paid_content/main.py:70`).

## Build-vs-Buy

| Option | Capability match | Adoption cost | Maintenance | Lock-in | Verdict |
|--------|-----------------|---------------|-------------|---------|---------|
| **Status quo** (4-6 hand-reconciled sources + `_missing_` auto-mint) | — fragmented, drift-prone | $0 now | High (Slack-nudge runbooks; phantom-campaign hazard) | None | **Reject** — the documented anti-pattern |
| **BUY external** (Confluent Schema Registry / LaunchDarkly config / Debezium CDC / reference-data MDM) | Over-capable; built for Avro/feature-flags/CDC, not a 55-row 4-hourly domain vocabulary | High (new dependency, ops surface, S2S/auth integration) | New external SLA + version coupling | **High** (vendor/protocol) | **Reject** — disqualified on adoption cost + lock-in for the scope; NIH-guard satisfied by naming the disqualifier explicitly |
| **BUILD on existing in-house sync-contract** (new `POST /api/v1/{vocab}/sync` instance mirroring account-status; asana reads live `enum_options`; data snapshot-replaces keyed on `vertical_key`) | Exact fit; reuses proven idiom | Low (instantiate a known pattern) | Low (same discipline as 2 existing instances) | None (internal) | **ADOPT-as-pattern** |

The build option is **composing an existing, validated internal pattern**, not building from scratch — the NIH-syndrome guard is satisfied (external options enumerated and disqualified on concrete criteria, not dismissed). No multi-agent / agent-architecture is proposed, so that anti-pattern guard is N/A by construction.

## Recommendation

**Verdict: TRIAL.**

**Rationale**: This sits past "Assess" because the evidence is strong and convergent — the parent sync-contract pattern is in production (N≥2), the gfr-dynvocab governing precedent is merged and realized, the DEFER-1 trigger has *already fired* in production, the data-side option-set table + portable key already exist, and the asana schema-discovery contract *already anticipates* `values_source: 'asana_configured'`. It is not yet "Adopt" because (a) no production code exists (this is a SPIKE), (b) the option-set application of the pattern is un-built, and (c) option-identity keying and the empty-publish blast-radius guard need a hands-on probe before commitment. The calibrated call is **Trial via a time-boxed prototype** — which is exactly the next wave in this pipeline.

**Next Steps (handoff)**:
1. **integration-researcher (Wave 2)**: map the dependency/effort to (a) read live Asana `enum_options` through `CustomFieldsClient` for a representative enum field (vertical), (b) wire the schema-discovery `values_source: 'asana_configured'` path (`resolver_schema.py:366`), (c) instantiate a new typed `/sync` contract mirroring `account_status.py:50` against the `autom8y-data` `verticals` table; identify breaking changes vs the existing untyped `AccountStatusEntry.vertical` leak.
2. **prototype-engineer (Wave 3)**: throwaway demo proving the round-trip — asana reads its OWN live `enum_options` → projects a typed snapshot keyed on **normalized option name** → stub data-side ingest snapshot-replaces keyed on `vertical_key` → a drift observation **warns (never codegens)** when asana-live diverges from data-side. Time-box 1-2 days. Validate R2 (identity) and R4 (empty-publish guard) specifically.
3. **moonshot-architect (Wave 4)**: focus on the OPEN question — whether this scoped instance generalizes to the DEFER-1 fleet cf-contract registry — NOT on building the registry. Keep registry DEFER.

## Comparison Matrix (decision criteria)

| Criterion | Dyn enum-option sync contract (this) | Status quo (4-6 hand sources) | External schema-registry / MDM | gfr-dynvocab precedent (reference) |
|-----------|--------------------------------------|-------------------------------|--------------------------------|------------------------------------|
| Single source-of-record | Yes (Asana live `enum_options`, declared) | No (fragmented) | Yes | Yes (NAME vocab) |
| Identity portability | Name/external-key keyed (portable) | Mixed (gid + int PK + attr) | Tool-defined | NAME-keyed (portable) |
| Codegen-free (drift-gate) | Yes (warn-first) | No (`_missing_` auto-mint) | Varies | Yes (ADR-S4-001 one-way door honored) |
| New dependency / lock-in | None (in-house pattern) | None | High | None |
| Adoption cost / team readiness | Low (proven idiom, N≥2) | $0 now / high ongoing | High | Already paid |
| FROZEN cf-type-set respected | Yes (sidecar to enum/multi_enum) | n/a | n/a | Yes (set is the precedent) |
| Realizes DEFER-1 | Scoped (one drift class) | No | Partially (over-built) | Lodged the dissent |

## Complexity Recommendation for Downstream Waves

**SPIKE** (scouting + prototyping per the rnd complexity table) — confirmed appropriate. The substrate is mature enough that a full EVALUATION is unwarranted; the un-built application is small enough that a time-boxed prototype resolves the residual uncertainty (identity-keying R2, empty-publish guard R4, source-of-record R1). Do **not** escalate to MOONSHOT complexity for the contract itself; reserve moonshot altitude only for the *separate* open question of DEFER-1 registry generalization.

---

## Evidence Grade

`[STRUCTURAL | MODERATE]` — ceiling, not floor. Self-referential (assessing the fleet's own patterns from inside) caps at MODERATE per `self-ref-evidence-grade-rule`; the rnd-dk literature also caps at MODERATE (no STRONG available in this rite). The in-house structural evidence (live route/model/contract anchors below) is high-confidence but self-ref-capped; external corroboration (Thoughtworks lifecycle taxonomy, snapshot/CDC reference-data idioms) is general. The realization predicate belongs to the downstream prototype + a rite-disjoint attester, not to this scout pass.

## Handoff Exit Criteria (→ integration-researcher)

- [x] Verdict present (**Trial**) with rationale, risks + mitigations, complexity recommendation.
- [x] Current-state four-sources tension documented (and extended to six modern copies).
- [x] gfr-dynvocab field-NAME-vocab vs enum-OPTION-SET distinction stated explicitly (A.1).
- [x] DEFER-1 cf-contract-registry relationship assessed, not assumed (B.4: scoped realization, registry stays DEFER).
- [x] Cross-service "sync-into-autom8y-data" framed as the target seam with concrete anchors (A.5: `account_status.py:50`, `_account_status_sync.py`, `services/vertical.py`).
- [x] Asana cf-adapter seam described; the un-wired live-`enum_options` gap located (A.4).
- [x] HARD constraints carried (NAME-keying R2/B.3; drift-gate-not-codegen B.4; strictly-additive — gfr 105-test spine inviolable).
- [x] Comparison matrix includes status quo + ≥1 external alternative + the gfr precedent.

## Source Anchors (platform-internal, `{path}:{line}`)

**autom8y-asana (cwd)** — gfr-dynvocab substrate read from telos (gfr/ dir absent on branch `chore/bump-core-4.6.0`, ~25 commits behind `origin/main e49c30d7`; no Bash to `git show`, so gfr internals cited via `.know/telos/gfr-dynvocab.md`):
- `.know/telos/gfr-dynvocab.md:47,51,77,78,79` — NAME-keying constraint, FROZEN cf-type set, 105-test spine, DEFER-1 dissent, codegen-from-model reverses ADR-S4-001
- `src/autom8_asana/dataframes/resolver/default.py:234-287` (enum case :257-263) — selected-value extraction, NOT option-set
- `src/autom8_asana/dataframes/views/cf_utils.py:51-52` — DRY twin extractor
- `src/autom8_asana/models/custom_field.py:19-42,113,117-124` — `CustomFieldEnumOption`, `enum_options`, `enum_value`/`multi_enum_values`
- `src/autom8_asana/clients/custom_fields.py:441,528` — `create_enum_option` / `update_enum_option`
- `src/autom8_asana/api/routes/resolver_schema.py:275,366-369,375,427,448-457` — enum-detail route, `values_source: 'hardcoded'|'asana_configured'`, hardcoded `valid_values`
- `src/autom8_asana/dataframes/models/registry.py` — schema/drift registry (warn-first discipline)

**autom8y-data (sync target)**:
- `src/autom8_data/api/routes/account_status.py:7-9,41,50,77,107-130` — the proven `/sync` contract instance (warmer-push, S2S, snapshot-replace, integrity check)
- `src/autom8_data/api/data_service_models/_account_status_sync.py:6,44,70,102` — typed contract, `vertical: str` untyped leak, `extra="forbid"`
- `src/autom8_data/api/data_service_models/_gid_mapping_sync.py` + `api/routes/gid_mappings.py` — second instance (N≥2)
- `src/autom8_data/services/vertical.py:7-9,45-48,120-147,149` ; `grpc/adapters/vertical.py:75-79` — data-side option-set table, `vertical_id`/`vertical_key`

**autom8 monorepo (legacy NON-CANONICAL + modern north star)**:
- `apis/contente_api/models/vertical/main.py:12,19,82-158,261,305` — `Vertical(Enum)`, `_missing_` auto-mint, `VERTICAL_NAMES`, `db_verticals`
- `apis/asana_api/objects/custom_field/models/enum/vertical.py` — `Vertical(EnumField)` cf adapter seam (`enum_map`)
- `apis/asana_api/objects/custom_field/models/text/custom_cal_url.py:198,221,244-248` — modern declarative cascade north star (`_resolve_from_cascade`, `category` computed projection)
- `apis/asana_api/satellite/getdf_signals.py:77` — `_CONTRACT_COLUMNS=("office_phone","vertical","gid")` (DEFER-1 trigger)
- `apis/asana_api/objects/project/models/paid_content/main.py:69-84` — `KeyError: 'asset_id'` → typed `ColumnContractError` (drift-class blood drawn)
- `scheduling-stratum` / `/sync` operator-cited surface: **not present** in any of the three repos at HEAD (nascent or external) — confirmed via repo-wide search.
