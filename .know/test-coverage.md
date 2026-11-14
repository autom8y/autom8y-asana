---
domain: test-coverage
generated_at: "2026-11-14T18:10:41Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "gitidx-v1:5a15438a45d829aa10eb9e8b5c92b387fa17dfd228b999cba199073a9191b1e9"
source_commit: "584c8f79b5f7d0087a28a982a3ed4290cb98647d"
evidence_hash: "gitidx-v1:8a3fc15488f50892818d8bc70fccd524bf028906c1e7c8e4423991a3ad37e92b"
anchor_source: "stamp-pin"
stamp: {pin_id: "d55b30ac3e8e8159", pin_commit: "584c8f79b5f7d0087a28a982a3ed4290cb98647d", body_sha256: "649e3f845251a5ce129c64e4c1d87dfa42d85544727b4d17d8c024b937eb5037"}
confidence: 0.84
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@584c8f79"
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "9db9c6f33d48f5c2fce398de7d3359fef30a0a0bd809044f7259f792ee6c4b9e"
---

# Codebase Test Coverage

> Observed at `origin/main@584c8f79` (detached worktree, 2026-11-14). Covered: all 845 `tests/**/*.py` files (743 `test_*.py` modules, 67 `__init__.py`, 19 `conftest.py`, 16 helper or fixture modules), the 50 `mcp/**/*.py` files (25 `mcp/tests/test_*.py` plus `mcp/tests/conftest.py` and one canary), and the 628 `src/**/*.py` files (627 under `src/autom8_asana/`, 30 packages, 195,390 LOC, plus `src/autom8_query_cli.py`). Every number is static: an AST walk of the test files (test functions, `Test*` classes, decorators, literal parametrize lists, fixtures, `pytestmark`), a regex census over the file universe in the manifest, and an import-graph map from each `src` module to the tests that import it. The test suite, `uv`, `pip` and coverage tools were NOT run, so no measured coverage percentage exists in this document. Test language is Python (`pytest`, `pytest-asyncio` with `asyncio_mode = "auto"`, `pytest-xdist`, `pytest-split`, `pytest-timeout`).

## Coverage Gaps

### How to read the source-to-test map

Method (AST walk of 895 test files, 627 `src/autom8_asana` modules): a test "references" a module when it imports the module by dotted path, imports a name from it, or contains a string literal that starts with the module's dotted path (the `patch("autom8_asana.x.y.z")` form). Re-exports through a package `__init__` hide use (a test that imports `from autom8_asana.dataframes import X` counts for the package, not for the module that defines `X`), and routes are mostly exercised through `TestClient` against `create_app()`, not by importing the route module. So "zero importers" is a lower bound on coverage and an upper bound on risk, never a proof of either.

- 550 of 627 modules (87.7%) are imported by at least one test module. 77 are not (12.3%).
- 63 modules (10.0%, 9,674 LOC) have neither an import nor a string reference. 10 of them are `__init__.py` files; the rest are leaf helpers, model files or modules reached through a facade.
- Adding the filename heuristic (a `test_*.py` whose name contains the module stem) leaves **23 of 558 non-`__init__` modules (4.1%, 3,668 LOC) with no signal of any kind**. That is the hard gap list below.

Per-package map (modules, LOC, test modules importing any module of the package, mirrored test files under `tests/unit/<pkg>/`, test functions in that mirrored dir). Packages without a mirrored `tests/unit/<pkg>/` directory are marked "none":

| Package | Modules | LOC | Importing test files | Mirrored dir (files / functions) |
|---|---|---|---|---|
| `dataframes` | 66 | 21,562 | 118 | 77 / 1,437 |
| `automation` | 71 | 21,163 | 95 | 82 / 1,702 |
| `api` | 63 | 20,624 | 107 | 107 / 1,595 |
| `cache` | 55 | 17,513 | 123 | 67 / 1,382 |
| `models` | 61 | 16,889 | 185 | 46 / 1,487 |
| `services` | 35 | 14,824 | 110 | 38 / 936 |
| `clients` | 42 | 14,271 | 81 | 50 / 941 |
| `lambda_handlers` | 21 | 8,287 | 43 | 37 / 623 |
| `persistence` | 20 | 8,118 | 52 | 30 / 986 |
| `query` | 19 | 6,248 | 40 | 25 / 989 |
| `lifecycle` | 18 | 5,550 | 21 | 19 / 410 |
| `substrate` | 12 | 5,520 | 30 | 17 / 274 |
| root modules (`client.py`, `config.py`, `errors.py`, `settings.py`, `src/autom8_asana/entrypoint.py`, `storage_namespace.py`, `__init__.py`) | 7 | 4,869 | n/a | none (18 top-level files in `tests/unit/`) |
| `core` | 22 | 4,698 | 113 | 15 / 402 |
| `metrics` | 14 | 3,986 | 31 | 18 / 394 |
| `resolution` | 19 | 3,805 | 30 | 24 / 302 |
| `observability` | 16 | 3,187 | 9 | none (tests sit at the `tests/unit/` top level) |
| `transport` | 7 | 2,316 | 19 | 15 / 180 |
| `trigger` | 7 | 1,806 | 6 | 7 files (4 test modules) / 74 |
| `reconciliation` | 6 | 1,604 | 8 | 10 / 127 |
| `enrollment` | 3 | 1,170 | 3 | 4 / 69 |
| `auth` | 8 | 1,118 | 47 | 10 / 116 |
| `_defaults` | 5 | 1,016 | 18 | none |
| `protocols` | 9 | 918 | 10 | none |
| `search` | 3 | 914 | 4 | 4 / 51 |
| `normalizer` | 3 | 844 | 14 | 8 / 102 |
| `readout` | 4 | 790 | 2 | none (tests at `tests/unit/test_readout_generation.py` and the `test_rail_*.py` family) |
| `batch` | 3 | 672 | 27 | none (`tests/unit/test_batch_adversarial.py`, `tests/integration/test_batch_api.py`) |
| `domain` | 3 | 549 | 6 | 3 / 31 |
| `patterns` | 3 | 445 | 2 | 3 / 67 |
| `contracts` | 2 | 114 | 5 | 1 / 12 |

Five packages have no mirrored test directory: `observability`, `_defaults`, `protocols`, `readout`, `batch`. All five are reached by tests elsewhere (see the "Importing test files" column), so the gap is organizational, with these exceptions: `protocols` has four modules (`insights`, `item_loader`, `log`, `metrics` under `src/autom8_asana/protocols/`) that no test imports and no conformance suite checks, and `observability` has no direct importer for `correlation.py`, `decorators.py` or `src/autom8_asana/observability/rung_receipts/join.py` (which is named in `tests/unit/test_rung_receipts.py` only through its public names).

### The new `src/autom8_asana/trigger/` package and `tests/unit/trigger/`

`src/autom8_asana/trigger/` is new since the prior pass (D6 shadow receiver, registration half only; `src/autom8_asana/trigger/__init__.py` states it is DARK and that "nothing in production constructs these yet"). It has 7 files, 1,806 LOC: `src/autom8_asana/trigger/hook_environment.py` (149), `src/autom8_asana/trigger/hook_registry.py` (422), `src/autom8_asana/trigger/hook_store.py` (270), `src/autom8_asana/trigger/ports_webhooks.py` (184), `src/autom8_asana/trigger/registration.py` (664), `src/autom8_asana/trigger/watched_projects.py` (96) and `__init__.py` (docstring only, 21 LOC).

