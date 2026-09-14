# PROBE — `read-the-name` S1.4a · the PRE-DEPLOY half, two-sided, on the BUILT mechanism

> Station **chaos-engineer**. Sprint **S1.4a** of the `read-the-name` wave-1 shape
> (`.sos/wip/frames/read-the-name.shape.md`). Nothing is deployed; this probe exercises the
> real handler code **in-process** with a fake Insights client for the synthetic poles and the
> **real** CloudWatch Logs Insights (read-only) for the production pole, capturing the publish
> through an injected SNS client.
>
> **Self-cap: MODERATE** per `self-ref-evidence-grade-rule` — a single rite's probe of a single
> build. The three legs S1.4b/S1.7 must add are named in §11 in frozen UV-P syntax.
>
> **Fences honoured.** guid8 only — no office names, no phone digits (the live rendered page at
> §9 carries office names on the real surface; they are struck here and the strike is noted).
> No AWS resource was created. Read-only AWS only (`logs:StartQuery` / `logs:GetQueryResults`
> / `sts:GetCallerIdentity`). Every publish in this document was captured, never delivered.

---

## §1 Substrate under probe

| | |
|---|---|
| mechanism | autom8y **PR #2205**, branch `sre/s1-3-office-floor-20260914T041830` |
| commit probed | `1116e00893f3e3851a80170103bee56652da1148` |
| module | `services/email-booking-intake/src/email_booking_intake/office_floor/` |
| probe worktree | `.knossos/worktrees/wt.sre.s1-4a-probe.20260914T044450.a7f3` (autom8y; reaped after) |
| interpreter | `/Users/tomtenuta/Code/a8/a8/repos/autom8y/.venv/bin/python` (3.12.12) — the venv the builder used |
| `PYTHONPATH` | `<worktree>/services/email-booking-intake/src` |
| predicates read | `.ledge/decisions/ADR-read-the-name-s1-implementation-2026-09-14.md` D1 / D2 / D8 + errata **E-1** (page topic → scratch, R-168 governs) and **E-2** (D8.1 section predicate re-keyed on `last_booking_age_days`) |

**Module resolution receipt — printed once, as charged:**

```
email_booking_intake.__file__ = /Users/tomtenuta/Code/a8/a8/repos/autom8y/.knossos/worktrees/
  wt.sre.s1-4a-probe.20260914T044450.a7f3/services/email-booking-intake/src/email_booking_intake/__init__.py
```

### The injection seams (read before probing, per the charge)

`handler.evaluate()` is the seam and it is clean — all three AWS clients are keyword
parameters with no construction inside:

```python
def evaluate(*, logs_client, sns_client=None, cloudwatch_client=None,
             event=None, config=None, now=None, params=None) -> dict[str, Any]
```

`lambda_handler()` is the only place `boto3.client(...)` is called. `insights.run_query()`
takes the client positionally and drives `start_query` → `get_query_results`. The probe
therefore substitutes three capture objects and drives the **production code path**, not a
re-implementation:

- `FakeLogs` — serves synthetic Insights payloads (`status` / `results` / `statistics`),
  dispatching the pinned window query and the day-N lookback query by call order.
- `FakeSNS` — records `TopicArn` / `Subject` / `Message`; **publishes nothing**.
- `FakeCW` — records `put_metric_data`; **emits nothing**.

**Injected topic ARN (all synthetic poles):**
`arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch` — a synthetic account with
the terraform-declared topic *name* (`aws_sns_topic.office_floor_scratch`, `office_floor.tf:42-43`).

**Note on synthetic counts attached to real guid8 keys.** `snapshot.class_of()` is keyed by
guid8, so exercising the class-dependent paths (P1a, P6) requires guid8s that are resident in
the baked snapshot. Where a probe attaches counts to such a key, **the counts are fabricated by
this probe and say nothing about that office.** Only §9 (P7) reports measured production values.

---

## §2 P1 — ZERO pole FIRES · **PROBE-LIVE two-sided: YES**

**Input.** Control filler of six synthetic offices (`f1110001`…`f1110006`, 30 arrivals / 5
bookings each → 16.7%, quiet, and `offices_with_bookings = 6 ≥ 5`) plus two subjects at
**7 arrivals / 0 bookings**: `06a9afb0` (snapshot class `active`) and `a0000001` (absent from
the snapshot → `unknown`). `records_scanned = 31007`. `now = 2026-09-14T11:00Z`.

