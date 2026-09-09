# PROPOSAL — the blast-radius predicate and the fast lane

- **initiative:** `name-the-zero` · **WAVE 2** (the containment wave) · **S-13**
- **posture: GOVERNANCE.** Declared explicitly. Posture is **per workstream** and is **NEVER inherited by proximity** (CUSTODY register `:8`). S-14 beside it is *remediation*; S-15 is *observability*. Neither posture reaches this artifact and this artifact's posture reaches neither of them.
- **gate served:** **G-FL1** — new, **unspoken**. This artifact is the receipt G-FL1 would consume; it is not the word.
- **predicate legs:** serves **NEITHER**. This artifact moves `shipped:` and `verified_realized:` **zero inches** and does not touch `.know/telos/name-the-zero.md`.
- **status:** AUTHORED. No PR, no push, no merge, no deploy. The main thread holds all pushes under a four-way fence.
- **seat:** architect (10x-dev, co-seated) · **self-attestation capped MODERATE** · **disjoint reviewer: `security-reviewer`** (a wall reviewed by the seat building behind it is asserted, not proven).
- **instant:** 2026-09-08 · **read surface:** autom8y **object DB at `origin/main` = `cc88b75e`** only. The local autom8y checkout is on `fix/wss-wildcard-scope-bypass-closure` @ `29e59e81` with 351 dirty entries — **STALE-TREE TRAP ACTIVE**; its working tree was never read.

---

## §1 WHY THIS EXISTS — the finding, carried verbatim

A visionary consult adjudicated the wave's central tension and found ONE structural defect: **single-lane governance.** There is exactly one lane through this arc and it is priced at the maximum blast radius, so a one-argument change that touches a path which currently *records nothing* is queued behind the same triple operator word as a four-function container image event with a `terraform plan` nobody has run. Its words: *"A gate architecture with no fast lane is not rigorous. It is uniformly expensive, which means it is expensive in exactly the cases where speed is the value."*

**One addition, from this seat, that sharpens the finding rather than softening it.** The uniform gate is not only expensive — it is **mis-shaped for the risk actually present in the small change.** The operator word is an instrument for *blast radius*. The live hazard in S-14 is a **wrong determinism premise** (§4.3): whether `missing_contact_name` recurs identically on retry. **No number of operator words can detect a temperature default.** A two-sided test and a rite-disjoint reviewer can. So the single lane is simultaneously too expensive for the small change *and too weak at the thing that would actually go wrong in it*. That is the argument for a second lane that does not reduce to "we would like to go faster."

---

## §2 WHAT IS ACTUALLY BEING FIXED — three things that got fused

The arc has been treating one decision where there are three. The defect is the fusion, not the strictness.

| # | Decision | Owner | Instrument |
|---|---|---|---|
| **1** | **Which evidence bar does this change face?** | this predicate | the four conjuncts below |
| **2** | **Is the change right?** | the reviewer | verdict on the merits |
| **3** | **May it merge and deploy?** | the standing blocks | Blocker C · R-35 · M-4 · C-1 image-event law |

Today (1) is decided by (3): because the *hardest* landing on the arc needs a triple word, *every* change is priced at a triple word. **Unfusing (1) from (3) is the whole proposal.** Nothing in this artifact touches (3) — every block that stands today stands unchanged after it (§6).

**This is a READING of ratified law, not a request for a new grant.** `CHARTER-decision-space-of-record-2026-07-30.md:55` (verbatim core, byte-verified region): *"Autonomous work stops at **TWO gates, nothing else**: (a) **irreversibility** — anything you can't cheaply take back; (b) **a short sensitive list regardless of reversibility** — anything a customer sees, anything touching security/credentials, anything that spends money or makes an external commitment. **Everything else** — INCLUDING reversible decisions that set patterns others will copy — **runs autonomously, no per-step check-in.**"

The charter's **"nothing else"** is a **ceiling on the gate count**. The arc has been operating a de-facto third gate — a uniform operator word — applied to changes the charter's own §5 places outside both of its gates. **The fast lane is not new authority. It is the charter's §5 residue, which this arc has been declining to use, given a written test so the use is checkable.** What licenses it is `:56`: *"independent verification (something actively trying to break the work before it is real) AND reversibility. **Autonomy is void where independent verification did not happen.**"* That is a HARD RULE, and it is why the fast lane drops the operator word but **cannot** drop the reviewer (§8).

---

## §3 THE PREDICATE

### §3.1 One paragraph a person can apply

