---
type: handoff
artifact_subtype: arch-to-10x
initiative: dyn-enum-contract
handoff_type: arch-validated-design
from_rite: arch
to_rite: 10x-dev
from_station: remediation-planner (sprint-4 of 5)
created: 2026-06-30
status: proposed
rung: authored        # G-RUNG: arch reaches "authored" / validated-design ONLY
ready_for_downstream: true    # arch-adversary sprint-5 = PASS-WITH-CONDITIONS (2026-07-01, sha256:6af7b54f); crossing still gated on Gate-A countersign (operator-sovereign, §5)
evidence_grade_ceiling: "MODERATE — self-referential authorship ceiling; see §G-CRITIC"
producer_truth_anchor: "autom8y-asana origin/main (ca28251d)"
consumer_truth_anchor: "autom8y-data HEAD (92d3606d, branch main)"
---

# HANDOFF: arch → 10x-dev — dyn-enum-contract (2026-06-30)

> **Status**: `proposed` / `authored` — arch-adversary sprint-5 cleared this HANDOFF
> **PASS-WITH-CONDITIONS** (2026-07-01); `ready_for_downstream: true`. See §14.
>
> **Who reads this first**: The 10x-dev build owner. The SOLE remaining blocker is Gate-A
> (operator countersigns the telos, §5). Do NOT start the build until Gate-A is CLOSED —
> `ready_for_downstream: true` is arch's attestation, NOT authorization to cross the seam.

---

## §1 · Handoff Summary

The arch rite has completed all 5 sprints for the `dyn-enum-contract` initiative:
topology-inventory (S1) → dependency-map (S2) → architecture-assessment (S3) →
remediation-planning (S4, this handoff) → arch-adversary gate (S5 — PASS-WITH-CONDITIONS, §14).

**What the arch rite validated**: One typed, additive, FK-safe sync contract carrying Asana
enum-option-set changes into `autom8y-data.verticals`. The design is conditionally viable with
7 mandatory architectural corrections (see §2).

**What the 10x-dev build owns**: Everything from authored→proven. Producer PR (sprint-1) +
consumer PR (sprint-2) + coherence checks (sprint-3) + live reconciliation (sprint-4) +
rite-disjoint attestation hand-off to review rite (sprint-5 of the BUILD shape, distinct from
this arch sprint-5).

**Hard prerequisites before build starts**:
1. Gate-A CLOSED — operator countersigns `.know/telos/dyn-enum-contract.md` (currently OPEN) — **SOLE REMAINING BLOCKER**
2. arch-adversary sprint-5 — ✅ SATISFIED (PASS-WITH-CONDITIONS, `ready_for_downstream: true`; §14)
3. PT-02 operator fork resolved — see §11 + §14/C3. NOTE: consumer rite is UNSETTLED (topology read `dre`; live `autom8y-data/.knossos/ACTIVE_RITE` reads `eunomia`) → settle at the PT-01→PT-02 boundary, not at this producer seam

---

## §2 · Validated Design with 7 Arch Corrections

Each correction is mandatory. "Accepted from rnd" means the rnd/frame framing was correct;
"CORRECTION" means the arch rite overrules the rnd framing.

### Correction 1 — Route through `VerticalService.create` [ARCHITECTURAL CORRECTION]

**Rnd framing**: "G6 CRITICAL new component — vocab_upsert store / VocabUpsertStore class."
**Arch verdict**: MIS-ALIGNED. The bespoke `vocab_upsert` store manufactures a second-writer
condition (violating single-writer invariant at `services/vertical.py:212`) and bypasses the
no-delete invariant surface (`services/vertical.py:9`).

**Correct design**: Extend `VerticalService.create` in
`autom8y-data/src/autom8_data/services/vertical.py` with an upsert method:
- Create-if-absent keyed on `vertical_key` (UNIQUE at `_platform.py:146`)
- Update-name-when-safe (guarded against dual-unique collision — see Correction 3)
- NEVER DELETE (already the service's stated invariant at `:9`)

Route `/api/v1/vocabularies/sync` THROUGH this extended service. NOT a bespoke store class.

**Receipt**: [C] `services/vertical.py:212` (sole canonical writer); [C]
`services/vertical.py:9` (no-delete invariant enforced here, proto at
`proto/autom8/data/v1/__init__.py:667`, gRPC at `grpc/handlers/vertical.py:128`).

### Correction 2 — EC-1 SETTLED = MySQL; shape-B is `INSERT…ON DUPLICATE KEY UPDATE` + `GET_LOCK`/`RELEASE_LOCK`

**Rnd framing**: "EC-1 CRITICAL UNRESOLVED — priors disagree (INTEGRATE MySQL / PROTO
PostgreSQL)."
**Arch verdict**: SETTLED by direct inspection of `autom8y-data` at HEAD. MySQL confirmed by
7 live receipts (see §3). The PROTO PostgreSQL canary (`ON CONFLICT`, `pg_advisory_xact_lock`)
is REFUTED.

**Shape-B implication for the build**:
- Upsert syntax: `INSERT INTO verticals ... ON DUPLICATE KEY UPDATE name=VALUES(name)` (NOT `ON CONFLICT(key) DO UPDATE`)
- Lock syntax: `SELECT GET_LOCK('verticals_vocab_sync_{field_key}', 30)` / `SELECT RELEASE_LOCK(...)` MySQL named-lock (0 hits in consumer tree today — 10x-dev introduces this in sprint-2; LIVE EXEMPLAR at `api/services/forwarding_binding_store.py:155/:218/:252/:315` — `INSERT … ON DUPLICATE KEY UPDATE` CONFIRMED LIVE in the consumer)

This is a SETTLED FACT from arch inspection, not a design choice for the build to re-open.

### Correction 3 — account-status/sync is a FALSE-FRIEND for write semantics (shape YES / semantics NO)

**Rnd framing**: "Use account-status/sync as the template."
**Arch verdict**: PARTIAL — the typed-envelope SHAPE is the correct template; the
SNAPSHOT-REPLACE SEMANTICS are catastrophically wrong and MUST NOT be copied.

**Correct use boundary**:
- REUSE from account-status: request/response envelope shape, S2S JWT auth, rate-limit config,
  fleet error envelopes. Shape source: `api/data_service_models/_account_status_sync.py:70/:113`.