**Command.** `PYTHONPATH=<wt>/services/email-booking-intake/src .venv/bin/python probe.py`

**Observed — emitted `office_floor_evaluated` (real structured log line, verbatim slice):**

```json
{"window_start": "2026-09-11T00:00:00+00:00", "window_end": "2026-09-14T00:00:00+00:00",
 "window_days": 3, "arrival_unit": "U-3", "query_status": "Complete", "records_scanned": 31007,
 "records_matched": 1152, "bytes_scanned": 7953053, "estimated_records_skipped": 0,
 "log_groups_scanned": 1, "offices_evaluated": 8, "offices_with_bookings": 6,
 "control_status": "pass", "control_reason": "", "snapshot_date": "2026-09-11",
 "snapshot_age_days": 3, "evaluator_version": "s1.3", "dry_run": false, "control": "passed",
 "kind": "", "zero_floor_count": 2, "rate_floor_count": 0, "dedup_inert": true,
 "paged": true, "page_class": "digest", "event": "office_floor_evaluated", "level": "info"}
```

**Captured publish — the digest, sectioned:**

```
[1] ACTIONABLE  (booked within 30d, OR class=active | activating)
    ZERO  06a9afb0  —   arrivals=7  bookings=0  rate=0.00%  last_booking=none(30d)  day_n=0  class=active
[2] EXPECTED SILENCE  (no booking in 30d AND class=inactive | ignored)
    (none)
[3] CLASS UNKNOWN  (no booking in 30d, class not in the snapshot)
    ZERO  a0000001  —   arrivals=7  bookings=0  rate=0.00%  last_booking=none(30d)  day_n=0  class=unknown
```

| assertion | got | want |
|---|---|---|
| `floor_class(06a9afb0)` | `zero` | `zero` |
| `offer_class(06a9afb0)` | `active` | `active` |
| section(`06a9afb0`) | **ACTIONABLE** | ACTIONABLE |
| `floor_class(a0000001)` | `zero` | `zero` |
| section(`a0000001`) | **CLASS UNKNOWN** | CLASS UNKNOWN |
| `zero_floor_count` | 2 | 2 |
| publishes | 1 | 1 |

**The other side (teeth).** The *same* office at **4 arrivals / 0 bookings** — one below the
ruled `A = 5`:

| assertion | got | want |
|---|---|---|
| verdict for `06a9afb0` | `None` (absent) | absent |
| `zero_floor_count` | 0 | 0 |

The floor bites at 5 and is silent at 4. It is not a no-op renderer.

> **Named, not smoothed.** A ZERO-floor office with no booking in 30 days and no snapshot class
> lands in **[3] CLASS UNKNOWN**, not [1] or [2]. That is the ruled E-2 predicate behaving
> correctly, and §9 shows it is the *majority* outcome on live traffic — see the §10 finding.

---

## §3 P2 — RATE pole FIRES · **PROBE-LIVE two-sided: YES**

**Input.** Filler as above plus `ccb52f4c` at the S1.1-measured window-C shape: **99 arrivals /
2 bookings = 2.02%**.

**Observed captured publish:**

```
[1] ACTIONABLE  (booked within 30d, OR class=active | activating)
    RATE  ccb52f4c  —   arrivals=99  bookings=2  rate=2.02%  last_booking=none(30d)  day_n=0  class=active
```

| assertion | got | want |
|---|---|---|
| `floor_class(ccb52f4c)` | `rate` | `rate` |
| rate | `2.02%` | `2.02%` |
| `rate_floor_count` | 1 | 1 |
| publishes | 1 | 1 |

**The other side (teeth), three cuts:**

| input | got | want | what it proves |
|---|---|---|---|
| 3 bookings / 99 arrivals = **3.03%** | not listed | not listed | one more booking silences the founding shape — the floor is a threshold, not a label |
| 1 booking / **41** arrivals = **2.44%** | `rate` | `rate` | fires just inside `r = 0.025` |
| 1 booking / **40** arrivals = **2.50%** | not listed | not listed | the comparison is strict `<`, and the boundary is exactly where the ADR puts it |

