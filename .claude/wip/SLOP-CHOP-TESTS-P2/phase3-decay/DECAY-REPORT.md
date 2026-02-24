---
type: audit
---
# DECAY-REPORT: Temporal Debt Scan — Test Suite Phase 3

**Scope**: `tests/integration/` (42 files), `tests/validation/` (8 files), `tests/benchmarks/` (4 files), `tests/_shared/` (2 files — dead code only)
**Date**: 2026-02-24
**Agent**: cruft-cutter
**Staleness boundary**: 90-day heuristic (before 2025-11-25); provable evidence takes priority

---

## Summary Table

| Category | Count |
|---|---|
| dead-helper | 4 |
| stale-skip | 3 |
| ephemeral-comment | 5 |
| dead-shim | 2 |
| orphaned-infra | 3 |
| **Total** | **17** |

All findings are SMELL severity. Temporal debt is always advisory.

---

## Findings

### Finding P3-001: Unused async fixture `stale_task`
- **Severity**: SMELL
- **File**: `tests/integration/automation/polling/conftest.py:164`
- **Category**: dead-helper
- **Evidence**: The `stale_task` async fixture is defined at line 164. An exhaustive grep across the entire `tests/` tree shows zero usage as a pytest fixture parameter in any test file. The only matches for `stale_task` as a name are local variables constructed inline within `test_end_to_end.py` (line 1000) using `MockTask(...)` directly — not injected from conftest. The fixture itself explains the limitation in its docstring ("we cannot actually make a task stale without waiting days"), which is why callers bypassed it with inline `MockTask`. Git last-modified: 2026-02-22.
- **Suggested fix**: Remove the `stale_task` fixture (lines 163–196) from `tests/integration/automation/polling/conftest.py`. The inline `MockTask` usage in `test_end_to_end.py` is the correct pattern, per the fixture's own note.

---

### Finding P3-002: Unused async fixture `task_with_due_date`
- **Severity**: SMELL
- **File**: `tests/integration/automation/polling/conftest.py:201`
- **Category**: dead-helper
- **Evidence**: The `task_with_due_date` async fixture (lines 201–228) creates a real Asana API task with a due date. An exhaustive grep of `task_with_due_date` across all test files shows zero usage as a pytest fixture parameter in any test. Deadline trigger tests in `test_trigger_evaluator_integration.py` all construct `MockTask` objects inline with controlled `due_on` values instead. The fixture requires live API access (`test_project_gid`), which further discourages use in the mock-based trigger tests. Git last-modified: 2026-02-22.
- **Suggested fix**: Remove the `task_with_due_date` fixture (lines 200–228) from `tests/integration/automation/polling/conftest.py`.

---

### Finding P3-003: Unused helper triad in `tests/validation/persistence/conftest.py`
- **Severity**: SMELL
- **File**: `tests/validation/persistence/conftest.py:116,177,218`
- **Category**: dead-helper
- **Evidence**: Three standalone helpers defined in the conftest are never imported or used by any test file:
  - `create_multi_result()` (line 116): builds lists of mixed `BatchResult`. Grep across all `tests/` files shows no import or direct call.
  - `create_task_hierarchy()` (line 177): builds a tree of `Task` objects for hierarchy testing. Same — never imported.
  - `CallTracker` class + `call_tracker` fixture (lines 218, 236): a call-count utility. Never imported or used in any validation test file.
  The active imports in `test_functional.py`, `test_error_handling.py`, `test_concurrency.py`, and `test_performance.py` only use `create_mock_client`, `create_success_result`, and `create_failure_result`. Git last-modified for conftest: 2025-12-22 (63 days ago).
- **Suggested fix**: Remove `create_multi_result`, `create_task_hierarchy`, `CallTracker`, and the `call_tracker` fixture from `tests/validation/persistence/conftest.py`. These were infrastructure staged for tests that were never written or were removed.

---

### Finding P3-004: Orphaned test stub block — `tests/integration/persistence/test_live_api.py`
- **Severity**: SMELL
- **File**: `tests/integration/persistence/test_live_api.py:42`
- **Category**: orphaned-infra
- **Evidence**: The file contains a large multi-line string (lines 42–306) that is a complete test suite — `TestLiveAPICreate`, `TestLiveAPIUpdate`, `TestLiveAPIBatch`, `TestLiveAPIDelete`, `TestLiveAPIErrors` — all stored as dead Python string literals, never executed. The companion comment at line 38 reads: `"Note: These tests require the AsanaClient to be implemented with a save_session() method that returns a SaveSession instance. Once implemented, uncomment and adapt as needed."` The condition has been met: `AsanaClient.save_session()` is fully implemented and actively used throughout the codebase (confirmed in `src/autom8_asana/client.py:776`). Git blame shows the file was created 2025-12-22 (63 days ago). This is a migration stub that was never promoted to active tests after the implementation landed.
- **Suggested fix**: Either promote the test suite from the string literal to active pytest tests (replacing the placeholder `TestIntegrationInfrastructure` class), or remove the entire block if coverage is provided elsewhere. Do not leave it as a multi-line string — it provides zero test coverage.