- DO NOT COPY from account-status: `DELETE FROM account_status WHERE source='section_classifier'`
  at `_platform.py:497-498`. This snapshot-replace is scoped to `account_status.source` — a
  column `verticals` does NOT have (`_platform.py:142-147` = id/key/name only). An unconditional
  DELETE wipes the FK-parent hub.

**Receipt**: [C] `_platform.py:497-498` (the DELETE to never copy); [C] `_platform.py:142-147`
(verticals schema — no source column present).

### Correction 4 — FK-parent SPOF cascade: defense = WRITE-PATH INTEGRITY (not hub decoupling)

**Rnd framing**: "HIGH-severity FK-parent SPOF; spike canary confirmed FK-safe additive-upsert."
**Arch verdict**: CONFIRMED severity. Correction: the actionable defense is WRITE-PATH
INTEGRITY (hard-refuse + additive-upsert + rename guard), NOT hub decoupling. Primary and
FALLBACK paths share the SAME parent with NO independent redundancy. DuckDB LEFT JOIN
produces silent corruption (no error raised) — the blast radius is fleet-wide.

**FK fan-in = ≥7 edges** (all active at HEAD):
- E1 `_advertising.py:80` — Campaign int FK PRIMARY
- E2 `_advertising.py:322/:326` — AssetVertical junction composite PK ~43K rows
- E3 `_platform.py:162` — Offer STRING FK (`category` column) — no DB-level RI enforcement
- E4 `_platform.py:72` — Business.default_vertical_id FALLBACK (table chiropractors)
- E5 `_platform.py:451` — Question.vertical_id (table questions)
- E6 `_platform.py:419` — Payment soft-ref/generated
- E7 `[sched] models/shared.py:48` — cross-repo scheduling shared-schema FK

**Join hub**: [C] `dimension_enrichment.py:144` (J1 PRIMARY) + `:166` (J2 FALLBACK, same parent,
NO independent redundancy) + [C] `analytics/core/infra/enrichment_views.py:152` (DuckDB
LEFT JOIN, 45 files, silent corruption path).

**Build implication**: implement referential-coverage HARD-REFUSE on the producer vocab path
(see Correction 5 below); additive-upsert DELETE-forbidden; first-sync ORPHAN-RISK dry-run.

### Correction 5 — Producer HARD-REFUSE on vocab path; coverage union MUST include the STRING FK edge

**Rnd framing**: "canary2 hard-refuse guard on empty publish" (PARTIALLY correct; needed
broader coverage).
**Arch verdict**: CORRECT direction; INADEQUATE calibration. The leaf guard at `gid_push.py:328`
and `:554` (`return True  # Nothing to push is not a failure`) is appropriate for gid-mappings
and account-status paths. For the vocab path, it must be REPLACED with a referential-coverage
HARD-REFUSE that covers all THREE FK edges:

- INT FK edges: [C] `_advertising.py:80` (campaigns) + [C] `_advertising.py:326` (asset_verticals ~43K)
- STRING FK edge: [C] `_platform.py:162` (Offer.category — no DB-level RI; orphan on rename is silent)

**Calibration**: Empty Asana read → HARD-REFUSE + ALERT (not "nothing to push is not a failure").
Truncated read (missing any FK-referenced key) → HARD-REFUSE + ALERT. The additive-upsert
already handles empty-WIPE via NO DELETE — the hard-refuse guards the truncated-rename residual
de-alignment of the STRING FK.

**Receipt (live empty-guard lines to REPLACE on vocab path only)**:
- [P] `services/gid_push.py:328` (call-path A leaf guard)
- [P] `services/gid_push.py:554` (call-path B leaf guard)

### Correction 6 — SDK model home for the typed contract (`autom8y-core`, `>=4.2.0,<5.0.0`)

**Rnd framing**: "Define typed models at the contract boundary."
**Arch verdict**: CORRECT principle; specify the locus. Home `VocabularySyncRequest` and
`VocabularySyncResponse` pydantic models ONCE in `autom8y-core` (the established cross-repo
model home at `data_intake.py:473` `VerticalsListResponse`). All 4 Python consumers carry
uniform pin `autom8y-core>=4.2.0,<5.0.0` (confirmed: [P]`:26`, [ads]`:21`, [sms]`:26`,
[sched]`:31`). Import in both repos from `autom8y_core`. No per-repo duplicate definitions.

**Why it matters**: If the model is defined twice, a schema change requires coordinated edits
in two repos — hidden release-coupling. The SDK typed conduit is the established precedent.

### Correction 7 — Live line-number anchors; flag surface is `gid_push.py:62` (NOT resolver_schema.py past EOF)

**Rnd/frame anchors that were stale** (corrected to `autom8y-asana origin/main ca28251d`):

| Stale (frame/spike) | Live (arch-validated, origin/main) | What it is |
|---------------------|-----------------------------------|------------|
| `resolver_schema.py:491` | `gid_push.py:62 GID_PUSH_ENABLED_ENV_VAR` | Feature flag env var |
| `resolver_schema.py:495` | `gid_push.py:95` | Feature flag gate (conditional read) |
| `gid_push.py:131` | `gid_push.py:163` | `_push_to_data_service()` helper entry |
| `gid_push.py:519` (ONE guard) | `gid_push.py:328` AND `gid_push.py:554` (TWO paths) | Leaf empty-guards (both paths) |
| `gid_push.py:351/:491` | `gid_push.py:375/:564` | Account-status envelope/endpoint refs |

Note: `resolver_schema.py` is 475 lines at origin/main. `:491` is past EOF. The feature flag
is governed by `gid_push.py:62` `GID_PUSH_ENABLED_ENV_VAR`. 10x-dev sprint-0 MUST re-verify
all anchors at the sprint-0 build HEAD (the sprint-0 architect re-verifies per telos
`code_verbatim_match: false` clause).

**FK fan-in correction**: Fan-in = ≥7 (spike enumerated 3; arch added [C] `_platform.py:72`
Business FALLBACK + `_platform.py:451` Question nullable). All 7 confirmed in dependency-map.

---

