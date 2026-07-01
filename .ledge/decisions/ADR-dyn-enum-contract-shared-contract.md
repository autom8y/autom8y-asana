---
type: decision
status: accepted
initiative: dyn-enum-contract
id: ADR-dyn-enum-contract-shared-contract
title: "Shared cross-repo contract for the dynamic enum-option-set sync (asana producer ↔ data consumer)"
date: 2026-07-01
rite: 10x-dev
sprint: sprint-0 (design-lock — the single true head)
rung: authored            # G-RUNG cap = authored→proven→merged (ship-dark, flag OFF); NEVER live/verified-realized
evidence_grade_ceiling: "MODERATE — self-referential authorship ceiling per self-ref-evidence-grade-rule + G-CRITIC; STRONG belongs to the review-rite disjoint critic at PT-07"
producer_truth_anchor: "autom8y-asana feat/dyn-enum-contract @ 1eec7622 (advanced from the HANDOFF base ca28251d; +3 commits #171/#173/#174)"
consumer_truth_anchor: "autom8y-data feat/dyn-enum-contract @ 00106ea2 (advanced from the HANDOFF base 92d3606d)"
supersedes_wording: "the shape's 'vocab_upsert store / G6' framing (HANDOFF Correction 1 / REC-1 wins)"
authoritative_inputs:
  - ".ledge/handoffs/HANDOFF-arch-to-10x-dyn-enum-contract-2026-06-30.md  # authoritative; wins on conflict"
  - ".ledge/handoffs/HANDOFF-rnd-to-10x-dyn-enum-contract-2026-06-30.md   # FR-001..009 / NFR-001..004 / CON-001..010 source"
  - ".sos/wip/frames/dyn-enum-contract.shape.md                           # DAG, CON-001..010, RR risks"
  - ".know/telos/dyn-enum-contract.md                                     # RATIFIED 2026-07-01 (Gate-A CLOSED); realization predicate = acceptance target"
---

# ADR — dyn-enum-contract: the shared cross-repo sync contract

> **The ONE spec both build halves consume.** The producer (autom8y-asana, sprint-1) constructs
> against it; the consumer (autom8y-data, sprint-2) implements against it. This ADR is `authored`
> only — it locks the contract; it builds nothing. CAP = `authored → proven → merged (ship-dark,
> flag OFF)`. The production-mutating levers (two PR merges + the `GID_PUSH_ENABLED` live enable)
> stay the operator's.

## Status

`accepted` — design-lock. Gate-A is **CLOSED** (telos RATIFIED 2026-07-01, operator Tom Tenuta
countersign, as-drafted — `.know/telos/dyn-enum-contract.md:10`). This ADR is the sprint-0
exit-artifact named at `dyn-enum-contract.shape.md:113`.

---

## 1 · Context

An Asana Vertical enum-option-set change (a vertical added / renamed / disabled) does not reach
`autom8y-data.verticals` through any **typed** contract today. The vocabulary leaks across the seam
**untyped** — the producer emits `"vertical": str(vertical)` (`src/autom8_asana/services/gid_push.py:490`)
and the consumer receives `vertical: str` (`autom8y-data api/models_comparison.py:62`). The producer's
own resolver reads only the **selected** value, never the option-**set**
(`src/autom8_asana/dataframes/resolver/default.py:258-263` — `enum_value = get_attr("enum_value")` …
`return getattr(enum_value, "name", None)`); the option-set this contract carries has no reader today.

`verticals` is an **FK-PARENT** reference dimension. A careless snapshot-replace sync — safe for the
account-status *leaf* — would orphan FK children. The team's existing snapshot-replace idiom even ships
a literal `DELETE FROM account_status WHERE source = 'section_classifier'`
(`autom8y-data _platform.py:498`), but `verticals` has no `source` column to scope a DELETE to
(`_platform.py:131-149` = id/key/name only) — an unconditional DELETE would wipe the hub.

This ADR locks **one typed, additive, FK-safe sync contract** so both repos build against a single
spec, and it composes **up** to a future fleet registry (DEFER-1) without a rewrite.

**Realization predicate (the acceptance target, carried verbatim from the telos):**

> "Verified-realized" = a NEW or renamed Asana enum_option round-trips into `autom8y-data.verticals`
> via additive-upsert with existing ids + FK children (campaigns / asset_verticals ~43K /
> offers.category) intact within one sync cycle, AND an empty/truncated Asana read is hard-REFUSED
> with an alert (never applied) — asserted by a LIVE/integration test on a real option-set round-trip.
> NOT "endpoint merged", NOT "PRs green". (`.know/telos/dyn-enum-contract.md:101-106`)

