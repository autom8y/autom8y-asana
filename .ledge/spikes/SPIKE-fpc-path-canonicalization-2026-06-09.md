---
type: spike
title: FPC Path-Canonicalization Mechanism (riskiest pillar — N>=2 throughline)
initiative: field-provenance-population-contract
status: accepted  # spike concluded; findings stand (lifecycle-valid value per ledger schema)
rung: spike-proven  # mechanism sound + field-agnostic + zero-new-calls; NOT live-healed (operator-gated)
date: 2026-06-09
author: principal-engineer (10x-dev, N3)
head: 50ebfe3381a627df868887ca3cdf9e223e1f9a90
worktree: /Users/tomtenuta/Code/a8/repos/seam2-unit-econ  # @ e686ba06 (buildable sibling)
poc: /Users/tomtenuta/Code/a8/repos/seam2-unit-econ/tests/spikes/test_fpc_path_canonicalization_spike.py
upstream:
  - .ledge/specs/TDD-field-provenance-population-contract-2026-06-09.md  # §5 spike target
evidence_grade: MODERATE  # self-ref ceiling per self-ref-evidence-grade-rule; STRONG = eunomia rite-disjoint (HELD)
---

# SPIKE — FPC Path-Canonicalization Mechanism

> **Spike question (TDD §5, the riskiest pillar):** does ONE field-agnostic
> canonical-source-materialization mechanism — *reuse the maximal-completeness
> per-task-GET copy as the null-recovery backstop for the list-path frame* —
> heal BOTH `unit.mrr` (cell-0) AND a 2nd number cell `unit.weekly_ad_spend`
> (the sibling, same SOURCE root) via the SAME code path, while adding ZERO new
> Asana API calls (reusing the hierarchy-warmed GET copy already fetched for the
> cascade, NOT issuing per-row N+1 GETs that would regress CR-3)?
>
> **Answer: YES — proven for the mechanism.** (NOT live-healed; see §5 boundary.)

---

## 1. Result Summary

| Spike acceptance criterion (TDD §5.3) | Result | Receipt |
|---|---|---|
| N>=2: one mechanism heals 2 distinct number cells | **PROVEN** | `test_one_mechanism_heals_mrr_AND_weekly_ad_spend` PASSED — 4 cells (mrr+weekly_ad_spend × 2 rows), `healed_columns == {"mrr","weekly_ad_spend"}` |
| ZERO new `get_async` calls (CR-3-safe gate) | **PROVEN** | `test_recovery_issues_ZERO_new_get_async_calls` PASSED — `client.get_async_calls == 0`, 4 cells healed |
| Cache miss → honest null, no N+1, no fabrication | **PROVEN** | `test_cache_miss_yields_honest_null_no_n_plus_1_no_fabrication` PASSED |
| Field-agnostic beyond unit.* (G-PROPAGATE) | **PROVEN** | `test_mechanism_is_field_agnostic_offer_cost_via_same_path` PASSED — offer.cost healed via the SAME function |
| Defect is real before the cure (G-THEATER control) | **PROVEN** | `test_RED_list_path_genuinely_drops_both_number_cells` PASSED — list-path cf yields `None` under canonical extraction |
| Live healing (571 falls, source genuinely null vs path-stripped) | **OPERATOR-GATED — NOT proven** | 2 SKIP sentinels (see §5) |

Full PoC receipt (run via `direnv exec . uv run python -m pytest … -q --no-header -p no:randomly`):

```
......ss                                                                 [100%]
6 passed, 2 skipped in 0.14s
```

`ruff check` on the PoC: `All checks passed!`

---

## 2. The Mechanism (TDD §5.1 realized — the SOLE propagation point)

A single field-agnostic function `recover_null_number_cells(rows, contracts,
warm_cache, client)`:

- iterates each row × each `NumberRecoveryContract` (a minimal field-agnostic
  slice of the TDD FieldContract: `(column, cf_source, cache_reuse=True)`);
- for a cell that is NULL on the list frame, reads the **already-fetched**
  hierarchy-warm GET copy via `warm_cache.get_versioned(gid)` (mirrors
  `cache/backends/memory.py:212` → `CacheEntry | None`, `.data` = task dict);
- extracts the number via the **canonical** `extract_cf_value` number-branch
  semantics (reconstructed inline as `_canonical_extract_number` — dispatch on
  `resource_subtype == "number"`, return `number_value`);
- on cache miss → leaves an HONEST null. It NEVER calls `client.get_async`
  (the client is injected ONLY to count-prove zero calls), and NEVER zero-fills.

