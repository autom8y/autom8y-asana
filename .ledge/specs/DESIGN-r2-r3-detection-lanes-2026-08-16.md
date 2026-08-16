---
type: spec
artifact_type: observability-design
artifact_id: DESIGN-r2-r3-detection-lanes-2026-08-16
status: proposed
wave: coc-reattest-seam
lane: C
session: session-20260816-103254-f12e8f75
seat: observability-engineer (sre, co-seated)
self_assessment_cap: MODERATE
scope: "DESIGN ONLY — no build, no apply, no live mutation performed by this dispatch"
supersedes: none
levers_addressed:
  - "H-1 lever 6 — R-2 continuous swap detection (.ledge/handoffs/H-1-coc-arm-the-instrument-2026-08-15.md:86)"
  - "H-1 lever 7 — R-3 hash-presence deadman (.ledge/handoffs/H-1-coc-arm-the-instrument-2026-08-15.md:87)"
law_refs:
  - .ledge/reviews/SURFACE-limb-a-live-realized-2026-08-15.md
  - .ledge/handoffs/H-1-coc-arm-the-instrument-2026-08-15.md
  - .ledge/decisions/ADR-asr-content-hash-canonicalization-2026-08-14.md
  - .know/scar-tissue.md (SCAR-ALARM-BINDING-001)
---

# DESIGN — R-2 continuous-detection lane + R-3 hash-presence deadman

**This is a design paper. Nothing here is built, applied, or armed by this
dispatch.** Every AWS-mutating step below is named as an operator-gated action
with its exact command. The build is a follow-on with its own writer.

---

## §0. The two gaps, stated as symptoms

The swap detector was ARMED on the wire 2026-08-14 (autom8y PR #1636 →
`3dde20ef`), and the first two live ticks traversed the join's OBSERVABLE
branch — occurrence count 0 → 2
(`.ledge/reviews/SURFACE-limb-a-live-realized-2026-08-15.md:46-56`). Two
residuals were surfaced with it and are the subject of this paper
(`SURFACE-limb-a-live-realized-2026-08-15.md:78-84`):

| # | Gap | Symptom (customer-facing framing) | Blind window today |
|---|---|---|---|
| **R-2** | **armed-as-emitter**: `content_hash_mismatch` fires only when a human runs the join | A swapped Slack readout is delivered to `#account-health` and nothing notices until an attester happens to re-run the instrument | **unbounded** |
| **R-3** | **silent de-arming**: if `report_posted` regresses to hashless, clause 4a goes dark and the join silently falls to the 4b block-count fallback | The instrument reads GREEN while payload-identity is no longer verified — swap-blindness with the paper still saying LIVE-REALIZED | **unbounded** |

R-3 is not hypothetical. H-1 carries HAZARD H-2 standing:
`.ledge/handoffs/H-1-coc-arm-the-instrument-2026-08-15.md:89` — *"any manual
apply there can roll the Lambda back past `3dde20ef` and silently un-arm the
instrument while the paper reads LIVE-REALIZED."* **R-3's deadman is the
tripwire for H-2.**

Both gaps are symptom-shaped, not cause-shaped: the alert conditions below fire
on delivered-artifact integrity and on detector-arming state, not on CPU,
memory, or invocation counts.

---

## §1. Verified anchors (SVR)

All file:line anchors are read at `origin/main` unless stated. autom8y-asana
local `main` == `origin/main` == `13d43f09`; autom8y monorepo `origin/main` ==
`3dde20ef`. `terraform/services/asana/observability_alarms.tf` carries
uncommitted working-tree modifications — **every citation of that file in this
paper is to the `origin/main` version**, read via
`git show origin/main:terraform/services/asana/observability_alarms.tf`.

**SVR-1 — the swap signal is clause 4a and it requires BOTH hashes**

```yaml
structural_verification_receipt:
  claim: "the join emits CONTENT_HASH_MISMATCH only on the two-hash path; a delivery carrying no content_hash leaves the payload-identity clause unattested and the verdict falls through to the coarser block-count comparison"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/observability/rung_receipts/join.py"
    line_range: "L98-L128"
    marker_token: "Clause 4a -- content-hash swap detection. Fires ONLY when BOTH sides carry a"
    claim: "the detector's discriminating power is conditional on hash presence on both halves, which is exactly what R-3 must keep watch over"
```

**SVR-2 — the R-4 raw-JSON ingestion fence**

```yaml
structural_verification_receipt:
  claim: "ingestion for the continuous lane must be raw filter-log-events JSON; a Logs-Insights projection stringifies booleans and the receipt projection then misclassifies the occurrence"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/SURFACE-limb-a-live-realized-2026-08-15.md"
    line_range: "L81-L84"
    marker_token: "watch: hashed-vs-total `report_posted` deadman), **R-4** ingestion must"
    claim: "the fence is a standing residual of record, not an inference of this paper; the hazard site is the bool-coercion at schema.py:270"
```

Hazard site, plain anchor:
`src/autom8_asana/observability/rung_receipts/schema.py:270` —
`human_in_loop=bool(evt.get("human_in_loop", True)),`. Over an Insights
projection the JSON boolean `false` arrives as the string `"false"`, which is
truthy → `HUMAN_IN_LOOP` → `not_observable`. Fail-closed direction, **wrong
reason** — a corrupted instrument that still looks like it is working.

**SVR-3 — the delivery half omits the key, never nulls it**

```yaml
structural_verification_receipt:
  claim: "a delivery-side hash failure removes the content_hash key from the report_posted event rather than emitting a null, so a key-absence filter pattern is the shape-correct detector for the delivery-half de-arming"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y/services/account-status-recon/src/account_status_recon/orchestrator.py"
    line_range: "L1312-L1329"
    marker_token: "OMIT the key when unavailable -- never emit an explicit null"
    claim: "R-3's metric filter must test for key ABSENCE (NOT EXISTS), not for a null value; the emitter guarantees the absent shape"
```

**SVR-4 — the generation half fails CLOSED by emitting nothing**

```yaml
structural_verification_receipt:
  claim: "when the generation-side hash is unavailable the emitter returns before logging, so a generation-half de-arming produces NO report_generated event at all — invisible to any single-event presence filter"
  verification_method: bash-probe
  verification_anchor:
    source: "cd /Users/tomtenuta/Code/a8/a8/repos/autom8y && git show origin/main:services/account-status-recon/src/account_status_recon/payload_hash.py | sed -n '208,212p'"
    command_output_verbatim: "        content_hash = safe_content_hash(blocks, text, invocation_id=invocation_id)\n        if not content_hash:\n            return\n        log.info(\n            \"report_generated\","
    exit_code: 0
    claim: "the two halves de-arm in structurally different shapes (delivery = present-but-keyless, generation = absent), which is why R-3 needs two different detector shapes and why the generation half requires the join's denominator"
```

**SVR-5 — the SEV-1 dual-route paging idiom of record**

```yaml
structural_verification_receipt:
  claim: "the asana fleet's live SEV-1 paging leg puts BOTH the notify topic and the paging topic on BOTH alarm_actions and ok_actions, with the paging topic verified to carry live SMS and email subscribers"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/terraform/services/asana/story_warm_dead_alarm.tf"
    line_range: "L43-L51"
    marker_token: "action lists — platform-alerts (notify tier: Slack lambda + email) AND"
    claim: "R-2's paging leg inherits this exact wiring rather than inventing a route, so the recovery transition also reaches both tiers"
```