---

### Finding P3-005: Stale "AsanaClient not available" scaffold in persistence conftest
- **Severity**: SMELL
- **File**: `tests/integration/persistence/conftest.py:18,58`
- **Category**: orphaned-infra
- **Evidence**: Line 18 reads `"# Note: These imports assume the client module exists"` and lines 58–80 contain a commented-out fixture block preceded by `"# Uncomment when AsanaClient is available:"`. AsanaClient has been implemented since at least commit `6095709` (2025-12-22). The conftest was last modified 2025-12-22 (63 days ago). The "uncomment when available" instruction is stale. The commented-out fixtures (`live_client`, `cleanup_tasks`) are also unnecessary now — the same pattern exists in `tests/integration/automation/polling/conftest.py` which is the live API fixture reference.
- **Suggested fix**: Remove the commented-out fixture block (lines 58–80) and the stale guard comment at line 18. If live-API persistence tests are desired, follow the pattern in `automation/polling/conftest.py` instead.

---

### Finding P3-006: `@pytest.mark.skip` with inaccurate removal reason — `_CompletionAdapter` test
- **Severity**: SMELL
- **File**: `tests/integration/test_lifecycle_smoke.py:1695`
- **Category**: stale-skip
- **Evidence**: `test_completion_adapter_returns_empty` is skipped with the reason `"_CompletionAdapter removed: CompletionService is now used directly without a shim adapter (see _import_completion_service in engine.py)"`. The skip implies the tested class no longer exists. The test body (lines 1699–1712) still contains `from autom8_asana.lifecycle.engine import _CompletionAdapter` inside the function body and attempts to instantiate it. No audit was performed to verify the class exists before the skip was added; no removal date or tracking ticket is cited. Git last-modified: 2026-02-18. This is a permanently skipped dead test — the skip description says the tested thing was removed, which means the test itself should be deleted rather than kept indefinitely.
- **Suggested fix**: Verify whether `_CompletionAdapter` still exists in `autom8_asana/lifecycle/engine.py`. If confirmed absent, delete `test_completion_adapter_returns_empty` entirely. If `_CompletionAdapter` still exists, remove the skip and investigate why the test was incorrectly marked.

---

### Finding P3-007: `MIGRATION_REQUIRED` skip on `TestProjectDataFrameBuilderUnifiedIntegration` and `TestNoRegression` — migration completed
- **Severity**: SMELL
- **File**: `tests/integration/test_unified_cache_integration.py:37,182,507`
- **Category**: stale-skip
- **Evidence**: Two test classes (`TestProjectDataFrameBuilderUnifiedIntegration` at line 182, `TestNoRegression` at line 507) are marked `@MIGRATION_REQUIRED` — `pytest.mark.skip(reason="Requires migration to ProgressiveProjectBuilder - constructor signatures differ")`. The git tag `unified-cache-phase-4-complete` was applied 2026-01-02 (53 days ago). The migration to `ProgressiveProjectBuilder` is complete — the builder exists and is actively used in source (`src/autom8_asana/cache/dataframe/factory.py`). The test bodies are all `pass` stubs. The `MIGRATION_REQUIRED` sentinel was intended for removal after migration; it was not removed.
- **Suggested fix**: Either write the actual migration-aware test bodies using `ProgressiveProjectBuilder` (the constructors now exist), or delete the two skipped classes and the `MIGRATION_REQUIRED` sentinel. Stub `pass` bodies inside skipped classes provide zero coverage and false assurance.

---

