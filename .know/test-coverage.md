---
domain: test-coverage
generated_at: "2026-10-05T03:05:00Z"
expires_after: "7d"
source_scope:
  - "./src/autom8_asana/__init__.py"
  - "./src/autom8_asana/client.py"
  - "./src/autom8_asana/config.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./src/autom8_asana/errors.py"
  - "./src/autom8_asana/settings.py"
  - "./src/autom8_asana/storage_namespace.py"
  - "./mcp/asana_mcp/__init__.py"
  - "./mcp/asana_mcp/assembly.py"
  - "./mcp/asana_mcp/bridge.py"
  - "./mcp/asana_mcp/context.py"
  - "./mcp/asana_mcp/envelopes.py"
  - "./mcp/asana_mcp/errors.py"
  - "./mcp/asana_mcp/observability.py"
  - "./mcp/asana_mcp/schemas.py"
  - "./mcp/asana_mcp/server.py"
  - "./mcp/asana_mcp/settings.py"
  - "./mcp/asana_mcp/timeouts.py"
  - "./mcp/canary/test_broken_fixture_canary.py"
  - "./mcp/probes/c2_sandbox_reput_probe.py"
  - "./mcp/tests/conftest.py"
  - "./mcp/tests/test_assembly_floor.py"
  - "./mcp/tests/test_bridge_401_fail_clean.py"
  - "./mcp/tests/test_budget_partition_and_rate_cap.py"
  - "./mcp/tests/test_cold_frame_mapping.py"
  - "./mcp/tests/test_composite_write_s3.py"
  - "./mcp/tests/test_confirm_gate_rb1.py"
  - "./mcp/tests/test_discovery_tools.py"
  - "./mcp/tests/test_errors_c3.py"
  - "./mcp/tests/test_errors_passthrough.py"
  - "./mcp/tests/test_errors_substrate_424.py"
  - "./mcp/tests/test_fences.py"
  - "./mcp/tests/test_honesty_passthrough.py"
  - "./mcp/tests/test_import_safety_obs.py"
  - "./mcp/tests/test_import_safety.py"
  - "./mcp/tests/test_instrument_seam.py"
  - "./mcp/tests/test_postures.py"
  - "./mcp/tests/test_query_tools.py"
  - "./mcp/tests/test_readiness_gate.py"
  - "./mcp/tests/test_resolve_tool.py"
  - "./mcp/tests/test_schema_canary.py"
  - "./mcp/tests/test_seam_conformance.py"
  - "./mcp/tests/test_span_and_traceparent.py"
  - "./mcp/tests/test_tag_dual_key_wsb2.py"
  - "./mcp/tests/test_timeout_cascade_invariant.py"
  - "./mcp/tests/test_workflows_disclosure.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "6a8debe2b2650bf405b8e8a3a03e3c969e935410abcd9c5b1c21410fbd76784d"
confidence: 0.86
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@c29f58f4"
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "9db9c6f33d48f5c2fce398de7d3359fef30a0a0bd809044f7259f792ee6c4b9e"
---

# Codebase Test Coverage

> Fresh full re-census at origin/main `c29f58f4` (2026-10-04), observed in a detached worktree; every count below was re-derived by grep/find/script, not carried from the 2026-07-23 doc. Growth since the prior census (`d0c8b662`): test files 655 → **726**, test functions 14,603 → **15,973**, asserts 28,488 → **31,578**, `pytest.raises` 1,538 → **1,724**, `@pytest.fixture` 752 → **792**, parametrize 205 → **275** sites / 116 files, `xdist_group` 6 groups / 32 files → 6 groups / **35** files. Root `tests/` and the disjoint `mcp/tests/` island are mapped separately. Test language: Python (`pyproject.toml:117-146`); runner `pytest` + `pytest-asyncio` (`asyncio_mode="auto"`, 4,489 `async def test_*`).

## Coverage Gaps

### Package-level map (structural)
Source: 30 package dirs under `src/autom8_asana/` (543 non-`__init__.py` .py files, incl. 6 root modules such as `client.py`, `config.py`, `entrypoint.py`). New since prior: **`substrate/`** (11 modules), **`enrollment/`** (2), **`readout/`** (3 modules + `__init__`) — all three have direct test coverage (`tests/unit/substrate/` 15 files, `tests/unit/enrollment/` 2 files; `readout/` is covered by top-level `tests/unit/test_readout_generation.py`, `test_rail_readout_shape.py`, `test_rail_block_budget.py`, `test_rail_delivery_receipt.py`, `test_rung_receipts.py` — there is NO `tests/unit/readout/` dir).

