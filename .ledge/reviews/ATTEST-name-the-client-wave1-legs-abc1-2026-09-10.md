# ATTEST — `name-the-client` wave 1, legs (a) / (b) / (c1)

**R3 · RITE-DISJOINT ATTESTATION.** Attester: eunomia / verification-auditor.
Authors under grade: sre · platform-engineer · observability-engineer · dre.
Date: 2026-09-10. Read-only throughout (CloudWatch reads; git reads at explicit refs; no mutation).
**Self-cap: MODERATE** per `self-ref-evidence-grade-rule`. Nothing below is inherited; every leg
was re-derived by this seat's own hands.

---

## VERDICT

| leg | verdict |
|---|---|
| **(a)** live attributed `booking_completed` naming the office | **ATTESTED** |
| **(b)** two-sided — a failure for the same office also names it, with its kind, never blank | **ATTESTED-WITH-FLAG** |
| **(c1)** anti-anecdote — ONE office carrying BOTH poles | **ATTESTED** |
| **(d)** activation refusal, two-sided | **UNBUILT — named, not graded** |

**OVERALL: the three legs (a), (b), (c1) are ATTESTED — (b) with flags — as re-derived against
the bar as AMENDED at asana `origin/main` `83a9ae99`. Clause (d) is UNBUILT. Clause (c2) is BOOKED
OPEN and was not graded. Per the wave's own rule, and per operator ruling R-116 explicitly, a
three-of-four verdict is UNATTESTED AGAINST THE FULL BAR. This attestation closes three legs; it
does NOT close `name-the-client` wave 1.**

> Read this verdict line as written. It says three legs stand up. It does not say the initiative
> is done, and R-116 is the operator's own instruction that it must not be read that way.

---

## ★ SCOPE CORRECTION — a mis-citation in my own dispatch, surfaced before grading

My dispatch instructed me that clause (d) is *"OUT OF SCOPE for this attestation by operator ruling
R-121 (sitting VII)."* **I read the ruling at source. R-121 does not say that.**

Re-derivation — `git`/`cat` at `.ledge/decisions/RATIFICATION-decision-space-sitting-VII-2026-09-10.md`:

- **`:36` R-121 verbatim:** *"**Tonight's threads, ALL FOUR:** the not-enrolled split · the instrument
  census · the record corrections · the independent check."* — R-121 governs which four WORK THREADS
  run overnight. It says nothing about attestation scope or clause (d).
- **`:26` R-116 verbatim:** *"**Clause (d): BUILD THE FOURTH LEG FIRST**, then verify all four. A
  three-of-four verdict is UNATTESTED by the wave's own rule; the operator chose to close that gap
  rather than scope around it."* — displaced? **`YES` — seat recommended scoping to three.**
- **`:34` R-119 verbatim:** *"Clause (d) is NOT built tonight."*
- **`:68` §5 verbatim:** *"**Clause (d)** — blocked on F-2. Foundation exists (`b17a066c`, NOT WIRED,
  no default referent by design)."*

**The correct anchors for "(d) is unbuilt tonight" are R-119 and §5 — not R-121.** And R-116 is the
operator explicitly REFUSING the three-leg scoping that a seat had recommended. This is the arc's
own dominant defect class — *the right object answering a different question* — appearing in the
dispatch that commissioned this attestation.

**Disposition.** The (d)-unbuilt FACT is well-receipted and I re-verified it independently (below),
so I grade the three legs as instructed. But I will not issue a verdict line that reads as
operator-sanctioned three-leg closure, because the operator ruled the opposite. The overall verdict
above is worded accordingly. **`:63-64` §4 is binding on me and I quote it:** *"neither this seat nor
any peer declares a clause closed. R3 attests; R2 has now fired (R-113), so the attester grades
against the current bar."*

---

## PRE-FLIGHT — fences discharged own-hands

**STALE-TREE.** Both trees were on non-main branches, as warned. Re-resolved by `git ls-remote`:

```
$ git ls-remote origin main            # autom8y-asana
83a9ae99b47439c6b65339d75c355fe6d6fdf467	refs/heads/main      rc=0
  (checkout was on sre/ws-smoke-activation-hook)
$ git ls-remote origin main            # autom8y
99078f5307085b9e4fa490bc8b023e5e86164235	refs/heads/main      rc=0
  (checkout was on fix/wss-wildcard-scope-bypass-closure)
```
All source below is read via `git show <ref>:<path>` at those two SHAs. The bar was read at
`83a9ae99` — the amended ref, as instructed.

**WRONG-OBJECT / orphan log group.** Re-derived, unpiped rc:

```
$ aws lambda get-function --function-name autom8-email-booking-intake-ebi
ResourceNotFoundException: Function not found: ...:function:autom8-email-booking-intake-ebi
UNPIPED rc=254
$ aws logs describe-log-groups --log-group-name-prefix /aws/lambda/autom8-email-booking-intake
/aws/lambda/autom8-email-booking-intake-ebi	0	90        <-- 0 stored bytes
/aws/lambda/autom8-email-booking-intake	80565209	90    <-- the real object
```
Confirmed orphan. **Every query below runs against `/aws/lambda/autom8-email-booking-intake`.**

**PIPE-MASKED rc.** Caught myself once: `aws lambda get-function ... | tail -3` reported `rc=0`
(tail's rc). Re-measured unpiped → `rc=254`. The 254 above is the unpiped measurement.

**critic-never-author.** I authored none of the code, commits, rulings or artifacts under grade.
No prior `name-the-client` attestation exists in `.ledge/reviews/`. No conflict.

---

## LEG (a) — ATTESTED

**Bar (`83a9ae99`, telos `user_visible_evidence`):** *"A LIVE attributed booking line on the plane
NAMING the office it belongs to — resolved to a client identity, not an 8-hex prefix, and readable
without a cross-service trace join."*

**Query** (CloudWatch Logs Insights, log group `/aws/lambda/autom8-email-booking-intake`):
```
fields @timestamp, @message | filter @message like /booking_completed/ | sort @timestamp asc | limit 50
```
**Window:** 2026-09-09T00:00:00Z → 2026-09-10T12:00:00Z. **`QUERY_STATUS=Complete`, rc=0.**
**Matched 34 records / scanned 1,498.**

**In-query control:** the same query returned both the ABSENT class (26 lines) and the NAMED class
(8 lines) in one result set — the negative pole proves the extraction is not blind, the positive
pole proves the field exists. The zero is TAKEN.

**Raw line quoted verbatim — claimed timestamp #1:**
```json
{"office_name": "Shift Family Chiropractic", "chiropractor_guid": "21b09c5c-***",
 "office_identity_kind": "resolved", "status": "scheduled", "appointment_id": "18250755",
 "idempotency_key": "ebi-4d0bd6f3d17e6e7f", "event": "booking_completed", "service": "unknown",
 "level": "info", "trace_id": "b794d95e…", "span_id": "f5ed8e5322b515aa",
 "timestamp": "2026-09-09T22:12:29.271714Z"}
```
**Raw line quoted verbatim — claimed timestamp #2:**
```json
{"office_name": "Active 4 Life Chiropractic", "chiropractor_guid": "087d7de5-***",
 "office_identity_kind": "resolved", "status": "scheduled", "appointment_id": "18250925",
 "idempotency_key": "ebi-8b4bef77290ed771", "event": "booking_completed", "service": "unknown",
 "level": "info", "trace_id": "07d39550…", "span_id": "67c879ae92820a2e",
 "timestamp": "2026-09-10T00:55:19.465324Z"}
```

**THE FIELD THAT DISCHARGES (a) IS `office_name`, NOT THE GUID.** I was directed to cite the right
field and I confirm the direction is correct: `chiropractor_guid` is `"21b09c5c-***"` and
`"087d7de5-***"` — precisely the redacted 8-hex prefix the telos objects to. That field discharges
NOTHING. What discharges (a) is `"office_name": "Shift Family Chiropractic"` / `"Active 4 Life
Chiropractic"` — a human client identity, present on the line itself, requiring no join to read.

**Cutover observed (all 34 lines, in one query):**

| booking_completed | office_name | count |
|---|---|---|
| 2026-09-09 01:33 → 19:03 (26 lines) | `<ABSENT>` | 26 |
| 2026-09-09 22:12 → 2026-09-10 02:32 (8 lines) | named, `kind=resolved` | 8 |

**Attribution corrected.** (a) was NOT cured by #2125. `git log -S office_log_fields` at
`99078f5307085b9e4fa490bc8b023e5e86164235` shows the success-line cure is **#2073 (`571e80d8`,
2026-09-09 20:56:00Z, "feat(ebi): name the clinic on booking success lines")** — merge-base-verified
ancestor of `origin/main` (rc=0). The 22:12:29Z first-named line follows that merge, ~76 min later.
#2125 cured the FAILURE lines and lands at 00:13Z (leg b). Two distinct deploys, two distinct legs.

