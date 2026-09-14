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
> **STATUS: CERTIFIED-WITH-CONDITIONS** by **integrity-architect** (dre, borrowed;
> critic-never-author; rite-disjoint), which re-derived the poles with its own independent harness
> at the same commit. All eight poles hold. This revision applies the two conditions binding S1.5 —
> **C-1** (§9: the untaken-zero fence reaches the pinned query only; the lookback's zero is UNTAKEN
> at this altitude) and **C-2** (§9: the zero-SNS proof re-cited structurally, not by a stdout
> grep) — absorbs the two F-1 sharpenings, and carries the three arming-gate conditions **C-3 /
> C-4 / C-5** into §11.1 with owners and refutable triggers. Both S1.5 conditions were corrections
> to this record's **citations**, not to its **findings**; each is verified against the probed
> commit before being applied here.
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

> **Provenance note on the co-occurrence rows (integrity-architect, non-blocking).** The
> `distinct_park_events` rows are the **module's own production path** (`floors.py:263-280`,
> defaulting to `park_key`; the `key=` parameter exists solely so the vacuity is demonstrable). The
> **co-occurrence** rows — 1-vs-0 and 524-vs-0 — are **harness-side arithmetic**; there is no
> co-occurrence symbol in the module. This does not weaken P8, because the module-side cut
> (`parked-line-only`: `park_key → 1`, `message_id → 0`) is itself two-sided on the real code path.
> Recorded so the record cannot be read as though the 524-vs-0 pair came out of production code.

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
`logs:StartQuery` and `logs:GetQueryResults` were exercised.

### C-2 CORRECTION — the "zero SNS / zero PutMetricData" proof, re-cited structurally

> **This paragraph replaces a weak receipt in the record as first filed.** It previously cited
> `grep -ci "sns|PutMetricData"` over the captured streams returning `0`. A grep over stdout proves
> what a process *printed*, never what it *called*. The correction is owed to integrity-architect's
> C-2; the stronger proof was already true and simply was not the one written down.

The dry-run entrypoint passes `sns_client=None` and `cloudwatch_client=None`
(`__main__.py:42-43`), and **three independent structural guards** follow from that:

| # | guard | anchor | consequence |
|---|---|---|---|
| 1 | `if not (sns and topic_arn): return False` | `handler.py:211-215` | `_publish` is unreachable — a `None` client cannot publish |
| 2 | `if cloudwatch_client is not None and not dry_run:` | `handler.py:426` | the success-metric block is never entered |
| 3 | `page_gate = (... hour == page_hour_utc) and not dry_run` | `handler.py:248` | `dry_run=True` forces the gate `False` regardless of the clock |

Guards 1 and 3 are each independently sufficient for the publish; guards 2 and 3 each
independently sufficient for the metric. And `boto3.client(...)` is constructed in exactly **two**
places in the whole module — `__main__.py:41` (**logs only**) and `handler.py:480-482` (the Lambda
entrypoint, deliberately not exercised by this probe). **No SNS client and no CloudWatch client
were ever constructed in this process**, which is a stronger statement than "no call was printed".

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
| `estimatedRecordsSkipped` (pinned query) | 0 | **0** | ✅ |
| `logGroupsScanned` (pinned query) | 1 | **1** | ✅ |

### C-1 CORRECTION — the untaken-zero fence reaches ONE query, not two

> **This paragraph replaces an over-claim in the record as first filed.** It previously read
> "`estimatedRecordsSkipped = 0` and `logGroupsScanned = 1` **on both queries**". That is **not
> derivable from the cited command** and the correction is owed to integrity-architect's C-1.

`estimatedRecordsSkipped = 0` and `logGroupsScanned = 1` hold **on the pinned window query only.**
At the probed head those two fields are sourced from `result` — the pinned query's `QueryResult` —
at `handler.py:259-260`. The day-N lookback emits exactly **three** fields, `day_n_query_status` /
`day_n_records_scanned` / `day_n_bytes_scanned` (`handler.py:392-394`); its
`estimatedRecordsSkipped` and `logGroupsScanned` **never leave `run_query`** and appear in neither
the log line nor the returned `outcome` dict. **The lookback query's statistics were not emitted at
that head**, so this probe could not read them.