> **A change enters the FAST LANE if and only if all four conjuncts hold, each checkable by reading the diff alone and nothing else: (FL-1 SURFACE) every changed file lives under exactly one service's `src/` tree — no terraform, no `.tfvars`, no workflow, no Dockerfile, no dependency manifest, no IAM, no alarm, no schema, no allowlist or census file appears in the diff; (FL-2 VOCABULARY) the diff introduces no new symbol — every identifier it uses is already imported in the file it edits, already declared in the service, and the idiom it applies already appears at another site in that same file, so the change is the *application of an existing rule* rather than the *authoring of a new one*; (FL-3 DIRECTION) the change's entire effect falls on a path that today produces **no durable record**, and **no already-recorded outcome changes**; (FL-4 FLOOR) the diff crosses neither CHARTER §5 gate — it is (a) cheaply revertible by one revert commit leaving behind no migration, no backfill and no external state, and (b) touches nothing on the sensitive list (anything a customer sees, anything touching security/credentials, anything that spends money or makes an external commitment) and nothing on R-A4's never-liftable floor (credential-rotation execution, customer-visible outbound acts, business-of-record identity mints). Any one conjunct failing sends the change to the standard lane — the conjuncts are ANDed and there is no override. Passing all four buys exactly one thing: the evidence bar for authoring-and-review becomes one two-sided test plus one rite-disjoint reviewer, instead of a triple operator word. It buys no merge, no deploy, and no claim whatever about correctness.**

### §3.2 The conjuncts, with what each is for

| id | conjunct | the failure it exists to catch | checkable by |
|---|---|---|---|
| **FL-1** | **SURFACE** — changed files all under one service's `src/` | config/infra changes wearing a code change's clothes | `git diff --name-only` |
| **FL-2** | **VOCABULARY** — no new symbol; the idiom already appears in the same file | a *new policy* smuggled in as a *small edit* | reading the diff + the edited file's imports |
| **FL-3** | **DIRECTION** — effect falls wholly on a currently-unrecorded path; nothing already-recorded changes | a change that silently alters behaviour someone is already relying on | reading the diff + the status/record locus it lands on |
| **FL-4** | **FLOOR** — clears CHARTER §5(a) and §5(b) and R-A4 | the two ratified gates, restated so the lane cannot route around them | reading the diff against the charter |

**Why FL-3 is the load-bearing one.** FL-1 is a file-extension test and file-extension tests are gameable: move the allowlist into `src/` and FL-1 admits it. FL-3 refuses it anyway, on substance, because flipping an office out of the dry-run keyspace **changes an outcome that is already recorded**. A predicate whose refusals all rest on one clause is a predicate with one bug between it and a bad landing. **H2 fails three of the four independently** (§5) — that redundancy is deliberate.

### §3.3 What the predicate is NOT

- **Not a severity scale.** There is no score, no weighting, no threshold. Multi-dimensional scores invite the arithmetic that produces a pass; four ANDed booleans do not.
- **Not a claim about the image.** Written entirely about **the diff**. See §7 — this is binding, not stylistic.
- **Not a correctness test.** A change can pass all four conjuncts and be wrong. S-14 is exactly such a case (§4.3).
- **Not an override.** No conjunct may be waived, argued around, or satisfied "in spirit". Failing one is not an obstacle to remove; it is the lane assignment.

---

## §4 ADMIT EXEMPLAR — S-14

### §4.1 The change

Add `terminal_decline=TerminalDecline("missing_contact_name", ParkKind.REVIEW)` to the raise site at `services/email-booking-intake/src/email_booking_intake/pipeline/stages/match_lead.py:725-728`, which today raises **unmarked**:

```python
    if not ctx.contact_name:
        raise LeadMatchError(
            "No contact_name available for lead matching",
            failure_kind=LeadMatchError.KIND_MISSING_CONTACT_NAME,
        )
```
*(verbatim, autom8y `origin/main` @ `cc88b75e`, `match_lead.py:724-728`)*

### §4.2 Verdict: **ADMIT**, and the clause that produced each half