Packages with **no matching `tests/unit/<pkg>/` subdir** (4 of 30, unchanged set, but `readout` is now a fifth by directory-name alone): `_defaults/`, `batch/`, `observability/`, `protocols/` (+ `readout/` tested via top-level files). Methodology: a script scanned every `src` module for a dotted-path reference (`autom8_asana.<pkg>.<mod>`), a `from <pkg> import <mod>`, or a `test_*<stem>*.py` filename anywhere under `tests/`.

**Module-level result: 514 of 542 modules (94.8%) have at least one test-side reference; 28 have none** (heuristic — package `__init__` re-exports can hide indirect use). Unreferenced modules, by criticality:

| Tier | Module(s) | Why it matters |
|------|-----------|----------------|
| Higher | `entrypoint.py` (root); `api/routes/tags.py`; `api/error_responses.py`; `api/health_models.py` | Process entry / HTTP error shaping. NOTE: `tests/unit/api/test_tags_auth_exclusion.py` is `@pytest.mark.scar` and `test_tag_service.py` exists, so `tags.py` is exercised via the app client, not by import path |
| Higher | `automation/workflows/active_offer_enumeration.py`; `api/routes/identity_supply_models.py`, `api/routes/forwarding_stage_census_models.py` | Recently added workflow / S2S route models; no import-path reference |
| Medium | `cache/integration/schema_providers.py`, `cache/integration/upgrader.py`, `cache/backends/base.py` | Cache seam; ABC base + upgrader unreferenced |
| Medium | `dataframes/builders/post_build_validation.py`, `dataframes/resolver/default.py`, `dataframes/resolver/mock.py` | Post-build validation unreferenced |
| Medium | `clients/task_operations.py`, `clients/task_ttl.py`, `clients/goal_relationships.py`, `clients/goal_followers.py`, `clients/data/_endpoints/simple.py` | Client mixins; likely reached through `tasks`/`goals` client tests |
| Lower | `core/string_utils.py`, `core/datetime_utils.py`, `observability/correlation.py`, `observability/decorators.py`, `observability/rung_receipts/join.py`, `protocols/log.py`, `protocols/item_loader.py`, `models/business/mixins.py`, `query/cli.py`, `api/preload/constants.py` | Utilities / Protocols (no conformance suite) / CLI |

### Corrections to the prior doc's "Module-Level Gaps"
Prior listed these as untested; at `c29f58f4` they are **referenced**:
- `lifecycle/loop_detector.py` — `autom8_asana.lifecycle.loop_detector` imported by `tests/unit/lifecycle/test_webhook_dispatcher.py` and `test_lifecycle_observation_contracts.py` (no dedicated `test_loop_detector.py`: file-organization gap only).
- `lifecycle/observation_store.py` — imported by `tests/unit/lifecycle/test_lifecycle_observation_contracts.py` (contract coverage, no dedicated file).
- `services/intake_create_service.py` / `intake_resolve_service.py` / `intake_custom_field_service.py` — imported by `tests/unit/api/routes/test_intake_create.py`, `test_intake_resolve.py`, `test_intake_custom_fields.py`, plus `tests/unit/services/test_br3_unit_vertical_carry.py` and `test_intake_resolve_business_index.py` (service-layer test now exists for resolve; create/custom_field remain route-layer-mediated).
- `services/entity_context.py` — imported by `tests/unit/services/test_entity_service.py`.
Residual: no dedicated `tests/unit/services/test_intake_*_service.py` for create/custom-field; isolation of service error paths from the HTTP layer is unverified.

