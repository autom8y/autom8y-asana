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
window_declared: 2026-09-08T00:00:00Z .. 2026-09-15T00:00:00Z (epoch 1788825600 .. 1789430400)
window_effective: 2026-09-09T22:12:29.271Z .. 2026-09-14T05:33:33.175Z — the kind-horizon (§1.2). Kind-filtered counts are horizon-bounded; `***`-filtered counts are NOT, which is where the 11 pre-horizon lines enter (§1.2, §4.2)
errata: E-1..E-5 applied 2026-09-14 after rite-disjoint refusal (asana #455 review, qa-adversary)
refs_read:
  - autom8y-asana origin/main @ 2ef49ff60e55
  - autom8y       origin/main @ 21d439515fb4
fences: guid8 only · no phone digits · no raw client names · no raw malformed values (first-4 + length) · account id rendered `<ACCOUNT>` · rc unpiped · no reads under other worktrees
---

# TRIAGE — S-4 malformed-GUID residual · `read-the-name` wave 1 (R-158 tail)

**Line one — the totals.** Over 2026-09-08..09-14 the `office_identity_kind=absent` residual is
**145 lines in 4 classes**, and **three of the four classes are not malformed GUIDs at all**. The
malformed-GUID class proper is **19 traces / 57 lines** carrying **3 distinct malformed values**.
The `>10 %` `***` tripwire ruled at ADR D5.3 **DOES see S-4 — and cannot tell it apart from
anything else in the bucket**: its numerator is `count(*)` over ALL office-bearing `***` lines, so it
captures **136 of the 145 lines (93.8 %)**. What it cannot do is *discriminate*: **88 of those 136
(64.7 %) are the webhook-body class, not a GUID defect at all.** **Every class has NO WATCHER on the
alarm plane** — the metric filters exist and emit; no alarm subscribes to any of them.

> **ERRATUM E-1..E-5 (2026-09-14, post-review) — the refusal is ACCEPTED IN FULL.**
> The first revision asserted the opposite — *"the tripwire sees 16 of 145 (11 %)"* — on the premise
> that `NON_TERMINAL_OFFICE_EVENTS` (`query.py:87-93`) excludes `stage_exception` and
> `terminal_decline_parked` from the tripwire. **That premise is false.** The constant is **dead
> code**: referenced only at its own definition and at `tests/test_office_floor.py:52,219`, never
> interpolated into `PINNED_QUERY`. The share is `floors.py:140-141` `self.lines / self.window_lines`,
> fed from `u1_lines` (`count(*)`) at `:210-213`; `PINNED_QUERY` (`query.py:104`) has exactly one
> filter, `ispresent(office_guid)`. ADR D5.3 says it verbatim — *"exceeds 10 % of window **lines**"*,
> *"127/1,129 = 11.2 % over window B"*. **This was a measurement defect in the triage, not a
> definitional defect in the record**, and §4.3's charge that D5.3 was "quantitatively wrong"
> inverted the real polarity. Raised rite-disjoint (asana #455 review, qa-adversary; authored none
> of this triage) and re-verified at source by this seat before acceptance. §0, §2.2, §3.1, §4 and
> §7 are re-derived below. **The corrected finding is stronger for the record and weaker for this
> seat: the instrument is not blind, it is undiscriminating.**

---

## §0 THE CLASS TABLE

All counts over the declared window. `traces` = distinct pipeline runs (each malformed-GUID trace
emits exactly 3 lines: `stage_exception` + `terminal_decline` + `terminal_decline_parked`).
Raw values are masked to **first-4 + length** per the fence; never reproduced whole.

| # | value-shape | count (traces / lines) | first seen (UTC) | last seen (UTC) | producer (file:line @ autom8y origin/main) | recoverable-by | watcher |
|---|---|---|---|---|---|---|---|
| **S4-A** | `<8cd5..len=27>` — a UUID **missing its first hex group**: 4-4-4-12 where 8-4-4-4-12 is required. Renders `chiropractor_guid=***` | **13 / 39** | 2026-09-10 01:45:33.381 | 2026-09-14 02:43:41.994 | `services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py:191-195` (`TerminalDecline("malformed_business_guid", ParkKind.OPS)`) | envelope-to fallback — **BUILT** at `resolve_office.py:137` + `:149-155`, **structurally cannot fire**; the cure needs BOTH gates (§3.1, E-3) | **NO WATCHER** |
| **S4-B** | `<e5a6..len=12>` — 12 hex, no dashes. Renders `chiropractor_guid=e5a68603-***` (see §2.2) | **3 / 9** | 2026-09-11 07:51:20.021 | 2026-09-12 23:50:02.716 | same (`resolve_office.py:191-195`) | same as S4-A | **NO WATCHER** |
| **S4-C** | `<1..len=1>` — one character. Renders `chiropractor_guid=***` | **3 / 9** | 2026-09-11 10:25:41.917 | 2026-09-12 13:04:12.545 | same (`resolve_office.py:191-195`) | envelope-to only; **nothing on the line** recovers a 1-char key | **NO WATCHER** |
| **S4-D** | **not a GUID defect.** `WebhookValidationError: Missing body field: at least one of html, text required` — the `parse` stage dies before `resolve_office` ever runs, so no GUID is ever extracted. Renders `chiropractor_guid=***` | **~56 / 88** (56 `stage_exception` + 32 `booking_intake_fault`) | 2026-09-10 02:10:35.644 | 2026-09-11 17:21:29.097 | `parse` stage (`stage=parse`), surfaced via the orchestrator boundary; loss line via `intake_loss_count.py:225` | `office_log_fields_absent(guid)` — **BUILT** at `office_identity.py:134-149`, **called with a guid** at `ad_lead_gate/observe.py:163`, **not wired** on the parse-exception path | **NO WATCHER** |
| | **TOTAL** | **145 lines** | 2026-09-10 01:45:33 | 2026-09-14 02:43:42 | | | |

**Arithmetic closes:** 39 + 9 + 9 + 88 = **145** = the measured `office_identity_kind="absent"`
total (Q2, `recordsMatched=145`). S4-A + S4-C render `***` (13+3 = 16 traces × 3 = 48 lines);
S4-B renders a guid8 (3 × 3 = 9). 48 + 9 + 88 = 145.

**Only 3 distinct malformed values exist in the window** — S4-A/B/C are each a single repeated
value, not a population of distinct malformed keys.

**The watcher column, precisely (E-1).** `NO WATCHER` means **no CloudWatch alarm subscribes** (§5,
measured on `describe-alarms`). It does **not** mean unmeasured: S4-A, S4-C and S4-D all land in the
D5.3 residual-share numerator (§4); **S4-B does not** — it is attributed to the phantom office
(§2.2). And the residual-share line is a **page line on a daily digest, not an alarm**: it cannot
page, and it cannot say which class moved.

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

**The `office_identity_kind` field did not exist in the log plane before 2026-09-09T22:12:29.271Z.**
The effective kind-bearing window is **≈4.31 days** (to `2026-09-14T05:33:33.175Z`), not 7. Every
rate in this document must be read against that denominator. The 52,402 field-absent lines are
overwhelmingly (a) pre-horizon and (b) non-office-bearing lines (the field is only splatted on
office-bearing emissions).

**Declared window vs measured horizon — the reconciliation (E-5).** Kind-filtered counts (the 145)
are horizon-bounded by construction. `***`-filtered counts are **not**: the 147 of §4.1 spans the
full declared window and therefore admits an 11-line pre-horizon tail
(`2026-09-08T01:26:46.320Z .. 2026-09-09T23:07:07.393Z`, §4.2). A rite-disjoint re-measurement bounded
at the horizon (`2026-09-09T22:12:00Z .. 2026-09-14T06:14:03Z`) returns **138** `***` lines; the
**9**-line delta from 147 is exactly the part of that tail falling before the horizon start.
**Two distinct nines appear in this document and must not be conflated:** this one (pre-horizon
tail, §1.2) and the 9 `e5a68603` lines outside the tripwire numerator (§4.2). They are different
lines.

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
> S-1 page would print a **guid-prefix-only row** (`e5a68603 —`, D5.4 last bullet) for a client that
> does not exist. The rendering is not a crash — D5.4 handled that — but the row is a **category
> error of the same kind D5.3 removed for `***`**, arriving by a different door.
>
> **The admitting mechanism, named (E-4).** `guid8_of` (`office_floor/floors.py:170-183`) is
> `raw.split("-", 1)[0]` with **no validation** — it special-cases only `***` (`:181-182`). So
> `redact_uuid` prefix-promotes the 12-hex dashless local-part to `e5a68603-***` (`redact.py:68`),
> `guid8_of` splits it to `e5a68603`, and the fold inserts it into the offices dict
> **indistinguishably from a real office**.
>
> **What this does NOT do — correction.** The first revision claimed *"it will fire the zero floor."*
> **That is false.** `ZERO_FLOOR_MIN_ARRIVALS = 5` (`floors.py:37`) against `WINDOW_DAYS = 3`
> (`query.py:61`), and the phantom carries **3** arrival-bearing lines across the whole ~4.3 d
> kind-horizon (its other 6 lines are `stage_exception` + `terminal_decline_parked`, which are
> `t_line = 0` and so do not feed `arrivals`). `arrivals ≤ 3 < 5`: **it cannot reach a zero-floor
> page at today's rates**, and D5.4 hedges the same way (*"likely to fall below A = 5 on their own
> arithmetic"*). The phantom is a **printed-row** category error, not a **paging** one — and it is
> latent, not dormant: `guid8_of` admits the key unconditionally, so any malformed value that reaches
> A = 5 prints.
>
> **The two surfaces disagree.** `e5a68603` is **NOT a row in `SNAPSHOT-offer-class-2026-09-11.json`**
> at asana `origin/main` — the literal does not appear in the file. It is invisible to the snapshot
> and admissible to the page.

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

**But there are TWO gates, not one (E-3).** `:137` must itself return an address, and
`_first_contenteapp_envelope_address` has its own three-part predicate (`:90-94`): the envelope entry
must split on `@`, be on the contenteapp domain, **and** carry a non-empty local part
(`:93` `and parts[0].strip()`). So a precedence flip at `:138` is **necessary but not sufficient** —
if `:137` already returned `None` (no envelope entry, or none on the contenteapp domain), the flip
recovers nothing. **Whether the envelope held an intact GUID on these 19 traces is UNMEASURED** —
see §6 UV-P 1, which is the item that decides whether the cure is worth 19 traces or 0.

| mechanism | BUILT? | cite (autom8y `origin/main`) | what it would take |
|---|---|---|---|
| envelope-to fallback | **BUILT** | `resolve_office.py:137`, `:149-155` | a precedence flip at `:138` is **necessary but NOT sufficient** — `:137` carries its own gate (`:90-94`, incl. `:93` non-empty local part). **UNBUILT, and its yield is UNPROVEN** (§6 UV-P 1). |
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

## §4 DOES THE `***` TRIPWIRE MEASURE S-4? — **YES, AND IT CANNOT DISCRIMINATE**

*Re-derived 2026-09-14 per E-1/E-2. The first revision answered "NO" on a false premise; the
measurements below are unchanged, only their interpretation is corrected.*

### 4.1 What the tripwire actually counts

`office_floor/query.py:104` — `PINNED_QUERY` has **exactly one filter**:

```
| filter ispresent(office_guid)
```

There is no event filter. The six event names appear only inside a **projection**,
`if(event = ... , 1, 0) as t_line` (`:105`), which is summed into `terminal_lines` and feeds
`residual.arrivals` / `residual.bookings` (`floors.py:215-216`). The **share** is a different
quantity:

```python
# floors.py:140-141
@property
def share(self) -> float:
    return (self.lines / self.window_lines) if self.window_lines else 0.0
```

`lines` is fed at `floors.py:210-213` from `u1_lines`, which is `stats count(*)` (`query.py:113`).
`is_high` (`:143-145`) compares it to `RESIDUAL_SHARE_TRIPWIRE = 0.10` (`:53`).

**So the numerator is every office-bearing `***` line, of any event.** ADR D5.3 says so verbatim —
*"exceeds 10 % of window **lines**"*, and its own worked figures (`144/1,725`, `127/1,129`,
`15/402`) are line counts. The record was right; the first revision of this triage was not.

**`NON_TERMINAL_OFFICE_EVENTS` (`query.py:87-93`) rules nothing at runtime.** `git grep` over
`services/` returns three hits: the definition, and `tests/test_office_floor.py:52` (import) and
`:219` (assertion). It is never interpolated into `PINNED_QUERY`. The same holds for
`TERMINAL_OUTCOME_EVENTS` (`:67`). **A tests-only constant shaped like a production filter, sitting
where a production filter would be, is what cost this triage its first thesis** — see §7-4.

### 4.2 The measurement (Q5, Q6) — unchanged, re-interpreted

```
--query-string 'fields coalesce(chiropractor_guid, office.chiropractor_guid) as g,
                       coalesce(office_identity_kind, office.office_identity_kind) as k
 | filter g = "***" | ... | stats count() as n, sum(t_line) as t by k, event | sort n desc'
```
`queryId=226c8551-1147-43c1-b739-c506206b23a8` · **`recordsMatched=147 recordsScanned=53814`**

| `k` | event | n | `t_line` | **in the tripwire numerator?** |
|---|---|---|---|---|
| `absent` | `stage_exception` | 72 | 0 | **YES** |
| `absent` | `booking_intake_fault` | 32 | 32 | **YES** |
| `absent` | `terminal_decline_parked` | 16 | 0 | **YES** |
| `absent` | `terminal_decline` | 16 | 16 | **YES** |
| *(no kind — pre-horizon)* | `terminal_decline` | 11 | 11 | YES (outside the kind window, §1.2) |

The `t_line` column governs `arrivals`, **not** `share`. Every row is in the numerator.

The flat-field query (Q5) returned the identical `recordsMatched=147` on `recordsScanned=30358` —
no `***` line reaches the plane only in nested form.

| population | lines | note |
|---|---|---|
| **S-4 residual** (`office_identity_kind = "absent"`) | **145** | 4 classes, §0 |
| **S-4 lines IN the tripwire numerator** | **136** | **93.8 %** |
| **S-4 lines OUT of it** | **9** | the `e5a68603` lines — missed by the **phantom** mechanism (§2.2), not by any event exclusion |
| `***` bucket, declared window | **147** | 136 kinded + an 11-line pre-horizon tail (§1.2) |

The 11 kind-less lines are **not a separate class**: Q8 resolves them to
`event=terminal_decline · class=malformed_business_guid · stage=resolve_office`, spanning
`2026-09-08 01:26:46.320` → `2026-09-09 23:07:07.393` — **the same S-4 class emitted by the
pre-instrument code version**, tailing ~55 min past the `22:12:29Z` horizon as warm execution
environments recycled. (`recordsMatched=11 recordsScanned=30358`.)

### 4.3 The corrected ruling

> **The tripwire sees S-4. It cannot tell S-4 apart from anything else in the bucket.**
>
> - It captures **136 of 145** S-4 lines — **93.8 %**. The first revision's *"16 of 145 (11 %)"*
>   is **withdrawn**, and with it the claim that *"S4-A could triple and the tripwire would not
>   move"*: every `stage_exception` and `terminal_decline_parked` line lands in the numerator, so
>   S4-A tripling **would** move it.
> - **What survives, and is the real gap: the numerator is undifferentiated.** Of the 136 S-4 lines
>   it counts, **88 (64.7 %) are S4-D — the webhook-body class, not a GUID defect at all**; 39 are
>   S4-A, 9 are S4-C. If the share crosses 10 %, the page says *"office attribution is degrading"*
>   and **nothing about which of four unrelated defects moved**. It is a share-of-lines degradation
>   signal, correctly built for that job — it is **not**, and was never claimed by the record to be,
>   a per-class S-4 watcher.
> - **S4-B is the one class genuinely outside it** — and for a reason worse than an exclusion: its 9
>   lines are attributed to a **phantom office** (§2.2), so they are counted as a *client's* lines
>   rather than as residual.
> - **ADR D5.3's parenthetical** — *"it is the same class as the R-158 tail's 54/202 `kind=absent`
>   residual"* — is **correct**. The first revision called it "quantitatively wrong"; that charge is
>   **withdrawn**.
> - **The ADR's own UV-P (§11) is discharged for this window.** On its stated axis — guid absent at
>   the line vs guid present but unresolvable — the split is **0 / 147**: every one of the 147 is a
>   line where `redact_uuid` received a value and refused it, never a line where no value existed.
>   Composition: 72 `stage_exception` + 32 `booking_intake_fault` + 16 `terminal_decline_parked` +
>   16 `terminal_decline` + 11 pre-horizon.

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

1. **The tripwire is not blind; it is undiscriminating.** It sees 93.8 % of S-4 (§4.3). The live
   question is therefore *not* "does it measure S-4" but **"is a share-of-lines degradation signal
   the right instrument for a per-class defect?"** — 64.7 % of what it counts is a different defect
   class, so a firing page names no class. That must be re-asked against 93.8 %, never against the
   withdrawn 11 % figure.
2. **`e5a68603` must not be printed as an office** on the S-1 page (§2.2). ADR D5.4 currently rules
   that it is one. That is a ruling to revisit, not a bug to fix.
3. **The `absent` kind should split** — "never ran" vs "died before the lookup" are 61 %/39 % of the
   residual and have entirely different remediations (§2.2). That is a vocabulary amendment to
   `office_identity.py:53-70`, an author-side decision.

4. **A hygiene defer with an owner, not `NO WATCHER`:** `NON_TERMINAL_OFFICE_EVENTS`
   (`query.py:87-93`) and `TERMINAL_OUTCOME_EVENTS` (`:67`) are **tests-only constants standing
   where a production filter would be**. **Document-or-delete** — owner: the **S1.3 builder seat**.
   *Not* a seat cure to WIRE them: interpolating either into `PINNED_QUERY` would **change the
   tripwire's numerator**, which is a sitting question, not a hygiene one.

For the **Platform Engineer**, if and only if a sitting rules it: §3.1's precedence flip at
`resolve_office.py:138` (**both gates**, E-3) and §3.2's wiring of `office_log_fields_absent(guid)`
on the parse path are both small, both against BUILT primitives, and both need a two-sided fixture
before they land. §3.1 must not be scheduled before §6 UV-P 1 is taken — it decides whether the flip
recovers 19 traces or 0.