### Finding P3-008: `LEGACY_CASCADE_PATH` skip with inaccurate removal claim — `cascade_plugin` still optional
- **Severity**: SMELL
- **File**: `tests/integration/test_unified_cache_integration.py:49,280,299`
- **Category**: stale-skip
- **Evidence**: Two tests (`test_resolver_without_plugin_uses_existing_path` at line 280, `test_both_paths_return_same_value_for_unregistered_field` at line 299) are skipped with `LEGACY_CASCADE_PATH`, reason: `"CascadingFieldResolver requires cascade_plugin after TDD-UNIFIED-CACHE-001 Phase 4. Legacy path without cascade_plugin has been removed."` This is factually incorrect. Inspection of `src/autom8_asana/dataframes/resolver/cascading.py` shows `CascadingFieldResolver.__init__` still accepts `cascade_plugin: CascadeViewPlugin | None = None` (optional, defaults to None) and `_parent_cache: dict[str, Task] = {}` still exists at line 197. The legacy path has NOT been removed. The assertions these tests would make (`resolver._parent_cache == {}`, `resolver._cascade_plugin is None`) remain true in the current codebase — both tests would pass if un-skipped.
- **Suggested fix**: Remove the `LEGACY_CASCADE_PATH` skip markers from both tests and run them to confirm they pass. Delete the `LEGACY_CASCADE_PATH` sentinel definition (line 49) once its three use-sites are cleaned up.

---

### Finding P3-009: Ephemeral comment — `spike_write_diagnosis.py` with hardcoded task GID
- **Severity**: SMELL
- **File**: `tests/integration/spike_write_diagnosis.py:1`
- **Category**: ephemeral-comment
- **Evidence**: The file opens with `"""Diagnostic spike: trace the exact write pipeline — ALL field types. Target: Task 1213235375126350 (leftover E2E proof offer)"""` and hardcodes `TARGET_GID = "1213235375126350"` at line 21 — a live Asana task GID from a specific debugging session. The file is a standalone script, not a pytest test. The investigation it served is concluded — line 222 writes `"internal_notes": "All field types verified by spike_write_diagnosis.py"`, confirming the spike completed. Git last-modified: 2026-02-15 (9 days ago). Spike scripts belong outside `tests/` once the spike is done.
- **Suggested fix**: Delete `tests/integration/spike_write_diagnosis.py`. If the script is needed for future diagnosis, move it to `scripts/` or similar. Hardcoded production GIDs in diagnostic scripts should not persist in the test directory.

---

### Finding P3-010: Ephemeral comment — initiative tag referencing `MIGRATION-PLAN-legacy-cache-elimination` in fixture docstring
- **Severity**: SMELL
- **File**: `tests/integration/test_cascading_field_resolution.py:108`
- **Category**: ephemeral-comment
- **Evidence**: The `mock_client` fixture docstring reads: `"Per MIGRATION-PLAN-legacy-cache-elimination RF-008: Sets unified_store=None to ensure tests use legacy cascade resolution path (not unified cache)."` No `MIGRATION-PLAN-legacy-cache-elimination` document exists in the repository. The `unified-cache-phase-4-complete` tag (2026-01-02) confirms the migration is complete. The initiative reference is an artifact of the migration epoch; the behavior (`client.unified_store = None`) is self-describing. Git last-modified: 2026-01-19.
- **Suggested fix**: Replace `Per MIGRATION-PLAN-legacy-cache-elimination RF-008:` with a plain technical description: `"Sets unified_store=None to exercise the legacy cascade resolution path without unified cache."` Drop the initiative reference — it belongs in commit history.

---

### Finding P3-011: Ephemeral comment — `Per IMP-23` ticket reference in test docstring
- **Severity**: SMELL
- **File**: `tests/integration/test_hydration_cache_integration.py:91`
- **Category**: ephemeral-comment
- **Evidence**: The docstring at line 91 reads: `"Per IMP-23: Hydration module uses full field set for all fetches, eliminating the detection-then-refetch pattern."` `IMP-23` is an internal implementation tracker reference. The commit that shipped the change is `4cf54f87` (2026-02-16, `"perf(models): unify detection field set to eliminate business double-fetch (IMP-23)"`). Implementation is complete; the ticket reference in the docstring is a post-ship artifact. The description after the reference is the documentation value.
- **Suggested fix**: Remove `Per IMP-23:` from the docstring prefix. Preserve the description. Ticket references belong in commit messages.

---

### Finding P3-012: Ephemeral comment — `Per Story 3.2` and `IMP-20` references in benchmark module
- **Severity**: SMELL
- **File**: `tests/benchmarks/test_insights_benchmark.py:4,151,423,484,546`
- **Category**: ephemeral-comment
- **Evidence**: The module docstring at line 4 opens with `"Per Story 3.2: Performance benchmarking to validate P95 < 500ms target."` `Story 3.2` is a completed story reference with no active tracker visible in the repository. Lines 151, 423, 484, and 546 also contain `Per IMP-20:` attribution comments inside implementation docstrings and inline comments. These are initiative tags embedded in production code that describe what the system does; the implementation context they reference has shipped. Git last-modified: 2026-02-16.
- **Suggested fix**: Remove `Per Story 3.2:` from the module docstring; replace with a plain description of the benchmark purpose. Remove the `Per IMP-20:` inline attributions from `build_batch_mock_handler` and related comments; preserve the factual descriptions of the behavior.

