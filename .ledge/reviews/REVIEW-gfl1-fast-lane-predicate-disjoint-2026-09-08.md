# REVIEW — G-FL1 fast-lane blast-radius predicate · RITE-DISJOINT

- **sprint:** S-13R · **rite:** security (`security-reviewer`) · **deploy class:** C-INERT
- **serves:** operator word **O-2** (PT-00, 2026-09-08) — *ratify G-FL1 CONDITIONAL ON A RITE-DISJOINT REVIEW.* This artifact is that review. **Until it is read, G-FL1 is not ratified.**
- **under review:** `.ledge/decisions/PROPOSAL-fast-lane-blast-radius-predicate-2026-09-08.md` (270 lines, read in full at source)
- **review question (verbatim from the proposal :270):** *does any change satisfying FL-1..FL-4 cross a security or customer-visible boundary the four conjuncts fail to see?*
- **binding on this output (verbatim, proposal :270):** *If one exists, the predicate is wrong and the predicate is what changes — never the exemplar.* Every amendment below changes conjunct text. **No amendment narrows an exemplar.**
- **disjointness:** this seat did not author the predicate, is in a different rite from the authoring seat (10x-dev architect), and re-derived every code fact from the object DB at an explicit ref. Grade is therefore **not** capped at MODERATE by self-reference. Per-finding grades are stated at each finding; **measured** and **reasoned** are labelled separately throughout.

---

## VERDICT — **CLEAR WITH AMENDMENT**

**Yes. Such changes exist, and the exemplar is one of them.** Four boundary-crossing classes pass all four conjuncts as written. One of them (G-1) means the lane as drafted admits the **empty set**. Three of them (G-2, G-3, G-4) are boundary crossings the conjuncts cannot see, and all three are **realized in the exemplar itself, at named production loci, verified own-hands.**

**Not REFUSE.** The predicate's architecture is sound as a class and I want to say so plainly: four ANDed booleans with no override, reading the change's *effect* rather than its *address*, with a written REFUSE regression test that travels with every revision, is a better instrument than the three alternatives §9 rejects — and §9's rejections are honest, not strawmen. ALT-B's diagnosis (*"with no written test, nobody can be shown to have applied it wrongly, so the safe play is always the maximum"*) is correct and is the reason to fix this predicate rather than discard it. The defects below are enumerable and closable in conjunct text. That is an amendment, not an unsound class.

**Not CLEAR.** G-1 alone is disqualifying: FL-1 and FL-E1 are mutually unsatisfiable, so no PR can enter the lane. G-2 and G-3 are worse than gaps — they are the two failure classes **this exact service has already been bitten by and had to build bespoke instruments to cover.**

**Ratify G-FL1 only with §A's amended conjunct text substituted.** As written, do not ratify.

---

## §1 WHAT I VERIFIED, AND AT WHICH REF

**Refs re-resolved at this seat's start (fence 2, STALE-TREE TRAP):**

| repo | ref | resolved |
|---|---|---|
| autom8y-asana (session repo) | `HEAD` | `d75bfe1a` (branch `main`) |
| autom8y-asana | `origin/main` | `389c59bc` |
| autom8y | `origin/main` | **`883eb3bf`** |
| autom8y | local checkout | `29e59e81` on `fix/wss-wildcard-scope-bypass-closure`, **352** dirty — never read |

**★ READ-SURFACE DRIFT — the fence undercounted, and I am reporting it rather than inheriting it.** The dispatch fence states origin/main was re-resolved to `a4bc0e39` at 20:33Z and calls it the fourth move. At my start it is `883eb3bf` — a **fifth** move. The proposal (:9) read `cc88b75e`. `a4bc0e39` does **not** resolve in autom8y-asana at all (`fatal: Not a valid object name`); it is an autom8y ref. Three distinct refs are in play across three artifacts of the same day.

**Does the drift invalidate the proposal's code facts? Measured: no for `services/`, YES for two other paths.**

```
git diff --name-only cc88b75e 883eb3bf -- services/email-booking-intake   -> ZERO files
git diff --name-only cc88b75e 883eb3bf                                    -> 9 files
```

Positive control on the same loop (varying the dimension asserted over — *does this filter ever match?*): the unfiltered range returns 9 files, and grepping them for `^(services|terraform|\.github)/` returns **exit 0 with two hits**. So the filter matches when there is something to match; the `services/` zero is **TAKEN**.

The two hits are load-bearing and both are proposal premises:

- `terraform/services/email-booking-intake/sprint2_forwarding_confirm_compliance.tf` — EBI terraform moved after the proposal was authored.
- `.github/scripts/merge-surface-sweep.sh` — **the M-4 required-check the proposal carries as a live UV-P has itself changed since the proposal read it.**

**Consequence:** the S-14 exemplar's `src/` facts hold at current `origin/main` and I re-verified them there (§3). The proposal's `merge-surface-sweep` UV-P is **not** discharged and has gotten *staler*, not less stale (§6).

**UV-P I explicitly did NOT inherit as discharged** — the dispatch instructed this and I honour it. All four of the proposal's UV-Ps remain OPEN at my exit; see §6. I discharged none of them and I opened three more.

---

## §2 THE FOUR GAPS

