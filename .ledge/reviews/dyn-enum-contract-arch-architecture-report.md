---
type: review
artifact_subtype: arch-architecture-report
initiative: dyn-enum-contract
rite: arch
sprint: 4-of-5 (topology -> dependency -> structure -> REMEDIATION -> adversary)
generated_by: remediation-planner
created: 2026-06-30
status: draft
rung: authored   # G-RUNG: remediation reaches "authored" / validated-design ONLY — never proven/merged/live
evidence_grade_ceiling: "MODERATE (self-ref per G-CRITIC; STRONG requires rite-disjoint arch-adversary at sprint-5)"
producer_truth_anchor: "autom8y-asana origin/main (ca28251d) — NOT cwd chore/bump-core-4.6.0 (f4f924d2, OFF-ANCHOR)"
consumer_truth_anchor: "autom8y-data HEAD (92d3606d, branch main)"
upstream_artifacts:
  - .ledge/reviews/dyn-enum-contract-arch-pv-preflight.md
  - .ledge/reviews/dyn-enum-contract-arch-topology-inventory.md
  - .ledge/reviews/dyn-enum-contract-arch-dependency-map.md
  - .ledge/reviews/dyn-enum-contract-arch-architecture-assessment.md
ready_for_downstream: false   # arch-adversary (sprint-5) gates ready_for_downstream=true
---

# Architecture Report — dyn-enum-contract

> **Acid test**: This report is written for someone unfamiliar with the codebase. Every
> recommendation names (1) what to change, (2) which file with `{path}:{line}`, (3) why it
> matters architecturally, and (4) the expected outcome. Every finding from the
> architecture-assessment appears with either a recommendation or an explicit accept-as-is
> designation. No finding silently disappears.

---

## Executive Summary

The `dyn-enum-contract` initiative — *one typed, additive, FK-safe sync contract carrying an
Asana enum-option-set change into `autom8y-data.verticals`* — has completed the arch rite's
four-phase validation (PV preflight → topology inventory → dependency map → architecture
assessment). The design is **conditionally viable** with 7 architectural corrections required
before the 10x-dev build begins.

**Platform state in one paragraph**: `autom8y-data.verticals` is a maximally-stable (I≈0)
global reference-data hub with 7 inbound FK children spanning campaigns, asset_verticals
(~43K rows), offers.category STRING FK, business FALLBACK, questions, payments soft-ref, and
cross-repo scheduling — plus a DuckDB analytics read surface covering 45 files. It carries the
fleet's lead-enrichment spine. The Asana→data seam crosses today as an **untyped `str`** with
no contract. The proposed `/api/v1/vocabularies/sync` endpoint would replace this with a typed,
additive sync. The architecture is correct in its boundary direction (Asana owns vocabulary
authority; data materializes downstream), its permanence invariant (no-delete across service
layer, proto contract, gRPC handler), and its single-writer discipline. The highest-risk
structural characteristic is the FK-parent cascade: a mis-keyed or orphaned vertical row
propagates silently fleet-wide via LEFT JOIN to fact tables.

**Top-line conclusions:**

1. The rnd's proposed `vocab_upsert` store is MIS-ALIGNED — routing through the existing
   `VerticalService.create` (`autom8y-data/src/autom8_data/services/vertical.py:212`) is the
   correct boundary-preserving design (see REC-1, highest leverage).
2. EC-1 is definitively settled: MySQL, not PostgreSQL. The PROTO PostgreSQL canary is refuted
   by 7 live receipts.
3. The `account-status/sync` precedent is a FALSE-FRIEND for write semantics — its
   snapshot-replace DELETE would wipe the FK-parent hub.
4. Write-path integrity (hard-refuse + additive-upsert + rename guard) is the fleet-safety
   requirement, not hub decoupling.
5. The telos is DRAFT and Gate-A is OPEN; the build cannot start until the operator
   countersigns `.know/telos/dyn-enum-contract.md`.

**Evidence grade**: `[STRUCTURAL | MODERATE]` — self-referential ceiling per G-CRITIC.
STRONG requires the rite-disjoint arch-adversary (sprint-5) downstream.

`ready_for_downstream: false` — the arch-adversary (sprint-5) gates progression to 10x-dev.

---

## 1. Platform Architecture State

### 1.1 The Seam Under Validation

The `dyn-enum-contract` contract crosses one structural seam: `autom8y-asana` (producer) →
`autom8y-data` (consumer/store). The producer reads live Asana `enum_options` from custom
field GID `1182735041547604` (`models/custom_field.py:113`) and pushes a typed snapshot to
a new `/api/v1/vocabularies/sync` endpoint behind the `GID_PUSH_ENABLED` flag
(`gid_push.py:62`).

**What exists today** (the pre-contract state; not the design under validation):
- Producer emits `"vertical": str(vertical)` at `services/gid_push.py:490` — untyped string
- Consumer receives `vertical: str = Field(...)` at `api/models_comparison.py:62` — untyped
- The `/api/v1/vocabularies/sync` endpoint has **0 bindings** at both repos (confirmed: grep
  `git grep -nE "vocabularies/sync"` at both anchors → 0 files)

**What the design proposes** (the telos target; not yet built):
- NEW `POST /api/v1/vocabularies/sync` route on `autom8y-data` with `field_key` discriminator
  and `extra=forbid`
- Producer: read live `enum_options`, project NAME-keyed snapshot, push via
  `_push_to_data_service` (`gid_push.py:163`) behind the feature flag
- Consumer: additive-upsert (INSERT-new / UPDATE-name / NEVER DELETE) keyed on `vertical_key`
  (UNIQUE at `core/models/_platform.py:146`)

### 1.2 Structural Context (live receipts)

| Fact | Receipt | Confidence |
|------|---------|------------|
| `verticals` is a GLOBAL reference hub | [C] `routes/factory.py:354` "GLOBAL entities (verticals…)" | High |
| Single canonical writer today | [C] `services/vertical.py:212` `self._session.add(vertical)` | High |
| No-delete invariant (3 surfaces) | [C] `services/vertical.py:9`; `proto/autom8/data/v1/__init__.py:667`; `grpc/handlers/vertical.py:128` | High |
| FK fan-in ≥7 edges | E1–E7 (dependency-map §2.a; 5 declared FKs + 1 soft-ref + 1 cross-repo) | High |
| DuckDB analytics read (45 files; LEFT JOIN) | [C] `analytics/core/infra/enrichment_views.py:152` | High |
| EC-1 confirmed MySQL | [C] `core/config.py:217/:222`; `pyproject.toml:99` | High |
| No second write-consumer (U-3 NEGATIVE) | [C] `analytics/initialization.py:259-324` (writes temp/fact tables, NOT verticals) | High |
| Producer feature flag surface | [P] `services/gid_push.py:62` `GID_PUSH_ENABLED_ENV_VAR` (gate read `:95`) | High |