- Tests: `tests/unit/trigger/` holds 4 test modules (`test_hook_marker.py` 15 functions, `test_hook_registry.py` 17, `test_ports_webhooks.py` 7, `test_registration.py` 35; 74 functions, 90 after literal parametrize expansion, 28 of them `async`), plus `conftest.py` (11 fixtures) and `adapters.py` (test-only `InMemoryHookRegistry` and `InMemoryKeyHookStore`).
- Every trigger module is imported by at least 2 test files (static map). There are no dedicated test modules named for the store, the environment marker or the watched-projects map: `HookStore` and the marker logic are exercised through `tests/unit/trigger/test_hook_marker.py` (it builds the real `HookStore` with a client and an `environ` mapping at lines 118, 169, 219 and 234), and `watched_projects` through `test_registration.py` (`test_c1_project_list_is_asset_edit_and_offer_only`).
- The trigger tests use `moto.mock_aws` for the DynamoDB registry (`tests/unit/trigger/conftest.py:79`) and a `FakeAsana` double that backs the real SDK `WebhooksClient` (`tests/unit/trigger/conftest.py`, function `sdk_client_backed_by`), so the conditional-write expressions run for real.
- Structure is guarded by `tests/arch/` (below), not by the trigger tests: `tests/arch/test_import_contracts.py` (12 functions, 15 expanded), `tests/arch/test_trigger_adapter_placement.py` (11 / 21) and `tests/arch/test_trigger_asana_client_ast.py` (3 / 3).
- Not yet present: the receiver route, signature check, sweeper and decision engine. The pending import-linter contract `trigger-decide-readonly` (`pyproject.toml:344`) lists their future module names as sources. `MODULE_CONTRACTS` in `tests/arch/test_import_contracts.py:81-96` already names `ports_readonly`, `signature`, `liveness`, `decision`, `tag_registry`, `sweeper`, `resolver_adapter` and `autom8_asana.api.routes.asana_hook`; none of those files exists in the tree, and the suite is built to fail the moment one lands without being bound to a contract (docstring at the top of that file, "No vacuous pass").

### Hard gap list: 23 modules with no import, no string reference and no filename match (3,668 LOC)

Ordered by LOC (AST import map plus filename heuristic). For each, the "reached via" note says what a quick read of `src/` shows, so an agent can tell a true hole from a facade-covered file:

| LOC | Module | Reached via / risk |
|---|---|---|
| 362 | `src/autom8_asana/api/routes/identity_supply_models.py` | Pydantic models for the identity-supply route; route tests exist (`tests/unit/api/routes/test_identity_supply_route.py` names 1 of its 6 public classes) |
| 333 | `src/autom8_asana/clients/task_operations.py` | `TaskOperations`, imported lazily at `src/autom8_asana/clients/tasks.py:113`; no test names the module or class; reached only through tasks-client tests |
| 315 | `src/autom8_asana/models/business/mixins.py` | Business entity mixins; tests mention "mixins" only in docstrings (`tests/unit/models/business/test_business.py:323`) |
| 298 | `src/autom8_asana/clients/goal_relationships.py` | named only in `tests/unit/test_tier2_adversarial.py` |
| 280 | `src/autom8_asana/clients/data/_endpoints/simple.py` | data-service endpoint mixin, reached through `DataServiceClient` tests |
| 276 | `src/autom8_asana/dataframes/resolver/mock.py` | test double shipped in `src/`; `MockCustomFieldResolver` is imported via the package by `tests/unit/dataframes/test_cache_integration.py:25` |
| 211 | `src/autom8_asana/cache/integration/upgrader.py` | referenced once by name in `tests/unit/cache/test_reorg_imports.py` |
| 193 | `src/autom8_asana/clients/goal_followers.py` | named only in `tests/unit/test_tier2_adversarial.py` |
| 189 | `src/autom8_asana/automation/workflows/active_offer_enumeration.py` | one plain-text mention in `tests/unit/automation/workflows/test_onboarding_walkthrough.py` |
| 140 | `src/autom8_asana/cache/integration/schema_providers.py` | startup wiring; one mention in `tests/unit/api/test_lifespan_status_push_wiring.py` |
| 138 | `src/autom8_asana/dataframes/builders/post_build_validation.py` | lazy import at `src/autom8_asana/dataframes/builders/progressive.py:1169`; no test names it |
| 111 | `src/autom8_asana/observability/decorators.py` | instrumentation decorators |
| 107 | `src/autom8_asana/observability/correlation.py` | correlation-id helpers; `tests/unit/test_observability.py` names one of two public symbols |
| 106 | `src/autom8_asana/clients/task_ttl.py` | `TaskTTLResolver`, lazy import at `src/autom8_asana/clients/tasks.py:126`; TTL values are also cited in `src/autom8_asana/transport/budget_allocator.py` comments |
| 106 | `src/autom8_asana/api/routes/forwarding_stage_census_models.py` | response models; route tests exist |
| 104 | `src/autom8_asana/entrypoint.py` | process entry module; no test imports or names it |
| 104 | `src/autom8_asana/api/error_responses.py` | HTTP error shaping; named only by the fuzz suite `tests/test_openapi_fuzz.py` |
| 96 | `src/autom8_asana/protocols/item_loader.py` | Protocol with no conformance test |
| 70 | `src/autom8_asana/services/wire/receipts_models.py` | wire models |
| 50 | `src/autom8_asana/api/routes/_security.py` | `pat_router`/`s2s_router` factories; covered structurally by `tests/unit/api/test_secure_router_adoption.py` (AST walk of routes) |
| 32 | `src/autom8_asana/core/string_utils.py` | utility |
| 31 | `src/autom8_asana/core/datetime_utils.py` | utility |
| 16 | `src/autom8_asana/api/preload/constants.py` | constants |

Highest value per effort (INFERRED from LOC, exposure and the write or boot path they sit on): `src/autom8_asana/clients/task_operations.py` (333 LOC on the task-write client path), `src/autom8_asana/dataframes/builders/post_build_validation.py` (validation on the progressive build path), `src/autom8_asana/clients/task_ttl.py` (cache TTL policy for tasks), `src/autom8_asana/entrypoint.py` and `src/autom8_asana/api/error_responses.py` (process entry and error envelope).

### Zero-direct-importer modules that DO have name-matched or facade tests (do not mislabel these as untested)

- `src/autom8_asana/persistence/actions.py` (731 LOC, defines `ActionBuilder` at line 488): imported only by `src/autom8_asana/persistence/session.py:18`. No test imports it; `ActionBuilder` appears only in comments of `tests/unit/persistence/test_session_concurrency.py` (lines 614 and 631). Its generated `SaveSession` methods are exercised by the session tests (10 test files whose names contain `session`, 265 expanded tests). Gap: no test targets the builder's variant table in isolation.
- `src/autom8_asana/dataframes/cache_integration.py` (657 LOC): re-exported by `src/autom8_asana/dataframes/__init__.py:36`; `tests/unit/dataframes/test_cache_integration.py` imports through the package.
- `src/autom8_asana/observability/prometheus_metrics.py` (857 LOC, zero importers): patched by string in `tests/unit/api/test_receiver_sli_emf_export.py:202` and `:214` and in `tests/unit/cache/dataframe/test_dataframe_cache.py` (e.g. line 1532). Recording functions (`record_cache_op`, `record_api_call`, `record_receiver_query_outcome`, ...) are mostly patched, not asserted on.
- `src/autom8_asana/services/receipts_service.py` (469 LOC): string patches at `tests/unit/api/routes/test_receipts.py:553` and `:572`; route-mediated.
- `src/autom8_asana/api/startup.py` (133 LOC, four helper functions): reached through `src/autom8_asana/api/lifespan.py:24` and patched at `autom8_asana.api.lifespan._discover_entity_projects` by many tests (for example `tests/integration/test_composite_verification.py:109`).

### Thin by static signal (imported by exactly one test module with 15 or fewer functions)

(INFERRED; route modules are really exercised through `TestClient`, so treat as "verify before trusting".) `src/autom8_asana/services/discovery.py` (291 LOC, 2 tests), `src/autom8_asana/cache/durable_task_cache.py` (336 LOC, 3 tests, see below), `src/autom8_asana/api/routes/resolver.py` (503 LOC; also reached by 13 name-matched resolver test files, 336 functions), `src/autom8_asana/dataframes/contracts/field_contract_maps.py` (425, 7), `src/autom8_asana/persistence/cache_invalidator.py` (286, 9), `src/autom8_asana/automation/forwarding_stage_backfill/cli.py` (256, 11), `src/autom8_asana/api/routes/workflows.py` (472, 11), `src/autom8_asana/api/routes/sections.py` (359), `src/autom8_asana/api/routes/projects.py` (551), `src/autom8_asana/api/preload/legacy.py` (625, 13), `src/autom8_asana/resolution/strategies.py` (393, 14), `src/autom8_asana/observability/rail_delivery/distinguishability.py` (371, 15; has its own `tests/unit/test_rail_distinguishability.py`).

