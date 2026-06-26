---
type: spec                       # canonical .ledge type; this is an IC disposition / sequencing artifact
artifact_class: ic-disposition
plan_id: IC-DISPOSITION-cr3-serve-stale-section-sequencing-2026-06-04
title: "CR-3 IC disposition — serve-stale-section contract framing, gate sequencing, project-arm decoupling"
status: draft
decision_state: authored-not-run
rite: sre
author: incident-commander
date: 2026-06-04
initiative: cr3-fleet-data-plane-foundation-cutover
evidence_grade: moderate
# Self-ref MODERATE ceiling: this sre rite authored the receiver substrate + the §B lane. The
# only STRONG claims are rite-disjoint-corroborated (OQ-1 width, OQ-4 cred) or live-execution-
# measured (the §B 429 wall). The ≥99% cutover PASS is the chaos §D re-gate's to ISSUE — this
# IC disposition SEQUENCES the gates and FRAMES the consumer contract; it issues NO cutover PASS.
reversible_only: true            # AUTHOR-ONLY — .ledge authorship + describe. No merge, no apply,
                                 # no deploy, no knob edit, no lambda mutation, no secret op, no
                                 # re-enable of the paused §B lane. Nothing fired.
disjointness: "IC sequences the gates; the chaos §D re-gate (rite-disjoint) issues the ≥99% verdict; the consumer (autom8 arch/10x-dev) owns the contract answer. The IC does NOT decide the contract FOR the consumer."
grounding:
  - .ledge/decisions/CR3-FINAL-REGATE-PLAN-2026-06-03.md                         # §D re-gate plan + §1 PRE-SB-1
  - .ledge/decisions/ADR-section-10min-x-502-headroom-2026-06-03.md              # §A.2 headroom, §B infeasibility, §D seed
  - .ledge/handoffs/HANDOFF-releaser-to-sre-cr3-land-handback-2026-06-04.md      # IC-GATES 1-6 LANDED; step-i FAILED; re-scope ask
  - .ledge/handoffs/HANDOFF-asana-sre-to-autom8-cr3-return-3-2026-06-04.md       # CQ-RETURN-3 (delivered, UNANSWERED); knob implication; project decouple
  - .ledge/handoffs/HANDOFF-sre-to-rnd-cr3-section-cdc-materialization-2026-06-04.md  # section→CDC R&D route (status: pending)
  - .ledge/decisions/CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md                  # IC-GATE 7 / step j / step k sequencing
  - .sos/wip/cr3-verified-findings-2026-06-03.md                                 # V6 serve-stale read-path
---

# CR-3 IC DISPOSITION — serve-stale-section contract framing + gate sequencing

> **AUTHOR-ONLY — nothing fired.** This is the Incident Commander's disposition for the CR-3
> consumer-coupled section contract: the dependency graph (what gates what), the data-backed
> frame the consumer needs to answer **CQ-RETURN-3** (the IC does NOT answer it for them), the
> #55 / IC-GATE-7 / PRE-SB-1 / Stage-B holds, and the PROJECT-arm decoupling option. Every
> platform claim carries a `file:line` / exit-code / artifact receipt verified at source this
> pass, or is marked **[GS]** (grounded-state, asserted by a prior pass, not re-probed) or
> **UV-P**. Secret VALUES never printed. The §B SECTION warm lane STAYS PAUSED.

---

## §0. DISPOSITION FIRST (read this)

The CR-3 receiver substrate is **LANDED + HEALTHY** (IC-GATES 1–6). The §B ≤10-min/576s SECTION
warm lane is **FALSIFIED + PAUSED** — the failure is an **upstream Asana API rate-limit ceiling**
(5/34 GIDs in ~12 min against 896×429 → ~80 min projected = ~8× over the 576s contract), **not a
receiver compute gap**. The paradigm is therefore **re-scoped to SERVE-STALE-SECTION (V6)**:
project AND section both ride LKG-serve, builds absorbed by the 2048/8192 headroom.

Three things follow, and the IC sequences them:

1. **The contract decision is the CONSUMER's, and it is UNANSWERED.** CQ-RETURN-3 ("is 576s
   section freshness load-bearing for offer-join correctness, or is serve-stale-section at the
   achievable ~30–50 min acceptable?") was delivered in RETURN-3 §1 and has **not** been
   answered. The IC frames the data the consumer needs (§2 below) but does **not** decide it —
   only the offer-join correctness owner can. *(meet-the-real-need; do not relax the consumer
   for them — surface the achievable bound + the project §D evidence and let them choose.)*

2. **The arms decouple.** The PROJECT arm is **independent** of the section contract
   renegotiation (project rides 24h LKG; a frame an hour old is trivially within a 24h
   contract). It is **re-gateable + cut-over-able now** on the headroom-applied substrate. The
   SECTION arm waits on (a) the consumer's CQ-RETURN-3 answer, (b) the KNOB re-think coupled to
   that answer, and (c) — if 576s is load-bearing — the section→CDC R&D. **The IC's recommended
   sequencing decouples them** (§4) so PROJECT is not held hostage to the SECTION contract.

3. **The real section fix is OUT of the CR-3 critical path.** The section→CDC incremental-
   materialization track is routed to rnd/inquisition → thermia (`HANDOFF-sre-to-rnd-cr3-section-
   cdc-materialization-2026-06-04`, `status: pending`, consumer PRE-ACCEPTED at CQ-5). CR-3 ships
   the interim (serve-stale-section); CDC is the foundation evolution. It must NOT block, gate,
   or regress the CR-3 land.

---

## §1. THE DEPENDENCY GRAPH (what gates what)

The single load-bearing artifact of this disposition. Read top-to-bottom; each arrow is a
hard precondition.

```
                         ┌─────────────────────────────────────────────┐
                         │  IC-GATES 1–6 — LANDED + HEALTHY [GS/STRONG] │
                         │  (substrate: cpu=2048/mem=8192 task-def :471;│
                         │   knob {project:86400,section:576} live;     │
                         │   Secret 1 authoritative, Secret 2 preserved)│
                         └───────────────────────┬─────────────────────┘
                                                 │
                  ┌──────────────────────────────┴──────────────────────────────┐
                  │                                                               │
        ╔═════════▼═══════════╗                                       ╔═══════════▼════════════╗
        ║   PROJECT ARM        ║                                       ║   SECTION ARM           ║
        ║   (decoupled)        ║                                       ║   (consumer-gated)      ║
        ╚═════════╤═══════════╝                                       ╚═══════════╤════════════╝
                  │                                                               │
                  │                                          ┌────────────────────▼────────────────────┐
                  │                                          │  CQ-RETURN-3 ANSWER  ← CONSUMER  (open)   │
                  │                                          │  (a) accept serve-stale ~30–50min         │
                  │                                          │  (b) wait for section→CDC R&D             │
                  │                                          └────────────────────┬────────────────────┘
                  │                                                               │
                  │                                          ┌────────────────────▼────────────────────┐
                  │                                          │  T1 KNOB RE-THINK (sre)  ← coupled to ans │
                  │                                          │  loosen section=576 → achievable bound    │
                  │                                          │  (else section reads hit build/502 path)  │
                  │                                          └────────────────────┬────────────────────┘
                  │                                                               │
       ┌──────────▼───────────┐                                      ┌───────────▼────────────┐
       │ §D PROJECT-ARM RE-GATE│                                      │ §D SECTION-ARM RE-GATE  │
       │ ≥99% (chaos, disjoint)│                                      │ ≥99% serve-stale basis  │
       │ on headroom substrate │                                      │ (chaos, disjoint)       │
       └──────────┬───────────┘                                      └───────────┬────────────┘
                  │  PASS                                                         │  PASS
                  │                                                               │
       ┌──────────▼────────────────────────────┐              ┌──────────────────▼──────────────────────┐
       │ CONSUMER QA RE-GATE (project) green     │              │ CONSUMER QA RE-GATE (section) green +     │
       │                                         │              │ PRE-SB-1 (Section rollback-lever TEST)    │
       └──────────┬────────────────────────────┘              │ green  ← BLOCKING, consumer-prong         │
                  │                                            └──────────────────┬──────────────────────┘
                  │                                                               │
       🔒 IC-GATE 7 (project)                                       🔒 IC-GATE 7 (section)
                  │                                                               │
       ┌──────────▼───────────┐                                      ┌───────────▼────────────┐
       │ #55 merge (project    │   IRREVERSIBLE (cross-repo autom8)   │ #55 merge (section      │
       │ repoint)              │                                      │ repoint)                │
       └──────────┬───────────┘                                      └───────────┬────────────┘
                  │                                                               │
       ┌──────────▼───────────┐                                      ┌───────────▼────────────┐
       │ STAGE-B (project)     │   human/IC-gated; 7d S7 soak first   │ STAGE-B (section)       │
       │ retire fallback       │                                      │ retire fallback         │
       └──────────────────────┘                                      └─────────────────────────┘

   OUT OF CRITICAL PATH (parallel, non-blocking):
   section→CDC materialization R&D ── rnd/inquisition → thermia (status: pending)
   = the REAL fix that makes ≤10-min section freshness feasible; option (b)'s landing track.
```