**The lookback's zero is therefore UNTAKEN at this altitude.** That is not a cosmetic gap: the day-N
read is exactly what produces `last_booking_age_days = null` for `e63bbbe0`, `8a9b1a84` and
`40f86e73` — the three rows that *constitute* F-2's "3 of 4 outside ACTIONABLE" distribution. A
silently-skipped or wrong-scoped lookback renders `null` ages **indistinguishable** from "genuinely
no booking in 30 d". What this probe *can* say about the lookback is its emitted receipt —
`status = Complete`, `recordsScanned = 605,145`, `bytesScanned ≈ 156 MB` — plus the structural fact
that `daily.complete` gates the fold (`handler.py:345`), so an incomplete read yields empty counters
rather than false ones. That is strong circumstantial evidence the read was real. It is **not** the
untaken-zero fence, and this record no longer claims it is.

The builder's C-1 fix carries the lookback's `estimatedRecordsSkipped` / `logGroupsScanned` onto the
run line; once it lands, the fence reaches both queries and S1.4b can close this at first live
invoke. Until then:

[UV-P: the day-N lookback query's `estimatedRecordsSkipped = 0` and `logGroupsScanned = 1` — i.e. that the `last_booking_age_days = null` ages underpinning F-2 rest on a fully-scanned, correctly-scoped read | METHOD: deferred-to-the-builder-C-1-fix-then-S1.4b | REASON: at probed head `1116e008` those two statistics are emitted for the pinned query only (`handler.py:259-260`); the lookback emits three fields and no skip/scope statistics (`handler.py:392-394`), so they are unreadable from any invocation of this code. Discharge: the builder's C-1 fix landing both fields on the `office_floor_evaluated` line, then read at the S1.4b live invoke]

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

**Two sharpenings absorbed from integrity-architect's §3 — both make the finding harder, not softer:**

1. **The retry path is live in production, not hypothetical.** `_publish` runs at
   `handler.py:379`; `put_metric_data` runs at `handler.py:426`. **Any** exception between them —
   a CloudWatch throttle, a boto timeout on the metric call — fails the invocation *after the page
   is already out*. EventBridge→Lambda is an **asynchronous** invocation, and no
   `maximum_retry_attempts` is set on this function in `terraform/services/email-booking-intake/`,
   so the AWS default of **2 retries** applies. The retry re-runs the whole handler and republishes.
   The critic reproduced this directly (publish succeeds, then `put_metric_data` raises → 2
   publishes, same UTC date).
2. **`reserved_concurrency = 1` is itself a *source* of sequential re-delivery.** It closes the
   concurrent door, which is exactly what the builder documented it for. But an async invoke
   arriving while the single slot is occupied is **throttled**, and Lambda **retries throttled async
   invocations**. The setting that closes the concurrent case widens the sequential one. The record
   as first filed said only that (c) does not close the sequential case; it should also say (c)
   feeds it.

**Bounded blast radius.** A duplicate is a duplicate *page*, never a wrong *verdict* — the two
floors are disjoint by construction (`floors.py:241-247`), so no office is double-classified — and
the topic has **no subscriptions** today (R-168). Severity is bounded by the arming decision.

**Route.** Named for S1.4b (a live double-invoke at the page hour is the post-deploy
observation) and for the incident-commander's arming sitting — this is an input to "what does
the consumer see", not a build defect. **Not a blocker for S1.5.** The remedy is condition **C-3**
in §11.

### F-2 — `[STRUCTURAL | MODERATE]` on live traffic today, **3 of 4** firing offices land **outside** ACTIONABLE

§9 measures the real distribution: one ACTIONABLE, one EXPECTED SILENCE, two CLASS UNKNOWN.
This is the ruled E-2 predicate behaving **correctly** — and it is also the shape of the page a
reader will actually receive on day one. The two CLASS UNKNOWN rows are offices absent from the
29-row snapshot. Observation, not defect.

