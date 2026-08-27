---
type: handoff
artifact_id: HANDOFF-thermia-to-arch-f1a-budget-allocator-2026-07-20
status: proposed
handoff_type: cross-rite (thermia → arch)
procession_id: f1a-budget-allocator
source_rite: thermia
source_station: thermia (Phases 0–2)
target_rite: arch
target_station: arch (Phases 3–4)
initiative: F1a — asana cross-consumer rate-limit budget allocator (offer-substrate freshness cure)
telos: TELOS-asana-substrate-freshness-2026-07-13 (ratified)
charter: CHARTER-f1a-budget-allocator-2026-07-20 (verbatim-execute; DAG nodes 0–9)
date: 2026-07-20
adjudicated_by: pythia — felt-line fork Branch B CLEAN; model fork Branch B MALDISTRIBUTED (arithmetic-independence re-computed)
grant: autonomous THROUGH live-leg-proven/INERT; GO-LIVE (node 8) operator-only
max_rung_claimed: attributed (C1) + detecting (AL-5) + pre-BUILT design proposal — nothing cured, nothing protecting-prod
artifacts:
  - .sos/wip/thermia/f1a/thermal-assessment.md            # node 1 / C1 attribution
  - .sos/wip/thermia/f1a/ADJUDICATION-felt-line-fork.md   # pythia felt verdict
  - .sos/wip/thermia/f1a/cache-architecture.md            # node 2a / model
  - .sos/wip/thermia/f1a/ADJUDICATION-model-fork.md       # pythia model verdict + C-1..C-11
  - .sos/wip/thermia/f1a/capacity-specification.md        # node 2b / allocation proposal
  - .sos/wip/thermia/f1a/EXECUTION-RECEIPT-al5-reconfig.md # node 0 / AL-5 + per-GID SLO
acceptance_criteria:
  - C1 attribution is MEASURED per-consumer and anchored (not inherited; EBI onset falsified)
  - model verdict DERIVED from shown arithmetic, re-computed independently by pythia
  - felt verdict rests on a code-path receipt (Branch B CLEAN; residual closed at commit a7823851)
  - allocation names WHO yields + quantified magnitude (ECS; 142/min worst-minute = 1.54% of 3h)
  - every attributed/verified/derived/detecting token carries a receipt/VERDICT anchor or DEFER tag (telos-integrity Gate C)
---

# HANDOFF-1 — thermia → arch: F1a budget allocator (measured · adjudicated · pre-BUILT)

## 0. Rung-honesty banner (§D item 5 — read first)

The thermia seam claims exactly three rungs, none rounded up:
- **C1 = `attributed`** — verdict anchored to `.sos/wip/thermia/f1a/thermal-assessment.md`.
- **AL-5 (node 0) = `detecting`** — two-sided teeth proven, anchored to `.sos/wip/thermia/f1a/EXECUTION-RECEIPT-al5-reconfig.md`.
- **Allocator = pre-BUILT DESIGN PROPOSAL** — sized in `.sos/wip/thermia/f1a/capacity-specification.md`; NOT built, NOT merged, NOT canary-proven.

Nothing is `cured`; nothing is `protecting-prod`. Those rungs live downstream of the operator GO-LIVE gate (node 8). Autonomous grant continues into arch Phases 3–4 at **design-level only** (F-b).

**Receipt-grammar note (telos-integrity Gate C):** anchors below are artifact-level receipt/VERDICT citations (Gate C disjunct (b)) into `.sos/wip/thermia/f1a/`; the pythia adjudication files are VERDICT-class. Line-pins are affixed against those source artifacts. Un-anchorable forward claims carry an explicit `[DEFER-…]` tag.

---

## 1. C1 attribution receipt (§D item 1 · pre-answers arch demand: *measured per-consumer, anchored*)

- **ECS service = 100% of measured 429s across ALL windows** — the shared-budget draw that starves the substrate warmer is attributed, single-consumer, to the ECS service [anchor: `.sos/wip/thermia/f1a/thermal-assessment.md`].
- **EBI-flip onset hypothesis FALSIFIED** — the storm predates `2026-07-10T15:50Z` and is diurnal-bursty since ≥`2026-07-08`; attribution was measured against the WIDER window, not the nominal onset (F-d honored) [anchor: `.sos/wip/thermia/f1a/thermal-assessment.md`].
- **SIBLING-1 `union(stored ∪ requested ∪ STANDARD)` hydration** counted as a consumer line-item in the heat-map per the charter's one honored coupling [anchor: `.sos/wip/thermia/f1a/thermal-assessment.md`].
- **Read-only throughout** — no fault-injection / load-probe into a producer in a 429 storm (F-b honored).
- **Rung: `attributed`** — verdict anchored [`.sos/wip/thermia/f1a/thermal-assessment.md`].