### Known blind spots (code-verified)
1. **`metrics/compute.py` select-then-filter ordering has no regression test.** `compute.py:90-97` projects only `name` + dedup keys + metric column (`df.select(unique_cols)`), and `compute.py:105-107` applies `expr.filter_expr` AFTER the projection. Every `filter_expr` in `tests/unit/metrics/test_adversarial.py:144,174,260` references the metric column `val` (always selected); `test_lifecycle_metrics.py:140-143` only asserts `filter_expr is not None`. No test builds a `filter_expr` over a non-projected column. Matches the open SCAR-METRICS-SELECT-FILTER-001 from the sibling scar-tissue doc; `grep SCAR-METRICS` over `tests/` and `src/` returns nothing.
2. **Scar marker coverage stalled.** `@pytest.mark.scar` = **46 sites / 17 files** (`grep mark\.scar tests`), identical to the prior count while sibling scar-tissue reports ≥17 newer unmarked scars. The `scar` marker is declared at `pyproject.toml:130`; selecting with `-m scar` therefore under-represents the true regression set.
3. **Resolved-scar narration guard covers 2 IDs.** `tests/unit/knowledge/register_drift_checks.py:36` `RESOLVED_SCAR_IDS = frozenset({"SCAR-REG-001","SCAR-IDEM-001"})` — the only drift-guard on resolved-scar prose; new resolutions must be appended manually (comment at :33 "Add new IDs here").
4. **Three of four `worker_isolated` modules never run in the blocking CI gate nor the isolated job.** `worker_isolated` is a module-level `pytestmark` in 4 files (`tests/unit/lambda_handlers/test_workflow_handler.py:58`, `test_workflow_handler_auth_injection.py:50`, `test_workflow_handler_workspace_gid.py:54`, `test_workflow_handler_dataframe_cache_init.py:58`). The sharded PR/push gate excludes them (`.github/workflows/test.yml:121` `not … worker_isolated`). The `workflow-handler-isolated` job (non-blocking, `continue-on-error: true`, `test.yml:306`) runs ONLY `tests/unit/lambda_handlers/test_workflow_handler.py` (`test.yml:382-384`; the in-file comment at `test.yml:379-381` says "Add a file here when you quarantine a test in a new module" — 3 files were not added). Only `post-merge-coverage.yml:94` (`-m "not integration and not benchmark and not fuzz"`) re-includes them, on push to main.
5. **Negative-path density is high but uneven.** `pytest.raises` appears 1,724× in 324 files; adversarial/edge/fail/error-named files: 42 (`test_*error*|*adversar*|*edge*|*fail*`) + 23 `test_*adversar*|*qa_adversary*`. Negative tests absent (by dir-name signal) for `observability/` and `protocols/`, which have no dedicated tests dir.

### Schemathesis / OpenAPI fuzz
`tests/test_openapi_fuzz.py:70` `KNOWN_VIOLATIONS` has **56 dict entries** (header text at :71 says 45 VIOLATION xfail; :130 says 10 CONFORMING-PINNED XPASS; the remaining one is outside either header comment — prior doc said 55). Applied as `xfail(strict=False)` at runtime (`:247-264`). `fuzz` job is `continue-on-error: true` (`test.yml:144`), runs `-p no:xdist`, `SCHEMATHESIS_MAX_EXAMPLES` 5 on PRs / 25 otherwise (`test.yml:283-289`).

### Prioritized Gaps
1. Regression test for `metrics/compute.py:97` vs `:107` (filter on non-projected column) — open scar, zero guard.
2. Add the 3 omitted `worker_isolated` modules to `test.yml:382-384` file list (silent non-execution in the blocking-adjacent lane).
3. Mark the ≥17 unmarked scar tests with `@pytest.mark.scar`; extend `RESOLVED_SCAR_IDS` (`register_drift_checks.py:36`) beyond 2 of ≥5 resolved IDs.
4. Direct service-layer tests for `services/intake_create_service.py` and `intake_custom_field_service.py` (route-mediated only).
5. `entrypoint.py`, `api/error_responses.py`, `api/routes/tags.py` — no import-path reference; confirm indirect coverage or add.
6. `observability/`, `protocols/`, `_defaults/`, `batch/` — no dedicated test dirs (indirect: `tests/unit/test_observability.py`, `tests/unit/test_batch_adversarial.py`).
7. Schemathesis 56 known violations — endpoint triage pending.