### ★ G-1 — FL-1 and FL-E1 are mutually unsatisfiable. The lane admits the empty set. [BLOCKING · measured]

FL-1 requires **every changed file** under one service's `src/`. FL-E1 requires **a two-sided test** — and it is explicitly not droppable (§8: *"A one-sided green is not a receipt"*).

Measured at `origin/main`:

```
git ls-tree -r --name-only origin/main -- services/email-booking-intake | grep -E 'test'
  -> services/email-booking-intake/tests/__init__.py, tests/_fake_ddb.py, tests/_fake_http.py, ...
```

Every real test in this service lives under `services/email-booking-intake/**tests/**`, **outside `src/`**. (The one `src/` hit, `contente_booking_disjointness_attest.py`, is my substring grep catching `attest`, not a test file — reported so the zero is honest.) Positive control on the same corpus and loop: `match_lead` matches under `src/`, so the path filter is not empty.

**Therefore:** a fast-lane PR that carries its own FL-E1 two-sided test has a changed file outside `src/` and **fails FL-1**. A fast-lane PR that satisfies FL-1 has no test and **fails FL-E1**. There is no diff that satisfies both. §10 files this as FR-2 ("a pure test-only diff — FL-1 refuses it, though its blast radius is nil") and reads it as a *cost*. It is not a cost. It is a **contradiction between the predicate and the evidence bar the predicate substitutes**, and it makes the admit set empty.

The escape — submit the test in a separate PR — is worse than the disease: it splits a change from its proof, and each half then enters a lane the other half's evidence justified. §6's C-1 image-event law makes that split expensive in envelopes as well.

### ★ G-2 — FL-3 is blind to aggregate-shape movement. Three live alarms take their input from exactly the quantity the exemplar moves. [BLOCKING · measured]

FL-3 tests two things: the path *today* produces no durable record, and **no already-recorded outcome changes**. Both are per-outcome tests. **Neither sees a counter's shape.**

The dispatch named this from PT-08 (`PIPELINE_TOTAL{status}` shifting from `failed` to `declined` while no individual recorded outcome changes). I went looking for what consumes that quantity in production. Measured at `origin/main`, **three** detection surfaces do:

| # | surface | locus | shape |
|---|---|---|---|
| 1 | `autom8-email-booking-intake-apigw-5xx-burst` | `op1_watch_alarms.tf:104-112` | `metric_name = "5xx"`, `threshold = 3`, `period = 300`, `statistic = "Sum"` |
| 2 | `autom8-email-booking-intake-apigw-5xx-sustained` | `op1_watch_alarms.tf:131-139` | `metric_name = "5xx"`, `threshold = 1`, `period = 300`, `evaluation_periods = 3` |
| 3 | `ebi-transient-fail-sustained` | `semantic_alarms.tf:133` | metric filter `{ $.event = "pipeline_completed" && $.status = "failed" }` |

`semantic_alarms.tf:124` states the coupling in the codebase's own words: *"``status=failed`` is the transient class (-> HTTP 502 -> SendGrid retry)."* The exemplar's entire effect is to move a population **out of** `status=failed` and **out of** 502. It is a direct move on the input of all three.

**FL-1 fences alarm FILES out of the diff. Nothing in the predicate fences alarm INPUTS.** A conforming fast-lane diff touches no `.tf`, passes FL-1 cleanly, and re-bases three production detection surfaces.

**And this is not a hypothetical class in this service — it is a realized one, twice, and the terraform says so verbatim:**

- `contente_stage_failure_detector.tf:24` — *"the trace returns HTTP 200, so no 5xx alarm sees it"*
- `extraction_disagreement_detector.tf:19-21` — *"no exception is raised, so the trace returns HTTP 200 and no 5xx alarm, no ``ebi-transient-fail-sustained`` (semantic_alarms.tf), and no API-GW surface ever sees it"*

**Two bespoke detectors exist in this service for no reason other than that 200-returning failures are invisible to the 5xx alarms.** FL-3 as written admits precisely that class of change. That is the answer to the review question, and it is measured, not argued.

**Reasoned (labelled as such), on direction:** for the exemplar specifically the movement plausibly *reduces* 5xx noise and so is benign or better. I am not claiming the exemplar breaks an alarm. I am claiming the predicate cannot tell the difference — the same conjuncts admit a change that moves the counter the other way, and the mirror-image change (marking a genuinely transient site terminal) would blind all three surfaces for that population. **The exemplar is safe here by luck of direction, not by predicate.**

### ★ G-3 — FL-4 is blind to disclosure-surface changes, and its floor is undefined pending a FLAGGED-PROVISIONAL ruling. [BLOCKING · measured + reasoned]

Measured: the exemplar moves its population onto the **park** path. `park.py` composes a human-visible Slack receipt, `_park_message`:

```
lines = [ f"*Booking parked ({decline.park_kind.value})*: `{decline.decline_class}`",
          f"office: {ctx.office_name or 'Unknown office'}" ]
if ctx.to:      lines.append(f"mailbox: {ctx.to}")
if ctx.subject: lines.append(f"subject: {ctx.subject}")
if ctx.appt_dt: lines.append(f"appt_dt: {ctx.appt_dt}")
```
*(`park.py:117-123`, `origin/main`)*