*Why this defeats onset-anchor theater:* the attribution is against the wider diurnal-bursty window with a named per-consumer share (ECS = 100%), not a restatement of the 07-13 service-level narrative.

---

## 2. Felt verdict (§D item 2 · pre-answers arch demand: *code-path receipt, not circumstantial*)

- **Felt-line = NO / internal-only — Branch B CLEAN** — pythia adjudication anchored to `.sos/wip/thermia/f1a/ADJUDICATION-felt-line-fork.md`. No F-c fire; autonomous flow proceeded correctly.
- **Residual closed** — the open coupling residual was closed via cross-repo receipt at **commit `a7823851`** (code-path receipt; not circumstantial).
- **`/section-timelines` ruled client-felt-ADJACENT** — NOT client-felt, but adjacent → carried as **`[DEFER-WATCH-FELT-ADJ]`** (see §11). Arch MUST re-test this adjacency at 3b: if ECS throttling touches the `/section-timelines` surface, the adjacency can escalate to F-c.

*Why this defeats felt-theater:* the verdict is a code-path receipt with a commit anchor, not a circumstantial "a client surface exists" inference. The one adjacency is named and watched, not silently dropped.

---

## 3. Model verdict + arithmetic (§D item 3 · pre-answers arch demand: *derived from shown arithmetic*)

- **MALDISTRIBUTED on BOTH axes — Branch B** — pythia adjudication with **arithmetic-independence verified by re-computation** anchored to `.sos/wip/thermia/f1a/ADJUDICATION-model-fork.md`. The verdict is independently re-derived, not asserted.
- **HARD constraints C-1..C-11** travel with this handoff — full text in `.sos/wip/thermia/f1a/ADJUDICATION-model-fork.md`. Two are surfaced explicitly for arch:
  - **C-10 → flag at 3c** (SPOF / single-writer boundary constraint).
  - **C-11 (NEW) = claimable-floor** — the floor must be claimable independent of queue position; designed-to-constraint with a **build-time instrumentation prerequisite** (node-5 obligation; see §4 and `[DEFER-BUILD-C11]`).
- **The shown arithmetic (derived, not picked):**
  - Shared budget = **1500 req / 60 s**.
  - Warmer protected floor = **3,291 parent-GID gap set ÷ 30-min warm window ≈ 109.7/min ≈ 110/60s**.
  - Allocation closes exactly: **110 (warmer floor) + 1390 (all other consumers, incl. ECS) = 1500/60s**.

*Why this defeats model-theater:* the maldistributed ruling is re-computed independently by pythia, and every number is derived from C1's measurement — the mandate's protected-floor presumption did NOT pre-empt the fork test (F-d).

---

## 4. Allocation proposal (§D item 4 · pre-answers arch demand: *WHO yields + quantified, for the node-4 adversary*)

- **Protected-minimum warmer floor = 110/60s, queue-position-INDEPENDENT.** The offer key sits at **position 17-18 of 68**, past the 16-key budget — a naive FIFO queue never reaches it, so the floor MUST be claimable regardless of queue position (this is why C-11 exists) [anchor: `.sos/wip/thermia/f1a/capacity-specification.md`].
- **WHO YIELDS: the ECS service. HOW MUCH: 142/min in the worst minute = 1.54% of ECS's 3-hour traffic** [anchor: `.sos/wip/thermia/f1a/capacity-specification.md`]. **These are the quantified numbers the node-4 adversary MUST falsify against** (§6).
- **C-11 build prerequisite:** the claimable-floor requires build-time instrumentation to be real — carried as **`[DEFER-BUILD-C11]`** into HANDOFF-2's build AC.
- **SPOF / single-writer question → arch 3c** — the capacity spec explicitly defers the "does the allocator become a new single-writer on the shared producer?" boundary to structure-evaluator (C-10).
- **3 operator escalations** enumerated in `.sos/wip/thermia/f1a/capacity-specification.md` — genuine trade-offs against client-felt consumers; per the ratified F1a mandate these **escalate to the operator, not adjudicated locally**. Carried as **`[DEFER-OP-ESCALATION ×3]`** (see §11).

