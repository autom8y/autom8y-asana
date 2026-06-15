---
type: handoff
status: proposed
handoff_type: assessment
from: sre
to: 10x-dev + incident-commander (cross-repo: autom8 monolith)
date: 2026-06-10
initiative: substrate-integration-convergence
station: S9 (CR-3 close) — AC-6 cutover-live investigation
evidence_grade: MODERATE  # sre-authored; STRONG needs the 5-signal bilateral cutover verification + eunomia rite-disjoint
heads:
  asana: 02c032ea  # pre-AMBER-2-merge; main now e109fe86 (AMBER-2 #117 squash-merged)
  autom8y: 75eb9b98
  monolith_deploy: monolith-prod:385 (image pushed 2026-06-09T12:27Z; deployed 12:40Z)
---

# HANDOFF — sre → 10x-dev/IC : AC-6 cutover NOT live-flowing (the soak-START blocker)

## TL;DR
The sre window landed the keystone soak-precondition (**AMBER-2 affirmative SLI heartbeat — merged + deploying**). But the **soak cannot START**: the monolith→receiver CR-3 cutover is **not live-flowing**, so there is nothing to soak. This is a more fundamental blocker than any observability gap and is largely cross-repo (autom8 monolith) — handed to 10x-dev/IC for the AC-6/PDG-3 functional verification (task #36 / R2).

## What the sre window LANDED (banked vs gated — never rounded up)

| Item | Rung | Receipt |
|------|------|---------|
| **AMBER-2 SLI heartbeat** (`sli_heartbeat.py` + lifespan wiring) | **merged → deploying** | PR #117 squash-merged → main `e109fe86`; 9/9 anti-theater unit tests PASS (real registry-sample materialization; G-DENOM probe-class only; dead-man NOT neutered); CI fully green. Deploy in flight (`Push on main` running). **SLI-lit verification PENDING the deploy** (~15 min): `count(autom8y_http_request_duration_seconds_count{service=asana})≥1` + `EcsServiceDenominatorAbsent` clears. |
| `/health`→`/ready` repoint | **REFUTED (unsafe)** | `/ready` (health.py:143) is a 503-deep readiness probe → would cycle the single task. The heartbeat is the robust replacement. |
| **FLOOR/VG-005 TF codify** | **plan-proven, apply prod-env-gated** | autom8y `terraform/services/asana/main.tf:158-159` 1024→2048 UP; `aws_ecs_service` no-op (ignore_changes=[task_definition]) → template-convergence, no redeploy; live `:497` already 2048/8192. CORRECTED apply needs `-var image_tag=02c032e` (else 6 Lambdas clobber `→:latest`). Apply path = PR→merge→workflow_dispatch env=production (**prod-env reviewer approval = operator lever**). |
| **AMBER-1 affirmative guards** (resolver-drift+SNS, population-receipt-floor, active-offer-telos) | **designed, not applied** | 7 promtool-valid SLI/burn rules designed (prior window). active-offer-telos metric may need a receiver-emit (gated). Apply = autom8y TF (prod-env-gated). |
| #35 source-of-truth | **reconciled** | TF owns the task-def TEMPLATE (floor/env/health); CI `service-deploy.yml` is image-only + copies LIVE. Codifying the floor in TF prevents a TF-apply clobber but does not change live. |
| AMP delta #469 | **noted (G-PROPAGATE precedent)** | autom8y just cured an analogous series-presence false-RED with `or vector(0)` arms — the established idiom; do NOT apply it to the dead-man (it neuters the backstop). |
| auth ALARMs (`auth-no-healthy-targets`/`alb-unhealthy-hosts`) | **benign (banked)** | retired-blue B/G (green=Weight-100, drained-blue=Weight-0; /health+/jwks=200). NOT a soak-HALT. |

## THE ASSESSMENT ASK (AC-6/PDG-3 — task #36/R2) — for 10x-dev/IC + cross-repo

**Finding (sre, live receipts, default-to-REFUTED):** the CR-3 cutover is NOT live-flowing — confirmed a full day after the `:385` monolith deploy.
- `receiver_query_outcome_total` = **NONE** (no series in AMP) — the economics-serving counter the cutover would increment.
- `EcsServiceDenominatorAbsent{service=asana}` still **firing** — receiver has zero inbound traffic.
- CR-3 charter §5 defines soak entry as "#55 repoint **LIVE-VERIFIED**." #55 merged 2026-06-04 but the monolith ran the pre-cutover `:382` (May-31) image until `:385` deployed 2026-06-09T12:40Z — and even now the receiver shows no monolith traffic.

**Acceptance criteria (what proves the cutover live + re-anchors the soak):**
1. Does `monolith-prod:385`'s image actually contain the post-`#55`/`#60` SM-first cutover code? (mutable `:prod` tag — unverified read-only; needs the image-lineage check.)
2. Is `satellite_get_df_enabled = True` live in the monolith config, AND does the monolith actually route its dataframe-resolver reads to the receiver (satellite path), not the legacy SDK?
3. The 5-signal bilateral verification: monolith → Secret-1 SM-fetch → receiver HTTP 200 → `receiver_query_outcome_total{success}`++ → `up{service=asana}=1` → no fallback-cause spike.
4. On PASS: the soak clock RE-ANCHORS to that live-verified moment (+7 clean days). On FAIL: the cutover is not live; the convergence-deploy + a deliberate cutover are needed before any soak.

**Why cross-rite:** the "why-not" is monolith-side (autom8 repo: the satellite flag, the deployed image lineage, the routing) + IC sequencing — beyond the sre window's gift. sre owns the receiver-side observability (AMBER, now landing) but not the monolith cutover.

## DEFER watch (registered, not scope-crept)
- DEFER-AMBER-1-APPLY (resolver-drift/population-floor/active-offer-telos — designed; prod-env-gated apply)
- DEFER-FLOOR-VG005-APPLY (plan-proven; `-var image_tag=02c032e`; prod-env-gated)
- DEFER-G2-DURABLE (#34, main converge)
- DEFER-CHAOS-FAULT-TO-ALARM (prove each new alarm; gated on the alarms existing + heartbeat deployed)
- DEFER-T73-SPOF (Dockerfile:294 — gates Secret-2 decommission)
- DEFER-OFFLINE-READER-FOSSIL (Consumer-0, 10x-dev-owned)

## Rungs — banked vs gated
- BANKED: AMBER-2 merged (deploying); the platform HALT learnings; auth-ALARMs benign; #35 reconciled; the live-cutover-RED finding.
- GATED: AMBER-2 live (deploy + SLI-lit verify, ~15 min); FLOOR/AMBER-1 apply (prod-env); the telos-soak (AC-6 live-verification + 7 clean days); Stage-B → Secret-2 (ARMED-AND-STAGED; soak-gated, IRREVERSIBLE); eunomia STRONG (HELD).

## Next /frame routing
→ **10x-dev/IC framing** for AC-6: functionally verify (or establish) the monolith→Secret-1→receiver cutover live (task #36/R2). On cutover-live + the convergence-deploy assembled, return to sre to start the telos-soak. eunomia rite-disjoint STRONG attests the full convergence at the exit.

*Authored by the sre main thread (acting orchestrator) at the rite-switch seam, 2026-06-10. Production-mutating + prod-env levers remain the operator's except as the Meta-Grant delegated this window. The soak never validly started — AC-6 is its gate. Soak the telos.*