---

## 2 · Decision — the locked contract (THREE compose-up locks as ONE spec)

The three locks are inviolable (prescribed doctrine, `dyn-enum-contract.shape.md:518`; CON-001/002/003,
`HANDOFF-rnd-to-10x…:144-147`). They are what keep the DEFER-1 registry door open at cardinality 1→N.

### Lock 1 — generic endpoint `POST /api/v1/vocabularies/sync` [CON-001]

The new consumer endpoint is the **generic plural** path `POST /api/v1/vocabularies/sync` —
**NEVER** `/verticals/sync`. A vertical-specific path would entrench cardinality-1 and force a rewrite
when a 2nd vocabulary binds. The route mirrors the account-status route's transport contract:
S2S JWT (`autom8y-data api/routes/account_status.py:42` `dependencies=[Depends(verify_jwt)]`),
rate-limit (`account_status.py:26` `from autom8_data.api.rate_limit import limiter`), and x-fleet-*
envelopes (`account_status.py:68-69`). It is a **NEW** endpoint, **not** an extension of
`/account-status/sync` (Lock-adjacent CON-010/BC-1 — see §6).

### Lock 2 — `field_key` discriminator = `"vertical"` from row one [CON-002]

Every request carries a `field_key` discriminator, valued `"vertical"` for this instance, **present
from row one**. This is the seam by which a 2nd vocabulary becomes a **data** addition (a new
`field_key` value), not a code change. Absent the discriminator, the per-instance contract cannot
compose up.

### Lock 3 — NAME-keying `vertical_key`, NEVER `enum_option.gid` / `vertical_id` [CON-003]

The cross-service key is `normalize(option.name) → vertical_key` (FR-002). The producer **never**
persists `enum_option.gid` and the consumer **never** persists `vertical_id` as the cross-service key.
`enum_option.gid` is a per-side Asana runtime handle; `vertical_id` is the consumer's autoincrement PK.
Either as the wire key would couple the two services to a per-side identifier and orphan on the other
side. The portable name-key is FK-safe at both ends: `vertical_key` is `unique=True` on the consumer
(`autom8y-data _platform.py:146` — `vertical_key: str = Field(unique=True, sa_column_kwargs={"name": "key"})`).

### The typed envelope (homed once in autom8y-core — see §5)

```
VocabularySyncRequest:
  field_key: Literal["vertical"]            # Lock 2 — discriminator, from row one
  options: list[VocabularyOption]           # the full option-SET (not the selected value)
  # model_config = {"extra": "forbid"}      # 422 on unknown fields (NFR-003 / BC-1)

VocabularyOption:
  vertical_key: str                         # Lock 3 — normalize(option.name); NEVER gid/vertical_id
  name: str                                 # display name (UPDATE-name target; unique=True consumer-side)
  enabled: bool | None                      # carried for drift observability only (RR2); NOT a stored column

VocabularySyncResponse:
  inserted: int; updated: int; refused: list[RefusedRow]   # additive-only accounting; per-row WARN+refuse
  # model_config = {"extra": "forbid"}
```

`enabled` rides the envelope for drift-WARN observability (`CustomFieldEnumOption.enabled`,
`src/autom8_asana/models/custom_field.py:35`). It is **not** a stored column — the `verticals` schema is
id/key/name only (`_platform.py:131-149`). A disabled-but-referenced option is a drift WARN, never a
DELETE (RR2/BC-3). The producer reads the live option-set off `enum_options`
(`src/autom8_asana/models/custom_field.py:113` — `enum_options: list[CustomFieldEnumOption] | None`).

---

## 3 · Decision — EC-1 CONFIRM-RECEIPT: the engine is **MySQL** (the fork is collapsed)

EC-1 is **CONFIRM-only** (not re-litigated). The PROTO PostgreSQL canary is REFUTED. Re-pasted live at
consumer HEAD **00106ea2**:

| Receipt | Live anchor @ 00106ea2 | Verbatim |
|---|---|---|
| R1 MySQL URL docstring | `core/config.py:217` | `MySQL URL in format: mysql+asyncmy://user:pass@host:port/database` |
| R2 asyncmy normalization | `core/config.py:222` | `return self.mysql_url.replace("mysql://", "mysql+asyncmy://")` |
| R5 DSN allowlist tuple | `services/base.py:387` | `for prefix in ("mysql+asyncmy://", "mysql+aiomysql://", "mysql://"):` |
| Upsert live exemplar | `api/services/forwarding_binding_store.py:155,:218,:252,:315` | `INSERT … ON DUPLICATE KEY UPDATE …` (4 occurrences) |