The body names NO field/entity. mrr, weekly_ad_spend, and offer.cost all flow
through the identical loop — this is the **G-PROPAGATE** property: one
propagation point for the entire number-cell class, no per-field orphan fixes.

---

## 3. N>=2 Throughline Evidence (the two — actually three — fields)

| field | entity | cf_source | healed by | API calls |
|---|---|---|---|---|
| `mrr` | unit | "MRR" | `recover_null_number_cells` | 0 |
| `weekly_ad_spend` | unit | "Weekly Ad Spend" | `recover_null_number_cells` (SAME call) | 0 |
| `cost` | offer | "Cost" | `recover_null_number_cells` (SAME function, diff entity) | 0 |

`mrr` is cell-0 (the economic headline; `coherence_consumers=("offer.mrr",)`,
the 571-gun source). `weekly_ad_spend` is the TDD-designated 2nd Source field —
same SOURCE root, but **`LegitimatelySparse`** per G-DENOM (the mechanism heals
its *presence*; the population policy does NOT floor it — recovery and
population-policy are orthogonal, exactly as the contract separates them).
`offer.cost` over-proves field-agnosticism across an entity boundary (one of the
8 unguarded number cells in the opportunity matrix).

The N>=2 receipt is mechanical, not asserted by adjective:
`{col for (_gid, col) in report.recovered_keys} == {"mrr", "weekly_ad_spend"}`.

---

## 4. ZERO-NEW-CALLS Proof + G-THEATER Broken-Fixture-RED

### 4.1 Zero-calls receipt (CR-3-safe gate, TDD §5.3)

`test_recovery_issues_ZERO_new_get_async_calls` asserts `client.get_async_calls
== 0` after healing 4 cells. The mechanism is O(null-rows reusing cache), not
O(rows fetched).

### 4.2 The tests have teeth — proven by deliberate mutation (G-THEATER)

Green-run-alone is rejected. Two mutations were applied and observed RED, then
reverted:

**Mutation 1 — turn the mechanism into the REJECTED N+1 fan-out** (inject
`client.get_async_calls += 1` at the cache-read site):

```
>       assert client.get_async_calls == 0
E       assert 1 == 0
FAILED ... ::test_recovery_issues_ZERO_new_get_async_calls
FAILED ... ::test_cache_miss_yields_honest_null_no_n_plus_1_no_fabrication
FAILED ... ::test_partial_cache_heals_only_what_is_cached
FAILED ... ::test_mechanism_is_field_agnostic_offer_cost_via_same_path
4 failed, 2 passed, 2 skipped
```

The CR-3-safe gate genuinely catches the N+1 design. (TDD §5.2's rejected
design is empirically rejectable by this test, not just by prose.)

**Mutation 2 — make the warm cache carry the path-stripped cf** (swap the GET
copy for the list-path cf, `number_value=None`):

```
>       assert list_frame_rows[0]["mrr"] == 79485.0
E       assert None == 79485.0
FAILED ... ::test_one_mechanism_heals_mrr_AND_weekly_ad_spend
FAILED ... ::test_recovery_issues_ZERO_new_get_async_calls
FAILED ... ::test_partial_cache_heals_only_what_is_cached
3 failed, 3 passed, 2 skipped
```

The heal is genuinely sourced from the GET copy's `number_value` — when the
cache carries the path-stripped frame, the heal correctly fails. This is the
A-vs-B discriminator in microcosm: recovery only works if the GET copy actually
carries a value the list path dropped.

### 4.3 The defect control (no green-run theater)

`test_RED_list_path_genuinely_drops_both_number_cells` proves the fixture
reproduces the live AP-1 defect BEFORE the cure: the list-path cf has
`number_value=None` and `_canonical_extract_number(list_cf) is None`. The
mechanism cures a frame that was genuinely broken.

---

## 5. CR-3 Safety Argument

The CR-3 receiver substrate was stabilized as single uvicorn worker / 0.25 vCPU
/ SlowAPI 100/min with no SA exemption (per memory: receiver bulk-fanout
reliability + cr3-cutover-authorized-soak). The TDD §5.2 names the regression
risk: a per-row `get_async` over ~3021 unit rows would blow both the rate limit
and the single-worker budget.

