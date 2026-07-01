---
type: spike
status: draft
slug: dyn-enum-contract
wave: 5 (tech-transfer)
upstream:
  - .ledge/spikes/SCOUT-dyn-enum-contract.md (wave 1 — TRIAL)
  - .ledge/spikes/INTEGRATE-dyn-enum-contract.md (wave 2 — FK-parent correction)
  - .ledge/spikes/PROTO-dyn-enum-contract.md (wave 3 — GO; two-sided canaries)
  - .ledge/spikes/MOONSHOT-dyn-enum-contract.md (wave 4 — Option F target, DEFER-1)
downstream: 10x-dev (productionization rite) via HANDOFF-rnd-to-10x-dyn-enum-contract-2026-06-30
evidence_grade: "[STRUCTURAL | MODERATE]"
verdict: "CONDITIONAL GO"
---

# TRANSFER: Dynamic Enum-Option-Set Sync Contract (dyn-enum-contract)

> rnd /spike — Wave 5 (tech-transfer). The R&D-to-production bridge. NO production code, NO telos
> authoring (user-sovereign — surfaced, not authored). This TRANSFER is the internal R&D summary that
> feeds `HANDOFF-rnd-to-10x-dyn-enum-contract-2026-06-30.md`.
> Evidence ceiling **MODERATE** — self-referential (assessing the fleet's own seams from inside) per
> `self-ref-evidence-grade-rule`; rnd-dk literature caps at MODERATE. The spike's GO is **feasibility-grade,
> not production-grade**: the per-instance contract is NOT YET BUILT. Spike-PROVEN is rigorously partitioned
> from production-PROVEN throughout (§0.2).

---

## 0. Frame

### 0.1 What this packages

A **dynamic enum-option-set sync contract**: `autom8y-asana` reads its OWN live Asana `enum_options`
(canonical example: the `Vertical` custom field), projects a typed snapshot keyed on the portable
**option NAME** (`vertical_key`), and pushes it to the sibling `autom8y-data` service, which **upserts
additively** (insert-new / update-name-enabled / **never delete**) onto its FK-parent `verticals` table.
This makes the vocabulary that **already leaks across the asana→data seam untyped today**
(`AccountStatusEntry.vertical: str`, `_account_status_sync.py:44`) typed, named, and governed — by
**composing an existing production idiom** (the N≥2 snapshot-sync contract family), corrected from
snapshot-replace to additive-upsert because the target is an FK-parent dimension, not a leaf store.

### 0.2 Evidence partition — what is PROVEN vs what is NOT YET BUILT (the load-bearing distinction)

The Wave-3 prototype is **feasibility-PROVEN** (two-sided discriminating canaries with captured output,
stdlib only, throwaway fixtures). The production contract is **NOT YET BUILT**. This TRANSFER does not let
spike-proven bleed into production-proven.

| Claim | Status | Receipt |
|-------|--------|---------|
| Additive-upsert preserves existing `id`s; FK children resolve after insert-new + update-in-place | **SPIKE-PROVEN** (Canary 1, two-sided, teeth) | `.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:182-201` (upsert fn), captured GREEN verdict `PROTO-dyn-enum-contract.md:152` |
| Snapshot-replace (DELETE+INSERT) orphans FK children or FK-blocks the DELETE | **SPIKE-PROVEN** (Canary 1 RED) | `.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:146-174` (replace fn), captured RED verdict `PROTO-dyn-enum-contract.md:126` |
| Canary 1 is two-sided / discriminating (bites only on the defect) | **SPIKE-PROVEN** | `.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:389-393`, `PROTO-dyn-enum-contract.md:164` |
| Leaf-calibrated empty guard returns `True` (no-op) on empty input | **SPIKE-PROVEN** (file-read + Canary 2) | `src/autom8_asana/services/gid_push.py:514-519`; canary mirror `canary2_empty_publish.py:108-126` |
| FK-parent hard-refuse guard discriminates empty/truncated from healthy | **SPIKE-PROVEN** (Canary 2, two-sided) | `.sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py:134-190`, two-sided verdict `:328-332`; captured `PROTO-dyn-enum-contract.md:227,249,281` |
| The production `vocab_upsert` store / `/vocabularies/sync` endpoint / drift observer | **NOT BUILT** | n/a — these are REQUIREMENTS (§3), not claims |
| Concurrent-upsert correctness; first-sync reconciliation; live-Asana payload shape | **PROJECTED / UV-P** | §4 risks; staging-test deferred |
| The `verticals` table DB engine (MySQL vs PostgreSQL) | **UNRESOLVED / UV-P** — priors disagree | §5 entry-criterion EC-1 |

### 0.3 Prototype code is REFERENCE ONLY

The two canary scripts at `.sos/wip/spikes/dyn-enum-contract/` are **throwaway proof fixtures** (SQLite
in-memory, hardcoded option-sets, `print()` instead of structured logging, no S2S/HTTP, no live Asana).
**Production MUST be reimplemented against production contracts** — the canaries prove the *mechanism
decision*, not a portable codebase. The prototype-to-production translation table (§2) maps every fixture
component to its production equivalent with the gap that separates them. There is no "cleanup" path; there
is a fresh build against the requirements in §3.

---

## 1. Prototype Summary

**What was built** (`PROTO-dyn-enum-contract.md`, two canaries): a discriminating proof of the two
load-bearing mechanism questions the integration researcher flagged as Medium-confidence and routed for
hands-on validation.

- **Canary 1 — FK-parent write semantics.** On a fixture `verticals{id,key,name}` table with `campaigns`
  and `asset_verticals` FK children (mirroring `_advertising.py:80,326`; 43,057 rows in production),
  snapshot-replace (DELETE+INSERT) either FK-blocks the DELETE (strict mode) or reassigns the AUTOINCREMENT
  `id` and orphans every FK child (loose mode); additive-upsert keyed on `vertical_key` preserves existing
  `id`s and inserts a genuinely-new key without collision. Two-sided, teeth (`canary1_fk_parent.py:389-393`).
- **Canary 2 — empty/truncated-publish hard-refuse.** The current producer empty guard
  (`gid_push.py:514-519`, `return True  # Nothing to push is not a failure`) is correct for the
  `account_status` leaf but **catastrophic** for an FK-parent: an empty or truncated Asana read silently
  no-ops. The FK-parent hard-refuse guard correctly refuses empty input AND truncated input missing any
  FK-referenced key, while passing the healthy full set. Two-sided, teeth (`canary2_empty_publish.py:328-332`).

**What was validated**: the additive-upsert mechanism is safe where snapshot-replace is not; the
referential-coverage hard-refuse guard is the correct replacement for the leaf-calibrated empty guard.
Both decisions are now evidenced, not hypothesized.

**Key constraints discovered** (carried forward as Non-Negotiable Constraints, §3.3): the FK-parent reality
forbids DELETE; `verticals` has no `source` column to scope a DELETE (`_platform.py:145-147`); the portable
identity is `vertical_key`, never `enum_option.gid` or `vertical_id`; `verticals.vertical_name` is
`unique=True` (`_platform.py:147`) — a name-collision hazard on the UPDATE path discovered at moonshot wave.

---

## 2. Prototype-to-Production Translation Table (REFERENCE ONLY)

Every prototype shortcut maps to a production component it papers over. This is the anti-"prototype-as-production"
discipline: the left column is throwaway; the right column is a fresh build.

| Prototype component (REFERENCE) | Anchor | Production equivalent (BUILD) | Gap |
|---------------------------------|--------|-------------------------------|-----|
| Hardcoded `VERTICAL_ENUM_OPTIONS_FIXTURE` | `canary1_fk_parent.py:40-45` | Live read `CustomFieldsClient.get(vertical_cf_gid).enum_options` | network, auth (AWS Secrets Manager `autom8y/asana/asana-pat`), rate-limit, feature flag (`gid_push.py:491`) |
| SQLite in-memory `verticals` fixture | `canary1_fk_parent.py:61-88` | Real `autom8y-data` `verticals` store via service layer | **DB engine UNRESOLVED** (EC-1); real upsert syntax + advisory lock; staging validation |
| In-fixture `additive_upsert` via `ON CONFLICT(key)` | `canary1_fk_parent.py:182-201` | New `vocab_upsert()` store method on `VerticalService` (genuinely new code, NOT a clone) | concurrency, name-collision guard (RR1), engine-specific syntax |
| `snapshot_replace` simulation (the RED) | `canary1_fk_parent.py:146-174` | **NOT built — proven unsafe; the path to avoid** | n/a (this is the rejected mechanism) |
| Hardcoded `FK_REFERENCED_KEYS` frozenset | `canary2_empty_publish.py:80-85` | Real cross-table coverage query unioning 3 FK edges incl `offers.category` string-edge | 1 DB round-trip/cycle; `offers.category` clause (RR4) must be present |
| `current_leaf_guard` (the RED) | `canary2_empty_publish.py:108-126` | **NOT built — the existing leaf guard `gid_push.py:514-519` is REPLACED for the vocab path** | the leaf guard stays for account_status; the vocab path gets the hard-refuse |
| `fk_parent_hard_refuse_guard` | `canary2_empty_publish.py:134-190` | Producer-side hard-refuse guard before transport | real DB coverage query; structured alert; deploy-gate metric |
| `print()` output | both canaries | `structlog`/JSON `logger.warning(..., extra={...})` | observability; ship-dark canary metric |
| No transport | both canaries | New `push_vocab_to_data_service()` reusing `_push_to_data_service` (`gid_push.py:528`) + S2S JWT | new producer fn; new consumer endpoint |
| No consumer endpoint | n/a | New `POST /api/v1/vocabularies/sync`, `extra="forbid"`, S2S, rate-limit, fleet envelopes | NEW endpoint — never extend `/account-status/sync` (BC-1) |

---

## 3. Production Gap Analysis + Requirements

### 3.1 Production Gap Analysis (severity + effort-to-close + impact-if-unaddressed)

Per the gap-minimization discipline: every gap carries a severity, an effort estimate, and the impact if
left unaddressed. **Two gaps are CRITICAL** — which is why the overall verdict is CONDITIONAL GO, never
unconditional GO (§7).

| ID | Gap | Prototype state | Production requirement | Severity | Effort | Impact if unaddressed |
|----|-----|-----------------|------------------------|----------|--------|-----------------------|
| G1 | Offline fixture → live Asana read | Hardcoded options | `CustomFieldsClient.get → .enum_options`; creds via AWS Secrets Manager `autom8y/asana/asana-pat`; flag-gated | HIGH | 0.5d + cred wiring | Contract has no real input; feature inert |
| G2 | SQLite → real `autom8y-data` store; **DB engine UNRESOLVED** | In-memory SQLite | Real `verticals` store; engine determines `ON CONFLICT` vs `ON DUPLICATE KEY UPDATE` + lock primitive | **CRITICAL** | 0.25d to resolve EC-1 + 1.5d store | Wrong upsert syntax → build fails; wrong lock → concurrency corruption |
| G3 | Hardcoded coverage keys → real query | Fixture frozenset | Cross-table query unioning `asset_verticals` + `campaigns` (int FK) + `offers.category` (string FK) | HIGH | 1d | Missing `offers.category` clause → silent orphan hazard (RR4) |
| G4 | No transport | None | `push_vocab_to_data_service()` + S2S JWT (reuse `_push_to_data_service`) | MEDIUM | 0.5d | No cross-service delivery |
| G5 | No consumer endpoint | None | NEW `POST /api/v1/vocabularies/sync`, `extra="forbid"`, S2S, rate-limit, envelopes | HIGH | 1d | Nowhere to land; extending account-status is BREAKING (BC-1) |
| G6 | No `vocab_upsert` store | Fixture upsert | Additive-upsert store method (NOT `snapshot_replace`), keyed on `vertical_key` | **CRITICAL** | 1.5d | `snapshot_replace` orphans 43,057 FK rows (BC-2) — the one Medium-confidence component |
| G7 | No drift observer | None | WARN-only drift observer (asana-live vs data-side; name-collision; disabled-but-referenced) | MEDIUM | 0.5d | Drift invisible; ship-dark risk (R7) |
| G8 | `print()` → structured logging | `print()` | `structlog` JSON + publish-count canary metric | LOW | trivial | No observability; ship-dark undetectable |
| G9 | Concurrency + name-collision untested | Single-writer SQLite | Transaction-scoped advisory lock per `field_key` + name-uniqueness guard (`vertical_name` unique=True) | HIGH | 1d + staging | Race on overlapping syncs; unique-violation crash on `UPDATE SET name` (RR1) |
| G10 | No first-sync reconciliation | Clean fixture | Read-only dry-run classifying MATCH / INSERT-CANDIDATE / ORPHAN-RISK; refuse first sync on ORPHAN-RISK | HIGH | 1d | First publish inserts duplicates or strands a referenced key (RR3) |
| G11 | Disabled-option policy unresolved | `enabled=True` only | Policy: disabled = PRESENT-but-INACTIVE, never DELETE; carry `enabled` envelope-only for pilot | MEDIUM | policy decision | Operator-judgment gap; staleness or wrong refusal (RR2) |
| G12 | schema-discovery re-point | Not wired | Wire `values_source:'asana_configured'` (`resolver_schema.py:366`); verify consumer-compat first | MEDIUM | 0.5d + compat gate | Discovery route keeps serving hardcoded copy; 2x effort risk if consumers depend on shape |
| G13 | **No production telos / frame** | n/a (spike) | `/frame` + `.know/telos/dyn-enum-contract.md` (user-sovereign) — the 10x-dev entry gate | HIGH (process) | user action | No verification-realized gate; initiative cannot close honestly (EC-3) |

**Total build effort**: ~6.5 person-days (matches `INTEGRATE-dyn-enum-contract.md:259`), PLUS sprint-0
entry-criteria resolution (§5) which is gating, not additive coding.

### 3.2 Requirements Translation (functional + non-functional, each with a testable acceptance criterion)

**The three build-time compose-up LOCK decisions** (FR-001, FR-002, FR-003) are non-negotiable: they are
what let the per-instance contract compose UP to the DEFER-1 registry at cardinality 1→N *without a rewrite*
(`MOONSHOT-dyn-enum-contract.md:275-288`). Omitting them does not break the pilot — it silently forecloses
the registry door, which is the expensive-to-retrofit regret.

#### Functional Requirements

- **[FR-001] Generic vocab endpoint (LOCK #1 + #2).** A NEW consumer endpoint `POST /api/v1/vocabularies/sync`
  (generic plural path, NEVER `/verticals/sync`), request body carrying a `field_key` discriminator with
  value `"vertical"`, `model_config = {"extra": "forbid"}`, S2S JWT, rate-limit, fleet OpenAPI envelopes.
  - *Acceptance*: endpoint resolves at the generic plural path; a request with `field_key="vertical"` is
    accepted; an unknown top-level field is rejected 422; the endpoint is NOT a modification of
    `/account-status/sync` (BC-1 — `_account_status_sync.py:67,102` `extra="forbid"` untouched).
- **[FR-002] NAME-keying (LOCK #3).** The cross-service / persisted key is `normalize(option.name) →
  vertical_key`; `enum_option.gid` and `vertical_id` are local handles only and never appear in the contract key.
  - *Acceptance*: round-trip test — an option name with whitespace/case variance maps to the same
    `vertical_key` on producer and consumer; no `gid`/`vertical_id` is persisted as the key. (Spike-PROVEN
    feasible: `canary1_fk_parent.py:49-50`, `PROTO-dyn-enum-contract.md:321-324`.)
- **[FR-003] Additive-upsert store, DELETE-forbidden.** New `vocab_upsert()` method: INSERT new keys,
  UPDATE name/enabled on existing keys, NEVER DELETE; keyed on `vertical_key`.
  - *Acceptance*: staging test on a real `verticals`-shaped table with FK children — existing `id`s
    preserved, a new key inserted without collision, all `campaigns`/`asset_verticals`/`offers` references
    still resolve post-upsert; no code path issues a DELETE against `verticals`. (Mechanism spike-PROVEN:
    `canary1_fk_parent.py:182-201`, `PROTO-dyn-enum-contract.md:152`.)
- **[FR-004] Referential-coverage hard-refuse guard.** Replace the leaf-calibrated empty guard
  (`gid_push.py:514-519`) **for the vocab path only**: REFUSE+ALERT on empty `enum_options`; REFUSE+ALERT
  when incoming options are missing ANY FK-referenced `vertical_key`; PASS the healthy full set.
  - *Acceptance*: empty read → refusal + alert (not no-op, not delete); a truncated read missing an
    FK-referenced key → refusal + alert; healthy full set → publish; the coverage query unions all THREE
    FK edges including the `offers.category` string-edge. (Mechanism spike-PROVEN: `canary2_empty_publish.py:134-190`,
    `PROTO-dyn-enum-contract.md:281`.)
- **[FR-005] Live Asana `enum_options` source-read.** Producer reads `CustomFieldsClient.get(vertical_cf_gid).enum_options`
  (model `custom_field.py:113`), NOT the hardcoded `SEMANTIC_ANNOTATIONS.valid_values`; credentials via AWS
  Secrets Manager `autom8y/asana/asana-pat`; gated behind a feature flag (pattern: `gid_push.py:491`).
  - *Acceptance*: with the flag off the push no-ops cleanly; with the flag on and valid creds the producer
    projects a name-keyed snapshot from the live option-set; a deploy-gate assertion confirms the first real
    publish lands (anti ship-dark, R7).
- **[FR-006] Drift observer — WARN, never codegen.** Divergence (asana-live vs data-side; name-collision;
  disabled-but-referenced) emits WARN + metric only; ZERO auto-mutation; no schema codegen-from-model; no
  phantom-mint.
  - *Acceptance*: a forced divergence fixture emits a WARN + metric and mutates nothing; no code path
    auto-generates the `Vertical(Enum)` or the data-side table from a model (ADR-S4-001 one-way door,
    `.know/telos/gfr-dynvocab.md:78`).
- **[FR-007] Name-uniqueness collision guard.** On the UPDATE path, update `name` only when it does not
  collide with another row's `name`; a name-collision is a per-row DRIFT WARN + refuse-the-row (not the batch).
  - *Acceptance*: a fixture with two options normalizing to a colliding `vertical_name` produces a WARN +
    single-row refusal and no unique-constraint crash; `verticals.vertical_name` `unique=True`
    (`_platform.py:147`) is honored.
- **[FR-008] First-sync reconciliation dry-run (per `field_key`).** A read-only dry-run classifies each
  Asana option into MATCH / INSERT-CANDIDATE / ORPHAN-RISK against the existing `verticals.key` set; the
  first real sync is REFUSED if any ORPHAN-RISK key exists; emits a reconciliation report; mutates nothing.
  - *Acceptance*: a drift fixture (an existing FK-referenced key that no Asana option normalizes to) yields
    ORPHAN-RISK and refuses the first sync; a clean fixture passes; the dry-run writes no rows.
- **[FR-009] schema-discovery re-point.** Wire the `values_source:'asana_configured'` path
  (`resolver_schema.py:366`) to serve live `enum_options`; reversible config flip; consumer-compat verified
  before flipping.
  - *Acceptance*: with the flip on, `GET /{entity}/schema/enums/{field}` returns `values_source:'asana_configured'`
    sourced from live options; a documented consumer-compat check passes before the flip is enabled.

#### Non-Functional Requirements

- **[NFR-001] Concurrency — single-writer-per-`field_key`.** Wrap `vocab_upsert` for a `field_key` in a
  transaction-scoped advisory lock (`pg_advisory_xact_lock(hashtext('vocab:'||field_key))` on Postgres /
  `GET_LOCK('vocab:'||field_key)` on MySQL — engine TBD by EC-1).
  - *Acceptance*: two overlapping same-`field_key` syncs serialize; different `field_key`s and readers are
    not blocked; the lock releases at transaction end (no deadlock on a crashed sync). [UV-P: staging test, RR1]
- **[NFR-002] Idempotency.** The upsert is no-op-suppressing: `DO UPDATE SET name=excluded.name WHERE name
  IS DISTINCT FROM excluded.name`.
  - *Acceptance*: re-running an identical publish touches zero rows.
- **[NFR-003] Transport security.** S2S JWT (`Depends(verify_jwt)`), `@limiter.limit`, and `x-fleet-idempotency`
  / `x-fleet-cross-service-refs` envelopes carried on the new endpoint.
  - *Acceptance*: the endpoint rejects unauthenticated calls; rate-limit applies; envelopes present in the
    OpenAPI spec (parity with `account_status.py:41,66-70,85`).
- **[NFR-004] Observability + anti-ship-dark.** Structured JSON logging (no `print()`), a publish-count
  canary metric, and a deploy-gate assertion that the first real publish lands.
  - *Acceptance*: refusals and publishes emit structured events; the publish-count metric is queryable; the
    deploy gate fails if the flag is present but no publish ever fires (HD-4 / R7).
- **[NFR-005] Performance.** The coverage query is ~1 DB round-trip per 4h cycle; coverage arithmetic is O(n)
  on ~10-55 options.
  - *Acceptance*: coverage check runs pre-publish; no measurable contention given the read-heavy
    `VerticalService` (`services/vertical.py:7`) and the 4h cadence.

### 3.3 Non-Negotiable Constraints (what MUST NOT change — preserve list)

These are as load-bearing as the requirements. Each carries the WHY tied to a prototype/prior validation.
A receiving-rite change to any of these breaks the validated hypothesis.

| ID | Constraint | WHY (validation reference) |
|----|------------|----------------------------|
| CON-001 | Endpoint path is generic `/api/v1/vocabularies/sync`, NEVER `/verticals/sync` | The compose-up seam to the DEFER-1 registry; vertical-specific path forecloses it (`MOONSHOT-dyn-enum-contract.md:279`) |
| CON-002 | `field_key` discriminator present from row one (value `"vertical"`) | Adding a 2nd vocabulary becomes a new `field_key` value, not a schema change (`MOONSHOT-dyn-enum-contract.md:281`) |
| CON-003 | NAME-keying — never key cross-service on `enum_option.gid` or `vertical_id` | gid is per-workspace/opaque; `vertical_id` is FK-referenced and must never be reassigned (`.know/telos/gfr-dynvocab.md:47`; `INTEGRATE-dyn-enum-contract.md:128`) |
| CON-004 | Additive-only / DELETE-forbidden on `verticals` | FK-parent; DELETE orphans 43,057 `asset_verticals` rows (`canary1_fk_parent.py:389-393`; `_advertising.py:326`; `services/vertical.py:9`) |
| CON-005 | Drift-gate-not-codegen (ADR-S4-001 one-way door) | Codegen-from-model is the legacy `_missing_` auto-mint anti-pattern being ESCAPED (`.know/telos/gfr-dynvocab.md:78`) |
| CON-006 | FROZEN cf-type set; option-set is a sidecar to `enum`/`multi_enum`, never a 7th type | Preserves gfr-dynvocab's FROZEN contract surface (`.know/telos/gfr-dynvocab.md:47`; `SCOUT-dyn-enum-contract.md:108`) |
| CON-007 | Strictly-additive to the gfr 105-test certified spine (CERT-1 / CERT-3 inviolable) | The certified identity spine must not regress (`.know/telos/gfr-dynvocab.md:51,79`) |
| CON-008 | Asana live `enum_options` = single upstream source-of-record; data ingests one-way | Resolves truth-ownership; matches the warmer-push direction (`INTEGRATE-dyn-enum-contract.md:142`) |
| CON-009 | Legacy `Vertical(Enum)` / `_missing_` cascade stays NON-CANONICAL — never extended | The phantom-campaign auto-mint is the thing being escaped; 0 import edges proven (`INTEGRATE-dyn-enum-contract.md:160`) |
| CON-010 | NEW endpoint — never extend `/account-status/sync` | `extra="forbid"` makes a new field BREAKING until both sides deploy (BC-1; `_account_status_sync.py:67,102`) |

---

## 4. Technical Risk Assessment

The 4 PROTO residual risks (`PROTO-dyn-enum-contract.md:376-395`) carried forward, PLUS the moonshot RR
sharpenings (`MOONSHOT-dyn-enum-contract.md:300-399`) — notably the NEW `verticals.vertical_name`
`unique=True` collision finding (`_platform.py:147`). Each: probability + impact + mitigation the build MUST
implement + residual after mitigation.

| ID | Risk | Prob | Impact | Mitigation the build MUST implement | Residual |
|----|------|------|--------|-------------------------------------|----------|
| TR-1 | **Concurrent upsert race** on overlapping same-`field_key` syncs (manual re-trigger races the 4h cron) | LOW | HIGH | NFR-001 transaction-scoped advisory lock per `field_key`; no-op-suppressing upsert (NFR-002) | UV-P until staging test (RR1); low by construction (read-heavy service) |
| TR-2 | **`vertical_name` unique-constraint collision** on the `UPDATE SET name` path (rename collides, or two options normalize to same key/different names) | MEDIUM | MEDIUM | FR-007 name-uniqueness guard: update name only when non-colliding; collision → per-row WARN + refuse-the-row | Structural; mitigated by FR-007; never auto-resolve (ADR-S4-001) |
| TR-3 | **First-sync key-mismatch** — existing `verticals.key` drifted from Asana option NAME; naive ingest inserts a duplicate or strands a referenced key | MEDIUM | HIGH | FR-008 read-only reconciliation dry-run; refuse first sync on any ORPHAN-RISK; human reconciles in Asana (SoR) before automation | UV-P until staging dry-run against live Asana payload (RR3) |
| TR-4 | **`offers.category` string-edge omitted** from the coverage query (string FK to `verticals.key`, structurally distinct from the int `vertical_id` edges) | MEDIUM | HIGH | FR-004 coverage query MUST union the `EXISTS(SELECT 1 FROM offers o WHERE o.category=v.key)` clause | None structural once the third clause is present (RR4; `_platform.py:162`) |
| TR-5 | **Empty/truncated publish blast radius** on the FK-parent (leaf guard silently no-ops) | MED→HIGH-likelihood | HIGH | FR-004 hard-refuse (empty + referential-coverage); additive-upsert removes the DELETE direction entirely | Spike-PROVEN mitigated (`canary2_empty_publish.py:328-332`); residual = the production coverage query correctness |
| TR-6 | **Ship-dark via feature flag** — vocab push behind a flag that never flips (silent non-function) | MEDIUM | MEDIUM | NFR-004 publish-count canary metric + deploy-gate assertion the first publish lands; do not declare done on flag-present alone | Observable once metric + gate exist (HD-4/R7) |
| TR-7 | **DB-engine syntax/lock mismatch** — building `ON CONFLICT` against a MySQL engine (or vice-versa) | MEDIUM | HIGH | EC-1: resolve the engine before build; select upsert syntax + lock primitive accordingly | Eliminated once EC-1 resolved; a build blocker until then |
| TR-8 | **`_missing_` auto-mint contamination** (legacy phantom-campaign side-effect) | NEGLIGIBLE | HIGH | CON-009 + producer reads via `CustomFieldsClient`, never `VerticalModel`; 0 import edges proven | Quarantine holds while producer never traverses the monorepo cf-adapter (`INTEGRATE-dyn-enum-contract.md:160`) |
| TR-9 | **Disabled-option semantics** — operator disables an FK-referenced option | MEDIUM | MEDIUM | RR2 policy: disabled = PRESENT-but-INACTIVE, counts toward coverage, never propagates as DELETE; carry `enabled` envelope-only for pilot | Operator-judgment; persist `active` column deferred to S1 |

**DORA framing** [PE:SRC-001 Forsgren, Humble & Kim 2018] [MODERATE | 0.77 @ 2026-03-31]: the contract is
neutral-to-positive on the four key metrics — it *reduces* change-failure-rate (removes the 4-6-source
hand-reconciliation that produced the `KeyError: 'asset_id'` class) and *reduces* MTTR (typed
hard-refuse + integrity check vs cryptic `KeyError`). No metric is degraded; the DORA production-readiness
gate is satisfiable. [PLATFORM-HEURISTIC: DORA gating threshold is operational convention.]

---

## 5. Build Entry-Criteria / Blockers (sprint-0 — resolve or escalate BEFORE building)

These are the gates a 10x-dev sprint-0 architect MUST settle before code. They are conditions on the GO
verdict (§7), not optional polish.

- **[EC-1] CRITICAL — `verticals` DB engine (MySQL vs PostgreSQL) is UNRESOLVED.** The priors disagree:
  `INTEGRATE-dyn-enum-contract.md:42` calls account_status a "MySQL leaf"; `PROTO-dyn-enum-contract.md:293`
  references "PostgreSQL staging"; `MOONSHOT-dyn-enum-contract.md:78` flags the conflict explicitly. The engine
  determines **upsert syntax** (`INSERT ... ON CONFLICT (key) DO UPDATE` vs `INSERT ... ON DUPLICATE KEY
  UPDATE`) AND the **lock primitive** (`pg_advisory_xact_lock` vs `GET_LOCK`). *Resolution*: the sprint-0
  architect inspects the autom8y-data migration/engine config and settles this as a design-lock before
  building `vocab_upsert`. Until resolved, FR-003 and NFR-001 cannot be implemented correctly. [UV-P:
  verticals-table DB engine | METHOD: inspect migration/engine config | REASON: priors disagree; load-bearing]
- **[EC-2] HIGH — Live-Asana credential path is operator-shell-only.** The live `enum_options` read requires
  the Asana PAT from AWS Secrets Manager `autom8y/asana/asana-pat` (per gfr-dynvocab credential topology).
  This credential is available in the operator's shell context, not ambiently in CI/build. *Resolution*:
  confirm the production runtime (the cache-warmer process) has the secret-fetch path; do not assume CI parity.
  Escalate to the operator if the warmer runtime lacks the scope. [UNATTESTED — DEFER-POST-HANDOFF: live
  credential path verification]
- **[EC-3] HIGH (process) — No production telos exists; `/frame` + telos declaration is USER-SOVEREIGN.**
  No `.know/telos/dyn-enum-contract.md` exists (verified — absent from `.know/telos/`). This is a SPIKE; the
  initiative has no named user-visible outcome, no verification-realized definition, no rite-disjoint
  attester, no deadline. Per `telos-integrity-ref` §3 Gate A, the 10x-dev entry gate is a `/frame` that
  produces `.know/telos/dyn-enum-contract.md` with the §2 schema fields populated by the USER. **Tech-transfer
  does NOT author this** (user-sovereign declaration is the load-bearing semantic). *Resolution*: surface to
  the user/10x-dev Potnia as the inception gate before any build session.
- **[EC-4] MEDIUM — schema-discovery consumer-compat gate (M1).** Before re-pointing `#5`
  `SEMANTIC_ANNOTATIONS.valid_values` to live options (FR-009), verify no downstream consumer depends on the
  hardcoded `SEMANTIC_ANNOTATIONS` *shape* — `INTEGRATE-dyn-enum-contract.md:251` flags a 2x-effort risk if they do.

---

## 6. DEFER-1 Boundary (the registry is OUT of build scope)

**In build scope (this handoff)**: the per-instance `vertical` vocab-sync contract (moonshot M0–M1; ~6.5
person-days), built **compose-up-ready** via the three locked decisions (FR-001/002/003).

**OUT of build scope (DEFER)**: the fleet cf-contract REGISTRY — the moonshot Option F full form (generic
`cf_vocabularies` carrier at cardinality N + declarative `cf-contracts/*.yaml` coherence layer +
per-`field_key` policy). The registry is a **one-way door once 2+ services bind** and stays DEFER behind an
explicit trigger.

**DEFER-1 N≥3 escalation trigger** (restated verbatim from `MOONSHOT-dyn-enum-contract.md:468-475`,
`:526`): a 2nd option-set vocabulary binds `/vocabularies/sync` (a 2nd `field_key`) **AND** a 3rd consuming
service requests the vocabulary (e.g., `scheduling-stratum` materializes, or a reporting service binds).
The conjunction is the N≥3 condition. On trigger, escalate to **user/leadership** (strategic bet + resource
commitment) AND back to **technology-scout** (fresh build-vs-buy: central service vs event stream vs
declarative coherence layer). The per-instance build is the reversible waypoint (B at cardinality 1) that
keeps the door open without speculative investment — generalize to F *without a rewrite* when the trigger
fires.

The receiving rite MUST NOT build the registry as part of this handoff. Building it pre-trigger is the
Technology-Driven-Architecture anti-pattern the moonshot explicitly guards (`MOONSHOT-dyn-enum-contract.md:290-296`).

---

## 7. Recommendation — CONDITIONAL GO

**Verdict: CONDITIONAL GO** for productionization of the per-instance additive-upsert vocab-sync contract.

**Why GO (not NO-GO)**: the two load-bearing mechanism uncertainties are spike-PROVEN with two-sided
discriminating canaries (`canary1_fk_parent.py:389-393`, `canary2_empty_publish.py:328-332`); the build
composes a production idiom the team operates at N≥2; zero new third-party dependency; every migration phase
M0–M3 is reversible; no one-way door is crossed by the pilot.

**Why CONDITIONAL (not unconditional GO)**: two gaps are CRITICAL severity (G2 DB-engine UNRESOLVED, G6
`vocab_upsert` genuinely-new code) and three entry-criteria are unmet (EC-1 engine, EC-2 credential path,
EC-3 user-sovereign telos/frame). Per the gap-minimization discipline, an unconditional GO with an
unresolved CRITICAL gap is forbidden.

**The GO is contingent on, in sprint-0 order**:
1. **EC-1** resolved — DB engine settled (upsert syntax + lock primitive locked).
2. **EC-3** satisfied — user authors `/frame` + `.know/telos/dyn-enum-contract.md` (inception gate; user-sovereign).
3. **EC-2** confirmed — live-Asana credential path available to the warmer runtime.
4. The three compose-up LOCK decisions (FR-001/002/003) held — non-negotiable at build time.
5. The coverage query includes the `offers.category` string-edge (FR-004 / TR-4) from day one.

**Adoption J-curve** [PE:SRC-007 DORA team 2024] [MODERATE | 0.77 @ 2026-03-31]: SHALLOW. The team operates
the snapshot-sync idiom in production (N≥2: account-status + gid-mappings), so the adoption dip is confined
to the two genuinely-new surfaces (the `vocab_upsert` store + the referential-coverage guard). **Recovery
criteria**: M1/M3 convergence — ≥30 days of clean sync cycles with the drift observer showing zero
unresolved divergence (`MOONSHOT-dyn-enum-contract.md:457-464`). **SPACE** [PE:SRC-004 Forsgren et al. 2021]
[MODERATE | 0.77 @ 2026-03-31]: team-readiness HIGH (known idiom); no developer-satisfaction/flow regression
expected — the new code is a single store method against a familiar substrate.

**Target rite**: 10x-dev. **Handoff type**: `implementation` (Research → Dev; the per-instance contract is
the build subject, artifacts are design references, GO supports immediate implementation conditioned on
sprint-0). NOT `strategic_evaluation` — the only strategic-bet item (the registry) is explicitly DEFER and
out of build scope, so there is no go/no-go for strategy to make here.

---

## 8. TRANSFER → HANDOFF field mapping

| TRANSFER section | HANDOFF destination |
|------------------|---------------------|
| §3.1 Gap Analysis | Item `production_gaps` + `design_references` |
| §3.2 Requirements | Item `acceptance_criteria` |
| §3.3 Non-Negotiable Constraints | Item `constraints` / Notes for Target Rite |
| §4 Risk Assessment | Item `risks` / Notes for Target Rite |
| §5 Entry-Criteria | Item `entry_criteria` (blocking) / Notes |
| §6 DEFER-1 boundary | Notes for Target Rite (watch item) |
| §7 Recommendation | `priority` + routing + verdict |

---

## Source Anchors / Receipts (platform-internal, `{path}:{line}`)

**Spike-PROVEN (this initiative's own canaries + captured output):**
- `.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:146-174` (snapshot_replace), `:182-201` (additive_upsert), `:389-393` (two-sided verdict)
- `.sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py:108-126` (leaf guard), `:134-190` (hard-refuse guard), `:328-332` (two-sided verdict)
- `.ledge/spikes/PROTO-dyn-enum-contract.md:126,152,164,227,249,281` — captured canary verdicts

**HARD constraints (gfr-dynvocab telos):**
- `.know/telos/gfr-dynvocab.md:47` (NAME-keying + FROZEN cf-type set), `:51,79` (105-test certified spine), `:78` (ADR-S4-001 drift-gate-not-codegen)

**Production primitives (REFERENCE — the build targets; NOT YET BUILT against):**
- `src/autom8_asana/services/gid_push.py:491` (feature flag), `:514-519` (leaf empty guard), `:528` (push helper)
- `src/autom8_asana/models/custom_field.py:35` (`enabled`), `:113` (`enum_options`), `:3` (`extra="ignore"`)
- `src/autom8_asana/clients/custom_fields.py:442,529` (create/update enum option)
- `src/autom8_asana/api/routes/resolver_schema.py:366,449,473` (`asana_configured` door, hardcoded valid_values)
- `autom8y-data: api/routes/account_status.py:41,50,85,108,133` (S2S, /sync, rate-limit, integrity, snapshot_replace)
- `autom8y-data: api/services/account_status_store.py:82-143` (leaf snapshot-replace)
- `autom8y-data: api/data_service_models/_account_status_sync.py:44,67,102` (`vertical:str` leak, `extra="forbid"`)
- `autom8y-data: core/models/_platform.py:145-147` (`verticals{id,key,name}`, `vertical_name` unique), `:162` (`offers.category`→`verticals.key`)
- `autom8y-data: core/models/_advertising.py:80,326` (campaigns/asset_verticals FK; 43,057 rows)
- `autom8y-data: services/vertical.py:7,9-10,34-43,48` (read-heavy, no delete/update, caller owns txn, IMMUTABLE)

## Evidence Grade

`[STRUCTURAL | MODERATE]` — ceiling, not floor. Self-referential (packaging the fleet's own spike from
inside) caps at MODERATE per `self-ref-evidence-grade-rule`; rnd-dk literature caps at MODERATE. The spike's
GO is **feasibility-grade**; the production GO is **CONDITIONAL** and explicitly partitions spike-PROVEN
(§0.2) from PROJECTED/UV-P (the entire production contract). The realization predicate belongs to the 10x-dev
build + a rite-disjoint attester against a user-authored telos (EC-3), not to this transfer pass.

## Artifact Verification Table

| Artifact | Path | Status |
|----------|------|--------|
| This TRANSFER | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/TRANSFER-dyn-enum-contract.md` | Written (this file) |
| HANDOFF (to 10x-dev) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/handoffs/HANDOFF-rnd-to-10x-dyn-enum-contract-2026-06-30.md` | Authored (companion) |
| Canary 1 (spike-PROVEN) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py` | Read + verified (exists, two-sided verdict `:389-393`) |
| Canary 2 (spike-PROVEN) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py` | Read + verified (exists, two-sided verdict `:328-332`) |
| Upstream — scout | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/SCOUT-dyn-enum-contract.md` | Read (Wave 1) |
| Upstream — integration | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/INTEGRATE-dyn-enum-contract.md` | Read (Wave 2) |
| Upstream — prototype | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/PROTO-dyn-enum-contract.md` | Read (Wave 3) |
| Upstream — moonshot | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/MOONSHOT-dyn-enum-contract.md` | Read (Wave 4) |
| HARD-constraint source | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/telos/gfr-dynvocab.md` | Verified present (`:47,51,78,79`) |
| Production telos (EC-3) | `.know/telos/dyn-enum-contract.md` | **ABSENT** — user-sovereign `/frame` is the 10x-dev entry gate |