### Coverage infrastructure
- `pyproject.toml:134-146`: `[coverage.run] source=["src/autom8_asana"]`, `branch=true`; `[coverage.report] fail_under=80`; `exclude_lines` = `pragma: no cover`, `if TYPE_CHECKING:`, `@abstractmethod`, `raise NotImplementedError`, `if __name__ == .__main__.:`.
- PR/push gate (`test.yml:99-137`): reusable `satellite-ci-reusable.yml@c824da59…`, `coverage_threshold: 0` per shard, `coverage_threshold_aggregate: 80`, `test_splits: 4`, `test_maxprocesses: 2`, `mypy_targets: 'src/autom8_asana'`, `run_integration: github.event_name == 'push'`, PR marker exclusion `not integration and not benchmark and not slow and not fuzz and not worker_isolated` (push drops `not slow`).
- Post-merge (`post-merge-coverage.yml:93-94`): single-shard `--cov-fail-under=80`, `-m "not integration and not benchmark and not fuzz"`, on push to `main` + `workflow_dispatch`.
- Other test lanes: `aegis-synthetic-coverage.yml:73` (`pytest tests/synthetic/`), `nightly-live-smoke.yml` (cron `15 9 * * *`, live S3 smokes `tests/unit/cache/test_durable_task_cache_live_smoke.py`, `tests/unit/dataframes/builders/test_null_number_recovery_live_smoke.py`, with a log-grep "assert smokes RAN" step), `durations-refresh.yml` (weekly Monday cron, `.test_durations` = 13,596 entries).
- **No measured coverage % in this cycle** (no runnable venv for the worktree — see Knowledge Gaps).

## Testing Conventions

### Runner and invocation
- `pyproject.toml:117-124`: `asyncio_mode="auto"`, `testpaths=["tests"]`, `timeout=60`, `timeout_method="thread"`, `addopts="--dist=loadgroup"`. CI per-job timeout `test_timeout: 40` (`test.yml:110`).
- `justfile`: `test` (`uv run pytest`), `test-cov`, `test-fast` (`-m "not slow and not integration and not benchmark"`, :112), `test-slow`, `test-integration` (needs `ASANA_PAT`), `test-bench`, `fitness` (:135, runs `tests/unit/dataframes/test_concurrency_invariants_guard.py -p no:xdist -o addopts=""`), **`test-mcp` (:145, new)**.

### Naming and structure
- Files `test_*.py` only (0 `*_test.py`). 607 of 726 test files use `class Test*` (3,587 classes); the rest are module-level `def test_*`. Test-name stems are descriptive (`test_get_*` 408, `test_no_*` 307, `test_empty_*` 275). 66 `__init__.py` files under `tests/` make most dirs packages (imports like `from tests.unit.knowledge.register_drift_checks import …` at `tests/unit/knowledge/test_register_drift_guard.py:25`).
- Assertions are bare `assert` (31,578 vs. `unittest.TestCase` = 0 files). Exceptions via `pytest.raises` (1,724 / 324 files). `caplog` in 194 files, `capsys/capfd` 37 files.
- Parametrization: `@pytest.mark.parametrize` 275 sites / 116 files (61 at column-0 decorator form), `ids=` 296 occurrences.

### Markers (all counts re-derived)
| Marker | Sites / files | Notes |
|--------|---------------|-------|
| `parametrize` | 275 / 116 | prior 205/91 |
| `integration` | 49 / 12 | declared `pyproject.toml:127`; **8** of 12 files live in `tests/integration/`; note `tests/unit/automation/workflows/test_onboarding_walkthrough.py` also carries it (misplaced by dir) |
| `slow` | 24 / 15 | PR lane excludes |
| `scar` | 46 / 17 | `pyproject.toml:130`; flat vs prior |
| `benchmark` | 4 / 1 | `tests/benchmarks/test_insights_benchmark.py` |
| `fuzz` | 1 / 1 | `tests/test_openapi_fuzz.py` |
| `worker_isolated` | 4 / 4 | `pyproject.toml:131`; see Gap 4 |
| `skip` | 11 / 4 | plus `pytest.skip(` 34 / 18 |
| `skipif` | 49 / 27 | 25× `not MOTO_AVAILABLE`, 16 with multi-line conditions, 3× `not ASANA_PAT` (live-API gating), 1× each `os.geteuid()==0`, `MYPY_AVAILABLE`, `JSONSCHEMA_AVAILABLE`, `FAKEREDIS_AVAILABLE`, `_HAS_HYPOTHESIS` |
| `xfail` | 4 / 3 (+ runtime xfails from `KNOWN_VIOLATIONS`) | |
| module `pytestmark` | 53 / 52 | the dominant way markers/groups are applied |
| `importorskip` | 3 / 2 | |

