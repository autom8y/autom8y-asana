---
type: soak-table
initiative: read-the-name
sprint: S1.6
instrument: S-1 per-office booking floor (autom8-email-booking-intake-office-floor)
rule: every new metric soaks ≥ 7 consecutive days with daily sums receipted own-hands before its alarm arms (charge §3; R-168 keeps every page path on the scratch topic regardless)
started: 2026-09-14
owner: the seat that resumes read-the-name (this table is appended one row per UTC day; the handoff names the command)
---

# S1.6 · soak table — S-1 booking floor

Every row is one UTC day, read own-hands the following day with the commands in §2. A row with any blank cell is not a row. Seven complete consecutive rows close S1.6; S1.7 stays BLOCKED on the consumer word (R-168) even then.

## 1 · Table

| day | UTC date | evaluations (`office_floor_evaluated` lines) | controlled (`"control": "passed"` — `status==Complete ∧ records_scanned≥500 ∧ offices_with_bookings≥5` on both queries) | refused (`"control": "failed"`) | `LastSuccessTimestamp` datapoints (`Autom8y/EbiOfficeFloor`) | prober gauge datapoints (`Autom8y/Freshness` `age_since_last_invocation_seconds`, max s) | deadman alarm states 23:59Z (`…-lambda-freshness` / `…-freshness-prober-liveness`) | pages to scratch (`NumberOfMessagesPublished` on `autom8-ebi-office-floor-scratch`) | page-class distribution (ZERO / RATE / none) | `***` residual > 10 % tripwire | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-09-14 (partial, read 06:41Z) | 4 (3 S1.4b controlled invokes 06:00:27 / 06:00:48 / 06:01:07Z + the first SCHEDULED fire 06:27:15Z; `filter-log-events` one page) | 3 (A, C-dry-run, D; scheduled D: `records_scanned` 13979, offices_with_bookings 31) | 1 (leg B, 10-min window, `records_scanned_below_floor`; timestamp withheld) | 2 (06:00Z, 06:27Z — A and D only; B refused and C dry-run emitted nothing) | 8 samples since 05:52Z, min 200 s, max 2000.6 s (< 7200) | both OK (`…-lambda-freshness` OK 06:04:56Z; `…-freshness-prober-liveness` OK 06:27:14Z) | 4 — ALL four are alarm `INSUFFICIENT_DATA → OK` OK-action notifications (05:53:09 / 05:53:48 / 06:04:56 / 06:27:14Z), 0 from the evaluator (`paged:false` on all four run lines); subscriptions 0 | from the 06:27:15Z run line: `zero_floor_count: 3`, `rate_floor_count: 0`, 39 evaluated → 36 quiet; office lines `floor_class` quiet 108 / zero 9 over the four runs (Gate C's own read); `ccb52f4c` quiet at 3.23 % (93 arrivals / 3 bookings) | `residual_share: 0.0746`, `residual_share_high: false` on the 06:27:15Z run line (own-hands 07:05Z; the earlier "needs the 11:27Z digest" was untrue — the field is on every run line) | born 05:52:27Z by run 34810812077; first scheduled fire OBSERVED 06:27:15Z; day-1 read must add the 11:27Z digest (`MessageId`, `sns:Publish` proven), the `***` share, and the full-day sums |
| 1 | 2026-09-15 (complete, read 2026-09-16T00:06Z) | 24 | 24 (`control: passed` on every run line) | 0 | 24 (one per hour, 00Z–23Z, UTC-normalised) | 288 samples, Maximum 3803.16 s (< 7200) | all four OK, `AlarmActions` **and** `OKActions` = `autom8-ebi-office-floor-scratch` only (`…-freshness-prober-liveness`, `…-lambda-freshness`, `…-office-floor-dlq-not-empty`, `…-office-floor-lambda-errors`) | **1** — the 11:27Z digest, and nothing else all day; subscriptions still **0** | office lines 1091: quiet 1016 / zero 54 / rate 21; run-line `zero_floor_count` 2–3, `rate_floor_count` 0–1 | **BREACH — day max `residual_share` 0.1141, `residual_share_high: true` on 4 of 24 run lines** | **ROW FAILS §3 on the `***` residual alone; the other seven criteria pass.** The step is datable to the **20:27Z run** (19:27Z 0.0480 → 20:27Z 0.1038 → 0.1073 → 0.1134 → 0.1141, still climbing at 23:27Z) and it happened on **s1.3**, two hours BEFORE the s1.4 deploy, so it is not #2272. Cause measured at source: the **19:00Z hour** carried 110 office-bearing lines of which **65 were `***` (59.1 %)**, decaying to 0 % by 00Z — 46 distinct traces / 98 lines, **40 × `WebhookValidationError` at `stage=parse`** (each also emitting a `booking_intake_fault`, which IS in the arrival unit) + 6 × `OfficeResolutionError`. These fail before office resolution, so `redact_uuid` renders `***` and they are unattributable **by construction**. W = 3 d rolling, so the burst stays in the denominator until ≈ 2026-09-18T19:00Z. **Also in this row:** the evaluator switched s1.3 → s1.4 at 22:52Z and PT-08(a) passed every fence token at the 23:27:15Z fire, with `office_name` two-sided on one query (50 of 50 named at 22:00Z, **0 of 50 at 23:00Z**); and EBI deployed autom8y #2290 as image `c95c59b` at **2026-09-16T00:06:08Z**, five functions unanimous, `office_floor/` tree untouched by source diff. |
| 2 | 2026-09-16 (complete, read 2026-09-17T00:38Z) | 24 | 24 | 0 | 24 | 288 samples, Maximum 3802.85 s (< 7200) | **4 of 4 expected present**, none missing, none unexpected, all OK, `AlarmActions` **and** `OKActions` = `autom8-ebi-office-floor-scratch` only — the first row graded under §3c, which asserts cardinality **before** grading; under the old form this cell could have passed on a deleted alarm | **1** — the 11:27Z digest and nothing else; subscriptions still **0** | office lines 1279: quiet 1224 / zero 55 / **rate 0**; run-line `zero_floor_count` 2–3, `rate_floor_count` **0** | **BREACH — day max `residual_share` 0.1414, `residual_share_high: true` on 24 of 24 run lines** | **ROW FAILS §3 on the `***` residual alone; the other seven criteria pass.** Same cause as row 1 and no new arrival: the 09-15T19Z no-body batch's 3-hourly SendGrid redelivery tail accumulating inside the 3-day window while quieter hours age out (SOAK §3b). Composition of the residual over this window, by `error_type` × `stage` on `***` lines: `WebhookValidationError`/`parse` 74 · `OfficeResolutionError`/`resolve_office` 32 · their paired fault/decline/parked lines 136. **`ccb52f4c` off the RATE floor all day** (`rate_floor_count` 0 on every run), consistent with E-6: its arrivals are relayed `unknown_loud`, and it books by its native path. **Deploys inside this row: none.** autom8y-data #472 merged `769522ff` at 2026-09-17T00:08:37Z and booted at 00:30-00:32Z — **both after this row closed**; autom8y #2324 was HELD, then split (head `8149625d`) and had not merged. |

## 2 · Daily own-hands commands (region us-east-1; rc read unpiped)

```bash
D=2026-09-15   # the UTC day being closed
S=$(date -u -j -f %Y-%m-%d "$D" +%s) 2>/dev/null || S=$(date -u -d "$D" +%s); E=$((S+86400))
LG=/aws/lambda/autom8-email-booking-intake-office-floor

# evaluations / controlled / refused — from the evaluator's own log group (Insights; recordsScanned must be printed)
QID=$(aws logs start-query --log-group-name "$LG" --start-time "$S" --end-time "$E" \
  --query-string 'fields @message | filter @message like /office_floor_evaluated/ | stats count(*) as evaluations, sum(@message like /"control":\s*"passed"/) as controlled, sum(@message like /"control":\s*"failed"/) as refused, sum(@message like /"dry_run":\s*true/) as dry_runs' \
  --output text --query queryId); sleep 8
aws logs get-query-results --query-id "$QID" --output json   # read results[] AND statistics.recordsScanned

# LastSuccessTimestamp datapoints for the day
aws cloudwatch get-metric-statistics --namespace Autom8y/EbiOfficeFloor --metric-name LastSuccessTimestamp \
  --start-time "$(date -u -r $S +%FT%TZ)" --end-time "$(date -u -r $E +%FT%TZ)" --period 86400 --statistics SampleCount Maximum --output json

# prober gauge (the deadman's age metric) for the day
aws cloudwatch get-metric-statistics --namespace Autom8y/Freshness --metric-name age_since_last_invocation_seconds \
  --dimensions Name=FunctionName,Value=autom8-email-booking-intake-office-floor \
  --start-time "$(date -u -r $S +%FT%TZ)" --end-time "$(date -u -r $E +%FT%TZ)" --period 86400 --statistics SampleCount Maximum --output json

# deadman alarm states + their actions (must be the scratch topic ARN only)
aws cloudwatch describe-alarms --alarm-name-prefix autom8-ebi-booking-floor --output json \
  --query 'MetricAlarms[].{n:AlarmName,s:StateValue,a:AlarmActions,ok:OKActions}'

# pages that reached the scratch topic (subscriptions must still be zero)
aws cloudwatch get-metric-statistics --namespace AWS/SNS --metric-name NumberOfMessagesPublished \
  --dimensions Name=TopicName,Value=autom8-ebi-office-floor-scratch \
  --start-time "$(date -u -r $S +%FT%TZ)" --end-time "$(date -u -r $E +%FT%TZ)" --period 86400 --statistics Sum --output json
# NEVER count with --query 'length(...)'. The AWS CLI applies a JMESPath --query to EACH PAGE
# separately and prints one result per page, so a paginated count read as a single number
# UNDERCOUNTS. (Found on the EBI plane 2026-09-16: `describe-alarms --query 'length(...)'
# --output text` printed "38" then "3" -- 38 read as the answer, 41 the truth.) A plain
# --output json read is auto-paginated AND MERGED by the CLI, so counting the merged object is
# safe. `NextToken` is printed as the proof that the read was complete: a subscription count is
# the R-168 fence, and "0" from page 1 of 2 is exactly the shape of a silent failure.
aws sns list-subscriptions-by-topic --topic-arn "arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch" --output json \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("subscriptions=", len(d.get("Subscriptions",[])), "NextToken=", d.get("NextToken"))'

# page-class distribution — the per-office lines carry `floor_class` (lowercase: quiet | zero | rate); `page_class` exists ONLY on the run line (Gate C F-1)
QID=$(aws logs start-query --log-group-name "$LG" --start-time "$S" --end-time "$E" \
  --query-string 'fields @timestamp, @message | filter @message like /office_floor_office/ | stats count(*) as offices, sum(@message like /"floor_class":\s*"zero"/) as zero, sum(@message like /"floor_class":\s*"rate"/) as rate, sum(@message like /"floor_class":\s*"quiet"/) as quiet' \
  --output text --query queryId); sleep 8; aws logs get-query-results --query-id "$QID" --output json   # a healthy plane prints quiet ≫ 0; zero=rate=quiet=0 is an UNTAKEN read, not a quiet day

# the *** tripwire and the floor counts — from EVERY run line (`office_floor_evaluated`), not the digest
QID=$(aws logs start-query --log-group-name "$LG" --start-time "$S" --end-time "$E" \
  --query-string 'fields @timestamp | filter @message like /office_floor_evaluated/ | parse @message /"residual_share":\s*(?<share>[0-9.]+)/ | parse @message /"residual_share_high":\s*(?<high>true|false)/ | parse @message /"zero_floor_count":\s*(?<zero>[0-9]+)/ | parse @message /"rate_floor_count":\s*(?<rate>[0-9]+)/ | display @timestamp, share, high, zero, rate | sort @timestamp asc' \
  --output text --query queryId); sleep 8; aws logs get-query-results --query-id "$QID" --output json   # the column is the DAY'S MAX share; `high: true` on any run line is the tripwire
```

Fences: an Insights zero needs `recordsScanned` comparable to a control (UNTAKEN-ZERO); the office-floor function has no alias, so an unqualified read IS its served object; no phone digits, guid8 only, `<ACCOUNT>` for the account id (merge-surface sweep `digits12`).

## 2b · Ruled constraint on what the soak may certify (pythia's T2 ruling, `.ledge/decisions/RULING-read-the-name-t2-15caa02c-class-2026-09-14.md` R-2; measured in asana #454 → `24886bca`)

The fleet's booking lines carry `chiropractor_guid` only from **2026-09-09**; the 30-day `last_booking_age_days` lookback is therefore ~6 days effective on day 0 and reaches its full horizon on **2026-10-09**. Until then the soak may certify ACTIONABLE and CLASS UNKNOWN rows of the digest; it may **not** certify EXPECTED SILENCE (class ∈ {inactive, ignored} with no booking) — record those rows as `EXPECTED SILENCE (unattributable before 2026-10-09)`. A computed attribution floor printed on the page is the ruled cure (owner: S1.3 builder seat), not a re-tune of A/A′/r.

## 3 · What closes the soak

Seven consecutive complete rows with: evaluations ≥ 20/day, controlled ≥ 20/day, zero `FLOOR-REFUSED` on a healthy plane (or each refusal explained), `LastSuccessTimestamp` SampleCount ≥ 20/day, prober gauge SampleCount ≥ 280/day (`rate(5 minutes)`) with Maximum < 7200 s (cadence 3600 × buffer 2), both deadman alarms OK with actions = scratch only, exactly one page/day to scratch at 11:00Z (day count incrementing), `***` residual ≤ 10 %.

### 3·0 · INDEX AND DISPOSITIONS — read this before any section below

This section grew from four entries to eleven on 2026-09-16/17. **The single thing a reader must not get wrong
is which of them CHANGED the criterion.** Exactly one did.

| § | what it is | **disposition** |
|---|---|---|
| **3c** | the deadman criterion passed vacuously on an empty set | **APPLIED** — the only section that changes what the instrument checks. Applied because it can **only tighten**: it turns passes into failures and can never rescue a failing row. |
| 3a | the residual criterion has no floor under its denominator | **PROPOSED, NOT APPLIED** |
| 3b | the residual counts redeliveries as new lines — a false rate | **PROPOSED, NOT APPLIED** |
| 3e | the residual reads `chiropractor_guid` while attribution lands in `office_handle` | **PROPOSED, NOT APPLIED** |
| 3d | deploy instants bounding rows 3–5 | record only |
| 3d-i | the three realization reads §3d demanded, one of them untakeable | record only |
| 3d-ii | two further deploy instants, and v76's inertness measured | record only |
| 3e-i | §3e's dated prediction, settled at the source before its instant | record only |
| 3f | a FALSE ALARM this seat raised against the arrival unit, and withdrew | record only — **no criterion changed; the instrument was right** |
| 3g | the caller's plane: what U-3 structurally cannot see, now bounded | record only |
| 3h | the allowlist retirement inside rows 3–5, and the calibration subject's 0.26-point margin | record only |

**The rule that produces this asymmetry, and it is the whole of it.** §3a, §3b and §3e would each **loosen** the
criterion — under any of them the rows that have already breached would pass. **A criterion amended while it
is failing must never be the thing that makes the failing rows pass**, so all three go to the operator with
that fact on their face, and the threshold, the pinned query, the arrival unit and the namespace are all
untouched. §3c can only tighten, so it needed no word.

**Three consequences a reader should carry away.**

1. **The `***` residual has NOT been re-pointed, re-scoped or re-thresholded.** Rows 1 and 2 stand as breached.
2. **Nothing in §3f changed the instrument.** It records a defect this seat reported against U-3 and then
   withdrew; `dedup_inert` was correct throughout.
3. **Rows 3–5 span five deploy instants and must not be read as confirming any of them** — see §3d-i for the
   one whose effect is undetectable at this instrument's own window size.


### 3a · The residual criterion has no floor under its denominator — PROPOSED, and DELIBERATELY NOT APPLIED

`***` residual ≤ 10 % is a **share**, and §3 puts no minimum on `window_lines`. Reconstructing the criterion across the
30 days to 2026-09-16 (rolling W = 3 d, the pinned query's own population: every line where
`coalesce(chiropractor_guid, office.chiropractor_guid)` is present; residual = the rows whose value is the literal `***`):

| | |
|---|---|
| days that would have **passed** ≤ 10 % | **25 of 31** |
| days that would have **breached** | **6** |
| longest actual **consecutive pass run** | **15 days — 2026-08-27 … 2026-09-10** |

Two of the six breaches are not attribution signals at all. **2026-08-25 read 25.3 % on 79 lines; 2026-08-26 read
92.6 % on 27 lines** — quiet weekend days where a handful of unattributable lines blew the ratio. 92.6 % on 27 lines is
a signal about Sunday, not about attribution. **This is the UNTAKEN-ZERO discipline applied to a ratio instead of a
count, and the soak design missed it.**

**Proposed guard:** the residual criterion is evaluated only when the day's `window_lines` clears a floor; below it the
cell reads `UNTAKEN (denominator N < floor)` and neither passes nor fails. The floor itself wants the operator's word,
because it sets how quiet a day may be before the instrument declines to judge.

**NOT APPLIED, on purpose, and it does not rescue row 1.** Row 1 breached on **1,306 window lines** — a real denominator,
a real burst, a true reading. A guard written while failing a criterion must never be the thing that makes the failing
row pass, and it does not here. Recorded now so the correction and the failure it was discovered by stay in the same
place.

**What this measurement does change** is the shape of the blocker, and the change runs the *hopeful* way: on the
evidence, seven consecutive clean rows are not merely possible but have happened twice inside the last month. The arm
needs **seven days without a burst**, not the upstream defect gone. The honest statement to the operator is a
probability over a date, not a wall. **The threshold is not to be raised, and the residual is not to be re-pointed:
the tripwire reported that attribution was degrading, which is exactly what it was built for, and a row made green by
moving the line it failed is the F-2 failure written out in full.**


### 3b · The residual counts REDELIVERIES as new lines — a false rate, PROPOSED and DELIBERATELY NOT APPLIED

Found 2026-09-16T16:40Z, after the EBI lane pointed at the mechanism. Split by `(stage, error_type)` per
hour over 36 h, the no-body class (`parse/WebhookValidationError`) reads:

```
09-15 19Z  28    20Z  8    21Z  4
09-16 00Z   4    03Z  4    06Z  4    09Z  4    12Z  4    15Z  4        = 64 *** lines
```

That is **one rejected batch** — ~28 first deliveries — re-delivered by SendGrid on a 3-hour, 72-hour
ladder, each pass a new trace id and a new `***` line. The criterion is line-based, so it counts every
redelivery of the same email as fresh unattributable traffic, and a single arrival inflates the share for
three days. **Not a false zero and not a false confirmation: a correct count with a wrong denominator in
time — a false rate.** The day-2 climb (0.1136 → 0.1390 across 16 runs with nothing new arriving) is this
ladder accumulating inside the 3-day window while quieter hours age out.

**Proposed de-dup:** count first deliveries, not lines — collapse the class to one arrival per 3-hour
bucket. The ladder is deterministic enough that no message id is needed (the lines carry none).

**NOT APPLIED, on purpose, and here is the number that is the reason:** de-duplicated, row 1's day-max
residual falls **well under 10 %** and rows 1–2 pass. A criterion amended while it is failing must never be
the thing that makes the failing rows pass, and this one would. It goes to the operator with that fact on
its face, beside §3a. The threshold is not raised and the residual is not re-pointed.

**Population note, so nobody inherits it wrong:** the residual has exactly two feeders in 36 h —
`parse/WebhookValidationError` 64 and `resolve_office/OfficeResolutionError` 15. `FieldExtractionError`
contributes **zero**: `extract_fields` runs after `resolve_office`, so those lines carry a guid and are
attributed. A neighbouring lane's split of *all* stage exceptions is a different population from this
residual's *unattributable* lines; the two agree on the no-body class and must not be summed.


### 3d · Deploy instants bounding rows 3–5, recorded before those rows are read

**autom8y-data #472 (the lead-search 400 fix)** — merge `769522ff` **2026-09-17T00:08:37Z**; task definition
`autom8y-data-service:651` registered **00:30:43Z**; tasks created 00:30:56Z / 00:31:27Z, running 00:31:52Z /
00:32:21Z; rollout COMPLETED, 2 of 2. **Verified own hands 00:41:32Z**, not taken on report. Merge-to-running
**23m 15s**. It affects two offices on this page — `ccb52f4c` (13 of 17 lead-search 400s in 30 d) and
`79be1b75` (4 of 17) — by changing the **terminal class** (a decline becoming a possible booking), **not the
arrival count**: `terminal_decline` and `booking_completed` are both in the arrival unit, so a converted mail
stays one arrival and gains a booking. **Rows 3–5 span it** (W = 3 d from ~00:30Z 09-17).

**Recording conditions for those rows.** (i) Each records the boot instant on its face. (ii) **If `79be1b75`
leaves the ZERO floor after the boot, that is our own lead-search dependency starting to work — not the clinic
starting to book.** The E-6 shape: a plumbing change wearing a behaviour's clothes, and it must never read as a
recovery. (iii) The claim that the fix *can remove a floor firing but never create one* holds for the
decline→booking conversion, with one escape: those 17 mails now proceed past `match_lead` into booking stages
they never reached, and any downstream non-200 re-enters the `booking_intake_fault` per-redelivery fan-out,
which **inflates arrivals and drives a rate down**. Small at 17 per 30 d, unmeasurable before the boot, and the
only path by which the monotonicity fails — so the realization read includes `booking_intake_fault` on those two
offices holding at its pre-boot level.

**A second instance of the S10 tag-versus-digest finding, measured here.** `:651` references its image by the
**mutable tag** `data:769522f`, not by digest — ECR resolves that tag to `6cf2cd0e…` (pushed 00:24:25Z), which is
what both running tasks report. So a rollback to `:651` by revision number would carry whatever `769522f` names
at that later instant, exactly as `:648` would have. **On this family a revision number is a config floor, never
a bytes floor**, and that is now confirmed on two separate deploys rather than one.
### 3d-ii · Two MORE deploy instants inside rows 3–5, and what they do to §3e-i

Recorded 2026-09-17T04:40Z, verified own hands on the version plane rather than taken on a neighbouring
lane's report. **Rows 3–5 now span five instants, not three.**

| # | instant | what | version / sha |
|---|---|---|---|
| 1 | 2026-09-17T00:30Z | autom8y-data #472 boot | task def `:651` |
| 2 | 2026-09-17T01:05:49Z | autom8y #2324 (split) | **v74** `36a8ee38d1c9` |
| 3 | 2026-09-17T03:46:06Z | autom8y #2350 | **v75** `6c763b679732` |
| 4 | **2026-09-17T04:24:01Z** | **the main-is-red fix, whose own change was a test and a docstring** | **v76** `e7ec666179d3`, alias `live` → v76 |
| 5 | **2026-09-17T04:24:19Z** | autom8y-data `6700c517`, gate-contract server half, boot ≈ 04:47Z | endpoint only ACCEPTS a caller-resolved lead; its client is behind a flag defaulting off |

**Instant 4 also applied log retention 365 to all six `autom8-email-booking-intake*` groups, including this
instrument's own `-office-floor` group.** Verified own read, `nextToken` absent so the listing is complete.
**Inert for the soak:** retention governs how long lines persist, 365 days exceeds both W = 3 d and the 30-day
booking lookback, and it touches no threshold, no pinned query and no namespace. **It does not reset the soak.**

**What instant 4 DOES change is the meaning of the §3e-i confirmation, and this is the point of recording it.**
§3e-i measured `502 → 200` on **v73 versus v74**. The ≈ 06:35Z ladder slot will execute on **v76**. If v76
altered the parse path, that read confirms v76's behaviour and not v74's. **RESOLVED by measurement, not by report.** The neighbouring lane
first said instant 4's commit carried "a test and a docstring"; pressed, they corrected that a **source** file
changed too and offered an AST proof. **Reproduced own-hands here against the merge's first parent:**

```
files changed by the merge : name_evidence_counts.py (+25/-?) and its test -- 2 files
bytes identical            : False   (25,908 -> 26,947)
AST equal WITH docstrings   : False
AST equal WITHOUT docstrings: True
```

**Every difference is docstring text; the executable AST is identical.** So **v75 → v76 changes no executable
code in this service**, and the ≈ 06:35Z read on v76 is behaviourally comparable to the v73/v74 pair. The read
still **records the executing qualifier from the log-stream name on its face**, and its verdict stays scoped to
the version it actually ran on — comparable is not the same as identical.

**Note on how the retention change arrived, because it is the merged-versus-applied gap in one object.** That
merge's own diff contains **no terraform at all**. The retention change was merged separately and earlier, and
was applied by **this** deploy's terraform run. **A deploy applied a change that was not in the commit that
triggered it.**

**A general instance worth keeping, in the neighbouring lane's own framing and confirmed here: a merged
terraform change and an APPLIED one are different states, and nothing marks the gap.** Instant 4's deploy
carried what its own commit contained, not a change merged eight minutes later; a census change believed to
have landed with it had not, and its allowlist parameter still read the prior version. **A plan that merges is
not a plan that applies** — the same sentence this wave already learned on alarms, arriving by a different
route. **Consequence for this file: every instant above is recorded from the version/alias plane or the log
stream, never from a report that a merge happened.**


### 3d-i · The three realization reads §3d demanded, taken — and why one of them can never be taken

Read 2026-09-17T04:15Z, 3.67 h after the autom8y-data #472 boot. §3d set three recording conditions for rows
3–5 and owed three reads. All three are taken here; **two return a reading and the third returns a reason.**

**Read 1 — the named escape of condition (iii) has NOT fired.** Terminal-class mix for both affected offices,
each window matched to the 3.67 h elapsed since the boot, **with the same clock hours 24 h earlier as a
diurnal control** so a busier evening cannot read as an effect:

| window | `terminal_decline` | `ad_lead_gate_refused` | `booking_completed` | **`booking_intake_fault`** |
|---|---|---|---|---|
| POST-boot | 9 | 0 | 0 | **0** |
| PRE-boot | 17 | 0 | 0 | **0** |
| −24 h control (post-slot) | 6 | 0 | 0 | **0** |
| −24 h control (pre-slot) | 8 | 2 | 2 | **0** |

`booking_intake_fault` is **0 in all four windows**. The escape §3d named — mails proceeding into booking
stages they never reached, a downstream non-200 re-entering the per-redelivery fan-out, arrivals inflated and
a rate driven down — **has not fired.** The 17 → 9 fall in declines is matched in shape by the control's 8 → 6,
so it is diurnal and not the boot.

**Read 2 — and the structural finding, which matters more than read 1.** Every `ccb52f4c` decline in every
window is class `no_appt_dt`. **The lead-search class #472 addresses is absent on both sides**, and absence
here is not evidence:

```
#472 target class for ccb52f4c        13 events / 30 d   (SOAK §3d)
observed window                        3.67 h
EXPECTED count of the target class     0.066
expected count over the soak's own W = 3 d               1.3
hours to expect 3 of them             166 h  =  6.9 d
```

**Rows 3–5 span the boot and cannot evidence the conversion.** A criterion whose window is 3 days cannot
detect a class arriving 13 times in 30 days; to expect three of them takes 6.9 days, more than twice the
window. **This is not "untaken for now" — it is undetectable at the instrument's own window size**, and no
number of clean rows will change that. It belongs beside B-2: a thing whose rate is below the criterion's
resolution cannot be evidenced by that criterion, and a row that passes says nothing about it either way.
**Rows 3–5 must therefore not be read as confirming #472's realization**, and §3d's condition (iii) is
discharged as *escape did not fire*, never as *conversion observed*.

**Read 3 — condition (ii) cannot be graded at all, and the zero is controlled.** `79be1b75` reads 0 in all
four windows. That zero is only meaningful against a control, so: the office emits **99 lines across 6 days in
30 d, last emission 2026-09-14** — silent for three days before the boot. So it has not "left the ZERO floor";
**it is not on the page at all**, and with 0 arrivals it cannot meet `arrivals >= 5` either. Condition (ii) is
recorded UNGRADEABLE on this plane rather than passed.

**The probe after-window, re-read wide.** The 02:51:48Z read was untaken on too narrow a window. Re-read
02:51:40Z → 04:11:04Z: **1 `terminal_decline` at `ccb52f4c`**, against a control of **204 lines on the intake
plane** in the same window. The window is live, so the 1 is a reading and no longer an untaken zero.

**A filter-agreement check run before any of these numbers were written down.** Two scripts used two different
office filters — `@message like /ccb52f4c/` and a parsed `chiropractor_guid` equality. Tonight already
produced one number that was about a different object than it named (§3e's hash basis), so both filters were
run over identical windows: **9 and 9 post-boot, 1 and 1 post-probe — exact agreement, every event class.**
The numbers above do not depend on which filter produced them.


### 3e-i · The §3e prediction, SETTLED AT THE SOURCE two hours before its instant

§3e committed to a dated prediction: that `pipeline_completed.status` moving `failed → declined` means
SendGrid receives a terminal response and stops the 3-hourly ladder, testable at the ≈ 06:35Z slot. **That was
a proxy.** The thing itself — the HTTP status SendGrid actually received — is recorded in the API Gateway
access log for this route, which has `$context.status` in its format. Read directly, 2026-09-17T04:35Z:

```
PRE  (v73)  00:35:00-00:39:00Z   POST /webhooks/sendgrid   502 x4   responseLength 167
POST (v74)  03:35:00-03:39:00Z   POST /webhooks/sendgrid   200 x4   responseLength 196
```

**The same four-request cluster, one ladder period apart, on the same route: 502 before, 200 after.** The
`502` is a Bad Gateway from the handler raising, and **it is the retry driver**. It is gone.

**Control, so the zero is taken and not untaken.** Status by hour on that route across the deploy:

| window | 200 | 502 |
|---|---|---|
| 09-15 22:00Z → 09-17 01:00Z (pre) | 246 | 60, in a 3-hourly pattern of 4 |
| 09-17 02:00Z → 04:00Z (post) | **12** | **0** |

The post window is **alive at 12 successful requests**, so the zero is a reading. It is also only three hours,
i.e. **one ladder period**, so the aggregate alone would be weak — **the load-bearing evidence is the paired
cluster above**, the same class measured one period apart, not the aggregate.

**SCOPE CORRECTION, and it changes a word that mattered.** The EBI client lane reproduced the paired cluster
own-hands and then caught that the control window above starts at **02:00Z**, which excludes the deploy hour.
Measured from the deploy instant itself, `01:05:49Z → now`, the distribution is **200 × 23 and 502 × 1**. The
single 502 is at **01:07:29Z**, one minute forty after the deploy, latency **22,264 ms**, and the lambda lines
in that minute carry **`booking_intake_fault`** — not the no-body class.

**So the correct sentence is "the 502s for THIS CLASS are gone", never "there are no 502s".** The stronger
version would have been a **defect report, not a success**: `booking_intake_fault` returning 502 is the RIGHT
behaviour for a transient failure, because a transient failure must stay retryable. **A wholesale
disappearance of 502 would mean transients were being swallowed too**, which is precisely what removing the
LLM narrowing was meant to avoid. The class moved; the mechanism did not.

**And the two neighbouring accounts were never opposed — this seat was wrong to frame it as one winning.**
Their rule was *never convert a loud 4xx into a SILENT 2xx*. What shipped returns 200 **and** emits
`terminal_decline` with `class = no_body_field` plus a durable `terminal_decline_parked` carrying its own
`park_key`. **The 2xx is not a swallow precisely because the park is loud and durable.** "One parked 200" and
"do not swallow the 4xx" describe the same shipped object from two sides. What the access-log read settles is
something neither account contained: **the caller now receives a terminal answer, so the retry driver is
removed at the source.**

**This resolves the conflict between the two neighbouring accounts of the fix's emission shape.** One lane said
it turns the retry chain into *"one parked 200"*; the other said it *"must attach the park at the raise and not
swallow the 4xx into a 2xx"*. **What shipped returns 200.** The first account describes the deployed behaviour.

**What this does and does not establish.** It establishes that the retry DRIVER is removed at the source: a 200
is what tells SendGrid to stop. It does **not** by itself observe SendGrid stopping — that is the 06:35Z slot,
which is now a **confirmation rather than the decider**, and is still owed either way. **If 06:35Z fires at 4
despite a 200, the finding is about SendGrid's retry semantics and not about this fix**, which would be a
different and more interesting result than the one predicted.

**Method note, because it is the transferable part.** §3e's prediction was built on `pipeline_completed.status`,
a field the service writes about itself. The access log records what the *caller* received. **When a claim is
about what another party will do, measure the thing that party sees, not the thing we say about ourselves** —
and here that was available the whole time, two hours before the clock this seat had armed.


### 3f · A FALSE ALARM on the arrival unit's de-dup branch, caught before publishing — and the exact scale at which `count_distinct` stops being exact

Found 2026-09-17T04:40Z. **This section exists because the claim it nearly made would have been a defect
report against U-3's core, and it was wrong.** Recorded in full because the next reader will reach for the
same query and get the same wrong answer.

**What this seat nearly published.** Re-asking FACT-1 over 30 days instead of the 2.7 h of §3e:

```
count(message_id) = 2517 ,  count_distinct(message_id) = 2118   ->  "399 DUPLICATES"
```

The reading would have been: FACT-1 is falsified, the de-dup branch is LIVE, `arr_id` is not additive across
day bins, the day-N fold is inexact, and U-3 no longer means what §3e says it means. **All of that is false,
and it fails for two compounding reasons, each sufficient on its own.**

**Cause 1 — `count_distinct` is APPROXIMATE, and here is the scale at which it starts.** Measured against an
exact enumeration of the same rows:

| window | id-bearing lines | `count_distinct` | EXACT distinct | delta |
|---|---|---|---|---|
| 1 d | 111 | 111 | 111 | 0 |
| 3 d | 308 | 307 | 307 | 0 |
| 7 d | 516 | 515 | 515 | 0 |
| 14 d | 1000 | 999 | 999 | 0 |
| **30 d** | **2517** | **2118** | **2384** | **−266 (11 %)** |

**So 399 of the "duplicates" were an artefact of an approximate aggregate. The real number is 133.**

**Cause 2 — the population. All 133 real duplicates are a second line the evaluator already excludes.**
Classified individually:

| shape | count |
|---|---|
| `quarantine_capture_written` + `terminal_decline` sharing one id | 132 |
| `park_body_retained` + `terminal_decline` sharing one id | 1 |
| **same office, BOTH lines terminal and office-bearing** | **0** |

Every one is **one mail emitting a second, NON-office-bearing line**. The pinned query's first clause is
`filter ispresent(office_guid)`, so those lines are not in its population at all. **Not one duplicate is a
redelivery counted twice.**

**Therefore the instrument is right and this seat was wrong.** The evaluator publishes `dedup_inert` on every
run as its own tripwire for exactly this: **73 of 73 runs over 14 d report `dedup_inert = 1`, and that is
CORRECT.** FACT-1 holds inside the population U-3 is computed over.

**And `count_distinct` is exact everywhere it is actually used.** It appears twice, in `PINNED_QUERY` at
**W = 3 d** and in `DAILY_QUERY` binned **per UTC day** — both measured exact above. The 30-day booking
lookback issues **no** 30-day aggregate: `last_booking_ages` folds the same per-day bins and only tests
`bk_id + bk_noid > 0` per bin. **So `arr_id` and `bk_id` are exact where they are read, and the approximation
cannot reach a page.**

**The standing hazard, which is the part worth keeping.** Anyone AUDITING this instrument over a 30-day window
with `count_distinct` will get an 11 % undercount **and will read it as duplicates that do not exist**. That is
precisely what happened here. **Above roughly 1,000 distinct values on this log group, `count_distinct` must be
checked against an enumeration before any conclusion rests on it.**

**How it was caught, because the method is the transferable part.** Two of this seat's own numbers disagreed
over the same window — an aggregate saying 2118 and an enumeration saying 2384. **The choice was to find out
which was right rather than to pick the one that made a finding.** The first would have read as a defect in the
arrival unit on the night before an arm decision. **A disagreement between two of your own instruments is the
finding; it is never a number to choose between.**


### 3g · The caller's plane — what U-3 structurally cannot see, now BOUNDED rather than unmeasurable

The API Gateway access log (`/aws/apigateway/autom8-email-booking-intake`, retention 365 d) records requests
**the handler never ran**. Those are arrivals U-3 cannot count by construction, not by defect. **B-2's shape
was "a hole whose defining property is emitting nothing cannot be measured on the plane it blinds" — and this
is that hole measured, by changing planes.**

**The gateway-rejected class is BOUNDED and negligible.**

| status | 30 d | per day | handler ran? | visible to U-3? |
|---|---|---|---|---|
| `413` payload too large | **2** | **0.07** | **no** — 0 lambda lines within ±3 s on both | **no, invisible** |
| `503` gateway timeout | 96 in 30 d | **0.33–0.43 steady-state, NOT 3.20** — see the correction below | **yes** — lambda lines present on 5 of 5 sampled | see below |

**Positive control, so the "no lambda lines" reading is a measurement and not a failed query:** the identical
method over three `200`s finds lambda lines on **3 of 3**. The method can detect a handler run; it did not
detect one for either `413`. **So U-3's structural blindness to gateway rejections is bounded at ~0.07
arrivals/day — negligible against A = 5, and now a number instead of an unknown.**

**The `503` class is a timeout, and its consequence for U-3 is NOT proven here.** All 96 carry
`integrationLatency` of 30,000–30,001 ms, i.e. exactly the gateway's 30-second ceiling, and lambda `Duration`
values above 30 s coincide in 6 of 8 sampled instants (33.3 s, 33.9 s, 37.6 s, 39.6 s, 41.5 s, 42.1 s). **The
coherent mechanism is: the handler runs past the gateway's ceiling, the gateway answers 503, SendGrid retries,
and the mail arrives again.**

**What is NOT established, stated plainly: this seat looked for terminal lines within ±180 s of each 503, not
for lines belonging to the SAME invocation.** Other mail flows concurrently, so those lines may belong to other
requests. **The "terminal present on 8 of 8" reading does not support any claim about the 503's own
invocation.** Proving it needs the access-log `requestId` correlated to the lambda `REPORT RequestId`, then a
later invocation carrying the same `message_id`.

**But §3f bounds the harm without needing that proof, and this is the useful part.** A 503-driven redelivery
produces a second terminal line for the same mail. **If that line carries a `message_id`, `count_distinct`
collapses the pair and the mail counts ONCE — the de-dup branch is exactly the protection against this.** If it
does NOT carry one, it lands in `arr_noid`, which is a per-line sum, and the mail counts TWICE.

**Which is precisely why the no-body class inflated the residual before #2324.** On v73 that class emitted
`booking_intake_fault`, which carries **no** `message_id` (measured: present on none of the 12 pre-deploy
traces), so every redelivery counted afresh. On v74 it emits `terminal_decline`, which **does** carry one.
**§3b's false rate, §3e's field defect and §3f's de-dup branch are three views of one mechanism: whether a
terminal line carries the identity that lets a redelivery be recognised as the same mail.**

**★ CORRECTION TO THIS SECTION'S OWN `503` RATE, and the way it was caught is the point.** The EBI client
lane applied **this section's own outage-versus-rate warning to this section's own number**, one class over.
Verified on this seat's instrument:

| window | total requests | `503` | `503`/day |
|---|---|---|---|
| 1 d | 264 | 0 | 0.00 |
| 3 d | 751 | 1 | 0.33 |
| 7 d | 1,354 | 3 | 0.43 |
| 14 d | 2,861 | 13 | 0.93 |
| **30 d** | **22,397** | **96** | **3.20** |

**The 30-day window holds 22,397 requests against 2,861 in the last 14** — roughly 19,500 of them in the same
tail the `502` burst occupies. **So 3.20/day is the outage; the steady state is 0.33–0.43/day, an order of
magnitude lower.** The warning against a 30-day baseline was written in this very section and then not applied
to the line above it. **Recorded as this seat's error, corrected by the neighbouring lane using this seat's own
rule.**

**And the defect does NOT retire with the rate, because it is a config mismatch rather than a frequency.**
Measured on the serving qualifier: **the Lambda's `Timeout` is 60 s while the gateway gives up at ~30 s** (all
96 carry `integrationLatency` 30,000–30,001 ms). **So the handler may keep running for ~30 s after SendGrid
has been told the delivery failed.** That is true at any rate; the rate only sizes how often it bites — about
one mail every two to three days at steady state. **The harm has a direction:** the caller believes it failed
and retries, so the mail may be processed twice while the first pass was still succeeding, which is the
duplicate-write class the v75 guard exists for. **Neither lane has proven the handler completes in the 30–60 s
band, nor that SendGrid retries on a 503** — both are inferences from config and timing, and are recorded as
such, not as findings.

**A denominator warning while this plane is in use:** `/aws/lambda/autom8-email-booking-intake-ebi` is an
**orphaned log group** — retention 365, `storedBytes` 0, and **no function of that name exists**. It is one of
the six groups the 04:24:01Z retention change touched. Harmless, but it must never enter a denominator of
groups or functions.

**A population warning on this log group, because the obvious 30-day read is misleading.** Of 17,388 `502`s in
30 days, **15,297 (88 %) fall in four days, 2026-08-24 to 08-27**, during which successful requests collapsed
to 38–48/day against up to 5,032 failures — a multi-day outage, not a rate. Outside that burst the class runs
8–155/day. **It is outside W = 3 d and outside every soak row recorded so far, so no row is affected** — but
any 30-day baseline computed for this endpoint is quoting the outage, and must not be used to size anything.


### 3h · The contente allowlist retirement landed INSIDE rows 3–5, it targets 12 of 12 offices on this page, and it fires no floor — but the calibration subject is 0.26 points from one

**Instant 6, verified own hands on both planes.** SSM parameter
`/autom8y/email-booking-intake/contente-booking-census` went **v7 → v8 at 2026-09-17T04:33:07.738Z**; the
alias moved to **v77 at 04:33:08Z**, one second later. Live parameter read by this seat: **33 distinct
office guid8**, and **`ccb52f4c` is ABSENT — retired.**

**★ THE MECHANISM THAT MATTERS MORE THAN THE INSTANT, from the EBI client lane and adopted here: writing the
parameter does not retire an office — a COLD START does.** `_census.py` resolves the parameter at cold start
and then sets env vars `ServiceConfig` reads. A warm execution environment keeps the allowlist it resolved when
it started, for as long as it lives. **So the retirement is fleet-effective at 04:33:08Z because the v77 deploy
forced every environment to cold-start, not because the parameter was written.**

**Standing hazard for this file, and the reason it is recorded here rather than in a neighbour's:** *a soak row
spanning a census parameter write WITHOUT an accompanying deploy has had its subject changed at an instant
nobody recorded, and possibly PER CONTAINER rather than fleet-wide.* A per-container change is not an instant
at all; it is a smear whose width is the container lifetime. **Any future row must record whether a census
write was accompanied by a deploy, and if it was not, the row cannot claim a clean before/after.**

**The intersection is total, which this seat did not expect.** Hashing the whole graded population through the
recovered transform: **all 12 retired handles are offices on this page in W = 3 d.** Not a sample of the fleet
— every retired office is one this instrument grades.

**Floor impact, measured rather than assumed.** Only **3 of 12** had any contente booking at all in W = 3 d, and
removing them crosses nothing:

| guid8 | arrivals | bookings | contente | native | rate now | rate after | floor after |
|---|---|---|---|---|---|---|---|
| `03859024` | 14 | 6 | 1 | 5 | 42.86 % | 35.71 % | clear |
| `800f9fe1` | 6 | 3 | 1 | 2 | 50.00 % | 33.33 % | clear |
| `d167d635` | 63 | 16 | 1 | 15 | 25.40 % | 23.81 % | clear |
| the other nine | — | — | **0** | — | unchanged | unchanged | clear |

**No retired office crosses either floor.** E-6's reading that the founding office "books by its native path"
is confirmed on the booking-event mix: `ccb52f4c` has **0 contente bookings and 10 native in 30 d**, so the
retirement does not touch its booking count at all.

**★ BUT THE CALIBRATION SUBJECT IS 0.26 POINTS FROM THE RATE FLOOR, AND THAT IS THE FINDING.**

```
ccb52f4c, W = 3 d : arrivals 181 · bookings 5 · rate 2.76 %   RATE floor = 2.50 %
losing ONE booking   -> 4/181 = 2.21 %   FLOOR FIRES
gaining 19 arrivals  -> 5/200 = 2.50 %   FLOOR FIRES
```

**One booking decides whether the founding office is on the page.** E-5 recorded that it "oscillates at the
RATE floor"; this is that oscillation quantified, and the margin is one event wide. **Every row 3–5 must
record this margin on its face**, because a floor firing on this office in the next three days is far more
likely to be a one-booking fluctuation than a change in the clinic's behaviour — and per E-6 its RATE reading
is a plumbing shape to begin with.

**Correction carried, since two figures for this instant are circulating.** A recount seat reported the
retirement at **04:16:36Z**. That is wrong and this seat verified why: at 04:16:36Z the live alias was still
v75 and the parameter still v7. **Both independent instruments — SSM parameter history and the Lambda version
list — put it at 04:33:07.738Z / 04:33:08Z.**


### 3c · The deadman criterion passed VACUOUSLY on an empty set — APPLIED, because it can only tighten

§3 requires *"both deadman alarms OK with actions = scratch only"*. That is an **all-quantifier with no
cardinality assertion**, and `all(...)` over an empty set is **true**. Measured 2026-09-16T18:2xZ against a
deliberately mistyped prefix:

```
real prefix  -> 2 alarms   'all actions are scratch-only' = True
typo prefix  -> 0 alarms   'all actions are scratch-only' = True     <- VACUOUSLY TRUE
```

**So a DELETED or RENAMED S-1 alarm passed this criterion silently** — and an alarm's *absence* is precisely
the failure a deadman exists to catch. The instrument could not see the one thing it is for.

**Cure, applied:** name the expected set and assert its cardinality **before** grading it —
`…-freshness-prober-liveness`, `…-lambda-freshness`, `…-office-floor-dlq-not-empty`,
`…-office-floor-lambda-errors`. The row now prints `N of 4 present`, the missing and unexpected names, the
off-scratch actions and the not-OK states, and a missing alarm is a **BREACH**, not a silent pass.

**Proven two-sided rather than by presence:** real set → 4 of 4, missing none, PASS; the same check with one
alarm removed → 3 of 4, missing named, **FAIL, the guard bit**.

**Why this one is APPLIED while §3a and §3b are not.** The asymmetry is the whole of it. §3a and §3b would
**loosen** the criterion — de-duplicated, the failing rows pass — so applying either while the soak is failing
would be the amendment rescuing the rows it was written against, and that decision is the operator's. §3c can
only **tighten**: it turns passes into failures and can never rescue a failing row. A strictly conservative
change to what the instrument *checks*, with no change to the pinned query, the arrival unit, or any
threshold, does not reset the soak and does not need a word to be honest.

**Rows already read:** row 1 named all four alarms explicitly with their actions, so it re-verifies under the
stricter form on its own recorded text. Row 0 named the two that existed at its instant. The stricter form
binds from row 2 forward.

**Provenance:** found by turning the identity lane's own S12 self-criticism on this instrument. They measured
six `all`-style predicates in their grader passing over an empty population and printing HOLDS, and flipped
each to VACUOUS. The same question asked here found this. **A predicate that examined nothing cannot support a
pass — and the emptier the set, the more confident the `all`.**

### 3e · The residual reads `chiropractor_guid`; the attribution now lands in `office_handle` — PROPOSED, DELIBERATELY NOT APPLIED

Found 2026-09-17T04:10Z, reading whether autom8y #2324 (merged, deployed **2026-09-17T01:05:49Z**) removed the
no-body class from the `***` residual. It did not, but not for the reason either neighbouring lane gave, and
not for the reason this seat first published.

**Anchored at the qualifier, not at the deploy time.** This function carries an alias (`live`), so a
no-qualifier config read attests `$LATEST` and not what served — the standing wrong-object hazard. The log
stream name carries the executing version, so the lines settle it themselves: the pre-deploy no-body lines ran
on **v73**, the 03:35–03:38Z lines on **v74**. Those redeliveries genuinely executed #2324's code. The window
after the 03:46:06Z deploy is **17 minutes against a 3-hour ladder**, so its zero is UNTAKEN and is not read here.

**What #2324 changed, measured two-sided across the boundary on this seat's own connection:**

```
v73 (pre) : 12 no-body traces -> 12 booking_intake_fault,  0 terminal_decline, 0 parked
v74 (post):  4 no-body traces ->  0 booking_intake_fault,  4 terminal_decline, 4 parked
pipeline_completed.status : "failed" (v73) -> "declined" (v74)
```

**U-3 is unaffected, and that is the leg only this seat could check.** `booking_intake_fault` and
`terminal_decline` are both in the arrival unit and `terminal_decline_parked` is excluded by design, so the
class move is arrival-neutral: **1.00 counted lines per trace on both sides**. FACT-1 was re-asked because
`terminal_decline` is the one event carrying `message_id` and a redelivery ladder is exactly what would make
the de-dup branch live — `count(message_id) = 13`, `count_distinct = 13` over the window. **The branch stays
inert and U-3 still means "count terminal-outcome lines."**

**The new field, and why the criterion cannot see it.** The post-deploy lines carry `office_handle = 75c2be4e`
on **4 of 4**, `office_handle_source = routing_guid` — while `chiropractor_guid` is still `***` on 4 of 4. The
residual is defined on `coalesce(chiropractor_guid, office.chiropractor_guid)`. **So the class is now
attributable on the line and the criterion keeps counting it as unattributable, because it reads the other
field.** That is a defect in this instrument, not in the fix.

**A false negative this section nearly carried, recorded because the next reader will hit it.** Tested
`75c2be4e` against the 74-office graded population on both declared bases — raw `guid8` and `sha256(guid)[:8]`
— and got **NONE on both**, which reads as "not a real office" and would have corroborated a neighbouring
lane's conclusion that this class can never attribute. It is wrong. Asking instead whether the token appears
anywhere else at all found it a second time with `office_handle_source = chiropractor_guid`. Lines carrying
**both** fields give the mapping by observation:

| office_handle | chiropractor_guid |
|---|---|
| **75c2be4e** | **ccb52f4c** |
| f5c07c30 | d167d635 |
| fc1df111 | 7a1e83fd |
| bea49103 | 8a9b1a84 |

**The transform is `sha256(guid8 ASCII)[:8]`** — verified own hands, reproducing all four pairs and mapping
distinct guids to distinct handles. It was recovered only after the EBI client lane named it; nine candidates
tried here first reproduced none of the pairs.

**And the worse fact, found while checking whether the arming receipt needed the same correction: the basis was
already written in this seat's own record.** Receipt E-6 states *"Identity confirmed two ways: `sha256(guid8)`
and the full-guid hash both resolve to this office, from two seats."* **The transform was declared, in the
governing document of this very wave, and this seat re-derived instead of reading it.** So the lesson is not
"the handle declares no basis on the line" — though it does not. It is that **a declared basis was available
and was not consulted**, and nine wrong candidates were generated in its place. The line-level complaint stands
for future readers; the error here was not the line's. **The reason they missed is the finding, not a footnote: the
log field holds the REDACTED full guid `ccb52f4c-***`, and this seat hashed that, while the basis is the bare
8-character prefix.**

```
sha256("ccb52f4c-***")[:8] = afbd20cf   <- what the test computed
sha256("ccb52f4c")[:8]     = 75c2be4e   <- the actual basis, and the handle on the line
```

The slice to `guid8` was applied for DISPLAY and not to the hashed input. **A test written to catch
undeclared-basis errors carried one itself**, and it returned NONE on both bases — a confident negative that
agreed with a neighbouring lane's wrong conclusion. This is the handle-without-a-declared-basis hazard for the
third time on this wave, and the first time it bit rather than being caught. The mapping is now **derived and
computable for the whole page**, not merely observed on four lines.

**The defect that produced the divergence, which someone should own.** On these lines
`office_identity_kind` reads `absent` while `office_handle` is populated. The kind field describes the
`chiropractor_guid` resolution, not the handle, and **nothing on the line says so**. A reader keying on kind
concludes there is no identity; a reader keying on the handle finds one. Two honest readers of the same line
reach opposite conclusions, and that is exactly what happened between this seat and the EBI client lane — they
read `stage_exception`, which carries no handle at all, and concluded the attach produced nothing. **The
attach surfaces on `terminal_decline`, not on the exception line.**

**So the no-body class is the founding office's mail.** `ccb52f4c` is the confirmed relay sink of receipt E-6
(130 of 130 arrivals `unknown_loud`). The `***` residual and E-6 are **one phenomenon seen from two sides**,
which this seat did not know when §3a and §3b were written.

**Why this is NOT APPLIED, and the second reason is the load-bearing one.**

1. It **loosens**: re-pointing the residual at `office_handle` clears the breach on the rows it was written
   against. Same disposition as §3a and §3b, same rule — a criterion amended while it is failing must never be
   the thing that makes the failing rows pass.
2. **It would move those arrivals onto `ccb52f4c`'s count**, and on a relay-sink shape that is a live route to
   firing a ZERO or RATE floor on the founding office for something that is plumbing. **Trading a residual
   breach for a probable false floor firing on the founding office is a worse instrument, not a better one**,
   and the choice is the operator's.
3. **It cannot be applied to rows 1–3 in any case.** `office_handle` did not exist before 01:05:49Z, so for
   most of those windows there is nothing to re-point at. Any retrospective application would be reading a
   field into a period that never emitted it.

**The size of the trade, so the operator chooses between numbers and not between adjectives.** Measured over
the 3.04 h since the deploy, every `***` line in the window:

| event | class | handle | lines |
|---|---|---|---|
| `stage_exception` | — | none | 4 |
| `terminal_decline` | `no_body_field` | **75c2be4e** | 4 |
| `terminal_decline_parked` | `no_body_field` | none | 4 |

**One no-body trace emits three `***` lines and only one of them gains a handle.** So a re-point clears
**4 of 12 — 33.3 %** — and leaves 8 unattributable, while moving those 4 onto `ccb52f4c` (resolved through the
derived transform). **It does not clear the breach; it reduces the residual by a third and creates floor risk
on the founding office to do it.** That is a materially worse trade than it appeared when this section was
first drafted, and it is recorded here rather than argued: the decision is still the operator's.

**A structural objection to this criterion, from the EBI client lane, recorded because it is the strongest
argument against the instrument and it is not this seat's to rule.** *A residual criterion that counts
unattributed LINES charges the system for making a loss loud.* Every improvement that adds a durable record —
a park intent, a receipt, a named decline — adds a line to the unattributed bucket and worsens the number. On
this criterion **the best-scoring system is the one that emits least**, which is the condition this whole arc
exists to end. #2324 is the first instance measured: it made the class loud and the criterion scored it 50 %
worse. **The criterion is not wrong so much as pre-dated** — it was written before the thing it now measures
existed. Recorded here in the neighbouring lane's framing, unamended, and left to the operator.

**A dated, falsifiable prediction this section commits to.** `failed → declined` should mean SendGrid receives
a terminal response and stops the 3-hourly ladder. **The next slot is ~06:35Z on 2026-09-17.** Zero no-body
traces in that hour means the ladder has stopped and §3b's false rate stops accumulating **without the
criterion being amended at all** — the clean outcome. Four traces means the response is still being retried.
The park lines carry `newly_recorded: true` and a per-message `park_key`, which separates "ladder stopped"
from "ladder fired and was recognised as a repeat."

**Correction owed and made here.** This seat told the EBI client lane that at the apply *"the residual
criterion that has breached since 09-15 stops breaching."* **That sentence is withdrawn.** It was stated
before the deploy could be measured, and the measurement does not support it: the residual is unchanged,
because the criterion reads a field the fix does not populate. Whether it stops breaching now rests on the
06:35Z ladder read, not on the apply.

**Evidence limitation, stated on its face.** `office_handle` has existed for under three hours, so the
transform is verified on **four pairs**. Being a declared hash rather than an observed table, it now maps the
whole page — but four pairs do not exclude a collision in an 8-hex space, and nothing on the line declares the
basis, so a future reader must re-verify rather than inherit it.

**One ground strengthened by the EBI client lane's own reading of the source: the attach is PROSPECTIVE
ONLY.** Mail that faulted before 01:05:49Z carries no office field of any kind and stays permanently
unattributable — their 596-trace census measured that population and is not contradicted by anything here.
So re-pointing the residual would clear forward mail only, while rows 1–3 and the historical backlog remain
exactly as unattributable as they are now. **The amendment would not even repair the rows it would appear to
rescue**, which is ground 3 stated at full strength.
