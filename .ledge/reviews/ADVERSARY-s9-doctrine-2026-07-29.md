---
type: review
status: rendered
artifact_id: ADVERSARY-s9-doctrine
title: "Adversary review — S9 substrate constitution + companion memory/teeth plan (WAVE-2)"
challenger_agent: arch-adversary
initiative: substrate-v2-epoch
sprint: S9
date: "2026-07-29"
iter: 2   # DELTA re-challenge appended; iteration 2 of 2 (cap)
targets:
  - autom8y-asana-wt-w2-s9/.ledge/decisions/CONSTITUTION-substrate-invariants-DRAFT-2026-07-29.md
  - autom8y-asana-wt-w2-s9/.ledge/decisions/PLAN-substrate-doctrine-memory-and-teeth-DRAFT-2026-07-29.md
grounded_against:
  - .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md (P3/P11/P12)
  - .ledge/specs/TDD-substrate-v2.md (§3 RC constructions + §11 build-notes; read in full, 638 lines)
  - .ledge/decisions/DP-3-consumer-contracts.md (§Ratification record 2026-07-29)
  - .know/scar-tissue.md (2026-07-23 regen)
scope_note: "WIDE per pythia FORK-W4 — spans the doctrine AND the folded remediation-planner scope (memory plan + teeth register). Author is structure-evaluator as GAP-PROXY."
verdict: PASS   # FINAL (iter-2 DELTA); iter-1 verdict was PASS-WITH-CONDITIONS — preserved in body
conditions_must_fix_before_landing: [MF-1, MF-2, MF-3, MF-4]
conditions_advisory: [A-1, A-2, A-3, A-4]
evidence_grade: MODERATE
evidence_grade_rationale: "Self-assessment cap per self-ref-evidence-grade-rule; all disk-state claims below carry direct-probe receipts (SVR discipline)."
arch_ref_citations:
  - "AV:SRC-001 Messick 1989 (P-01 construct validity; P-08 construct underrepresentation) — assessment-methodology"
  - "AQ:SRC-010 Cohen 1960 (rite-disjoint challenger requirement) — assessment-methodology"
---

# ADVERSARY — S9 doctrine + companion plan

## Verdict

**PASS-WITH-CONDITIONS.** No law misrenders its ratified RC construction; no fork ruling is
reversed or invented; no memory transition retires a guard before its guarded class dies; both
surface items are correctly operator-routed, not self-ratified. Four MUST-FIX-BEFORE-LANDING
conditions (all cheap, none structural — they gate the post-S8-green landing PR, not this wave)
and four ADVISORY notes. The sharpest finding (MF-1) is the doctrine breaching its own OQ-2
honesty discipline in exactly one place.

## Axis 1 — FIDELITY (per-law verdicts against TDD §3 + DP-3)

| Law | Verdict | Note |
|-----|---------|------|
| RC-A | FAITHFUL | CAS/If-Match, collision-free version-IDs, `ArtifactMissing` — all transcribe C3/[H5]/[H6] exactly. |
| RC-B | FAITHFUL + flag A-1 | MIN-fold, probe-cannot-freshen, deleted re-stamp bridge = C1/[H3] verbatim. The SLA-governance sentence transcribes TDD §11 C8's AV-3 watch line — but see A-1: it states as law a mechanism C8 has NOT yet designed (CARRY, operator-due at S8). |
| RC-C | FAITHFUL | The OQ-2 honest split (omission BY-CONSTRUCTION / explicit-member FAIL-LOUD) is carried exactly; registry-derived servable set, coerce-or-refuse — C6/[H4] verbatim. |
| RC-D | FAITHFUL | SUNSET_AFTER + extension-requires-ruling is C11, which TDD §11 EXPLICITLY routes to S9 ("one doctrine line at S9/S11") — carrying it is instructed, not scope creep. |
| RC-E | FAITHFUL | ValidationReceipt-OR-ordering-test disjunction preserved as the undecided C9 carry, correctly not pre-resolved. |
| RC-F | FAITHFUL | Two-sided expected-set (C7), heartbeat/completeness split ([H20]), division-of-labor advisory, C10 cutover obligation — all transcribed. Generalizing C10 to fleet law is legitimate P12 doctrine extraction. |
| F5-5 | FAITHFUL | Matches DP-3 §Ratification record exactly (424+Retry-After+SLI ruling; RATIFIED as P11 law; supersession EXECUTED). The "proving-ground shape, not the fleet-universal law" quarantine of the 424 realization is exemplary portability discipline. |