### 1.3 Distributed-Monolith Status

**CLEARED at runtime/deploy.** The dependency is unidirectional (asana→data), ADP
non-violated, and the flag-gated expand/contract sequencing is the correct deploy pattern.
One **conditional residual** remains: if the typed contract model is duplicated per-repo
rather than homed in the `autom8y-core` SDK, that introduces hidden release-coupling (see
REC-5 / R6). [STRUCTURAL | MODERATE]

---

## 2. Consolidated Findings

Findings synthesize all four upstream artifacts. Confidence ratings are inherited from the
upstream stations and propagated through without re-derivation.

### F1 — Route-through-VerticalService: ARCHITECTURAL CORRECTION [High confidence]

The rnd handoff's "G6 CRITICAL new component" (`vocab_upsert` store) is architecturally
MIS-ALIGNED. It manufactures the exact second-writer condition the dependency-map FORK-3 watch
was guarding against. The correct design routes `/vocabularies/sync` THROUGH the existing
canonical writer.

**Evidence**: [C] `services/vertical.py:212` (sole canonical writer confirmed); [C]
`services/vertical.py:9` (no-delete invariant already enforced at the service layer); U-3
DuckDB-write NEGATIVE (`analytics/initialization.py:259-324`) confirming writer exclusivity.
Architecture-assessment §1.a, §6. [STRUCTURAL | MODERATE]

**Correction**: Extend `VerticalService.create` (create-only today at `:149/:212`) with an
upsert path — create-if-absent / update-name-when-safe / NEVER DELETE. Route the
`/vocabularies/sync` write path through this extended service method, not a bespoke store
class.

### F2 — EC-1 SETTLED = MySQL; shape-B is `INSERT…ON DUPLICATE KEY UPDATE` + `GET_LOCK`/`RELEASE_LOCK` [High confidence]

The PROTO spike's PostgreSQL canary (`ON CONFLICT(key) DO UPDATE`, `pg_advisory_xact_lock`)
is REFUTED by direct inspection. The autom8y-data `verticals` write-path is MySQL. 10x-dev
must re-derive the upsert for MySQL.

**Evidence**: [C] `core/config.py:217` (MySQL URL docstring); [C] `core/config.py:222`
(`mysql+asyncmy://` normalization); [C] `pyproject.toml:99` (`pymysql>=1.1.0`); [C]
`api/services/forwarding_binding_store.py:155/:218/:252/:315` (live `INSERT … ON DUPLICATE
KEY UPDATE` exemplar already in the consumer). PV-preflight §PREMISE-2. [STRUCTURAL | MODERATE]

**Shape-B implication**: Upsert = `INSERT … ON DUPLICATE KEY UPDATE`; lock =
`GET_LOCK()`/`RELEASE_LOCK()` (MySQL named-lock primitive; 0 hits in consumer tree today —
10x-dev introduces this in sprint-2). NOT PostgreSQL `ON CONFLICT`. This is a SETTLED FACT,
not a design choice.

### F3 — account-status/sync: FALSE-FRIEND for semantics (not shape) [High confidence]

The `account-status/sync` precedent is the correct template for the SHAPE of the typed
envelope. Its WRITE SEMANTICS are catastrophically wrong for verticals and must never be
copied.

**Evidence**: [C] `core/models/_platform.py:497-498` — `DELETE FROM account_status WHERE
source='section_classifier'` (the snapshot-replace that MUST NOT be copied). [C]
`core/models/_platform.py:131-162` — `verticals` schema = id/key/name only, NO `source`
column present; source-scoped DELETE is structurally impossible on verticals; an unconditional
DELETE wipes the FK-parent hub. [C]
`api/data_service_models/_account_status_sync.py:70/:113` (the correct typed-envelope SHAPE
to reuse). Architecture-assessment §6, PV-preflight §PREMISE-3. [STRUCTURAL | MODERATE]

**Correct reuse boundary**: Envelope / transport / auth shape from account-status: YES.
Snapshot-replace write semantics: NO.

### F4 — FK-parent SPOF cascade: HIGH severity; write-path integrity is the defense [High confidence]

The `verticals` dimension is a single-point-of-failure hub with fleet-wide blast radius.
The lead-enrichment PRIMARY and FALLBACK paths share the single parent with NO independent
redundancy. Failures are silent (LEFT JOIN → NULL attribution, not an error).

**Evidence**: [C] `dimension_enrichment.py:144` (J1, PRIMARY campaign join); [C]
`dimension_enrichment.py:166` (J2, business FALLBACK — shares the SAME parent, no
redundancy); [C] `analytics/core/infra/enrichment_views.py:152` (DuckDB LEFT JOIN, 45 files,
silent corruption path); E1–E7 (7 FK edges in dependency-map §2.a). Architecture-assessment
§2.2, §3. [STRUCTURAL | MODERATE]

**Actionable defense**: WRITE-PATH INTEGRITY — hard-refuse on empty/truncated read +
additive-upsert DELETE-forbidden + first-sync ORPHAN-RISK dry-run. NOT hub decoupling (which
would re-introduce the fragmentation the contract is designed to solve).

### F5 — SDK model home: residual schema-drift risk [Medium confidence]

If the typed request/response models for `/vocabularies/sync` are defined independently
per-repo, a schema change requires coordinated cross-repo edits — hidden release-coupling.

**Evidence**: [SDK] `clients/data_intake.py:473` (`VerticalsListResponse` — established
cross-repo shared-model home in `autom8y-core`); dependency-map U-4 RESOLVED — all 4 Python
consumers carry uniform pin `autom8y-core>=4.2.0,<5.0.0`. Architecture-assessment §2.1, §6.
[STRUCTURAL | MODERATE — conditional on implementation choice]

**Correction**: Home `VocabularySyncRequest` / `VocabularySyncResponse` pydantic models once
in `autom8y-core` SDK, not duplicated per-repo.

### F6 — Generic endpoint + compose-up locks: ALIGNED-WITH-WATCH [Medium confidence]

The three compose-up locks (generic `/api/v1/vocabularies/sync` + `field_key` discriminator +
NAME-keying) are a sound forward-compatibility hedge. The hedge is VALID while thin; it
becomes speculative generality if `field_key` accretes per-vocab dispatch branching.

**Evidence**: DEFER-1 N<3 confirmed (PV-preflight §PREMISE-5); [P] `annotations.py:50`
frozenset door ({hardcoded, asana_configured, mixed}); [C] `routes/factory.py:354` (GLOBAL
entity). Architecture-assessment §1.b, §4. [STRUCTURAL | MODERATE — boundary case]

