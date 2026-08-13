---
type: review
status: accepted
artifact_id: CRITIQUE-exec-register-2026-08-13
initiative: exec-insight-delivery
subject: .ledge/reviews/REPORT-exec-state-of-work-2026-08-13.md
reader: eunomia / verification-auditor (rite-disjoint SECOND READER)
author_of_subject: 10x-dev (main thread)
disjointness: eunomia != 10x-dev — Q-7 second-reader gate satisfied
role: Read-only + Bash; this reader authored ONE file (this one) and sent nothing (delivery operator-performed, C-7)
grammar: STANDS / FALLS / NARROWS per §A.3 (register-critique grammar; NOT the execution-altitude PASS/PARTIAL/FAIL, NOT the product-altitude *-ADVISORY tiers)
self_attestation_ceiling: MODERATE, except own-hands re-derivations flagged [STRONG-own-hands]
date: 2026-08-13
---

# Second reading — the exec state-of-work register

**Overall verdict on the register's negatives: STANDS, with NARROWS on three
exit-criteria (EC-3, EC-4, EC-6) and EC-1 operator-pending.** No FALLS. The
register does **not** pre-select any of R-16's three open decisions (Q5.2
answer below), carries **no** falsified 68/68-as-completeness premise, and
treats the probe's MODERATE ceiling as a *stated grade*, not an absence. The
NARROWS trace to a **single root cause**: one honest half of the TemporalFilter
finding — *exploitation frequency is undetermined* — does not travel, and the
blanket reassurance "None is an active incident" mildly over-reaches where the
probe says traffic is unknown. The remedy is **additive** (a clause + folding
one named gap into the could-not-determine section), so this is REVISE-before-
deliver, **not** REVERT. The dissent on EC-4 is not softened: as written, the
criterion's "both halves travel or neither does" is **UNMET**.

---

## 1. Seven exit criteria — verbatim from shape §2, each verified

| # | Criterion (compressed) | Verdict | Evidence |
|---|---|---|---|
| 1 | Delivered + operator confirms receipt (delivery operator-performed, C-7) | **OPERATOR-PENDING** (not a defect) | Draft frontmatter `REPORT:6` self-declares "delivery is operator-performed; this document does not send itself"; `status: draft`. The artifact is delivery-ready and correctly stops the receipt at the operator. The receipt event is unreachable from this seat and is operator-owned. |
| 2 | Pre-selects NONE of R-16's three (invest / trust numbers / what-is-broken-and-cost) | **STANDS** [STRONG-own-hands] | `REPORT:158-165` explicitly disclaims all three ("does not recommend whether to invest further, tell you to trust or distrust the numbers, or rank the problems"). Grep for steer verbs returns only this disclaimer (`REPORT:160-161`). Matches `RULING:162-176` R-16 orientation-not-steering. |
| 3 | Every cost figure carries its evidence class; ~100% imputation is INFERENCE not measurement | **NARROWS** | Compliant where it counts: the cache-empty/imputation claim is class-tagged inference with a named upgrade path (`REPORT:136-139`, "Inferred but not enumerated … One authenticated call would convert this from inference to measurement") — mirrors probe §6 MODERATE ceiling (`PROBE:393`). The register never states "~100%" as measured (grep NULL), so it does **not** trip the fail condition. NARROWS: finding-2 states "currently true for effectively all of them" assertively (`REPORT:114`) with the class carried in a *different* section, not inline. |
| 4 | Two-sided: TemporalFilter ACTIVE (correctness) **and** exploitation frequency UNDETERMINED — both halves travel or neither | **NARROWS — criterion UNMET as written** | The ACTIVE/correctness half travels (`REPORT:112-115`, "can report offers as having 'moved' when they were merely created"). The UNDETERMINED-frequency half does **not** travel: grep for frequency/traffic/exercised/undetermined in the draft returns NULL. The register folds it into the blanket "None is an active incident" (`REPORT:101`), which (a) omits the probe's explicit disclosure (`PROBE:263-266` "I did **not** measure how often anyone exercises … Exploitation frequency is undetermined. ACTIVE is a statement about correctness, not about traffic"; `PROBE:357-359`), and (b) mildly OVER-claims by asserting not-an-incident where the probe states traffic is unknown. Fix is one clause; hence NARROWS not FALLS — but the criterion is not met. |
| 5 | C-3 (non-aliasing), C-5 (G4′ per number), C-6 (denominator-only) bind exactly | **STANDS** | C-3 is the document's thesis and is exemplary ("one quantity being used to answer two different questions", `REPORT:58-61`). C-5/G4′: the publishable report enumerates its error direction ("can only *overstate* quiet time, never manufacture activity", `REPORT:82-85`); the warmer's "success on any work" alias is named (`REPORT:108`). C-6: rates carry denominators (12 of 16; 324 runs; "six times a day"). Lone soft spot — "effectively all of them" states a rate without its 4,192 denominator inline — folds into the EC-3/EC-4 NARROWS, not a fresh fail. |
| 6 | Explicit what-I-could-not-determine section; body = §B UV-P register; appendix, not a separate document | **NARROWS** | The load-bearing half holds: an explicit could-not-determine section EXISTS and is **inline** (`REPORT:129-144`, "Verified directly / Inferred but not enumerated / Not yet known") — it does **not** offload to a separate doc, and it carries the two most decision-relevant unknowns (cache-emptiness inferred; team-demand unknown, `PROBE:341-355` + UV-P-2). NARROWS: it is a curated prose distillation, not the §B register reproduced as an appendix, and it **drops the query-traffic-undetermined gap** (`PROBE:357-359` gap 2) — the same omission as EC-4. |
| 7 | DV-3 discharged: no 68/68-as-completeness inherited; gate/attestation uses CORRECT and untouched | **STANDS** [STRONG-own-hands] | Grep for "68/68"/completeness in the draft returns NULL (the two "complete" hits are "completes *any* work" `REPORT:108` and "completely empty" cache `REPORT:136` — neither a completeness claim). The register touches none of the five live sites (`frames/…:73,:166,:391`, `REPORT-asr-team-brief…:205`, `DESIGN-option4-…:1188` per `BRIEF:280-285`); it does not "fix" the correct gate/attestation uses (DV-3 rider honored). |

