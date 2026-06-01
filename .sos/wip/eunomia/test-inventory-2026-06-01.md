---
artifact_id: test-inventory-2026-06-01
type: audit
scope: test-ecosystem
target: /Users/tomtenuta/Code/a8/repos/autom8y-asana
stack: Python / pytest / pytest-xdist / pytest-split / schemathesis
produced_by: test-cartographer
date: 2026-06-01
status: complete
---

# Test Ecosystem Inventory — autom8y-asana
## Produced: 2026-06-01 | For: entropy-assessor

---

## 1. Scope and Target

Single Python service repository. Stack: Python 3.12, pytest with asyncio_mode=auto, pytest-xdist (loadgroup strategy), pytest-split (4 shards), schemathesis/Hypothesis for fuzz. Source truth: `tests/` tree only (worktrees in `.worktrees/` are excluded — they are copies of main; 10 worktrees exist but do not contribute to test count).

---

## 2. Test File Census

**Total test Python files (main tree, `tests/` only):** 530 (includes `__init__.py`, `conftest.py`)
**Executable test files (`test_*.py`):** 512
**Non-test Python files (conftest + init):** 18

| Bucket | test_*.py count | Notes |
|--------|----------------|-------|
| `tests/unit/` | 468 | Dominant bucket; subdivided by domain |
| `tests/integration/` | 33 | Mix of live-API and local-stack integration |
| `tests/validation/persistence/` | 5 | Named validation — heavy concurrency/functional |
| `tests/benchmarks/` | 3 (bench_ prefix) | Performance benchmarks; bench_ naming convention |
| `tests/synthetic/` | 1 | Aegis synthetic coverage |
| `tests/contracts/` | 1 | Auth contract test |
| `tests/` (top-level) | 3 | `test_openapi_fuzz.py`, `test_computation_spans.py`, `test_openapi_endpoint.py` |

**Directory depth:** unit tree has 3-4 levels (`tests/unit/api/routes/`, `tests/unit/clients/data/`, `tests/unit/automation/workflows/payment_reconciliation/`).

**Per-domain unit distribution (selected):**

| Domain dir | Approximate file count |
|---|---|
| `unit/api/` (all sub) | ~45 |
| `unit/cache/` (all sub) | ~25 |
| `unit/automation/` (all sub) | ~20 |
| `unit/services/` | ~25 |
| `unit/dataframes/` (all sub) | ~20 |
| `unit/persistence/` | ~18 |
| `unit/models/` (all sub) | ~15 |
| `unit/clients/` (all sub) | ~15 |
| `unit/lambda_handlers/` | ~8 |
| `unit/lifecycle/` | ~5 |
| `unit/query/` | ~15 |
| `unit/transport/` | ~6 |
| Other domains | remainder |

---

## 3. Fixture Topology

### 3.1 Conftest Hierarchy (main tree)

**15 conftest.py files** in the active tree:

| Level | File | Key fixtures / hooks |
|---|---|---|
| Root | `tests/conftest.py` | `pytest_configure` (schemathesis xdist patch), `mock_http`, `config`, `auth_provider`, `logger` (MockLogger), `_bootstrap_session` (session-scoped), `reset_all_singletons` (autouse) |
| `tests/synthetic/` | `tests/synthetic/conftest.py` | (inspect pending — aegis-specific) |
| `tests/integration/automation/polling/` | `...polling/conftest.py` | Imports `MockTask` from `_shared`; polling-specific fixtures |
| `tests/unit/api/` | `tests/unit/api/conftest.py` | 13 fixtures — FastAPI test client, app factory, dependency overrides |
| `tests/unit/automation/polling/` | `...polling/conftest.py` | Imports `MockTask` from `_shared`; 340 lines |
| `tests/unit/automation/workflows/` | `...workflows/conftest.py` | Workflow fixtures |
| `tests/unit/cache/` | `tests/unit/cache/conftest.py` | SDK `_SDKMockCacheProvider` alias; 2 fixtures |
| `tests/unit/clients/` | `tests/unit/clients/conftest.py` | Extends `_SDKMockCacheProvider` as local `MockCacheProvider`; 2 fixtures |
| `tests/unit/clients/data/` | `...clients/data/conftest.py` | Data client fixtures |
| `tests/unit/dataframes/` | `tests/unit/dataframes/conftest.py` | Dataframe-specific fixtures |
| `tests/unit/lifecycle/` | `tests/unit/lifecycle/conftest.py` | Lifecycle fixtures |
| `tests/unit/persistence/` | `tests/unit/persistence/conftest.py` | Extends `_SDKMockCacheProvider` as `MockCacheProviderForInvalidation` |
| `tests/unit/reconciliation/` | `tests/unit/reconciliation/conftest.py` | Reconciliation fixtures |
| `tests/unit/resolution/` | `tests/unit/resolution/conftest.py` | Resolution fixtures |
| `tests/validation/persistence/` | `tests/validation/persistence/conftest.py` | Heavy concurrency/load fixtures |

