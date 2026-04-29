---
artifact_id: EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29
type: triage
artifact_type: pre-inventory-substrate
purpose: opportunity-space contextualization for Pythia inaugural consult
session_id: session-20260429-161352-83c55146
rite: eunomia
track: test
initiative: test-suite efficiency optimization
authored_by: main-thread (synthesis of 5 parallel Explore agents)
authored_at: 2026-04-29T14:19Z
evidence_grade: MODERATE
self_grade_ceiling_rationale: "main-thread synthesis of read-only Explore agents; eunomia self-grading caps at MODERATE per self-ref-evidence-grade-rule"
swarm_lanes:
  - lane-1: parallelization-blast-radius
  - lane-2: fixture-cost-surface
  - lane-3: ci-shape-and-shard-topology
  - lane-4: slow-tail-pathology
  - lane-5: mock-cost-surface
status: ready-for-potnia-consumption
---

# Explore Swarm Synthesis — Test-Suite Perf Opportunity Space

## §0 What this document is

Pre-inventory substrate for the eunomia perf-track engagement. Five parallel
read-only Explore agents mapped distinct dimensions of the test-suite cost
surface. This synthesis collapses their outputs into a single tier-ranked
opportunity hierarchy with calibrations against prior knowledge corrected.

**This is NOT the inventory phase.** test-cartographer authors the formal
INVENTORY artifact in Phase 1. This document gives Potnia + Pythia the
substrate needed to author a competent inaugural consult.

## §1 Headline Calibrations vs Prior Knowledge

Five corrections matter for downstream framing:

