---
type: review
status: proposed
---

# CRITIQUE — swap-detector closure (CC-1), NR-1 NCSR receipt

- **Wave:** chain-of-custody-closure · **Node:** CC-1 (keystone; predicate limb (i) rests on NR-1, the highest-value negative)
- **Author under second-read:** `principal-engineer` (10x-dev)
- **Second reader (rite-disjoint):** `structure-evaluator` (arch) — adversarial NCSR, attack-not-confirm, one hop past the author
- **Worktree:** `.knossos/worktrees/wt.10x-dev.coc-cc1.20260813T2130.reconverge` — branch `coc-cc1-reconverge` @ `d7560153`
- **Rung reached:** `rung-BUILT-DARK` (own-tests GREEN; NOT merged/committed — Q-4 HALT)
- **Grade licensed:** **STRONG** on every leg I personally re-derived own-hands (RED, GREEN two-sided, single-variable causation, clause-3, clause-4a residual, refuters a/b/c/d). This is the one place in the wave STRONG is warranted.
- **Date:** 2026-08-13

---

## 0. Bottom line

- **NR-1: STANDS.** The negative — *"a count-preserving swap passes as OBSERVABLE at origin/main; the guard is genuinely absent"* — is confirmed own-hands on an independently-extracted pristine `d7560153` tree, with my OWN swap fixture, and is byte-consistent with the preserved RED capture. It is a **genuine RED**, not theater: it returns `observable` (no ImportError masking), the swap is count-preserving (6==6 blocks, so clause 4b cannot be the cause), and the generation event is fully-formed (no missing-field trip).
- **Flagged item 1 (clause-3 frozen wire token): deferral ACCEPTABLE → STANDS.** The rename is NOT required for CC-1's predicate (i). Condition: the surviving wire-token over-claim must be named in the exit rung (author did).
- **Flagged item 2 (clause-4a residual / hashless live emitter): NARROWS.** Predicate (i) holds for the *mechanism*; the swap-check is UNATTESTED for the live hashless emitter. The closure is a **BUILT-DARK mechanism closure, not a live-emitter closure**, and this must ride into the exit rung.
- **Predicate (i): HOLDS at rung-BUILT-DARK**, carrying two named narrowings (N1 deferred wire-token over-claim; N2 swap-check unattested for the live emitter). It does NOT hold as a live-emitter swap-closure.

---

## 1. Own-hands re-derivation (the STRONG substrate)

### 1.1 Independent RED on pristine `d7560153`
I extracted the pristine `src` tree via read-only `git archive d7560153 src` into a scratchpad (never the worktree), set `PYTHONPATH` to it, and drove my OWN count-preserving swap through the pristine `run_query` — NOT the author's `_swap` helper or test file:

```
(1) content_hash in pristine DeliveryReceipt fields: False
(3) generation-side (blocks-only) hash : sha256:f5909b2bce19043b ...
(3) delivery-side ({blocks,text}) hash : sha256:a45682881da6857c ...
(3) two canonicalizations agree?       : False
(2) block counts equal (swap vs gen)   : 6 == 6
(2) pristine verdict for swap          : observable
(2) pristine not_observable_reason     : None
(2) delivery carried content_hash?     : False
RED HOLDS (independent): True
```

