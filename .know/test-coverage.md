---
domain: test-coverage
generated_at: "2026-07-23T14:56:44Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./mcp/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "70d45434e1e79ce7bc380936e47a4e265447ffd4db88dc37cd8b37edc70b862f"
confidence: 0.90
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "9db9c6f33d48f5c2fce398de7d3359fef30a0a0bd809044f7259f792ee6c4b9e"
---

# Codebase Test Coverage

> Fresh full re-census at synced HEAD `d0c8b662` (2026-07-23), direct grep/find verified. Volume growth since the last census: test files 502→**655**, test functions ~12,842→**14,603**, asserts 23,881→**28,488**, `pytest.raises` 1,249→**1,538**, xdist_group 3→**6** groups, parametrize sites 148→**205**, scar marks 35→**46**, schemathesis xfail 47→**55**. Root `tests/` and the disjoint `mcp/tests/` island mapped separately.

## Coverage Gaps

### Package-Level Map
Source: 26 top-level packages (501 non-`__init__.py` .py). `tests/unit/` has 26 matching subdirs + 3 cross-cutting (`canary/`, `packaging/`, `knowledge/`). **Packages with zero dedicated `tests/unit/` subdir** (unchanged): `_defaults/` (indirect only), `batch/` (indirect across 8 files), `observability/` (indirect via `test_observability.py` + scattered span asserts), `protocols/` (no conformance-test suite).

### Module-Level Gaps
- `lifecycle/loop_detector.py` — **no `test_loop_detector.py`**, BUT `LoopDetector` IS behaviorally tested (`TestLoopDetector` in `test_webhook_dispatcher.py:230`, `TestLO15…` in `test_lifecycle_observation_contracts.py:547`). **File-organization gap, not a coverage gap** — corrects the prior doc's "unguarded safety path" characterization.
- `lifecycle/observation_store.py` — no dedicated test; indirect contract coverage only.
- `services/intake_create_service.py`/`intake_resolve_service.py`/`intake_custom_field_service.py` — tested ONLY through the HTTP route layer; service-layer error/boundary paths unverified in isolation.
- `services/entity_context.py` — no direct unit test.
- `models/` top-level (15 resource models) — indirect + `test_models.py` instantiation checks.

### Schemathesis / OpenAPI Fuzz
`tests/test_openapi_fuzz.py` `KNOWN_VIOLATIONS` = **55 entries** (45 violation `xfail` + 10 conforming-pinned XPASS), up from 47. `xfail(strict=False)`; `fuzz` CI job is `continue-on-error` (non-blocking).

### Prioritized Gaps
1. `services/intake_*_service.py` (3) — critical write path, HTTP-layer-only coverage.
2. `lifecycle/observation_store.py` — no direct test.
3. `services/entity_context.py` — no direct test.
4. `lifecycle/loop_detector.py` — naming/discoverability gap only (downgraded from "unguarded").
5. `_defaults/` + `protocols/` — no dedicated dirs.
6. Schemathesis 55 xfail — pending endpoint-by-endpoint triage.

### Coverage Infrastructure
`[coverage.run] source=["src/autom8_asana"]`, `branch=true`; `[coverage.report] fail_under=80`. PR gate: `coverage_threshold: 0` per-shard (meaningless at 4-way split), `coverage_threshold_aggregate: 80` (combines 4 `.coverage`), `mypy_targets: 'src/autom8_asana'`. Post-merge: `post-merge-coverage.yml` single-shard `pytest --cov-fail-under=80` on push to main. No fresh %-run this cycle (Knowledge Gap).

## Testing Conventions

- Runner: `pytest`, `asyncio_mode="auto"`, `testpaths=["tests"]`, `addopts="--dist=loadgroup"`, `timeout=60`. PR CI: `test_maxprocesses: 2`, `test_splits: 4` (pytest-split, `.test_durations`, weekly `durations-refresh.yml`). PR marker exclusion drops `not slow` on push (`run_integration` on `push`).

### xdist_group Inventory — GROWN (3→6 groups, 32 files)
`fuzz` (1), `workflow_handler` (4), `query_routes` (4), **`scheduling_normalizer` (8, NEW)**, **`gfr_resolver` (11, NEW)**, **`gfr_drift_gate` (1, NEW)**. xdist history: disabled → re-enabled → load → loadfile → load → **loadgroup** (current).

### Markers
`parametrize` 205 sites/91 files (was 148/63); `integration` 44/8 files; `slow` 23/14; `scar` **46/17** (was 35/11); `benchmark` 3; `fuzz` 1 module; `worker_isolated` 4 (`test_workflow_handler*.py` — SIGKILL-under-xdist scar, run single-process non-blocking); `skip` 16; `skipif` (subset — `FAKEREDIS_AVAILABLE`/`MOTO_AVAILABLE`/`_HAS_HYPOTHESIS`).

### Other
- Hypothesis: exactly **1** `@given` in `tests/unit/` (`test_reorder.py:274`, `derandomize=True`); `test_openapi_fuzz.py` is the schemathesis consumer.
- Mocking: `AsyncMock`/`MagicMock` dominant; `MagicMock(spec=)` **147/38 files** (was 136/33); `respx` for httpx; `fakeredis`/`moto` conditional; SDK doubles funneled through conftest.
- MockTask canonicalization intact: `tests/_shared/mocks.py:12` the single `class MockTask` ("SUPERSET of all 11 prior variants per HYG-003"). `MockTasksClient` is a distinct class.

## Fixture Patterns

