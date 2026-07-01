---
type: review
artifact_role: incident-runbook + fork-resolution
slug: sre-insights-incident-runbook
status: accepted
incident_state: OPEN (proven-stale until a succeeded>0 run)
rite: sre
agent: incident-commander
phase: command (declare + classify FORK-I1 + operator runbook); READ-ONLY this phase
date: 2026-06-24
aws_account: 696318035277
aws_region: us-east-1
head_asana: f4f924d2684386093ef656ecde5e98613cdffce8
upstream:
  - .ledge/reviews/sre-dark-subsystem-postmortem.md (N1 coordinate — AI-1..AI-8 source)
  - .ledge/reviews/handoffs/cross-rite-handoff-releaser-to-10x-platform-know-2026-06-24.md
discipline: >
  Contributing factors, not root cause [II:SRC-001 Cook 1998 | STRONG]. Local rationality, not blame
  [II:SRC-002 Dekker 2006 | STRONG]. Latent conditions before the trigger [II:SRC-003 Reason 1997 | STRONG].
  G-RUNG: authored < emitting < alerting < proven < merged < live < protecting-prod — named, never rounded.
  G-DENOM: no proven-zero from silence. SVR: every platform-behavior claim carries a file:line receipt or is
  labelled UV-P.
acid_test: >
  If this recurs, does this runbook prevent a repeat? The single operator action is exact, reversible, and
  has a falsifiable verification (succeeded>0 + a live PutMetricData datapoint). Each item is a SYSTEM change.
---

# Incident Command — insights-export BI export DARK (succeeded:0 since 2026-06-10)

> **READ-ONLY phase.** No mutation, no deploy, no token, no PR. Every action below is operator-gated
> (confirm-first). The single USER-SOVEREIGN action is marked. The incident stays **OPEN / proven-stale
> until a `succeeded>0` run is observed.**

## §0 — DECLARATION

| Field | Value |
|---|---|
| **Severity** | **SEV2** (BI data product fully down; degraded-mode internal analytics, no external customer-data exposure, no regulatory surface) |
| **Status** | OPEN — proven-stale; NOT mitigated; NOT resolved |
| **Impact** | The insights-export bridge has produced **`succeeded:0` on every daily run since at least 2026-06-10** (~14 days). The user-visible BI insights export (12-table Asana attachment per offer) is **not being produced**. Lambda invokes daily, errors zero at the Lambda layer, succeeds zero at the workflow layer. |
| **Detection** | The dead-man succeeded-gate (`42b7cb0b`, deployed 06-17 12:24) converted an 8-day-old silent-green failure into a visible-stale `LastSuccessTimestamp` on 06-18. The gate is the detection event, NOT the fault [II:SRC-002 Dekker 2006 — local rationality]. |
| **Severity rationale** | NOT SEV1: <1% surface, internal analytics product, low-traffic modern stack (most prod traffic still flows the legacy monolith). Tying severity to impact, not team stress [SR:SRC-001 Beyer et al. 2016 — anti-inflation]. |

### Blameless timeline (receipted, UTC) — inherited + extended from N1 §1

| When | Event | Receipt |
|---|---|---|
| **2026-06-10 11:00:43** | `AUTH-TEB-001` already firing — earliest in the 14d scan window (could be older). Functional failure is **latent and pre-window**. | N1 §1: Logs Insights `filter @message like /AUTH-TEB-001/ sort asc limit 1` → `2026-06-10 11:00:43.861`, recordsScanned=18,007 (non-silent) |
| **06-17 11:00:35** | insights-export `cloudwatch:PutMetricData` **AccessDenied** logged verbatim; run posts `succeeded:0 failed:61`. | N1 §1 `metric_emit_error` |
| **06-17 12:24:34** | `42b7cb0b` succeeded-gate lands — detection trigger. | N1 §1 `git show -s 42b7cb0b` |
| **06-18** | First stale day post-gate — the "dark since 06-18" signal. | N1 §1 `insights_export_completed` 06-18 `succeeded:0` |
| **06-19..06-23** | insights-export continues `succeeded:0` daily (59-61 failed). | N1 §1 per-day receipts |
| **(monorepo, undated this phase)** | PR **#631** `feat(asana): grant workflow Lambdas CloudWatch PutMetricData for DMS emission` lands the `Autom8y/AsanaInsights` + `Autom8y/AsanaBridgeFleet` namespace grant in IaC. | `git -C autom8y log` → `50e4d241 feat(asana): grant workflow Lambdas CloudWatch PutMetricData ... (#631)` |
| **2026-06-24** | This command phase: FORK-I1 classified on live cross-repo evidence. | this artifact |