| Prior claim | Corrected finding | Source |
|---|---|---|
| "687 fixtures across 15 conftests" | **65 fixtures** in main-repo conftests; the 687 figure was inflated by `.worktrees/` discovery | Lane 2 §1 |
| "MockClientBuilder root fixture at conftest.py:137" | **No `MockClientBuilder` class exists**. Root mock surface is 4 distributed fixtures (`mock_http`, `logger`, `config`, `auth_provider`) at `tests/conftest.py:98-123` | Lane 5 §1 |
| "12,842 unit test functions" | Counts in flux — `.test_durations` has **13,140**, blast-radius lane reports **~13,605**. Resolved by Phase-1 baseline run | Lanes 3, 1 |
| "97.3% unspec mock rate" | Confirmed at **97.8%** (3,110 sites, 67 spec'd) | Lane 5 §3 |
| "Sleep budget ~341s if all sleeps fired" | **Mostly virtualized** by `_fast_clock` fixture; real blocking <50s | Lane 4 §1 |

## §2 The Headline Number

**Suite serial wall-clock: 374.41s** (per `.test_durations` 13,140-test sum,
last refreshed 2026-04-15, ~2 weeks stale).

Theoretical 4-shard ideal: **94s per shard pytest time**. CI shard timeout is
40 minutes. The gap between 94s and 40min is consumed by:

- Reusable workflow setup (uv install, mypy, spec-check, semantic-score)
- Cache restore/save
- xdist worker startup × N
- The schemathesis fuzz job (separate, 15min timeout, single-threaded)

**Verdict: pytest-internal optimization has a ~94s floor per-shard. Anything
faster requires CI-shape work in `autom8y/autom8y-workflows/satellite-ci-reusable.yml`.**

## §3 Empirical Truths Established

These are no longer hypotheses — the swarm closed them:

1. **All real I/O is mocked.** Every boto3 site is under `@mock_aws` (moto);
   every httpx site under `respx.mock`; redis under `fakeredis`. Zero
   network/filesystem hot paths. Lane 4 §5.
2. **Asyncio overhead is sub-bottleneck.** ~2,000+ async tests × ~1-3ms loop
   creation = ~5-15s aggregate. Not a primary pace lever. Lane 4 §8.
3. **Sleep blocking is mostly virtualized.** `tests/unit/cache/test_memory_backend.py:138,148,475`
   uses `_fast_clock` (line 15) to patch `time.sleep`. Real wall-clock sleep
   budget is <50s, not 341s. Lane 4 §1.
4. **Mock teardown discipline is sound.** 1,079 `with patch()` context managers
   vs 206 `@patch` decorators (5.2:1 ratio). No `patch.stopall()` debt. Lane 5 §6.
5. **Slow tests already gated.** 23 `@pytest.mark.slow` tests excluded from PR
   CI per `test.yml:56`. Only run on push to main. Lane 4 §9.

## §4 The Tier-1 Lever — `--dist=loadfile` Blast Radius

This is the load-bearing finding of the swarm.

### §4.1 The structural blocker

`pyproject.toml:113` declares `addopts = "--dist=loadfile"`. This was added
2026-04-10 (commit `c5d2930d`) as a band-aid for two specific files:

- `tests/unit/lambda_handlers/test_workflow_handler.py` (process-global state)
- `tests/test_openapi_fuzz.py` (schemathesis hypothesis DB + module-level `app`)

**Cost of the band-aid**: parallelism caps at file count (~570 files), not test
count (~13,140). Workers under-utilize.

### §4.2 The root cause

`src/autom8_asana/core/system_context.py:28` defines `_reset_registry: list[Callable[[], None]] = []` —
a **module-level global** with **11 registered singletons**:

| Singleton | Registration site |
|---|---|
| Settings | `src/autom8_asana/settings.py:923` |
| MetricRegistry | `src/autom8_asana/metrics/registry.py:44-55` |
| EntityRegistry | `src/autom8_asana/core/entity_registry.py:1072-1080` |
| DataFrameCache | `src/autom8_asana/cache/dataframe/factory.py:37,155-228` |
| WatermarkRepository | `src/autom8_asana/dataframes/watermark.py:324-326` |
| SchemaRegistry | `src/autom8_asana/dataframes/models/registry.py:331-333` |
| ProjectTypeRegistry | `src/autom8_asana/models/business/registry.py:740-743` |
| BootstrapState | `src/autom8_asana/models/business/_bootstrap.py:189-191` |
| HolderRegistry | `src/autom8_asana/persistence/holder_construction.py:109-111` |
| WorkflowRegistry | `src/autom8_asana/automation/workflows/registry.py:96-98` |
| EntityProjectRegistry | `src/autom8_asana/services/resolver.py:705-707` |

`tests/conftest.py:193-204` autouse fires `SystemContext.reset_all()` **before
and after every test**. ~13,605 tests × 2 calls × 11 callbacks = **~300K reset
operations per run**. Under `--dist=load`, multiple workers race the same
shared global → worker crashes (the original 31.23% coverage failure pre-loadfile).

### §4.3 The unblock cost

Three concrete changes unlock `--dist=load`:

1. **Refactor `_reset_registry` to be worker-local** OR thread-safe with copy-on-fork semantics. Single file (`core/system_context.py`).
2. **Isolate hypothesis DB per worker.** Set `database=None` in fuzz settings or use `HYPOTHESIS_DATABASE` env var keyed to `PYTEST_XDIST_WORKER`. Single edit at `tests/test_openapi_fuzz.py:72-81`.
3. **Move `tests/test_openapi_fuzz.py:113-115` module-level `app`/`schema` into a fixture** (function or module scope). OR: leave the fuzz file alone and add per-file pytest mark `pytest.mark.xdist_group("fuzz")` so it stays loadfile-scoped while everything else moves to load. Lane 1 §6 hypothesis 4.

**Estimated wallclock multiplier: 3–5×** if fully unlocked (Lane 1 hypothesis 1+4).
Risk class HIGH. Surgical scope (1 src file + 1 test file).

## §5 Tier-2 Levers — Targeted Quick-Wins

### §5.1 Fuzz budget compression
`tests/test_openapi_fuzz.py:70` reads `SCHEMATHESIS_MAX_EXAMPLES` from env (default 25),
combined with `deadline=10_000ms` (line 79) → **250s baseline budget per run, can hit 900s
ceiling**. Reducing to 5 for PR runs while keeping 25 for nightly preserves signal.
**Estimated saving: ~200s per PR CI run.** Risk class LOW. Single env var.
Source: Lane 4 §3 + opportunity #1.

### §5.2 `.test_durations` refresh
File last touched 2026-04-15 (commit `af32c278`). Test count drift since then
(~12,842 → 13,140 → 13,605) means 4-shard `pytest-split` balance is stale; the
slowest shard pays a known imbalance penalty. **Estimated saving: 5-15% on the
straggler shard.** Risk class TRIVIAL. Generate via `pytest --store-durations`
on main and commit. Source: Lane 3 §2.

### §5.3 Largest-file collection cost
`tests/unit/automation/test_insights_formatter.py` is **3,570 lines / 267 tests** —
the largest single test file. Under loadfile mode the file pins to one worker.
Splitting into 3 files (~90 tests each) by formatter category lets the loadfile
distributor balance better. **Estimated saving: depends on shard imbalance**;
pure structural change, no logic risk. Risk class LOW. Source: Lane 4 §4 + Lane 4 opportunity #2.

## §6 Tier-3 — Test-Count Compression (Hygiene-Flavored)

Four files account for 295 enum-style tests with zero parametrize use:

| File | Lines | Tests | Pattern |
|---|---|---|---|
| `tests/unit/test_tier1_adversarial.py` | 1,817 | 102 | Per-model validation × 14 model classes |
| `tests/unit/test_tier2_adversarial.py` | 1,582 | 99 | Per-signature validation × 11 input combos |
| `tests/unit/test_batch_adversarial.py` | 1,104 | 94 | Per-filename × 12 edge-case variants |
| `tests/unit/test_config_validation.py` | 694 | 65 | Per-value-range × 14 reject-tests |

**Estimated impact**: collapse 295 → ~80 parametrized tests (~73% function-count
reduction). **Wallclock impact bounded** — pytest collection cost reduces, per-test
cost largely unchanged. Risk class LOW (no behavioral change). Better routed to
**eunomia consolidation-planner** as CHANGE-NN specs vs route-to-/hygiene because
the perf-lens does want collection-time savings.
Source: Lane 2 §5.

## §7 Mock Surface — Reframed for Pace

97.8% unspec rate is a **correctness debt** (SCAR-026 surface), not a primary
pace lever. Lane 5 estimates total pace impact at **2-8%** even with full spec=
adoption + session-cache of MockLogger/MockCacheProvider.

**Routing recommendation**: Mock-surface work is correctness-rite-flavored
(/hygiene as canonical target). Eunomia perf-track should NOT take this scope
unless it surfaces as the residual bottleneck after Tier-1+2 land.

The 11 bespoke `MockTask` redefinitions (`.know/test-coverage.md` GLINT-004) are
similarly low-pace-leverage; pure consolidation hygiene.

## §8 What Is NOT a Pace Driver (Eliminate from Plan Scope)

The swarm closed these dimensions explicitly so they don't consume planner attention:

- **Real I/O**: zero (all mocked correctly). Lane 4 §5.
- **Asyncio overhead**: bounded sub-millisecond per test. Lane 4 §8.
- **Sleep blocking**: virtualized by `_fast_clock`. Lane 4 §1.
- **Skip/xfail collection cost**: 20 sites, negligible. Lane 4 §6.
- **Iteration-heavy tests** (`range(100)`): lightweight list construction, not compute. Lane 4 §7.
- **Decorator/context-manager teardown**: discipline is sound. Lane 5 §6.
- **Network DNS / database connections**: not present. Lane 4 §5.
- **Fixture-chain depth**: max 5, mostly 2-3. Not a driver. Lane 2 §6.

## §9 The Open CI-Shape Question

Lane 3 confirms the test workflow is mostly **delegated to a reusable workflow
in another repo** (`autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd`).
Critical CI-shape variables are opaque from this repo:

- True per-shard wallclock breakdown (pytest vs install vs mypy vs spec-check)
- xdist worker count per shard
- Cache key strategy (lockfile-keyed or branch-keyed)
- Whether shard 4→8 expansion is feasible given runner pool

**Implication**: Phase 1 baseline measurement MUST include `gh run view` against
recent main runs to extract per-job wallclock. Without this, eunomia cannot
attribute wallclock between suite-internal and CI-infrastructure causes — which
determines whether Phase 4 changes meaningfully move CI or whether `/sre`
follow-on is required.

## §10 Tiered Opportunity Hierarchy

Synthesized for consolidation-planner Phase 3 sequencing:

### Tier 1 — Structural (highest ceiling, surgical scope)
- **CHANGE-T1A**: Refactor `core/system_context.py:_reset_registry` to worker-local. Unlock --dist=load.
- **CHANGE-T1B**: Isolate hypothesis DB per worker (`test_openapi_fuzz.py:72-81`).
- **CHANGE-T1C**: Resolve module-level state in `test_openapi_fuzz.py:113-115` (fixture or `xdist_group`).
- **Aggregate ROI**: 3-5× parallel multiplier within each shard.

### Tier 2 — Targeted (quick-win, low risk)
- **CHANGE-T2A**: `SCHEMATHESIS_MAX_EXAMPLES=5` for PR runs (env in `test.yml`).
- **CHANGE-T2B**: Refresh `.test_durations` and rebalance 4-shard split.
- **CHANGE-T2C**: Split `test_insights_formatter.py` into 3 files by category.
- **Aggregate ROI**: ~200s + 5-15% straggler-shard reduction.

### Tier 3 — Compression (hygiene, low risk)
- **CHANGE-T3A**: Parametrize-promote 4 adversarial files (295 → ~80 tests).
- **Aggregate ROI**: collection-time savings, smaller suite footprint.

### Tier 4 — Defer / Route Out
- Mock spec= adoption → /hygiene
- MockTask consolidation → /hygiene
- 4→8 shard expansion → /sre (requires reusable-workflow visibility)
- Aggregate post-merge coverage job → /sre (separate concern, GLINT-003)

## §11 Verification-Phase Anchor

Phase 5 verification-auditor PASS gate requires **measured wallclock delta
≥ planned ROI**. Pre-engagement baseline must capture:

1. `pytest --collect-only -q` time (collection-time floor)
2. `pytest --durations=100 --tb=no -q tests/unit/` top-100 + total (suite-time floor)
3. Last 5 successful main CI runs from `gh run list --workflow=test.yml`, with per-job timings via `gh run view <id> --json jobs`
4. xdist worker distribution under current loadfile config
5. `wc -l .test_durations` + age check

Baseline artifact target: `.ledge/reviews/BASELINE-test-perf-2026-04-29.md`.

## §12 Inaugural Consult Charter (for Pythia)

This synthesis recommends Pythia frame the engagement with these locks:

- **Track**: test (pipeline closed in VERDICT 2026-04-29).
- **Lens overlay**: extend canonical 5 entropy categories with **Suite Velocity** + **Parallelization Health**.
- **Phase 1 first action**: capture baseline per §11 BEFORE inventory authorship.
- **Phase 3 sequencing rule**: Tier-1 changes precede Tier-2/3 because Tier-1 changes the math for everything downstream (parallelism multiplier).
- **Inviolable constraint**: 33+ SCAR regression tests preserved through Phase 4.
- **Out-of-scope routing**: mock-spec work, MockTask consolidation → recommend to /hygiene at close. CI shard expansion → recommend to /sre at close.
- **Authority**: user has explicitly granted full eunomia authority for rewrites/reworks/refactors. Tier-1 IS a refactor of `core/system_context.py` — within scope.
- **Drift-audit discipline**: per VERDICT §5 Pattern-6 finding, re-run drift-audit at consolidation-planner dispatch (planner must not trust this synthesis without re-checking against current main).

---

## Appendix — Per-Lane Receipts

Lane 1 (parallelization): `Explore` agent `a323d6349b7f1eaaa` — confirmed git history of `--dist=loadfile`, mapped 11 SystemContext singletons, identified hypothesis DB sharing as secondary blocker.

Lane 2 (fixtures): `Explore` agent `acae770eb16cacdfb` — corrected fixture count from 687 to 65 (worktree noise), identified 4 parametrize-promotion hotspots in adversarial files.

Lane 3 (CI shape): `Explore` agent `af804322e9d48bb86` — established 374.41s serial baseline, mapped 4-shard pytest-split topology, confirmed coverage-gate-theater state, identified opaque reusable-workflow boundary.

Lane 4 (slow-tail): `Explore` agent `a39def9be38825a75` — established sleep is virtualized, fuzz budget is the dominant per-run cost, asyncio overhead is bounded.

Lane 5 (mocks): `Explore` agent `aa0e168505c51a22f` — corrected MockClientBuilder claim, confirmed 97.8% unspec rate, established mock-surface bound at 2-8% pace impact.
