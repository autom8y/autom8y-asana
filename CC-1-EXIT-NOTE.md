# CC-1 EXIT NOTE — swap-detector closure (chain-of-custody-closure)

- **Rung reached:** `rung-BUILT-DARK` (code in worktree, own-tests GREEN). NOT merged, NOT committed (Q-4 HALT). The main thread raises to PR-UP-MERGE-HELD.
- **Worktree:** `.knossos/worktrees/wt.10x-dev.coc-cc1.20260813T2130.reconverge` — branch `coc-cc1-reconverge`, cut from `origin/main` @ `d7560153`.
- **Anti-collision guard:** CLEAN. `git status --porcelain` was empty at entry; at exit every modified path is one I authored (11 files, 0 foreign). No concurrent duplicate observed. No git verbs run (files-only; DF-2 honored).
- **Self-assessment grade:** MODERATE (builder self-attestation ceiling). STRONG is the critic's own-hands re-derivation.

---

## 1. Files touched (11)

**New (2):**
- `src/autom8_asana/observability/payload_hash.py` — REC-001 shared canonicalization.
- `tests/unit/test_swap_detector_closure.py` — the two-sided demonstration suite.

**Modified (9):**
- `src/autom8_asana/readout/generation.py` — removed `content_hash_of`; added `text` field to `GeneratedOccurrence`; hash via shared canon.
- `src/autom8_asana/readout/template.py` — added `render_fallback_text` (D-4 text surface).
- `src/autom8_asana/readout/__init__.py` — dropped `content_hash_of`, exported `render_fallback_text`.
- `src/autom8_asana/observability/rail_delivery/delivery_receipt.py` — `content_hash` delegates to the shared canon.
- `src/autom8_asana/observability/rung_receipts/schema.py` — REC-003 splice + `BLOCK_COUNT_MISMATCH` + clause-3 over-claim docs.
- `src/autom8_asana/observability/rung_receipts/join.py` — clause 4→4a/4b split + clause-3 narrowing + docstring contract-truth.
- `tests/unit/test_readout_generation.py` — collateral (import + block-count label).
- `tests/unit/test_rung_receipts.py` — collateral (mismatch test → 4b label).
- `tests/fixtures/rung_receipts/PROVENANCE.md` — swap-fixture derivation.

---

## 2. RED receipt (verbatim, pristine tree BEFORE any edit)

