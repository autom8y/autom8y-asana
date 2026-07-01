---
type: spike
status: draft
slug: dyn-enum-contract
wave: 4 (moonshot-architect)
upstream: .ledge/spikes/PROTO-dyn-enum-contract.md (wave 3 — GO)
downstream: tech-transfer (wave 5)
evidence_grade: "[STRUCTURAL | MODERATE]"
time_horizon: "2+ years"
---

# MOONSHOT-dyn-enum-contract

> rnd /spike — Wave 4 (moonshot-architect). Design prose + diagrams-in-text. NO production code, NO telos authoring.
> Long-horizon (2+ yr) architecture for a contractualized dynamic enum-option vocabulary that syncs cross-service,
> and the migration path OFF the legacy six-sources-of-truth toward it.
> Evidence ceiling **MODERATE** — self-referential (designing the fleet's own future from inside) per
> `self-ref-evidence-grade-rule`; rnd-dk literature caps at MODERATE. PROVEN (Wave-3 canaries) is distinguished
> from PROJECTED (this design) in §0.4 and throughout.
> SVR discipline: production-primitive claims carry a `{path}:{line}` receipt verified at authoring time, or `[UV-P]`.

---

## 0. Frame

### 0.1 Executive Summary

The Wave-3 prototype proved the **mechanism** for one option-set (`vertical`): additive-upsert keyed on a
portable name (`vertical_key`) is safe on the FK-parent `verticals` table where snapshot-replace orphans 43k
rows, and an FK-parent-calibrated hard-refuse guard correctly discriminates empty/truncated Asana reads from
healthy ones. **This wave answers the altitude question the scout and integration deferred to me: is the
`Vertical`-option-set sync a one-off, or the FIRST INSTANCE of a general pattern — the DEFER-1 fleet cf-contract
REGISTRY the gfr-dynvocab moonshot lodged?**

**Disposition: FIRST INSTANCE, by deliberate design — but the registry stays DEFER.** The per-instance contract
this spike builds *composes UP* into the fleet registry at cardinality-1→N **without a rewrite**, provided three
cheap, forward-compatible decisions are locked at build time (generic endpoint, `field_key` discriminator,
NAME-keying). The full registry (central authority / event bus / declarative coherence layer) is a **one-way
door once 2+ services bind** — it is held DEFER behind an explicit N≥3 trigger, exactly the escalation my prior
gfr-dynvocab moonshot dissent registered (`.claude/agent-memory/moonshot-architect/gfr-dynvocab-coherence-dissent.md`).

This plan: (1) defines four 2-yr scenarios + a black-swan section and stress-tests today's nine decisions against
each; (2) enumerates seven end-state architecture options and recommends the compose-up target; (3) resolves the
four residual risks Wave-3 deferred at design level; (4) sequences the migration OFF the six sources with
observable triggers, reversible rollback points, and one-way-door callouts; (5) states what survives, what is
reversible, and what to DEFER with a per-item escalation trigger.

### 0.2 Time Horizon

**2+ years.** Steady-state (M0–M3, the per-instance contract + source collapse) is a 1–2 quarter horizon; the
registry generalization (M4 / DEFER-1) is the 2+ year horizon gated on fleet growth signals.

### 0.3 The gfr-dynvocab HARD constraints the long-horizon design must NOT reopen

These are inherited as load-bearing. The registry end-state is built *on top of* them, never by relaxing them.

| HARD constraint | Source | Long-horizon stance |
|-----------------|--------|---------------------|
| **NAME-keying** — vocabulary keys on the canonical (normalized) option NAME; `enum_option.gid` / `vertical_id` are runtime handles only, never the cross-service key | gfr-dynvocab telos `.know/telos/gfr-dynvocab.md:47`; scout B.3 | **NEVER reopen.** Vindicated by Scenario S4 (Asana identity change). Re-keying onto gid is a one-way regression. |
| **ADR-S4-001 drift-gate-not-codegen** — schema codegen-FROM-model is forbidden; warn-first drift GATE is the mechanism | gfr-dynvocab telos `:78`; scout B.4 | **NEVER reopen.** The registry remains a snapshot-PUSH + drift-GATE; it must never auto-generate the data-side table or the Asana option-set from a model. |
| **FROZEN cf-type set** `{text,number,enum,multi_enum,date,people}` | gfr-dynvocab telos `:47`; scout B.2 | **NEVER reopen.** Option-set sync is a SIDECAR to the two closed-domain members (`enum`/`multi_enum`), never a 7th type. |
| **Strictly-additive to the certified spine** — 105 GFR tests, CERT-1 guard, CERT-3 round-trip are the inviolable regression gate | gfr-dynvocab telos `:51,79` | **NEVER reopen.** Every phase of this plan is additive; none re-opens the certified identity spine. |

### 0.4 PROVEN vs PROJECTED (evidence partition — honored throughout)

| Claim | Status | Anchor |
|-------|--------|--------|
| Additive-upsert preserves existing `id`s; FK children resolve after insert-new + update-in-place | **PROVEN** (Wave-3 canary 1, two-sided, teeth) | PROTO §2 |
| Snapshot-replace (DELETE+INSERT) orphans FK children or FK-blocks the DELETE | **PROVEN** (Wave-3 canary 1) | PROTO §2 |
| Leaf-calibrated empty guard returns `True` (no-op) on empty input | **PROVEN** (file-read + canary 2) | `gid_push.py:514-519` (re-verified this wave) |
| FK-parent hard-refuse guard discriminates empty/truncated from healthy | **PROVEN** (Wave-3 canary 2, two-sided) | PROTO §3 |
| `verticals.vertical_name` is `unique=True` (name-collision risk on `UPDATE SET name`) | **PROVEN** (file-read, NEW this wave) | `_platform.py:147` |
| `offers.category` is a STRING FK to `verticals.key` (distinct from int `vertical_id` edges) | **PROVEN** (file-read this wave) | `_platform.py:162` |
| `VerticalService` has no update/delete path; verticals permanent | **PROVEN** (file-read this wave) | `vertical.py:9-10,48` |
| The per-instance contract composes UP to the registry without a rewrite | **PROJECTED** (design) | §2 |
| Concurrent-upsert correctness under overlapping syncs | **PROJECTED / UV-P** | §3 RR1 |
| First-sync reconciliation against live Asana payload | **PROJECTED / UV-P** | §3 RR3 |
| The DB engine of the `verticals` table (Postgres vs MySQL — determines upsert syntax + lock primitive) | **UNRESOLVED / UV-P** — priors disagree (INTEGRATE C2 "MySQL leaf" vs PROTO §4 "PostgreSQL staging") | §3 RR1 |

---

## 1. Future Scenarios (2+ yr) and the Stress-Test

Planning depth is allocated **proportional to probability** (anti-pattern register: Low-Probability Over-Investment).
S1/S2 are HIGH/MED-prob and get full treatment; S3/S4 get scoped treatment; the black-swan set gets one paragraph.

### 1.1 Scenario S1 — Vocabulary Proliferation (100x enum cf option-sets)

**Probability: HIGH. Impact if true: HIGH.**

**Assumptions:** the `vertical` option-set is one of many enum/multi_enum cf option-sets the fleet will want
synced. The `account-status` payload *already* leaks sibling vocabularies untyped — `pipeline_section`,
`account_activity` ride as free strings alongside `vertical` (`account_status_store.py:117-120`). Each is the
same drift class. As the fleet types its cross-service contracts, 1 synced option-set becomes 10s–100s.

**Observable signals (external, specific):**
- A 2nd option-set is added to a sync payload as an untyped `str` (a PR mirroring the `vertical:str` leak at
  `_account_status_sync.py:44`).
- A sibling endpoint is *proposed* — e.g. `POST /api/v1/pipeline-stages/sync` — the proliferation smell (N
  hand-built endpoints).
- `SEMANTIC_ANNOTATIONS.valid_values` accrues additional hardcoded option-sets observed drifting from Asana live
  (`resolver_schema.py:449`).

### 1.2 Scenario S2 — Fleet Fan-out (N>2 consuming services)

**Probability: MEDIUM. Impact if true: HIGH.**

**Assumptions:** today there is one producer (autom8y-asana) and one consumer (autom8y-data). The operator's
cited north star `scheduling-stratum/sync` is a 3rd consumer surface that is **not present at HEAD** (scout
confirmed absent in all three repos) but is anticipated. autom8y-stripe already reads verticals via the gRPC
`VerticalService` (`vertical.py:3-4`) — a latent 2nd consumer. When a 3rd+ service needs the vocabulary, the
single producer-push topology stops scaling.

**Observable signals:**
- A 3rd service requests the vertical vocabulary (scheduling-stratum materializes, or a reporting service binds).
- A consumer asks to PULL/subscribe rather than receive a PUSH (the fan-out inversion).
- The producer's `push_vocab_to_data_service` accretes a 2nd hardcoded consumer base-URL alongside
  `AUTOM8Y_DATA_URL` (`gid_push.py:498`).

> **S2 is the literal DEFER-1 N≥3 trigger.** It is the boundary case from my calibration anchors: "architecture
> requires orchestration topology change at scale" — a legitimate migration (push→pull/registry), not a failure.

### 1.3 Scenario S3 — The Invariant Inversion (a vocabulary that needs DELETE semantics)

**Probability: MEDIUM. Impact if true: MEDIUM-HIGH.**

**Assumptions:** `vertical`'s additive-only / DELETE-forbidden invariant is grounded in a domain fact —
"verticals are permanent" (`vertical.py:9`). A *general* registry will eventually hold a vocabulary that is NOT
permanent (campaign tags, seasonal categories, or a GDPR-mandated option removal). The global "never delete"
invariant becomes a **per-`field_key` policy**, not a fleet constant.

**Observable signals:**
- A vocabulary is proposed whose options are legitimately ephemeral.
- A regulatory/GDPR request requires hard-removal of an option value fleet-wide.
- Asana operators routinely *disable* (not just add) options on a synced field and consumers complain of staleness.

### 1.4 Scenario S4 — Asana Changes Its enum_option Identity Model

**Probability: LOW-MEDIUM. Impact if true: MEDIUM.**

**Assumptions:** Asana ships portable cross-workspace option IDs, or introduces option semantics (typed/
hierarchical options) or a name-collision (two options with identical display names). Vendor roadmap is exogenous.

**Observable signals:**
- Asana API changelog announces stable/portable enum_option identifiers or cross-workspace option refs.
- Asana permits two enum options with the same display name on one field (breaks the `normalize(name)→key` 1:1
  assumption).
- Asana version-bumps or deprecates the `custom_fields`/`enum_options` endpoint shape.

### 1.5 Stress-Test Table — which of today's nine decisions survive each scenario

Legend: **SURVIVES** (no change) · **MIGRATE** (planned, reversible change) · **VINDICATED** (the decision is
*why* the scenario is non-breaking) · **ONE-WAY** (crossing this under the scenario is irreversible — guard it).

| # | Today's decision (Wave 1–3) | S1 100x vocabs | S2 N>2 consumers | S3 DELETE-needing vocab | S4 Asana identity change |
|---|------------------------------|----------------|-------------------|--------------------------|---------------------------|
| D1 | NAME-keying on portable key (gid is a handle) | SURVIVES | SURVIVES | SURVIVES | **VINDICATED** (the insulation layer that makes S4 non-breaking) |
| D2 | Additive-upsert, DELETE-forbidden | SURVIVES (per-vocab) | SURVIVES | **MIGRATE** → per-`field_key` delete policy; flipping `vertical` itself = **ONE-WAY** | SURVIVES |
| D3 | Generic endpoint `/api/v1/vocabularies/sync` + `field_key` discriminator | **VINDICATED** (this is *why* S1 is non-breaking) | SURVIVES (carrier unchanged) | SURVIVES | SURVIVES |
| D4 | Producer PUSH (reuse `_push_to_data_service`) | SURVIVES (one producer, N vocabs is fine) | **MIGRATE/BREAK** → push→pull/subscribe; hardcoding N consumer URLs is the anti-pattern | SURVIVES | SURVIVES |
| D5 | Hard-refuse empty/truncated guard + referential-coverage | SURVIVES (coverage query parameterizes per `field_key`) | **MIGRATE** → coverage check moves consumer-side or into the registry (producer can't know every consumer's FK graph) | SURVIVES (the coverage check IS the delete-guard) | SURVIVES |
| D6 | Drift-gate-not-codegen (ADR-S4-001) | SURVIVES | SURVIVES | SURVIVES | SURVIVES |
| D7 | Asana live `enum_options` = single source-of-record | SURVIVES | SURVIVES | SURVIVES | SURVIVES (S4 only changes the *handle*, not the source-of-record) |
| D8 | FROZEN cf-type set; option-set is a sidecar | SURVIVES | SURVIVES | SURVIVES | SURVIVES (unless Asana adds a *type* — orthogonal, gfr-dynvocab's concern) |
| D9 | Per-consumer referential-coverage (FK keys must be present) | **MIGRATE** → parameterize per `field_key` | **MIGRATE** → per-consumer ownership | SURVIVES | SURVIVES |

**Reading of the table:** seven of nine decisions survive all four scenarios unchanged. The two pressure points
are **D4 (transport)** — push breaks at S2 fan-out — and **D2/D9 (write policy + coverage)** — which become
per-`field_key`/per-consumer parameters under S1/S3. Both are MIGRATIONS along pre-identified seams, not
re-architectures. **No scenario forces re-opening any of the four HARD constraints (§0.3).** The only ONE-WAY
crossings are: flipping `vertical`'s additive-only invariant (S3), and standing up a central registry authority
before the N≥3 trigger (S2). Both are explicitly guarded below.

### 1.6 Black-Swan section (what scenario planning cannot predict)

Per the calibration anchor distribution-assumption: these invalidate scenario *assumptions* wholesale and are
documented, not planned-for:
- **Asana platform discontinuity** — acquisition, API v2 rewrite, or `enum_options` deprecation invalidates the
  source-of-record (D7).
- **Regulatory source-of-record inversion** — if a US SaaS (Asana) becomes an impermissible system-of-record for
  EU customer vertical data, the contract *direction* inverts (data-side #6 becomes authoritative, Asana a mirror).
  NAME-keying (D1) and the generic carrier (D3) survive an inversion; the push direction (D4) does not.
- **Fleet consolidation** — autom8y-asana + autom8y-data merging eliminates the cross-service seam entirely,
  making the contract intra-process (the sync becomes a function call; the registry becomes a module).
- **LLM-driven schema inference** replacing the hand-curated annotation layer (#5) wholesale.

---

## 2. End-State Architecture — Enumerated Options + Recommended Target

Per `option-enumeration-discipline`: the slate below offers a **null option, three+ structurally-distinct
mechanisms, an external-flavored option, a delegation option, and a query-through (no-replica) option**. As the
self-referential author I cannot externally audit my own enumeration — this slate is offered to tech-transfer /
a rite-disjoint critic FOR enumeration audit before any registry commitment (the recommendation is held at
DEFER precisely so the audit precedes the one-way door).

### 2.1 The option slate

**Option NULL — Per-instance contract proliferation (current trajectory).**
Stay per-instance forever: every new option-set × every consuming service gets its own hand-built `/sync`
endpoint + store method, mirroring this spike. *Mechanism:* none new (extrapolated status quo). *Pro:* zero
new abstraction; each contract is independently simple. *Con:* N endpoints × M consumers; the fragmentation
this initiative escapes, re-grown one contract at a time. The "why not just keep cloning?" null.

**Option A — Centralized vocabulary registry service (new authority).**
A standalone registry microservice owns canonical option-set vocabularies; producers register, consumers
subscribe/pull. *Mechanism:* new service + new API. *Pro:* single authority, clean fan-out. *Con:* heavyweight
for ~55-row, 4-hourly vocabularies; new ops surface + SLA; **one-way door once 2+ services bind its API.**
(This is the Confluent-Schema-Registry idiom internalized — the scout disqualified the *external* version on
adoption cost/lock-in; the internal version inherits the same weight.)

**Option B — Generic registry table inside autom8y-data (no new service).**
Generalize the `verticals`-style table into a generic `cf_vocabularies` registry *inside the existing consumer
hub*, served by one generic `POST /api/v1/vocabularies/sync` parameterized by `field_key`. *Mechanism:* a
`field_key` discriminator + a generic store; uses existing FastAPI/S2S/store substrate. *Pro:* the per-instance
`vertical` contract is literally row-class #1; compose-up = add a `field_key`, not an endpoint. *Con:* one
table/endpoint co-tenanting many vocabularies needs per-`field_key` policy columns (delete policy, coverage
contract).

**Option C — Event-streamed vocabulary (pub/sub / CDC bus).**
Asana option-set changes publish to an internal event stream / outbox; consumers subscribe and materialize their
own replicas. *Mechanism:* event bus + outbox. *Pro:* clean producer↔N-consumer decoupling. *Con:* heavyweight
infra; ordering/replay/idempotency to operate; **one-way door once 2+ services bind topics.** (Debezium/Kafka
idiom internalized.)

**Option D — Asana-as-live-source-of-record, query-through (no replica).**
No data-side replica; consumers query Asana live `enum_options` through a thin fleet-shared read-through cache
at read time. *Mechanism:* shared client + cache, NO sync contract. *Pro:* eliminates the replica + the sync
entirely; zero drift (one source). *Con:* couples every consumer to Asana availability/latency/rate-limits at
read time; loses the FK-parent dimension (autom8y-data's `verticals` FK graph requires a local table — D would
break the 43k FK edges). The null-mechanism-for-the-replica option; disqualified for FK-parent vocabularies,
viable for FK-free ones.

**Option E — Declarative versioned contract registry (delegation to VCS + CI).**
Option-set vocabularies live as a checked-in declarative artifact (`cf-contracts/*.yaml` or a knossos-style
ledger) both producer and consumers read; sync is a CI-time materialization + drift-gate, not a runtime push.
*Mechanism:* delegate the registry to the existing declarative/version-control substrate; drift-gate at CI
(gfr-dynvocab's own Option-A heritage, `registry.py`). *Pro:* the *governance/coherence* layer needs no runtime
service; review-able, diffable, rollback-able by git. *Con:* CI-cadence (not 4-hourly runtime) for the
*vocabulary values*; best as a coherence layer over a runtime carrier, not the carrier itself.

**Option F — HYBRID (RECOMMENDED): B as runtime carrier + E as coherence layer + D's source-of-record principle.**
Runtime carrier = **B** (one generic `/vocabularies/sync` + a `field_key`-discriminated store inside
autom8y-data). Coherence/governance layer = **E** (a versioned declarative `cf-contracts` registry the drift-gate
reads to know which `field_key`s are bound by which consumers, with per-`field_key` policy: delete policy,
coverage contract, source-of-record). Source-of-record principle = **D** (Asana live `enum_options` is
authoritative) — *without* D's no-replica weakness, because B keeps the FK-parent local table.

### 2.2 Recommended target + the compose-up path

**Target = Option F**, reached *incrementally*, not built now. The decisive property: **this spike, built as
specified, IS Option B at cardinality 1.** INTEGRATE already named the endpoint generically — `/vocabularies/sync`
(plural), not `/verticals/sync` — and the request already carries `field_key` (INTEGRATE Target-State table,
`VocabSyncRequest{field_key, options[], ...}`). That is the compose-up seam.

```
  CARDINALITY 1 (this spike, GO'd)                CARDINALITY N (registry end-state, DEFER)
  ┌───────────────────────────────┐               ┌──────────────────────────────────────────┐
  │ Asana live enum_options        │               │ Asana live enum_options (SoR, per D7)      │
  │   (Vertical cf)  ── SoR ──┐    │               │   N cf option-sets  ── SoR ──┐             │
  │                           ▼    │   compose UP   │                              ▼             │
  │ producer push_vocab_to_  ─┐    │  ===========>  │ producer projects N field_keys ─┐         │
  │   data_service()          │    │  (no rewrite)  │   (or consumers PULL — S2 migrate)│        │
  │                           ▼    │               │                                   ▼         │
  │ POST /vocabularies/sync        │               │ POST /vocabularies/sync                     │
  │   field_key="vertical"  ←──────┼─── SAME ───────┼──→ field_key ∈ {vertical, pipeline_stage,  │
  │                                │   ENDPOINT     │       lead_source, ...}                     │
  │                           ▼    │               │                              ▼              │
  │ vocab_upsert (additive)        │               │ vocab_upsert + per-field_key policy         │
  │   → verticals (row-class #1)   │               │   → cf_vocabularies (N row-classes)         │
  │                                │               │ + cf-contracts/*.yaml coherence layer (E)   │
  └───────────────────────────────┘               └──────────────────────────────────────────┘
```

**The three forward-compatible decisions that MUST be locked at build time** (cheap now, expensive to retrofit —
these are what keep the door to F open without speculative investment):

1. **Generic endpoint name** `/api/v1/vocabularies/sync` — never `/verticals/sync`. (Already specified in
   INTEGRATE; confirm tech-transfer does not "simplify" it to a vertical-specific path.)
2. **`field_key` discriminator in the request body** — present from row one, value `"vertical"`. Adding a 2nd
   vocabulary is a new `field_key` value, not a schema change.
3. **NAME-keying** (D1) — the portable key is the cross-service identity; gid/`vertical_id` are local handles.

With those three locked, cardinality 1→N is **additive** (new `field_key` rows, new producer projections, new
per-`field_key` policy entries) — no endpoint rewrite, no store-method rewrite, no re-keying. **This is the
direct answer to the DEFER-1 generalization: the Vertical sync is the first instance of a general pattern,
realized through a deliberately-generic carrier, so the registry is the same carrier at higher cardinality plus
a coherence layer — not a different system.**

**Why F over A/C now (and why the registry stays DEFER):** A and C are the heavyweight fan-out answers and are
*one-way doors once 2+ services bind*. Standing either up before the N≥3 trigger is the Technology-Driven-
Architecture anti-pattern (excitement about a registry/bus driving the decision ahead of validated need). F lets
the fleet sit at a **reversible waypoint** (B at cardinality 1) and migrate to A/C/E-coherence *only when S2
fires*, with a fresh build-vs-buy at that point (route back to technology-scout). This is the three-tier
complexity spectrum applied to architecture planning: start at the simplest tier (generic table, push), escalate
only when measured fan-out justifies it [AD:SRC-010 Microsoft 2026] [MODERATE | 0.72 @ 2026-03-31].

---

## 3. The Four Residual Risks — Design-Level Resolution

### RR1 — Concurrent PostgreSQL upsert (race/locking on `ON CONFLICT`)

**The risk:** two overlapping syncs of the same `field_key` (e.g., a manual re-trigger racing the 4h cron) race
on `INSERT ... ON CONFLICT (key) DO UPDATE`; or the `UPDATE SET name` collides on the `vertical_name` unique
constraint (NEW finding, `_platform.py:147`).

**Design resolution:**
- **Single-writer-per-`field_key` via a transaction-scoped advisory lock.** The store never commits — the caller
  owns the transaction boundary (`vertical.py:34-43`; the snapshot_replace precedent runs everything inside one
  `session.begin()`, `account_status_store.py:82`). Wrap `vocab_upsert` for a `field_key` in
  `pg_advisory_xact_lock(hashtext('vocab:'||field_key))` (Postgres) / `GET_LOCK('vocab:'||field_key)` (MySQL).
  This serializes same-`field_key` syncs **without** blocking different `field_key`s or readers, and releases at
  transaction end so a crashed sync cannot deadlock.
- **Idempotent, no-op-suppressing upsert:** `... DO UPDATE SET name=excluded.name WHERE verticals.name IS
  DISTINCT FROM excluded.name` — conditional update shortens lock hold and avoids write amplification. Order-
  independence is guaranteed by keying on the unique `verticals.key` (`_platform.py:146`, `unique=True`).
- **Name-uniqueness guard (the NEW finding):** `verticals.vertical_name` is `unique=True`. A rename whose new
  name collides with another row's name — or two Asana options normalizing to the same key but different names —
  raises a unique violation. Resolution: the upsert updates `name` only when it does not collide; a name-collision
  is a **DRIFT signal** (WARN + refuse the *individual row*, not the batch), the sibling of the referential-
  coverage guard. Never auto-resolve (ADR-S4-001).
- **Cadence makes contention low by construction:** read-heavy service (`vertical.py:3-4,28-33`), single push
  job, 4h cycle. The lock is a correctness floor, not a throughput concern.

**Residual / verification:** the **DB engine is UNRESOLVED** — priors disagree (INTEGRATE C2 "MySQL leaf" vs
PROTO §4 "PostgreSQL staging"). The engine determines upsert syntax (`ON CONFLICT` vs `ON DUPLICATE KEY UPDATE`)
and lock primitive. `[UV-P: verticals-table DB engine | METHOD: inspect the autom8y-data migration/engine config
before build | REASON: priors disagree; load-bearing for RR1 syntax]`. `[UV-P: concurrent-upsert + name-collision
behavior | METHOD: integration test on staging — two overlapping same-field_key syncs + a forced name-collision
fixture]`.

### RR2 — Disabled-option policy (Asana disables an enum_option with live FK children)

**The risk:** an operator disables an Asana option (`CustomFieldEnumOption.enabled=False`, `custom_field.py:35`)
that is currently FK-referenced. Does it count as "present" for coverage? Does it propagate as a delete?

**Design resolution (policy, not technical):**
- **A disabled option is PRESENT-but-INACTIVE, never DELETED.** Referential coverage = "key present in payload"
  *regardless of the `enabled` flag*. Disabling in Asana propagates as `active=false`, not a removal. This honors
  BC-3 (disable must not propagate as DELETE) and D2 (DELETE-forbidden on the FK-parent).
- **Carry `enabled` in the contract envelope now; persist a soft `active` column later.** For the pilot
  (cardinality 1), carry `enabled` envelope-only for drift. Persisting an `active` shadow column on the registry
  row is **additive** (new nullable column) and is deferred to S1 (when a 2nd vocabulary needs consumer-visible
  active/inactive distinction). Consumers then decide surfacing (e.g., autom8y-stripe hides inactive verticals
  from new-customer flows but still resolves them for existing customers).
- **True retirement of a disabled+referenced option is a human runbook, never a cascade:** re-point the FK
  children first, then a governed removal under S3's per-`field_key` delete policy. This is the deliberate inverse
  of the legacy `_missing_` auto-mint (scout A.3) — no auto-mutation.

**Residual:** the *persist-vs-envelope* choice is a scoped build decision (recommend envelope-only for pilot).
The `enabled` field existence is PROVEN (`custom_field.py:35`, prior SVR).

### RR3 — First-sync key-mismatch (existing `verticals.key` vs Asana option NAME divergence)

**The risk:** `verticals` is already populated (FK-referenced by 43k+ rows). The first sync must MATCH existing
keys, not re-key. If an Asana option name has drifted from the DB `vertical_key` (e.g., "Chiropractic" in Asana
vs `chiro` in the DB), naive ingest either inserts a duplicate or strands the referenced key.

**Design resolution — the one-time reconciliation dry-run gate:**
- Before the first real push *for each `field_key`*, run a **read-only dry-run reconcile**: project Asana
  options → `normalize(name)` → candidate keys; diff against the existing `verticals.key` set. Classify each into:
  - **MATCH** (key exists; name maybe drifted → update name, subject to RR1 name-uniqueness guard),
  - **INSERT-CANDIDATE** (new key not in DB → allowed; additive),
  - **ORPHAN-RISK** (an existing FK-referenced `vertical_key` that NO Asana option normalizes to → the dangerous
    class).
- **First sync is REFUSED if any ORPHAN-RISK key exists.** The Asana vocabulary has drifted from the DB; a human
  reconciles in Asana (the source-of-record — rename/add the option) or via a governed one-time DB key-alignment
  *before* automated sync is enabled. This is HD-5's hard-refuse applied at onboarding.
- **One-time cost per `field_key`:** reconciliation is paid once at onboarding, not every cycle. After the first
  clean sync, steady-state coverage is cheap set arithmetic (PROVEN cheap, PROTO §5). The dry-run is itself fully
  reversible (read-only; emits a reconciliation report, mutates nothing).

**Residual:** `[UV-P: first-sync reconciliation against the live Asana vertical cf payload | METHOD: staging
dry-run | REASON: prototype used a clean fixture, no drift tested]`.

### RR4 — `offers.category` FK coverage (string-keyed `offers.category`→`verticals.key` vs int `vertical_id` edges)

**The risk (sharpened this wave by first-hand read):** `offers.category` is a **STRING** column (`_platform.py:162`,
DB col `category`) that is FK to `verticals.**key**` — structurally different from `campaigns.vertical_id` /
`asset_verticals.vertical_id`, which are INT FKs to `verticals.**id**` (prior SVR, `_advertising.py:80,326`).

**Design resolution:**
- **Additive-upsert protects the string edge for the same reason it protects the int edges — but via a different
  invariant.** The int edges are safe because `id` is never reassigned (upsert preserves it). The string edge is
  safe because the *existing key is the conflict target and is never deleted or mutated* — a rename produces a
  NEW key (an INSERT) while the old key row PERSISTS (additive, never deleted), so `offers.category` rows
  continue to resolve. Both edges reduce to the same root guarantee: **never delete an existing key.**
- **The referential-coverage query MUST union both join types.** A coverage check that only joins on `id` (the
  int edges) would MISS a key referenced *only* by `offers.category`. The FK-referenced key set is:
  `keys-referenced-by-id-edges ∪ keys-referenced-by-the-offers.category-string-edge`. Concretely the producer/
  consumer coverage query is:
  `SELECT DISTINCT v.key FROM verticals v WHERE EXISTS(SELECT 1 FROM asset_verticals av WHERE av.vertical_id=v.id)
   OR EXISTS(SELECT 1 FROM campaigns c WHERE c.vertical_id=v.id) OR EXISTS(SELECT 1 FROM offers o WHERE
   o.category=v.key)`. The third clause is a string-join — **verified-necessary, not speculative** (`_platform.py:162`).

**Residual:** none structural — the requirement is to include the third clause. The 43,057-row `asset_verticals`
magnitude is carried from prior SVR (`_advertising.py:326`); the string-edge necessity is PROVEN this wave.

---

## 4. Migration Path OFF the Six Sources

### 4.1 The six sources today

| # | Source | Anchor | End-state role |
|---|--------|--------|----------------|
| 1 | legacy `Vertical(Enum)` (~55 members) | `contente_api/.../vertical/main.py:19` | FROZEN legacy (quarantined) |
| 2 | `VERTICAL_NAMES` display map | `contente_api/.../vertical/main.py:261` | FROZEN legacy |
| 3 | SQL `verticals` (contente) | `contente_api/.../vertical/main.py:12` | FROZEN legacy mirror |
| 4 | **Asana live `enum_options`** | `custom_field.py:113` | **AUTHORITATIVE source-of-record** |
| 5 | asana hardcoded `SEMANTIC_ANNOTATIONS.valid_values` | `resolver_schema.py:449,473` | DERIVED view of #4 |
| 6 | **autom8y-data `verticals` table** | `_platform.py:131-147` | GOVERNED DERIVED replica of #4 |

**Target:** ONE authoritative source (#4), one governed derived replica (#6), one derived view (#5); #1/#2/#3
frozen legacy. Six → "1 SoR + 1 replica + 1 view + 3 frozen."

### 4.2 Sequenced retirement (triggers + rollback + one-way callouts)

> Each step lists a **start trigger** (observable), a **rollback point**, and a **reversibility** grade. Steps
> M0–M1 are **safe-now** (the GO'd per-instance contract). M2–M3 are **gated** on quarantine/convergence signals.
> M4 is **DEFERRED** behind the registry trigger. This builds on INTEGRATE's Phases 0–3 (the per-instance build)
> and layers the *source-retirement* sequence on top.

**M0 — Establish #4 as declared SoR; #6 becomes a governed derived replica. (SAFE-NOW)**
*Mechanism:* the per-instance contract — producer reads #4 live `enum_options`, pushes via `/vocabularies/sync`
(`field_key="vertical"`), `vocab_upsert` additive on #6, drift observer WARNs.
- **Start trigger:** Wave-3 GO (already fired).
- **Retires:** nothing yet — #6 is now *derived* but #1/#2/#3/#5 untouched.
- **Rollback:** producer flag off (HD-4, `gid_push.py:491`); additive-upsert means **no data to revert**.
- **Reversibility: FULL.** One-way doors crossed: **none.**

**M1 — Re-point #5 to read #4. (SAFE-NOW, with a compat gate)**
*Mechanism:* wire schema-discovery `values_source:'asana_configured'` (`resolver_schema.py:366`); #5's hardcoded
`valid_values` becomes a derived view of #4 (or fallback-only cache).
- **Start trigger:** M0 steady-state — ≥N clean sync cycles with the drift observer showing #4↔#6 convergence.
- **Retires:** #5 as an *independent* hand-maintained source (becomes derived).
- **Rollback:** re-point to the hardcoded annotation (config flip).
- **Reversibility: FULL (config flip).** **Compat gate:** INTEGRATE flagged a 2x-effort risk if downstream
  consumers depend on the hardcoded `SEMANTIC_ANNOTATIONS` *shape* — verify consumer-compat before flipping.
  Reversible, but gate on the compat check.

**M2 — Freeze #1/#2/#3 (legacy contente) as read-only. (GATED)**
*Mechanism:* declarative — mark NON-CANONICAL, stop hand-editing, point any residual readers at #6 via
`VerticalService`. These are already quarantined (HD-1: 0 import edges from either synced service).
- **Start trigger:** M1 complete **AND** a fresh grep proving no NEW import edge into contente `Vertical(Enum)`
  from either synced service (HD-1 quarantine still holds).
- **Retires:** #1/#2/#3 as WRITE sources (frozen); they remain legacy read mirrors until the contente monorepo
  is itself retired (a different initiative, out of scope).
- **Rollback:** un-freeze (resume hand-edits). REVERSIBLE but **socially sticky** — once maintenance stops, drift
  re-accrues, so the rollback window is practically time-bounded.
- **ONE-WAY callout (SOFT):** severing the `_missing_` phantom-campaign auto-mint cascade
  (`vertical/main.py:138-149`) is irreversible *if* any job depends on the side-effect. Scout/INTEGRATE proved 0
  import edges, so severing is safe — and severing is the thing being **ESCAPED** (BC-3/HD-1), never re-entered.
  **Guard:** confirm no production job depends on `_missing_`'s auto-mint before freezing.

**M3 — #6 is the single governed authority for all in-fleet consumers; #4 stays SoR. (GATED)**
*Mechanism:* all in-fleet consumers (autom8y-stripe SDK, future services) read #6 via gRPC `VerticalService`;
#4 = SoR; #5 = derived view; #1/#2/#3 frozen. The six-way fragmentation is collapsed.
- **Start trigger:** M2 complete **AND** sustained #4↔#6 convergence (e.g., 30 days of clean syncs, zero
  unresolved drift WARNs).
- **Retires:** the *fragmentation* itself.
- **Rollback:** each consumer re-points to its prior source; #6 is additive → no data loss. REVERSIBLE per-consumer.
- **Reversibility: FULL.** One-way doors crossed: **none** (the codegen door is never crossed).

**M4 — Generalize to the fleet cf-contract registry (target F). (DEFERRED — one-way watch)**
*Mechanism:* the §2 compose-up — generic carrier B at cardinality N + coherence layer E.
- **Start trigger (DEFER-1 N≥3):** a 2nd option-set vocabulary binds `/vocabularies/sync` (a 2nd `field_key`)
  **AND** a 3rd consuming service requests it (e.g., scheduling-stratum materializes). The conjunction is the
  N≥3 condition from my gfr-dynvocab dissent.
- **ONE-WAY DOOR:** standing up a central registry *authority* (Option A) or event bus (Option C) is reversible-
  expensive once 2+ services bind. The B-at-cardinality-1 waypoint (built at M0) keeps the door OPEN — generalize
  to F *without a rewrite*.
- **Escalation:** to **user/leadership** (resource commitment + strategic bet) **AND** back to **technology-scout**
  (fresh build-vs-buy at N≥3: central service vs event stream vs declarative coherence layer).

### 4.3 Migration ASCII timeline

```
  SAFE-NOW (GO'd, fully reversible)        GATED (signal-triggered)          DEFERRED (N>=3 one-way watch)
  ├── M0 ──────────┬── M1 ───────────┬──── M2 ──────────┬──── M3 ──────────┬──── M4 ─────────────────►
  │ #6 derived     │ #5 re-pointed   │ #1/#2/#3 frozen  │ #6 single auth   │ fleet cf-contract registry
  │ flag-off       │ config-flip     │ un-freeze        │ per-consumer     │ ONE-WAY: central authority
  │ rollback       │ rollback        │ rollback (sticky)│ rollback         │ escalate leadership+scout
  └── reversible ──┴── reversible ───┴── soft 1-way ────┴── reversible ────┴── DEFER until N>=3 ──────►
   trigger: GO       trigger: N clean   trigger: quarantine  trigger: 30d      trigger: 2nd field_key
                     syncs converge     grep holds           convergence       + 3rd consumer
```

---

## 5. What Survives / What Is Reversible / What to DEFER

### 5.1 Survives all scenarios (the architectural invariants — do not relitigate)

- **NAME-keying** (D1) — vindicated by S4; the portable-key insulation layer.
- **Additive-upsert as the default write policy** (D2 default) — the FK-parent safety property (PROVEN, PROTO §2).
- **Drift-gate-not-codegen** (D6 / ADR-S4-001) — the one-way door we never re-open.
- **FROZEN cf-type set; option-set as sidecar** (D8) — never a 7th type.
- **Asana live `enum_options` as source-of-record** (D7).
- **The generic carrier: `/vocabularies/sync` + `field_key` discriminator** (D3) — the compose-up seam to the registry.
- **Strictly-additive to the certified spine** (the 105 GFR tests; gfr-dynvocab telos `:51,79`).

### 5.2 Reversible (two-way doors — time-box the decision, plan a review point)

| Decision | Now | Migrates to | Trigger |
|----------|-----|-------------|---------|
| Transport (D4) | producer PUSH | pull/subscribe or registry fan-out | S2 (N>2 consumers) |
| Disabled-option persistence (RR2) | envelope-only `enabled` | persisted `active` column | S1 (2nd vocab needs it) |
| Referential-coverage location (D5/D9) | producer-side, vertical-specific | per-consumer / registry-governed, per-`field_key` | S1/S2 |
| #5 source (`SEMANTIC_ANNOTATIONS`) | hardcoded | derived view of #4 | M1 (after compat gate) |
| Per-vocab write policy (D2) | global DELETE-forbidden | per-`field_key` `deletion_policy` column | S3 |

### 5.3 One-way doors (never cross / never re-enter)

1. **ADR-S4-001 codegen-from-model** — never re-open (HARD constraint §0.3).
2. **DELETE on the `vertical` FK-parent** — never flip `vertical`'s additive-only invariant (orphans 43k+ rows;
   `_advertising.py:326`, `_platform.py:162`).
3. **gid-keying** — never key on `enum_option.gid` or `vertical_id` (re-keying + cross-workspace breakage).
4. **Central registry authority (A) / event bus (C) before N≥3** — don't cross until the DEFER-1 trigger fires.

### 5.4 DEFER register (each with its escalation trigger)

| DEFER | What is deferred | Escalation trigger (observable) | Escalate to |
|-------|------------------|----------------------------------|-------------|
| **DEFER-1** | The fleet cf-contract registry (target F at cardinality N) | 2nd `field_key` bound **AND** 3rd consuming service requests the vocab | user/leadership (strategic bet) + technology-scout (build-vs-buy) |
| **DEFER-2** | Relaxing additive-only to a per-`field_key` delete policy | a legitimately-ephemeral vocab is proposed, or a GDPR removal is required | user/leadership (safety-property relaxation) |
| **DEFER-3** | Adopting an Asana stable option-ID / handling name-collision | Asana ships portable option IDs, or permits same-display-name options | technology-scout (re-evaluate keying; composite key?) |
| **DEFER-4** | Push→pull transport inversion | N>2 consumers (producer hardcoding N consumer URLs) | integration-researcher / architect (transport re-design) |

### 5.5 Immediate actions (start now, regardless of which future arrives)

These pass the Acid Test ("if this future arrives in 18 months, will we wish we'd started today?") — minimum
viable preparation that is future-independent:
1. **Lock the three compose-up decisions at build (§2.2)** — generic endpoint, `field_key` discriminator,
   NAME-keying. Zero extra cost now; the entire registry door depends on them.
2. **Resolve the DB-engine UV-P (RR1)** before build — it determines upsert syntax and the lock primitive.
3. **Build the referential-coverage query with the `offers.category` string-edge clause from day one (RR4)** —
   PROVEN-necessary; cheap to include, a silent orphan-hazard to omit.
4. **Add the name-uniqueness guard alongside the coverage guard (RR1)** — `vertical_name` is `unique=True`; the
   `UPDATE SET name` path needs it.
5. **Make the first-sync reconciliation dry-run a build deliverable (RR3)** — a read-only gate, future-independent.
6. **Instrument the drift observer + a publish-count canary metric** — so M1/M3 convergence triggers and the HD-4
   ship-dark risk (R7) are *observable*, not assumed.

---

## 6. Handoff to Tech-Transfer

**Exit criteria (all met):**
- [x] Long-term target architecture defined (§2, Option F) with seven enumerated alternatives (NULL/A/B/C/D/E/F)
      offered for external enumeration audit per `option-enumeration-discipline`.
- [x] DEFER-1 registry generalization addressed — compose-up path stated (§2.2: this spike = Option B at
      cardinality 1; cardinality 1→N is additive given the three locked decisions). Registry stays DEFER.
- [x] Four residual risks resolved at design level (§3), each with a concrete mechanism + remaining UV-P.
- [x] Migration path off the six sources sequenced (§4) with observable start triggers, reversible rollback
      points, and one-way-door callouts; safe-now (M0–M1) vs gated (M2–M3) vs deferred (M4) distinguished.
- [x] One-way doors flagged (§5.3); survives/reversible/DEFER partitioned (§5) with per-DEFER escalation triggers.
- [x] HARD constraints honored as load-bearing (§0.3); none reopened by any scenario or migration step.

**For tech-transfer specifically:** the production build is INTEGRATE's ~6.5 person-days (the per-instance
contract, M0–M1). The registry (M4/DEFER-1) is NOT a build item — it is a watch item with a defined trigger. The
six immediate actions (§5.5) are the production-readiness checklist; items 1–4 are non-negotiable at build time
(they are the difference between a one-off and the first instance of the pattern).

---

## Artifact Verification Table

| Artifact | Path | Status |
|----------|------|--------|
| This moonshot plan | `.ledge/spikes/MOONSHOT-dyn-enum-contract.md` | Written; self-verified against template + brief deliverable structure |
| Upstream — prototype (GO) | `.ledge/spikes/PROTO-dyn-enum-contract.md` | Read (Wave 3) |
| Upstream — integration | `.ledge/spikes/INTEGRATE-dyn-enum-contract.md` | Read (Wave 2) |
| Upstream — scout | `.ledge/spikes/SCOUT-dyn-enum-contract.md` | Read (Wave 1) |
| HARD-constraint source | `.know/telos/gfr-dynvocab.md` | Read (`:47,51,77,78,79`) |

## Source Anchors (verified first-hand THIS wave; SVR discipline)

**autom8y-asana (cwd):**
- `src/autom8_asana/services/gid_push.py:491` — `_is_status_push_enabled()` producer feature flag (HD-4 / rollback lever)
- `src/autom8_asana/services/gid_push.py:514-519` — leaf-calibrated empty guard `return True # Nothing to push is not a failure`
- `src/autom8_asana/services/gid_push.py:528` — `_push_to_data_service(endpoint_path=...)` shared, endpoint-parameterized helper

**autom8y-data (sync target) — verified first-hand this wave:**
- `src/autom8_data/core/models/_platform.py:145-147` — `verticals{vertical_id PK(col id), vertical_key unique(col key), vertical_name UNIQUE(col name)}` — **`vertical_name` unique is the NEW RR1 finding**
- `src/autom8_data/core/models/_platform.py:162` — `offers.category` STRING col, `foreign_key="verticals.key"` — the string-edge that sharpens RR4
- `src/autom8_data/services/vertical.py:9-10` — "No Delete operation (verticals are permanent)" / "No Update operation in scope" — DELETE-forbidden invariant + `vocab_upsert` is genuinely new code
- `src/autom8_data/services/vertical.py:34-43,48` — service never commits; caller owns txn boundary; `IMMUTABLE_FIELDS={"vertical_id","id"}`
- `src/autom8_data/api/services/account_status_store.py:82-143` — snapshot_replace single-`session.begin()` txn, source-scoped DELETE, bulk INSERT, carry-forward (migration contrast + RR1 txn pattern)

**Carried from prior SVR (verified at their authoring time):**
- `_advertising.py:80,326` — `campaigns.vertical_id` / `asset_verticals.vertical_id` (43,057 rows) int FK to `verticals.id` (INTEGRATE HD-2 SVR)
- `custom_field.py:35,113` — `CustomFieldEnumOption.enabled`, `CustomField.enum_options` (scout/INTEGRATE SVR)
- `resolver_schema.py:366,449,473` — `values_source:'asana_configured'` door, hardcoded `valid_values` (#5) (scout A.4 SVR)

## Evidence Grade

`[STRUCTURAL | MODERATE]` — ceiling, not floor. Self-referential (designing the fleet's own future from inside)
caps at MODERATE per `self-ref-evidence-grade-rule`; rnd-dk literature caps at MODERATE (no STRONG available in
this rite). The mechanism foundation is PROVEN (Wave-3 two-sided canaries, §0.4); the registry compose-up,
concurrent-upsert behavior, first-sync reconciliation, and DB engine are PROJECTED/UV-P and explicitly tagged.
The recommendation (Option F, held at DEFER) is offered for rite-disjoint enumeration audit per
`option-enumeration-discipline` before any one-way registry commitment — the DEFER posture is itself the
discipline operating: the audit precedes the irreversible door.
