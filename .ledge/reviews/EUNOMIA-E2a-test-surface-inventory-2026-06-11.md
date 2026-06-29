---
type: review
status: accepted
evidence_grade: MODERATE
evidence_note: >
  Eunomia inventorying surfaces eunomia-adjacent processions produced. Self-referential
  position (test-cartographer inventorying tests written during the same saga whose
  governance this rite administers) caps at MODERATE per self-ref-evidence-grade-rule.
  No rite-disjoint external corroboration has occurred yet. All counts are derived from
  the origin/main (49099b12) checkout via a read-only detached worktree /tmp/e2a-inv
  (now removed).
station: E2a
rite: eunomia
procession: Pre-Clear External Corroboration & Governance Custody
scan_sha: 49099b120e6292e44fb24ce79d5ae35007e10792
scan_surface: /tmp/e2a-inv (detached worktree, now removed)
authored: 2026-06-11
---

# EUNOMIA-E2a Test Surface Inventory — 2026-06-11

Scope: cure-recovery saga test accumulation (PR #103–#130 era), whole-surface
denominators. Read-only against origin/main (49099b12).

---

## 1. Test File Census

### Whole-Surface Counts

| Metric | Value |
|--------|-------|
| Total Python files under tests/ | 616 |
| Test files (test_*.py pattern) | 543 |
| Conftest files | 16 |
| Shared-infra files (_shared/) | 2 |
| Benchmark/bench helpers | 4 |
| Total test functions (def test_) | 13,084 |
| Test LOC (test_*.py only) | 270,747 |
| Source LOC (src/) | 148,440 |
| **Test-to-source LOC ratio** | **1.82:1** |
| Source files | 497 |
| Source-to-test file ratio | 543/497 = 1.09:1 |

### Directory Breakdown

| Directory | test_*.py Files | Notes |
|-----------|----------------|-------|
| tests/unit/ | 495 | Primary corpus |
| tests/integration/ | 35 | Live-ish integration suite |
| tests/arch/ | 2 | StorageNamespaceContract SNC t1-t5 + gen diff guard |
| tests/validation/ | 5 | Persistence validation suite |
| tests/contracts/ | 1 | Contract auth test |
| tests/benchmarks/ | 1 | test_insights_benchmark.py |
| tests/synthetic/ | 1 | Synthetic conftest + 1 file |
| tests/ (root) | 3 | test_computation_spans.py, test_openapi_endpoint.py, test_openapi_fuzz.py |

### Unit Subdirectory Breakdown

| Subdirectory | Files | Notes |
|-------------|-------|-------|
| unit/api/ | 80 | Largest subdomain |
| unit/dataframes/ | 60 | Saga focal area (includes builders/) |
| unit/cache/ | 58 | Cache layer tests |
| unit/automation/ | 43 | Automation workflow tests |
| unit/models/ | 40 | Model tests |
| unit/clients/ | 36 | Client tests |
| unit/services/ | 26 | Service layer |
| unit/persistence/ | 28 | Persistence tests |
| unit/query/ | 22 | Query layer |
| unit/lambda_handlers/ | 19 | Lambda handler tests |
| unit/metrics/ | 15 | Metrics tests |
| unit/lifecycle/ | 15 | Lifecycle tests |
| unit/resolution/ | 7 | Resolution tests |
| unit/transport/ | 7 | Transport tests |
| unit/reconciliation/ | 5 | Reconciliation tests |
| unit/auth/ | 6 | Auth tests |
| unit/core/ | 12 | Core tests |
| unit/canary/ | 1 | Deploy gate canary test |
| unit/detection/ | 1 | Detection cache test |
| unit/patterns/ | 2 | Pattern tests |
| unit/search/ | 3 | Search tests |

---

## 2. Fixture Topology

### Conftest Hierarchy

| Conftest | Level | Fixture Count | Named Fixtures |
|----------|-------|--------------|----------------|
| tests/conftest.py | Root | 6 | mock_http, config, auth_provider, logger, _bootstrap_session (autouse/session), reset_all_singletons (autouse) |
| tests/unit/api/conftest.py | Subdirectory | 13 | Various API-specific fixtures |
| tests/unit/automation/polling/conftest.py | Subdirectory | 27 | Automation polling fixtures (largest local conftest) |
| tests/integration/automation/polling/conftest.py | Subdirectory | 12 | Integration polling fixtures |
| tests/unit/lifecycle/conftest.py | Subdirectory | 7 | Lifecycle fixtures |
| tests/unit/reconciliation/conftest.py | Subdirectory | 5 | Reconciliation fixtures |
| tests/unit/resolution/conftest.py | Subdirectory | 6 | Resolution fixtures |
| tests/validation/persistence/conftest.py | Subdirectory | 3 | Validation persistence fixtures |
| tests/unit/cache/conftest.py | Subdirectory | 2 | Cache fixtures |
| tests/unit/clients/conftest.py | Subdirectory | 2 | Client fixtures |
| tests/unit/clients/data/conftest.py | Subdirectory | 2 | Client data fixtures |
| tests/unit/persistence/conftest.py | Subdirectory | 1 | Persistence fixture |
| tests/unit/automation/workflows/conftest.py | Subdirectory | 3 | Workflow fixtures |
| tests/unit/automation/conftest.py | Subdirectory | 0 | Empty (placeholder) |
| tests/unit/dataframes/conftest.py | Subdirectory | 0 | No @pytest.fixture — contains make_mock_task() factory and _TestBuilder class helper only |
| tests/synthetic/conftest.py | Subdirectory | 3 | Synthetic test fixtures |

**Root conftest noteworthy properties:**
- `_bootstrap_session` (autouse/session scope): populates ProjectTypeRegistry once + rebuilds all Pydantic models for NameGid forward references. Session-scoped, autouse — every test benefits.
- `reset_all_singletons` (autouse/function scope): SystemContext.reset_all() before + after each test. Critical isolation guard.
- Root conftest contains a schemathesis/xdist compatibility patch (R4-FIX-002) in `pytest_configure` — addresses the xdist WorkerController workeroutput AttributeError.

**No conftest exists** under tests/unit/dataframes/builders/ or tests/unit/canary/ or tests/arch/. The saga-era focal files carry no directory-level conftest below the dataframes/ level.

### Factory / Builder Patterns

| Location | Pattern | Description |
|----------|---------|-------------|
| tests/_shared/factories.py | make_task_dict() | Minimal Asana task dict builder for cache/pacing tests |
| tests/_shared/mocks.py | MockTask class | Canonical MockTask superset (per HYG-003); comment states bespoke redefinition forbidden |
| tests/unit/dataframes/conftest.py | make_mock_task() function | Local factory producing a MagicMock with 13 fields set; NOT a pytest fixture |
| tests/unit/automation/polling/conftest.py | 27 fixtures | Dense fixture set for automation polling |

---

## 3. Mock Inventory and Proliferation Index

### Shared Infrastructure Available

| Location | Type | Scope |
|----------|------|-------|
| tests/_shared/mocks.py::MockTask | Canonical class | Cross-suite; docstring explicitly forbids bespoke redefinition |
| tests/_shared/factories.py::make_task_dict | Factory function | Cross-suite |
| tests/conftest.py::mock_http | Fixture (MagicMock(spec=AsanaHttpClient)) | Root — all tests |
| tests/conftest.py::auth_provider | Fixture (MagicMock(spec=AuthProvider)) | Root — all tests |
| tests/conftest.py::logger | Fixture (MockLogger from autom8y_log.testing) | Root — all tests |

### MockTask Proliferation

| Metric | Value |
|--------|-------|
| Canonical MockTask definitions | 1 (tests/_shared/mocks.py) |
| Bespoke MockTask class redefinitions | 0 (grep confirmed: no `^class MockTask` outside _shared) |
| MockTask() usages across test files | 205 (calls/references, not redefs) |
| Files importing from tests._shared | 18 |
| MockTask proliferation index | **1:1** (no bespoke redefinitions — HYG-003 discipline holds) |

### Local Stub Classes (Private Convention)

The saga-era files use a `class _ClassName` (underscore-prefix private) convention for bespoke stubs rather than generic MagicMock proliferation. These are intentional transport-boundary stubs, not mock proliferation:

| Class | File(s) | Purpose |
|-------|---------|---------|
| _InMemoryStorage | test_cure_recovery_fail_closed.py, test_warmer_preserve_enforcement.py, test_warmer_preserve_serve_altitude.py | In-memory DataFrameStorage backend; 3 definitions |
| _DegradedBuildStrategy | test_warmer_preserve_enforcement.py, test_warmer_preserve_serve_altitude.py | Strategy stub returning the builder's degraded output frame + write decision carry |
| _RevokedGrantS3Client | test_cure_recovery_fail_closed.py | boto3 transport boundary stub raising AccessDenied |
| _HealthyGrantS3Client | test_cure_recovery_fail_closed.py | boto3 transport boundary stub returning real raw-dict bytes |
| _ColdHotStore | test_cure_recovery_fail_closed.py | UnifiedTaskStore stub with cold hot-tier |
| _Body, _ClientError | test_cure_recovery_fail_closed.py | boto3 response shape stubs |

**Total whole-surface local stub classes (class _* or class Mock*):** 109
**Total inline MagicMock() invocations:** 2,627 across 339 test files

### Shared Infrastructure Utilization Rate

| Metric | Count | Rate |
|--------|-------|------|
| Test files using root conftest fixtures (mock_http, auth_provider, logger) | 76 | 14% of 543 |
| Test files importing from tests._shared | 18 | 3.3% of 543 |
| Test files using autom8y_log MockLogger (any import) | 51 | 9.4% of 543 |

The low rate (14%) is NOT evidence of entropy in this codebase. Many test files (particularly the saga-era integration tests) need no mock_http or auth_provider because they stub at the transport boundary with private stub classes that implement real persistence contracts. The root conftest `reset_all_singletons` autouse fixture applies to 100% of tests silently.

---

## 4. Saga-Era Focal Files: Detailed Inventory

### a. test_cure_recovery_fail_closed.py (#127 builder-path)

- **Path**: tests/unit/dataframes/builders/
- **LOC**: 717
- **Test count**: 9
- **Local fixtures**: 1 (`_reset_s3_client` using monkeypatch — resets module-cached boto3 client)
- **Root conftest fixtures used**: monkeypatch (pytest built-in)
- **Mock/patch sites**: 21 (primarily monkeypatch.setattr; no MagicMock proliferation)
- **Local stub classes**: _Body, _ClientError, _RevokedGrantS3Client, _HealthyGrantS3Client, _ColdHotStore, _InMemoryStorage (6 classes)
- **Skip/xfail markers**: 0
- **Log assertions as primary proof**: 0 (all assertions on frame content: mrr_nonnull count, decision enum, keys_seen)
- **Shared _shared import**: No
- **Fork structure**: BASELINE (documents pre-fix behavior, stays GREEN after fix), RED-1/GREEN-1 (Fork-1), RED-2/GREEN-2 (Fork-2), COALESCE path, OFFER-INTACT (NFR-3), G-DENOM (NFR-4)

### b. test_warmer_preserve_enforcement.py (#128 W3 disk-write path)

- **Path**: tests/integration/cache/
- **LOC**: 421
- **Test count**: 6
- **Local fixtures**: 0
- **Root conftest fixtures used**: monkeypatch (pytest built-in)
- **Mock/patch sites**: 12 (primarily monkeypatch.setattr on warmer._get_strategy_instance)
- **Local stub classes**: _InMemoryStorage, _DegradedBuildStrategy (2 classes)
- **Skip/xfail markers**: 0
- **Log assertions as primary proof**: 0 (docstring explicitly states "Assert by FRAME CONTENT, never the log"; all assertions on storage.load_dataframe result)
- **Shared _shared import**: No

### c. test_warmer_preserve_serve_altitude.py (#128 D2b/D2c hot-tier path)

- **Path**: tests/integration/cache/
- **LOC**: 471
- **Test count**: 7
- **Local fixtures**: 0
- **Root conftest fixtures used**: monkeypatch (pytest built-in) for warmer tests; 2 tests need no monkeypatch (direct cache manipulation)
- **Mock/patch sites**: 8 (monkeypatch.setattr on warmer; otherwise real cache objects)
- **Local stub classes**: _InMemoryStorage, _DegradedBuildStrategy (2 classes)
- **Skip/xfail markers**: 0
- **Log assertions as primary proof**: 0 (docstring: "content is the only honest oracle"; all assertions on cache.get_async return frame content)
- **Shared _shared import**: No

### d. test_concurrency_invariants_guard.py (FROZEN-4 guard)

- **Path**: tests/unit/dataframes/
- **LOC**: 318
- **Test count**: 7
- **Local fixtures**: 0
- **Root conftest fixtures used**: 0 (pure structural assertion tests; no fixtures needed)
- **Mock/patch sites**: 1 (unittest.mock.patch.dict used for clean env in settings tests)
- **Local stub classes**: 0 (AST-parse and inspect-based guard tests, no stubs)
- **Skip/xfail markers**: 0
- **Log assertions as primary proof**: 0
- **Shared _shared import**: No
- **Notable**: Contains an explicit _SANCTIONED_IO_TO_THREAD allowlist (6 entries) with file:line rationales. Any new asyncio.to_thread site outside the allowlist fails the test.

### e. test_deploy_gate_content_binding.py (canary)

- **Path**: tests/unit/canary/
- **LOC**: 295
- **Test count**: 17
- **Local fixtures**: 0
- **Root conftest fixtures used**: 0 (module-level canary import via importlib; pure function tests)
- **Mock/patch sites**: 0
- **Local stub classes**: 0
- **Skip/xfail markers**: 0
- **Log assertions as primary proof**: 0 (tests classify canary function outputs: cls, reason, gate pass/fail)
- **Shared _shared import**: No

### f. tests/arch/test_namespace_contract.py (SNC t1-t5)

- **Path**: tests/arch/
- **LOC**: 436
- **Test count**: 16
- **Local fixtures**: 0
- **Root conftest fixtures used**: 0 (structural/registry tests, no fixtures)
- **Mock/patch sites**: 0
- **Local stub classes**: 0 (uses dataclasses.replace on registry copies for RED-fixture proofs)
- **Skip/xfail markers**: 0
- **Log assertions as primary proof**: 0
- **Shared _shared import**: No
- **RED-fixture pattern**: Each test has a paired RED-fixture sub-test proving the assertion fires (G-THEATER mandate)

### g. tests/arch/test_namespace_gen.py (SNC gen diff-test)

- **Path**: tests/arch/
- **LOC**: 100
- **Test count**: 4
- **Local fixtures**: 0
- **Root conftest fixtures used**: 0
- **Mock/patch sites**: 0
- **Local stub classes**: 0
- **Skip/xfail markers**: 0
- **Log assertions as primary proof**: 0
- **Notable**: Idempotence guard for namespaces.gen.json regeneration; FP-2a byte-equality assertion against live TF literals.

### Saga Focal Files Summary Table

| File | LOC | Tests | Fixtures | Mock-sites | Skip/xfail | Log-primary | Shared Import |
|------|-----|-------|----------|-----------|-----------|------------|--------------|
| test_cure_recovery_fail_closed.py | 717 | 9 | 1 local | 21 | 0 | 0 | No |
| test_warmer_preserve_enforcement.py | 421 | 6 | 0 | 12 | 0 | 0 | No |
| test_warmer_preserve_serve_altitude.py | 471 | 7 | 0 | 8 | 0 | 0 | No |
| test_concurrency_invariants_guard.py | 318 | 7 | 0 | 1 | 0 | 0 | No |
| test_deploy_gate_content_binding.py | 295 | 17 | 0 | 0 | 0 | 0 | No |
| test_namespace_contract.py | 436 | 16 | 0 | 0 | 0 | 0 | No |
| test_namespace_gen.py | 100 | 4 | 0 | 0 | 0 | 0 | No |
| **TOTAL** | **2,758** | **66** | **1** | **42** | **0** | **0** | **0/7** |

---

## 5. Duplication Topology: Altitude-Layering vs Copy-Paste

### _InMemoryStorage Across Three Files

Three files define `class _InMemoryStorage`. On inspection this is honest altitude-layering, not copy-paste accumulation:

| File | Lines | API Contract | Distinction |
|------|-------|--------------|-------------|
| test_cure_recovery_fail_closed.py | ~60 class body | Full v2 entity-keyed save/load | No save_dataframe_calls tracking |
| test_warmer_preserve_enforcement.py | ~75 lines | Full v2 entity-keyed save/load | Adds `save_dataframe_calls: list[dict]` call-log for W3 verification |
| test_warmer_preserve_serve_altitude.py | ~60 lines | Full v2 entity-keyed save/load | No call-log (serve altitude asserts via get_async, not save calls) |

All three implement the identical 7-method async API (`save_dataframe`, `load_dataframe`, `load_dataframe_with_metadata`, `save_index`, `load_index`, `save_json`, `load_json`). The enforcement file adds `save_dataframe_calls` tracking because its assertions need to verify the write was called at all; the serve-altitude file does not because its oracle is `cache.get_async()` return value. The builder file includes additional class body interleaved with other helpers explaining its larger line count.

**Verdict: These are NOT copy-paste duplicates.** The API contract is identical across all three; each variant is the minimum necessary for its test altitude. Consolidation into a shared fixture would require a conftest at integration/cache/ or a higher-level shared helper — currently absent, but the variants are small enough (60–75 lines each) that duplication cost is low.

**The concrete duplicated block across all three**: the `_prior_good_frame(n_active)`, `_degraded_frame(n_active)`, and `_frame(rows)` helper functions appear in both integration files with identical bodies at n_active=3, and in the builder file with n_active=5. The function bodies are identical except for the default parameter. This is genuine copy-paste (5 total copies across 3 files). It could be extracted to a shared conftest or helper module.

### _DegradedBuildStrategy Across Two Integration Files

Both `test_warmer_preserve_enforcement.py` and `test_warmer_preserve_serve_altitude.py` define `_DegradedBuildStrategy`. The class body is structurally identical (same `__init__`, same `_build_dataframe` method, same `_last_write_context` dict shape). The difference is context only: comments and docstrings differ to describe each test's altitude-specific role.

**Verdict: This is copy-paste within the same logical test domain.** The two integration files cover W3 (disk write) and the serve-altitude gap respectively — genuinely distinct concerns that warranted separate files per the PR description. But the `_DegradedBuildStrategy` class and the frame helpers could be shared via a conftest at tests/integration/cache/ without loss of clarity.

### Overlapping PRESERVE/decide_write Assertions at Two Altitudes (#127 vs #128)

The #127 builder tests (test_cure_recovery_fail_closed.py) and #128 warmer tests (test_warmer_preserve_enforcement.py) both assert that a PRESERVE_PRIOR_GOOD decision results in the prior-good frame being stored, not the degraded frame. This is INTENTIONAL altitude-layering, not coverage duplication:

- #127 asserts at the builder's `_finalize_artifacts_write_async` seam (Writer A — the builder's own persistence call).
- #128 asserts at the warmer's `put_async` → `ProgressiveTier.put_async` → `write_final_artifacts_async` seam (Writer B — the operative write site that #127 did not cover).
- test_warmer_preserve_serve_altitude.py asserts at `cache.get_async()` (the serve path — memory tier contamination that disk-only assertions missed).

The game-day incident documented in the test docstrings explicitly explains why three altitudes are needed: PRESERVE was correctly computed (level 1 passed), correctly logged (level 2 passed), but NOT enforced at the operative write site (level 2 gap). A single test at one altitude would have failed to catch the game-day bug. This is textbook correct altitude-layering.

**Verdict: Zero copy-paste accumulation across altitude layers.** The only copy-paste is the frame-builder helper functions (_frame, _prior_good_frame, _degraded_frame) which are boilerplate, and the _DegradedBuildStrategy class between the two integration files.

---

## 6. Coverage Configuration and CI Enforcement

| Dimension | State |
|-----------|-------|
| Coverage config present (pyproject.toml) | YES — [tool.coverage.run] branch=True, source=src/autom8_asana |
| fail_under configured | YES — 80% in [tool.coverage.report] |
| CI enforces coverage threshold on PR | YES — coverage_threshold_aggregate: 80 in test.yml (aggregate across shards) |
| Per-shard coverage threshold | DISABLED (coverage_threshold: 0) — intentional; per-shard is meaningless for sharded xdist runs |
| Post-merge coverage job | YES — .github/workflows/post-merge-coverage.yml runs `--cov-fail-under=80` single-process |
| Coverage theater detection | NOT APPLICABLE — the aggregate CI gate is real and enforced at both PR (aggregate) and post-merge altitudes |

**Coverage is NOT theater.** The upload-artifact v4.4 bug (dotfile exclusion breaking the aggregate gate) was repaired per memory `upload-artifact-hidden-files-coverage-gate.md` → autom8y-workflows#24 → repinned in #112. The current test.yml uses the fixed workflow.

---

## 7. Agent-Provenance and Adversarial File Accumulation Signals

### Epoch/Saga-Tagged Naming

| Pattern | Count | Files |
|---------|-------|-------|
| *_sprint2* in filename | 1 | tests/unit/api/test_routes_query_project_section_rows_sprint2.py |
| *adversarial* in filename | 17 | Distributed across api, cache, dataframes, metrics, persistence, query, reconciliation |
| *_qa* or *qa_* in filename | 2 | test_cpu_offload_adversarial_qa.py, test_honest_observability_adversarial_qa.py, test_cache_warmer_adversarial_qa.py |
| qa/ subdirectory | 0 | No qa/ subdirectory exists |

**Sprint2 file assessment**: `test_routes_query_project_section_rows_sprint2.py` is a 309-line, 7-test active file covering AC-R1 acceptance criteria for the Sprint 2 receiver surface. It carries an `xdist_group("query_routes")` marker. The docstring notes deliberate shortcuts ("prototype") — the file self-describes as prototype-grade, not gold-standard integration. This is a mild provenance signal but the tests are live and ungated. The "sprint2" suffix in the filename should be renamed to reflect the feature being tested rather than the sprint it was written in.

**Adversarial files assessment**: The adversarial naming convention appears well-established across multiple subdomains (cache, persistence, query, reconciliation, dataframes/builders). This is a project-level naming discipline for edge-case / hostile-input tests — it is not agent-accumulation noise. The 17 adversarial files span 7+ distinct subdomain directories and were written across multiple sprints.

### Skip Markers with Staleness Risk

| File | Skip Count | Reason Category | Staleness Risk |
|------|-----------|----------------|----------------|
| tests/integration/test_workspace_switching.py | 8 / 8 tests | "Needs behavioral test: ..." (aspirational placeholders) | HIGH — 100% of tests in the file are skipped; entire file is a skeleton |
| tests/test_computation_spans.py | 1 | "DataServiceClient.get_insights_batch_async not yet instrumented" | MEDIUM — implementation-gap skip |
| tests/unit/cache/dataframe/test_coalescer_dedup_metric.py | 1 | CI-vs-local moto-singleton flake, load-bearing emit covered elsewhere | LOW — documented rationale with review artifact citation |
| tests/integration/test_platform_performance.py | 1 | RS-021: resolve_batch cache miss — needs investigation | MEDIUM — open scar reference |
| tests/unit/metrics/* | 7 | skipif(not MOTO_AVAILABLE) / skipif(not JSONSCHEMA_AVAILABLE) | CORRECT — dependency guards, not stale |
| tests/unit/cache/test_redis_backend.py | 1 | skipif(not FAKEREDIS_AVAILABLE) | CORRECT — dependency guard |
| tests/unit/cache/test_s3_backend.py | 1 | skipif(not MOTO_AVAILABLE) | CORRECT — dependency guard |
| tests/unit/persistence/test_reorder.py | 1 | skipif(not _HAS_HYPOTHESIS) | CORRECT — dependency guard |

**test_workspace_switching.py is the primary skip-accumulation signal**: 148 LOC, 8 tests, all 8 skipped with "Needs behavioral test" reasons. This file contains no passing tests and amounts to a dead-test accumulation artifact.

### TestPq5GuardFires Status

The prior station noted two TestPq5GuardFires xdist_group failures. Current state:

- `tests/unit/api/test_routes_query_section_missing_selector_guard.py` defines `TestPq5GuardFires` with 4 test methods.
- The class carries the module-level `pytestmark = [pytest.mark.xdist_group("query_routes")]` marker — it runs in the same xdist group as sibling query_routes test files.
- **No xfail, no skip markers** on the TestPq5GuardFires class or any of its 4 methods.
- The module is 169 LOC, structurally complete (conftest provides `client` fixture via the api conftest).
- **Current marker hygiene: CLEAN.** The tests are live, ungated, and in the standard xdist_group. If the prior station observed failures, they may have been timing or infrastructure artifacts rather than persistent test failures on origin/main.

---

## 8. Log-String Assertion Analysis

**Saga's lesson**: The game-day proved the `fail_closed_write_preserve_prior_good` log FIRED while the write degraded — log assertions are insufficient oracle.

| Scope | Count | Assessment |
|-------|-------|-----------|
| Saga focal files (7 files) asserting logs as PRIMARY proof | 0 | CLEAN — all saga files assert frame content (mrr_nonnull) or enum values, never log strings |
| Whole-surface files using MockLogger / assert_logged / .entries | 115 | Present but distributed across non-saga files |
| test_cascade_validator.py log assertions (within builders/) | Multiple | Asserts mock_logger.info/warning/error.assert_called_once(); this is a behavioral contract on logging structure, not a content-only oracle — lower risk than saga's anti-pattern |

**Notable exception in builders/ neighborhood**: `tests/unit/dataframes/builders/test_cascade_validator.py` uses `mock_logger.{level}.assert_called_once()` extensively. These tests assert that the cascade validator emits structured log calls at specific severity levels — this is testing the logger is invoked at the right level, not testing the message string content. This is borderline: it is an improvement over string matching but still log-call-as-primary-oracle when the behavioral outcome (cascade validation result) would be a stronger oracle.

---

## 9. Whole-Surface Shared Infrastructure Utilization

| Metric | Count | Denominator | Rate |
|--------|-------|-------------|------|
| Files importing from tests._shared | 18 | 543 | 3.3% |
| Files using root conftest fixtures explicitly | 76 | 543 | 14.0% |
| Files using autom8y_log.testing.MockLogger | 51 | 543 | 9.4% |
| Files with 0 fixtures from any conftest | ~370 | 543 | ~68% |

The 68% "fixture-less" rate is not entropy — most of these files use the `reset_all_singletons` autouse fixture invisibly, and many saga-era files use monkeypatch (pytest built-in) rather than custom fixtures because their stubs are transport-boundary classes, not generic mocks. The autouse session fixtures from root conftest apply to all 13,084 tests regardless of explicit invocation.

---

## 10. Raw Metrics Table

| Metric | Value | Notes |
|--------|-------|-------|
| Total test files (test_*.py) | 543 | origin/main 49099b12 |
| Total test functions (def test_) | 13,084 | grep count |
| Total test LOC | 270,747 | test_*.py only |
| Source LOC | 148,440 | src/ |
| Test-to-source LOC ratio | 1.82:1 | Above 1.5:1 investigation threshold |
| Conftest files | 16 | Full hierarchy |
| Total fixtures across all conftests | ~97 | Summed per-conftest counts |
| MockTask proliferation index | 1:1 | 1 canonical def, 0 bespoke redefs |
| Local stub classes (class _* or class Mock*) | 109 | Whole surface |
| Inline MagicMock() invocations | 2,627 | Whole surface |
| Test files using shared infra (_shared imports) | 18 | 3.3% |
| Saga focal files using shared infra | 0/7 | None of the 7 focal files import from _shared |
| _InMemoryStorage definitions | 3 | Across 3 saga files |
| _DegradedBuildStrategy definitions | 2 | Across 2 integration saga files |
| Frame helper function copies (_frame, _prior_good_frame, _degraded_frame) | 3 sets | Copy-paste across builder + 2 integration files |
| xfail markers (whole surface) | 0 | No xfail markers found |
| skip markers (whole surface) | 25 | 8 in test_workspace_switching.py (dead-file signal); 9 dependency guards (correct); 3 documented flake/scar skips; 5 "needs behavioral test" |
| Dead-test files (100% skipped) | 1 | test_workspace_switching.py |
| Sprint/epoch-tagged filenames | 1 | test_routes_query_project_section_rows_sprint2.py |
| Log-assertion as primary oracle in saga focal files | 0 | Clean |
| Log-assertion files (whole surface) | 115 | Distributed, non-saga |
| Coverage gate enforced in CI | YES | Aggregate 80% in test.yml + post-merge job |
| Adversarial files (naming signal) | 17 | Project-level naming discipline, not agent accumulation |
| qa/ subdirectory | 0 | Not present |
| TestPq5GuardFires skip/xfail markers | 0 | Tests are live and ungated |

---

## 11. Findings Ranked by Severity

### F-1 (MEDIUM): test_workspace_switching.py — 100% Dead-Test File

- **Location**: tests/integration/test_workspace_switching.py
- **Finding**: 148 LOC, 8 test functions, all 8 skipped with "Needs behavioral test: ..." reasons. The file has never had a passing test — it is a skeleton accumulated during a sprint and never completed.
- **Signal type**: Skip-accumulation / aspirational placeholder
- **Impact**: Zero coverage contribution; misleads census counts; a reader would expect 8 integration tests for workspace switching behavior.
- **Severity**: Medium (not a false-positive like a flapping test — it is cleanly skipped; but it inflates test counts and adds maintenance drag).

### F-2 (MEDIUM): test_routes_query_project_section_rows_sprint2.py — Sprint-Tagged Prototype File

- **Location**: tests/unit/api/test_routes_query_project_section_rows_sprint2.py
- **Finding**: Active file (7 live tests, no skip markers) but self-described as "prototype" with "deliberate shortcuts." The sprint2 suffix is an epoch-tag that should be replaced with a feature-describing name. Sprint-suffixed names create confusion about whether the file supersedes or supplements the non-suffixed sibling test_routes_query_project_section_rows.py.
- **Signal type**: Epoch-tagged naming
- **Severity**: Medium (tests are live; the naming is the defect, not the tests themselves).

### F-3 (LOW): _InMemoryStorage and _DegradedBuildStrategy Duplication Across Integration Files

- **Location**: tests/integration/cache/test_warmer_preserve_enforcement.py and test_warmer_preserve_serve_altitude.py
- **Finding**: _InMemoryStorage defined in both files with the same 7-method API contract; _DegradedBuildStrategy defined in both with structurally identical bodies. Also duplicated with test_cure_recovery_fail_closed.py in unit/dataframes/builders/.
- **What is NOT duplicated**: The test functions themselves cover distinct concerns (disk-write vs serve-altitude vs circuit-LKG), and the strategy stubs differ in comments. The duplication is limited to infrastructure boilerplate.
- **Impact**: Any change to the DataFrameStorage contract requires updates in 3 places; _DegradedBuildStrategy changes require 2. Low friction currently.
- **Severity**: Low (genuine altitude-layering present; duplication is boilerplate-only; no false-positive tests).

### F-4 (LOW): Frame Helper Function Copy-Paste (_frame, _prior_good_frame, _degraded_frame)

- **Location**: Three files (test_cure_recovery_fail_closed.py, test_warmer_preserve_enforcement.py, test_warmer_preserve_serve_altitude.py)
- **Finding**: `_frame()`, `_prior_good_frame()`, and `_degraded_frame()` are copy-pasted across files with only the default `n_active` parameter differing (5 vs 3). These are 5-10 line functions each.
- **Severity**: Low (minor duplication; no behavioral divergence).

### F-5 (INFO): 1.82:1 Test-to-Source LOC Ratio — Above Investigation Threshold but Compound Signals Absent

- **Finding**: 270,747 test LOC vs 148,440 source LOC = 1.82:1, above the SCAR-TC-006 1.5:1 investigation threshold. However, the compound entropy signal requires mock proliferation + adversarial accumulation + high ratio together. MockTask proliferation index is 1:1 (HYG-003 discipline holds), there is no adversarial file accumulation (0 qa/ directories, adversarial naming is project-discipline not noise), and xfail is at 0. The ratio alone does not indicate pathology.
- **Severity**: Informational (threshold triggered; compound signal absent).

### F-6 (INFO): Saga Focal Files Do Not Use Shared _shared Infrastructure

- **Finding**: 0/7 saga focal files import from tests._shared.mocks or tests._shared.factories. All 7 files use local stub classes (_InMemoryStorage, etc.) or no external stubs at all. This is appropriate: the saga tests operate at the DataFrameStorage/DataFrameCache layer, not the Task/MockTask layer where shared mocks apply.
- **Severity**: Informational (expected given the domain; not entropy).

### F-7 (INFO): test_cascade_validator.py Uses Log-Call Assertions as Primary Oracle

- **Location**: tests/unit/dataframes/builders/test_cascade_validator.py
- **Finding**: Extensive use of `mock_logger.{level}.assert_called_once()` as the primary proof of cascade validation behavior. This is the log-as-oracle anti-pattern the saga explicitly corrected in the integration tests. The cascade_validator tests are not saga-era but represent the pre-saga pattern that the saga demonstrated is unreliable.
- **Severity**: Informational (not new; pre-dates the saga; noted for entropy-assessor awareness).

---

*Scan completed at origin/main (49099b12). Worktree /tmp/e2a-inv removed. Read-only throughout.*
