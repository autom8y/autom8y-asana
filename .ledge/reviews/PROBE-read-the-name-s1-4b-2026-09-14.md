# PROBE — S1.4b POST-DEPLOY LIVE PROBE of the S-1 per-office booking-floor evaluator

**Station**: chaos-engineer (sre, co-seated) · **Wave**: `read-the-name` wave 1 · **Date**: 2026-09-14
**Region**: us-east-1 · **Object**: Lambda `autom8-email-booking-intake-office-floor` (`$LATEST` IS the
served object — no alias exists; every configuration read below is unqualified and therefore reads the
served object)

**Refs named** (per the substrate-of-record fence — every repo read is `git show origin/main:<path>`):

| Repo | Ref | SHA |
|---|---|---|
| `autom8y` | `origin/main` | `21d439515fb49ed7398e11f0a49f73f759fb1720` |
| `autom8y-asana` | `origin/main` | `2ef49ff60e55a54e760c6b49dc522fe4a079c593` |

**Fences honoured**: guid8 only (no raw office names, no phone digits anywhere in this artifact — the
live digest body DOES carry office names and is quoted here with them elided); the AWS account id
appears nowhere (`<ACCOUNT>` in every ARN); no worktree or `.terraform/` read; every `rc` unpiped.

**What was NOT touched**: terraform, the alarms, the SNS topic, the EventBridge schedule, and every
other function. This probe made three `RequestResponse` invokes of one function and otherwise only read.

---

## §0 The page-gate fence, verified in source BEFORE any invoke

Read in full at `autom8y` `origin/main:services/email-booking-intake/src/email_booking_intake/office_floor/handler.py`.

```
structural_verification_receipt:
  claim: "no invoke made by this probe can publish a page, because the page gate conjoins the UTC hour with the dry_run flag and the handler exposes no force-page lever"
  verification_method: file-read
  verification_anchor:
    source: "git show origin/main:services/email-booking-intake/src/email_booking_intake/office_floor/handler.py  (autom8y @ 21d43951)"
    marker_token: "page_gate = (now.astimezone(UTC).hour == config.page_hour_utc) and not dry_run"
    claim: "the publish is reached only under page_gate; the event contract parsed by resolve_window and evaluate is exactly {dry_run, window_start, window_end}, so no event key can force a publish"
```

Three independent enforcers, all read in source, all confirmed live:

1. **Hour gate** — `page_hour_utc` = `11` (env `EMAIL_BOOKING_INTAKE_OFFICE_FLOOR_PAGE_HOUR_UTC=11`,
   read live). Every invoke below ran in the 06:00Z hour.
2. **dry_run gate** — `and not dry_run`.
3. **No lever** — the only event keys consumed are `dry_run`, `window_start`, `window_end`.

All three legs returned `paged: false`, `page_class: "none"`, and `idempotence_status: "not-checked"`
(the ledger read is itself behind the page gate). §7 proves the SNS counter did not move.

---

## §1 The object as read (unqualified `$LATEST`)

`aws lambda get-function-configuration --function-name autom8-email-booking-intake-office-floor --region us-east-1`

| Field | Value |
|---|---|
| `FunctionArn` | `arn:aws:lambda:us-east-1:<ACCOUNT>:function:autom8-email-booking-intake-office-floor` |
| `Version` | `$LATEST` (no alias; served object) |
| `LastModified` | `2026-09-14T05:52:27.155+0000` |
| `CodeSha256` | `7d84017c86a674082308b9d59ca676f69648857bcbbc8cee0e9c13f06ca78b1e` |
| `PackageType` / `Timeout` / `MemorySize` | `Image` / `300` s / `512` MB |
| `State` / `LastUpdateStatus` | `Active` / `Successful` |
| `Role` | `arn:aws:iam::<ACCOUNT>:role/autom8-email-booking-intake-office-floor-lambda-role` |
| `ReservedConcurrentExecutions` | `1` (`aws lambda get-function-concurrency`) |

Env (the load-bearing subset, read live): `..._LOG_GROUP=/aws/lambda/autom8-email-booking-intake`,
`..._SELF_LOG_GROUP=/aws/lambda/autom8-email-booking-intake-office-floor`,
`..._METRIC_NAMESPACE=Autom8y/EbiOfficeFloor`, `..._WINDOW_DAYS=3`,
`..._BOOKING_LOOKBACK_DAYS=30`, `..._PAGE_HOUR_UTC=11`,
`..._PAGE_TOPIC_ARN=arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch`.

**R-168 NOT ARMED, verified live, not assumed**:
`aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch`
→ `{"Subscriptions": []}`. Zero subscribers. Nothing in this probe could reach a human even had a
publish occurred.

---

## §2 LEG A — HEALTHY, cold start · payload `{}` · **CONTROL PASSED on BOTH queries**

```
aws lambda invoke --function-name autom8-email-booking-intake-office-floor \
  --invocation-type RequestResponse --cli-read-timeout 330 --payload '{}' \
  --cli-binary-format raw-in-base64-out --log-type Tail --region us-east-1 out.json
rc=0
```
Sent `2026-09-14T06:00:17Z`, returned `2026-09-14T06:00:27Z`.

