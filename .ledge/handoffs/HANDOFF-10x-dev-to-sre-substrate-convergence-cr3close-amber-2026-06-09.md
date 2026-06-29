---
type: handoff
status: active
handoff_type: execution  # @cross-rite-handoff: Planning→Execution (sre executes the arc; acceptance_criteria per item)
from_rite: 10x-dev
to_rite: sre
initiative: substrate-integration-convergence
phase: Arc-3 CR-3 close + AMBER observability hardening (S9)
created: 2026-06-09
evidence_grade: MODERATE  # self-ref ceiling; STRONG requires eunomia rite-disjoint critic of the AMBER hardening + CR-3 close
head_asana: 02c032eae39d12cfa91a2abb8769f30691b69ab6  # origin/main autom8y-asana (benign #116 test-only since 50ebfe33)
head_autom8y: re-verify live (alarms TF live here; two prod-env gates)
soak_clock: ~2026-06-11T12:25Z (in-progress; ~6/7d at handoff)
authority: OPERATOR META-GRANT — sre pantheon has user-grade execution authority through the next cross-rite seam (see §Authority)
reconcile_against:
  - .sos/wip/frames/substrate-integration-convergence.shape.md   # S9 (sre arc) + PT-08
  - .sos/wip/frames/substrate-integration-convergence.md          # frame: telos, §8 DEFER (AMBER), Consumer-0
  - .sos/wip/frames/autom8y-receiver-consumer-cutover.shape.md     # CR-3 GO-1..GO-11, PT-08/09/10, RB-1 boundary
  - .ledge/handoffs/HANDOFF-10x-dev-to-monorepo-cpumem-floor-and-vg005-alarm-2026-06-08.md
  - .ledge/decisions/CR3-IC-GATE-7-LAND-PASS-2026-06-04.md
  - .ledge/decisions/CR3-RELEASE-GATE2-DEPLOY-READINESS-2026-06-05.md
---

# HANDOFF — 10x-dev → sre — Substrate-Integration-Convergence: CR-3 Close + AMBER Observability (S9)

## Grandeur Anchor
We make the contracted data plane **observable** and land CR-3 **durably**: the receiver's correct-economics serving path is guarded by *affirmative* SLI/SLO signal (not OK-on-absence silence), the active-offer telos + population-receipt-floor + resolver-drift alarms fire on *real* degradation, the 7-day soak closes clean to **protecting-prod**, and CR-3's irreversible Stage-B → Secret-2 retire the auth fallback — proven ONLY by live AMP query results, an armed alarm transitioning to ALARM under a deliberately-injected fault, and a clean soak window. Never by a green dashboard or an optimistic apply.