**Sequencing receipts (verified at source this pass):**

- IC-GATE 7 fires on **§D PASS + consumer QA re-gate green** — `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md:369`
  (`🔒 IC-GATE 7 (cross-repo) ─── §D PASS + consumer QA re-gate green`) and `:296-303` (STEP j:
  "#55 merges **AFTER the receiver land AND after the §D re-gate PASS**"). **[STRONG — source-read this pass]**
- The §D re-gate runs **between step i and step j** and is **the gate on step j** —
  `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md:329` / `:335` ("Failure → recede per §D abort
  criteria; do NOT merge #55"). **[STRONG — source]**
- #55 = repo `autom8y/autom8`, base main, head `09e0f64b` (≡ local `ae41170c` by patch-id) —
  `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md:303`. **[GS — cross-repo, not re-probed this read-only pass]**
- PRE-SB-1 (the Section rollback-lever TEST) is **BLOCKING-before-Stage-B independently of the
  re-gate verdict** — `CR3-FINAL-REGATE-PLAN-2026-06-03.md:106-122` ("If PRE-SB-1 is absent at
  Stage-B time → Stage-B is BLOCKED independently of the re-gate verdict"). **[STRONG — source]**

---

## §2. THE DATA-BACKED CONSUMER FRAME (for CQ-RETURN-3 — the IC does NOT answer it)

The consumer (autom8 arch/10x-dev) owns the answer. The IC's job is to put the achievable reality
and the project-arm evidence in front of them so the answer is informed, not to choose for them.
This frame is to be **populated** from Lane C's section-frame-age measurement and Lane A's project
§D result; the slots below are explicit about what is known-now vs to-be-filled.

### 2.1 What serve-stale-section actually delivers (the achievable bound)

| Dimension | Value | Receipt / status |
|-----------|-------|------------------|
| 576s warm freshness via polling | **INFEASIBLE** (~8× over) | 5/34 GIDs / ~12 min / 896×429 → ~80 min projected. **[STRONG — live-execution-measured, RETURN-3 §0.2 / land-handback §3]** |
| Root cause | **Upstream Asana API rate limit on the resolver token** — NOT receiver compute | Raising `reserved_concurrency` WORSENS it (more parallel callers → more 429s). **[STRONG — live-attempt diagnosis]** |
| Achievable section cadence (serve-stale) | **~30–50 min** | 30-min bulk warmer `cron(0,30 * * * ? *)` ENABLED (68 keys = 34 GID × {project,section}) + ~46-min worst-case inter-warm on the heaviest GID. **[GS/MODERATE — RETURN-3 §1(a); ADR §B.1]** |
| Per-GID worst case (the heaviest) | BusinessUnits: 17 sections, per-section fetch 38s–326s, rebuild ~5.5 min | Blows a 10-min serial budget on ONE GID before any rate-limit. **[STRONG — gameday `warm-cadence-vs-lkg-ceiling-tension.md:10-14`]** |
| Build-on-read tail absorber | 2048/8192 headroom: ~3 safe ~2GB Polars builds + Retry-After backpressure | ADR §A.2; the headroom is the safety valve for the warm-miss/cold tail. **[MODERATE — self-ref sizing; the §D re-gate is the corroboration]** |
| **Measured live section frame-age distribution** | **← TO BE FILLED from Lane C** | The empirical "what is section freshness ACTUALLY delivering right now" — the single most decision-relevant datum for the consumer. |

### 2.2 The project-arm §D evidence (what cutover looks like when freshness is NOT contentious)

| Dimension | Value | Receipt / status |
|-----------|-------|------------------|
| Project contract | 24h (`"project": 86400.0`) — frame an hour old is trivially in-bound | `config.py:163`. **[STRONG — source-read this pass]** |
| Project build pressure | near-zero — project keys do NOT contend for the build semaphore | ADR §0 asymmetry; RETURN-3 §4. **[MODERATE — self-ref; §D project arm corroborates]** |
| **Project §D ≥99% result** | **← TO BE FILLED from Lane A** | The demonstration that the serve-stale paradigm clears ≥99% on the arm where freshness is not in tension — the proof-of-concept the section arm inherits. |

### 2.3 The frame to put to the consumer (verbatim ask, not an answer)

> "576s section freshness is not reachable by polling-warm on the resolver token (Asana rate
> ceiling, ~8× over — not our compute). Serve-stale-section delivers ~30–50 min today
> [+ the live frame-age distribution, Lane C]. The project arm clears the serve-stale paradigm
> at ≥99% [Lane A §D result]. **Two questions for you, the offer-join correctness owner:**
> (1) Is 576s load-bearing for offer-join correctness, or is ~30–50 min acceptable in the
> interim? (2) If 576s is load-bearing, the only feasible path is the section→CDC R&D (already
> routed, consumer PRE-ACCEPTED) — do you hold the section cutover for it, or accept the looser
> interim now and let CDC tighten it later? **The PROJECT arm is unaffected either way and can
> cut over independently** (see §4)."

The IC does **not** prefer (a) or (b) for the consumer. The IC's recommendation is procedural:
**answer CQ-RETURN-3 so the SECTION arm's knob + §D basis can be locked** — and **do not block the
PROJECT arm on that answer.**

---

## §3. THE HOLDS (what stays gated, and why)

| Item | State | Gate / precondition | Receipt |
|------|-------|---------------------|---------|
| **§B SECTION warm lane** | **PAUSED — STAYS PAUSED** | Re-enabling reasserts the 429 storm. Falsified for ≤10-min/576s. | `reserved_concurrency=0` + EventBridge rule `autom8-asana-cache-warmer-section-schedule` DISABLED. **[GS — current session grounded-state; RETURN-3 §0.2 / land-handback §3]** |
| **section=576 knob (T1 re-think)** | **LIVE — INVERSION HAZARD** | Loosen toward achievable serve-stale bound, **coupled to the CQ-RETURN-3 answer.** With the lane paused, 576 FORCES section reads onto the build/502 path (opposite of relief). Knob-edit is OUT of read-only scope; flagged for the sre knob re-think. | `config.py:160-165` (the hazard comment `:160-161` + the live `"section": 576.0` at `:164`). **[STRONG — source-read this pass]** |
| **PRE-SB-1 (Section rollback-lever TEST)** | **OPEN — consumer-prong, BLOCKING** | A tracked consumer test must drive `Section.get_df` with the flag patched OFF and assert `emit_fallback_signals(reason=REASON_FLAG_DISABLED, source=SOURCE_SECTION)` → `_get_df_legacy_sdk`, plus a companion `_flag_enabled is None` PRESERVES-satellite case. **Blocks Stage-B(section) independently of the §D verdict.** | `CR3-FINAL-REGATE-PLAN-2026-06-03.md:106-122`. H-2 branch is CODE-PRESENT (`section/main.py:679` `if _flag_enabled is False:`) but the TEST is absent. **[STRONG — rite-disjoint source-read of consumer code, per RETURN-3 §5.1]** |
| **#55 (consumer repoint) / IC-GATE 7** | **HELD** | Merges ONLY after §D PASS (arm-applicable) + consumer QA re-gate green. Section #55 additionally after PRE-SB-1 green. | `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md:369-370`, `:296-303`. **[STRONG — source]** |
| **Stage-B (fallback retirement)** | **HELD — human/IC-gated** | After 7-day S7 soak post-§D-PASS. Section Stage-B additionally gated on PRE-SB-1. | `CR3-FINAL-REGATE-PLAN-2026-06-03.md:267-270` (§8 routing). **[STRONG — source]** |
| **Secret 2 decommission** | **HELD — IC-gated, sequenced with task #73** | Only AFTER #55 repoint is live-verified (Secret 2 actively consumed, `LastAccessedDate=2026-06-03`). #343 declares the drift alarm, NOT the decommission. | `CR3-COORDINATED-LAND-RUNBOOK-2026-06-03.md:343`. **[GS]** |

---

## §4. THE PROJECT-ARM DECOUPLING (the recommended option to surface)

**RECOMMENDATION (procedural, IC-owned): decouple the arms. Cut the PROJECT arm over INDEPENDENTLY;
hold the SECTION arm on the consumer answer + CDC.**

Rationale — the PROJECT arm has **zero dependence** on the section contract renegotiation:
- Project rides 24h LKG (`config.py:163` `"project": 86400.0`) — serve-stale paradigm already
  satisfied; project reads almost never rebuild (project keys do not contend for the build
  semaphore — ADR §0 asymmetry; RETURN-3 §4). **[STRONG — config source; MODERATE — asymmetry self-ref]**
- The §D project arm has **no dependence on the section lane** (RETURN-3 §4: "re-gateable now").
- The KNOB INVERSION hazard is **section-only** — the project knob (86400) is not in tension.

**Decoupled sequence (project, runnable now):**
`§D PROJECT-arm re-gate (chaos, disjoint) PASS → consumer QA re-gate (project) green → IC-GATE 7 (project) → #55 project repoint → 7d S7 soak → Stage-B (project, human/IC-gated).`

**Held sequence (section, consumer-gated):**
`CQ-RETURN-3 answer → T1 knob re-think → §D SECTION-arm re-gate (serve-stale basis) PASS → consumer QA re-gate (section) green + PRE-SB-1 green → IC-GATE 7 (section) → #55 section repoint → 7d S7 soak → Stage-B (section).`

> **The decoupling decision the consumer must confirm:** RETURN-3 §7.3 already asks "OK to re-gate
> + cut over the PROJECT arm independently of the section contract renegotiation?" — that
> confirmation is the unblock for the project track. The IC recommends YES; the consumer ratifies.

**Caveat (honest):** decoupling assumes #55 can repoint project-only without coupling section in
the same merge. If #55's repoint is **all-or-nothing** (single flag flips both arms), the arms
CANNOT be split at the merge boundary and the project cutover inherits the section hold. **This is
a consumer-side fact about #55's granularity that the IC cannot verify from the receiver subtree.**

[UV-P: #55's repoint can flip the PROJECT arm independently of the SECTION arm (per-arm flag granularity, not all-or-nothing) | METHOD: deferred-to-consumer-confirm | REASON: #55 lives in autom8y/autom8 (cross-repo); arm-granularity of the repoint flag is a consumer-side fact not falsifiable from the receiver subtree this read-only pass — confirm with the consumer at CQ-RETURN-3 response time]

---

## §5. WHAT'S RUNNABLE-NOW vs CONSUMER-GATED (the bottom line)

**RUNNABLE NOW (no consumer dependency):**
- §D **PROJECT-arm** re-gate on the headroom-applied substrate (chaos-engineer, rite-disjoint).
- Lane C section-frame-age measurement (read/measure; reversible) — populates §2.1.
- Lane A project §D result — populates §2.2.

**CONSUMER-GATED (blocked on the autom8 consumer):**
- **CQ-RETURN-3 answer** — gates the SECTION knob re-think (T1) and the SECTION §D basis.
- **PROJECT-arm cutover confirmation** (RETURN-3 §7.3) — the YES that unblocks the project track.
- **PRE-SB-1** (Section rollback-lever TEST) — consumer-prong, BLOCKING-before-Stage-B(section).
- **#55 merge** (IC-GATE 7) — IRREVERSIBLE, cross-repo, gated on §D PASS + QA green (+ PRE-SB-1 for section).
- **Consumer QA re-gate** — per arm.

**OUT OF CRITICAL PATH (parallel, non-blocking):**
- section→CDC materialization R&D — rnd/inquisition → thermia (`HANDOFF-sre-to-rnd-cr3-section-cdc-
  materialization-2026-06-04`, `status: pending`). The real fix; option (b)'s landing track. Must
  NOT block, gate, or regress the CR-3 land.

**HELD (do not move without the gate):**
- §B section warm lane (PAUSED, falsified) — do NOT re-enable.
- Stage-B (both arms) — human/IC-gated, post-soak.
- Secret 2 decommission — IC-gated, post-#55-live.

---

## §6. ACID TEST (IC self-check)

*"If this incident happens again, will this disposition prevent a repeat?"*

The recurring trap this disposition guards against is the **stale-datum re-gate** — measuring the
section arm under the knob=576 + lane-paused substrate (which forces the build/502 path) and reading
the resulting <99% as a paradigm verdict. That is the 82%/86.8% INTERIM error repeated. This
disposition prevents it by: (1) re-scoping §D to the serve-stale-section basis (not 576s-warm),
(2) making the T1 knob re-think a **precondition** of the section §D run (so the re-gate measures
serve-stale, not forced-build), and (3) decoupling the project arm so a section-contract stall does
not freeze the whole cutover. The remaining recurrence risk is **the consumer not answering
CQ-RETURN-3** — which this disposition cannot fix (it is the consumer's call), only surface and
hold cleanly. **That hold is correct, not a failure: an honest "section is consumer-gated" beats a
rubber-stamped section cutover on a paradigm-wrong substrate.**

---

## §7. BOUNDARIES & EVIDENCE LEDGER (held throughout)

- **AUTHOR-ONLY — nothing fired.** No merge, no `terraform apply`, no deploy, no knob edit, no
  lambda mutation, no secret op. `origin/main` = `e57a3cba` (verified `git rev-parse origin/main`
  this pass); the working branch HEAD `a62fd401` (obs wiring) is one commit ahead and is NOT a
  CR-3 mutation. The §B section lane STAYS PAUSED.
- **Self-ref MODERATE ceiling.** This sre rite authored the substrate + the §B lane; the ≥99%
  cutover PASS is the chaos §D re-gate's to ISSUE. STRONG claims = rite-disjoint-corroborated
  (OQ-1 width, OQ-4 cred) or live-execution-measured (the 429 wall) or source-read-this-pass
  (knob, sequencing anchors). The IC issues NO cutover PASS.
- **The contract is NOT decided here.** CQ-RETURN-3 is framed (§2) for the consumer's answer;
  the IC does not choose (a) or (b) for them (meet-the-real-need).
- **Secret-value redaction:** no raw secret printed — Secret 1 client_id-prefix / sha-prefix /
  SecretId-name only where referenced.
- **[GS]** = grounded-state (AWS-runtime / cross-repo claims asserted by a prior pass, not
  re-probed this read-only pass): IC-GATES 1–6 AWS receipts, the §B pause state, #55 head SHA,
  Secret 2 LastAccessedDate.

### UV-P (open, carried)
[UV-P: #55's repoint can flip the PROJECT arm independently of the SECTION arm | METHOD: deferred-to-consumer-confirm | REASON: cross-repo arm-granularity fact, not falsifiable from the receiver subtree — see §4]

[UV-P: the live section frame-age distribution under the current (lane-paused, knob=576) substrate | METHOD: deferred-to-lane-C-measurement | REASON: populates §2.1; a read/measure Lane-C output, not authored by this IC disposition pass]

[UV-P: the §D PROJECT-arm ≥99% result | METHOD: deferred-to-lane-A-chaos-re-gate | REASON: populates §2.2; the chaos §D project-arm run is rite-disjoint and downstream of this disposition]

---

*Authored 2026-06-04 by the Incident Commander (sre rite). AUTHOR-ONLY — reversible: true; nothing
merged/applied/deployed/knob-edited/secret-touched; the §B section lane STAYS PAUSED. The contract
(CQ-RETURN-3) is FRAMED for the consumer, not decided. The ≥99% cutover PASS is the chaos §D
re-gate's to ISSUE. Self-ref MODERATE ceiling held; STRONG claims source-anchored inline.
Grounding: CR3-FINAL-REGATE-PLAN, ADR-section-10min-x-502-headroom, the releaser land-handback,
RETURN-3, the rnd section→CDC handoff, the coordinated-land runbook, and the V6 verified findings.*
