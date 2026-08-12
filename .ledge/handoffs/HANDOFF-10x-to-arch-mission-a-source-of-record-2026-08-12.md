---
type: handoff
status: draft
revision: 2
remediates: CRITIQUE-s4-mission-a-source-of-record-2026-08-12
initiative: asana-native-insight-delivery
sprint: S4
name: Mission-A source-of-record decision
edge: 10x-dev -> arch
outbound_rite: 10x-dev
inbound_rite: arch (CO-SEATED)
inbound_seats: [dependency-analyst, structure-evaluator]
external_critic: arch-adversary
date: 2026-08-12
repo: autom8y-asana
premise_validation_stamp: PV-PARTIAL
exit_artifact: .ledge/decisions/ADR-mission-a-source-of-record-2026-08-12.md
uvp_carried: [UV-P-1, UV-P-2, UV-P-4, UV-P-7, UV-P-8, UV-P-9, UV-P-10, UV-P-11]
uvp_closed: [UV-P-5]
uvp_discharged_rev2: ["PREDICATE-sayable-set…:797", "PREDICATE-sayable-set…:798"]
uvp_retired_rev2: [UV-P-6]
self_attestation_cap: MODERATE
---

# HANDOFF — 10x-dev → arch: Mission-A source-of-record (S4)

> Companion to `.ledge/decisions/ADR-mission-a-source-of-record-2026-08-12.md`.
> This artifact records **the inbound charge** and **the receiving seat's
> premise-validation entry gate**, stamped per shape §14.2.

---

## REVISION 2 — what changed under BLOCK

> Rite-disjoint critic: **eunomia `entropy-assessor`**, verdict **BLOCK**,
> `.ledge/reviews/CRITIQUE-s4-mission-a-source-of-record-2026-08-12.md`.
> Full finding-by-finding disposition lives in the ADR's `REVISION 2` section.
> This section records only what changed **in this artifact** and what the
> operator needs to read differently.

### The one thing that matters most

**§6's GATE-FORK sentence was a false biconditional and is WITHDRAWN.**

Rev-1 told the operator:

> *"Mission A is buildable as framed **if and only if** the operator rules that the
> readout may begin its history at first run."*

