---
type: handoff
artifact_id: CHARTER-f1a-budget-allocator-2026-07-20
status: accepted
source_rite: thermia→arch→10x-dev (cross-rite-seamed procession)
date: 2026-07-20
initiative: F1a — asana cross-consumer rate-limit budget allocator (offer-substrate freshness cure)
grant: operator user-grade execution authority (2026-07-20), autonomous THROUGH live-leg-proven/INERT; GO-LIVE operator-only
adjudicated_by: pythia (thermia+arch DAG), 2026-07-20
telos: TELOS-asana-substrate-freshness-2026-07-13 (ratified)
---

# CHARTER / SELF-PROMPT — F1a Asana cross-consumer budget allocator (HIGHEST-BLAST BUILD)

> **Turnkey, self-contained execution charter.** Paste into a FRESH session launched in
> **`autom8y-asana`** (NOT the monorepo — F1a roots here). `ari rite thermia` for Phases 0–2,
> switch to `arch` at the thermia→arch seam, co-seat `10x-dev` at the arch→10x seam. A fresh,
> clean-context session is the right vehicle. The charter is idempotent and resumable.

---

You hold **USER-GRADE execution authority** (operator-granted 2026-07-20) to **design + build**
a cross-consumer rate-limit allocator on the LIVE shared Asana **1500/60s** budget — the durable
cure for the offer-frame sawtooth (GID `1143843662099250` oscillating 1344s↔14229s under the
2026-07-10 429 storm) that starves the whole ASR verdict surface. Full cross-repo filesystem
access. **This is the highest-blast build of the arc:** a wrong allocation makes the 429 storm
WORSE fleet-wide (every Asana consumer, not just the offer warmer). So the grant runs **measure →
model → litigate → adversary-gate → build → canary → live-leg-prove**, then **STOPS at GO-LIVE
and surfaces.** Coordinate via one **potnia** across the whole seam; report at each gate;
**HALT + surface at any fence.**

## STRICT FENCES (confirm-first EVEN under this grant — never fire; surface)
- **F-a — GO-LIVE is OPERATOR-ONLY.** Activation / `NullCacheProvider`-unpin / any flip that puts
  the allocator onto the shared budget is the operator's carve-out (cross-consumer arbitration +
  client-visible risk). The autonomous grant ends at **LIVE-LEG-PROVEN / INERT** — then surface.
- **F-b — no budget-consuming experiment.** Phase 1 read-only; the adversary gate is design-level;
  the live-leg is read-only or bounded inside the allocator's OWN protected quota. **No
  fault-injection or load-probe into a producer already in a 429 storm.**
- **F-c — client-felt → surface NOW.** If C1 proves a client render reads the starved offer path,
  HALT the autonomous flow and notify the operator immediately (Pillar-9).
- **F-d — measure, never assume.** C1 MEASURES who burns the budget; the EBI-flip correlation is
  an UNVERIFIED hypothesis. A warmer-side patch under an un-attributed storm "burns the wave
  without moving G2."

## THE C1 KEYSTONE + FELT-LINE FORK (hard first gate)
**C1 (attribution) blocks ALL downstream — no allocator design exists before the heat-map.** At
C1 exit the felt-line FORKS and HALTS:
- **client-felt PROVEN** (insights render reads the starved `1143843662099250` path → wrong
  client coverage numbers = the Pillar-5 silent-wrong-outcome, the worst failure): **Pillar-9
  fire → HALT, notify operator NOW, re-rank.** Outranks the substrate telos.
- **internal-only:** proceed under the substrate telos (foundation-hardening; Q3 consolidation).
Until resolved, treat as **potentially client-felt** and protect accordingly.

## THE MODEL FORK (Phase 2a)
- **budget INSUFFICIENT** (1500/60s structurally too small for real demand): the allocator is
  MOOT → route to demand-reduction / an operator budget-increase ask. Do NOT build an allocator
  that can't help.
- **budget MALDISTRIBUTED:** capacity-engineer designs a protected-minimum quota (measured
  sizing from C1) — the substrate warmer gets a protected floor.