---

## §1 — FORK-I1 VERDICT (the load-bearing deliverable)

> **The question:** is `AUTH-TEB-001` caused by **(a)** an expired/invalid `AUTOM8Y_DATA_API_KEY` JWT value
> (user-sovereign token rotation), **(b)** asana client not registered / wrong `SERVICE_CLIENT_ID` on the
> autom8y-data side (cross-repo data-side fix), or **(c)** asana reading the wrong secret name / wiring
> (10x-dev code fix)?

### VERDICT: **(c) — a 10x-dev code-wiring defect, with a (b)-shaped env contradiction as the proximate trigger.** The insights-export Lambda authenticates via the WRONG asana code path.

This is **not** a token-rotation incident (a). It is a **wiring divergence**: the Lambda env provisions the
**mint-leg credentials** (`SERVICE_CLIENT_ID` + `SERVICE_CLIENT_SECRET`) but the Lambda **code path reads a
different, unprovisioned credential** (`AUTOM8Y_DATA_API_KEY`). The two halves do not meet.

### What AUTH-TEB-001 means on the data side (proven)

- **"TEB" = Token Exchange Boundary.** `AUTH-TEB-001` is the canonical class **`AuthTebInvalidCredentialsError`**,
  HTTP **401**, `retryable=False`, severity `warning`, raised at the **`POST /tokens/exchange-business`** mint
  boundary in the central auth service. Receipt: `autom8y/services/auth/tests/test_hc12_auth_teb_observability.py:154,168,217,226-227` —
  `AuthTebInvalidCredentialsError(...)` → `error_code == "AUTH-TEB-001"`, `http_status == 401`,
  `request_path == "/tokens/exchange-business"`, `retryable is False`.
- **Plain-English semantics**, stated by the autom8y-data canary subsystem (the rite-disjoint authority written
  expressly to catch this): *"the wrong-leg mint fails with AUTH-TEB-001 'id recognized, secret wrong'"* and
  *"wrong leg — service-key value is not the exchange-business client_secret."* Receipt:
  `autom8y-data/src/autom8_data/api/canary/mint.py:8-12,45-48`; `.../canary/__init__.py:12-14`.
- The autom8y-data inbound JWT path (`autom8_data/src/autom8_data/api/auth/jwt.py:209-344`) validates a
  *presented* token via the `autom8y-auth` SDK against JWKS (signature/expiry/issuer). A **mint-time**
  AUTH-TEB-001, by contrast, fires when the **caller's own credential exchange at `/tokens/exchange-business`
  is rejected** — i.e. the caller never obtains a valid token to present. The asana insights-export failures
  are mint-leg failures, not inbound-validation failures.

### How asana mints/sends the outbound JWT (proven) — the wiring contradiction

1. **The Lambda data client is constructed with NO auth_provider.**
   `autom8y-asana/src/autom8_asana/lambda_handlers/workflow_handler.py:158`:
   `async with DataServiceClient() as data_client:` — positional/keyword `auth_provider` is **absent**.
