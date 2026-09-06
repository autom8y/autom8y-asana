---
type: concurrence
initiative: name-the-zero
checkpoint: .sos/wip/CHECKPOINT-name-the-zero-PT-02-2026-09-05.md
packet: .sos/wip/security/PACKET-retro-redrive-write-class-2026-09-05.md
pr: autom8y#1936 (feat/ntz-s08-retro-redrive)
head_sha: 282851d3fffa0a968fbee041ec871aa278a18f67
base: integration/name-the-zero @ 52995b26
author_seat: security-reviewer (co-seated security; packet author)
authored_at: 2026-09-05T05:45:05Z
evidence_grade: MODERATE
self_ref_cap: MODERATE — concurrence on my own design; claims re-derived from the
  object DB at the head SHA, never from the packet's memory
read_only: true
addressees: [S-09 assembly, S-10 certifier brief]
never_consulted: [integrity-architect, penetration-tester]
---

# ITEM A — terminal on a disjoint `retro_terminal`; `status` never written

## VERDICT: **CONCUR-WITH-CONDITIONS**

The departure is **correct and my packet's §5.3 was defective.** `SET #s = :terminal`
would have written the terminal onto the one attribute the armed SEV-1 dead-letter LEVEL
alarm positively selects on — silently emptying the level for `held` and
`refused_with_reason`, i.e. resolving a live loss by silence, the exact failure
`dead_letter_level_surface.tf:201` exists to refuse. S-08 proved this two-sidedly with a
fixture mutant (`test:526-544`). The conditions below bind the **cost the departure
moves**, not the mechanism.

### (1) Are the three ConditionExpression duties preserved exactly? — **YES, verbatim.**

`idempotency_ddb.py:604-607` emits, character-for-character:
`"attribute_exists(pk) AND #s = :dead_letter AND attribute_not_exists(retro_redrive_at)"`.
All three intact and un-collapsed: existence (no upsert), correctness, one-shot
authorization. `#s` is aliased to `status` at `:608` and appears **only** in the condition —
never in a SET (`set_parts`, `:582-586`, is `retro_terminal` / `retro_redrive_at` /
`retro_word_ref` [+ reason, receiver_status]). §5.3's naming ruling is honoured, with
`operator_redrive_at` left standing as the historical stamp of the 09-04 re-arm
(`:573-578`). The hold sibling adds a fourth condition (`:650-653`) — a strengthening.

### (2) Stronger, equal or weaker on the T-E1 reachability axis? — **STRICTLY STRONGER.**

Under `SET #s = :terminal` the module would hold a **`status`-write primitive**, and
B-1 ("the retro path writes `status ∈ {failed, intent}`") would be a *value-range*
predicate over a set that can grow — one widened terminal, one "just add `failed` for
the re-queue case", and 09-04 is re-created inside the walled path. Under the disjoint
form there is **no `status` write at all**, so B-1 becomes an assertable **ABSENCE**
(`test:778`, `test:789`). This is my own packet's terraform argument applied to code:
*a resource that does not exist cannot be enabled by a one-line edit.* The
state-laundering class is not merely refused here — it is **unspellable**.

### (3) Restated EC-2 §2.2 assertion 2 — I concur; the restatement is:

> **2.** X's terminal is read from the **DISJOINT `retro_terminal` attribute**:
> `row_X["retro_terminal"] ∈ {landed, refused_with_reason, held}`; **AND** X's `status`
> is **UNWRITTEN by the act** — byte-identical to its pre-act value and therefore still
> literally `dead_letter`, hence not `failed`, not `intent`, not `redriving`; **AND** the
> retro module emits no `status` write of any kind — assert the emitted
> `UpdateExpression`'s SET clause names no `status` attribute and no alias resolving to
> one, and that `#s` occurs **only** inside the `ConditionExpression`.

Strictly stronger than the original, which asserted a value-range on a *written*
field. **Note for S-09/S-10:** `test:301` asserts only `row_x["status"] not in
{"failed","intent","redriving"}` — which admits a `status` written to some *other*
value (dropping the row out of the level). The absence is covered elsewhere (`:778`,
`:789`); the restatement asks for `status == "dead_letter"` unchanged **at the
Direction-B site itself**, so the one test that names EC-2 §2.2 carries it whole.