Resource-level anchors for the same idiom:
`terraform/services/asana/story_warm_dead_alarm.tf:98-105` (both action lists),
`:64-78` (both topic ARNs as variable defaults),
`:96` (`treat_missing_data = "breaching"` — dead-man semantics).

**SVR-6 — the AI-6 design-around already exists in-tree**

```yaml
structural_verification_receipt:
  claim: "the monorepo ASR terraform already carries an UNGATED, notBreaching dead-man authored specifically to sidestep the schedules_enabled count-gate hazard that kills the success-keyed detector with the schedule"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y/terraform/services/account-status-recon/source_coverage_deadman.tf"
    line_range: "L34-L42"
    marker_token: "the AI-6 \"detector dies with the schedule\" hazard the success_deadman must live with"
    claim: "R-3 inherits this shape verbatim rather than the count-coupled shape, so a bare-apply flip of schedules_enabled cannot destroy the hash-presence detector"
```

The AI-6 incident of record:
`terraform/services/account-status-recon/variables.tf:207-213` — a bare deploy
apply resolved `schedules_enabled=false` from the variable default and
*"silently set the EventBridge rule ENABLED->DISABLED and DESTROYED the
success-deadman (count-coupled in success_deadman.tf)"*.

**SVR-7 — monorepo terraform applies are operator-gated**

```yaml
structural_verification_receipt:
  claim: "the monorepo service terraform workflow has no automatic apply path: pull requests and pushes to main run plan only, and every apply is a human-initiated workflow_dispatch naming the service"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y/.github/workflows/service-terraform.yml"
    line_range: "L6-L18"
    marker_token: "Runs plan ONLY (drift visibility; applies never auto-fire)"
    claim: "the R-3 apply step is honestly an operator action, not a merge side-effect; a merged PR leaves the detector authored-but-absent until a human dispatches"
```

**SVR-8 — the asana tf tree has no apply pipeline at all (CLI code-of-record)**

```yaml
structural_verification_receipt:
  claim: "the autom8y-asana terraform tree is applied by hand from the CLI and the committed HCL is a code-of-record that a later import adopts, which is the posture the story-warm SEV-1 alarm shipped under"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/terraform/services/asana/story_warm_dead_alarm.tf"
    line_range: "L53-L61"
    marker_token: "CODE-OF-RECORD, CLI-applied (the F-1 pattern — this tf tree has no"
    claim: "R-2's alarms land in the same posture — HCL merged, resource created by an operator-run CLI command, terraform import deferred to whenever an apply path lands"
```

**SVR-9 — the proof-clone precedent (paging-safe two-sided proof)**

```yaml
structural_verification_receipt:
  claim: "the monorepo carries a disposable, identically-keyed alarm clone with deliberately empty action lists whose state transitions are read from describe-alarm-history rather than delivered to a real channel"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y/terraform/services/account-status-recon/success_deadman.tf"
    line_range: "L38-L45"
    marker_token: "the clone MUST NOT page the real trained-ignore channel during"
    claim: "both proof plans below adopt the clone pattern so the RED leg can be exercised without firing a real pager, and both carry the clone-absence probe that closes the disposable apparatus"
```

Clone-absence probe of record: `success_deadman.tf:64-67` (predicate P10 —
`describe-alarms --alarm-name-prefix ...-proof` must return ZERO at ruling
time) and the plan-time `check` block at `:269-285`.

**SVR-10 — the R-2 lane's host pattern and its named honest limit**

```yaml
structural_verification_receipt:
  claim: "the asana repo already runs a scheduled AWS-touching workflow using OIDC plus a secrets-manager credential bridge, and its header names a CloudWatch-side dead-man on the workflow's own green heartbeat as the durable fix for the failure class that in-job paging structurally cannot cover"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.github/workflows/nightly-live-smoke.yml"
    line_range: "L64-L72"
    marker_token: "CloudWatch-side dead-man on this workflow's green heartbeat, not more"
    claim: "R-2's lane-liveness alarm SD-2 is not a new invention; it discharges a residual this repo already named and owned to the sre lane"
```

Host-pattern anchors reused verbatim by R-2:
`nightly-live-smoke.yml:113-121` (OIDC assume-role),
`:122-145` (cred-bridge via `autom8_env`),
`:257-277` (page-on-red SNS publish),
`:223-255` (anti-theater assertion: a silently-skipping scheduled job FAILS).

**SVR-11 — the receipt schema is closed**

```yaml
structural_verification_receipt:
  claim: "the RUNG-E receipt JSON schema forbids additional properties, so adding a first-class clause-4a-attested field to the receipt is a schema-surface change and not a free annotation"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/observability/rung_receipts/schema.py"
    line_range: "L492-L495"
    marker_token: "There is deliberately NO combined/engagement/total property: such a field"
    claim: "the recommended first-cut R-2 build reads existing receipt fields and adds nothing to the schema; the first-class field is named as a follow-on hardening with its own schema change"
```

**Working-tree/origin discipline note.** `terraform/services/asana/observability_alarms.tf`
is `M` in the working tree (`git status --porcelain` → ` M terraform/services/asana/observability_alarms.tf`).
This paper cites only the origin version. The binding-blind cure surfaces cited
below (`alarm_binding_report` output, `require_alarm_binding` precondition,
`ticket_sns_topic_arn` BINDING-BLIND WARNING) are all present at origin.

---

## §2. R-2 — the continuous-detection lane

### 2.1 What must become true

> A `content_hash_mismatch` on any production ASR tick reaches a human within
> one detection interval, without a human having chosen to look.

### 2.2 Option slate

| # | Option | Verdict | Rationale |
|---|---|---|---|
| **M-1** | **Scheduled GitHub Actions job in `autom8y-asana` that runs the canonical join over raw `filter-log-events` JSON and publishes CloudWatch metrics; alarms page from CloudWatch** | **CHOSEN** | The join stays where it is — zero duplication (ADR one-canonicalization). Ingestion is raw JSON by construction (R-4 fence honoured). The repo already runs exactly this shape of job (`nightly-live-smoke.yml`) with a proven OIDC + cred-bridge + page-on-red spine. Paging goes through CloudWatch→SNS, matching the StoryWarm idiom, so the alert is a *condition* with hysteresis, not a one-shot CI notification. |
| M-2 | Small scheduled Lambda in the monorepo running the join | REJECTED | Requires the asana join to be packaged into the monorepo (duplication — the exact thing `ADR-asr-content-hash-canonicalization-2026-08-14.md` option (iv) refused) **or** a cross-repo dependency edge. The ADR's own reasoning applies with the arrow reversed: a dependency edge *"would invert the direction and put the observer in this Lambda's deploy path"* (PR #1636 body). An observer that ships with the observed is not an observer. |
| M-3 | Extend an existing scheduled surface — the nightly live smoke, or an asana ECS/Lambda job | REJECTED as primary, retained as fallback | Cheapest by line count, but (a) nightly cadence is 1/day against a 6/day emitter → up to 24h detection latency; (b) it couples the swap detector's liveness to the smoke lane's health — the lane that ran 60 nights red unpaged (`nightly-live-smoke.yml:29-31`). A detector that dies when its host suite goes red is the AI-6 hazard in a different costume. Keep as the degraded fallback if a new workflow is refused. |
| M-4 | CloudWatch Logs Insights scheduled query, or a metric filter, detecting mismatch directly in logs | REJECTED | Structurally impossible without re-implementing the join: the mismatch is a **join across two events on `invocation_id`**, and no metric filter joins. An Insights `stats by invocation_id` formulation would (a) duplicate clause 4a in Insights QL — one-canonicalization breach, and (b) run over Insights projections — R-4 breach (SVR-2). Both fences broken for a strictly weaker detector. |
| M-5 | Real-time CloudWatch Logs subscription filter → Lambda → join | REJECTED | Same duplication problem as M-2, plus a per-event streaming design for a 6-events/day signal. The generation and delivery halves arrive ~130ms apart (`SURFACE-limb-a-live-realized-2026-08-15.md:51`) but nothing guarantees ordering or single-batch delivery; a windowed batch is simpler and strictly more robust. Latency gain is irrelevant against a 4h emitter cadence. |