- **752** `@pytest.fixture` (was 687), **17** `conftest.py` (+ a disjoint `mcp/tests/conftest.py`). Root conftest: `_bootstrap_session` (session autouse), `reset_all_singletons` (function autouse, `SystemContext.reset_all()`), forces `AUTOM8Y_ENV=test`/`AUTH__JWKS_URL`, patches schemathesis xdist reporting.
- **Golden files DO exist [correction]**: prior doc said "no file-based test data" — FALSE. `tests/fixtures/scheduling_posture_golden_entries.json` (consumed by `test_scheduling_posture_golden.py`) and `tests/unit/knowledge/fixtures/drift/` both exist. Golden-file testing IS present, narrowly scoped.
- Dominant inline construction: `make_*`/`create_*`/`build_*` helpers.

## Test Structure Summary

```
tests/                              655 test_*.py
  conftest.py, _shared/mocks.py (canonical MockTask)
  arch/            2   # StorageNamespaceContract t1-t5, discriminating-canary RED/GREEN
  unit/          604   # api 86 · automation 70 · dataframes 66 · cache 60 · clients 47 ·
                       #   models 41 · services 33 · persistence 28 · lambda_handlers 28 ·
                       #   query 23 · resolution 20 · metrics 15 · lifecycle 15 · transport 13 ·
                       #   core 12 · auth 9 · reconciliation 8 · normalizer 6 · search 3 ·
                       #   canary 3 · patterns 2 · domain 2 · packaging 1 · knowledge 1 · contracts 1 · detection 1
  integration/    38   # 8 carry @pytest.mark.integration (44 marks); 30 wire real components w/ mocked I/O
  contracts/       1 · validation/persistence/ 5 · synthetic/ 1 · benchmarks/ 1 · fixtures/ 1 golden JSON
```
Distribution: 655 files / 14,603 functions / 28,488 asserts / 1,538 `pytest.raises`. Packages with ZERO `tests/integration/`: auth, core, models, metrics, query, patterns, transport, search, reconciliation.

- **`tests/arch/`** (previously undocumented category): `test_namespace_contract.py` + `test_namespace_gen.py` — StorageNamespaceContract t1-t5 via the discriminating-canary doctrine (each test paired with a deliberately-broken registry COPY proving it fires RED — guards "G-THEATER").
- **`tests/synthetic/test_synthetic_coverage.py`** (purpose resolved): full-surface OpenAPI harness ("Project Aegis") — a parametrized invocation exercising every operation across 44 paths / ~54 ops, NOT a coverage-gap detector.

## MCP Island Test Topology (`mcp/tests/`) — DISJOINT ISLAND, NOT COLLECTED

**The single highest-priority structural finding.** 24 `test_*.py` + 1 `conftest.py` (158 test functions, 422 asserts). Its own `mcp/pyproject.toml` (`name="asana-mcp"`, own `[tool.pytest.ini_options]`, `pythonpath=["."]`); `mcp/tests/conftest.py` builds a faked-HTTP fixture set (`httpx.MockTransport`).

- **NOT collected by root pytest**: root `testpaths=["tests"]` excludes `mcp/`; bare `pytest` from root never discovers it.
- **NOT in any CI workflow**: `grep -rn "mcp" .github/workflows/*.yml` → **zero** matches across all 12 workflows.
- **No justfile target** references `mcp/` test execution.
- **NOT in coverage source** (`coverage_package: 'autom8_asana'`, `source=["src/autom8_asana"]`; `mcp/pyproject.toml` has no `[tool.coverage]`).
- **NOT type-checked** (`mypy_targets: 'src/autom8_asana'`; `mcp/pyproject.toml` has no `[tool.mypy]`).
- **Ruff DOES reach it** (repo-wide) with a `mcp/**` carve-out (`TID251`, `TC001-3`, `ERA001`, `SIM105`) — the only quality gate touching `mcp/`.

Reference posture is explicit (charter §5.3 "NOT production code, NOT to be promoted before the §4 probe rules COMMIT") — but the ENTIRE 158-function suite is local-only-gated: a contributor can break every one and merge to `main` with zero CI signal. Satellite-side tests that ARE CI-gated: `tests/unit/services/test_entity_vocabulary_parity.py`, `tests/unit/api/preload/test_ready_fail_closed.py` (root `tests/`, not part of the island).

## Knowledge Gaps

1. Actual runtime coverage % — `fail_under=80` enforced; no report run this cycle.
2. `tests/validation/persistence/` — whether it runs in the 4-shard PR matrix or only post-merge, unverified.
3. `services/intake_*_service.py` + `entity_context.py` — direct unit-test isolation still unresolved.
4. Schemathesis 55 xfail — endpoint-by-endpoint triage pending.
5. `mcp/tests/` island CI-gap — confirmed total (no workflow/justfile/coverage/mypy); resolution (dedicated `pytest`-from-`mcp/` lane vs recorded reference-posture acceptance) unexplored.
6. `xdist_group` growth — the commits introducing `scheduling_normalizer`/`gfr_resolver`/`gfr_drift_gate` not traced this cycle.

## Experiential Observations (from `.sos/land/workflow-patterns.md`)

Cross-session: test execution present in multiple sessions; the corpus has grown ~13% past the project-crucible campaign floor (13,072→12,320 dedup / 87.59% baseline are experiential, not re-measured — current live function count 14,603 exceeds both). Parametrize discipline (≥8% target) met and climbing. [Numbers attributed as experiential where not directly re-derived.]
