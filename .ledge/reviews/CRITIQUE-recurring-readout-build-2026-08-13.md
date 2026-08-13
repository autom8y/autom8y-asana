---
type: review
status: accepted
artifact_id: CRITIQUE-recurring-readout-build-2026-08-13
initiative: exec-insight-delivery (asana-native-insight-delivery)
sprint: EX-5 (WS-2 — GENERATION BUILD limb; EXIT HELD pending operator Q-2)
rite: eunomia (rite-disjoint critic)
critic_seat: verification-auditor
subject_author_seat: 10x-dev / principal-engineer (DISJOINT — eunomia != 10x-dev; Axiom-1 satisfied)
subject_worktree: .knossos/worktrees/ex-5-recurring-readout-gen (branch ex-5-recurring-readout-gen, off main 164382c0 = EX-4 schema)
subjects:
  - src/autom8_asana/readout/item_1a.py
  - src/autom8_asana/readout/template.py
  - src/autom8_asana/readout/generation.py
  - src/autom8_asana/readout/__init__.py
  - tests/unit/test_readout_generation.py
  - tests/fixtures/readout/{rows_response_item1a.json, rows_response_item1a_truncated.json, PROVENANCE.md}
date: 2026-08-13
evidence_grade: MODERATE (rite-disjoint attestation cap; self-ref-evidence-grade-rule). STRONG only on the own-hands mechanical re-derivations explicitly marked [STRONG — own-hands] (uncached test run, own-construction two-sided join teeth, content_hash recompute, DF-1 source+transitive isolation).
build_limb_verdict: CONCUR-WITH-FLAGS — no BLOCK. Code is LANDABLE. One design-completeness DEFECT (DF-1 guard-token blind spot) + one residual confirmation (coarse swap teeth, delivery-side/out-of-scope).
landable: YES (the code) — EXIT correctly HELD on operator Q-2 (C-9); this build is NOT EX-5's exit.
fences_honoured: CR-1, CR-2, CR-5 (no credential call, no s3 read, no forbidden git show); monorepo-trap (subject is autom8y-asana worktree, NOT the divergent autom8y sibling — 4b converse, this tree authoritative); C-9 (cadence UNRULED, EXIT held); no infra mutation; no git write/commit/push.
---

# CRITIQUE — the recurring exec readout (EX-5 GENERATION BUILD)

Rite-disjoint critic: **eunomia / verification-auditor** (Bash-bearing, dual-altitude).
Author: **10x-dev / principal-engineer**. Disjointness holds (Axiom-1). This
artifact carries the adversarial verification the wave cannot route to
qa-adversary (qa-adversary is 10x-dev native → would break rite-disjointness).
Every load-bearing claim below was re-derived **own-hands** in the worktree with
`PYTHONPATH="$PWD/src"` (venv editable-install otherwise resolves `autom8_asana`
to the MAIN tree — verified the import resolves to
`.knossos/worktrees/ex-5-recurring-readout-gen/src/autom8_asana/…` before every
probe). The author's receipts were treated as CONTEXT, never inherited as
EVIDENCE (dispatcher-critic-degeneracy guard).

**Scope.** The generation BUILD over SYNTHETIC data. The live worked render (exit
criterion 1, a real figure from a real call) is EXIT-HELD, operator/credential-
gated (CR-5) — assessed only as *specified/mechanised*, not fired. No
authenticated call was made.

---

## §1 — Verify-item disposition (own-hands)

