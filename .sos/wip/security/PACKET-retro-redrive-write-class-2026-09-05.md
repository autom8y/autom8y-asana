---
type: authority-packet
initiative: name-the-zero
wave: 1
parallel_group: PG-0
sprint: S-03
title: "WS-C wall — the write-class authority packet for the RETRO re-drive"
rite: security
seat: security-reviewer
co_seated_with: threat-modeler
annex: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/security/THREAT-retro-redrive-wall-2026-09-05.md
authored_at: 2026-09-05T04:07:11Z
dispatched_on: PT-00 PASS, instant of record 2026-09-05T03:24:39Z
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
code_sha_read:
  autom8y: 52995b267a773f9b91b1c8992bcf8acba543b222   # origin/main, fetched this dispatch
  autom8y-asana: 8f7ed3cb                             # session HEAD (fix/manifest-tombstone-reconciliation)
read_discipline: "object DB only (git show origin/main:<path>); never a working tree (C-10, scar 15)"
evidence_grade: MODERATE
self_assessment_cap: MODERATE
decides: "the authorization DESIGN and the CLASS of the act"
does_not_decide: "F-P4 (what 'landed' means) · F-P5 (EXTEND-TTL) · F-A1 · any operator word"
executes: "nothing. No probe. No code. No word."
---

# PACKET — RETRO re-drive: write-class authority

## Realization predicate (VERBATIM, frame `:52-62`)

> **"Verified-realized"** = (a) a LIVE `name_evidence_outcome` line in which one
> read leg failed WITH its status carried and the surviving leg's candidates were
> scored — distinguishable AT THE PLANE without a cross-service trace join;
> two-sided: a genuinely empty pool with both legs OK still reads `no_candidates`,
> and a both-legs-failed read still reads `read_failed`; AND (b) a dead-lettered
> booking appears in a kind-named loss count (receiver-refused vs intake-fault vs
> TTL-reaped) that a resting-green alarm cannot mask, and ONE past-dated row
> re-driven on an operator word produces a TYPED terminal outcome (landed /
> refused-with-reason / held), never a silent drop. NOT "PRs merged".

## What this packet is, and is not

This packet **designs and classifies** the WS-C re-drive as a write-class
authorization problem, and resolves **F-M6**. It is the document the operator
reads *before* speaking the word.

It **executes nothing**: no probe, no code, no terraform, no ledger write, no
word. Its sole write is this file.

It is authored by a seat that will not build S-08. That separation is the whole
reason S-03 exists: *"a wall designed by the seat that also builds the thing
behind it is asserted, not proven"* (shape §0 D-4, `:86`).

The threat-modeler is authoring the **attack-surface annex** in parallel at the
`annex:` path above. This packet owns the **authorization design**; the annex
owns the enumerated attack surface. They are coordinated by citation, not by
message. Where this packet names a break vector (§1.3), the annex is the place
to look for its exploitation path.

---

# WHAT THE OPERATOR READS BEFORE SPEAKING

**One page. Everything below this section is the proof.**

### 1. The act you are being asked to authorize

A POST that creates a **customer-visible appointment** at `thenewnhc`
(Heroku) — a receiver outside either lane's control (R-15 black box). It is
**call site #3** for that POST. Today there are exactly two:
`book_contente.py:838` (a fresh booking from a live mail) and
`reconcile_handler.py:508` (the sweep re-drive). WS-C adds a third.

### 2. This class is ABOVE the deny-by-default precedent, not inside it