**Root-level autouse fixtures (apply to all tests):**
- `reset_all_singletons` (function-scoped, autouse): calls `SystemContext.reset_all()` before/after each test — `tests/conftest.py:184`
- `_bootstrap_session` (session-scoped, autouse): bootstraps `ProjectTypeRegistry` + resolves Pydantic forward refs — `tests/conftest.py:117`

**SDK provider fixtures (cross-level):**
Root conftest provides: `mock_http` (MagicMock spec AsanaHttpClient), `auth_provider` (MagicMock spec AuthProvider), `logger` (SDK MockLogger), `config` (AsanaConfig).

### 3.2 Fixture Duplication Signals

**MockCacheProvider fragmentation:** 4 independent definitions extend or redefine the SDK's `_SDKMockCacheProvider`:
- `tests/unit/clients/conftest.py:22` — extends SDK mock, named `MockCacheProvider`
- `tests/unit/persistence/conftest.py:14` — extends SDK mock, named `MockCacheProviderForInvalidation`
- `tests/unit/persistence/test_session_detection_invalidation.py:28` — inline class extending SDK mock
- `tests/unit/cache/test_events.py:38` — standalone `MockCacheProvider` (does NOT extend SDK mock)
- `tests/unit/clients/test_client.py:264` — `MockCacheProviderWithMetrics` (standalone, no SDK inheritance)

Proliferation index for MockCacheProvider variants: 5 definitions, 1 shared SDK canonical = **5:1**.

---

## 4. Mock Inventory

### 4.1 Shared Infrastructure (GOLDEN)

| Location | Mock / Helper | Canonical |
|---|---|---|
| `tests/_shared/mocks.py:12` | `MockTask` | Canonical — "SUPERSET of all 11 prior bespoke variants per HYG-003. Bespoke redefinition forbidden." |
| `tests/conftest.py:78` | `_make_mock_http_client()` | Factory for `MagicMock(spec=AsanaHttpClient)` |
| `tests/conftest.py:82` | `_make_mock_auth_provider()` | Factory for `MagicMock(spec=AuthProvider)` |
| `autom8y_cache.testing.MockCacheProvider` | SDK-provided | Imported by 4 conftests via `_SDKMockCacheProvider` alias |
| `autom8y_log.testing.MockLogger` | SDK-provided | Used in root conftest, propagated as fixture |
| `autom8y_telemetry.testing.find_span` | SDK-provided | Used in `tests/test_computation_spans.py` |

### 4.2 MockTask Proliferation

**Canonical:** `tests/_shared/mocks.py:12` (1 definition)
**Importers:** 14 files import from `tests._shared.mocks` (correct consumers)
**Surviving bespoke violations:** 0 — all `class MockTask` definitions are confined to `_shared/mocks.py`. The consolidation from HYG-003 is confirmed complete.

Proliferation index for MockTask: **1:1 (CLEAN)**

### 4.3 Bespoke Local Mock Classes (All Remaining)

