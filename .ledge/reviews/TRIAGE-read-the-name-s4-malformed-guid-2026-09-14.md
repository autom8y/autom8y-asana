---
type: review
kind: triage
initiative: read-the-name
status: COMPLETE — read-only triage; arms nothing, changes nothing
node: T1 (charge DAG, after S1.5) — S-4 MALFORMED-GUID TRIAGE
station: observability-engineer (sre, co-seated)
created: 2026-09-14
scope: READ-ONLY. No code, no terraform, no alarms, no arming. One file written.
region: us-east-1
log_group: /aws/lambda/autom8-email-booking-intake
window: 2026-09-08T00:00:00Z .. 2026-09-15T00:00:00Z (epoch 1788825600 .. 1789430400)
refs_read:
  - autom8y-asana origin/main @ 2ef49ff60e55
  - autom8y       origin/main @ 21d439515fb4
fences: guid8 only · no phone digits · no raw client names · no raw malformed values (first-4 + length) · account id rendered `<ACCOUNT>` · rc unpiped · no reads under other worktrees
---

# TRIAGE — S-4 malformed-GUID residual · `read-the-name` wave 1 (R-158 tail)

**Line one — the totals.** Over 2026-09-08..09-14 the `office_identity_kind=absent` residual is
**145 lines in 4 classes**, and **three of the four classes are not malformed GUIDs at all**. The
malformed-GUID class proper is **19 traces / 57 lines** carrying **3 distinct malformed values**.
The `>10 %` `***` tripwire ruled at ADR D5.3 **is NOT measuring S-4**: it sees **16 of the 145
lines (11 %)**, because the S-1 evaluator's pinned query counts only six terminal events and
`stage_exception` + `terminal_decline_parked` are RULED OUT of it
(`office_floor/query.py:87-93`). **Every class has NO WATCHER** — the metric filters exist and emit;
no alarm subscribes to any of them.

---

## §0 THE CLASS TABLE

All counts over the declared window. `traces` = distinct pipeline runs (each malformed-GUID trace
emits exactly 3 lines: `stage_exception` + `terminal_decline` + `terminal_decline_parked`).
Raw values are masked to **first-4 + length** per the fence; never reproduced whole.

| # | value-shape | count (traces / lines) | first seen (UTC) | last seen (UTC) | producer (file:line @ autom8y origin/main) | recoverable-by | watcher |
|---|---|---|---|---|---|---|---|
| **S4-A** | `<8cd5..len=27>` — a UUID **missing its first hex group**: 4-4-4-12 where 8-4-4-4-12 is required. Renders `chiropractor_guid=***` | **13 / 39** | 2026-09-10 01:45:33.381 | 2026-09-14 02:43:41.994 | `services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py:191-195` (`TerminalDecline("malformed_business_guid", ParkKind.OPS)`) | envelope-to fallback — **BUILT** at `resolve_office.py:137` + `:149-155`, **structurally cannot fire** (see §3.1) | **NO WATCHER** |
| **S4-B** | `<e5a6..len=12>` — 12 hex, no dashes. Renders `chiropractor_guid=e5a68603-***` (see §2.2) | **3 / 9** | 2026-09-11 07:51:20.021 | 2026-09-12 23:50:02.716 | same (`resolve_office.py:191-195`) | same as S4-A | **NO WATCHER** |
| **S4-C** | `<1..len=1>` — one character. Renders `chiropractor_guid=***` | **3 / 9** | 2026-09-11 10:25:41.917 | 2026-09-12 13:04:12.545 | same (`resolve_office.py:191-195`) | envelope-to only; **nothing on the line** recovers a 1-char key | **NO WATCHER** |
| **S4-D** | **not a GUID defect.** `WebhookValidationError: Missing body field: at least one of html, text required` — the `parse` stage dies before `resolve_office` ever runs, so no GUID is ever extracted. Renders `chiropractor_guid=***` | **~56 / 88** (56 `stage_exception` + 32 `booking_intake_fault`) | 2026-09-10 02:10:35.644 | 2026-09-11 17:21:29.097 | `parse` stage (`stage=parse`), surfaced via the orchestrator boundary; loss line via `intake_loss_count.py:225` | `office_log_fields_absent(guid)` — **BUILT** at `office_identity.py:134-149`, **called with a guid** at `ad_lead_gate/observe.py:163`, **not wired** on the parse-exception path | **NO WATCHER** |
| | **TOTAL** | **145 lines** | 2026-09-10 01:45:33 | 2026-09-14 02:43:42 | | | |