### Response body (verbatim, office names elided per fence)

```json
{"control": "passed", "kind": "", "paged": false, "page_class": "none",
 "zero_floor_count": 3, "rate_floor_count": 0, "offices_evaluated": 39, "records_scanned": 14002,
 "verdicts": [
   {"guid8": "e63bbbe0", "floor_class": "zero", "arrivals": 9, "bookings": 0, "rate": 0.0, "lines": 26, "mails": 8, "day_n": 7, "last_booking_age_days": null, "offer_class": "unknown"},
   {"guid8": "40f86e73", "floor_class": "zero", "arrivals": 8, "bookings": 0, "rate": 0.0, "lines": 10, "mails": 0, "day_n": 4, "last_booking_age_days": null, "offer_class": "inactive"},
   {"guid8": "8a9b1a84", "floor_class": "zero", "arrivals": 7, "bookings": 0, "rate": 0.0, "lines": 18, "mails": 4, "day_n": 5, "last_booking_age_days": null, "offer_class": "unknown"}],
 "residual": {"lines": 62, "mails": 10, "arrivals": 26, "share": 0.0746, "high": false},
 "body": "<FLOOR-DIGEST render; carries office names, elided>"}
```

### REPORT line

```
REPORT RequestId: 204de4df-a6ee-4c91-a90e-d886a7dc5e18  Duration: 7417.37 ms
  Billed Duration: 9261 ms  Memory Size: 512 MB  Max Memory Used: 135 MB  Init Duration: 1843.36 ms
```

**The cold-start UV-P is DISCHARGED.** Cold `lambda_handler` constructed all three boto3 clients and
completed BOTH bounded Insights queries (3-day primary + 30-day lookback, 605,299 records scanned) in
**7.42 s against a 300 s timeout — 2.5% of budget**, at **135 MB of 512 MB — 26%**. Init 1.84 s.
Headroom is ~40x on time and ~3.8x on memory.

### The `office_floor_evaluated` line

Fetched with `aws logs filter-log-events --log-group-name /aws/lambda/autom8-email-booking-intake-office-floor --start-time 1789099200000 --filter-pattern '"office_floor_evaluated"' --limit 20 --region us-east-1` (**one page**; page 2 via `--next-token` returned `0` events and **no** further token, so the three lines below are the COMPLETE filtered set for the group, not a truncation):

```json
{"window_start": "2026-09-11T06:00:22.812663+00:00", "window_end": "2026-09-14T06:00:22.812663+00:00",
 "window_days": 3, "arrival_unit": "U-3", "query_status": "Complete", "records_scanned": 14002,
 "records_matched": 831, "bytes_scanned": 3798559, "estimated_records_skipped": 0,
 "log_groups_scanned": 1, "offices_evaluated": 39, "offices_with_bookings": 31,
 "control_status": "pass", "control_reason": "", "snapshot_date": "2026-09-11", "snapshot_age_days": 3,
 "evaluator_version": "s1.3", "dry_run": false, "control": "passed", "kind": "",
 "zero_floor_count": 3, "rate_floor_count": 0, "residual_lines": 62, "residual_mails": 10,
 "residual_share": 0.0746, "residual_share_high": false, "day_n_query_status": "Complete",
 "day_n_records_scanned": 605299, "day_n_records_matched": 4734, "day_n_bytes_scanned": 155743245,
 "day_n_estimated_records_skipped": 0, "day_n_log_groups_scanned": 1, "booking_lookback_days": 30,
 "stall_count": 0, "dedup_inert": true, "paged": false, "page_class": "none",
 "idempotence_status": "not-checked", "pages_today": 0, "evaluations_today": 0,
 "event": "office_floor_evaluated", "level": "info", "timestamp": "2026-09-14T06:00:27.692777Z"}
```

### The D2 in-run control, checked on BOTH queries

| ADR D2 predicate | Primary (3d) | Lookback (30d) | Verdict |
|---|---|---|---|
| `status == Complete` | `Complete` | `Complete` | PASS |
| `records_scanned >= 500` | `14002` | `605299` (and `>= primary`, the relative floor) | PASS |
| `offices_with_bookings >= 5` | `31` | (inherits primary) | PASS |
| `estimated_records_skipped == 0` | `0` | `0` | PASS |
| `log_groups_scanned >= 1` | `1` | `1` | PASS |

**LEG A CONTROL STATUS: PASSED on both queries.** `day_n_records_scanned = 605,299` is within 0.03% of
the S1.4a pre-deploy in-process measurement of 605,145 (PROBE §9) — the same read under Lambda's
network and memory profile, not a different one.

### Parity against S1.1's window-B receipts

The live window is `2026-09-11T06:00Z..2026-09-14T06:00Z`, not S1.1's window B, so the firing set
differs — as expected, and it differs **explicably**:

- **Firing set (3 offices, all ZERO, 0 RATE)**: `e63bbbe0` (9 arrivals, 0 bookings, `day_n=7`,
  class `unknown`), `40f86e73` (8/0, `day_n=4`, class `inactive`), `8a9b1a84` (7/0, `day_n=5`,
  class `unknown`). All three clear `ZERO_FLOOR_MIN_ARRIVALS = 5` with `bookings == 0`
  (`floors.py:37`, `floors.py:242-244`).