**Watch condition**: `field_key` must be DATA, not CONTROL-FLOW. `if field_key ==
"vertical": … elif …` dispatch in the build = registry-by-stealth before N≥3 fires.

### F7 — Stale rnd/frame line-number anchors: corrected to LIVE numbers [High confidence]

Several anchors in the rnd/frame artifacts are stale. All downstream stations must use the
live numbers (all receipts at `autom8y-asana origin/main ca28251d`).

**Corrections**:
- Feature flag: `services/gid_push.py:62` `GID_PUSH_ENABLED_ENV_VAR` (NOT `resolver_schema.py:491` — that file is 475 lines; `:491` is past EOF)
- Push helper entry: `services/gid_push.py:163`
- Call path A empty-guard: `services/gid_push.py:328`
- Call path B empty-guard: `services/gid_push.py:554`
- Account-status envelope: `services/gid_push.py:375`
- Account-status endpoint: `services/gid_push.py:564`
- FK fan-in: ≥7 (not 3) — additional edges: Business.default_vertical_id at `_platform.py:72` (table chiropractors), Question.vertical_id at `_platform.py:451` (table questions)

---

## 3. Leverage-Ranked Recommendations

Leverage = impact/effort (inherited from architecture-assessment; PLATFORM-HEURISTIC: impact
1–5, effort 1–5; quick-win leverage ≥3, strategic 1–3 with impact ≥4, long-term <1).

All 8 risks (R1–R8) from the architecture-assessment appear here. No finding is orphaned.

### REC-1 — Route `/vocabularies/sync` THROUGH `VerticalService.create` [ARCHITECTURAL CORRECTION]

**Addresses**: F1, R1, R2 (write-path integrity, single-writer preservation)
**Leverage**: HIGH (eliminates second-writer condition; low effort as design correction; high
impact on correctness and blast-radius prevention)
**Classification**: Strategic correction / quick win at design rung
**Confidence**: High (corroborated across topology §BONUS, dependency-map §2.d, assessment §1.a)

**What to change**: In `autom8y-data/src/autom8_data/services/vertical.py`, extend the
`VerticalService` class (currently create-only at `:149/:212`) with a `upsert` method:
create-if-absent keyed on `vertical_key` (UNIQUE at `_platform.py:146`) and update
`vertical_name` when safe (non-colliding with UNIQUE at `_platform.py:147`). Route the
`/api/v1/vocabularies/sync` write path through this extended service method. No bespoke
`vocab_upsert` store class.

**Why it matters**: `VerticalService.create` is the sole canonical writer to `verticals`
(U-3 DuckDB-write NEGATIVE). A bespoke store creates a SECOND writer, bypasses the no-delete
invariant enforcement surface (`services/vertical.py:9`), and breaks the additive-upsert
exclusivity that is the entire contract's structural foundation. The rnd's "G6 CRITICAL" label
was correct that new behavior is required; the LOCUS is wrong (service, not store).

**Acceptance criterion (RED→GREEN)**: Assert no class/function outside `services/vertical.py`
writes the `verticals` table in the sprint-2 build. RED = a bespoke `vocab_upsert` function
directly writes `verticals` → write-ownership fragmented → second-writer condition
manufactured → exclusivity broken. GREEN = all vocab-sync writes route through
`VerticalService`.

### REC-2 — Implement producer referential-coverage HARD-REFUSE on the vocab path

**Addresses**: R2 (empty/truncated-publish blast-radius)
**Leverage**: 2.5 (impact=5, effort=2)
**Classification**: Strategic investment
**Confidence**: High

**What to change**: In `autom8y-asana/src/autom8_asana/services/gid_push.py`, replace the
leaf-calibrated guard (`return True  # Nothing to push is not a failure` at `:328` and `:554`)
SPECIFICALLY ON THE VOCAB PATH with a referential-coverage hard-refuse: empty Asana read →
REFUSE+ALERT; truncated (missing any FK-referenced key in the coverage union) →
REFUSE+ALERT; healthy full set → publish. The leaf guard REMAINS correct for gid-mappings and
account-status paths. Only the vocab path gets the hard-refuse.

**Coverage union must include ALL THREE FK edges**: int edges `_advertising.py:80` (campaigns)
+ `:326` (asset_verticals ~43K) + STRING edge `_platform.py:162` (offers.category). The
STRING edge is the commonly-omitted hazard (FR-004/RR4 in rnd/shape).

**Why it matters**: The existing `return True` guard is leaf-calibrated. For the FK-parent
SPOF hub, a truncated read that applies partial renames can de-align the STRING FK
(`Offer.category` at `_platform.py:162`) with no transactional rollback. The additive-upsert
design already handles the empty-WIPE case (adds nothing, deletes nothing because the verticals
dimension has no `source` column — `_platform.py:497-498` confirms snapshot-replace is
structurally impossible on verticals). The hard-refuse guards the truncated-rename residual.

**Acceptance criterion (RED→GREEN)**: Mock empty `enum_options` → assert HARD-REFUSE (does
NOT reach `gid_push.py:328/:554` "nothing to push is not a failure" on the vocab path). Mock
truncated (missing a FK-referenced key) → assert HARD-REFUSE+ALERT. Mock healthy full set →
assert publish proceeds. RED = empty/truncated read reaches the data store.

### REC-3 — Implement dual-unique rename guard on the UPDATE-name path

**Addresses**: R3 (dual-unique rename collision on the net-new update path)
**Leverage**: 2.0 (impact=4, effort=2)
**Classification**: Strategic investment
**Confidence**: High

**What to change**: In the `VerticalService` UPDATE-name path (net-new per REC-1), implement
the name-uniqueness guard before issuing `UPDATE SET name=…`. Three scenarios: (a) rename
collision (another `vertical_key` row already holds the target name) → per-row WARN +
refuse-the-row; (b) name-swap A↔B → require two-phase update through an intermediate name;
(c) safe rename → proceed with UPDATE.

**Why it matters**: `verticals.vertical_name` carries a UNIQUE constraint (`_platform.py:147`).
A naive `ON DUPLICATE KEY UPDATE name=VALUES(name)` that collides on the name unique index
will throw a MySQL constraint exception. If mishandled via catch-and-skip, the store goes
stale without surfacing failure. This concentrates on the UPDATE-name path — net-new behavior,
since `VerticalService.create` is create-only today (`:149/:212`). Asana OWNS rename
authority, so renames WILL occur; the guard is non-optional.