## §3 · EC-1 Verdict: MySQL (7 receipts + shape-B implication)

**Verdict**: SETTLED = MySQL. PostgreSQL canary REFUTED.

**7 live receipts** from `autom8y-data HEAD (92d3606d)`:

| Receipt | Location | What it confirms |
|---------|----------|-----------------|
| R1 | `core/config.py:217` | MySQL URL docstring: `MySQL URL (mysql+asyncmy://user:pass@host:port/db)` |
| R2 | `core/config.py:222` | `mysql+asyncmy://` URL normalization |
| R3 | `api/routes/read_only_deps.py:75/:77` | `url = f"mysql+asyncmy://..."` + `create_async_engine` |
| R4 | `api/routes/deps.py:129` | `_async_engine = create_async_engine(mysql+asyncmy://...)` |
| R5 | `services/base.py:387` | Tuple `("mysql+asyncmy://", "mysql+aiomysql://", "mysql://")` |
| R6 | `pyproject.toml:99` | `"pymysql>=1.1.0"  # Direct MySQL driver` |
| R7 | `docker-compose.override.yml:3/:29/:65` | `Dependencies: mysql` / `DB_HOST: mysql` |

**Shape-B live exemplar** (upsert — confirmed LIVE, NOT prospective):
`api/services/forwarding_binding_store.py:155/:218/:252/:315` —
`INSERT INTO ... ON DUPLICATE KEY UPDATE ...` (4 occurrences in the consumer)

**Shape-B prospective** (advisory lock — NOT yet in consumer, 10x-dev introduces):
`GET_LOCK('verticals_vocab_sync_vertical', 30)` / `RELEASE_LOCK(...)` [UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/lock-intro-sprint-2] MySQL named-lock primitive. PV-preflight confirmed grep → 0 hits on `GET_LOCK` in the consumer tree.

**The PROTO PostgreSQL canary syntax that MUST NOT appear in the sprint-2 build**:
- `ON CONFLICT(key) DO UPDATE SET name=EXCLUDED.name` — PostgreSQL only, not supported by MySQL
- `pg_advisory_xact_lock` / `pg_advisory_lock` — PostgreSQL only

---

## §4 · Carried Risk Map (R1–R8 + design risks) — RED→GREEN Acceptance Criteria

All 8 risks from the architecture-assessment, plus EC-1 and two design risks. Each carries its
severity, leverage score, and a falsifiable RED→GREEN acceptance criterion.

### R1 — FK-parent SPOF cascade [HIGH | leverage=1.67 | impact=5, effort=3]

**What**: Mis-keyed or orphaned vertical row → fleet-wide silent corruption via DuckDB LEFT
JOIN enrichment (45 files, `enrichment_views.py:152`). Primary (J1 `dimension_enrichment.py:144`)
and FALLBACK (J2 `:166`) share one parent; NO independent redundancy.

**Accepted trade-off**: Hub is the correct topology for a global reference dimension. Defense
is WRITE-PATH INTEGRITY, not hub decoupling.

**RED**: Any DELETE or INSERT of an unknown key on the vocab path reaches `verticals` without
passing through the referential-coverage hard-refuse guard.
**GREEN**: Hard-refuse fires on empty or truncated read; additive-upsert fires on healthy
full read; zero rows deleted from `verticals` by any vocab-sync operation. INT FK and STRING
FK coverage included in the refusal check.

### R2 — Empty/truncated-publish blast-radius [HIGH | leverage=2.5 | impact=5, effort=2]

**What**: An empty Asana read or a truncated read (missing FK-referenced keys) on the vocab
path could propagate silently or de-align the STRING FK.

**RED**: Empty Asana read reaches the data store (guard fires `return True` on vocab path, the
old leaf calibration). OR truncated read applies partial renames, de-aligning offers.category.
**GREEN**: Mock empty `enum_options` → HARD-REFUSE + ALERT (does NOT reach `gid_push.py:328/:554`
"nothing to push" on the vocab path). Mock truncated → HARD-REFUSE + ALERT. Mock healthy →
publish proceeds. Tested in producer unit tests.

### R3 — Dual-unique rename collision on UPDATE-name path [MOD-HIGH | leverage=2.0 | impact=4, effort=2]

**What**: `vertical_name` carries UNIQUE constraint (`_platform.py:147`). A naive `UPDATE SET
name=VALUES(name)` that collides → MySQL constraint exception. Three hazards: name collision,
name-swap A↔B, first-sync key-mismatch. This is net-new behavior (create-only today).

**RED**: Naive `ON DUPLICATE KEY UPDATE name=VALUES(name)` throws MySQL constraint violation
on rename collision, uncaught or silently skipped, leaving store stale or server-errored.
**GREEN**: Rename collision → per-row WARN + refuse-the-row (deterministic). Name-swap A↔B
→ two-phase update completes without error. First-sync mismatch → ORPHAN-RISK detected by
dry-run and live sync refused. Tested in consumer integration tests.

### R4 — STRING-FK fragility on key rename [MOD-HIGH | leverage=2.0 | impact=4, effort=2]

**What**: `Offer.vertical_key → verticals.key` is a STRING FK in the `category` column
(`_platform.py:162`). No DB-level referential integrity. Orphaned string does not raise an
FK violation — it silently stops resolving.

**RED**: Coverage union omits `_platform.py:162` STRING FK edge. A key rename proceeds,
orphaning Offer.category references. No alert fired.
**GREEN**: Coverage union includes the STRING FK edge (`Offer.category` count in the
union query). On rename, the hard-refuse fires if the old key is referenced. Tested in producer
unit tests with mock Offer.category join.

### R5 — Vocabulary fragmentation (4-conduit read-side) [MODERATE | leverage=0.6 | impact=3, effort=5]

**What**: 4-conduit read-side fragmentation: SDK typed conduit #1 (`data_intake.py:473`), ads
parallel `VerticalNormalizer` #2 (`creative_performance.py:90`), sms denormalized fields #3
(`models/conversation.py:169`), scheduling shared-FK #4 (`shared.py:48`). The write-seam
contract closes the producer gap but does not unify the read-side.

