---
type: handoff
status: accepted
from: sre
to: 10x-dev, know, platform
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — sre observability-restoration → 10x-dev / know / platform

> **Grandeur anchor:** Restore the dark observability backbone so the cutover-readiness signal is trustworthy before traffic leaves the `../../../autom8` legacy monolith. Levers under the ELEVATED GRANT were exercised only for safe/reversible/asana-local work; prod-behavior + cross-repo + paging stay operator-sovereign.

## What sre LANDED (PR #148, OPEN — operator merges)
`feat(obs): StatusPushSkipped counter + alarm IaC + FORK-1 410 canary` · branch `sre/obs-statuspush-skipped-alarms` @ `615d477d` (off `origin/main` 4f05876b) · +890/−0, 8 additive files · 97–113 regression green · two critics CONCUR-WITH-FLAGS (no BLOCKING) · two-sided RED-first teeth independently re-proven.
- **W-OBS `StatusPushSkipped{skip_reason}`** — emits at 4 skip sites (`gid_push.py` feature_disabled/url_absent/invalid_key; `push_orchestrator.py` three_way_denominator_null else-branch). Rung: **emitting** (fixtures), NOT proven-in-prod.
- **Alarm IaC AL-1..AL-4** (`terraform/services/asana/observability_alarms.tf`) — `terraform validate` clean, **zero SNS actions wired**. Rung: **authored** (un-armed).
- **FORK-1 410-canary** (`QUERY_LEGACY_410_GONE` env flag, route still mounted) — reversible. Usage **proven** (0 hits / 18.9M scanned, live ECS group); removal **authored**.

## Corrected diagnosis (postmortem — `.ledge/reviews/sre-dark-subsystem-postmortem.md`)
The "dark subsystem" was **not one incident**:
1. **recon push-seam gap (06-20..23) = EXPECTED** — EventBridge rule `autom8y-account-status-recon-schedule` is **DISABLED**. Not a defect. Why-disabled is unknown → operator decision.
2. **insights-export = REAL INCIDENT, latent since ~2026-06-10** — every run `succeeded:0 failed:~60` from upstream `InsightsServiceError AUTH-TEB-001`, PLUS IAM `AccessDenied cloudwatch:PutMetricData` on `autom8-asana-insights-export-lambda-role` (present from **06-10**, per critic F1). "Dark since 06-18" is the dead-man succeeded-gate (`42b7cb0b`, 06-17) **correctly surfacing** an 8-day-old silent failure — detection working, not a new fault.
3. **data-quality skips = mixed** — `three_way` dispatch lives in **autom8y-data** (`query_grain_guard.py:84`, `batch_grain_guard.py:174,199`), not asana; empty push for low-traffic phones is EXPECTED; the DEFECT was observability-silence (now fixed by W-OBS).
4. **dd8e43ab EXONERATED** — temporal (failure predates the 06-19 deploy) + governor is observability-only.

## Realization rungs (no rounding)
W-OBS metric `emitting` · alarm IaC `authored` · FORK-1 usage `proven` / removal `authored` · insights-export incident `proven` (root-caused, unfixed) · recon gap `proven` (classified EXPECTED) · W-IRIS (SCAR-REG-001) unchanged `proven-in-code-only` / BLOCKED-on-auth.

## Operator-gated levers — SURFACED, exact commands (do NOT auto-fire)
- **AI-1** re-enable recon (or record intended pause): `aws events enable-rule --name autom8y-account-status-recon-schedule`
- **AI-3** grant insights IAM (unblocks bridge-fleet success metric): add `cloudwatch:PutMetricData` to `autom8-asana-insights-export-lambda-role` (IaC).
- **AI-5** deploy `environment` dim on BridgeFleetHealth (`workflow_handler.py:256-262,330-339`) → creates the missing prod fleet dimension.
- **AI-7** apply + arm alarms: `terraform apply` then set `paging_armed_alarms`/`ticket_sns_topic_arn` (paging = confirm-first).
- **AI-8** FORK-1 cutover: set `QUERY_LEGACY_410_GONE=true` (canary) → later unmount `api/main.py:~470`.
- **Merge PR #148** — operator-sovereign.

## Routed to next rites (do NOT dispatch their specialists from here)
- **→ 10x-dev/framing:** **W-IDEM** SCAR-IDEM-001 finalize double-exec (`idempotency.py:719`, RED-first) + **W-REG** SCAR-REG-001 dual-anchor GID join (gated on the W-IRIS live receipt, still BLOCKED-on-auth) + **AI-2** insights-export `AUTH-TEB-001` upstream auth fix (likely cross-repo).
- **→ know/framing:** corpus refresh (`/know --all`, 90-commit drift) + defer-watch dispositions.
- **CROSS-REPO (autom8y-data):** **AI-6** classify/repair the three-way null denominator + empty-vertical at `query_grain_guard.py`/`batch_grain_guard.py`.

## Watch-registered DEFER (not this cycle)
FORK-2 interop shared-substrate PR (2026-09-29); H-4 cache_warmer decomposition; lapsed 2026-05-29 defer-watch triggers.

## Inherited receipts
`.ledge/reviews/sre-observability-design.md` · `sre-dark-subsystem-postmortem.md` · `sre-critic-verdict.md` (18🟢/0🔴) · `sre-build-critic-verdict.md` (5🟢/0🔴) · PR #148.