**ZERO PostgreSQL dialect in the consumer tree** (grep @ 00106ea2): `ON CONFLICT` = 0 hits (not even
Pydantic `description=` prose); `pg_advisory` / `asyncpg` / `psycopg2` = 0 hits; `GET_LOCK` /
`RELEASE_LOCK` = 0 hits.

**Bound upsert dialect:** `INSERT INTO verticals (key, name) VALUES (…) ON DUPLICATE KEY UPDATE
name=VALUES(name)`, keyed on `vertical_key` (`_platform.py:146`). **NOT** `ON CONFLICT(key) DO UPDATE`.
This is the SETTLED engine fact — not a build-time choice.

---

## 4 · Decision — concurrency (PT-04 refinement): reuse the PROVEN idempotent-upsert guard; **no** `GET_LOCK`

> This is the one genuinely open architectural decision the HANDOFF deferred (Correction 2 settled the
> *dialect*: IF a lock, then MySQL `GET_LOCK`, never `pg_advisory`; §9 least-certain-1 + §12 deferred the
> *need*-question as a runtime/sre concern, `[UNATTESTED — DEFER-POST-HANDOFF: lock-intro-sprint-2]`).
> The brief scopes the refinement here. **Decision: Option B.**

**NFR-001 (single-writer-per-`field_key`) is realized by the idempotent `INSERT … ON DUPLICATE KEY
UPDATE` upsert + the caller-owned transaction boundary + the FR-007 per-row collision guard — NOT by an
app-level named lock.**

### The two options (genuine; both viable)

- **Option A — app-level `GET_LOCK('vocab_sync_{field_key}', N)` / `RELEASE_LOCK(...)`** — a MySQL named
  lock serializing the whole per-`field_key` sync as one critical section.