| # | verify item | disposition |
|---|---|---|
| 1 | Re-run tests UNCACHED; confirm 44 (29 new + EX-4's 15) | **PASS** — `44 passed in 0.21s`, `-p no:cacheprovider`; 29 collected in test_readout_generation.py (27 `def test_` + the DF-1 scan parametrized ×3), 15 in test_rung_receipts.py |
| 2 | `report_generated ⋈ EX-4` GREEN, two-sided, OWN construction | **PASS** — POSITIVE `satisfied`/`observable`; NEGATIVE `human_in_loop=True → not_observable/human_in_loop`; SWAP `block_count → content_hash_mismatch`; plus `assembled_by=human → assembled_by_human` and delivery-only `→ generation_provenance_absent`. Teeth built fresh, not inherited. |
| 3 | content_hash is REAL (EX-4 CONCERN-1 discharge); structural constants | **PASS** — real 64-hex sha256 over canonical block bytes, recomputed own-hands to the same digest; deterministic; flips on seq/time/payload delta; `assembled_by`/`human_in_loop` are **module constants** — `render()` has no such kwargs and raises `TypeError` if passed them. Replaces EX-4's stub `"sha256:abc"` + schema default `""`. |
| 4 | DF-1 has teeth (AST import-scan FAILS on temporal/section_timelines/story, PASSES clean) | **PASS-WITH-FLAG (CONCERN)** — property holds own-hands (source-level + readout-adds-nothing); scan is two-sided. **DEFECT**: the FORBIDDEN token set is blind to the **plural `stories`** module — the actual story-cache read surface. §4 below. |
| 5 | No live/authenticated call, no Asana write, no monorepo change | **PASS** — zero network/auth/write surface in the readout package (grep clean); fixtures declared SYNTHETIC (PROVENANCE.md); scope confined to 3 new untracked paths in autom8y-asana; `git diff HEAD` empty (nothing on top of EX-4 164382c0); no autom8y sibling touch. |

**Hygiene (own-hands):** `ruff check` → *All checks passed*; `mypy` → *no issues
found in 4 source files*.

---

## §2 — The receipts

**R1 — tests UNCACHED [STRONG — own-hands].**
`python -m pytest tests/unit/test_readout_generation.py tests/unit/test_rung_receipts.py -p no:cacheprovider -q`
→ `44 passed in 0.21s`. Collect-only split: 29 / 15. The author's 44 (29 new +
EX-4's 15) is confirmed. EX-4's 15 passing inside the 44 is the test-preservation
receipt: the build is purely additive (no existing source or test file edited —
`git status` shows only untracked new paths), so no pre-existing test could
regress and none did.

**R2 — two-sided limb-(a) join, OWN construction [STRONG — own-hands].**
I drove EX-4's `run_query` over occurrences I generated fresh (not the author's
`_generate`/`_delivery_for` helpers):
- POSITIVE — two machine occurrences → `status=satisfied`, `observable_occurrences=2`, every receipt `observable` / reason `None`.
- NEGATIVE — `{**report_generated, "human_in_loop": True}` → `not_yet_observed`, reason `human_in_loop`.
- NEGATIVE₂ — `assembled_by="human"` → reason `assembled_by_human` (distinct branch).
- SWAP — delivery `block_count = generated + 7` → reason `content_hash_mismatch`.
- PROV-ABSENT — delivery only → reason `generation_provenance_absent`.
All five branches of `_classify` (join.py:48-80) fire as designed; the negative
side genuinely rejects. This is the *did-a-human-touch-this* claim proven with
two-sided teeth.

**R3 — the REAL content_hash [STRONG — own-hands].**
`content_hash_of(blocks)` = `"sha256:" + sha256(json.dumps(blocks, sort_keys=True,
separators=(",",":"), ensure_ascii=False))`. I recomputed the canonical digest
independently and it equalled both `occ.content_hash` and
`occ.report_generated["content_hash"]` (`sha256:f5909b2b…`). Deterministic across
two generations of the same inputs; flips on a single-character block mutation and
on seq/time deltas. `EX-4 GenerationReceipt.from_event(...).content_hash` carries
the real, non-empty digest (≠ schema default `""`). `assembled_by`/`human_in_loop`
are `generation.py:72-73` module constants; `inspect.signature(render)` has no
`human_in_loop`/`assembled_by` parameter and passing either raises `TypeError` —
the "no human assembled it" claim is structural, not call-site-settable.