Captured own-hands at `coc-cc1-reconverge @ d7560153` with `PYTHONPATH=<worktree>/src`, using ONLY pre-existing symbols (no dependency on new code — the RED is the genuine gap, not an ImportError). Full log: scratchpad `RED-reconverge.txt`. It agrees byte-for-byte with the preserved cross-run `RED-verbatim.txt` (both prior runs' RED).

```
rung_receipts.DeliveryReceipt fields : ['invocation_id', 'channel', 'block_count', 'delivered_at', 'outcome', 'trace_id', 'message_ts', 'permalink']
  'content_hash' on DeliveryReceipt   : False
  'content_hash' in schema.delivery   : False

generation-side hash (blocks only)    : sha256:f5909b2bce19043bff2439250b5677a18e1427e6143790039e723f4cf05b369b
delivery-side hash ({blocks,text})    : sha256:04ff9b6204e2092ef22f56ef3b284510eeed43210d960c2801744e176a2b5ac5
  two canonicalizations agree?        : False

... count-preserving swap (block_count 6 == 6; hashes differ) ...
  rung_e_limb_a_attestation: "observable"
  rung_e_not_observable_reason: null

RED ASSERTION 1: swapped payload classifies -> 'observable'
RED ASSERTION 2: schema.DeliveryReceipt.content_hash -> AttributeError('DeliveryReceipt' object has no attribute 'content_hash')
RED CONFIRMED: the swap-detector does not exist. Guard genuinely absent.
```

The RED is two-fold and genuine: (i) a count-preserving swap classifies `observable` because the join never compared a hash and block-counts were equal; (ii) `DeliveryReceipt` had no `content_hash` attribute at all. **No defect was injected** — the guard is authentically absent (G-THEATER forbidden, honored).

---

## 3. GREEN receipts (verbatim, AFTER edits — two-sided + single-variable flip)

Own-hands, same worktree, `PYTHONPATH=<worktree>/src`. Full log: scratchpad `GREEN-reconverge.txt`.

```
DeliveryReceipt fields          : [..., 'outcome', 'content_hash', 'trace_id', ...]
  'content_hash' on DeliveryReceipt: True
  'content_hash' in schema.delivery.properties: True
  'content_hash' in schema.delivery.required  : False

REC-001 — two canonicalizations now AGREE:
  generation occ.content_hash        : sha256:f9c6ad469a162f1de383c816c2240fccce3e265537b77c8ffd60fa0bfa423e9d
  delivery content_hash(blocks,text) : sha256:f9c6ad469a162f1de383c816c2240fccce3e265537b77c8ffd60fa0bfa423e9d
  agree?                             : True

TWO-SIDED VERDICTS (same generation receipt, delivery varied):
  HONEST  (matching hash, equal count) -> observable / None
  SWAP    (differ hash,  equal count)  -> not_observable / content_hash_mismatch
  RESIDUAL(no hash,      equal count)  -> observable / None   (4a UNATTESTED, passes on 4b)

SINGLE-VARIABLE CAUSATION:
  fields differing between honest and swap delivery inputs: {'content_hash'}
  verdict honest: observable | verdict swap: not_observable
GREEN CONFIRMED: swap CAUGHT on content_hash alone; honest passes; residual hashless delivery observable-but-unattested.
```

- **Swap direction (RED→GREEN):** the SAME count-preserving swap that was `observable` on the pristine tree is now `not_observable` / `content_hash_mismatch`, block counts still equal — so 4b cannot be the cause; the teeth bit on 4a.
- **Honest direction:** matching hash → `observable`.
- **Single-variable causation:** the honest and swap delivery INPUTS differ in exactly `{'content_hash'}`, and the verdict flips — the guard bites ONLY on `content_hash` (two-sided teeth per `discriminating-canary-doctrine`).

Pinned as pytest in `tests/unit/test_swap_detector_closure.py`: `TestSwapNowCaught`, `TestHonestDirection`, `TestSingleVariableCausation`, `TestClause4aResidual`, `TestREC001SharedCanon`, `TestREC003SchemaSplice`, `TestClause3Narrowing`, `TestClause4bDistinct`.

---

## 4. REC-001 — one shared canonicalization (both call sites)

Symbol: `canonical_payload_hash(blocks, text)` at `src/autom8_asana/observability/payload_hash.py:38`, using the delivery-side `{blocks, text}` form (`"sha256:" + sha256(json.dumps({"blocks": list(blocks), "text": text}, sort_keys=True, separators=(",", ":")).encode())`).

- **Call site A (generation):** `src/autom8_asana/readout/generation.py:190` — `content_hash = canonical_payload_hash(blocks, text)`, where `text` is `render_fallback_text(...)` (`generation.py:181`), stored on `GeneratedOccurrence.text` (`generation.py:103`, `:212`). Old `content_hash_of` REMOVED.
- **Call site B (delivery):** `src/autom8_asana/observability/rail_delivery/delivery_receipt.py:65` — `content_hash(...)` now delegates: `return canonical_payload_hash(blocks, text)`. Its old in-line `json.dumps` deleted. The public `content_hash` name is kept as a thin wrapper so existing importers (`test_rail_delivery_receipt.py`) are undisturbed.
- **D-4 text surface:** `render_fallback_text` at `src/autom8_asana/readout/template.py:83` — deterministic, figure-derived, no human-typed slot (the "no human assembled it" invariant extends to the fallback text).

Effect (grep-verified, NR-1(c)): the readout `{blocks,text}` payload has exactly TWO consumers, both now on the one symbol; no third site canonicalizes it. The RED's "two canonicalizations agree? False" is now True.

## 5. REC-003 — schema splice (cites)

`src/autom8_asana/observability/rung_receipts/schema.py`:
- `DeliveryReceipt.content_hash: str | None = None` (`:208`), projected in `from_event` (`:231`, `content_hash=_opt_str(evt.get("content_hash"))` → `None` for the live hashless emitter).
- Ingestion query select gains `content_hash` (`DELIVERY_LOGS_INSIGHTS_QUERY`, `:378`).
- `RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA.delivery.properties.content_hash` added (`:436`) but **NOT** in `.delivery.required` — documented in-comment (`:432`): the live `report_posted` emitter does not populate it, so a schema that required it "would reject every real delivery receipt — describing an instrument nobody runs." That judgment is the deliberate optional-not-required choice.

---

## 6. Contract-truth diff (join.py clause 4 → 4a / 4b)

`src/autom8_asana/observability/rung_receipts/join.py` `_classify`:
- **4a (`:98`–`:108`):** fires ONLY when BOTH sides carry a `content_hash` and they differ → `CONTENT_HASH_MISMATCH`.
- **4b (`:116`–`:126`):** bare block-count disagreement → its OWN reason `BLOCK_COUNT_MISMATCH` (new enum `schema.py:155`). Before CC-1, a block-count disagreement was mislabelled `content_hash_mismatch` though no hash was ever compared — that over-claim is ended.
- Module docstring (`:15`–`:44`) rewritten so no clause over-claims; every clause states its precondition and what it does NOT establish.

**Clause-4a residual (added + pinned):** a delivery carrying NO `content_hash` leaves 4a **UNATTESTED (not satisfied)** — the swap-check cannot run; the join invents no match and falls through to 4b (`join.py:109`–`:115`). Because the live emitter is hashless (REC-002 out of scope), a count-preserving swap on a hashless delivery is still undetected. Pinned honestly by `TestClause4aResidual.test_hashless_delivery_is_observable_but_hash_is_unattested` and `...test_swap_on_a_hashless_delivery_is_still_undetected`.

**Clause-3 narrowing (found by both prior runs — carried, NOT renamed):** clause 3 trips on `assembled_by is not Assembler.MACHINE` (`join.py:87`–`:96`), true for BOTH `HUMAN` and `UNKNOWN`; an `UNKNOWN` assembler is reported under the `ASSEMBLED_BY_HUMAN` token — asserting a human authored it when only un-attested authorship was established. Documented in the contract (`join.py:31`–`:36`) and the enum docstring (`schema.py:130`–`:150`). The wire token is **deliberately NOT renamed** — it is a frozen `rung_e_not_observable_reason` JSON-schema enum value; a truthful `assembled_by_human` vs `assembled_by_unknown` split is a breaking schema change out of CC-1 scope. **Flagged for the critic** and pinned (over-claim behavior locked) by `TestClause3Narrowing`.

---

## 7. NCSR — negative + NR-1 first-sweep (returns incl. nulls)

**Negative stated (RED):** *"a count-preserving swap passes as OBSERVABLE today."* Confirmed §2.
**Negative stated (post-repair):** *"no over-claiming docstring survives."* Clause 4a/4b split ends the `content_hash_mismatch`-on-block-count over-claim; clause-3 over-claim + clause-4a residual are documented, not swept (§6).

**NR-1 refuters (rite-disjoint second-read of NR-1 by `structure-evaluator` (arch)):**
- **(a) Is `_classify` the only classification path?** YES (null of alternatives). `run_query`/`join_occurrences`/`observe_limb_a` all route the per-occurrence verdict through the single `_classify`; grep for `RungEObservability.OBSERVABLE` / `NotObservableReason` shows `_classify` (`join.py`) is the sole producer. No second classifier.
- **(b) Does the RED trip on the hash comparison and nothing else?** YES. The swap is count-preserving (`len(swapped) == occ.block_count`, asserted), so clause 4b (block-count) cannot fire; the only signal that catches it is 4a. The single-variable causation test shows the verdict flips on `{'content_hash'}` alone. On the pristine tree the RED tripped because NO hash comparison existed and block-counts matched → `observable`.
- **(c) Does the chosen canonicalization have any THIRD site that would silently disagree?** NO third site (null). `grep content_hash_of` → only the 4 sites removed/updated. The readout `{blocks,text}` payload is consumed by exactly `generation.py` and `delivery_receipt.py`, both now on `canonical_payload_hash`. Other `sort_keys`/`sha256` sites (substrate frames, idempotency keys, webhooks) hash different domains/inputs and never touch this payload — orthogonal, not silently-disagreeing.
- **(d) Does any OTHER clause over-claim?** Confirmed and CARRIED: clause 3 (`ASSEMBLED_BY_HUMAN` also fires for `UNKNOWN`) — both prior runs found it; documented + flagged, token not renamed (breaking-change scope fence). And I ADD the clause-4a residual note (hashless delivery → 4a unattested, not a silent pass). No other clause over-claims after the docstring rewrite.

---

## 8. Verification commands + results (own-hands)

Import resolution guard (worktree editable-install trap): `python -c "import autom8_asana.observability.rung_receipts.join as j; print(j.__file__)"` → resolves to the WORKTREE `src` (with `PYTHONPATH=<worktree>/src`).

```
PYTHONPATH="$PWD/src" python -m pytest \
  tests/unit/test_swap_detector_closure.py tests/unit/test_readout_generation.py \
  tests/unit/test_rung_receipts.py tests/unit/test_rail_delivery_receipt.py -q
=> 69 passed in 0.63s
```

Wider blast-radius slice (rail + readout + rung):
```
PYTHONPATH="$PWD/src" python -m pytest tests/unit/test_rail_distinguishability.py \
  tests/unit/test_rail_readout_shape.py tests/unit/test_rail_block_budget.py \
  tests/unit/test_rail_delivery_receipt.py tests/unit/test_readout_generation.py \
  tests/unit/test_rung_receipts.py tests/unit/test_swap_detector_closure.py -q
=> 101 passed in 0.41s
```

- `mypy` (7 changed src files, `MYPYPATH=<worktree>/src`): **Success: no issues found in 7 source files.**
- `ruff check` (all changed src + tests): **All checks passed!**
- `ruff format --check` (all changed src + tests): all formatted.

---

## 9. Fences honored

- Build DARK, files only — **no git verbs** (no add/commit/branch/checkout/stash/push/PR; no `git checkout --`). `git status`/`git diff` are read-only inspections.
- **DF-2:** zero monorepo touches, zero live posts — the join ran over synthetic events only. **REC-002 stayed OUT** (parent egress not entered; no F-6 needed — the hashless-delivery residual is documented in-repo, not blocked on). **REC-004 OUT** (no live post).
- **CR-1** (no Asana write), **CR-5** (no credential material), no infra mutation, **G-THEATER forbidden** (guard genuinely absent — RED used only pre-existing symbols). No limb-(a) attestation (eunomia's, blocked until both halves land).

## 10. Route to critic (STRONG re-derivation)

Ceiling here is MODERATE. For STRONG, `structure-evaluator` (arch) re-derives own-hands: (1) re-run the RED on a fresh pristine checkout of `d7560153` (swap → `observable` + `DeliveryReceipt.content_hash` AttributeError); (2) construct its OWN count-preserving swap fixture and confirm `content_hash_mismatch` with equal block-counts; (3) confirm the clause-3 `UNKNOWN`→`ASSEMBLED_BY_HUMAN` over-claim and rule on whether the frozen-token deferral is acceptable or should be escalated for a schema-version bump. Second-read target: NR-1.