The 40-vs-41 pair is the sharpest available two-sided cut: one arrival of difference flips the
verdict, so the predicate under test is the ruled arithmetic and nothing else.

---

## §4 P3 — NEGATIVE (healthy office) · **PROBE-LIVE two-sided: YES**

**Input.** Filler plus `c0000007` at **100 arrivals / 7 bookings = 7.00%**.

| assertion | got | want |
|---|---|---|
| verdict for `c0000007` | `None` (absent) | absent |
| `zero_floor_count` | 0 | 0 |
| `rate_floor_count` | 0 | 0 |
| `control` | `passed` | `passed` |
| `"c0000007" in body` | `False` | `False` |
| `LastSuccessTimestamp` emissions | 1 | 1 |

A healthy office is **neither** floor's subject and its guid does not appear anywhere in the
rendered page. The run still publishes a digest (`0 offices below floor`) and still emits the
success metric — a quiet day is an *attested* quiet day, not an absent one.

---

## §5 P4 — DEGRADED READ · **PROBE-LIVE two-sided: YES**

Three distinct degradations, each producing a **named** kind. All three fail closed.

| # | injected degradation | `control` | `kind` | publish | `LastSuccessTimestamp` | day-N query |
|---|---|---|---|---|---|---|
| a | `status = "Timeout"` | `failed` | `query_status_Timeout` | 1 × `FLOOR-REFUSED` | **0 — WITHHELD** | not run (1 query only) |
| b | `records_scanned = 499` (floor 500) | `failed` | `records_scanned_below_floor` | 1 × `FLOOR-REFUSED` | **0 — WITHHELD** | not run |
| c | `offices_with_bookings = 4` (floor 5) | `failed` | `offices_with_bookings_below_floor` | 1 × `FLOOR-REFUSED` | **0 — WITHHELD** | not run |

**Observed `office_floor_evaluated` lines, all three, at `level=error`:**

```
{'level':'error','control':'failed','kind':'query_status_Timeout',
 'query_status':'Timeout','records_scanned':31007,'offices_with_bookings':6,
 'paged':True,'page_class':'refused'}
{'level':'error','control':'failed','kind':'records_scanned_below_floor',
 'query_status':'Complete','records_scanned':499,'offices_with_bookings':6,
 'paged':True,'page_class':'refused'}
{'level':'error','control':'failed','kind':'offices_with_bookings_below_floor',
 'query_status':'Complete','records_scanned':31007,'offices_with_bookings':4,
 'paged':True,'page_class':'refused'}
```

**Captured `FLOOR-REFUSED` publish (case a), verbatim:**

```
run     : window=2026-09-11T00:00Z..2026-09-14T00:00Z (3d) | unit=U-3
control : FAILED | kind=query_status_Timeout
          query_status=Timeout | records_scanned=31007 | offices_with_bookings=6

no floor verdict was produced for this run

LastSuccessTimestamp is WITHHELD for this run; two consecutive refusals turn the
success-gap alarm red without any human reading this page.
```

The literal sentence `no floor verdict was produced for this run` (ADR D2.6) is present in all
three refusal bodies.

**The other side (teeth).** The identical healthy run:

| assertion | got | want |
|---|---|---|
| `LastSuccessTimestamp` emissions | **1** | 1 |
| metric name | `LastSuccessTimestamp` | `LastSuccessTimestamp` |
| namespace | `Autom8y/EbiOfficeFloor` | `Autom8y/EbiOfficeFloor` |

The withheld metric is **provably withheld** (0 on every refusal) and **provably emitted**
(1 on the control-PASS run). The wire to the S1.7 success-gap alarm is real in both directions.

> Incidental structural receipt: on a refusal the day-N lookback query is **never started**
> (`len(logs.starts) == 1`). A degraded run does not spend the ~155 MB second scan.

---

## §6 P5 — PAGE GATE · **PROBE-LIVE two-sided: YES** · with one named gap (§10)

**Input.** Identical healthy inputs (filler + one ZERO-floor office), `dry_run = False`, SNS
injected; only the clock varies.

| `now` (UTC) | publishes | `paged` | `page_class` | verdict still computed? |
|---|---|---|---|---|
| `2026-09-14T10:00Z` | **0** | `False` | `none` | yes — `floor_class = zero` |
| `2026-09-14T11:00Z` | **1** | `True` | `digest` | yes — `floor_class = zero` |
| `2026-09-14T12:00Z` | **0** | `False` | `none` | yes — `floor_class = zero` |

