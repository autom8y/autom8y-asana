# PROBE — S1.4b POST-DEPLOY LIVE PROBE of the S-1 per-office booking-floor evaluator

> ## ERRATUM — 2026-09-14, after rite-disjoint certification
>
> **Verdict on this artifact: CERTIFIED-WITH-ERRATA**, by the **integrity-architect** acting as S1.4b
> CRITIC, rite-disjoint from the chaos-engineer station that ran the probe (review on `autom8y-asana`
> PR #456). The critic authored none of this probe, invoked nothing, and re-derived every number with
> their own hands against us-east-1 and both repos' `origin/main`.
>
> Six errata are applied **in place** below, each marked `[E-n]` at its site. Nothing was retracted;
> four of the six are over-reads right-sized, one is an attribution sharpened, one re-seats a finding's
> authority. In summary:
>
> | | What was wrong | Where |
> |---|---|---|
> | **E-1** | §7's SNS table used 5-minute buckets, which under-resolve the attribution and actively mislead — a reader maps the `06:00Z bkt = 1` onto legs A/B/C. Replaced with the strictly stronger `--period 60` table. | §7 |
> | **E-2** | "Two independent lines of evidence" over-claimed: `NumberOfMessagesPublished` has **no publisher dimension**. For leg D the run line's `paged:false` is **load-bearing, not corroborating**. | §7 |
> | **E-3** | "the withheld-timestamp half is proven LIVE" over-read: leg B exercised **1 of `_control`'s 6** predicates and **0 of `_lookback_control`'s 5**. | §3 |
> | **E-4** | §2's D2 table rendered the lookback column as a checked leg; `offices_with_bookings` is **not a predicate of `_lookback_control` at all**. | §2 |
> | **E-5** | The at-most-one-digest-per-UTC-day UV-P was mis-framed (`PageLedger.unread` **publishes anyway** by design) and its ≥24 h discharge clause could not establish the property. | §8 |
> | **E-6** | F-3's authority was left implicit and is not this station's to claim; re-seated on the C-4 UV-P's own discharge clause, and re-filed as a record/build discrepancy **predicted and owned at S1.4a**. | §9 |
>
> Also added by the critic and carried here: **DEFECT-1** (§9), **UV-P-A** and **UV-P-B** (§8), and the
> starvation geometry (§5). Two refusal conditions were looked for and neither held: no
> `INTEGRITY-DESIGN-REFUSED` (the catastrophic state — a success timestamp on a half-run — is
> **unrepresentable by construction**, because `_lookback_control` reassigns the single `control`
> variable and the refusal path early-returns before `put_metric_data`), and no `RECOVERY-FLOOR-REFUSED`.
> The arming word remains the operator's; neither the station nor the critic closes this gate.

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

Fetched with `aws logs filter-log-events --log-group-name /aws/lambda/autom8-email-booking-intake-office-floor --start-time 1789099200000 (= `2026-09-11T04:00:00Z`) --filter-pattern '"office_floor_evaluated"' --limit 20 --region us-east-1` (**one page**; page 2 via `--next-token` returned `0` events and **no** further token, so the three lines below are the COMPLETE filtered set for the group, not a truncation):

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

### The D2 in-run control — **`[E-4]` the two chains are SEPARATE, and only one column is a checked leg**

`_control` and `_lookback_control` are two distinct predicate chains over two distinct reads. The
earlier rendering of this table put both under one header and showed `offices_with_bookings` as
"inheriting" into the lookback column; that reads as a checked leg and it is not.
**`offices_with_bookings` is not a predicate of `_lookback_control` at all.**

`_control` — six predicates over the PRIMARY read (all PASSED on leg A):

| `_control` predicate | Leg A value | Verdict |
|---|---|---|
| `status != "PollTimeout"` | `Complete` | PASS |
| `status == "Complete"` | `Complete` | PASS |
| `log_groups_scanned >= 1` | `1` | PASS |
| `estimated_records_skipped == 0` | `0` | PASS |
| `records_scanned >= 500` | `14002` | PASS |
| `offices_with_bookings >= 5` | `31` | PASS |

`_lookback_control` — five predicates of its OWN over the SECOND read. Two were **passively observed
passing**; three were **never evaluated** on any leg:

| `_lookback_control` predicate | Leg A | State |
|---|---|---|
| `day_n_query_status != "PollTimeout"` | `Complete` | passively observed passing |
| `day_n_query_status == "Complete"` | `Complete` | passively observed passing |
| `day_n_log_groups_scanned >= 1` | `1` | **never evaluated in the refusing direction** |
| `day_n_estimated_records_skipped == 0` | `0` | **never evaluated in the refusing direction** |
| `day_n_records_scanned >= max(500, primary)` | `605299 >= 14002` | passively observed passing |

The honest reading: leg A shows the lookback read was healthy. It does **not** show that the lookback's
refusal branches bite. See **UV-P-A** (§8) — `_lookback_control` is the path minted to cure the DW-10
silent-loss defect, and it has **zero live exercise in the refusing direction**.

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
**`[E-3]` The withheld-timestamp half is proven LIVE for the PRIMARY control's records-floor
predicate — and for that predicate only.** `_control` is a six-branch chain
(`query_timeout` · `query_status_*` · `log_groups_scanned_zero` · `records_skipped` ·
`records_scanned_below_floor` · `offices_with_bookings_below_floor`); leg B exercised **one** of the
six. `_lookback_control` is a **separate five-branch chain**, and **not one of its five was exercised
in the refusing direction by any leg** — leg B failed the primary first, so `day_n_query_status=NotRun`.
The earlier unqualified "the deadman's withheld-timestamp half is proven LIVE" over-read that. The
wire is proven; the full predicate surface is not. See **UV-P-A** (§8).

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

**Starvation geometry, and how long silence stays invisible** (re-derived from the alarms' own
configuration, not from the module's declared inputs). **A stuck invoke cannot starve the next
scheduled fire**: `timeout = 300 s` is bounded far below the `rate(1 hour)` cadence, and
`reserved_concurrency = 1` prevents *overlap*, not *re-invocation* — the handler's docstring says
exactly this. The real vector is the **retry path**: up to **three deliveries of one scheduled event**
inside `MaximumEventAgeInSeconds: 3600` (`MaximumRetryAttempts: 2`), each serialised by the concurrency
of 1, with anything unplaceable ageing out to the DLQ. **But the freshness deadman does not see that as
silence for roughly four hours**: its geometry is `Maximum(age_since_last_invocation_seconds)`,
`Period 3600`, **`DatapointsToAlarm: 2` of `EvaluationPeriods: 3`**, `> 7200`, `TreatMissingData:
missing` — age first exceeds 7200 s at ~T+2 h, and two breaching hourly Maxima land at ~T+3 h and
~T+4 h, so the alarm reds at roughly the **fourth** consecutively missed fire. **One, two and three
missed hourly fires are invisible to it** (consistent with `office_floor.tf`'s own "~4.1 h blind
window" comment). The **faster** floor for this class is `autom8-email-booking-intake-office-floor-dlq-not-empty`
(P300, 1 evaluation period) — and note what it does and does not catch: it fires on a failed
**delivery**, not on an invocation that runs and returns an error with no DLQ entry.

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

Fetched with `aws logs filter-log-events --log-group-name /aws/lambda/autom8-email-booking-intake-office-floor --start-time 1789365700000 (= `2026-09-14T06:01:40Z`) --filter-pattern '"office_floor_evaluated"' --limit 20 --region us-east-1` (**one page**; 1 event returned):

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

**Cadence**: the rule was created `05:26:56Z` (the log group's `creationTime` is `1789363616713`, i.e. `2026-09-14T05:26:56.713Z`), the
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

**`[E-1]` At `--period 60`** (re-derived by this station on the critic's erratum, and independently by
the critic; the earlier 5-minute rendering under-resolved the attribution and actively misled — its
`06:00Z bkt = 1` invited a reader to map that publish onto legs A/B/C, which ran `06:00:17Z..06:01:07Z`,
when it is in fact the `06:04:56.621Z` alarm):

```
aws cloudwatch get-metric-statistics --namespace AWS/SNS --metric-name NumberOfMessagesPublished \
  --dimensions Name=TopicName,Value=autom8-ebi-office-floor-scratch \
  --start-time 2026-09-14T05:45:00Z --end-time 2026-09-14T06:45:00Z --period 60 --statistics Sum
```

| Minute | Sum |
|---|---|
| `05:53Z` | 2 |
| `06:04Z` | 1 |
| `06:27Z` | 1 |
| **total** | **4** (three datapoints) |

**The `06:00Z` and `06:01Z` minutes hold NO datapoint at all.** Legs A, B and C are separated from every
publish on this topic **by time alone** — a taken zero at 1-minute resolution, needing no alarm
arithmetic and no attribution premise whatsoever.

**Every one of the four publishes is attributed to a CloudWatch ALARM action.**
`aws cloudwatch describe-alarm-history --history-item-type StateUpdate` for the four alarms whose
*action ARNs* target this topic returns exactly four `INSUFFICIENT_DATA -> OK` transitions. **The
load-bearing detail: all four alarms carry `AlarmActions=1`, `OKActions=1` and
`InsufficientDataActions=0`** — which is precisely why their creation-time `INSUFFICIENT_DATA` entries
published *nothing*, and therefore why four transitions account for four publishes with **zero
residual**. Each alarm's watched subject is named, because the fourth is not what its name suggests:

| Transition | Alarm | Watches (ns / metric / dimension) | Geometry | Minute |
|---|---|---|---|---|
| `05:53:09.828Z` | `...-office-floor-lambda-errors` | `AWS/Lambda Errors`, `FunctionName=autom8-email-booking-intake-office-floor` | P300, 1 eval, `>= 1`, notBreaching | 05:53Z (of 2) |
| `05:53:48.769Z` | `...-office-floor-dlq-not-empty` | `AWS/SQS ApproximateNumberOfMessagesVisible`, `QueueName=...-office-floor-dlq` | P300, 1 eval, `> 0`, notBreaching | 05:53Z (of 2) |
| `06:04:56.621Z` | `autom8-ebi-booking-floor-lambda-freshness` | `Autom8y/Freshness age_since_last_invocation_seconds` **Maximum**, `FunctionName=autom8-email-booking-intake-office-floor` | P3600, **2 of 3 datapoints**, `> 7200`, missing | 06:04Z |
| `06:27:14.447Z` | `autom8-ebi-booking-floor-freshness-prober-liveness` | `AWS/Lambda Invocations` **Sum**, `FunctionName=`**`autom8-ebi-booking-floor-freshness-prober`** — the **watcher of the watcher**, not a second watcher of the evaluator | P86400, 2 eval, `< 1`, breaching | 06:27Z |

**`[E-2]` The correction to how this evidence composes.** `AWS/SNS NumberOfMessagesPublished` carries
**no publisher dimension** — the metric cannot attribute by publisher, ever. The earlier claim of "two
independent lines of evidence" was therefore an over-claim, and the two lines are not symmetric:

- **Legs A, B, C** need no attribution at all. Their minutes are empty (above). Proven by time.
- **Leg D does not stand on the metric alone.** The `06:27Z` minute holds **exactly one publish and two
  candidate producers**: the prober-liveness OK transition at `06:27:14.447Z` and leg D's own
  evaluation at `06:27:15.835Z` — **1.4 seconds apart, same minute**. Had the alarm action silently
  failed and leg D published, the count would still read `1`.

So the composed claim is: **(i)** the metric arithmetic accounts for 4 of 4 with zero residual, and
**(ii)** the run line's taken zero — `paged: false` / `page_class: "none"`, emitted unconditionally on
every run line alongside `records_scanned`, so a *measured* absence rather than silence — which is
**load-bearing, not corroborating, for the `06:27Z` minute, the one bucket the metric cannot resolve**.
**ZERO SNS publishes are attributable to legs A–D's evaluator code path**, by conjunction for leg D.
See **DEFECT-1** (§9) for why that boolean is not a strong enough receipt at the page hour.

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
firing is proven, but `page_class = digest` has never been emitted. **`[E-5]` And it is not awaiting a
≥ 24 h window** — that was the mis-framing corrected below. Because `PageLedger.unread` publishes
anyway by design, the property is a best-effort suppression with a named fail-open, and only the
two-sided UV-P-B fixture (positive · teeth · the taken zero) can establish it. Leg D proves the
trigger, not the day-scoped uniqueness, and no amount of quiet observation would.

### STILL OPEN after S1.4b (frozen syntax)

[UV-P: the deployed function can publish to `arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch` under its OWN execution role, returning a real `MessageId` | METHOD: deferred-to-the-11:27Z-scheduled-evaluation | REASON: the page gate `(UTC hour == 11) AND NOT dry_run` has no override in the event contract, so the live SNS delivery leg is structurally unreachable from any invoke S1.4b could make — that unreachability is the design working, not a gap in the probe. The four publishes observed on the topic today are CloudWatch alarm `OKActions` (§7), which proves the TOPIC receives but not that the ROLE can publish. Discharge: the 11:27Z run's `office_floor_evaluated` line with `paged=true`/`page_class=digest` plus the `NumberOfMessagesPublished` delta]

[UV-P: the date-keyed page-idempotence read (`_read_page_ledger`) can execute against the evaluator's OWN log group under the deployed role | METHOD: deferred-to-the-11:27Z-scheduled-evaluation | REASON: the ledger read sits behind the same page gate; all four legs logged `idempotence_status: "not-checked"`, so the second resource ARN in the `StartInsightsQueryOnTheIntakeLogGroup` statement has never been exercised. Discharge: an `office_floor_evaluated` line carrying `idempotence_status` of `read` with a non-zero `evaluations_today`]

**`[E-5]` The at-most-one-digest property was mis-framed here, and its previous discharge clause
(a ≥ 24 h observation window) could not have established it.** `PageLedger` (`digest.py`) defines a
**third state** whose docstring says it outright — *"UNREAD IS A THIRD STATE AND IT PUBLISHES ANYWAY"* —
and `already_paged` is `status == "read" and pages_today > 0`, so an untrustworthy ledger read
**publishes**. R-172 is therefore a **best-effort suppression with a named fail-open**, not an
invariant, and a clean 24 h records only that the fail-open branch did not fire that day. An unfired
guard is not a safe design. Replaced with the critic's two-sided UV-P-B:

[UV-P-B: the date-keyed page-idempotence gate SUPPRESSES a second digest inside one UTC date, and the suppression is CAUSED BY the ledger read rather than by accident | METHOD: deferred-to-a-two-sided-double-invoke-at-the-page-hour-plus-an-ingestion-latency-measurement | REASON: `PageLedger.unread` publishes anyway by explicit design, so a one-sided green cannot discharge the property; and the gate's input is an Insights read of the evaluator's OWN log group, whose ingestion latency versus the EventBridge retry backoff — `MaximumRetryAttempts: 2` with `MaximumEventAgeInSeconds: 3600`, i.e. **up to three deliveries of one scheduled event** — is unmeasured, which is exactly the retry case `_read_page_ledger`'s docstring says it exists to close. Discharge, all three legs: (i) POSITIVE — two page-hour invocations with the second fired after the first run line is queryable: exactly one `NumberOfMessagesPublished` delta, two run lines, the second carrying `idempotence_status=read`, `pages_today=1`, `paged=false`; (ii) TEETH — the same fixture with the second invoke fired BEFORE the first line is queryable: two publishes and a second run line carrying `pages_today=0` or `unread`, proving the suppression is the ledger's doing and not an unrelated accident; (iii) the TAKEN ZERO — the measured delay between a run line's `timestamp` and the first instant `IDEMPOTENCE_QUERY` returns it. Without (ii) and (iii), an always-`unread` ledger and a working gate are indistinguishable in the single-fire case]

[UV-P-A: the lookback control's five `day_n_*` refusal predicates BITE — a non-Complete, short, skipped or wrong-group SECOND read is refused and `LastSuccessTimestamp` is withheld | METHOD: deferred-to-a-refusing-second-query-fixture, with the reachability seam named | REASON: every S1.4b leg either passed both queries or failed the PRIMARY before the lookback ran (`day_n_query_status=NotRun`), so `_lookback_control` has ZERO live exercise despite being the code path minted to cure the DW-10 silent-loss defect — the load-bearing half of the D2 invariant. Note the seam honestly: the event contract exposes only `{dry_run, window_start, window_end}`, the lookback window is a strict SUPERSET of the primary over the same group, and its floor is relative (`max(500, primary_records_scanned)`), so a lookback-only refusal may be **structurally unreachable from any live invoke** — an irreducible reactive seam at the live altitude, **named here for the change-warden**. Discharge: EITHER a live run line carrying `control=failed` with `kind` in the `day_n_*` family and no `LastSuccessTimestamp` datapoint in that minute, OR — if live reachability is genuinely nil — a cited in-process fixture that drives each of the five predicates two-sidedly, with the unreachability itself recorded as the reason the live leg is waived]

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

**F-3 · `[E-6]` C-4's coverage trigger fires on live traffic — a record/build discrepancy PREDICTED
AND OWNED at S1.4a, of which this station supplies only the live confirmation.**

*Whose requirement this is* (the authority, stated rather than left implicit — it is not this station's
to claim). ADR D8.2's run-line field list at `asana origin/main` ends at `evaluator_version` and
contains **neither** `offices_unclassified` **nor** `class_unknown_share`; the ADR's erratum E-2 (the
class-is-context amendment) introduces the CLASS UNKNOWN section but adds **no run-line field**. The
requirement's actual source is the **C-4 arming-gate condition's own UV-P discharge clause** in
`PROBE-read-the-name-s1-2026-09-14.md §11.1`: *"Discharge: the field landing on the run line plus a
named owner for the trigger's first firing — which §9 shows would fire on the very first live run."*
**Owner: the S1.3 seat. Due: before the arming word.**

*What S1.4b contributes — the live confirmation, and nothing more.* Two of the three firing offices
(`e63bbbe0` at 9 arrivals, `8a9b1a84` at 7) sit in CLASS UNKNOWN above the ZERO floor, satisfying
C-4's refutable trigger ("the digest's CLASS UNKNOWN section lists an office with `arrivals >= 5`") on
the very first live run, exactly as S1.4a §9 predicted it would. The 2026-09-11 snapshot is 3 days old
and covers 29 of the 39 offices evaluated. `offices_unclassified` / `class_unknown_share` remain absent
from `run_fields`. This is a **discrepancy between the record and the build**, not a station discovery —
a digest that pages on an office whose class nobody can resolve is a page whose routing key is unread,
the exact defect class the lookback control was built to close.

**DEFECT-1 · The evaluator's publish leaves no independent receipt. Owner: the S1.3 seat, before the
arming word.** Filed by the critic; recorded here because two of this artifact's own open UV-Ps depend
on it. `_publish` calls `sns.publish(...)` and returns a bare `True` — **the response's `MessageId` is
discarded**. A whole-day grep of the evaluator's log group for `MessageId` returns **0 events**. So
"did the digest actually reach SNS" is answerable only by (a) the handler's own boolean and (b) a topic
counter with **no publisher dimension** — the identical non-discriminating pair that left the `06:27Z`
minute resolvable only by conjunction (§7 `[E-2]`). This is not cosmetic: §6's two open IAM UV-Ps both
name their discharge as "`paged=true` co-emitted with the `NumberOfMessagesPublished` delta", and at
`11:27Z` that delta lands in a minute that can also hold an alarm transition — **exactly as `06:27Z`
did**. The S1.4a UV-P demanded something stronger and more specific: *"the `MessageId` from the real
`sns:Publish` response co-emitted alongside the `office_floor_evaluated` line carrying `paged=true`."*
**The deployed code cannot produce that receipt.** The cure is one line — carry
`sns.publish(...)["MessageId"]` onto the run line — and it converts the 11:27Z discharge from an
arithmetic inference into a direct one. Named, not fixed.

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
- **Certified rite-disjointly, with six errata applied in place** (see the ERRATUM block at the head of
  this artifact). The critic re-derived every number independently and found no refusal condition; the
  errata sharpened the attribution (E-1, E-2), right-sized two over-reads about *which* control was
  proven (E-3, E-4), corrected a UV-P whose discharge clause could not establish its property (E-5),
  and re-seated one finding's authority (E-6).
- **Carried to the S1.3 / builder seats before the arming word**: **DEFECT-1** (the discarded
  `MessageId`), **UV-P-A** (`_lookback_control`'s five predicates, zero live exercise — with the
  structural-unreachability seam named for the change-warden) and **UV-P-B** (two-sided idempotence).
  None of them is this station's to fix, and this station fixed none of them.