**Acceptance criterion (RED→GREEN)**: Rename to a name held by another key → assert
deterministic handling (WARN+refuse-the-row, not raw MySQL throw). Name-swap A↔B test →
assert two-phase succeeds. RED = naive single-statement UPDATE throws MySQL constraint
exception uncaught, or silently skips, leaving store stale.

### REC-4 — Include the offers.category STRING-FK edge in the producer coverage union

**Addresses**: R4 (offers.category STRING-FK fragility on key rename)
**Leverage**: 2.0 (impact=4, effort=2)
**Classification**: Strategic investment
**Confidence**: High

**What to change**: In the producer referential-coverage query (part of REC-2's hard-refuse
guard), the coverage union MUST include the STRING FK edge: `_platform.py:162`
(`Offer.vertical_key → verticals.key`, column `category`) alongside the INT FK edges
(`_advertising.py:80` campaigns, `:326` asset_verticals). This is the "FR-004 third union
clause" from the rnd handoff, now carrying arch-level endorsement.

**Why it matters**: The STRING FK (`Offer.category`) is NOT referentially constrained at the
DB level — string references bind by value, not by ID. An orphaned string does not raise a
FK violation; it just silently stops resolving. This is the most fragile path and the most
commonly omitted from coverage queries (it looks like a column name alias, not a FK edge).

**Acceptance criterion (RED→GREEN)**: Coverage query returns the union of all three
edge-classes. Deliberate key rename → hard-refuse fires. RED = coverage query omits the
STRING FK edge and a renamed key orphans Offer.category references silently.

### REC-5 — Home the typed contract model in `autom8y-core` SDK

**Addresses**: F5, R6 (schema-drift release-coupling)
**Leverage**: 1.5 (impact=3, effort=2)
**Classification**: Strategic investment
**Confidence**: Medium (conditional on implementation choice; the risk is real if duplicated)

**What to change**: Define `VocabularySyncRequest` and `VocabularySyncResponse` once in
`autom8y-core` (`sdks/python/autom8y-core/src/autom8y_core/`), imported by both
`autom8y-asana` and `autom8y-data`. Both repos already pin `autom8y-core>=4.2.0,<5.0.0`
uniformly (dependency-map U-4 RESOLVED). The SDK is the established shared-model home
(`data_intake.py:473` `VerticalsListResponse`).

**Why it matters**: The current untyped seam is the telos target. If the fix introduces TWO
typed model definitions that can drift independently, it recreates the coordination problem at
the type-system level. The SDK typed conduit is the precedent for cross-repo shared types.

**Acceptance criterion (RED→GREEN)**: Both repos import the contract model from
`autom8y_core`; no independent `VocabularySyncRequest`/`Response` class definition in either
repo's source tree. RED = two divergent model definitions across repos.

### REC-6 — ACCEPT-AS-IS: vocabulary fragmentation (4-conduit) is a long-term watch

**Addresses**: R5 (vocabulary fragmentation — ads parallel canonical list drift)
**Leverage**: 0.6 (impact=3, effort=5)
**Classification**: Long-term transformation
**Confidence**: High (fragmentation is real; registry trigger condition is not met)
**Designation**: ACCEPT-AS-IS for this initiative's scope; watch-registered under DEFER-1