### 2.3 Chosen mechanism — the sweep lane

**Cadence.** `cron: '35 1,5,9,13,17,21 * * *'` — every 4h, 95 minutes after each
ASR tick (ASR fires `cron(0 */4 * * ? *)`; observed ticks land at `:01`,
`SURFACE-limb-a-live-realized-2026-08-15.md:47-48`). The `:35` offset dodges the
busy `:00` runner-contention slot, mirroring `nightly-live-smoke.yml:78-79`, and
gives ~95 min of slack for GitHub Actions schedule drift.

**Window.** 24h lookback on every sweep. Deliberately overlapping: each tick is
evaluated ~6 times. Consequences, stated rather than discovered later:
* a mismatch remains visible for 24h after the offending tick, then auto-clears
  — free hysteresis, and the alarm returns to OK without human action;
* metrics are **window levels, not rates**, so every alarm below reads them with
  `Maximum`, never `Sum` (a `Sum` would multiply overlapping windows).

**Ingestion (R-4 fence, load-bearing).**

```
aws logs filter-log-events \
  --log-group-name /aws/lambda/autom8y-account-status-recon \
  --start-time <now-24h ms> --end-time <now ms> \
  --filter-pattern '{ ($.event = "report_posted") || ($.event = "report_generated") }' \
  --output json   # paginate on nextToken
| jq -r '.events[].message'   # raw JSON lines, one per event
| python -m autom8_asana.observability.rung_receipts.query -
```

`filter-log-events` returns the **raw `message` string** — the event exactly as
the emitter wrote it. `jq -r` emits it unchanged; `query.main` reads JSONL from
stdin (`src/autom8_asana/observability/rung_receipts/query.py:74-84`). Booleans
stay booleans. **`aws logs start-query` (Insights) is FORBIDDEN in this lane**,
and the constants `DELIVERY_LOGS_INSIGHTS_QUERY` /
`GENERATION_LOGS_INSIGHTS_QUERY` (`schema.py:376-388`) must not be used to feed
it — using them naively reproduces the R-4 defect (SVR-2).

**Ingestion-integrity guard (discriminates "detector broken" from "ASR quiet").**
An empty match set has two very different causes. The sweep runs a second,
unfiltered probe over the same window and branches:

| matched events | total events in window | Meaning | Lane behaviour |
|---|---|---|---|
| 0 | 0 | ASR emitted nothing — outage | publish zeroes, **do not fail**; the ASR liveness dead-man (`terraform/services/account-status-recon/main.tf:360-367`) and `reconciliation_success_deadman` own this |
| 0 | > 0 | log shape changed / pattern no longer matches — **the detector is broken** | **hard-fail the job** → page-on-red |
| > 0 | > 0 | healthy | publish real values |

Without this branch, a log-format change renders the lane permanently, silently
green — the vacuous-green failure mode that makes a detector worse than none.

**Published metrics.** Namespace `Autom8y/AsanaRungReceipts`, dimensions
`{ lane = "swap-detector", source = "asr", environment = "production" }`
(minimum label set: service, environment, surface — per the missing-context
anti-pattern).

| Metric | Meaning | Derived from |
|---|---|---|
| `SwapDetectorMismatch` | occurrences with `rung_e_not_observable_reason == "content_hash_mismatch"` | receipt verdict, verbatim — **the join decides, the lane counts** |
| `SwapDetectorHashAttested` | occurrences that are `observable` **and** carry a `content_hash` on both halves | presence read of two receipt fields; no equality re-derivation (equality is already implied by `observable`, `join.py:100-108`) |
| `SwapDetectorDeliveries` | total delivery occurrences in window — **the denominator** | `receipts | length` |
| `SwapSweepHeartbeat` | `1` on every completed sweep | lane liveness |

One-canonicalization boundary, stated explicitly: the lane **never re-decides**
anything. `SwapDetectorMismatch` is a count of a verdict the canonical join
emitted. `SwapDetectorHashAttested` is a presence read of fields the canonical
receipt already carries. No clause of the join is restated in bash, jq, HCL, or
Insights QL anywhere in this design.

*Follow-on hardening (named, not required for the first cut):* add a
first-class `clause_4a_attested: bool` to `DeliveryOccurrenceReceipt` so the
lane reads one field instead of two. That is a **schema-surface change** —
`RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA` sets `additionalProperties: False`
(SVR-11) — so it must land with its JSON-schema update and its own tests. Do
not smuggle it into the first cut.

### 2.4 Files and resources to touch

| Repo | Path | Action | Note |
|---|---|---|---|
| autom8y-asana | `.github/workflows/swap-detector-sweep.yml` | **NEW** (~130 lines) | Modeled line-for-line on `nightly-live-smoke.yml`: OIDC `:113-121`, cred-bridge `:122-145`, CodeArtifact + uv install `:147-191`, page-on-red `:257-277`. Add `workflow_dispatch` so the proof legs are runnable on demand. |
| autom8y-asana | `scripts/swap_detector_sweep.sh` | **NEW** (~90 lines) | The sweep itself, so it is runnable by hand for the proof legs and not trapped inside YAML. `scripts/` exists and carries executable helpers (`scripts/entrypoint.sh`, `scripts/aegis-check.py`). |
| autom8y-asana | `terraform/services/asana/swap_detector_alarms.tf` | **NEW** (~170 lines) | SD-1 / SD-2 / SD-3 + the disposable proof clones. Additive file; **does not touch** `observability_alarms.tf` (which is dirty in the working tree) or `story_warm_dead_alarm.tf`. |
| autom8y-asana | `src/autom8_asana/observability/rung_receipts/**` | **NO CHANGE** | Fence. The lane composes the module; it does not modify it. |
| autom8y | anything | **NO CHANGE** | R-2 touches the monorepo not at all — read-only log access only. |

### 2.5 Alarms and the paging leg

All three inherit the dual-route wiring verbatim from
`story_warm_dead_alarm.tf:43-51,98-105` (SVR-5): notify topic
`arn:aws:sns:us-east-1:696318035277:autom8y-platform-alerts`, paging topic
`arn:aws:sns:us-east-1:696318035277:autom8y-platform-sre-sev1`, both topics on
**both** action lists so recovery notifies both tiers. AlarmNames follow the
fleet SEV-1 contract `autom8y-<service>-<class>`
(`story_warm_dead_alarm.tf:47-49`).

**SD-1 — `autom8y-asana-swap-detector-mismatch` — PAGE (SEV-1)**

