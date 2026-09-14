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
| 0 | 2026-09-14 (partial, read 06:41Z) | 4 (3 S1.4b controlled invokes 06:00:27 / 06:00:48 / 06:01:07Z + the first SCHEDULED fire 06:27:15Z; `filter-log-events` one page) | 3 (A, C-dry-run, D; scheduled D: `records_scanned` 13979, offices_with_bookings 31) | 1 (leg B, 10-min window, `records_scanned_below_floor`; timestamp withheld) | 2 (06:00Z, 06:27Z — A and D only; B refused and C dry-run emitted nothing) | 8 samples since 05:52Z, min 200 s, max 2000.6 s (< 7200) | both OK (`…-lambda-freshness` OK 06:04:56Z; `…-freshness-prober-liveness` OK 06:27:14Z) | 4 — ALL four are alarm `INSUFFICIENT_DATA → OK` OK-action notifications (05:53:09 / 05:53:48 / 06:04:56 / 06:27:14Z), 0 from the evaluator (`paged:false` on all four run lines); subscriptions 0 | leg A/D: 39 offices, 3 ZERO / 0 RATE / 36 none; `ccb52f4c` quiet at 3.23 % (93 arrivals / 3 bookings) | not read (needs the 11:27Z digest) | born 05:52:27Z by run 34810812077; first scheduled fire OBSERVED 06:27:15Z; day-1 read must add the 11:27Z digest (`MessageId`, `sns:Publish` proven), the `***` share, and the full-day sums |

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
aws sns list-subscriptions-by-topic --topic-arn "arn:aws:sns:us-east-1:<ACCOUNT>:autom8-ebi-office-floor-scratch" --output json --query 'length(Subscriptions)'

# page-class distribution + the *** tripwire — from the 11:00Z digest line(s)
QID=$(aws logs start-query --log-group-name "$LG" --start-time "$S" --end-time "$E" \
  --query-string 'fields @timestamp, @message | filter @message like /office_floor_office/ | stats count(*) as offices, sum(@message like /"page_class":\s*"ZERO"/) as zero, sum(@message like /"page_class":\s*"RATE"/) as rate' \
  --output text --query queryId); sleep 8; aws logs get-query-results --query-id "$QID" --output json
```

Fences: an Insights zero needs `recordsScanned` comparable to a control (UNTAKEN-ZERO); the office-floor function has no alias, so an unqualified read IS its served object; no phone digits, guid8 only, `<ACCOUNT>` for the account id (merge-surface sweep `digits12`).

## 2b · Ruled constraint on what the soak may certify (pythia, T2 ruling on asana #454)

The fleet's booking lines carry `chiropractor_guid` only from **2026-09-09**; the 30-day `last_booking_age_days` lookback is therefore ~6 days effective on day 0 and reaches its full horizon on **2026-10-09**. Until then the soak may certify ACTIONABLE and CLASS UNKNOWN rows of the digest; it may **not** certify EXPECTED SILENCE (class ∈ {inactive, ignored} with no booking) — record those rows as `EXPECTED SILENCE (unattributable before 2026-10-09)`. A computed attribution floor printed on the page is the ruled cure (owner: S1.3 builder seat), not a re-tune of A/A′/r.

## 3 · What closes the soak

Seven consecutive complete rows with: evaluations ≥ 20/day, controlled ≥ 20/day, zero `FLOOR-REFUSED` on a healthy plane (or each refusal explained), `LastSuccessTimestamp` SampleCount ≥ 20/day, prober gauge SampleCount ≥ 280/day (`rate(5 minutes)`) with Maximum < 7200 s (cadence 3600 × buffer 2), both deadman alarms OK with actions = scratch only, exactly one page/day to scratch at 11:00Z (day count incrementing), `***` residual ≤ 10 %.
