---
type: design
artifact_type: refactor-plan
rite: hygiene
session_id: session-20260430-105520-40481a0e
target: HYG-001
evidence_grade: STRONG
authored_at: 2026-04-30
authored_by: architect-enforcer
governance:
  handoff: .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md
  parent_verdict: .ledge/reviews/VERDICT-test-perf-2026-04-29.md  # §5 deviation 1
remediation_posture: register-and-apply
---

# PLAN HYG-001 — SCAR marker codification (`@pytest.mark.scar`)

## §1 Plan purpose

The parent eunomia VERDICT (§5 deviation 1) flagged the SCAR marker as **vacuously claimed** — referenced in test docstrings but absent from `pyproject.toml [tool.pytest.ini_options].markers`, which means `pytest -m scar` collects nothing despite a 149-reference SCAR registry. The user-directive remediation posture is **register-and-apply** (not remove-the-claim): the marker exists operationally — registered in pyproject, applied to the test functions whose docstring/body cites a SCAR-NN identifier — so a downstream operator can run `pytest -m scar` and exercise the SCAR regression surface as a single selectable suite. This plan delivers a deterministic, file:line-anchored mutation set the janitor executes without judgment calls.

## §2 SCAR test enumeration (receipt-grammar)

Two-tier enumeration, both grounded in `grep` evidence across the autom8y-asana main worktree (worktree paths under `.worktrees/*` are explicitly out-of-scope per §8).

### §2.1 Tier-A — tests whose body/docstring carries a SCAR-NN identifier

| # | file:line | test_name | SCAR-NN | source |
|---|-----------|-----------|---------|--------|
| A-01 | tests/unit/reconciliation/test_section_registry.py:205 | test_valid_non_sequential_gids_emit_no_logs | SCAR-REG-001 | docstring at L232 |
| A-02 | tests/unit/reconciliation/test_section_registry.py:243 | test_excluded_section_gids_are_detected_as_sequential | SCAR-REG-001 | docstring at L244 |
| A-03 | tests/unit/reconciliation/test_section_registry.py:255 | test_unit_section_gids_are_detected_as_sequential | SCAR-REG-001 | docstring at L256 |
| A-04 | tests/unit/reconciliation/test_section_registry.py:267 | test_excluded_section_gids_warn_at_module_validation | SCAR-REG-001 | docstring at L270, assert L280 |
| A-05 | tests/unit/api/middleware/test_idempotency_finalize_scar.py:97 | test_finalize_failure_calls_logger_exception | SCAR-IDEM-001 | docstring at L91, assert L112 |
| A-06 | tests/unit/api/middleware/test_idempotency_finalize_scar.py:116 | test_finalize_failure_log_includes_impact_field | SCAR-IDEM-001 | assert L138 |
| A-07 | tests/unit/api/middleware/test_idempotency_finalize_scar.py:158 | test_response_returned_when_finalize_fails | SCAR-IDEM-001 | section header L147 |
| A-08 | tests/unit/api/middleware/test_idempotency_finalize_scar.py:177 | test_idempotency_key_echoed_when_finalize_fails | SCAR-IDEM-001 | section header L195 |
| A-09 | tests/unit/api/middleware/test_idempotency_finalize_scar.py:212 | test_retry_after_finalize_failure_sees_in_flight_409 | SCAR-IDEM-001 | docstring at L200 |
| A-10 | tests/unit/api/middleware/test_idempotency_finalize_scar.py:260 | test_store_empty_after_finalize_failure_confirms_no_persistence | SCAR-IDEM-001 | module docstring |
| A-11 | tests/unit/api/test_exports_auth_exclusion.py:56 | test_exports_route_tree_excluded_from_jwt_auth | SCAR-WS8 | module docstring L19 |
| A-12 | tests/unit/api/test_exports_auth_exclusion.py:73 | test_pat_route_trees_co_excluded_consistently | SCAR-WS8 | docstring at L76 |
| A-13 | tests/unit/dataframes/test_cascade_ordering_assertion.py:70 | test_cascade_providers_warm_before_consumers | SCAR-005/006 | docstring at L71, msg L106 |
| A-14 | tests/unit/dataframes/builders/test_cascade_validator.py:647 | test_high_nulls_logs_error | SCAR-005 | inline comment L649 |
| A-15 | tests/unit/models/business/matching/test_normalizers.py:64 | test_normalize_trailing_whitespace_stripped | SCAR-020 | docstring at L65 |
| A-16 | tests/unit/api/test_exports_format_negotiation.py:54 | test_csv_body_contains_identity_complete_column | SCAR-005-006 | inline comment L61 |
| A-17 | tests/unit/services/test_section_timeline_service.py:741 | test_timeline_computation_under_threshold_at_production_scale | SCAR-015 | docstring at L744, msg L817 |
| A-18 | tests/unit/services/test_universal_strategy_status.py:170 | test_classify_gids_null_section_returns_none | SCAR-005/006 | docstring at L175 |
| A-19 | tests/unit/services/test_universal_strategy_status.py:251 | test_classify_gids_gid_not_in_dataframe_returns_none | SCAR-005 | docstring at L256 |
| A-20 | tests/unit/core/test_entity_registry.py:1387 | test_all_resolvable_entities_have_entity_type | SCAR-005/006 | docstring at L1416 |

