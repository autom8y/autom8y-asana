---
type: review
status: accepted
station: K4 (janitor)
procession: Freeze-Window Capitalization (hygiene-rite)
authored_at: 2026-06-12
truth_anchor: origin/main fa265ce1bde8be1d003f39501877d17fe600b0c0
rescue_worktree: /tmp/k4-seam2-rescue
branch: hygiene/seam2-econ-rescue
pr: https://github.com/autom8y/autom8y-asana/pull/133
original_worktree: /Users/tomtenuta/code/a8/repos/seam2-unit-econ
original_branch: cr3-dfr/seam2-unit-economics-population
original_base: e686ba06
snapshot: .sos/wip/SNAPSHOT-seam2-unit-econ-full-2026-06-11.patch
consumers: [K5 naxos-archive, SEAM-2 /frame (post-clear)]
---

# HYGIENE-K4 — seam2-unit-econ Rescue & Adjudication

> Rescue of the dying `seam2-unit-econ` worktree onto `origin/main fa265ce1`.
> K1 adjudication directives followed exactly. Original worktree preserved;
> snapshot covers 100% of the dirty state. Nothing lost.

---

## Execution Log

| Step | Action | Result |
|------|--------|--------|
| 1 — Snapshot | `git -C worktree diff HEAD > .sos/wip/SNAPSHOT-seam2-unit-econ-full-2026-06-11.patch` | 821-line patch; untracked files also captured |
| 2 — Worktree | `git worktree add /tmp/k4-seam2-rescue origin/main -b hygiene/seam2-econ-rescue` | HEAD `fa265ce1` |
| 3 — Apply | 5 src + 7 test files copied; parked files excluded | see file table below |
| 4 — Validate | ruff format (1 reformatted), ruff check (all pass), 377 tests pass | see test log |
| 5 — Commits | 2 atomic commits (b5dde87e, 824ab191) | see commit table |
| 6 — PV-CLOCK | `env -u GITHUB_TOKEN gh api repos/autom8y/autom8y-asana/commits/main --jq .sha` | `fa265ce1` — unchanged |
| 7 — PR | #133 created, MERGE-FROZEN | /files scope verified: 12 files exact |

---

## Applied Files (CLEAN-APPLY)

| File | Change | Commit |
|------|--------|--------|
| `src/autom8_asana/dataframes/schemas/unit.py` | discount dtype Decimal→Utf8 | b5dde87e |
| `src/autom8_asana/dataframes/models/task_row.py` | UnitRow.discount Decimal\|None→str\|None | b5dde87e |
| `tests/unit/dataframes/test_unit_schema.py` | assert discount dtype == Utf8 | b5dde87e |
| `tests/unit/dataframes/test_task_row.py` | discount fixture "10%" not Decimal | b5dde87e |
| `tests/unit/dataframes/test_builders.py` | discount fixture update | b5dde87e |
| `tests/unit/dataframes/test_extractors.py` | discount fixture + assert update | b5dde87e |
| `src/autom8_asana/dataframes/resolver/coercer.py` | _normalize_numeric_string + _to_numeric convergence | 824ab191 |
| `src/autom8_asana/dataframes/resolver/default.py` | number-branch display_value fallback | 824ab191 |
| `src/autom8_asana/dataframes/views/cf_utils.py` | number-branch display_value fallback | 824ab191 |
| `tests/unit/dataframes/test_resolver.py` | discount contract update | 824ab191 |
| `tests/unit/dataframes/test_type_coercer.py` | coercer convergence contract change | 824ab191 |
| `tests/unit/dataframes/test_seam2_unit_economics.py` | new: real-path extraction tests | 824ab191 |

---

## Parked Files (DO NOT APPLY without design ruling)

| File | Reason |
|------|--------|
| `src/autom8_asana/dataframes/builders/post_build_population_receipt.py` | Pythia fork — see adjudication below |
| `tests/unit/dataframes/test_seam1_entity_identity.py` (3 new methods + `_unit_frame` + import) | Depend on parked population receipt change |

---

## Conflict Adjudication: `post_build_population_receipt.py`

### Named Pythia Fork

**Worktree intent** (base `e686ba06`, pre-`#115`):

File: `src/autom8_asana/dataframes/builders/post_build_population_receipt.py:59-73` (worktree dirty state, in `.sos/wip/SNAPSHOT-seam2-unit-econ-full-2026-06-11.patch`)

```python
"unit": ("mrr", "weekly_ad_spend"),
```

Comment: *"FM-4 unit blind-spot cure: a hollow unit frame (mrr/weekly_ad_spend present
but 100% null on the active subset) previously fired NO receipt because 'unit' was
omitted here (assessed=False silent no-op)."*

