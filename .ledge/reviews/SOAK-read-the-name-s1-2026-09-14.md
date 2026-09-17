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

**The transform is NOT recovered** — nine candidates (raw prefix, suffix, sha256/sha1/md5/blake2s prefixes,
case- and separator-variants) reproduce none of these pairs. **The mapping above is observed, not derived**,
and `office_handle` declares no basis on the line. This is the handle-without-a-declared-basis hazard for the
third time on this wave, and on this occasion it bit: the face-value miss was the answer that agreed with the
neighbouring lane.

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

**Evidence limitation, stated on its face.** `office_handle` has existed for under three hours, so the mapping
table above rests on **four pairs**. It is what exists; it is not a census, and a collision in an 8-hex handle
space is not excluded by four observations.