**Tier-A count: 20 tests** (≥16 directly proximal SCAR refs + 4 sibling tests within the same SCAR-themed test class block whose section headers/module docstring cite the SCAR; verified by re-grep).

### §2.2 Tier-B — file-themed SCAR regression suites

Files whose **module docstring** opens with "Regression tests for SCAR-NN" or names SCAR-NN as the file's invariant. **Every test function** in these files is a SCAR regression test by construction (the file's framing puts the SCAR identifier in scope for every function); per Tier-B receipt grammar they all carry the marker.

| File | Module docstring SCAR claim | Test count |
|------|------------------------------|------------|
| tests/unit/reconciliation/test_section_registry.py | L1: "Regression tests for SCAR-REG-001" | 15 |
| tests/unit/api/middleware/test_idempotency_finalize_scar.py | L1: "Regression tests for SCAR-IDEM-001" | 6 |
| tests/unit/dataframes/test_warmup_ordering_guard.py | L4: "warm-up ordering invariant (SCAR-005/006 prevention)" | 14 |
| tests/unit/dataframes/test_cascade_ordering_assertion.py | L7: "safety net for regression risk 1 (SCAR-005/006)" | 3 |

**Tier-B count: 38 tests** (file-level enumeration; mechanical via `grep -cE "^[[:space:]]*(async )?def test_"`).

### §2.3 Union — final marker target set

Tier-A ∪ Tier-B = **47 distinct test functions** (38 Tier-B + 9 Tier-A singletons in non-Tier-B files: A-11, A-12, A-14, A-15, A-16, A-17, A-18, A-19, A-20). A-01..A-10 and A-13 are Tier-B-resident and counted once.

**HANDOFF acceptance criterion #4 (≥33)**: 47 ≥ 33. **PASS** with margin of 14.

## §3 pyproject.toml mutation

**File**: `pyproject.toml`
**Anchor**: lines 114–119 (existing `[tool.pytest.ini_options].markers` array).

**Mutation**: insert one new array entry at line 119 (immediately before the closing `]` on L119), preserving alphabetical order is NOT required (existing entries are not alphabetized).

**old_string** (L118–L119, exact):

```toml
    "fuzz: OpenAPI hypothesis fuzz tests (heavy — excluded from sharded CI runs)",
]
```

**new_string** (exact):

```toml
    "fuzz: OpenAPI hypothesis fuzz tests (heavy — excluded from sharded CI runs)",
    "scar: scar-tissue regression tests (selectable via `pytest -m scar`); see .know/scar-tissue.md",
]
```