Both off-hours poles **evaluate, fold, classify and log** — they are silent on the page, never
silent on the measurement. That is the distinguishing property: the gate withholds the *reader*,
not the *verdict*.

**Third side.** `dry_run = True` at hour 11: **0 publishes, 0 metric emissions** — the parity
path cannot page and cannot write the success metric even inside the page window.

---

## §7 P6 — CLASS-AS-CONTEXT (DW-10 / erratum E-2) · **PROBE-LIVE two-sided: YES**

**Input, one run, two subjects both carrying snapshot class `inactive`:**

- `87bd31d7` — 9 arrivals / 0 bookings in the window (over the ZERO floor), **plus** a booking
  in the day-N lookback dated `2026-09-02` — 12 days before `window_end = 2026-09-14`.
- `6b93fb76` — 9 arrivals / 0 bookings, **no** booking anywhere in the 30-day lookback.

**Observed captured publish, verbatim:**

```
[1] ACTIONABLE  (booked within 30d, OR class=active | activating)
    ZERO  87bd31d7  —   arrivals=9  bookings=0  rate=0.00%  last_booking=12d  day_n=0  class=inactive
[2] EXPECTED SILENCE  (no booking in 30d AND class=inactive | ignored)
    ZERO  6b93fb76  —   arrivals=9  bookings=0  rate=0.00%  last_booking=none(30d)  day_n=0  class=inactive
[3] CLASS UNKNOWN  (no booking in 30d, class not in the snapshot)
    (none)
```

| assertion | got | want |
|---|---|---|
| `offer_class(87bd31d7)` | `inactive` | `inactive` |
| `last_booking_age_days(87bd31d7)` | `12` | `12` |
| section(`87bd31d7`) | **ACTIONABLE** | ACTIONABLE |
| `offer_class(6b93fb76)` | `inactive` | `inactive` |
| `last_booking_age_days(6b93fb76)` | `None` | `None` |
| section(`6b93fb76`) | **EXPECTED SILENCE** | EXPECTED SILENCE |
| renders `none(30d)`, never `0` | `True` | `True` |

Two offices with the **identical** snapshot class land in **opposite** sections, separated only
by the plane's own booking evidence. E-2 is implemented as ruled: class is context, never a
suppressor. The `None` → `none(30d)` render is proven — the cell that would read "booked today"
if `None` were coerced to `0` never appears.

---

## §8 P8 — PARK DE-DUP · **PROBE-LIVE two-sided: YES**

**Input.** ONE mail, TWO lines, sharing `park_key = "pk1"`:
`terminal_decline` (carries `message_id = "mid1"`) and `terminal_decline_parked`
(carries **no** `message_id`) — the S1.1-measured shape.

| measure | key | got | reading |
|---|---|---|---|
| naive line-sum | — | **2** | the double-count U-3 exists to strip |
| `distinct_park_events(...)` | `park_key` | **1** | **counts once — correct** |
| co-occurrence (keys carrying BOTH events) | `park_key` | **1** | the double-count is **detected** |
| co-occurrence (keys carrying BOTH events) | `message_id` | **0** | **the FALSE ALL-CLEAR** |
| `distinct_park_events(parked line only)` | `message_id` | **0** | the park event is **invisible** |
| `distinct_park_events(parked line only)` | `park_key` | **1** | the park event is **visible** |

**The second pole is the whole point, and it does not fail loudly — it succeeds quietly.** A
`message_id`-keyed co-occurrence detector returns `0` and reads as "no double-counting found."
The real answer is 1-of-1. The ADR as originally written specified exactly that detector; the
build corrected it to `park_key` and the correction is what this probe proves.

**At the S1.1-measured scale** (524 mails, 1,048 lines):

| measure | key | got |
|---|---|---|
| lines | — | 1048 |
| `distinct_park_events` | `park_key` | **524** |
| co-occurrence | `park_key` | **524** |
| co-occurrence | `message_id` | **0** |

524 detected versus 0 detected, on identical input, from the key choice alone.

---

