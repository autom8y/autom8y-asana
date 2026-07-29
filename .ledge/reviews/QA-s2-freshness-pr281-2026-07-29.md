# QA-ADVERSARY REVIEW — S2 freshness (PR #281, feat/substrate-v2-s2-freshness)

```yaml
reviewer: qa-adversary (P7)
date: 2026-07-29
scope: src/autom8_asana/substrate/freshness.py + tests/unit/substrate/ (worktree autom8y-asana-wt-w2-s2, HEAD 536650d4)
bar: TDD-substrate-v2 §4 Seam-1 + §3 RC-B; RC-acceptance-predicates RC-B-1..4; FEASIBILITY [H1][H2]; ADVERSARY AV-1/AV-3 (C1/C2/C8)
prod_touch: NONE (pure unit + local probe harness only)
verdict: NO-GO (fix-and-return; DELTA is small and validated below — no architectural change)
evidence_ceiling: MODERATE (same-rite adversarial review; every FINDING carries an executed bash-probe receipt)
```

## 1. What was verified GREEN (builder claims held)

| Check | Result | Receipt |
|---|---|---|
| Suite | 35/35 pass (31 new in test_freshness.py + 4 seam-contract) | `pytest tests/unit/substrate/ -q` -> `35 passed in 0.93s` |
| mypy --strict freshness.py | clean | `Success: no issues found in 1 source file` |
| Export surface | exactly 24 in `substrate/__init__.py.__all__` | `len(s.__all__) == 24` |
| Frozen signatures | `is_provable(proof, served_frame_digest, now) -> Provability`; `canonical_digest(frame: pl.DataFrame) -> str` | `inspect.signature` probe |
| Diff surface | ONLY freshness.py + test_freshness.py + test_seam_contracts.py; NO dataframes/** edits; S3 stubs (`artifact_key`/`is_servable`) still raise `NotImplementedError("owned by S3")` | `git diff origin/main --stat` = 3 files |
| [H2] both loci | naive rejected at construction (`__post_init__`), at comparison (`is_provable` now), at fold input, AND through `dataclasses.replace` (post_init re-fires) | probe R1b PASS |
| Mixed-offset math | +02:00 proof vs UTC now: age==sla PROVABLE, +1us STALE | probe H2 PASS |
| STALE precedence, inclusive boundary | per frozen contract | tests + probes |
| AV-1 MIN-fold | reused stale section drags artifact age back; fold takes content-fetch instants ONLY (signature-asserted) | test + probe R5 |
| Digest sanity | dup rows are a multiset (1 row != 2 identical rows); all-null column != absent column; +0.0/-0.0 fold; 0.1+0.2 != 0.3 (honest); layout/GID/name changes invisible; value change visible | probes D4/D5/D6/A4 PASS |
| sla_seconds_for loudness | UNKNOWN/unregistered -> ValueError; builder correctly avoided the fail-quiet `get_entity_ttl(default=300)` accessor (entity_registry.py:375-385) | test passes |

Probe harness: 23 adversarial probes, 10 raw findings, triaged below. Harness at scratchpad `qa_probes.py` (session-ephemeral; reproduction inputs inline below).

## 2. FINDINGS

### F1 — BLOCKING (HIGH): silent wrong-column-set digest -> demonstrated false PROVABLE on changed content
**Input/state**: any frame missing some/all of the four pinned value columns.
```
biz_a = pl.DataFrame([{"business_gid":"B-1","business_name":"Acme","active_mrr":5000}])
biz_b = pl.DataFrame([{"business_gid":"B-2","business_name":"Zeta","active_mrr":9999}])
canonical_digest(biz_a) == canonical_digest(biz_b)   # True — ONE digest f9dd991d55e0… for BOTH
== canonical_digest(pl.DataFrame())                  # True — also the empty-frame digest
is_provable(proof_over_biz_a, canonical_digest(biz_b), now)  # -> Provability.PROVABLE  [executed]
```
**Wrong outcome**: `canonical_digest` filters `_VALUE_COLUMNS` by presence (`if column in frame.columns`, freshness.py:216) and digests whatever remains — down to the empty set — with no error. Two different non-offer frames, an empty frame, and any frame with all value columns renamed/dropped share ONE digest; `is_provable` then returns PROVABLE over changed content. This is the RC-B-1 falsification clause verbatim ("a value edit that yields silent CLEAN = FALSIFIED") re-opened for every non-offer entity — and this module is chartered as "the ONE digest function every producer/consumer calls" while the registry's servable world includes BUSINESS (sla 3600s, asserted by this PR's own test). Partial presence is equally silent: dropping `cost` digests over the 3 remaining pins (probe A3) — an offer column-drop corruption is invisible to the CORRUPT arm because build and serve both compute the same wrong digest.
**Severity**: HIGH. **Blocks**: YES.
**Delta**: fail loud unless the pinned set is fully present:
```python
missing = [c for c in _VALUE_COLUMNS if c not in frame.columns]
if missing:
    raise ValueError(f"frame is missing pinned value column(s) {missing}; refusing to digest a partial/foreign column set")
```
Empty-but-fully-columned offer frame keeps a defined digest (correct); foreign/partial frames go loud. Add two-sided tests (non-offer frame raises; column-drop raises; empty offer frame with full columns still digests). Note the frozen seam signature (`canonical_digest(frame)`) is untouched.

### F2 — BLOCKING (MEDIUM, on freeze-timing): Decimal canonicalization is thread-context-dependent and silently rounds at >28 significant digits
**Input/state**: `mrr`/`weekly_ad_spend` are **Decimal dtype in OFFER_SCHEMA** (dataframes/schemas/offer.py:77-91 — this is the production path, polars decimal carries up to 38 digits; Python's default thread-local decimal context is prec=28).
```
_canon_number(Decimal("1234567890123456789012345678.91"))   # 30 sig digits
_canon_number(Decimal("1234567890123456789012345678.92"))
# BOTH -> "1234567890123456789012345679"  [executed — silent round-collision at default prec]
with decimal.localcontext() as c: c.prec = 5; canonical_digest(frame)
# -> DIFFERENT digest than outside the context  [executed — same frame, two digests]
```
**Wrong outcome**: `dec.normalize()` (freshness.py:166) rounds to the *ambient thread-local* context precision. Two consequences: (a) neighbouring high-precision Decimals collide silently (false same-digest -> a real value edit invisible); (b) any library in the shared process that adjusts `decimal.getcontext().prec` changes every digest computed on that thread (false CORRUPT — same frame, two digests). [H1] was frozen precisely to kill RK2 ("digest non-reproducible" — TDD §risk RK2, "top divergence risk"); pin (e) promises "one pinned fixed-precision format", and this one is neither pinned nor context-free.
**Severity**: MEDIUM by realistic input range (monetary values won't reach 29 sig digits), but it BLOCKS on freeze-timing: S2 is the LAST point where canonicalization can change without a `_DIGEST_SCHEME` bump + full rebuild, because no digest has persisted yet. Fix now is one line; fix after S4 is a migration.
**Delta (VALIDATED — executed against all five pin tests' forms, zero change to any currently-valid canonical output, so NO scheme bump needed)**:
```python
_DECIMAL_CONTEXT = decimal.Context(prec=60, traps=[decimal.Inexact])  # module-level; 60 > polars decimal 38
...
dec = Decimal(str(value))
if not dec.is_finite():                        # also fixes F3
    raise ValueError(f"non-finite number in a value column: {value!r}")
if dec == 0: return "0"
return format(dec.normalize(_DECIMAL_CONTEXT), "f")
```
Verified: context-independent under hostile prec=5; 30-digit neighbours stay distinct; >60-digit input fails LOUD (Inexact trapped) instead of silently rounding; trailing-zero strip unaffected; 1000/1000.0/1E+3/100.50/-0.0 canon forms unchanged.

### F3 — BLOCKING (bundled with F2, same line): Decimal non-finite is SILENT and collides with the string "NaN"
```
_canon_number(Decimal("NaN"))       # -> 'NaN'  silently  [executed]
_canon_number(Decimal("Infinity"))  # -> 'Infinity' silently  [executed]
canonical_digest(frame_with_Decimal_NaN_cell) == canonical_digest(frame_with_str_"NaN"_cell)  # True [executed, object dtype]
```
**Wrong outcome**: the non-finite guard (freshness.py:161) is `isinstance(value, float)`-scoped, so Decimal NaN/Inf bypass the stated pin ("non-finite ... is corruption — fail loud") and canonicalize to strings that collide with the literal strings "NaN"/"Infinity". Reachability is low (polars Decimal dtype cannot hold NaN; demonstrated via object dtype), but the pin is stated unconditionally and the fix is the same `is_finite()` line as F2. `Decimal("sNaN")` additionally escapes as `decimal.InvalidOperation` (wrong error type) today; the F2 delta makes all three loud `ValueError`s (verified).
**Severity**: MEDIUM (low reachability, pin violation). **Blocks**: bundled into the F2 delta.

### F4 — ADVISORY (LOW): number-vs-string type erasure is real and UNDOCUMENTED
```
canonical_digest(frame(cost=500)) == canonical_digest(frame(cost="500"))   # True [executed]
canonical_digest(frame(cost=True)) == canonical_digest(frame(cost="true")) # True [executed]
```
`_canon_value` maps numbers to decimal STRINGS pre-JSON, so numeric 500 and string "500" (and True vs "true") produce identical canonical cells. Within one frozen schema the dtype is stable (`cost` is Utf8), so this needs schema drift or mixed representation to bite — arguably even desirable cross-representation behavior — but the prompt's bar is "DOCUMENTED + stable" and the docstring's type-distinctness claim covers only null. **Delta (non-blocking)**: one docstring line declaring the collapse as a pin property + one pinning test freezing it either way. Unicode note: NFC vs NFD digest differently (verbatim-bytes pin, probe D3) — consistent with "strings pass through verbatim", acceptable as documented.

### F5 — ADVISORY (MEDIUM, feeds C8): freshness-SLA is silently bound to a field documented as CACHE TTL
`sla_seconds_for` returns `descriptor.default_ttl_seconds` — a field that lives under `# --- Cache Behavior ---` and is documented "Cache TTL in seconds. Defaults to 300." (entity_registry.py:122, :166-168). The freshness SLA is "the whole truth-content of RC-B" (AV-3 verbatim), and it is now governed by a knob whose existing operational meaning is cache performance. AV-3's drift construction ("config drift -> 14d SLA -> wound served PROVABLE with a green proof") is maximized when the governing field carries a DIFFERENT name and semantic: this fleet has live history of tuning warm/TTL behavior for 429 mitigation — such a tune would now silently loosen freshness truth. The TDD's "sourced from the entity registry"/"no new config home" sanctions the registry as the home, and the freshness.py docstring declares the equation CONSUMER-side; the registry field itself (the edit surface an operator actually touches) says only "Cache TTL". **Not blocking at S2** (C8 is CARRY-TO-BUILD, due at the S8 cutover gate) — but the C8 discharge obligation is now concrete: (a) annotate `default_ttl_seconds` at its definition site as ALSO the substrate-v2 freshness SLA (dual-role declaration on the edit surface), and (b) the S8 door packet must surface per-entity values + the "provably <= SLA-old" semantic delta per C8. Ledger this against C8 so it cannot be lost.

### F6 — NOTE (spec-fidelity): pin (b) deviates from the FROZEN text
TDD [H1](b): "row order = ascending sort on declared `row_key`". Implementation sorts the full per-row canonical encodings (freshness.py:227), docstring-declared as "a pragmatic refinement". Behaviorally it is a superset-robust choice (immune to null/duplicate row_key) and cannot cause producer/consumer divergence (there is only ONE function), but a FROZEN pin was reworded in code without a disposition line. Add one sentence to the TDD §10 disposition ledger (or the PR body) ratifying the refinement, so the frozen text and the frozen implementation agree on record.

### F7 — NOTE (W9 never-overclaim): "unconstructable" is over-stated at S2 altitude
`dataclasses.replace(proof, built_from_live_at=now)` (and the plain constructor) mint a fresh-stamped proof at will [executed]; `object.__setattr__` mutates the frozen+slots instance [executed — inherent Python]. What S2 honestly delivers: NO S2 API advances an instant without a content fetch (probe confirms: no forbidden verbs, fold takes fetch-instants only, [H2] holds through replace). Proof-minting custody is an S3/S4 property. Suggest softening the module docstring's "unconstructable, not merely guarded" to scope the claim to the S2 surface.

### F8 — NOTE: future-dated proof is PROVABLE
`built_from_live_at` one year in the FUTURE -> negative age -> PROVABLE [executed]. Permitted by the frozen predicate (`<= sla`); not S2's to change unilaterally. Carry to S5: negative age is an anomaly worth an observability emission.

## 3. DELTA required for GO
1. **F1**: refuse to digest a frame missing any pinned value column (loud ValueError) + two-sided tests (foreign frame raises / column-drop raises / empty-but-fully-columned offer frame still digests).
2. **F2+F3**: `_canon_number` — fixed `decimal.Context(prec=60, traps=[Inexact])` passed to `normalize`, `is_finite()` gate before it (covers float+Decimal, NaN/Inf/sNaN) + tests (context-hostility, 30-digit distinctness, Decimal-NaN loud). Validated to change NO currently-valid canonical output — no scheme bump.
3. **F6**: one disposition line for the pin (b) refinement (TDD §10 or PR body).
F4/F5/F7/F8 are non-blocking advisories; F5's registry-side annotation is cheap and recommended in this PR, with the rest of C8 riding to S8 as designed.

Re-review scope on return: DELTA-only (the three items above + no regression in the 35-green suite).

## 4. Conformance attestation
- No sibling-module or S3-stub edits; no v1 `dataframes/**` edits (`git diff origin/main --stat` = freshness.py + 2 test files).
- Export surface 24/24; frozen Seam-1 signatures intact; `Provability` closed at 3 members.
- FORK-W1 (the object->pl.DataFrame narrowing authority) is cited from SEAM-0-landed code (merged #280) — inherited, not minted here; it has no `.ledge` inscription (wave-shape-resident). Provenance note only.
- 23 adversarial probes executed; 31 builder tests + 4 seam-contract tests re-run green; mypy-strict green.

---

# ITERATION-2 — DELTA re-review at aebe5472 (2026-07-29)

```yaml
verdict: GO
scope: DELTA-only per critique-iteration-protocol (536650d4..aebe5472) + full-gate re-run + probe re-fire
delta_surface: freshness.py (+102/-48-ish), test_freshness.py (31->41 tests), entity_registry.py (COMMENT-ONLY dual-role annotation — verified no behavior line touched)
f8_ruling: comment+carry STANDS — in-module guard REJECTED (grounds below); carry upgraded to a LEDGERED S5/RC-F obligation (condition of GO, non-code)
```

## 1. Blocking fixes — each genuinely resolves the finding (probe receipts, re-fired by my own hands)

| Fix | Verification | Receipt |
|---|---|---|
| **F1** `MissingValueColumnsError` | Round-1 probes A1/A2/A3 re-fired: foreign frame LOUD, empty frame LOUD, column-dropped frame LOUD (names the missing column); the false-PROVABLE end-to-end construction is now UNBUILDABLE (the digest call raises before a proof can exist). All-null-but-present column still digests (distinct, R2-1); empty-but-fully-columned frame keeps a defined digest (F1 boundary test). Error subclasses `ValueError` (R2-6 catch-path verified). NOT added to `__all__` — export surface still 24/24 (R2-7). | probe log: `A1/A2/A3 -> loud: MissingValueColumnsError` |
| **F2** fixed `Context(prec=60, traps=[Inexact])` | Digest STABLE under hostile `getcontext().prec=5` and `prec=3` (R2-2, R2-8 — the pinned constant 295f7ffe... reproduces byte-identically INSIDE a hostile context); 30-sig-digit neighbours distinct (R2-3); `Decimal(str(...))` construction is exact/context-free so normalize was the only context-touching op — now pinned. | probe log R2-2/R2-3/R2-8 |
| **F3** `is_finite()` gate | float nan/inf AND `Decimal("NaN"/"Infinity"/"sNaN")` ALL raise loud `ValueError` (R2-4) — including sNaN, which previously escaped as `InvalidOperation`. The "NaN"-string collision path is dead (non-finite never reaches string form). | probe log R2-4 |

## 2. Known-good byte-identity — INDEPENDENTLY verified (not trusted from the builder)

- Extracted the PRE-FIX module (`git show 536650d4:...freshness.py`) and computed old-vs-new `canonical_digest` over a 15-frame battery (basic/multi/null/empty-string/"null"-literal/unicode/decimal-forms/int-float-mix/signed-zero/dup-rows/shuffled/empty-full-columns/high-precision-in-range/float-sum): **15/15 IDENTICAL — zero valid outputs changed; no `_DIGEST_SCHEME` bump required. CONFIRMED.**
- Both PR-pinned constants reproduced from the OLD implementation with my own hands: `295f7ffee5b013d3...` (single) and `1fabb37710022b0f...` (multi) both MATCH. (Audit note: my first multi reconstruction mismatched — my OWN fixture error, dropped `offer_id="OF-2"`; corrected reconstruction matches exactly. Recorded for honesty.)
- Cross-check: the pinned single constant also reproduces under a hostile prec=3 ambient context (R2-8) — byte-identity and context-independence hold simultaneously.

## 3. Advisories F4-F8 — applied sanely

- **F4**: type-erasure documented as a DELIBERATE pin in the `canonical_digest` docstring + pinning test (`test_number_string_type_erasure_is_a_deliberate_pin`). Bar was "documented + stable" — met.
- **F5**: dual-role annotation landed at BOTH registry loci (EntityDescriptor docstring L122-126 AND the field definition site under `# --- Cache Behavior ---`), naming `sla_seconds_for`, the C8 S8-gate ruling, and the AV-3 drift watch. Comment-only edit (verified via diff — no behavior line). The operator edit surface now discloses the coupling. C8 residue rides to S8 as designed.
- **F6**: pin-(b) refinement disposition RATIFIED on record in the PR-comment disposition table (full-record sort as a strictly-more-robust total order; single-function => no producer/consumer divergence). TDD frozen text unchanged — acceptable: the disposition ledger entry is the reconciliation artifact.
- **F7**: "unconstructable" softened to the honest floor at all three sites (module docstring, class docstring, renamed test) + a NEW two-sided honest-floor test proving `dataclasses.replace` CAN re-stamp while [H2] re-fires through it. W9-clean.
- **F8**: comment at the `is_provable` age arm + behavior pin test (`test_future_dated_proof_is_provable_negative_age_carry_to_s5`). Ruling below.

## 4. No-new-defect hunt

- Full suite 45/45 green; mypy --strict clean; ruff clean (all 3 delta files).
- Round-1 harness re-fired: every previously-PASS probe still PASSES (R2-9 invariants: dup-row multiset, signed-zero fold, 0.1+0.2 honesty; R2-11: inclusive boundary, +1us STALE, STALE-precedence, mixed-offset math). No regression.
- S3 stubs untouched; no v1 `dataframes/**` edits; export surface 24/24.
- ONE new NOTE (non-blocking): a >60-significant-digit input escapes as `decimal.Inexact` (an `ArithmeticError`), not `ValueError` (R2-5). LOUD is the bar and it is met; unreachable via any polars dtype (decimal caps at 38 digits, i64 at 19) except object-dtype frames. If ever touched again, wrap in `ValueError` — do not fix now (byte-identity discipline: no unforced churn on a frozen surface).

## 5. F8 RULING — comment+carry STANDS; in-module guard REJECTED (double-hit re-weighed, not dismissed)

The S6 adversary's independent hit (age=-86400 -> PROVABLE, negative `MaxStalenessAgeSeconds` emitted) upgrades the WEIGHT of the anomaly. I re-examined guard-now under that weight and REJECT it at the S2 gate on three grounds:

1. **The frozen surface has no honest verdict for "future"**: `Provability` is CLOSED (PROVABLE/STALE/CORRUPT — "no builder adds a member") with pinned semantics: STALE = age exceeded, CORRUPT = digest mismatch. Mapping future-dated to CORRUPT lies about the digest; to STALE lies about the age direction. Guard-now is therefore a SEAM AMENDMENT (architect altitude), not a bounded builder delta — smuggling it through round 2 would violate the same freeze discipline this review enforced at F2.
2. **A strict guard fails CLOSED at the freshest moment**: ordinary NTP-level skew (rebuilder Lambda clock milliseconds-to-seconds ahead of the serving Lambda) makes `built_from_live_at > now` briefly TRUE on the first post-swap read of every fresh artifact — the guard would refuse artifacts precisely when they are freshest. A skew-tolerance constant to fix that would plant an ungoverned magic number in the pure frozen core (the AV-3 disease at a new altitude).
3. **The guard does not stop the threat it implies**: any writer able to forge `built_from_live_at = future` can forge `built_from_live_at = now - 1s`, which NO in-module check can detect. The real control is proof-minting custody (S3/S4 single-writer + CAS pointer swap). What a negative age buys is DISCLOSURE — and disclosure is Seam-5's charter (RC-F: cannot read green while broken).

**Where the double-hit's weight LANDS (condition of GO — ledger entry, not code)**: the S5 carry must be a NAMED, owner-assigned obligation, not a comment: (a) the Seam-5 evaluator emits a DISTINCT negative-age anomaly signal that FIRES (alarm/flag, not a silently-negative gauge) when `age < 0` beyond skew tolerance; (b) the S6 `MaxStalenessAgeSeconds` emission is clamped-or-flagged at the emission site (a raw negative gauge is exactly the "reads green/super-fresh while broken" shape RC-F exists to kill). Route both to the wave ledger / S5-S6 dispatch so neither can evaporate. The S2 behavior pin test keeps the anomaly visible in-repo until then.

## 6. GO conditions (all non-code)

1. Coordinator ledgers the F8/S5-S6 carry per §5 (named obligation, owner-assigned).
2. F5's C8 residue (per-entity SLA values + "provably <= SLA-old" semantic delta in the S8 door packet) remains on the C8 CARRY-TO-BUILD ledger — already the TDD's design; restated so the dual-role coupling is in the packet.

With those ledgered: **GO — arm auto-merge for #281.**
