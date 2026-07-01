---
type: handoff
status: accepted
from: releaser
to: operator, platform, 10x-dev, iris, know
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — releaser land-#151 → operator / platform / 10x-dev / iris / know

> **Grandeur anchor:** End the live BI insights-export outage by landing the proven auth-wiring fix #151; proven incident-close ONLY by a live succeeded>0 run + a live PutMetricData datapoint — never by a merge alone.

## DONE — PR #151 MERGED (under the operator grant; authorized, reversible)
**W-AUTH (insights auth-wiring): `merged`.** Squash **`a30d55a5`** on `main` (17:22:23Z), via auto-merge-on-green (CI-gated, not a red-bypass). The fix is on main: `ServiceTokenAuthProvider` injected at `workflow_handler.py` + `resolve_secret_from_env` in `service_token.py` (handles the `SERVICE_CLIENT_SECRET_ARN` `_ARN`-rename asymmetry). Proven before merge: QA GO + rite-disjoint critic CONCUR; 23 CI checks green.
- Rollback if needed: `gh pr revert` / revert `a30d55a5`.

## NOT DONE — the incident is STILL OPEN (`merged ≠ live`, honest rung)
The asana repo has **no deploy-on-main CD** (verified — no deploy workflow). So `a30d55a5` is on main but the **prod insights-export Lambda still runs the old code**. Today's run remains `succeeded:0 / 720 tables` (scanned 1177, non-silent). The incident closes ONLY on:
1. **deploy** the insights-export Lambda from `a30d55a5`, AND
2. a live **`succeeded>0`** `insights_export_completed` run + a live **PutMetricData** datapoint.

## Surfaced — operator/platform (prod-irreversible; the grant authorizes, but these are the high-blast cross-repo CD steps; FORK-3: if the live run still fails, capture the AUTH-TEB-001/secret receipt and ESCALATE — do not loop)
- **Deploy** the insights-export Lambda at `a30d55a5` via the monorepo CD / your deploy path (the mechanism is NOT in autom8y-asana). This is the action that turns the BI export back on.
- **R4 IAM (`PutMetricData`):** still implicitDeny on `autom8-asana-insights-export-lambda-role`. Fix in the autom8y monorepo terraform (set `ASANA_CW_NAMESPACE=Autom8y/AsanaInsights` on the insights_export env, mirroring cache_warmer, OR widen the namespace condition). Without it the success-metric attester (and the AL alarm) stay dark — fix before relying on WorkflowSuccessRate as a deploy gate.
- **Verify-and-close:** `aws logs ... filter insights_export_completed` shows `succeeded>0` + `AUTH-TEB-001`→0; a live PutMetricData datapoint lands.

## Routed (next /frame; do NOT dispatch their specialists from here)
- **10x-dev/framing** — the `workflows.py:361` bare-`DataServiceClient` sibling (same class as #151, live `POST /v1/workflows/{id}/invoke`): same `ServiceTokenAuthProvider` injection, RED-first; plus the stale `test_fleet_query_adapter.py:370` assertion (re-assert the retired endpoint is GONE) + D-2 coverage. (Builds, not releaser actions.)
- **iris/framing** — the W-IRIS token-safe read route → unblocks SCAR-REG-001 / W-REG (the *other* live correctness gate; `EXCLUDED_SECTION_GIDS` is the live default at `reconciliation/processor.py:165`).
- **know/framing** — corpus refresh (90+ commits stale) + defer-watch reconcile.

## Honest scope note (G-DENOM)
This was NOT a multi-repo fleet release — ONE proven merge (#151), reversible, no cross-repo cascade (core-4.6.0 already live, range-pinned). No cartographer/resolver fleet spun. The 7 backlog PRs (#97/#114/#130/#132/#133/#134/#142) excluded.

## Watch-registered DEFER
FORK-2 interop substrate (2026-09-29); H-4 cache_warmer decomposition; W-REG until W-IRIS lands; SCAR-REG-001 dual-anchor until the iris route.

## Production-mutating levers still confirm-first (NOT fired)
token/secret rotation (`AUTOM8Y_DATA_API_KEY`, `SERVICE_CLIENT_SECRET`, Asana PAT); rollback of an unrelated service; deploy-freeze; paging; the live Asana section-GID WRITE (W-REG, BLOCKED-on-iris).

## Inherited receipts
PR #151 merged `a30d55a5`; `.ledge/reviews/asana-closing-{case-file,critic-verdict}-2026-06-24.md`; `cross-rite-handoff-10x-wauth-to-operator-2026-06-24.md`; HEAD pre-merge `8bc31a6a`.