**PROBE LIVE:** ✅ — the ABSENT→NAMED transition is itself the two-sided live probe, on the real
instrument, on real traffic. **SUBJECT LIVE:** ✅ — 1,437 `booking_completed` over 90 days
(measured below), 8 named post-cure in the graded window.

**Verdict (a): ATTESTED.**

---

## LEG (b) — ATTESTED-WITH-FLAG

**Bar:** *"a FAILURE for the SAME office also names it, carrying its kind, never blank."*

### (b)(i) SUBJECT LIVE — the gate that #2105 fails

**Query:**
```
filter event in ["business_lookup_failed","business_not_found","booking_gate_declined",
                 "terminal_decline","booking_completed"]
| stats count(*) as n by event | sort n desc
```
**Window:** 2026-06-12T00:00:00Z → 2026-09-10T12:00:00Z (90d, = retention). **`Complete`, rc=0.**

```
  business_lookup_failed             0   <-- #2105's SUBJECT
  business_not_found                 0   <-- #2105's SUBJECT
  terminal_decline                6527   (in-query control, FIRING)
  booking_gate_declined           2306   (in-query control, FIRING)
  booking_completed               1437   (in-query control, FIRING)
```

**This is the discriminating measurement, and it is one query.** The two zeros are TAKEN, not
untaken: the identical `count(*) by event` expression, same log group, same window, returns 6,527 /
2,306 / 1,437 for three sibling events. The instrument is demonstrably not blind. **#2105 —
five tests, three mutants RED-then-GREEN — cured two events that have not fired once in ninety
days. It would FAIL this attestation on the SUBJECT-LIVE half, exactly as I was directed to grade.**
The authoring seat reached the same conclusion independently and said so in `aa92926`'s own message,
which I quote from the commit at `origin/main`: *"#2105 is a correct cure on an unreachable branch:
this initiative's own built-and-unconsumed class, committed inside the cure for it."*

`booking_gate_declined` by contrast: **2,306 / 90d**. 7-day re-measure (2026-09-03T12:00Z →
2026-09-10T12:00Z): **`booking_gate_declined` 269, `booking_attempt` 470, `booking_completed` 134.**
The claim of "≈282/7d" is not exact against my window; **I report my own figure, 269.** Same order,
window-dependent, not a falsification.

**"100% post-`booking_attempt`" — re-derived, not inherited:**
```
| stats sum(event="booking_gate_declined") as declines, sum(event="booking_attempt") as attempts by trace_id
| filter declines > 0
| stats count(*) as traces_with_decline, sum(attempts > 0) as had_attempt, sum(attempts = 0) as no_attempt
```
Window 7d. **`Complete`, rc=0.** → `traces_with_decline 269 · had_attempt 269 · no_attempt 0`.
**CONFIRMED at 100%**, with `had_attempt=269` serving as the firing control against `no_attempt=0`.

### (b)(ii) The deploy-boundary cutover — claim 3

**Query:** `filter event = "booking_gate_declined" | sort @timestamp asc`, window
2026-09-09T20:00:00Z → 2026-09-10T12:00:00Z. **`Complete`, rc=0.** 23 lines.

