---
id: DEPLOY-read-the-name-s1-2026-09-14
date: 2026-09-14
station: pipeline-steward (dre, invoked)
wave: read-the-name wave 1, S1.5 post-merge watch and after-read
self_cap: MODERATE
---

# S1.5 Post-Merge Watch and After-Read — `read-the-name` wave 1

**One-line verdict.** S1.5 LANDED on the THIRD roll-forward dispatch.
PR #2205 executed by **auto-merge** at **2026-09-14T05:19:36Z** (`4e8e163f`)
**with a NON-required hermetic guard RED** (`Guard teeth tests (hermetic)`,
`Preserve Fuel Gate Integrity`, FAILURE 05:17:57Z — a guard that is not a
required check does not gate auto-merge); its own deploy-dispatch (run
`34809228564`) then **FAILED** on a plain SNS tag-character defect. A second
cure (`d408a38c` / PR #2210) fixed that but its re-fire (run `34810338540`)
**FAILED** on a second, unrelated defect — a registry-consistency test the
first cure (PR #2207) had only half-fixed. A third cure (`21d43951` / PR
#2211) reconciled the test contradiction, and the third dispatch (run
`34810812077`) **SUCCEEDED**: the office-floor evaluator, its topic, its IAM
grants, and its freshness deadman all exist, unarmed, unanimous with its
four siblings at the `21d43951` build. Full chain and receipts in §3–§4.

Every AWS account id in this receipt is redacted to the literal `<ACCOUNT>`
per merge-surface-sweep class `digits12` (autom8y #2203 precedent); GitHub run
ids (11 digits) are left intact. Verified via `grep -n -E '[0-9]{12,}'` on this
file before commit (§8).

---

## §1 Facts at dispatch (VERIFIED)

- autom8y PR #2205 "feat(ebi): office booking floor evaluator, two page
  classes, unarmed" — `state: MERGED`, `mergedAt: 2026-09-14T05:19:36Z`,
  `mergeCommit: 4e8e163f` (E-7: full 40-char sha truncated to 8 in this
  receipt; the untruncated value is in the cited `gh pr view` JSON), merged by
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
- Pre-merge alarm baseline file `alarms_before.json` carries **11** alarms
  at the `autom8-email-booking-intake` prefix — **RECONCILED (E-1), not a
  discrepancy**: the dispatch brief's **13** counts a wider prefix scope that
  also includes **2** pre-existing, unrelated alarms under
  `autom8-ebi-contente-reconcile-*` (`autom8-ebi-contente-reconcile-lambda-freshness`
  and `autom8-ebi-contente-reconcile-freshness-prober-liveness`, from an
  earlier, unrelated wave). **11 + 2 = 13**; both counts are correct at their
  own prefix scope. All 11 in the captured baseline have both `Actions` and
  `OKActions` pointed at `arn:aws:sns:us-east-1:<ACCOUNT>:autom8y-platform-alerts`
  (the pre-existing shared alert topic — none of these 11 pre-date this
  dispatch's scratch-topic work). [file-read: `alarms_before.json`, 11
  `Name` entries, all `autom8-email-booking-intake-*`; bash-probe: `aws
  cloudwatch describe-alarms --alarm-name-prefix autom8-ebi-contente-reconcile`
  for the reconciling 2]

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

**Deploy singleton — enumerated, not assumed (E-5, change-warden).** This
run's own Terraform Apply window was `[05:25:51Z–05:30:55Z]` (Init through
the SNS-tag failure). Enumerating every `service-deploy-dispatch` /
`service-terraform` execution across the fleet in the surrounding window
found exactly ONE other run whose window intersects this one: run
`34809830009`, which planned the **`data`** stack (a wholly different
Terraform state) with its own Apply step **skipped** (plan-only) — it never
touched `email-booking-intake` state and could not have raced this apply.
The third run's own apply window, `[05:51:33Z–05:56:34Z]`, is disjoint from
the first by **20m38s** — no two `email-booking-intake` applies were ever
concurrent across this receipt's three dispatches. **Risk-map note**: the
deploy singleton is gating (drain-before-fire), not a concurrency lock —
`service-deploy-dispatch.yml` and `service-terraform.yml` use different
concurrency groups (change-warden P-2); the enumeration above, not the
existence of a lock primitive, is what rules out a race here.

## §3 DIAGNOSIS — Deploy Lambda job failure (STOP point; no re-fire attempted)

**Named error, verbatim** [bash-probe: `gh run view 34809228564 --repo autom8y/autom8y --log-failed`]:

```
Error: creating SNS Topic (autom8-ebi-office-floor-scratch): operation error SNS:
CreateTopic, https response error StatusCode: 400, RequestID:
4255d8f5 (E-7: UUID truncated to first 8 chars), InvalidParameter: Invalid parameter: Tags
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

**The 26-minute v70 window was behaviour-identical (E-6, change-warden).**
Alias `live` served v70 (image tag `4e8e163`) from `05:26:57Z` to
`05:52:27Z` — ~26 minutes. `git diff --name-only 0850228f..4e8e163f --
services/email-booking-intake/src ':(exclude)*office_floor*'` returns **0
files** — PR #2205 added the `office_floor` subpackage and its Terraform
but touched NO existing service source file. v70 was tag-different but
behaviour-identical to the prior `0850228` image on every code path other
than the not-yet-wired `office_floor` package; the 26-minute window carried
no runtime risk to live intake traffic.

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

## §3d THIRD RUN — cure #2211, dispatch, and SUCCESS

**Cure PR #2211** ("test(ebi): registry row may carry the office-floor
birth-state entry (S1.5 roll-forward 2)"), `services/email-booking-intake/tests/**`-only,
reconciles the two tests named in §3c by splitting the expectation into a
`live` set (`_EXPECTED_SOURCES`, unchanged) and a `pending` set
(`_EXPECTED_PENDING = {"autom8-email-booking-intake-office-floor"}`),
asserted independently. **MERGED `2026-09-14T05:45:36Z`** as **`21d43951`**.
[bash-probe: `gh pr view 2211 --json state,mergedAt,mergeCommit`; diff via
`gh pr diff 2211`]

**Third dispatch: run `34810812077` at `21d43951`, `workflow_dispatch`,
started `05:45:49Z`. RUN CONCLUSION: `success`.** [bash-probe: `gh run view
34810812077 --repo autom8y/autom8y --json status,conclusion,jobs`, polled by
this station's own watch loop from discovery through terminal state]

| Job | Window | Conclusion |
|---|---|---|
| Detect Changes | — | success |
| CI (email-booking-intake) / Run Tests | 05:46:12Z → 05:47:57Z | **success** (the registry-pin twin from §3c is resolved) |
| Build (email-booking-intake) / Build and Push | 05:48:00Z → 05:51:30Z | success |
| **Deploy Lambda (email-booking-intake) / Deploy Lambda via Terraform** | 05:51:33Z → 05:56:34Z | **success** |
| Smoke Advisory (email-booking-intake) | — | success (advisory) |
| Deploy Summary | — | success |

**Own-hands confirmation the apply actually created the full graph** (read
after the run's own `completed`/`success` status, not inferred from it):
the SNS topic exists, the office-floor function exists, both freshness-deadman
alarms exist, and the intake alias moved again — see §4, rewritten in place
below to report this run's realized output rather than run 1's failure state.

**Roll-forward chain, complete:**

1. `4e8e163f` (PR #2205, merged 05:19:36Z) → run `34809228564` → **FAILED**
   05:30:50Z (apply: SNS `CreateTopic` tag-character defect, §3). The four
   pre-existing consumers and the intake alias (→ v70, tag `4e8e163`) had
   already updated successfully before the topic error surfaced.
2. `d408a38c` (PR #2210, tag-fix, merged 05:35:47Z) → run `34810338540` →
   **FAILED** 05:40:01Z (tests: registry-pin four-vs-five contradiction,
   §3c). Build/Deploy never reached; no new AWS state (alias confirmed still
   v70/`4e8e163` at the between-runs read, §3b).
3. `21d43951` (PR #2211, test-reconciliation, merged 05:45:36Z) → run
   `34810812077` → **SUCCESS** 05:57:00Z. Alias now v71, tag `21d4395`; the
   office-floor evaluator and its full freshness-deadman module exist.

## §4 AFTER-READ — item by item, against the SUCCESSFUL run `34810812077`

Every claim below is an own-hands AWS read taken AFTER the run reached
`completed`/`success` (or is explicitly marked "main-thread read,
05:57:40Z" where this station consumed a reading taken by the coordinating
thread rather than re-deriving it itself, per the turn-budget instruction).

### (2) alias `live`, the new function, unanimity

- **alias `live`** (`autom8-email-booking-intake`): **version 71**, served
  image tag **`21d4395`** (== `21d43951` merge commit short form),
  `LastModified 2026-09-14T05:52:27Z`, 46 env vars. [bash-probe: `aws lambda
  get-alias` + `get-function --qualifier live` + `get-function-configuration
  --qualifier live`, own-hands] Between v70 (`4e8e163`,
  05:26:57Z-05:52:27Z) and v71 (`21d4395`), the intake image changed for the
  registry-pin test fix and the SNS-tag fix only — see E-6 (§3b) for the
  own-hands diff proving v70 itself was behaviour-identical to the prior
  `0850228` build on every path outside `office_floor`.
- **the office-floor function**: **BORN.** `aws lambda get-function
  --function-name autom8-email-booking-intake-office-floor` (unqualified —
  it carries no alias, so `$LATEST` IS its served object, per the preserve-
  fuel registry's own documented rule for this function): `State: Active`,
  image tag **`21d4395`**, `LastModified 2026-09-14T05:52:27.155Z`,
  `ReservedConcurrentExecutions: 1` (matches `reserved_concurrency = 1` in
  `office_floor.tf`). [bash-probe, own-hands]
- **UNANIMITY HOLDS, all five, at the `21d43951` build**: office-floor
  `21d4395` == intake alias-served `21d4395` == `contente-reconcile`
  `21d4395` == `forwarding-nudge` `21d4395` == `contente-retro-redrive`
  `21d4395` (each independently re-read via `aws lambda get-function
  --function-name {fn} --query "{ImageUri:Code.ImageUri,...}"`, own-hands).
  This is the four-way-plus-one check §3b pre-registered before the outcome
  was known; it is satisfied.
- **its env**: `EMAIL_BOOKING_INTAKE_OFFICE_FLOOR_PAGE_TOPIC_ARN` ==
  `arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch` — the
  scratch topic, exactly as R-168 specifies while the consumer word is
  withheld. [bash-probe: `aws lambda get-function-configuration --query
  "Environment.Variables.EMAIL_BOOKING_INTAKE_OFFICE_FLOOR_PAGE_TOPIC_ARN"`,
  own-hands]
- **the EventBridge rule**: `autom8-email-booking-intake-office-floor-schedule`
  (confirmed by reverse lookup — `aws events list-rule-names-by-target
  --target-arn {office-floor function arn}` returns exactly this one name,
  own-hands, independent of the name guessed from the Terraform source),
  `State: ENABLED`, `rate(1 hour)`, and now — unlike the failed run 1 state —
  **targets the function**: `list-targets-by-rule` returns one target, Id
  `autom8-email-booking-intake-office-floor-target`, `Arn` the office-floor
  function, with its own `DeadLetterConfig` (the DLQ) and `RetryPolicy`
  (`MaximumRetryAttempts: 2`, `MaximumEventAgeInSeconds: 3600`). [bash-probe,
  own-hands]

### (3) SNS topic `autom8-ebi-office-floor-scratch`

**EXISTS** — `arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch`.
`list-subscriptions-by-topic` → **`{"Subscriptions": []}`** — zero
subscriptions, confirmed own-hands. The scratch design holds exactly as
built: a real, addressable topic that pages nobody. [bash-probe: `aws sns
list-topics` + `list-subscriptions-by-topic`, own-hands]

**Realized-output containment proof (E-3, change-warden).** CloudWatch
metrics on the topic show `NumberOfMessagesPublished = 3` in the post-apply
window, while `NumberOfNotificationsDelivered` and
`NumberOfNotificationsFailed` carry **no datapoints at all** — consistent
with zero subscriptions (nothing to deliver to or fail against). The 3
publishes are attributed to the S1.4b station's own controlled invokes at
≈`06:00Z`, **not to a scheduled fire** (the schedule's first tick is
≈`06:27Z`, after these publishes) — a controlled-test signature, named as
such rather than left ambiguous.

### (4) Alarm diff — two-sided, against `alarms_before.json`

- **Before**: **13** pre-existing alarms, RECONCILED per §1 (E-1): 11 at
  the `autom8-email-booking-intake` prefix (the captured `alarms_before.json`
  baseline) + 2 at the `autom8-ebi-contente-reconcile-*` prefix (an earlier,
  unrelated wave) = 13. Both the dispatch brief's 13 and this station's own
  11-count file-read were correct at their own prefix scope; neither was in
  error.
- **After — pre-existing set unchanged**: own-hands re-read of
  `autom8-email-booking-intake*` (excluding `office-floor`) returns the
  identical 11-name set with `Actions`/`OKActions` still exactly
  `arn:aws:sns:us-east-1:<ACCOUNT>:autom8y-platform-alerts` on every one — no
  drift. [bash-probe: `aws cloudwatch describe-alarms --alarm-name-prefix
  autom8-email-booking-intake --query "...[?!contains(AlarmName,
  'office-floor')]..."`, own-hands]
- **New alarms — exactly four, all scratch-only**:
  - `autom8-email-booking-intake-office-floor-lambda-errors` — Actions =
    scratch topic ARN only.
  - `autom8-email-booking-intake-office-floor-dlq-not-empty` — Actions =
    scratch topic ARN only.
  - `autom8-ebi-booking-floor-lambda-freshness` — Actions = scratch topic ARN
    only. Read at `05:57:45Z`: `StateValue: INSUFFICIENT_DATA` (expected —
    the alarm's evaluation window had not yet accumulated 2-of-3 datapoints
    since apply). **Update (E-2, change-warden re-read): transitioned
    INSUFFICIENT_DATA → OK at `2026-09-14T06:04:56Z`** — the prober's gauge
    reached 2-of-3 fresh datapoints and the alarm evaluated healthy, the
    expected steady state once the module ages past its bootstrap window.
  - `autom8-ebi-booking-floor-freshness-prober-liveness` — Actions = scratch
    topic ARN only, `StateValue: INSUFFICIENT_DATA` (same reason; the
    prober-seed invocation fires once at apply, one datapoint is not yet
    2-of-3).
  All four confirmed own-hands via `aws cloudwatch describe-alarms
  --alarm-names ...` / `--alarm-name-prefix ...`. **No alarm anywhere newly
  references `autom8y-platform-alerts`** — every new alarm's actions are the
  scratch ARN, confirmed by literal string match on each `Actions` array.
- **Success-gap alarm — confirmed ABSENT**, as designed (deferred to S1.7):
  `aws cloudwatch describe-alarms --alarm-names
  autom8-ebi-booking-floor-invoke-success-gap` → empty result. [bash-probe,
  own-hands]

### (5) IAM — all four IAM grants present

Role `autom8-email-booking-intake-office-floor-lambda-role`:
- **Attached managed policies (3)**: `AWSLambdaBasicExecutionRole`,
  `AWSXRayDaemonWriteAccess`, and now **`autom8-email-booking-intake-office-floor`**
  (the custom policy — ABSENT in the failed-run state, PRESENT now).
- **Custom policy, all FOUR statements confirmed** (`aws iam
  get-policy-version`, own-hands): `StartInsightsQueryOnTheIntakeLogGroup`
  (`logs:StartQuery`), `ReadBackInsightsResults` (`logs:GetQueryResults`),
  `PublishTheDigestOrTheRefusal` (`sns:Publish`),
  `PublishTheSuccessTimestampInItsOwnNamespaceOnly`
  (`cloudwatch:PutMetricData`) — exactly the 4-grant design from
  `office_floor.tf`'s own comment ("FOUR grants, not two").
- **Inline DLQ policy** (`autom8-email-booking-intake-office-floor-dlq`):
  `sqs:SendMessage`, `sqs:GetQueueAttributes` — the base module's DLQ grant,
  unchanged in shape from the failed-run reading.

### (6) First evaluation — UV-P DISCHARGED (E-4, change-warden re-read)

The S1.4b station's controlled invokes (source of the 3 SNS publishes,
§4(3)) produced two real `office_floor_evaluated` records, read from
`/aws/lambda/autom8-email-booking-intake-office-floor`:

- **`2026-09-14T06:00:27.692Z`** — `dry_run: false`, `control: passed`,
  `records_scanned: 14002`, **39 offices evaluated, 31 with bookings**,
  `paged: false` (correct — hour 06 != the page-gate hour 11 UTC).
- **`2026-09-14T06:00:48.820Z`** — a negative-control run:
  `records_scanned_below_floor`, distinct from the main evaluation above.

Both are CONTROLLED invokes (S1.4b), not the scheduled `rate(1 hour)` fire —
the schedule rule was created `05:26:57Z` by the first (failed) run, so its
first SCHEDULED tick is still expected ≈`06:27Z`. **The original UV-P (any
controlled evaluation) is DISCHARGED** by the two records above; the residual
narrows to one remaining, more specific gap:

`[UV-P: the first SCHEDULED (rate(1 hour), not controlled-invoke)
office_floor_evaluated firing | METHOD: main-thread or follow-up read at or
after ~06:27Z | REASON: unobserved at this receipt's writing (~06:1xZ); the
two 06:00Z records above are controlled invokes, not the schedule's own
first tick]`

### (7) The other four Lambdas — confirmed at the `21d43951` build

`contente-reconcile`, `forwarding-nudge`, `contente-retro-redrive`: each
own-hands re-read now reports image tag `21d4395`, matching the intake alias
and the office-floor function. The whole-stack apply resolved ONE tag across
all five consumers this time — the split-fuel condition named as the risk in
§3b did not occur.

## §5 Pending set as applied — final state

- **#2200** (`a1f3ecf3`, deploy-and-pin single-act): applied hours before
  this dispatch; undisturbed throughout.
- **#2205** (`4e8e163f`): code landed at merge; its OWN terraform apply
  failed (§3). Superseded by the roll-forward.
- **#2207** (registry `pending:` coverage entry): landed, `scripts/`-only,
  correct in isolation but incomplete — missed the service-local twin test
  (§3c).
- **#2210** (`d408a38c`, SNS tag-character fix): landed, necessary, but not
  sufficient alone — CI failed on the registry-pin twin before this fix's
  apply could even be attempted (§3c).
- **#2211** (`21d43951`, registry-pin twin reconciliation): landed; with
  BOTH #2210 (the runtime fix) and #2211 (the test fix) on `HEAD`, run
  `34810812077` carried every required change simultaneously and succeeded.
  **The office-floor evaluator is now BORN, unarmed exactly as R-168
  specifies, and unanimous with its four siblings at the `21d43951` build.**

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

**S1.5 LANDED, on the third dispatch.** The completeness invariant is
asserted on the REALIZED output, own-hands, after the fact — not on the
merge event, not on CI-green, not on any intermediate label:

- The Lambda function `autom8-email-booking-intake-office-floor` **EXISTS**,
  `Active`, image tag `21d4395`.
- Its schedule rule **targets it** (not target-less, as in the failed-run
  debris).
- Its custom IAM policy (all four grants) **is attached**.
- Its scratch SNS topic **exists with zero subscriptions** — unarmed exactly
  as R-168 specifies, not "does not exist" as the failed-run state left it.
- Its freshness deadman (prober + two alarms) **exists**, pointed at the
  scratch topic only; read at `05:57:45Z` both alarms were
  `INSUFFICIENT_DATA` (too young to have 2-of-3 datapoints yet), and
  `autom8-ebi-booking-floor-lambda-freshness` is confirmed to have since
  transitioned to `OK` at `2026-09-14T06:04:56Z` (E-2, change-warden
  re-read) — the deadman is not just present, it has proven it evaluates.
- Unanimity **holds** across all five `var.image_tag` consumers at the
  `21d43951` build.
- No pre-existing alarm's actions changed; no success-gap alarm was created
  early.

**The sole discriminator this receipt named up front — "does the Lambda
function `autom8-email-booking-intake-office-floor` exist in AWS?" — now
reads YES**, own-hands verified, not inferred from the green run conclusion.

**Two real, distinct defects were found and cured in the roll-forward, named
so neither is lost to a "third time's the charm" narrative:**
1. An SNS tag-character validation error in `office_floor.tf`'s `Purpose`
   tag (parentheses) — a plain infrastructure-as-code defect, invisible to
   every test in this repo because none of them exercise a live `terraform
   apply` against AWS's tag validator.
2. A registry-consistency test split across two files
   (`scripts/tests/test_apply_preserve_fuel.py` and
   `services/email-booking-intake/tests/test_ebi_image_pin_currency.py`)
   that PR #2207 updated only one half of — the required, service-local CI
   gate caught what the non-required, repo-root gate's own cure had missed.

**Residual for the operator/architect, not executed by this read-only
station**: the first controlled `office_floor_evaluated` run is DISCHARGED
(§4(6), E-4 — two real records at `06:00:27.692Z` and `06:00:48.820Z`). The
narrowed residual is the first SCHEDULED (`rate(1 hour)`) firing, expected
≈`06:27Z` and unobserved at this receipt's writing; handed to the main
thread for that read.

## §8 Redaction check (merge-surface sweep class `digits12`)

Every AWS account id in this document is replaced with the literal
`<ACCOUNT>`. The GitHub run id (11 digits, `34809228564`) is left intact per
the coordinator's ruling (autom8y #2203 precedent) — it is not account-shaped.
Per-job GitHub ids (which run 12 digits) are deliberately NOT cited anywhere
in this document by their raw digit string, precisely because they would
trip the same `digits12` class the coordinator named; job identity above is
conveyed by job NAME only.

**Classes checked (E-7, change-warden — named explicitly, not left implicit)**:
(1) **12+ digit numeric tokens** (`digits12`) — the AWS account id class,
swept via `grep -n -E '[0-9]{12,}'`, must print nothing; (2) **phone-number
shapes** — no phone digits appear anywhere in this receipt (none were ever
sourced; the office-floor evaluator's own data is guid8-keyed, never
phone-keyed); (3) **full GUIDs/UUIDs** (36-char dashed form) — the one
instance found, the SNS `RequestID` in §3's error text, is truncated to its
first 8 characters per E-7 rather than quoted in full, since a full UUID is
its own distinguishing/re-identifying token class independent of digit
count. The merge-commit sha in §1 is likewise truncated 40→8 chars (E-7).
Verified below (§9).

## §9 Reap

Session AWS credentials used were the ambient read-only profile already
active in this shell; no credentials were minted, rotated, or written. The
worktree at `.knossos/worktrees/wt.dre.s1-5-deploy-receipt.20260914T052622Z.bcdb`
is reaped (`git worktree remove`) immediately after the PR is opened from its
branch tip; the branch itself is left for the PR.