### xdist_group inventory (35 files, 6 groups)
Re-derived by grep of `xdist_group(...)`: `scheduling_normalizer` (13 uses — `tests/unit/normalizer/test_scheduling_*.py`, `test_normalizer_fitness.py`, `test_gcal_served_calendar_id.py`, `tests/unit/lambda_handlers/test_scheduling_*snapshot*`, `test_office_spine_projection.py`, `tests/unit/services/test_scheduling_*`), `gfr_resolver` (12 — `tests/unit/resolution/gfr/*`, `tests/integration/test_gfr_tenant_roundtrip.py`, `tests/integration/test_pr1_qa_adversary_probes.py`), `workflow_handler` (4 — the 4 `worker_isolated` modules), `query_routes` (4 — `tests/unit/api/test_routes_query_*.py`), `gfr_drift_gate` (1 — `tests/unit/resolution/gfr/test_drift_gate.py`), `fuzz` (1). Rationale lives at `tests/unit/lambda_handlers/test_workflow_handler.py:25-46` and `tests/test_openapi_fuzz.py:64-72` (cited by `pyproject.toml:122-123`). Hypothesis: exactly **1** `@given` in `tests/` (`tests/unit/persistence/test_reorder.py:274`) — property testing is effectively absent outside the schemathesis fuzz consumer (`tests/test_openapi_fuzz.py`).

### Mocking / doubles
`unittest.mock` imported in 434 files; `AsyncMock`/`MagicMock` in 399 files; spec'd mocks (`MagicMock(spec…)`/`create_autospec`/`AsyncMock(spec…)`) **184 uses / 41 files** (prior 147/38). `respx` 18 files; `moto` 12 files; `fakeredis` 1 file (the `FAKEREDIS_AVAILABLE` skipif); `monkeypatch` 84 files; `tmp_path` 28 files; freezegun/time-machine: 0 files. Canonical mock: `tests/_shared/mocks.py:12` `class MockTask` (single definition repo-wide); `tests/_shared/factories.py:13` `make_task_dict`; `tests/_shared/cf_write_readback.py` shared helper.

## Fixture Patterns

- **792** `@pytest.fixture`/`@pytest_asyncio.fixture` in `tests/` (prior 752), **18 `conftest.py`** (root + 17; prior 17) plus `mcp/tests/conftest.py`. New: `tests/unit/substrate/conftest.py`.
- Root `tests/conftest.py`: forces `os.environ["AUTOM8Y_ENV"]="test"` (:60, force-set not setdefault), `setdefault("AUTH__JWKS_URL",…)` (:66), fails loudly if binding `ASANA_CACHE_*` env knobs leak (:81-84), `_bootstrap_session` session-autouse (:138), `reset_all_singletons` function-autouse (:205-206, `SystemContext.reset_all()`), a second autouse at :256, `pytest_configure` patches xdist `testnodedown` (:36-43). Shared fixtures: `mock_http`, `config`, `auth_provider`, `logger` (`:109-128`). conftest helper `def`s: 126 across conftests.
- **File-based fixtures exist** (corrects earlier "no testdata" worry): `tests/fixtures/scheduling_posture_golden_entries.json`; `tests/fixtures/rung_receipts/*.jsonl` + `PROVENANCE*.md`; `tests/fixtures/readout/rows_response_item1a*.json` + `PROVENANCE.md`; `tests/unit/knowledge/fixtures/drift/` (9 paired `*.green.*`/`*.stale.*` yaml/md files — two-sided teeth fixtures); `tests/harness/substrate_gate/fixtures/offer_1143843662099250/{offer_plane_section_mrr.parquet,watermark.json}` (a real captured frame). Provenance files accompany captured fixtures (convention).
- Dominant inline construction: `make_*`/`create_*`/`build_*` helpers; per-domain `conftest.py` factory fixtures (e.g. `tests/unit/reconciliation/conftest.py` `make_unit_df`).
- **Discriminating-canary / two-sided-teeth pattern**: RED fixtures paired with GREEN to prove a guard bites — `tests/arch/test_namespace_contract.py` + `test_namespace_gen.py` (StorageNamespaceContract t1-t5 with a deliberately-broken registry copy), `tests/unit/knowledge/test_register_drift_guard.py` (green/stale fixture pairs), `tests/harness/substrate_gate/test_self_discrimination.py`, `mcp/canary/test_broken_fixture_canary.py` (rc==1 is the GREEN receipt).
- **AST / source-text fitness guards**: `tests/unit/dataframes/test_concurrency_invariants_guard.py`, `tests/unit/dataframes/test_warmup_ordering_guard.py`, `tests/unit/test_swap_detector_closure.py`; `ast.parse/walk` used in 21 test files; `read_text()/getsource` in 37.