---

### Finding P3-013: Dead shim — orphaned env-var fixtures in `tests/integration/persistence/conftest.py`
- **Severity**: SMELL
- **File**: `tests/integration/persistence/conftest.py:40,47,53`
- **Category**: dead-shim
- **Evidence**: The conftest defines `asana_token` (line 40), `workspace_gid` (line 47), and `project_gid` (line 53) — each calling `get_env_or_skip()`. A grep of all `tests/integration/persistence/` Python files shows no test function uses these fixture names as parameters. `test_live_api.py` reads `ASANA_ACCESS_TOKEN` directly via `os.getenv()` without fixture injection. All other persistence tests use inline mock clients. These fixtures were scaffolded for the live API tests that exist only as a multi-line string stub (see P3-004). Git last-modified: 2025-12-22.
- **Suggested fix**: Remove `asana_token`, `workspace_gid`, and `project_gid` fixtures from `tests/integration/persistence/conftest.py`. They are shims from the same migration stub epoch as the `test_live_api.py` block. Re-introduce them if and when the live API tests are promoted from string literals.

---

### Finding P3-014: Dead shim — `LEGACY_PATH_REMOVED` skip on a double-skipped empty stub
- **Severity**: SMELL
- **File**: `tests/integration/test_unified_cache_integration.py:200`
- **Category**: dead-shim
- **Evidence**: `test_builder_without_unified_store_uses_existing_path` (line 200) carries both the class-level `@MIGRATION_REQUIRED` skip AND an inner `@LEGACY_PATH_REMOVED` skip, with a body of `pass`. It is double-skipped and unconditionally unreachable. The outer `MIGRATION_REQUIRED` class decorator would suppress execution regardless of the inner marker. The inner `LEGACY_PATH_REMOVED` (reason: "unified_store is now mandatory in Phase 4") adds no discriminating value. This skip-on-skip pattern accumulated during the Phase 3→4 migration and was never cleaned up. Git tag `unified-cache-phase-4-complete`: 2026-01-02.
- **Suggested fix**: Delete `test_builder_without_unified_store_uses_existing_path` entirely. Also delete the `LEGACY_PATH_REMOVED` sentinel definition (line 43) if its remaining two use-sites (P3-008) are cleaned up simultaneously.

---

### Finding P3-015: Orphaned-infra — `tests/integration/conftest.py` is a narrow single-consumer conftest using a superseded construction pattern
- **Severity**: SMELL
- **File**: `tests/integration/conftest.py:15,45`
- **Category**: orphaned-infra
- **Evidence**: `client_fixture` (line 15) requests `mock_http`, `auth_provider`, and `logger` from the root conftest, then manually constructs a `MagicMock(spec=AsanaClient)` with a real `TasksClient` injected via internal attributes (`_http`, `_auth_provider`, `_log`). `task_fixture` (line 45) returns `Task(gid="1234567890", name="Test Task")`. Both fixtures are consumed only by `test_gid_validation_edge_cases.py`. The `MockClientBuilder` utility in `tests/conftest.py:64` is the current project pattern for mock client construction — `client_fixture` predates it and uses a more fragile approach (setting private attributes directly). The file-level docstring says `"Provides mock client and task fixtures for testing GID validation"` — scoped to exactly one file's concern.
- **Suggested fix**: Move `client_fixture` and `task_fixture` directly into `test_gid_validation_edge_cases.py` as local fixtures (or migrate to `MockClientBuilder`). Delete `tests/integration/conftest.py`. A conftest serving exactly one test file with a superseded construction pattern is orphaned infrastructure.

---

### Finding P3-016: Ephemeral comment — `Per TDD-CONV-AUDIT-001` ticket reference in inline test docstring
- **Severity**: SMELL
- **File**: `tests/integration/automation/polling/test_trigger_evaluator_integration.py:467`
- **Category**: ephemeral-comment
- **Evidence**: Line 467 reads: `"Per TDD-CONV-AUDIT-001: Empty conditions are only allowed for schedule-driven workflow rules. Condition-based rules must have at least one condition."` This is a `Per TDD-*:` attribution embedded inline in a test docstring. The referenced document `TDD-CONV-AUDIT-001` exists as `docs/design/TDD-conversation-audit-workflow.md`. The attribution is an initiative tag that belongs in commit history; the behavioral description that follows it is the actual documentation value.
- **Suggested fix**: Remove the `Per TDD-CONV-AUDIT-001:` prefix from the inline docstring. Preserve the behavioral description. If linking to the TDD is desired, add it to the module-level docstring, not an inline test comment.