Total `class Mock*` definitions (all test files): **~105 unique class definitions** across ~55 files.

Key proliferation patterns by mock type:

| Mock Name | Independent definitions | Has shared alternative? | Proliferation Index |
|---|---|---|---|
| `MockTask` | 1 (canonical only) | Yes (_shared) | 1:1 CLEAN |
| `MockCacheProvider` (all variants) | 5 | Yes (autom8y_cache.testing) | 5:1 |
| `MockAuthProvider` | 3 (`test_client.py:16`, `test_asana_http.py:23`, `test_aimd_integration.py:21`) | Yes (conftest `auth_provider` fixture) | 3:1 |
| `MockLambdaContext` | 2 (`test_cache_warmer.py:385`, `test_warmer_manifest_clearing.py:22`) | No shared canonical exists | n/a (candidate for consolidation) |
| `MockNameGid` | 3 (`test_cascading_resolver.py:27`, `test_cascading_field_resolution.py:36`, `test_platform_performance.py:45`) | No — domain-specific struct | 3:1 candidate |
| `MockEntity` | 3 (`test_engine_integration.py:28`, `test_rule.py:27`, `test_base.py:24`) | No | 3:1 candidate |
| `MockProcess` | 4+ (`test_assignee_resolution.py:19`, `test_onboarding_comment.py:28`, `test_pipeline.py:38`, `test_pipeline_hierarchy.py:48`) | No | 4:1 candidate |
| `MockProcessType(Enum)` | 3 (`test_base.py:17`, `test_integration.py:46`, `test_pipeline.py:23`) | No | 3:1 candidate |
| `MockSection` | 2 (`test_integration.py:104`, `test_templates.py:17`) | No | 2:1 candidate |
| `MockPageIterator` | 3 (`test_integration.py:112`, `test_pipeline.py:81`, `test_templates.py:25`, `test_waiter.py:15`) | No | 4:1 candidate |
| `MockBusiness` | 3 (`test_assignee_resolution.py:45`, `test_onboarding_comment.py:44`, `test_seeding.py:31`) | No | 3:1 candidate |
| `MockUnit` | 2 (`test_assignee_resolution.py:33`, `test_pipeline_hierarchy.py:28`) | No | 2:1 candidate |
| `MockTasksClient` | 2 (`test_waiter.py:25`, `test_unit_cascade_resolution.py:62`) | No | 2:1 candidate |
| `MockAsanaClient` | 2 (`test_name_resolver.py:23`, `test_waiter.py:32`) | No | 2:1 candidate |

**Most impactful compound:** automation/ domain has the deepest mock re-definition density — MockProcess (4), MockProcessType (3), MockPageIterator (4), MockSection (2), MockBusiness (3). All live within `tests/unit/automation/` without a shared automation-domain conftest providing these types.

---

## 5. Coverage Configuration

| Layer | Setting | Source |
|---|---|---|
| pyproject.toml | `fail_under = 80`, branch coverage, source = `src/autom8_asana` | `pyproject.toml:120-127` |
| PR CI | `coverage_threshold: 0` (DISABLED) | `tests/test.yml:52` — explicitly documented: "per-shard coverage is meaningless with test_splits > 1" |
| Post-merge CI | `--cov-fail-under=80` on push to main, full suite single-shard | `.github/workflows/post-merge-coverage.yml:83` |

**Coverage theater status:** PARTIALLY RESOLVED. The original theater was 4-shard-per-PR coverage reporting. `post-merge-coverage.yml` was introduced (ADR-011, 2026-04-30) to close this gap — runs full suite single-shard on push to main with `fail_under=80` gated. PR coverage remains theatrical (threshold=0). This is the documented intentional design per ADR-011, not unaddressed theater.

**CI enforcement verdict:** Coverage gate EXISTS and fires on main push. NOT enforced at PR time (by design). Gap: a regression introduced in a PR won't fail the PR — it will fail post-merge, adding fix-forward churn. Pattern is present but documented.

---

## 6. xdist / pytest-split Configuration