**Arithmetic closes:** 39 + 9 + 9 + 88 = **145** = the measured `office_identity_kind="absent"`
total (Q2, `recordsMatched=145`). S4-A + S4-C render `***` (13+3 = 16 traces × 3 = 48 lines);
S4-B renders a guid8 (3 × 3 = 9). 48 + 9 + 88 = 145.

**Only 3 distinct malformed values exist in the window** — S4-A/B/C are each a single repeated
value, not a population of distinct malformed keys.

---

## §1 THE RE-MEASUREMENT, WITH ITS CONTROL

### 1.1 Live vocabulary discovery (Q1)

```
aws logs start-query --region us-east-1 \
  --log-group-name /aws/lambda/autom8-email-booking-intake \
  --start-time 1788825600 --end-time 1789430400 \
  --query-string 'fields @timestamp | stats count() as n by office_identity_kind | sort n desc'
```
`queryId=2f18fdc2-19de-4357-bee9-d1493d5f2895` · `status=Complete` ·
**`recordsMatched=53814 recordsScanned=53814`** · rows=3

| `office_identity_kind` | n |
|---|---|
| *(field not present on the line)* | 52,402 |
| `resolved` | 1,267 |
| `absent` | **145** |

**The live vocabulary is 2 of the 5 declared kinds.** `not_found`, `lookup_failed` and
`unrecognized` are **measured zeros** over the window — on a query that scanned every one of the
53,814 records in the group. `unrecognized=0` is the good news: no stage is writing a value outside
the closed vocabulary (`office_identity.py:96-101`).

### 1.2 The instrument horizon — the window is NOT 7 days (Q7)

```
--query-string 'fields @timestamp | filter ispresent(office_identity_kind)
                | stats count() as n, min(@timestamp) as kind_first_seen, max(@timestamp) as kind_last_seen'
```
`recordsScanned=53814` · `n=1412` · **`kind_first_seen=2026-09-09 22:12:29.271`** ·
`kind_last_seen=2026-09-14 05:33:33.175`

**The `office_identity_kind` field did not exist in the log plane before 2026-09-09T22:12:29Z.**
The effective kind-bearing window is **≈4.31 days**, not 7. Every rate in this document must be
read against that denominator. The 52,402 field-absent lines are overwhelmingly (a) pre-horizon and
(b) non-office-bearing lines (the field is only splatted on office-bearing emissions).

### 1.3 The residual (Q2) and its POSITIVE CONTROL (Q3) — identical query shape

Residual:
```
--query-string 'fields @timestamp | filter office_identity_kind = "absent"
 | stats count() as n, min(@timestamp) as first_seen, max(@timestamp) as last_seen
   by chiropractor_guid, level, class, event, stage | sort n desc'
```
`queryId=a9a36032-c353-4e28-8222-064c771eb00a` · **`recordsMatched=145 recordsScanned=49370`** · rows=8

Control — **the identical shape**, one literal changed (`"absent"` → `"resolved"`):
```
--query-string 'fields @timestamp | filter office_identity_kind = "resolved"
 | stats count() as n, min(@timestamp) as first_seen, max(@timestamp) as last_seen
   by chiropractor_guid, level, class, event, stage | sort n desc'
```
`queryId=931ca89d-...` (ctrl) · **`recordsMatched=1267 recordsScanned=52671`** · **rows=249**

**§4 two-sided check — DISCHARGED.**

