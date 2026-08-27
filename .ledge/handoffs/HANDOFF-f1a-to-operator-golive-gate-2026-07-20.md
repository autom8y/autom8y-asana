---
type: handoff
artifact_id: HANDOFF-f1a-to-operator-golive-gate-2026-07-20
status: proposed
handoff_type: operator-gate (procession → OPERATOR)
procession_id: f1a-budget-allocator
initiative: F1a — asana cross-consumer rate-limit budget allocator (offer-substrate freshness cure)
telos: TELOS-asana-substrate-freshness-2026-07-13 (ratified)
charter: CHARTER-f1a-budget-allocator-2026-07-20 (executed verbatim, nodes 0–7)
date: 2026-07-20
rung_reached: LIVE-LEG-PROVEN (allocator) + detecting (AL-5) + attributed (C1) — grant STOPS here per F-a
gate: "NODE 8 — GO-LIVE. OPERATOR-ONLY. Nothing below activates anything."
session: session-20260720-130138-e7b1cb59 / sprint-20260720-f1a-budget-allocator
---

# OPERATOR GO-LIVE GATE — F1a budget allocator (LIVE-LEG-PROVEN / INERT)

## 1. Where the procession stands (nothing rounded up)

`BUILT` → `MERGED-INERT` → `CANARY-PROVEN` → **`LIVE-LEG-PROVEN`** ✅ → **[YOU ARE HERE: OPERATOR GO-LIVE]** → `WATCHED-LIVE`
Telos ladder: `attributed` ✅ (C1) · `detecting` ✅ (AL-5, teeth-proven) · `cured` — **NOT claimed** (requires your activation + node-9 watch) · `protecting-prod` — NOT claimed (SNS gap, §5).