**Correction to this finding as first filed.** The record said the coverage question was "on the
record". That is not sufficient under `defer-watch-manifest` discipline: a defer with **no owner and
no refutable trigger is a silent drop**. The ADR §12 row-1 watcher is keyed on
`snapshot_age_days > 30`, which is the **staleness** watcher and structurally cannot surface a
**coverage** hole — a snapshot refreshed weekly reads `age_days = 3` forever while 8 offices stay
unclassified. Neither `offices_unclassified` nor `class_unknown_share` exists in `run_fields`
(`handler.py:250-269`). Filed properly as condition **C-4** in §11, with an owner and a trigger.

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

### §11.1 ARMING-GATE CONDITIONS — carried from integrity-architect, with owners

These three bind the **arming word** (the incident-commander's sitting), not S1.5. They are
recorded here rather than in a separate artifact because the arming sitting reads this record as
its evidence base, and a condition filed somewhere else is a condition nobody carries.

**C-3 — idempotence before a consumer is attached.** *Owner: the builder seat, before S1.7.*

The remedy for F-1 is a **UTC-date-keyed skip sourced from the run's own log lookback**: one
bounded probe of the evaluator's own log group since UTC midnight for
`event = "office_floor_evaluated" AND page_class = "digest"`, skipping the publish when the count
is `≥ 1`. The run line is still emitted, `LastSuccessTimestamp` is still emitted, and the verdict is
still computed — the gate withholds the **reader**, never the **measurement**, which is exactly the
property P5 already proves for the hour gate. **This is state-free and R-167 / M3 survives intact**:
it introduces no store, because the log plane the evaluator already reads *is* the state.

> **SNS message-deduplication is REJECTED as the answer, on window.** SNS content/ID deduplication
> holds for **5 minutes** against a **one-day** gate — three orders of magnitude short. It would
> close the tight-retry case and silently leave the late-retry and manual-re-invoke cases open,
> which is worse than the honest gap named today. Admissible only as a second layer, never as C-3's
> discharge.

[UV-P: the evaluator skips a second digest publish within one UTC date | METHOD: deferred-to-the-C-3-build-then-S1.4b-double-invoke | REASON: no idempotence surface exists at probed head `1116e008` — this probe measured 2 publishes from 2 sequential hour-11 invocations, and the critic independently reproduced the production-shaped path (publish succeeds, `put_metric_data` raises, async retry republishes). Discharge: the UTC-date log-lookback skip landing, then a deliberate double-invoke at the page hour showing exactly 1 publish and 2 `office_floor_evaluated` lines]

**C-4 — the snapshot-coverage defer needs a refutable trigger.** *Owner: the S1.3 seat.*

**Trigger, as ruled: "the digest's CLASS UNKNOWN section lists an office with `arrivals ≥ 5`."**
That is refutable on every single run and it makes **the page itself the watcher** — the same
self-surfacing pattern the ADR uses elsewhere — rather than relying on a staleness clock that
cannot see coverage. §9 shows the trigger is **already firing on live traffic today**: `e63bbbe0`
(9 arrivals) and `8a9b1a84` (6 arrivals) both sit in CLASS UNKNOWN above the ZERO floor. The
cheapest mechanism is an `offices_unclassified` / `class_unknown_share` field on the
`office_floor_evaluated` line.

[UV-P: the coverage hole between the 29-row baked snapshot and the 37 offices evaluated is watched by a trigger that can fire | METHOD: deferred-to-the-C-4-build | REASON: the only extant watcher is keyed on `snapshot_age_days > 30` (ADR §12 row 1), which is the staleness watcher and cannot surface coverage; no `offices_unclassified` field exists in `run_fields` at probed head. Discharge: the field landing on the run line plus a named owner for the trigger's first firing — which §9 shows would fire on the very first live run]

**C-5 — do not speak the arming word before the success-gap alarm exists.** *Owner: the
incident-commander's arming sitting.*

The withheld-`LastSuccessTimestamp` → success-gap alarm is the **recovery floor**, and it is
correctly *independent* of the path it protects: it rides the **metric** plane, not the **SNS page**
plane, so it survives the page plane's failure. But by this record's own UV-P it **does not exist
yet** — ADR D2 sequences it after a ≥ 7 d soak, at S1.7.

`RECOVERY-FLOOR-REFUSED` does **not** fire at S1.4a or S1.5, because nothing is activated: R-168
withholds the consumer and the topic has no subscriptions. It **would** fire at the arming word — an
armed instrument whose only failure channel is the page plane has no floor independent of the thing
it protects. Therefore: **sequence the arming word after S1.7**, and key the rollback runbook on the
**deploy phase** (`pre-apply` / `applied-unarmed` / `armed`), **never on the lever name**
`office_floor_page_topic_arn`. That one variable is inert before the alarm exists and
consumer-visible after it — a lever whose meaning **inverts across a deploy boundary** is precisely
the thing a runbook must not key on.

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

**Eight of eight PROBE-LIVE two-sided: YES** — independently re-derived at the same commit by
integrity-architect with its own harness. One `[TACTICAL | MODERATE]` finding (F-1) and one
`[STRUCTURAL | MODERATE]` observation (F-2), neither blocking S1.5.

**Ten UV-P labels** now carry what this altitude structurally cannot reach: the original seven
(live SNS delivery and `MessageId`; IAM sufficiency under the function's own role; the EventBridge
trigger; the dead-man's fire **and** restore legs; the success-gap alarm after the ≥ 7 d soak; the
terraform one-variable re-point; cold-start duration and memory), plus three added under
certification — the lookback query's untaken zero (C-1), the UTC-date idempotence skip (C-3), and
the snapshot-coverage trigger (C-4). C-5 is a sequencing condition on the arming word and carries no
UV-P because it asserts nothing about the mechanism.

### Condition status

| # | condition | binds | owner | status in this revision |
|---|---|---|---|---|
| **C-1** | §9 statistics sentence over-claims "both queries" | **S1.5** | this seat | **APPLIED** — corrected; lookback zero marked UNTAKEN + UV-P |
| **C-2** | "zero SNS / PutMetricData" cited by grep, not structure | **S1.5** | this seat | **APPLIED** — re-cited to `__main__.py:42-43`, `handler.py:211-215/248/426` |
| **C-3** | UTC-date-keyed idempotence skip (SNS dedup rejected on window) | arming gate | **builder seat, before S1.7** | **CARRIED** — §11.1 + UV-P |
| **C-4** | coverage trigger: CLASS UNKNOWN lists an office with `arrivals ≥ 5` | arming gate | **S1.3 seat** | **CARRIED** — §11.1 + UV-P; already firing on live traffic |
| **C-5** | arming word only after S1.7; rollback keys on deploy phase, never the lever name | arming gate | **incident-commander** | **CARRIED** — §11.1 |

---

## §14 Provenance

- Probe harness and captured streams: session scratchpad (ephemeral, not committed).
- Probed commit: autom8y `1116e00893f3e3851a80170103bee56652da1148` (PR #2205).
- Predicates: asana `origin/main` `.ledge/decisions/ADR-read-the-name-s1-implementation-2026-09-14.md`
  D1 / D2 / D8 + errata E-1 / E-2 (landed via #451, `fc241566`).
- Both probe worktrees are reaped after this record lands.
- **Certification:** `CRITIQUE-S1.4a-integrity-architect-2026-09-14` (dre, borrowed;
  critic-never-author; posted on asana PR #452) — **CERTIFIED-WITH-CONDITIONS**, 8/8 poles held
  under independent re-derivation at commit `1116e008`. C-1 and C-2 applied in this revision; C-3,
  C-4 and C-5 carried into §11.1 with owners. The critic built, armed, pushed and merged nothing.
- Evidence grade **MODERATE** — a single rite's probe plus a single rite-disjoint critic, both
  pre-deploy and both self-capped. STRONG requires the S1.4b post-deploy half plus the S1.7
  three-leg dead-man proof.