- **`ccb52f4c`, the founding office, is EVALUATED and correctly `quiet`.** Its live
  `office_floor_office` line: `arrivals=93, bookings=3, booking_rate=0.032258, floor_class=quiet,
  offer_class=active, day_n=1, last_booking_age_days=0`. The RATE floor is
  `arrivals >= 20 AND rate < 0.025` (`floors.py:43,48,245-246`); 3.23% is **above** 2.5%, so `quiet`
  is the arithmetically correct verdict. S1.1 measured this office at 2.02% in window B — the
  classifier has not changed; the traffic has. `day_n=1` says it WAS below a floor in the
  immediately-preceding day-aligned window, which is the counter working, not a defect.
- **CLASS UNKNOWN is populated on live traffic** (`e63bbbe0`, `8a9b1a84` above the ZERO floor with
  `offer_class=unknown`) — PROBE §11.1 **C-4's ruled trigger fires on the very first live run**, as
  that record predicted. `offices_unclassified` is still not a field on the run line.

### Two-sided ledger for leg A

`paged: false` · `page_class: none` · SNS counter unmoved (§7) · **exactly one** new
`LastSuccessTimestamp` datapoint (§7).

---

## §3 LEG B — DEGRADED read → **FLOOR-REFUSED** · the withheld-timestamp half, live

**Interval chosen and why.** `window_start=2026-09-14T05:30:00Z`, `window_end=2026-09-14T05:40:00Z` —
a 10-minute interval **inside** retention, not a pre-retention one. `aws logs describe-log-groups`
shows the source group `/aws/lambda/autom8-email-booking-intake` at `retentionInDays = 90`, so a
pre-retention interval would have to reach back > 90 days and its zero would be **indistinguishable
from an infrastructure failure** — an expired window, a wrong group and a broken query all read the
same. The 10-minute interval is the sharper instrument: the query still returns `Complete`, the group
is still scanned (`log_groups_scanned = 1`), nothing is skipped (`estimated_records_skipped = 0`) —
so the refusal is provably a **genuine below-floor read of a live group**, which is the degraded-read
class the control exists to catch.

```
aws lambda invoke ... --payload '{"window_start":"2026-09-14T05:30:00Z","window_end":"2026-09-14T05:40:00Z"}' ...
rc=0
```
Sent `2026-09-14T06:00:45Z`, returned `2026-09-14T06:00:48Z`.

### Response body (verbatim)

```json
{"control": "failed", "kind": "records_scanned_below_floor", "paged": false, "page_class": "none",
 "body": "run     : window=2026-09-14T05:30Z..2026-09-14T05:40Z (3d) | unit=U-3\ncontrol : FAILED | kind=records_scanned_below_floor\n          query_status=Complete | records_scanned=60 | offices_with_bookings=0\n\nno floor verdict was produced for this run\n\nLastSuccessTimestamp is WITHHELD for this run; two consecutive refusals turn the\nsuccess-gap alarm red without any human reading this page."}
```

### REPORT line

```
REPORT RequestId: d61ae2b7-e71d-43a9-9fb1-6d1798e3c6c1  Duration: 2424.77 ms
  Billed Duration: 2425 ms  Memory Size: 512 MB  Max Memory Used: 135 MB
```
(warm — no `Init Duration`.)

### The `office_floor_evaluated` line (same one-page fetch as §2)

```json
{"window_start": "2026-09-14T05:30:00+00:00", "window_end": "2026-09-14T05:40:00+00:00",
 "window_days": 3, "arrival_unit": "U-3", "query_status": "Complete", "records_scanned": 60,
 "records_matched": 5, "bytes_scanned": 19861, "estimated_records_skipped": 0,
 "log_groups_scanned": 1, "offices_evaluated": 1, "offices_with_bookings": 0,
 "control_status": "failed", "control_reason": "records_scanned_below_floor",
 "snapshot_date": "2026-09-11", "snapshot_age_days": 3, "evaluator_version": "s1.3",
 "dry_run": false, "control": "failed", "kind": "records_scanned_below_floor",
 "zero_floor_count": 0, "rate_floor_count": 0, "day_n_query_status": "NotRun",
 "day_n_records_scanned": 0, "day_n_records_matched": 0, "day_n_bytes_scanned": 0,
 "day_n_estimated_records_skipped": 0, "day_n_log_groups_scanned": 1,
 "residual_lines": 0, "residual_share": 0.0, "paged": false, "page_class": "none",
 "idempotence_status": "not-checked", "pages_today": 0,
 "event": "office_floor_evaluated", "level": "error", "timestamp": "2026-09-14T06:00:48.820417Z"}
```

### Why this is a non-vacuous refusal (the zero is comparable to a control)

`records_scanned = 60` over 10 minutes against leg A's `14002` over 4320 minutes — leg A's rate is
3.24 records/min, so ~32 records were the expectation and 60 were observed: the **same order of
magnitude**, on the same group, in the same hour. The window is small, the read is healthy, and the
control refuses anyway. That is the control biting on a **measured** insufficiency, not on a broken
query. The refusal names its kind — `records_scanned_below_floor` — and `day_n_query_status = NotRun`
proves the second ~155 MB read was correctly skipped once the primary had already failed.