**ACCEPT-AS-IS for this scope**: DEFER-1 N<3 gate not fired; 4 consumers are fragmentation
evidence, NOT the trigger. Contract is neutral to read-side fragmentation; does not entrench;
does not collapse.

**DEFER-1 escalation trigger**: When a 2nd `field_key`-class vocabulary binds
`/vocabularies/sync` AND a 3rd consuming service materializes the vocabulary (N≥3 conjunction)
→ escalate to platform architecture + leadership. Do NOT build the registry pre-trigger
(one-way door).

**Routed**: CRR-002 to debt-triage for ads fragmentation characterization.

### R6 — Schema-drift release-coupling (if model duplicated per-repo) [LOW-MOD | leverage=1.5 | impact=3, effort=2]

**What**: Risk is conditional on implementation choice. If `VocabularySyncRequest`/`Response`
are defined independently in both repos, a schema change requires coordinated cross-repo edits.

**RED**: `VocabularySyncRequest` defined in both `autom8y-asana` and `autom8y-data` source trees.
**GREEN**: Single definition in `autom8y-core` SDK; both repos import from `autom8y_core`.
Verified by grep: no independent `VocabularySyncRequest` definition outside `autom8y-core`.

### R7 — First-sync ORPHAN-RISK key-mismatch [MODERATE | leverage=1.5 | impact=3, effort=2]

**What**: `vertical_key` is derived from Asana option NAME via normalization. If existing rows
were inserted with a different normalization scheme, the first sync creates parallel key rows
rather than matching existing FK parents.

**RED**: First live publish re-keys existing verticals → duplicate verticals rows → FK
fan-in inconsistency → silent enrichment corruption.
**GREEN**: Dry-run before first live publish classifies all Asana options as MATCH /
INSERT-CANDIDATE / ORPHAN-RISK. Mutates nothing. Refuses first real sync on any
ORPHAN-RISK. Dry-run reconciliation report emitted.

### R8 — Untyped str seam (the overarching telos target) [MODERATE | leverage=1.5 | impact=3, effort=2]

**What**: Current seam: `gid_push.py:490` `"vertical": str(vertical)` → `models_comparison.py:62`
`vertical: str = Field(...)`. Unvalidated, no schema, no contract.

**This IS the telos target** (see §3 of telos: realization predicate requires typed seam).

**RED**: Post-contract, `str(vertical)` still crosses the seam on the vocab path without a
typed validator.
**GREEN**: Producer sends `VocabularySyncRequest` (typed, extra-forbidden payload); consumer
validates `VocabularySyncRequest` and rejects unknown fields 422. No raw `str(vertical)` on
the vocab path.

### R-EC1 — PostgreSQL syntax appearing in sprint-2 build [resolved-watch]

**EC-1 is SETTLED = MySQL** (§3). If the sprint-2 build produces PostgreSQL syntax, it means
the settlement was not propagated. Watch condition:

**RED**: `ON CONFLICT`, `pg_advisory_xact_lock`, `asyncpg`, `psycopg2` appears in the
`/vocabularies/sync` endpoint or its service chain.
**GREEN**: None of the above present; `ON DUPLICATE KEY UPDATE` + MySQL engine confirmed.

### R-F1 — Bespoke vocab_upsert store (second-writer risk) [resolved-watch]

**Correction 1 clears this if applied.** Watch condition for sprint-2 review:

**RED**: A class or function named `vocab_upsert`, `VocabUpsertStore`, or similar writes
directly to the `verticals` table outside `services/vertical.py`.
**GREEN**: grep `autom8y-data/src` for writes to `verticals` table → only
`services/vertical.py` appears.

### R-F3 — account-status DELETE semantics copied to verticals [resolved-watch]

**Correction 3 clears this if applied.** Watch condition for sprint-2 review:

**RED**: Any `DELETE FROM verticals WHERE ...` or `session.delete(vertical)` in the
`/vocabularies/sync` endpoint or its service chain (with any condition, including `source=...`
which verticals doesn't even support).
**GREEN**: Zero DELETE operations on `verticals` from the vocab-sync codepath.

---

## §5 · Gate-A OPEN — Build BLOCKING Dependency

**Current state**: `.know/telos/dyn-enum-contract.md` is DRAFT-PENDING-OPERATOR-COUNTERSIGN.

```
ratified_by: "[PENDING — operator (Tom Tenuta) countersign]"
ratification_status: "DRAFT — PENDING OPERATOR COUNTERSIGN (drafted 2026-06-30)"
```

**Two `[OPERATOR-SET]` fields** in the telos that await operator confirmation:
- `verification_deadline: "2026-07-23"` (proposed; operator confirms or amends)
- `rite_disjoint_attester: "review-rite external critic"` (proposed; operator confirms or names)

**Gate-A sequence** (operator performs EXACTLY in this order; do NOT shortcut):
1. Review `.know/telos/dyn-enum-contract.md` draft (currently at the anchor above)
2. Confirm or amend the two `[OPERATOR-SET]` fields
3. Replace `"[PENDING — operator (Tom Tenuta) countersign]"` with your name + date + signature
4. Update `ratification_status` to `"RATIFIED — (Tom Tenuta, YYYY-MM-DD)"`
5. Run `ari sync --rite=10x-dev` (SINGULAR — one rite per invocation)
6. ONE CC restart (required after `ari sync`)
7. Then and ONLY THEN proceed to sprint-0 design-lock

**Cascading gates gated on Gate-A**:
- Sprint-0 ADR authoring (entry-gate item)
- Sprint-1 producer PR open
- Sprint-2 consumer PR open (also gated on PT-02 resolution — see §11)
- Sprint-4 LIVE ENABLE (operator flips `GID_PUSH_ENABLED` flag)
- Sprint-5 rite-disjoint attestation

---

## §6 · Rung + Critic Framing (G-CRITIC — BOTH critics named)

**G-RUNG discipline**: Arch reaches `authored` / validated-design ONLY. This HANDOFF is the
arch rite's maximum deliverable. The design is VALIDATED but NOT PROVEN. NEVER round up.

| Rung | Who owns | What it means for this initiative |
|------|----------|----------------------------------|
| authored | arch rite (this handoff) | Design validated; corrections mandated; NOT built |
| proven | 10x-dev sprint-1+2 | PRs merged; tests green; no live data touched |
| merged | 10x-dev sprint-1+2 | PRs landed on main; both repos updated |
| live | operator lever | `GID_PUSH_ENABLED` flag enabled; first real sync executed |
| verified-realized | review rite PT-07 | rite-disjoint critic attests LIVE round-trip against telos |

**G-CRITIC — TWO DISTINCT CRITICS (do NOT conflate):**

**Critic 1 — In-rite arch-adversary** (sprint-5 of the ARCH rite, THIS workflow):
- Scope: Challenges THIS HANDOFF artifact for epistemic integrity (TL-A/B/C)
- Gate: `ready_for_downstream: true` on this HANDOFF (SET 2026-07-01 — PASS-WITH-CONDITIONS, §14)
- Evidence ceiling: MODERATE (in-rite peer challenge)
- When: BEFORE 10x-dev build starts
- Artifact challenged: This HANDOFF document

**Critic 2 — Rite-disjoint external critic** (sprint-5 of the BUILD workflow = PT-07):
- Scope: Attests the LIVE verified-realized production build against the user-countersigned
  telos. The telos realization predicate is the attestation target: "Verified-realized = a NEW
  or renamed Asana enum_option round-trips into autom8y-data.verticals via additive-upsert
  with existing ids + FK children (campaigns / asset_verticals ~43K / offers.category) intact
  within one sync cycle, AND an empty/truncated Asana read is hard-REFUSED with an alert
  (never applied) — asserted by a LIVE/integration test on a real option-set round-trip."
- Gate: Verified-realized attestation on telos
- Evidence ceiling: STRONG (rite-disjoint attestation is the STRONG-upgrade path)
- When: AFTER build is live and LIVE/integration harness confirms the round-trip
- Artifact challenged: The LIVE build (not this HANDOFF)
- Signal-sifter execution note: only the signal-sifter agent in the review rite has Bash access;
  assign shell-heavy live round-trip re-runs to signal-sifter (not pattern-profiler or
  case-reporter)

---

## §7 · TL-A — Falsifiable Predictions the 10x Build Will Fire

Three independently-falsifiable predictions rooted in the validated design. If ANY fires FALSE
(build contradicts the prediction), the HANDOFF claim at that point is wrong and must be
escalated to the arch-adversary for re-triage.

### TL-A-1: MySQL confirmation in sprint-2 build

**Prediction**: Sprint-0 engine-config inspection at the BUILD HEAD confirms MySQL.
`ON DUPLICATE KEY UPDATE` + `GET_LOCK()`/`RELEASE_LOCK()` appear in the sprint-2 consumer
code. `ON CONFLICT`/`pg_advisory_xact_lock` do NOT appear in the vocab-sync service chain.

**Basis**: `core/config.py:217/:222` (MySQL URL); `pyproject.toml:99` (pymysql driver);
`forwarding_binding_store.py:155/:218/:252/:315` (live `ON DUPLICATE KEY UPDATE` exemplar in
the consumer). [STRUCTURAL | MODERATE]

**How to falsify**: If the sprint-2 build contains `ON CONFLICT` or `asyncpg` anywhere in
the vocab-sync chain → EC-1 settlement was not applied → escalate.

### TL-A-2: Snapshot-replace DELETE fails a DELETE-guard test

**Prediction**: A snapshot-replace DELETE attempt on `verticals` (the account-status semantics
anti-pattern) fires ORPHAN-RISK RED in the FR-008 dry-run, as FK children (campaigns/
asset_verticals ~43K/offers.category) exist for those keys.

**Basis**: `_platform.py:497-498` (the DELETE that MUST NOT be copied); `_platform.py:131-162`
(no source column on verticals); 7 FK edges E1-E7 (dependency-map §2.a). The dry-run
classifies a DELETE attempt against an FK-referenced key as ORPHAN-RISK.

**How to falsify**: If the FR-008 dry-run passes for a DELETE attempt (no ORPHAN-RISK raised
on an FK-referenced key) → the dry-run is not checking FK edges → the guard is incomplete →
escalate.

### TL-A-3: No bespoke writer to `verticals` outside `VerticalService`

**Prediction**: Grep of `autom8y-data/src` in the sprint-2 PR confirms no class or function
outside `services/vertical.py` writes the `verticals` table. REC-1 correctly applied.

**Basis**: `services/vertical.py:212` (sole canonical writer at HEAD); U-3 DuckDB-write
NEGATIVE (`analytics/initialization.py:259-324` writes temp/fact tables, NOT verticals).
[STRUCTURAL | MODERATE]

**How to falsify**: grep finds a `INSERT INTO verticals` or `session.add(Vertical(...))` or
`VocabUpsertStore` outside `services/vertical.py` → REC-1 was not applied → second-writer
condition present → escalate to arch-adversary.

---

## §8 · TL-B — Source Citations (Arch Artifact `{path}:{line}`)

Every load-bearing claim in this HANDOFF maps to a `{path}:{line}` receipt or carries
`[UNATTESTED — DEFER-POST-HANDOFF]` per telos-integrity §3 Gate-C discipline.

| Claim | Receipt | Artifact |
|-------|---------|---------|
| Single canonical writer to verticals | [C] `services/vertical.py:212` | dep-map §2.d; assessment §1.a |
| No-delete invariant (service) | [C] `services/vertical.py:9` | PV-preflight BONUS |
| No-delete invariant (proto) | [C] `proto/autom8/data/v1/__init__.py:667` | PV-preflight BONUS |
| No-delete invariant (gRPC) | [C] `grpc/handlers/vertical.py:128` | PV-preflight BONUS |
| MySQL URL docstring | [C] `core/config.py:217` | PV-preflight PREMISE-2 |
| MySQL asyncmy normalization | [C] `core/config.py:222` | PV-preflight PREMISE-2 |
| pymysql driver dep | [C] `pyproject.toml:99` | PV-preflight PREMISE-2 |
| Shape-B live upsert exemplar | [C] `api/services/forwarding_binding_store.py:155/:218/:252/:315` | dep-map §4 |
| `GET_LOCK`/`RELEASE_LOCK` in consumer | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/lock-intro-sprint-2]` | dep-map §4 "0 hits" |
| FK fan-in PRIMARY join | [C] `dimension_enrichment.py:144` | dep-map §2.a |
| FK fan-in FALLBACK join | [C] `dimension_enrichment.py:166` | dep-map §2.a |
| DuckDB LEFT JOIN 45 files | [C] `analytics/core/infra/enrichment_views.py:152` | topology §DIGITAL |
| account-status snapshot-replace DELETE | [C] `_platform.py:497-498` | PV-preflight PREMISE-3 |
| verticals has no source column | [C] `_platform.py:142-147` | PV-preflight PREMISE-3 |
| vertical_key UNIQUE constraint | [C] `_platform.py:146` | PV-preflight PREMISE-1 |
| vertical_name UNIQUE constraint | [C] `_platform.py:147` | PV-preflight PREMISE-1 |
| STRING FK offers.category | [C] `_platform.py:162` | PV-preflight PREMISE-1 |
| Business FK (FALLBACK hub) | [C] `_platform.py:72` | dep-map U-5 RESOLVED |
| Question FK (nullable) | [C] `_platform.py:451` | dep-map U-5 RESOLVED |
| asset_verticals junction | [C] `_advertising.py:322/:326` | dep-map §2.a |
| Feature flag env var surface | [P] `services/gid_push.py:62` | PV-preflight PREMISE-4 |
| Feature flag gate | [P] `services/gid_push.py:95` | PV-preflight PREMISE-4 |
| Push helper entry point | [P] `services/gid_push.py:163` | PV-preflight PREMISE-4 |
| Call-path A empty-guard (to replace) | [P] `services/gid_push.py:328` | PV-preflight PREMISE-4 |
| Call-path B empty-guard (to replace) | [P] `services/gid_push.py:554` | PV-preflight PREMISE-4 |
| Enum_options field read | [P] `models/custom_field.py:113` | PV-preflight PREMISE-4 |
| Untyped producer seam | [P] `services/gid_push.py:490` | PV-preflight PREMISE-3 |
| Untyped consumer seam | [C] `api/models_comparison.py:62` | PV-preflight PREMISE-3 |
| account-status typed-envelope shape | [C] `api/data_service_models/_account_status_sync.py:70/:113` | dep-map §5; assessment §6 |
| SDK VerticalsListResponse home | [SDK] `clients/data_intake.py:473` | dep-map U-4 RESOLVED |
| uniform pin >=4.2.0,<5.0.0 | [P]`:26` / [ads]`:21` / [sms]`:26` / [sched]`:31` pyproject.toml | dep-map U-4 RESOLVED |
| DEFER-1 N<3 gate state | grep result 0 hits at PV-preflight PREMISE-5 | pv-preflight PREMISE-5 |
| telos DRAFT | `.know/telos/dyn-enum-contract.md` frontmatter | assessment §7 |
| asset_verticals row count ~43K | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/U-1-row-counts]` | dep-map U-1 (UV-P) |
| EC-2 credential scope | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/EC-2-credential-path]` | dep-map EC-2 (UV-P) |

---

## §9 · TL-C — Adversarial Disposition (Considered + Rejected; Least Certain)

### What was considered and rejected

**Option 1 — Hub decoupling (denormalize verticals for blast-radius isolation)**
- Rationale for rejection: Hub is the correct topology for a global reference dimension with
  4 downstream consumers. Denormalization would replicate state across consumers — introducing
  write-side fragmentation rather than eliminating it. The hub's stability (I≈0) IS the design
  goal. Defense is at the write path, not the hub topology.
- Evidence: [C] `routes/factory.py:354` "GLOBAL entities (verticals…)"; dep-map §10 "ACCEPTED
  TRADE-OFF — hub is the correct topology"; assessment §2.2 rationale.

**Option 2 — Bespoke vocab_upsert store (the rnd G6 framing)**
- Rationale for rejection: Manufactures a second-writer condition; bypasses the no-delete
  invariant enforcement at `services/vertical.py:9`; concentrates novel risk in a new class
  rather than composing with the established service layer. The rnd correctly identified
  CRITICALITY but not LOCUS.
- Evidence: [C] `services/vertical.py:212` (sole writer at HEAD); U-3 DuckDB-write NEGATIVE;
  assessment §1.a.

**Option 3 — Fleet-wide vocabulary registry (DEFER-1 Option-F)**
- Rationale for rejection: DEFER-1 N<3 gate not fired. Building a registry at N<3 is a
  one-way speculative door. The 4 downstream consumers are fragmentation EVIDENCE, not the
  escalation trigger. The per-instance contract with 3 compose-up locks is the correct
  stopping point.
- Evidence: PV-preflight PREMISE-5 (0 bindings at both repos); assessment §4 (N<3 confirmed);
  DEFER-1 escalation trigger stated explicitly.

**Option 4 — PostgreSQL advisory lock (the PROTO canary)**
- Rationale for rejection: Directly refuted by 7 live MySQL receipts in the `autom8y-data`
  production tree. The PROTO spike ran against a PostgreSQL fixture, not the live consumer. EC-1
  is SETTLED by the arch inspection, not a design choice.

### Where least certain

**Least certain point 1 — `GET_LOCK`/`RELEASE_LOCK` contention under production write concurrency**

The advisory lock primitive is well-matched to the MySQL engine and established in the
`forwarding_binding_store.py` exemplar. However: `GET_LOCK`/`RELEASE_LOCK` has NOT been
introduced in the consumer tree yet (0 hits; `[UNATTESTED — DEFER-POST-HANDOFF:
dyn-enum-contract/lock-intro-sprint-2]`). The runtime behavior under concurrent vocab-sync
invocations from multiple warmer instances is unassessed at this rung. If the warmer scales
horizontally, the lock contention surface is proportional.

**Arch disposition**: The lock introduction is sound at the design level (matching primitive for
the MySQL engine; `forwarding_binding_store.py` exemplar demonstrates successful use in the
consumer). The contention question is a runtime/sre concern, not a structural correctness
concern. Escalation path: sre rite post-build.

**Least certain point 2 — First-sync key-mismatch severity at HEAD**

The ORPHAN-RISK dry-run is mandated by REC-7. The SEVERITY of the orphan-risk depends on the
historical normalization scheme used to insert existing `verticals` rows. If existing keys
match the Asana-option-name normalization exactly, orphan-risk severity = LOW (smooth first
sync). If not, first sync is blocked until manual reconciliation. Arch cannot assess this
without a live DB read (no creds at this altitude). The dry-run surfaces the severity before
any mutation.

**Arch disposition**: Dry-run is the correct guard. Severity is UNKNOWN-UNTIL-DRY-RUN
(`[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/U-1-key-mismatch-severity]`).

**Least certain point 3 — ads `VerticalNormalizer` as fragmentation or bounded-context**

`VerticalNormalizer` at `creative_performance.py:90` is a parallel vocabulary authority in the
ads service. Arch cannot determine from static analysis whether it's intentional bounded-context
divergence (acceptable) or accidental duplication (R5 severity bump). Routed as CRR-002.

**Arch disposition**: Unknown U-B; debt-triage characterizes; does not block the telos.

---

## §10 · Production-Mutating Levers (Exact Commands; DO NOT Execute Now)

> These are the EXACT commands. Arch surfaces them here for the 10x build to execute at the
> correct time. Arch does NOT execute them. No command runs against any repo during the arch
> sprint.

### Lever 1 — Gate-A Close (operator-only; run before build starts)

```bash
# Step 1: Review and edit the telos
# Edit: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/telos/dyn-enum-contract.md
# Update ratified_by, ratification_status, and two [OPERATOR-SET] fields