## Test Structure Summary

```
tests/                                  726 test_*.py   (15,973 test functions; 31,578 asserts)
  conftest.py, _shared/{mocks,factories,cf_write_readback}.py
  test_openapi_endpoint.py, test_openapi_fuzz.py, test_computation_spans.py   (3 top-level)
  unit/            667   # api 96 · dataframes 71 · automation 70 · cache 62 · clients 47 · models 42 ·
                         #   services 38 · lambda_handlers 36 · persistence 28 · query 24 · resolution 20 ·
                         #   lifecycle 17 · metrics 16 · substrate 15 · transport 14 · core 14 · auth 9 ·
                         #   reconciliation 8 · normalizer 7 · search 3 · canary 3 · patterns 2 ·
                         #   enrollment 2 · domain 2 · packaging 1 · knowledge 1 · detection 1 · contracts 1
                         #   + 17 top-level tests/unit/test_*.py (settings, observability, batch, readout rails, rung receipts, swap detector…)
  integration/      38   # api 2 · automation (polling+workflows) · cache 2 · events 1 · persistence 1 · ~28 flat
  harness/           8   # substrate_gate (budget, corpus, parity ×3, replay, self-discrimination, exemplar_two_drift) — NEW
  validation/persistence/ 5 · arch/ 2 · contracts/ 1 · synthetic/ 1 · benchmarks/ 1
mcp/tests/    25 test files (24 test_* + conftest) · mcp/canary/ 1
```
- Density by function count: automation 1,602 · api 1,565 · models 1,487 · dataframes 1,437 · cache 1,382 · query 992 · persistence 986 · clients 943 · services 936 · integration 624 · lambda_handlers 623 · lifecycle 411 · metrics 387 · resolution 302 · substrate 274 · harness 88.
- Unit/integration split by location: 667 unit files / 38 integration files (5.4% by files; 624 of 15,973 functions = 3.9%). `integration` marker is applied in only 12 files, so most `tests/integration/` files are "integration" by wiring mocked components, not by marker (PR lane runs them unless marked); live-API ones gate with `skipif(not ASANA_PAT)`.
- Packages with ZERO `tests/integration/` presence: auth, core, models, metrics, query, patterns, transport, search, reconciliation, lifecycle (has `tests/unit/lifecycle/test_integration.py` internally), substrate (gated by `tests/harness/substrate_gate`).
- No `TestMain`-style entry (n/a in Python); the equivalent global setup is root `conftest.py` + `_bootstrap_session`.
- Internal vs external test package: Python tests are import-based, not `package foo_test`; `tests` is importable as a package (66 `__init__.py`).

### MCP island (`mcp/tests/`) — NOW CI-GATED [material correction]
Prior doc (2026-07-23) called this "the single highest-priority structural finding: NOT in any CI workflow, no justfile target". **No longer true at `c29f58f4`:**
- `.github/workflows/test.yml:489-606` job **`mcp-island`** (FL-4, fleet-delegation-phase2 WAVE-1): installs mcp's OWN pyproject (`uv pip install --system --no-sources './mcp[dev]'`, :575), runs `python -m pytest tests -q` with `working-directory: mcp` (:577-585), then a **teeth canary**: `python -m pytest canary -q --tb=line`, requiring rc==**1** EXACTLY (:588-604). HARD GATE — no `continue-on-error` (comment at :500). 15-minute timeout.
- `justfile:145` `test-mcp` mirrors CI ("CI parity").
- Inventory: 24 `test_*.py` + 1 `conftest.py` under `mcp/tests/` (165 test functions, 444 asserts, 4 fixtures); `mcp/canary/test_broken_fixture_canary.py` (deliberately-broken SVR-5-stripped envelope that the real battery must reject); `mcp/probes/` (non-test C2 sandbox probe). Own config `mcp/pyproject.toml:55-61` (`pythonpath=["."]`, `asyncio_mode="auto"`, `testpaths=["tests"]`).
- **Still outside**: root coverage (`source=["src/autom8_asana"]`, `pyproject.toml:135`), mypy (`mypy_targets: 'src/autom8_asana'`, `test.yml:100`), and root pytest collection (`testpaths=["tests"]`). `mcp/` source (24 .py outside tests) therefore has gating TESTS but no coverage-percentage or typing gate. Includes throwaway write-path tests (`test_composite_write_s3.py`, `test_confirm_gate_rb1.py`) retained "guard-until-replaced" per `test.yml:501-505`.