- Pristine `_classify` (git-archived) has **no clause 4a**; its block-count clause returns `CONTENT_HASH_MISMATCH` — the pre-CC-1 over-claim (a block-count disagreement mislabelled a hash mismatch though no hash was compared). Confirmed at source.
- Pristine `DeliveryReceipt` fields: `[invocation_id, channel, block_count, delivered_at, outcome, trace_id, message_ts, permalink]` — **no `content_hash`** (the RED's AttributeError class).
- The generation-side blocks-only hash `sha256:f5909b2bce19043b...` matches the preserved `RED-verbatim.txt:9` **byte-for-byte** → same pristine code, same fixture. Cross-check passes.

### 1.2 Independent GREEN on the repaired worktree
Own fixture again, driven through the repaired `run_query`:

```
count-preserving (swap vs gen blocks): 6 == 6
HONEST (matching hash, equal count) : observable / None
SWAP   (differ hash,  equal count)  : not_observable / content_hash_mismatch
HASHLESS SWAP (no hash, equal count): observable / None
honest vs swap differing input keys : {'content_hash'}
refuter(b) block_counts equal        : True
clause-3 UNKNOWN assembler -> reason : assembled_by_human
clause-3 HUMAN   assembler -> reason : assembled_by_human
GREEN two-sided + single-variable HOLDS: True
```

### 1.3 Suites re-run own-hands (worktree, `PYTHONPATH=$PWD/src`)
- `tests/unit/test_swap_detector_closure.py` → **17 passed**.
- Wider blast-radius slice (rail_distinguishability + rail_readout_shape + rail_block_budget + rail_delivery_receipt + readout_generation + rung_receipts + swap_detector_closure) → **101 passed** (matches author's claim; no collateral breakage, no import-error masking).

---

## 2. NR-1 refuters swept (returns incl. nulls; the hop taken)

**(a) Is `_classify` the ONLY classification path?** — **YES (null of alternatives).**
`grep` across `src` shows `rung_e_limb_a_attestation` is *set* exactly once (`join.py:166`) from `_classify`'s return; `observe_limb_a` only *reads* it (`join.py:187`); `run_query` routes through `join_occurrences → observe_limb_a → _classify`. `RungEObservability` appears only in `join.py` (producer), `schema.py` (type + JSON-schema enum), `__init__.py` (re-export). The other `_classify_hop` (`gfr/planner.py`) and `_classify_gids` (`universal_strategy.py`) are unrelated domains. **No second classifier; no downstream consumer sets the attestation.**

**(b) Does the RED trip on the hash comparison and NOTHING ELSE?** — **YES.** The pristine RED returns `observable` (not a crash → no ImportError theater). The swap is count-preserving (`len(swapped)==occ.block_count`, 6==6 → clause 4b cannot fire). The generation event carries all fields (no missing-field trip). On GREEN, the single-variable test shows honest vs swap delivery inputs differ in **exactly `{'content_hash'}`** and the verdict flips → **clause 4a and only 4a bites.** Not a false RED.

**(c) Any THIRD canonicalization site that would silently disagree?** — **NO third site (null).**
- `content_hash_of` is **fully removed** from `src`/`tests` (only a historical docstring mention in `payload_hash.py:6` + a stale `.pyc` remain).
- `canonical_payload_hash` has **exactly two callers**: `readout/generation.py:190` and `rail_delivery/delivery_receipt.py:65`.
- The only payload `sha256`/`hashlib` is `payload_hash.py:55`. The `schema.py:302` `json.dumps` is **receipt-envelope serialization** (`to_dict`), an orthogonal domain never compared as a content hash; `query.py:83` is CLI pretty-print. Closure holds **within CC-1's repo scope.** The live monorepo `report_posted` egress is a future coordination point (REC-002, out of scope, correctly deferred).

**(d) Does any OTHER clause over-claim?** — Confirmed **clause 3** (documented) and the **clause-4a residual** (documented); **no third undocumented over-claim of the same class.** Defaults are all fail-safe: `human_in_loop` defaults `True`, `assembled_by` defaults `unknown` → both drive to `not_observable`.

**ADDED refuter (my hop past the author):** the clause-4a residual is **SYMMETRIC**, but the author's explanatory prose names only the *delivery-hashless* direction. I confirmed own-hands that a **generation-hashless** side (even paired with a swap-hash-bearing delivery) also passes `observable / None`:
```
ADDED: gen-hashless + delivery-swap-hash -> observable / None
```
Note: the **formal contract precondition** in the docstring ("IF both sides carry a `content_hash`") IS symmetric and therefore accurate; only the residual *narrative* is one-directional. This is not a contract/implementation mismatch — it is an asymmetric emphasis that the schema-version follow-on should read as "either side hashless ⇒ 4a unattested," not "delivery-hashless only."

---

## 3. Ruling on the two flagged items

### Item 1 — clause-3 over-claim, frozen wire token carried-not-renamed → **STANDS (deferral ACCEPTABLE)**
`_classify` trips on `assembled_by is not Assembler.MACHINE` (`join.py:86`), so `UNKNOWN` is reported under the `ASSEMBLED_BY_HUMAN` wire token — asserting human authorship when only un-attested authorship was shown. Confirmed own-hands (`c3("unknown") -> assembled_by_human`).

**Predicate (i) does NOT require the rename for CC-1.** Reasoning against the three-check gate:
1. **Intentional trade-off?** YES — the token is a frozen `rung_e_not_observable_reason` JSON-schema enum value; renaming it is a breaking schema change (a truthful `assembled_by_human` vs `assembled_by_unknown` split needs a schema-version bump), legitimately out of CC-1's mission scope.
2. **Documented / bounded?** YES — contract docstring (`join.py:32-37`), enum docstring (`schema.py:130-149`), and pinned by `TestClause3Narrowing` (both UNKNOWN and HUMAN cases).
3. **Evidence sufficiency?** The over-claim is real, confirmed, not a false positive.

Decisive: the predicate's clause is *"no over-claiming **docstring** surviving"* — and the docstrings are now **truthful** (they declare the over-claim). The surviving over-claim is a **wire-token diagnostic label on the FAIL side** — both HUMAN and UNKNOWN correctly yield `not_observable`, so the over-claim never lets a bad payload *pass*; it is conservative and does not compromise the two-sided swap demonstration. **Acceptable to defer, provided the exit rung names the surviving wire-token over-claim** (author did, exit note §6 + `NotObservableReason` docstring).

### Item 2 — clause-4a residual, hashless live emitter → **NARROWS**
A hashless delivery leaves 4a UNATTESTED; a count-preserving swap on a hashless delivery is still `observable` (confirmed own-hands). The author made `content_hash` OPTIONAL (`schema.py:208`, properties-not-required) and pinned the residual with `TestClause4aResidual`.

**Predicate (i) is honestly satisfied for the MECHANISM but must be scoped in the exit rung:**
- The two-sided demonstration is real (honest→observable, swap-with-hash→not_observable).
- BUT the swap-check is **UNATTESTED for the exact live emitter that exists today.** So this is a **built-dark mechanism closure, not a live-emitter closure.**
- **Mitigating (verified at source):** the live generation half is *also* absent (`report_generated` = zero rows per the census), so on live telemetry TODAY every occurrence classifies `generation_provenance_absent` → `not_observable`. The residual therefore **cannot bite on live data today**; it becomes a live hazard only after EX-5 ships `report_generated` while REC-002 (delivery `content_hash`) remains undone. Correctly scoped out.
- **UV-P I could not discharge:** the "live `report_posted` emitter carries no `content_hash`" claim rests on a **preserved CloudWatch census (`queryId 7c59f3d8-...`) NOT re-probed this session.** Fences CR-5 (no credentials) and DF-2 (no monorepo touch) forbid me from re-probing. **Carried forward as an unverified premise** — the exit rung should not upgrade it to fact without a re-probe.

Verdict: **NARROWS** — the closure is honest but narrower than "the swap is caught"; it is "the swap is caught *once both halves carry the hash*; the live emitter is hashless, so the check is unattested for it today," on an un-reprobed census.

---

## 4. Predicate (i) verdict at rung-BUILT-DARK

> Predicate (i): the two-sided demonstration, with the join's contract matching its implementation, no over-claiming docstring surviving.

**HOLDS at rung-BUILT-DARK**, carrying two named narrowings:
- **Component 1 — two-sided demonstration:** HOLDS (re-derived own-hands, §1.2, single-variable causation on `content_hash` alone).
- **Component 2 — contract matches implementation:** HOLDS. I walked every clause of the `join.py` module docstring + `NotObservableReason` enum docstring against `_classify` line-by-line; each precondition and each returned reason matches, including the symmetric 4a precondition.
- **Component 3 — no over-claiming docstring surviving:** HOLDS (docstrings are truthful). **N1:** one over-claiming *wire token* survives (`assembled_by_human` for UNKNOWN) — conservative fail-side label, documented + pinned + deferred to a schema-version bump. **N2:** the swap-check is unattested for the live hashless emitter (clause-4a residual), on an un-reprobed census.

It does **not** hold as a live-emitter swap-closure. It holds as a **BUILT-DARK mechanism closure with a genuine two-sided demonstration.**

---

## 5. Honest rung I would certify for CC-1

**`rung-BUILT-DARK` — mechanism closure, two-sided teeth re-derived own-hands (STRONG on the re-run legs).** NOT a live-emitter closure. The two residuals (clause-3 wire token; clause-4a hashless live emitter) are documented, pinned, and correctly scoped out; they MUST ride into the exit rung as named narrowings, and the "hashless live emitter" premise MUST be carried as UV-P (census not re-probed this session) rather than asserted.

---

## 6. Fences honored
Read + ran tests in the worktree; pristine tree extracted to **scratchpad only** via read-only `git archive` (no working-tree mutation). **No git verb that mutates** (no add/commit/branch/checkout/push/PR; no `git checkout --`). DF-2 (no monorepo touch), CR-1 (no Asana write), CR-5 (no credential material — census NOT re-probed), REC-004 (no live post) all honored. No limb-(a) attestation performed or invited (eunomia's at CC-8, blocked until both WS-A halves land). This critique rests authored-unmerged (Q-4 HALT); the main thread owns every git verb.