Single-line addition; net delta +1 line.

## §4 Per-test mutation pattern

**Decision: bare `@pytest.mark.scar`** (not parameterized form).

**Rationale**: The SCAR-NN identifier is already documented in each test's docstring/body (Tier-A) or module docstring (Tier-B). Encoding it in the marker would duplicate the identifier and force a coupled mutation when SCAR docs evolve. The marker's job is **selection** (`pytest -m scar`), not identification — the docstring already identifies. Simpler form satisfies the operational need with no information loss.

**Placement rule**: insert `@pytest.mark.scar` as the **outermost decorator** (line above any existing `@pytest.mark.parametrize`, `@pytest.mark.asyncio`, `@pytest.mark.<other>`, `@patch`, `@pytest.fixture` boundaries). Indentation matches the `def`/`async def` line. No blank lines between the new decorator and the next decorator/def.

**Class-level apply**: for the four Tier-B files where every test in the file gets the marker, the janitor MAY apply the marker at the **class level** (one decorator on `class TestXxx:` covers all methods inside). Verification: `pytest --collect-only -m scar` count must match the per-class test count. If a Tier-B file has top-level (non-class) test functions, those receive an individual marker each.

**Marker form** (verbatim; both function-level and class-level placements):

```python
@pytest.mark.scar
def test_xxx(...) -> None: ...

@pytest.mark.scar
class TestXxx: ...
```

**Import precondition**: `import pytest` must already exist in each target file. All 11 enumerated files already import pytest (verified via §2 grep evidence). Janitor confirms pre-mutation: `grep -l "^import pytest" {file}`.

## §5 Verification protocol

The janitor executes these commands **in order** post-application. Any failure halts the commit and triggers a re-author cycle.

1. **Marker registration confirmed (no warning)**:
   ```
   pytest -m scar --collect-only 2>&1 | grep -i "PytestUnknownMarkWarning"
   ```
   Must produce **no output** (grep exit code 1). If "PytestUnknownMarkWarning: scar" appears, the pyproject mutation did not land — abort.

2. **Collection count ≥ 33**:
   ```
   pytest -m scar --collect-only -q | tail -3
   ```
   Tail must show a "collected N items" line where **N ≥ 33**. Plan-target N=47; absolute floor N=33.

3. **Behavior preservation (all SCAR tests pass)**:
   ```
   pytest -m scar --tb=short
   ```
   Must exit **0**. If any test fails, the marker has been applied to a test whose pre-mutation state was failing OR the indentation/placement broke the file — abort and revert.

4. **Negative gate (no false positives in non-marked tests)**:
   ```
   pytest -m "not scar" --collect-only -q | tail -3
   ```
   Tail must show a "collected M items" line where **M = (full unit suite count) − N**. Confirms the marker is not silently leaking via a class-level decorator inheritance bug.

5. **Optional — full unit suite still green**:
   ```
   pytest tests/unit -q
   ```
   Sanity check that adding decorators did not break collection elsewhere (e.g., a malformed import). Janitor MAY skip if steps 1–4 pass; audit-lead may require this in their gate.

## §6 Atomic commit shape

**Recommendation: 2 commits**.

| # | scope | message |
|---|-------|---------|
| 1 | pyproject.toml only | `chore(pytest): register scar marker for scar-tissue regression suite` |
| 2 | 11 test files | `test(scar): apply @pytest.mark.scar to ~47 SCAR regression tests [HYG-001]` |

**Rationale**:

- Commit 1 is a **single-line registration mutation** that is independently reviewable and independently revertable. If a downstream consumer adopts the marker before commit 2 lands, the registration alone causes no harm (zero tests are marked yet, but `pytest -m scar` is now a non-warning operation).
- Commit 2 is the **per-test application**. Its diff is large (~50 decorator additions across 11 files) but mechanical. Reviewing commit 2 as separate diff makes the application surface clear.
- Rollback boundaries: revert commit 2 alone if marker placement is wrong; revert both if registration is rejected upstream.
- The two-commit shape follows the same "register-then-apply" pattern as the user directive, giving each operation an independent rollback point per the architect-enforcer phase-sequencing principle [RF:SRC-006 Shieh et al. 2024 — sharding bounds blast radius] [STRONG | 0.75 @ 2026-04-01].

## §7 Risks (janitor pre-flight surfacing)

| # | risk | likelihood | mitigation |
|---|------|------------|------------|
| R-1 | pytest strict-marker mode rejects scar before pyproject mutation lands → mass test failure if commits land out of order | LOW (no `--strict-markers` in current addopts at L113) | Land commit 1 BEFORE commit 2; verify by running step §5.1 between commits. |
| R-2 | Class-level `@pytest.mark.scar` inherits onto a non-test helper method or fixture inside the class, causing collection surprise | LOW | Apply at function level (not class level) for any class containing non-test members; verify via §5.2 collection count matching enumeration §2.3 (47). |
| R-3 | A Tier-B test file's class structure splits SCAR and non-SCAR tests in same class (e.g., a setup-helper class with mixed concerns) | MEDIUM-LOW for `test_section_registry.py` (15 tests across 3 classes) | Apply at function level for `test_section_registry.py`; class-level OK for the other three Tier-B files where the file is uniformly SCAR-themed. |
| R-4 | Decorator stacking breaks `@pytest.mark.parametrize` semantics | LOW | Bare `@pytest.mark.scar` at outermost position composes cleanly with parametrize/asyncio/patch — no semantic change. |
| R-5 | CI shard topology (`--dist=load`, L113) cascades a marker-induced collection failure across shards | LOW | §5.1 + §5.2 catch this pre-merge. |

## §8 Out-of-scope refusal (janitor MUST NOT)

The janitor's mandate is bounded to **decorator addition + pyproject markers entry**. Any of the below is a scope violation:

1. **Do NOT modify any test body** — no logic changes, no assertion edits, no docstring rewrites, no parameter changes. Only the decorator line is added.
2. **Do NOT modify the SCAR-NN identifier in any test** — the docstring SCAR-NN references stay verbatim. The marker captures *that* a test is SCAR-tagged, not *which* SCAR.
3. **Do NOT touch other markers** in `pyproject.toml` (slow/integration/benchmark/fuzz at L115–L118 stay byte-identical).
4. **Do NOT add `--strict-markers`** to `addopts` at L113 — that is a separate hardening initiative requiring its own ADR.
5. **Do NOT touch worktree paths** (`.worktrees/*`) — those are independent worktrees with their own commit lineages; cross-worktree edits violate worktree isolation. Plan scope is the autom8y-asana main worktree only.
6. **Do NOT modify `.know/scar-tissue.md`** — registry stays canonical; this initiative does not amend the registry, only operationalizes its consumer-side selection.
7. **Do NOT add tests** — if the enumeration §2.3 reaches only 46 (one off-by-one), do NOT manufacture a 47th. Surface the count mismatch to architect-enforcer for adjudication.
8. **Do NOT reorder existing decorators** — `@pytest.mark.scar` goes at the top; everything else preserves byte-exact order/spacing.
9. **Do NOT touch platform mods in working tree** (per HANDOFF: platform mods are isolated by `/sos` lifecycle agent; janitor stays out).

## §9 Janitor handoff checklist

- [ ] §3 mutation applied (pyproject.toml +1 line)
- [ ] §4 mutation applied across all 11 files in §2 (decorator additions)
- [ ] §5.1–§5.4 verification gates all green
- [ ] Commits 1 and 2 landed in order per §6
- [ ] No file in §8 prohibition list mutated

**Plan terminus.** Verification protocol §5 + scope-fence §8 are the contract surface.
