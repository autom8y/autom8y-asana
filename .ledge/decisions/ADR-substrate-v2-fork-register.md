---
type: decision
decision_subtype: adr
artifact_id: ADR-substrate-v2-fork-register
id: ADR-SUBSTRATE-V2-FORKS
title: "Substrate-v2 design forks F1-F6 — enumerated option slates + provisional rulings"
created_at: "2026-07-27T23:21:07Z"
author: architect
status: proposed            # recognized lifecycle value
lifecycle_status: fully-ratified   # Phase-2 passed; F2/F4/F6 RATIFIED-AUTO; F1+F3 (DP-2) + F5 (DP-3) RATIFIED-BY-OPERATOR 2026-07-29 — all six forks resolved
finalized_at: "2026-07-29T08:52:09Z"
schema_version: "1.0"
rite: 10x-dev
initiative: substrate-v2-epoch
sprint: S1
phase: FINALIZED (Phase-3 of the S1 DAG — arch-adversary PASS-WITH-CONDITIONS folded; conditions per fork below)
evidence_grade: MODERATE
evidence_grade_rationale: >
  Self-authored design within the 10x-dev corridor; caps at MODERATE per
  self-ref-evidence-grade-rule. The arch-adversary (rite-disjoint, arch rite)
  rendered PASS-WITH-CONDITIONS (no fork reversed) in Phase-2; conditions folded.
  STRONG is the eunomia attestation at epoch exit (S12).
context: >
  The substrate-v2 charter delegates six design forks (F1-F6) to /architect under
  option-enumeration-discipline + adversarial challenge (P8). This register
  enumerates each fork's structurally-distinct option slate, records a provisional
  ruling with rationale, and routes the two one-way-door forks (F1+F3 -> DP-2;
  F5 -> DP-3) to the operator with the adversary's dissent to be attached in Phase-3.
decision: >
  Corridor forks F2/F4/F6 auto-ratify (provisional, pending arch-adversary): F2 =
  content-digest-plus-build-from-live-age freshness with NO probe-stamp (D8 class
  subtracted); F4 = stage-validate-swap rebuild with a capability-typed read-only
  reader; F6 = query-independent scheduled provability evaluator with self-heartbeat.
  Door forks stage as operator packets: DP-2 (F1+F3 storage-shape + key/schema) =
  versioned immutable artifact + atomic current-pointer, entity_type a REQUIRED
  typed key field; DP-3 (F5 consumer contracts) = a single typed read choke-point
  returning a Provable|Refused result. No fork is finalized in this DRAFT.
consequences:
  - type: positive
    description: "Each RC-A..F acquires a construction (impossible-by-construction or fail-loud) traceable to a fork ruling; the design is legible-small (6 modules / 5 seams)."
  - type: positive
    description: "Refuse-loud and plane-correctness become type/API properties (one read choke-point, entity_type-required key) rather than per-call-site discipline — the exact class that let v1 drift."
  - type: negative
    description: "Two forks are one-way doors post-cutover (key/schema, consumer contracts) and block their build sprints (S3, S5) until operator ratification of DP-2/DP-3."
    mitigation: "Batch DP-2 + DP-3 at S1 as compact packets carrying the arch-adversary dissent (P8); S3/S5 are entry-gated on ratification per the shape."
  - type: negative
    description: "'Impossible-by-construction' in Python is not compile-time absolute; it reduces to (deleted capability) + (mypy-strict CI tooth) + (construction-time guard). Honest floor, stated per fork."
    mitigation: "mypy-strict on the identity/reader types is the P11 sparing CI tooth where construction cannot fully reach; named explicitly, not hand-waved."
related_artifacts:
  - CHARTER-substrate-v2-epoch-2026-07-27
  - TDD-substrate-v2
  - DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27
  - ADVERSARY-substrate-v2-design-s1
  - FEASIBILITY-substrate-v2-seams-s1
  - DP-2-v2-storage-shape
  - DP-3-consumer-contracts
  - ADR-seam1-entity-identity-key
  - ADR-006-freshness-equals-verification-recency
tags:
  - substrate-v2
  - option-enumeration
  - one-way-door
  - freshness
  - storage
  - rebuild
  - serving
  - observability
---

# ADR — Substrate-v2 design forks F1-F6 (enumerated option slates + provisional rulings)