**R4 — DF-1 independence holds own-hands [STRONG — own-hands].**
Direct-import AST scan re-derived: `generation.py`/`item_1a.py`/`template.py` all
PASS clean; injecting `from autom8_asana.query.temporal import TemporalFilter`
FAILS, injecting `section_timelines` FAILS — the scan is two-sided. Transitive
isolation: bare `import autom8_asana` *already* pulls
`cache.integration.stories` + `models.business.section_timeline` + `models.story`
because the top `__init__.py` is **eager** (`:22` `AsanaClient`, `:89` `models`);
importing the readout leaves adds **ZERO** forbidden-root modules on top of that
universal baseline. So the substrate presence in `sys.modules` is a whole-repo
eager-load artifact, NOT the readout path reaching the substrate. DF-1 is a
source-level property (the code never imports or calls temporal/section-timelines/
story-cache), and at that altitude it holds.

**R5 — no live surface [STRONG — own-hands].**
`grep -rnE "boto3|requests|httpx|\.post\(|credentials|create_task|slack|send_blocks"
src/autom8_asana/readout/` → none. `render()` is a pure function over an in-memory
dict; the emitted event is an in-memory dict. Fixtures are hand-authored synthetic
double-envelope responses (PROVENANCE.md). CR-1/CR-5 honoured.

---

## §3 — Adversarial rulings (the four the author routed)

**(i) DR-2 floor over the k contributing sections — INTENDED, CONCUR.**
The `min` is over the `k` sections that contributed a non-null `max(last_modified)`,
not all `n`. This is the SPEC's explicit reading: §1 defines `{t_s}` as "the `min`
floor over constituents" and §4 defines `k` as "the count that contributed a
non-null `max(last_modified)` to the `min` floor" — empty sections are disclosed by
the `k of n` denominator (a completeness statement, C-6), **not folded into the
floor**. It is also the only coherent reading: an empty section has no timestamp to
enter a `min`. The code implements exactly this (`item_1a.py:184-194`:
`contributing = {…}`, `as_of = min(contributing.values())`, `k=len(contributing)`,
`n=len(in_scope)`), and refuses loudly (`Item1aError`) at `k==0` rather than
inventing a floor. This is the DR-2 (age) / C-6 (completeness) split working as
designed. **Not a defect.**

**(ii) content_hash vs delivery — CONCUR; residual is delivery-side, out of EX-5 scope.**
The generation half is content_hash-**ready**: it emits a real sha256 over the
delivered bytes. The join's swap-detection rides on `block_count`
(`join.py:71-79`) — labelled `CONTENT_HASH_MISMATCH` — because EX-4's
`DeliveryReceipt` (`report_posted`) carries **no** `content_hash` field
(`schema.py:161-179` + module docstring: delivery half is live but hash-less). So
the residual is a **delivery-emitter** gap (the ASR `report_posted` emitter must
emit `content_hash` before the join can compare hashes directly) — EX-6 / delivery-
side, correctly out of EX-5's build scope. Confirmed sharpening: today's teeth are
**coarse** — a swap that preserves `block_count` (6 blocks) would evade until the
delivery hash lands. That is the exact delivery-side residual named above, not an
EX-5 defect. The generation half did its part.

**(iii) timezone parsing — CONCUR (PASS).**
`_parse_dt` (`item_1a.py:120-135`) normalises `Z` / explicit-offset / naive to
aware-UTC. Probed own-hands: `10:00Z` == `15:00+05:00` == `02:00-08:00` == naive
`10:00` == both aware `datetime` objects → identical instant. Adversarial mixed-
offset `max`: a `2026-08-12T15:00:00+02:00` row (=13:00Z) correctly beats a
`09:00Z` row in the per-section `max`; a `-05:00` row lands on the right UTC day.
No naive-vs-aware comparison is ever attempted (every cell is coerced to aware UTC
before comparison). **Not a defect.**