```
2026-09-09 20:27:02.548  <ABSENT>     ...  17 consecutive blank lines ...
2026-09-10 00:05:52.787  <ABSENT>                       <-- LAST BLANK
2026-09-10 00:13:28.057  Network Wellness Center        resolved   <-- FIRST NAMED
2026-09-10 00:30:58.401  Optimal Health Chiropractic    resolved
2026-09-10 00:50:10.159  Optimal Health Chiropractic    resolved
2026-09-10 01:10:29.113  Axis Spine and Sport           resolved
2026-09-10 02:53:22.581  PostureWorks San Francisco...  resolved
2026-09-10 03:03:58.560  Wellness Chiropractic Dr. ...  resolved
NAMED: 6   ABSENT: 17
```
**Claim 3 CONFIRMED exactly:** named on every line after 00:13Z, none before 00:06Z.

**Deploy correlation, own-hands:**
```
$ aws lambda get-function --function-name autom8-email-booking-intake --query Code.ImageUri
<acct>.dkr.ecr.us-east-1.amazonaws.com/autom8y/email-booking-intake:aa92926   rc=0
$ aws lambda get-function-configuration ... --query [LastModified,PackageType]
2026-09-10T00:04:23.000+0000	Image                                                rc=0
$ git log -1 aa92926   # autom8y
aa92926e91d93b7a4c5f64a689afc2700a64e047  2026-09-09 19:56:11 -0400
fix(ebi): name the office on the failure lines that actually fire (#2125)
$ git merge-base --is-ancestor aa92926 99078f53...  → rc=0
```
Image tag `aa92926` **CONFIRMED** and is an ancestor of `origin/main`.

### (b)(iii) The strongest evidence — a 28,091-line natural experiment

I attempted to FALSIFY the cutover by looking for any named failure line before it.

**Query:** `filter event in [booking_gate_declined, terminal_decline, terminal_decline_parked,
stage_exception] | stats count(*) as n, sum(ispresent(office_name)) as named by event`,
window 2026-08-11T00:00:00Z → 2026-09-10T00:13:00Z. **`Complete`, rc=0.**

```
stage_exception               20572       0
terminal_decline               3779       0
terminal_decline_parked        2433       0
booking_gate_declined          1307       0
TOTAL                         28091       0
```

That is a large zero, so I re-took it in a form where **the control fires inside the same query** —
hourly bins spanning the deploy, one query, window 2026-09-09T18:00Z → 2026-09-10T06:00Z:

```
hour (UTC)                lines   named
2026-09-09 18:00            47       0
2026-09-09 19:00            47       0
2026-09-09 20:00            45       0
2026-09-09 21:00            21       0
2026-09-09 22:00            38       0
2026-09-09 23:00            40       0
2026-09-10 00:00            24      16     <-- deploy hour, mixed
2026-09-10 01:00            10      10
2026-09-10 02:00            12      12
2026-09-10 03:00            11      11
2026-09-10 04:00             6       6
```
**`Complete`, rc=0.** Six consecutive hours at exactly zero, then 100% named in every hour after,
from a single `sum(ispresent(office_name))` expression that demonstrably returns non-zero. **The
zero is TAKEN.** This is the cleanest form of the two-sided proof available: the pre-deploy corpus
is the negative pole on the real instrument at production volume.

### (b)(iv) "NEVER BLANK" graded LITERALLY

Directed to fail a present-but-empty field. **Query:** all four failure events, window
2026-09-10T00:15:00Z → 12:00:00Z, 51 lines. **`Complete`, rc=0.**

| event | n | missing `office_name` key | **blank** `office_name` | missing kind key | **blank** kind |
|---|---|---|---|---|---|
| `booking_gate_declined` | 5 | 0 | **0** | 0 | **0** |
| `stage_exception` | 23 | 0 | **0** | 0 | **0** |
| `terminal_decline` | 15 | 0 | **0** | 0 | **0** |
| `terminal_decline_parked` | 8 | 0 | **0** | 0 | **0** |

**51/51 lines: key present, value non-empty, kind present and non-empty.** Kinds observed live:
`resolved` ×44, `absent` ×7.