---

### Finding P3-017: Ephemeral comment — `(Phase 3: TDD-UNIFIED-CACHE-001)` phase label in a Phase 4+ module
- **Severity**: SMELL
- **File**: `tests/integration/test_unified_cache_integration.py:1`
- **Category**: ephemeral-comment
- **Evidence**: The module docstring opens: `"Integration tests for unified cache wiring (Phase 3: TDD-UNIFIED-CACHE-001)."` The file was last substantively modified 2026-02-23 and contains Phase 4 content (skip markers reference "Phase 4" as a completed milestone). The `(Phase 3: ...)` qualifier in the title is a time-capsule label written when the file was first created during Phase 3 work and never updated. The `unified-cache-phase-4-complete` tag (2026-01-02) confirms Phase 4 is complete. The phase number in the title is a stale initiative tag.
- **Suggested fix**: Update the module docstring to remove the phase qualifier: `"Integration tests for unified cache wiring (TDD-UNIFIED-CACHE-001)."` This is low-priority and naturally handled if the larger refactor suggested in P3-007 and P3-008 proceeds.

---

## Staleness Classification Summary

| Finding | Tier | Key Evidence |
|---|---|---|
| P3-001 | Provably stale | Zero callers in all test files; inline MockTask used instead |
| P3-002 | Provably stale | Zero callers in all test files |
| P3-003 | Probably stale | Zero callers; conftest last modified 2025-12-22 (63 days) |
| P3-004 | Provably stale | `AsanaClient.save_session()` implemented; "once implemented" condition met |
| P3-005 | Provably stale | AsanaClient fully implemented; "uncomment when available" is factually false |
| P3-006 | Provably stale | Skip says class removed; test body remains permanently dead |
| P3-007 | Provably stale | `unified-cache-phase-4-complete` tag 2026-01-02; ProgressiveProjectBuilder exists in source |
| P3-008 | Provably stale | Skip reason is factually wrong; `cascade_plugin` is still optional in source; tests would pass |
| P3-009 | Probably stale | Diagnostic spike; hardcoded production GID; completion stated in file |
| P3-010 | Provably stale | `unified-cache-phase-4-complete` 2026-01-02; no document for referenced plan |
| P3-011 | Provably stale | IMP-23 commit landed 2026-02-16; implementation complete |
| P3-012 | Probably stale | Story 3.2 and IMP-20 references; no active tracker in repo |
| P3-013 | Provably stale | Zero callers; shims for live API tests that live only in string literal |
| P3-014 | Provably stale | Double-skipped, empty body, phase 4 complete |
| P3-015 | Probably stale | Single-consumer conftest; pattern superseded by MockClientBuilder |
| P3-016 | Probably stale | TDD attribution in inline comment; TDD document exists separately |
| P3-017 | Provably stale | Phase 3 label in Phase 4+ file; tag confirms phase complete |

---

## Negative Findings (Deliberately Not Flagged)

- **aiohttp references**: None found. WS-HTTPX migration is complete in the target directories.
- **Environmental skip markers** (`ASANA_PAT not set`, `LocalStack not running`): These are active conditional skips, not temporal debt. Not flagged.
- **ADR references** (ADR-0053, ADR-0117, ADR-0037, ADR-0040): All verified to exist in `docs/.archive/2025-12-adrs/` and/or `docs/decisions/`. Archived ADRs are valid permanent references. Not flagged.
- **FR-*/NFR-*/SC-* references in docstrings**: These describe test-to-requirement traceability and are the project's accepted documentation pattern. Not flagged.
- **`pytest.skip()` inside fixture bodies** (e.g., `if not token: pytest.skip(...)`): These are active conditional skips for missing credentials. Not flagged.
- **`tests/_shared/mocks.py` MockTask**: `MockTask` is actively used in 11+ test files. No dead code found.

---

## Methodology Notes

- **Caller analysis**: All dead-helper and dead-shim findings verified via exhaustive grep across `tests/` for fixture names, function names, and class names before flagging.
- **Source verification**: All claims about source code (e.g., `cascade_plugin` still optional, `save_session()` implemented, `_parent_cache` still exists) verified by reading the relevant source files under `src/`.
- **Git evidence**: `git log --follow`, `git tag --list`, and commit dates used for all provably-stale classifications.
- **Conservative threshold**: When in doubt, findings were not raised. P3-015 and P3-016 are the most borderline; both are flagged at SMELL with "probably stale" tier to allow human judgment.