That posts the **raw subject line of a patient's booking email**, plus the mailbox, to Slack. `park.py:96-97` states what the mailbox is: *"``ctx.to`` is the routing mailbox ``{clinic-guid}@appointments.…`` — it LITERALLY CONTAINS the clinic identity."* And `park.py:110-113` states the two-plane split in its own words:

> *"Disclosure posture is unchanged: this ops receipt already carries the raw ``subject`` and ``office_phone`` … The STRUCTURED LOG keeps redacting (the ``redact_uuid`` discipline is a log-plane rule, not a Slack-plane one)."*

Confirmed measured: `park.py:178` uses `redact_uuid(ctx.chiropractor_guid or "")` on the log plane; `park.py:119-122` uses no redaction on the Slack plane.

**So the change moves a population from a plane that discloses nothing (502 records nothing, posts nothing) onto a plane that discloses raw patient-email subjects.** In a chiropractic-booking context that is PII and plausibly PHI-adjacent.

**Does FL-4(b) see it?** FL-4(b) is *"anything a customer sees, anything touching security/credentials, anything that spends money or makes an external commitment."* The customer does not see Slack. So the question collapses onto *"anything touching security/credentials"* — **and that limb's breadth is currently undetermined.**

`RULING-decision-space-amendments-2026-08-26.md:137-139` narrows it: *"The core §5 gate (b) credential limb — 'anything touching security/credentials' — **specializes to IDENTITY surfaces**: token species, claims models, validator contracts, isinstance gates, and audit semantics."* Under R-A8, a disclosure change is **out of gate**. Under the broad charter reading it may be in.

**And R-A8 is FLAGGED-PROVISIONAL** (`:131-136`): *"it operates provisionally on the operator's in-session word and MUST be re-consented at the next decision-space sitting convened outside session ``f73c2e72``, failing which it lapses to the broad reading."* Its certification was **REFUSED** by change-warden on lineage grounds.

**FL-4 cites R-A4 and CHARTER §5 and never names which reading of the credential limb it uses.** The predicate's floor is therefore *undefined against a ruling that may lapse* — meaning the same diff is in-lane or out-of-lane depending on an unresolved governance question. Worse, the same ruling's own warden flag (`:238-240`) records that **credential residence and read-route is in neither R-A4's floor nor R-A8's in-gate list and flows autonomously today** — a hole the predicate inherits silently.

**A gate whose floor is a function of a provisional ruling is not a floor.**

### ★ G-4 — FL-2 sees identifiers, not the policy carried in values. [BLOCKING · measured]

FL-2 tests *"no new symbol — every identifier it uses is already imported … and the idiom it applies already appears at another site in that same file."* Two measured holes.

**(a) `ParkKind` is a routing decision, and the exemplar's own FL-2 receipt overclaims.**

`decline.py:32-46` defines `ParkKind` and says what it does: *"Where (and whether) a parked decline's human-visible receipt is routed"* — `REVIEW` → *"routed to the review channel"*, `OPS` → *"routed to the ops channel"*. Choosing the member chooses **which humans get paged**.

The exemplar (§4.1) proposes `ParkKind.REVIEW`. Measured, every `TerminalDecline` site in `match_lead.py` at `origin/main`:

```
:549  TerminalDecline("name_evidence_ambiguous", ParkKind.OPS)
:574  TerminalDecline(BELOW_BAR_DECLINE_CLASS,   ParkKind.OPS)
:594  TerminalDecline("name_evidence_organic",   ParkKind.OPS)
:686  TerminalDecline(BELOW_BAR_DECLINE_CLASS,   ParkKind.OPS)
:913  TerminalDecline("lead_create_validation",  ParkKind.OPS)
```

**All five are `OPS`. Zero are `REVIEW`.** The proposal's §4.2 FL-2 cell reads *"The identical idiom **already appears five times in the same file**"* — **the idiom is not identical**; it differs on the axis that selects the channel. Whether the exemplar passes its own FL-2 depends entirely on whether "idiom" means the call shape or the `(class, park_kind)` pair, and **FL-2's text does not say.** This is not a quibble about the exemplar: it is proof that FL-2's granularity is undefined at exactly the granularity that carries the policy.

**(b) `decline_class` is an open string with no closed set, and a new value mints two production namespaces.**

Measured (zero, with corpus control): searching EBI `src/` for any closed-set guard — `DECLINE_CLASSES|ALLOWED_DECLINE|Literal\[.*decline|_VALID_DECLINE` — returns **zero hits, exit 1**. Positive control on the same corpus and tool: `BELOW_BAR_DECLINE_CLASS` returns 3 hits in `match_lead.py`. The corpus and the loop work; the zero is **TAKEN**. *(Bounded honestly: this proves no guard under those names. A guard under an unguessed name would evade my pattern — I did not exhaustively prove non-existence.)*

A new `decline_class` string literal is not an identifier, so FL-2 admits it unconditionally. Measured, what a new value does:

- `decline.py:73-74` — *"Emitted as the pipeline ``failure_class`` (``PIPELINE_TOTAL{status="declined", failure_class}``)"* → **mints a new CloudWatch metric-dimension value.** Any alarm or metric filter keyed on the dimension silently does not cover it.
- `park.py:285` — `"ns": f"decline|{decline.decline_class}"` → **mints a new DynamoDB keyspace namespace** on the shared `ebi-forwarding-idempotency` table.