- **Option B — reuse the codebase's proven idempotent-upsert race guard** — `INSERT … ON DUPLICATE KEY
  UPDATE`, the in-production pattern at `forwarding_binding_store.py:244-252`.

### Rationale for Option B (against the real write-concurrency profile)

1. **The proven idiom already exists in production.** `forwarding_binding_store.py:244-245` documents it
   verbatim: *"protects against double-activation race; ON DUPLICATE KEY UPDATE id = id makes the
   statement idempotent no-op on collision"* (`:252` is the live SQL). Reusing it composes with the
   established abstraction; `GET_LOCK` has **0 hits** in the consumer tree — a novel primitive with no
   precedent.
2. **The target is read-heavy / low-write.** `services/vertical.py:3` ("read-heavy operations"),
   `:32` ("This is a read-heavy service"), `:65` ("~40 verticals"); `dyn-enum-contract.shape.md:581`
   RR1 `probability: low`. Vocab changes are rare. The realistic hazard is two warmer instances pushing
   the **same** option-set near-simultaneously — and because both carry **identical** payloads
   (idempotent reads of the single Asana source-of-record, CON-008), MySQL row-level unique-key locking
   serializes the INSERT/UPDATE: one wins the INSERT, the other resolves via `ON DUPLICATE KEY UPDATE
   name=VALUES(name)` to the same name. Convergent; no lost-update; no orphan. NFR-002 (idempotent
   no-op-suppressing upsert) is satisfied by the same statement.
3. **On MySQL, `GET_LOCK` is connection-scoped, not transaction-scoped — so NFR-001's literal "lock
   releases at txn end" is a PostgreSQL `pg_advisory_xact_lock` semantic that EC-1 REFUTED.** With the
   consumer's async pool (asyncmy, `config.py:222`) a connection holding a named lock is returned to the
   pool and may be reused — a lock-lifecycle hazard (held across an unrelated request, or released early
   by pool recycling). The named lock is not merely unnecessary; on the SETTLED MySQL engine it is
   semantically mismatched to the NFR-001 phrasing and adds a failure surface.
4. **The two real serialization needs are met without a global lock.** (a) INSERT-vs-INSERT / UPDATE-name
   races → MySQL unique-key row lock + the idempotent upsert. (b) Name-swap A↔B two-phase update (R3) →
   the **already-established** caller-owned transaction boundary: `VerticalService` "NEVER commits … the
   caller owns the transaction boundary via `session.begin()`" (`services/vertical.py:34-43`); the
   FR-007 per-row collision guard (update-name only when non-colliding, else WARN + refuse-the-row) makes
   constraint violations deterministic. A two-statement swap is made atomic by the transaction, not by a
   per-`field_key` mutex.
5. **Don't open a one-way contention door pre-trigger.** The `GET_LOCK` contention surface under
   horizontal warmer scaling is explicitly UNATTESTED (HANDOFF §9 least-certain-1; §12 deferred to sre,
   adversary condition **C6**). The worst case Option B admits is *transient self-healing name staleness*
   (a stale name corrected on the next cycle; the FK-critical key/id is never mutated, no orphan) — a
   latency/contention concern, never a correctness one. Mirrors the initiative's own DEFER discipline:
   don't build the heavier primitive before its trigger fires.

### Bound consumer-store spec + the named contingency

Single-writer-per-`field_key` = (a) idempotent `INSERT … ON DUPLICATE KEY UPDATE name=VALUES(name)` keyed
on `vertical_key`, (b) the caller-owned `session.begin()` transaction enclosing the multi-row sync + any
name-swap two-phase, (c) the FR-007 per-row collision guard. **No `GET_LOCK`.** IF a post-build sre
contention finding (C6) shows the idempotent guard insufficient under real warmer fan-out, the
settled-dialect follow-on is `GET_LOCK('vocab_sync_{field_key}')` — a bounded, additive escalation, not a
rewrite. This **honors** the HANDOFF (settled dialect = GET_LOCK) while **resolving** the need-question it
deferred.

---

## 5 · Decision — REC-1: route through `VerticalService`, not a bespoke store (SUPERSEDES the shape's "vocab_upsert / G6")

The shape's "vocab_upsert store / `VocabUpsertStore` class / G6" wording is **superseded** by HANDOFF
Correction 1 / REC-1. A bespoke store manufactures a **second writer** to `verticals` (violating the
single-writer invariant) and bypasses the no-delete invariant.

**Live premise (re-verified @ 00106ea2):** `VerticalService.create` is the **sole** canonical writer.
`services/vertical.py` has exactly one write method — `create` (def at `:149`; the physical INSERT
`self._session.add(vertical)` at `:212`); `list`/`get`/`get_by_key` are read-only; there is **no**
update and **no** delete method. The no-delete invariant is stated at `services/vertical.py:9`
("No Delete operation (verticals are permanent)").

**Spec:** extend `VerticalService` with an **additive-upsert** operation (e.g. `upsert_by_key`) — NOT a
new class. It must: create-if-absent keyed on `vertical_key` (`_platform.py:146`); update-name only when
non-colliding against the `vertical_name` unique constraint (`_platform.py:147` — FR-007: else per-row
WARN + refuse-the-row); **NEVER DELETE** (`services/vertical.py:9`). Route `/api/v1/vocabularies/sync`
**through** this extended service. The FR-003 "vocab_upsert" is the additive-upsert **operation** homed
in `VerticalService`, not a standalone store. (Watch R-F1: grep `autom8y-data/src` for `verticals` writes
→ only `services/vertical.py` may appear.)

---

## 6 · Decision — Correction 6 / G-PROPAGATE: SDK-home in autom8y-core is the SOLE propagation point

`VocabularySyncRequest` + `VocabularySyncResponse` are homed **once** in `autom8y-core`, the established
cross-repo model home (precedent: `VerticalsListResponse` at autom8y-core `clients/data_intake.py:473`).
Both repos import from `autom8y_core`; **zero** per-repo duplicate definitions.

**Confirmed live:** both repos pin `autom8y-core>=4.2.0,<5.0.0` (producer `pyproject.toml:26`, consumer
`pyproject.toml:30`); installed `autom8y-core 4.6.0` satisfies the range. `VocabularySync*` /
`vocab_upsert` / `VocabUpsert` = **0 hits** in both `src/` trees today — the models are net-new. The
propagation mechanism is a single autom8y-core minor bump (e.g. 4.7.0) homing the two models; both repos'
existing `>=4.2.0,<5.0.0` pins absorb it with **no pin-range edit** (defeats R6 release-coupling: a schema
change is one SDK edit, not two coordinated repo edits).

The producer reuses the **endpoint-parameterized** push helper — `_push_to_data_service(*, endpoint_path:
str, payload, response_model, …)` (`src/autom8_asana/services/gid_push.py:163`) — passing the new
`/api/v1/vocabularies/sync` path (the same helper today carries
`endpoint_path="/api/v1/account-status/sync"` at `gid_push.py:564`).

---

## 7 · C4 — anchor re-verification table (HEADs advanced; stale → live) + the #174 finding

Every load-bearing anchor re-verified LIVE at producer **1eec7622** / consumer **00106ea2** (G-PROVE).

### Producer (autom8y-asana) — base ca28251d → HEAD 1eec7622 (+#171/#173/#174)

| Anchor | Correction-7 (ca28251d) | LIVE (1eec7622) | Status |
|---|---|---|---|
| `GID_PUSH_ENABLED_ENV_VAR` | `gid_push.py:62` | `gid_push.py:62` | **STABLE** |
| flag gate (conditional read) | `gid_push.py:95` | `gid_push.py:95` | **STABLE** |
| `_push_to_data_service` helper | `gid_push.py:163` | `gid_push.py:163` | **STABLE** (endpoint-parameterized) |
| leaf empty-guard path A | `gid_push.py:328` | `gid_push.py:328` | **STABLE** (`return True  # Nothing to push is not a failure`) |
| leaf empty-guard path B | `gid_push.py:554` | `gid_push.py:554` | **STABLE** (same line, 2nd path) |
| untyped producer seam | `gid_push.py:490` | `gid_push.py:490` | **STABLE** (`"vertical": str(vertical),`) |
| account-status endpoint_path | `gid_push.py:564` (env :375) | `gid_push.py:564` / `:375` | **STABLE** |
| `enum_options` | `custom_field.py:113` | `custom_field.py:113` | **STABLE** |
| `enabled` flag | `custom_field.py:35` | `custom_field.py:35` | **STABLE** |
| `extra="ignore"` | `custom_field.py:3` | `custom_field.py:3` | **STABLE** |
| `values_source` door | `resolver_schema.py:366`/`:473` | `resolver_schema.py:366`/`:473` | **STABLE** (file=475 ln; stale `:491` past-EOF confirmed) |
| selected-value-only read (the gap) | `default.py:258-263` | `default.py:258-263` | **STABLE** |
| autom8y-core pin | `pyproject.toml:26` | `pyproject.toml:26` | **STABLE** (`>=4.2.0,<5.0.0`) |

