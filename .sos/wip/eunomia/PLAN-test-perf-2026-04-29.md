---
type: design
artifact_type: consolidation-plan
rite: eunomia
track: test
session_id: session-20260429-161352-83c55146
authored_by: consolidation-planner
authored_at: 2026-04-29
evidence_grade: STRONG
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf
upstream_assessment: ASSESS-test-perf-2026-04-29.md
upstream_inventory: INVENTORY-test-perf-2026-04-29.md
upstream_baseline: BASELINE-test-perf-2026-04-29.md
upstream_synthesis: EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29.md
planned_changes_count: 6
deferred_changes_count: 1
pattern_6_compliance: drift-audit-re-run-confirmed
sequencing_invariant: tier-1-precedes-tier-2-and-tier-3
self_grade: STRONG
---

# PLAN — test-perf — 2026-04-29

## §1 Plan Purpose

This plan operationalizes the entropy-assessor verdict (Overall F; keystone compound F-PH-2 + F-FH-3 + F-PH-1 CRITICAL per ASSESS-test-perf-2026-04-29 §6) into 6 atomic, independently-revertible change specifications. Each change carries a Tier classification (1=keystone-unblock, 2=PR-scope ROI, 3=collection-time compression — DEFERRED), a measured anchor file:line, a risk class with rationale, a verification protocol, and a `git revert HEAD --no-edit` rollback path. The Tier-1-precedes-Tier-2/3 sequencing invariant from charter §7 is non-negotiable: addopts `--dist=load` switch (CHANGE-T1D) cannot land before the three Tier-1 isolation refactors (T1A, T1B, T1C) preserve test correctness under non-fileloaded distribution.

## §2 Drift-Audit Attestation

Pattern-6 drift-audit performed at planner-dispatch-time (2026-04-29) against the four anchor file:line claims carried forward from INVENTORY-test-perf-2026-04-29 and ASSESS-test-perf-2026-04-29. All four anchors CONFIRMED — no upstream drift since assessment authoring.

| Anchor | Claim | Verification | Result |
|---|---|---|---|
| `pyproject.toml:113` | `addopts = "--dist=loadfile"` (whole-file worker grouping) | `sed -n '113p'` | CONFIRMED — exact string match |
| `src/autom8_asana/core/system_context.py:28` | `_reset_registry: list[Callable[[], None]] = []` (module-global registry) | `sed -n '28p'` | CONFIRMED — exact string match |
| `tests/test_openapi_fuzz.py:113-115` | Module-level `app = _create_fuzz_app(); schema = from_asgi("/openapi.json", app=app)` | `sed -n '113,115p'` | CONFIRMED — module-level state at exactly cited lines |
| `tests/conftest.py:193-204` | `reset_all_singletons` autouse fixture invoking `SystemContext.reset_all()` | `sed -n '193,204p'` | CONFIRMED — autouse fixture body matches inventory |

**Outcome**: ZERO DRIFT. Plan is grounded in present-tense file state. Executor MUST re-run this drift-audit at dispatch-time per §9 protocol; if any anchor drifts between plan-authoring and executor-dispatch, executor HALTS and routes to potnia for plan re-validation.

## §3 Singleton Coupling Trace

Direct inspection of all 11 `register_reset(...)` sites enumerated in INVENTORY §F-PH-2 / Lane 1 §2. Classification: ISOLATED (single callable, no cross-site state read) vs COUPLED (cross-singleton subscription or shared mutable state observed in registration block).