2. **`DataServiceClient(auth_provider=None)` falls through to the static env-token path.**
   `clients/data/client.py:131` (`config or DataServiceConfig.from_env()`) + `:450-474` `_get_auth_token()`:
   with `auth_provider is None`, it returns `resolve_secret_from_env(self._config.token_key)` where
   `token_key = "AUTOM8Y_DATA_API_KEY"` (`clients/data/config.py:231`). The resolved value is attached
   **verbatim** as `Authorization: Bearer {token}` (`client.py:438-439`). **There is no mint step on this path** —
   it forwards a *pre-existing static token value*.
3. **The mint path exists but is wired ONLY into FastAPI/CLI — never the Lambda.**
   `api/dependencies.py:494-505` prefers `ServiceTokenAuthProvider()` (which reads `SERVICE_CLIENT_ID` +
   `SERVICE_CLIENT_SECRET` and mints via `autom8y_core.TokenManager`, `auth/service_token.py:35-56`), falling
   back to the static key. The Lambda workflow handler does **not** use `dependencies.py`; it never builds
   `ServiceTokenAuthProvider`.
4. **The IaC provisions the MINT-leg credentials, not the static key.**
   `autom8y/terraform/services/asana/main.tf:1852-1864` (insights_export module env):
   `environment_variables = { AUTOM8Y_DATA_URL, SERVICE_CLIENT_ID, OTEL_SERVICE_NAME }` and
   `secret_arns = { SERVICE_CLIENT_SECRET, ASANA_PAT, ASANA_WORKSPACE_GID }`. **`AUTOM8Y_DATA_API_KEY` is NOT set
   on this Lambda.**
5. **TokenManager's mint-leg routing nails the failure mode.** `autom8y_core/token_manager.py:429-490`:
   `client_*` client_id → `POST /oauth/token` (RFC 6749 client_credentials); `sa_*` client_id →
   `POST /tokens/exchange-business` (legacy TEB — **where AUTH-TEB-001 lives**). A `sa_*` SERVICE_CLIENT_ID with a
   secret that is not the exchange-business client_secret is the canary's literally-named trap.

### Why (c), and the (b)-shaped proximate trigger

The **defect is in asana code** (c): the Lambda handler constructs `DataServiceClient()` without injecting
`ServiceTokenAuthProvider`, so it authenticates via the wrong leg (static `AUTOM8Y_DATA_API_KEY`) instead of
minting from the provisioned `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET`. The **proximate runtime symptom** is
(b)-shaped — the data/auth side returns AUTH-TEB-001 because the credential reaching the exchange boundary is
wrong/absent for this SA — but the **fix locus is asana**, not autom8y-data's client registry.

Two operator-resolvable surfaces collapse to ONE root action, in priority order:
- **PRIMARY (c):** wire the Lambda data client to mint via `ServiceTokenAuthProvider` (use the
  `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET` already in the env). Code fix → 10x-dev.
- **FAST-PATH bridge (operator, no code):** make the *existing* static-key path valid by provisioning the
  Lambda with a correct `AUTOM8Y_DATA_API_KEY` — BUT this is a static long-lived token (anti-pattern; the canary
  exists to shame exactly this leg). Use only as a stop-gap.

### Honest residual / missing receipts (G-DENOM)

- **No live JWT was observed in any source read this phase.** No `exp`/`claims`/sha256-prefix is recorded
  because no token value crossed the read surface (READ-ONLY, no prod log pull this phase). The N1 phase pulled
  the `AUTH-TEB-001` log lines but did not capture a token body; this phase did not re-pull logs. **The verdict
  rests on code+IaC wiring, which is deterministic and file:line-receipted — not on a captured token.**
- **What would FALSIFY (c) and promote (a):** a Lambda Logs-Insights pull showing the insights-export client
  DID build a `ServiceTokenAuthProvider` (a `token_manager`/mint log line) AND the mint itself returned
  AUTH-TEB-001 — that would mean the `SERVICE_CLIENT_SECRET` value is stale/wrong (a). **This is the one
  unpulled receipt.** Leading hypothesis remains (c): the code at `workflow_handler.py:158` provably never
  constructs the mint provider, so the mint log line cannot exist on the current HEAD.