*Why this defeats rung round-up:* this is a sized PROPOSAL, pre-BUILT — the floor is not yet claimable in code (C-11 instrumentation is a build obligation).

---

## 5. Node-0 status (§D item 6 · AL-5 sparsity fix + per-GID SLO — telos C2)

- **Rung = `detecting`; teeth proven TWO-SIDED** (RED-before archived: a deliberately-starved GID actually trips the reconfigured alarm — not a green dashboard) [anchor: `.sos/wip/thermia/f1a/EXECUTION-RECEIPT-al5-reconfig.md`].
- **Gates Phase 6 (canary), NOT this handoff** — node 0 ran ∥ and does not block arch Phases 3–4.
- **TF codification routed to the node-5 PR** — the alarm reconfig lands as Terraform in the build PR: **`[DEFER-BUILD-TF-AL5]`**.
- **SNS gap surfaced** — a notification-path gap identified during the reconfig: **`[DEFER-WATCH-SNS]`** (see §11).

---

## 6. ARCH-PHASE QUESTION LIST (execute charter DAG nodes 3a–4)

**3a — topology-cartographer (consumer topology map · ∥ 3b):**
Map every consumer of the shared 1500/60s Asana budget and who shares the choke. Anchor consumers: ECS service (100% of 429s), the substrate warmer (`hierarchy_gap_warming`, the 3,291-GID gap set), SIBLING-1 union-hydration. Resolve: is ECS a single service or a fleet of tasks (does it need per-task or per-service quota)? Does the warmer share a process/credential boundary with any client-felt or client-felt-ADJACENT path (`/section-timelines`)? Deliver the topology that the allocator will arbitrate over.

**3b — dependency-analyst (blast-radius / coupling DAG · ∥ 3a):**
Build the coupling DAG for the 142/min ECS yield. What depends on ECS's full throughput? Compute the blast radius of throttling ECS by 1.54% of its 3h volume. **CRITICAL:** trace whether `/section-timelines` (client-felt-ADJACENT, §2) sits downstream of ECS — if the ECS yield degrades `/section-timelines`, the adjacency escalates to F-c and the whole procession re-ranks. Deliver the allocator coupling map.