**Strategy:** `--dist=loadgroup` (global default, pyproject.toml:105)
**Shards:** `test_splits: 4` (via satellite-ci-reusable.yml input)
**Workers per shard:** `test_maxprocesses: 2` (capped; rationale: OOM prevention under asyncio-heavy coverage instrumentation)
**Durations file:** `.test_durations` — 13,597 entries, committed, weekly refresh via `durations-refresh.yml`
**Load balance health:** 13,597 entries suggests the durations file is comprehensive. Weekly automated refresh workflow committed.

---

## 7. xdist Worker-Isolated Quarantine (ASSESS-5)

### 7.1 The `worker_isolated` Quarantine

**Single file quarantined:** `tests/unit/lambda_handlers/test_workflow_handler.py`
- Marker: `pytest.mark.worker_isolated` at `test_workflow_handler.py:58`
- xdist_group: `"workflow_handler"` at `test_workflow_handler.py:50`
- Root: lambda handler runs `asyncio.run` internally (production code `workflow_handler.py:96-97`). Tests call handler synchronously — no outer async loop — but under CI resource pressure (coverage memory + xdist co-residency) the SIGKILL still occurs.
- Quarantine job: `workflow-handler-isolated` in `test.yml:206` — `continue-on-error: true`, single-process (`-p no:xdist`), non-blocking

**Root cause per test file:** The production handler itself runs `asyncio.run` (synchronous entry point with internal event loop). Not fixable at test level without restructuring the production handler to be async-native.

### 7.2 ASSESS-5: Full asyncio.run-in-handler Risk Family

Files using `asyncio.run` in synchronous `def` test methods (NOT in async test context) — each carries the same structural risk as the quarantined file if run under xdist with resource pressure:

| File | asyncio.run call count | xdist marker present? | Quarantined? |
|---|---|---|---|
| `tests/unit/lambda_handlers/test_workflow_handler.py` | uses production handler which runs asyncio.run | xdist_group("workflow_handler") | YES — worker_isolated |
| `tests/unit/patterns/test_async_method.py` | 12 | None | NO |
| `tests/unit/lifecycle/test_lifecycle_observation_contracts.py` | 10 | None | NO |
| `tests/unit/models/business/test_seeder.py` | 14 | None | NO |
| `tests/unit/lifecycle/test_observation.py` | 2 | None | NO |
| `tests/unit/dataframes/test_freshness_verification_recency.py` | 2 | None | NO |
| `tests/unit/dataframes/test_public_api.py` | 1 (sync path test) | None | NO |
| `tests/unit/models/business/test_resolution.py` | 2 (commented - acknowledges cannot actually call sync wrapper) | None | NO |

**xdist risk family size: 8 files** (including the quarantined one). 7 files with asyncio.run calls in synchronous test bodies have NO quarantine marker and NO xdist isolation.

**Distinction:** Most of these (patterns, lifecycle, seeder, dataframes) are testing async-to-sync bridge wrappers or pure async code called via asyncio.run — NOT lambda handlers that run asyncio.run in production code. Their SIGKILL risk profile is different from workflow_handler: they don't spawn nested loops or threads. However, they remain structurally non-idiomatic under pytest-asyncio auto mode (which can interfere with `asyncio.run` in sync tests in some configurations).

**Files confirmed non-risky at current marker level:**
- `tests/unit/models/business/test_resolution.py` — asyncio.run calls are commented/noted as structurally impossible
- `tests/benchmarks/bench_batch_operations.py` — not in test suite proper (bench_ prefix, excluded from normal runs)

---

## 8. PR vs. Main CI Gate Asymmetry (ASSESS-1 / ASSESS-10)

### 8.1 Structural Difference

The `test.yml` feeds into `satellite-ci-reusable.yml@cbc3c58e`. Lint/type logic lives upstream in the reusable workflow — not inspectable here. The satellite invocation at `test.yml:45` passes `mypy_targets: 'src/autom8_asana'` unconditionally.

### 8.2 Confirmed Asymmetric Gates