The spike's binding gate is `get_async` call delta == **0**. The mechanism
reuses `warm_cache.get_versioned` (the GET copy `hierarchy_warmer.py:186`
ALREADY fetched for cascade-ancestor resolution and stored via
`put_batch_async`). Recovery cost is O(null-rows reading an in-process cache),
introducing **zero** new outbound Asana traffic on the warm path. The sad path
(cache miss) does NOT degrade to N+1 — it degrades to honest null. CR-3's
single-worker/SlowAPI ceiling is therefore untouched by the mechanism on both
the happy and sad paths.

Caveat carried forward: at IMPLEMENTATION time, if Phase-2 wires the recovery
read-point such that a cache miss is ever filled by a fresh GET, that crosses
the CR-3 regression line AND the FEATURE×external-integration security gate
(TDD §9). The spike proves the mechanism need NOT do this; the implementation
must hold the line.

---

## 6. Live-Efficacy Boundary (G-RUNG — what this spike does NOT prove)

The spike proves the **mechanism** is sound, field-agnostic, and zero-new-call.
It explicitly does NOT prove **live healing**. Two boundary sentinels are
SKIP-documented in the PoC to keep the boundary loud and un-fakeable:

1. **A-vs-B is operator-probe-gated** (`test_LIVE_get_copy_actually_carries_
   number_value_for_571_phones`, SKIPPED): the spike assumes the GET copy
   carries `number_value` where the list path dropped it. Whether the LIVE
   source is *genuinely null* (the value was never entered in Asana) vs *merely
   path-stripped* (present on GET, dropped on list) requires a live `ASANA_PAT`
   GET against a real unit task for the 571 null phones. If the live source is
   genuinely null, recovery correctly yields honest null and the 571 does NOT
   fall — the mechanism is sound either way, but the *cure magnitude* is
   unknown until the live probe runs.

2. **Live population is operator-re-warm-gated** (`test_LIVE_571_gun_falls_
   after_rewarm`, SKIPPED): moving `coherent` off 0 (NFR-2) needs an operator
   re-warm of the unit frame through the recovery path + a re-run of the §2
   DuckDB 571 canary on live S3 parquet. The spike does not touch live S3.

3. **FM-A (Asana non-determinism)** remains a MITIGATION not a GUARANTEE: the
   mechanism assumes same-task+same-opt_fields determinism between the cached
   GET copy and the list frame. Temporal server drift is out of scope.

---

## 7. Substrate Fidelity (G-PROVE — receipts at origin/main 50ebfe33)

- **opt_fields are symmetric** → the list drop is server-side, not an omission:
  `fields.py:69` (`"custom_fields.number_value"`) ∧ warmer GET uses
  `BASE_OPT_FIELDS` (same list). Confirmed by reading `builders/fields.py`.
- **the GET copy carries number_value**: `hierarchy_warmer.py:186`
  `get_async(gid, opt_fields=BASE_OPT_FIELDS)` → `_task_to_dict` →
  `put_batch_async(...)`. Confirmed by reading `builders/hierarchy_warmer.py`.
- **cache contract**: `cache/backends/memory.py:212` `get_versioned(key,
  EntryType) -> CacheEntry | None`; `cache/models/entry.py:101` `data:
  dict[str, Any]`. Confirmed by `git show 50ebfe33:…`.
- **extraction primitive**: `dataframes/views/cf_utils.py` `extract_cf_value`,
  number branch returns `number_value` (line ~49-50 at 50ebfe33). Confirmed.

**Worktree-divergence note (honesty):** the spike worktree's
`views/cf_utils.py` AND `resolver/default.py` are locally MODIFIED (uncommitted)
— `cf_utils.py` adds a `display_value` fallback on the number branch (the SEAM-2
defense-parity patch). The PoC therefore reconstructs the **canonical** origin/
main number-branch semantics inline (`_canonical_extract_number`, no
display_value fallback) so the spike proves the path-canonicalization mechanism
independent of the local patch. The dirty tree was NOT staged.

---

## 8. Confidence

**MODERATE** (self-ref ceiling per `self-ref-evidence-grade-rule`; STRONG
requires the rite-disjoint eunomia critic, HELD as an operator lever).

- Mechanism soundness, field-agnosticism, and zero-new-calls: **high
  confidence** within MODERATE — proven by passing assertions AND by
  broken-fixture-RED on two independent mutations (the tests have teeth).
- Live cure magnitude (will the 571 actually fall?): **unknown** — gated on the
  operator A-vs-B probe. The spike is honest that recovery yields honest-null if
  the live source is genuinely null.
- The mechanism is **CR-3-safe by construction** (zero new calls on both happy
  and sad paths); the implementation must preserve this at wiring time.

**Rung topped at: spike-proven (mechanism).** NOT live, NOT verified-realized.