**3c — structure-evaluator (SPOF / single-writer boundary — FLAG C-10 EXPLICITLY):**
The capacity spec routed the SPOF question here. **Constraint C-10 (from ADJUDICATION-model-fork.md) binds this node — carry it verbatim.** Does introducing a central budget-arbiter create a NEW single point of failure that, on its own death, starves ALL consumers (strictly worse than today's maldistribution)? Evaluate: allocator in-path (every request transits it) vs advisory (consumers self-limit against a published floor). Deliver the boundary verdict + the allocator's own failure mode.

**3d — remediation-planner (kill-switch + rollback boundary; light) + pythia option-slate re-adjudication:**
Spec the default-off kill-switch and rollback boundary (charter node 5 requires the allocator MERGED-INERT behind a kill-switch). Define instant-disable → revert to today's un-arbitrated behavior. **Per the charter DAG, pythia RE-ADJUDICATES the option-lens slate at this node** — surface the slate for re-adjudication: (i) allocator in-path, (ii) allocator advisory, (iii) demand-reduction fallback (the "insufficient" escape, now moot given MALDISTRIBUTED but retained as a rollback option).

**4 — arch-adversary (HARD GATE — falsification target, quantified):**
Falsify: **"does this REDUCE fleet 429s, or merely SHIFT the starvation?"** Named target with the quantified yield: **ECS yields 142/min worst-minute = 1.54% of 3h traffic; warmer claims a 110/60s queue-position-independent floor; 110 + 1390 = 1500.** The adversary MUST prove two-sided: (a) capping ECS at 1390/60s does NOT create a new starvation on ECS's own downstream (tie to 3b blast-radius), and (b) the warmer's 110/60s floor is actually CLAIMABLE (C-11) rather than re-consumed by other consumers filling the 1390 pool. **HARD GATE — no build (node 5) until shift-starvation is defeated.** Fence: F-b — design-level falsification only; NO budget-consuming experiment against a producer in a storm.

---

## 7. arch premise-validation ENTRY-GATE — pre-answered

| arch entry-gate demand | Satisfied by | Anchor |
|---|---|---|
| Attribution MEASURED per-consumer, not inherited | ECS = 100% of 429s, wider window, EBI falsified | §1 · `.sos/wip/thermia/f1a/thermal-assessment.md` |
| Model verdict DERIVED from shown arithmetic | 3,291÷30min→110; 110+1390=1500; re-computed by pythia | §3 · `.sos/wip/thermia/f1a/ADJUDICATION-model-fork.md` |
| Felt verdict on a CODE-PATH receipt | Branch B CLEAN; residual closed at commit `a7823851` | §2 · `.sos/wip/thermia/f1a/ADJUDICATION-felt-line-fork.md` |
| WHO yields, NAMED + QUANTIFIED (arms node-4 adversary) | ECS; 142/min worst-minute = 1.54% of 3h | §4 · `.sos/wip/thermia/f1a/capacity-specification.md` |
| Gate C: attributed/verified tokens carry anchor or DEFER | Every claim §1–§5 anchored or DEFER-tagged | §11 registry |

---

## 8. FENCES that bind arch

- **F-b — design-level ONLY.** Phases 3–4 are analytical/design; the adversary gate falsifies on paper. NO fault-injection or load-probe into ECS or the warmer while the storm is live. NO budget-consuming experiment.
- **F-a — GO-LIVE is OPERATOR-ONLY.** The autonomous grant ends at LIVE-LEG-PROVEN/INERT (node 7). Arch never activates, never unpins, never puts the allocator on the shared budget.
- **F-c — client-felt → surface NOW.** The `/section-timelines` client-felt-ADJACENT residual is live: if 3b finds ECS-yield degrades that surface, HALT and notify the operator.
- **F-d — measure, never assume.** Carried intact: arch designs ON the C1 measurement; the EBI hypothesis is falsified and must not be re-imported.

---

## 9. Realization-rung ladder (name in every downstream receipt; never round up)

`BUILT < MERGED < CANARY-PROVEN < LIVE-LEG-PROVEN < [OPERATOR GO-LIVE] < WATCHED-LIVE`
Telos ladder: `attributed < cured < detecting < protecting-prod`.
**Current position:** `attributed` (C1) + `detecting` (AL-5 node 0); allocator = pre-BUILT proposal. Arch adds no rung — it produces the adjudicated ADR/TDD + adversary conditions + AC + canary spec + kill-switch for HANDOFF-2.

---

## 10. RESUME ANCHOR

- **Node:** HANDOFF-1 authored/complete → next = arch **node 3a ∥ 3b** (topology ∥ blast-radius), then 3c (SPOF/C-10) → 3d (kill-switch + pythia option-slate) → **node 4 adversary HARD GATE**.
- **Last HANDOFF artifact:** `.ledge/handoffs/HANDOFF-thermia-to-arch-f1a-budget-allocator-2026-07-20.md`
- **Rung reached:** `attributed` + `detecting` + pre-BUILT allocation proposal.
- **Next HALT:** node-4 adversary gate (HARD — no build until shift-starvation defeated); then HANDOFF-2 (arch → 10x).

---

## 11. DEFER-WATCH REGISTRY (every carried DEFER, per defer-watch-manifest)

| ID | Carried item | Watch-trigger | Escalation / owner |
|---|---|---|---|
| DEFER-WATCH-FELT-ADJ | `/section-timelines` client-felt-ADJACENT (felt verdict §2) | 3b finds ECS-yield touches `/section-timelines` | F-c fire → operator; re-rank (arch) |
| DEFER-BUILD-C11 | claimable-floor build-time instrumentation prerequisite (C-11, §4) | node-5 build AC | HANDOFF-2 build AC (10x) |
| DEFER-BUILD-TF-AL5 | AL-5 alarm reconfig Terraform codification (§5) | node-5 PR | HANDOFF-2 build AC (10x) |
| DEFER-WATCH-SNS | SNS notification-path gap surfaced at AL-5 reconfig (§5) | alarm fires but SNS does not deliver | thermal-monitor (node 9) |
| DEFER-OP-ESCALATION ×3 | 3 operator escalations in capacity-specification.md (§4) | any client-felt trade-off adjudication | OPERATOR (per F1a mandate) |
| DEFER-CONSTRAINTS | C-1..C-9 HARD constraints (full text) | any arch design decision | ADJUDICATION-model-fork.md (arch reads verbatim) |

---

*Authored by potnia (single throughline, thermia→arch→10x seam) per CHARTER-f1a-budget-allocator-2026-07-20 HANDOFF-1 contract. thermia phases COMPLETE. Grant autonomous through node 7; GO-LIVE (node 8) operator-only.*
