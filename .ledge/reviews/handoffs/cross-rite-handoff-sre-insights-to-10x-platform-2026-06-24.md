---
type: handoff
status: accepted
from: sre
to: 10x-dev, platform, operator, know
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — sre insights-incident-command → 10x-dev / platform / operator / know

> **Grandeur anchor:** Command the LIVE insights-export incident — drive the BI export from succeeded:0-since-2026-06-10 to a real succeeded>0 run. Proven ONLY by a live succeeded>0 run + a live PutMetricData datapoint. Production-mutating levers stay the user's.

## INCIDENT (DECLARED SEV2, OPEN / proven-stale)
The BI insights export produces `succeeded:0` on every daily run since 2026-06-10 (confirmed live today 2026-06-24 11:01Z: total:61 / succeeded:0 / failed:60 / 720 tables; recordsScanned 10,432 — real, not silence). Runbook: `.ledge/reviews/sre-insights-incident-runbook-2026-06-24.md`; critic verdict: `.ledge/reviews/sre-insights-incident-critic-verdict-2026-06-24.md` (rite-disjoint CONCUR-WITH-FLAGS, 0 BLOCKING, root cause STRONG).

## ROOT CAUSE — REFRAMED (this is the headline; overturns the session-long assumption)
**AI-2 is a CODE-WIRING defect (FORK-I1 verdict (c)), NOT a token rotation.** Evidence (code+IaC file:line + live lambda config, critic-corroborated):
- `lambda_handlers/workflow_handler.py:158` builds `DataServiceClient()` with **no `auth_provider`**.
- `clients/data/client.py:450-474` with `auth_provider=None` → reads `AUTOM8Y_DATA_API_KEY` (`config.py:231`) and sends it verbatim as Bearer — **no mint step**.
- Live `aws lambda get-function-configuration autom8-asana-insights-export`: `AUTOM8Y_DATA_API_KEY` **ABSENT**; `SERVICE_CLIENT_ID=sa_2018…` + `SERVICE_CLIENT_SECRET` present.
- → the Lambda sends **no/empty Authorization header** → autom8y-data raises `AUTH-TEB-001` ("No Authorization header present"; the SDK envelope, `autom8y-auth/errors.py:51-52`).
- The mint path (`ServiceTokenAuthProvider`→`autom8y_core.TokenManager`) is wired ONLY into FastAPI/CLI (`api/dependencies.py:494-505`), **never the Lambda**.
- **(a) token rotation is proven-REFUTED** — there is no stale token; there is no token at all on this path.

## Routed — what restores the incident (do NOT dispatch next-rite specialists from here)

### → 10x-dev — THE FIX (durable, agent-buildable, RED-first)
- **AI-2 PRIMARY:** inject `ServiceTokenAuthProvider` into the Lambda's `DataServiceClient` at `workflow_handler.py:155-159` (mirror `api/dependencies.py:497-505`) so it mints from the already-provisioned `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET`. RED-first: a fixture proving the no-auth_provider client sends no Authorization header (→ AUTH-TEB-001 path) RED; the mint-wired client GREEN. Rung: `authored`→`merged`→`live`→`proven` (a real succeeded>0 run).

### → operator (user-sovereign FAST-PATH stop-gap, optional)
- Provision the insights-export Lambda's `AUTOM8Y_DATA_API_KEY` with a VALID data-service S2S token (Secrets Manager + extension, like the other secrets). Stop-gap only (long-lived-token anti-pattern; the durable fix is the code path above). Never print the token; sha256-prefix only.

### → platform (autom8y monorepo terraform — `terraform/services/asana/main.tf`, NOT autom8y-wt-golive)
- **AI-3a:** IAM `PutMetricData` grant is **already live** (verified on the prod role; namespaces `Autom8y/AsanaInsights`+`AsanaBridgeFleet`). No action beyond confirming the 06-17 AccessDenive predates the grant deploy.
- **AI-3b:** set `ASANA_CW_NAMESPACE=Autom8y/AsanaInsights` on the insights_export env block (`main.tf:1852-1856`, mirror cache_warmer) — drift-proofs grant↔emit so `WorkflowDuration`/`WorkflowSuccessRate` stop hitting the default `autom8/lambda` namespace. PROD-MUTATING (operator applies).
- **AI-7:** arm the merged (#148) alarm IaC — AL-1 ticket-tier now; AL-3 page only after a succeeded>0 run exists; AL-2 only after recon re-enable. Arming is user-sovereign.

### → iris/sre (separate from this incident)
- **W-IRIS:** token-safe read-only Asana section route — unblocks W-REG (still `authored` scaffold, BLOCKED-on-auth).

### → know
- corpus refresh + defer-watch.

## SLO
Insights freshness: ≥95% of daily runs `succeeded>0` + fresh `LastSuccessTimestamp` within 28h (30-day rolling); budget ~1.5 days/30d, **currently 100% exhausted (14/14 dark)** → reliability work takes priority.

## Watch-registered DEFER
FORK-2 (2026-09-29); H-4 cache_warmer decomposition; lapsed 2026-05-29 triggers; W-REG until W-IRIS lands.

## Two non-blocking critic flags
F1: AUTH-TEB-001 semantic = "No Authorization header present" (not "secret wrong") — strengthens (c): token absent, not wrong. F2: per runbook (minor, non-verdict-changing).

## Inherited receipts
`.ledge/reviews/sre-insights-incident-runbook-2026-06-24.md` · `…-critic-verdict-2026-06-24.md` · `sre-dark-subsystem-postmortem.md`; PRs #135/#148/#149/#150 landed on main (HEAD `8bc31a6a`).