---

## 2. NR-1 refuter sweep — each swept, nulls reported (a null is evidence)

**NR-1(a) — the §B UV-P register: each item genuinely unclosable FROM HERE, or merely unattempted?**
Result: the unknowns the register *carries* are genuine; the defect is an unknown it *omits*.
- Gap 1 (direct key count of STORIES entries, `PROBE:343-355`): **genuinely unclosable** — ElastiCache in private VPC (`nslookup` timed out) + auth token behind CR-5 STOP. Well-justified; the probe attempted the resolve and was blocked. The register correctly renders this as inference (`REPORT:136-139`).
- Gap 2 (traffic on `query/__main__.py`, `PROBE:357-359`): **decision-relevant and OMITTED from the register.** Plausibly genuinely unclosable (a `__main__.py` CLI entrypoint likely emits no centralized invocation telemetry the way the section-timelines endpoint did), **but the probe under-justifies WHY** — unlike gap 1 it names no barrier, only "not measured." This is the gap that should have travelled per EC-4; its omission is the root NARROWS.
- Gaps 3, 4, 6 (`PROBE:361-379`): unattempted but **immaterial** to an exec register (starvation onset, StoryWarmFailure step-change, lambda series) and out of this seat's decision-relevant scope. Correctly absent.
- Gap 5 (overflow threshold, `PROBE:370-375`): **resolved** — dead config, "recorded so no one re-derives it." Correctly absent.
Net: **NOT NULL** — feeds EC-4 and EC-6.

**NR-1(b) — the five DV-3 sites: is a falsified premise (68/68-as-completeness) carried as a live one?**
Result: **NULL** (a null is evidence). The register carries no 68/68 token at all (grep NULL). The five live sites are *other* artifacts (`BRIEF:280-285`), out of this register's authoring scope, and their gate/attestation uses are CORRECT and must not be touched — they aren't. Swept, absent = clean.

**NR-1(c) — "MODERATE ceiling" vs "unknown": does the register treat the ceiling as a STATED GRADE, not an absence?**
Result: **STANDS (register-correct).** The register renders the cache-empty claim as a graded inference *with a named upgrade path* — "One authenticated call would convert this from inference to measurement" (`REPORT:139`) — exactly the probe's §6 posture ("the imputation *rate* is derived … Upgrade path: one authenticated call", `PROBE:395-401`). It is treated as a grade, not an absence. Confirmed.

---

## 3. Added refuters (beyond NR-1)

**NR-ADD-1 — unverified-negative reassurance (measured negative, or inference?).**
"None is an active incident; none involves customer data exposure" (`REPORT:101`) and "Nothing has misused it, nothing external can reach it" (finding 3, `REPORT:122-123`) are stated as fact but are **absence-of-evidence, not evidence-of-absence**: the S2S "nothing misused" is not an audit of every S2S call, and "not an active incident" for finding 2 sits in tension with undetermined query traffic (NR-1a gap 2). This is precisely the alias the document claims to have cured — *"the process ran"* mistaken for *"we checked, and it was right"* (`REPORT:29-30`) — now recurring in its own reassurances. **NARROWS**: hedge to "we have no evidence of misuse." Feeds EC-3/EC-4.