| predicate | measured | verdict |
|---|---|---|
| the control fires | 1,267 matched across **249** groups | **YES** — the shape is not vacuous |
| residual `recordsScanned` comparable to control's | 49,370 vs 52,671 = **93.7 %** | **YES** — same substrate, same scan |
| the residual's zeros are taken, not untaken | `not_found`/`lookup_failed`/`unrecognized` zero on a 53,814-record scan (Q1) | **TAKEN** |

The residual's 8 rows:

| `chiropractor_guid` | level | class | event | stage | n |
|---|---|---|---|---|---|
| `***` | error | | `stage_exception` | `parse` | 56 |
| `***` | warning | | `booking_intake_fault` | | 32 |
| `***` | info | `malformed_business_guid` | `terminal_decline_parked` | | 16 |
| `***` | error | | `stage_exception` | `resolve_office` | 16 |
| `***` | info | `malformed_business_guid` | `terminal_decline` | `resolve_office` | 16 |
| `e5a68603-***` | info | `malformed_business_guid` | `terminal_decline` | `resolve_office` | 3 |
| `e5a68603-***` | error | | `stage_exception` | `resolve_office` | 3 |
| `e5a68603-***` | info | `malformed_business_guid` | `terminal_decline_parked` | | 3 |

### 1.4 The value extraction (Q4)

```
--query-string 'fields @timestamp, error, error_type
 | filter office_identity_kind = "absent" and event = "stage_exception" | limit 300'
```
**`recordsMatched=75 recordsScanned=29010`** · 75 rows returned (no truncation: matched == returned).

| masked value | `error_type` | n |
|---|---|---|
| *(none — body defect)* | `WebhookValidationError` | 56 |
| `<8cd5..len=27>` | `OfficeResolutionError` | 13 |
| `<e5a6..len=12>` | `OfficeResolutionError` | 3 |
| `<1..len=1>` | `OfficeResolutionError` | 3 |

75 = 56 + 19, and 19 = the 16 `***` + 3 `e5a68603-***` `stage_exception`/`resolve_office` rows of
§1.3. **The two reads reconcile exactly.**

---

## §2 THE PRODUCER SIDE — WHAT FEEDS THE GUID, AND WHY THE KIND READS `absent`

### 2.1 The GUID is the inbound mailbox local-part. Not a lead field, not a routing table.

`resolve_office.py:157-166` (autom8y `origin/main` @ `21d439515fb4`):

```python
parts = cleaned.split("@")
...
guid = parts[0].strip()
...
ctx.chiropractor_guid = guid
log.info("guid_extracted", guid=redact_uuid(guid), resolve_source=resolve_source)
```

`cleaned` is the header-`To` (override-applied, zero-width-stripped), or the SendGrid **envelope-to**
under the F-2 fallback (`:149-151`). **So a malformed GUID is a malformed inbound routing address.**
It is not produced by this service; it ARRIVES. S4-A's shape — a UUID with its **first hex group and
dash removed** — is an upstream address-rewrite/truncation signature, not a random corruption.

### 2.2 Why `kind=absent` here is NOT "resolve_office never ran" — and FLAG-B dissolves

The kind is written at **three** sites, all **after** the GUID lookup:
`resolve_office.py:247` (`lookup_failed`), `:272` (`not_found`), `:296` (`resolved`).
The malformed-GUID raise is at **`:191-195`** — **before all three**. So the context keeps its
`__init__` default `absent` (`pipeline/context.py:149`).

> **The `absent` kind is honest but COARSE.** Its docstring says *"`resolve_office` never populated an
> identity on this trace (it did not run, or it halted before the lookup)"* (`office_identity.py:62-66`).
> S-4 is entirely the **second** disjunct. `absent` conflates "the stage never ran" (S4-D, 88 lines)
> with "the stage ran and died at GUID validation" (S4-A/B/C, 57 lines) — a 61 %/39 % split that no
> consumer can currently separate without joining on `class=malformed_business_guid`.