The allocator is **merged and INERT on origin/main** (PR #250, six rebase-merged atomic commits `4fd903ea..f6a72824`; `ASANA_BUDGET_ALLOCATOR_ENABLED` default **false**; the ENABLED=false path is test-proven byte-identical to pre-allocator behavior). No deployed process has the knob set. **Nothing changes in production until you flip it.**

## 2. What was proven (receipts, all in `.sos/wip/thermia/f1a/` unless noted)

| Claim | Receipt |
|---|---|
| WHO burns the budget: ECS service = 100% of measured 429s (3 windows, 105.8h); EBI onset FALSIFIED | `thermal-assessment.md` |
| Felt-line NO (client-felt not proven; residual CLOSED via commit `a7823851`) | `ADJUDICATION-felt-line-fork.md` |
| MALDISTRIBUTED both axes (burst-monopolization, ≤3.7% of active minutes at negative headroom) — arithmetic re-computed independently | `cache-architecture.md` + `ADJUDICATION-model-fork.md` |
| Floor = 110/60s derived (3,291-GET gap set ÷ 30-min tick); ECS yields 142/min worst-minute = 1.54% of its 3h traffic | `capacity-specification.md` |
| Advisory published-floor chosen; SPOF defeated (no producer single-writer; fail-open per-lane) | `ADJUDICATION-option-slate.md` + `architecture-assessment.md` + `killswitch-rollback-spec.md` |
| Adversary gate: PASS-WITH-CONDITIONS (6, zero blocking) — REDUCES fleet 429s, does not shift starvation; shed lands on ECS self-generated bulk, not client-felt | `ADVERSARY-REPORT-f1a-1.md` |
| AL-5 sparsity blindness CURED (2-of-12h @3600s), two-sided teeth proven; IaC==live (`31fe9bbf`) | `EXECUTION-RECEIPT-al5-reconfig.md` + `observability_alarms.tf` |
| CANARY-PROVEN: 48/48 uncached + QA's own fixtures + 2 mutants killed + G-THEATER-negative RED-before audit | `QA-canary-verdict.md` |
| LIVE-LEG-PROVEN: 95 paced live GETs, max rolling-60s = 95 ≤ 110; 5 natural 429s handled; **real AIMD suppression fired live while the floored lane completed** — the 2026-07-14 disease observed live, cure held | `QA-live-leg-verdict.md` |
| Seam handoffs (full TL-A/B/C discipline) | `.ledge/handoffs/HANDOFF-thermia-to-arch-f1a-budget-allocator-2026-07-20.md`, `.ledge/handoffs/HANDOFF-arch-to-10x-f1a-budget-allocator-2026-07-20.md` |

## 3. THE GO-LIVE LEVER (yours alone — F-a)

Activation is **per-process env config**, no code change: set `ASANA_BUDGET_ALLOCATOR_ENABLED=true` on the deployed surfaces and let the normal deploy/restart cycle pick it up. Deployment surfaces (from `topology-inventory.md`):

1. **ECS `autom8y-asana-service` task definition** (the monopolist — this is the one that matters most; its self-cap = 1390/60s during contention).
2. **The warmer Lambdas' env** (`autom8-asana-cache-warmer`, `-bulk`; `-section` is schedule-disabled) — the floored lane (110/60s claimable, AIMD-decoupled inside the floor).
3. The remaining workflow Lambdas (near-zero measured draw) — optional at first flip; they default INERT and safe either way.

**Staged-flip suggestion (not a ruling):** warmer Lambdas first (claims the floor; lowest risk), then the ECS service (activates the yield). Both directions rehearsed: flip back = instant per-process revert to today's exact behavior (byte-identity proven).

**Rollback:** unset/false the env (seconds, per-process, KILLED-state semantics = per-lane fallback: warmer→static decoupled floor, ECS→AIMD) or revert the PR commits (minutes; AL-5 TF commit `31fe9bbf` is independently revertible and should normally be KEPT — it is a separate cure).

## 4. OPEN ITEMS ON YOUR DECISION SURFACE (none block INERT; all pre-GO-LIVE or watch-window)

1. **AC-4 — TTL-regrowth wrinkle (routed to arch, genuine finding):** generic gap-parent TASK entries carry TTL=300s < the ~1795s floor-paced sweep — the floor cures admission-starvation, but early-warmed entries can expire before sweep-end (regrowth loop risk). Recommendation: let arch re-derive (options: TTL bump for gap-parents, sweep chunk-ordering, or floor re-size) **before or during** the watch window; the allocator is still net-positive without it (the live leg completed its sweep-shaped workload under real storm pressure).
2. **AC-5 — near-zero Lambda caps final sizing:** C1's zeros for `conversation-audit` are window-artifacts (its Sunday cron fell outside every window). Soft-caps currently keep config defaults; final sizing = node-9/operator item.
3. **SNS gap (`DEFER-WATCH-SNS`):** AL-5 has `Actions=[]` and NO SNS topic exists in the account — the alarm is honest but routes to no one. `protecting-prod` is unreachable until you sanction notification wiring (paging-adjacent = your carve-out).
4. **Fail-open live-proof scope:** `budget_lane_failopen` never fired live (no allocator fault occurred) — fail-open is in-silico-proven only. Honest gap, low risk (fail-open = proceed-as-today).
5. **3 escalations from `capacity-specification.md`** (client-felt trade-off class, per your 2026-07-14 mandate R-2: ties escalate) — enumerated in that artifact §escalations.

## 5. NODE 9 — WATCHED-LIVE plan (post-flip; thermal-monitor owns)

Per charter: per-GID SLO (`OfferFrameAgeSeconds{1143843662099250}` < 3600s sustained) + fleet-429 rate through **≥1 storm-equivalent window** (a 09:00–12:00Z diurnal peak is the natural candidate). Success = sawtooth amplitude collapses (no more 1,301↔25,763s oscillation) AND fleet 429 rate does not worsen. AL-5 (2-of-12h, reads-honest, teeth-proven) is the tripwire; the `budget_floor_overage` / cap-leak reconciliation metric (adversary condition-2) is the allocator's own ground truth. Watch `aimd_at_minimum` frequency as the suppression-relief signal.

## 6. Fences held throughout

F-a: nothing activated, ever (ENABLED=true existed only inside test/QA processes). F-b: zero budget-consuming probes; live leg = 103 GET-only calls bounded inside the allocator's own floor, in the diurnal trough. F-c: never fired (felt-line Branch B clean, re-proven twice). F-d: every number measured; the falsified EBI hypothesis stayed falsified.

*Procession executed 2026-07-20 under the operator user-grade grant (charter verbatim): one potnia seam, pythia adjudicating all three forks, thermia→arch→10x-dev, adversary-gated, rite-disjoint QA. The grant is discharged at this line.*