I inspected the `absent` class, since that is where "never blank" is actually tested:
```json
{"event": "terminal_decline", "office_name": "Unknown",
 "chiropractor_guid": "***", "office_identity_kind": "absent"}
```
`office_name` is the sentinel string `"Unknown"` with `kind="absent"` — a **positive claim of
absence**, not a blank subject. Structurally guaranteed at
`services/email-booking-intake/src/email_booking_intake/office_identity.py:134` (read at
`99078f53`), verbatim:
```python
return {
    "office_name": ctx.office_name or OFFICE_NAME_UNKNOWN,
    "chiropractor_guid": redact_uuid(ctx.chiropractor_guid),
    "office_identity_kind": office_identity_kind_of(ctx),
}
```
Totality is real: exactly three keys on every call, `or` sentinel, never `None`, never `""`.
**"Never blank" is satisfied literally.** Code-verbatim match at the `booking_gate_declined` emit
site (`pipeline/stages/book_appointment.py:183`, read at `99078f53`) confirms `**office_log_fields(ctx)`
is present in the deployed source.

### (b) FLAGS

**FLAG-b1 — no direct probe on the `booking_gate_declined` office fields.** The 13 new tests in
`services/email-booking-intake/tests/test_office_attribution_on_firing_failures.py` (read at
`99078f53`; 9 test functions + a 5-way parametrization; **19 assertions; 0 skip/xfail evasions**)
exercise `terminal_decline`, `terminal_decline_parked` and `stage_exception`. `booking_gate_declined`
appears in that file **exactly once — at line 15, inside the module docstring.** The totality arm
`test_no_context_state_can_blank_a_failure_line` drives `_park(...)` and asserts only over
`("terminal_decline", "terminal_decline_parked")`. The pre-existing
`test_gate_decline_log_line_is_loud_and_pii_clean` (`tests/test_book_appointment.py:1018`) does
exercise the emission but asserts only `stage`, `gate_code`, `office_phone_hash` and PII —
**it would remain GREEN if the clause-(b) cure were reverted at that site.** So for the specific
instrument carrying claims 3 and 4, the unit-probe is INDIRECT (a property argument via a different
emit site), not a synthetic-violation probe. The authors state this reliance explicitly and I regard
the argument as sound — but it is an argument, not a probe. **Mitigation is strong and empirical:**
the 28,091-line pre-deploy zero against 100%-named post-deploy is a live two-sided probe on the real
instrument, which I weight above a unit test. Hence ATTESTED-WITH-FLAG rather than UNATTESTED.

**FLAG-b2 — (b) is NOT universal across failure kinds.** Open-vocabulary sweep of all
`warning|error|critical` events post-deploy (00:15Z→12:00Z), **`Complete`, rc=0**:

| event | n | named | status |
|---|---|---|---|
| `stage_exception` | 23 | 23 | ALL NAMED |
| `booking_gate_declined` | 5 | 5 | ALL NAMED |
| `ad_lead_gate_refused` | 7 | 0 | **ALL BLANK** |
| `booking_intake_fault` | 15 | 0 | **ALL BLANK** |
| `autom8y_sms_unavailable` | 38 | 0 | all blank (infra, not office-scoped) |
| `core_sdk_warning` | 15 | 0 | all blank (SDK, not office-scoped) |
| `logging_already_configured` | 6 | 0 | all blank (infra) |
| `contente_two_writer_overlap` | 1 | 0 | all blank |

`ad_lead_gate_refused` and `booking_intake_fault` are **office-scoped failure classes that still do
not name the office.** #2125 declares this exclusion deliberately and gives its reason (signature
change on functions with exactly-once contracts). It is honest and reasoned — but it is a live gap,
and (b) holds for the four cured classes, not for every failure a client can suffer.

**FLAG-b3 — 7 of 51 post-deploy failure lines name no client.** The `absent`/`"Unknown"` class
(13.7%) is conformant to the bar as written (non-blank, kind carried) and is good design. It is not
a violation. But an operator reading those 7 lines still cannot tell which client was affected.

**Verdict (b): ATTESTED-WITH-FLAG.**

---

## LEG (c1) — ATTESTED

**Bar (as AMENDED — R-78 split + RATIF-VI-D1):** *"CLOSES AT ONE OFFICE carrying BOTH poles."*
I graded against ONE, per RATIF-VI-D1. **I did not grade against R-79's superseded `>=2`.**