**(iv) SC-1 structural counting + R-16/F-E3 non-steering — CONCUR (PASS).**
SC-1 is structural (`say_able_value` field, not NLP): a rendered occurrence carries
exactly **one** `say_able_value`. Adversarial numeric-token scan of every block's
prose (after stripping ISO timestamps): the only bare numerals are the `k of n`
denominator (`2 of 3`) and its echo `the {k} constituents` — the **same
completeness count**, which C-6/D-6 permits as a denominator, not a second say-able
number-class. No second business number leaks through the footer/disclosure/g4
prose. Steering scan (my banned list, wider than the author's): `should`/`prioriti`/
`urgent`/`rank`/`recommend`/`best`/`worst`/CTA — **none** present. The orientation
footer states what the figure is and is-not and where the alarm lives; it issues no
instruction. **Not a defect.**

*(Minor observation, non-blocking: the denominator quantity `k` is echoed in prose
in two blocks as "the {k} constituents". This is the same completeness count C-6
already licenses in the typed slot, so it is within the fence; the typed-slot
guarantee is about the denominator SLOT, and SC-1's structural counter — the
load-bearing check — correctly returns 1. Recorded for completeness, not a FLAG.)*

---

## §4 — DEFECT (my ADDED refuter): the DF-1 AST guard is blind to the plural `stories` cache module

**Finding.** The DF-1 import-scan's forbidden set is
`("temporal","section_timeline","section_timelines","story")`
(`test_readout_generation.py:395`). The token `"story"` (singular) is **not** a
substring of `"stories"` (plural). The real story-cache read in this repo is
plural: `section_timeline_service.py:420` does
`from autom8_asana.cache.integration.stories import read_stories_batch`, and the
cache/client modules are `autom8_asana.cache.integration.stories` and
`autom8_asana.clients.stories`. I verified own-hands that the scan **MISSES** both
(`"story" in "…cache.integration.stories"` → False) while it catches only
`models.story` (singular) and `story_warmer`. So a future edit adding the exact,
natural story-cache import — `from autom8_asana.cache.integration.stories import
read_stories_batch`, the very line `section_timeline_service.py:420` uses — would
report the guard **GREEN** while directly reading the story cache DF-1 exists to
fence out.

**Severity: FLAG (design-completeness / guard-teeth), NOT a live violation.** The
build's DF-1 property holds *today* (R4: no forbidden import present at source; the
readout leaves add no substrate module transitively). This is a hole in the
**guard**, on the one constraint the shape names as "the single easiest thing in
this envelope to get wrong." It does not block landing.

**Recommendation (Phase-2 / hardening-binding):** add `"stories"` to the forbidden
set (ideally switch to path-segment matching, e.g. reject any imported module whose
dotted segments include `stories`, `story`, `temporal`, or `section_timeline*`).
Note the residual limitation even then: a direct-import AST scan cannot see coupling
through the eager top `__init__.py` — but that is a whole-repo condition affecting
every module equally, so DF-1 must remain a source-level (does-this-code-import/call-
it) property, which is the correct altitude for this guard.

### §A.3 reporting duty (for this added negative)

- **Refuters swept + returns (incl NULLS).** (a) *Does the scan bite on the temporal
  substrate?* → YES (`temporal` FAILS, `section_timelines` FAILS, clean PASSES —
  two-sided). (b) *Does the source path import the substrate today?* → **NULL** (no
  forbidden import in any of the 3 modules). (c) *Does the token set cover the story
  cache's real module name?* → **NO** — misses plural `stories`. (d) *Is there a live
  import that would evade?* → **NULL today** (none present), but the evading spelling
  is the one `section_timeline_service.py:420` actually uses.
- **The hop one past, named concretely.** `section_timeline_service.py:420`
  `from autom8_asana.cache.integration.stories import read_stories_batch` — a direct
  import of this into any readout module passes the guard GREEN. That is the exact
  seam the guard fails to close.
- **Refuter I added.** The plural-token completeness refuter (is the FORBIDDEN set a
  superset of the real substrate module basenames?). It is not.
- **Verdict on "DF-1 has teeth": NARROWS.** It has two-sided teeth against
  `temporal`, `section_timelines`, and *singular* `story` imports; it is **blind to
  the plural `stories` cache module**. The build's DF-1 property STANDS today; the
  guard's coverage NARROWS to that corrected scope. Dissent not softened: on the one
  constraint flagged as easiest to get wrong, the guard has a demonstrable blind spot
  aimed at the exact spelling the live substrate uses.

---

## §5 — Landability, revertibility, EXIT