**LEG B REFUSAL: `FLOOR-REFUSED` / `kind = records_scanned_below_floor`** · `paged: false` ·
`page_class: none` · **NO** `LastSuccessTimestamp` datapoint (§7) · no publish (§7).
**The deadman's withheld-timestamp half is proven LIVE**, not in-process.

---

## §4 LEG C — DRY RUN · payload `{"dry_run": true}`

```
aws lambda invoke ... --payload '{"dry_run": true}' ...   rc=0
```
Sent `2026-09-14T06:01:02Z`, returned `2026-09-14T06:01:07Z`.

```
REPORT RequestId: c8e7680c-f602-47c8-ba89-50475054f48e  Duration: 4946.06 ms
  Billed Duration: 4947 ms  Memory Size: 512 MB  Max Memory Used: 136 MB
```

Response (elided of `body`/`verdicts` detail): `control=passed`, `kind=""`, `paged=false`,
`page_class=none`, `zero_floor_count=3`, `rate_floor_count=0`, `offices_evaluated=39`,
`records_scanned=14002`, residual `{lines:62, mails:10, arrivals:26, share:0.0746, high:false}`.
Verdict set identical to leg A: `e63bbbe0`/zero/9/0/day_n=7/unknown · `40f86e73`/zero/8/0/day_n=4/inactive ·
`8a9b1a84`/zero/7/0/day_n=5/unknown.

Its `office_floor_evaluated` line carries `"dry_run": true`, `control_status: "pass"`,
`records_scanned: 14002`, `day_n_records_scanned: 605299`, `day_n_query_status: "Complete"`,
`paged: false`, `page_class: "none"` (timestamp `2026-09-14T06:01:07.792059Z`).

**Full evaluation logged; no metric emission; no publish.** The evaluation is complete and identical
to the controlled run — the dry_run flag withholds the two SIDE EFFECTS (`put_metric_data`, `publish`)
and nothing else. That is the correct shape: the gate withholds the writer, never the measurement.

---

## §5 LEG D — THE SCHEDULED FIRE · **the EventBridge UV-P is DISCHARGED**

### The rule, read (not assumed)

```
aws events describe-rule --name autom8-email-booking-intake-office-floor-schedule --region us-east-1
aws events list-targets-by-rule --rule autom8-email-booking-intake-office-floor-schedule --region us-east-1
```

| Field | Value |
|---|---|
| `ScheduleExpression` | `rate(1 hour)` |
| `State` | **`ENABLED`** |
| `EventBusName` | `default` |
| Target `Arn` | `arn:aws:lambda:us-east-1:<ACCOUNT>:function:autom8-email-booking-intake-office-floor` |
| Target `Input` | `{"detail":{"environment":"production","schedule":"rate(1 hour)","service":"autom8-email-booking-intake-office-floor"},"detail-type":"Scheduled Event","source":"aws.events"}` |
| Target `DeadLetterConfig` | `arn:aws:sqs:us-east-1:<ACCOUNT>:autom8-email-booking-intake-office-floor-dlq` |
| Target `RetryPolicy` | `MaximumRetryAttempts: 2`, `MaximumEventAgeInSeconds: 3600` |

The scheduled `Input` carries **no** `dry_run` and **no** `window_start`/`window_end`, so the
scheduled fire takes exactly leg A's code path — the default 3-day rolling window, `dry_run` false.

### The fire HAPPENED, at 06:27:15Z, and it is NOT one of mine

**Request-id disjointness (the match key).** The scheduled invocation's request id is
`7a72a5f0-a17f-409b-b5d0-70704911ba46`. My three are `204de4df-a6ee-4c91-a90e-d886a7dc5e18` (A),
`d61ae2b7-e71d-43a9-9fb1-6d1798e3c6c1` (B), `c8e7680c-f602-47c8-ba89-50475054f48e` (C). No overlap.
It also landed in a **different log stream** — `2026/09/14/[$LATEST]33e4c83f<...>` (first event `06:27:07.097Z`) versus my legs' `...b1469228<...>` (first event
`06:00:18.610Z`) — a fresh execution environment, which the `Init Duration` below independently
confirms.

```
START  RequestId: 7a72a5f0-a17f-409b-b5d0-70704911ba46 Version: $LATEST
REPORT RequestId: 7a72a5f0-a17f-409b-b5d0-70704911ba46  Duration: 7640.03 ms
  Billed Duration: 8841 ms  Memory Size: 512 MB  Max Memory Used: 136 MB  Init Duration: 1200.75 ms
```

### Its `office_floor_evaluated` line

Fetched with `aws logs filter-log-events --log-group-name /aws/lambda/autom8-email-booking-intake-office-floor --start-time 1789365700000 --filter-pattern '"office_floor_evaluated"' --limit 20 --region us-east-1` (**one page**; 1 event returned):