| conjunct | verdict | the reading that produced it (all own-hands at `origin/main`) |
|---|---|---|
| **FL-1 SURFACE** | **PASS** | One file, `…/src/email_booking_intake/pipeline/stages/match_lead.py`. No tf, no tfvars, no workflow, no Dockerfile, no `pyproject.toml`. |
| **FL-2 VOCABULARY** | **PASS, with five precedents** | `ParkKind` and `TerminalDecline` are **already imported** at `match_lead.py:71-74`. `LeadMatchError.__init__` **already accepts** `terminal_decline` and forwards it (`errors.py:133-141`). The constant `KIND_MISSING_CONTACT_NAME = "missing_contact_name"` is **already declared** (`errors.py:127`). The identical idiom **already appears five times in the same file**: `:549`, `:574`, `:594`, `:686`, `:913`. **Zero new symbols, zero new imports, zero new files.** |
| **FL-3 DIRECTION** | **PASS** | The site's entire population lands FAILED→502, and `handler.py:1157` states the record consequence verbatim: *"a **FAILED/502 records NOTHING** and its redelivery correctly re-runs the full pipeline"*. The DANGER BOUNDARY at `handler.py:850-861` confirms the mapping is total: *"ONLY FAILED returns 502 … **Every unmarked failure lands here as FAILED -> 502 by construction**"*. Nothing on the 200 path (COMPLETED / SHORT_CIRCUITED / DECLINED, `handler.py:862-867`) is touched. **The change moves an unrecorded outcome into the recorded set and changes no recorded outcome** — the consult's *"a path which currently records nothing"*, exactly. |
| **FL-4 FLOOR** | **PASS**, boundary named | **(a) revertible:** one revert commit; no migration, no backfill, no external state. **(b) sensitive list:** no outbound act is added; nothing touches credentials; nothing spends money. **The boundary, named rather than waived:** the diff *does* change one externally-observable byte — the HTTP status on the **response to an inbound webhook** (502→200 for this population). Ruled **inside** the fast lane because CHARTER §5(b) and R-A4(2) both govern **outbound acts** — things we *initiate* toward a party — not the status code on a reply to a call made to us. The reviewer, not this predicate, owns whether that status is the *right* one. |

**Corroborating (not conjunct-bearing): the change is the application of a rule the codebase has already ratified.** The sibling two files away raises the same *shape* of condition and does mark it, with a comment reasoning explicitly about not 200-ACKing a retryable failure — `extract_fields.py:419-429`: *"THIS raise site ONLY: the invalid-JSON / truncation / LLM-call-failed sites above raise FieldExtractionError WITHOUT a marker and STAY 5xx-transient … **sweeping truncation into no-appt-dt would 200-ACK a retryable extraction failure and silently lose the booking.**"* And the **kind axis is already correct** at the S-14 site (`failure_kind=KIND_MISSING_CONTACT_NAME`, classified `other` — the LOUD label — per `errors.py:92-93`). **Kind and disposition are two axes.** S-14 sets the second on a site whose first is already set. That is a disposition-axis edit, which is the narrowest kind of change this service admits.

### §4.3 ★ The substantive question the fast lane ADMITS BUT DOES NOT DECIDE

`extract_fields.py:419-425`'s rule is *mark only the deterministic-terminal site; leave the retryable ones unmarked.* Applying it to S-14 requires that `missing_contact_name` **recur identically on retry**. TRIAGE §10 argues it does — control reaches `match_lead` only because `extract_fields` succeeded. **That premise is not established, and this seat found a live reason to doubt it:**

`ctx.contact_name` is produced by an LLM extraction. **The EBI source sets no temperature anywhere.** Own-hands zero over all 324 files at `origin/main` under `services/email-booking-intake`: `temperature` appears **only** in `pyproject.toml:84` (a comment) and `scripts/_stubs.py:105,123,134` (test stubs) — **zero occurrences in `src/`**. Positive control on the same loop: `contact_name` fires in **9 distinct `src/` files**, so the probe and the path filter both work. And `pyproject.toml:84` states the adapter's behaviour: *"the `temperature` kwarg **the adapter always sends**"* — a value EBI never chooses. **If that default is non-zero, a retry can yield a contact name where the first attempt yielded none, and marking the site terminal would 200-ACK a retryable failure — precisely the silent loss `extract_fields.py:424-425` names.**

**This is the reviewer's blocking question, and it is the argument for the lane rather than against it.** A triple operator word does not surface a temperature default. A two-sided test plus a rite-disjoint reviewer is shaped to. **The fast lane assigns the evidence bar; it does not certify the change.**

---

## §5 REFUSE EXEMPLAR — H2 (the ADIO allowlist widening)

### §5.1 The change

Add ADIO's office GUID to `contente_booking_live_allowlist` at `terraform/services/email-booking-intake/environments/production.tfvars:160`, parsed at `config.py:500` (`parse_contente_booking_live_allowlist`). Own-hands delta at `origin/main`: the list holds **42** GUIDs; ADIO's `e3267756…` is **absent** (grep exit 1) while Salkin `6f22301a-4c51-4282-bf86-a64108e644ad` and Sand Lake `1b271a63-33ff-4135-a92d-f1ef0eeea062` are **present** (grep exit 0 — the two positive controls that make the ADIO zero a taken zero). **H2 is 42 → 43.**

### §5.2 Verdict: **REFUSE** — on three independent conjuncts