**Query:** `filter @message like /07d39550…/`, window 2026-09-10T00:50:00Z →
01:05:00Z. **`Complete`, rc=0.** 38 lines in the trace.

**Positive pole, verbatim** (`+0.465324s`) — quoted in full under leg (a) above.
**Negative pole, verbatim** (`+0.513049s`):
```json
{"class": "ad_lead_gate_refused", "park_kind": "ops", "stage": "book_contente",
 "reason_code": "p4_null_source", "appt_dt": "2026-09-10 16:00:00",
 "office_name": "Active 4 Life Chiropractic", "chiropractor_guid": "087d7de5-***",
 "office_identity_kind": "resolved", "event": "terminal_decline", "service": "unknown",
 "level": "info", "trace_id": "07d39550…",
 "span_id": "67c879ae92820a2e", "timestamp": "2026-09-10T00:55:19.513049Z"}
```
**Claim 2 CONFIRMED in every particular:** same office, same single trace
`07d39550…`; `class=ad_lead_gate_refused`; `office_identity_kind=resolved`
on both poles; both non-blank. **Delta re-computed from the raw sub-second stamps:
`19.513049 − 19.465324 = 0.047725 s` = 47.7 ms — the "48ms" claim is accurate.**

**The bar is met with margin — three ways.** I did not stop at the single claimed pair.

*Margin 1 — the same office carries the pair three times.* Query `filter @message like /087d7de5/`,
window 2026-09-09T22:00Z → 2026-09-10T12:00Z, **`Complete`, rc=0**, 9 pole-bearing lines:

| ts | event | trace | office_name | kind |
|---|---|---|---|---|
| 2026-09-09 23:55:36.005 | `booking_completed` | `b27b6cda…` | Active 4 Life Chiropractic | resolved |
| 2026-09-09 23:55:36.068 | `terminal_decline` | `b27b6cda…` | **`<ABSENT>`** | **`<ABSENT>`** |
| 2026-09-10 00:55:19.465 | `booking_completed` | `07d39550…` | Active 4 Life Chiropractic | resolved |
| 2026-09-10 00:55:19.513 | `terminal_decline` | `07d39550…` | Active 4 Life Chiropractic | resolved |
| 2026-09-10 02:32:24.416 | `booking_completed` | `d8f372fb…` | Active 4 Life Chiropractic | resolved |
| 2026-09-10 02:32:24.481 | `terminal_decline` | `d8f372fb…` | Active 4 Life Chiropractic | resolved |

The 23:55 trace is a **pre-cure control on the same office and the same event** — blank before the
deploy, named after. The pair reproduces post-cure at 00:55 AND 02:32.

*Margin 2 — three distinct offices carry both poles*, not one. Query over all named pole-bearing
lines, window 2026-09-09T22:00Z → 2026-09-10T12:00Z, **`Complete`, rc=0**; 12 distinct named
offices; `Unknown` excluded from the office set by construction:

| office | positive | negative | negative kinds |
|---|---|---|---|
| Active 4 Life Chiropractic | 3 | 2 | `terminal_decline` |
| Chiropractic Wellness Center | 3 | 3 | `terminal_decline` |
| Back On Track Chiropractic | 1 | 6 | `stage_exception`, `terminal_decline`, `terminal_decline_parked` |

**(c1) needs one office. Three carry both poles.** For the record and as a bonus only: this would
also have satisfied the superseded R-79 `>=2` bar. **That is noted, not graded** — R-79 was dropped
by RATIF-VI-D1 and I did not hold it as a gate.

**FLAG-c1 — the same-trace pairing is narrower than it may read.** In the claimed trace both poles
sit in ONE email's pipeline, and the negative pole fires 48 ms AFTER a *successful* booking
(`status=scheduled`, `appointment_id=18250925`): it is a downstream `book_contente` ops park, not a
booking that failed. The bar as written asks for one office carrying both poles and does not require
them to be independent events, so this satisfies it. But "a booking succeeded and a downstream write
parked" is a weaker thing than "this client had a booking arrive and another booking fail." Margin 1
and Margin 2 above are what carry this leg past that objection — particularly Back On Track
Chiropractic (1 positive, 6 negatives across three distinct failure kinds).