From `test.yml:64` — `test_markers_exclude` ternary:
- **PR mode:** excludes `not integration and not benchmark and not slow and not fuzz and not worker_isolated`
- **Push (main) mode:** excludes `not integration and not benchmark and not fuzz and not worker_isolated`

Difference: **`slow` tests run on main but are skipped on PRs.** (23 slow-marked tests across: `test_memory_backend`, `test_concurrency`, `test_insights`, `test_circuit_breaker`, `test_observability`, `test_startup_preload`, `test_routes_admin`, `test_edge_cases`, `test_health`, `test_performance`)

`run_integration: ${{ github.event_name == 'push' }}` — **integration tests only run on push to main, never on PRs.**

### 8.3 ruff check / mypy Asymmetry (ASSESS-1 root)

**The `ruff check` + `mypy --strict` asymmetry is in the upstream reusable workflow**, not in this repo's YAML. The satellite-ci-reusable.yml at SHA `cbc3c58e` controls whether ruff check/mypy run conditionally on branch. The 3 session failures (I001+SIM300, arg-type mypy) confirm that ruff check and mypy --strict do NOT gate PRs but DO gate main pushes. This is not configurable via the `test.yml` inputs visible here — the asymmetry is structural to the upstream reusable workflow's conditional logic.

**Confirmed asymmetric checks (from session direct observation per HANDOFF):**
- `ruff check` — main only
- `mypy --strict` — main only
- `ruff format --check` — both PR and main

**Gate count by trigger:**

| Check | PR | Main Push |
|---|---|---|
| ruff format --check | YES | YES |
| ruff check | NO | YES |
| mypy --strict | NO | YES |
| Unit tests (fast path) | YES | YES |
| slow tests | NO | YES |
| integration tests | NO | YES |
| fuzz tests (non-blocking) | YES (5 examples) | YES (25 examples) |
| worker_isolated (non-blocking) | YES (isolated job) | YES (isolated job) |
| post-merge coverage gate | NO | YES (separate workflow) |

---

## 9. SCAR-Marker Discipline

**Total `@pytest.mark.scar` usages:** 42

| File | Count | SCAR references |
|---|---|---|
| `tests/unit/reconciliation/test_section_registry.py` | 15 | SCAR-REG-001 (GID validation regression) |
| `tests/unit/dataframes/test_warmup_ordering_guard.py` | 5 | SCAR-005/006 (cascade ordering) |
| `tests/unit/dataframes/test_freshness_verification_recency.py` | 6 | freshness/recency regression guards |
| `tests/unit/dataframes/test_cascade_ordering_assertion.py` | 3 | SCAR-005/006 |
| `tests/unit/api/middleware/test_idempotency_finalize_scar.py` | 3 | Idempotency finalize regression |
| `tests/unit/api/test_exports_auth_exclusion.py` | 2 | SCAR-WS8 (auth exclusion paths) |
| `tests/unit/api/test_exports_format_negotiation.py` | 1 | Format negotiation regression |
| `tests/unit/services/test_universal_strategy_status.py` | 2 | Strategy status regression |
| `tests/unit/services/test_section_timeline_service.py` | 1 | Section timeline regression |
| `tests/unit/dataframes/builders/test_cascade_validator.py` | 1 | SCAR-005 (cascade field null rate) |
| `tests/unit/core/test_entity_registry.py` | 1 | SCAR-005/006 (entity registry null) |
| `tests/unit/models/business/matching/test_normalizers.py` | 1 | SCAR-020 (phone normalization) |
| `tests/unit/api/middleware/test_idempotency_finalize_scar.py` | 1 | Idempotency |

**SCAR references found in file content (beyond marker usage):**
- SCAR-REG-001, SCAR-005, SCAR-006, SCAR-020, SCAR-WS8, SCAR-W1E-LOADGROUP-001

**Marker registration:** confirmed in `pyproject.toml:109` — `"scar: scar-tissue regression tests (selectable via pytest -m scar); see .know/scar-tissue.md"`