## Inherited LIVE state (re-verify; default-to-REFUTED)
- **Receiver deploy ADVANCED `:494→:497`** = image `02c032e` (current HEAD), running=1, **floor `cpu=2048/mem=8192` preserved** (ECS `autom8y-asana-service:497`, us-east-1, account 696318035277).
- **Soak in-flight**, completes ~`2026-06-11T12:25Z`. Stage-B MUST NOT fire before clean-soak-complete (PT-08).
- **AMBER state (the work):** g2-cutover guards are OK-on-absence (`treat_missing=notBreaching` — silence ≠ healthy); receiver SLI/EMF **dark** (`RECEIVER_SLI_EMF_ENABLED` off); resolver-drift alarm + SNS paging **not armed**; population-receipt-floor alarm **not wired**; active-offer telos metric **not emitting**; receiver SLI/SLO burn-rate **absent**.
- **Alarms are Terraform in the `autom8y` repo** (two prod-env gates) — TF work needs a worktree off `autom8y` origin/main, not autom8y-asana.
- **g2 alarm `count=0` is a worktree STOPGAP** (not converged to main) — durable fix outstanding (task #34).
- **Monorepo floor + VG-005** (`HANDOFF-...-cpumem-floor-and-vg005-alarm-2026-06-08`): codify `cpu=2048/mem=8192` + VG-005 CPU_STARVATION_REPLACEMENT alarm; the TF plan MUST show `1024→2048` (UP, not down).
- **Consumer-0 fossil (10x-dev finding, 2026-06-09):** the offline `metrics` CLI reads the legacy entity-agnostic fossil ($8,775 / fluctuating) not the SEAM-1 `offer/` frame. → the **active-offer telos metric (SRE-N6) is exactly the guard that would alarm on this**; wire it against the entity-keyed served value (62/$79,485), G-DENOM-correct.

## sre arc — work items (acceptance criteria are LIVE receipts)
| Node | Owner | Mission | Acceptance (G-PROVE) | Gate |
|---|---|---|---|---|
| **N9.a** soak tail | incident-commander | monitor per-arm ≥99%, capacity_502=0, ell-lag bounded, warm-lane paused | AMP query receipts over the soak window | PV-4 |
| **N9.b Stage-B** | incident-commander | CR-3 Stage-B (IRREVERSIBLE, RB-1 boundary) | clean-soak-complete + Platform §9.3 headroom + IC sign-off, all receipted | **HARD/IRREVERSIBLE** |
| **N9.c Secret-2 decommission** | incident-commander | retire auth fallback (IRREVERSIBLE, **LAST**) | PDG-2/3 + task-#73 + monolith-not-orphaned (credential-topology verified) + access-stopped | **HARD/IRREVERSIBLE** |
| **AMBER-1** | observability-engineer | OK-on-absence guards → affirmative-signal; resolver-drift alarm + SNS; population-receipt-floor alarm; active-offer telos metric (G-DENOM) | armed alarm → ALARM under injected fault (not "created=working") | DEFER→active |
| **AMBER-2** | observability-engineer | flip `RECEIVER_SLI_EMF_ENABLED`; receiver SLI/SLO burn-rate | EMF emitting live + burn-rate rule promtool-valid | DEFER→active |
| **FLOOR/VG-005** | platform-engineer | codify floor + VG-005 alarm (autom8y TF) | TF plan shows 1024→2048 (UP); alarm armed | — |
| **g2-durable** | platform-engineer | durable g2 alarm fix; converge main (drop count=0 stopgap) | main-converged TF apply = intended diff | — |
| **RESILIENCE** | chaos-engineer | controlled blast: prove guards + serve-stale + floor HOLD | experiment report; abort criteria honored; alarms fired | post-deploy |

## Authority (operator Meta-Grant, this session)
User-grade execution authority is GRANTED to the sre pantheon through the next cross-rite seam — **execute, don't merely surface**: terraform apply (autom8y alarms + floor + VG-005), arm alarms + SNS, flip `RECEIVER_SLI_EMF_ENABLED`, AMP rules (promtool-valid), scoped merges to main (both repos), receiver redeploy/re-warm, chaos within blast-radius + abort criteria. Full filesystem reach (all repos above/below/across). Bias: clean/modern/robust integration, confident landing, ecosystem coherence.
**Irreversibles fire ONLY on their empirical gate GREEN with a pasted receipt** (Stage-B, Secret-2 above) — not speculatively; the soak gate is NOT met this window, so they stay ARMED-AND-STAGED. **Strict impossibilities** (escalate via `! command`): interactive human-MFA logins (gcloud/AWS-SSO browser), anything needing a human at a console.

## DEFER watch-register (not scope-crept)
DEFER-AMBER-1/2 (now activated by this handoff), DEFER-G-DENOM-BACKSTOP (#44, 5th _evaluate_gate criterion on 4xx/401 spike), DEFER-OFFLINE-READER-FOSSIL (Consumer-0, 10x-dev-owned — sre adds the telos-metric guard), 33-legacy-sections delete (#53d, HELD).

## Exit → next seam
protecting-prod (soak clean + Stage-B landed + Secret-2 decommissioned) AND/OR AMBER hardening landed-live. At the seam: STOP → write cross-rite HANDOFF (eunomia for STRONG cert of AMBER+CR-3, or operator for the 06-11 soak-gated irreversibles) → name rungs → watch-register DEFER → route next /frame.