SEC-001 (`54431c18` / #391) answers *"which SERVICE may invoke which Asana write
class?"* and answers it with a **deny-by-default allowlist of standing
principals**. The RETRO re-drive is **not a member of that taxonomy**. Its class
is `outbound:create_appointment:retroactive`, and its defining property is that
**no standing principal — human or machine — may ever be allowlisted for it.**
It sits on R-A4's never-grantable floor: *customer-visible outbound acts*, which
no grant at any tier reaches. Admitting it as a seventh `WriteClass` member would
be exactly the admission-by-analogy R-A3 forbids, because membership in that enum
carries the false property "an allowlist entry can authorize this."

**Consequence you should hold onto:** there is no configuration in which this act
becomes routine. Every instance is a fresh word.

### 3. The precedent is a wall BYPASS, and it already fired

On **2026-09-04T18:21:35Z** the operator's word was executed as a raw
`UpdateItem`: `status dead_letter → failed`, `redrive_attempts → 0`. That flip
put the row **back inside the scheduled sweep's positive selection set**. The
sweep — running every 15 minutes, live in production — claimed it within
seconds, and **five POSTs went out to the receiver on one word** (CARD `:116-117`).

**One word authorized one act and the mechanism delivered five.** That is the
never-grantable class (C-5: *"no automatic re-drive"*) occurring in fact, under a
word that did not contemplate it. It is the single most important thing in this
packet, and it is why the S-08 build **must not re-use the `dead_letter → failed`
re-arm.** The wall is not "get a word first." The wall is "the word moves exactly
one row exactly once, and never hands the row to the sweep."

### 4. What we recommend the wall is (F-M6)

**None of the three enumerated options is safe as written.** The resolution is a
fourth: a **dedicated, unscheduled, trigger-less Lambda function** sharing the
existing image (so the booking client, the secrets and the `run_gate` call are
the SAME symbols — no fork), whose **IAM role holds no `dynamodb:Scan`**.

The strongest property that buys: **a code path that cannot scan cannot enumerate
rows.** ONE-ROW-AT-A-TIME stops being a convention and becomes an IAM fact.

### 5. The four questions this packet does NOT answer, and their weight

| | Question | Why it is yours | What turns on it |
|---|---|---|---|
| **F-P4** | What does `landed` MEAN for a past-dated appointment? | Product policy | **Highest leverage in the packet.** If `landed` means *our* scheduling-performance record (RS-3's own clause names the data plane), then **no POST is needed to pay RS-3** — and the never-grantable act disappears from the design entirely. WS-C would drop from a floor act to a records-wall write. We enumerate; we do not choose (§8). |
| **UV-P-1** | Does `thenewnhc` refuse past-dated appointments, and how? | A probe POST is customer-visible outbound | Determines whether `landed` is even *reachable*. **Cheapest recourse first: ask the receiver's owner. Zero blast radius.** The A/B probe (§7) is the fallback and costs one real appointment. |
| **F-P5** | EXTEND-TTL on `bd875254…`? | A ledger write | The fixture reaps **2026-09-10T05:28:46Z**. S-08 builds synthetic regardless, so no sprint is blocked — but if it reaps, predicate leg (b)'s live half is **WAITING**, and every artifact must say so. |
| **F-M7 (widened)** | Does WS-C's terraform ride WS-B's apply? | Operator-burden change | §6 grows WS-C from code-only to code+terraform. Surfaced, not absorbed (§9 Δ-3). |

### 6. What we found that nobody asked us for

- **Frame D-5's suggested provenance field is already occupied.** `operator_redrive_at` was written onto `bd875254…` by the 2026-09-04 un-walled act. Re-using it as the walled act's one-shot guard would make the live fixture permanently un-retro-drivable *and* would conflate the two acts on the ledger. Use distinct names (§5). This is checkable and it would have bitten S-08.
- **The exclusion is two-layer, not one.** The shape's proof cites one anchor; there are two independent ones (§1.1). Both must be widened for the sweep to reach a dead-lettered row.
- **The sweep handler ignores its event payload entirely** — AST-verified, zero references (§1.2 P-6). That is a live structural fact worth freezing with a guard, because F-M6 option (c) would have been the thing that broke it.

---

# EC-1 — The re-drive path is PROVEN NOT reachable by any sweep, cron, or retry ladder

**Claim.** At `autom8y origin/main 52995b26`, no scheduled, cron, event-driven or
retry-ladder path can cause a `dead_letter` row to be re-POSTed. The proof is
positive-selection by construction at two independent layers, plus an exhaustive
enumeration of the outbound call sites.

## 1.1 — The two independent layers

**Layer 1 — SELECTION.** `scan_redrive_candidates` (`idempotency_ddb.py:501-545`)
filters server-side with a **positive whitelist over `status`**:

```
filter_expression = "#ns = :ns AND (#s = :failed OR (#s = :intent AND #c < :cutoff))"
```
`idempotency_ddb.py:528` (SVR P-3)

`dead_letter` is not in `{failed, intent}`. It is excluded because it is **absent
from an allowlist**, not because it appears on a blocklist. That distinction is
load-bearing and the repo already says so in its own words:

> *"added an exclusion list would be one careless edit away from regression forever"*
> — `reconcile_handler.py:184-185` (SVR P-5)

**Layer 2 — CLAIM.** Even a row that somehow reached the candidate set cannot be
claimed. The claim is a conditional write:

```
if not store.update_status(pk, status="redriving", expect_status=("failed", "intent")):
```
`reconcile_handler.py:420` (SVR P-4)

`expect_status` is again a positive tuple. A `dead_letter` row fails the
`ConditionExpression` and the sweep skips it.

**Both layers must be widened** for the sweep to reach a dead-lettered row. This
is *stronger* than the shape's exit criterion states (which cites the single
anchor `idempotency_ddb.py:660-700`) — see §9 Δ-1 for the anchor correction.

## 1.2 — The complete outbound-POST surface

An exhaustive grep for the booking POST across the EBI source tree at the SHA
returns exactly **two live call sites** (SVR P-15):

| # | Call site | Reached by | Gate between trigger and POST |
|---|---|---|---|
| 1 | `book_contente.py:838` | a live inbound mail (SES/SNS → intake Lambda) | the full pipeline + `run_gate` |
| 2 | `reconcile_handler.py:508` | the EventBridge schedule, `rate(15 minutes)`, `contente_booking_reconcile_enabled = true` in production (SVR P-16) | payload-parseable · guid present · guid allowlisted · conditional claim · `run_gate` at redrive time |

WS-C adds **call site #3**. The reachability question for S-08 is therefore
narrow and answerable: *what, other than an operator invocation, can reach site
#3?* §6's resolution answers **nothing**, and §1.3 says how a builder could
falsify that.

A third status-reading sweep exists — `scan_corroboration_candidates`
(`idempotency_ddb.py:638`, filter `#ns = :ns AND #s IN (:posted, :dead_letter)`,
SVR P-20) — and it **does** select `dead_letter` rows. It is observe-only: it
writes the disjoint `corroboration_status` attribute and reaches no booking POST
(confirmed by P-15's exhaustive call-site enumeration). It is named here so S-08
does not discover it late and mistake it for a reachability hole.

## 1.3 — What a builder could do to BREAK the proof (S-08 must assert each)

Each row is a named break vector with the assertion that falsifies it. These are
the tests S-08 owes; the annex is the place to look for exploitation paths.

| # | Break vector | Why it breaks the wall | Assertion S-08 must carry |
|---|---|---|---|
| **B-1** | The retro path writes `status ∈ {failed, intent}` on any row, or resets `redrive_attempts` | Re-enters Layer 1 → the 15-min sweep claims it → up to `_MAX_REDRIVE_ATTEMPTS = 5` POSTs from ONE word. **This is not hypothetical: it happened on 2026-09-04** (§EC-3.4) | Two-sided: for every terminal the retro path can write, assert the written `status` value ∉ `{failed, intent}`; assert no code path in the retro module writes `redrive_attempts` |
| **B-2** | `scan_redrive_candidates`' filter or the claim's `expect_status` is widened to admit `dead_letter` | Collapses Layer 1 or Layer 2 | Fixture: a `dead_letter` row is absent from `scan_redrive_candidates`' result. Separate fixture: `update_status(..., status="redriving", expect_status=("failed","intent"))` returns `False` on a `dead_letter` row. **Two assertions, not one** — a single test cannot tell which layer regressed |
| **B-3** | Event-dispatch is added to `reconcile_handler.lambda_handler` | Puts the retro path on the function the schedule already invokes every 15 min. One payload-shape bug from a C-5 breach | **AST-structural** guard (never whole-file, never grep): parse `reconcile_handler.py`, locate the `lambda_handler` FunctionDef, assert the count of `ast.Name` nodes with `id == "event"` in its body is `0`. Verified `0` today (SVR P-6) — this is a *regression* guard over a live fact |
| **B-4** | The retro function acquires a trigger: an `aws_cloudwatch_event_target`, an `aws_lambda_permission`, an event-source mapping, or a module whose `schedules_enabled` boolean can be flipped | A boolean you can flip is not a wall | Terraform assertion: zero resources of those types reference the retro function's ARN/name. **Prefer a module that creates no schedule resource at all** over one where a schedule exists and is set `false` — a resource that does not exist cannot be enabled by a one-line tfvars edit |
| **B-5** | `dynamodb:Scan` is granted to the retro role | Restores the ability to enumerate rows → bulk becomes expressible | Assert the retro role's policy `Action` list contains `UpdateItem` and `GetItem` and **does not contain** `Scan`. Contrast the sweep role, which does hold `Scan` (SVR P-17) |
| **B-6** | The retro code path calls any `scan_*` store method | Enumeration in code even if IAM later drifts | **AST-structural**: no `ast.Attribute` node in the retro module's call graph whose `attr` starts with `scan_`. Defence in depth behind B-5 |
| **B-7** | The retro entry accepts a collection for `pk` (list, tuple, comma-string, glob, prefix) | One invocation, N rows | Typed refusal test: a payload whose `pk` is a list/dict/comma-joined string is rejected **before any store read or POST**, with the refusal counted |
| **B-8** | The one-shot guard is dropped, or re-uses `operator_redrive_at` | Replay → a second POST; or the guard fail-closes on the live fixture and a builder deletes it to make a test pass (§9 Δ-2) | Assert the terminal write's `ConditionExpression` contains `attribute_not_exists(retro_redrive_at)`; assert a second identical invocation produces **zero** additional `client.book` calls |

---

# EC-2 — "Absent word → REFUSE" as a TWO-SIDED requirement

Not a comment. Two named, independently-failing tests, each of which must be able
to go RED for its own reason. A one-sided proof (only the refusal, or only the
success) is not a wall — it is half of one.

## 2.1 — Direction A: absent word → NO POST fires

**Specification.** With no invocation carrying a well-formed, unexpired,
single-`pk` payload, the retro path never executes and **zero** POSTs are emitted
to the receiver, for an unbounded number of scheduled cycles, on a row in
`dead_letter`.

**Testable form (S-08).** Seed a synthetic `dead_letter` row in a non-live `ns`.
Drive the ENTIRE automated surface: N ≥ 3 full `reconcile_handler.lambda_handler`
invocations (the sweep, the corroboration pass, all four level observers), with
no retro invocation at any point. Assert:
1. `client.book` call count == **0**;
2. the row is **byte-identical** before and after (status, `redrive_attempts`, and every attribute) — *not merely "still dead_letter"*, because an attribute mutation is the tell that something claimed it;
3. no `retro_redrive_at` attribute exists on the row.

**Its RED (the positive control that earns the green).** The same fixture with
the row's `status` set to `failed` instead of `dead_letter` **must** produce
`client.book` call count ≥ 1. Without this arm, the test passes trivially in a
harness where the booking client was never wired, and a green carries zero
information (frame I-5 / shape §7.2). **This is a two-sided proof, and neither
arm injects a defect into working production code** — the RED arm is a
deliberately-different *input* the live surface correctly acts on (D-9,
discriminating-canary doctrine).

## 2.2 — Direction B: present word → EXACTLY ONE row moves

**Specification.** One well-formed invocation naming `pk` X produces: exactly one
`client.book` call (or zero, for `held`); exactly one conditional `UpdateItem` on
X; a terminal `status ∈ {landed, refused_with_reason, held}` on X; and **zero
writes of any kind to any other pk**.

**Testable form (S-08).** Two-row fixture (X in `dead_letter`, Y in
`dead_letter`). One invocation naming X. Assert:
1. `client.book` called exactly **once**, with X's persisted payload;
2. X's terminal is in the typed set and is **not** `dead_letter`, `failed` or `intent`;
3. **Y is byte-identical before and after** — the discriminator that separates "one row moved" from "the right row moved among others that also moved";
4. X carries `retro_redrive_at` and `retro_word_ref`;
5. a **second, identical** invocation produces **zero** additional `client.book` calls and leaves X's terminal unchanged (replay refusal, B-8).

**Its RED.** An invocation naming a pk that is absent, or in a non-`dead_letter`
status, or past `not_after`, must produce zero `client.book` calls and a typed
refusal — not a silent no-op. *A refusal that is indistinguishable from a
success-with-nothing-to-do is a silent drop wearing a green shirt.*

## 2.3 — Why both directions are one requirement

Direction A alone permits a mechanism that refuses everything, including the
operator. Direction B alone permits the 2026-09-04 outcome exactly: the word
worked, and so did four more POSTs nobody authorized. **The wall is the
conjunction.**

---

# EC-3 — Classification against the SEC-001 write-class taxonomy and the never-grantable floor

## 3.1 — What SEC-001 actually established (read, not summarized)

`54431c18` (#391) landed `src/autom8_asana/api/write_authz.py` and attached a
deny-by-default gate to all 26 declared Asana-write routes. Its structure:

| Property | SEC-001's answer | Anchor |
|---|---|---|
| The question | *"which service may invoke which Asana write class?"* | `write_authz.py:3` |
| The taxonomy | `WriteClass(StrEnum)`, six members, `<domain>:<verb>`: `tasks:write` · `projects:write` · `sections:write` · `intake:write` · `receipts:write` · `workflows:execute` | `write_authz.py:100-108` (SVR P-8) |
| The key | **issuer-asserted principal identity** — strict precedence `service_account_id → client_id → sub` | `write_authz.py:204-256` |
| The predicate | membership in a per-class allowlist; **empty set == deny-all** | `write_authz.py:264-275` (SVR P-9) |
| Refused axis | `has_scope` — permanently, machine-checked, because `scope == "*"` short-circuits `True` | `write_authz.py:21-55` |
| Posture | every resolution fails toward denial; `ENFORCE` is the default and `OBSERVE` requires an exact literal | `write_authz.py:57-68`, `:153-172` |

## 3.2 — The class of the RETRO re-drive, NAMED

> **`outbound:create_appointment:retroactive`**
>
> *A single, past-dated, customer-visible appointment POST to an external
> receiver outside our control, replayed from a terminal ledger row, on a
> per-instance operator word that authorizes exactly one row exactly once.*

Named on its own terms. Derived below; **not admitted by analogy** (R-A3:
*"Novel act-classes are not admitted by analogy: they require a tier amendment or
an explicit named extension in the grant itself"*).

## 3.3 — Why it is DISJOINT FROM, and ABOVE, `WriteClass` — the derivation

Every member of `WriteClass` shares one property: **some standing principal may
be allowlisted for it.** That is what `ALLOWLIST_ENV` *means*. A class is a
member of that taxonomy exactly when a per-class allowlist is a coherent control
for it.

For the RETRO act that property is **false**, and it is false by ruling, not by
preference:

- **R-A4 (never-grantable floor), clause (2): "customer-visible outbound acts."**
  The floor sits *above both tiers*: "ADMIN-GRADE does not approach it, and no
  grant phrasing, however explicit, lifts it" (`RULING-decision-space-amendments-2026-08-26.md:83-88`, SVR P-10).
- **Charter operative core §5(b)** — the sensitive list, *"regardless of
  reversibility"*: "anything a customer sees ... makes an external commitment"
  (`CHARTER:55`, SVR P-11). A booking at a clinic is both.
- **Frame D-7 / C-5**, carried into shape §7 Prescribed item 7: *"no
  customer-visible outbound on autopilot; no automatic or bulk re-drive."*

Therefore **no allowlist entry — no `service_account_id`, no human, no
`ASANA_WRITERS_*`-shaped env var — can ever authorize this class.** Adding it as
a seventh `WriteClass` member would silently confer the property "an allowlist
entry can authorize this," which is the exact false inheritance R-A3 forbids.

**The correct relation, stated:**

```
  R-A4 FLOOR         outbound:create_appointment:retroactive
   (never grantable)  ── authority: a per-INSTANCE operator word, per row
                      ── standing principals: NONE, at any tier
                      ── the machine's whole job here is to REFUSE
  ─────────────────────────────────────────────────────────────────────
  ADMIN-GRADE / USER-GRADE
  SEC-001 WriteClass  tasks:write · projects:write · sections:write
   (deny-by-default)  intake:write · receipts:write · workflows:execute
                      ── authority: a STANDING allowlisted principal
```

**What IS inherited from SEC-001, and it is a lot** — the *shape* of the door,
not the membership:

1. **Deny-by-default, fail-closed on every resolution.** Unset, empty, malformed → refuse. There is deliberately no "allow on error" branch (`write_authz.py:57-68`).
2. **Authorize on identity, never on a self-describing capability field.** SEC-001's CORRECTION-3 refused `has_scope` because `"*"` short-circuits `True`. The RETRO analogue: **never authorize on a flag the payload asserts about itself.** A payload field like `{"operator_confirmed": true}` is precisely `scope == "*"` in a new costume. Authority comes from *who could invoke the function at all* (§6), and from the row's own conditional state — never from the payload's self-description.
3. **`OBSERVE` has no analogue here and must not be built.** SEC-001 could afford a shadow posture because its denied act is an Asana write we own. A shadow posture over a floor act would mean "compute the refusal, then POST anyway." **Refused permanently. If S-08 ships a mode enum for this path, that is a finding.**

## 3.4 — The ONE precedent of an operator-worded row write: it was NOT walled

The CARD records the only prior instance. It is the strongest evidence in this
packet and it points the opposite way from comfort.

**What happened** (CARD `:86-120`):

- **18:21:35Z** — condition-guarded `UpdateItem` on `bd875254…`: `status dead_letter → failed`, `redrive_attempts → 0`, `operator_redrive_at = 1788543695` (SVR P-13). The condition was `attribute_exists(pk) AND status = dead_letter` — a *correctness* guard (right row, right starting state). **It was not an authorization guard**, and it bounded nothing downstream.
- **Seconds later** — read-back showed `status: redriving`. The **scheduled sweep had already claimed the row.** The operator's own manual `lambda invoke` was refused with `ReservedFunctionConcurrentInvocationLimitExceeded` — because the automation had taken the slot first.
- **By 21:00Z** — *"Five fresh sweep re-drives (attempts 1–5 after the operator re-arm at 18:21Z)"* (SVR P-14), each a real POST to the receiver, each `503`.

**What it teaches, in four lines:**

1. **One word produced five customer-visible outbound attempts.** The bound was `_MAX_REDRIVE_ATTEMPTS = 5` (`reconcile_handler.py:119`), a *retry* constant. **The word had no bound of its own.** The act was authorized once and executed five times.
2. **The bypass mechanism was state laundering.** Nothing broke the wall. The wall (`dead_letter` ∉ the positive filters) is real and held. The act simply moved the row *out of the protected state* into an automated one — and the automation was, correctly, automatic.
3. **The correctness guard was mistaken for a wall.** `status = dead_letter` in the condition means "I am acting on the row I think I am." It does not mean "only this act may proceed." **S-08 must not confuse the two**, and the one-shot guard of §5 is specifically the *authorization* condition the 2026-09-04 act lacked.
4. **Therefore the retro path may never route through the sweep.** Not "should not." The 2026-09-04 receipt is the proof that routing through it converts a per-instance word into a ladder. This is B-1, and it is the highest-severity assertion S-08 owes.

*Severity note.* Under the Bug Bar this reads **HIGH**, not Critical: the
exploitation context is an authenticated operator act with no remote or anonymous
path, and the outcome was five refused POSTs rather than five created
appointments — the receiver's persistent 503 is what bounded the blast radius, and
a receiver bound is not a control we own. Had the receiver accepted, the same
word would have created up to five appointments. **We were bounded by luck, and
luck is not in the design.**

---

# EC-4 — ONE ROW AT A TIME is a MECHANISM property

Bulk is not discouraged. It is **not expressible**. Six layers, each
independently checkable, ordered outermost-first.

| # | Layer | The property | How bulk fails here | Checkable by |
|---|---|---|---|---|
| **M-1** | **IAM** | The retro role holds `dynamodb:GetItem` + `dynamodb:UpdateItem` and **NOT `dynamodb:Scan`** | A path that cannot scan **cannot enumerate rows**. It can only act on a pk it was handed. There is no API by which it discovers a second row's key | Reading the role's policy JSON (contrast the sweep role, which does hold `Scan` — SVR P-17) |
| **M-2** | **Signature** | The entry contract is `pk: str`, singular. A list, tuple, dict, comma-joined string, prefix or glob is a **typed refusal before any store read** | There is no plural form to pass | B-7's test |
| **M-3** | **Call graph** | The retro module invokes no `scan_*` store method | Enumeration is absent from the code even if M-1 later drifts | B-6, AST-structural — never whole-file, never grep |
| **M-4** | **Control flow** | The path contains **no loop over rows**: one `get_item`, at most one `client.book`, exactly one conditional `UpdateItem` | There is no iteration construct for a payload to feed | AST: no `For`/`While`/comprehension whose iterable derives from the payload |
| **M-5** | **The row itself** | The terminal write's `ConditionExpression` includes `attribute_not_exists(retro_redrive_at)` | N invocations against one row yield **at most one TERMINAL**. A SERIAL replay is also bounded to one POST (the second invocation's pre-check sees `retro_redrive_at` and refuses before the POST); **N CONCURRENT invocations are NOT** — the condition is evaluated at STAMP time, after the POST. See M-6 | B-8's test |
| **M-6** | **One execution at a time** | `reserved_concurrent_executions = 1` on the retro function (`contente_retro_redrive.tf`) | This is what bounds one word to at most one POST: with a single concurrent execution there is no window for two invocations to race between the pre-check and the stamp. Deleting it, or raising it above 1, re-opens N-POSTs-per-word | `test_retro_redrive_terraform.py::TestReservedConcurrencyIsTheOnePostGuard` |

★ CORRECTION (PT-04 F-01, 2026-09-05). The M-5 row above previously read "N
invocations against one row yield **at most one** POST. Replay is refused **by
the row**". That was wrong, and it is the sentence S-08's module text mirrored.
`attribute_not_exists(retro_redrive_at)` is evaluated at STAMP time, which is
AFTER the POST, so it bounds the TERMINAL and not the POST. N CONCURRENT
invocations of one word each pass the handler's pre-check, each POST, and then
N-1 lose the conditional write and surface as CRITICAL
`terminal_stamp_not_applied` — N customer-visible appointments on one word. The
bound is real but it is held by M-6, not by M-5, and the two are now stated
apart. The layer count moves from five to six; the conjunction claim below is
unchanged.

**Why five and not one.** M-1 is the strongest (it survives every code change) but
is the furthest from the developer and the easiest to widen in a hurry. M-5 is
the weakest per-instance but is the only layer that survives a *correct*
invocation being repeated. **No single layer is the wall; the conjunction is.**

**Note the asymmetry with the sweep.** The sweep is *designed* to be plural: it
scans, it loops, it claims many. That is correct for a sweep. The retro path is
its structural inverse, and the inversion must be visible in the artifacts —
different function, different role, different permissions, different shape. **If
S-08's retro path and the sweep share a role, an IAM policy, or a scan, the
inversion has been lost regardless of what the code says.**

---

# EC-5 — The operator-word token form

## 5.1 — What the operator types

A single AWS CLI invocation of the dedicated retro function (§6), whose payload
**is** the word:

```
aws lambda invoke \
  --function-name autom8-email-booking-intake-contente-retro-redrive \
  --cli-binary-format raw-in-base64-out \
  --payload '{"act":"retro_redrive",
              "pk":"bd875254…",
              "word_ref":".ledge/decisions/CARD-…-2026-09-XX.md#disposition",
              "not_after":<epoch>}' \
  /dev/stdout
```

An `ari` subcommand **may** exist as a typing convenience that constructs exactly
this invocation. If it does, it **adds no authority**: it holds no credential of
its own, mints nothing, and can reach nothing the operator's own AWS session
cannot. Stated explicitly so that the ergonomics answer to F-M6 is not mistaken
for a second authorization path.

## 5.2 — What binds it to ONE pk

The pk is **inside the payload, and the payload is the token.** There is no
separate "token + target" pairing — that shape is what permits one token to
authorize N targets. Binding is enforced by M-1..M-5 (§4) jointly: the singular
signature, the absence of scan, the absence of a loop, and the row's own one-shot
condition.

## 5.3 — How the row records the word's provenance

**One** conditional `UpdateItem` writes the terminal *and* the provenance
together, so a terminal without provenance is not a reachable state:

```
UpdateExpression:  SET #s = :terminal,
                       retro_redrive_at   = :now,
                       retro_word_ref     = :word_ref,
                       retro_terminal_reason = :reason      (when applicable)
ConditionExpression: attribute_exists(pk)
                     AND #s = :dead_letter
                     AND attribute_not_exists(retro_redrive_at)
```

Three conditions, three distinct duties — **do not collapse them**:

- `attribute_exists(pk)` — the row is real. (`update_status` already always carries this so an update can never upsert a row into existence: `idempotency_ddb.py:191-194`.)
- `#s = :dead_letter` — the **correctness** guard. This is the one the 2026-09-04 act had.
- `attribute_not_exists(retro_redrive_at)` — the **authorization** guard, one-shot. This is the one the 2026-09-04 act **lacked**, and it is the difference between a word and a ladder.

**Field naming — a live collision, and the reason for it (§9 Δ-2).** Frame D-5
suggests `operator_redrive_at`. **That attribute already exists on `bd875254…`**,
written at 18:21:35Z by the un-walled re-arm (SVR P-13). Re-using it would (i)
make the live fixture permanently un-retro-drivable, and (ii) conflate a walled
act with an un-walled one on the same ledger field. Use **`retro_redrive_at` /
`retro_word_ref`**, and let `operator_redrive_at` stand as the historical stamp
of the 2026-09-04 re-arm. Keeping them distinct is what lets the ledger tell the
two acts apart forever.

## 5.3-AMENDMENT — the BUILT form, recorded (name-the-zero S-09, 2026-09-05)

> **RECORDED, NOT RULED.** This amendment is appended by the ASSEMBLY seat
> (`principal-engineer`, name-the-zero S-09) discharging PT-02 §2 items A and B
> (BD-4: *carried as EXPLICIT ACTS, not rediscovered as diffs*). The seat records;
> it does not adjudicate a security packet. **Concurrence of record:**
> `.sos/wip/security/CONCURRENCE-retro-terminal-and-dryrun-2026-09-05.md`
> (`security-reviewer`, **CONCUR-WITH-CONDITIONS** on BOTH items).

### ITEM A — the terminal lives on the DISJOINT `retro_terminal` attribute, never on `status`

§5.3 above specifies `SET #s = :terminal`. **The built form does not write `status`
at any value, ever** (`retro_redrive_handler.py:195-196`, `:40`). The emitted
UpdateExpression's SET clause is `retro_terminal` / `retro_redrive_at` /
`retro_word_ref` (+ `retro_terminal_reason`, `retro_receiver_status`); `#s` is
aliased to `status` and appears **only inside the ConditionExpression**.

**The packet's author has concurred that §5.3 as written was DEFECTIVE**, and that
the departure is a **correction, not an alternative**: `SET #s = :terminal` would
have written the terminal onto the one attribute the armed SEV-1 dead-letter LEVEL
alarm positively selects on, silently emptying the level for `held` and
`refused_with_reason` — resolving a live loss **by silence**, the exact failure
`dead_letter_level_surface.tf:201` exists to refuse. A false red on an armed alarm
is the survivable direction; a false green is not.

**The three ConditionExpression duties are preserved verbatim and un-collapsed** —
`"attribute_exists(pk) AND #s = :dead_letter AND attribute_not_exists(retro_redrive_at)"`
— and §5.3's naming ruling (`retro_redrive_at` / `retro_word_ref`, never
`operator_redrive_at`) is honoured, leaving `operator_redrive_at` standing as the
historical stamp of the 2026-09-04 un-walled re-arm. The hold sibling adds a fourth
condition (`attribute_not_exists(retro_held_at)`) — a strengthening.

**Reachability: STRICTLY STRONGER (T-E1).** Under `SET #s = :terminal` the module
would hold a `status`-write primitive and B-1 would be a *value-range* predicate
over a set that can grow. Under the disjoint form there is **no `status` write at
all**, so B-1 becomes an assertable **ABSENCE**.

**THE COST, NAMED (condition A-C1).** A re-driven row keeps `status="dead_letter"`
forever, so it remains inside the legacy `ContenteBookingDeadLetterRowsCurrent`
gauge. `ebi-contente-booking-dead-letter-level` (armed, `treat_missing_data =
"missing"`, SEV-1 SNS with a confirmed SMS subscription) therefore **stays in ALARM
until TTL reap on a booking that is no longer lost**, and as the row ages
`…-ttl-approach` fires a second SEV-1 whose runbook tells the operator to take a
disposition on a booking already recovered. Severity **Medium**. The danger is
second-order and precise: **an un-clearable SEV-1 on an already-recovered row
manufactures pressure toward exactly the raw-`UpdateItem` laundering act that caused
2026-09-04.** The new kind-named count does NOT over-count; the two planes disagree
permanently, by construction, and the kind-named count is the honest one.

- **OWNER:** the **operator**, as a data/monitoring decision — it is a live armed
  SEV-1 paging surface and no build seat may re-point it. **The fork is theirs:**
  (i) a gauge-side exclusion keyed on `retro_terminal = landed` **ALONE** (never on
  `held`, which must keep paging — G-HOLD), or (ii) accept-and-record.
- **DATED TRIGGER:** the **first `retro_terminal = landed` stamp on a LIVE row**.
  Until one exists the disagreement is synthetic and costs nothing; from that
  instant an armed SEV-1 is un-clearable by any act short of the TTL reap, and the
  fork must be closed. This is a real, observable instant — not a calendar date
  that lapses in silence.
- **PROVEN BY FIXTURE, not asserted:** `test_s09_composed_head.py`
  `TestARetroTerminalRowLeavesTheOutstandingLevel::test_the_LEGACY_gauge_over_count_is_NAMED_here_not_hidden`.

**Condition A-C2 — EC-2 §2.2 assertion 2 RESTATES to** (the concurrence's exact form):

> **2.** X's terminal is read from the **DISJOINT `retro_terminal` attribute**:
> `row_X["retro_terminal"] ∈ {landed, refused_with_reason, held}`; **AND** X's `status`
> is **UNWRITTEN by the act** — byte-identical to its pre-act value and therefore still
> literally `dead_letter`, hence not `failed`, not `intent`, not `redriving`; **AND** the
> retro module emits no `status` write of any kind — assert the emitted
> `UpdateExpression`'s SET clause names no `status` attribute and no alias resolving to
> one, and that `#s` occurs **only** inside the `ConditionExpression`.

**Condition A-C3 — break vectors B-9..B-12** (`CONCURRENCE… §(5)`) are carried into
the S-10 certifier brief; **B-10 and B-12 are the two a certifier is most likely to
miss.** B-10 in particular: a gauge "reconciliation" that excludes rows carrying ANY
`retro_terminal` would silence `held` — the false green this whole amendment exists
to refuse.

### ITEM B — `dry_run` is honoured FAIL-CLOSED only; it is NOT a mode enum

Recorded as a packet-delta, **not** a new mode. EC-3 forbids an `OBSERVE` posture: a
mode **monotone toward the POST** ("compute the refusal, then POST anyway"). The
built lever is monotone **away** from it:

1. **Not an enum.** `_ACTS = frozenset({"redrive", "hold"})` is CLOSED at two and
   `dry_run` adds no member.
2. **Fail-closed on every resolution mode.** `getattr(config,
   "contente_booking_dry_run", True)` defaults **True** on an absent attribute, over
   a typed `bool = True` — including a config object that lost the field.
3. **The forbidden ordering is UNREACHABLE, not merely unused.**
   `REFUSE_POSTURE_PAUSED` returns inline; `await client.book(payload)` lives inside
   `apply_retro_redrive`, and the `ContenteBookingClient` is **not constructed until
   after the gate**. At the moment the refusal is computed there is no client object
   in scope to POST with. The hold branch has the same property by construction.

**Standing fence (the concurrence's condition on this item):** no successor may
introduce a value of any lever under which the refusal is computed and the act still
fires. Mutant `POSTURE` at the assembled head kills that regression.

---

## 5.4 — Replay and expiry semantics

| Case | Behaviour | Enforced by |
|---|---|---|
| Same payload replayed | **Zero additional POSTs.** The conditional fails on `attribute_not_exists(retro_redrive_at)`; a typed `already_consumed` refusal is returned and counted | The row (M-5) |
| Payload replayed after the row moved | Conditional fails on `#s = :dead_letter`; typed refusal | The row |
| Stale payload | `not_after < now` → refuse **before** any store read and **before** any POST | The handler, first check |
| Payload naming an absent pk | `get_item` returns nothing → typed refusal, counted, never a silent success | The handler |
| Payload naming a live non-`dead_letter` row | Conditional fails; typed refusal | The row |

**Every refusal is TYPED and COUNTED.** A refusal that returns the same shape as
"nothing to do" is a silent drop — the exact defect the initiative exists to
eliminate ("a reading that cannot name its own kind is still silence").

## 5.5 — Who may mint it

**Nobody mints anything. There is no secret, and that is a deliberate design
decision, argued rather than assumed.**

A signing secret (HMAC over the pk) was considered and **refused**:

1. It does not reduce reachability. Whoever can invoke the function is who can act; a MAC checked *inside* the function is downstream of the only control that matters.
2. It creates a new credential to hold, rotate and leak — and **credential-rotation execution is itself R-A4 never-grantable** (clause 1). We would be adding a permanent floor-class obligation to guard a floor-class act.
3. It violates charter operative core §2: *"simple wins and earns its proof — a simpler thing needs less proof, so that proof stays cheap."* An IAM-reachability wall is checkable by reading one policy document. A MAC wall requires reasoning about key custody, rotation, and replay windows — more proof, for no reduction in reachability.

**Therefore: minting authority == IAM.** The authority to speak this word is
exactly the AWS principal set holding `lambda:InvokeFunction` on the retro
function's ARN — which §6 constrains to the operator's own SSO identity, and
which CloudTrail records per invocation with the caller identity attached.

*The honest limit of this choice, stated:* an attacker who obtains the operator's
AWS session can speak the word. That is true of every design here, including the
MAC variant (the MAC would live where the session lives). **The residual is
correctly a credential-custody risk, not an authorization-design risk, and it is
named rather than papered.** It belongs in the annex's attack surface.

---

# EC-6 — F-M6 RESOLVED, with the reason

**The fork.** WS-C entry surface for the word: `ari` subcommand · guarded script ·
Lambda invoke payload with a word token. Vacuity tell if unnamed: *"A re-drive
path that a sweep could reach (C-5 violation)"* (frame `:1192`).

## 6.1 — CONSTRAINT-1 does NOT bind here. Stated explicitly.

**CONSTRAINT-1 (frame C-2) governs field additions to the 6-field gate request to
`autom8y-data`: server-first, nullable on the `extra="forbid"` model, then
client; client-first is a 422 → `p0_attribution_read_failed` → every booking
refuses.**

**It has no application to this fork.** The retro entry surface adds no field to
any gate request, touches no `autom8y-data` model, and crosses no service
boundary. Written here so that nobody imports it by analogy into a decision it
does not govern — which would be the same analogy-admission error R-A3 forbids,
run in the direction of excess caution rather than excess permission.

## 6.2 — The three enumerated options, weighed on the six axes

| | (a) `ari` subcommand | (b) guarded script | (c) invoke payload on the **reconcile** function |
|---|---|---|---|
| **Auditability** | Workstation shell history; the DDB write and the POST originate from the laptop | Same, plus the script is a repo artifact CI can also run | **Best.** CloudTrail `lambda:Invoke` with caller identity; the POST originates from the Lambda as every other booking POST does |
| **Least privilege** | The operator's workstation would need the **CONTENTE booking secrets** — credentials that live only in the Lambda's Secrets Extension today. **Widens a credential's residence.** | Same, worse (a repo file suggests a CI path) | **Best.** No credential moves. The secrets stay where they are |
| **Reachability from automation** | The script is reachable by anything that can run on the workstation or in CI | **Worst.** A repo script is one workflow away from a scheduled runner | **WORST IN A DIFFERENT WAY.** The retro path would live on the function **the EventBridge schedule already invokes every 15 minutes**. `lambda_handler` reads `event` **zero** times today (SVR P-6); adding event-dispatch converts an event-*ignoring* handler into an event-*dispatching* one, on a function with a live trigger. **This is the fork's own vacuity tell arriving.** |
| **Operator ergonomics** | **Best** — one short command | Good | Verbose; wrappable |
| **IaC footprint** | **None** | None | None |
| **Client fork risk** | **FATAL.** A workstation-side POST is a **second booking client** — a different HTTP client, a different timeout, a different `run_gate` call (or none). The repo has already refused exactly this: *"this is `run_gate`, the SAME symbol `book_contente._execute` calls — not a redrive-local re-implementation ... a re-implementation that happens to agree today is the fork this spec exists to prevent"* (`reconcile_handler.py:445-451`) | **FATAL**, same reason | **None** — same image, same client, same gate, same secrets |

**Result: none of the three is safe as written.** (a) and (b) fork the booking
client, which the codebase has already refused by name and which would also move
a credential. (c) preserves the client but co-locates the floor act with a live
15-minute trigger — the precise C-5 exposure the fork was raised to prevent.

## 6.3 — RESOLUTION: option (d) — a dedicated, unscheduled, trigger-less function

> **Resolve F-M6 to a FOURTH option: `autom8-email-booking-intake-contente-retro-redrive`
> — a dedicated Lambda function sharing the SAME image, with NO schedule
> resource, NO event source, NO `aws_lambda_permission`, and a role holding
> `dynamodb:GetItem` + `dynamodb:UpdateItem` and NOT `dynamodb:Scan`. Its only
> invocation path is an explicit `lambda invoke` by a principal that CloudTrail
> records.**

Enumerating a fourth option is required, not optional: the frame's own fork text
says the options are *"not exhaustive — enumerate at /shape"* (frame `:1175`), and
a truncated option slate is how a design's search space silently closes.

**What (d) keeps from (c):** the POST stays in the Lambda, on the same image, with
the same `ContenteBookingClient`, the same `run_gate` symbol, the same secrets
extension. **Zero fork.**

**What (d) removes from (c):** co-residence with a scheduled trigger. The retro
function has **no** schedule resource — not a schedule set `false`. *A boolean you
can flip is not a wall; a resource that does not exist is.* Flipping (c) back on
is a one-line tfvars edit. Reaching (d) requires authoring a new terraform
resource, which is a reviewable diff.

**What (d) adds that neither (a), (b) nor (c) offers:** the **IAM-layer bulk
impossibility** of M-1. On (c), the retro path would inherit the sweep role,
which holds `dynamodb:Scan` (SVR P-17) — so ONE-ROW-AT-A-TIME could only ever be
a code convention. On (d) it is a permissions fact.

**Where the ergonomics answer goes:** an `ari` subcommand that *constructs this
invocation* is welcome (§5.1) and adds no authority. That is how option (a)'s one
genuine advantage is kept without its fatal one.

**The honest cost, surfaced not absorbed (§9 Δ-3).** (d) adds a **terraform
surface** to WS-C, which the frame scoped as code-only (frame `:991-994`
names "reconcile Lambda code ... ledger row fields"). The new function is created
by a `terraform apply`, not by the image event. This does **not** breach C-1 (one
*image* event, on all three functions) — a fourth function pinned to the same
image tag is an apply, not a second image event — but it **widens F-M7** from
"does WS-B's alarm apply ride the deploy dispatch?" to "does WS-B's alarm **and
WS-C's function** ride one apply?" **That is an operator-burden question and it is
now larger than the frame priced it. It is the operator's, and this packet does
not rule it.**

---

# EC-7 — UV-P-1's probe: DESIGNED here, EXECUTED by nobody here

> `[UV-P: thenewnhc refuses PAST-DATED appointments (and 503 is how it says so) | METHOD: operator-worded single probe designed in WS-C, or a word from the receiver's owner | REASON: never probed by either lane; a probe POST is customer-visible outbound (D-7) and is not an agent's act]`

**Nothing in this section was executed. No POST was made. No probe was run.**

## 7.1 — Recourse order: the cheapest answer first

**RECOURSE 1 — a word from the receiver's owner. Zero blast radius. Try this
first.** The question is *"does your endpoint reject a booking whose `appt_time`
is in the past, and with what status?"* A human answer costs one message and
creates no appointment. The frame's own UV-P-1 METHOD names it. **If this
answers, RECOURSE 2 is never run.**

**RECOURSE 2 — the paired A/B probe below.** Only if RECOURSE 1 is unavailable.
It costs one real appointment.

## 7.2 — The smallest probe that actually discriminates (RECOURSE 2)

**The question is two-sided and a single POST cannot answer it.** The CARD names
two live hypotheses: *"Whether it is a past-dated-appointment refusal mis-coded
as 503, or an office/guid-specific fault"* (CARD `:126-127`). A single past-dated
POST returning 503 is **consistent with both** and therefore discriminates
nothing. That is why the smallest *sufficient* probe is a **pair**:

| Arm | Payload | Blast radius |
|---|---|---|
| **A (past-dated)** | The `bd875254…` shape, `appt_time` in the past | If accepted: a past-dated appointment at a real clinic |
| **B (future-dated)** | **Identical in every field except `appt_time`**, set to a near-future slot | If accepted: **a real, customer-visible appointment that a human must cancel at the receiver** |

Same office, same guid, same synthetic patient identity, **one field apart** —
because a probe that varies two things answers neither question. This is the same
one-mutant-per-case discipline the initiative applies everywhere else (shape §7
Prescribed 1, item 16).

**Reading the pair:**

| A | B | Conclusion |
|---|---|---|
| 503 | 2xx | **The 503 IS the past-date refusal.** UV-P-1 discharged positive |
| 503 | 503 | The 503 is office/guid/payload-specific. **UV-P-1 is NOT discharged** — it is *replaced* by a different open question, and saying otherwise would be an overclaim |
| 2xx | 2xx | Past-dated is accepted. `bd875254…`'s 10×503 is something else entirely |
| 2xx | 503 | Incoherent; re-probe or escalate. Do not rationalize |

## 7.3 — Blast radius, and whose act this is

**Both arms are `POST`s that create customer-visible appointments at a real
receiver.** Both are therefore **R-A4 never-grantable / charter §5(b) sensitive
list / frame D-7**: *"a 'probe' of UV-P-1 is an operator act, never an agent's"*
(frame `:858-859`).

- **Arm B is the expensive one.** If it succeeds it creates a real appointment that a human must cancel at the receiver, at a clinic we do not control. **Budget for that cleanup before running it, not after.**
- Neither arm is reversible from our side (charter §5(a)).
- Arm A is *probably* cheap — but "probably" is doing the work of an untested premise, which is what UV-P-1 *is*. **If arm A were known cheap, UV-P-1 would already be discharged.** Do not treat A as the safe half.
- **Sequencing:** run **A first**. If A returns 2xx, the past-dated hypothesis is already falsified and **arm B is unnecessary** — which halves the expected blast radius at zero cost to the answer.

## 7.4 — What each answer changes for S-08's terminal set `{landed, refused_with_reason, held}`

| Outcome | Effect on the terminal set | Effect on the build |
|---|---|---|
| **Positive** (past-dated refused) | The set stays 3-wide; its **distribution** becomes known. `landed` is **unreachable via the receiver** for past-dated rows; `refused_with_reason` is the expected terminal | S-08's `refused_with_reason` path becomes the **primary** path and needs the richer treatment. **F-P4 collapses hard toward "record-only"** — the RS-3 data-plane clause could then only ever be paid by our own record. **`landed` must not be built as the default reading of a 2xx** |
| **Negative** (past-dated accepted) | The set stays 3-wide, `landed` genuinely reachable | `bd875254…`'s 503 is office/guid-specific → a **different defect class**, and whether re-drive can ever succeed for *that* row re-opens. WS-C's mechanism is unaffected; the fixture's prognosis is not |
| **Undischarged** (RECOURSE 1 unanswered, probe not run) | **The set stays 3-wide and S-08 builds all three anyway.** This is the correct default | The terminal set is a **discrimination requirement**, not a prediction. Building all three costs little; **collapsing to two on an unmeasured premise is exactly the fault this initiative exists to cure.** No sprint is blocked on UV-P-1 |

**`held` is ours in every branch.** It never touches the receiver and no probe
outcome affects it (§8).

---

# EC-8 — The terminal set's authorization semantics

## 8.1 — Which terminals imply an external effect

| Terminal | External effect? | Reversible from our side? | Class | Authority required |
|---|---|---|---|---|
| **`landed`** | **YES** — an appointment now exists at the receiver | **NO** | R-A4 floor: customer-visible outbound + external commitment | Per-instance operator word |
| **`refused_with_reason`** | The POST was **attempted** (the attempt is itself the floor act); the outcome is a write to OUR record | The record write, yes; the attempt, no | The **attempt** is floor-class; the **stamp** is records-wall | Per-instance operator word (for the attempt) |
| **`held`** | **NO POST FIRES.** A write to OUR record only | **YES** | Records-wall write | See 8.2 — **not** floor-class |

**The load-bearing asymmetry:** the floor is crossed by the **attempt**, not by
the outcome. `refused_with_reason` is not a "safe" terminal — by the time it is
stamped, a customer-visible POST has already left. **A design that treats
`refused_with_reason` as cheap has misread where the floor is.**

## 8.2 — A design consequence: `held` must not be forced through the floor

`held` is the only terminal reachable **without crossing R-A4 at all** — it is the
operator's decision *not* to act.

**Therefore the retro entry should carry an `act` discriminator, and
`act:"hold"` must be structurally incapable of reaching `client.book`** — not
merely branched away from it. Two consequences:

1. **Tier.** `act:"hold"` is a reversible records-wall write on a business ledger. It plausibly sits at **ADMIN-GRADE** (R-A3: *"reversible business-ledger METADATA writes"*) rather than on the floor. **We do not rule that** — a tier assignment for a novel act-class is an amendment, not an inference (R-A3), and R-A3 forbids admitting it by analogy to the unstamp class. **Routed to the operator; flagged as the cheapest thing in this packet to say yes to.**
2. **Testable form.** The `hold` path must be provably POST-free: assert `client.book` call count == 0 for every `act:"hold"` invocation, including malformed ones. If `hold` and `retro_redrive` share a code path that *branches* before the POST, one refactor puts `hold` on the wire.

## 8.3 — F-P4 ENUMERATED, NOT CHOSEN

> **F-P4: what does `landed` mean for a past-dated appointment?** This is the
> operator's and this packet does not choose it. Enumerated with the
> **authorization consequence** of each, which is the part this seat owes.

| # | Option | What `landed` asserts | Does it require the floor act? | Authorization consequence |
|---|---|---|---|---|
| **(i)** | **Receiver's calendar** | The receiver now holds the appointment | **YES** — a POST must succeed | Full §5/§6 wall required. `landed` is only claimable on a 2xx, and only if UV-P-1 says past-dated is accepted at all |
| **(ii)** | **Record-only** — OUR scheduling-performance data | Our data plane records the booking as reconciled; the receiver is out of scope | **NO — NO POST AT ALL** | **The never-grantable act disappears from the design.** WS-C drops from R-A4 floor to a records-wall write. §5's one-shot wall would still be wanted (a record of the booking is a record of record), but the outbound POST — the entire reason S-03 exists — is not needed to pay RS-3 |
| **(iii)** | **Both, typed apart** — `landed_receiver` / `landed_record` | Two distinct facts, never conflated | **Partially** — `landed_record` does not; `landed_receiver` does | Most honest and most expensive: the terminal set grows to 4. The wall applies **only** to the `landed_receiver` path, which is then the one narrow floor act. **Also the only option that survives a "2xx but the receiver silently dropped it" outcome** |

**The reading this seat owes the operator, without choosing:** RS-3's own words
are *"retroactive processing of past-dated bookings after downtime/issues MUST be
supported so the database keeps accurate scheduling-performance data"*
(RATIFICATION `:36-38`, SVR P-12). **The stated beneficiary is the database.**
That is textual support for (ii) or (iii) — and if either is the word, **the
highest-risk act in this entire wave becomes unnecessary or narrows to one
branch.**

**The vacuity tell is live and named in the frame:** *"'landed' defaults to 'the
POST returned 2xx' and the RS-3 data-plane clause goes unpaid"* (frame `:1180`).
**If nobody rules F-P4, option (i) happens by default** — the most expensive
option, chosen by silence, paying the clause it was meant to satisfy least.

---

# §9 — SURFACED DELTAS (surfaced, never absorbed)

Where this packet departs from the dispatch, the frame or the shape, it says so
here rather than let S-08 inherit it silently.

| # | Class | Delta | Disposition |
|---|---|---|---|
| **Δ-1** | **anchor vs mechanism** | The dispatch and shape both cite `idempotency_ddb.py:660-700` as the by-construction fact. At `52995b26` that range is **`scan_dead_letter_rows`** — the READ-ONLY level observer, whose docstring `:668-671` *narrates* the exclusion. The **enforcing** code is `scan_redrive_candidates` at **`:501-545`**, filter at **`:528`** | **Corrected, and the proof is STRONGER than cited.** Both anchors are real; the packet cites the enforcing line and adds the second layer (`reconcile_handler.py:420`) the shape did not name. **S-08 must assert both layers** (B-2) — a single-layer test cannot tell which one regressed |
| **Δ-2** | **frame suggestion vs live ledger** | Frame D-5 names `operator_redrive_at` as the provenance stamp. That attribute **already exists on the live fixture**, written by the 2026-09-04 un-walled re-arm (SVR P-13) | **Use `retro_redrive_at` / `retro_word_ref`.** Re-using D-5's name makes `bd875254…` permanently un-retro-drivable AND conflates a walled act with an un-walled one on one field. Distinct names are what let the ledger tell them apart. §5.3 |
| **Δ-3** | **scope: WS-C grows a terraform surface** | The frame scopes WS-C's surfaces as "reconcile Lambda code ... ledger row fields" (`:991-994`). §6's resolution adds a **new Lambda function + IAM role** — a `terraform apply`, not an image event | **Surfaced as an operator-burden growth.** Does **not** breach C-1 (a fourth function on the same image tag is an apply, not a second image event) but **widens F-M7**. The operator now decides whether WS-B's alarm apply and WS-C's function apply are one act or two. **Not ruled here** |
| **Δ-4** | **fork slate was not exhaustive** | F-M6 enumerates three options; **all three fail** (§6.2) | **A fourth option is named.** The frame's own text licenses this: options are *"not exhaustive — enumerate at /shape"* (`:1175`). Recorded so the resolution is visibly an *addition* to the slate, not a silent re-reading of one of the three |
| **Δ-5** | **severity, stated against exploitation context** | It would be easy to rate the 2026-09-04 bypass Critical | **HIGH, not Critical**, and the reasoning is recorded (§3.4): authenticated operator act, no remote/anonymous path, and the receiver's persistent 503 — **not any control of ours** — is what held the blast radius to five refused POSTs instead of five created appointments. **Rating it Critical would be alarm inflation; rating it Medium would credit us for the receiver's luck** |
| **Δ-6** | **a comment's anchors have drifted** | `reconcile_handler.py:180-185` cites `idempotency_ddb.py:371` and `:447-449` for the two positive filters; at `52995b26` those are `:528` and `:638` | **Noted, not fixed.** Out of this packet's scope (its sole write is this file) and out of WS-C's. Recorded so a future reader does not treat the stale anchors as a contradiction of §1.1 |

---

# §10 — SVR LEDGER

Every platform-behavior claim in this packet carries a receipt below or a UV-P
label in §11. All `autom8y` reads are from the object DB at
`origin/main 52995b267a773f9b91b1c8992bcf8acba543b222`; all `autom8y-asana` reads
are from the session repo at `8f7ed3cb` / its object DB. No working tree was read
for code (C-10, scar 15).

| ID | Claim | Method | Anchor | marker_token (verbatim slice) |
|---|---|---|---|---|
| **P-0** | The autom8y read SHA is fixed for this packet and was re-fetched at dispatch | bash-probe | `git -C …/autom8y fetch -q origin main && git … rev-parse origin/main` | `52995b267a773f9b91b1c8992bcf8acba543b222` (exit 0) |
| **P-1** | The dead-letter LEVEL alarm's own description hands disposition to a human records-wall act rather than to any automated recovery | file-read | `autom8y:terraform/services/email-booking-intake/dead_letter_level_surface.tf:164` | `disposition (redrive-past-dated-HAZARD / accept-loss / human-recontact) is an operator records-wall card` |
| **P-2** | The TTL-approach alarm's description states the hazard class of the very act WS-C is designing, in the runbook a paged operator reads at 03:00 | file-read | `autom8y:terraform/…/dead_letter_level_surface.tf:201` | `recovery on a past-dated appointment is a HAZARD and is a walled records-wall act` |
| **P-3** | Layer 1 of the reachability proof: the sweep's candidate selection is a positive whitelist over `status`, so `dead_letter` is excluded by absence from an allowlist rather than by presence on a blocklist | file-read | `autom8y:services/email-booking-intake/src/email_booking_intake/forwarding_confirm/idempotency_ddb.py:528` | `#ns = :ns AND (#s = :failed OR (#s = :intent AND #c < :cutoff))` |
| **P-4** | Layer 2 of the reachability proof: even a row reaching the candidate set cannot be claimed, because the claim is conditional on a positive status tuple | file-read | `autom8y:services/…/reconcile_handler.py:420` | `if not store.update_status(pk, status="redriving", expect_status=("failed", "intent")):` |
| **P-5** | The repo has already reasoned its way to the whitelist-not-blacklist doctrine this packet's §1.1 depends on, and recorded the regression cost of the alternative | file-read | `autom8y:services/…/reconcile_handler.py:185` | `exclusion list would be one careless edit away from regression forever` |
| **P-6** | The sweep's entry point ignores its invocation payload entirely today, which is why F-M6 option (c) would convert an event-ignoring handler into an event-dispatching one on a triggered function | bash-probe | `python3 -c "ast.parse(reconcile_handler.py) → lambda_handler FunctionDef → count ast.Name id=='event'"` | `lambda_handler line 894 ; refs to event in body: 0` / `refs to context in body: 1` (exit 0) |
| **P-7** | The in-repo precedent for a reaper-exempt-by-construction row, cited for the provenance-stamp shape rather than re-derived | file-read | `autom8y:services/…/idempotency_ddb.py:242-243` | `the written ``Item`` NEVER carries a ``ttl`` key, at any value` |
| **P-8** | The SEC-001 taxonomy's members are each a class for which a standing service principal can be authorized — the property the RETRO act lacks | file-read | `autom8y-asana:src/autom8_asana/api/write_authz.py:101` | `An Asana write class subject to per-service authorization.` |
| **P-9** | SEC-001's predicate is deny-by-default membership with an empty allowlist meaning deny-all, which is the door-shape §3.3 inherits | file-read | `autom8y-asana:src/autom8_asana/api/write_authz.py:267` | `Returns False for an unresolved principal and for an empty allowlist` |
| **P-10** | The never-grantable floor is a ruling of record in this repo and sits above both grant tiers, so no phrasing reaches the RETRO act | file-read | `autom8y-asana:.ledge/decisions/RULING-decision-space-amendments-2026-08-26.md:85` | `No wording reaches these**, in any grant, at any tier: (1) credential-rotation` |
| **P-11** | The charter's second autonomy gate fires on this act independently of reversibility, so even a reversible variant would stop here | file-read | `autom8y-asana:.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md:55` | `anything a customer sees, anything touching security/credentials, anything that spends money` |
| **P-12** | The operator requirement of record names the DATABASE as the beneficiary — the textual basis for F-P4 options (ii)/(iii) in §8.3 | file-read | `autom8y-asana:.ledge/decisions/RATIFICATION-matcher-recalibration-sitting-2026-09-04.md:37` | `retroactive processing of past-dated bookings after downtime/issues MUST be supported` |
| **P-13** | The 2026-09-04 act wrote a status flip, an attempts reset and a provenance stamp in one raw UpdateItem — the flip is the state-laundering step and the stamp is the field-name collision of Δ-2 | file-read | `autom8y-asana:.sos/wip/CARD-dead-letter-disposition-2026-09-04.md:92` | `` `status dead_letter → failed`, `redrive_attempts → 0`, `operator_redrive_at = 1788543695` `` |
| **P-14** | One operator word produced five customer-visible outbound attempts on the scheduled sweep's cadence — the empirical basis for B-1 and §3.4 | file-read | `autom8y-asana:.sos/wip/CARD-dead-letter-disposition-2026-09-04.md:116` | `Five fresh sweep re-drives (attempts 1–5 after the operator re-arm at 18:21Z)` |
| **P-15** | The complete customer-visible-POST surface in EBI is two live call sites today; WS-C adds the third, which bounds the reachability question to a narrow one | bash-probe | `git grep -n "\.book(" origin/main -- 'services/email-booking-intake/src/**/*.py' \| grep -v test` | `book_contente.py:838:            response = await contente_booking_client.book(payload)` and `reconcile_handler.py:508:                await client.book(payload)` (2 live call sites; remaining 3 hits are comment lines) |
| **P-16** | The sweep is live in production on a 15-minute cadence, which is what made the 2026-09-04 claim land within seconds of the operator's flip | bash-probe | `git show origin/main:terraform/…/variables.tf \| grep -A4 contente_booking_reconcile_schedule` + `… production.tfvars \| grep reconcile_enabled` | `default     = "rate(15 minutes)"` and `contente_booking_reconcile_enabled = true` (exit 0) |
| **P-17** | The sweep's role holds Scan — so a retro path sharing that role could never make ONE-ROW-AT-A-TIME an IAM fact, which is the argument for a separate role in §6.3 | file-read | `autom8y:terraform/services/email-booking-intake/contente_booking_reconcile.tf:193-197` | `Action = [ "dynamodb:Scan", "dynamodb:UpdateItem", "dynamodb:GetItem", ]` |
| **P-18** | The repo's own precedent for minting a NEW terminal status value that is unselectable by every positive filter without editing any filter — the pattern §1.3/B-1 tells S-08 to follow for the typed terminals | file-read | `autom8y:services/…/reconcile_handler.py:177` | ``Sibling of `posted` / `dead_letter` on the SAME `booking|live` namespace:`` |
| **P-19** | SEC-001's write surface was DERIVED from route metadata rather than hand-enumerated, and derivation found four times what the design asserted — the discipline §1.2 follows when it enumerates the outbound-POST surface by exhaustive grep rather than by assertion | bash-probe | `git -C …/autom8y-asana log -1 --format=%B 54431c18` | `The design enumerated 5 write classes across 6 routes; a derived sweep of` (exit 0) |
| **P-20** | A third status-reading sweep does select dead-lettered rows, so §1.2 accounts for it explicitly rather than letting S-08 find it late | file-read | `autom8y:services/…/idempotency_ddb.py:638` | `#ns = :ns AND #s IN (:posted, :dead_letter) ` |
| **P-21** | The retry ladder's bound is a retry constant, not an authorization bound — which is why one word could produce five acts (§3.4 point 1) | file-read | `autom8y:services/…/reconcile_handler.py:119` | `_MAX_REDRIVE_ATTEMPTS = 5` (preceded at `:117-118` by `after this many FAILED sweep re-drives, the row is stamped`) |
| **P-22** | The codebase has already refused a re-implemented gate call by name, which is the basis for §6.2's fatal-fork rating of options (a) and (b) | file-read | `autom8y:services/…/reconcile_handler.py:449` | `that identity: a re-implementation that happens to agree` |

**Receipt-quality note.** Every `marker_token` above was re-verified by direct
probe against its cited anchor at authoring time — each is a literal substring of
its source line, and each `claim` articulates what the citation supports rather
than restating it (orthogonality). P-0, P-6, P-15, P-16 and P-19 are bash-probes
whose captured output IS the receipt. **One exception, declared:** P-17's
`marker_token` is a whitespace-normalized join of the contiguous range
`:193-197` (a five-line Terraform list), not a single-line slice; the tokens and
their order are verbatim.

---

# §11 — UV-P LEDGER

Carried in the frozen syntax so S-08, PT-01 and the attester can discharge or
carry each. RULE-2 applies: any unconsumed entry travels into the next HANDOFF.

- **UV-P-S03-1** `[UV-P: thenewnhc refuses PAST-DATED appointments and 503 is how it says so | METHOD: RECOURSE 1 a word from the receiver's owner (zero blast radius), else RECOURSE 2 the paired A/B probe designed at §7.2 | REASON: CARRIED FORWARD UNCHANGED from frame UV-P-1. This packet DESIGNED the probe and EXECUTED NOTHING. Both arms are customer-visible outbound (D-7 / R-A4) and are the operator's act, never an agent's. S-08 is NOT blocked: it builds all three terminals regardless (§7.4)]`

- **UV-P-S03-2** `[UV-P: the retro function's execution role can be provisioned WITHOUT dynamodb:Scan while still performing GetItem + conditional UpdateItem on the shared ebi-forwarding-idempotency table | METHOD: terraform plan on the S-08 branch, reading the rendered role policy; corroborated by an integration run against the table | REASON: the mechanism is sound on its face (the retro path addresses a known pk and needs no enumeration) and the sweep's own policy shows the three actions are separable (SVR P-17), but no seat has yet PROVISIONED a scan-less role against this table. M-1 — the strongest bulk-impossibility layer — rests on it]`

- **UV-P-S03-3** `[UV-P: a fourth Lambda function on the SAME image tag is an apply-only change that does not constitute a second image event under C-1 | METHOD: Pythia/architect ruling at PT-01, with the terraform diff in hand | REASON: C-1 says ONE EBI image event on all THREE functions. This packet reads a fourth function pinned to the same tag as a terraform apply rather than an image event (Δ-3), which is a READING of C-1, not a mechanical fact. If the reading is wrong, F-M6's resolution needs re-pricing, not re-deciding — the security argument for (d) is independent of how the apply is scheduled]`

- **UV-P-S03-4** `[UV-P: no principal other than the operator's own SSO identity holds lambda:InvokeFunction on the retro function's ARN once provisioned — in particular not the github-actions-terraform CI role | METHOD: IAM policy simulation / a read of the CI role's policy against the new ARN, at S-08 build time | REASON: §6.3's reachability claim is a claim about a resource that does not exist yet (Trigger Table row 7 — design-choice masquerading if asserted as present-tense). It is the annex's natural first attack-surface question and is deliberately left to it]`

- **UV-P-S03-5** `[UV-P: act:"hold" is admissible at ADMIN-GRADE as a reversible business-ledger METADATA write rather than sitting on the R-A4 floor | METHOD: operator tier-amendment or an explicit named extension in a grant (R-A3) | REASON: R-A3 forbids admitting a novel act-class by analogy, INCLUDING analogy to the unstamp class. §8.2 enumerates and declines to rule. This is the cheapest word in the packet and it unblocks the only terminal that never touches the receiver]`

- **UV-P-S03-6** `[UV-P: the live fixture bd875254… survives to S-08's build | METHOD: none available to this seat — the TTL 2026-09-10T05:28:46Z runs without anyone and F-P5 is the operator's (FORK-2) | REASON: PC-7 rates reaping LIKELY. BINDING REGARDLESS: S-08 builds on a SYNTHETIC row in a non-live ns, so no sprint is blocked; and if the fixture is synthetic, EVERY artifact says predicate leg (b)'s live half is WAITING. A synthetic row never reads as satisfying the predicate]`

**WEAK claims, graded WEAK and not upgraded by restatement:**

- **W-S03-1** — that the receiver's persistent 503 would have continued to bound the blast radius of a repeat of the 2026-09-04 act. Rests on 10 attempts across ~40h against one payload (CARD `:122-124`). A receiver-side change, a different office, or a different payload could all falsify it. **§3.4's severity rating deliberately does not lean on it** — it names it as luck rather than crediting it as a control.

---

# §12 — FENCES HONORED

| Fence | Status |
|---|---|
| `integrity-architect` (attester, RESERVED) | **Not consulted, not messaged, not addressed.** Nothing in this packet is written for its eyes or anticipates its reading. R-9 intact |
| `penetration-tester` (PG-3 wall prober, must stay UNBRIEFED until PT-03) | **Not consulted, not messaged, not addressed.** This packet was not routed to it |
| Gates G-P5 / G-A1 / G-P6 | **Unspoken. A gate is not work** (shape §7 Prescribed 18). No gate is reported obtained, absorbed, simulated or waited out |
| Clocks | **None parked.** No background waiter. Every clock (TTL 2026-09-10T05:28:46Z, alarm flip ~2026-09-08T05:28Z) is the main thread's |
| **PII fence** (C-4) | **Held.** The row is referenced by pk prefix `bd875254…` ONLY. `payload` was never read and is never reproduced. No patient contact field appears. Probe fixtures in §7 are specified as synthetic |
| Self-assessment cap | **MODERATE.** This is a same-rite security design; the rite-disjoint attestation is `integrity-architect`'s at PT-03, and this packet does not anticipate it |
| Code-read discipline (C-10, scar 15) | **Held.** Every `autom8y` code and terraform read is `git show origin/main:<path>` at `52995b26`. No working tree was read |
| Artifact path discipline (C-11) | **Held.** Authored at the absolute asana path with a `wc -l` read-back |
| Shell traps (C-12) | **Held.** `"${VAR}:path"` quoted; globs quoted; no `comm` used (no `LC_ALL=C` needed); no `--admin`; no `gh api -f` |
| Write scope | **This file only.** No code, no terraform, no ledger write, no probe, no word |
| Crusades | **meta-optimization** — the wall is five checkable layers, not five paragraphs. **modernization** — no legacy re-drive shortcut is inherited (D-8); the monolith's silent drop is a floor, not a reference. **principled future-proofing** — *a wall that is simpler is a wall that is provable*: §5.5 refuses a signing secret precisely because IAM reachability is cheaper to prove and cheaper to keep true |

---

**END PACKET.** S-03 exit criteria 1-8 addressed in order at §EC-1..§EC-8.
Deltas surfaced at §9. Receipts at §10. Unverified premises at §11.
Evidence grade **MODERATE** (same-rite authorship; the rite-disjoint attestation
is not this seat's and is not anticipated here).