### Consumer (autom8y-data) — base 92d3606d → HEAD 00106ea2

| Anchor | HANDOFF (92d3606d) | LIVE (00106ea2) | Status |
|---|---|---|---|
| MySQL URL docstring | `core/config.py:217` | `core/config.py:217` | **STABLE** |
| asyncmy normalization | `core/config.py:222` | `core/config.py:222` | **STABLE** |
| DSN allowlist tuple | `services/base.py:387` | `services/base.py:387` | **STABLE** |
| upsert exemplar | `forwarding_binding_store.py:155/:218/:252/:315` | same | **STABLE** |
| idempotent `id = id` race guard | (within :252) | `forwarding_binding_store.py:244-245`/`:252` | **STABLE** |
| **sole writer** `create` | `services/vertical.py:212` | `services/vertical.py:149` (def); `:212` = `session.add` INSERT | **MOVED — invariant HOLDS** |
| no-delete invariant | `services/vertical.py:9` | `services/vertical.py:9` | **STABLE** |
| `vertical_key` unique | `_platform.py:146` | `_platform.py:146` | **STABLE** |
| `vertical_name` unique | `_platform.py:147` | `_platform.py:147` | **STABLE** |
| **offers.category STRING FK** | `_platform.py:162` | `_platform.py:162` | **STABLE** (`foreign_key="verticals.key"`) |
| campaigns int FK | `_advertising.py:80` | `_advertising.py:80` | **STABLE** |
| asset_verticals int FK (composite PK) | `_advertising.py:322`/`:326` | `_advertising.py:322`/`:326` | **STABLE** |
| account-status DELETE (not to copy) | `_platform.py:497-498` | `_platform.py:498` | **MINOR −1** |
| Business.default_vertical_id (FALLBACK) | `_platform.py:72` | `_platform.py:70` | **MINOR −2** |
| Question.vertical_id (nullable) | `_platform.py:451` | `_platform.py:451` | **STABLE** |
| Payment generated vertical_id (str) | `_platform.py:419` | `_platform.py:419` | **STABLE** |
| verticals schema (id/key/name only) | `_platform.py:142-147` | `_platform.py:131-149` (class :131, tablename :142) | **STABLE** |
| untyped consumer seam | `models_comparison.py:62` | `models_comparison.py:62` | **STABLE** |
| envelope template Request/Response | `_account_status_sync.py:70`/`:113` | `_account_status_sync.py:70`/`:113` | **STABLE** (`extra="forbid"` :67/:102/:128) |
| SDK-home precedent | `data_intake.py:473` | `data_intake.py:473` | **STABLE** (`VerticalsListResponse`) |