- **`[UV-P: insights-export Lambda runtime resolves AUTOM8Y_DATA_API_KEY to empty/stale at invoke time |
  METHOD: deferred-to-prod-log-pull | REASON: READ-ONLY phase; env-at-runtime not probed]`** — the IaC shows the
  var is unset, but a Lambda-extension or account-default secret could theoretically inject it; a prod env dump
  (`aws lambda get-function-configuration`) discharges this.

---

## §2 — OPERATOR RUNBOOK (the single precise action that restores succeeded>0)

> **Decision authority (IC):** the FAST-PATH stop-gap restores `succeeded>0` with NO code deploy and is fully
> reversible — it is the correct first lever to convert OPEN→mitigated. The PRIMARY code fix (c) is the durable
> remediation and is routed to 10x-dev. Do FAST-PATH first only if a code deploy cannot land within SLA.

### PRIMARY action (c) — durable fix — route to 10x-dev (code) + platform (deploy)

**Single change:** inject `ServiceTokenAuthProvider` into the Lambda's `DataServiceClient` so it mints from the
already-provisioned `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET` instead of reading the unset
`AUTOM8Y_DATA_API_KEY`.

- **Exact locus:** `autom8y-asana/src/autom8_asana/lambda_handlers/workflow_handler.py:155-159`. Mirror the
  `api/dependencies.py:497-505` pattern: build `ServiceTokenAuthProvider()` (catching `ValueError`/`ImportError`),
  pass it as `DataServiceClient(auth_provider=...)`.
- **G-RUNG:** `authored` → (PR) `merged` → (deploy) `live` → `proven` (on a `succeeded>0` run).
- **Mutation class:** SAFE-AUTONOMOUS to author (asana-local code + RED-first test asserting the Lambda path
  builds a mint provider); PROD-MUTATING at deploy (operator-gated).

### FAST-PATH action — operator stop-gap, NO code — **USER-SOVEREIGN**

> **⚠ USER-SOVEREIGN — token/secret provisioning. Do NOT execute autonomously. Operator confirm-first.**
> This makes the *existing* static-key path valid. It is a long-lived-token anti-pattern; prefer PRIMARY.

**Exact step (operator console / authorized CLI, account 696318035277, us-east-1):**
1. Mint/locate a VALID data-service S2S JWT (or the `client_credentials`-issued token) for the asana SA, then
   set it as the insights-export Lambda's `AUTOM8Y_DATA_API_KEY` secret value — provisioned the SAME way the
   other secrets are (Secrets Manager + `enable_secrets_extension`), so it resolves via the Lambda extension.
   *Equivalently:* set `AUTOM8Y_DATA_API_KEY` to the Secrets-Manager ARN the extension resolves, populated with
   the valid token value.
2. This is USER-SOVEREIGN: only the operator holds the SA secret. **Never print the token; record sha256-prefix
   only.**

### Rollback (both paths)

- **PRIMARY:** revert the PR / redeploy the prior image tag (`var.image_tag`) — the Lambda returns to the static
  path. Reversible.
- **FAST-PATH:** delete/blank the `AUTOM8Y_DATA_API_KEY` secret value (or detach the ARN) — the Lambda returns to
  its current `succeeded:0` state. Reversible, no data written on a failed run (Lambda-layer error isolation held
  — Errors=0 throughout, per N1 §What-went-well).

### Verification (the incident does NOT close until BOTH are observed)

1. **A real `succeeded>0` run:** next daily `insights_export_completed` (or a manual invoke) posts
   `succeeded > 0` (was `succeeded:0`), and the `AUTH-TEB-001` count drops to 0 over one daily cadence.
   Probe: Logs Insights `filter @message like /insights_export_completed/` + `filter @message like /AUTH-TEB-001/`.