| conjunct | verdict | the clause that produced it |
|---|---|---|
| **FL-1 SURFACE** | **★ FAIL** | The changed file is `terraform/services/email-booking-intake/environments/production.tfvars`. FL-1 names `.tfvars` and "allowlist or census file" explicitly. **Refused at the first conjunct, before any argument about the office is heard.** |
| **FL-2 VOCABULARY** | pass (and this is why FL-1 alone is not enough) | Adding a GUID to a CSV introduces no new symbol. **H2 would survive a vocabulary-only predicate** — which is exactly the gap FL-1/FL-3/FL-4 exist to close. |
| **FL-3 DIRECTION** | **★ FAIL** | The effect does **not** fall on an unrecorded path. An off-allowlist office's bookings are **recorded today** — demoted to the dry_run keyspace (TRIAGE §11). H2 **changes an already-recorded outcome**: the same booking stops being a dry-run row and becomes a live outbound POST. FL-3's second half fails outright. |
| **FL-4 FLOOR** | **★ FAIL — absolutely** | `production.tfvars:154` states what the variable is, verbatim: *"**This is the ONE policy flip that turns the 17 activated offices' live contente POST on.**"* A live contente POST is a **customer-visible outbound act** — R-A4(2) of `RULING-decision-space-amendments-2026-08-26.md:85-88`: *"**No wording reaches these**, in any grant, at any tier: (1) credential-rotation **EXECUTION**; (2) customer-visible **outbound** acts; (3) business-of-record **identity mints**. The floor sits **above both tiers** — ADMIN-GRADE does not approach it, and **no grant phrasing, however explicit, lifts it**."* It fails CHARTER §5(b) ("anything a customer sees") on the same facts. |

**And the identity is not confirmed.** TRIAGE §11, verbatim: *"Shannon's card says 'ADIO **Corrective** Chiropractic'; the office resolving is 'ADIO **Chiropractic Kennesaw**'. Probably the same account, possibly a second location. **Confirm before acting on the allowlist finding.**"* Turning live outbound POSTs on for an office whose identity is *probably* right is the shape of act the never-confidently-wrong floor (CHARTER `:52`) forbids. H2 requires an operator word **and** prior identity confirmation — the predicate's refusal and the standing requirement agree.

### §5.3 The self-check the task demanded

**The predicate refuses H2 by its own written terms, three times over, and the refusals do not depend on each other.** Delete FL-1 and FL-3 refuses it. Delete FL-1 and FL-3 both and FL-4 refuses it, on a floor no grant can lift. There is no reading of the four conjuncts under which H2 is admitted, and none under which the file could be relocated into `src/` to sneak past — FL-3 and FL-4 read the *effect*, not the *path*.

---

## §6 WHAT THE FAST LANE BUYS — and the four things it does not

**The fast lane buys the RIGHT to land small things. It does NOT buy the ability to land any particular one.** Stated so it cannot be misread:

1. **It does not buy the deploy — and this is not theoretical.** Own-hands at `origin/main`: `service-deploy-dispatch.yml:26-32` triggers on `push: branches:[main] paths:['services/**']` plus `workflow_dispatch`, **never** on `pull_request`; it calls `service-deploy-lambda.yml` at `:270`; that workflow runs **`terraform apply -input=false -auto-approve tfplan` at `:304`**. So **opening a PR deploys nothing** (CUSTODY `:10`, re-verified here), and **merging a `services/**` change to main fires a terraform apply on the EBI service.** S-14 is a `services/**` change. Its merge is therefore a deploy act, and everything in item 2 applies to it.

2. **★ BLOCKER C is INDEPENDENT of R-35 and blocks EVERY intake deploy from EVERY lane.** R-35 is a *ruling* — the EBI freeze, liftable in principle by a word. **Blocker C is a state of the world, and lifting R-35 does not cure it.** Production's intake serves `…@sha256:76c21a00…` from an out-of-band hand-deploy (`salkin-safe-routing-20260905-90e0aa5a4937`, LastModified 2026-09-05T16:31:56Z), while `production.tfvars` still pins `image_tag = "67d89d7"` and reconcile + nudge still serve `:67d89d7` (CUSTODY fence row; CHARGE ★BLOCKER C). Per that finding's consequence (2), **any apply on the service — S-11's Apply A, and equally a fast-lane S-14 merge — rolls the intake back to `67d89d7` and silently erases an uncertified change**. **No lane assignment reaches this. The fast lane does not touch it, does not weaken it, and does not create an exception to it.**

3. **It does not buy the merge.** `merge-surface-sweep` is a **NEW ARMED REQUIRED CHECK** (CHARGE Addendum L, M-4) and the CUSTODY register records it **RED with 3 hits** against `origin/main...origin/assembly/name-the-zero`, two-sided (self-test positive control 8/8, clean-range control exit 0). A fast-lane change faces every required check a slow-lane change faces. **A RED check is a finding, not an obstacle to remove.**

4. **It does not buy correctness.** §4.3.