| Field | Value | Why |
|---|---|---|
| metric | `SwapDetectorMismatch` | the delivered artifact is not the generated one |
| statistic | `Maximum` | window level, not rate (overlapping 24h lookbacks) |
| comparison / threshold | `GreaterThanThreshold` / `0` | baseline is a **hard zero**: across all pairs since arming, zero mismatches; before arming, zero pairs existed at all. This is *not* the StoryWarmFailure situation (`story_warm_dead_alarm.tf:13-16`: routinely nonzero, so `>0` would hold ~60% alarm duty). Here `>0` never fires on healthy traffic. |
| period / eval / datapoints | `14400` / `1` / `1` | one sweep interval; a mismatch is never a transient to be smoothed |
| treat_missing_data | `notBreaching` | absence = lane dark or ASR quiet — owned by SD-2 and by the ASR liveness dead-man, not by this alarm |
| actions | notify + page, both lists | SEV-1: a swapped payload reached a customer-facing channel |
| runbook | `RUNBOOK-platform-sre-sev1-paging-response.md` (autom8y `docs/reliability/runbooks/`, verified present) + a new `RUNBOOK-asana-swap-detector-mismatch.md` | every page needs a runbook or it does not ship |

**Known false-positive class, designed for rather than discovered.** A mismatch
can also arise from a *canonicalization split* rather than a swap. Today both
hashes come from one ASR-internal function, so a split is impossible within a
deploy — but the ADR's `(iv)→(iii)` migration trip-wire
(`ADR-asr-content-hash-canonicalization-2026-08-14.md:108-125`, trigger =
REC-004) is precisely the event that makes a cross-repo digest split possible,
and it would present as a **mismatch storm**. Mitigations, both required:
1. the alarm description names it, so the pager text itself carries the
   discriminator;
2. the runbook's **first** triage step is *"did an ASR deploy or REC-004 land in
   the last 24h?"* before *"was a payload swapped?"*.

**SD-2 — `autom8y-asana-swap-sweep-dead` — NOTIFY**

Dead-man on the lane itself: `Sum(SwapSweepHeartbeat) <= 0`, period `28800`
(8h — spans **two** sweep slots, the anchor-drift discipline from
`story_warm_dead_alarm.tf:24-27` and the AL-5 scar), `2`-of-`2`,
`treat_missing_data = "breaching"` (silence IS the signal). Notify tier only:
a dead detector has no customer impact at the moment it dies, and paging on it
would be cause-based. It is nonetheless mandatory — without SD-2, R-2 recreates
R-2 one level up (an unwatched watcher).

SD-2 covers the failure class the in-job page-on-red structurally **cannot**:
a workflow that never starts has no step to run (`nightly-live-smoke.yml:68-72`,
SVR-10). The two are complementary, not redundant: page-on-red catches loud
failures, SD-2 catches silent non-execution.

**SD-3 — `autom8y-asana-swap-detector-unarmed` — NOTIFY (this is R-3's second leg; see §3.6)**

Metric math with an explicit denominator guard:

```
IF(m_deliveries > 0, m_deliveries - m_attested, 0)
```
`m_deliveries` = `Maximum(SwapDetectorDeliveries)`, `m_attested` =
`Maximum(SwapDetectorHashAttested)`. Threshold `> 0`, period `21600` (6h,
≥1 sweep), `2`-of-`2` (~12h sustained), `treat_missing_data = "notBreaching"`.

The `IF` guard is what makes this AI-6-safe: when the lane is dark or ASR is
quiet, the denominator is 0, the expression yields 0, and the alarm stays quiet
— it cannot inherit someone else's outage. It fires only on the honest
condition *"deliveries happened and the payload-identity clause did not run on
them."* This is the **only** leg that sees a generation-half de-arming (SVR-4:
that half vanishes rather than degrading, so no single-event filter can see it).

### 2.6 Two-sided proof plan (discriminating, input-only, no defect injection)

