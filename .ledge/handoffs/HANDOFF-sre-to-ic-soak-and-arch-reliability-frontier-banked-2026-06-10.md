---
type: handoff
handoff_type: validation
status: proposed
source_rite: sre
target_rite: ic-soak (primary) · arch (PV-PREFIX config split) · operator (decision list)
title: Reliability frontier BANKED — SLI lit (verified), deploy chain hardened (4 PRs), soak-readiness bundle merged-not-applied, blast designed, soak checklist authored
date: 2026-06-10
---

# HANDOFF — sre → ic-soak / arch / operator — the frontier banked

## R6 EXIT MATRIX (GREEN/RED, live receipts)

| Station | Result | Receipt |
|---|---|---|
| R1 AMBER-2 | **GREEN — COLLAPSED TO RECEIPT: the SLI is LIT** | AMP `count(autom8y_http_request_duration_seconds_count{service="asana"})=3`: heartbeat `/__sli_heartbeat__` route_class=probe (226 obs) + business `POST /v1/resolve/{entity_type}` 200; present since ≥06-09 14:00Z — the "dark" claim was STALE. Grafana alert-state = access-gated (P7 work). |
| R2 deploy chain | **GREEN — 4 PRs MERGED** | autom8y#485 `0a5ef15c` (gate timeout 60×2 + job split → lock releases on deploy success; /ready-scrape was ALREADY on main via #464) · autom8y-workflows#25 `93dbbc2` (Node24 ×8 workflows + CodeArtifact retry ×5 sites) · autom8y#487 `49972967` (Node24 ×6 deploy-chain workflows; aws-creds dual-SHA → canonical `e7f100cf` v6.2.0) · asana#122 `8f9051b1` (reusable re-pin + 2 CodeArtifact sites; **green CI against the new reusable = proof-in-anger**). Residual: satellite-receiver changes prove on the NEXT deploy; ~60 non-deploy autom8y workflows still Node20 (separate sweep before 06-16). |
| R3 soak bundle | **GREEN — MERGED-NOT-APPLIED** | autom8y#486 `bc2faa7c`: burn-rate SLO rules (promtool SUCCESS 8+3 rules, 4 behavioral cases incl. no-data-honesty) + probe dead-man + floor-breach + active-offer-collapse(<40) + resolver-loop alarms (ALL `actions_enabled=false`); TF validate+plan pasted (asana: 6 to add; observability: 1 to add, paging namespace count-gated); GATE-A live-AMP receipt STRONG. |
| R4 blast design | **GREEN — DESIGNED (execution = operator)** | `.ledge/specs/CHAOS-DESIGN-receiver-post-cure-blast-2026-06-10.md`: 6 experiments (run-first: EXP-1 IAM-revocation honest-null drill + EXP-2 heartbeat-kill dead-man validator); EXP-1/4 alarm-signals DOWNGRADED to log-only until #486 is APPLIED (G0 gate — honest). |
| R5 soak checklist | **GREEN — AUTHORED, CLOCK NOT STARTED** | `.ledge/decisions/IC-SOAK-READINESS-telos-soak-2026-06-10.md`: P1 AC-6 **RED (THE gate)**; P2 apply PENDING; P3a must-arm PENDING; P5 deploy-in-anger PENDING; P6 stability GREEN; P8 UK-2 refuted-as-blocker. 7d duration argued. Reset-vs-log criteria falsifiable. |
| AC-6 | **RED (unchanged)** | `receiver_query_outcome_total` ABSENT in AMP — the cutover not flowing; #36/R2 cross-repo owns it. |

## Rungs (never round up)
SLI = **lit-live** (verified, not just deployed) · R2 = **merged** (deploy-in-anger pending next deploy) · R3 = **merged-NOT-applied** (apply+arm = operator) · R4 = **designed** · R5 = **surfaced** · soak = **NOT started** · telos = **NOT verified-realized** (five-signal: SEAM-2 C2/C3 deferred, AC-6 RED).

## OPERATOR DECISION LIST (today)
1. **AC-6 (#36/R2)** — confirm the monolith cutover owner/plan; without it the soak has no subject.
2. **Apply #486** (TF, prod-env gates) + **arm the must-arm pair** (probe dead-man + burn-rate: `terraform apply -var=asana_receiver_slo_alerts_armed=true`); the 3 CW alarms may stay dark.
3. **Proving deploy** — trigger (or await) one post-#485 deploy; verify the lock releases in minutes + the split gate behaves.
4. **Chaos EXP-1+EXP-2** — authorize the game-day (after #486 applied).
5. **Ratify 7d soak** + co-sign START when P1–P5+P7 green.
6. Standing: CHANGE-001 ack · UK-2 ruling (#114) · CR-3 Stage-B HELD · ASANA-PAT probe (cure magnitude + Stream-B fork).

## → arch (separate frame)
**PV-PREFIX config split**: `ASANA_CACHE_S3_PREFIX` drives BOTH task-cache `S3Settings.prefix` AND dataframe storage (prod=`asana-cache/project-frames/`); the cure is pinned-constant-decoupled but the next consumer trips it. Design the env split + consumer audit (Option-2 S3-read-tier decision rides along).

## DEFER watch-register
CHANGE-002..005 · stub-census Top-10 · throughline `integration-boundary-fidelity` (N=1→2) · #97 warmer fast-lane · non-deploy Node20 sweep (deadline 06-16) · hadolint pre-existing reds (asana Dockerfiles) · bulk/section lanes' first empirical cold-read heal · D-1 docstring nit.

Next `/frame` → **`ic-soak/framing`** (or `arch/framing` for the prefix split — operator's pick).