**Verdict (c1): ATTESTED.**

---

## LEG (d) — UNBUILT. NAMED, NOT GRADED.

Re-derived own-hands rather than inherited:

```
$ git merge-base --is-ancestor b17a066c 83a9ae99...   → rc=1   (NOT on asana origin/main)
$ git log -1 b17a066c
b17a066c7ffb43d91e6d3b7d3a52fec1e6c92003  2026-09-08 22:18:40 -0400
feat(lifecycle): referent-injected activation smoke (NOT WIRED)
 src/autom8_asana/lifecycle/activation_smoke.py | 906 +++++++++
 tests/unit/lifecycle/test_activation_smoke.py  | 695 +++++++++
$ git grep -n activation_smoke HEAD -- 'src/*'   (excluding its own file)
   (no output — ZERO callers)
$ git grep -c activation_smoke HEAD -- 'src/*'
HEAD:src/autom8_asana/lifecycle/activation_smoke.py:4     (self-references only)
```

**1,601 lines of implementation and tests, zero production callers, and not merged to `main`.**
Clause (d) is UNBUILT in the only sense that matters to the bar: no account activation is refused
by anything, because nothing calls it. Consistent with sitting VII `:68`: *"Foundation exists
(`b17a066c`, NOT WIRED, no default referent by design)."*

This is the wave's own **built-and-unconsumed** class, sitting inside the wave. I name it; per
R-119 I do not grade it.

---

## FLAGS — consolidated

| # | flag | severity |
|---|---|---|
| **F-1** | **Dispatch mis-cites R-121 as scoping (d) out.** R-121 governs overnight work threads. **R-116 is the operator DISPLACING a seat's recommendation to scope to three**, ruling "BUILD THE FOURTH LEG FIRST… the operator chose to close that gap rather than scope around it." Correct anchors for (d)-unbuilt are R-119 + §5. | **HIGH — governance** |
| **F-2** | **The governing ruling is UNCOMMITTED.** `RATIFICATION-decision-space-sitting-VII-2026-09-10.md` exists on disk but `git show 83a9ae99:…` → *"exists on disk, but not in 83a9ae99"*. The document scoping tonight's authority is not in the repo of record. | **MEDIUM** |
| **F-3** | No direct synthetic-violation probe on `booking_gate_declined`'s office fields; the pre-existing test stays GREEN if that site's cure is reverted. Mitigated by the 28,091-line live natural experiment. | MEDIUM |
| **F-4** | `ad_lead_gate_refused` (7 in window) and `booking_intake_fault` (15 in window) are office-scoped failures that remain ALL BLANK. Deliberate and reasoned in #2125, but (b) is not universal. | MEDIUM |
| **F-5** | 7/51 post-deploy failure lines carry `office_name="Unknown"` (`kind=absent`). Bar-conformant; still names no client. | LOW |
| **F-6** | **A commit whose subject reads `[DO NOT MERGE — R-35 PARKED] fix(intake): clause (b) on the FAILURE pole (#2105)` (`002316ca`) IS an ancestor of autom8y `origin/main`** (`--is-ancestor` rc=0) and is inside the deployed image. Its effect is inert (its two events fire 0/90d), so I found no live harm — but a DO-NOT-MERGE-labelled commit on main is a merge-discipline signal outside my three legs. | MEDIUM — referred |
| **F-7** | Claimed `≈282/7d` for `booking_gate_declined`; I measured **269** in my stated window. Same order, window-dependent. Not a falsification; recorded so the number of record is mine, not inherited. | LOW |
| **F-8** | One blank `booking_gate_declined` at 00:05:52.787Z lands **89 s AFTER** the lambda's `LastModified` 00:04:23Z — consistent with a warm-container tail. The boundary is clean but not instantaneous at the deploy stamp. | LOW |

---

## WHAT I DID NOT VERIFY

Stated plainly, because an attestation that hides its edges is not one.