## THE DAG (execute verbatim)
| # | Node | Agent (rite) | P/S | Produces / Proves | Gate | Fence |
|---|------|-------------|-----|-------------------|------|-------|
| **0** | AL-5 sparsity-blindness fix + per-GID freshness SLO (= telos C2) | thermal-monitor (thermia) | ∥ to 1–4 | AL-5 reads-honest (Period↔emission cadence / M-of-N / continuous emit); per-GID SLO owned | AL-5 GREEN **gates Phase 6** | read-only reconfig |
| **1** | **C1 attribution KEYSTONE** — heat-map who burns 1500/60s across storm window (~2026-07-10T15:50Z) + felt-line verdict | heat-mapper (thermia) | **S, blocks ALL** | dated per-consumer WHO-burns receipt; felt-line code-path receipt | **HARD GATE** | F-b, F-d read-only |
| **2a** | MODEL — insufficient vs maldistributed | systems-thermodynamicist (thermia) | S | diagnostic fork verdict | fork gates 2b | analytical only |
| **2b** | Design allocation/partition (protected-minimum, measured sizing) | capacity-engineer (thermia) | S — **conditional on "maldistributed"** | allocation proposal sized from C1 | → HANDOFF-1 | no live load-test |
| — | **HANDOFF-1** (cross-rite) | potnia | seam | C1 receipt + felt verdict + model + allocation proposal | arch premise-validation entry-gate | — |
| **3a∥3b** | Consumer topology map ∥ blast-radius/coupling DAG | topology-cartographer ∥ dependency-analyst (arch) | ∥ | who shares the choke; allocator coupling | — | — |
| **3c** | SPOF/boundary — does the allocator become a NEW single-writer on the shared producer? | structure-evaluator (arch) | S | boundary verdict | — | — |
| **3d** | Kill-switch + rollback-boundary spec (light) | remediation-planner (arch) | S | kill-switch contract | **pythia re-adjudicates option-lens slate** | — |
| **4** | **ADVERSARY-GATE** — falsify *"does this REDUCE fleet 429s, or SHIFT the starvation?"* — name WHICH consumer yields, by how much, and whether it's client-felt | arch-adversary (arch) | S | two-sided verdict | **HARD GATE — no build until shift-starvation defeated** | F-b design-level only |
| — | **HANDOFF-2** (cross-rite) | potnia | seam | adjudicated ADR/TDD + adversary conditions + AC + canary spec + kill-switch | — | — |
| **5** | BUILD to PR/INERT (default-off, behind kill-switch) | principal-engineer (10x) | S | **BUILT → MERGED-INERT** | green CI | never unpin/activate in the build PR |
| **6** | **CANARY-PROVEN** (2-sided, RED-before archived) | principal-engineer + qa-adversary (10x) | S (needs #0 GREEN + #5) | deliberately-maldistributed input the allocator correctly reprioritizes GREEN; pre-fix starvation reproduced RED-before | 2-sided suite green (teeth) | discriminating-canary; no prod defect-injection |
| **7** | **LIVE-LEG-PROVEN** vs live Asana | qa-adversary (10x) | S | allocator behaves on the real budget | **LAST autonomous rung** | F-b read-only / own-quota-bounded |
| **8** | **GO-LIVE GATE** | **OPERATOR ONLY** | HALT | activation / unpin on the shared budget | **HARD HALT — grant STOPS at #7, surfaces** | F-a |
| **9** | WATCHED-LIVE | thermal-monitor (thermia) | post-op | per-GID SLO + fleet-429 rate through ≥1 storm-equivalent window; closes the arc | — | — |

## RITE COMPOSITION
thermia (Phases 0–2, in `autom8y-asana`) **--switch-->** arch (Phases 3–4, native pantheon incl.
arch-adversary) **--HANDOFF-->** 10x-dev (Phases 5–7, co-seat; already holds the substrate /goal
charge). One potnia holds the whole seam.

## REALIZATION RUNGS (name in every receipt; never round up)
`BUILT < MERGED < CANARY-PROVEN < LIVE-LEG-PROVEN < [OPERATOR GO-LIVE] < WATCHED-LIVE`.
Telos rung ladder: `attributed < cured < detecting < protecting-prod`.

## SKIP (ceremony)
10x `architect` (arch's structure-evaluator + HANDOFF-2 TDD own the design) · 10x
`requirements-analyst` (fold into HANDOFF-2) · a separate thermia `potnia` (one coordinator) ·
arch `remediation-planner` DE-SCOPED to kill-switch/rollback spec only. `capacity-engineer` is
CONDITIONAL (fires only on the "maldistributed" fork).

## NOT THIS BUILD (separate procession)
**SIBLING-1** (TASK-cache hit-path projection-coverage; `clients/tasks.py`; done-bar UNPINNED) is
an ORTHOGONAL failure class (wrong-data-served, not capacity-starvation) → its own ticket. **One
coupling to honor:** SIBLING-1's `union(stored ∪ requested ∪ STANDARD)` hydration AMPLIFIES budget
draw → count it as a consumer in the C1 heat-map. SIBLING-2 / ITEM-5 are out of scope entirely.

## Reporting + resume
Report at each gate (C1, model fork, adversary gate, CANARY, LIVE-LEG) and at any HALT. Resume
anchor: {current node} / {last HANDOFF artifact path} / {rung reached} — every node is an
idempotent checkpoint.

## Ground (read; do not re-derive — litigate the design ON these)
- `.ledge/decisions/TELOS-asana-substrate-freshness-2026-07-13.md` (ratified telos; C1/C2; felt-line)
- `.ledge/handoffs/HANDOFF-asr-to-substrate-durability-finding-2026-07-14.md` (live evidence; AL-5 defect; F1a-budget-partition named as the durable cure)
- `.ledge/specs/FRAME-sibling-substrate-arch-sprint-2026-07-08.md` + `.ledge/reviews/HANDOFF-arch-to-10xdev-sibling-substrate-2026-07-08.md` (arch-DAG recipe; realization rungs)