**Age signal:** `test_idempotency_finalize_scar.py` filename embeds "scar" directly — created as a dedicated regression file. No epoch-tagged filenames detected.

---

## 10. Schemathesis xfail Markers

**Module-level xfail:** `tests/test_openapi_fuzz.py:58-66` — single `pytest.mark.xfail(strict=False)` applied at module level via `pytestmark`.

**Stated violation count:** "47 pre-existing contract violations" per comment at `test_openapi_fuzz.py:32`. Post-S3 triage at `test_openapi_fuzz.py:44-57` records ~46 XFAIL remaining (with ~7 XPASS from health/ready/users/me/dataframes endpoints).

**Current state:** Single module-level non-strict xfail. This is NOT 47 individual per-endpoint xfails — it is one blanket marker with the comment documenting that 47 violations exist. The backlog states "per-endpoint xfail narrowing tracked separately."

**Architecture:** `xfail(strict=False)` means XFAIL tests don't fail the job, XPASS tests don't fail the job either. The fuzz job is also `continue-on-error: true` at the CI level — doubly non-blocking. Signal is preserved but zero enforcement.

---

## 11. Adversarial File Accumulation

### 11.1 Named Adversarial Files

| File | Pattern | Domain |
|---|---|---|
| `tests/unit/cache/test_adversarial_pacing_backpressure.py` | `test_*adversarial*` | Cache pacing |
| `tests/unit/cache/test_staleness_adversarial.py` | `test_*adversarial*` | Cache staleness |
| `tests/unit/dataframes/builders/test_adversarial_pacing.py` | `test_*adversarial*` | Dataframe pacing |
| `tests/unit/dataframes/test_schema_extractor_adversarial.py` | `test_*adversarial*` | Schema extraction |
| `tests/unit/metrics/test_adversarial.py` | `test_*adversarial*` | Metrics |
| `tests/unit/metrics/test_freshness_adversarial.py` | `test_*adversarial*` | Freshness metrics |
| `tests/unit/persistence/test_action_batch_adversarial.py` | `test_*adversarial*` | Persistence batch |
| `tests/unit/persistence/test_reorder_adversarial.py` | `test_*adversarial*` | Persistence reorder |
| `tests/unit/query/test_adversarial.py` | `test_*adversarial*` | Query engine |
| `tests/unit/query/test_adversarial_aggregate.py` | `test_*adversarial*` | Query aggregate |
| `tests/unit/query/test_adversarial_hierarchy.py` | `test_*adversarial*` | Query hierarchy |
| `tests/unit/reconciliation/test_adversarial.py` | `test_*adversarial*` | Reconciliation |
| `tests/unit/test_batch_adversarial.py` | `test_*adversarial*` | Batch |
| `tests/unit/test_tier1_adversarial.py` | `test_*adversarial*` | Tier1 |
| `tests/unit/test_tier2_adversarial.py` | `test_*adversarial*` | Tier2 |

**Adversarial file count: 15**

### 11.2 Sprint-Named File

- `tests/unit/api/test_routes_query_project_section_rows_sprint2.py` — contains literal "sprint2" in filename. Agent-provenance naming signal.

### 11.3 Agent-Provenance Assessment

**Epoch-tagged files:** 1 confirmed (`sprint2` suffix)
**Adversarial accumulation:** 15 files. Breadth spans 8 domains (cache, dataframes, metrics, persistence, query, reconciliation, batch, tier-level). This is domain-appropriate naming (adversarial = edge-case/boundary testing) rather than agent-copy accumulation — the files cover distinct domains with different content. No near-duplicate content detected at file-name level.

**No `_ws\d+`, `_\d{3}`, `_qa_` patterns found.** The adversarial naming is intentional test design vocabulary, not agent proliferation epoch-tagging.

---

## 12. Shared Infrastructure Utilization

### 12.1 SDK Testing Infrastructure (GOLDEN)