### (4) The COST — an ACCEPTABLE NAMED divergence; **not** a reachability hazard, but it lands on an ARMED SEV-1 path and must not be left un-owned

**Reachability: NO hazard. Enumerated, not asserted.** Booking POST call sites are exactly
three (S-4). A `dead_letter` row carrying `retro_terminal=landed` is selected by exactly two
paths, both READ-ONLY: `scan_dead_letter_rows` (`:864`, whose only caller
`ledger_level_observation.py:140-147` counts and logs) and `scan_corroboration_candidates`
(`:805-808`, which writes the disjoint `corroboration_status` and self-excludes thereafter).
The sweep excludes it at **both** layers (S-3). The retro path refuses its own replay by the
row (M-5). **No selection path reaches `client.book`.**

**False RED: YES, and it is real.** After a `landed` retro the row keeps
`status="dead_letter"`, so (i) `ContenteBookingDeadLetterRowsCurrent` over-counts and
`ebi-contente-booking-dead-letter-level` — armed, `treat_missing_data = "missing"`,
SEV-1 SNS with a **confirmed SMS subscription** — **stays in ALARM until TTL reap** on
a booking no longer lost; and (ii) as it ages, `…-ttl-approach` fires a second SEV-1
whose runbook (`:201`) tells the operator to *"take the operator disposition — recovery
on a past-dated appointment is a HAZARD"* — on a booking already recovered. Severity
**Medium** (operational-signal integrity on the only paging surface for durable booking
loss; no remote/anonymous path; the five layers still bound any resulting act to one
POST on one pk). Its danger is second-order and precise: **an un-clearable SEV-1 on an
already-recovered row manufactures pressure toward exactly the raw-`UpdateItem`
laundering act that caused 09-04.** Hence WITH-CONDITIONS, not bare CONCUR.

**But the counterfactual is worse.** Under §5.3 as I wrote it, `held` and
`refused_with_reason` would have LEFT the level — a **false GREEN** on a live loss,
against CONTRACT `:751`. A false red on an armed alarm is the survivable direction; a
false green is not. **The departure is a correction of my packet, not an alternative.**

**CONDITIONS** (non-blocking to the mechanism; they bind the divergence):