**That is false.** A seventh option exists — `GET /api/v1/offers/section-timelines`
— already built, already mounted (`src/autom8_asana/api/main.py:488`), already in
the published contract (`docs/api-reference/openapi.json:3859`), with **no
CloudWatch retention dependency, no K-lane contact, and no producer deploy
required**. It is **better contracted than the source this HANDOFF recommends**
(in-schema and spec-gated, where option (b)'s route is `include_in_schema=False`).

**Rev-1 would have told the operator they cannot do something they can, on a live,
date-bounded, operator-reserved decision (GATE-FORK, free until 2026-08-18).**
The corrected statement is at §6 below and in ADR §11.1.

### What did NOT change

- **The recommendation.** Option (b) stands for the recurring forward-looking
  readout. The critic attacked all six grounds and could not break it.
- **The PV-PARTIAL stamp** (§2). The critic tried to call it a hedge and could not.
  It grades the **inbound charge's premises**; it says nothing about whether the
  sprint discharged the charge. That distinction is now stated explicitly at §2.
- **The read-only fence.** Held at rev-1 and at rev-2. Zero git operations.

### What changed in this artifact

| § | Change |
|---|---|
| frontmatter | `revision: 2`, `remediates:`; UV-P-6 retired; UV-P-9/10/11 opened; two S1-routed UV-Ps recorded as discharged |
| §0 | Records that the same false premise propagated through S1, which rev-1 did not say |
| §2 gate item 3 | Adds the precedent-citation failure rev-1's audit did not catch: S1's routing was consumed without attribution |
| §2 stamp | Adds what PV-PARTIAL does **not** cover — a clean entry gate is not an exit warrant |
| §3 | **Seven** options, not six; exit criterion 1 re-stamped |
| §4 | The outbound charge's own item 4 — *"is there a seventh?"* — is now **answered YES**, by an external critic rather than by this seat |
| §5 | UV-P carry rewritten |
| §6 | **The GATE-FORK sentence, corrected** |
| §7 | Two additional read-only AWS calls declared |
| §8 | Grade re-stated with the BLOCK on the record |

### Self-attestation ceiling: **MODERATE**, and I do not clear my own BLOCK

This revision remediates a BLOCK. It does not lift one. Both artifacts remain
`status: draft`.

---

## §0 Premise refinement — surfaced, not papered

Per shape §14.2 item 5, a charge premise falsified mid-flight is surfaced in the
HANDOFF §0, never papered. **One was.**

> **The charge (via shape §2.3 / NF-2) states that
> `terraform/services/asana/` "does not exist in the monorepo at `origin/main`."
> IT DOES — 17 entries at `0e60e0f5`, `git ls-tree` exit 0. Re-verified at rev-2
> against `origin/main` = `a5c98f9c`.**

The dispatching message anticipated this and pre-warned the seat. Both the
dispatching message and this seat's own probe agree. Recorded here at the top of
the artifact because that is where a falsified premise belongs.

**What survives**: NF-2's *finding* — that UV-P-5 was genuinely open and that
Logs Insights is an uncontracted surface — is intact and **strengthened**. Scoped
to that directory, `git grep retention_in_days` returns **zero matches** (exit 1).
The retention is not merely undocumented; it is **declared in neither repo**, and
the actual owner (a third repo, at a pinned ref, as an unoverridden default) is a
**worse** coupling than NF-2 assumed. See ADR §4 and §4.1.1.

**What is withdrawn**: only the stated *reason* for the UV-P.

> **Rev-2 addition — the propagation path rev-1 did not name.** The same false
> premise travelled through **S1** as well as the shape:
> `.ledge/decisions/PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:799`
> carries it verbatim (*"REASON: terraform/services/asana/ does not exist at
> autom8y origin/main"*), inherited from `shape:694`. Rev-1 attributed the premise
> to the shape alone, which understated how far it had spread. Credit for spotting
> the propagation belongs to the rite-disjoint critic.

---

## §1 The inbound charge, as received

| Field | Value |
|---|---|
| **Sprint** | S4 — *Mission-A source-of-record decision* |
| **Workstream** | NEW (added by the shape, from NF-2) |
| **Rite** | arch — **co-seated**, active rite unchanged (see §2 gate item 2) |
| **Seats** | `dependency-analyst` (this seat, authoring), `structure-evaluator` |
| **External critic** | `arch-adversary` |
| **PR boundary** | 1 atomic PR — `.ledge/decisions/` only. READ-ONLY across repos; autom8y read at `origin/main` per ADR-007 §8 O-11 (`shape:679`) |
| **Producer deploy** | `false` (`shape:680`) |
| **Window-bound** | `false` |
| **Rung** | PENDING |

**Mission (verbatim from shape §5.1):**

> Decide and contract the source-of-record for board-behaviour metrics BEFORE any
> Mission-A build. Enumerate options before recommending. A NEGATIVE result (no
> contractable source at acceptable cost) is a first-class outcome and is
> decision-grade input to GATE-FORK.

**Entry criteria as charged** (all three discharged — §2):
1. shape §2.3 (NF-2) read
2. `EVIDENCE-w1` `:15`, `:629`, `:669` read — the CloudWatch Logs Insights provenance
3. `ADR-007` §7.5 `:1228-1239` read — the one-way-door hazard class

**Binding fences as charged**: read-only across both repos; no code change; no
infra mutation; no AWS writes (read-only AWS queries permitted); no producer
deploy; **no dependency on the K-lane**; self-attestation capped at MODERATE.

> **Rev-2 correction to the fence's provenance.** Rev-1 listed the K-lane fence as
> though the S4 sprint block declared it. **It does not** — the sprint block
> (`shape:672-703`) declares **no `fences:` key at all**; its only stated
> boundaries are `pr_boundary` (`:679`) and `producer_deploy: false` (`:680`), and
> its K-lane item (`:696`) is an **exit criterion** (an obligation to *state*), not
> a prohibition. **The prohibition is nonetheless real**, declared at initiative
> level in the shape's §15.1 **PRESCRIBED — must follow** register, `shape:1501-1503`
> (*"Zero K-lane dependency: no touch on the offer-axis combiner, the freshness-meta
> reducer, `RowsMeta` / `AggregateMeta`, the manifest write path, or `SectionInfo`"*),
> corroborated by success criterion `shape:82` and failure signal `shape:88`.
>
> **This is one of two places the critic is wrong**, and it is receipted: the
> critique concluded from the sprint block's silence that no fence bound this
> sprint. It did. **The critic's substantive point survives anyway and lands on
> better ground** — the fence's own next sentence (`shape:1504`, *"If a readout
> wants a number that only exists on the K-lane, it WAITS"*) is what dissolves
> rev-1's over-reading, because the disputed quantity does **not** only exist on
> the K-lane. Full treatment: ADR §9.3.

---

## §2 Premise-validation entry gate — **PV-PARTIAL**

Per `handoff-premise-validation-entry-gate` and shape §14.2. Five checks, each
stamped independently. **The stamp is unchanged at rev-2. Gate item 3 gains a
recorded failure that rev-1's self-audit missed.**

### Gate item 1 — Substrate accessibility → **PASS**

Every cited path resolved and was **live-read by this seat**; none inherited.

| Cited substrate | Resolution | Probe |
|---|---|---|
| `.sos/wip/frames/asana-native-insight-delivery.shape.md` §2.3, §5.1 S4, §14.2, §15.1, §16 | **RESOLVES** | `sed -n` on lines 74-92, 160-205, 578-740, 1470-1510, 1545-1567 |
| `.sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md` `:15`, `:629`, `:669` | **RESOLVES** | `sed -n '15p;629p;669p'` + bounded surrounding context |
| `.ledge/decisions/ADR-007-verification-axis-gate-2026-08-12.md` `:1228-1239` | **RESOLVES** | `sed -n '1228,1239p'`; **rev-2 extends the read to `:1195-1240`** to reach the derivability text at `:1198-1201` and the blast-radius rows at `:1219`/`:1223`/`:1224` |
| `autom8y` monorepo | **RESOLVES at `origin/main` = `0e60e0f5` (rev-1); re-verified at `a5c98f9c` (rev-2)** | fetched, then read **exclusively** via `git show/grep/ls-tree origin/main:` |
| `a8` platform-modules repo (`git@github.com:autom8y/a8.git`) | **RESOLVES at pin `0fb9527b`** | `git cat-file -t 0fb9527b` → `commit` |
| AWS us-east-1 / 696318035277 | **RESOLVES** | `sts get-caller-identity` → assumed-role AdministratorAccess |

**⚠ ADR-007 §8 O-11 hazard — HONOURED, and it mattered.** The autom8y working
tree sits on `fix/wss-wildcard-scope-bypass-closure` (`58c5eb92`), not an ancestor
of `origin/main`. **Every autom8y fact in the ADR is anchored to `origin/main`.**
The dispatching message's warning was load-bearing: the *falsified* premise in §0
is precisely a false-negative of the shape it warns about.

> **Rev-2 — this fence was independently corroborated by the one datum that
> differs.** The critic (holding no Bash, and honestly carrying the doubt as
> UV-P-C-2) read the **working tree** and compared it against rev-1's
> origin/main-attested claims. **Everything matched byte-exactly except the module
> `ref=`**: rev-1 reported `0fb9527b`; the trap surface carries `80402fd3`. A value
> that appears **nowhere in the trap surface** cannot have been read from it.
> Rev-2 settles UV-P-C-2 by direct probe:
> `git show origin/main:terraform/services/asana/main.tf | sed -n '101p'` →
> `ref=0fb9527b`. **Rev-1's attestation is confirmed.**
>
> **Rev-2's own single working-tree-adjacent read** is an explicit
> `git show HEAD:terraform/services/asana/main.tf | sed -n '101p'`, performed
> *solely to demonstrate the divergence* in ADR §4.1.1, and **labelled as the
> divergent branch at every mention**. No origin/main fact is asserted from it.

**Note on scope**: resolving UV-P-5 honestly required reading a **third** repo
(`a8`), because the retention owner is neither in asana nor in autom8y. That read
was **read-only** and is therefore inside the fence, but it is an **expansion of
the charged read surface** and is declared here rather than absorbed.

### Gate item 2 — Rite-classification verification → **PASS (with a recorded nuance)**

Required: the named seat resolves in `ari rite pantheon` **and** in
`.claude/agents/`. **Both, not either.**

| Seat | `ari rite pantheon` | `.claude/agents/` | Verdict |
|---|---|---|---|
| `dependency-analyst` | **present** — *"Traces cross-repo dependencies, coupling, and integration patterns."* | **present** — `dependency-analyst.md` | **RESOLVES** |
| `structure-evaluator` | **present** — *"Evaluates architectural health, anti-patterns, and boundary alignment."* | **present** — `structure-evaluator.md` | **RESOLVES** |
| `arch-adversary` | **present** — *"Adversarial reviewer of arch outbound HANDOFFs."* | **present** — `arch-adversary.md` | **RESOLVES** |

**Nuance, recorded rather than glossed**: `ari rite current` reports
`Active Rite: 10x-dev`, while the sprint block declares `rite: arch`. This is
**not** a defect — the repo `CLAUDE.md` documents arch as a **borrowed / co-seated**
rite (`ari rite invoke`, active rite unchanged), listing exactly
`arch-adversary, dependency-analyst, remediation-planner, structure-evaluator,
topology-cartographer`. The gate's requirement ("both, not either") is satisfied
by the pantheon + agents-dir pair. The edge is therefore correctly labelled
`10x-dev -> arch (CO-SEATED)` and not `10x-dev -> arch (ACTIVE)`.

### Gate item 3 — Precedent-citation audit → **PASS on reads; FAILED on attribution (rev-2)**

Every artifact cited in the exit ADR was **live-read by this seat in this
dispatch**. Nothing was inherited from the charge's summary of it. Specifically:

- The three charged reads were performed **directly**, not taken from the shape's
  quotation of them.
- `query.py:549` was **re-read at HEAD `4129ae7e`**, not accepted from shape §2.3's
  re-verification claim (which independently held).
- `activity.py:181-230` (`OFFER_CLASSIFIER`) was **re-read directly**, not taken
  from `EVIDENCE-w1:660-662`'s citation of it.
- `freshness.py:298-306`, `section_persistence.py:551-559`, `query/models.py:387`
  and `:225` were each read at source rather than accepted from EVIDENCE-w1's
  anchor list.

**One deliberate non-read, declared**: the *full* ADR-007 and the *full* EVIDENCE-w1
were **not** preloaded, per shape §16's explicit "Do NOT preload" instruction. Only
the named line ranges plus bounded surrounding context were read.

> **⚠ REV-2 — A FAILURE THIS GATE SHOULD HAVE CAUGHT AND DID NOT.**
>
> Rev-1's audit checked that every cited artifact was **read at source**. It did
> **not** check that every *consumed finding* was **attributed to its source**.
> Those are different questions, and the second one failed.
>
> **S1 derived the caller-hostage coverage finding and routed it to S4 by name**:
> `PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:619-624` —
> *"`query_rows_complete` … emits … **request-shaped, with no edit-time field**. A
> section appears in that stream iff some caller queried it. **Routed to S4** as a
> named option-enumeration input; **not decided here.**"* Rev-1's ADR §5(a)
> presented it as *"⚠ Coverage dependency the shape did not name"* — as its own
> discovery — and cited neither S1 nor the routing.
>
> **The substance was true** (I re-verified it own-hands at `query.py:557-558`:
> `section` and `classification` are `request_body.*` echoes). **But one reading was
> counted twice**, which made an inherited chain look like independent
> corroboration between two seats.
>
> **The concrete cost**: S1 routed **two** enumeration questions alongside it
> (`PREDICATE…:797`, `:798`), and rev-1 discharged **neither**. Both are answered
> by option (g), the option rev-1 missed. A seat that had noticed it was consuming
> a routed charge would have had a second prompt to look. **This is the strongest
> argument in the whole exchange for rite-disjoint critique**, and it is the
> critic's finding, not mine.
>
> **Corrective for future gates**: the precedent-citation audit must ask **two**
> questions — *was it read at source?* **and** *was it attributed, and were its
> routed questions discharged or explicitly carried?*

### Gate item 4 — Load-bearing premise anchoring → **PASS**

Every load-bearing premise in the exit ADR carries a `{path}:{line}` anchor. The
structural claims additionally carry full SVR tuples (ADR §14) with
`verification_method` ∈ {`git-ls-files`, `bash-probe`, `file-read`} and
orthogonal `claim` fields. Design-choice and estimative claims (the recommendation
itself; the SA-1 preconditions; the conditional cost conclusion) correctly carry
**no** receipt, per the trigger-table rows 5/6 discrimination.

> **Rev-2**: eight receipts became eleven. Four were **re-anchored for line
> precision** (critic F-12 — verified: `freshness.py` marker at `:298` not `:299`;
> `_save_manifest_async` def at `:480` not `:481`; `query_ms` at `:398` not within
> `:390-396`; `OFFER_CLASSIFIER` statement `:181-230` not `:179-231`; the
> `module "service"` block closes at `main.tf:350` not `:361`). **Rev-1's SVR-8 is
> replaced outright** — its claim (*"the retrospective spine is SectionInfo-derived,
> therefore fenced"*) is withdrawn. **SVR-2b lowers the grade of one of rev-1's own
> claims** on the strength of a probe rev-1 did not run (ADR §4.0).

### Gate item 5 — §10.5 premise refinement → **EXERCISED**

A charge premise was falsified mid-flight and is surfaced in §0 of this HANDOFF
and §2 of the exit ADR, with its own finding ID (**FP-S4-1**). Not papered.

### Stamp

> ## **PV-PARTIAL**

**Why PARTIAL and not PASS**: gate items 1-5 all pass, but a **load-bearing premise
of the inbound charge is falsified** (§0). Stamping PV-PASS would paper the
falsification, which §14.2 item 5 forbids.

**Why PARTIAL and not FALSE**: the charge's *conclusion* — that UV-P-5 was open and
that the Logs Insights surface is uncontracted — **survives and is strengthened**.
Only the stated *reason* fails. PV-FALSE would overstate the damage and would
wrongly imply the sprint should not have run. It should have, and did.

**Consequence**: **the charge is CONSUMED, not refused.** S4 proceeded to completion
on a corrected premise base.

> **Rev-2 — what this stamp does NOT cover, stated because the BLOCK sits exactly
> in the gap.** PV-PARTIAL grades the **inbound charge's premises**. It says
> nothing about whether the sprint **discharged** the charge, and nothing about
> whether the charge's **routed questions** were answered. `PREDICATE…:797-798`
> routed two enumeration questions that rev-1 did not discharge, and exit criterion
> 1 was self-attested **MET** while **unmet**. **A clean entry gate is not an exit
> warrant.** The stamp is honest and stands unchanged; the BLOCK sits downstream of
> it and is not in tension with it. *(The critic reached this conclusion
> independently and I concur without reservation.)*

---

## §3 What was produced

**Exit artifact**: `.ledge/decisions/ADR-mission-a-source-of-record-2026-08-12.md`
(`type: decision`, `status: draft`, `revision: 2`).

**Verdict (rev-2)**: **QUALIFIED RECOMMENDATION + NARROWED NEGATIVE RESULT.**
*(Rev-1's "BOUNDED NEGATIVE RESULT" is withdrawn.)*

| Half of the question | Result (rev-1) | Result (rev-2) |
|---|---|---|
| Recurring, **forward-looking** readout | **Contractable** — adopt option (b) | **UNCHANGED** — adopt option (b): the offers frame via the rows query surface, `classification` derived locally from `section` **and `is_completed`**, aggregated into a self-owned snapshot series |
| **Retrospective** 14-day history | **NEGATIVE RESULT** — no contractable source at acceptable cost | **REACHABLE, CONDITIONALLY** — option (g), `GET /api/v1/offers/section-timelines`, already deployed and in the published contract. **Rev-1's answer was wrong** |
| **Log-derived** retrospective source | *(not separated)* | **NEGATIVE RESULT — this is what survives.** 30-day-capped, uncontracted, externally-defaulted retention. This is the whole of NF-2's original hazard |

**SEVEN options enumerated before any recommendation** (the charge named four; the
dependency trace surfaced two; **the rite-disjoint critique surfaced the seventh**):
(a) Logs Insights over `query_rows_complete`, (b) the offers frame / query surface,
(c) a new purpose-built emission, (d) no contractable source, (e) Grafana Cloud Loki
via the live forwarder, (f) the S3 dataframe substrate,
**(g) `GET /api/v1/offers/section-timelines` — NEW at rev-2**.

> **The enumeration-method failure, recorded so the next seat inherits it.**
> Rev-1 built its enumeration by tracing **from surfaces already in hand**. It did
> **not** sweep the **published contract artifact** for candidate surfaces — even
> though `docs/api-reference/openapi.json` was open and being queried for SVR-4.
> Option (g) sits at `:3859` of that file.
>
> **Enumerating options from the surfaces you already know is not the same as
> enumerating from the published contract.** *Querying a contract to confirm a fact
> about a known surface* and *sweeping a contract to discover unknown surfaces* look
> identical from the inside and are not.

**Exit criteria status:**

| # | Criterion | rev-1 | rev-2 |
|---|---|---|---|
| 1 | Options enumerated before recommendation | **MET** *(self-attested — and wrong)* | **NOT MET at rev-1 → MET at rev-2** (seven enumerated and dispositioned; an eighth not proven absent) |
| 2 | UV-P-5 closed or carried | MET — CLOSED | **MET — CLOSED**, re-verified at a second `origin/main` |
| 3 | Contract statement for the recommended source | MET at code altitude | **MET at code altitude**; human owner → UV-P-7; §8.3 recounted **7 silent : 3 loud : 1 partial** |
| 4 | Explicit K-lane non-dependency attestation | MET | **MET** — five surfaces, per item, two counter-findings, **independently re-traced by the critic with none found**; three residuals added; fence provenance corrected |
| 5 | NF-2 hazard named | MET | **MET** |
| 6 | arch-adversary verdict returned and dispositioned | **OPEN** | **OPEN** — a eunomia BLOCK has been returned and dispositioned; that is a **different critic** and does not satisfy this criterion |

---

## §4 Outbound charge to the external critic (arch-adversary)

The exit ADR is `status: draft` and is **not exit-complete** until this runs.

> **Rev-2 status of the four rev-1 items.** A rite-disjoint **eunomia** critic has
> since run and returned **BLOCK**. Its findings are dispositioned in ADR
> `REVISION 2`. The four items below are re-stated with what is now known, so
> arch-adversary spends its attack surface on what is still open rather than
> re-running a settled attack.

1. **§9's attestation** — *"is a discipline-based non-dependency worth the word
   attestation?"* **PARTLY ANSWERED.** The critic traced all five named surfaces
   independently and found **none** consumed; it judged the discipline acceptable on
   ADR-007's own gating language (`:1233-1236`). **But it added a hazard rev-1
   missed** (`RowsMeta` is `extra="forbid"` and growing → a hand-rolled strict
   parser breaks when K-2 lands), and **rev-2 adds a second the critic missed**: the
   clean fix for the empty-serve disclosure reads `meta.honest_empty`, itself a
   **manifest-derived `RowsMeta` field** (`query/models.py:466-478`). **Still open
   for arch-adversary**: is ADR §9.2 item (iv)'s fork correctly *held* at the
   operator/structure-evaluator boundary, or is this seat ducking a call it owns?
2. **§7.2's negative result** — *"is cohort spread reconstructible in a weaker form
   the ADR dismissed too quickly?"* **ANSWERED YES, and worse than "weaker form."**
   The critic found a **stronger** form: a published endpoint that replays section
   history over an arbitrary window. Rev-1's negative result is withdrawn.
   **Still open for arch-adversary**: is rev-2's *narrowed* negative result
   (no **log-derived** retrospective source) itself over-claimed? It rests on the
   retention chain (verified twice) and the uncontracted emission (verified twice).
   Attack the word "contractable."
3. **§6's coupling scoring of option (b)** — *"is the gate doing its job, or the
   anti-pattern in reverse?"* **UNTESTED by the eunomia critic** — it explicitly
   deferred coupling adjudication to structure-evaluator. **Fully open.** And rev-2
   adds a second target: **option (g) is scored MODERATE / not-a-hotspot on the same
   bounded-context reasoning.** If the reasoning is excusing coupling by asserting
   domain alignment, it is now doing so **twice**.
4. **"Is there a seventh option?"** — **ANSWERED: YES, and this seat did not find
   it.** Rev-1 asked the question in its own outbound charge, self-attested the
   option space complete at six anyway, and was refuted by an external critic
   reading the same contract artifact rev-1 had open. **Still open for
   arch-adversary — and it is the sharpest available attack**: *is there an
   eighth?* Rev-2 declines to grade option-space completeness above **MODERATE**
   for exactly this reason. Rev-1's hedge (*"Absence of a seventh is not proven"*)
   was the correct instinct and was under-weighted; **rev-2 must not repeat the
   error by treating seven as closure.**

**Two new targets rev-2 hands to arch-adversary:**

5. **The fence-provenance correction (ADR §9.3).** Rev-2 asserts the K-lane fence is
   real and binding at `shape:1501-1503`, and that the critic was wrong to infer
   from the sprint block's silence that no fence existed. **Test that.** If rev-2's
   reading of `shape:1504` (*"a number that **only exists** on the K-lane"*) is
   itself convenient rather than correct, the whole §9.3 correction inverts and
   rev-1's leg 3 partially revives.
6. **Option (g)'s operational reality.** Every claim about (g) in this artifact is
   **code-and-contract attested, NOT live-attested**. No HTTP request was made; the
   story-cache hit rate is unmeasured (UV-P-10); Asana's story retention is unknown
   (UV-P-9). **If (g) is degraded in practice, rev-2 has over-corrected** — the
   negative result would narrow rather than fall, and §11.1's three-path input to
   the operator would need a fourth qualification. **This is the cheapest and most
   consequential thing left to probe.**

---

## §5 UV-P carry — Gate-C DEFER-tag pattern

**Closed by this sprint**: **UV-P-5** (ADR §4 — value 30 days; owner `autom8y/a8`
module default at pin `0fb9527b`; stated reason falsified, real reason resolved;
terraform chain re-verified at a second `origin/main`).

**Discharged at rev-2 — the two enumeration questions S1 routed here and rev-1 did
not answer** (full treatment ADR §12):

- `PREDICATE…:797` — *"whether any per-section or per-offer observation series can
  be reconstructed from an existing emission"* → **YES via an existing published
  endpoint** (option (g)); **NO** if "emission" is read strictly as *log emission*.
- `PREDICATE…:798` — *"whether mean dwell is derivable from cohort counts via a
  queueing identity"* → **DISCHARGED BY OBVIATION**: the identity is not needed,
  because gross transition flow is what Asana `section_changed` stories carry
  (`section_timeline_service.py:245-267`). **Conditional**: the raw intervals are
  not returned over the wire (`section_timeline.py:158-226`, `extra="forbid"`), so
  this needs an additive field on an already-published model.

**Retired at rev-2**:

```
[UV-P-6 — RETIRED as non-load-bearing. Grafana Cloud Loki retention. Option (e) is
rejected on independent grounds, and rev-2 opens two UV-Ps that ARE load-bearing
because they bound a RECOMMENDED option, which UV-P-6 never was on a rejected one.
Recorded so a future reader does not assume Loki is a longer-retention archive]
```

**Opened by this sprint and carried**:

```
[UNATTESTED — DEFER-POST-HANDOFF]
[UV-P-7: named human/team owner of BASE_SCHEMA + OFFER_CLASSIFIER + the rows route
+ the section-timelines route | METHOD: deferred-to-operator | REASON: code
ownership is unambiguous; the accountable party is not derivable from the repo.
Exit criterion 3 is MET at code altitude and OPEN at human altitude]
```

```
[UNATTESTED — DEFER-POST-HANDOFF]
[UV-P-8: dollar cost of a scheduled Logs Insights query over 14 days on a ~1.55 GB
group | METHOD: deferred — pricing probe not run | REASON: option (a) is rejected on
contract grounds that hold at any price; stated qualitatively only]
```

```
[UNATTESTED — DEFER-POST-HANDOFF]
[UV-P-9: Asana's own retention of `section_changed` stories | METHOD:
deferred-to-vendor-documentation-or-live-probe | REASON: option (g)'s retrospective
DEPTH is bounded by it, and it is a vendor property not resolvable from any of the
three repos. LOAD-BEARING — (g) is recommended for the retrospective half, not
rejected]
```

```
[UNATTESTED — DEFER-POST-HANDOFF]
[UV-P-10: option (g)'s real story-cache hit rate on the offers board | METHOD: a
Logs Insights query on `story_cache_gap_above_threshold` /
`inline_story_fetch_complete` / `timeline_computed_on_demand`
(`section_timeline_service.py:522-541`, `:656-661`) | REASON: caveat 3 of ADR §5(g)
is a footnote if the hit rate is high and a disqualifier if it is low. NOT probed
under this sprint's minimal-AWS fence. THE single most important open question on
option (g), and cheaply answerable — the emissions already exist]
```

```
[UNATTESTED — DEFER-POST-HANDOFF]
[UV-P-11: whether `last_modified` is non-null IN PRACTICE, not merely declared |
METHOD: a null-count over the live offers frame, or a probe of
`coerce_rows_to_schema` enforcement | REASON: `nullable=False` at `base.py:79` is a
DECLARATION; no runtime gate found, and the write paths defend against nulls
(`freshness.py:539`, `progressive.py:678`). NEITHER rev-1, rev-2, NOR the critic
probed it. A probe not run, honestly labelled]
```

**Inherited and untouched** (shape §14.3): **UV-P-1, UV-P-2, UV-P-4** remain live and
are not this sprint's to resolve. **UV-P-3** remains DISCHARGED.

---

## §6 Downstream consumption notes

**For SA-1** (board-behaviour readout generator, gated behind GATE-FORK): the ADR's
**§8.4 preconditions** are a binding charge, not advice — and there are now **six,
not three**: FM-5 consumer registration, a two-sided drift test, a named owner,
**plus** (4) declare which classification semantic the readout implements and
disclose the divergence, (5) parse the rows response permissively or consume via the
SDK, and (6) refuse or label a zero-row readout rather than render it. They require
code changes S4 was fenced from making. Proceeding without them is a deliberate
acceptance to be **recorded**, not a silent omission. **Precondition 6 carries a
fork with a K-lane consequence (ADR §9.2 item iv) that SA-1 may not resolve
unilaterally.**

**For GATE-FORK**: the rev-1 sentence is **WITHDRAWN**.

> ~~*"Mission A is buildable as framed if and only if the operator rules that the
> readout may begin its history at first run. Otherwise Mission A acquires either a
> 30-day-capped, uncontracted, K-lane-derived dependency, or a new-emission cost the
> frame did not budget."*~~
>
> **FALSE — a biconditional presenting a two-branch choice where three branches
> exist, and excluding the branch that is already paid for. Had it reached the
> operator unrevised it would have foreclosed a real capability.**

**The corrected decision-grade input:**

> **The retrospective half is REACHABLE. Three paths exist, not two.**
>
> 1. **Begin the series at first run under option (b)** — **zero additional cost**,
>    and it reproduces brief #1's per-section spine *going forward*, because that
>    spine — `SectionInfo.watermark` — **is** `max(last_modified)` over the
>    section's rows (`freshness.py:536-540`, `:645-648`; `progressive.py:680`,
>    `:1729-1731`; docstring `section_persistence.py:521`), a reduction over declared
>    columns the recommended source already returns. **Zero K-lane contact.**
> 2. **Consume `GET /api/v1/offers/section-timelines`** for historical per-offer
>    classification occupancy over an arbitrary past window — **already built,
>    already mounted (`api/main.py:488`), already published
>    (`openapi.json:3859`), no producer deploy, no CloudWatch retention dependency,
>    no K-lane contact**, and **better contracted than the source this HANDOFF
>    recommends** (in-schema and spec-gated, where option (b)'s route is
>    `include_in_schema=False`). **Conditional on** two additive disclosure fields,
>    a day-sweep for per-day occupancy, acceptance of a current-membership
>    denominator, and the open questions UV-P-9 and UV-P-10.
> 3. **The 30-day-capped, uncontracted log mine** — still correctly **REJECTED**.
>
> **Mission A is NOT shown to be more expensive than framed on the retrospective
> half.** The fork is no longer *"history, or no history"* — it is *"which
> already-paid-for retrospective surface, at what disclosure cost, with which open
> vendor question accepted."*
>
> **The fork is operator-reserved, free until 2026-08-18, and is NOT decided here.**
> Option (g) changes **what the operator is choosing between** — which is exactly
> why it must reach them **accurately and unresolved**.

**For the SRE lane** (routed, not decided): the asana ECS log group's retention is
undeclared in both repos while all ten sibling Lambda groups declare it explicitly
(ADR §4.1, ten sites re-verified at `origin/main` at exactly the cited lines).
**Rev-2 strengthens this materially**: the effective pin at `main.tf:101`
(`ref=0fb9527b`) occurs **exactly once in the file** — it is named in **none** of
the twelve comment lines written to document the bump chain, which terminate at a
**different** value (`80402fd3`, `:96`/`:99`), which is also what the divergent
branch carries at the same line. **The prose record is already out of sync with the
pin it documents.** This is a standing cross-repo coupling affecting **every**
future log-derived readout. Two candidate remedies are named in ADR §13 item 2.
**This sprint holds no authority to act on either.**

**For structure-evaluator** (co-seat): ADR §6's coupling table (**now seven rows**)
and §9.1's contract-dependency / derived-value-dependency / **independent-derivation**
trichotomy are offered for adjudication. **Two questions are specifically yours:**

1. **Option (g)'s inversion** (ADR §6 addendum): it is the only option whose
   coupling is **strongest at the contract layer and weakest at the operational
   layer** — better contracted than the recommended source, while carrying a silent
   story-cache degradation mode the recommended source does not have. **Whether
   contract quality or operational determinism binds for a recurring readout is
   yours, not this seat's.**
2. **The honest-empty fork** (ADR §9.2 item iv): disclosure precision vs. K-lane
   non-dependency, a genuine quality-attribute trade-off
   [AQ:SRC-003 Kazman et al. 2000] [STRONG].

This seat maps what IS and scores coupling; **whether any of these coupling levels
is acceptable is not this seat's call.**

---

## §7 Fence compliance

Read-only throughout, across all three repos, at rev-1 and rev-2.

- **No** code change, **no** infra mutation, **no** producer deploy, **no** git
  operation of any kind (no add, commit, branch, stash, checkout, or push).
  Read-only `git show` / `git grep` / `git ls-tree` / `git rev-parse` /
  `git cat-file` only.
- **Writes**: exactly two files, both under `.ledge/` in `autom8y-asana` — the exit
  ADR and this HANDOFF. Rev-2 rewrote the same two paths in place; no new artifact
  was created and no target-repo file was touched.
- **autom8y**: read **exclusively** via `git show/grep/ls-tree origin/main:`
  (ADR-007 §8 O-11). **One** explicit `git show HEAD:…` in rev-2, used solely to
  demonstrate the branch divergence in ADR §4.1.1, **labelled as the divergent
  branch at every mention**; no origin/main fact asserted from it. The working tree
  itself was never read.
- **a8**: read at pin `0fb9527b` and at `origin/main` refs only; working tree not
  modified.
- **AWS calls made** — **five total, all read-only**:
  - rev-1: `sts get-caller-identity` ×1, `logs describe-log-groups` ×1,
    `logs describe-subscription-filters` ×1
  - rev-2: `logs describe-log-groups` ×1, `logs describe-log-streams` ×1
  - **No** `start-query`, **no** Lambda invocation, **no** S3 object read, **no**
    request to the asana serve path, **no** Asana API call, **no** mutation of any
    kind.
- **K-lane**: not touched, not read for consumption, not depended on (ADR §9).
  The fence's provenance is corrected at §1 and ADR §9.3; the attestation itself is
  unchanged and was independently re-traced by the critic across all five surfaces.

---

## §8 Evidence grade

**MODERATE — self-attestation ceiling, binding.** Both artifacts are
`status: draft`.

**The record as it now stands**: a rite-disjoint **eunomia** critic ran and
returned **BLOCK**. This revision remediates it. **It does not clear it** — a seat
does not clear its own BLOCK, and the sprint's named external critic
(`arch-adversary`) has still **not** run (exit criterion 6, OPEN). Nothing in
either artifact should be consumed as certified.

**What moved up at rev-2:**

- **UV-P-5 / §4** holds at **STRONG**, but on **two** disjoint methods rather than
  three — the terraform chain (re-verified at a *second, later* `origin/main`) and
  a direct live retention read. **Rev-1's third method is withdrawn by my own
  probe**: the group is actively written (last event ≈ 21.5 minutes before the
  probe), so a `storedBytes` figure byte-identical across three readings eleven days
  apart is a cached field, not three converging measurements. It establishes
  same-group identity and nothing more. *(Recorded against my own prior work
  because the critic's seat had no Bash and could not have found it.)*
- **§4.1** rises to **STRONG** on four independent structural facts and is the
  finding this sprint should be remembered for outside Mission A.

**What moved down at rev-2:**

- **The negative result (§7.2)**: rev-1 graded it **STRONG on the mechanism** on
  three grounds *"each independently sufficient."* One is refuted, one rested on a
  misdescribed observable, and the class conclusion is refuted. **Withdrawn as
  stated**; the narrowed survivor is **MODERATE**.
- **Option-space completeness (§5)**: **falsified at rev-1**. **MODERATE at rev-2**,
  and deliberately not higher — seven options include one this seat did not find,
  and an eighth is not proven absent.
- **§11's GATE-FORK input**: graded **MODERATE**, deliberately, because it is the
  sentence the operator consumes and its relative-cost claim depends on two open
  UV-Ps.

**The honest one-line summary**: the sprint's **structural work** (retention chain,
K-lane attestation, contract statement, coupling gate) survived rite-disjoint
attack largely intact and in two places got stronger. Its **search** did not. The
failure was one of enumeration, not of candour — and the artifact that caught it
was seated outside this rite, which is the whole reason that seat exists.