**MF-1 (FIDELITY breach — strengthen-by-mislabel).** Constitution §2 closing: "no result-cache
above the freshness gate — each such absence is a broken v1 invariant made **unconstructable**,
not guarded." Plan §2 deliberately-not-added entry 3: "**forbidden by construction**." The TDD's
word is **FORBIDDEN** — a frozen seam CONTRACT ([H16]/C2: "caching of ServedNumber/Provable
results above the gate is FORBIDDEN"), never a construction claim. Inside the package the
bytes-only tier IS constructive, but a consumer memoizing a `Provable` is trivially constructable;
AV-2's closure is contract-freeze + build-time adversarial review (P7), not unconstructability.
This is precisely the mislabel class the doctrine's own RC-C/OQ-2 discipline forbids ("no silent
BY-CONSTRUCTION on a runtime guard") — a sibling repo applying the template would believe no
vigilance is needed at its adapters. **Fix**: relabel both sites: "forbidden by frozen seam
contract ([H16]/C2), review-guarded at build — the built-in tier is constructive (bytes below the
gate only); consumer-side memoization is the disclosed residue."

## Axis 2 — TEMPLATE-APPLICATION BAR (P12)

The bold LAW paragraphs are portable: no S3, no parquet, no asana registry names appear in any of
the seven law statements (RC-B correctly abstracts [H1]'s parquet-independence to "value-bytes,
canonicalized"; F5-5 quarantines the 424 wire shape). A sibling could reconstruct the guarantees
from the laws as written. One smuggled assumption, factually safe today but unscoped:

**A-2 (ADVISORY).** The construction/floor bullets and the entire §2 teeth table assume Python
("Python has no compile step", mypy-strict, `typing.assert_never`, import-layer lint) as fleet
fact. Probe: `autom8y-data/pyproject.toml` EXISTS, `package.json` absent; same for `autom8y-ads`
— the census siblings ARE Python, so the assumption holds at authorship. Add one scoping line:
"fleet substrate surfaces are Python at census date; a non-Python surface translates 'mypy-strict'
to 'strict static type-checking enforced in CI', 'assert_never' to its exhaustiveness-check
equivalent." Cheap future-proofing of the template kit.

## Axis 3 — TEETH AUDIT (P3/P11)

Per-tooth: **T1 mypy-strict** — construction-unreachable TRUE (no compile step); repo-wide but it
is the type-checking SUBSTRATE that makes type-level constructions real, not a guard suite;
pre-existing, honestly declared. PASS. **T2 exhaustiveness** — TRUE (sum type cannot force arm
handling); targeted at `ServedNumber` consumers; net-new honestly declared (zero uses per PE
grep). PASS. **T3 import-forbid** — TRUE (no module privacy in Python); targeted. PASS. **T4
SUNSET_AFTER** — the canonical case, verbatim from RC-D/C11. PASS. None of the four is a blanket
suite in disguise. Deliberately-not-added entries 1 (call-site guard), 2 (query-gated alarm), 4
(blanket suite): all correctly subtracted per RC-C/RC-F/P11 — none is actually needed. Entry 3
carries the MF-1 mislabel (right conclusion — no guard — wrong rationale).

**MF-2 (missing disposition for a construction-unreachable residue).** "Who may change
`sla_seconds`" is not a code property — the SAME unreachable class as T4's extension-ruling
(both are governed-act-vs-quiet-edit hazards). TDD AV-3 names the stake: "an unreviewed 14-day
SLA re-serves the wound with a green proof — SLA governance is the whole truth-content of RC-B."
Yet the §2 register gives this residue neither a tooth nor a deliberately-NOT-added entry — it
appears only in §3 cross-rite observations. By the register's OWN three-check logic, every
construction-unreachable residue must be dispositioned in §2. **Fix**: add either a fifth row
(e.g., an `sla_seconds` diff in the registry requires a ruling reference, the exact C11 pattern)
OR a recorded deliberately-not-added entry: "no SLA-diff tooth — governance-owned per C8,
operator rules by the S8 gate; revisit post-ruling." Either satisfies; silence does not.

**A-3 (ADVISORY).** C9's fallback branch (a discriminating swap-before-validate ordering test if
the ValidationReceipt capability is declined at S4) is a conditional tooth-shaped enforcement not
noted in the register. One line noting the S4 contingency prevents a future pass reading the
four-row register as closed.

## Axis 4 — MEMORY-PLAN AUDIT

**Direction-of-danger: CLEAN.** No transition retires a guard before its class dies: SEAM1 test
cluster green until S11; FRESH-001 T11-T16 green until v1 deletion; ADR-006 governs v1 until
cutover (marked superseded only THEN); DFR-001 lineage-only (probe: zero `DFR` hits across
`tests/`+`src/` — consistent with "no live guard to flip"). Serve-stale row verified EXECUTED:
`ADR-serve-stale-within-bound-2026-06-03.md` frontmatter carries
`superseded_by: DP-3-consumer-contracts` + `superseded_date: 2026-07-29` (direct read).

**MF-3 (silent casualty in the supersession chain).** `ADR-seam1-entity-identity-key.md` EXISTS
(probe: status `draft`, `supersedes: []`, no `superseded_by`) — it is the v1 SEAM-1
entity-identity key contract, i.e. the identity paradigm `ArtifactId`/RC-A/RC-C replaces
wholesale at cutover. It appears in the TDD's `related_artifacts` yet has NO row in the plan's
§1 transition table. At S11 it dies as an implicit casualty of a seam invariant — the exact
AC-03 silent-supersession class DP-3 dissent item 3 made this initiative guard against.
**Fix**: one staged row — "ADR-seam1-entity-identity-key | v1 entity-identity keying | subsumed
by RC-A + RC-C (ArtifactId) | staged now, marked superseded at cutover/S11; governs v1 until
then." (Deeper v1 lineage, e.g. TDD-UNIFIED-DF-PERSISTENCE-001, may ride the same sweep at the
author's judgment; only the seam1 ADR is load-bearing enough to condition on.)

## Axis 5 — SELF-CONFORMANCE

The plan self-applies RC-D to its transitions (event-bound to cutover/S11 — legitimate forcing
functions, since S11 is the epoch's scheduled extinction event). Evidence grades: both artifacts
correctly cap MODERATE with rationale. Honesty discipline: self-applied everywhere except MF-1.

**MF-4 (RC-D self-conformance gap — the doctrine's own hold has no sunset).**
"LANDING-HELD-TO-S8-GREEN" is a gate with no expiry and no red-path disposition. If S8 stalls or
renders red indefinitely, the DRAFT persists as an undated open lever — the immortal-bridge shape
applied to the doctrine about immortal bridges. RC-D's own law: a held-open state needs a forcing
function or an operator door. **Fix**: one clause in the constitution's landing banner: "If the
S8 gate has not rendered green by {S8's scheduled close + bounded grace, or epoch re-plan event},
this hold escalates to an operator ruling (land-as-doctrine-of-record / revise / withdraw) rather
than persisting silently." Cheap now; structurally required of a document that legislates
forcing functions.

## Axis 6 — SURFACE-ITEM CHECK

**SURFACE-i (P11 `.a8/knossos`): CORRECTLY FRAMED, probe REPLICATED.** Independent re-probe:
`ls /Users/tomtenuta/Code/a8/.a8/knossos` → "No such file or directory"; `.a8/` contains only
`autom8y/`. The draft invokes P11's own hedge ("if wrong, amend here"), recommends the amendment
to the operator, and does NOT amend the charter itself. The de-facto home (`.ledge/decisions/`,
where R24-R34 live) is used on pythia UV-P-4 authority with the item surfaced — acceptable.
**A-4 (ADVISORY)**: add one sentence making the §3 home explicitly provisional-on-operator: if
the P11 amendment rules a DIFFERENT home, the landing PR relocates. Closes the residual
self-ratification reading.

**SURFACE-ii (T3 same-repo/disjoint-files): CORRECTLY FRAMED.** A framing correction for the
operator's model; changes no artifact location this wave; ruled by pythia UV-P-4, not
self-ratified. PASS.

## Conditions register

| ID | Tag | One-line |
|----|-----|----------|
| MF-1 | MUST-FIX-BEFORE-LANDING | Relabel result-cache absence: contract-forbidden ([H16]/C2) + review-guarded, NOT "unconstructable"/"by construction" (CONST §2 closing; PLAN §2 entry 3). |
| MF-2 | MUST-FIX-BEFORE-LANDING | Disposition the SLA-governance residue inside the §2 teeth register (fifth C11-pattern tooth OR recorded not-added entry routing to C8/operator-by-S8). |
| MF-3 | MUST-FIX-BEFORE-LANDING | Add ADR-seam1-entity-identity-key staged supersession row to PLAN §1 (subsumed by RC-A/RC-C; executed at cutover/S11). |
| MF-4 | MUST-FIX-BEFORE-LANDING | Name a sunset/escalation for the LANDING-HELD-TO-S8-GREEN hold (RC-D applied to the doctrine itself). |
| A-1 | ADVISORY | RC-B honest floor: cite the "governed act" mechanism as C8-pending (operator-due S8), not as an existing mechanism. |
| A-2 | ADVISORY | Scope the Python/mypy fleet assumption with one translation line (census: data+ads are Python today — receipted). |
| A-3 | ADVISORY | Note C9's conditional ordering-test fallback as an S4 contingency in the teeth register. |
| A-4 | ADVISORY | Mark the §3 constitution-of-record home provisional-on-operator-amendment of P11. |

## Falsification of this verdict

Each condition names its own reversal: MF-1 dissolves if the author produces ratified TDD text
claiming the C2 prohibition as by-construction (none found in 638 lines — the TDD says
"FORBIDDEN"); MF-3 dissolves if ADR-seam1-entity-identity-key is shown dispositioned elsewhere
(its frontmatter shows `supersedes: []`, no `superseded_by`, status `draft` — direct read);
MF-2 dissolves if a §2 disposition for the SLA residue exists that I missed; MF-4 dissolves if
an S8-red escalation path is recorded in the wave-2 dispatch specs. The verdict upgrades to
PASS when the four MF edits land in the drafts (a DELTA-scope re-challenge per
critique-iteration-protocol §4 suffices; iteration 2 of 2). It would REVISE TO BLOCK only on
evidence that a law materially deviates from its ratified construction — no such evidence
exists; every law traced to its TDD §3 / DP-3 source verbatim or with faithful abstraction.

Self-assessment cap: MODERATE (self-ref-evidence-grade-rule). Challenges grounded in
assessment-methodology P-01 (construct articulated per law) and P-08 (the MF findings are
underrepresentation-of-residue findings, not invented obligations).

---

# ITERATION-2 — DELTA re-challenge (2026-07-29, PR #279 head 918c3324)

**DELTA-scope attestation** (critique-iteration-protocol §4): this critique is DELTA-ONLY.
Evaluated: (a) MF-1..MF-4 resolution, (b) A-1..A-4 integration, (c) new surface introduced by
the +49/−7 edits. NOT re-opened: the seven per-law fidelity verdicts, the T1-T4 tooth gates,
memory-plan rows 1-4/6, and both surface items — all interrogated and passed at iteration 1.
This is iteration 2 of 2; the cap is exhausted with this verdict.

## MF resolution

| ID | Status | Evidence |
|----|--------|----------|
| MF-1 | **RESOLVED** | CONST §2: result-cache absence REMOVED from the "unconstructable" closing list and given a dedicated "One honest exception" paragraph — frozen seam contract ([H16]/C2 FORBIDDEN), bytes-below-gate half constructive, consumer memoization named as the disclosed residue, closed by build-time adversarial review (P7), explicitly NOT by-construction per the doctrine's own OQ-2 rule. PLAN §2 entry 3 relabeled identically. The prohibition itself is unchanged — enforcement label corrected, law not weakened. |
| MF-2 | **RESOLVED** | PLAN §2 gained a fifth deliberately-NOT-added entry: "No `sla_seconds`-diff tooth yet — NOT-added-pending-C8", same-class-as-T4 analysis, named future C11-pattern tooth (diff-requires-ruling), revisit trigger bound to the C8 ruling. The register's own three-check logic is now satisfied for every construction-unreachable residue. The rationale correctly invokes design-choice-masquerading (SVR row-7) for why the tooth cannot be asserted against an undesigned registry mechanism. |
| MF-3 | **RESOLVED** | PLAN §1 gained the ADR-seam1-entity-identity-key row: subsumed by RC-A+RC-C (`ArtifactId`), staged now, superseded at cutover/S11, governs v1 until then — carrying the direct-read frontmatter facts (`status: draft`, `supersedes: []`, no `superseded_by`) and naming the AC-03 class. Direction-of-danger clean: nothing retires early; identical staging pattern to the ADR-006 row. TDD-UNIFIED-DF-PERSISTENCE-001 noted as same-sweep candidate, correctly not conditioned on. |
| MF-4 | **RESOLVED** | CONST banner gained "Hold sunset (RC-D self-applied)": S8-RED escalates unconditionally; not-green-by-S8-checkpoint escalates to an operator ruling with three named dispositions (land / revise / withdraw). The checkpoint date is operator-set at wave-2 fan landing — honest deference (the draft cannot self-ratify the S8 date), and the RED arm is unconditional, so no silent-persistence path remains. |

## Advisory integration

A-1 (RC-B honest floor now discloses "governed act" as C8-pending, operator-due S8 — the
obligation stands as law, the mechanism honestly marked undesigned): SANE. A-2 (fleet-portability
scope paragraph with the census probe receipt + mechanism-not-law translation mappings; correctly
notes the unreachable *reasons* are language-general): SANE. A-3 (C9 contingency recorded; the
register explicitly declared not-closed pending the S4 capability decision): SANE. A-4 (§3 home
declared provisional-on-P11-amendment; landing PR relocates on a different ruling): SANE.

## New-surface check (edits-introduced defects)

None verdict-driving. The edits touch no LAW paragraph except RC-B's honest floor (an honesty
disclosure, not a weaken); no ratified construction is altered; the remaining three items in the
CONST §2 "unconstructable" closing list (call-site guard, query-gated alarm, re-consolidation
step) are genuinely construction-subtracted. One cosmetic residual, non-blocking: PLAN §4 still
reads "adversary-review pending" while the CONST banner reads "iter-1 ... MF-1..MF-4 applied" —
accurate at edit time, stale after this verdict; the post-S8-green landing PR may point both at
this report's final verdict. (ADVISORY-residual; does not gate.)

## FINAL VERDICT: PASS

Per the iteration-1 falsification pathway, verbatim: "The verdict upgrades to PASS when the four
MF edits land in the drafts." They landed — genuinely, not cosmetically: each edit engages the
finding's substance (relabel with disclosed residue; residue dispositioned with named future
tooth; staged supersession row with direct-read receipts; sunset with unconditional RED arm).
Zero regressions on iteration-1-accepted surface. Gate clears; the drafts are
adversary-cleared for the post-S8-green landing PR (landing remains held by the S8 gate + the
MF-4 sunset clause, which is the drafts' own discipline, not this review's).

Iteration cap: 2 of 2 exhausted. No third critique exists for this handoff-slug.
Self-assessment cap: MODERATE (self-ref-evidence-grade-rule).