**NR-ADD-2 — two-audit provenance (aliasing check).**
The draft's "Verified directly" refuser claim ("the four-hourly check runs and refuses correctly … we audited every run over a recent 24-hour window", `REPORT:44-46`, `:131-134`) is **not** in the warm-path probe. I traced it: it is sourced in `.ledge/decisions/RAILS-insight-delivery-verified-2026-08-12.md` (grep-confirmed present in corpus on refuse/reconcile/freshness-gate). The draft keeps the **24h-refuser audit** and the **324-run starvation audit** distinct — no conflation. **STANDS** — I looked for aliasing here and found none.

**Downstream watch (not a finding against the register):** `honest_contract_complete` may be vacuously True for an empty manifest (`BRIEF:287-291`, "routed, not ruled"). The register's "clears our publication bar" for the quiet-corners report (`REPORT:82-85`) rests on the *directional* argument (Asana's own timestamp, safe-direction error), which is sound **independently** of that receipt — so the echo does not undermine publishability. Flagged only so the operator does not let "clears the bar" harden into a completeness claim before the echo is resolved.

---

## 4. §A.3 receipt grammar

1. **Refuters swept, incl. nulls**: NR-1(a) NOT-NULL (gap-2 omission); NR-1(b) **NULL** (no 68/68 in register); NR-1(c) STANDS (ceiling treated as grade). Added: NR-ADD-1 (unverified negatives, NARROWS), NR-ADD-2 (two-audit provenance, STANDS/clean).
2. **The hop one past where the argument stopped, named concretely**:
   - Re-derived the starvation load-bearing figures own-hands at `PROBE:24,:39,:133,:330,:390`: 324 runs/14 days, max 8,527, first offer GID 10,617, shortfall ≥2,089, 4,192 offer tasks, entities 5–16 starved — all reconcile; the draft's "12 of 16 / 324 runs / including offers" (`REPORT:106-109`) map exactly. **STANDS [STRONG-own-hands].**
   - Hopped past the imputation inference: grep-confirmed the register states no "~100%" as measured, and the probe's §6 last row (`PROBE:393`) is the MODERATE ceiling. Class-tag correct.
   - Hopped past the "verified directly (refuser)" claim: traced its provenance to `RAILS-insight-delivery-verified-2026-08-12.md` (a *distinct* source from the probe); confirmed the draft does not alias the two audits.