```json
{"window_start": "2026-09-11T06:27:10.634146+00:00", "window_end": "2026-09-14T06:27:10.634146+00:00",
 "window_days": 3, "arrival_unit": "U-3", "query_status": "Complete", "records_scanned": 13979,
 "records_matched": 831, "bytes_scanned": 3792385, "estimated_records_skipped": 0,
 "log_groups_scanned": 1, "offices_evaluated": 39, "offices_with_bookings": 31,
 "control_status": "pass", "control_reason": "", "snapshot_date": "2026-09-11", "snapshot_age_days": 3,
 "evaluator_version": "s1.3", "dry_run": false, "control": "passed", "kind": "",
 "zero_floor_count": 3, "rate_floor_count": 0, "residual_lines": 62, "residual_mails": 10,
 "residual_share": 0.0746, "residual_share_high": false, "day_n_query_status": "Complete",
 "day_n_records_scanned": 605303, "day_n_records_matched": 4737, "day_n_bytes_scanned": 155747346,
 "day_n_estimated_records_skipped": 0, "day_n_log_groups_scanned": 1, "booking_lookback_days": 30,
 "stall_count": 0, "dedup_inert": true, "paged": false, "page_class": "none",
 "idempotence_status": "not-checked", "pages_today": 0, "evaluations_today": 0,
 "event": "office_floor_evaluated", "level": "info", "timestamp": "2026-09-14T06:27:15.835119Z"}
```

**Control status: PASSED on both queries** — `Complete`/`Complete`, `records_scanned = 13,979 >= 500`,
`day_n_records_scanned = 605,303 >= 13,979`, `offices_with_bookings = 31 >= 5`, nothing skipped.
`paged: false`, `page_class: none` (06:27Z is not hour 11).

**Its metric datapoint**: `LastSuccessTimestamp` gained a second datapoint at the 06:27Z minute,
`SampleCount = 1`, `Maximum = 1789367235` — epoch 1789367235 is `2026-09-14T06:27:15Z`, matching the
run line's `06:27:15.835119Z`. The schedule's evaluation emitted the timestamp on its own.

