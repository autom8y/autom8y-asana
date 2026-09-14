---
id: DEPLOY-read-the-name-s1-2026-09-14
date: 2026-09-14
station: pipeline-steward (dre, invoked)
wave: read-the-name wave 1, S1.5 post-merge watch and after-read
self_cap: MODERATE
---

# S1.5 Post-Merge Watch and After-Read — `read-the-name` wave 1

**One-line verdict.** S1.5 executed by **auto-merge** at **2026-09-14T05:19:36Z**
(autom8y PR #2205, merge commit `4e8e163f`) **with a NON-required hermetic guard
RED** (`Guard teeth tests (hermetic)` / workflow `Preserve Fuel Gate Integrity`,
FAILURE at 05:17:57Z) — carrier: **a guard that is not a required check does not
gate auto-merge**. The registry cure landed separately as **autom8y PR #2207**
(merged 05:24:31Z), `scripts/`-only, promoting the office-floor Lambda from
`pending:` coverage-only to a fifth named `var.image_tag` consumer once its
birth apply (this run) completes.

Every AWS account id in this receipt is redacted to the literal `<ACCOUNT>`
per merge-surface-sweep class `digits12` (autom8y #2203 precedent); GitHub run
ids (11 digits) are left intact. Verified via `grep -n -E '[0-9]{12,}'` on this
file before commit (§8).

---

## §1 Facts at dispatch (VERIFIED)

- autom8y PR #2205 "feat(ebi): office booking floor evaluator, two page
  classes, unarmed" — `state: MERGED`, `mergedAt: 2026-09-14T05:19:36Z`,
  `mergeCommit: 4e8e163f520c5e98a554c5e8297173889ae556f4`, merged by
  `tomtenuta` (auto-merge). [bash-probe: `gh pr view 2205 --repo autom8y/autom8y --json number,state,mergedAt,mergeCommit,mergedBy,title`]
- PR #2205 files: `scripts/ebi_pending_terraform.sh`, 8 files under
  `services/email-booking-intake/src/email_booking_intake/office_floor/**`,
  2 test files, `terraform/services/email-booking-intake/office_floor.tf`
  (new, 345 lines), `terraform/services/email-booking-intake/variables.tf`
  (modified, +52). [bash-probe: `gh pr view 2205 --json files`]
- Non-required guard RED: `Guard teeth tests (hermetic)` (workflow
  `Preserve Fuel Gate Integrity`), `conclusion: FAILURE`, completed
  `2026-09-14T05:17:57Z` — i.e. it failed **before** the merge instant
  (05:19:36Z) and did not block it. [bash-probe: `gh pr view 2205 --json statusCheckRollup --jq '.statusCheckRollup[] | select(.conclusion=="FAILURE")'`]
- Failing assertion, named: `test_ebi_registry_covers_every_image_tag_consumer`
  in `scripts/tests/test_apply_preserve_fuel.py` — the office-floor Lambda is a
  FIFTH `var.image_tag` consumer (module-form, `office_floor.tf`) not yet
  listed in `scripts/apply-preserve-fuel-registry.tsv`'s `email-booking-intake`
  row. [file-read: `scripts/tests/test_apply_preserve_fuel.py` docstring
  "EBI has FOUR module-form consumers... Count both forms" (post-cure)]
- Cure PR #2207 — `scripts/`-only, MERGED `2026-09-14T05:24:31Z`. Diff:
  registry row gains `,pending:autom8-email-booking-intake-office-floor`
  (BIRTH-STATE entry — enrolled for coverage, excluded from unanimity/
  resolution until promoted, because the birth apply that creates the
  function IS this run); test file gains `EBI_PENDING_FNS` list and widens
  `_ebi_image_tag_consumers()` docstring from THREE+ONE to FOUR+ONE forms.
  All 2207 checks green (12+ CheckRuns, all `SUCCESS`).
  [bash-probe: `gh pr view 2207 --json files,mergedAt,statusCheckRollup`;
   file-read diff `git diff 4e8e163f pr2207-ref -- scripts/apply-preserve-fuel-registry.tsv scripts/tests/test_apply_preserve_fuel.py`]
- Pending set at merge (INHERITED from the S1.5 pre-merge enumeration,
  `S1.5-premerge-2026-09-14.md`): ONE member, `a1f3ecf3` / PR #2200
  ("deploy-and-pin as a single act"), evidence-consistent with
  already-applied (v69 config `LastModified` 2026-09-14T00:54:29Z postdates
  the anchor apply-run completion by 8m35s; no image-pin var in the 46-var
  v69 environment). Independently re-confirmed here: PR #2200
  `state: MERGED`, `mergedAt: 2026-09-14T01:51:18Z`, well before this
  dispatch. [bash-probe: `gh pr view 2200 --repo autom8y/autom8y --json number,state,title,mergedAt,mergeCommit`]
- Alias `live` before: `served_version: 69`, `served_image` tag `0850228`
  (INHERITED from the pre-merge enumeration's qualified `get-function`/
  `get-alias` read; not re-probed independently pre-apply by this station —
  the pre-merge artifact is the receipt of record for the BEFORE state).
- Pre-merge alarm baseline file `alarms_before.json` carries **11** alarms,
  not the 13 named in the dispatch brief — a discrepancy named honestly here,
  not silently corrected. All 11 have both `Actions` and `OKActions` pointed
  at `arn:aws:sns:us-east-1:<ACCOUNT>:autom8y-platform-alerts` (the
  pre-existing shared alert topic — none of these 11 pre-date this dispatch's
  scratch-topic work). [file-read: `alarms_before.json`, 11 `Name` entries,
  all `autom8-email-booking-intake-*`]

## §2 Run 34809228564 — job table (VERIFIED, own-hands re-run)

[bash-probe: `gh run view 34809228564 --repo autom8y/autom8y --json status,conclusion,jobs`,
polled every 45s from 05:26:04Z to terminal at 05:31:25Z (7 polls); full poll log
retained at the session scratchpad `run_watch2.log`]

**RUN CONCLUSION: `failure`** (status: `completed`).

| Job | Conclusion |
|---|---|
| Detect Changes | success |
| CI (email-booking-intake) / Run Tests | success |
| Build (email-booking-intake) / Build and Push | success |
| **Deploy Lambda (email-booking-intake) / Deploy Lambda via Terraform** | **failure** |
| Smoke Advisory (email-booking-intake) | success (advisory-only; ran independently of the deploy job's outcome and does not exercise the office-floor function, which never came into existence — see §3) |
| Deploy Summary | success (summary job; does not override the run's own `failure` conclusion) |

## §3 DIAGNOSIS — Deploy Lambda job failure (STOP point; no re-fire attempted)

**Named error, verbatim** [bash-probe: `gh run view 34809228564 --repo autom8y/autom8y --log-failed`]:

```
Error: creating SNS Topic (autom8-ebi-office-floor-scratch): operation error SNS:
CreateTopic, https response error StatusCode: 400, RequestID:
4255d8f5-df2b-51ee-8234-bbd458cbdea3, InvalidParameter: Invalid parameter: Tags
Reason: The given tag(s) contain invalid characters

  with aws_sns_topic.office_floor_scratch,
  on office_floor.tf line 42, in resource "aws_sns_topic" "office_floor_scratch":
  42: resource "aws_sns_topic" "office_floor_scratch" {
```

**Root cause named**: `terraform/services/email-booking-intake/office_floor.tf:42-48`
declares
```
tags = {
  ManagedBy  = "terraform"
  Initiative = "read-the-name"
  Purpose    = "S-1 booking-floor page paths while the consumer word is WITHHELD (R-168)"
}
```
The `Purpose` tag value contains parentheses `(R-168)`. AWS SNS's `CreateTopic`
tag-value validation rejects characters outside its allowed set (letters,
digits, spaces, and `+ - = . _ : / @`); `(` and `)` are not in that set. This
is a **plain SNS API-side input-validation defect in a newly-authored resource
block** — it is NOT a Terraform state lock (verified: no active lock item for
`email-booking-intake` in the `terraform-locks` DynamoDB table, only steady-state
`-md5` digest rows for unrelated stacks), NOT an apply refusal by any gate, and
NOT the preserve-fuel resolver's REFUSE-ON-SPLIT-FUEL (the resolver's own
domain — `scripts/ebi_pending_terraform.sh` / the registry unanimity check —
was never reached; this failed at plain resource creation inside the raw
`terraform apply`, upstream of any fuel-resolution step).

**Timing note (named honestly, not smoothed over)**: the `Creating...` line for
`aws_sns_topic.office_floor_scratch` appears at `05:26:56.4087334Z`; the
`Error:` block is not printed until `05:30:50.4566312Z`, a ~3m54s gap. This is
NOT a slow SNS call — `CreateTopic` 400s are sub-second. Terraform's apply
graph ran the topic creation (which failed fast) concurrently with the
independent long-poll `aws_lambda_alias.serving[0]` CodeDeploy traffic-shift
for the main intake (which took 3m25s, `05:27:23Z`→`05:30:49Z`); Terraform
defers printing accumulated diagnostics until the current concurrent batch
completes, so the SNS failure's message surfaced only after the unrelated,
successful intake alias shift finished. **STOP point per dispatch: diagnosed,
not re-fired.** No apply, plan, or destroy was attempted by this station.

**Terraform's own plan summary for this apply** (`Terraform Plan` step,
`05:26:47Z`, before the graph ran): `Plan: 28 to add, 5 to change, 0 to
destroy.` — 28 new resources (the office_floor module + office_floor_freshness
module in full) and 5 in-place modifications (the four pre-existing Lambdas'
`image_tag` plus the intake alias). Of the 28 planned adds, the table below
shows which actually landed before the SNS error stopped the graph.

**Partial-apply state — what the failed run actually left behind** (every line
below is an own-hands AWS read taken AFTER the run reached `completed`, not an
assumption from the log):

| Resource | State | Evidence |
|---|---|---|
| `aws_sns_topic.office_floor_scratch` (`autom8-ebi-office-floor-scratch`) | **DOES NOT EXIST** — creation REJECTED by AWS | `aws sns list-topics` filtered on `ebi-office-floor` → `[]` |
| `module.office_floor.module.lambda.aws_lambda_function.main` (the evaluator itself) | **DOES NOT EXIST** — blocked (transitively depends on the topic ARN via `aws_iam_policy.office_floor`) | `aws lambda get-function --function-name autom8-email-booking-intake-office-floor` → `ResourceNotFoundException` |
| `aws_iam_policy.office_floor` (the 4-grant StartQuery/GetQueryResults/sns:Publish/PutMetricData policy) | **DOES NOT EXIST** — blocked (its policy document embeds `local.office_floor_page_topic_arn`) | see §4.4 IAM read below: only the module's 2 baseline managed policies + 1 DLQ inline policy are attached; the custom policy is absent |
| `module.office_floor_freshness.*` (prober Lambda, prober role, prober log group, prober schedule rule, prober self-deadman alarm, the `autom8-ebi-booking-floor-lambda-freshness` alarm) | **ENTIRE MODULE DOES NOT EXIST** — blocked (its `alarm_actions` input is `[local.office_floor_page_topic_arn]`) | `aws cloudwatch describe-alarms --alarm-name-prefix autom8-ebi-` → only the PRE-EXISTING, unrelated `autom8-ebi-contente-reconcile-freshness-prober-liveness` / `autom8-ebi-contente-reconcile-lambda-freshness` (from an earlier wave); no `autom8-ebi-booking-floor-*` names |
| `module.office_floor.module.lambda.aws_iam_role.lambda_execution` (`autom8-email-booking-intake-office-floor-lambda-role`) | **EXISTS** — created 05:26:56Z, does not depend on the topic | `aws iam get-role` → `CreateDate: 2026-09-14T05:26:56+00:00` |
| `module.office_floor.module.lambda.aws_cloudwatch_log_group.lambda` (`/aws/lambda/autom8-email-booking-intake-office-floor`) | **EXISTS**, 0 stored bytes (never invoked — no function to invoke it) | `aws logs describe-log-groups --log-group-name-prefix ...` |
| `module.office_floor.module.lambda.aws_cloudwatch_event_rule.schedule` (`autom8-email-booking-intake-office-floor-schedule`) | **EXISTS**, `State: ENABLED`, `rate(1 hour)`, but **ZERO targets** | `aws events describe-rule` (exists) + `aws events list-targets-by-rule` → `{"Targets": []}` |
| `module.office_floor.module.lambda.aws_sqs_queue.dlq[0]` (`autom8-email-booking-intake-office-floor-dlq`) | **EXISTS** | `aws sqs get-queue-url` succeeds |

**Net effect**: the apply is stuck in a half-built state — a role, a log group,
an ENABLED-but-target-less schedule rule, and a DLQ exist; the evaluator
function, its custom IAM grants, the scratch topic, and the entire freshness
deadman (including the module's own `enabled=true` prober that would have
seeded a real datapoint at apply-time) do not. **No page path exists at all**
right now — not even the scratch one — because the topic itself never came
into being. This is a stronger safety posture than "unarmed" (R-168's design
intent): it is "does not exist," which happens to be even less reachable, but
it is also not the shipped, evaluating-and-silent state S1.5 was supposed to
land.

**What DID succeed in the same apply** (the four pre-existing consumers, whose
`var.image_tag` update is unrelated to the office-floor resource graph):

- `autom8-email-booking-intake` (main intake): config Modified in 27s, alias
  `live` traffic-shifted via CodeDeploy in 3m25s — **alias now serves version
  70**, image tag `4e8e163` (== the merge commit short SHA), 46 env vars
  (same count as the v69 baseline), `LastModified: 2026-09-14T05:26:57Z`.
- `autom8-email-booking-intake-contente-reconcile`, `-forwarding-nudge`,
  `-contente-retro-redrive`: all three Modified successfully, all now report
  `ImageUri` ending `:4e8e163`, all `LastModified: 2026-09-14T05:26:57Z` — the
  four pre-existing consumers resolved to ONE consistent tag, exactly as the
  preserve-fuel unanimity discipline requires of them.

## §3b ROLL-FORWARD — cure #2210 and the re-fire (mid-dispatch update)

**The chain, three shas/runs, named plainly:**

1. **`4e8e163f`** (PR #2205, merged 05:19:36Z) → run **`34809228564`**
   (`workflow_dispatch`? no — ordinary push-triggered `service-deploy-dispatch`)
   → **FAILED** 05:30:50Z on the SNS tag-character defect (§3 above).
2. **`d408a38c`** (PR #2210, "fix(ebi): office-floor scratch topic tag — drop
   the parentheses (S1.5 roll-forward)", merged **05:35:47Z**) — a
   ONE-LINE diff, verified: `terraform/services/email-booking-intake/office_floor.tf`
   line 47 changes `"...WITHHELD (R-168)"` to `"...WITHHELD per R-168"` — the
   parentheses are gone, nothing else in the file changed. [file-read:
   `git diff 4e8e163f d408a38c -- terraform/services/email-booking-intake/office_floor.tf`]
   Its own push-plan run, **`34810213990`** ("Service Terraform — push"),
   completed `success` at `05:37:55Z`. [bash-probe: `gh run view 34810213990
   --repo autom8y/autom8y --json name,status,conclusion,headSha`]
3. **Roll-forward re-fire**: **run `34810338540`**, workflow
   `Deploy Dispatch — email-booking-intake → production`, triggered by
   `workflow_dispatch` (the S-5 precedent shape, cf. run `34661356644` in this
   fleet's history) at `headSha d408a38c`, `createdAt 05:37:58Z`. **This is
   the run this receipt now watches to terminal state** — the remainder of
   this document (§4 onward) reports on `34810338540`'s outcome, not
   `34809228564`'s.

**Alias `live` in its TRANSIENT between-runs state** (read at `2026-09-14T05:39:00Z`,
BEFORE `34810338540`'s apply could move it again — time-sensitive, captured
first per the coordinator's instruction): `FunctionVersion: 70`, image tag
`4e8e163` (== the FAILED run's merge commit, confirming the failed run's
partial success on the four pre-existing consumers persisted un-touched
through the gap between the two dispatches), `LastModified
2026-09-14T05:26:57Z` — identical to the §4(2) "after" reading taken
immediately following the first run's completion. Nothing moved the alias in
the ~8-minute gap between the two runs, as expected (no apply was in flight
during that window).

**Expectation for the re-fire's own after-read** (stated here before the
result is known, so the eventual finding is checked against a pre-registered
expectation, not fitted to it after the fact): `34810338540` builds a NEW
image from `d408a38c` and should re-shift the intake alias to a version ABOVE
70, carrying a tag distinct from `4e8e163` (the `d408a38c`-built tag). The
**unanimity condition** this station checks for a clean landing is now
FOUR-WAY, not the original two-way alias-vs-new-function comparison: the
office-floor function's `$LATEST` tag == the intake's alias-served tag == each
of the three siblings' (`contente-reconcile`, `forwarding-nudge`,
`contente-retro-redrive`) `$LATEST` tag, **all four at the `d408a38c` build**.
Anything less than all four agreeing is a fresh split-fuel finding, not a
clean landing.

## §3c SECOND FAILURE — roll-forward re-fire `34810338540` (mid-dispatch update 2)

**RUN CONCLUSION: `failure`.** Job table [bash-probe: `gh run view 34810338540
--repo autom8y/autom8y --json status,conclusion,jobs`]:

| Job | Conclusion |
|---|---|
| Detect Changes | success |
| **CI (email-booking-intake) / Run Tests** | **failure** |
| Smoke Advisory (email-booking-intake) | success (advisory-only) |
| Build (${{ matrix.service }}) | skipped |
| Deploy Lambda (${{ matrix.service }}) | skipped |
| Deploy Summary | success (summary job) |

**Because CI failed, Build and Deploy Lambda never ran — no `terraform
apply` of any kind was attempted in this run.** Confirmed by direct AWS
re-read taken AFTER this run's completion (`2026-09-14T05:42:40Z`): alias
`live` is still `FunctionVersion: 70` (unchanged from §3b's between-runs
reading) and `autom8-email-booking-intake-office-floor` still returns
`ResourceNotFoundException`. **The AWS stack is byte-identical to its
post-`34809228564` state; this second failure added zero new apply debris.**

**Named diagnosis, exact assertion** [bash-probe: `gh api /repos/autom8y/autom8y/actions/jobs/<JOB_ID>/logs
--allow-escape-sequences`, `<JOB_ID>` = the `CI (email-booking-intake) / Run
Tests` job's own databaseId, resolved via `gh run view 34810338540
--json jobs`]:

```
FAILED tests/test_ebi_image_pin_currency.py::TestPinIsRetired::test_the_registry_row_names_all_four_functions
AssertionError: autom8-email-booking-intake,autom8-email-booking-intake-contente-reconcile,autom8-email-booking-intake-forwarding-nudge,autom8-email-booking-intake-contente-retro-redrive,pending:autom8-email-booking-intake-office-floor
assert {..., 'pending:autom8-email-booking-intake-office-floor'} == {...four names, no pending entry...}
1 failed, 3558 passed, 3 skipped, 10 warnings in 50.19s
error: recipe `ci-test` failed on line 31 with exit code 1
```

**Root cause named**: TWO independent tests read the SAME
`scripts/apply-preserve-fuel-registry.tsv` `email-booking-intake` row and
assert CONTRADICTORY contracts on it:

1. `scripts/tests/test_apply_preserve_fuel.py::test_ebi_registry_covers_every_image_tag_consumer`
   (repo-root `Preserve Fuel Gate Integrity` workflow, **NOT required**) —
   updated by PR **#2207** to REQUIRE the fifth
   `pending:autom8-email-booking-intake-office-floor` entry (coverage for the
   not-yet-born consumer).
2. `services/email-booking-intake/tests/test_ebi_image_pin_currency.py::TestPinIsRetired::test_the_registry_row_names_all_four_functions`
   (service-local test, part of the **REQUIRED** `CI (email-booking-intake) /
   Run Tests` job via `just ci-test`) — hard-codes `_EXPECTED_SOURCES` as
   EXACTLY the four pre-existing function names
   (`services/email-booking-intake/tests/test_ebi_image_pin_currency.py:40-45`),
   with no allowance for a `pending:`-prefixed fifth member. NOT touched by
   #2207, because #2207 was scoped `scripts/`-only.

**Why the first (failed) deploy's own CI passed on this same registry row**:
run `34809228564`'s `CI (email-booking-intake) / Run Tests` job ran against
`4e8e163f` — the merge commit that PREDATES #2207's registry edit entirely
(the registry still had four sources, no `pending:` entry, when that CI run
executed). The roll-forward's re-fire pulls `d408a38c`, which sits on top of
BOTH #2207 (the five-source registry) and #2210 (the tag fix) — so this is
the FIRST run in this chain whose CI has ever evaluated the five-source
registry row against the service-local test's stale four-source contract.
**This is a genuinely new defect, not a recurrence of the SNS tag issue and
not predicted by anything this station's earlier reads flagged.**

**Roll-forward chain, now three sha/run pairs** (per the coordinator's
instruction, updated as each fires):

1. `4e8e163f` (PR #2205) → run `34809228564` → **FAILED** (apply: SNS
   `CreateTopic` tag-character defect, §3).
2. `d408a38c` (PR #2210, tag-fix cure) → run `34810338540` → **FAILED**
   (tests: registry-pin contradiction, this section). Build/Deploy never
   reached; no new AWS state.
3. **Third run pending** — the coordinator reports a tests-only cure
   (`services/**/tests/**`, which per this stack's own path-filtering fires
   no deploy on its own PR) is being cut now; this station HOLDS per
   instruction and will record the third run's id, sha, and outcome here
   once dispatched. **No re-fire attempted by this station itself** at any
   point in this chain — every re-fire dispatch has come from the operator/
   coordinator side.

## §4 AFTER-READ, item by item (dispatch items 2–7)

Item numbering below matches the dispatch brief; each is answered against the
**actual** post-failure AWS state, not the "on success" assumption.

### (2) alias `live` + new function + SNS topic scratch + EventBridge rule

- **alias `live`** (`autom8-email-booking-intake`): version **70**, image tag
  **`4e8e163`** (== merge commit `4e8e163f` short form), `LastModified
  2026-09-14T05:26:57Z`, 46 env vars — the `services/**` merge DID rebuild and
  reserve the image as expected. [bash-probe: `aws lambda get-alias`,
  `get-function --qualifier live`, `get-function-configuration --qualifier live`]
- **the new function** (`autom8-email-booking-intake-office-floor`): **does
  not exist** — `ResourceNotFoundException`. There is no `$LATEST` image tag
  to read, qualified or unqualified, because there is no function. The
  unanimity check the dispatch asked for ("its `$LATEST` tag EQUALS the
  intake's alias-served tag") is **not evaluable**: the fifth consumer has not
  been born. [bash-probe: `aws lambda get-function --function-name
  autom8-email-booking-intake-office-floor`]
- **its env** (`EMAIL_BOOKING_INTAKE_OFFICE_FLOOR_PAGE_TOPIC_ARN` — note the
  dispatch brief's guessed name `OFFICE_FLOOR_PAGE_TOPIC_ARN` is not the
  actual variable; the module prefixes every env var
  `EMAIL_BOOKING_INTAKE_OFFICE_FLOOR_*`, confirmed by direct read of
  `office_floor.tf`'s `environment_variables` block): **not evaluable**, no
  function exists to carry it.
- **reserved concurrency, the EventBridge rule**: the rule
  `autom8-email-booking-intake-office-floor-schedule` **does exist**, `State:
  ENABLED`, `ScheduleExpression: rate(1 hour)` (matches `var.office_floor_schedule`
  default) — but it targets **nothing** (`list-targets-by-rule` → `{"Targets": []}`).
  An enabled rule with zero targets fires into the void every hour and invokes
  no Lambda; this is a structurally inert, not merely unarmed, schedule.
  [bash-probe: `aws events describe-rule` + `aws events list-targets-by-rule`]

### (3) SNS topic `autom8-ebi-office-floor-scratch`

**Does not exist.** `aws sns list-topics` filtered on `ebi-office-floor`
returns `[]`. There is therefore nothing to check for zero subscriptions —
the honest answer is not "0 subscriptions on an armed-but-quiet topic," it is
"no topic." [bash-probe: `aws sns list-topics --region us-east-1 --query
"Topics[?contains(TopicArn, 'ebi-office-floor')]"`]

### (4) Alarm diff — two-sided

- **Before** (`alarms_before.json`, captured pre-merge): **11** alarms, not
  the 13 named in the dispatch brief — a discrepancy named here honestly (see
  §1). All 11 already pointed `Actions`/`OKActions` at
  `arn:aws:sns:us-east-1:<ACCOUNT>:autom8y-platform-alerts`.
- **After**: re-read of the same `autom8-email-booking-intake*` prefix returns
  the **identical 11-name set**, verified byte-for-byte equal via a Python set
  comparison (`before_names == after_names` → `True`). **No pre-existing
  alarm's actions changed** (the set match alone does not re-read every
  alarm's `AlarmActions`, but since the apply never reached any resource that
  could edit those 11 — they belong to the intake/reconcile/nudge modules
  whose only touched attribute this run was `image_tag`, and Modify-in-place
  on those modules does not touch `alarm_actions` — there is no code path in
  this PR's diff that could have mutated them).
- **New alarms expected** (`autom8-email-booking-intake-office-floor-lambda-errors`,
  `-dlq-not-empty`, `autom8-ebi-booking-floor-lambda-freshness`,
  `autom8-ebi-booking-floor-freshness-prober-liveness`): **NONE were
  created.** `describe-alarms --alarm-name-prefix autom8-ebi-` returns only
  the pre-existing, unrelated `autom8-ebi-contente-reconcile-freshness-prober-liveness`
  and `autom8-ebi-contente-reconcile-lambda-freshness` (a different wave's
  alarms). `describe-alarms --alarm-name-prefix autom8-email-booking-intake-office-floor`
  returns an empty set. **No alarm anywhere references `autom8y-platform-alerts`
  newly** — trivially true, since nothing new was created to reference
  anything. The "success-gap alarm ABSENT (deliberately deferred to S1.7)"
  expectation holds, but not for the reason the design intended — it's absent
  because the whole module is absent, not because S1.7 hasn't arrived yet.
  [bash-probe: `aws cloudwatch describe-alarms --alarm-name-prefix ...` x3]

### (5) IAM

The role `autom8-email-booking-intake-office-floor-lambda-role` exists
(created 05:26:56Z) with:
- **Attached managed policies**: `AWSLambdaBasicExecutionRole`,
  `AWSXRayDaemonWriteAccess` — the module's own baseline grants, unrelated to
  the office-floor-specific 4-grant policy.
- **Inline policies**: exactly one, `autom8-email-booking-intake-office-floor-dlq`
  (the DLQ send-message grant the base module attaches for `enable_dlq=true`).
- **The custom 4-grant policy is ABSENT.** `aws_iam_policy.office_floor`
  (`logs:StartQuery` + `logs:GetQueryResults` + `sns:Publish` scoped to the
  scratch topic ARN + `cloudwatch:PutMetricData` namespace-conditioned) never
  got created, because its policy document embeds
  `local.office_floor_page_topic_arn`, which errored along with the topic.
  **The role can invoke nothing this evaluator needs** — it cannot query
  Insights, cannot publish, cannot emit its success metric — on top of the
  function not existing at all.
  [bash-probe: `aws iam get-role`, `list-attached-role-policies`,
  `list-role-policies`]

### (6) First evaluation

**Not observable and could not be, even had the window been longer**: no
function exists to have evaluated, the schedule rule has zero targets, and
the log group (`/aws/lambda/autom8-email-booking-intake-office-floor`) reports
`storedBytes: 0` — zero log events of any kind, `office_floor_evaluated` or
otherwise. `[UV-P: first controlled office_floor_evaluated run | METHOD:
deferred-to-re-apply-after-tag-fix | REASON: the evaluator Lambda does not
exist in this apply's partial state; there is nothing to invoke or observe
until the SNS topic tag defect is fixed and a clean apply lands the full
module graph]`

### (7) The other four Lambdas — unchanged alias/version behaviour, one resolved tag

**Confirmed, own-hands, for the three non-aliased functions**
(`contente-reconcile`, `forwarding-nudge`, `contente-retro-redrive`): each now
reports `ImageUri` ending `:4e8e163` and `LastModified 2026-09-14T05:26:57Z` —
identical to the main intake's newly-served tag. The whole-stack apply DID
resolve one consistent tag across the four pre-existing consumers, even though
it failed before reaching the fifth (office-floor). This is the exact claim
the preserve-fuel registry's now-FOUR-plus-`pending`-one unanimity set exists
to protect — and for the four LIVE members, it held.
[bash-probe: `aws lambda get-function --function-name {fn} --query
"{ImageUri:Code.ImageUri,LastModified:Configuration.LastModified}"` x3]

## §5 Pending set as applied

- **#2200** (`a1f3ecf3`, deploy-and-pin single-act): applied hours before this
  dispatch (`mergedAt 2026-09-14T01:51:18Z`), re-confirmed here independently
  via `gh pr view`; not disturbed by this run's failure.
- **#2205** itself (`4e8e163f`): the CODE landed (office_floor Python package,
  `office_floor.tf`, `variables.tf`) via merge; the TERRAFORM did **not**
  fully apply. The four pre-existing consumers picked up the new image; the
  fifth (office-floor) — the actual point of the PR — did not come into
  existence. #2205's own merge auto-completed on a NON-required guard RED
  (`Guard teeth tests (hermetic)`, `Preserve Fuel Gate Integrity`) that would
  have caught the registry-coverage gap had it been required; the cure
  (**#2207**) landed 5 minutes later, `scripts/`-only, and is itself green.
  Neither PR's CI predicted or could have predicted the SNS tag defect — that
  defect lives in `office_floor.tf`, outside both PRs' diffs' test surface
  (no test in this repo unit-tests `terraform apply` against a live AWS tag
  validator; `test_ebi_registry_covers_every_image_tag_consumer` only checks
  registry-vs-terraform-source coverage, not runtime tag legality).

## §6 Guest-footprint conformance (D7)

This station stayed a bounded read-only guest on both the source repos and
AWS for the entire watch + after-read: every AWS call above is a `describe-*`,
`get-*`, or `list-*` (no `create`, `update`, `put`, `delete`, `apply`, or
`terraform` invocation of any kind); no re-fire of the failed run, no retry,
no `terraform apply`/`plan` was attempted. The one write surface used is the
docs-only PR in `autom8y-asana` this receipt itself lands on, via a worktree
off `origin/main` at the blessed path
(`.knossos/worktrees/wt.dre.s1-5-deploy-receipt.20260914T052622Z.bcdb`),
reaped at the end of this dispatch (§9).

## §7 Verdict and handoff

**S1.5 did NOT land the office-floor evaluator.** The merge landed the code;
the apply that was supposed to be S1.5's one irreversible node
(`office_floor.tf`'s own header: "THE MERGE IS THE APPLY (R-136), AND THAT IS
S1.5's NODE") **failed on a plain SNS tag-character validation error**, an
implementation defect in the new Terraform resource block, orthogonal to
every ruling (R-160..R-172) and every guard this wave built. The four
pre-existing EBI Lambdas are healthy and running the new image
(`4e8e163`); the fifth does not exist; its role, log group, DLQ, and an
inert (target-less) schedule rule are stranded in AWS as apply debris.

**This is not a GATE-1 landing receipt for the evaluator** — there is no
realized output to assert a completeness invariant against (no function, no
topic, no page path, not even the deliberately-unarmed scratch one). Per the
pipeline-steward's own front-loaded reflex: a receipt that reported "S1.5
succeeded" here, asserting completeness on the merge event or the CI-green
label rather than on the AWS-observed realized state, would be exactly the
seam-stop violation this station exists to refuse. This receipt instead names
the sole discriminator between "shipped" and "not shipped" plainly: **does the
Lambda function `autom8-email-booking-intake-office-floor` exist in AWS?**
It does not. Every cheaper signal (PR merged, CI green on required checks,
image built and pushed, 4/5 consumers updated) reads GREEN or PLAUSIBLE while
that one answer is NO.

**Operator/architect-facing next step (named, not executed by this
read-only station)**: strip the parenthetical characters from the `Purpose`
tag value at `terraform/services/email-booking-intake/office_floor.tf:45`
(e.g. `"S-1 booking-floor page paths while the consumer word is WITHHELD --
R-168"` or drop the ticket reference from the tag entirely) and re-run the
apply. Until that lands, the office-floor evaluator is fully unbuilt in AWS
regardless of what the merged source tree says.

## §8 Redaction check (merge-surface sweep class `digits12`)

Every AWS account id in this document is replaced with the literal
`<ACCOUNT>`. The GitHub run id (11 digits, `34809228564`) is left intact per
the coordinator's ruling (autom8y #2203 precedent) — it is not account-shaped.
Per-job GitHub ids (which run 12 digits, e.g. the Deploy Lambda job's own
numeric id) are deliberately NOT cited anywhere in this document by their raw
digit string, precisely because they would trip the same `digits12` class the
coordinator named; job identity above is conveyed by job NAME only. Verified
below (§9).

## §9 Reap

Session AWS credentials used were the ambient read-only profile already
active in this shell; no credentials were minted, rotated, or written. The
worktree at `.knossos/worktrees/wt.dre.s1-5-deploy-receipt.20260914T052622Z.bcdb`
is reaped (`git worktree remove`) immediately after the PR is opened from its
branch tip; the branch itself is left for the PR.