Only **one semantic move** (sole-writer `create` def `:212→:149`; the INSERT now sits at `:212`) and two
**±1/2-line** drifts. **No anchor falsified.** The REC-1 sole-writer premise HOLDS.

### #174 "ACTIVE-enum sweep" investigation → **FALSE-FRIEND; NO G-HALT**

Commit #174 (`1eec7622` — *"feat(onboarding-walkthrough): ACTIVE-enum sweep trigger + C-BN1-05 audit +
VERIFIED-tier (DARK)"*) touched **only** `workflows/onboarding_walkthrough/{constants,identity_guard,
workflow}.py`, `lambda_handlers/{__init__,onboarding_walkthrough}.py`, and their tests. The direct diff
`git diff ca28251d..1eec7622 -- gid_push.py custom_field.py resolver_schema.py` is **EMPTY**. The
"ACTIVE-enum" is the onboarding-walkthrough workflow's active-enum — **not** the Asana Vertical
custom-field `enum_options` this contract reads. The two other intervening commits (#171 GFR by-guid
guard; #173 scheduling asana normalizer-seam) likewise do not touch the producer contract surface.
**Producer pipeline: no G-HALT.** The contract surface is byte-identical across the advance.

> **G-DEFER watch (noted, not designed):** #173 (scheduling normalizer-seam + snapshot-push) and the
> consumer's #218 (scheduling stratum) are **DEFER-1 watch signals** toward the "3rd consuming service"
> half of the N≥3 trigger. N<3 today (only `field_key="vertical"` binds, and `/vocabularies/sync` does
> not yet exist). The registry stays ESCALATE-only; **NOT built here** (G-DEFER).

---

## 8 · FK coverage denominator (G-DENOM = **3 FK edges**) + the ≥7-edge fan-in

The referential-coverage hard-refuse (FR-004) unions **exactly three** inbound FK edges — the
denominator that gates empty/truncated REFUSE. All re-verified @ 00106ea2:

| Edge | Type | Live anchor | Verbatim |
|---|---|---|---|
| E1 campaigns | INT FK | `_advertising.py:80` | `vertical_id: int = Field(foreign_key="verticals.id")` |
| E2 asset_verticals (~43K) | INT FK, composite PK | `_advertising.py:326` (table `:322`) | `vertical_id: int = Field(foreign_key="verticals.id", primary_key=True)` |
| **E3 offers.category** | **STRING FK** | `_platform.py:162` | `vertical_key: str = Field(sa_column_kwargs={"name": "category"}, foreign_key="verticals.key")` |

**E3 is the load-bearing edge** (RR4/TR-4): a STRING FK with **no DB-level referential integrity** — an
orphaned string does not raise; it silently stops resolving. The coverage union MUST include it from day
one. (asset_verticals row count ~43K is `[UNATTESTED — DEFER-POST-HANDOFF: U-1-row-counts]`.)

Wider fan-in (≥7, NOT in the FR-004 coverage denominator but in the blast-radius map): + E4
Business.default_vertical_id FALLBACK (`_platform.py:70`), E5 Question.vertical_id (`_platform.py:451`),
E6 Payment generated str (`_platform.py:419`), E7 `[sched] models/shared.py:48` (cross-repo). Join hub:
`dimension_enrichment.py:144` (J1 PRIMARY) + `:166` (J2 FALLBACK, same parent, no redundancy) → DuckDB
LEFT JOIN silent-corruption path (`enrichment_views.py:152`).

---

## 9 · Entry-gate ledger (EC-1..4)

| EC | State | Receipt / disposition |
|---|---|---|
| **EC-1** DB engine | **CONFIRMED = MySQL** | §3 receipts @ 00106ea2; `ON DUPLICATE KEY UPDATE`; PostgreSQL dialect 0 hits. Fork COLLAPSED. |
| **EC-2** live-Asana credential path | **OPERATOR-SHELL-ONLY** | AWS Secrets Manager `autom8y/asana/asana-pat`; do **not** assume CI parity. Settled at the sprint-1 build-phase live probe. `[UNATTESTED — DEFER-POST-HANDOFF: EC-2-credential-path]` (security/IAM, CRR-003). |
| **EC-3 / Gate-A** telos countersign | **CLOSED** | telos RATIFIED 2026-07-01, operator countersign as-drafted (`.know/telos/dyn-enum-contract.md:10`); both `[OPERATOR-SET]` fields approved (deadline 2026-07-23; attester = review-rite external critic). |
| **EC-4** schema-discovery consumer-compat | **SEQUENCED AHEAD of the flip** | the `values_source:'asana_configured'` re-point (`resolver_schema.py:366`/`:473`, FR-009) is gated on a consumer-compat check **before** the live schema-discovery flip (sprint-4). |

PT-02 (consumer-repo execution rite) remains the **operator's** fork (dre-native vs 10x-dev-synced) —
NOT pre-picked here; the consumer leg builds against THIS ADR either way (RESOLVED = the ADR is the one
spec the consumer pipeline consumes).

---

## 10 · Realization-predicate → contract-acceptance trace, and FR/NFR → ADR mapping

### Predicate legs → where the contract makes each assertable

| Predicate leg (telos `:62-66`) | Contract mechanism | Anchor |
|---|---|---|
| POSITIVE round-trip, additive-upsert keyed on `vertical_key`, ids preserved | §5 extend `VerticalService` (create-if-absent / update-name) + §3 `ON DUPLICATE KEY UPDATE name=VALUES(name)` | `vertical.py:149`; `_platform.py:146` |
| FK children intact (campaigns / asset_verticals ~43K / offers.category) | §8 3-edge coverage union; DELETE-forbidden | `_advertising.py:80,:326`; `_platform.py:162`; `vertical.py:9` |
| NEGATIVE empty/truncated → hard-REFUSE + alert, never applied | §2 Lock-1 route + producer referential-coverage hard-refuse replacing the leaf guard | `gid_push.py:328`/`:554` (leaf guard the vocab path hardens) |
| COMPOSE-UP locks hold (generic path / field_key / NAME-key) | §2 Locks 1-3 | CON-001/002/003 |
| DRIFT honesty (WARN, never codegen; per-row name-collision refuse) | §5 FR-007 guard; drift-WARN (ADR-S4-001) | `_platform.py:147` |
| SPINE unregressed (gfr **105-test** certified spine; new endpoint, not extend) | CON-007 mechanical gate; CON-010 new endpoint | `dyn-enum-contract.shape.md:524` |

### FR/NFR → ADR exit-criteria

| Req | Bound in | Req | Bound in |
|---|---|---|---|
| FR-001 new generic endpoint | §2 Lock-1 + §6 route parity | FR-007 name-collision guard | §5 (per-row WARN+refuse) |
| FR-002 NAME-key | §2 Lock-3 | FR-008 first-sync dry-run | §9 EC-4 sequencing (sprint-4) |
| FR-003 additive-upsert (no 2nd writer) | §5 REC-1 | FR-009 schema-discovery re-point | §9 EC-4 |
| FR-004 3-edge coverage hard-refuse | §8 (G-DENOM=3) | NFR-001 single-writer-per-field_key | §4 (idempotent guard + txn) |
| FR-005 live read + creds + flag-gate | §6 helper + §9 EC-2 | NFR-002 idempotent no-op upsert | §4 (`ON DUPLICATE KEY UPDATE`) |
| FR-006 drift WARN, no codegen | §10 trace (ADR-S4-001) | NFR-003 S2S/rate-limit/envelopes | §2 Lock-1 (`account_status.py:42/:26/:68`) |
| CON-001/002/003 three locks | §2 | NFR-004 structured logging + deploy-gate | sprint-1 (ship-dark) |

---

## 11 · Alternatives considered (genuine; not strawmen)

| # | Alternative | Rejected because |
|---|---|---|
| A1 | **`/verticals/sync`** vertical-specific path | Entrenches cardinality-1; forces a rewrite at the 2nd vocabulary. CON-001. |
| A2 | **Extend `/account-status/sync`** with a vocab field | `extra="forbid"` (`_account_status_sync.py:67`) makes a new field BREAKING. CON-010/BC-1 → new endpoint. |
| A3 | **`enum_option.gid` / `vertical_id`** as the wire key | Per-side handles; orphan on the other side. CON-003 → NAME-key. |
| A4 | **Bespoke `vocab_upsert` / `VocabUpsertStore`** | Second writer to `verticals`; bypasses no-delete invariant. REC-1 → route through `VerticalService`. |
| A5 | **Per-repo duplicate models** | Hidden release-coupling (R6). Correction 6 → autom8y-core home. |
| A6 | **`GET_LOCK` named lock** (PT-04 Option A) | Novel primitive (0 hits); connection-scoped on MySQL ≠ NFR-001 "releases at txn end"; contention UNATTESTED. §4 → idempotent guard; GET_LOCK is the deferred contingency. |
| A7 | **PostgreSQL advisory lock / `ON CONFLICT`** | REFUTED by 7 live MySQL receipts. §3. |
| A8 | **Snapshot-replace DELETE** (account-status semantics) | `verticals` has no `source` column to scope a DELETE; unconditional DELETE orphans the FK-parent. CON-004. |
| A9 | **Hub decoupling / denormalize verticals** | Hub is the correct topology for a global reference dimension; denormalization spreads write-side fragmentation. Defense is write-path integrity, not topology. |
| A10 | **Fleet cf-contract registry now** (DEFER-1 Option-F) | One-way door at N<3. ESCALATE-only at the N≥3 conjunction. §7 G-DEFER. |

---

## 12 · Consequences

**Positive.** One typed seam replaces six hand-reconciled sources; FK-parent safety by construction
(additive-only, DELETE-forbidden, 3-edge coverage refuse); composes up to the DEFER-1 registry without a
rewrite (the three locks); zero new runtime dependency (reuses the proven upsert idiom + endpoint-
parameterized push helper + autom8y-core SDK home); strictly-additive to the gfr 105-test spine.

**Negative / accepted.** Option B admits transient self-healing **name** staleness under the rare
concurrent-distinct-payload race (corrected next cycle; FK key/id never mutated) — accepted vs. the
`GET_LOCK` lifecycle hazard. The read-side stays fragmented across **4 consumers** (SDK typed conduit, ads
`VerticalNormalizer`, sms denormalized, scheduling shared-FK) — this contract is neutral to it (R5
ACCEPT-AS-IS; CRR-002 to debt-triage).

**Reversibility (one-way vs two-way doors).** Two-way (reversible): the producer flag (ship-dark, OFF at
merge); the `values_source` re-point (FR-009, reversible config flip); the autom8y-core model bump
(additive). One-way (guarded): a live DELETE on `verticals` (FORBIDDEN, CON-004); building the DEFER-1
registry (ESCALATE-only, §7). The `GET_LOCK` contingency (§4) is additive, not one-way.

**Carried adversary conditions (HANDOFF §14).** C1 ✅ applied; **C2** Gate-A ✅ CLOSED; **C3** PT-02
operator-sovereign (unsettled, defer to PT-01→PT-02 boundary); **C4** ✅ this §7 table; **C5** re-run
R-EC1/R-F1/R-F3 at sprint-2 PR; **C6** sre `GET_LOCK` contention assessment post-build (the §4 contingency
gate).

---

## 13 · Evidence grade & gate compliance

`[STRUCTURAL | MODERATE]` — self-referential authorship ceiling (`self-ref-evidence-grade-rule`; G-CRITIC
caps MODERATE). STRONG belongs to the rite-disjoint **review-rite** critic at PT-07 (out of scope here).

- **G-PROVE** — every claim a live `{path}:{line}` re-verified at producer 1eec7622 / consumer 00106ea2;
  no carried-from-frame anchors (the stale `gid_push.py:519/:131/:351/:491` and `vertical.py:212` frame
  anchors are corrected in §7).
- **G-RUNG** — cap = **merged ship-dark, flag OFF**; this ADR is `authored`. Not rounded to live/verified.
- **G-DENOM** — named: **3** FK coverage edges (§8); **105** gfr certified tests (CON-007); **4** read-side
  consumers (§12); ≥7 fan-in edges (§8).
- **G-PROPAGATE** — SDK-home (autom8y-core) is the sole propagation point (§6); 0 per-repo duplicates.
- **G-DEFER** — DEFER-1 registry ESCALATE-only at N≥3; not designed (§7).
- **G-CRITIC** — self-grade MODERATE; STRONG reserved for PT-07.

**ADR path:** `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-dynenum/.ledge/decisions/ADR-dyn-enum-contract-shared-contract.md`