**Nor does it touch the C-1 image-event law.** One image event per envelope; bundling is REFUSAL; folding a cure into #1941 is FORBIDDEN (CUSTODY `:9`). A fast-lane change is still an image event and still consumes an envelope. **The lane is cheaper in evidence, not in envelopes.**

---

## §7 ★ M-3 — THE RESIDUAL THIS PREDICATE DOES NOT CLOSE

**BINDING: the fast lane may NOT claim "provably cannot make things worse."** It makes no such claim, and here is the verified reason it cannot.

**Verified own-hands at `origin/main`, not inherited from the CHARGE:**

1. **No lockfile in the EBI build context.** `git ls-tree -r origin/main -- services/email-booking-intake` filtered for `uv.lock|requirements*.txt|poetry.lock|Pipfile.lock|constraints*.txt` → **zero hits, exit 1**. **Positive control A:** the identical pattern over the whole tree at the same ref → **6 hits** (`uv.lock`, `sdks/python/autom8y-meta/uv.lock`, and four under `tools/`), so the pattern finds lockfiles when they exist. **Positive control B:** the path filter is not empty — the EBI tree holds **324 files**. **The zero is TAKEN.**
2. **Resolution happens at build time.** `services/email-booking-intake/Dockerfile:53` and `:59` run `uv pip compile pyproject.toml --output-file /tmp/requirements.txt --generate-hashes`. The build context copies only `pyproject.toml README.md` (`:44`) and `src/` (`:75`). **The requirements file is generated inside the build, not committed.**
3. **The floor is open-ended and the package moved.** `pyproject.toml:24` = `"autom8y-log>=0.5.6"`, no upper bound. `sdks/python/autom8y-log/pyproject.toml` at `origin/main` = **`version = "0.9.0"`**; the release commit **`695f3dea` ("chore(log): release 0.9.0", 2026-09-07 14:55:56 -0400)** shows `-version = "0.8.0"` / `+version = "0.9.0"`. **The movement is 0.8.0 → 0.9.0 and it happened YESTERDAY** — after `b9bbfadc` was certified on 2026-09-05.

**Therefore: identical build context ≠ identical dependency closure.** Two builds of the same commit, minutes apart, can ship different code.

**Two facts this seat found that make M-3 sharper than the CHARGE states it:**

- **★ The channel has already caused a production outage, and the codebase says so in its own words.** `pyproject.toml:82-87`, verbatim: *"Direct cap, belt-and-suspenders with autom8y-ai's own <1: **this image resolves at BUILD time (no lockfile)**, and anthropic 1.x rejects the `temperature` kwarg the adapter always sends — **the 2026-08-23..27 intake outage class.**"* M-3 is **not a hypothetical residual. It is a realized outage class with a known blast pattern**, cured once, reactively, on one dependency.
- **★ The cure covers 2 of 13 direct dependencies.** Parsed own-hands from the `[project] dependencies` array (`pyproject.toml:21-100`, 13 requirement strings): **2 capped** — `autom8y-core[testing]>=4.19.0,<5.0.0` (`:78`) and `anthropic>=0.40.0,<1` (`:87`) — **exactly the two that already caused incidents**. **11 uncapped**, including the `autom8y-log>=0.5.6` that moved yesterday. **Eleven channels remain open in the same shape as the one that took the intake down for five days.**

**What this means for the predicate, stated as a rule:**

> **The predicate governs THE DIFF. The image is a different object with its own provenance, and no lane — fast or slow — may claim the image it reasoned about is the image that ships.** A fast-lane verdict is a verdict on a diff. It is never a verdict on a deployment.

**And a fairness clause, so M-3 is not misused.** M-3 afflicts the standard lane **identically** — a triple operator word closes it no better than a two-sided test does. **M-3 is not an argument against the fast lane; using it as one would be a category error.** What it *is*: the reason the fast lane must never let its cheapness be read as a safety claim. **The predicate does not close M-3, does not narrow M-3, and its correct disposition is a lockfile or a capped floor set — a separate change, in a different workstream, that FL-1 refuses on sight.**

---

## §8 THE EVIDENCE BAR THE FAST LANE SUBSTITUTES

Replacing a triple operator word with three requirements that are cheaper to produce and better aimed:

| id | requirement | why it is not droppable |
|---|---|---|
| **FL-E1** | **A two-sided test.** It must bite on the defect **and** pass on the no-defect variant. A one-sided green is not a receipt. | The fleet's discriminating-canary doctrine. A test that only proves the new path works cannot show the old path was broken. |
| **FL-E2** | **One rite-disjoint reviewer**, adversarially aimed. | **CHARTER `:56` is a HARD RULE**: *"Autonomy is void where independent verification did not happen."* This is the charter's own line and it is why the fast lane can drop the operator word but not the reviewer. |
| **FL-E3** | **The residual named in the change's own receipt** — at minimum M-3, plus any premise the diff rests on that the diff does not prove (for S-14: the determinism of `missing_contact_name`, §4.3). | CHARTER `:53`: *"ship it and **write down the known gaps**"*; `:52`: **NEVER CONFIDENTLY WRONG.** |