**`origin/main` ruling** (`#115` `b2c2beb5`, FPC Phase-1):

File: `src/autom8_asana/dataframes/builders/post_build_population_receipt.py` on `origin/main` — `_VALUE_COLUMNS_BY_ENTITY` already contains:

```python
"unit": ("mrr",),
```

`#115` commit message (verifiable via `git show b2c2beb5`): chose 1-column floor, explicitly labelled `weekly_ad_spend` as `LegitimatelySparse`, citing the `$8,775/7-row null-fossil anti-precedent` — *"manufacturing false WARNs for a column that is legitimately sparse is the exact failure mode the anti-precedent warned against."*

### Resolution

The worktree predates the ratified ruling. Neither position is wrong on its own terms — they answer different questions:

- The worktree answers: *"should a hollow unit frame ever be invisible to the receipt?"* (No → add unit entry with both economic columns.)
- `#115` answers: *"should `weekly_ad_spend` be in the population floor given its observed sparsity?"* (No → `LegitimatelySparse`.)

The conflict is semantic, not textual. `origin/main` wins on the rebase baseline. The worktree's `weekly_ad_spend` hunk is **PARKED** in the snapshot.

### Design Question Routed to SEAM-2 /frame (post-soak-clear)

> **Does Consumer-2's unit-economics observability require `weekly_ad_spend` in the
> population floor — does the `LegitimatelySparse` ruling hold, or has the data-entry
> status changed since `#115`?**

Context:
- Live probe (2026-06-09): `weekly_ad_spend` is 0%-populated on the active unit subset for project 1201081073731555 — consistent with `LegitimatelySparse`.
- The worktree was authored pre-`#115`; the author may have had different data-entry expectations.
- If `weekly_ad_spend` population is a SEAM-2 deliverable (operator must enter it), the floor should include it (warmer fires RED until populated). If it is genuinely sparse long-term, `#115`'s ruling stands.

**Action**: Operator rules post-soak-clear at SEAM-2 /frame. To include `weekly_ad_spend` in the floor: apply the parked hunk from `.sos/wip/SNAPSHOT-seam2-unit-econ-full-2026-06-11.patch` + the 3 test methods + `_unit_frame` helper + `UNIT_SCHEMA` import in `test_seam1_entity_identity.py`. Those tests will then pass by design.

---

## Test Results

| Suite | Passed | Failed | Notes |
|-------|--------|--------|-------|
| `test_seam2_unit_economics.py` (new) | 13 | 0 | Real-path extraction tests |
| `test_builders.py` | 30 | 0 | |
| `test_extractors.py` | 56 | 0 | |
| `test_resolver.py` | 58 | 0 | |
| `test_task_row.py` | 54 | 0 | |
| `test_type_coercer.py` | 93 | 0 | |
| `test_unit_schema.py` | 73 | 0 | |
| `test_seam1_entity_identity.py` | 23 | 0 | Unchanged — confirms no regression |
| `tests/unit/cache/` + `tests/unit/api/` | 2665 | 5 | 5 pre-existing in `test_backends_with_manager.py` — confirmed identical on `origin/main` |

**Total rescue suite**: 377 passed, 0 new failures.

---

## Commit Log

| SHA | Subject | Scope |
|-----|---------|-------|
| `b5dde87e` | fix(dataframes): honest Utf8 dtype for unit discount field | dtype contract pair |
| `824ab191` | fix(dataframes): coercer convergence + number display_value fallback | coercer + fallback + new test |

---

## Rollback Points

- After commit 1 (`b5dde87e`): dtype contract only — independently revertible
- After commit 2 (`824ab191`): coercer + display_value fallback — independently revertible

---

## Artifacts Verified

| Artifact | Path | Status |
|----------|------|--------|
| Full diff snapshot | `.sos/wip/SNAPSHOT-seam2-unit-econ-full-2026-06-11.patch` | written (821 lines) |
| Git status snapshot | `.sos/wip/SNAPSHOT-seam2-unit-econ-status-2026-06-11.txt` | written |
| Untracked test_seam2 | `.sos/wip/SNAPSHOT-seam2-untracked-test_seam2_unit_economics-2026-06-11.py` | written (472 lines) |
| Untracked spike | `.sos/wip/SNAPSHOT-seam2-untracked-test_fpc_path_canonicalization_spike-2026-06-11.py` | written |
| PR | https://github.com/autom8y/autom8y-asana/pull/133 | 12 files, MERGE-FROZEN |
| Original worktree | `/Users/tomtenuta/code/a8/repos/seam2-unit-econ` | intact (naxos retires at K5) |