**Cadence**: the rule was created `05:26:56Z` (the log group's `creationTime` is `1789363616713`), the
first scheduled fire landed `06:27:07Z` — one hour later, as `rate(1 hour)` specifies. The verdict set
reproduced leg A's exactly (39 offices evaluated, 3 ZERO, 0 RATE, residual share 7.46%) 27 minutes
later against a 23-record-larger window, which is the evaluator being stable under a moving window,
not a coincidence.

---

## §7 THE TWO-SIDED LEDGER — every metric and publish, before and after

### `Autom8y/EbiOfficeFloor` / `LastSuccessTimestamp`

`aws cloudwatch get-metric-statistics --namespace Autom8y/EbiOfficeFloor --metric-name LastSuccessTimestamp --start-time 2026-09-14T00:00:00Z --end-time <T> --period 60 --statistics SampleCount Maximum --region us-east-1`

| Read at | Datapoints |
|---|---|
| `2026-09-14T05:59:57Z` (BEFORE every leg) | `[]` — **zero** |
| `2026-09-14T06:01:34Z` (after legs A, B, C) | **one**: 06:00Z minute, `SampleCount=1`, `Maximum=1789365627` (= 06:00:27Z) |
| `2026-09-14T06:36:49Z` (after leg D) | **two**: the above, plus 06:27Z minute, `SampleCount=1`, `Maximum=1789367235` (= 06:27:15Z) |

**Four invocations, two datapoints.** Leg A (controlled, not dry) emitted. Leg D (controlled, not dry)
emitted. **Leg B (FLOOR-REFUSED) emitted nothing. Leg C (dry_run) emitted nothing.** That is the
withheld-timestamp wire proven two-sided on live infrastructure: it fires when it should and is silent
when it should be, and the silence is a *measured* absence — the same read that shows leg A's datapoint
shows leg B's and leg C's absence.

### `AWS/SNS` / `NumberOfMessagesPublished` on `autom8-ebi-office-floor-scratch`

| Read at | 05:50Z bkt | 06:00Z bkt | 06:25Z bkt | Total |
|---|---|---|---|---|
| `2026-09-14T05:59:47Z` (BEFORE) | 2 | — | — | 2 |
| `2026-09-14T06:01:34Z` | 2 | — | — | 2 |
| `2026-09-14T06:36:49Z` (FINAL) | 2 | 1 | 1 | **4** |

**The counter moved, and every one of the four is attributed to a CloudWatch ALARM action — none to
the Lambda.** `aws cloudwatch describe-alarm-history --history-item-type StateUpdate` over
`05:00Z..06:40Z` for the four alarms whose actions target this topic returns exactly four
`INSUFFICIENT_DATA -> OK` transitions, each alarm holding exactly one `OKActions` entry (the scratch
topic), and each transition falling inside the bucket that incremented:

| Transition | Alarm | Bucket it explains |
|---|---|---|
| `2026-09-14T05:53:09.828Z` INSUFFICIENT_DATA → OK | `autom8-email-booking-intake-office-floor-lambda-errors` | 05:50Z (of 2) |
| `2026-09-14T05:53:48.769Z` INSUFFICIENT_DATA → OK | `autom8-email-booking-intake-office-floor-dlq-not-empty` | 05:50Z (of 2) |
| `2026-09-14T06:04:56.621Z` INSUFFICIENT_DATA → OK | `autom8-ebi-booking-floor-lambda-freshness` | 06:00Z |
| `2026-09-14T06:27:14.447Z` INSUFFICIENT_DATA → OK | `autom8-ebi-booking-floor-freshness-prober-liveness` | 06:25Z |

Two independent lines of evidence say the Lambda published nothing: (i) the arithmetic above accounts
for 4 of 4 publishes with zero residual, and (ii) all four `office_floor_evaluated` lines carry
`paged: false` and `page_class: "none"`, which is the handler's own record of not having called
`_publish`. **ZERO SNS publishes are attributable to legs A–D's evaluator code path.**

### `AWS/Lambda` / `Invocations` on the function

| Bucket | Sum | Attribution |
|---|---|---|
| 06:00–06:05Z | 3 | legs A, B, C (mine) |
| 06:25–06:30Z | 1 | leg D (the schedule) |

Four invocations total for the day, four `office_floor_evaluated` lines, no others. The reserved
concurrency of 1 was never contended: legs A–C were serialised by hand and finished by `06:01:07Z`,
25 minutes clear of the scheduled fire.

---

## §6 LEG E — IAM sufficiency: which grant each leg PROVED, and which is still unproven

The execution role's customer-managed policy, read live:

```
ARN=$(aws iam list-attached-role-policies --role-name autom8-email-booking-intake-office-floor-lambda-role \
      --query 'AttachedPolicies[?PolicyName==`autom8-email-booking-intake-office-floor`].PolicyArn' --output text)
aws iam get-policy --policy-arn "$ARN" --query 'Policy.DefaultVersionId'   # -> v1
aws iam get-policy-version --policy-arn "$ARN" --version-id v1
```

```json
{"Version": "2012-10-17", "Statement": [
 {"Sid": "StartInsightsQueryOnTheIntakeLogGroup", "Effect": "Allow", "Action": ["logs:StartQuery"],
  "Resource": ["arn:aws:logs:us-east-1:<ACCOUNT>:log-group:/aws/lambda/autom8-email-booking-intake:*",
               "arn:aws:logs:us-east-1:<ACCOUNT>:log-group:/aws/lambda/autom8-email-booking-intake-office-floor*:*"]},
 {"Sid": "ReadBackInsightsResults", "Effect": "Allow", "Action": ["logs:GetQueryResults"], "Resource": "*"},
 {"Sid": "PublishTheDigestOrTheRefusal", "Effect": "Allow", "Action": ["sns:Publish"],
  "Resource": "arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch"},
 {"Sid": "PublishTheSuccessTimestampInItsOwnNamespaceOnly", "Effect": "Allow", "Action": ["cloudwatch:PutMetricData"],
  "Resource": "*", "Condition": {"StringEquals": {"cloudwatch:namespace": "Autom8y/EbiOfficeFloor"}}}]}
```

Four grants, exactly as ADR D4.4 rules them (the `PutMetricData` namespace condition is present and
is the scoping the deadman module uses). **The probe identity is irrelevant to this leg** — the S1.4a
probe ran under SSO AdministratorAccess and therefore could not falsify an under-scoped role; every
invoke below ran under the **function's own execution role**, so an insufficient grant would have
surfaced as an `AccessDenied` in the response, not as a silent pass.

| Grant | Proved by | How the proof is non-vacuous |
|---|---|---|
| `logs:StartQuery` on `/aws/lambda/autom8-email-booking-intake:*` | Legs A, B, C, D | `query_status = "Complete"` with `log_groups_scanned = 1` and non-zero `records_scanned` on every leg. An `AccessDenied` on `StartQuery` cannot produce a `Complete` result with 14,002 records. |
| `logs:GetQueryResults` (`Resource: *`) | Legs A, B, C, D | `records_matched`, `bytes_scanned` and the folded row set (39 offices) exist only if the results were read back. Leg A read back **two** query result sets (primary + 605,299-record lookback). |
| `cloudwatch:PutMetricData` under `namespace == Autom8y/EbiOfficeFloor` | Leg A (and leg D) | A new `LastSuccessTimestamp` datapoint appeared in that exact namespace (§7). The namespace condition was satisfied by a real `PutMetricData` call, not asserted from the policy text. |
| `logs:StartQuery` on the **self** group `/aws/lambda/...-office-floor*:*` | **NOBODY** | `_read_page_ledger` sits behind the page gate; every leg logged `idempotence_status: "not-checked"`. UV-P below. |
| `sns:Publish` to the scratch topic | **NOBODY** | Three enforcers made a publish impossible by design. UV-P below. |

**UV-P (frozen syntax per `structural-verification-receipt` §1):**

[UV-P: the execution role's `sns:Publish` grant to `arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch` is SUFFICIENT — the deployed function can actually publish under its own role | METHOD: deferred-to-the-11:27Z-scheduled-evaluation | REASON: the page gate is `(UTC hour == 11) AND NOT dry_run` and the handler exposes no force-page lever, so NO invoke available to S1.4b could exercise the publish path. The 2 `NumberOfMessagesPublished` datapoints observed on the topic today are attributable to two CloudWatch ALARM `OKActions` (§9 finding F-2) — the CloudWatch service principal, not the Lambda's role — so the topic is proven RECEIVABLE but the role's grant is not proven EXERCISABLE. Discharge: the 11:27Z scheduled evaluation's `office_floor_evaluated` line carrying `paged=true` and `page_class=digest`, co-emitted with the `NumberOfMessagesPublished` delta on the scratch topic]

[UV-P: the execution role's `logs:StartQuery` grant on its OWN log group `/aws/lambda/autom8-email-booking-intake-office-floor*` is SUFFICIENT — the date-keyed page-idempotence read can actually run | METHOD: deferred-to-the-11:27Z-scheduled-evaluation | REASON: `_read_page_ledger` is called only when `page_gate` is true, so all four legs logged `idempotence_status: "not-checked"` and the second resource ARN in the `StartInsightsQueryOnTheIntakeLogGroup` statement was never exercised. This is the one grant whose FIRST live exercise will be at the page hour — the worst moment to discover an ARN typo. Discharge: an `office_floor_evaluated` line with `idempotence_status` equal to `read` (or `unread`, which would itself be the finding) and a non-null `evaluations_today`]

---

## §8 UV-P LEDGER — what S1.4b DISCHARGED, and what remains open

### DISCHARGED by this probe (PROBE-read-the-name-s1-2026-09-14 §11)

| Pre-deploy UV-P | Discharged by | Receipt |
|---|---|---|
| a cold-start `lambda_handler` constructs its three boto3 clients and completes both bounded Insights queries inside the 300 s timeout at the configured memory | **Leg A** | `Duration 7417.37 ms` / `300 s` budget (2.5%), `Init 1843.36 ms`, `Max Memory Used 135 MB` / `512 MB` (26%), with `day_n_records_scanned = 605,299` proving the full 30-day lookback ran. Independently reproduced by leg D's own cold start (`Init 1200.75 ms`, `Duration 7640.03 ms`, 136 MB). |
| the EventBridge rule created from `rate(1 hour)` actually fires the evaluator | **Leg D** | `State: ENABLED`, target = the function; a run line at `06:27:15.835Z` under request id `7a72a5f0-…`, disjoint from all three of mine, in a distinct log stream, one hour after rule creation. |
| three of the four ADR D4.4 IAM grants are sufficient under the function's own role | **Legs A–D** | §6 table: `logs:StartQuery` on the intake group, `logs:GetQueryResults`, and `cloudwatch:PutMetricData` under the `Autom8y/EbiOfficeFloor` namespace condition all exercised end-to-end with no `AccessDenied`. |

### PARTIALLY discharged

The once-per-day property of the digest (the same pre-deploy UV-P) is **not** discharged: `rate(1 hour)`
firing is proven, but `page_class = digest` has never been emitted, so the "at most once inside the
hour-11 window" half awaits a ≥ 24 h window. Leg D proves the trigger, not the day-scoped uniqueness.

### STILL OPEN after S1.4b (frozen syntax)

[UV-P: the deployed function can publish to `arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch` under its OWN execution role, returning a real `MessageId` | METHOD: deferred-to-the-11:27Z-scheduled-evaluation | REASON: the page gate `(UTC hour == 11) AND NOT dry_run` has no override in the event contract, so the live SNS delivery leg is structurally unreachable from any invoke S1.4b could make — that unreachability is the design working, not a gap in the probe. The four publishes observed on the topic today are CloudWatch alarm `OKActions` (§7), which proves the TOPIC receives but not that the ROLE can publish. Discharge: the 11:27Z run's `office_floor_evaluated` line with `paged=true`/`page_class=digest` plus the `NumberOfMessagesPublished` delta]

[UV-P: the date-keyed page-idempotence read (`_read_page_ledger`) can execute against the evaluator's OWN log group under the deployed role | METHOD: deferred-to-the-11:27Z-scheduled-evaluation | REASON: the ledger read sits behind the same page gate; all four legs logged `idempotence_status: "not-checked"`, so the second resource ARN in the `StartInsightsQueryOnTheIntakeLogGroup` statement has never been exercised. Discharge: an `office_floor_evaluated` line carrying `idempotence_status` of `read` with a non-zero `evaluations_today`]

[UV-P: the evaluator publishes AT MOST one digest per UTC date | METHOD: deferred-to-a-≥24h-observation-window-plus-the-C-3-double-invoke | REASON: no `page_class=digest` line exists yet; `rate(1 hour)` delivery is proven but day-scoped uniqueness is a property of 24 invocations, only one of which can page. Discharge: `page_class=digest` count per UTC day from the evaluator's own log group over ≥ 24 h]

[UV-P: the freshness dead-man `autom8-ebi-booking-floor-lambda-freshness` transitions to ALARM when the evaluator stops being invoked | METHOD: deferred-to-S1.7-three-leg-proof | REASON: S1.4b observed only the RESTORE leg (`INSUFFICIENT_DATA -> OK` at `06:04:56.621Z`, §7 / §9 F-2). A dead-man is proven only by the firing leg AND the restore leg; this probe supplies one of two, incidentally, and never drove the alarm. Discharge: ADR D2.7's three-leg two-sided proof]

[UV-P: the success-gap alarm turns red on two consecutive withheld `LastSuccessTimestamp` emissions | METHOD: deferred-to-S1.7-after-the-≥7d-soak | REASON: ADR D2 sequences the success-gap alarm AFTER a ≥ 7 d daily-sum soak, so the CONSUMER of the wire does not exist yet. S1.4b proved the WIRE live and two-sided (§7): emitted on both controlled runs, withheld on the refusal and on the dry run. Discharge: the soak table plus a deliberate refusal driving the alarm to ALARM]

---

## §9 FINDINGS

**F-1 · The in-run control is live and two-sided on the first day.** Legs A and D passed both query
legs on real traffic; leg B refused a measurably-thin-but-healthy read and named its kind. The refusal
is the sharper half: the query returned `Complete` with `log_groups_scanned=1` and
`estimated_records_skipped=0`, so the control bit on an *insufficiency it measured*, not on an error it
inherited. `day_n_query_status: "NotRun"` on leg B additionally proves the ~155 MB second read is
skipped once the primary has failed — the cost discipline in the docstring is real.
**Classification: PASS.**

**F-2 · The deadman's RESTORE leg fired live, unprompted, and it is attributable to this probe.**
`autom8-ebi-booking-floor-lambda-freshness` sat at `INSUFFICIENT_DATA` from creation (05:52:46Z) until
`06:04:56.621Z`, when it went OK — the gauge had no data until leg A gave the function its first
invocation. The same pattern at `06:27:14.447Z` for `-freshness-prober-liveness`. **This is a POSITIVE
result**: the alarm → SNS wire is proven to carry, end to end, with a real delivery to the scratch
topic. It is *half* of D2.7's two-sided proof, obtained incidentally; the ALARM (firing) leg remains
S1.7's and is not claimed here. *Operational note for S1.7: the freshness deadman's clock was started
by a manual probe invocation, so its first OK is not evidence that the schedule sustains it — leg D's
06:27Z invocation is.*

**F-3 · C-4's ruled coverage trigger is firing on live traffic, and the field to carry it still does
not exist.** Two of the three firing offices (`e63bbbe0` at 9 arrivals, `8a9b1a84` at 7 arrivals) sit
in CLASS UNKNOWN above the ZERO floor — exactly PROBE §11.1 C-4's refutable trigger ("the digest's
CLASS UNKNOWN section lists an office with `arrivals >= 5`"), firing on the very first live run as that
record predicted. The 2026-09-11 snapshot is 3 days old and covers 29 of the 39 offices evaluated.
`offices_unclassified` / `class_unknown_share` are still absent from `run_fields`.
**Route to: the S1.3 seat (C-4 owner). Priority: before the arming word** — a digest that pages on an
office whose class nobody can resolve is a page whose routing key is unread, which is the exact defect
class the lookback control was built to close.

**F-4 · `ccb52f4c`, the founding office, is evaluated and correctly quiet — the parity holds
arithmetically.** 93 arrivals, 3 bookings, 3.23% against a RATE floor of `< 2.5%` at `>= 20` arrivals.
S1.1 measured 2.02% in window B. The classifier did not change; the window did. `day_n = 1` records
that it *was* below a floor in the immediately preceding day-aligned window — the state-free counter
working. **Classification: PASS (parity explicable, not merely different).**

**F-5 · The page gate held under four live invocations and is structurally unbypassable from the event
contract.** Three enforcers, all read in source before the first invoke and all confirmed in the log
lines. **This is also the probe's boundary**: the same property that makes S1.4b safe makes the SNS
delivery leg unreachable from it. The `sns:Publish` grant and the idempotence-ledger read are the two
IAM grants whose FIRST live exercise will be at the 11:27Z page hour. An ARN typo or a missing grant in
either would surface for the first time *at the moment the instrument is supposed to speak*.
**Recommendation (route to Platform Engineer, non-blocking for S1.4b): before 11:27Z, consider a
read-only `aws iam simulate-principal-policy` for `sns:Publish` on the topic ARN and `logs:StartQuery`
on the self-group ARN under the function's role — it discharges the grant question without touching the
page gate.** I did not run it: it is a new probe class outside this charge's leg list, and the honest
UV-P is preferable to an unchartered action.

**F-6 · Cold-start headroom is ~40x on time and ~3.8x on memory.** Two independent cold starts (legs A
and D) at 7.42 s and 7.64 s against 300 s, 135/136 MB against 512 MB, with the full 605k-record lookback
inside each. The 300 s timeout is not a constraint at present traffic; the memory is provisioned ~3.8x
above observed peak. No action required — recorded as the baseline the next reading is measured against.

### Handoff state

- **No FAIL results.** Four legs, four PASS-class outcomes (A pass, B correct-refusal, C correct-
  suppression, D pass). Nothing in this probe found the evaluator doing something it should not.
- **Nothing was armed, fixed, or mutated.** Zero terraform, zero alarm edits, zero schedule edits,
  zero topic edits. Four synchronous invocations and reads.
- **The gap this probe cannot close is named, not papered over**: the live SNS delivery leg and the
  idempotence-ledger read belong to the 11:27Z scheduled evaluation, per §8.