## §9 P7 — PRODUCTION POLE (read-only) · **PROBE-LIVE two-sided: YES**

**Command** (the handler's own dry-run entrypoint — same pinned query, same fold, same floors,
same rendering; `sns_client=None`, `cloudwatch_client=None`):

```
PYTHONPATH=<wt>/services/email-booking-intake/src .venv/bin/python \
  -m email_booking_intake.office_floor \
  --start 2026-09-11T00:00:00Z --end 2026-09-14T00:00:00Z --print-body
```

`rc = 0`, **unpiped** (recorded from the process exit, not from a pipeline tail). Identity:
`arn:aws:sts::<acct>:assumed-role/AWSReservedSSO_AdministratorAccess_.../tomtenuta`. Only
`logs:StartQuery` and `logs:GetQueryResults` were exercised; `grep -ci "sns|PutMetricData"` over
both captured streams returns **0**.

**Observed `office_floor_evaluated` (real log line, real traffic):**

```json
{"control":"passed","kind":"","query_status":"Complete","records_scanned":13464,
 "records_matched":819,"bytes_scanned":3657761,"estimated_records_skipped":0,
 "log_groups_scanned":1,"offices_evaluated":37,"offices_with_bookings":30,
 "zero_floor_count":3,"rate_floor_count":1,"residual_lines":75,"residual_mails":9,
 "residual_share":0.0916,"residual_share_high":false,"day_n_query_status":"Complete",
 "day_n_records_scanned":605145,"dedup_inert":true,"paged":false,"page_class":"none",
 "dry_run":true}
```

### Parity against the builder's declared window-C figures — cell by cell