## Knowledge Gaps

1. **Runtime coverage % not measured**: `fail_under=80` is the only evidence. The session venv (`.venv`, Python 3.12.13, pytest 9.0.2) could not run `pytest --collect-only` against the worktree — collection aborted with `ModuleNotFoundError: No module named 'autom8y_calendly'` (venv stale vs main's dependency set). Counts here are therefore grep-derived static counts, not pytest-collected node counts (parametrize expansion not included in the 15,973 figure).
2. `tests/validation/persistence/` (5 files) — whether it runs in the 4-shard PR matrix vs post-merge only: not verifiable without CI logs.
3. Heuristic module→test mapping (dotted-path / `from X import` / filename substring) can false-negative on re-exports and false-positive on substring matches; the 28 "unreferenced" and 514 "referenced" are bounds, not proofs.
4. Whether the 3 omitted `worker_isolated` modules pass under single-process post-merge coverage was not run.
5. KNOWN_VIOLATIONS entry count 56 vs comment arithmetic 45+10=55 — the extra entry unidentified.
6. `tests/unit/api` has subdirs `middleware/`, `preload/`, `routes/` — per-route-file test completeness (96 api test files vs. route count) not exhaustively mapped.

### Changes since prior version (2026-07-23 → origin/main `c29f58f4`)
- **CORRECTED — mcp island CI gap CLOSED**: now a hard-gated `mcp-island` job + `just test-mcp` + teeth canary (`test.yml:489-606`, `justfile:145`); the prior "zero workflow matches / no justfile target" claim is obsolete. Residual: still outside coverage/mypy.
- **CORRECTED — module-gap list**: `intake_*_service`, `entity_context`, `observation_store`, `loop_detector` all carry import-path test references; prior "no direct test" is retracted for all but a dedicated-file sense.
- **NEW — `worker_isolated` coverage hole**: 3 of 4 quarantined modules not executed by the blocking gate or the isolated job (`test.yml:382-384`).
- **NEW — packages**: `substrate/` (15 test files + 8-file `tests/harness/substrate_gate/`), `enrollment/` (2), `readout/` (top-level tests only).
- **NEW — metrics select/filter blind spot** (no test; ties to sibling scar-tissue SCAR-METRICS-SELECT-FILTER-001).
- Volume: files 655→726, functions 14,603→15,973, asserts 28,488→31,578, raises 1,538→1,724, fixtures 752→792, parametrize 205→275, spec'd mocks 147→184, integration marks 44→49, skipif 49 sites; scar marks flat at 46/17; `xdist_group` files 32→35 (same 6 groups); KNOWN_VIOLATIONS 55→56.
- Harness: `tests/harness/substrate_gate/` (8 test files + 7 support modules + parquet fixture) and `tests/arch/` confirmed; `tests/synthetic/` remains the Aegis OpenAPI harness (`aegis-synthetic-coverage.yml:73`).

## Experiential Observations (from `.sos/land/workflow-patterns.md`)

Source: dionysus synthesis of 18 sessions (generated 2026-04-28, `confidence 0.75`, expired relative to this run). Experiential, not code-verified: (a) the 33-test "SCAR cluster" is recorded as an inviolable constraint of project-crucible (`workflow-patterns.md` line ~32) — consistent with, but narrower than, the current 46 `@pytest.mark.scar` sites (code wins); (b) test execution is a recurring session command pattern (sessions 20260315, 0324, 0326, 0329, 0409, 0415); (c) the 20260415 asana-test-rationalization session ran 7 eunomia agents — the prior-doc baselines "13,072→12,320 dedup / 87.59% coverage" originate there and were not re-measured (current static function count 15,973 exceeds both). Hotspot test files in that corpus (`tests/test_openapi_fuzz.py`, `tests/unit/dataframes/builders/test_cascade_validator.py`, `tests/unit/services/test_universal_strategy*.py`, `tests/unit/api/routes/test_resolver_status.py`) all still exist.
