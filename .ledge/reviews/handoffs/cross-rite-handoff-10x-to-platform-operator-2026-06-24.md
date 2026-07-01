---
type: handoff
status: accepted
from: 10x-dev
to: platform, operator, iris, sre, know
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — 10x-dev blocker-remediation + insights-incident → platform / operator / iris / sre / know

> **Grandeur anchor:** Close autom8y-asana's correctness blockers + remediate the LIVE insights-export incident; proven only by a broken-fixture-firing-RED + live receipt, never a green dashboard. Production-mutating levers stay the user's.

## LANDED / PROVEN this cycle
- **W-IDEM — SCAR-IDEM-001 finalize double-exec: PROVEN, ready to merge.** PR **#149** (`10x/idem-finalize-contract`, `43a6c3cd`), state OPEN / **MERGEABLE / CLEAN**, +939/−191, 4 files (scoped). The fix re-sources the strict-once discriminator from the verified JWT `request.state.claims` (canonical `service_account_id`→`client_id`→`sub`, per the `rate_limit.py:25-46` scar) at middleware-dispatch time; on finalize failure a strict-once S2S caller now receives `500 IDEMPOTENCY_KEY_NOT_PERSISTED` + `X-Idempotent-Not-Persisted` + `IdempotencyFinalizeFailure` metric carrying the **real** service identity. **Prod-wired RED→GREEN proven** (old code 201/`unknown` → fixed 500/`autom8y-data`); regression 1329/0 full `tests/unit/api/`. QA GO + rite-disjoint critic CONCUR (DELTA, no ESCALATE).
  - **History (why this matters):** the FIRST attempt was production-INERT (gated on `request.state.auth_context`, which prod never sets) and passed its own tests via a fixture that presets state prod doesn't use. QA + critic caught it (D-IDEM-CRIT-1, BLOCKING); the REMEDIATE round closed it. **Do not regress to `auth_context`.**
  - **Rung: `proven` → `merged` on operator merge.** Caller-contract change: a previously-2xx S2S path can now return 500 — **notify autom8y-data** (its retry logic must reconcile, not blind-retry) BEFORE/at merge.
- **W-REG — dual-anchor GID join: `authored` scaffold** (in PR #149, `section_registry.py` `join_section_registry` + synthetic-fixture tests, 10/10). Wired to ZERO live callers; **BLOCKED-on-W-IRIS** (no live-Asana GIDs). Not proven — do not wire live until the iris receipt exists.

## Routed — what genuinely remains (do NOT dispatch next-rite specialists from here)

### → operator (LIVE production incident — highest business impact)
- **AI-2 insights `AUTH-TEB-001`:** the BI export has produced `succeeded:0` since 2026-06-10; today's run = 720 tables failed. `AUTH-TEB` is asana's **own inbound** JWT-reject envelope (`error_responses.py:17`) → autom8y-data is rejecting asana's **outbound** S2S JWT. Disambiguate: `aws logs filter-log-events --log-group-name /aws/lambda/autom8-asana-insights-export --filter-pattern "AUTH-TEB"`. Fix is ONE of: **(a) `AUTOM8Y_DATA_API_KEY` token rotation (user-sovereign)**, (b) cross-repo autom8y-data `SERVICE_CLIENT_ID` registration, (c) asana secret-name wiring (separate frame). Rung: `diagnosed` → `proven` on a `succeeded>0` run.

### → platform (cross-repo `autom8y-wt-golive` + IAM)
- **AI-3 PutMetricData:** the grant is NOT absent — policy `insights_export_cloudwatch_metrics` (`autom8y-wt-golive/terraform/services/asana/main.tf:1896-1919`) allows only namespaces `Autom8y/AsanaInsights`+`Autom8y/AsanaBridgeFleet`, but `workflow_handler.py:281-292` emits to the default `autom8/lambda` (no `ASANA_CW_NAMESPACE` set in the `insights_export` env block, unlike cache_warmer). **Fix: add `ASANA_CW_NAMESPACE = "Autom8y/AsanaInsights"`** to the insights_export env block. Rung: `authored`/located → `live` on apply.
- **AI-5 / AI-7:** add the `environment` dim to `BridgeFleetHealth` emit (creates the prod fleet dim); apply + arm the alarm IaC merged in #148 (paging = confirm-first).

### → iris / sre
- **W-IRIS:** build the token-safe read-only Asana section-list route — the structural blocker that gates W-REG reaching `proven`.

### → know
- corpus refresh (`/know --all`, drift) + defer-watch dispositions.

## Merge / apply — operator-sovereign (surfaced, NOT executed)
`gh pr merge 149 --squash` · `terraform apply` (AI-3/AI-5/alarms) · `AUTOM8Y_DATA_API_KEY` rotation (AI-2) · Lambda deploy · the live Asana section-GID WRITE (W-REG). I fired none of these.

## Watch-registered DEFER
FORK-2 interop shared-substrate PR (2026-09-29); H-4 cache_warmer decomposition; lapsed 2026-05-29 triggers.

## Inherited receipts
PR #149 (`43a6c3cd`); `.ledge/reviews/10x-idem-critic-verdict-2026-06-24.md` (round-1 BLOCKING) + the DELTA verdict (round-2 CONCUR); `sre-dark-subsystem-postmortem.md`; `asana-coherence-case-file.md`.