2. **A live PutMetricData datapoint:** `LastSuccessTimestamp` advances in namespace `Autom8y/AsanaInsights`
   AND no `metric_emit_error`/`AccessDenied` line for `cloudwatch:PutMetricData` appears.
   Probe: `aws cloudwatch list-metrics --namespace Autom8y/AsanaInsights` shows a fresh datapoint;
   `aws cloudwatch get-metric-statistics ... LastSuccessTimestamp` advances.

> **G-RUNG cap:** the incident reaches **`proven`** (one green run), NOT `live` (sustained) and NOT
> `protecting-prod`, until a daily cadence holds green AND the AI-7 alarms are armed.

---

## §3 — FOLD-IN ITEMS (rungs named per item)

### AI-3 — metric-restoration spec (`ASANA_CW_NAMESPACE` mirror of cache_warmer) — **SPEC + SURFACE only**

**Live-IaC correction (SVR):** the prior postmortem's CF-2 ("no policy permitting `cloudwatch:PutMetricData`")
was true at the **06-17 observation** but the IaC at current HEAD **already grants it**:
`autom8y/terraform/services/asana/main.tf:1896-1919` —
`aws_iam_role_policy "insights_export_cloudwatch_metrics"` with
`Condition.StringEquals."cloudwatch:namespace" = ["Autom8y/AsanaInsights","Autom8y/AsanaBridgeFleet"]` (PR #631,
`50e4d241`). The handler hardcodes `dms_namespace="Autom8y/AsanaInsights"`
(`lambda_handlers/insights_export.py:57`), which **matches the grant**.

**Therefore AI-3 is now a DEPLOY-STATE question, not an authoring gap.** Two sub-surfaces:
- **AI-3a (deploy):** confirm PR #631's grant is **applied to prod** (the 06-17 AccessDenied predates it). If the
  prod role lacks the grant, `terraform apply` the asana service module. **Rung: `authored` (in IaC) → `live`
  (on apply).** Verify: post-apply, `metric_emit_error`/PutMetricData-AccessDenied lines stop.