Every RED below is a **deliberately-broken INPUT that the live surface correctly
rejects**, never a defect injected into working code. This is the same method
the A-3 adjudication used and that qa adjudicated GO
(`SURFACE-limb-a-live-realized-2026-08-15.md:57-59`: *"input-only tamper on a
scratch copy → `not_observable / content_hash_mismatch` while the honest pair
stays observable in the same run"*).

**P2-1 — GREEN, and non-vacuously so.** Run the sweep by hand against the live
24h window. PASS requires **all** of:
* `SwapDetectorMismatch == 0`,
* `SwapDetectorDeliveries >= 5` (≥6/day cadence minus one tick of slack),
* **`SwapDetectorHashAttested >= 5`**.

The third assertion is the discriminator and is not optional: an empty window,
a broken pattern, and a de-armed emitter all produce `mismatch == 0` too.
"Quiet" only counts as evidence when the lane can show it was *looking at armed
pairs*.

**P2-2 — RED, input-only.** Copy the exact JSONL corpus from P2-1 to a scratch
file. Alter **one** hex character of **one** delivery's `content_hash` value.
Re-run the identical, unmodified sweep. PASS requires: that occurrence reports
`content_hash_mismatch`, every other occurrence in the same run stays
`observable`, and `SwapDetectorMismatch == 1`. Single variable: the input. No
source file is edited; the scratch copy is deleted at the end of the leg.

**P2-3 — the alarm actually transitions.** Publish P2-1's and P2-2's values to a
**proof dimension** (`lane = "swap-detector-proof"`) so the production series
stays clean, against disposable proof-clone alarms with **empty action lists**
(`success_deadman.tf:180-236`, SVR-9). Observe both transitions with
`aws cloudwatch describe-alarm-history`: OK on the P2-1 values, ALARM on the
P2-2 values. No pager is touched by this leg.

**P2-4 — SD-2 two-sided, in ~20 minutes not 16 hours.** A proof-clone of SD-2
keyed on the proof dimension with `period 300`, `2`-of-`2`: publish nothing →
ALARM (real absence, not injected); publish one heartbeat → OK. Real absence is
the honest RED for a dead-man.

**P2-5 — alarm-to-human, the DoD leg.** `SCAR-ALARM-BINDING-001`
(`.know/scar-tissue.md:85`) is explicit: *"an alarm is not DONE at resource
creation — its definition-of-done includes one receipted end-to-end fire
(signal → alarm → action → human surface)."* On the **real** SD-1, an operator
runs `aws cloudwatch set-alarm-state --state-value ALARM`, captures the pager
receipt (SMS/email arrival + `describe-alarm-history`), then resets to `OK`.
This is exactly the StoryWarm precedent (`story_warm_dead_alarm.tf:55-58`:
*"synthetic ALARM transition fired to the pager and reset the same day"*).
**Until this leg is receipted, R-2 is `authored`, not `alerting`.**

**P2-6 — binding non-blindness.** Before declaring done, assert every new alarm
resolves to a non-empty action list. The origin module's
`alarm_binding_report` output renders `"UNBOUND -- detects and notifies NOBODY"`
for any unbound alarm (`observability_alarms.tf` binding-report output block @
`origin/main`); the new file should either extend that report or carry its own
`require_alarm_binding`-style precondition. Seven of twenty live `asana-*`
alarms were measured unbound on 2026-08-11, all seven from this module
(`.know/scar-tissue.md:81`) — this is a repeat-offender surface.

**P2-7 — clone teardown.** `aws cloudwatch describe-alarms --alarm-name-prefix
autom8y-asana-swap-detector-proof` returns **zero** alarms at close. The P10
discipline (`success_deadman.tf:64-67`).

### 2.7 Operator-gated steps (explicit)

| # | Step | Who | Command / action |
|---|---|---|---|
| O2-1 | Merge the workflow + script + HCL | normal PR review | no AWS effect |
| O2-2 | **IAM discharge** — the CI principal must hold `logs:FilterLogEvents` on `/aws/lambda/autom8y-account-status-recon` and `cloudwatch:PutMetricData` | platform-engineer | probe first (§2.9 UV-P-R2-1); if absent, an IAM change is required before the lane can run |
| O2-3 | **Create the alarms** (asana tf tree has no apply pipeline — SVR-8) | operator | `aws cloudwatch put-metric-alarm ...` byte-matched to the HCL, per the story-warm F-1 pattern (`story_warm_dead_alarm.tf:53-58`); `terraform import` deferred until an apply path exists |
| O2-4 | **Receipted end-to-end fire on SD-1** (P2-5) | operator | `aws cloudwatch set-alarm-state` → capture pager receipt → reset |
| O2-5 | Destroy the proof clones + P10 probe (P2-7) | operator | `delete-alarms` then `describe-alarms --alarm-name-prefix` |
| O2-6 | Author `RUNBOOK-asana-swap-detector-mismatch.md` | sre | must exist **before** SD-1 is armed to page |

### 2.8 Sizing

| Item | Estimate |
|---|---|
| `swap-detector-sweep.yml` (fork of a proven workflow) | 0.5 d |
| `scripts/swap_detector_sweep.sh` incl. pagination + ingestion-integrity guard | 0.5 d |
| `swap_detector_alarms.tf` (3 alarms + 2 proof clones) | 0.5 d |
| Proof legs P2-1..P2-7 | 0.5 d |
| Runbook | 0.25 d |
| IAM discharge (if a grant is needed) | 0 – 1 d, platform-engineer |
| **Total** | **~2.25 – 3.25 engineering-days + 3 operator gates** |

### 2.9 UV-P ledger for R-2

`[UV-P: the CI principal (OIDC github-actions-deploy, or the autom8_env bridged pair) holds logs:FilterLogEvents on /aws/lambda/autom8y-account-status-recon and cloudwatch:PutMetricData | METHOD: deferred-to-build-probe — one workflow_dispatch dry run executing filter-log-events --limit 1 and put-metric-data to a scratch namespace | REASON: the nightly lane's verified grants are S3/secretsmanager/codeartifact-scoped (nightly-live-smoke.yml:50-57); no logs or cloudwatch grant has been observed on either principal and this paper performed no live AWS probe]`

`[UV-P: CloudWatch metric math evaluates IF(m_deliveries > 0, m_deliveries - m_attested, 0) and yields no datapoint rather than an error when the referenced series are absent | METHOD: deferred-to-build-probe — read-only `aws cloudwatch get-metric-data` with the exact expression over a window containing and a window not containing the series | REASON: SD-3's AI-6 safety rests entirely on this evaluation behaviour; it must be observed before the alarm is authored, not assumed]`

`[UV-P: GitHub Actions schedule drift on this repo stays inside the 95-minute offset budget | METHOD: deferred-to-first-week-observation of swap-detector-sweep run start times | REASON: schedule drift is an empirical property of runner contention; the 95-min offset is a design margin, not a measurement]`

---

## §3. R-3 — the hash-presence deadman

### 3.1 What must become true

> If `report_posted` stops carrying `content_hash`, a human is told — even
> though the join keeps reporting `observable` via the 4b block-count fallback,
> and even though nothing else in the system looks wrong.

### 3.2 Option slate

| # | Option | Verdict | Rationale |
|---|---|---|---|
| **D-1** | **Metric filter counting `report_posted` events with `content_hash` ABSENT; alarm on that count `> 0`** (present-0 trips, absence tolerated) | **CHOSEN — leg 1** | Structurally AI-6-immune: the only absence class is "ASR posted nothing", which is `notBreaching` and belongs to the sibling dead-men. A hashless delivery is a **present, nonzero datapoint** → trips. This is the `source_coverage_3of3_deadman` shape verbatim (SVR-6). It is also shape-correct for the emitter: the key is omitted, never nulled (SVR-3). |
| **D-2** | **Ratio alarm `hashed / total < 1` via metric math** (the framing in the R-3 proposal) | REJECTED as leg 1, **re-admitted as SD-3 in a safe form** | Three problems as stated. (a) The denominator is 0 whenever the schedule is off; a naive ratio yields no datapoint and the alarm's behaviour then depends entirely on `treat_missing_data` — re-coupling the detector to the schedule, which is the AI-6 hazard (SVR-6). (b) A ratio needs both filters anyway, so it costs strictly more than D-1 for the same delivery-half detection. (c) Denominator-integrity: a ratio hides the absolute count — "0.83" does not say whether one tick or a thousand went blind. **The legitimate residue** of D-2 — the generation-half absence, which no single-event filter can see (SVR-4) — is served by SD-3 (§2.5), where the join supplies a real denominator and `IF()` supplies the guard. |
| D-3 | Absence alarm: `Sum(HashedReportPosted) <= 0` with `treat_missing_data = "breaching"` | REJECTED | This is exactly the count-coupled/breaching shape that AI-6 names. It fires on every schedule-off window, duplicating `reconciliation_success_deadman` and the liveness dead-man, and would need `count = var.schedules_enabled` gating — which is *the hazard itself* (`variables.tf:207-213`: a bare apply destroyed the count-coupled success-deadman). |
| D-4 | Emitter-side self-check: ASR publishes a `HashPresent` CloudWatch metric directly | REJECTED | Requires editing the freshly-armed emitter, adding deploy risk to the exact code path under observation, and putting the observer inside the observed Lambda's deploy path — the same inversion the ADR refused. A metric filter is read-only on the log stream and cannot regress the emitter. |
| D-5 | Author the deadman in the asana tf tree alongside AL-1..AL-6 | REJECTED, with the counter acknowledged | The counter is real: asana's AL-2 already alarms on the ASR Lambda (`observability_alarms.tf` AL-2 block, `recon_function_name = "autom8y-account-status-recon"`). But the log group is monorepo-owned, the ASR tf tree already holds three sibling dead-men on this exact service (`success_deadman.tf`, `source_coverage_deadman.tf`, `completion_event_deadman.tf`), and splitting a service's detector suite across two repos multiplies the surfaces an oncall must know. Locality wins; the split is noted so a future consolidation has the reasoning. |

### 3.3 Chosen mechanism — leg 1 (monorepo, log-native, lane-independent)

**Why lane-independent matters:** R-3 must not depend on the R-2 lane, or a
dead lane hides a de-armed emitter and both gaps return together. Leg 1 reads
the log group directly, so it survives R-2 being broken, unbuilt, or unarmed.

**Metric filter** — `aws_cloudwatch_log_metric_filter.report_posted_hashless`

```hcl
log_group_name = "/aws/lambda/autom8y-account-status-recon"
pattern        = "{ ($.event = \"report_posted\") && ($.content_hash NOT EXISTS) }"

metric_transformation {
  name          = "ReportPostedHashless"
  namespace     = "Autom8y/Reconciliation"
  value         = "1"
  default_value = 0          # present-0 on every matching-window evaluation
  dimensions    = { Service = "account-status-recon" }
}
```

`NOT EXISTS` is the correct predicate precisely because of SVR-3: on a
fail-open the emitter **omits the key**. So this one filter catches both
de-arming shapes on the delivery half — a version rollback past `3dde20ef`
(H-2) *and* a `safe_content_hash` fail-open — without a second surface.

**Alarm** — `autom8y-account-status-recon-report-posted-hashless`

| Field | Value | Derivation |
|---|---|---|
| statistic | `Sum` | a count of blind deliveries in the bucket |
| comparison / threshold | `GreaterThanThreshold` / `0` | any blind delivery is a real loss of payload-identity verification |
| period | `28800` (8h) | ASR fires 6/day at 4h spacing; an 8h bucket spans **two** ticks, so a single missed/shifted tick can never empty a bucket — the anchor-drift discipline from `story_warm_dead_alarm.tf:24-27` and the AL-5 scar |
| evaluation_periods / datapoints_to_alarm | `2` / `2` | requires the condition to persist across two buckets: a **one-off** fail-open (a single hashing exception) cannot page; a **regression** (every tick hashless) pages within 8–16h |
| treat_missing_data | `notBreaching` | absence = no deliveries at all = schedule-off/dry-run, owned by `reconciliation_success_deadman` and the liveness dead-man. **This is the AI-6 design-around** (SVR-6) |
| count gate | **NONE** — resource is UNGATED | a bare deploy apply resolving `schedules_enabled=false` from the variable default must not be able to destroy this detector (`variables.tf:207-213`) |
| actions | notify + page (dual-route) | see §3.5 |

**Detection latency: 8–16h.** Against an otherwise *unbounded* blind window
that is an acceptable trade, and SD-3 (§2.5) independently corroborates the
same regression in ~4–12h once R-2 exists. The two lanes are complementary in
latency as well as in coverage.

**What leg 1 deliberately does NOT do:** it does not compare hashes, does not
key on `invocation_id`, and does not join anything. It is a **presence** check.
The join's clause 4a is not restated anywhere in HCL — the one-canonicalization
fence holds (`ADR-asr-content-hash-canonicalization-2026-08-14.md`).

**Rejected companion, named so it is not silently forgotten:** a second filter
counting `report_generated` with a metric-math difference `IF(m_posted > 0,
m_posted - m_generated, 0)` would give the monorepo a generation-half signal
too. **DEFERRED**, because `report_generated` fires at all three assembly sites
(PR #1636 body) and nothing guarantees exactly one per invocation, so the count
difference is legitimately noisy — and SD-3 does the same job precisely with
per-`invocation_id` receipts. Adding both would be alert sprawl for a strictly
worse signal.

### 3.4 Files and resources to touch

| Repo | Path | Action | Note |
|---|---|---|---|
| autom8y | `terraform/services/account-status-recon/hash_presence_deadman.tf` | **NEW** (~130 lines) | **ADDITIVE ONLY**, matching the sibling naming and the scope fence at `success_deadman.tf:47-52`: no edits to `main.tf` / `variables.tf` / `outputs.tf`. Contains: 1 metric filter, 1 alarm, 1 disposable proof clone (empty actions), 1 output. |
| autom8y | `docs/reliability/runbooks/RUNBOOK-account-status-recon-hash-presence.md` | **NEW** | Or an appended section in the existing `RUNBOOK-account-status-recon-freshness.md` (verified present), which the sibling dead-men already point at. |
| autom8y | ASR service source | **NO CHANGE** | The detector is read-only on the log stream (D-4 rejected). |
| autom8y-asana | anything | **NO CHANGE** | R-3 leg 1 is entirely monorepo-side. Leg 2 is SD-3, already scoped under R-2. |

### 3.5 Paging leg

The ASR tf tree's three existing dead-men all route **notify-tier only**
(`platform_alerts_topic_arn`, e.g. `success_deadman.tf:152-153`,
`source_coverage_deadman.tf` action block). R-3 asks for a page, so the paging
topic must be introduced to this tree.

**Recommendation:** dual-route exactly as `story_warm_dead_alarm.tf:98-105`
(SVR-5) — `platform_alerts_topic_arn` (from
`data.terraform_remote_state.shared.outputs`, the tree's existing idiom) **plus**
`arn:aws:sns:us-east-1:696318035277:autom8y-platform-sre-sev1`, both on
`alarm_actions` and `ok_actions`.

**Justification for SEV-1 rather than notify:** a silently de-armed detector is
the condition under which a swap reaches a customer channel *undetected*. It is
the meta-failure the whole chain-of-custody arc exists to prevent, and it has
no other tripwire. It also has a hard-zero baseline (see the replay in P3-2
below), so it cannot become an alert-fatigue source.

**Honest caveat, to be stated in the alarm description:** the SEV-1 topic's
live SMS + email subscribers were verified 2026-08-14
(`story_warm_dead_alarm.tf:70-78`); this paper did not re-probe them.
Re-verification is part of O3-4.

**Runbook** (must exist before arming): first triage step is
*"`git log` the ASR image: did `image_tag`
(`terraform/services/account-status-recon/environments/production.tfvars:30`,
currently `c21cab9`) roll back past `3dde20ef`?"* — that is H-2, the highest-prior
cause.

### 3.6 R-3's second leg

Leg 2 is **SD-3** (`autom8y-asana-swap-detector-unarmed`, §2.5). It is listed
under R-2 because it is built from the R-2 lane's metrics, but it discharges an
R-3 obligation: the **generation-half** de-arming, which vanishes rather than
degrading (SVR-4) and is therefore invisible to leg 1's presence filter.

| De-arming shape | Detected by | Independent of R-2 lane? |
|---|---|---|
| delivery half loses `content_hash` (rollback past `3dde20ef`, or `safe_content_hash` fail-open) | **leg 1** (monorepo filter) | **yes** |
| generation half stops emitting `report_generated` entirely | **SD-3** (asana lane) | no — requires R-2 |
| ASR stops delivering at all | `reconciliation_success_deadman`, `service_liveness` (`main.tf:360-367`) | yes |
| delivered payload ≠ generated payload | **SD-1** (asana lane) | no — requires R-2 |

Non-substitution, stated: **no row substitutes for another.** Leg 1 green does
not mean the instrument is armed (the generation half could be dark). SD-3
green does not mean deliveries are hashed (the lane could be reading a stale
window). Both green plus SD-1 quiet plus a nonzero attested count is the full
statement.

### 3.7 Two-sided proof plan (discriminating, input-only, no defect injection)

**P3-1 — pattern discrimination against REAL log lines, before any apply.**

```
aws logs test-metric-filter \
  --filter-pattern '{ ($.event = "report_posted") && ($.content_hash NOT EXISTS) }' \
  --log-event-messages '<a REAL pre-arm report_posted line>' '<a REAL post-arm report_posted line>'
```

* RED input: a genuinely hashless production line from the pre-arming window.
  These exist and are counted: *"0/12 `content_hash` on pre-arm deliveries
  (2026-08-13 through 2026-08-14T20:10Z)"*
  (`SURFACE-limb-a-live-realized-2026-08-15.md:60-62`).
* GREEN input: a real armed line from the first post-deploy tick,
  `invocation_id 0012255b-532f-4b86-bfa5-37b89d5bf2da` @ 2026-08-15T00:01Z
  (`SURFACE-limb-a-live-realized-2026-08-15.md:47-51`).

PASS = exactly **one** match, and it is the pre-arm line. This is the ideal
discriminating fixture: **both inputs are real production bytes**, nothing is
fabricated, no code is broken, and the API is read-only. It simultaneously
discharges the `NOT EXISTS` premise (UV-P-R3-1) and the JSON-parseability
premise (UV-P-R3-2).

> ⏳ **TIME-BOXED PROOF ASSET — act before it expires.** ASR log retention is
> 30 days (`terraform/services/account-status-recon/variables.tf:43-47`,
> `log_retention_days` default `30`, not overridden in
> `environments/production.tfvars`). The pre-arm hashless lines date from
> 2026-08-13/14, so they age out around **2026-09-12**. After that the RED
> input can only be synthesized, which is strictly weaker evidence.
> **Recommendation: capture two real lines to a committed fixture file now**,
> as part of this design's follow-through, independent of when the build runs.
> A captured real line is an *input*, not a defect — the fence holds.

**P3-2 — historical replay, both sides, read-only.** Same pattern via
`aws logs filter-log-events --filter-pattern ... --start-time/--end-time`:

| Window | Expectation | Meaning |
|---|---|---|
| 2026-08-13T00:00Z → 2026-08-14T20:10Z (pre-arm) | **≥ 12 matches** | would-have-paged: the alarm demonstrably fires on the real historical de-armed state |
| 2026-08-15T00:00Z → now (post-arm) | **0 matches** | quiet on healthy |
| post-arm window, pattern `{ ($.event = "report_posted") }` | **≥ 6/day** | **non-vacuity control** — proves the zero above means "all hashed", not "no deliveries" |

The third row is not optional. Without it, a broken pattern and a healthy
emitter are indistinguishable. This is the StoryWarm replay discipline
(`story_warm_dead_alarm.tf:26-31`: *"7-day replay... ZERO zero-valued buckets...
exactly ONE would-have-paged event"*) applied to a presence signal.

**P3-3 — alarm transition on the proof clone.** Author the disposable clone
(identical filter/metric/thresholds, **empty** action lists, gated on a
throwaway `hash_presence_proof_enabled` defaulting `false` —
`success_deadman.tf:76-97,180-236`). Because the pre-arm datapoints are
historically present, CloudWatch evaluates existing datapoints at creation; if
the metric filter's backfill window still holds them the clone transitions
immediately — the `source_coverage_deadman.tf:26-32` "immediate honest RED on
deploy is the proof" phenomenon. **Caveat to verify, not assume:** metric
filters only produce datapoints for events ingested *after* filter creation, so
the historical RED may not materialize as metric data. If it does not, the RED
is instead demonstrated by P3-1 + P3-2 (pattern-level, which is where the
discrimination actually lives) plus P3-4.

**P3-4 — alarm-to-human, the DoD leg.** On the **real** alarm:
`aws cloudwatch set-alarm-state --state-value ALARM`, capture the pager receipt
(SMS/email + `describe-alarm-history`), reset to `OK`. Required by
`SCAR-ALARM-BINDING-001` (`.know/scar-tissue.md:85`) and precedented by
StoryWarm (`story_warm_dead_alarm.tf:55-58`). **Until receipted, R-3 is
`authored`, not `alerting`.**

**P3-5 — AI-6 survival receipt.** Run `terraform plan` in
`terraform/services/account-status-recon/` **with no `TF_VAR_*` overrides**
(the bare-apply resolution path described at `variables.tf:200-213`) and show
the metric filter and alarm are both present and unchanged. A `count`-gated
resource would render as a destroy under that resolution — that is the exact
2026-07-23 incident. The plan output is the receipt.

**P3-6 — clone teardown.** `aws cloudwatch describe-alarms --alarm-name-prefix
autom8y-account-status-recon-report-posted-hashless-proof` returns **zero** at
close (P10 discipline, `success_deadman.tf:64-67`).

### 3.8 Operator-gated steps (explicit)

| # | Step | Who | Command / action |
|---|---|---|---|
| O3-1 | **Capture the two real fixture lines before retention expiry (~2026-09-12)** | sre / operator | `aws logs filter-log-events` on both windows → commit two lines as a test fixture |
| O3-2 | Merge `hash_presence_deadman.tf` + runbook | normal PR review | **no AWS effect** — merging to main runs **plan only** (SVR-7) |
| O3-3 | **`terraform apply`** — Actions → *Service Terraform* → Run workflow → `service_name = account-status-recon`, `environment = production` (`service-terraform.yml:16-18,47-57`) | **operator** | this is the ONLY apply path; nothing auto-fires |
| O3-4 | **Pager wiring**: confirm `autom8y-platform-sre-sev1` still carries live subscribers before arming the page tier | **operator** | `aws sns list-subscriptions-by-topic` |
| O3-5 | **Receipted end-to-end fire** (P3-4) | **operator** | `set-alarm-state` → capture → reset |
| O3-6 | Proof-clone teardown + P10 probe (P3-6) | **operator** | flip `hash_presence_proof_enabled=false` → apply → `describe-alarms --alarm-name-prefix` |
| O3-7 | Watch H-2: after any ASR `image_tag` change, confirm this alarm stayed OK | operator | standing item; the alarm is now the automated form of this watch |

### 3.9 Sizing

| Item | Estimate |
|---|---|
| `hash_presence_deadman.tf` (filter + alarm + proof clone + output + header) | 0.5 d |
| Runbook section | 0.25 d |
| Proof legs P3-1..P3-6 (P3-1/P3-2 are read-only and can run **today**, pre-build) | 0.5 d |
| **Total** | **~1.25 engineering-days + 4 operator gates** |

**R-3 is the cheaper and more urgent of the two.** It closes a standing hazard
(H-2), its RED fixture is perishable, and its proof legs P3-1/P3-2 are
read-only and executable before a single line of HCL is written.

### 3.10 UV-P ledger for R-3

`[UV-P: CloudWatch Logs JSON metric-filter patterns support the NOT EXISTS predicate on a key, matching events where the key is absent | METHOD: deferred-to-P3-1 — aws logs test-metric-filter with the two real log lines | REASON: the whole leg-1 design rests on this predicate; the proof leg is itself the discharge and requires no apply, so no premise should be carried past P3-1]`

`[UV-P: report_posted lines in /aws/lambda/autom8y-account-status-recon are top-level JSON parseable by a metric filter (no Lambda log prefix) | METHOD: deferred-to-P3-1 — the same test-metric-filter call proves it | REASON: strong corroboration exists (the 2026-08-13 Insights census discovered $.block_count/$.abort_reason as fields, queryId 7c59f3d8-821c-4b47-9034-f5d02a3d3fc8, schema.py:36-42) but corroboration is not a probe. FALLBACK if it fails: the unstructured two-term pattern `"\"event\": \"report_posted\"" -"\"content_hash\":"`, which must then be proven by the same test-metric-filter call]`

`[UV-P: the autom8y-platform-sre-sev1 topic still carries live SMS and email subscribers as of the arming date | METHOD: deferred-to-O3-4 — aws sns list-subscriptions-by-topic | REASON: the last verification is dated 2026-08-14 in story_warm_dead_alarm.tf:72-74; a paging leg must never inherit a subscription claim it has not re-checked]`

`[UV-P: a newly created metric filter produces datapoints for log events already ingested before its creation | METHOD: deferred-to-P3-3 observation | REASON: P3-3's immediate-RED expectation depends on it; the design does not rely on it (discrimination is proven at pattern level in P3-1/P3-2), and the caveat is stated in P3-3 rather than assumed away]`

---

## §4. Cross-cutting

### 4.1 Alert inventory after both lanes (what pages, what tickets)

| Alarm | Repo / file | Tier | Condition | Runbook |
|---|---|---|---|---|
| `autom8y-asana-swap-detector-mismatch` (SD-1) | asana `swap_detector_alarms.tf` | **PAGE** | delivered ≠ generated, any occurrence in 24h | new: `RUNBOOK-asana-swap-detector-mismatch.md` |
| `autom8y-asana-swap-sweep-dead` (SD-2) | asana `swap_detector_alarms.tf` | notify | detector lane silent ~16h | new (short) |
| `autom8y-asana-swap-detector-unarmed` (SD-3) | asana `swap_detector_alarms.tf` | notify | deliveries happened, clause 4a did not run, ~12h sustained | shares SD-1's runbook |
| `autom8y-account-status-recon-report-posted-hashless` | monorepo `hash_presence_deadman.tf` | **PAGE** | hashless deliveries across 2×8h buckets | new / appended to `RUNBOOK-account-status-recon-freshness.md` |

Two pages, two tickets. Both pages have a **hard-zero healthy baseline** (no
occurrences in live history), so neither is a flap candidate — the
`StoryWarmFailure` trap (`story_warm_dead_alarm.tf:13-16`) is explicitly
avoided by not alarming on any routinely-nonzero series.

### 4.2 Fences honoured

| Fence | How this design honours it | Anchor |
|---|---|---|
| **R-4 raw-JSON ingestion** | `filter-log-events` + `jq -r .message` + stdin JSONL; Insights forbidden in the lane, and the two Insights constants explicitly not used to feed it | §2.3; SVR-2; `schema.py:270,376-388` |
| **One canonicalization** (no join duplication into the monorepo) | R-2 composes the asana module unmodified; R-3 leg 1 is a presence filter that never compares hashes or keys on `invocation_id`; M-2/M-4/M-5 rejected on exactly this ground | §2.2, §3.3; `ADR-asr-content-hash-canonicalization-2026-08-14.md` |
| **Alarm DoD = one receipted end-to-end fire** | P2-5 and P3-4 are blocking; "authored ≠ alerting" stated for both | `.know/scar-tissue.md:85`; `story_warm_dead_alarm.tf:55-58` |
| **AI-6 (count-coupled deadmen die with the schedule)** | R-3 leg 1 is UNGATED + `notBreaching` + present-0-trips; SD-3 carries an `IF()` denominator guard; P3-5 is the bare-apply plan receipt | §3.3, §2.5; SVR-6; `variables.tf:207-213` |
| **No defect injection (G-THEATER)** | every RED is a deliberately-broken or genuinely-historical **input**; P3-1's RED is real production bytes; P2-2 tampers a scratch copy of real data | §2.6, §3.7; method precedented at `SURFACE-limb-a-live-realized-2026-08-15.md:57-59` |
| **FLAG-1 untouched** | `ASANA_STORY_WARM_PRIORITY_ENTITIES` appears in this artifact only in this fence row; no story-warm surface, setting, alarm, or threshold is read, written, or re-tuned by either lane. `story_warm_dead_alarm.tf` is cited as a **paging idiom** and is not modified — R-2's alarms land in a separate additive file | §2.4, §3.4 file tables |
| **Working-tree vs origin** | all `observability_alarms.tf` citations read from `git show origin/main:...`; the dirty working copy is never cited | §1 |

### 4.3 Anti-patterns explicitly avoided

* **Cause-based alerting** — nothing here alarms on CPU, memory, invocation
  counts, or duration. SD-1 alarms on delivered-artifact integrity; the
  hash-presence deadman alarms on detector-arming state, which is itself the
  precondition for detecting customer-visible corruption.
* **Unactionable alerts** — every alarm above has a named runbook and a named
  first triage step; runbooks are gating (O2-6, O3-2), not follow-ups.
* **Alert fatigue** — no alarm watches a routinely-nonzero series; both page-tier
  alarms have zero healthy baselines; the noisy generation-count companion
  (§3.3) is deliberately deferred rather than shipped.
* **Vacuous green** — the ingestion-integrity guard (§2.3), the non-vacuity
  assertions in P2-1, and the presence control in P3-2 all exist to make "quiet"
  mean something. This design treats an unexamined zero as a defect.
* **Missing context** — every published metric carries
  `{lane, source, environment}` / `{Service}` dimensions.
* **Detector without a detector** — SD-2 watches the R-2 lane; the R-2 lane's
  own workflow pages on red; leg 1 needs no watcher because it is a CloudWatch
  metric filter with no moving parts.

### 4.4 Handoff — platform-engineer items

1. **IAM**: `logs:FilterLogEvents` on `/aws/lambda/autom8y-account-status-recon`
   + `cloudwatch:PutMetricData` for the asana CI principal (UV-P-R2-1). Relates
   to the durable-successor grant work already tracked at
   `nightly-live-smoke.yml:58-62` (autom8y#481 IAM substrate) — worth bundling.
2. **SNS**: confirm `autom8y-platform-sre-sev1` subscriptions before either page
   tier is armed (O3-4).
3. **Terraform**: the ASR tree's apply is `workflow_dispatch`-only (SVR-7); the
   asana tree has no pipeline at all (SVR-8) and needs CLI creation byte-matched
   to the HCL. Neither is a merge side-effect; both need a named human.

### 4.5 Acid test

*"Can we catch degradation before customers do with this monitoring?"*

**With both lanes built and receipted: yes, for the four named failure modes in
§3.6 — with an 8–16h worst case on the delivery-half de-arming and ~4h on a
swap.** Residual blind spots, named rather than papered over:

* a swap that occurs **and** de-arms the hash in the same deploy → leg 1 catches
  the de-arming (the swap itself is unprovable once the hash is gone; this is
  irreducible and is why R-3 is a prerequisite for trusting R-2);
* a canonicalization split at REC-004 presents as a mismatch storm, not a swap —
  handled by runbook triage order, not by the detector (§2.5);
* everything outside ASR's report class. Both lanes are scope-fenced to it,
  per the R-1 fence carried verbatim at
  `SURFACE-limb-a-live-realized-2026-08-15.md:27-32`. `render()` still has zero
  production callers; **neither lane may be read as covering the EX-5 readout
  path.**

---

## §5. Evidence grade

**MODERATE (ceiling).** Self-referential authorship: the sre seat designing the
detector for an instrument the same fleet armed, at design altitude with no
built artifact and no live probe performed by this dispatch
(`self-ref-evidence-grade-rule`). Every file:line anchor in §1 is mechanically
re-readable at the stated commit; every claim about not-yet-existing behaviour
carries a UV-P with a named, read-only discharge probe. Nothing in this paper
was applied, armed, or observed live.

No seat in this dispatch speaks an attestation word. Both lanes reach
`alerting` only after their receipted end-to-end fire (P2-5, P3-4) — until then
they are `authored`.