| cell | builder (PR #2205) | this probe | match |
|---|---|---|---|
| `recordsScanned` | 13,464 | **13,464** | ✅ |
| `recordsMatched` | 819 | **819** | ✅ |
| `bytesScanned` | 3,657,761 | **3,657,761** | ✅ |
| `offices_evaluated` | 37 | **37** | ✅ |
| `rate_floor` | 1 | **1** | ✅ |
| `zero_floor` | 3 | **3** | ✅ |
| RATE `ccb52f4c` | 99 / 2 / **2.02%** | 99 / 2 / **2.02%** | ✅ |
| ZERO set | `e63bbbe0` · `40f86e73` · `8a9b1a84` | `e63bbbe0` · `40f86e73` · `8a9b1a84` | ✅ |
| ZERO arrivals | 9 · 8 · 6 | **9 · 8 · 6** | ✅ |
| residual | 75 lines / 9 mails / 9.2% | 75 / 9 / **9.16%** | ✅ |
| `dedup_inert` | `True` | `True` | ✅ |
| `estimatedRecordsSkipped` | 0 | **0** | ✅ |
| `logGroupsScanned` | 1 | **1** | ✅ |

**`estimatedRecordsSkipped = 0` and `logGroupsScanned = 1` on both queries: no zero in this
receipt is an unscanned zero.** The 30-day lookback scanned 605,145 records.

**Per-office lines emitted (flat fields, guid8 only):**

```
{"chiropractor_guid":"ccb52f4c","floor_class":"rate","arrivals":99,"bookings":2,
 "booking_rate":0.020202,"lines":262,"mails":70,"day_n":1,"last_booking_age_days":2,"offer_class":"active"}
{"chiropractor_guid":"e63bbbe0","floor_class":"zero","arrivals":9,"bookings":0,
 "booking_rate":0.0,"lines":26,"mails":8,"day_n":7,"last_booking_age_days":null,"offer_class":"unknown"}
{"chiropractor_guid":"8a9b1a84","floor_class":"zero","arrivals":6,"bookings":0,
 "booking_rate":0.0,"lines":15,"mails":3,"day_n":5,"last_booking_age_days":null,"offer_class":"unknown"}
{"chiropractor_guid":"40f86e73","floor_class":"zero","arrivals":8,"bookings":0,
 "booking_rate":0.0,"lines":10,"mails":0,"day_n":4,"last_booking_age_days":null,"offer_class":"inactive"}
```

**Rendered page on live traffic (office-name column struck per the fence):**

```
run     : window=2026-09-11T00:00Z..2026-09-14T00:00Z (3d) | unit=U-3 | offices_evaluated=37
control : PASS | query_status=Complete | records_scanned=13464 | offices_with_bookings=30
snapshot: offer-class snapshot 2026-09-11 (age 3d)

[1] ACTIONABLE  (booked within 30d, OR class=active | activating)
    RATE  ccb52f4c  <name-struck>   arrivals=99  bookings=2  rate=2.02%  last_booking=2d  day_n=1  class=active
[2] EXPECTED SILENCE  (no booking in 30d AND class=inactive | ignored)
    ZERO  40f86e73  <name-struck>   arrivals=8  bookings=0  rate=0.00%  last_booking=none(30d)  day_n=4  class=inactive
[3] CLASS UNKNOWN  (no booking in 30d, class not in the snapshot)
    ZERO  e63bbbe0  <name-struck>   arrivals=9  bookings=0  rate=0.00%  last_booking=none(30d)  day_n=7  class=unknown
    ZERO  8a9b1a84  <name-struck>   arrivals=6  bookings=0  rate=0.00%  last_booking=none(30d)  day_n=5  class=unknown
[4] ATTRIBUTION RESIDUAL (not an office; never suppressed)
    unattributed: lines=75 mails=9 (9.2% of window lines)
```

**The negative side of the production pole is carried by the run itself**: `paged = false`,
`page_class = "none"`, zero SNS calls, zero `PutMetricData` calls. The dry-run path is
**provably unable to reach the page plane** on live data — which is the property that made it
safe to run this probe against production at all.

> **DW-10 confirmed on real traffic, not only on a fixture.** `ccb52f4c` renders
> `last_booking=2d` — it is a genuine **stall** and lands in ACTIONABLE on its *evidence*, and
> would land there even if its class were `inactive`. The E-2 amendment is not hypothetical;
> the live surface exercises it on day one.

---

## §10 Findings

### F-1 — `[TACTICAL | MODERATE]` D8.1's "at most ONE publish per UTC day" has **no in-handler idempotence**

**Probe.** Two sequential `evaluate()` calls at `now = 2026-09-14T11:00Z` against one SNS capture:

```
two hour-11 invocations against one topic -> 2 publishes
subjects: ['[ebi-floor] 1 offices below floor | W=3d | 2026-09-14',
           '[ebi-floor] 1 offices below floor | W=3d | 2026-09-14']
```

**Reading.** The ruled invariant (R-172 / ADR D8.1) is enforced by **three** things, not one:
(a) `schedule_expression = "rate(1 hour)"` (`variables.tf:office_floor_schedule`), (b) the
`hour == 11` handler gate, and (c) `reserved_concurrency = 1` (`office_floor.tf:164-167`,
which the builder added explicitly for "two concurrent runs at the page hour could publish
twice"). (c) closes the **concurrent** case. It does **not** close the **sequential** case: an
EventBridge at-least-once re-delivery, a Lambda retry after a post-publish failure, or a manual
re-invoke inside the hour-11 window each yield a second digest. The handler is state-free by
ruling (R-167 / M3) and therefore cannot deduplicate without reintroducing the store that M3
deliberately refuses.

**Bounded blast radius.** A duplicate is a duplicate *page*, never a wrong *verdict*, and the
topic has **no subscriptions** today (R-168). Severity is bounded by the arming decision.

**Route.** Named for S1.4b (a live double-invoke at the page hour is the post-deploy
observation) and for the incident-commander's arming sitting — this is an input to "what does
the consumer see", not a build defect. Not a blocker for S1.5.

### F-2 — `[STRUCTURAL | MODERATE]` on live traffic today, **3 of 4** firing offices land **outside** ACTIONABLE

§9 measures the real distribution: one ACTIONABLE, one EXPECTED SILENCE, two CLASS UNKNOWN.
This is the ruled E-2 predicate behaving **correctly** — and it is also the shape of the page a
reader will actually receive on day one. The two CLASS UNKNOWN rows are offices absent from the
29-row snapshot. Observation, not defect; recorded so the arming sitting is not surprised by it,
and so the snapshot-coverage question (29 rows against 37 offices evaluated) is on the record.

### F-3 — clean bill on the control's discriminating half

`offices_with_bookings ≥ 5` is genuinely discriminating: P4c passes `records_scanned = 31007`
(far above its floor) and still refuses on four booking-bearing offices. A mis-scoped query that
scanned the right bytes and matched the wrong thing cannot pass this control. This is a POSITIVE
result and is reported as one.

---

## §11 What this PRE-DEPLOY probe **CANNOT** prove — frozen UV-P syntax

Per `structural-verification-receipt` §1 (FROZEN; not modified). Each is S1.4b's or S1.7's, and
each names its discharge artifact.

[UV-P: the captured SNS publish is actually DELIVERED by the AWS SNS service to `aws_sns_topic.office_floor_scratch` and returns a real `MessageId` | METHOD: deferred-to-S1.4b-live-invoke | REASON: the SNS client in this probe is a capture object that records `TopicArn`/`Subject`/`Message` and returns a synthetic MessageId; no AWS resource exists at probe time and none was created. Discharge: a live invoke of the deployed Lambda after S1.5, with the `MessageId` from the real `sns:Publish` response co-emitted alongside the `office_floor_evaluated` line carrying `paged=true`]

[UV-P: the four IAM grants of ADR D4.4 are SUFFICIENT — the deployed execution role can actually perform `logs:StartQuery`, `logs:GetQueryResults`, `sns:Publish` to the scratch topic, and `cloudwatch:PutMetricData` in namespace `Autom8y/EbiOfficeFloor` | METHOD: deferred-to-S1.4b-live-invoke | REASON: this probe ran under an SSO AdministratorAccess principal, not the Lambda's execution role, and its SNS/CloudWatch calls never left the process. An over-broad probe identity cannot falsify an under-scoped role. Discharge: the S1.4b live invoke succeeding end-to-end under the function's own role, plus an `aws iam get-policy-version` read of `aws_iam_policy.office_floor`]

[UV-P: the EventBridge rule created from `schedule_expression = "rate(1 hour)"` actually fires the evaluator, and fires it at most once inside the hour-11 window | METHOD: deferred-to-S1.4b/S1.7-observation | REASON: no EventBridge rule exists pre-deploy; the probe drove `evaluate()` directly and never exercised the trigger. F-1 shows the handler does not deduplicate, so the once-per-day property rests entirely on unobserved delivery semantics. Discharge: `AWS/Lambda Invocations` datapoints over a ≥ 24 h post-deploy window, plus the count of `page_class=digest` lines per UTC day]

[UV-P: the freshness dead-man `autom8-ebi-booking-floor-lambda-freshness` transitions to ALARM when the evaluator stops being invoked, and restores when it resumes | METHOD: deferred-to-S1.7-three-leg-proof | REASON: the alarm is a terraform resource that does not exist pre-deploy; a dead-man is only proven by the firing leg AND the restore leg, and neither is expressible in-process. Discharge: ADR D2.7's three-leg two-sided proof with `aws cloudwatch describe-alarms` state transitions observed on each leg]

[UV-P: the S1.7 success-gap alarm turns red on two consecutive withheld `LastSuccessTimestamp` emissions | METHOD: deferred-to-S1.7-after-the-≥7d-soak | REASON: ADR D2 sequences the success-gap alarm instance AFTER a ≥ 7 d daily-sum soak of the metric, so the alarm does not exist at S1.4a. This probe proves the metric is withheld on every refusal and emitted on every controlled run (§5) — the WIRE is proven; the CONSUMER of the wire is not. Discharge: the soak table plus a deliberate `WINDOW_OVERRIDE` refusal driving the alarm to ALARM]

[UV-P: the terraform `office_floor_page_topic_arn` re-point reaches BOTH consumers (the Lambda env and every `alarm_actions`) with one variable | METHOD: deferred-to-the-arming-word | REASON: R-168 withholds the reader; the variable defaults to `null` and resolves to the scratch topic. This probe proved every publish path in the CODE reads one injected ARN (§12), which is the handler half; the terraform half is asserted by `test_office_floor_terraform_guard.py` and by an `office_floor_page_topic_arn` output, neither of which is a post-apply read. Discharge: E-1's own receipt — an alarm-driven MessageId AND a digest-run MessageId on `platform_alerts`, two-sided against the scratch topic]

[UV-P: a cold-start `lambda_handler` constructs its three boto3 clients and completes both bounded Insights queries inside the 300 s timeout with the configured memory | METHOD: deferred-to-S1.4b-live-invoke | REASON: `lambda_handler` was deliberately NOT executed by this probe — it is the only code path that calls `boto3.client(...)`, and exercising it would have constructed a real SNS client. The 30-day lookback measured 605,145 records scanned in-process (§9); the same read under Lambda's network and memory profile is unmeasured. Discharge: the `Duration`/`MaxMemoryUsed` REPORT line from the S1.4b live invoke]

---

## §12 Fence receipt — every captured publish

13 publishes were captured across all synthetic poles. **Every one** carries the injected
scratch ARN; **none** references `platform_alerts`.

```
publish#01 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 2 offices below floor | W=3d | 2026-09-14
publish#02 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 0 offices below floor | W=3d | 2026-09-14
publish#03 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 1 offices below floor | W=3d | 2026-09-14
publish#04 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 0 offices below floor | W=3d | 2026-09-14
publish#05 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 1 offices below floor | W=3d | 2026-09-14
publish#06 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 0 offices below floor | W=3d | 2026-09-14
publish#07 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 0 offices below floor | W=3d | 2026-09-14
publish#08 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] FLOOR-REFUSED | W=3d | 2026-09-14
publish#09 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] FLOOR-REFUSED | W=3d | 2026-09-14
publish#10 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] FLOOR-REFUSED | W=3d | 2026-09-14
publish#11 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 0 offices below floor | W=3d | 2026-09-14
publish#12 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 1 offices below floor | W=3d | 2026-09-14
publish#13 TopicArn=arn:aws:sns:us-east-1:000000000000:autom8-ebi-office-floor-scratch  Subject=[ebi-floor] 2 offices below floor | W=3d | 2026-09-14
```

| fence assertion | got | want |
|---|---|---|
| all ARNs == injected scratch ARN | `True` | `True` |
| any ARN mentions `platform_alerts` | `False` | `False` |
| AWS resources created | 0 | 0 |
| SNS messages delivered | 0 | 0 |
| CloudWatch metrics written | 0 | 0 |

**Harness exit:** `PROBE_RC=0`, unpiped — every assertion in the harness passed. The harness
exits non-zero on any failure, so `0` is a two-sided receipt of the assertion set, not a silence.

---

## §13 Verdict table

| pole | what it tests | PROBE-LIVE two-sided |
|---|---|---|
| **P1** | ZERO pole fires (arrivals ≥ 5, bookings == 0); silent at 4 | **YES** |
| **P2** | RATE pole fires (< 2.5%); silent at 3.03% and at exactly 2.50% | **YES** |
| **P3** | healthy office at 7.00% listed under neither floor | **YES** |
| **P4** | degraded read → `FLOOR-REFUSED`, named kind, `LastSuccessTimestamp` withheld; emitted on the healthy run | **YES** |
| **P5** | page gate: 0 at hour 10, **1** at hour 11, 0 at hour 12; verdict computed at all three | **YES** (see F-1) |
| **P6** | DW-10 / E-2: class-inactive + 12 d booking → ACTIONABLE; class-inactive + none → EXPECTED SILENCE | **YES** |
| **P7** | production pole reproduces the builder's window-C parity figures, cell for cell | **YES** |
| **P8** | park de-dup on `park_key` counts once; `message_id` returns the false all-clear | **YES** |

**Eight of eight PROBE-LIVE two-sided: YES.** One `[TACTICAL | MODERATE]` finding (F-1) and one
`[STRUCTURAL | MODERATE]` observation (F-2), neither blocking S1.5. Seven UV-P labels carry what
this altitude structurally cannot reach into S1.4b and S1.7.

---

## §14 Provenance

- Probe harness and captured streams: session scratchpad (ephemeral, not committed).
- Probed commit: autom8y `1116e00893f3e3851a80170103bee56652da1148` (PR #2205).
- Predicates: asana `origin/main` `.ledge/decisions/ADR-read-the-name-s1-implementation-2026-09-14.md`
  D1 / D2 / D8 + errata E-1 / E-2 (landed via #451, `fc241566`).
- Both probe worktrees are reaped after this record lands.
- Evidence grade **MODERATE** — single-rite probe, self-capped; STRONG requires the S1.4b
  post-deploy half plus the S1.7 three-leg dead-man proof by a rite-disjoint attester.