- **AI-3b (mission's `ASANA_CW_NAMESPACE` mirror — SPEC):** the mission asks to set
  `ASANA_CW_NAMESPACE=Autom8y/AsanaInsights` on the insights_export env, mirroring cache_warmer
  (`main.tf:339,458,618,1568` set it per-Lambda; cache_warmer resolves the DMS namespace via
  `get_settings().observability.cloudwatch_namespace` ← `ASANA_CW_NAMESPACE`, `settings.py:697-700`,
  `cloudwatch.py:50`, `cache_warmer.py:93-105`). **For insights-export this is DEFENSIVE, not load-bearing:** the
  handler's hardcoded literal already equals the granted namespace, so emit is not currently namespace-denied
  *if the grant is deployed*. Setting `ASANA_CW_NAMESPACE` makes the code-path resolution explicit and
  drift-proof (grant ↔ emit can never silently diverge), exactly as cache_warmer's C2 comment intends
  (`cache_warmer.py:75-90`). **SPEC:** add `ASANA_CW_NAMESPACE = "Autom8y/AsanaInsights"` to the
  insights_export `environment_variables` block (`main.tf:1852-1856`); no code change needed (the namespace
  flows through `dms_namespace or "BridgeWorkflows"` only when the handler passes a literal — to fully mirror
  cache_warmer, a 10x-dev follow-up could route `dms_namespace` through `_dms_namespace()` so the env is
  authoritative). **Rung: `authored` (spec, here) → `live` (on IaC apply). Mutation class: PROD-MUTATING (env
  change, confirm-first).**

**IaC target repo — SURFACE (mission asked to locate it):** the mission named `autom8y-wt-golive` as the IaC
target. **That repo is NOT on this filesystem** (verified: `find ... -name autom8y-wt-golive` → no match). The
**actual asana IaC lives in the autom8y MONOREPO** at
`/Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/asana/main.tf` (+ modules under
`terraform/modules/asana-workflow-lambda/`). All AI-3/AI-5/AI-7 IaC edits target THAT path.
**`[UV-P: autom8y-wt-golive is the deploy/apply harness for autom8y/terraform | METHOD: deferred-to-operator |
REASON: repo absent from this filesystem; relationship between the monorepo terraform/ and any -wt-golive apply
harness not probed]`.**

### AI-7 — alarm-arm plan (thresholds; paging gated)

The alarm IaC is **merged un-armed** (PR #148 `9b698280`,
`autom8y-asana/.../terraform/services/asana/observability_alarms.tf` per the releaser handoff §LANDED).
Arming the PAGE tier is a separate confirm-first step. Plan (4 alarms, inherited from N1 §B-2):

| Alarm | Signal | Threshold (PLATFORM-HEURISTIC) | Arm gate |
|---|---|---|---|
| **AL-3 LST-stale** | `LastSuccessTimestamp` (Autom8y/AsanaInsights) age | breach if `now - LST > 28h` (daily cadence + 4h grace) | arm AFTER a `succeeded>0` run exists (else it pages on the known-open incident) |
| **AL-4 prod BridgeFleetHealth** | `BridgeFleetHealth{workflow_id=insights-export, environment=production}` | breach if `< 1.0` for 1 datapoint | arm after AI-5 (the prod `environment` dim) lands |
| **AL-1 StatusPushSkipped** | `StatusPushSkipped{skip_reason}` (PR #148) | breach on `url_absent`/`invalid_key` reason > 0 (misconfig); idle/`feature_disabled` excluded | arm now (no incident dependency) |
| **AL-2 recon-gap** | recon Invocations | breach on 0 invocations in 8h | arm ONLY after AI-1 re-enables the recon rule (else pages on intended-off) |

- **Severity tie (anti-inflation):** page only AL-3/AL-4 (the data-product down signal). AL-1/AL-2 → ticket tier.
  Severity reflects user impact, not stress [SR:SRC-001 Beyer 2016].
- **G-RUNG:** alarms `authored` (IaC merged un-armed) → `alerting` (only on operator arm-confirm). No alarm is
  `alerting` until armed. **Mutation class: SAFE-AUTONOMOUS to author; PROD-MUTATING to arm.**

### Insights-freshness SLO / error-budget (one line)

**SLO:** ≥ 95% of scheduled daily insights-export runs produce `succeeded>0` and emit a fresh
`LastSuccessTimestamp` within 28h of schedule, measured 30-day rolling. **Error budget:** 5% = ~1.5
missed-freshness days / 30d; current consumption = **100% breached** (14/14 days dark → budget exhausted →
reliability work takes priority over feature velocity until restored) [SR:SRC-001 Beyer 2016 — error-budget
policy]. Threshold values are [PLATFORM-HEURISTIC].

---

## §4 — INCIDENT STATE LEDGER

- **OPEN / proven-stale.** Closes only on a `succeeded>0` run + a live `Autom8y/AsanaInsights` PutMetricData
  datapoint (§2 verification). No `proven` claim is licensed from silence (G-DENOM).
- **FORK-I1: VERDICT (c)** — asana Lambda authenticates via the wrong code path (static `AUTOM8Y_DATA_API_KEY`
  instead of minting from the provisioned `SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET`); proximate symptom is a
  (b)-shaped mint-boundary 401. NOT (a) token rotation. One unpulled receipt (prod Lambda log/env) would
  discharge the residual UV-P.
- **Per-item rungs:** Operator FAST-PATH `authored`→`proven` (on green run). PRIMARY (c) code fix
  `authored`→`merged`→`live`→`proven`. AI-3a `authored`→`live` (deploy-state). AI-3b SPEC `authored`→`live`.
  AI-7 `authored`→`alerting` (arm-gated). SLO `authored`.
- **Routing:** PRIMARY (c) → 10x-dev (code) + platform (deploy). FAST-PATH → operator (USER-SOVEREIGN). AI-3/AI-5/
  AI-7 IaC → platform-engineer, target `autom8y/terraform/services/asana/`. Resilience verification of the fix
  (mint-leg failure injection) → chaos-engineer.