1. **I did not EXECUTE any test.** The read-only fence binds me and both checkouts sit on
   non-ancestor branches, so running the suite would have exercised the wrong tree. **I CITED the
   tests at explicit ref `99078f5307085b9e4fa490bc8b023e5e86164235` and READ them** — counting test
   functions, assertions (19) and skip/xfail evasions (0), and reading the totality arm in full.
   The "10 RED with the source reverted / 13 GREEN with the cure" two-sidedness is the **authors'
   claim, which I did NOT re-derive.** My confidence in leg (b) rests on the live CloudWatch
   natural experiment, not on that claim.
2. **Clause (c2) — COVERAGE over a ruled population — NOT GRADED.** Booked open. I measured 12
   distinct named offices in a 14-hour window; that is an observation, not a denominator, and I make
   no coverage claim whatsoever.
3. **Clause (d) — NOT GRADED.** Named unbuilt only.
4. **I did not verify that any `office_name` is CORRECT.** I verified the field is present,
   non-empty, kind-carrying, and resolved via the data service (`guid_extracted` →
   `guid_resolved_via_data_service` → `office_resolved`). I did **not** confirm that
   `087d7de5-***` genuinely IS "Active 4 Life Chiropractic", nor cross-check any name against the
   account model, Asana section membership, or the C-3 denominator. **A confidently-rendered wrong
   name would pass every check I ran.**
5. **I did not verify completeness of the plane.** I measured lines that EXIST. An office whose
   bookings produce no line at all — the parent `name-the-zero` class — is invisible to every query
   above. Absence of a blank line is not presence of a client.
6. **I did not audit the six-office dark class, WS-JOIN, WS-DENOM, WS-CONTAIN, WS-DARK or WS-CARGO.**
   Out of scope for legs (a)/(b)/(c1).
7. **I did not verify the deploy chain end-to-end** — only that image tag `aa92926` is on the
   function, that `LastModified` is 00:04:23Z, and that the commit is an ancestor of `origin/main`.
   I did not inspect the dispatch workflow run or the ECR push event.
8. **I did not verify PII posture** beyond observing `chiropractor_guid` is redacted to `8-hex-***`
   and that `office_name` is a business name. Whether business names on the plane are compatible with
   the `office_phone`-DROPPED ruling is a question for the PII custodian, not this seat.
9. **I did not re-derive `stage_exception` coverage at 76%** or the other histogram figures quoted in
   `aa92926`'s message. I re-derived only what my three legs required.
10. **F-6 is REFERRED, NOT ADJUDICATED.** I established the ancestry fact and the inertness of its
    effect. I did not investigate whether the merge was later ratified.

---

## EVIDENCE GRADE

**MODERATE (self-capped).** Grounds for MODERATE rather than higher: every live measurement is
first-hand, in-query-controlled, and the (b) natural experiment is unusually strong (28,091 lines
at zero against 100% post-deploy, single-query bins). Grounds against STRONG: I did not execute the
test suite (item 1); I cannot confirm name CORRECTNESS (item 4); the observation window for the
post-cure state is ~14 hours; and this is a single attester on a single plane. Per
`self-ref-evidence-grade-rule` and the arc's own standing cap, **MODERATE is the ceiling and I do
not exceed it.**

---

## CLOSING

Three legs stand up, one with flags. The instrument that carries leg (b) is genuinely live —
2,306 firings in ninety days — and the wave earned that by measuring first and curing second, which
is exactly what #2105 did not do. The seat that wrote `aa92926` caught its own built-and-unconsumed
defect and said so in the commit message; that is the discipline working.

What I will not do is let the verdict read larger than it is. **Clause (d) is unbuilt, clause (c2)
is open, and R-116 is the operator's own word that three-of-four does not close this wave.** The
mis-citation at F-1 would have converted an honest partial into an apparent closure, and it was the
arc's own dominant failure class — the right document answering a different question — pointed at
the attestation itself.

**Three legs: ATTESTED / ATTESTED-WITH-FLAG / ATTESTED. `name-the-client` wave 1: NOT CLOSED.**

— eunomia / verification-auditor, 2026-09-10. Rite-disjoint. Inherited nothing.