**Rationale**: The 4-conduit read-side fragmentation (SDK #1 typed, ads-local normalizer #2,
sms-local fields #3, scheduling shared-FK #4) is a real fragmentation anti-pattern
[AQ:SRC-005 Mo et al. 2015]. However: (a) it is a READ-side concern; the telos addresses the
WRITE seam; (b) the fleet registry is a one-way door (DEFER-1); (c) DEFER-1 N<3 gate has not
fired (only 1 vocab consumer for `/vocabularies/sync`); (d) the 4-consumer count is
fragmentation EVIDENCE, not the DEFER-1 escalation TRIGGER. The per-instance contract improves
the write-seam source-side; read-side unification requires the deferred fleet registry.

**DEFER-1 escalation trigger (NOT this scope)**: When a 2nd `field_key`-class vocabulary
binds `/vocabularies/sync` AND a 3rd consuming service materializes the vocabulary (N≥3
conjunction), escalate to platform architecture + leadership. The 4 consumers are fragmentation
evidence, NOT the trigger. Do not build the registry pre-trigger (one-way door).

**Cross-rite note**: ads' `VerticalNormalizer` ([ads] `api/creative_performance.py:90`) may
be intentional bounded-context divergence or accidental drift — Unknown U-B. Routed as
CRR-002 to debt-triage for characterization.

### REC-7 — First-sync ORPHAN-RISK dry-run before the first live publish

**Addresses**: R7 (first-sync key-mismatch)
**Leverage**: 1.5 (impact=3, effort=2)
**Classification**: Strategic investment
**Confidence**: High

**What to change**: Before the first live publish (shape sprint-4), implement a read-only
reconciliation dry-run that classifies each Asana option against the existing `verticals.key`
set as MATCH / INSERT-CANDIDATE / ORPHAN-RISK. REFUSE the first real sync on ANY ORPHAN-RISK
result; emit a reconciliation report; mutate nothing. This is FR-008 from the rnd handoff,
now carrying arch endorsement.

**Why it matters**: The `vertical_key` is derived from the Asana option NAME via normalization
(`normalize(option.name) → vertical_key`). If existing `verticals` rows were inserted with a
different normalization scheme, the first sync creates parallel key rows rather than matching
→ duplicate verticals → FK fan-in inconsistency. The dry-run detects this BEFORE the store is
touched.

**Acceptance criterion (RED→GREEN)**: Dry-run classifies every option; ORPHAN-RISK detection
fires and REFUSES the first sync when stale keys exist. Dry-run mutates nothing. RED = first
live publish re-keys existing verticals and orphans FK children.

### REC-8 — Typed seam (the telos target itself)

**Addresses**: R8 (untyped `str` seam — the overarching telos deliverable)
**Leverage**: 1.5 (impact=3, effort=2)
**Classification**: Strategic investment (the CORE deliverable; listed for R8 completeness)
**Confidence**: High

**What to change**: Replace `"vertical": str(vertical)` at `gid_push.py:490` (producer) and
`vertical: str = Field(...)` at `models_comparison.py:62` (consumer) with the typed
`VocabularySyncRequest` (home in SDK per REC-5). This IS the telos target.

**Acceptance criterion (RED→GREEN)**: Post-contract, the seam carries a typed/validated vocab
payload on the vocab path. RED = untyped `str(vertical)` still crosses the seam on the vocab
path after the contract is built.

---

## 4. Migration Path: Six Sources → Single Typed Pipeline

**Current state**: 6 vertical materialization sources, 4 downstream consumers, no typed sync
contract.

**Target state**: One authoritative pipeline (#4 Asana `enum_options` → #6
`data.verticals`) + Asana-deferring door (#5 `SEMANTIC_ANNOTATIONS`, re-pointed to #4) +
frozen-legacy (#1/#2/#3 isolated and inert).

**Arch corrections applied to the migration**: The migration uses `VerticalService.create`
(extended with upsert) as the write path — NOT a bespoke `vocab_upsert` store. MySQL shape-B
primitives govern the upsert syntax. Account-status semantics are explicitly excluded.

### Migration Phases (reconciled with shape.md M0-M4 and the 6-sprint DAG)

| Phase | Shape Sprint | What Lands | Arch Correction Applied | Observable Trigger | Reversible Rollback |
|-------|-------------|------------|------------------------|-------------------|---------------------|
| M0 — Design Lock | sprint-0 | Contract spec locked; EC-1 verdict (MySQL); SDK model home decision | F2 (EC-1 settled), F5 (SDK home), F7 (live anchors) | `ADR-dyn-enum-contract-shared-contract.md` authored with `{path}:{line}` EC-1 receipt | Cancel sprint-0 → no code touched |
| M1 — Consumer endpoint (data, deploy-first) | sprint-2 | NEW `POST /api/v1/vocabularies/sync`; `VerticalService` upsert extension; `GET_LOCK`/`RELEASE_LOCK` | F1/REC-1 (route-through-VerticalService); F2 (MySQL lock); REC-3 (rename guard) | Consumer endpoint live, producer flag OFF (ship-dark) | Revert consumer PR → endpoint disappears; no producer impact (flag OFF) |
| M2 — Producer push (asana, ship-dark) | sprint-1 (parallel with M1) | Producer hard-refuse guard; NAME-keyed snapshot; flag OFF at merge | F4/REC-2 (hard-refuse); REC-4 (STRING-FK coverage) | Producer code deployed, flag OFF; canary confirms REFUSE+ALERT | Revert producer PR → flag gate remains OFF; no data impact |
| M3 — Live enable (operator lever) | deploy-order | Producer flag flipped ON | Enable-ordered: consumer deployed BEFORE producer enabled (CON-010/BC-1) | First live vocab push; drift observer active | Flag OFF → producer push disabled; no dimension state lost (additive, no deletes) |
| M4 — Legacy sequencing | sprint-4 | First-sync dry-run; sources #1/#2/#3 documented FROZEN; source #5 re-pointed to #4 (EC-4 gate) | REC-7 (first-sync ORPHAN-RISK); EC-4 consumer-compat check blocks live flip if compat fails | Reconciliation report: MATCH/INSERT-CANDIDATE/ORPHAN-RISK; no mutations | Dry-run mutates nothing; EC-4 blocks the live flip if compat fails |
| M5 — Rite-disjoint attestation | sprint-5 | LIVE round-trip test; verified-realized attestation by review-rite disjoint critic | All corrections in place | PT-07 issues verified-realized attestation | Withhold routes back to 10x-dev for named deficiency |

**DEFER-1 boundary (NOT in migration scope)**: The fleet cf-contract REGISTRY (moonshot
Option-F) is out of scope. The per-instance contract with 3 compose-up locks is the correct
stopping point at N<3. Escalate-only at the N≥3 conjunction (2nd `field_key` binds
`/vocabularies/sync` AND 3rd consuming service materializes vocabulary). G-PROPAGATE: the
shared contract IS the propagation point; validate compose-up without building the registry.

---

## 5. Cross-Rite Referrals

### Cross-Rite Referral: CRR-001
- **Target Rite**: dre (autom8y-data native data-reliability rite)
- **Concern**: Sprint-2 consumer build lands in `autom8y-data`, whose `ACTIVE_RITE=dre` (live-verified 2026-06-30 per `dyn-enum-contract.shape.md §3`). The FK-parent additive-upsert correctness, orphan-risk guard, and real-data-landing proof are the exact domain of `dre` (`integrity-architect`, `pipeline-steward`, `source-load-analyst`, `change-warden`).
- **Evidence**: PT-02 fork in `dyn-enum-contract.shape.md §3`; [C] `services/vertical.py:212` (sole canonical writer); [C] `_advertising.py:326` (asset_verticals ~43K FK rows); [C] `api/services/forwarding_binding_store.py:155/:218/:252/:315` (shape-B live exemplar in the consumer)
- **Suggested Scope**: Sprint-2 (autom8y-data PR): implement NEW `POST /api/v1/vocabularies/sync` endpoint + extend `VerticalService.create` with upsert (INSERT-new / UPDATE-name-safe / NEVER DELETE) + `GET_LOCK`/`RELEASE_LOCK` serialization + referential-coverage union including the STRING FK edge + reject unknown fields 422. Verify FK-integrity and additive-only invariant on staging.
- **Priority**: BLOCKING — consumer endpoint must deploy BEFORE producer push is enabled (CON-010/BC-1). Operator must resolve PT-02 (10x-dev-synced-into-data vs dre-native) before sprint-2 starts. Not polish; this is the hard deploy-order gate.

### Cross-Rite Referral: CRR-002
- **Target Rite**: debt-triage
- **Concern**: Six vertical materialization sources + 4-conduit read-side fragmentation are a vocabulary-drift surface. Specifically: (a) legacy sources #1/#2/#3 (`autom8` contente_api `Vertical(Enum)` at [L] `main.py:19`, `VERTICAL_NAMES` at `main.py:261`, `db_verticals()` at `main.py:12`) are isolated/frozen but unretired; (b) ads `VerticalNormalizer` ([ads] `creative_performance.py:90` import `:24`) is a parallel vocabulary authority whose intent is Unknown U-B.
- **Evidence**: [L] `apis/contente_api/models/vertical/main.py:19/:261/:12`; [ads] `api/creative_performance.py:90`; dependency-map §9 Shared Model Registry "diverged (ads owns a parallel vocab)"
- **Suggested Scope**: (a) Characterize ads `VerticalNormalizer` as intentional bounded-context divergence or accidental drift; document. (b) Document legacy frozen sources (#1/#2/#3) as tech-debt with retirement plan (isolated, low-urgency, but cluttering the six-source picture). (c) Assess whether sms denormalized fields (`models/conversation.py:169`) should be unified post-DEFER-1.
- **Priority**: Medium — non-blocking for the current telos; escalation trigger for the DEFER-1 registry if ads drift is confirmed as unintentional.

### Cross-Rite Referral: CRR-003
- **Target Rite**: security
- **Concern**: EC-2 credential path — the live Asana PAT fetch uses AWS Secrets Manager `autom8y/asana/asana-pat`. This is operator-shell-only access currently. The credential scope for the cache-warmer runtime must be confirmed.
- **Evidence**: [P] `services/gid_push.py:62` `GID_PUSH_ENABLED_ENV_VAR` (feature flag governing the push); frame `dyn-enum-contract.md` EC-2 note; rnd handoff EC-2 `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/EC-2-credential-path]`
- **Suggested Scope**: Verify the IAM/role binding for the cache-warmer runtime to AWS Secrets Manager `autom8y/asana/asana-pat`. Confirm whether the runtime execution context has the secret-fetch scope (do NOT assume CI parity). If runtime access is not established, surface the gap to the 10x-dev build as EC-2 blocking criterion for sprint-1.
- **Priority**: High — must be resolved before enabling the producer push (sprint-1 entry criterion). Not blocking for design-lock (sprint-0) but blocking for the first live publish.

### Cross-Rite Referral: CRR-004
- **Target Rite**: hygiene
- **Concern**: (a) The current asana→data seam carries an untyped `str` for the vertical vocabulary (`gid_push.py:490` `"vertical": str(vertical)` → `models_comparison.py:62` `vertical: str`). This pattern may recur across the fleet. (b) The producer push helper (`gid_push.py:163`) is a general-purpose 2-path helper shared by gid-mappings (`:338`) and account-status (`:563`); the vocab-sync concern is not cleanly modularized within the producer (architecture-assessment §7.c "MODERATE" module-to-domain alignment for the producer push conduit).
- **Evidence**: [P] `gid_push.py:490` (untyped producer); [C] `models_comparison.py:62` (untyped consumer); [P] `gid_push.py:163/:338/:563` (shared helper architecture); architecture-assessment §7.c
- **Suggested Scope**: Code-quality review of the producer push module for modularization improvement. Fleet-wide scan for other untyped inter-service field payloads similar to `"vertical": str(...)`.
- **Priority**: Low-Medium — the dyn-enum-contract telos itself closes the vertical seam type-safety gap; the hygiene concern is the broader fleet pattern.

---

## 6. Unknowns Registry

All unknowns from all four upstream phases, deduplicated and organized by impact severity.

### HIGH IMPACT

#### Unknown: Gate-A OPEN — telos DRAFT, NOT countersigned
- **Question**: Has the operator countersigned `.know/telos/dyn-enum-contract.md`?
- **Why it matters**: Per `telos-integrity-ref` §3 Gate-A, the 10x-dev BUILD cannot start until the user-sovereign telos is countersigned. `/frame` and `/shape` proceeded against the draft; the build is BLOCKING-gated on Gate-A CLOSED.
- **Evidence**: `.know/telos/dyn-enum-contract.md` frontmatter `ratified_by: "[PENDING — operator (Tom Tenuta) countersign]"` + `ratification_status: "DRAFT — PENDING OPERATOR COUNTERSIGN (drafted 2026-06-30)"`. Two `[OPERATOR-SET]` fields (`verification_deadline` = 2026-07-23, `rite_disjoint_attester` = review-rite external critic) await confirmation.
- **Suggested source**: Operator action — review `.know/telos/dyn-enum-contract.md`, confirm or amend the two `[OPERATOR-SET]` fields, then countersign (then `ari sync --rite=10x-dev` + ONE CC restart).

#### Unknown: U-A — committed 2nd `asana_configured` vocab on the roadmap?
- **Question**: Does the product roadmap have a committed second vocabulary (beyond `vertical`) to sync through the seam in the foreseeable horizon?
- **Why it matters**: Resolves whether the generic endpoint's `field_key` discriminator is a sound forward hedge (thin, no committed 2nd vocab) or a speculative-generality bet (thin today, committed soon). Also informs DEFER-1 escalation timing.
- **Evidence**: [P] `annotations.py:50` `VALID_VALUES_SOURCES = frozenset({"hardcoded","asana_configured","mixed"})` (3 modes; only `vertical` is `asana_configured`/`dynamic` on the traced surface); DEFER-1 N<3 confirmed (PV-preflight PREMISE-5).
- **Suggested source**: Product roadmap owner / platform architecture.

#### Unknown: U-B — ads `VerticalNormalizer` intentional or accidental drift?
- **Question**: Is ads' `VerticalNormalizer` an intentional parallel vocabulary authority (domain-specific vertical groupings for ad-scoring) or accidental duplication that should bind the canonical store?
- **Why it matters**: Determines R5 severity and DEFER-1 registry urgency. If intentional, accept-and-document. If accidental, R5 severity is higher.
- **Evidence**: [ads] `api/creative_performance.py:90` + import `:24` `from autom8_ads.intelligence.vertical_scoring`; dependency-map §9 "diverged (ads owns a parallel vocab)".
- **Suggested source**: ads-service domain owner. Routed as CRR-002 to debt-triage.

### MEDIUM IMPACT

#### Unknown: U-1 (carried) — FK fan-in row counts (blast-radius magnitude)
- **Question**: Actual row counts on `asset_verticals` (~43K asserted by spike), `campaigns`, `offers`, and other inbound verticals FK tables.
- **Why it matters**: Sizes the blast-radius MAGNITUDE of R1/R2. Structural severity classification is HIGH regardless; row counts quantify cascade depth.
- **Evidence**: Structural FK edges confirmed (dependency-map §2.a); no DB creds in env. `[UV-P: asset_verticals + inbound-FK row counts | METHOD: bash-probe (live MySQL SELECT COUNT) | REASON: no DB creds at this altitude; operator with creds is the attester]`
- **Suggested source**: Live MySQL query by operator or DBA with creds.

#### Unknown: EC-2 (carried) — live Asana credential path scope
- **Question**: Does the cache-warmer runtime have the IAM scope to fetch `autom8y/asana/asana-pat` from AWS Secrets Manager, or is it operator-shell-only?
- **Why it matters**: If the warmer runtime lacks the scope, the live Asana read cannot execute in production — a build-blocking gap for sprint-1 live probe.
- **Evidence**: Frame `dyn-enum-contract.md` EC-2 note; rnd handoff EC-2 `[UNATTESTED — DEFER-POST-HANDOFF]`. Routed as CRR-003 to security.
- **Suggested source**: IAM/cloud-infra team; security rite review (CRR-003).

#### Unknown: U-C — `values_source:"mixed"` semantics
- **Question**: When is a field's `values_source` `"mixed"` vs `"asana_configured"`?
- **Why it matters**: The `vertical` field is `asana_configured` (no immediate impact). A generic `/vocabularies/sync` could eventually handle a `"mixed"` vocab — the contract must handle all three modes in the door.
- **Evidence**: Sole occurrence at [P] `annotations.py:50`; zero dispatch/consumer logic in the producer (dependency-map U-7 resolved partial). The `"mixed"` value is OFF the vertical path today.
- **Suggested source**: Producer-domain owner / git history of `annotations.py`.

### LOW IMPACT (RESOLVED)

| Unknown | Resolution | Receiving station |
|---------|-----------|-------------------|
| U-2 resolver-flag completeness | No resolver-level env-flag; sole gate = `gid_push.py:62 GID_PUSH_ENABLED` | RESOLVED — dependency-map §7 |
| U-3 DuckDB write-consumer | NEGATIVE — no analytics write to verticals dimension | RESOLVED — dependency-map §7 |
| U-4 SDK pin matrix | Uniform `>=4.2.0,<5.0.0` across 4 Python consumers | RESOLVED — dependency-map §7 |
| U-5 owning models of `_platform.py:72/:451` | `:72` = Business (table chiropractors); `:451` = Question (table questions) | RESOLVED — dependency-map §7 |
| U-6 scheduling local-vs-shared | Shared-schema FK consumer (no local verticals table) | RESOLVED — dependency-map §7 |
| U-7 "mixed" values_source | ZERO dispatch logic on vertical path; general semantics undefined-in-code (UV-P carried) | RESOLVED PARTIAL |

---

## 7. Scope and Limitations

This architecture report covers the **structural design dimension** of the `dyn-enum-contract`
initiative. The following dimensions are explicitly NOT covered and may be partially addressed
by other rites or require human assessment:

- **Runtime behavior**: Performance characteristics (sync latency, throughput under concurrent
  writes, MySQL advisory lock contention under high write concurrency). The `GET_LOCK`/
  `RELEASE_LOCK` serialization is prospective (0 hits in consumer tree); its runtime behavior
  under concurrency is unassessed here. → Relevant to sre / dre rite.

- **Data architecture**: Actual row counts in FK tables (U-1 — UV-P carried), data retention
  policy for disabled Asana options, and the disabled-option policy (RR2 in shape.md —
  operator-judgment item for the build). → Relevant to dre / data governance.

- **Operational concerns**: Deployment pipeline sequencing (consumer-deployed-before-producer-
  enabled is documented as CON-010 but its operational enforcement is not assessed here),
  observability coverage (NFR-004 publish-count canary metric is in the rnd handoff but not
  assessed here), incident response readiness if the advisory lock deadlocks.

- **Organizational alignment**: PT-02 consumer-repo rite (autom8y-data is natively `dre`, not
  `10x-dev`) is an operator decision, not an arch decision. Conway's Law effects (team
  ownership boundary between asana and data) are surfaced as CRR-001 but not analyzed.

- **Evolutionary architecture**: Fitness functions for the compose-up locks (asserting
  `field_key` stays data-not-control-flow), DEFER-1 N≥3 trigger monitoring, and telos
  TELOS_OVERDUE deadline enforcement (2026-07-23 proposed). Watch-registered but not
  implemented here.

- **Rite-disjoint validation**: This report is MODERATE-ceilinged (self-referential authorship
  ceiling per `self-ref-evidence-grade-rule`). The arch-adversary (sprint-5 of the arch rite)
  provides TL-A/TL-B/TL-C challenge grounding and is the MODERATE-ceiling gate. The external
  rite-disjoint critic (review rite, at the cross-rite residency exit) is the STRONG-upgrade
  path at the production-grade verified-realized attestation gate.

---

## 8. Migration Readiness Assessment (DEEP-DIVE)

### 8.1 Readiness Score

| Dimension | Score | Basis |
|-----------|-------|-------|
| Design clarity | HIGH | 7 arch corrections surfaced; validated design is unambiguous at the authored rung |
| Structural risk coverage | HIGH | R1–R8 all have falsifiable RED→GREEN acceptance criteria; write-path integrity centralized |
| EC-1 resolution | SETTLED | MySQL confirmed by 7 live receipts; shape-B implication identified; PostgreSQL canary refuted |
| Gate-A telos | OPEN | Draft authored and countersign-ready; operator countersign is the blocking prerequisite |
| PT-02 consumer-repo rite | UNRESOLVED | Operator fork — 10x-dev-synced-into-data vs dre-native; escalate to operator |
| EC-2 credential scope | UNKNOWN | `[UNATTESTED — DEFER-POST-HANDOFF]`; security rite verification (CRR-003) required before live enable |

**Overall readiness**: CONDITIONALLY READY. Design is validated; two blocking dependencies
remain (Gate-A telos countersign + PT-02 operator fork). No structural blockers; all remaining
gates are process/operational. The design is the most unblocked it can be at the arch rung.

### 8.2 Decomposition Health

The initiative decomposes cleanly into two independently-buildable halves (producer/asana +
consumer/data) with a single hard-gate dependency at the deploy-order edge (consumer deployed
BEFORE producer enabled — CON-010/BC-1). Build-parallel; enable-ordered. This is healthy
decomposition: the critical path is well-bounded, parallelism is preserved, and the enable-
ordered constraint is observable via the feature flag at `gid_push.py:62`.

**Health signal — the single genuinely-new component**: With REC-1 routing through
`VerticalService`, the "CRITICAL new code" surface narrows to: (a) the UPDATE-name extension
to `VerticalService.create` (the upsert half — a focused service-layer extension), and (b) the
`GET_LOCK`/`RELEASE_LOCK` advisory lock invocation (a MySQL primitive; pattern-established by
`forwarding_binding_store.py:155/:218`). The rest composes existing patterns. This is a sign
of healthy decomposition — the novel surface is small and well-bounded.

**Coupling health**: Stable reference hub (I≈0, correct). Single-writer (correct). Additive-
only (correct). The only unhealthy coupling is the untyped seam — the one the telos closes.
No new structural coupling is introduced by the validated design.

### 8.3 Confidence by Phase

| Phase | Confidence | Key dependency |
|-------|-----------|----------------|
| Sprint-0 design-lock | HIGH | None — EC-1 settled by arch inspection |
| Sprint-1 producer | HIGH | None — hard-refuse pattern established by canary2; flag-gated |
| Sprint-2 consumer | HIGH | PT-02 operator fork must be resolved before starting |
| Sprint-3 coherence | HIGH | None — drift-gate pattern established by gfr-dynvocab precedent |
| Sprint-4 reconciliation | MEDIUM | EC-4 (schema-discovery compat gate) could block the live #5 re-point |
| Sprint-5 attestation | MEDIUM | rite-disjoint critic must be engaged (propose review rite per telos draft) |

---

## 9. Phased Remediation Roadmap (DEEP-DIVE)

> Arch does NOT author production code or execute any phase. The roadmap is a validated design
> for 10x-dev (and dre for sprint-2) execution. Production-mutating levers are the operator's.
> Effort estimates are inherited from the rnd handoff (~6.5 person-days total) and adjusted
> by arch corrections.

### Phase 0 — Design-Lock (sprint-0): ~0.5 person-days (design only, no code)

Author `ADR-dyn-enum-contract-shared-contract.md` at
`.ledge/decisions/ADR-dyn-enum-contract-shared-contract.md` with:
- EC-1 verdict: MySQL (cite `core/config.py:217/:222`)
- Shared cross-repo contract spec: three compose-up locks (generic path + `field_key='vertical'`
  + NAME-keying `vertical_key`)
- SDK model home decision (per REC-5): `VocabularySyncRequest`/`Response` in `autom8y-core`
- Entry-gate ledger: EC-1..4 status; Gate-A status

**Arch corrections applied**: F2 (EC-1 MySQL), F5 (SDK model home), F7 (live anchors).
**Entry gate**: Gate-A CLOSED (operator countersigns `.know/telos/dyn-enum-contract.md`).

### Phase 1 — Consumer Endpoint (sprint-2): ~3 person-days (autom8y-data, post PT-02 resolution)

NEW `POST /api/v1/vocabularies/sync` route (generic path, `field_key` discriminator,
`extra=forbid`, S2S JWT + rate-limit + fleet envelopes — parity with
`account_status.py:41`). Extend `VerticalService.create` (`services/vertical.py:149/:212`)
with upsert path: INSERT-new / UPDATE-name-when-safe / NEVER DELETE. `GET_LOCK`/
`RELEASE_LOCK` advisory lock per `field_key`. Referential-coverage union: ALL THREE FK edges
(campaigns `_advertising.py:80` + asset_verticals `_advertising.py:326` + offers.category
STRING `_platform.py:162`).

**Arch corrections applied**: F1/REC-1 (route-through-VerticalService — NOT bespoke vocab_upsert
store); F2 (MySQL `ON DUPLICATE KEY UPDATE`); F3 (envelope shape YES / snapshot-replace
semantics NO — do NOT copy `account_status_store.py:82-143`); REC-3 (dual-unique rename guard).

**Deploy gate**: Consumer endpoint deployed to production BEFORE producer push enabled
(CON-010/BC-1). Estimate: 3 person-days (comparable to the rnd's G6 estimate, with the
VerticalService extension replacing the bespoke store; net complexity is similar).

### Phase 2 — Producer Push (sprint-1): ~2 person-days (autom8y-asana, parallel with Phase 1)

Read live Asana `enum_options` (`custom_field.py:113`). Project NAME-keyed snapshot. Push via
`_push_to_data_service` (`gid_push.py:163`) to `/api/v1/vocabularies/sync`. REPLACE leaf
guard (`gid_push.py:328/:554`) on the vocab path with referential-coverage HARD-REFUSE
(STRING-FK coverage included per REC-4). Ship with `GID_PUSH_ENABLED` flag OFF (ship-dark).

**Arch corrections applied**: F4/REC-2 (hard-refuse replacing leaf guard); REC-4 (STRING-FK
coverage in the union); F7 (live line numbers). Producer ENABLE waits on Phase 1 consumer
deployed.

### Phase 3 — Coherence + Live Enable (sprint-3 + operator deploy-order): ~1 person-day

Drift observer (WARN-not-codegen, ADR-S4-001). Compose-up-ready contract seed (3 locks so
2nd `field_key` is a DATA addition). LIVE/integration harness (assertable cross-repo
round-trip; harness authoring — sprint-3; harness EXECUTION — after both endpoints deployed +
flag enabled). Operator flips `GID_PUSH_ENABLED` flag ON AFTER Phase 1 consumer deployed.

**Arch corrections applied**: F6 (generic endpoint thin watch — drift observer enforces non-
accretion of per-vocab dispatch; watch condition at sprint-3 exit PT-05).

### Phase 4 — Legacy Reconciliation + First-Sync Dry-Run (sprint-4): ~1 person-day (gated on P/C convergence)

Read-only dry-run classifying each Asana option as MATCH / INSERT-CANDIDATE / ORPHAN-RISK
against existing `verticals.key`. REFUSE first real sync on any ORPHAN-RISK. EC-4 consumer-
compat check before re-pointing `SEMANTIC_ANNOTATIONS` source #5 to live Asana. Sources
#1/#2/#3 documented FROZEN (no action needed beyond documentation — already isolated and zero
inbound import edges).

**Arch corrections applied**: REC-7 (first-sync ORPHAN-RISK guard). Gated on sprints 1 + 2
both landed (P/C convergence).

### Phase 5 — Rite-Disjoint Critic Attestation (sprint-5): ~0.5 person-days (review rite)

Review-rite disjoint critic (rite-disjoint from 10x-dev author) runs LIVE/integration harness
and issues verified-realized attestation against the user-countersigned telos. Signal-sifter
runs the shell-heavy live round-trip (the only review agent with Bash, per the review-rite
agent capability map). Self-grade caps MODERATE; STRONG requires this rite-disjoint
attestation.

**Total estimate**: ~7.5 person-days (consistent with rnd's "~6.5 person-days build +
sprint-0 entry-criteria resolution"; arch corrections add ~0.5–1 day for the VerticalService
upsert extension but eliminate the bespoke store's complexity — net wash).

**Note on both critics**: The in-rite arch-adversary (sprint-5 of the ARCH rite, THIS
workflow) gates the HANDOFF artifact — it challenges the DESIGN claims at MODERATE ceiling.
The review-rite disjoint critic (sprint-5 of the BUILD workflow in shape.md) gates the
verified-realized TELOS claim — it attests the LIVE build at STRONG. Two distinct critics,
two distinct gates, two distinct claim-scopes. Never conflate.

---

## Evidence Grade Ceiling

`[STRUCTURAL | MODERATE]` — self-referential authorship ceiling per G-CRITIC /
`self-ref-evidence-grade-rule`. This station's architecture synthesis caps at MODERATE.
Individual upstream receipt-level evidence carries High/Medium confidence from the map and
topology stations. The synthetic ARCHITECTURE CLASSIFICATION (boundary alignment, anti-pattern
severity, recommendation ranking) is MODERATE-ceilinged.

STRONG requires: (a) the in-rite arch-adversary (sprint-5 of the arch rite) TL-A falsifiable-
prediction challenge; (b) the rite-disjoint external critic at cross-rite residency exit.

**Rung**: `authored`. Status: `draft` (WIP-uncommitted; no auto-commit; dirty tree not
staged per no-auto-commit discipline).
