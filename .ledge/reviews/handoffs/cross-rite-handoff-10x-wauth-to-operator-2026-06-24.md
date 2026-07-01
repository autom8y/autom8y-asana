---
type: handoff
status: accepted
from: 10x-dev
to: operator, 10x-dev, know
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — 10x-dev W-AUTH (insights auth-wiring) → operator / 10x-dev / know

> **Grandeur anchor:** Turn the BI insights-export back on — succeeded:0 since 2026-06-10. Proven by a prod-path RED-first fixture + ultimately a live succeeded>0 run (operator deploy). Production-mutating levers (merge, Lambda deploy) stay the user's.

## PROVEN this cycle — PR #151 (ready for operator merge+deploy)
**W-AUTH — the insights-export auth-chain fix: `proven`** (prod-path fixture; QA GO; rite-disjoint critic CONCUR, 0 RED, 0 BLOCKING; prod-inertness disproved). `fix/w-auth-secret-resolution` @ `ec975e7c`, OPEN/MERGEABLE, 5 files. **Pure asana code fix — no IaC, no secret provisioning.**

### Root cause (precise, evidence-STRONG — refines the sre handoff)
A **secret-NAME asymmetry**, not a missing/expired token:
- `ServiceTokenAuthProvider` reads bare `os.environ["SERVICE_CLIENT_SECRET"]` (`service_token.py:38`), no ARN resolution.
- The `scheduled-lambda` Terraform module renames every `secret_arns` key with an `_ARN` suffix (`modules/scheduled-lambda/main.tf:120` `{ for k,v: "${k}_ARN" => v }`), so on the Lambda the var is **`SERVICE_CLIENT_SECRET_ARN`** — the bare name is unset (this is why the plain-env probe showed null). ECS delivers it bare → the provider works on ECS, fails on Lambda.
- `cache_warmer` works only because it resolves via `resolve_secret_from_env` (keys on `_ARN` first, `lambda_extension.py:151`).

### The fix (PR #151)
1. `ServiceTokenAuthProvider` now resolves the secret via `resolve_secret_from_env("SERVICE_CLIENT_SECRET")` (resolves `_ARN` on Lambda, bare on ECS) — convention-agnostic.
2. `workflow_handler.py:175` injects `DataServiceClient(auth_provider=ServiceTokenAuthProvider())`, mirroring `dependencies.py:499-501` but NOT its `:502-503` silent-swallow — honest-failure (raise→500; `RuntimeError` propagates; only absent-secret `ValueError` narrowed).
3. Prod-path RED→GREEN: a fixture driving the real `handler` and capturing the `auth_provider` kwarg on the real `DataServiceClient` — RED on HEAD (no provider), GREEN after. 59 + 532 + 22 touched-module/auth/data-client tests pass. IaC verified NO-change-needed (insights_export already delivers via `secret_arns`).

## Routed (do NOT dispatch next-rite specialists from here)

### → operator — THE action that closes the incident
- **Merge PR #151 + deploy the insights-export Lambda.** That is the only step between `proven` and a live `succeeded>0` run. No secret provisioning needed (the secret already exists on the Lambda under `SERVICE_CLIENT_SECRET_ARN`). Verify closure: a real `succeeded>0` `insights_export_completed` + AUTH-TEB-001 → 0.
  - `gh pr merge 151 --squash` (user-sovereign) → deploy → observe one daily run.

### → 10x-dev — the sibling (separate, pre-existing)
- **`api/routes/workflows.py:361`** constructs `DataServiceClient()` **bare** on the live `POST /api/v1/workflows/{id}/invoke` S2S route (mounted `api/main.py:462`) — same dark-export class, predates W-AUTH (#27, 2026-04-27), NOT in PR #151's diff. Apply the same provider injection (mirror `workflow_handler.py:175`) as a separate RED-first PR. Any `requires_data_client=True` workflow invoked via this route hits the identical bug.

### → platform (DEFER / lower priority now)
- **AI-3b** `ASANA_CW_NAMESPACE` metric drift-proofing (monorepo terraform) — the metric-emission half; the AI-3a IAM grant is already live. Not incident-blocking.

### → iris/sre · know
- **W-IRIS** read route (unblocks W-REG, still `authored`); **know** corpus refresh + defer-watch.

## Rung status (no rounding)
W-AUTH: **`proven`** (prod-path fixture) → `merged` on operator merge → `live`/incident-closed ONLY on a real `succeeded>0` run. The `succeeded>0` attestation is `[UNATTESTED — operator-deploy-gated]`.

## Watch-registered DEFER
FORK-2 (2026-09-29); H-4 cache_warmer decomposition; W-REG until W-IRIS; AI-3b namespace.

## Inherited receipts
PR #151 (`ec975e7c`); `.ledge/reviews/10x-insights-auth-critic-verdict-2026-06-24.md`; `sre-insights-incident-runbook-2026-06-24.md`; HEAD `8bc31a6a` (#135/#148/#149/#150 landed).