Minting a metric-dimension value and a storage namespace are policy acts with cost and blast radius. **They pass FL-1 (in `src/`), FL-2 (no new identifier), FL-3 (the path records nothing today), and FL-4 (not outbound, not customer-visible, not a credential) — all four, cleanly.** That is a second direct answer to the review question: **yes, an open string dimension is a hole, and it is the exact hole PT-08 walked through when it cleared `normalized_name_empty` / `initials_normalization_invalid` on the grounds that `decline_class` is governed by no closed contract.** PT-08's reasoning was correct about the facts and wrong about the consequence: the *absence* of a closed contract is not a reason the conjunct passes, it is the reason the conjunct cannot see.

---

## §3 THE FL-1 RELOCATION ATTACK (dispatch axis 1) — the proposal's stated defence does not hold for the class

The proposal at :54 concedes FL-1 is gameable (*"move the allowlist into ``src/`` and FL-1 admits it"*) and defends with *"FL-3 refuses it anyway, on substance."*

**I tested that defence and it holds only for H2's shape, not for the class.** FL-3 refuses H2 because an off-allowlist office's bookings are *recorded today* (demoted to the dry_run keyspace), so widening changes an already-recorded outcome. That reasoning is sound **for a policy artifact whose current effect is recorded**. It says nothing about a relocated policy artifact whose effect lands on a path that records nothing.

Constructed class, in the shape the dispatch asked for — a policy artifact relocated into `src/` such that FL-1 admits it:

> A set literal in `src/` gating some behaviour, whose governed population **today terminates on an unrecorded path**. Adding an entry: **FL-1 passes** (file is under `src/`). **FL-2 passes** (a string in an existing set; no new identifier; the idiom — a member of that set — appears many times in the same file). **FL-3 passes** (the path records nothing today; no already-recorded outcome changes). The only thing standing between this and the lane is **FL-4**.

FL-4 catches the sub-case where the newly-enabled effect is an outbound act or customer-visible — which is why the redundancy *feels* sound. But by **G-3**, FL-4 does **not** catch a change whose effect is a *disclosure* onto a weaker-redaction plane; and by **G-2**, nothing catches a change whose effect is an *alarm-input* move. **So for two entire effect-classes the AND collapses to a single unguarded conjunct, and the "H2 fails three of four independently" redundancy claim does not generalize.**

The claim at :54 should not have been stated at class scope. That is a predicate defect, not an exemplar defect, and §A-1 amends it.

---

## §4 THE ANDing, AND OVER-REFUSAL (dispatch axis 5)

**Does anything pass all four individually while the combination is unsafe?** Yes — §2 G-2, G-3, G-4 are exactly that, and the exemplar realizes all three simultaneously. The ANDing is sound as *logic*; it fails because the conjunct **set is incomplete**, not because the connective is wrong. Adding a fifth conjunct is not required; the gaps sit inside FL-2, FL-3 and FL-4 and are closable there.

**Does it refuse things it should admit?** Yes, and over-refusal is a real cost — it is the whole reason the operator wants a fast lane. §10 names FR-1/FR-2/FR-3 honestly and I credit that. But:

- **FR-2 is misfiled as a false-refusal.** It is G-1 — a contradiction, not a conservatism.
- **FR-1 (no in-file precedent) is *correctly* refused** once G-4 is understood. A first `terminal_decline` in a file is a first *routing choice* for that file, and G-4(a) shows the routing axis is the unguarded one. §10 proposes v2 might cure FR-1; **it should not**. I record that as a dissent from §10's own widening wishlist.

**★ And the widening rule is unfalsifiable as written.** §10: *"v1 may be widened only after N≥3 fast-lane changes have landed with **zero incidents attributable to the lane assignment**."* By G-2, the lane's characteristic failure mode is **a silenced or re-based detection surface**. A silenced surface produces exactly one observable: *no incidents*. **The evidence the widening rule requires is the same artefact the defect manufactures.** This is the untaken-zero fence applied to governance: "no incidents" is an UNTAKEN zero unless something varied the dimension being asserted over. §A-5 amends it to require a positive attestation.

---

## §5 CHARTER FIDELITY (dispatch axis 4) — the restatement is faithful on §5 and DROPS §4 and §7

**Faithful where it quotes.** I diffed FL-4(b)'s sensitive-list restatement against the charter's byte-verified core at `CHARTER-decision-space-of-record-2026-07-30.md:55`. The four items — *"anything a customer sees, anything touching security/credentials, anything that spends money or makes an external commitment"* — are carried **verbatim and complete**. R-A4's three floor classes are carried verbatim from `RULING-decision-space-amendments-2026-08-26.md:85-88`. **No clause is dropped from §5 or R-A4.** The proposal's §2 reading of *"nothing else"* as a ceiling on gate count is a defensible reading of `:55`, and I do not object to it.

**★ But FL-4 is titled and scoped as *"clears CHARTER §5(a) and §5(b)"*, and the charter has two further binding clauses the predicate never restates.** This is the classic route around a gate, and it is present:

- **`:54` (§4)** — *"**'Done' for priority domains requires a real-world check.** Anything touching **money, customers, or data people act on** is not done until checked against reality at least once — not merely against its own tests. 'Merged and green' is never 'done' here. **Lower-stakes work: discriminating tests + an independent attempt to break it suffice.**"*
- **`:57` (§7)** — *"never ship into a priority domain without a reality check."*

Read §4's last sentence against FL-E1 + FL-E2. **The fast lane's substituted bar — a discriminating (two-sided) test plus an independent attempt to break it — is verbatim the charter's bar for *lower-stakes work*.** The charter grants that bar **conditionally**, and the condition is that the change is *not* in a priority domain. **FL-4 never tests the condition.** It tests §5(a) reversibility and §5(b) sensitivity, and stops.

And the exemplar is squarely inside the condition: the entire purpose of the containment wave is to convert an invisible 502 blob into a **named, human-actionable record** — that is *data people act on*, and `park.py:123` says so in the artifact itself: *"(acknowledged 200 -- no SendGrid retry; **a human should action this**)"*.

The proposal will answer that lane 1 ≠ lane 3, and §4-"done" lives in lane 3. **The answer does not close it**, because lane 3's enumerated blocks (§6: Blocker C, R-35, M-4, C-1) are *deploy* and *merge* blocks — **none of them is a reality check.** Once Blocker C is cured and R-35 lifted, a fast-lane change reaches production having met FL-E1+FL-E2 and nothing else. §4's reality check falls between the two lanes and is caught by neither. **That is a dropped clause with a live path through it.** §A-4(d) closes it.