**FLAG-B of the attestation (a guid8 present while the kind reads `absent`) is fully explained and is
NOT a two-field disagreement.** Two independent mechanics:

1. `ctx.chiropractor_guid` is set at `:165`; the kind is not set until `:247+`. A trace that dies at
   `:191` therefore carries **a guid and no kind**. Both fields are correct.
2. `redact_uuid` is a **prefix matcher, not a UUID validator**
   (`utils/redact.py:24` `_UUID_HEX_RE = re.compile(r"[0-9a-fA-F]{8}")`, `:68` `.match(value)` —
   `match`, never `fullmatch`, and no length or dash check). Any string **beginning** with 8 hex
   chars renders as `<8hex>-***`. `<e5a6..len=12>` is 12 hex with no dashes; the data service
   rejected it as not-a-UUID; the log plane still promoted it to a guid8.

> **Consequence — a PHANTOM OFFICE.** `e5a68603` is not an office. It is a malformed 12-char
> local-part that `redact_uuid`'s prefix match dressed as a guid8. ADR-read-the-name-s1 **D5.4**
> evaluates it as one: *"the malformed-guid office `e5a68603` (12 / 9 / 3 lines; fires in A and B)
> [is] evaluated, printed, and class-labelled like every other office."* Under the ruled shape the
> S-1 page will print a **guid-prefix-only row** (`e5a68603 —`, D5.4 last bullet) for a client that
> does not exist, and it will fire the zero floor. The rendering is not a crash — D5.4 handled that —
> but the row is a **category error of the same kind D5.3 removed for `***`**, arriving by a
> different door.

### 2.3 A redaction-posture observation (not a breach, reported for the record)

The raw malformed local-part is echoed **unredacted** into the `error` field, because
`resolve_office.py:192-193` f-strings the data-service exception message:
`f"Data service rejected GUID (validation, HTTP {exc.status_code}): {exc}"`. For S4-A that puts **27
of the 36 characters of a real routing UUID** in plaintext in CloudWatch. DG-SRE-5's bar is *zero
raw UUID* (`utils/redact.py:8-10`); a **truncated** UUID is not a raw UUID, so the gate is not
breached as written — but the `[0-9a-fA-F]{8}` prefix discipline the module exists to enforce is
bypassed on this path. **Reported, not ruled.** This is also, unavoidably, the substrate §3 depends
on: it is the only place the malformed value survives.

---

## §3 RECOVERABLE vs NOT — PER CLASS

### 3.1 S4-A / S4-B / S4-C — the envelope-to fallback is BUILT and cannot fire

`resolve_office.py:136-155` implements the F-2 envelope-to fallback. The gate is:

```python
if _is_contenteapp_routing_address(cleaned):      # :138
    if envelope_address is not None:
        ... log.warning("resolve_source_disagreement", ..., winner="header")   # :143-148
elif envelope_address is not None:                 # :149  <-- the only fallback path
    cleaned = envelope_address
```

and the predicate checks **the domain only**:

```python
def _is_contenteapp_routing_address(cleaned: str) -> bool:   # :74
    parts = cleaned.split("@")
    return len(parts) >= 2 and parts[-1].strip().lower() == _CONTENTEAPP_DOMAIN   # :77-78
```

**The local-part shape is never inspected.** A truncated, 12-hex, or 1-character local-part on the
right domain returns `True`, the header keeps authority (`winner="header"`, `:147`), and the
`elif` at `:149` is unreachable. If the SendGrid envelope carried an intact GUID for these 19 traces,
it was **logged as a disagreement and discarded**.