**What is dropped, precisely:** the triple operator word for *lane 1 (evidence bar)* only. **Nothing is dropped from lane 3.** Every standing block in §6 applies unchanged.

---

## §9 ALTERNATIVES CONSIDERED

Four genuinely different decompositions were evaluated. Each has a real advantage over the selected option; none is a strawman.

**ALT-A — measured-impact predicate.** Classify by the change's measured production effect (e.g. "affects fewer than N requests/day"). *Genuinely different:* a runtime/telemetry predicate rather than a diff predicate. **Advantage over selected:** it measures the construct "blast radius" *directly*, where the selected option measures a proxy — and P-07 of the assessment methodology is explicit that proxies require their own criterion validity. **Rejected because it is circular here:** TRIAGE §3 establishes that this plane **cannot name whose booking it was** (a successful booking logs no office, no business, no lead; a `malformed_business_guid` decline redacts the GUID). The measurement substrate that would ground ALT-A **is the thing this initiative exists to build**. A predicate that depends on the initiative's own deliverable cannot gate the initiative's own changes.

**ALT-B — reviewer-count tiering, no written test.** Keep one lane; scale reviewer count to a subjective severity call at dispatch. *Genuinely different:* no predicate at all — discretion at the point of use. **Advantage over selected:** zero authoring cost, and it adapts to novel cases a written predicate cannot foresee (see §10's known false-refusals, which ALT-B would not produce). **Rejected because it is the status quo with extra steps.** Unwritten discretion is what produced uniform single-lane pricing in the first place: with no written test, **nobody can be shown to have applied it wrongly**, so the safe play is always the maximum, and the maximum is what we have.

**ALT-C — path allowlist.** Enumerate the files that may go fast (`match_lead.py`, `extract_fields.py`, …). *Genuinely different decomposition:* enumeration instead of predicate. **Advantage over selected:** trivially checkable, zero ambiguity, zero judgment, and immune to the FL-2 boundary disputes §10 anticipates. **Rejected on two grounds:** (i) the allowlist is itself a governance artifact requiring a word to amend, so it **re-creates the bottleneck one level up** — the first change to a non-listed file needs the triple word to *add the file*; (ii) it is blind to FL-3 and FL-4, so a customer-visible change landing in an allowlisted file is admitted. **It gets the cheapness and loses the safety.**

**ALT-D — SELECTED: diff-shape predicate, four ANDed conjuncts.** Chosen because it is checkable at authoring time (unlike ALT-A), written and therefore falsifiable and auditable (unlike ALT-B), and reads the change's *effect* rather than its *address* (unlike ALT-C). Its cost is §10.

---

## §10 DELIBERATE UNDER-INCLUSION, AND THE WIDENING RULE

**This predicate is deliberately too narrow at v1.** An over-inclusive fast lane is the failure mode that kills fast lanes: one bad landing and the lane is revoked entirely, leaving the arc back at single-lane pricing with a scar attached. Under-inclusion costs speed on some changes; over-inclusion costs the lane.

**Known false-refusals — changes of the same class that v1 wrongly sends to the standard lane:**

- **FR-1.** Adding a first `terminal_decline` at a raise site in a file that has **no** existing `terminal_decline` site (e.g. a first mark in `resolve_office.py`). Identical in class to S-14; **FL-2 refuses it** for want of an in-file precedent.
- **FR-2.** A pure test-only diff under `tests/` — **FL-1 refuses it** (not under `src/`), though its blast radius is nil.
- **FR-3.** A same-class change spanning two raise sites in two files of one service — **FL-1 as written permits it** (one service's `src/`), but the *spirit* of "one site" is strained; a reviewer should read FL-2's per-file precedent requirement as binding per changed file.

**Widening rule (so v2 is earned, not argued):** **v1 may be widened only after N≥3 fast-lane changes have landed with zero incidents attributable to the lane assignment**, and each widening must name the false-refusal it cures and re-run **both** exemplars in this artifact. **A widening that admits H2 is void on its face.** H2's REFUSE verdict is this predicate's regression test and it travels with every future revision.

---

## §11 RISK AND REVERSIBILITY

**Reversibility of the lane itself: TWO-WAY DOOR.** The fast lane is a reading of ratified law, revocable by one word; revoking it returns the arc to single-lane pricing with nothing to unwind. **But changes landed under it are not un-landed by revoking it** — which is precisely why **FL-4(a) requires each admitted change to be cheaply revertible on its own terms**. The lane's reversibility and its landings' reversibility are separate properties and the predicate carries the second explicitly.

| # | risk | mitigation | residual |
|---|---|---|---|
| R-1 | The lane becomes a **precedent for widening by analogy** — "S-14 went fast, so this can too". | FL-2's in-file-precedent requirement + §10's earned widening rule + R-A4's floor above every tier. | **Real.** R-A3 (`:78-79`) already refuses widening by analogy; this is one more surface where that must hold. |
| R-2 | A change **passes all four conjuncts and is wrong** (S-14's own determinism question). | FL-E1 two-sided test + FL-E2 rite-disjoint reviewer. **The predicate never claimed to catch this** — §2 decision (2) is a different decision with a different owner. | **Accepted and named.** This is the cost of unfusing (1) from (2). |
| R-3 | The lane is read as **weakening a standing block**. | §6, four numbered denials; §7's binding rule; this artifact opens no exception to Blocker C, R-35, M-4 or C-1. | Mitigated by construction — the artifact grants nothing in lane 3. |
| R-4 | **M-3** — a fast-lane diff ships in an image whose closure nobody resolved. | None available here. Named, quantified (11/13 uncapped), and **explicitly not closed** (§7). | **OPEN. Correct disposition is a lockfile or a capped floor set — a separate change that FL-1 refuses on sight.** |
| R-5 | FL-3's "currently records nothing" is **read too loosely** — everything looks unrecorded if you squint. | For S-14 the reading rests on a **verbatim code comment at the record locus** (`handler.py:1157`), not on inference. Require the same standard: **cite the locus that states the non-recording, or the conjunct fails.** | Manageable; make the citation requirement explicit in any ratification. |

---

## §12 WHAT I DID NOT VERIFY

Stated so no reader infers coverage that was not taken.

- **The value of the LLM adapter's default temperature.** Established only that EBI's `src/` never sets one (own-hands zero, controlled) and that `pyproject.toml:84` says the adapter always sends one. **The default's actual value lives in `autom8y-ai` / `autom8y-core`, which I did not read.** §4.3's hazard is therefore **live and unresolved**, not measured.
- **Whether marking S-14 terminal actually drops the 5xx rate to ~11%.** TRIAGE §10's arithmetic (77 unmarked vs 76 measured 5xx) is carried as read; I re-derived none of the log-plane numbers and made no CloudWatch query.
- **Any live AWS state.** No Lambda config, no ECR, no CloudTrail, no alarm state read by this seat. Blocker C's production facts are carried from the CUSTODY fence-check and the CHARGE, not re-taken.
- **`merge-surface-sweep`'s current colour.** Carried from the CUSTODY register (RED, 3 hits); not re-run. I did not confirm it is a *required* context on the branch-protection rule — that is CHARGE Addendum L's claim, uninspected here.
- **Whether the S-14 diff as written passes the existing test suite.** No test was run. `tests/test_match_lead.py` exists at `origin/main`; its contents were not read, so **whether FL-E1's two-sided test already exists or must be authored is unknown**.
- **Whether ADIO Corrective and ADIO Chiropractic Kennesaw are the same account.** TRIAGE's caveat carried; no lookup performed. Immaterial to the REFUSE verdict (which fires on the surface, the direction, and the floor regardless of identity) but material to H2 itself.
- **Any Asana card.** No Asana tool in this session.
- **The contents of the out-of-band `salkin-safe-routing` image.** No branch or commit for it exists in the repo (TRIAGE §6); unreadable from any ref.
- **The autom8y working tree.** Never read — every autom8y fact above came from `git show origin/main:<path>` at `cc88b75e`.

---

## §13 RECEIPTS

**Method:** every platform-behavior claim above was verified by direct inspection at claim-assertion time, from the object DB at an explicit ref. Marker tokens are literal substrings of the cited source.

| # | claim | method | anchor | marker (verbatim) |
|---|---|---|---|---|
| 1 | S-14's raise site is unmarked | file-read | autom8y `origin/main:…/stages/match_lead.py:724-728` | `failure_kind=LeadMatchError.KIND_MISSING_CONTACT_NAME,` |
| 2 | The sibling marks its site and reasons about retryability | file-read | `…/stages/extract_fields.py:419-429` | `sweeping truncation into no-appt-dt would 200-ACK a retryable` |
| 3 | Unmarked ⇒ FAILED ⇒ 502 by construction | file-read | `…/handler.py:850-861` | `Every unmarked failure lands here as FAILED -> 502 by construction` |
| 4 | 502 records nothing | file-read | `…/handler.py:1157` | `FAILED/502 records NOTHING and its redelivery correctly re-runs` |
| 5 | The idiom + imports already exist in `match_lead.py` | file-read | `match_lead.py:71-74`, `:549`, `:574`, `:594`, `:686`, `:913` | `terminal_decline=TerminalDecline("name_evidence_organic", ParkKind.OPS),` |
| 6 | `LeadMatchError` accepts `terminal_decline`; the kind constant exists | file-read | `…/errors.py:127`, `:133-141` | `KIND_MISSING_CONTACT_NAME: ClassVar[str] = "missing_contact_name"` |
| 7 | The allowlist is the live-POST policy flip | file-read | `terraform/…/production.tfvars:154` | `This is the ONE policy flip that turns the 17 activated` |
| 8 | ADIO absent, Salkin + Sand Lake present, 42 entries | bash-probe (zero + 2 positive controls) | `production.tfvars:160` | `6f22301a-4c51-4282-bf86-a64108e644ad` (control hit); `e3267756` exit 1 |
| 9 | The allowlist parser locus | bash-probe | `…/config.py:500` | `def parse_contente_booking_live_allowlist(raw_csv: str) -> frozenset[str]:` |
| 10 | PR deploys nothing; merge to main deploys | file-read | `.github/workflows/service-deploy-dispatch.yml:26-32` | `paths:` / `- 'services/**'` under `push: branches: - main` |
| 11 | The deploy path executes a terraform apply | file-read | `.github/workflows/service-deploy-lambda.yml:270` (call), `:304` (apply) | `run: terraform apply -input=false -auto-approve tfplan` |
| 12 | **M-3a** no lockfile in the EBI build context | bash-probe, **zero + 2 positive controls** | `git ls-tree -r origin/main -- services/email-booking-intake` | zero hits exit 1; control A = 6 hits repo-wide; control B = 324 files in path |
| 13 | **M-3b** build-time resolution | file-read | `…/Dockerfile:53`, `:59` | `uv pip compile pyproject.toml \` |
| 14 | **M-3c** open floor; package moved 0.8.0→0.9.0 | file-read + git-show | `pyproject.toml:24`; `sdks/python/autom8y-log/pyproject.toml`; commit `695f3dea` | `-version = "0.8.0"` / `+version = "0.9.0"` |
| 15 | **M-3d** the channel already caused an outage | file-read | `pyproject.toml:82-87` | `this image resolves at BUILD time (no lockfile), and anthropic 1.x rejects the` |
| 16 | **M-3e** 2 of 13 deps capped | bash-probe (parsed array) | `pyproject.toml:21-100` | 2 capped (`:78`, `:87`), 11 uncapped |
| 17 | EBI `src/` sets no temperature | bash-probe, **zero + positive control** | all 324 files at `origin/main -- services/email-booking-intake` | zero in `src/`; control `contact_name` hits 9 `src/` files |
| 18 | CHARTER two-gate core | file-read | asana `.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md:55`, `:56` | `Autonomous work stops at TWO gates, nothing else:` |
| 19 | R-A4 never-liftable floor | file-read | asana `.ledge/decisions/RULING-decision-space-amendments-2026-08-26.md:85-88` | `No wording reaches these**, in any grant, at any tier` |

**UV-P ledger (frozen syntax) — premises this artifact carries without a receipt:**

- `[UV-P: the LLM adapter's default temperature is non-zero, making missing_contact_name non-deterministic on retry | METHOD: read the adapter default in autom8y-ai / autom8y-core at origin/main, or a single controlled retry probe designed by the reviewer | REASON: EBI src sets no temperature (zero taken, controlled); the value lives outside this repo's service tree and was not read. This premise is the reviewer's blocking question, not the predicate's.]`
- `[UV-P: merge-surface-sweep is a REQUIRED context on the branch-protection rule for main | METHOD: gh api branch-protection read at merge time | REASON: carried from CHARGE Addendum L (M-4); this seat inspected neither the rule nor the check's current colour.]`
- `[UV-P: the S-14 diff as written passes the existing suite, and a two-sided test for it exists rather than needing authoring | METHOD: run tests/test_match_lead.py against the diff — the builder's act, not this seat's | REASON: no test was read or run; FL-E1's cost is therefore unestimated.]`
- `[UV-P: G-FL1 is a gate the operator will recognize as such | METHOD: operator word | REASON: G-FL1 is NEW AND UNSPOKEN. This artifact is the receipt such a gate would consume; it is not, and does not substitute for, the word.]`

**Evidence grade: `[STRUCTURAL | MODERATE]`.** Self-attestation caps at MODERATE — this seat authored the predicate and cannot certify the wall it built. **Disjoint reviewer: `security-reviewer`.** The review question is narrow and nameable: **does any change satisfying FL-1..FL-4 cross a security or customer-visible boundary the four conjuncts fail to see?** If one exists, the predicate is wrong and the predicate is what changes — never the exemplar.