3. **Refuters added beyond NR-1**: NR-ADD-1, NR-ADD-2 (above).
4. **Verdict**: **STANDS** overall (register's negatives hold; no pre-selection, no falsified premise, ceiling-as-grade), **NARROWS on EC-3/EC-4/EC-6** with corrected scope: the one additive correction is to make the *exploitation-frequency-undetermined* half travel (finding 2 + the could-not-determine section) and to hedge the unverified negatives. **EC-1 operator-pending.** No FALLS — the register does not pre-select and is not reverted.

---

## 5. PT-05 Q5.2 — which decision does this text choose?

**It chooses none.** Asked the one falsifying question — *which of {keep investing / trust the numbers / what is broken and what it costs} does this text choose?* — the register selects no answer to any of the three. It explicitly holds all three open and returns each to the reader (`REPORT:158-165`), and invites correction if any section reads as steering. **No STEER (F-E3, rung-level).** This is the criterion-2 result confirmed from the reader's chair.

---

## 6. Required corrections before operator delivery (additive; REVISE not REVERT)

1. **Make finding 2 two-sided (EC-4, blocking-as-written).** Add one clause carrying the probe's honest bound: the defect is ACTIVE as a *correctness* claim, and *how often the surface is exercised is undetermined* (`PROBE:263-266`). Do not leave "None is an active incident" to carry that half alone.
2. **Fold the query-traffic-undetermined gap into the could-not-determine section (EC-6).** It is the one decision-relevant named gap currently dropped.
3. **Hedge the unverified negatives (NR-ADD-1).** "Nothing has misused it" → "we have no evidence of misuse"; qualify "None is an active incident" as an inference where traffic is unknown.
4. **Optional (EC-3 tidy).** Move the inference class-tag inline at finding 2's "effectively all of them", so the class travels with the number rather than living one section away.

None of these reverses the register. With them applied, EC-3/EC-4/EC-6 move from NARROWS to STANDS; EC-1 remains the operator's to close on delivery.

---

## 7. Fences honored (kit §3)

- **CR-1** (Asana write classes operator-reserved): no board write, no Asana call of any kind.
- **CR-2** (`s3://autom8y-asr-verdicts`): not read, not listed.
- **CR-5** (credential material): none minted/extracted/copied/logged; encountered none. The live-hazard path in git history was not traversed (`git log -p`/`git show <sha>:` against the flagged commits was NOT run).
- **Monorepo trap (4)**: no read of `/Users/tomtenuta/Code/a8/a8/repos/autom8y`. **4b converse**: in THIS repo (autom8y-asana) the working tree is authoritative; all four subject/evidence artifacts read present from the working tree (they are gitignored/untracked and local main lags origin/main) — a seat generalizing rule 4 here would have reported them absent.
- **No client/external communication**; delivery is operator-performed. No git write/commit/push. No infra mutation.

**Self-attestation**: MODERATE ceiling overall (single rite-disjoint seat, no further corroboration); [STRONG-own-hands] only where re-derived directly — the 324-run starvation reconciliation, the DV-3-absence grep, and the no-steer grep. This reader evaluated; it did not merge and it sent nothing.

---

## DELTA PASS 2 — corrected text (2026-08-13)

*Appended by the same seat (eunomia / `verification-auditor`, rite-disjoint from
10x-dev). The frontmatter above is pass 1's. This section's grammar is the same
register-critique grammar — **STANDS / FALLS / NARROWS** — and the same ceiling:
MODERATE, except where marked `[STRONG-own-hands]`.*

> **OVERALL: Q-7 DISCHARGED-ON-CORRECTED-TEXT.**
> All four required corrections are **FAITHFULLY APPLIED**; one was applied
> *beyond* what I asked. **The EC-4 dissent is DISCHARGED** — both halves now
> travel, together, in the same finding. EC-3/EC-4/EC-6 move **NARROWS → STANDS**
> as pre-committed in §6. EC-2/EC-5/EC-7 re-tested on the final text and hold.
> **EC-1 remains operator-pending** and is the only open exit criterion.
> **No FALLS. Nothing is reverted.** Three residuals are named below — all
> non-blocking, all one-clause, none reversing any verdict.
>
> **The discharge binds to a byte-state**, not to a filename:
> `.ledge/reviews/REPORT-exec-state-of-work-2026-08-13.md`, 176 lines, 9,638 bytes,
> mtime `2026-08-13T11:18:01`, `sha256 2d703a41e915e089275262414b5489ba7b1bf146ef56d5ccb1a0f7f15b6e9c3f`.
> See §D8 for what happens if the operator edits it further (the ratification
> expects them to).

### D1 — Method, and its one honest limitation

**No pre-image of the register exists on disk.** `grep -rl` for the pass-1
pre-correction strings ("None is an active incident", "Nothing has misused it",
"clears our publication bar") returns **exactly one file — this critique**. The
draft was edited in place and nothing preserved the prior bytes. So this is a
**reconstructed** delta, not a diff. The reconstruction rests on two own-hands
checks:

**(a) Anchor arithmetic.** Every line I cited verbatim in pass 1, re-located in
the corrected text. The offsets form a monotone ladder whose every step lands on
one of the four correction sites — i.e. **the edit surface is confined to the four
places I asked for**, and the regions between them shift by a constant.

| pass-1 anchor | pass-1 line | now | offset |
|---|---|---|---|
| frontmatter "does not send itself" | :6 | 6 | 0 |
| "the process ran" / "we checked, and it was right" | :29-30 | 29-30 | 0 |
| 24-hour refuser audit | :44-46 | 44-46 | 0 |
| C-3 thesis "one quantity … two different questions" | :58-61 | 57-61 | 0 |
| "can only *overstate* quiet time" | :82-85 | 82-85 | 0 |
| **"None is an active incident"** | :101 | **100-103 — EDIT 1** | +2 |
| "'success' when it completes *any* work" | :108 | 110 | +2 |
| finding-2 headline | :112-115 | 114-115 | +2 |
| **"effectively all of them"** | :114 | **117-119 — EDIT 2** | +3 |
| **"Nothing has misused it, nothing external can reach it"** | :122-123 | **127-131 — EDIT 3** | +5 |
| "Verified directly" | :131-134 | 139-142 | +8 |
| "Inferred but not enumerated" / "One authenticated call…" | :136-139 | 144-147 | +8 |
| **"Not yet known"** | ~:141-144 | **149-155 — EDIT 4** | +8 |
| closing three-decision disclaimer | :158-165 | 169-176 | +11 |

Net +11 lines (165 → 176), fully accounted for by the four edits. `[STRONG-own-hands]`

**(b) Verbatim presence/absence sweep.** Every pass-1 quotation outside the four
edit sites is still **byte-present** (whitespace-normalised match). Every
pre-correction string I required removed is **absent**. `"68/68"` remains absent
(EC-7). `[STRONG-own-hands]`

**The limitation, stated plainly**: a *same-line-count in-place substitution*
outside my quoted anchors would be invisible to this method. I found exactly one
candidate and resolve it in **R-4** below — against myself.

### D2 — Per-correction rulings

**Correction 1 — make finding 2 two-sided (EC-4, blocking-as-written) → FAITHFULLY APPLIED.**
The UNDETERMINED half now travels in **three** places, one of them inside the
finding itself:
- `REPORT:119-121` — *"Two-sided, honestly: the flaw itself is real and present as a correctness defect, but how often it is actually hit depends on how often this query is run, which we have not measured."*
- `REPORT:100-103` — the section header, hedged, **plus a clause I did not ask for**: *"and we mark that explicitly rather than assume it is zero."*
- `REPORT:151-153` — the could-not-determine section.

Probe fidelity checked at source: `PROBE:263-266` — *"I did **not** measure how
often anyone exercises … Exploitation frequency is undetermined. ACTIVE is a
statement about correctness, not about traffic."* The register's rendering is
faithful and adds no claim the probe does not carry. `[STRONG-own-hands]`

**One hop past this edit — the inverse failure I went looking for.** "Both halves
travel or neither does" also fails if adding the UNDETERMINED half *dilutes* the
ACTIVE half. It did not. `REPORT:119-120` keeps the defect **"real and present as
a correctness defect"**, and the header's new hedge attaches to the word
*incident*, not to *defect* — `"none is a **known** active incident"` is a
statement about production impact, not about whether the flaw is live. The
"rather than assume it is zero" clause is an explicit anti-dilution guard. This
fold is **stronger** than what I prescribed.

**Correction 2 — fold the query-traffic gap into could-not-determine (EC-6) → FAITHFULLY APPLIED.**
`REPORT:151-153` against `PROBE:357-359` ("Traffic on `query/__main__.py` … Not
measured. ACTIVE in §3.2 is a correctness claim; how often the wrong answer is
actually *served* is unknown"). This was the one decision-relevant named gap the
draft dropped; it is dropped no longer. The fold **also** imported a gap I did
not ask for (finding 3's external reachability, `REPORT:153-154`) — see **R-2**.

**Correction 3 — hedge the unverified negatives (NR-ADD-1) → FAITHFULLY APPLIED on both named strings.**
- *"Nothing has misused it"* → **"We have found no evidence it has been misused"** (`REPORT:127-128`).
- *"None is an active incident"* → **"none is a *known* active incident"** (`REPORT:101`), qualified in the same sentence.
- Both pre-strings verified **ABSENT** from the corrected text.

The rewrite went further than the hedge: finding 3 now discloses that external
reachability is **unverified** — *"it sits behind our platform load balancer, but
we have not confirmed that balancer is internal-only"* (`REPORT:129-131`). I
traced that to source and it is **exactly right**: `HANDOFF-10x-dev-to-security-s2s-authz-2026-08-13.md`
UV-P-C-2 records the shared platform ALB, private-subnet placement, and that the
`internal = true/false` attribute lives in an external module *"not checked out
anywhere accessible — so UV-P-C-2 remains genuinely open. A private-subnet
placement is suggestive but not dispositive."* The register neither over- nor
under-states it. Residuals **R-1** and **R-3** attach to this same sentence.

**Correction 4 — inline the inference class-tag at finding 2 (optional, EC-3 tidy) → APPLIED.**
`REPORT:117-119`: *"Per finding 1 that history is currently missing for what we
**infer** to be effectively all offers — an inference, not a count; we did not read
every entry."* The class now travels **with** the number instead of living a
section away. This was the one correction I marked optional; it was done anyway,
and it is what moves EC-3 cleanly rather than marginally.

### D3 — The seven exit criteria, re-run against the corrected text

Criteria read verbatim from the shape's EX-1 block (`exec-insight-delivery.shape.md` §2, EX-1 exit criteria 1-7).

| # | Criterion (compressed) | pass 1 | **pass 2** | Evidence on the corrected text |
|---|---|---|---|---|
| 1 | Delivered + operator confirms receipt (C-7) | OPERATOR-PENDING | **OPERATOR-PENDING** (unchanged, not a defect) | `status: draft` holds (`REPORT:3`); frontmatter still self-declares delivery operator-performed (`REPORT:6`). Unreachable from this seat by construction. |
| 2 | Pre-selects **none** of R-16's three | STANDS | **STANDS** `[STRONG-own-hands]` | Full-document steer sweep re-run on the final text (§D5). Disclaimer intact and unmoved (`REPORT:169-176`). R-16's three read verbatim at `RULING-operator-morning-set…:162-166`. |
| 3 | Every cost figure carries its evidence class; ~100% imputation is INFERENCE | NARROWS | **STANDS** | Class now inline at the number (`REPORT:117-119`) *and* in the register of confidence (`REPORT:144-147`, upgrade path preserved). `"~100%"` and `"100%"` both grep-NULL — nothing is reported as measured that is inferred. |
| 4 | Two-sided: ACTIVE correctness **and** UNDETERMINED frequency — **both halves travel or neither** | **NARROWS — UNMET as written** | **STANDS — dissent DISCHARGED** | Three travel-sites (§D2 correction 1); ACTIVE half undiluted; probe-faithful at `PROBE:263-266`. See §D4. |
| 5 | C-3 / C-5 (G4′) / C-6 bind exactly | STANDS | **STANDS** | Re-swept every numeral in the final text: 324 runs, 24-hour window, Twelve of sixteen, six times a day, every four hours, two weeks — each carries its denominator or its scope. C-5 error-direction argument intact (`REPORT:82-85`). The lone pre-existing soft spot ("effectively all offers" without its 4,192 denominator inline) now carries its **class**, which is what EC-3 required of it. |
| 6 | Explicit could-not-determine section; body = §B UV-P register; appendix not separate doc | NARROWS | **STANDS**, with a literalist residual named | Gap 2 folded (`REPORT:151-153`); gap 1 carried as inference (`REPORT:144-147`); gaps 3/4/6 immaterial to an exec register; gap 5 resolved-and-dead (`PROBE:370-375`). **Residual, restated not escalated**: the section is a curated prose distillation, not the §B register *reproduced* as an appendix. I ruled that ground non-blocking in pass 1 (the criterion's load-bearing half — "not a separate document" — is met) and I hold that ruling rather than move the goalpost. A literalist reading still records a partial miss; closing it is one attachment and is the operator's option, not a requirement. |
| 7 | DV-3 discharged: no 68/68-as-completeness; gate/attestation uses untouched | STANDS | **STANDS** `[STRONG-own-hands]` | `"68/68"` grep-NULL in the corrected text. Completeness-token sweep returns four hits, all benign: "full reconciliation" (`:40`), "every run over a 24-hour window" (`:45` — a named denominator), "every entry" (`:119` — inside a *negation*: "we did not read every entry"), "completely empty" (`:144` — the cache, explicitly class-tagged inference). None of the five live DV-3 sites is touched. |

### D4 — Disposition of the EC-4 dissent

**DISCHARGED on the corrected text.** Stated without softening: in pass 1 I held
the criterion **UNMET as written**, and I would have held it again had the fold
been cosmetic. It was not.

What discharged it, precisely:
1. The UNDETERMINED half is now **inside finding 2** (`REPORT:119-121`), not
   outsourced to a header or an appendix — the criterion says *travel*, and this
   is the half that had to travel.
2. The over-claim that carried it before (`"None is an active incident"`) is gone,
   replaced by a hedge that names its own limit and **refuses the zero
   assumption** (`REPORT:100-103`).
3. The ACTIVE half survived the edit at full strength (§D2, inverse-failure check).

What would have kept the dissent alive, and did not occur: the frequency half
travelling **only** in the header or **only** in the could-not-determine section
(outsourcing, not travelling); or the ACTIVE half being softened to "potential" /
"theoretical" / "possible" in the act of adding the second half. Neither happened.

**The falsifier that would revive it**, handed forward: delete `REPORT:119-121`
or the *"rather than assume it is zero"* clause at `REPORT:103`, and EC-4 reverts
to UNMET. Anyone editing this document before delivery should treat those two
spans as load-bearing.

### D5 — R-16 / F-E3 orientation fence, re-tested on the final text

R-16 verbatim (`RULING-operator-morning-set-2026-08-13.md:162-166`): *"whether to
keep investing, whether to trust the numbers, and what is broken and what it
costs must all remain **available** to the reader rather than pre-selected by the
author."*

**The one question, asked again of the corrected text: which decision does this
text choose? — It still chooses none.** Full-document sweep for recommend /
should / must / advise / suggest / propose / prioritise / urge / rank / top-first
priority / "the right call" / "next step is to" returns **five hits, none
steering**: `:65` and `:127` are descriptive ("must be able to say what it
measures"; "should require a specific grant"), `:122` describes an
already-routed fix, `:154` hands the cadence decision back explicitly ("that is a
decision, not a discovery"), and `:171-172` is the disclaimer itself.

**Three sentences nearest the fence, named so the operator knows where it is thin
— each re-tested, each clears:**
- `:111-112` *"This is the widest finding and it extends beyond this project"* —
  **scope descriptor, denominator-backed** (twelve of sixteen; fleet-wide per
  Q-4's routing edge), not a priority ordering. "Widest" ≠ "first". Clears.
- `:162-165` *"has one approval gate remaining before build; the preceding gates
  cleared this week"* — **status, not a nudge**. It does not say the gate should
  clear, by whom, or when. This is the closest sentence in the document to
  decision 1 (keep investing) and it stops short. Clears.
- `:121-123` *"The fix is one change … and it is scoped and routed"* — the fix is
  already owned; nothing is asked of the reader. Clears.

**NR-ADD-3 (new refuter, specific to a corrective fold): did the added hedging
accumulate into a pre-selection of decision 2 — "don't trust the numbers"?**
Result: **NO.** The corrections are *per-number* epistemics, not a global trust
verdict, and the structure stays balanced: the "Verified directly" block leads
with four items (`:139-142`) against five hedged/unknown items (`:144-155`), and
the one publishable report still **survives** the bar (`:82-85`). Nothing says
"treat our outputs as unreliable." Giving the reader a per-number basis to decide
trust is the opposite of deciding it for them — which is what R-16's own recorded
divergence says (*"that would have pre-selected one decision and framed the other
two out"*). Fence holds.

**Verdict: no STEER. F-E3's rung-level failure is not triggered. EC-2 STANDS.**

### D6 — Residuals introduced or surviving at the edit sites (one hop past each edit)

All four are **non-blocking**. None reopens a criterion. None is a required
correction. They are listed because folding is editing.

**R-1 — one absolute negative survives in a sentence whose siblings were hedged.**
`REPORT:100-101` still opens *"None involves customer data exposure"* with no
qualifier, in the very sentence where the incident claim was hedged and two
sentences from where finding 3 concedes external reachability is unverified.
**I tested it substantively rather than stylistically**: finding 1 is a refresh
starvation, finding 2 is wrong internal movement data, finding 3 is a *write*
authorisation gap using a server-side credential (`HANDOFF…s2s-authz…` §1a — five
write classes, no read/disclosure path). **No disclosure vector in any of the
three**, so the claim is *true*; it is only un-hedged. It is also **scoped** — "Three
findings … None" ranges over the three, so it does not silently absorb the
separately-tracked credential hazard. Grade: wording note, not a truth defect.

**R-2 — the voluntary import is asymmetric.** The fold imported UV-P-C-2 (network
reachability) into "Not yet known" but not UV-P-C-1 (*whether a fleet seat can
obtain a valid service JWT by documented patterns* — `HANDOFF…s2s-authz…` §2,
also OPEN), and registered no gap for "we did not audit call history" behind
*"We have found no evidence it has been misused."* Importing one half of a
two-part open question can read as completeness. **Materiality is low**: the
register already concedes the stronger inside-exposure statement in the finding
itself — *"Any service inside our fleet that can authenticate can reach write
operations that should require a specific grant"* (`REPORT:126-127`) — so nothing
is over-claimed as safe. One clause closes it if the operator wants symmetry.

**R-3 — "prevents" over-reaches for a process fence.** `REPORT:131-132`: *"a
standing operational rule currently prevents the writes in question."* CR-1
proscribes; it does not prevent (`HANDOFF…s2s-authz…` §1: CR-1 "is currently the
**only** control"). **Discharged in the same breath** by the clause that follows —
*"but that rule is procedure, not software"* — which is precisely the right
correction and is the sentence's point. Noted, not escalated.

**R-4 — against myself.** Pass 1 §3 quoted the register as *"clears our
publication bar"*; the corrected text at `:82` reads *"**survives** our
publication bar"*, and `:82-85` sits inside the **zero-offset** region whose
neighbours are byte-identical to my pass-1 quotations. Two readings: an in-place
one-word edit outside the four corrections, or **my own loose quotation in pass 1**
(blending `:82`'s "our publication bar" with `:96`/`:159`'s "clears the bar").
Parsimony favours the second and I record it as **my imprecision**. Immaterial
either way: neither verb is a completeness claim, and the pass-1 downstream watch
(*do not let "clears the bar" harden into a completeness claim before the
`honest_contract_complete` echo is resolved*) survives verbatim — "clears the bar"
still appears at `:96` and `:159-160`. **That watch is carried forward
unchanged.**

### D7 — NR-1 re-sweep (nulls reported; a null is evidence)

- **NR-1(a)** — the §B UV-P register. Pass 1: NOT-NULL (gap 2 omitted). **Pass 2: NULL** — the omission is closed (`REPORT:151-153` ↔ `PROBE:357-359`); gap 1 remains genuinely unclosable from here and is correctly rendered as inference (`PROBE:343-355` ↔ `REPORT:144-147`).
- **NR-1(b)** — falsified 68/68-as-completeness carried as live. **NULL, still** (grep-NULL; five live sites untouched).
- **NR-1(c)** — MODERATE ceiling as a stated grade, not an absence. **STANDS, still** — the upgrade path sentence is byte-present and unmoved (`REPORT:147` ↔ `PROBE:393-401`).
- **NR-ADD-1** (unverified negatives) — **discharged** on both named strings; residuals R-1/R-2/R-3.
- **NR-ADD-2** (two-audit provenance, `RAILS-insight-delivery-verified-2026-08-12.md`) — **re-checked: still no aliasing.** The 24-hour refuser audit (`:44-46`) and the 324-run starvation audit (`:141`) remain distinct and both are byte-unchanged.
- **NR-ADD-3** (hedge-accumulation as covert pre-selection) — **NULL** (§D5).

### D8 — Governance notes for the operator (not findings against the register)

1. **Two artifacts already record the upgrade this section is the first
   rite-disjoint basis for.** `GATE-pt05-fan-in-2026-08-13.md:75-84` (main-thread
   addendum) and `HANDOFF-exec-wave-close-2026-08-13.md:69` both state
   *"NARROWS folded → STANDS"* and attribute it to the EX-1 critic. Until this
   section existed that was the **author rite attesting the disjoint reader's
   verdict on its own corrections**. It is now backed. The receipt-grammar fix is
   one citation: those rows should point at
   `.ledge/reviews/CRITIQUE-exec-register-2026-08-13.md § DELTA PASS 2`, not at
   the pass-1 verdict.
2. **The ratification's own ordering is now restored.**
   `RULING-operator-exec-defaults-ratification-2026-08-13.md` (§"Also ratified by
   scope") says the draft *"is **NOT approved for delivery** … it now goes to its
   Q-7 second reader, then to the operator for edit and personal delivery."* The
   author-rite fold was inserted between reader and operator; this pass closes
   that loop. **The operator's own edit still comes next, and is expected.**
3. **What the discharge does and does not travel to.** It binds the byte-state in
   the header of this section. If the text changes again before delivery, the
   operator can self-check without another pass: *(a)* are `REPORT:119-121` and
   the "rather than assume it is zero" clause still present (EC-4)? *(b)* does the
   new text contain any of recommend / should / rank / prioritise addressed **to
   the reader** (EC-2)? If both answers are good, the discharge carries. If either
   fails, it does not, and this seat is re-runnable in minutes.
4. **Product-altitude gate did not fire, and that is correct.** There is no
   `.know/telos/exec-insight-delivery.md`; the sibling family telos
   `.know/telos/asana-native-insight-delivery.md` is `status: PROPOSED` and Q-5
   ruled it stays that way. Per `telos-integrity-ref` §3 Gate B the close-gate
   precondition is unmet, so **no `-ADVISORY` tier verdict is emitted by this
   pass** — and none should be read into it. The grammar here is the
   register-critique grammar only (STANDS / FALLS / NARROWS), distinct from both
   the execution-altitude PASS/PARTIAL/FAIL and the product-altitude
   `*-ADVISORY` tiers.

### D9 — Fences honored, and self-attestation

- **CR-1**: no board write, no Asana call of any kind. **CR-2**: `s3://autom8y-asr-verdicts` not read, not listed.
- **CR-5**: no credential material minted, extracted, copied, quoted or transcribed. I encountered a **reference** to the live unrotated-PAT hazard while reading the security handoff's fence block — **path and fact only**, the history objects were not traversed and are not restated here.
- **No git operations of any kind** this pass (no `log`, no `show`, no `diff`, no write). Tooling was confined to `ls`/`find`/`grep`/`sed`/`wc`/`stat`/`shasum` and a read-only Python string check.
- **Monorepo trap**: `/Users/tomtenuta/Code/a8/a8/repos/autom8y` not read. **4b converse** re-affirmed: in this repo the working tree is authoritative — the register, the probe, the shape and the handoffs are untracked/local and read present from the working tree; local `main` lags `origin/main` and a seat generalising the monorepo rule here would have wrongly reported them absent.
- **No client or external communication. Delivery remains operator-performed (C-7).** This reader evaluated; it wrote exactly one file (this one); it sent nothing.

**Self-attestation.** MODERATE ceiling overall — one rite-disjoint seat, no further
corroboration, and a delta pass is a *narrower* instrument than a first read.
`[STRONG-own-hands]` only where re-derived directly this pass: the anchor-arithmetic
edit-surface reconstruction, the verbatim presence/absence sweep, the probe-fidelity
re-derivation at `PROBE:263-266` / `:357-359` / `:393`, the full-document steer
sweep, and the completeness/denominator sweeps. **Named limitation, so the operator
can weigh it**: no pre-image of the register survives, so the delta is reconstructed
rather than diffed; a same-line-count in-place substitution outside my quoted anchors
would be invisible to this method, and I have recorded the single candidate instance
against myself at **R-4**.