`src/autom8_asana/cache/durable_task_cache.py` (336 LOC, `DurableTaskCacheReader` at line 126): the only importer is `tests/unit/cache/test_durable_task_cache_live_smoke.py`, whose three tests read a real object store and are skip-gated on a real cache-bucket env var plus AWS credentials (module docstring). Two other test files name the reader (`tests/unit/dataframes/builders/test_cure_recovery_fail_closed.py`, `tests/unit/dataframes/test_concurrency_invariants_guard.py`). There is no hermetic unit module for the reader's own read, envelope-unwrap and `.gz` fallback logic; the nightly workflow is its only direct exercise (`.github/workflows/nightly-live-smoke.yml`).

### Critical paths: what is covered and by what

| Critical path | Evidence of coverage | Residual gap |
|---|---|---|
| Write authorization (deny-by-default allowlists) | `tests/unit/api/test_write_authz.py` (50 functions); `tests/unit/api/test_write_authz_coverage.py` derives the write surface from the `x-fleet-side-effects` declaration and fails if a declared write route lacks the dependency, plus an AST ban on the `has_scope`/`require_scope` family in `src/` | The guard trusts the declaration: a route that writes without declaring a side effect is invisible to it (stated in the file's own docstring as UV-P-S14-1). The root conftest authorizes three test principals for every write class (`tests/conftest.py:256-262`), so route tests run in the real ENFORCE posture |
| SecureRouter adoption on business routes | `tests/unit/api/test_secure_router_adoption.py` (AST walk with a closed-world exemption allowlist) | Allowlist is manual |
| Rate limiting (verified-identity buckets) | New since the prior pass: `tests/unit/api/test_rate_limit_verified_key.py` (11, drives the real middleware stack with signed JWTs), `test_limiter_hardening.py` (3), `test_limiter_config_file.py` (4), `test_health_limiter_exempt.py` (8) | `src/autom8_asana/api/rate_limit.py` is 404 LOC; 5 test files import it (69 tests, 43 of them in `test_receiver_bulk_fanout_reliability_stage1.py`) |
| Idempotency middleware | `tests/unit/api/middleware/` (4 files named for it: contracts 39, dynamo 21, finalize scar 9, store default 3), `tests/integration/test_composite_verification.py` | `test_idempotency_store_default.py` has 3 tests for the store-default switch |
| Webhooks route | `tests/unit/api/routes/test_webhooks.py` (78), `tests/integration/api/test_envelope_convergence.py` | no test of the inbound D6 receiver (not built yet) |
| Persistence / SaveSession | 30 files and 986 functions in `tests/unit/persistence/`, plus `tests/validation/persistence/` (5 files, 121 functions: concurrency, ordering, errors, functional, performance) and `tests/integration/test_savesession_*.py` | `actions.py` builder not tested in isolation (above) |
| Lifecycle engine | 19 files, 410 functions; engine alone is named by 6 test files (164 functions); `tests/integration/test_lifecycle_smoke.py` (78 functions, `integration`-marked, so outside the PR lane) | unit tests drive the engine against mocks (fixtures in `tests/unit/lifecycle/conftest.py`: `mock_client`, `mock_process`, `mock_business`, ...); the only integration-tier run is gated by the `integration` marker |
| Lambda handlers | 21 handlers; 37 test files, 623 functions. `src/autom8_asana/lambda_handlers/story_warmer.py` (497 LOC) has no test file named for it; 2 files import it (`tests/unit/lambda_handlers/test_story_warm_priority_offer.py` 20 functions, `test_story_warming.py` 10). `src/autom8_asana/lambda_handlers/cache_warmer.py` (1,498 LOC) has 5 test files (78 functions) | `cache_warmer.py` and `traffic_offer_divergence_tripwire.py` (1,176 LOC, 1 named file, 33 functions) are the largest handlers with the lowest density |
| Auth (JWT, bot PAT, per-business token) | `tests/unit/auth/` 10 files, 116 functions; `tests/contracts/test_contract_auth.py` (9) | `src/autom8_asana/auth/service_token.py` is imported by no auth test (it is reached through handler tests, e.g. `tests/unit/lambda_handlers/test_workflow_handler_auth_injection.py`) |
| Cache (tiers, warmer, invalidation) | 67 files, 1,382 functions; `tests/integration/cache/` (2 warmer-preserve files) | `durable_task_cache.py` (above) |
| Dataframe build / cascade | 77 files, 1,437 functions; scar guards for warmup ordering, L2 gate and freshness recency (`@pytest.mark.scar`; 46 test functions across those 3 files) | builder `base.py` (840 LOC) is imported by only one test module (9 functions); other builder tests reach it through subclasses |
| Query / metrics | `tests/unit/query/` 989 functions; `tests/unit/metrics/` 394; SCAR-METRICS-SELECT-FILTER-001 now has a regression file (see Knowledge Gaps, corrections) | `src/autom8_asana/query/__main__.py` (1,724 LOC) and `src/autom8_asana/metrics/__main__.py` (1,086 LOC) have no test file named for them (3 and 4 importing test files) |
| Substrate (cutover gate) | `tests/unit/substrate/` 17 files, 274 functions; `tests/harness/substrate_gate/` 8 test modules, 88 functions, parquet fixture | `src/autom8_asana/substrate/live.py` (1,336 LOC) is imported by 4 test files (83 functions); `src/autom8_asana/substrate/parity_run.py` (490) by 1 file (16) |
| Import and layer boundaries | `tests/arch/` (5 modules, 46 functions); `.semgrep.yml` run in CI by `semgrep-layer-rules.yml` | `trigger-decide-readonly` contract is pending (no sources yet) |

### Negative-path and blind-spot assessment

- `pytest.raises` appears 1,792 times in 331 of 845 test files (AST and regex census). No `pytest.warns` anywhere. Adversarial or edge-named test files: 18 `*adversarial*`, 8 `*edge_cases*`, 5 `*qa*`, 6 `*concurrency*`, 9 `*guard*`.
- Packages with no dedicated negative-test directory because they have no mirrored dir: `observability`, `protocols`, `_defaults`, `readout`, `batch`.
- `@pytest.mark.scar` is applied at decorator level 46 times in 17 files (the 17th, `tests/unit/knowledge/register_drift_checks.py`, is a helper), but class-level and module-level marks widen the effective set: an AST walk with mark inheritance finds **87 test functions in 16 files** selected by `pytest -m scar`. Largest: `tests/unit/dataframes/test_freshness_verification_recency.py` (17), `test_l2_gate_frameless_provider.py` (15), `test_warmup_ordering_guard.py` (14). The new regression file for the metrics scar, `tests/unit/metrics/test_compute_filter_columns.py`, carries no `scar` marker.
- Resolved-scar prose guard: `tests/unit/knowledge/register_drift_checks.py:36` `RESOLVED_SCAR_IDS = frozenset({"SCAR-REG-001", "SCAR-IDEM-001"})`; the guard covers 2 IDs and new resolutions must be appended by hand (comment at the same file).
- The `test_adversarial.py` docstring at `tests/unit/metrics/test_adversarial.py:270` still says pre_filters can only reference columns that `compute_metric` selects. That is stale since the select-filter fix (`src/autom8_asana/metrics/compute.py:98-127`).
- Schemathesis/OpenAPI fuzz: `tests/test_openapi_fuzz.py` carries `KNOWN_VIOLATIONS` with 56 entries (45 "violation", 10 "conforming-pinned", 1 other), applied as non-strict xfail. The fuzz job is non-blocking.

### Coverage measurement infrastructure

- `pyproject.toml:135-147`: `[tool.coverage.run] source = ["src/autom8_asana"]`, `branch = true`; `[tool.coverage.report] fail_under = 80`; `exclude_lines` = `pragma: no cover`, `if TYPE_CHECKING:`, `@abstractmethod`, `raise NotImplementedError`, `if __name__ == .__main__.:`.
- PR and push gate (`.github/workflows/test.yml:104-153`, job `ci`, reusable workflow pinned to a commit SHA): `coverage_threshold: 0` per shard (line 122) and `coverage_threshold_aggregate: 80` (line 125). What the reusable workflow does with the aggregate value cannot be seen from this repo (see Knowledge Gaps).
- The only place in-repo where the 80 floor is enforced by a command: `.github/workflows/post-merge-coverage.yml:89-95` (`pytest --cov=src/autom8_asana --cov-report=term-missing --cov-report=xml --cov-fail-under=80 -m "not integration and not benchmark and not fuzz" tests/`), single shard, push to `main` plus `workflow_dispatch`. It is a separate workflow from `Test`. The deploy trigger (`.github/workflows/satellite-dispatch.yml:12-15` and `:36-44`) keys only on a successful push-to-main run of the workflow named `Test`, so a post-merge coverage failure does not stop a deploy. Its header comments cite `pyproject.toml:127` and `.github/workflows/test.yml:52`/`:56`, which are stale (`fail_under` is at `pyproject.toml:140`; the per-shard threshold is at `.github/workflows/test.yml:122`; the marker expression is at `.github/workflows/test.yml:137`).
- No coverage percentage is stored in the repo (no `.coveragerc` among the tracked files, no committed coverage report); the `just test-cov` recipe (`justfile:107`) is local only.
- `mcp/` has its own gate (below) but is outside the coverage source and outside `mypy_targets: 'src/autom8_asana'` (`.github/workflows/test.yml:117`).

### Prioritized gap list

1. Run the three omitted `worker_isolated` modules in a gate. `worker_isolated` is a module-level `pytestmark` in 4 files; the sharded gate excludes them (`.github/workflows/test.yml:137`) and the `workflow-handler-isolated` job runs only `tests/unit/lambda_handlers/test_workflow_handler.py` (`.github/workflows/test.yml:400-402`). `test_workflow_handler_auth_injection.py` (mark at line 50), `test_workflow_handler_dataframe_cache_init.py` (58) and `test_workflow_handler_workspace_gid.py` (54) run only in `.github/workflows/post-merge-coverage.yml`, which does not gate deploy.
2. A hermetic unit module for `src/autom8_asana/cache/durable_task_cache.py` (the only direct test is a skip-gated live smoke).
3. Direct tests for `src/autom8_asana/clients/task_operations.py`, `src/autom8_asana/clients/task_ttl.py` and `src/autom8_asana/dataframes/builders/post_build_validation.py` (zero signal).
4. Add `@pytest.mark.scar` to `tests/unit/metrics/test_compute_filter_columns.py`; extend `RESOLVED_SCAR_IDS`.
5. A conformance test for the four `src/autom8_asana/protocols/` modules with no importer, and for `src/autom8_asana/observability/correlation.py` and `decorators.py`.
6. `src/autom8_asana/entrypoint.py` and `src/autom8_asana/api/error_responses.py`: no import-path test; confirm indirect coverage through the container smoke or add one.
7. Triage the 56 schemathesis known-violation entries; the lane is advisory only.
8. Isolated tests for `src/autom8_asana/persistence/actions.py` `ActionBuilder` variants.

## Testing Conventions

### Invocation and runner configuration

- `pyproject.toml:118-125`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `timeout = 60`, `timeout_method = "thread"`, `addopts = "--dist=loadgroup"` (activates `xdist_group` markers; rationale is at `tests/unit/lambda_handlers/test_workflow_handler.py:25-46` and `tests/test_openapi_fuzz.py:64-72`). No `python_files`, `python_classes` or `python_functions` override exists, so pytest defaults apply: only `test_*.py` and `*_test.py` are collected (0 files use the `*_test.py` form) and only `Test*` classes. Consequence: `tests/benchmarks/bench_batch_operations.py` and `bench_cache_operations.py` are standalone scripts with a `main()` and `benchmark_*` functions that pytest never collects.
- Dev dependencies (`pyproject.toml:86-110`): `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `pytest-timeout`, `pytest-xdist`, `pytest-split`, `respx`, `fakeredis`, `moto`, the `autom8y-*[testing]` SDK test subpackages, `openapi-spec-validator` and `import-linter`. `hypothesis` and `schemathesis` (`<4.15.0`) are pinned in a later dependency block (`pyproject.toml:559` and `:565`).
- `justfile:98-151` recipes: `test` (`uv run pytest`), `test-cov` (HTML + term report), `test-fast` (`-m "not slow and not integration and not benchmark"`), `test-slow`, `test-integration` (comment says it needs a live Asana token), `test-bench`, a fitness recipe that runs `tests/unit/dataframes/test_concurrency_invariants_guard.py` with `-p no:xdist -o addopts=""`, and `test-mcp` (mcp suite plus canary).
- Ruff for tests (`pyproject.toml:446-462`, `"tests/**/*.py"`): relaxed rules (`F841`, `E402`, `F821`, `F401`, `B015`, `B017`, `B023`, `TID251`, `SIM117`, `SIM102`, `T201`, the whole `S` family). `mypy_targets` in CI covers `src/autom8_asana` only, so tests are not type-checked; even so, 15,119 of 16,215 test functions (93.2%) carry a `-> None` return annotation (AST walk).

### Naming and structure

- Files are `test_<topic>.py`; the topic is descriptive, often a feature or a spec identifier, not a mirror of the module name. 743 test modules. Suffix families seen (counts of filenames): `adversarial` 18, `contract` 17, `integration` 15, `guard` 9, `edge_cases` 8, `parity` 7, `concurrency` 6, `smoke` 5, `qa` 5, `e2e` 4, `canary` 4.
- Class-based dominates: AST walk of `tests/` finds 14,760 test methods inside `Test*` classes against 1,455 module-level `def test_*` (91.0% / 9.0%); 3,656 `Test*` classes. `unittest.TestCase` appears in 0 files. Function-style modules are concentrated in `tests/unit/substrate/` (274 functions, 0 classes), `tests/arch/`, `tests/unit/trigger/`, `tests/harness/` and `mcp/tests/` (0 classes).
- 4,531 of the test functions are `async def` (28% of all); no `@pytest.mark.asyncio` is required because of `asyncio_mode = "auto"`, yet 226 explicit `asyncio` marks remain (redundant but harmless).
- Docstrings: 13,478 of 16,215 test functions (83.1%) have one; the house style is a docstring that names the requirement, spec or scar ID the test pins (for example `tests/unit/api/test_rate_limit_verified_key.py` opens with a policy list; `tests/unit/trigger/conftest.py` states that all identifiers are generated at runtime).
- 67 `__init__.py` make most test directories packages, so cross-test imports use `from tests.<path> import ...` (59 files import from `tests.unit`, 23 from `tests._shared`, 18 from `tests.harness`; for example `tests/unit/knowledge/test_register_drift_guard.py` imports its detector from `tests.unit.knowledge.register_drift_checks`).
- Subtests: pytest-native only. `parametrize` is the idiom (301 decorator sites by AST, 70 with a non-literal argument list; 304 regex sites in 128 files). Expanded static count 17,176 test items for `tests/` after expanding literal lists. `pytest.param` appears 200 times in 25 files and `ids=` 308 times in 67 files.

### Assertions, doubles and helpers (regex census over 845 test files)

| Idiom | Files | Occurrences |
|---|---|---|
| Bare `assert` (AST `Assert` nodes) | n/a | 32,174 |
| `pytest.raises` | 331 | 1,792 |
| `pytest.approx` | 30 | 107 |
| `MagicMock` | 369 | 5,672 |
| `AsyncMock` | 289 | 4,236 |
| `patch(` / `patch.object(` / `patch.dict(` | 259 | 3,138 |
| `spec=` / `create_autospec` / `spec_set` | 44 | 188 |
| `monkeypatch` | 94 | 1,303 |
| `tmp_path` | 31 | 793 |
| `respx` (httpx mocking) | 18 | 369 |
| `moto` `mock_aws` | 12 | 62 |
| `fakeredis` | 1 | 10 |
| `TestClient` (FastAPI) | 60 | 800 |
| `capsys` / `capfd` | 18 | 280 |
| `caplog` | 12 | 28 |
| `MockLogger` (`autom8y_log.testing`) | 10 | 42 |
| `pytest.skip(` | 19 | 35 |
| `pytest.importorskip` | 2 | 3 |
| `freezegun` / `time-machine` | 0 | 0 |
| `hypothesis` (`@given`) | 2 | 9 |
| `mocker` (pytest-mock) | 2 | 27 |

- Logging is asserted through a spy or `MockLogger`, not `caplog`: the autom8y logger bypasses `caplog`, and `tests/unit/trigger/conftest.py` defines `LogSpy` for that reason (its docstring says "autom8y_log bypasses caplog").
- Time is controlled with injected clocks (`FakeClock` in `tests/unit/trigger/conftest.py`) or `unittest.mock` patches of `datetime` (`tests/unit/api/routes/test_receipts.py:553`), not with a time-freezing library.
- Property testing is nearly absent: one `@given` in `tests/unit/persistence/test_reorder.py:274`; `hypothesis` otherwise appears in `tests/test_openapi_fuzz.py` (profile registered at line 145, `SCHEMATHESIS_MAX_EXAMPLES` read at line 143).
- Network-free by construction: `respx` for the Asana and data-service HTTP legs, `moto` for AWS, and `MagicMock`/`AsyncMock` of `AsanaHttpClient` and clients. The root fixtures `mock_http`, `config`, `auth_provider` and `logger` live in `tests/conftest.py` (lines 109-128).

### Skip, xfail and environment gating

- `skipif` appears at 49 regex sites (19 `not MOTO_AVAILABLE` plus 4 variants, 3 `not ASANA_PAT`, 16 with a multi-line condition, singletons for `sys.platform`, `os.geteuid() == 0`, `MYPY_AVAILABLE`, `JSONSCHEMA_AVAILABLE`, `FAKEREDIS_AVAILABLE`). Plain `skip` 11 AST sites; `xfail` 3 sites plus the runtime xfails from `KNOWN_VIOLATIONS`.
- Dependency-presence skips (`MOTO_AVAILABLE`) are safe in CI because `moto` is a dev dependency; the live-API ones skip silently without a token, which is why the nightly workflow adds an "assert smokes RAN" step (`.github/workflows/nightly-live-smoke.yml`, step "Assert smokes RAN (anti-theater forcing function)").
- `mcp/tests/test_schema_canary.py` skips when the native models are not present (lines 29 and 41) and `mcp/tests/test_seam_conformance.py:62` uses `importorskip("fastmcp")`.

### Fixtures and test data

- 817 `@pytest.fixture`/`@pytest_asyncio.fixture` in 277 test files (AST), 10 more under `mcp/`. Scope mix: 28 `module`, 3 `session`, the rest function-scoped.
- Root `tests/conftest.py` (262 lines): `pytest_configure` patches a schemathesis/xdist incompatibility on the class before plugin registration (line 36); `os.environ["AUTOM8Y_ENV"] = "test"` is force-set, not defaulted (line 60); `AUTH__JWKS_URL` is defaulted (line 66); the module raises `RuntimeError` at import if any binding `ASANA_CACHE_*` env knob leaks into the test environment (lines 81-83); `_bootstrap_session` (session, autouse, line 138) runs `bootstrap()` and rebuilds Pydantic forward references for the resource models; `reset_all_singletons` (autouse, line 205) calls `SystemContext.reset_all()` before and after every test; `_write_authz_test_allowlists` (autouse, line 256) authorizes three test principals for every write class so route tests run in the production ENFORCE posture.
- 19 `conftest.py` layers. Notable: `tests/unit/api/conftest.py` (388 lines; module-scoped `app` fixture that builds `create_app()` with auth dev mode on and a patched entity-discovery step, a default `get_auth_context` override, an autouse `reset_singletons` that clears bot-PAT, auth-client and readiness caches and repopulates the entity-project registry, a module-scoped `TestClient` aliased by `client`, plus `mock_*_client` and `authed_client`); `tests/unit/trigger/conftest.py` (`registry`, `store`, `fake_asana`, `port`, `registrar`, `clock`, `LogSpy`, runtime-generated gids and hook values via `secrets`); `tests/unit/lifecycle/conftest.py` and `tests/unit/resolution/conftest.py` (mock business-model graph: `mock_business`, `mock_unit`, `mock_offer`, `mock_contact`, `mock_process`); `tests/unit/reconciliation/conftest.py` (`make_unit_df`, `make_offer_df`); `tests/unit/automation/polling/conftest.py` (YAML-config fixtures, 27 fixtures); `tests/synthetic/conftest.py` (691 lines; module-scoped autouse memory guard and coverage summary for the Aegis harness).
- Shared helpers: `tests/_shared/mocks.py` (`MockTask`), `tests/_shared/factories.py` (`make_task_dict`), `tests/_shared/cf_write_readback.py` (`real_tasks_client`, `captured_put_body`, `apply_write_body`, `read_custom_field`). Dominant data style is inline `make_*`/`create_*`/`build_*` helper functions per module.
- File fixtures: `tests/fixtures/scheduling_posture_golden_entries.json`; `tests/fixtures/rung_receipts/*.jsonl` with two `PROVENANCE` notes; `tests/fixtures/readout/rows_response_item1a*.json` with `PROVENANCE.md`; `tests/unit/knowledge/fixtures/drift/` (10 files in `*.green.*` / `*.stale.*` pairs); `tests/harness/substrate_gate/fixtures/` (a captured parquet frame plus watermark JSON). Captured fixtures carry a provenance note by convention. `Path(__file__)` is used in 44 files to locate fixtures and docs; `docs/api-reference/openapi.json` is read by `tests/synthetic/test_synthetic_coverage.py` (constant `SPEC_PATH`).
- Hermeticity: no committed secrets; test GIDs and hook values are synthetic or runtime-generated (for example `runtime_gid()` and `runtime_hook_value()` in `tests/unit/trigger/conftest.py`).

### Marker catalog (`pyproject.toml:126-133`)

| Marker | Where applied (AST plus regex) | Effect in CI |
|---|---|---|
| `slow` | 24 sites in 15 files (`tests/unit/clients/data/test_insights.py` 4, `tests/unit/cache/test_memory_backend.py` 3, ...) | excluded on PRs only (`.github/workflows/test.yml:137`) |
| `integration` | 49 sites in 12 files; 10 of the 12 are test modules under `tests/integration/` (199 functions; an eleventh is `tests/integration/automation/polling/__init__.py`); the twelfth is `tests/unit/automation/workflows/test_onboarding_walkthrough.py` | excluded from sharded runs; `run_integration` is true on push events only (`.github/workflows/test.yml:138`) |
| `benchmark` | 1 file, `tests/benchmarks/test_insights_benchmark.py` (3 classes) | excluded everywhere in CI |
| `fuzz` | 1 file, `tests/test_openapi_fuzz.py` (module `pytestmark`) | excluded from the sharded runs; run by the non-blocking `fuzz` job |
| `scar` | 46 decorator sites, 87 effective test functions in 16 files | not excluded anywhere; runs in every lane; select with `pytest -m scar` |
| `worker_isolated` | 4 files, module-level `pytestmark` | excluded from sharded runs; see gap 1 |
| `xdist_group` (not declared as a marker) | 35 files, 40 sites, 6 groups: `scheduling_normalizer` 13, `gfr_resolver` 12, `query_routes` 4, `workflow_handler` 4, `fuzz` 2, `gfr_drift_gate` 1 | co-locates a group on one worker under `--dist=loadgroup` |
| `parametrize` | 301 (AST) | n/a |
| `asyncio` | 226 explicit | redundant under auto mode |

Marker semantics to know before adding tests: the `integration` marker's declared meaning is "requires live API access", but only 10 of the 38 files with tests under `tests/integration/` carry it. The other 28 files (421 functions, 68% of that directory's functions) are mock-wired and DO run in the PR lane. Directory name is not the tier selector, the marker is.

### Fitness, canary and "teeth" test idioms

- Two-sided teeth (a broken input must go RED, the clean twin GREEN): `tests/arch/test_namespace_contract.py` (storage-namespace contract tests t1-t5, each paired with a deliberately broken fixture), `tests/arch/test_namespace_gen.py` (regenerates the namespace JSON from the Python registry and asserts byte equality), `tests/arch/test_import_contracts.py` (plants forbidden imports in a synthetic package), `tests/unit/knowledge/test_register_drift_guard.py` (green and stale fixture pairs), `tests/harness/substrate_gate/test_self_discrimination.py`, `mcp/canary/test_broken_fixture_canary.py` (exit code 1 is the GREEN receipt).
- Source-text and AST guards: `tests/unit/dataframes/test_concurrency_invariants_guard.py` (four frozen concurrency invariants), `tests/unit/dataframes/test_warmup_ordering_guard.py`, `tests/unit/test_swap_detector_closure.py`, `tests/unit/api/test_secure_router_adoption.py`, `tests/unit/api/test_write_authz_coverage.py`, `tests/arch/test_trigger_asana_client_ast.py`.
- Deploy-gate canary logic is unit-tested by loading a script by file path: `tests/unit/canary/test_deploy_gate_content_binding.py` imports the canary module with `importlib` because it lives under `scripts/canary/`, which is not a package.
- Docstring receipts: guard tests cite `file:line` of the code they pin (for example the concurrency guard docstring cites `src/autom8_asana/settings.py` ranges). Line citations in test docstrings drift with edits.

## Test Structure Summary

### Distribution (AST walk, `tests/` 845 files plus `mcp/` 50 files)

```
tests/                                  743 test_*.py   16,202 test functions (17,176 after literal parametrize)
  conftest.py, _shared/{mocks,factories,cf_write_readback}.py
  test_openapi_endpoint.py, test_openapi_fuzz.py, test_computation_spans.py   (3 top-level test modules)
  unit/           757 files              # tests per mirrored package dir (functions):
                                         #   automation 1,702 · api 1,595 · models 1,487 · dataframes 1,437 ·
                                         #   cache 1,382 · query 989 · persistence 986 · clients 941 ·
                                         #   services 936 · lambda_handlers 623 · unit top level 535 ·
                                         #   lifecycle 410 · core 402 · metrics 394 · resolution 302 ·
                                         #   substrate 274 · transport 180 · reconciliation 127 · auth 116 ·
                                         #   normalizer 102 · trigger 74 · enrollment 69 · patterns 67 ·
                                         #   search 51 · domain 31 · canary 28 · detection 28 ·
                                         #   contracts 12 · knowledge 9 · packaging 3
  integration/     47 files, 620 functions   # api 2 · automation (polling, workflows) · cache 2 · events 1 · persistence 1 · 28 flat
  validation/      8 files, 121 functions    # persistence only
  harness/         19 .py files, 88 functions # substrate_gate: 8 test modules + 9 support modules + 2 __init__
  arch/            6 files, 46 functions     # 5 test modules
  contracts/       2 files, 9 functions
  synthetic/       3 files, 1 function       # one parametrized test over every OpenAPI operation (non-literal ids)
  benchmarks/      4 files, 8 functions      # 1 collectable module; 2 standalone bench scripts
mcp/tests/        25 test modules + conftest (165 functions) · mcp/canary/ 1 module (2 functions) · mcp/probes/ (not a test)
```

- 743 test modules hold tests; 102 other files in `tests/` are 67 `__init__.py`, 19 `conftest.py` and 16 helper or fixture modules (for example `tests/unit/trigger/adapters.py`, `tests/unit/knowledge/register_drift_checks.py`, the nine `substrate_gate` support modules).
- Most heavily tested by function count: `automation`, `api`, `models`, `dataframes`, `cache` (each above 1,350 functions). Highest density (functions per 1,000 LOC of mirrored source): `query` 158, `normalizer` 121, `persistence` 122, `patterns` 151, `metrics` 99, `auth` 104. Lowest nonzero: `trigger` 41, `substrate` 50, `enrollment` 59, `search` 56, `domain` 57, `services` 63.
- Unit versus integration: 757 of 845 files under `tests/unit/`; 47 under `tests/integration/` (620 of 16,202 functions, 3.8%). The directory is not the selector: see the marker semantics above.
- Package naming: Python tests are import-based; there is no `package foo_test` convention. `tests` is itself an importable package (67 `__init__.py`), and source modules are imported as `autom8_asana.<pkg>.<mod>`.
- There is no `TestMain`-style entry. The global equivalent is root `tests/conftest.py` (`pytest_configure`, session-autouse `_bootstrap_session`, function-autouse `reset_all_singletons`, `_write_authz_test_allowlists`).
- `pytest` is configured only in `pyproject.toml`; no `pytest.ini`, `tox.ini` or `noxfile.py` is tracked.

### Tiers and how each is selected

| Tier | Where | Selected by | Runs in |
|---|---|---|---|
| Unit | `tests/unit/**` | default collection (`testpaths = ["tests"]`) | PR and push sharded gate |
| Integration (mock-wired) | `tests/integration/**` unmarked files (28 files, 421 functions) | default collection | PR and push sharded gate |
| Integration (marker) | 10 files in `tests/integration/` plus one unit file | `-m integration` (excluded by default expression) | push events via `run_integration` (reusable workflow, content not in repo) |
| Validation | `tests/validation/persistence/` (one test marked `slow`) | default collection | sharded gate (PR lane drops `slow`) |
| Contract | `tests/contracts/test_contract_auth.py`; `tests/unit/contracts/test_vocabulary_sync_models.py` | default collection | sharded gate |
| Arch | `tests/arch/` | default collection; spawns `lint-imports` subprocess for the import-linter contracts (`tests/arch/test_import_contracts.py`); fails, never skips, if import-linter is absent | sharded gate |
| Canary | `tests/unit/canary/` (3 modules, 28 functions), `mcp/canary/` | default collection (unit); explicit path for `mcp/canary` with exit-code polarity | unit: sharded gate; mcp canary: `mcp-island` job |
| Smoke (live) | `tests/unit/cache/test_durable_task_cache_live_smoke.py`, `tests/unit/dataframes/builders/test_null_number_recovery_live_smoke.py` | skip-gated on env and credentials; invoked by path | nightly workflow; skipped (silently) elsewhere |
| Scar | marker `scar`, 87 functions in 16 files | `-m scar` | every lane (no exclusion) |
| Fuzz | `tests/test_openapi_fuzz.py` | `-m fuzz` / by path | non-blocking `fuzz` job |
| Benchmark | `tests/benchmarks/test_insights_benchmark.py` | `-m benchmark` | never in CI |
| Synthetic (Aegis) | `tests/synthetic/test_synthetic_coverage.py` | default collection, or by path | `aegis-synthetic-coverage.yml` plus the sharded gate |
| Harness | `tests/harness/substrate_gate/` | default collection | sharded gate |
| Worker-isolated | 4 `lambda_handlers` modules | `-m worker_isolated` | non-blocking isolated job (1 of the 4 files); post-merge coverage (all 4) |
| mcp island | `mcp/tests/` | its own `mcp/pyproject.toml` (`pythonpath`, `asyncio_mode = "auto"`, `testpaths = ["tests"]`) | `mcp-island` job; root pytest never collects it |

### `tests/harness` and its use from `src/`

`tests/harness/substrate_gate/` is the substrate-v2 cutover-gate parity harness: `budget.py`, `cases.py`, `corpus.py`, `divergence.py`, `exemplars.py`, `frame_codec.py`, `parity.py`, `reference.py`, `replay.py` plus 8 `test_*.py` modules (`test_self_discrimination.py` proves the runner discriminates both ways; `test_parity_dark_guard.py`; `test_replay_runner.py`; `test_budget.py`; `test_corpus_scaffold.py`; `test_exemplar_two_drift.py`; `test_parity_aimd_signal.py`; `test_parity_exemplar_one.py`) and a captured parquet fixture under `tests/harness/substrate_gate/fixtures/`.

`src/` imports from `tests.harness` at 12 import statements in 2 files: `src/autom8_asana/substrate/live.py` (3 under `TYPE_CHECKING` at lines 104-106 and 8 function-local runtime imports at lines 389, 641, 739, 1105, 1111, 1239, 1264, 1307) and `src/autom8_asana/substrate/parity_run.py:340`. The module docstring of `live.py` (lines 5-10) says the tool is deliberately kept out of `src/autom8_asana/substrate/__init__.py`, is never imported by deployed code, and "runs from the repo tree (where the harness is importable)". Guards that make this safe: `.dockerignore:62` excludes `tests/` from the image, the wheel packages are only `src/autom8_asana` and `src/autom8_query_cli.py` (`pyproject.toml:116`), and `mypy` treats `tests.harness.substrate_gate.*` with `follow_imports = "silent"` (`pyproject.toml:218-220`). Consequence for an agent: do not move or rename `tests/harness/substrate_gate/` modules without updating those `src` imports, and do not import `substrate.live` from deployed code. `tests/unit/substrate/test_live.py` (37 functions) and `test_parity_run.py` (16) test the `src` side with fakes.

### The arch tier (`tests/arch/`)

- `tests/arch/test_import_contracts.py` runs import-linter against the live contracts in `pyproject.toml` (`trigger-aws-only-in-stores`, `trigger-no-mint-transitive`, `trigger-registration-webhooks-only`; the pending contract `trigger-decide-readonly` lives under `[tool.importlinter-pending]`). It builds a synthetic package for each contract, plants each forbidden import, and requires the result to be BROKEN with exactly the planted pairs (the clean twin must be KEPT). It also requires every module under `src/autom8_asana/trigger/` to be declared in `MODULE_CONTRACTS` so a new module cannot slip past unclassified. It runs `lint-imports` as a subprocess with an explicit `PYTHONPATH`.
- `tests/arch/test_trigger_asana_client_ast.py` refuses `autom8_asana.AsanaClient` attribute access and any import of `AsanaClient` under `src/autom8_asana/trigger/` (the root re-export the import graph cannot see).
- `tests/arch/test_trigger_adapter_placement.py` checks that the in-memory test adapters (`tests/unit/trigger/adapters.py`) are absent from the wheel sources, the image copy lines, the entry points and `src/` wiring, each with a planted-violation twin.
- `tests/arch/test_namespace_contract.py` and `test_namespace_gen.py` hold the storage-namespace registry and its Terraform-derived JSON in lockstep.
- A separate non-pytest layer check runs in CI: `.github/workflows/semgrep-layer-rules.yml` runs `.semgrep.yml` with `--error`.

### CI wiring (`.github/workflows/`)

| Workflow / job | Trigger | What it runs | Gate? |
|---|---|---|---|
| `.github/workflows/test.yml` job `ci` (reusable workflow pinned by SHA) | push to `main` (docs and ledger paths ignored, `.github/workflows/test.yml:5-50`), pull request, dispatch | 4 shards (`test_splits: 4`), 2 xdist processes per shard, `test_timeout: 40`, marker expression excludes `integration`, `benchmark`, `fuzz`, `worker_isolated` (and `slow` on PRs), mypy on `src/autom8_asana`, OpenAPI spec check and Spectral, per-shard coverage threshold 0 and aggregate 80 | Yes; its success on a push to `main` triggers the deploy dispatch |
| `.github/workflows/test.yml` job `fuzz` | same events | `tests/test_openapi_fuzz.py` with `-p no:xdist`, `--timeout=300`, `SCHEMATHESIS_MAX_EXAMPLES` 5 on PRs and 25 otherwise | No (`continue-on-error: true`, line 160) |
| `.github/workflows/test.yml` job `workflow-handler-isolated` | same events | `tests/unit/lambda_handlers/test_workflow_handler.py -m worker_isolated -p no:xdist -o addopts=""` | No (`continue-on-error: true`, line 323) |
| `.github/workflows/test.yml` job `mcp-island` | same events | `python -m pytest tests -q` in `mcp/`, then `python -m pytest canary -q` requiring exit code exactly 1 | Yes (hard gate, no `continue-on-error`) |
| `.github/workflows/test.yml` jobs `fleet-schema-governance`, `lint-noqa-drift` | same events | response-schema governance check; `ruff` `RUF100` drift guard on `src/` | Yes (not test tiers) |
| `.github/workflows/post-merge-coverage.yml` | push to `main`, dispatch | full suite single shard, `--cov-fail-under=80`, excludes `integration`, `benchmark`, `fuzz` (includes `slow` and `worker_isolated`) | Advisory only (separate workflow; deploy keys on `Test`) |
| `aegis-synthetic-coverage.yml` | push and PR touching `src/**`, `tests/synthetic/**`, `docs/api-reference/**`, the aegis script | `pytest tests/synthetic/ -q -s`, then `scripts/aegis-check.py` threshold enforcement on the generated report | Yes for those paths |
| `nightly-live-smoke.yml` | cron `15 9 * * *` | the two live-smoke modules with `-p no:autom8y_config -p no:xdist -o addopts=""`, then a log grep that fails if the smokes were skipped, then a page-on-red step | Alerting, not a merge gate |
| `durations-refresh.yml` | cron Monday 09:00 UTC, dispatch | fast-path suite with `--store-durations --durations-path=.test_durations`, opens a PR | n/a |
| `con2-freeze-smoke.yml` | path-filtered (`Dockerfile.smoke`, `vendor/deck-producer/**`, a smoke script) | docker build plus a shell smoke (no pytest) | Yes for those paths |
| `merge-surface-sweep.yml`, `semgrep-layer-rules.yml` | PR and push | shell sweep with a positive-control self-test; semgrep rules | Static checks |

- Shard balancing: `pytest-split` with the committed `.test_durations`: 13,596 entries whose recorded durations sum to about 371 seconds. It has no entries for `tests/harness`, `tests/arch` or `tests/unit/trigger` (key-prefix census), so those tests are probably placed by pytest-split's fallback for unknown tests rather than by recorded time until the next weekly refresh [INFERRED from pytest-split's documented behavior; not run]. It has 493 `integration` and 126 `validation` entries, which means the refresh run includes unmarked integration-directory tests.
- Tiers NOT gated in CI: `benchmark` (never run), `fuzz` (advisory), the three non-`test_workflow_handler.py` `worker_isolated` modules (post-merge only), live smokes (nightly, alert only), and the `integration`-marked set (push-event run inside the reusable workflow, whose steps are not visible here).
- Duplicated or divergent marker sets: the PR lane drops `slow`; the push lane and post-merge coverage keep `slow`; the post-merge job also keeps `worker_isolated`. Tests marked `slow` never run on PRs.

### MCP island (`mcp/`)

25 `test_*.py` modules in `mcp/tests/` (165 functions, one conftest with 10 fixtures) plus `mcp/canary/test_broken_fixture_canary.py` (2 functions, a rows envelope that silently drops the honesty attestations; the real battery must reject it, so exit code 1 is the GREEN receipt and exit 0 means the gate has no teeth). The `mcp-island` job installs `./mcp[dev]` from its own `mcp/pyproject.toml`, runs `tests`, then the canary (`.github/workflows/test.yml:507-624`). The suite is outside root `testpaths`, coverage `source` and `mypy_targets`. The job comment calls it a "24-file suite" (`.github/workflows/test.yml:510` and `:596`); the tree has 25 `test_*.py` files. `just test-mcp` mirrors CI.

### Test invocation

- Whole suite: `uv run pytest` (xdist is not forced; `--dist=loadgroup` only matters under `-n`). Fast path: `uv run pytest tests/ -m "not slow and not integration and not benchmark"` (`just test-fast`). Scar set: `uv run pytest -m scar`. One tier by path: `tests/arch`, `tests/harness`, `tests/unit/trigger`. mcp island: `just test-mcp` or `cd mcp && python -m pytest tests -q` then `python -m pytest canary -q` (expect exit code 1).
- Worker-crash quarantine reproduction: `pytest <file> -m worker_isolated -p no:xdist -o addopts=""` (the same recipe CI uses).
- Not required for any tier here: live Asana access, except tests that skip without an `ASANA_PAT`.

## Knowledge Gaps

1. **No measured coverage.** No test, `uv`, `pip` or coverage command was run (run brief). `fail_under = 80` (`pyproject.toml:140`) is the only quantitative target in the repo, and no coverage report is committed. All counts are static: AST for functions, classes, decorators, fixtures and literal parametrize lists; regex over file text for idiom counts; an import-graph map for source-to-test links.
2. **Parametrize expansion is partial.** 70 of 301 `parametrize` decorators have a non-literal argument list (for example `tests/synthetic/test_synthetic_coverage.py` parametrizes over every OpenAPI operation read at import time), so 17,176 test items is a lower bound. Two measures of "test functions" exist: the AST walk (16,202 in `tests/`, fixtures excluded) and the regex `def test_` (16,221); the 19-function difference is nested or fixture-named helpers.
3. **Import-graph limits.** Re-exports through a package `__init__` hide use (for example `dataframes.cache_integration` is exercised through `autom8_asana.dataframes`), lazy and function-local imports are counted, but string-based `importlib` loads are not (the deploy canary under `scripts/canary/` is loaded by file path). Zero importers is therefore a risk signal, not proof of no coverage. The "thin by static signal" list in Coverage Gaps is INFERRED.
4. **Reusable CI workflow not visible.** `.github/workflows/test.yml` calls a reusable workflow pinned by SHA in another repository. Whether `coverage_threshold_aggregate: 80` actually fails a run, how `run_integration` selects tests on push, how `test_splits`/`test_maxprocesses` are applied and whether `.test_durations` is passed to `pytest-split` all happen there. This pass could not read it. Only the repo-local `.github/workflows/post-merge-coverage.yml` command was verified end to end.
5. **Whether `tests/validation/persistence/`, `tests/harness/`, `tests/arch/` and `tests/contracts/` run in the 4 shards** is inferred from `testpaths = ["tests"]` and the marker expression (none carries an excluded marker, except one `slow` test in `tests/validation/persistence/`); it was not confirmed from CI logs.
6. **Whether the three omitted `worker_isolated` modules pass in single-process mode** was not run. They execute only in the post-merge coverage workflow.
7. **Floor-excluded names.** Repository files whose names match the env, secret or credential floor were not opened and are out of scope (not read: floored name, operator's act); no test in `tests/`, `mcp/` or `src/` is among them. One audit script in `scripts/` that validates environment injection was likewise not read.
8. **[EXPERIENTIAL] `.sos/land/workflow-patterns.md`** (dionysus synthesis of 18 sessions, generated 2026-04-28, expired against this run) was integrated as follows. Consistent with code: the test-execution command pattern, the `tests/test_openapi_fuzz.py`, `tests/unit/dataframes/builders/test_cascade_validator.py`, `tests/unit/services/test_universal_strategy*.py` and `tests/unit/api/routes/test_resolver_status.py` hotspot files all still exist. Contradicted by code (code wins): the land file's "33 scar-tissue regression tests" cluster (project-crucible) is smaller than today's 87 `scar`-selected test functions in 16 files. The land file records phase and tool-usage patterns only; it holds no test-coverage baseline (the prior pass cited "13,072 to 12,320 dedup" and "87.59% coverage" as originating there, but neither string is in the file).
9. **Unverified by design**: the open-scar counts in the sibling scar-tissue document (the prior pass claimed "at least 17 newer unmarked scars"); this pass did not read that document, so the claim is neither confirmed nor refuted.

### Corrections to the prior pass (c29f58f4 -> 584c8f79)

Volume deltas (same method where stated; the prior pass used grep, this pass used AST plus regex, so small differences are partly method):

| Quantity | Prior (c29f58f4) | Now (584c8f79) |
|---|---|---|
| `test_*.py` modules | 726 (git ls-tree confirms 726 at the old ref) | 743 |
| test functions | 15,973 (grep) | 16,202 (AST) / 16,221 (regex `def test_`) |
| asserts | 31,578 | 32,174 (AST `Assert` nodes) |
| `pytest.raises` | 1,724 in 324 files | 1,792 in 331 files |
| fixtures | 792 | 817 in 277 files |
| parametrize sites | 275 in 116 files | 304 in 128 files (regex) |
| `conftest.py` under `tests/` | 18 | 19 (new: `tests/unit/trigger/conftest.py`) |
| `tests/arch/` | 2 test modules | 5 test modules (3 added: import contracts, adapter placement, AsanaClient AST guard) |
| `scar` marker sites / files | 46 / 17 | 46 / 17 (unchanged), but 87 effective selected functions in 16 files once class and module marks are counted (prior did not state it) |
| `integration`, `slow`, `skipif`, `xdist_group` | 49 / 12, 24 / 15, 49, 35 files and 6 groups | unchanged |
| `KNOWN_VIOLATIONS` | 56 | 56 |
| `.test_durations` | 13,596 entries | 13,596 entries (not refreshed in a way that adds the new test paths) |

Claims retracted or changed:

1. **Prior "Known blind spot 1" (`src/autom8_asana/metrics/compute.py` select-then-filter ordering has no regression test) is RESOLVED.** `src/autom8_asana/metrics/compute.py:98-127` now carries filter-referenced columns through the projection (comment cites SCAR-METRICS-SELECT-FILTER-001) and drops them after filtering. A new regression module, `tests/unit/metrics/test_compute_filter_columns.py`, covers a `filter_expr` on an unselected column, a `pre_filters` entry on an unselected column, the combination with dedup keys, unchanged output columns, and a parametrized run of every registered metric (`test_every_registered_metric_computes`). Residual: that file has no `@pytest.mark.scar`, and `tests/unit/metrics/test_adversarial.py:270` still carries the old "pre_filters can only reference columns that compute_metric selects" note.
2. **Prior "`caplog` in 194 files" was wrong.** The census finds `caplog` in 12 files (28 occurrences). The autom8y logger bypasses `caplog`; tests use `MockLogger` (10 files) or a local spy.
3. **Prior package count.** The prior pass said 30 package directories; the tree had 29 at `c29f58f4` (git ls-tree) and has 30 now because `src/autom8_asana/trigger/` was added.
4. **Prior mcp inventory.** The prior pass counted 24 `mcp/tests/test_*.py`; there are 25 (the CI comment also says 24). Function count is 165 in `mcp/tests/` plus 2 in the canary.
5. **Prior harness inventory.** The prior pass said 8 test files plus 7 support modules; `tests/harness/` has 8 test modules, 9 support modules and 2 `__init__.py` (19 `.py` files at both refs).
6. **Prior "28 modules unreferenced".** On the stricter, mechanical method used now (import, string reference or filename stem) the count is 23 of 558 non-`__init__` modules (list in Coverage Gaps). Modules from the prior list that now carry a signal: `src/autom8_asana/api/health_models.py` (imported by a test), `src/autom8_asana/api/routes/tags.py` (two name-matched test files), `src/autom8_asana/dataframes/resolver/default.py` (its public name is referenced by 9 test files) and `src/autom8_asana/observability/rung_receipts/join.py` (public names referenced by 2 test files). Modules that stay in the hard list: `src/autom8_asana/entrypoint.py`, `src/autom8_asana/api/error_responses.py`, `src/autom8_asana/clients/task_operations.py`, `src/autom8_asana/clients/task_ttl.py`, `src/autom8_asana/dataframes/builders/post_build_validation.py`, `src/autom8_asana/automation/workflows/active_offer_enumeration.py`, `src/autom8_asana/clients/goal_relationships.py`, `src/autom8_asana/clients/goal_followers.py`, `src/autom8_asana/clients/data/_endpoints/simple.py`, `src/autom8_asana/cache/integration/schema_providers.py`, `src/autom8_asana/cache/integration/upgrader.py`. `src/autom8_asana/observability/prometheus_metrics.py` and `src/autom8_asana/persistence/actions.py` are recorded separately as zero-importer modules with indirect coverage.
7. **Prior KNOWN_VIOLATIONS gap closed.** The 56th entry (outside the 45 "violation" and 10 "conforming-pinned" comments) is the TRACE method entry noting that the route returns 401 because auth precedes routing (`tests/test_openapi_fuzz.py`, within `KNOWN_VIOLATIONS`).
8. **Prior line citations are stale.** `.github/workflows/test.yml` moved: `fuzz` `continue-on-error` is now line 160 (was 144), the isolated job's `continue-on-error` line 323 (was 306), the isolated file list lines 400-402 (was 382-384), the marker expression line 137 (was 121), and the `mcp-island` job lines 507-624 (was 489-606).
9. **Prior experiential baseline dropped**: "13,072 to 12,320 dedup / 87.59% coverage" is not in the current land file and cannot be verified from code.
10. **New since the prior pass** (20 added test files by `git diff --name-status`): the whole `tests/unit/trigger/` set (4 test modules, conftest, adapters), `tests/arch/` guards (3), four rate-limit modules (`test_rate_limit_verified_key.py`, `test_limiter_hardening.py`, `test_limiter_config_file.py`, `test_health_limiter_exempt.py`) plus `test_ready_dependency_cache.py`, `tests/unit/api/middleware/test_idempotency_store_default.py`, `tests/unit/automation/workflows/test_render_check.py`, `tests/unit/automation/workflows/onboarding_walkthrough/floodgates/test_name_match.py`, `tests/unit/enrollment/test_r03_phone_field_contract.py`, and `tests/unit/metrics/test_compute_filter_columns.py`.