| # | Site (file:line) | Registered callable | Classification | Notes |
|---|---|---|---|---|
| 1 | `src/autom8_asana/settings.py:931` | `reset_settings` | ISOLATED | Module-local function; no cross-singleton reads |
| 2 | `src/autom8_asana/metrics/registry.py:152` | `MetricRegistry.reset` | ISOLATED | Class-method on local registry |
| 3 | `src/autom8_asana/core/entity_registry.py:1085` | `_reset_entity_registry` | ISOLATED | Module-local function |
| 4 | `src/autom8_asana/cache/dataframe/factory.py:302` | `reset_dataframe_cache` | ISOLATED | Cache-clear function; no cross-deps |
| 5 | `src/autom8_asana/dataframes/watermark.py:326` | `WatermarkRepository.reset` | ISOLATED | Class-method on local repo |
| 6 | `src/autom8_asana/dataframes/models/registry.py:333` | `SchemaRegistry.reset` | COUPLED-PUBLISHER | Publishes via `SchemaRegistry.on_reset(...)` subscription channel; subscribers fire when this resets |
| 7 | `src/autom8_asana/models/business/registry.py:742` | `ProjectTypeRegistry.reset` | ISOLATED | Class-method |
| 8 | `src/autom8_asana/models/business/registry.py:743` | `WorkspaceProjectRegistry.reset` | ISOLATED | Class-method (paired registration with #7) |
| 9 | `src/autom8_asana/models/business/_bootstrap.py:191` | `reset_bootstrap` | ISOLATED | Module-local function |
| 10 | `src/autom8_asana/persistence/holder_construction.py:111` | `reset_holder_registry` | ISOLATED | Module-local function |
| 11 | `src/autom8_asana/automation/workflows/registry.py:98` | `reset_workflow_registry` | ISOLATED | Module-local function |
| 12* | `src/autom8_asana/services/resolver.py:707` | `EntityProjectRegistry.reset` + `SchemaRegistry.on_reset(_clear_resolvable_cache)` | COUPLED-SUBSCRIBER | Inventory enumerated 11 sites; this site contains TWO actions — register_reset + cross-singleton on_reset subscription. Counts as 12th coupling action. |

**Summary**: 10 ISOLATED / 2 COUPLED of 12 actions across 11 file sites. The COUPLED pair (`SchemaRegistry.reset` publisher at row 6 + `_clear_resolvable_cache` subscriber at row 12*) forms one publish/subscribe edge. Worker-local refactor (CHANGE-T1A) MUST preserve this edge: when SchemaRegistry resets, resolver's cache MUST also reset via the same subscription mechanism. Subscription channel is `SchemaRegistry.on_reset(...)` (not `register_reset`), so it is structurally orthogonal to `_reset_registry` — the worker-local refactor of `_reset_registry` does not perturb the subscription channel.

**Sleeping risk surfaced (pre-Gate-A escalation candidate)**: `SystemContext.reset_all()` docstring at `src/autom8_asana/core/system_context.py:46-47` claims "Resets are ordered to respect dependencies: registries first, then caches, then settings." Implementation at line 51-52 iterates `_reset_registry` in registration order (import order), NOT by dependency type. Order is determined by which test imports which production module first — fragile under any change to import topology. CHANGE-T1A must preserve registration ORDER semantics by making the per-worker registry follow the same append-on-import discipline. Surfaced in §11 as RISK-2.

## §4 Hypothesis DB State

Direct inspection: `.hypothesis/` directory contains only `constants/` and `unicode_data/` (hypothesis-internal lookups; not example database). NO `examples/` subdir present locally. `.gitignore:130` declares `.hypothesis/` ignored; `git ls-files | grep '.hypothesis/'` returns ZERO tracked files. State classification: **EPHEMERAL — DB does not survive across runs in CI; not committed to git**.

`tests/test_openapi_fuzz.py:72-81` registers a `ci` profile with `derandomize=True` (deterministic seed sequence per run) and `max_examples` set from `SCHEMATHESIS_MAX_EXAMPLES` env (default 25). Per-worker isolation concern is therefore narrowed: NOT a deterministic-replay corruption risk (derandomize bypasses example-DB reads), but a write-collision risk where concurrent xdist workers write to `.hypothesis/examples/{module}/` simultaneously when the DB IS populated (e.g., in local-dev runs without `derandomize`, or future CI runs that toggle profile). CHANGE-T1B treats this as a structural prophylactic — even though present-tense CI behavior does not exhibit corruption, removing the latent write-collision vector is required before `--dist=load` lands (CHANGE-T1D).

## §5 CHANGE Specifications

The 6 specs are grouped by Tier. Tier-1 (T1A-T1D) addresses the keystone compound (parallelism preconditions); Tier-2 (T2A-T2B) addresses PR-scope ROI on top of unblocked parallelism. Each spec follows the lean template: receipts table + numbered steps + verification + revert + out-of-scope. Tier-3 CHANGE-T3A (parametrize-promote 4 adversarial files) is DEFERRED per §11 RISK-DEFER-T3A.

### §5.1 CHANGE-T1A — Worker-local SystemContext registry

| Field | Value |
|---|---|
| Tier | 1 |
| Anchor | `src/autom8_asana/core/system_context.py:28` (module-global `_reset_registry`); 11 consumer sites enumerated in §3 |
| Risk | MED |
| Effort | moderate |
| Estimated ROI | Unblocks `--dist=load` (CHANGE-T1D); without this, Tier-1D ships test-isolation regressions per Baseline §3 / ASSESS F-PH-2 chain. Direct ROI = 0; indirect ROI = enabling for 3-5x parallelism multiplier (Baseline §3.2). |
| Dependency | BLOCKS T1D; must commit BEFORE any of T1B, T1C, T1D, T2A, T2B (per charter §7 invariant) |
| SCAR exposure | Indirect — every test consuming `reset_all_singletons` autouse fixture (`tests/conftest.py:193-204`); pre/post measurement via full `pytest -m scar` invocation per §8 |

**Spec**:

1. Refactor `src/autom8_asana/core/system_context.py:28` from module-global `_reset_registry: list[Callable[[], None]] = []` to a per-worker keyed mapping. Use `os.environ.get("PYTEST_XDIST_WORKER", "main")` as the worker key (xdist documented public env var; falls back to "main" when running serially or outside pytest).
2. Refactor `register_reset` (line 31-37) to append into `_reset_registry[worker_key]` (lazily-initialized list per key). Preserve the duplicate-suppression invariant: `if fn not in _reset_registry[worker_key]: _reset_registry[worker_key].append(fn)`.
3. Refactor `SystemContext.reset_all` (line 44-54) to iterate `_reset_registry.get(worker_key, [])` instead of the module-global list. Preserve registration ORDER semantics (per §3 sleeping risk RISK-2): iterate in append order.
4. Preserve the 11 consumer-site call signatures unchanged. The 11 `register_reset(...)` invocations enumerated in §3 do NOT need modification — the worker-key resolution is internal to `system_context.py`.
5. Preserve the COUPLED pair (§3 rows 6 and 12*): the `SchemaRegistry.on_reset(...)` subscription channel is orthogonal to `_reset_registry` and is NOT touched by this change. Verify post-change by `grep -n "on_reset" src/autom8_asana/services/resolver.py` returns the same line as pre-change.

**Verification**:

1. `pytest -m scar -x` exits 0 pre-change AND post-change (SCAR cluster preservation per §8).
2. `pytest tests/ -p no:xdist -x` exits 0 (serial execution still works; "main" worker-key fallback path exercised).
3. Coverage delta: `pytest --cov=src/autom8_asana/core/system_context --cov-report=term-missing` shows >= pre-change coverage on `system_context.py`.

**Revert path**: `git revert HEAD --no-edit`. Single-commit change touching one production file (`src/autom8_asana/core/system_context.py`); no consumer-site coupling; revert is byte-for-byte safe.

**Out-of-scope**:

- Executor MUST NOT modify any of the 11 consumer-site `register_reset(...)` invocations.
- Executor MUST NOT touch `SchemaRegistry.on_reset(...)` subscription channel; it is structurally orthogonal per §3 trace.

### §5.2 CHANGE-T1B — Hypothesis DB per-worker isolation

| Field | Value |
|---|---|
| Tier | 1 |
| Anchor | `tests/test_openapi_fuzz.py:72-81` (hypothesis profile registration); future-conftest target |
| Risk | LOW |
| Effort | small |
| Estimated ROI | Removes latent write-collision vector ahead of CHANGE-T1D parallelism switch. Direct ROI = 0; structural prophylactic per §4. |
| Dependency | BLOCKS T1D; independent of T1A and T1C (can land in any order relative to T1A/T1C; MUST land before T1D) |
| SCAR exposure | None direct — hypothesis profile change does not alter SCAR cluster pass/fail behavior; verify via `pytest -m scar -x` regression check. |

**Spec**:

1. Extend `tests/test_openapi_fuzz.py:72-78` `register_profile("ci", ...)` block to set `database=None` when `derandomize=True` (current CI profile state per §4). With `derandomize=True`, the example DB is not read for replay; setting `database=None` explicitly disables the WRITE channel as well, eliminating the latent write-collision vector.
2. ALTERNATIVELY (if executor judgment determines the broader pattern is needed): introduce a per-worker DB directory at `tests/conftest.py` via a session-scoped fixture that sets `HYPOTHESIS_STORAGE_DIRECTORY=.hypothesis/{worker_key}/` before any test imports hypothesis. Executor SHOULD prefer the simpler `database=None` form unless a non-derandomize profile is added in the same change.
3. Do NOT touch `.gitignore:130` — `.hypothesis/` ignored declaration remains correct under either form.
4. Do NOT modify `derandomize=True` (line 77) — this is the CI determinism contract; preserve verbatim.

**Verification**:

1. `pytest -m scar -x` exits 0 (SCAR regression check).
2. `pytest tests/test_openapi_fuzz.py -x -p no:xdist` exits 0 (serial fuzz pass).
3. Confirm by inspection that no `.hypothesis/examples/` directory is created during test run: `ls .hypothesis/` post-test should still show only `constants/` and `unicode_data/` (the pre-existing hypothesis-internal lookup caches).

**Revert path**: `git revert HEAD --no-edit`. Single-file change to test-only code (`tests/test_openapi_fuzz.py` and optionally `tests/conftest.py`); no production code touched; revert is safe.

**Out-of-scope**:

- Executor MUST NOT change `derandomize=True` value.
- Executor MUST NOT touch the `.gitignore:130` declaration.

### §5.3 CHANGE-T1C — test_openapi_fuzz xdist_group pin

| Field | Value |
|---|---|
| Tier | 1 |
| Anchor | `tests/test_openapi_fuzz.py:113-115` (module-level `app = _create_fuzz_app()` and `schema = from_asgi(...)`) |
| Risk | LOW |
| Effort | trivial |
| Estimated ROI | Allows CHANGE-T1D `--dist=load` to ship without splitting fuzz-test functions across workers (which would race on the module-level `app`/`schema` state). Pin keeps fuzz-test class on a single worker without forcing the entire run into `--dist=loadfile`. Direct ROI = 0; structural enabler per Baseline §3.2. |
| Dependency | BLOCKS T1D; independent of T1A and T1B |
| SCAR exposure | Direct — `pytest -m scar -k test_openapi_fuzz` covers the fuzz cluster. Pre/post invocation per §8. |

**Spec**:

1. Add `pytestmark = pytest.mark.xdist_group("fuzz")` near the top of `tests/test_openapi_fuzz.py` (after existing imports, before line 72 profile registration). The `pytestmark` module-attribute applies the marker to every test in the module.
2. With `--dist=load` (Tier-1D), pytest-xdist routes all tests sharing the same `xdist_group` to the same worker. This preserves the module-level `app`/`schema` state co-locality that `--dist=loadfile` provided incidentally.
3. Do NOT refactor the module-level state itself (lines 113-115) into a fixture. The recommended pattern (per planner judgment over the alternative fixture-refactor strategy) is to pin via xdist_group; fixture refactor would cascade through the `@schema.parametrize()` decorator at line 117, increasing change footprint and risk.
4. Confirm `pytest-xdist` version supports `xdist_group`: it has been supported since pytest-xdist 2.0 (released 2020); `pyproject.toml` already requires xdist >=2.0 implicitly via `--dist=loadfile`. Executor verifies via `python -c "import xdist; print(xdist.__version__)"` >= 2.0.

**Verification**:

1. `pytest -m scar -k test_openapi_fuzz -x` exits 0 pre/post (SCAR fuzz cluster preserved).
2. `pytest tests/test_openapi_fuzz.py -x` exits 0 (full fuzz file passes).
3. Post-CHANGE-T1D, run `pytest tests/test_openapi_fuzz.py -n 4 --dist=load` and confirm exit 0 — this is the integration check that the pin works under `--dist=load`. (NOTE: this verification step REQUIRES T1D landed; if T1C lands before T1D, this check is performed at T1D verification time, not T1C verification time.)

**Revert path**: `git revert HEAD --no-edit`. Single-line addition to one test file; revert is trivial.

**Out-of-scope**:

- Executor MUST NOT refactor `app = _create_fuzz_app()` or `schema = from_asgi(...)` into a fixture.
- Executor MUST NOT change the `@schema.parametrize()` decorator at line 117.
- Executor MUST NOT add other `pytest.mark.xdist_group` markers in this commit; group additions to other files are out-of-scope.

### §5.4 CHANGE-T1D — Switch addopts loadfile to load

| Field | Value |
|---|---|
| Tier | 1 |
| Anchor | `pyproject.toml:113` (`addopts = "--dist=loadfile"`) |
| Risk | MED |
| Effort | trivial |
| Estimated ROI | 3-5x parallelism multiplier on full-suite wall-clock per Baseline §3.2 (loadfile groups whole files to one worker, leaving most workers idle on imbalanced files; `load` distributes test items round-robin, saturating workers). Largest single ROI in plan. |
| Dependency | BLOCKED-BY T1A, T1B, T1C (charter §7 invariant). Executor MUST NOT commit T1D until T1A+T1B+T1C have all landed. Verifies dependency by checking `git log --oneline` for T1A/T1B/T1C commits before opening T1D commit. |
| SCAR exposure | High — affects EVERY test invocation. Pre/post `pytest -m scar -x -n 4` per §8. |

**Spec**:

1. Modify `pyproject.toml:113` from `addopts = "--dist=loadfile"` to `addopts = "--dist=load"` (verbatim string change of `loadfile` to `load`).
2. No other lines modified. Confirm by `git diff pyproject.toml | wc -l` shows minimal-diff (typically 4 lines: `---`, `+++`, `-` line, `+` line, plus context).
3. Verify Tier-1A through Tier-1C have all landed before this commit: `git log --oneline -20 | grep -E "T1A|T1B|T1C"` should show three commits.

**Verification**:

1. `pytest -m scar -x` exits 0 (serial). [Must hold pre-T1D and post-T1D.]
2. `pytest -m scar -x -n 4 --dist=load` exits 0 (parallel under new directive). [The integration check of T1A+T1B+T1C+T1D combined.]
3. `pytest tests/ -n 4 --dist=load` exits 0 (full suite parallel). Wall-clock should drop materially per Baseline §3.2 expected delta; numerical confirmation deferred to verification-auditor.
4. Coverage delta: `pytest --cov=src --cov-report=term-missing` shows >= pre-change coverage (no module skipped due to xdist routing pathology).

**Revert path**: `git revert HEAD --no-edit`. Single-line change in `pyproject.toml`; revert is trivial. If revert fires, T1A/T1B/T1C remain in place (non-disruptive — they tolerate `--dist=loadfile` by construction).

**Out-of-scope**:

- Executor MUST NOT modify `--dist=load` to `--dist=worksteal` or any other variant in this commit.
- Executor MUST NOT change the worker count default (`-n auto` vs `-n 4`) in this commit.
- Executor MUST NOT add additional `xdist_group` markers in this commit (T1C is the only such pin in scope).

### §5.5 CHANGE-T2A — SCHEMATHESIS_MAX_EXAMPLES PR-scope envelope

| Field | Value |
|---|---|
| Tier | 2 |
| Anchor | `.github/workflows/test.yml` (fuzz job env block; `SCHEMATHESIS_MAX_EXAMPLES` env var; default value at `tests/test_openapi_fuzz.py:71` is `"25"`) |
| Risk | LOW |
| Effort | trivial |
| Estimated ROI | Reduces fuzz-job wall-clock by ~5x in PR scope (25 examples -> 5 examples); preserves full 25-example coverage on main/nightly. Per Baseline §4.1 fuzz job is the long-pole. PR-scope optimization, not a coverage reduction (full coverage runs on main). |
| Dependency | INDEPENDENT of all Tier-1 changes; can land in parallel. Recommended order: after T1D for clean wall-clock measurement attribution. |
| SCAR exposure | None — fuzz coverage on main/nightly unchanged. PR-scope coverage reduction is acceptable per Baseline §4.1 charter. |

**Spec**:

1. Locate `.github/workflows/test.yml` fuzz job (or the workflow file containing `SCHEMATHESIS_MAX_EXAMPLES` — executor confirms file path via `git grep -l SCHEMATHESIS_MAX_EXAMPLES .github/`).
2. Add `SCHEMATHESIS_MAX_EXAMPLES: 5` to the fuzz job's `env:` block, gated by a conditional that distinguishes PR vs main: `${{ github.event_name == 'pull_request' && '5' || '25' }}` (GitHub Actions ternary expression).
3. Do NOT modify `tests/test_openapi_fuzz.py:71` default value `"25"` — the env override at workflow altitude is the only change. Default remains 25 for local-dev and main-branch runs.
4. Do NOT add a new workflow file; modify the existing fuzz job in place.

**Verification**:

1. PR open after this change: confirm fuzz job logs show "max_examples=5" or equivalent (executor checks via `gh run view --log <run-id>` or workflow run UI).
2. Push to main after merge: confirm fuzz job logs show "max_examples=25" (the unchanged default).
3. `pytest -m scar -k test_openapi_fuzz -x` (local) exits 0 — local default unchanged at 25.

**Revert path**: `git revert HEAD --no-edit`. Single-file workflow YAML change; revert is safe.

**Out-of-scope**:

- Executor MUST NOT change the default value at `tests/test_openapi_fuzz.py:71`.
- Executor MUST NOT add `SCHEMATHESIS_MAX_EXAMPLES` to other workflow jobs.
- Executor MUST NOT alter the `derandomize=True` profile setting.

### §5.6 CHANGE-T2B — test_durations refresh and 4-shard rebalance

| Field | Value |
|---|---|
| Tier | 2 |
| Anchor | `.test_durations` (at repo root if present; else `tests/.test_durations` per pytest-split convention); CI shard configuration in `.github/workflows/test.yml` |
| Risk | LOW |
| Effort | small |
| Estimated ROI | Per Baseline §5 / Lane 3, current shard duration variance is 30%+ — rebalance reclaims wall-clock by leveling shards. Expected delta ~10-15% improvement on slowest-shard wall-clock. |
| Dependency | BLOCKED-BY T1D (must measure durations under `--dist=load` topology, not `--dist=loadfile`). Recommended order: after T1D AND T2A both land, rebalance once with both ROI sources reflected. |
| SCAR exposure | None — pure CI infrastructure rebalance; test invocation behavior unchanged. |

**Spec**:

1. After T1D and T2A both land, executor regenerates `.test_durations` by running `pytest --store-durations` against the full suite with `--dist=load -n 4`. This produces a fresh duration map.
2. Inspect `.github/workflows/test.yml` for shard configuration (`pytest --splits N --group K` invocation pattern). Confirm shard count is currently 4 and rebalance threshold logic uses `.test_durations` as input.
3. Commit the regenerated `.test_durations` file. The executor MUST NOT hand-edit duration values; `--store-durations` produces a deterministic snapshot.
4. Optionally: if the `--splits` count is configurable via workflow input, examine whether 4 -> 5 or 4 -> 6 shards yields meaningful wall-clock improvement. This sub-decision is OPTIONAL within T2B; the minimal form of T2B is duration-refresh only.

**Verification**:

1. CI run after merge: shard durations on the slowest shard should drop to within 15% of the fastest shard (vs the current 30%+ variance per Baseline §5).
2. `pytest -m scar -x` exits 0 (regression check unrelated to shard topology).
3. Confirm `.test_durations` is committed to the tree: `git ls-files | grep test_durations` shows the file.

**Revert path**: `git revert HEAD --no-edit`. Two-file change at most (`.test_durations` + optional workflow `--splits` value); revert restores prior balance (which works, just sub-optimally).

**Out-of-scope**:

- Executor MUST NOT hand-edit `.test_durations` values.
- Executor MUST NOT change shard count below 4 (would lose parallelism gains from T1D).
- Executor MUST NOT modify other workflow jobs in this commit.

## §6 Dependency Graph

```
                    +----------+       +----------+       +----------+
                    | CHANGE-  |       | CHANGE-  |       | CHANGE-  |
                    |  T1A     |       |  T1B     |       |  T1C     |
                    +----+-----+       +----+-----+       +----+-----+
                         |                  |                  |
                         +------------------+------------------+
                                            |
                                            v
                                     +-------------+
                                     |  CHANGE-T1D | (parallelism switch)
                                     +------+------+
                                            |
                              +-------------+-------------+
                              |                           |
                              v                           v
                       +-------------+              +-------------+
                       | CHANGE-T2A  |              | CHANGE-T2B  |
                       | (PR-scope)  |              | (durations) |
                       +-------------+              +-------------+
```

**Edges**:
- T1A, T1B, T1C BLOCK T1D (charter §7 sequencing invariant; conjunction — all three must land before T1D).
- T1A, T1B, T1C are mutually independent (can be committed in any order relative to each other).
- T2A is INDEPENDENT but recommended POST-T1D for clean wall-clock attribution.
- T2B is BLOCKED-BY T1D (durations measurement depends on `--dist=load` topology). T2B is also recommended POST-T2A so a single duration snapshot reflects both ROI sources.
- DEFERRED CHANGE-T3A (parametrize-promote 4 adversarial files) is independent of all of the above; deferred per §11 RISK-DEFER-T3A.

**Acyclicity**: The graph is a DAG (T1{A,B,C} -> T1D -> T2{A,B}); no back-edges. Each node carries an independent `git revert HEAD --no-edit` path.

## §7 Aggregate ROI Projection

| CHANGE | Direct ROI | Indirect/Enabling ROI | Wall-clock delta (full suite) | Confidence |
|---|---|---|---|---|
| T1A | 0% | Unblocks T1D parallelism multiplier | 0 in isolation | STRONG |
| T1B | 0% | Removes latent write-collision; enables T1D safely | 0 in isolation | STRONG |
| T1C | 0% | Pins fuzz-test colocality under T1D | 0 in isolation | STRONG |
| T1D | 200-400% (3-5x speedup) | (composed effect of T1A+T1B+T1C+T1D) | -50% to -75% wall-clock | STRONG (Baseline §3.2) |
| T2A | 80% on fuzz-job (PR-scope only) | Reduces PR-CI long-pole | -15% to -25% on PR-scope wall-clock | MODERATE (Baseline §4.1) |
| T2B | 10-15% on slowest-shard | Rebalances shard variance | -5% to -10% post-T1D | MODERATE (Baseline §5) |
| **TOTAL (full suite)** | — | — | **-55% to -80% wall-clock under -n 4 --dist=load + PR-scope envelope** | STRONG |

**Caveat**: aggregate is multiplicative across T1A-T1D (single composed effect, not sum) plus additive contributions from T2A and T2B. Numerical bounds are projection per Baseline; verification-auditor measures actual delta post-execution.

## §8 SCAR Cluster Preservation Matrix

For every Tier-1 change, executor runs `pytest -m scar` pre-change and post-change. Test-function count MUST be preserved (per [GUARD-CP-001]).

| CHANGE | SCAR pre-command | SCAR post-command | Equality assertion |
|---|---|---|---|
| T1A | `pytest -m scar --collect-only -q | wc -l` (capture as N_pre) | same command after commit (N_post) | N_pre == N_post |
| T1B | `pytest -m scar -k test_openapi_fuzz --collect-only -q | wc -l` | same command after commit | equality |
| T1C | `pytest -m scar -k test_openapi_fuzz --collect-only -q | wc -l` | same command after commit | equality |
| T1D | `pytest -m scar --collect-only -q | wc -l` | same after commit | equality (count) AND `pytest -m scar -x -n 4 --dist=load` exit 0 (behavior) |
| T2A | (no SCAR cluster touched; workflow-only) | (no SCAR cluster touched) | N/A — exposure NONE per spec |
| T2B | (no SCAR cluster touched; durations-only) | (no SCAR cluster touched) | N/A — exposure NONE per spec |

**Aggregate SCAR invariant**: total `pytest -m scar` collected count at HEAD-after-T2B == total at HEAD-before-T1A. Any divergence triggers verification-auditor REFUSED verdict per Pattern-6.

## §9 Drift-Audit Re-Dispatch Protocol for Executor

Before opening any commit in §5, executor MUST re-run §2 drift-audit (4 anchor checks). Procedure:

1. `sed -n '113p' pyproject.toml` -> expect `addopts = "--dist=loadfile"` (until T1D commits)
2. `sed -n '28p' src/autom8_asana/core/system_context.py` -> expect `_reset_registry: list[Callable[[], None]] = []` (until T1A commits)
3. `sed -n '113,115p' tests/test_openapi_fuzz.py` -> expect module-level `app = _create_fuzz_app()` and `schema = from_asgi(...)` (lines unchanged across all of T1A-T2B; only the `pytestmark` insertion at the top of the file moves the line numbers AFTER T1C — protocol acknowledges this and instructs executor to verify the BLOCK semantics not strict line numbers post-T1C)
4. `sed -n '193,204p' tests/conftest.py` -> expect `reset_all_singletons` autouse fixture body unchanged (all of T1A-T2B preserve this fixture; T1A's worker-key refactor is internal to `system_context.py` and does not require fixture changes)

If any anchor drifts: executor HALTS the in-progress commit, surfaces drift to potnia, and routes back to consolidation-planner for re-validation.

## §10 Out-of-Scope Refusal Posture

The following are explicitly OUT-OF-SCOPE for this plan and MUST be refused if surfaced as in-flight scope additions during execution:

- Production-code modification beyond `src/autom8_asana/core/system_context.py` (only file in production scope, per CHANGE-T1A).
- Tier-3 parametrize-promote work (adversarial-file consolidation) — DEFERRED per §11 RISK-DEFER-T3A.
- Modification of any of the 11 consumer-site `register_reset(...)` invocations.
- Refactor of `tests/test_openapi_fuzz.py:113-115` module-level state into a fixture (T1C uses xdist_group pin instead).
- Change to `derandomize=True` setting on hypothesis CI profile.
- Change to default value `"25"` at `tests/test_openapi_fuzz.py:71`.
- Worker count changes (`-n auto` <-> `-n 4`) outside T2B scope.
- Shard count reduction below 4.
- Addition of new workflow files; only existing workflow modifications are in scope (T2A).

If executor encounters in-flight scope addition matching any of the above, executor HALTS, surfaces to potnia, and routes to consolidation-planner for plan amendment.

## §11 Open Risks

**RISK-1 — CI overhead from PR-scope envelope under wide-spread profile use**: T2A reduces `SCHEMATHESIS_MAX_EXAMPLES` to 5 in PR scope. If a future workflow change introduces a non-derandomize hypothesis profile in PR scope, the 5-example envelope may produce excessive flake from non-deterministic seed exploration. Mitigation: T2A spec includes explicit "do not alter `derandomize=True`" out-of-scope clause; verification-auditor confirms by CI log inspection.

**RISK-2 — SystemContext registration-order coupling**: `_reset_registry` ordering is import-graph-determined (per §3 sleeping-risk surfacing). T1A preserves order via append-on-import discipline. If a future production-code change re-orders imports, reset-all behavior may shift silently. Mitigation: out-of-band — recommend potnia raise as a separate hygiene track (not in scope for this plan); CHANGE-T1A spec line 3 explicitly calls out the invariant for executor preservation.

**RISK-3 — Hypothesis DB latent population**: §4 asserts the example DB is currently ephemeral (only `constants/` and `unicode_data/` local). Future profile changes that toggle `derandomize=False` could populate `examples/` and create write-collision under T1D parallelism. Mitigation: T1B `database=None` form makes this structurally impossible regardless of `derandomize` state. If executor instead chose the per-worker DB directory form (T1B step 2), this risk persists at lower magnitude.

**RISK-4 — Baseline asymmetry**: BASELINE-test-perf-2026-04-29 measurements were captured under `--dist=loadfile` topology. Post-T1D wall-clock measurement under `--dist=load` cannot be directly compared to baseline absolute values, only to the projected delta envelope. Mitigation: verification-auditor must measure the post-T1D wall-clock via the same harness; ROI claims in §7 are intrinsic-delta projections, not baseline-relative absolutes.

**RISK-5 — xdist worker-ID API surface**: T1A relies on `os.environ.get("PYTEST_XDIST_WORKER", "main")`. This env var is documented public xdist behavior, but the documented form is `pytest-xdist-worker` (lowercase) in some pytest-xdist 3.x docs. Mitigation: executor verifies live env var name by `pytest -n 2 --collect-only` against a probe test that prints `os.environ.keys()`; if name differs, executor amends T1A spec by routing to consolidation-planner for an in-place spec correction (single-line) BEFORE committing T1A.

**RISK-DEFER-T3A — Tier-3 deferred**: CHANGE-T3A (parametrize-promote 4 adversarial test files into single parametrized files) is DEFERRED from this plan with rationale: (1) Tier-3 compression operates at collection time only, with ROI bounded to a few hundred milliseconds per `pytest --collect-only` invocation, vs Tier-1's 3-5x multiplier on full-suite wall-clock; (2) authoring 4 sub-specs (one per adversarial file) would exceed the lean-spec budget without proportionate value; (3) T3A's verification surface (test-function count preservation under `pytest.mark.parametrize` aggregation) is non-trivial and warrants its own focused plan; (4) ROI from T1+T2 may already deliver the wall-clock ceiling charter targets, rendering T3A non-essential. Defer to a follow-on consolidation pass after T1+T2 land and verification-auditor confirms wall-clock outcome. Track as inventory finding F-PH-3-related; surface in post-execution wrap as candidate for next session.

## §12 Source Manifest

- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md` — charter §7 sequencing invariant + §8 inviolable constraints
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/ASSESS-test-perf-2026-04-29.md` — Overall F; F-PH-2+F-FH-3+F-PH-1 keystone compound CRITICAL
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/INVENTORY-test-perf-2026-04-29.md` — 34 findings; F-PH-2 11 singleton sites
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/BASELINE-test-perf-2026-04-29.md` — wall-clock baseline + ROI projection sources
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29.md` — synthesis substrate; Lane 1/2/3 attribution
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/pyproject.toml:113` — addopts directive (T1D anchor)
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/core/system_context.py:28` — `_reset_registry` (T1A anchor)
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/test_openapi_fuzz.py:113-115` — module-level fuzz state (T1C anchor); `:72-81` — hypothesis profile (T1B anchor)
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/conftest.py:193-204` — `reset_all_singletons` autouse fixture
