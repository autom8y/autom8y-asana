---
type: review
artifact_role: blameless-postmortem
slug: sre-dark-subsystem-postmortem
status: accepted
lifecycle_note: "ANALYSIS-ONLY (observe->coordinate); NO PROD MUTATION this phase"
rite: sre
agent: incident-commander
phase: coordinate (postmortem + classification); design + classify only, no arm/deploy/merge/PR
head: f4f924d2684386093ef656ecde5e98613cdffce8
date: 2026-06-24
aws_account: 696318035277
aws_region: us-east-1
upstream: [sre-observability-design.md (N1, observability-engineer)]
discipline: "Contributing factors, not root cause [II:SRC-001 Cook 1998]. Local rationality, not blame [II:SRC-002 Dekker 2006]. Latent conditions before the trigger [II:SRC-003 Reason 1997]. Rungs named, never rounded: authored < emitting < alerting < proven < merged < live < protecting-prod. G-DENOM: no proven-zero from silence."
acid_test: "If this recurs, does this postmortem prevent a repeat? Each action item is a SYSTEM change with a named work-unit, rung, and the receipt that advances it — no 'be more careful' items."
---

# Blameless Postmortem — the ~06-18..06-23 "dark subsystem"

> **ANALYSIS + CLASSIFY ONLY.** No alarm armed, no Lambda env/schedule changed, no PR opened, no
> retire executed. All AWS calls read-only (CloudWatch get-metric-statistics, events describe-rule,
> logs start-query/get-query-results, lambda get-function-configuration). Every PROD-MUTATING action
> below is operator-gated (G: confirm-first).

## Headline

There is **no single dark subsystem and no single root cause** [II:SRC-001 Cook 1998 | STRONG]. The
window contains **three structurally distinct conditions**, two of which are **latent failures that
predate the window** [II:SRC-003 Reason 1997 | STRONG], surfaced by one **correct, benign deploy**:

1. **insights-export has been functionally failing since at least 2026-06-10** — every run posts
   `succeeded:0` because an upstream auth dependency returns `AUTH-TEB-001` ("No authoriz..."). This
   is a **real INCIDENT** (data product not produced), latent since before the window.
2. **The CloudWatch metric pipe for insights-export is IAM-denied** —
   `autom8-asana-insights-export-lambda-role` has **no policy permitting `cloudwatch:PutMetricData`**
   (verbatim AccessDenied from 06-17 11:00:35). A **DEFECT** (IAM), independent of (1).
3. **The recon push-seam cron is DISABLED** — EventBridge rule
   `autom8y-account-status-recon-schedule` `State=DISABLED`, so the 06-20..23 invocation gap is the
   **EXPECTED** consequence of the off switch, not a defect. Cause-not-symptom.

The "darkness since 06-18" is the **dead-man gate (commit `42b7cb0b`, deployed 06-17) doing exactly
its job** — it stopped publishing a silent-green `LastSuccessTimestamp` over a fully-failed run. The
deploy did not *cause* darkness; it *revealed* a pre-existing failure. Local rationality
[II:SRC-002 Dekker 2006 | STRONG]: the gate was a deliberate honesty fix; what it exposed had been
true for ~8 days before it landed.

---

## §1 — Timeline (receipted, UTC)

