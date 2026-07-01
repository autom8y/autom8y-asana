---
type: review
artifact_role: rite-disjoint-external-critic-verdict
slug: sre-insights-incident-critic-verdict
status: accepted
critic_rite: external (rite-disjoint from sre; adversarial, default-skeptical)
target_artifact: .ledge/reviews/sre-insights-incident-runbook-2026-06-24.md
date: 2026-06-24
aws_account: 696318035277
aws_region: us-east-1
head_asana: f4f924d2684386093ef656ecde5e98613cdffce8
head_autom8y: 4f7ccc94b922f56edefb889cd8f48afd01511b64
verdict: CONCUR-WITH-FLAGS
method: >
  Re-ran the cheap probes myself. Verified every load-bearing code/IaC file:line receipt by
  direct inspection at HEAD. Independently re-pulled CloudWatch Logs Insights (account
  696318035277, us-east-1) for succeeded-count, AUTH-TEB-001, and mint-activity. Pulled live
  prod IAM role policy and live Lambda env config (discharged the runbook's one UV-P).
---

# External Critic Verdict — insights-export DARK incident command

**OVERALL: CONCUR-WITH-FLAGS.** The incident is genuinely live today (re-confirmed by me, not
inherited). The FORK-I1 root-cause MECHANISM (c — asana Lambda authenticates via the wrong code
path; no mint provider injected; static key unset) is backed by deterministic code+IaC receipts I
verified line-by-line AND by live runtime evidence I pulled independently. Rungs are largely honest.
NO production-mutating lever is falsely claimed done.

Two flags, both NON-BLOCKING: (F1) the runbook's *semantic gloss* of AUTH-TEB-001 ("id recognized,
secret wrong") is WRONG per the authoritative SDK definition — the live error is "No authorization
token provided" = no header sent at all; this STRENGTHENS (c) and further refutes (a), but the
runbook's stated meaning is borrowed from canary prose that does not govern this code path. (F2) I
discovered a LIVE secondary gap the runbook under-weights: the IAM PutMetricData grant (PR #631) IS
deployed to prod, yet `cloudwatch:PutMetricData` is STILL AccessDenied TODAY for
`WorkflowSuccessRate`/`WorkflowDuration`/`WorkflowExecutionCount` because those emit to the ungranted
default namespace (`autom8/lambda`), not the granted `Autom8y/AsanaInsights`. AI-3b is therefore
load-bearing for those three metrics, not "defensive only." Neither flag changes SEV2 / incident-OPEN.

---

## GREEN / RED MATRIX

| # | Check | Result | Evidence (verified by me) |
|---|---|---|---|
| 1 | Incident genuinely still live TODAY (succeeded:0) | **GREEN** | Logs Insights, my pull: 2026-06-24 11:01:10 `insights_export_completed` → `succeeded:0 failed:60 total_tables_failed:720`. Every day 06-17..06-24 succeeded:0. recordsScanned=10,432 (real denominator, non-silent). |
| 1b | AUTH-TEB-001 still firing | **GREEN** | My pull: 2026-06-24 11:01:10 dozens of `insights_export_table_failed` with `{'code':'AUTH-TEB-001','message':'No authorization token provided.'}`. recordsScanned=3,469. |
| 2a | (c) MECHANISM — Lambda builds DataServiceClient with NO auth_provider | **GREEN** | `workflow_handler.py:158` `async with DataServiceClient() as data_client:` — no auth_provider. Verified at HEAD. |
| 2b | Static path returns AUTOM8Y_DATA_API_KEY; no mint | **GREEN** | `client.py:131` `config or DataServiceConfig.from_env()`; `_get_auth_token()` falls to `resolve_secret_from_env(token_key)`; `config.py:231` `token_key="AUTOM8Y_DATA_API_KEY"`; Bearer attached `client.py:438`. |
| 2c | Mint path wired ONLY into FastAPI/CLI, never Lambda | **GREEN** | `dependencies.py:494-505` builds `ServiceTokenAuthProvider`; comment explicitly says Lambda/ECS falls back to env `AUTOM8Y_DATA_API_KEY`. `grep ServiceTokenAuthProvider lambda_handlers/` = 0 hits. |
| 2d | IaC provisions mint-leg creds, NOT static key | **GREEN** | `autom8y/terraform/services/asana/main.tf:1851-1864` env sets `SERVICE_CLIENT_ID`, secret `SERVICE_CLIENT_SECRET`; `grep AUTOM8Y_DATA_API_KEY` in asana terraform = 0 hits. |
| 2e | TokenManager `sa_*` → /tokens/exchange-business (TEB) | **GREEN** | `autom8y_core/token_manager.py:481-484` `sa_` prefix → `/tokens/exchange-business`. |
| 2f | LIVE Lambda env confirms wiring (UV-P DISCHARGED) | **GREEN** | `aws lambda get-function-configuration`: `SERVICE_CLIENT_ID=sa_20180...` present; `AUTOM8Y_DATA_API_KEY` ABSENT; `SERVICE_CLIENT_SECRET_ARN` present. The runbook's one UV-P is now discharged: the static key really is unset at runtime. |
| 2g | NO mint activity in Lambda logs (refutes (a)) | **GREEN** | My pull over 2d for `TokenManager`/`ServiceTokenAuthProvider`/`oauth`/`mint`/`exchange-business` = **0 rows** (recordsScanned 2,342). The mint log line that would promote (a) provably does not exist. |
| 2h | AUTH-TEB-001 semantic = "id recognized, secret wrong" | **RED → F1** | Authoritative SDK: `autom8y-auth/errors.py:51-52` AUTH-TEB-001 = "No Authorization header present (401)"; `middleware.py:357-366` empty header→001, malformed→002, bad-JWT→003. Live message "No authorization token provided" = `MissingTokenError`→001 = NO header. The runbook's "secret wrong" gloss describes AUTH-TEB-003, lifted from canary docstring (`autom8y-data/.../canary/mint.py:8-12`), which narrates the canary's *own* wrong-leg trap — not this code. |
| 3a | Incident rung honest (OPEN, not proven-fixed) | **GREEN** | Runbook holds incident OPEN/proven-stale; no fix claimed. Matches my live succeeded:0. |
| 3b | AI-3 deploy-state honestly scoped | **GREEN (with correction)** | Runbook says AI-3a is "authored in IaC, confirm-applied-to-prod." I confirmed it: inline policy `autom8-asana-insights-export-cloudwatch-metrics` is LIVE on prod role with namespaces `[Autom8y/AsanaInsights, Autom8y/AsanaBridgeFleet]`. So AI-3a → **live** (I advanced it). |
| 3c | AI-2 fix correctly user-sovereign vs agent | **GREEN** | PRIMARY (c) = code → 10x-dev; FAST-PATH = USER-SOVEREIGN secret provisioning. Correct: only operator holds the SA secret. |
| 3d | IaC repo-surface honesty (-wt-golive absent) | **GREEN** | Runbook corrects mission assumption; asana IaC lives in autom8y monorepo `terraform/services/asana/main.tf`. Verified present. |
| 4 | No prod-mutating lever claimed DONE | **GREEN** | Token rotation, IAM apply, alarm-arm all surfaced as actions, not executed. Alarms ship `actions_enabled=false` (main.tf:690,749,781,817,858). I confirmed no autonomous mutation occurred. |
| 4b | AI-3b "defensive only" framing | **RED → F2** | Live AccessDenied TODAY (06-24 11:01:10, ×3 metrics) despite grant applied. `emit_metric("WorkflowSuccessRate",…)` (workflow_handler.py:287) passes NO namespace → defaults to `settings.observability.cloudwatch_namespace` = `ASANA_CW_NAMESPACE` (cloudwatch.py:50, default `autom8/lambda`), which the env does NOT set and the grant does NOT cover. So AI-3b is load-bearing for these 3 metrics, not merely defensive. |

**Counts: 14 GREEN, 2 RED (both non-blocking flags), 0 BLOCKING.**

---

## FLAG F1 (non-blocking) — AUTH-TEB-001 semantic gloss is wrong; verdict (c) is *strengthened* not weakened

The runbook repeatedly characterizes AUTH-TEB-001 as *"id recognized, secret wrong — the service-key
value is not the exchange-business client_secret."* That is **false for this error code.** The
authoritative `autom8y-auth` SDK (`sdks/python/autom8y-auth/src/autom8y_auth/errors.py:51-52` and
`middleware.py:329,357-366`) defines AUTH-TEB-001 as **"No Authorization header present on a protected
route (HTTP 401)"** — i.e. the client sent NO token at all. The "secret wrong" semantic belongs to
AUTH-TEB-003 (invalid/unverifiable JWT). The runbook lifted the "secret wrong" prose from the
autom8y-data canary docstring, which narrates the canary's *deliberate* wrong-leg mint — a different
scenario from this Lambda's.

The LIVE message I pulled — `'message': 'No authorization token provided.'` — is unambiguous and
matches the SDK's `MissingTokenError` ("No authorization token provided.", errors.py:177). This is
the EXACT runtime signature of the (c) mechanism: `_get_auth_token()` returns `None` (key unset, no
provider) → `client.py:437` `if token:` is False → **no Bearer header attached** → data service sees
no Authorization header → AUTH-TEB-001. So the corrected semantic makes (c) *more* certain and (a)
*less* plausible: a token-rotation/stale-secret incident (a) would surface as AUTH-TEB-003, not 001.
Recommend the runbook correct the gloss; the verdict and operator actions stand.

## FLAG F2 (non-blocking) — live PutMetricData AccessDenied persists; AI-3b is load-bearing

The IAM grant from PR #631 IS applied to the prod role (I verified the live inline policy). Yet on
the 06-24 run, `cloudwatch:PutMetricData` AccessDenied fired for `WorkflowSuccessRate`,
`WorkflowDuration`, `WorkflowExecutionCount`. Cause: those `emit_metric(...)` calls
(workflow_handler.py:281-292) pass no `namespace`, so they default to `autom8/lambda`
(cloudwatch.py:50; env has no `ASANA_CW_NAMESPACE`), which the grant's namespace Condition does NOT
include. The runbook frames AI-3b (`ASANA_CW_NAMESPACE` mirror) as "defensive only … the handler
literal already equals the granted namespace" — that is true for the DMS `LastSuccessTimestamp`/
`BridgeFleetHealth` emits (which pass explicit granted namespaces) but FALSE for the three default-
namespace metrics, which are denied live right now. Impact is bounded: these are secondary
observability metrics, NOT the succeeded-gated DMS (which never emits while dark anyway), so SEV2 and
incident-OPEN are unaffected. But AI-3b should be reclassified load-bearing-for-these-metrics, and the
runbook's verification step ("no AccessDenied for PutMetricData") will NOT go clean until either
`ASANA_CW_NAMESPACE=Autom8y/AsanaInsights` is set OR the grant adds `autom8/lambda`.

---

## WHAT IS CLEARED TO STRONG

- **Incident is live / OPEN / proven-stale** — STRONG. Re-pulled by me at HEAD date; succeeded:0 on
  today's run; non-silent denominator.
- **FORK-I1 root-cause MECHANISM = (c)** (Lambda authenticates via wrong path; no header sent) —
  STRONG. Carried by deterministic code+IaC receipts (all verified) PLUS three independent live
  signals: the literal "No authorization token provided" error, the discharged UV-P (key unset at
  runtime), and zero mint-activity in logs. NOT (a): a stale secret would yield AUTH-TEB-003, and no
  mint even executes.
- **(a) token-rotation ruled out** — STRONG (was "leading hypothesis" in the runbook; the live
  no-mint + no-header + key-unset evidence promotes the rebuttal to proven).
- **AI-3a IAM grant** — promoted **authored → live** by my prod-role pull.
- **No prod-mutating lever falsely claimed done** — STRONG.

## RESIDUAL / NOT CLEARED

- Operator FAST-PATH and PRIMARY (c) fix remain `authored` — neither executed (correct; READ-ONLY).
- Incident does NOT reach `proven` until a real `succeeded>0` run is observed. Unchanged.
- F2 means the runbook's PutMetricData-clean verification criterion is currently UNMET independent of
  the auth fix; surface this so it is not mistaken for collateral of the auth remediation.

**BLOCKING items: NONE.**