**LANDABLE: YES (the code).** The mechanism is correct and green: item 1a under
DR-2 (min-over-k floor, loud refusal at k==0), the typed C-6/DENOM-FENCE
denominator, the per-render C-5 G4′ enumeration *with* the FLAG-F-2 truncation
branch declared (present→OVERSTATE_AGE when truncated, declared-and-absent
otherwise), the SC-1 single say-able number, R-16 non-steering, and a real
content_hash + structural no-human-authorship. ruff + mypy clean.

**Revertibility: trivial.** The build is purely additive — three new untracked
paths (`src/autom8_asana/readout/`, `tests/fixtures/readout/`,
`tests/unit/test_readout_generation.py`), zero edits to any existing file
(`git diff HEAD` empty against EX-4 base `164382c0`). Removing the additive package
restores the exact EX-4 base with no impact on the existing tree; there is no commit
chain to `git revert`-test because the mechanism is a green-field package.

**EXIT correctly HELD on Q-2 (C-9).** This build is **not** EX-5's exit. Cadence is
UNRULED (operator's Q-2); `cadence_label` is a data-driven argument, and the live
worked render (exit criterion 1) stays EXIT-HELD, operator/credential-gated. The
telos is PROPOSED (Q-5). The one FLAG (§4) is a hardening input to Phase-2, not a
blocker. Nothing here rules cadence or fires a live call.

---

## §6 — Product-Altitude ADVISORY (telos posture)

Emitted in a section distinct from the execution-altitude verdict; `-ADVISORY`
suffix load-bearing; NON-BLOCKING by contract (surfaces only).

**FLAG-ADVISORY** — the initiative's `verified_realized` gate is not yet
attestable. The generation mechanism has **LANDED** (code + tests green,
`src/autom8_asana/readout/generation.py`), but the `shipped → verified_realized`
step (RUNG-2 limb (a): two consecutive *real* generated occurrences with no human
assembly) is HELD: today's proof is over SYNTHETIC fixtures; the live worked render
is EXIT-HELD on operator Q-2 and no user-visible realization exists yet. This is
the correct posture (the wave deliberately holds EXIT on Q-2), surfaced for human
disposition — it does not halt anything. The execution-altitude verdict below is the
binding one for the code.

---

## §7 — Overall verdict & evidence grades

**Execution-altitude verdict: CONCUR-WITH-FLAGS (no BLOCK). The code is LANDABLE;
EXIT stays HELD on Q-2.**

Verify items 1/2/3/5 PASS; item 4 PASS-WITH-FLAG (DF-1 property holds; guard token
blind to plural `stories` — §4 DEFECT/hardening). Adversarial (i)/(ii)/(iii)/(iv)
all CONCUR — no defect; (ii)'s coarse-swap residual is confirmed delivery-side and
out of EX-5 scope.

- **[STRONG — own-hands]:** the uncached test run (44, 29+15), the two-sided
  own-construction join teeth (five `_classify` branches), the content_hash
  recompute + determinism/flip + structural-constant proof, the DF-1 source-level +
  transitive-isolation re-derivation, and the no-live-surface grep. Mechanical,
  re-runnable, non-judgmental (per `self-ref-evidence-grade-rule` §Step-2).
- **MODERATE (ceiling):** all judgments (severity of the DF-1 token FLAG, the
  DR-2/C-6/timezone/SC-1 adequacy rulings, landability). eunomia is rite-disjoint
  from 10x-dev (Axiom-1 lifts this above pure self-attestation), but this is an
  in-fleet attestation of a satellite build — **STRONG is not claimed on any
  judgment.** MODERATE ceiling enforced.

**Acid test.** Would I stake my reputation that this mechanism generates item 1a
under DR-2 from the served bytes alone, carries exactly one say-able number under a
typed refusable fence, cannot emit a human authorship, binds its artifact with a
real content_hash, and can be independently removed to restore the EX-4 base — and
that its one gap (a DF-1 guard blind to the plural `stories` module) is named,
non-fatal, and hardening-bound? **Yes** — CONCUR-WITH-FLAGS, code LANDABLE, EXIT
held on operator Q-2.