| When | Event | Receipt |
|---|---|---|
| **2026-06-10 11:00:43** | insights-export upstream auth failures (`AUTH-TEB-001`) **already firing** — earliest in 14d scan window (could be older). The functional failure is **latent and pre-window**. | Logs Insights `filter @message like /AUTH-TEB-001/ sort asc limit 1` -> `2026-06-10 11:00:43.861`, recordsScanned=18,007 (non-silent) |
| ~06-04 onward | recon regular ~6/day cadence collapses; trail thins to 1-3/day | N1 §A-b Invocations trail (05-25=8 ... 06-04=6 06-05=4 ... 06-18=3) |
| **06-16 11:32** | `af2b012a` build(deps): adopt events 1.2.1 + log 0.6.0 | `git show -s af2b012a` |
| **06-17 11:00:35** | insights-export `cloudwatch:PutMetricData` **AccessDenied** logged verbatim; run posts `succeeded:0 failed:61` | Logs `metric_emit_error` + `insights_export_completed` 06-17 |
| **06-17 12:24:34** | **`42b7cb0b` fix(workflow-handler): gate dead-man timestamp on genuine success (#139)** lands — the succeeded-gate. | `git show -s 42b7cb0b` |
| **06-18** | First day the freshness dead-man goes stale post-gate: run posts `succeeded:0 failed:61` -> gate correctly suppresses `LastSuccessTimestamp`. **This is the "dark since 06-18" signal.** | `insights_export_completed` 06-18: `succeeded:0` |
| **06-18 16:32** | `29b7c439` fix(deps): pin starlette 1.3.1 (CVE) | `git show -s 29b7c439` |
| **06-19 10:07:26** | **`dd8e43ab` fix(warmer): observable AIMD + warm-cycle governor (#141)** lands — the warmer/governor change under suspicion. | `git show -s dd8e43ab` (stat: cache_warmer, transport, config; tests) |
| **06-19..06-23** | insights-export continues `succeeded:0` every day (60-61 failed). recon cron does not fire (rule DISABLED). | per-day `succeeded:0` 06-19/20/23; Invocations no datapoint 06-20..23 |
| **06-23 23:55:28** | insights-export Lambda last code/config modify (CodeSha 15983dc1...) | `lambda get-function-configuration` LastModified |
| **06-24 09:05:27** | **recon Lambda redeploy** (`autom8y-account-status-recon` LastModified `2026-06-24T09:05:27`) — the brief's "06-24 09:05 redeploy". Rule **still DISABLED** after it. | `lambda get-function-configuration` + `describe-rule State=DISABLED` (re-verified) |

---

## §2 — Per-symptom verdicts (INCIDENT | EXPECTED | DEFECT), each with a receipt

### SYMPTOM (1) — recon push-seam dark window 06-20..23 -> **EXPECTED** (cron OFF), not a defect

- **Verdict:** EXPECTED. The 06-20..23 invocation gap is the deterministic consequence of an
  intentionally/administratively **DISABLED** schedule, not a regression.
- **Receipt:** `aws events describe-rule --name autom8y-account-status-recon-schedule` ->
  `State=DISABLED`, `cron(0 */4 * * ? *)` (re-verified 06-24, still DISABLED). Invocations metric is
  **non-silent** on 06-18/19/24 (G-DENOM satisfied — the gap is a true gap, not absence-of-telemetry).
- **06-24 09:05 redeploy correlation:** the redeploy touched the recon **Lambda code/config**
  (LastModified `2026-06-24T09:05:27`) but did **NOT** re-enable the **rule** — `describe-rule` reads
  DISABLED after the redeploy. So cron still will not fire. The redeploy is **not** the gap's cause
  and does **not** resolve it. **Caveat (G-DENOM):** "DISABLED" is the proximate mechanism;
  *why* it is disabled (planned maintenance vs. forgotten re-enable vs. cost pause) is **not in the
  telemetry** — that is an IC decision input (§4 AI-1), not a falsified claim here.
- **Classification note (anti-pattern guard):** treating this as an INCIDENT would be Severity
  Inflation — there is no SLO breach until the rule is *meant* to be on. If reconciliation is
  business-required and the rule is off by accident, the INCIDENT is the **missing enable + the
  absence of an alarm that would have caught an off cron** — a process/coverage gap, not the cron.

### SYMPTOM (2) — insights-export bridge-fleet darkness (enabled cron, no LastSuccess since 06-18) -> **INCIDENT (real)**, latent since ~06-10

- **Verdict:** INCIDENT. The bridge **invokes daily, errors zero at the Lambda layer, and produces
  ZERO successful exports** — a fully-failed run every day. The user-visible data product
  (insights export) has not been produced since at least 06-10.
- **Receipts (pulled this phase — discriminates N1's two undecided hypotheses; BOTH are true):**
  - `insights_export_completed` per day: 06-17 `succeeded:0 failed:61`; 06-18 `succeeded:0 failed:61`;
    06-19 `succeeded:0 failed:59`; 06-20 `succeeded:0 failed:59`; 06-23 `succeeded:0 failed:60`.
    **`succeeded:0` on 06-17 too — before the gate and before the window.**
  - Upstream cause: every offer/table fails `InsightsServiceError {'code': 'AUTH-TEB-001', 'message':
    'No authoriz...'}`; earliest in 14d scan = **2026-06-10 11:00:43**.
  - IAM cause (independent): verbatim `AccessDenied ... arn:.../autom8-asana-insights-export-lambda-role
    ... is not authorized to perform: cloudwatch:PutMetricData because no identity-based policy allows
    the cloudwatch:PutMetricData action` (06-17 11:00:35).
- **Why "dark since 06-18" and not 06-10:** the dead-man succeeded-gate (`42b7cb0b`) deployed 06-17
  12:24. Pre-gate, a `succeeded:0` run still published a fresh `LastSuccessTimestamp` (silent-green).
  Post-gate, the gate suppresses the timestamp on `succeeded==0`, so the **first stale day is 06-18**.
  The gate **converted an 8-day-old silent failure into a visible one** — it is the detection event,
  not the fault.
- **This is a multi-factor failure** [II:SRC-001 Cook 1998 | STRONG]: even if `AUTH-TEB-001` were
  fixed tomorrow, the freshness/health metrics would **still** not emit because of the
  `PutMetricData` IAM denial. Two latent failures must both be cleared to restore the green signal.

### SYMPTOM (3) — data-quality skips (`three_way_denominator_null`, empty-vertical `invalid_key`) -> **mixed: EXPECTED at runtime, DEFECT in observability; location split asana vs autom8y-data**

- **Where `three_way` actually lives (confirmed):** the **three-way dispatch decision is in
  autom8y-data**, not asana — `autom8y-data/src/autom8_data/analytics/services/query_grain_guard.py:84`
  (`QueryRoute` PASS_THROUGH/DISPATCH/REFUSE) and `batch_grain_guard.py:174,:199` (the RQ-4 router).
  A grep for `three_way` in **autom8y-asana src** returns **no production source hits** (only test
  docstrings reference "denominator"). So `three_way_denominator_null` as a *reconciler* concept is a
  **data-repo (cross-repo) concern**.
- **What the asana skip actually is:** on the asana push-seam, the brief's
  `three_way_denominator_null` maps to the **empty-`all_entries` false branch** of
  `push_orchestrator.py:183` (no `else`), and the empty-vertical row-drop documented at
  `push_orchestrator.py:41-42` ("Others are silently skipped"). The `invalid_key` /
  `url_absent` / `feature_disabled` skips are at `gid_push.py:496,:504,:512` (all log-only,
  `return False`/`True`). Receipt: `gid_push.py` lines 491-519 read this phase.
- **Verdict:** For **low-traffic / test phones with no qualifying entries**, an empty push is
  **EXPECTED** (the docstring's "nothing to push is not a failure", `gid_push.py:514-519` returns
  `True`). It is **NOT** a runtime defect in asana. **However**, the **DEFECT is in observability**:
  every skip path is metric-silent (N1 §S4, `grep emit_metric gid_push.py` = none), so an *idle*
  skip (benign) and a *misconfigured* skip (`url_absent`/`invalid_key` = real "status data not
  reaching autom8_data") are indistinguishable. You cannot tell EXPECTED from INCIDENT without the
  `StatusPushSkipped{skip_reason}` counter.
- **Cross-repo caveat (G-DENOM):** whether the *reconciler-side* three-way denominator is genuinely
  null for the same phones (a data-side condition) cannot be proven from asana telemetry. That is the
  CROSS-REPO action AI-6.

### SYMPTOM (4) — deploy-correlation of `dd8e43ab` (06-19) -> **EXONERATED** for all three symptoms

- **Verdict:** `dd8e43ab` (the observable-AIMD + warm-cycle governor, #141) is **exonerated**. It did
  not cause the insights-export failure, the metric darkness, or the recon gap.
- **Receipts / reasoning:**
  - The governor is **observability-only by design** for the failing signal: its own commit body says
    C-1 fixed an AIMD logger that "runs observability-dark" — it *adds* visibility, it does not gate
    success. It touches `cache_warmer.py`, `adaptive_semaphore.py`, `asana_http.py`, `config.py`,
    `parallel_fetch.py` — the **warm transport path**, not the insights-export auth path nor the IAM
    role nor the EventBridge rule.
  - **Temporal exoneration:** the failing condition (`succeeded:0` driven by `AUTH-TEB-001`) is
    present on **06-17 and back to 06-10** — *before* `dd8e43ab` landed 06-19. A cause cannot
    postdate its effect [local-rationality timeline check, II:SRC-002 Dekker 2006].
  - The `PutMetricData` AccessDenied is an **IAM-role policy** condition (`-insights-export-lambda-role`),
    not code shipped in #141 (which changed no IAM).
  - The recon gap is the **DISABLED rule**, untouched by #141.
- **One honest residual:** #141 changed env-overridable rate tiers (C-4 UV-P) and a shared semaphore.
  If a *future* warm-set regression appears, that is its surface — but it is **orthogonal** to this
  postmortem's three symptoms. No implication here.

---

## §3 — Contributing factors (blameless; NOT a single root cause) [II:SRC-001 Cook 1998 | STRONG]

The Swiss-cheese alignment [II:SRC-003 Reason 1997 | STRONG] — multiple latent holes that lined up:

- **CF-1 (latent, upstream): `AUTH-TEB-001` auth failure to the insights service**, present since
  >=06-10. The insights-export bridge cannot authorize against its data dependency; every table for
  every offer fails. *Local rationality:* the bridge code is behaving correctly given a hard upstream
  401-class error; it logs per-offer failures and posts an honest `succeeded:0`.
- **CF-2 (latent, IAM): `cloudwatch:PutMetricData` denied** for the insights-export role. Even a
  fully-successful run could not publish `LastSuccessTimestamp`/`WorkflowSuccessRate`/`Duration`.
  This is a defense-in-depth hole that would have masked recovery. *Local rationality:* whoever
  scoped the role omitted the CloudWatch action; nothing failed loudly because the emit path
  swallows the error into a `warning` log (`metric_emit_error`).
- **CF-3 (correct fix, detection trigger): the dead-man succeeded-gate (`42b7cb0b`)** — by refusing
  to publish a fresh timestamp on `succeeded==0`, it converted CF-1 from silent-green to visible-stale
  on 06-18. *This is the system working as designed* — the gate was authored precisely to prevent a
  silent-green dead-man (its own comment, `workflow_handler.py:312-318`). It is a contributing factor
  to *detection timing*, not to *failure*.
- **CF-4 (coverage gap): no alarm on freshness, on PutMetricData denial, or on a disabled cron.**
  The failure ran ~8 days before any human noticed. The absence of N1's AL-2/AL-3/AL-4 is why this was
  found by archaeology, not by a page.
- **CF-5 (observability gap): metric-silent skip seam.** The `StatusPush*` skip reasons emit no
  metric, so benign-idle and misconfigured-skip are indistinguishable (Symptom 3).
- **CF-6 (process): recon cron DISABLED with no record of why** and no alarm to flag an off-but-
  expected-on schedule. Whether intended or forgotten is undetermined from telemetry (AI-1).
- **CF-7 (cross-repo seam): the three-way denominator semantics live in autom8y-data** while the
  asana skip surfaces the symptom — a divided-ownership seam where neither side alone can classify a
  null denominator as benign vs. broken.

**No blame-shaped factor.** No "developer should have...". Every CF above is a system/process/config
condition. The dead-man gate author shipped a *correct honesty improvement*; surfacing CF-1 is a win,
not a regression.

**Where we got lucky:** the dead-man gate landed 06-17 — one day before staleness. Had it not, CF-1
would still be silent-green today and the insights product would be quietly empty with a green
dashboard. The 06-17 deploy is the reason we are reading this at all.

**What went well:** Lambda-layer error isolation held (Errors=0; the bridge degraded gracefully
rather than crash-looping); per-offer structured failure logs (`insights_export_offer_failed` with
`error_count`, `trace_id`) made CF-1 diagnosable in one Logs Insights query; the succeeded-gate
prevented a false-green.

---

## §4 — Action items (each routed to a work-unit, with rung + advancing receipt + mutation class)

Rung ladder: `authored < emitting < alerting < proven < merged < live < protecting-prod`.
Mutation class: **SAFE-AUTONOMOUS** (reversible, asana-local, no prod arm) | **PROD-MUTATING**
(operator-gated, confirm-first per G) | **CROSS-REPO** (autom8y-data).

| ID | Action (SYSTEM change, not behavior) | Work-unit | Mutation class | Current rung -> target | Advancing receipt |
|---|---|---|---|---|---|
| **AI-1** | **IC decision: is recon reconciliation business-required?** If yes, re-ENABLE `autom8y-account-status-recon-schedule`; if intentionally paused, record the pause + expected-on date so AL-2 doesn't page on intended-off. | recon schedule (EventBridge) | **PROD-MUTATING** (enable-rule = confirm-first) | `authored` -> `live` | `aws events enable-rule` then `describe-rule State=ENABLED` + first cron Invocations datapoint within 4h |
| **AI-2** | **Fix CF-1: restore insights-export upstream authorization** (`AUTH-TEB-001`). This is the actual data-product INCIDENT. Likely a credential/scope on the insights service dependency. | insights-export fix (likely cross-service auth/secret) | **PROD-MUTATING** + may be **CROSS-REPO** (depends where the insights-service credential is owned) | `authored` -> `proven` | a run posting `succeeded > 0` in `insights_export_completed`; `AUTH-TEB-001` count drops to 0 over one daily cadence |
| **AI-3** | **Fix CF-2: grant `cloudwatch:PutMetricData`** to `autom8-asana-insights-export-lambda-role` (IaC the policy; do not hand-edit). Independent of AI-2 — needed for ANY green signal. | alarm/IaC -> Platform Engineer (IAM policy in IaC) | **PROD-MUTATING** (IAM change, confirm-first) | `authored` -> `live` | post-deploy: `metric_emit_error` PutMetricData lines stop; `list-metrics Autom8y/AsanaInsights` shows `LastSuccessTimestamp` advancing |
| **AI-4** | **Wire `StatusPushSkipped{skip_reason}` counter** at the 4 skip sites (`gid_push.py:496,:504,:512` + `push_orchestrator.py:183` else-branch). RED-first two-sided fixtures per reason (N1 §B-1). Closes CF-5 / Symptom 3 observability defect. | W-OBS metric (instrumentation) -> Platform Engineer | **SAFE-AUTONOMOUS** (asana-local code + tests; no prod arm) | `authored` -> `emitting` (then `merged` on PR) | new unit tests FAIL on HEAD (no emit), PASS post-change; `grep emit_metric gid_push.py` becomes non-empty |
| **AI-5** | **Add `environment` dimension to BridgeFleetHealth/DMS emit** (`workflow_handler.py:256-262,:330-339`) so a **prod** fleet-health series exists (today only `{staging, insights-export}`). | W-OBS metric (instrumentation) -> Platform Engineer | **SAFE-AUTONOMOUS** (code) then **PROD-MUTATING** at deploy | `authored` -> `emitting` | `list-metrics Autom8y/AsanaBridgeFleet` shows an `environment=production` series after deploy |
| **AI-6** | **Cross-repo: classify the three-way denominator for the affected phones** in autom8y-data (`query_grain_guard.py:84` / `batch_grain_guard.py:174`). Confirm whether null-denominator for low-traffic/test phones is benign-by-design (then assert it) or a reconciler gap. | CROSS-REPO data-side fix -> autom8y-data owners | **CROSS-REPO** | `authored` -> `proven` | a data-repo test asserting REFUSE/PASS_THROUGH route on the null-denominator shape + a decision record on benign-vs-defect |
| **AI-7** | **IaC the 4 alarms UN-ARMED** (N1 §B-2: AL-1 StatusPushSkipped, AL-2 recon-gap — arm only after AI-1 enable, AL-3 LST-stale, AL-4 prod BridgeFleetHealth). Arming the PAGE tier is a separate confirm-first step. Closes CF-4. | alarm IaC -> Platform Engineer | **SAFE-AUTONOMOUS** to author IaC; **PROD-MUTATING** to arm | `authored` -> `alerting` (only after arm-confirm) | `describe-alarms` shows the 4 alarms present; arm event is a distinct operator confirmation |
| **AI-8** | **FORK-1 retire `/v1/query/{entity_type}`** via 410-canary-then-unmount (N1 §D; usage `proven`-zero on live non-silent groups). Not a silent delete. | FORK-1 retire -> Platform Engineer | **PROD-MUTATING** (410 flip + mount removal, confirm-first) | usage `proven`; removal `authored` -> `live` | one cadence of ECS 4xx + `deprecated_query_endpoint_used` staying 0 after 410 flip, THEN remove `api/main.py:470` mount |

**Acid test pass:** none of AI-1..AI-8 is "remind/train/be-careful". Each is an enable, a grant, an
emit, a dimension, a cross-repo assertion, an alarm, or a retire — all system/config/code changes
with a falsifiable advancing receipt [II:SRC-002 Dekker 2006 | STRONG — fix the system, not the human].

---

## §5 — Mutation-class summary (operator gating, per brief)

- **SAFE-AUTONOMOUS (reversible, asana-local; can proceed in build phase without prod arm):**
  AI-4 (StatusPushSkipped code + tests), AI-5 (environment dimension code), AI-7 *authoring* the
  alarm IaC un-armed. These land as PRs/tests; nothing pages, nothing mutates prod state at author
  time.
- **PROD-MUTATING (operator-gated, confirm-first per G):** AI-1 (enable recon rule), AI-2 (restore
  insights auth), AI-3 (IAM PutMetricData grant), AI-5 *deploy*, AI-7 *arming* the paging tier, AI-8
  (410-canary + unmount). Each needs explicit IC + user sign-off; each is reversible
  (disable-rule / revoke-policy / re-arm-off / re-mount).
- **CROSS-REPO (autom8y-data):** AI-6 (three-way denominator classification). AI-2 may also be
  cross-repo/ cross-service depending on where the insights-service credential is owned (undetermined
  from asana telemetry — IC to route).

---

## §6 — Discipline ledger (G-RUNG / G-DENOM)

- **G-RUNG:** AI-2 capped at `proven` (a green run), not `live` (sustained). AI-8 usage `proven`,
  removal `authored`. No item claims `protecting-prod`. No alarm is `alerting` until armed (AI-7).
- **G-DENOM:** every proven-zero / true-gap is checked against non-silence first — recon gap validated
  against non-silent Invocations (06-18/19/24); `AUTH-TEB-001` onset read against recordsScanned=18,007
  (non-silent); insights `succeeded:0` read from live runs (recordsScanned>0 each day). The recon
  "DISABLED" mechanism is proven; the *intent* behind it is explicitly NOT asserted (AI-1).
- **No-single-root-cause:** seven contributing factors enumerated; the brief's framing of a single
  "dark subsystem" is re-cast as three distinct conditions + one benign detection trigger.

**Evidence footing:** contributing-factors-not-root-cause, local rationality, latent-conditions,
blameless system-fixes are STRONG [II:SRC-001 Cook 1998; II:SRC-002 Dekker 2006; II:SRC-003 Reason
1997]. Severity / freshness thresholds inherited from N1 are [PLATFORM-HEURISTIC].