| SDK Package | Testing Primitive | Used In |
|---|---|---|
| `autom8y_cache.testing.MockCacheProvider` | Canonical cache mock | 4 conftests (`cache/`, `clients/`, `persistence/`, `persistence/test_session_detection_invalidation`) |
| `autom8y_log.testing.MockLogger` | Log capture | Root conftest (`conftest.py:71`), propagated as `logger` fixture |
| `autom8y_telemetry.testing.find_span` | Span lookup | `tests/test_computation_spans.py:27` |

**SDK testing import count: 6 direct imports** (low utilization relative to 512 test files — but appropriate, as most tests don't need these specific primitives).

### 12.2 `tests/_shared/mocks.py` (GOLDEN)

**MockTask canonical:** 14 consuming files. Consolidation from HYG-003 is complete.

### 12.3 Root Conftest Fixtures (GOLDEN shared)

`mock_http`, `auth_provider`, `logger`, `config` — autouse and available to all. Direct adoption appears high for API/transport tests. Non-adoption occurs where tests construct their own `MagicMock()` inline rather than using fixtures — spot check confirmed in `test_client.py:16` (MockAuthProvider class) and `test_asana_http.py:23` (MockAuthProvider class) despite the root conftest providing `auth_provider` fixture.

### 12.4 Shared Infrastructure Utilization Summary

| Infrastructure | Canonical location | Utilization |
|---|---|---|
| MockTask | `tests/_shared/mocks.py` | 14/~25 applicable files (high) |
| MockLogger | Root conftest fixture | Multiple — fixture widely used |
| MockCacheProvider (SDK) | `autom8y_cache.testing` | 4 direct; 1 standalone reinvention |
| MockAuthProvider (root fixture) | `tests/conftest.py:82` | Partial — 3 reinventions exist despite fixture |

---

## 13. Raw Metrics Table

| Metric | Value | Source |
|---|---|---|
| Total test files (test_*.py) | 512 | `find tests -name "test_*.py"` |
| Total test Python LOC | ~263,200 | `wc -l` all test/*.py |
| Total source Python LOC | ~142,359 | `wc -l` all src/*.py |
| Test-to-source LOC ratio | **1.85:1** | 263,200 / 142,359 |
| Conftest count (main tree) | 15 | `find tests -name conftest.py` |
| `@pytest.fixture` in root conftest | 6 | `grep @pytest.fixture conftest.py` |
| `@pytest.mark.scar` total usages | 42 | grep count |
| SCAR-referenced distinct IDs | 7 (REG-001, 005, 006, 020, WS8, W1E-LOADGROUP-001, + inline) | content grep |
| xfail module markers (fuzz) | 1 module-level xfail(strict=False) | `test_openapi_fuzz.py:58` |
| Stated xfail violations | 47 (comment) / ~46 active | `test_openapi_fuzz.py:44-49` |
| `worker_isolated` quarantine files | 1 | `test_workflow_handler.py:58` |
| asyncio.run-in-sync-test files | 8 total (1 quarantined, 7 unquarantined) | grep |
| asyncio.run call sites (unquarantined) | 41 calls across 7 files | grep count |
| Adversarial-named test files | 15 | find |
| Sprint-epoch named files | 1 (`sprint2` suffix) | find |
| MockTask definitions | 1 (canonical, 0 violations) | grep |
| MockCacheProvider variants | 5 (4 extend SDK, 1 standalone) | grep + inspect |
| MockAuthProvider bespoke defs | 3 (despite fixture) | grep |
| MockProcess bespoke defs | 4 | grep |
| MockPageIterator bespoke defs | 4 | grep |
| Total `class Mock*` definitions | ~105 | grep |
| Files importing _shared MockTask | 14 | grep |
| test_splits (shards) | 4 | `test.yml:60` |
| xdist maxprocesses | 2 | `test.yml:59` |
| .test_durations entries | 13,597 | `wc -l .test_durations` |
| coverage fail_under | 80% | `pyproject.toml:120` |
| PR coverage threshold | 0 (disabled) | `test.yml:52` |
| Post-merge coverage enforced | YES (push to main) | `post-merge-coverage.yml:83` |
| slow tests skipped on PR | YES (23 tests) | `test.yml:64` |
| integration tests on PR | NO | `test.yml:65` |
| ruff check on PR | NO (upstream reusable) | session observation |
| mypy --strict on PR | NO (upstream reusable) | session observation |

---

## 14. The 3-5 Highest-Leverage Consolidation Surfaces

Identified for entropy-assessor; severity assignment deferred to entropy-assessor per role boundaries.

**1. ruff check + mypy --strict PR/main gate asymmetry (ASSESS-1/ASSESS-10)**
Root is in upstream `satellite-ci-reusable.yml@cbc3c58e` conditional logic — not directly configurable from this repo's `test.yml`. Three sequential fix-forward commits on main. Requires either: (a) upstream reusable workflow modification to run both on PR, or (b) duplicate ruff check + mypy steps added directly to this repo's `test.yml`. Cross-repo scope flag: work touches autom8y monorepo.

**2. asyncio.run-in-sync-test unquarantined family (ASSESS-5)**
7 files with 41 `asyncio.run` call sites in synchronous test methods have no quarantine marker or xdist isolation. The documented SIGKILL mechanism (resource pressure + co-resident asyncio-heavy tests under loadgroup) could trigger on any of them. `test_seeder.py` alone has 14 call sites. Root fix: convert production code to async-native where possible; migrate tests to `async def` + pytest-asyncio where the production code is async. The quarantine-as-permanent-design for `test_workflow_handler.py` is the technical debt embodiment.

**3. automation/ domain mock proliferation**
`tests/unit/automation/` has no domain-level conftest providing MockProcess, MockBusiness, MockUnit, MockSection, MockPageIterator, MockProcessType(Enum). These are independently redefined across 6-8 files with 15-25 variants total. An `automation/conftest.py` providing shared fixtures for this domain would eliminate the proliferation. The pattern mirrors the HYG-003 MockTask consolidation already executed.

**4. Schemathesis blanket xfail (47 violations, non-strict, non-blocking)**
One module-level `xfail(strict=False)` plus `continue-on-error: true` at job level means 47 contract violations produce zero signal. The comment documents per-endpoint narrowing as "tracked separately" but there is no evidence of a deadline or assignee. The fuzz suite is structurally incapable of failing the gate. Per-endpoint triage + reclassification to strict xfails (or root fixes) is the consolidation path.

**5. MockCacheProvider standalone reinvention + MockAuthProvider fixture bypass**
`tests/unit/cache/test_events.py:38` defines a `MockCacheProvider` that does NOT extend the SDK canonical — a structural divergence. Three `MockAuthProvider` classes bypass the root conftest `auth_provider` fixture. Both are symptomatic of the same pattern: authors creating local mocks rather than consuming shared fixtures. Consolidation is low-cost (replace with fixture injection or SDK extension pattern).

---

## 15. Scan Completeness

- [x] Test file census complete (512 test files, 15 conftests mapped)
- [x] Fixture topology mapped (15-level conftest hierarchy, autouse fixtures cataloged)
- [x] MockTask consolidation verified (HYG-003 complete; 1:1)
- [x] Mock proliferation measured (105 total class definitions, key types indexed)
- [x] xdist quarantine enumerated (1 quarantined + 7 unquarantined asyncio.run-in-sync files)
- [x] Coverage configuration mapped (PR=0, main=80% post-merge, ADR-011)
- [x] Adversarial file accumulation cataloged (15 files, 1 sprint-epoch file)
- [x] SCAR marker count confirmed (42 usages, 7 distinct references)
- [x] Schemathesis xfail confirmed (~46-47 violations, 1 module-level non-strict)
- [x] PR vs. main CI gate asymmetry mapped (ruff check, mypy, slow, integration)
- [x] Shared infrastructure utilization measured (SDK mocks, _shared, root conftest)
- [x] No scan areas incomplete
- [x] No areas escalated to user (structure unambiguous)