> **FINALIZED — Phase-3 of the S1 three-phase DAG.** The arch-adversary (rite-disjoint,
> arch rite) rendered **PASS-WITH-CONDITIONS** — no fork's provisional choice was reversed.
> Final states: **F2/F4/F6 = RATIFIED-AUTO** (challenge passed; conditions folded into the
> TDD seams); **F1+F3 = RATIFIED-BY-OPERATOR (DP-2, 2026-07-29: shape C · entity-after-project)**;
> **F5 = RATIFIED-BY-OPERATOR (DP-3, 2026-07-29: 424+refusal-SLI · F5-5 P11 law · stale-200 ADR
> superseded)**. **ALL SIX FORKS RESOLVED — no open design fork remains in the epoch.**
> The option slates below are the enumeration record (unchanged — the adversary added options
> to the door slates but reversed no choice); Phase-2 conditions per fork are appended to each
> ruling. Door packets carry the adversary dissent verbatim (DP-2, DP-3).

## Phase-2 outcome + final fork states

| Fork | Final state | Phase-2 conditions folded (see TDD §10 ledger) |
|------|-------------|-----------------------------------------------|
| **F1+F3** | **RATIFIED-BY-OPERATOR (DP-2, 2026-07-29)** — shape **C** · **entity-after-project** | C4 — false S3-atomicity premise CORRECTED (SVR docs-cite discharged at ratification, DP-2 §Ratification record); slate extended (A-prime, C-prime, E); genuinely re-evaluated (rec HELD at C on corrected grounds; A-prime named strongest simpler alt); dissent verbatim in DP-2 |
| **F2** | **RATIFIED-AUTO** | C1 — per-section provenance MIN-fold (a probe cannot advance a section's fetch-instant); closes the AV-1 D8-resurrection; RK1 answered honestly |
| **F4** | **RATIFIED-AUTO** | C3 (CAS swap + collision-free version-IDs) + C9 (validate-before-swap receipt → S4 build-note) |
| **F5** | **RATIFIED-BY-OPERATOR (DP-3, 2026-07-29)** — **424+refusal-SLI** · F5-5 = P11 law · supersession EXECUTED | C5 — F5-5 SDK enumerated; ADR-serve-stale-within-bound EXPLICIT SUPERSEDED (frontmatter marked 2026-07-29); status-class presented two-sided, operator ratified 424 (PE's 5xx preserved as the unadopted alternative); shape-hostile bodies; dissent verbatim in DP-3 |
| **F6** | **RATIFIED-AUTO** | C7 (two-sided expected-set: registry ∪ store enumeration) + C10 (end-to-end fired-alarm evidence → S6/S8 build-note) |

The adversary's per-fork dissent (F1/F3 and F5, packet-grade) is carried verbatim into DP-2 and DP-3
respectively. C2/C6 (RC-B serve-binding, RC-C UNKNOWN disclosure) folded into the TDD §3 constructions
+ Seam 2/4. C8/C11 are CARRY-TO-BUILD (TDD §11).

## How to read this register

Each fork carries: the **charter-verbatim question**, an **option slate** (>=2 structurally
distinct options + a null/no-new-mechanism option + a delegation option where applicable,
per `option-enumeration-discipline` §5), a **provisional ruling + rationale**, a
**reversibility / door routing** line, an **author self-audit** (the §4-Step-1 questions
that surface truncated search space), and an **adversary target** (the seam the Phase-2
critic should attack hardest — pre-naming the hard question is a gap-concealment guard).

Grounding is re-anchored on FRESH source content (discipline #8 — ADR line-anchors have
drifted; every claim below cites content verified at HEAD `b9438e83`, see the TDD premise
ledger). Prior-art from ADR-SEAM1 / ADR-006 is consulted for **behavior**, not treated as
**precedent** (charter: their Decision records are prior art, a floor to clear, not a shape
to inherit — `legacy-floor-isolation`).

---

## Door map (charter one-way-door register)

| Fork | Routing | Door | Provisional ruling |
|------|---------|------|--------------------|
| **F1 + F3** | **DP-2 (operator packet)** | Door #2 — v2 key/schema shape (post-cutover load-bearing) | Versioned immutable artifact + atomic `current` pointer; `entity_type` a REQUIRED typed key field |
| **F2** | auto-ratify (corridor) | — | Content-digest + build-from-live age; no probe-stamp (D8 subtracted) |
| **F4** | auto-ratify (corridor) | — | Stage-validate-swap; capability-typed read-only reader |
| **F5** | **DP-3 (operator packet)** | Door #3 — cross-service consumer contracts | Single typed read choke-point returning `Provable \| Refused` |
| **F6** | auto-ratify (corridor); terraform limb rides **existing Door #4** | Door #4 (already minted) — cross-repo alarm terraform | Query-independent scheduled provability evaluator + self-heartbeat |

F6 does **not** mint a new door; its parent-repo terraform limb is the already-registered Door #4.

---

## F1 + F3 — Canonical artifact shape + storage layout & key schema → DP-2

> **F1 (charter):** "Canonical artifact shape (consolidated vs per-section vs other)."
> **F3 (charter):** "Storage layout & key schema."
> These co-determine ONE physical thing — the shape you store and the key you address it
> by — so they resolve as a single ruling and a single operator packet (DP-2). The LIVE
> unremediated consolidated-`{entity}/dataframe.parquet` vs per-section-`{entity}/sections/*`
> split (DEFECT: "the consolidated-warm and the per-section read-layout are DIFFERENT write
> paths") is this fork's live counterexample: the #276 fix shipped AROUND it (P7 deferred).
> v2 must pick ONE layout.

### The key-schema half is settled first (RC-C, non-negotiable)

Before shape, the KEY: every option below carries the SAME key invariant — the artifact is
addressed by a typed `ArtifactId(project_gid, entity_type)` where **`entity_type` is a
required, non-defaultable field**. This directly subtracts v1's hole: at HEAD
`storage.py` builds keys via `_entity_segment(project_gid, entity_type: str | None = None)`
with `legacy_fallback_enabled: bool = True` — an entity-agnostic key is constructible by
passing `None`, and the whole legacy plane hangs off that default. In v2 there is **no
`None` branch and no legacy key-builder**: a plane-blind key cannot be named because the
constructor rejects an empty entity. (`grep -c entity_type` == 0 on any writer is a
mypy-strict + construction-time error, not a passing test — the SEAM-1 recurrence class is
unconstructable.) This half of F3 is **not** door-optional; it is RC-C and rides into the
build regardless of which shape the operator ratifies.

### Option slate (artifact shape)

**Option A — Consolidated single object per (project, entity), atomic overwrite.**
`dataframes/{project_gid}/{entity_type}/frame.parquet` is the ONLY artifact (+ a sidecar
freshness proof). No per-section files; no separate consolidated layer.
- Advantage: RC-A is trivial — one object, one writer, no re-consolidation step (v1's
  row-copy #3), no consolidated-vs-per-section duality (the DEFECT second split is
  unconstructable — there is no per-section layout to diverge from). Reader reads one
  object; no cross-section vintage mixing (the DEFECT's `$83,385`-with-63-combos artifact
  cannot arise).
- Disadvantage: overwrite of a large parquet on S3 is **not truly atomic** under multipart
  — a failed multipart PUT can leave a corrupt object; a reader mid-overwrite has no
  consistent pointer. No rollback primitive (the prior bytes are gone). Whole-frame
  materialization per refresh.

**Option B — Per-section directory as the single canonical layout, atomic manifest swap.**
`dataframes/{project_gid}/{entity_type}/sections/{section_gid}.parquet` is the ONLY layout;
the consolidated `dataframe.parquet` is SUBTRACTED. A manifest names the live section-set +
version; the reader concatenates the sections the manifest names.
- Advantage: incremental-delta-friendly (only changed sections re-staged); per-section
  provenance native; bounded object sizes.
- Disadvantage: the reader must concat N sections and run the `(office_phone, vertical)`
  cross-section dedup — the exact place the DEFECT's vintage-mixing fragility lives; safe
  ONLY if the manifest atomically names a consistent version-set, which is more moving
  parts than a pointer flip. RC-A holds only if NOTHING ever writes a consolidated object
  (must be enforced by subtraction, ongoing vigilance — weaker than "no such code path").

**Option C — Versioned immutable artifact + atomic `current` pointer (PROVISIONAL CHOICE).**
`dataframes/{project_gid}/{entity_type}/v{N}/frame.parquet` is one immutable consolidated
object per version; a tiny `dataframes/{project_gid}/{entity_type}/current.json` names the
live version AND carries the freshness proof (`built_from_live_at`, `content_digest`). Old
versions are immutable until GC'd.
- Advantage: the atomic swap (RC-E) is a single small-object PUT — the pointer — which IS
  genuinely atomic on S3 (single object, no multipart). RC-A single-source is a literal
  pointer object. Rollback = flip the pointer back to `v{N-1}` (two-way door until GC — the
  cutover reversibility P5 demands). Freshness proof read in ONE GET, co-located with the
  pointer. A reader never observes a half-written version (it reads `current.json`, then the
  named immutable version).
- Disadvantage: version GC is a new lifecycle concern (unbounded storage otherwise);
  whole-frame materialization per version (shared with A) unless versions store deltas;
  slightly more objects.

**Option D — Null / no-new-mechanism: keep the dual layout, harden reads.**
Retain v1's consolidated + per-section duality with the entity segment; add read guards.
- **REJECTED.** This IS the disease: two layouts is the DEFECT second split; the dual-read
  `legacy_fallback_enabled` bridge is RC-D's immortal bridge. P3 (subtract > guard) and P4
  (whole re-architecture, not incremental) forbid keeping the duality. Included to force the
  "why not just keep it" defense — the answer is that the duality is the wound.

### Provisional ruling (DOOR-PENDING — DP-2, operator)

**Option C (versioned immutable artifact + atomic `current` pointer), entity-segmented key
with `entity_type` required.** It is the only option where (a) the atomic swap is a
genuinely-atomic single-object write (RC-E), (b) single-source-of-truth is a literal
addressable pointer (RC-A), (c) the freshness proof is read in one GET co-located with the
pointer (RC-B/RC-F feed), and (d) rollback is a pointer flip (P5 reversibility). Option A is
simpler but its large-object overwrite is not atomic and gives no rollback; Option B keeps
the concat/dedup vintage-mixing fragility that produced the DEFECT's unreliable totals.

**Orthogonality note (load-bearing):** the *served shape* (F1/F3 — a versioned immutable
frame) is SEPARABLE from the *fetch/refresh strategy* (F2/F4 — how much to re-fetch from
live Asana). A version is WHAT is served; the rebuilder MAY fetch incrementally (reuse
content-verified sections, re-fetch only changed ones) yet always MATERIALIZE a complete
immutable version. Do not conflate "one served object per version" with "full re-fetch per
version" — the adversary should test that this decoupling holds.

### Reversibility / door

DP-2, **Door #2 (operator)**. The key/schema shape is a TWO-WAY door during the dark-build
+ parity window (writes go to v2, v1 still exists) and becomes a ONE-WAY door post-cutover
(charter: "post-cutover it is load-bearing"). Operator ratifies the packet with dissent.

### Author self-audit (option-enumeration §4 Step 1)

- *Existing substrate not considered as carrier?* The versioned-pointer pattern reuses S3's
  single-object-PUT atomicity (already the atomicity primitive the store has) rather than
  inventing a lock.
- *Enduring predicate of the minted layout?* The class encoded is "immutable-version +
  atomic-pointer," which stays true if the frame shape changes (columns added) — the pointer
  contract is shape-agnostic. Rot-trigger: if S3 gains true multi-object transactions, Option
  A's overwrite becomes atomic and the version machinery could simplify — named, deferred.
- *Data-driven derivation?* The entity segment is DERIVED from the entity registry
  (`entity_type` is a declared enum on the warm target), not hardcoded per project — the key
  falls out of declared config. Good.
- *Delegation option?* Storage layout has no external delegate (S3 is the substrate); N/A.

### Adversary target

Is versioning over-engineered against Option A? Does GC introduce a failure mode (reader
holding a GC'd version) worse than the duality it removes? Is a single immutable
`frame.parquet` per version actually atomic given multipart PUT thresholds for large frames?
Attack the claim that "one object per version" beats "one object, overwritten."

---

## F2 — Freshness model (content-derived; hash vs watermark vs hybrid) → auto-ratify

> **F2 (charter):** "Freshness model (content-derived; hash vs watermark vs hybrid)."
> **Brief (SVR-sharpened):** RETIRE the D8 null-watermark false-CLEAN class BY
> CONSTRUCTION. #276's P3 heal ALREADY bounded D8 to a self-healing one-cycle gap — so the
> brief is "make the class UNCONSTRUCTABLE via content-derived truth," NOT "add another heal."

### The class to make unconstructable (fresh-grounded)

At HEAD, `builders/freshness.py` derives freshness from a STRUCTURAL proxy: `compute_gid_hash`
= sha256 of sorted GIDs (structure only), plus a `modified_since` watermark check. The
docstring at step 5 states the hole verbatim: "If hash matches AND watermark is None ->
hash-only CLEAN. Content edits that preserve the GID set are INVISIBLE." A `CLEAN` verdict
then advances `SectionInfo.last_verified_at` (a re-stampable manifest field). Result (DEFECT):
34 sections share one bulk `last_verified_at`, 20/34 are `watermark=NULL` -> hash-only ->
false-CLEAN -> stamped fresh anyway. The freshness signal is a STAMP set by a proxy probe.
That is the RC-B violation in one sentence: **freshness is write-time metadata advanced by a
probe that does not read the content that determines the number.**

### Option slate

**Option F2-1 — Content-digest + build-from-live age; NO probe-stamp (PROVISIONAL CHOICE).**
The served artifact embeds two fields, and freshness is a pure function of them:
- `built_from_live_at` = the wall-clock instant the content was fetched from LIVE Asana. Set
  ONLY by a content-bearing rebuild. No probe, no re-consolidation, no bulk stamp advances it.
- `content_digest` = a hash over the exact **value-bytes that produce the served numbers**
  (canonical-sorted (row-key, value-columns) serialization), NOT over GIDs.
- `freshness = now - built_from_live_at`, decaying **monotonically**. Self-consistency: the
  served bytes MUST hash to `content_digest` at serve time.
- **D8 retirement by SUBTRACTION:** there is no CLEAN-stamps-fresh code path. The
  `last_verified_at` re-stamp mechanism and the watermark/gid-hash probe-to-stamp bridge are
  DELETED. A probe that "looks clean" does not reset the clock. The null-watermark case cannot
  falsely-freshen because probing no longer feeds freshness at all.
- Advantage: RC-B literal (freshness IS content-derived — build-from-live age + content
  self-consistency). D8 unconstructable by subtraction (P3). Absolute age is queryable for
  RC-F. Legible.
- Disadvantage: an artifact can be content-STALE (Asana changed) yet within SLA age — the age
  bounds staleness RISK, not staleness certainty. Catching mid-SLA change requires a refresh
  cadence < SLA. Accepted: the contract is "provably <= SLA-old, else refused," which is
  exactly the mission ("provably current OR loudly refused"); the parity window (S8) bounds
  the residual empirically.

**Option F2-2 — Live re-verification on read (content hash vs live Asana per query).**
Re-fetch content identity from live Asana on every read; serve only on match.
- **REJECTED.** Violates P10 — every read is a live pull; institutionalizes the 2026-07-27
  429-storm. Defeats the cache. Strongest freshness, unusable posture.

**Option F2-3 — Hybrid: F2-1 truth + a cheap structural probe that can only DECAY, never reset.**
F2-1 is the freshness law. Additionally an optional GID-set probe MAY detect a change and
mark the artifact NEEDS-REBUILD early (decay `built_from_live_at` to expired) — but a probe
may NEVER advance freshness.
- Advantage: keeps all F2-1 guarantees; adds early staleness detection between SLA windows
  WITHOUT re-opening false-CLEAN (probe-can't-freshen is the invariant; a null-watermark or
  ambiguous probe simply does not decay — worst case the artifact ages out at SLA, never
  falsely freshens).
- Disadvantage: adds API calls (P10 budget) + machinery; more surface than F2-1.

**Option F2-4 — Delegation: Asana webhooks/events push a decay signal.**
Subscribe to Asana events for warmed projects (there is already an `api/routes/webhooks.py`);
a change event marks the artifact NEEDS-REBUILD. Freshness still = build-from-live age; a push
event only DECAYS.
- Advantage: catches within-SLA change without polling (P10-friendly — no read-time pulls);
  delegates detection to Asana's already-capable event system.
- Disadvantage: webhook reliability — a missed event must not falsely-freshen (it can't; events
  only decay), but it also can't be the SOLE authority, so the SLA age bound stays primary.
  Cross-cutting infra.

### Provisional ruling (AUTO-RATIFY, pending arch-adversary)

**F2-1 as the freshness LAW** — content-digest + build-from-live age, no probe-stamp. The
frozen invariant that rides into the FRESHNESS seam: **only a content-bearing rebuild advances
freshness; no probe may reset it; freshness age is queryable independent of read.** F2-3's
decay-only probe and F2-4's webhook decay are **rejected-for-now, rot-trigger-named** (see
below) — deferred unless the S8 parity window reveals frequent within-SLA staleness. This is
P3-correct: retire D8 by DELETING the re-stamp, not by adding a fourth heal.

### Reversibility / self-audit / rot-triggers

- Two-way door: freshness is a value-object contract; F2-3/F2-4 are additive later.
- *Null option?* v1's stamp-and-heal (`last_verified_at` + `_heal_null_watermark`) — rejected;
  it is the D8 disease. *Delegation?* F2-4 (webhooks), enumerated + deferred.
- **Rot-trigger (adds F2-3):** S8/PT-04 parity or the >=2-warm-cycle window shows the served
  number diverging from live Asana WITHIN the SLA age more than [gate-tuned threshold] -> add
  the decay-only structural probe. **Rot-trigger (adds F2-4):** warm cadence cannot be pushed
  below SLA under the P10 budget -> add webhook decay to catch changes without polling.

### Adversary target

Does "build-from-live age" actually satisfy the mission's "provably CURRENT," or only "provably
<= SLA-old"? Attack whether within-SLA staleness (Asana changes 1h into a 6h SLA) is acceptable
truth-posture, or whether F2-3 must be in the floor rather than deferred. Also: is the
`content_digest` over value-bytes genuinely deterministic across polars/pandas serializations,
or is the digest itself a non-reproducible artifact?

---

## F4 — Atomic rebuild mechanism (stage-validate-swap or better) → auto-ratify

> **F4 (charter):** "Atomic rebuild mechanism (stage-validate-swap or better)."
> **Brief:** kill the CONFIRMED mid-fetch-persist hazard — at HEAD `builders/progressive.py`
> persists sections DURING the fetch loop (`_fetch_and_persist_section` -> `write_section_async`),
> reached from the full builder AND the warm strategy, so a "read-only" recompute wrote prod
> (DEFECT operational note). A "read-only" read must be PROVABLY side-effect-free.

### Option slate

**Option F4-1 — Stage-validate-swap with immutable staging version + capability-typed reader
(PROVISIONAL CHOICE).**
The rebuild writes ONLY to a staging version (`v{N+1}/`, composing F1/F3 Option C), never the
live pointer. It validates the staged version against the RC acceptance predicates, then
atomic pointer-flips `current.json`. Reads go through a `SubstrateReader` whose type has **no
write method**; the builder is a separate `Rebuilder` type that writes staging-only.
- The mid-fetch-persist hazard is unconstructable: (a) the reader has no write capability, so a
  "read-only recompute" literally cannot touch prod (the DEFECT counterexample becomes a
  passing test — a read exercises an object with no `put`); (b) the rebuilder writes staging
  only; the live pointer moves atomically at the end, so a partial/failed build leaves live
  untouched — partial != corrupt by construction.
- Advantage: RC-E literal. Side-effect-freedom is capability-typed (not flag-guarded). Composes
  with F1/F3 Option C. All live fetches route through the S4 paced primitive (P10).
- Disadvantage: staging storage overhead; version GC (shared with F1/F3-C); Python cannot
  enforce "no write method" at compile time — enforcement = deleted method + mypy-strict + no
  runtime `put` on the reader (honest floor, below).

**Option F4-2 — Copy-on-write temp key + S3 copy + delete (no version pointer).**
Build to `frame.parquet.staging-{uuid}`, S3-copy to the final key, delete staging.
- Advantage: simpler than versioning.
- Disadvantage: S3 has no atomic rename — copy+delete is a two-step window; without a pointer a
  reader between steps sees inconsistent state, and a multi-object frame is not atomically
  swapped. Does not TYPE-enforce side-effect-freedom (a reader could still hold a writer). Weaker
  than F4-1 on the exact property the DEFECT demands.

**Option F4-3 — Null: keep the mid-fetch persist, add a `read_only=True` flag.**
- **REJECTED.** A boolean flag is per-call-site discipline (RC-C anti-pattern); the DEFECT proves
  the "read-only" path DID write prod. A flag makes side-effect-freedom a convention, not a
  proof. P3 (subtract the write capability) beats guarding it.

### Provisional ruling (AUTO-RATIFY, pending arch-adversary)

**F4-1 (stage-validate-swap + capability-typed read-only reader).** Only option where
side-effect-freedom is a TYPE property (the reader has no write API) and partial-!=-corrupt is
structural (live pointer untouched until the atomic flip). Frozen invariant for the REBUILD
seam: **the rebuilder writes staging-only; the live pointer moves exactly once, atomically,
after validation; the reader capability has no persistence method; all live fetches route the
paced primitive.**

### Honest floor (Python "unconstructable")

"Impossible-by-construction" in a dynamically-typed language is not C++-compile-absolute. Here it
reduces to three concrete teeth, stated plainly: (1) the reader type **has no `put`/`write`
method** (deleted capability — the dominant guarantee); (2) **mypy-strict** on the substrate
package makes a write-through-reader a type error in CI (the P11 sparing tooth); (3) a
**construction-time guard** on the staging/live boundary. This is a real floor, not aspiration —
but it is honest that the enforcement is deletion + CI + guard, not language impossibility.

### Reversibility / self-audit / adversary target

Two-way door (rebuild mechanism is internal). *Null?* F4-3, rejected. *Delegation?* the paced
primitive (S4/thermia) is the delegated rate-safety substrate — the rebuilder does not
re-implement pacing. **Adversary target:** is a capability-typed reader enforceable enough in
Python to call "unconstructable," or is it aspirational without a runtime boundary test? Does
the atomic pointer-flip actually serialize against a concurrent rebuild of the same ArtifactId
(two rebuilders racing the pointer)?

---

## F5 — Consumer contracts (CLI, service, MCP/delegated-fleet) → DP-3

> **F5 (charter):** "Consumer contracts (CLI, service, MCP/delegated-fleet)."
> **CRITICAL SVR finding:** the P2 refuse-loud `PlaneDivergenceError` guard currently protects
> ONLY the offline/CLI path. Fresh-verified at HEAD: `_guard_plane_divergence` is called solely
> from `offline._resolve_section_keys` (CLI). The live-service + MCP query path
> (`services/query_service.py` -> `universal_strategy.py` `cache.get_async` -> `DataFrameCache`
> -> `storage.load_dataframe`), `metrics/freshness.from_s3_resolved`, `matching.py`
> `cache.get_async`, and the force-warm recheck are ALL unguarded. F5 MUST make refuse-loud
> unconstructable-to-bypass on EVERY consumer.

### Option slate

**Option F5-1 — Guard at each call-site (v1's approach).**
- **REJECTED (the proven failure).** This is precisely RC-C's defect: refuse-loud wired into ONE
  call-site (CLI) and missed on service/MCP/matching/force-warm. "Per-call-site guarding is
  exactly how v1 drifted and missed a layer." Enumerated only to force the defense.

**Option F5-2 — Single typed read choke-point returning a `Provable | Refused` result
(PROVISIONAL CHOICE).**
ALL consumers read through ONE `SubstrateReader.read(ArtifactId) -> ServedNumber`, where
`ServedNumber` is a sum type: `Provable(value, freshness_proof) | Refused(reason)`. Raw
`storage.load_dataframe` is made private — no consumer can call it. To obtain a bare number a
consumer MUST handle `Refused` (the type yields no value otherwise). The freshness gate (F2)
lives INSIDE the choke-point: `read` checks `now - built_from_live_at <= SLA` AND content
self-consistency; failure returns `Refused`.
- Advantage: RC-C applied to serving — correctness by construction, ONE gate, no drift. A NEW
  (6th) consumer automatically inherits refuse-loud; there is no bypass API to forget. P2 literal.
- Disadvantage: all consumers migrate to the choke-point (blast radius — but that IS the cutover,
  P4). The Result type changes call-site signatures across services (CLI/service/MCP) — a
  cross-service contract change (Door #3).

**Option F5-3 — Refuse at the storage layer (the store returns `Refused` for stale/inconsistent).**
The store itself refuses; even direct store access is safe.
- Advantage: the gate is the deepest layer; nothing can read under it.
- Disadvantage: conflates storage (persistence) with policy (SLA/refusal) — a DIP /
  single-responsibility violation; the store should not know the serving SLA. It also BLOCKS
  legitimate raw-artifact consumers that must see stale bytes: the rebuilder (reads prior-good to
  compute a delta) and the S7/S8 parity harness (reads BOTH planes to explain divergence). The
  gate belongs at the SERVING layer, not storage.

**Option F5-4 — Delegation: an HTTP-serving middleware (FastAPI dependency) checks freshness.**
Wrap every dataframe-serving route in a dependency that inspects the freshness proof.
- Disadvantage: covers only HTTP routes — the CLI and in-process library consumers
  (`universal_strategy`, `matching`) bypass it. Same partial-coverage drift risk as F5-1 for
  non-HTTP consumers. Rejected as SOLE mechanism; may ride ATOP F5-2 as defense-in-depth for the
  MCP HTTP surface.

### Provisional ruling (DOOR-PENDING — DP-3, operator)

**F5-2 (single typed read choke-point + `Provable | Refused` result), freshness gate inside the
choke-point, raw storage access private.** It is the RC-C construction for serving: refuse-loud
is unbypassable because there is exactly one read API and its return type forces refusal-handling.
F5-1 is the documented failure; F5-3 misplaces policy in storage and blocks the rebuilder + parity
harness; F5-4 covers only HTTP. Frozen invariant for the SERVING seam: **there is exactly one
public read path; it returns `Provable | Refused`; a bare value is unobtainable without handling
`Refused`; raw artifact bytes are reachable only by the rebuilder and the parity harness via a
distinct, non-serving capability.**

### Reversibility / door

DP-3, **Door #3 (operator)**. Cross-service consumer-contract change (CLI/service/MCP signatures) —
ONE-WAY once external consumers depend on the new contract. Operator ratifies with dissent.

### Self-audit / adversary target

*Null?* F5-1 (per-call-site), rejected. *Delegation?* F5-4 (middleware), rejected as sole
mechanism. *Existing substrate?* the choke-point reuses the memory->S3 tiering already in
`DataFrameCache` — it wraps, not replaces, the tier. **Adversary target:** does the choke-point
actually cover the MCP/delegated-fleet path, whose consumer is a SEPARATE PROCESS reading over
HTTP? Across a process boundary the `Provable | Refused` type is SERIALIZED — does refuse-loud
survive as an HTTP status/envelope the remote consumer cannot ignore, or does serialization let a
remote caller treat `Refused` as an empty-200? This is the hardest F5 seam and the reason it is a
door.

---

## F6 — Observability that cannot lie (RC-F) → auto-ratify (terraform limb = Door #4)

> **F6 (charter):** "Observability design that cannot lie (RC-F)."
> **Brief:** a plane-divergence / absolute-age alarm INDEPENDENT of query (v1's AL-5 only emits
> on query). Note the seam: autom8y-asana observability vs the parent-repo terraform (the DMS-24h
> dead-man is a PARENT-repo `.tf` resource). F6 auto-ratifies; its terraform limb is already Door #4.

### Option slate

**Option F6-1 — Query-independent scheduled provability evaluator + self-heartbeat (PROVISIONAL
CHOICE).**
A scheduled evaluator (EventBridge -> Lambda, or a warmer post-step that runs on schedule, NOT on
serve) iterates warmed `(project, entity)` artifacts, reads each `current.json` freshness proof,
and emits `provable = 1/0` per artifact: provable iff `now - built_from_live_at <= SLA` AND the
served bytes hash to `content_digest`. The alarm fires on `provable = 0`, on ABSENCE (artifact
unreadable = not provable = fire), AND the evaluator emits its OWN run-count so a stopped
evaluator alarms (a real dead-man on a LIVE metric). v1's query-gated AL-5 and the DMS-24h
dead-man-on-a-dead-metric are SUBTRACTED.
- Advantage: RC-F literal — reads the SAME freshness proof the serving gate reads (single source
  -> cannot read green while serving refuses). Fires when the WARM stops (the DEFECT scenario),
  when nobody queries (AL-5's gap), and when the artifact is missing (absence = alarm).
- Disadvantage: the evaluator is infra that could itself fail — mitigated by the self-heartbeat
  (its run-count is a CloudWatch metric with native "no data = alarm"). Cross-repo terraform
  (EventBridge/Lambda/alarm) is Door #4.

**Option F6-2 — Emit provability at SERVE time only (v1's AL-5 pattern).**
- **REJECTED.** Query-gated: a number nobody queries never emits -> stale-but-unqueried reads
  green. v1's exact RC-F failure. Forced-defense option.

**Option F6-3 — Emit provability from the rebuild (warm) path only.**
The warmer emits build-from-live age per artifact at the end of each warm.
- **REJECTED as sole mechanism.** If the WARM stops (exactly the DEFECT — the v2 plane froze
  because only the entity-blind prober wrote), no emission -> no alarm -> green-while-broken. The
  alarm must be independent of the warm too. F6-3's emission is fine as an ADDITIONAL signal but
  cannot be the alarm's sole source.

### Provisional ruling (AUTO-RATIFY, pending arch-adversary; terraform rides Door #4)

**F6-1 (query-independent scheduled provability evaluator + self-heartbeat).** Only option that
fires on all three green-while-broken modes: warm-stopped, query-absent, artifact-missing. Frozen
invariant for the OBSERVABILITY seam: **provability is evaluated on a schedule independent of
serve and of warm; it reads the same freshness proof the serving gate reads; absence of proof is a
firing condition; the evaluator emits a heartbeat so its own silence alarms.** The autom8y-asana
emission code auto-ratifies; the parent-repo terraform limb is the EXISTING Door #4 (no new door).

### Reversibility / self-audit / adversary target

Two-way door (autom8y-asana emission) + operator terraform apply (Door #4, one-way-ish infra).
*Null?* F6-2 (serve-time), rejected. *Existing substrate?* reuses the warmer's schedule +
CloudWatch EMF already in `metrics/cloudwatch_emit.py`. **Adversary target:** who watches the
watcher's watcher? The self-heartbeat bounds the regress at one level (CloudWatch native no-data
alarm is the terminal) — attack whether that terminal is genuinely un-fakeable, or whether a
partial evaluator run (reads SOME artifacts, emits a heartbeat, but silently skips the broken one)
can still read green.

---

## Cross-fork coherence (the six rulings compose)

The rulings are not independent picks; they compose into one legible whole:

- F1/F3 Option C's `current.json` pointer is WHERE F2-1's freshness proof (`built_from_live_at`,
  `content_digest`) lives — one GET reads both the live version and its proof.
- F4-1's atomic swap IS the pointer-flip of F1/F3 Option C — the rebuild's final act.
- F5-2's choke-point reads that pointer and applies F2-1's freshness law to return
  `Provable | Refused`.
- F6-1's evaluator reads the SAME pointer + proof F5-2 reads — so serving and observability share
  one freshness source (the RC-F "cannot read green while broken" construction).
- F3's required-`entity_type` key is the RC-C substrate every writer and reader threads by type,
  not by discipline.

If the operator ratifies a DIFFERENT DP-2 shape (A or B) or DP-3 contract, the composition above
re-derives — the seams (next section of the TDD) are the stable contract; the shape is the
variable. That is the P4 whole-design property: the pieces interlock, and the interlock survives a
door ruling because the seams, not the shapes, are frozen.

---

*Authored by architect (10x-dev), S1, 2026-07-27. DRAFT — Phase-1 of the S1 three-phase DAG.
Provisional rulings stand for the arch-adversary (rite-disjoint, arch rite) to attack in Phase-2;
DP-2 and DP-3 operator packets are authored in Phase-3 with the dissent attached. No fork is
finalized here (P8). Evidence grade MODERATE (self-authored corridor design; self-ref ceiling).*