*(Reasoned, not measured: I did not test whether an operator word has in practice been the instrument carrying §4's reality check on this arc. The structural gap stands regardless of what has been carrying it, because the predicate names no carrier.)*

---

## §6 UV-P LEDGER — none of the proposal's four discharged; three new

**Explicitly NOT inherited as discharged.** All four carry forward:

| # | proposal UV-P | status at my exit |
|---|---|---|
| 1 | LLM adapter default temperature ⇒ `missing_contact_name` non-determinism | **OPEN.** I did not read `autom8y-ai`/`autom8y-core` and ran no retry probe. Remains the reviewer's blocking question on the *change*; it is not a question about the *predicate*, so it is out of my scope but explicitly undischarged. |
| 2 | `merge-surface-sweep` is a REQUIRED context on branch protection | **OPEN AND WORSENED.** I ran no `gh api`. Measured: `.github/scripts/merge-surface-sweep.sh` **changed** between the proposal's read ref `cc88b75e` and current `origin/main` `883eb3bf`, so the premise is staler than when authored. |
| 3 | S-14 diff passes the suite / a two-sided test exists vs needs authoring | **OPEN, and now load-bearing.** G-1 makes the answer decisive: whichever it is, the test file is outside `src/`. |
| 4 | G-FL1 is a gate the operator will recognize | **OPEN.** Operator word only. This artifact does not substitute for it. |

**New, opened by this seat:**

- `[UV-P: the ≈52/day volume the exemplar moves between PIPELINE_TOTAL{status} buckets | METHOD: CloudWatch query on the three surfaces named in G-2 | REASON: carried from the PT-08 custody register via the dispatch; I ran no CloudWatch query and took no live AWS read. G-2's structural finding does not depend on the magnitude — it depends only on the movement being non-zero — but any claim about alarm-threshold proximity does.]`
- `[UV-P: whether the review channel ParkKind.REVIEW routes to has an attested human watcher | METHOD: read the Slack channel binding in EBI terraform + confirm an owner | REASON: G-4(a) shows the exemplar routes a population to a channel no other match_lead decline uses; park.py:123 makes a human the recovery floor. I did not resolve the channel or its watcher. If unwatched, the 200-ACK's recovery floor is nominal.]`
- `[UV-P: no closed-set guard for decline_class exists under a name my pattern did not cover | METHOD: read every module in EBI src/ that consumes decline_class | REASON: G-4(b)'s zero is taken against a named pattern set with a firing corpus control, but a guard under an unguessed identifier would evade it. The zero is bounded, not absolute.]`

---

## §7 ★ AMENDED CONJUNCT TEXT — §A

**Binding compliance note:** every amendment below changes the PREDICATE. **No exemplar is narrowed anywhere in this artifact.** Under §A the S-14 exemplar's status is genuinely re-opened — under A-2 and A-3 it must produce an alarm-input enumeration and a disclosure-delta reading it does not currently have, and under A-4(d) it may not qualify at all. **That is the correct direction: the predicate changed and the exemplar must re-run against it**, per §10's own rule that every widening re-runs both exemplars. H2's REFUSE verdict survives §A unchanged and is strengthened (A-4 adds two more limbs it fails).

### A-1 — FL-1 SURFACE (replaces FL-1; closes G-1 and §3)

> **FL-1 SURFACE** — every changed file lives under exactly one service's `src/` tree, **with one exception: test files under that same service's test tree are ADMITTED when and only when they exist solely to discharge FL-E1 for this diff.** No terraform, `.tfvars`, workflow, Dockerfile, dependency manifest, IAM, alarm, schema, allowlist or census file appears in the diff. **FL-1 is a necessary condition and never a sufficient one: it is a cheap first filter, and the proposal's own concession that file-location tests are gameable is binding — a policy artifact resident in `src/` is still a policy artifact, and FL-2′, FL-3′ and FL-4′ read the effect regardless of the address. No claim of the form "FL-3 refuses it anyway" may be made at class scope; it must be shown for the specific effect.**

### A-2 — FL-3 DIRECTION (replaces FL-3; closes G-2)

> **FL-3 DIRECTION** — the change's entire effect falls on a path that today produces **no durable record**, **no already-recorded outcome changes**, **and no derived surface takes the moved quantity as input.** The author MUST enumerate, by `file:line`, every alarm, metric filter, dashboard, SLO, deadman and downstream consumer keyed on the status, class, dimension or count the diff moves, and show each one either provably unaffected or explicitly re-based with the new operating point stated. **"No individual recorded outcome changes" DOES NOT SATISFY THIS CONJUNCT: a counter's SHAPE is itself a recorded outcome, and a detection surface that silently changes operating point is a changed outcome nobody recorded.** Per R-5, the non-recording claim must cite the locus that states it; per this clause, the alarm inventory must cite its loci too. **An empty enumeration is admissible only with a firing positive control proving the search would have found a surface had one existed.**

### A-3 — FL-4 FLOOR, limb (c) (adds to FL-4; closes G-3's disclosure half)

> **FL-4(c) DISCLOSURE** — the diff moves no field, record or population onto a surface with a **weaker redaction or narrower access posture** than the one it leaves. Where a service maintains distinct disclosure planes (e.g. a redacting structured-log plane and a non-redacting human-receipt plane), moving a population **across** those planes is a disclosure change and is REFUSED to the standard lane, **whether or not the destination is customer-facing.** The author must state the redaction delta explicitly; "the disclosure posture is unchanged **for that plane**" is not a finding that the population's posture is unchanged.

### A-4 — FL-4 FLOOR, limbs (b′) and (d) (amends FL-4; closes G-3's floor half and §5)

> **FL-4(b′) SENSITIVE LIST — BREADTH DECLARED.** FL-4(b) reads *"anything touching security/credentials"* in its **BROAD CHARTER FORM** (`CHARTER…:55`). **R-A8's narrowing of that limb to IDENTITY surfaces is FLAGGED-PROVISIONAL, its certification was REFUSED on lineage grounds, and it lapses to the broad reading absent lineage-disjoint re-consent. A PROVISIONAL narrowing MAY NOT be relied upon to ADMIT a change into the fast lane.** A provisional ruling may narrow what requires a word; it may never be the thing that lets a change skip one. If R-A8 is re-consented at a sitting convened outside session `f73c2e72`, this clause may be revisited by a fresh ruling — **not by reading.** Additionally, the credential-residence / read-route class that `RULING…2026-08-26:238-240` records as covered by **neither** R-A4's floor **nor** R-A8's in-gate list is, for fast-lane purposes only, treated as **IN GATE** — the lane does not inherit an acknowledged coverage hole.
>
> **FL-4(d) PRIORITY-DOMAIN GATE.** The diff clears **CHARTER §4 (`:54`) and §7 (`:57`)**, not only §5. If the change touches **money, customers, or data people act on**, it is a priority domain and **the fast lane does not apply** — §4 confines the "discriminating tests + an independent attempt to break it" bar (which is exactly FL-E1 + FL-E2) to **lower-stakes work by its own terms**, and §7 forbids shipping into a priority domain without a reality check. **The fast lane may not substitute the charter's lower-stakes bar for work the charter classes as priority-domain.** A change that creates a record a human is expected to action is data people act on.

### A-5 — FL-2 VOCABULARY (replaces FL-2; closes G-4)

> **FL-2 VOCABULARY** — the diff introduces **no new symbol AND no new value on any governed dimension.** Every identifier it uses is already imported in the file it edits and already declared in the service. **A "governed dimension" is any parameter whose value is consumed as: a metric dimension or label; a structured-log event field; a storage-key or namespace component; or a routing/destination selector.** Where the diff sets a value on a governed dimension, **the exact (value, selector) pair — not merely the call shape — must already appear at another site in the same file.** A new string literal on a governed dimension is a NEW OBSERVABLE CLASS, not an application of an existing rule: it mints a metric-dimension value no alarm covers and, where applicable, a storage namespace — both policy acts. **Choosing a different member of an existing enum on a routing dimension is likewise a new value and is REFUSED**, because the enum member, not the call, carries the policy. The per-file precedent requirement binds **per changed file** (curing §10's FR-3 by text rather than by reviewer disposition).

### A-6 — §3.1 and §10 corrections (textual, non-conjunct)

> **(i) STRIKE the claim that the conjuncts are *"checkable by reading the diff alone and nothing else"* (§3.1).** It is false on the proposal's own terms: §3.2 makes FL-3 checkable by *"the diff + the status/record locus"*, FL-2 by *"the diff + the edited file's imports"*, R-5 requires citing an external locus, and A-2 requires an alarm inventory. Replace with: *"checkable from the diff plus a bounded, enumerated set of loci which the author must cite."* The honesty matters — a false cheapness claim is how a gate gets applied without its reading.
>
> **(ii) REPLACE the widening rule's evidence test.** *"N≥3 … with zero incidents attributable to the lane assignment"* is **unfalsifiable**, because the lane's characteristic failure mode (A-2) manufactures "no incidents" as its own signature. Replace with: **"N≥3 fast-lane changes have landed AND, for each, a positive attestation that every derived surface enumerated under FL-3′ was re-observed post-landing at its stated new operating point."** Absence of an alarm is not evidence; a re-observed surface is. **A widening that admits H2 remains void on its face.**
>
> **(iii) WITHDRAW FR-1 from the false-refusal list.** Under A-5, a first `terminal_decline` in a file is a first routing choice for that file and is **correctly** refused. §10 should not propose curing it in v2.

---

## §8 THE ACID TEST

*"Would I be comfortable explaining this approval to the CEO after a breach?"*

For the predicate **as written**: no. I would be explaining that we adopted a gate which (a) could not admit any change at all because it forbade the test that justified it, (b) was blind to the movement of three alarms' inputs in a service that had already twice built custom detectors for that exact blindness, and (c) took its floor from a ruling whose certification had been refused.

For the predicate **as amended in §A**: yes. §A leaves the architecture the authoring seat built — four ANDed booleans, effect-not-address, no override, a REFUSE regression test that travels — and closes the four holes in conjunct text. The seat that authored this was right that the single lane is mis-shaped for the small change, and right that a two-sided test plus a disjoint reviewer is better aimed at the real hazard than a third operator word. It was also right to self-cap at MODERATE and ask for this review. **The wall is nearly load-bearing; it needs four courses of brick, not demolition.**

---

## §9 WHAT THIS REVIEW DOES NOT DO

- **It applies the predicate to nothing.** No merge, no deploy, no apply, no PR. This artifact is C-INERT.
- **It does not rule on whether S-14 is correct.** §4.3's determinism question is untouched and remains the reviewer-of-the-change's blocking question. I read no test and ran no test.
- **It takes no live AWS read.** Every alarm fact is from terraform at `origin/main`, not from CloudWatch. **Reasoned, not measured:** that the alarms as coded are the alarms as deployed. Blocker C — production serving an out-of-band image while tfvars pins another — is itself evidence that coded state and live state diverge on this service, so this caveat is not pro-forma.
- **It does not discharge M-3.** I concur with §7's fairness clause: M-3 afflicts both lanes identically and using it against the fast lane would be a category error. §A adds nothing there.
- **It does not re-run `merge-surface-sweep`, read branch protection, or resolve ADIO's identity.**
- **It never read the autom8y working tree.** Every autom8y fact is `git show origin/main:<path>` at `883eb3bf`.

## §10 O-3 COMPLIANCE — per-PR path fence, deny-list READ LIVE

O-3 requires asserting this sprint's changed paths against `.github/workflows/test.yml`'s deny-list read live, with a firing positive control.

**Deny-list read live** from `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.github/workflows/test.yml:29-35` — `paths-ignore` under `push`:
`.ledge/**` · `.sos/**` · `.claude/**` · `.gemini/**` · `.knossos/**` · `.know/**.md`

**Assertion, with controls that FIRED:**

| path | matcher result | matched pattern |
|---|---|---|
| `.ledge/reviews/REVIEW-gfl1-fast-lane-predicate-disjoint-2026-09-08.md` *(this sprint's ONLY write)* | **IGNORED** | `.ledge/**` |
| `src/autom8y_asana/handler.py` | **TRIGGERS** ← positive control FIRED | no-match |
| `.github/workflows/test.yml` | **TRIGGERS** ← positive control 2 FIRED | no-match |
| `.know/telos/name-the-client.md` | IGNORED | `.know/**.md` |
| `.know/data/x.json` | **TRIGGERS** | no-match |

Both positive controls fired, varying the dimension asserted over (*does this matcher ever classify a path as triggering?*). The zero is **TAKEN**. This sprint's sole changed path is denied from triggering the workflow.

**★ Incidental deny-list finding, reported per O-3's own warning that unlisted paths still deploy:** `.know/**.md` is **`.md`-restricted**, so a non-`.md` file under `.know/` (e.g. `.know/data/x.json`) **TRIGGERS** while its `.md` sibling does not. The other five patterns are extension-agnostic. This is an asymmetry in the live deny-list, not a finding about G-FL1. **I wrote no such file.**

---

## §11 ATTESTATION

| # | claim | method | anchor (ref-explicit) | marker (verbatim) |
|---|---|---|---|---|
| 1 | Tests live outside `src/` ⇒ G-1 | git-ls-tree, zero + corpus control | autom8y `origin/main` `services/email-booking-intake` | `services/email-booking-intake/tests/__init__.py` |
| 2 | 5xx burst alarm keyed on the moved quantity | file-read | `origin/main:…/op1_watch_alarms.tf:104-112` | `alarm_name = "autom8-email-booking-intake-apigw-5xx-burst"`, `threshold = 3` |
| 3 | 5xx sustained alarm | file-read | `origin/main:…/op1_watch_alarms.tf:131-139` | `metric_name = "5xx"`, `evaluation_periods = 3` |
| 4 | `status=failed` metric filter | file-read | `origin/main:…/semantic_alarms.tf:133` | `pattern = "{ $.event = \"pipeline_completed\" && $.status = \"failed\" }"` |
| 5 | `status=failed` IS the 502 class | file-read | `origin/main:…/semantic_alarms.tf:124` | `status=failed`` is the transient class (-> HTTP 502 -> SendGrid retry)` |
| 6 | 200 hides from the 5xx alarm — realized class #1 | file-read | `origin/main:…/contente_stage_failure_detector.tf:24` | `the trace returns HTTP 200, so no 5xx alarm sees it` |
| 7 | 200 hides from the 5xx alarm — realized class #2 | file-read | `origin/main:…/extraction_disagreement_detector.tf:19-21` | `no exception is raised, so the trace returns HTTP 200 and no 5xx alarm` |
| 8 | Slack plane posts raw subject + mailbox | file-read | `origin/main:…/park.py:117-123` | `lines.append(f"subject: {ctx.subject}")` |
| 9 | Two-plane redaction split stated in-code | file-read | `origin/main:…/park.py:110-113` | `the ``redact_uuid`` discipline is a log-plane rule, not a Slack-plane one` |
| 10 | Mailbox contains clinic identity | file-read | `origin/main:…/park.py:96-97` | `it LITERALLY CONTAINS the clinic identity` |
| 11 | `ParkKind` selects the channel | file-read | `origin/main:…/decline.py:32-46` | `routed to the review channel` |
| 12 | All 5 in-file sites are OPS, none REVIEW | bash-probe + corpus control | `origin/main:…/match_lead.py:549,574,594,686,913` | `TerminalDecline("name_evidence_organic", ParkKind.OPS),` |
| 13 | `decline_class` ⇒ metric dimension | file-read | `origin/main:…/decline.py:73-74` | `PIPELINE_TOTAL{status="declined", failure_class}` |
| 14 | `decline_class` ⇒ DDB namespace | file-read | `origin/main:…/park.py:285` | `"ns": f"decline\|{decline.decline_class}"` |
| 15 | No closed set for `decline_class` | bash-probe, **zero + firing corpus control** | `origin/main` EBI `src/` | zero hits exit 1; control `BELOW_BAR_DECLINE_CLASS` = 3 hits |
| 16 | CHARTER §4 / §5 / §7 verbatim | file-read | asana `CHARTER…2026-07-30.md:54,55,57` | `Autonomous work stops at TWO gates, nothing else:` |
| 17 | R-A4 floor verbatim | file-read | asana `RULING…2026-08-26.md:85-88` | `No wording reaches these**, in any grant, at any tier` |
| 18 | R-A8 narrows the credential limb, FLAGGED-PROVISIONAL | file-read | asana `RULING…2026-08-26.md:131-139` | `specializes to IDENTITY surfaces`; `failing which it lapses to the broad reading` |
| 19 | R-A8 coverage gap (credential residence/read-route) | file-read | asana `RULING…2026-08-26.md:238-240` | `is in neither R-A4's floor nor` |
| 20 | Exemplar raise site unchanged at current `origin/main` | file-read | `origin/main:…/match_lead.py:724-728` | `failure_kind=LeadMatchError.KIND_MISSING_CONTACT_NAME,` |
| 21 | Read-surface drift; `services/` zero TAKEN | bash-probe, zero + firing control | `git diff cc88b75e..883eb3bf` | 0 files in `services/…`; 9 repo-wide; control grep exit 0, 2 hits |
| 22 | O-3 deny-list live + controls fired | file-read + bash-probe | asana `.github/workflows/test.yml:29-35` | `paths-ignore:` / `- '.ledge/**'` |

**Coverage matrix — review focus areas exercised:**

| area | depth | notes |
|---|---|---|
| Authorization / access control | **exercised** | G-3: FL-4's floor is a function of a provisional ruling; R-A8 breadth undeclared |
| Data handling / PII exposure | **exercised — finding** | G-3: cross-plane disclosure, `park.py:110-123` |
| Error handling / info disclosure | **exercised — finding** | G-2: 200-ACK suppresses three detection surfaces; two realized precedents in-service |
| Input validation | **exercised — finding** | G-4(b): unbounded `decline_class` ⇒ metric-dimension + DDB-namespace mint |
| Authentication / crypto | **not applicable** | no auth, token, or crypto surface in the predicate or exemplar |
| Governance-artifact fidelity | **exercised — finding** | §5: FL-4 restates §5 only; §4 and §7 dropped |

**Evidence grade: `[STRUCTURAL | STRONG]` for G-1, G-2, G-4** — each rests on direct inspection at an explicit ref with a firing positive control, and G-2 additionally on two independent in-codebase statements of the same failure class. **`[STRUCTURAL | MODERATE]` for G-3 and §5** — the code and charter facts are measured, but whether a Slack ops receipt is "security/credentials" under the broad reading, and whether the exemplar is a priority domain under §4, are readings of governance text, not measurements. **Not self-capped:** this seat is rite-disjoint from the authoring seat and re-derived every fact rather than inheriting it.

**VERDICT: CLEAR WITH AMENDMENT.** Ratify G-FL1 with §A (A-1 … A-6) substituted. Do not ratify as written.