# Step 2: Switch to 10x-dev rite (SINGULAR — one rite per invocation)
ari sync --rite=10x-dev

# Step 3: ONE CC restart (mandatory after ari sync)
# Restart Claude Code — the operator performs this manually
```

### Lever 2 — PT-02 Option A: sync autom8y-data into 10x-dev roster (operator-chosen)

```bash
# In the autom8y-data repo directory
ari sync --rite=10x-dev   # SINGULAR + ONE CC restart
# Verify: cat .knossos/ACTIVE_RITE  → should show 10x-dev
```

### Lever 3 — PT-02 Option B: run sprint-2 consumer build natively under dre (operator-chosen)

```bash
# No ari sync needed — autom8y-data ACTIVE_RITE=dre already
# Open a separate autom8y-data CC session under the dre rite
# Verify: cat .knossos/ACTIVE_RITE  → should show dre
```

### Lever 4 — Live enable (consumer deployed BEFORE this runs)

```bash
# ONLY after: consumer endpoint deployed to production AND health-checked
# Set the env var in the producer deployment configuration:
GID_PUSH_ENABLED=true   # Sets gid_push.py:62 GID_PUSH_ENABLED_ENV_VAR = true

# The flag is gated at: services/gid_push.py:95
# enable-ordered: consumer deployed FIRST, then this flag enabled (CON-010/BC-1)
```

### Lever 5 — Rite-disjoint attestation (final; post-live)

```bash
# After: both PRs merged, live enable complete, LIVE/integration harness authored
# Switch to review rite for rite-disjoint attestation
ari sync --rite=review   # SINGULAR + ONE CC restart
# Verify: cat .knossos/ACTIVE_RITE  → should show review
# Then: run LIVE/integration harness via signal-sifter (only review agent with Bash)
```

**Enable-ordered deploy mandate (CON-010/BC-1)**: Consumer endpoint (`POST /api/v1/vocabularies/sync`)
MUST be deployed to production AND health-checked BEFORE the producer push flag
(`GID_PUSH_ENABLED`) is enabled. Lever 4 comes AFTER Lever 2/3's consumer deployment.

---

## §11 · PT-02 Operator Fork — autom8y-data ACTIVE_RITE = dre

**Fact** (live-verified 2026-06-30 per `dyn-enum-contract.shape.md §3`):
`autom8y-data` has `ACTIVE_RITE=dre` (data-reliability engineering rite). This is NOT
`10x-dev`. The sprint-2 consumer build lands in `autom8y-data`.

**This is a fork that the operator MUST resolve.** Arch does NOT pre-pick the option.

**Option A — 10x-dev-synced-into-data**:
Run `ari sync --rite=10x-dev` in the `autom8y-data` repo + ONE CC restart before sprint-2.
Sprint-2 consumer build runs as a standard 10x-dev build.
Consideration: overwrites the current `dre` rite context in `autom8y-data`; operator must
re-sync back to `dre` after sprint-2 if ongoing dre work is in flight.

**Option B — dre-native consumer build**:
Do NOT sync. Sprint-2 consumer build runs under the existing `dre` rite in a separate
`autom8y-data` session. Build owner coordinates with the dre rite's active workflow.
Consideration: `dre` agents (integrity-architect, pipeline-steward, source-load-analyst,
change-warden) review the consumer PR rather than 10x-dev agents — which may be PREFERABLE
given the FK-parent risk profile and data-reliability focus.

**Arch note**: Option B may be architecturally preferable given the FK-parent SPOF cascade
severity (R1 HIGH) and the data-reliability nature of the write-path integrity requirements.
The dre rite agents are specifically designed for this class of data-reliability concern.
This is the operator's call; escalate, do not pre-pick.

**CRR-001** routes the dre context formally to the dre rite; see architecture-report §5.

---

## §12 · Known Unknowns with UV-P Tags

| Unknown | Impact | Tag | Suggested attester |
|---------|--------|-----|-------------------|
| Gate-A telos countersign | BLOCKING | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/gate-a-telos]` | Operator (Tom Tenuta) — action required before build |
| EC-2 live Asana credential scope | HIGH | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/EC-2-credential-path]` | security rite / IAM-infra team (CRR-003) |
| `GET_LOCK`/`RELEASE_LOCK` runtime contention | MEDIUM | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/lock-intro-sprint-2]` | sre rite post-build; load test |
| First-sync key-mismatch severity | MEDIUM | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/U-1-key-mismatch-severity]` | dry-run output (self-documenting; no creds needed at arch) |
| FK child row counts (blast-radius magnitude) | MEDIUM | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/U-1-row-counts]` | operator / DBA with live MySQL SELECT COUNT |
| ads `VerticalNormalizer` intent | MEDIUM | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/U-B-ads-normalizer]` | ads-service domain owner; debt-triage (CRR-002) |
| Committed 2nd `asana_configured` vocab | LOW-MEDIUM | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/U-A-2nd-vocab]` | product roadmap owner |
| `values_source: "mixed"` semantics | LOW | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/U-C-mixed-semantics]` | producer-domain owner / git history |
| asset_verticals exact row count | LOW | `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/U-1-row-counts]` | ~43K asserted by spike; confirm with SELECT COUNT |

---

## §13 · Scope Limitation

This HANDOFF delivers a validated architectural design. It does NOT:

- **Author production code** — all code authoring is 10x-dev's. The remediation-planner
  describes WHAT to build and WHERE; HOW is the build's domain.
- **Execute any production-mutating lever** — all levers in §10 are documented for the build
  to execute at the correct time. None were run during the arch rite.
- **Attest live behavior** — the design is VALIDATED at the authored rung. Proving it correct
  requires the 10x-dev build + rite-disjoint attestation. `ready_for_downstream: false` until
  arch-adversary sprint-5 PASS.
- **Resolve Gate-A** — operator-sovereign. Arch cannot countersign the telos on the
  operator's behalf.
- **Resolve PT-02** — operator-sovereign. Option A vs Option B is the operator's call.
- **Assess the AWS credential scope** — security rite domain (CRR-003). Arch flags the
  unknown; it does not audit IAM policies.
- **Characterize the ads VerticalNormalizer** — debt-triage domain (CRR-002). Arch flags
  the fragmentation; characterization requires domain-owner input.
- **Implement the DEFER-1 fleet registry** — escalate-only at N≥3. Building it pre-trigger
  is the one-way door the arch rite explicitly refused to open.

---

## §14 · Arch-Adversary Gate Verdict + Conditions (sprint-5, in-rite)

**Verdict**: **PASS-WITH-CONDITIONS** · disposition CONCUR-WITH-FLAGS · in-rite ceiling MODERATE
(2026-07-01). `ready_for_downstream: true`. Full report:
`.ledge/reviews/dyn-enum-contract-arch-ADVERSARY-REPORT.md`.
**target_handoff_sha**: `sha256:6af7b54fdf7d8101fed0ece9d0a32788ed54f41c816349e181ac1c24d5ca33d0`
(cwd working-tree draft at challenge time; not committed — expected at the `authored` rung).

**Live-verified at the gate** (producer origin/main ca28251d, consumer autom8y-data HEAD 92d3606d):
- **TL-A-3 GREEN** — sole `verticals` writer = `services/vertical.py:212`; REST (`api/routes/verticals_crud.py:283`) + gRPC (`grpc/adapters/vertical.py:174`) both route THROUGH `service.create`; no bespoke `vocab_upsert`. **REC-1 (route-through-VerticalService) premise holds** — a 2nd writer would have been a BLOCK.
- **TL-A-1** — 4/7 MySQL receipts reproduced verbatim; `ON CONFLICT`/`pg_advisory`/`asyncpg` = 0 hits; `GET_LOCK` = 0 hits (matches the honest prospective tag).
- **TL-A-2** — Vertical model `_platform.py:131-149` = id/key/name only, 0 `source` columns → snapshot-replace DELETE genuinely unconditional-catastrophic.
- All 6 dispatch hard checks PASS (G-RUNG, G-CRITIC, telos Gate-C, Gate-A-carried, G-DEFER, G-THEATER).

**Conditions the 10x build must satisfy** (verbatim from the ADVERSARY-REPORT):
- **C1** (adversary FLAG, CH-01, non-blocking — ✅ APPLIED in this revision): §2 Correction 3's verticals-schema anchor (which mis-pointed at the Business-model docstring) corrected → `_platform.py:142-147` (the Vertical model fields). The claim was independently live-verified and is correctly cited at §7 (`:131-162`).
- **C2** (operator-sovereign, BUILD-BLOCKING): Gate-A — countersign `.know/telos/dyn-enum-contract.md` (live-confirmed DRAFT/OPEN) before the build. See §5.
- **C3** (operator-sovereign): resolve the PT-02 consumer-repo rite fork. NOTE: the consumer rite is UNSETTLED — topology read `dre`, but the live `autom8y-data/.knossos/ACTIVE_RITE` reads `eunomia`. Settle at the PT-01→PT-02 boundary (defer-the-decision), NOT at this producer seam. See §11.
- **C4**: sprint-0 architect re-verifies ALL `{path}:{line}` anchors at the build HEAD (per Correction 7 / telos `code_verbatim_match: false`).
- **C5**: re-run the resolved-watch conditions R-EC1 / R-F1 / R-F3 (§4) at sprint-2 PR review (all GREEN at current HEAD).
- **C6**: sre assesses `GET_LOCK` contention post-build (deferred; 0 hits today).

**Second TL-B flag (CH-02, ADVISORY, non-load-bearing)**: §2 Correction 1's `grpc/handlers/vertical.py:128` is the `create_vertical` handler (attests create-only indirectly, by absence-of-delete); the invariant is directly confirmed at `services/vertical.py:9` + `proto/.../v1/__init__.py:667`. No action required.

**Verdict falsification**: revise to BLOCK if a second `verticals` writer or PostgreSQL syntax appears at the sprint-2 build HEAD; revise to clean PASS once C1+C2+C3 land. This in-rite PASS-WITH-CONDITIONS caps the architecture verdict at **MODERATE** — STRONG belongs to the rite-disjoint review-rite critic (Critic 2) at PT-07.

---

*This HANDOFF is the arch rite's output for the `dyn-enum-contract` initiative. The arch-adversary
(sprint-5, in-rite) cleared it **PASS-WITH-CONDITIONS** (§14) → `ready_for_downstream: true`. The
SOLE remaining blocker before the 10x-dev build is the operator's Gate-A telos countersign (§5);
`ready_for_downstream: true` is arch's attestation, NOT authorization to cross the seam.*

*Critic 1 (arch-adversary, TL-A/B/C scope): challenged this document → PASS-WITH-CONDITIONS.*
*Critic 2 (rite-disjoint review-rite critic, verified-realized scope): challenges the live
build at PT-07. Two critics. Two gates. Two scopes. Do not conflate.*