- **A-C1.** The two-plane disagreement is recorded in the packet §5.3 amendment with an
  **owner and a dated trigger** — never "reconciling the legacy gauge is a separate act"
  with no name on it. Operator's fork: a gauge-side exclusion keyed on `retro_terminal =
  landed` **alone** (see B-10), or accept-and-record.
- **A-C2.** EC-2 §2.2 assertion 2 lands in its restated form, at the Direction-B site.
- **A-C3.** Break vectors **B-9..B-12** are carried into the S-10 brief; B-10 and B-12
  are the two a certifier is most likely to miss.

### (5) NEW break vectors the packet's B-1..B-8 did not name

All four follow from the terminal no longer being expressed in `status`. Under `SET #s
= :terminal` a consumed row **self-excluded** from every `dead_letter` selector by
construction; under the disjoint form exclusion depends on each path *also* reading the
second attribute — the invariant moved from structural to enumerated, and an enumeration
needs a guard.

- **B-9 — a `dead_letter`-selecting path acquires a write/POST caller.** The selectors
  are exactly two today (`:864`, `:805-808`), both read-only. *Assertion:* enumerate them
  **by literal** and assert AST-structurally that no caller of either reaches
  `client.book`, so a third selector fails loudly rather than inheriting the assumption.
- **B-10 — the legacy gauge is "reconciled" by excluding rows carrying
  `retro_redrive_at`.** The obvious cure, and a trap: it would also drop
  `refused_with_reason` (a permanent of-record loss) **and** `held` (which CONTRACT
  `:751` deliberately keeps INSIDE the outstanding total) out of the armed SEV-1 level —
  resolved-by-silence re-introduced by the fix. *Assertion:* any such exclusion keys on
  `retro_terminal = landed` ALONE; seed a `refused_with_reason` row and a `held` row and
  assert **both** are still returned. Only the `held` half exists today (`test:504`,
  mutant `:526`); the `refused_with_reason` half is **uncovered** and is the one where
  the contract and the code disagree.
- **B-11 — `retro_terminal` acquires a second writer.** A NEW attribute with no
  equivalent of BR-2's "every `update_status` call site is guarded" standing over it —
  BR-2 does not reach it. Two writers today (`:583`, `:648`), and the hold's condition
  prevents overwrite. *Assertion:* exactly two `retro_terminal =` SET occurrences in
  `src/`, both in those methods.
- **B-12 — the TTL-approach gauge fires on a landed row.**
  `dead_letter_min_ttl_remaining_hours` is computed over `scan_dead_letter_rows`' output
  (`ledger_level_observation.py:142-147`), so a landed row contributes its TTL to a
  `Minimum`-statistic SEV-1 alarm whose runbook instructs a hazardous recovery act.
  CONTRACT §10 says `landed` arms a 90d TTL; the retro act writes none. *Assertion:*
  either S-09 owns the TTL arm and a `landed` row is proven excluded from the
  TTL-approach input, **or** the divergence is recorded with a dated trigger. This is the
  sharpest edge of the cost.

# ITEM B — `dry_run` honoured fail-CLOSED only

## VERDICT: **CONCUR-WITH-CONDITIONS** (as built — **no rename** — plus one standing fence)

### (1) Is it a mode enum in the sense EC-3 forbids? — **NO.**

EC-3 forbids an `OBSERVE` posture: a mode **monotone toward the POST** — "compute the
refusal, then POST anyway." This is monotone **away**: `dry_run=True` REFUSES; no value of
it causes an act that would not otherwise occur. Not an enum at all — `_ACTS =
frozenset({redrive, hold})` is CLOSED at two (`:185`) and `dry_run` adds no member.
`getattr(config, "contente_booking_dry_run", True)` (`:588`) defaults **True** on an absent
attribute, over a typed `bool = True` (`config.py:316`) — fail-closed on every resolution
mode, including a config object that lost the field.

### (2) Any value or ordering under which the refusal is computed and the POST fires anyway? — **NO. The POST is not merely refused; it is unreachable, and the client does not yet exist.**

`lambda_handler:588-589` **returns** `REFUSE_POSTURE_PAUSED` inline. `await
client.book(payload)` is at `:495` inside `apply_retro_redrive`, reachable only via
`asyncio.run(_run_redrive_and_close(...))` at `:628`; the `ContenteBookingClient` is not
constructed until `:622` — **after** the gate. At the moment the refusal is computed
there is no client object in scope to POST with. The forbidden ordering has no
expression here. (Same property the hold branch has at `:604-605`: it returns before a
client exists, by construction, not by a branch a refactor could reorder.)

### (3) Env/tfvars lever (BR-12) or a 5th payload field? — **Env, and it is the SAFE polarity; NOT a payload field.**

`contente_retro_redrive.tf:274` passes the **shared estate-wide** tfvar, deliberately
not a retro-local lever (a second lever would be the fork this module refuses
elsewhere). BR-12's hazard is a standing flag that **substitutes for a word**; this one
cannot, and `test:1131` proves it with every lever permissive: no well-formed word →
REFUSE, book calls 0. Not a payload field: `_REQUIRED_FIELDS` is exactly four (`:234`)
and field-set **equality** is checked at `:348`, so an unknown key is a refusal rather
than an ignored extra — the `{"operator_confirmed": true}` / `scope="*"`-in-a-new-costume
shape cannot be spelled.

### (4) Disposition — **CONCUR as built, no rename, with a fence.**

I considered a rename (`dry_run` means *shadow-and-write-elsewhere* on the intake path,
*refuse* here) and rule **against** it: a rename mints a retro-local lever, and the
semantic that matters is identical on both paths — *no live customer-visible POST leaves
this estate while the posture is paused*. The divergence is only in what happens
**instead**, and this path's "instead" is the safe one.

**CONDITIONS:**

- **B-C1 (assert the ordering, don't infer it).** `test:1144` asserts book-calls == 0 and
  the typed reason, but not the ordering. Add one assertion that under `dry_run=True` **no
  `ContenteBookingClient` is constructed at all** (source/AST: the `REFUSE_POSTURE_PAUSED`
  return precedes the `ContenteBookingClient(` construction in `lambda_handler`).
  "Constructed but not called" is one refactor from "constructed and called."
- **B-C2 (standing refusal).** Record that `REFUSE_POSTURE_PAUSED` must **never** be
  "improved" into a shadow-write. That conversion — refuse → shadow — is exactly the
  `OBSERVE` posture EC-3 forbids, arriving later by a smaller, friendlier diff. The
  refusal IS the terminal, not a placeholder for one.

# UV-P-S03-4 — the CI role's `lambda:*` on `function:autom8-*` (no ruling; carried to S-10)

**It does not change EC-5's conclusion; it CONFIRMS it and falsifies one gloss on it.**
EC-5 refused a signing secret and set *minting authority ≡ IAM reachability* on the argument
that an IAM wall is checkable by reading one policy document — and this finding **is that
read succeeding**: `github-oidc/main.tf:921-932` grants `lambda:*` (hence
`InvokeFunction`) on `function:autom8-*`, which the retro function's name matches, to
`github-actions-terraform`, bounded by its trust policy (`:412-448` — main-branch pushes
/ environment-protected deployments, and where `terraform_apply_workflow_refs` is set,
only named reusable workflows). What is falsified is §5.5's *gloss* that §6 constrains
the principal set "to the operator's own SSO identity": the word is also speakable by a
**standing non-human principal**, which sits awkwardly against R-A4's "standing
principals: NONE, at any tier." Severity **Medium** — that role already holds `lambda:*`
across the whole `autom8-*` fleet including the sweep, so the retro function
**inherits** the exposure rather than creating it; no remote or anonymous path; and the
five layers still bound any such invocation to one POST on one named pk under a
well-formed ≤1h word. Credit where due: **S-08 surfaced this itself** at
`contente_retro_redrive.tf:96-106`. Cures, each a fleet/terraform act → G-M7 / operator:
**(a)** an explicit `Deny`, but **action-scoped to `lambda:InvokeFunction` /
`InvokeFunctionUrl` on that one ARN** — the same role needs `CreateFunction` /
`UpdateFunctionConfiguration` on that ARN to apply the resource, so a naive whole-ARN
Deny is self-blocking; **(b)** a name outside `autom8-*` — cheap, but it must also miss
`autom8y-*` (`:930`), breaks the naming convention, and is security-by-naming that the
next `autom8-…` function re-opens; **(c)** a function resource policy — **looks like a
cure and is not**: `aws_lambda_permission` is an allow-list, identity-based `lambda:*`
still grants invoke same-account, and adding one breaks the module's own
no-`aws_lambda_permission` invariant (B-4, `:35`); **(d)** accept-and-record with the
fleet-wide framing. Only (a), action-scoped, cures without breaking an invariant.
**No ruling — the operator's.**

# SVR ledger (all `file-read` / `bash-probe` against the object DB at 282851d3; no working tree)

| # | Claim | Anchor @ 282851d3 | Marker |
|---|---|---|---|
| S-1 | module writes no `status`, ever; terminal on a disjoint attribute | `retro_redrive_handler.py:40`, `:195-196` | `Nothing in this module writes ``status``, at any value, ever.` |
| S-2 | three duties verbatim; `#s` condition-only; SET names no status | `idempotency_ddb.py:604-607`, `:608`, `:582-586` | `attribute_exists(pk) AND #s = :dead_letter AND attribute_not_exists(retro_redrive_at)` |
| S-3 | hold adds a fourth condition (strengthening); sweep excludes dead_letter at BOTH layers | `idempotency_ddb.py:650-653`, `:696`; `reconcile_handler.py:420` | `AND attribute_not_exists(retro_held_at)` · `expect_status=("failed", "intent")` |
| S-4 | exactly three booking POST call sites (bash-probe, exit 0) | `git grep -n "\.book(" -- services/email-booking-intake/src` | `book_contente.py:838`, `reconcile_handler.py:508`, `retro_redrive_handler.py:495` |
| S-6 | the two dead_letter selectors, both read-only; both gauges' input includes the retro'd row | `idempotency_ddb.py:864`, `:805-808`, `:852-855`; `ledger_level_observation.py:140-147` | `READ-ONLY: this method issues ``Scan`` only.` · `rows = store.scan_dead_letter_rows(ns=ns)` |
| S-8 | level alarm armed, SEV-1 SMS, non-self-clearing; TTL-approach runbook instructs the hazardous act | `dead_letter_level_surface.tf:162-184`, `:201` | `STAYS in ALARM until the row is resolved or TTL-reaped` · `recovery on a past-dated appointment is a HAZARD` |
| S-10 | packet §5.3 proven defective for `held` by a fixture mutant | `test_retro_redrive_wall.py:504-544` | `test_RED_a_status_writing_hold_would_drop_the_row_out_of_the_level` |
| S-11 | contract keeps `held` outstanding, disposition ABSENT | `CONTRACT-…-2026-09-05.md:751` | ```held_at`` set; **``disposition`` stays ABSENT**` |
| S-12 | dry_run gate precedes client construction, which precedes the POST | `retro_redrive_handler.py:588-589` → `:622` → `:628` → `:495` | `if getattr(config, "contente_booking_dry_run", True):` |
| S-13 | dry_run is a typed bool defaulting closed; shared tfvar, not retro-local | `config.py:316`; `contente_retro_redrive.tf:274` | `contente_booking_dry_run: bool = True` |
| S-14 | four-key exact field set, equality-checked; retro role GetItem+UpdateItem, Scan absent | `retro_redrive_handler.py:234`, `:348`; `contente_retro_redrive.tf:198-200` | `if frozenset(event.keys()) != _REQUIRED_FIELDS:` |
| S-16 | CI role grant + trust bound; S-08 self-surfaced it | `github-oidc/main.tf:921-932`, `:412-448`; `contente_retro_redrive.tf:96-106` | `actions = ["lambda:*"]` … `function:autom8-*` |

# UV-P ledger

- [UV-P: the live set of AWS principals holding `lambda:InvokeFunction` on the retro function's ARN | METHOD: account-level IAM read (SSO permission-set membership + every role policy granting `lambda:Invoke*`) by a principal with `iam:` read | REASON: SSO permission-set membership is not readable from any commit of either repository; the design makes the invoke ACL the whole of the minting authority, so this is the one fact that most needs a live read. S-08 carries the same UV-P at `contente_retro_redrive.tf:302-308`; I do not discharge it here.]
- [UV-P: that the retro role provisions with `GetItem`+`UpdateItem` and no `Scan` against the live account | METHOD: `terraform plan`/`apply` by the operator | REASON: read-only fence; no plan or apply was run by any seat, and `terraform validate` in a backend-less init does not prove an applied policy shape.]
- [UV-P: whether the alarm-side false RED actually pages in production after a `landed` retro | METHOD: observe `ContenteBookingDeadLetterRowsCurrent` and the two alarms across a real retro act on the live `bd875254…` row | REASON: no retro act has been performed at any commit; the claim is derived from the emitter's input set (`ledger_level_observation.py:140-147`) and the alarm definitions, not from an observed firing.]
- [UV-P: that S-09's `loss_rows_outstanding_total` excludes a `retro_terminal`-bearing row and that its `loss_rows_unwitnessed_dead_letter` treatment is intended | METHOD: S-09's own re-derivation by test at the assembled head (PT-02 §2 must-derive) | REASON: the WS-B loss-plane register does not exist at this base; out of scope for this concurrence and NOT ruled on here.]