| mechanism | BUILT? | cite (autom8y `origin/main`) | what it would take |
|---|---|---|---|
| envelope-to fallback | **BUILT** | `resolve_office.py:137`, `:149-155` | a **precedence flip**, not a build: extend `:138` so a header local-part that fails UUID shape yields to the envelope. **UNBUILT.** |
| phone-keyed office lookup | **BUILT** | `resolve_office.py:236` `get_business_by_phone_async` | **unusable here** — the phone is only obtained *after* the GUID resolves (`:207`, `:217`). Nothing on an S-4 line carries a phone. |
| GUID-keyed lookup | **BUILT** | `resolve_office.py:178` `get_business_by_guid_async` | requires a full UUID by construction; it is the thing that rejected these. |
| suffix/prefix match against an office census | **UNBUILT** | census exists (ADR D5.4 names an SSM census; S-1 landed snapshot asana #449, 29 rows) | S4-A is 27 of 36 characters of a real UUID — a suffix match would resolve it to one office with very high confidence. **No such resolver exists.** |
| override mapping | **BUILT** | `resolve_office.py:215-217` (`guid in mapping`) | never reached: the validation raise at `:191` precedes it. |

**Verdict.** S4-A: **recoverable**, by the built envelope path under a precedence change, or by an
unbuilt suffix resolver. S4-B: **recoverable only via the envelope path** (a 12-hex string has no
reliable suffix). S4-C: **not recoverable from the line or the request** except via the envelope —
one character carries no signal.

### 3.2 S4-D — the largest class, and the cleanest fix

88 of the 145 lines (61 %) are the `parse`-stage body defect. **`resolve_office` never ran, so no
GUID was ever extracted — but the inbound address was present in the same webhook payload.** The
failure is *"Missing body field: at least one of html, text required"*: the envelope and headers
arrived; only the body was absent.

The recovery primitive is **already built and already called elsewhere with a guid**:

```python
def office_log_fields_absent(guid: str | None = None) -> dict[str, str]:   # office_identity.py:134
```
called **with** a guid at `ad_lead_gate/observe.py:163`, and **without** one at
`intake_loss_count.py:225` — which is exactly the S4-D loss line.

**Mechanism BUILT (`office_identity.py:134-149`); the wiring on the parse-exception path is UNBUILT.**
Passing the extracted local-part into `office_log_fields_absent(...)` on this path would name the
office on 88 lines without a single new lookup. **No build performed here; this is the triage's
finding, not its action.**

---

## §4 IS THE S-1 EVALUATOR'S `***` BUCKET THE SAME POPULATION? — **NO**

This is the question that decides whether the `>10 %` tripwire measures S-4. It does not.

### 4.1 The evaluator's bucket, measured on its own shape (Q5, Q6)

`office_floor/query.py:98` defines `RESIDUAL_GUID = "***"`, and `:102-104` keys the whole evaluator
on `coalesce(chiropractor_guid, office.chiropractor_guid)`. Measured on **the coalesced form**, so
nested `office.*` emissions (e.g. `book_contente.py:529`) are counted:

```
--query-string 'fields coalesce(chiropractor_guid, office.chiropractor_guid) as g,
                       coalesce(office_identity_kind, office.office_identity_kind) as k
 | filter g = "***"
 | fields if(event = "terminal_decline" or event = "ad_lead_gate_refused" or event = "booking_gate_declined"
          or event = "booking_completed" or event = "contente_booking_booked" or event = "booking_intake_fault", 1, 0) as t_line
 | stats count() as n, sum(t_line) as t by k, event | sort n desc'
```
`queryId=226c8551-1147-43c1-b739-c506206b23a8` · **`recordsMatched=147 recordsScanned=53814`**

| `k` | event | n | **t_line** |
|---|---|---|---|
| `absent` | `stage_exception` | 72 | **0** |
| `absent` | `booking_intake_fault` | 32 | **32** |
| `absent` | `terminal_decline_parked` | 16 | **0** |
| `absent` | `terminal_decline` | 16 | **16** |
| *(no kind)* | `terminal_decline` | 11 | **11** |

The flat-field query (Q5) returned the identical `recordsMatched=147` on `recordsScanned=30358` —
**no `***` line reaches the plane only in nested form.**

### 4.2 The disjunction

`office_floor/query.py:87-93` rules `terminal_decline_parked` and `stage_exception` **out** of the
arrival unit, held explicitly *"so a future reader can see the exclusion was RULED rather than
overlooked."* That ruling is correct for its own purpose and **is the reason the tripwire cannot see
S-4**:

| population | lines | composition |
|---|---|---|
| **S-4 residual** (`office_identity_kind = "absent"`) | **145** | 4 classes, §0 |
| **Evaluator `***` bucket** (`g = "***"`, any event) | **147** | 136 kinded + 11 pre-horizon |
| **Evaluator `***` ∩ t_line** — what the tripwire counts | **59** | 32 `booking_intake_fault` + 16 `terminal_decline` + 11 pre-horizon |
| **∩ with the S-4 malformed-GUID class proper** | **16** | the `terminal_decline` / `malformed_business_guid` lines only |
| **S-4 lines NOT in the evaluator's `***` bucket** | **97** (66.9 %) | 72 `stage_exception` + 16 `terminal_decline_parked` + 9 `e5a68603` — of which **94 are outside the t_line set entirely** and **3** (the `e5a68603` `terminal_decline` lines) are *visible but misattributed to a phantom office*, §2.2 |

The 11 kind-less lines are **not a separate class**: Q8 resolves them to
`event=terminal_decline · class=malformed_business_guid · stage=resolve_office`, spanning
`2026-09-08 01:26:46.320` → `2026-09-09 23:07:07.393` — i.e. **the same S-4 class emitted by the
pre-instrument code version**, tailing ~55 min past the `22:12:29Z` horizon as warm execution
environments recycled. (`recordsMatched=11 recordsScanned=30358`.)

### 4.3 Ruling on the charge's question

> **The `residual_share > 10 %` tripwire is NOT measuring S-4.**
>
> - It counts **16** of the 145 S-4 lines — **11.0 %** of the residual it is imagined to watch.
> - Its largest live component is **32 `booking_intake_fault` lines from S4-D** (the webhook-body
>   class), which is **not a GUID defect at all**.
> - S4-A could **triple** — every `stage_exception` and every `terminal_decline_parked` line — and
>   the tripwire would not move, because those events are RULED OUT at `query.py:87-93`.
> - S4-B does not reach the bucket **at all**: its 9 lines are attributed to the phantom office
>   `e5a68603` (§2.2), not to `***`.
>
> ADR D5.3's parenthetical — *"it is the same class as the R-158 tail's 54/202 `kind=absent`
> residual"* — is **directionally right and quantitatively wrong**. They overlap at one event type
> out of five. **The ADR's own UV-P (§11: "the exact composition of `***` … is not characterised")
> is hereby discharged for this window**: `***` is 72 `stage_exception` + 32 `booking_intake_fault`
> + 16 `terminal_decline_parked` + 16 `terminal_decline` + 11 pre-horizon, and its split on the
> ADR's stated axis is **0 lines guid-absent-at-the-line / 147 lines guid-present-but-not-UUID-shaped**
> — every one of the 147 is a line where `redact_uuid` received a value and refused it, not a line
> where no value existed.

---

## §5 WATCHER STATUS — `NO WATCHER` IS MEASURED, NOT ASSERTED

```
aws logs describe-metric-filters --region us-east-1 \
  --log-group-name /aws/lambda/autom8-email-booking-intake        # rc=0, 34 filters
aws cloudwatch describe-alarms --region us-east-1                 # rc=0, 427 alarms
```
Cross-joining every S-4-relevant filter's `metricTransformations` against the alarm inventory:

| metric filter | metric emitted | alarm subscribes? |
|---|---|---|
| `ebi-terminal-decline-by-class` | `Autom8y/EBI/Semantic/TerminalDecline` | **NO** |
| `ebi-terminal-decline-parked-distinct` | `Autom8y/EBI/Semantic/TerminalDeclineParked` | **NO** |
| `ebi-intake-loss-total` | `Autom8y/EBI/Semantic/IntakeLossTotal` | **NO** |
| `ebi-intake-loss-by-stage` | `Autom8y/EBI/Semantic/IntakeLossByStage` | **NO** |
| `ebi-intake-loss-unknown` | `Autom8y/EBI/Semantic/IntakeLossUnknown` | **NO** |
| `ebi-intake-loss-instrument-failed` | `Autom8y/EBI/Semantic/IntakeLossInstrumentFailed` | **NO** |
| `ebi-park-health` | `Autom8y/EBI/Semantic/ParkFailure` | **YES** (`ebi-park-failure`) |

**Every S-4 class is measured-but-unwatched.** The signal is being extracted into CloudWatch metrics
continuously and **nothing pages, nothing dashboards, nothing reads it**. `ebi-park-failure` fires
only when the *park itself* fails — a successful park of a malformed-GUID decline is, to the alarm
plane, a silent success. This is the built-unconsumed shape at the alarm altitude: the instrument
exists and the consumer does not.

Against the Four Golden Signals for this service, S-4 sits in **Errors**, and it is a
**symptom** (a client's mail is terminally declined and parked) — not a cause. It is the alertable
kind. **No alert is proposed here; T1 arms nothing.**

---

## §6 UNRESOLVED

- `[UV-P: whether the SendGrid envelope-to carried an INTACT GUID on the 19 S4-A/B/C traces | METHOD: query the same traces for event="resolve_source_disagreement" or "envelope_fallback_engaged" and compare the two redacted prefixes | REASON: the disagreement line is only emitted when BOTH header and envelope are contenteapp addresses; absence of the line does not distinguish "no envelope" from "envelope not contenteapp", and resolving it decides whether §3.1's precedence flip recovers 19 traces or 0]`
- `[UV-P: the 56 stage_exception : 32 booking_intake_fault ratio in S4-D | METHOD: join on trace_id and count faults per parse exception | REASON: not 1:1; either the loss instrument under-counts the parse class or the two lines have different trigger conditions, which changes whether the 32 are a subset of the 56 or a distinct population]`
- `[UV-P: whether the S4-A truncated value resolves to exactly one office under a 27-char suffix match against the office census | METHOD: read the SSM census (ADR D5.4) and suffix-match the masked value held in this seat's scratch | REASON: no suffix resolver is built and this triage performs no census read; the recoverability claim in §3.1 is therefore ARGUED from the 27/36-character overlap, not MEASURED]`
- `[UV-P: whether contente_two_writer_overlap lines emitted post-horizon (2026-09-12, 2026-09-13) carry a guid with no office_identity_kind by design | METHOD: read the emitter and check whether it splats office_log_fields | REASON: observed in Q7 but outside S-4's scope (not a failure line, not a t_line); flagged so it is not inherited as noise]`
- **Not taken:** any comparison against the 2026-09-11 single-day figures of the attestation
  (54 / 202). This triage re-measured a 7-day window on the ruled shape rather than replaying one
  day; the 54/202 figure is **not** re-derived here and is neither confirmed nor contradicted.

---

## §7 HANDOFF POSTURE

**Nothing was changed.** No code, no terraform, no alarm, no arming, no merge. One file written.

For the **Incident Commander** / next sitting, three things are decided by this read and none of them
by this seat:

1. **The `>10 %` `***` tripwire needs a second instrument or a re-scope** if S-4 is to be watched —
   it sees 11 % of the residual and its dominant component is a different defect class.
2. **`e5a68603` must not be printed as an office** on the S-1 page (§2.2). ADR D5.4 currently rules
   that it is one. That is a ruling to revisit, not a bug to fix.
3. **The `absent` kind should split** — "never ran" vs "died before the lookup" are 61 %/39 % of the
   residual and have entirely different remediations (§2.2). That is a vocabulary amendment to
   `office_identity.py:53-70`, an author-side decision.

For the **Platform Engineer**, if and only if a sitting rules it: §3.1's precedence flip at
`resolve_office.py:138` and §3.2's wiring of `office_log_fields_absent(guid)` on the parse path are
both small, both against BUILT primitives, and both need a two-sided fixture before they land.
