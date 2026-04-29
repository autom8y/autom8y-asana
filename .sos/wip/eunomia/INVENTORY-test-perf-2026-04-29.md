---
artifact_id: INVENTORY-test-perf-2026-04-29
schema_version: "1.0"
type: triage
artifact_type: inventory
rite: eunomia
track: test
session_id: session-20260429-161352-83c55146
authored_by: test-cartographer
authored_at: 2026-04-29
evidence_grade: STRONG
evidence_grade_rationale: "Multi-source corroboration: findings cite STRONG-graded empirical baseline (direct measurement) + 5-lane rite-disjoint Explore-agent swarm synthesis. Self-ref-evidence-grade-rule STRONG unblock satisfied per multi-source rule."
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf
---

# Test Ecosystem Inventory — perf-2026-04-29

## §1 Inventory Purpose

This inventory restructures two upstream substrates into the canonical eunomia
7-category schema for entropy-assessor grading at Phase 2. No new measurement
is performed; this is synthesis-only.

**Substrate 1** — EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29 (5-lane opportunity-space
map authored by rite-disjoint Explore agents): §1 (headline calibrations), §2
(headline number), §3 (empirical truths), §4 (Tier-1 blast radius), §5 (Tier-2),
§6 (Tier-3), §7 (mock surface), §8 (closed dimensions), §9 (CI shape), §10
(tiered hierarchy). Five prior-knowledge corrections are carried at Swarm §1.

**Substrate 2** — BASELINE-test-perf-2026-04-29 (empirical baseline captured
pre-inventory by test-cartographer): §3 (suite-internal measurements M-1 through
M-4 and M-6), §4 (CI wallclock M-5), §5 (Tier-1 anchor drift audit), §6
(triangulation notes), §7 (Phase-5 PASS gate anchors). STRONG evidence grade;
all claims anchored to command output verbatim.

Per charter §4.1 (PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf), the Pattern-6
drift-audit discipline is preserved: the 4 Tier-1 anchors were confirmed undrifted
at baseline capture (Baseline §5). This inventory carries that attestation forward
without adding new drift surface.

---

## §2 Test Ecosystem Topology

**Scale**: 13,605 tests collected across 570 test files, 15 conftest files,
65 fixtures in the main-repo conftest hierarchy (corrected from prior 687 figure
which included worktree noise per Swarm §1). Framework: pytest with asyncio_mode=
"auto", pytest-xdist, pytest-split.

**Parallelism configuration**: `pyproject.toml:113` declares
`addopts = "--dist=loadfile"` (added commit `c5d2930d`, 2026-04-10). 4-shard
CI via pytest-split driven by `.test_durations` file (13,141 lines; last committed
2026-04-15, 14 days stale at baseline).

**Serial wallclock disposition**: 374.41s stored total (`.test_durations` sum,
all subtrees including fuzz). Fresh measured: 215.34s for `tests/unit/` (12,716
tests). Collection-time floor: 29.90s median (3-run, 13,605 items).

**CI shape**: Slowest shard p50 = 447.0s across 5 recent main-branch runs
(Baseline §4). Theoretical pytest-internal floor at 4-shard ideal = ~94s. Gap
of ~353s is infrastructure overhead in `autom8y/autom8y-workflows/
satellite-ci-reusable.yml@c88caabd` (install, mypy, cache, xdist startup).

**Drift-audit pre-engagement**: CLEAN. All 4 Tier-1 anchors confirmed undrifted
at baseline §5 (2026-04-29). See §13.

---

## §3 Findings — Mock Discipline

**F-MD-1: 97.8% unspec mock rate**
3,110 `patch()` sites across the suite; only 67 carry `spec=` or `autospec=True`.
Unspec rate = 97.8%. Source: Swarm Lane 5 §3 (confirmed from prior 97.3% estimate).
Severity: HIGH (correctness debt; no spec= means attribute typos are silently
undetected). Canonical-category tag: MOCK-DISCIPLINE.

**F-MD-2: No MockClientBuilder class — root mock surface is 4 distributed fixtures**
Prior claim of "MockClientBuilder at conftest.py:137" is false. Correction per
Swarm Lane 5 §1: root mock surface consists of 4 named fixtures (`mock_http`,
`logger`, `config`, `auth_provider`) at `tests/conftest.py:98-123`. No
`MockClientBuilder` class exists anywhere in the codebase.
Severity: LOW (correction, not a defect). Canonical-category tag: MOCK-DISCIPLINE.

**F-MD-3: 11 bespoke MockTask redefinitions vs 1 canonical**
11 test files each independently define a `MockTask` class despite a canonical
definition at `tests/_shared/mocks.py:10`. Proliferation index: 11:1.
Source: Swarm Lane 5 §4 (cited as GLINT-004 in `.know/test-coverage.md`).
Severity: MED (correctness debt; divergent definitions risk behavioral drift
between canonical and bespoke). Canonical-category tag: MOCK-DISCIPLINE.

**F-MD-4: Mock teardown discipline is sound**
1,079 `with patch()` context-manager uses vs 206 `@patch` decorator uses (5.2:1
ratio). No `patch.stopall()` debt found. Teardown is deterministic.
Source: Swarm Lane 5 §6 (confirmed, closed dimension).
Severity: POSITIVE FINDING. Canonical-category tag: MOCK-DISCIPLINE.

---

## §4 Findings — Test Organization

**F-TO-1: Largest file `test_insights_formatter.py` — 3,570 lines, 272 collected tests**
`tests/unit/automation/workflows/test_insights_formatter.py`: 3,570 lines,
272 tests measured at baseline M-6. Stored duration for this file: 0.23s total
(fast tests; not a duration bottleneck). Under `--dist=loadfile` it pins to one
worker but contributes negligibly to duration imbalance.
Source: Swarm Lane 4 §4 (line/test count); Baseline §3 M-6 (272 measured tests).
Severity: MED (structural maintenance burden; test-count imbalance signal).
Canonical-category tag: TEST-ORGANIZATION.

**F-TO-2: 4 enum-style adversarial files with zero parametrize use**
Four files contain 360 total tests written as individual functions with no
`@pytest.mark.parametrize` use:

| File | Lines | Tests |
|---|---|---|
| `tests/unit/test_tier1_adversarial.py` | 1,817 | 102 |
| `tests/unit/test_tier2_adversarial.py` | 1,582 | 99 |
| `tests/unit/test_batch_adversarial.py` | 1,104 | 94 |
| `tests/unit/test_config_validation.py` | 694 | 65 |

Note: Swarm §6 reports these 4 files at 295 tests combined. Baseline M-6 reports
102+99+94+74 = 369 measured collected. Using Baseline M-6 as the authoritative count
(empirically measured): 369 tests across 5,197 lines.
Source: Swarm Lane 2 §5; Baseline §3 M-6.
Severity: MED (collection overhead; CHANGE-T3A target per charter §7.2).
Canonical-category tag: TEST-ORGANIZATION.

**F-TO-3: 23 `@pytest.mark.slow` tests properly gated from PR CI**
23 tests carry `@pytest.mark.slow` and are excluded from PR CI per `test.yml:56`.
They run only on push to main. Gate is operative.
Source: Swarm Lane 4 §9.
Severity: POSITIVE FINDING. Canonical-category tag: TEST-ORGANIZATION.

**F-TO-4: 244 files with async tests; asyncio_mode="auto" overhead is bounded**
~2,000+ async tests across 244 files. `asyncio_mode="auto"` is configured.
Aggregate loop-creation overhead estimated at 5-15s total. Not a primary pace
lever.
Source: Swarm Lane 4 §8.
Severity: POSITIVE FINDING (closed dimension). Canonical-category tag: TEST-ORGANIZATION.

---

## §5 Findings — Fixture Hygiene

**F-FH-1: 65 fixtures across 15 conftests (corrected from prior 687 figure)**
Main-repo conftest hierarchy contains 65 fixture definitions across 15 conftest
files. The prior "687 fixtures" figure was inflated by `.worktrees/` directory
discovery during an earlier scan. Corrected per Swarm Lane 2 §1.
Source: Swarm §1 (headline correction table).
Severity: POSITIVE FINDING (correction; actual scope is manageable).
Canonical-category tag: FIXTURE-HYGIENE.

**F-FH-2: Only 2 root autouse fixtures at `tests/conftest.py`**
Root conftest defines two autouse fixtures:
- `_bootstrap_session` (session-scoped; amortizes once per run)
- `reset_all_singletons` (function-scoped; fires before and after every test)
Source: Swarm Lane 2 §3; Baseline §5 confirms `tests/conftest.py:193-204`.
Severity: see F-FH-3 for the cost implication.
Canonical-category tag: FIXTURE-HYGIENE.

**F-FH-3: `reset_all_singletons` generates ~300K reset operations per run**
`tests/conftest.py:193-204` — autouse function-scoped fixture calls
`SystemContext.reset_all()` before AND after every test. 11 registered singletons
× ~13,605 tests × 2 calls = ~299,310 reset callback invocations per run.
Source: Swarm Lane 1 §3; anchor confirmed at Baseline §5
(`tests/conftest.py:193-204`).
Severity: HIGH (primary structural cost driver; directly coupled to F-PH-2 and
the `--dist=loadfile` band-aid). Canonical-category tag: FIXTURE-HYGIENE.

**F-FH-4: API conftest adds `reset_singletons` autouse on top of root autouse**
~50 API test modules are covered by a subdirectory-level conftest that adds a
second `reset_singletons` autouse fixture, effectively doubling reset-callback
overhead for the API test subset.
Source: Swarm Lane 2 §3.
Severity: MED (compound overhead for API subset). Canonical-category tag:
FIXTURE-HYGIENE.

**F-FH-5: Max fixture-chain depth 5 (API tests); typical depth 2-3**
No fixture chain exceeds depth 5. Typical fixture chains are depth 2-3. Not a
primary performance driver.
Source: Swarm Lane 2 §6.
Severity: POSITIVE FINDING (closed dimension). Canonical-category tag:
FIXTURE-HYGIENE.

---

## §6 Findings — Coverage Governance

**F-CG-1: Coverage gate is theater**
`pyproject.toml:126` declares `fail_under=80` in the `[tool.coverage.report]`
section. However, `.github/workflows/test.yml:52` sets `coverage_threshold=0`
for sharded runs. The declared threshold is never enforced in CI.
Source: Swarm Lane 3 §3; per-charter label GLINT-003.
Severity: MED (for coverage-governance grading purposes). ROUTE-OUT: /sre +
/hygiene. This track does not act on F-CG-1 at Phase 3/4.

**F-CG-2: Post-merge aggregate coverage job does not exist**
There is no CI job that aggregates shard coverage results after merge to main.
Coverage is reported per-shard but never combined. A full-suite coverage figure
is unavailable.
Source: Swarm Lane 3 §3.
Severity: MED. ROUTE-OUT: /sre. Not in perf-track Phase 3/4 scope.

**F-CG-3: 4 packages have no dedicated test directories**
`_defaults/`, `batch/`, `observability/`, `protocols/` have no corresponding
`tests/unit/<package>/` directory.
Source: `.know/test-coverage.md`.
Severity: LOW (coverage gap, not a pace issue). ROUTE-OUT: /hygiene.

**F-CG-4: 9 modules in covered packages have no dedicated test files**
Within packages that do have test coverage, 9 individual modules have zero
dedicated test files.
Source: `.know/test-coverage.md`.
Severity: LOW. ROUTE-OUT: /hygiene.

**Routing note**: All four F-CG findings are out-of-scope for perf-track
Phase 3/4 execution. The entropy-assessor grades them under Coverage Governance
using the weakest-link model; no execution agent acts on them in this engagement.

---

## §7 Findings — Semantic Adequacy

**F-SA-1: 33+ SCAR regression tests preserved and inviolable**
`tests/unit/scars/` plus distributed `@pytest.mark.scar`-tagged tests across the
suite. Inviolable per charter §8.1. Executor must run `pytest -m scar`
pre- and post-change as halt-on-fail gate.
Source: `.know/test-coverage.md`; `.know/scar-tissue.md`; charter §8.1.
Severity: POSITIVE FINDING (structural protection in place).
Canonical-category tag: SEMANTIC-ADEQUACY.

**F-SA-2: 1 hypothesis property-based test with calibrated settings**
`tests/unit/persistence/test_reorder.py` uses Hypothesis at
`max_examples=100, deadline=None, derandomize=True` (per TRIAGE-005 calibration).
Source: Swarm Lane 4 §2.
Severity: POSITIVE FINDING. Canonical-category tag: SEMANTIC-ADEQUACY.

**F-SA-3: 1 schemathesis fuzz module with 47 pre-existing violations**
`tests/test_openapi_fuzz.py` — OpenAPI fuzzing via schemathesis, marked
`xfail strict=False`. 47 pre-existing violations recorded. 2 of 5 recent CI
runs show fuzz job failure (non-blocking). Fuzz budget: 25 examples × 10s
deadline = 250s baseline; can hit 900s ceiling.
Source: Swarm Lane 4 §3.
Severity: MED (fuzz failures are non-blocking but signal API surface gaps;
xfail strict=False masks regression detection). Canonical-category tag:
SEMANTIC-ADEQUACY.

**F-SA-4: 8 workspace-switching tests permanently skipped due to singleton design**
8 tests are skipped permanently because the module-level singleton design makes
workspace switching impossible to test in isolation. This is an existing scar.
Source: `.know/test-coverage.md`.
Severity: MED (tests that cannot run = blind spot; but it is an acknowledged
pre-existing scar). Canonical-category tag: SEMANTIC-ADEQUACY.

**F-SA-5: All real I/O is mocked — zero network/redis/AWS calls in unit suite**
Every boto3 site is under `@mock_aws` (moto); every httpx site under
`respx.mock`; redis under `fakeredis`. Confirmed across entire unit suite.
Source: Swarm Lane 4 §5.
Severity: POSITIVE FINDING (closed dimension; not a pace issue).
Canonical-category tag: SEMANTIC-ADEQUACY.

---

## §8 Findings — Suite Velocity (PERF OVERLAY)

Charter §6.1 grading rubric applies. Initial expected grade: **D**.

**F-SV-1: Serial wallclock — 374.41s stored, 215.34s measured fresh for unit/**
`.test_durations` sum across full tree (13,140 entries): 374.41s.
Fresh measurement of `tests/unit/` (12,716 tests): 215.34s (3:35).
Stored unit/ subset sum: 245.13s; fresh is 12.2% faster (stale durations
overestimate). Delta within normal range for 14-day staleness.
Source: Baseline §3 M-4; Baseline §6 triangulation.

**F-SV-2: Slowest CI shard p50 = 447.0s**
Over 5 recent main-branch runs, the slowest per-run shard ranged 437-471s.
p50 = 447.0s, p95 = 471.0s. Charter §6.1 rubric thresholds: D = 300-600s slowest
shard (initial grade D confirmed).
Source: Baseline §4 M-5.

**F-SV-3: `.test_durations` is 14 days stale (last commit 2026-04-15)**
File `af32c278` committed 2026-04-15. Staleness at baseline: 14 days. Test count
has drifted from 13,140 stored entries to 13,605 currently collected. Stale
durations cause shard imbalance.
Source: Baseline §3 M-2; Swarm §2 (headline number).

**F-SV-4: `test_openapi_fuzz.py` consumes 111.46s = 29.8% of stored total**
`tests/test_openapi_fuzz.py` holds 111.46s of the 374.41s stored total. Mean
per-file stored duration is 0.78s; fuzz file is 143× the mean. 57 tests in the
file average ~1.95s/test vs 0.028s/test for the rest of the suite.
Source: Baseline §3 M-6 (duration axis table); Baseline §6 fuzz structural finding.

**F-SV-5: Schemathesis budget can hit 900s ceiling**
`SCHEMATHESIS_MAX_EXAMPLES` (default 25) × `deadline=10_000ms` = 250s nominal.
Upper ceiling at 25 examples × 36s worst-case = 900s. PR CI reduction to 5
examples = 50s nominal budget.
Source: Swarm Lane 4 §3; Swarm §5.1.

**F-SV-6: Collection-time floor = 29.90s for 13,605 tests**
3-run median of `pytest --collect-only -q tests/`. CPU utilization 71-79% during
collection. CHANGE-T3A (parametrize-promote) would reduce collection overhead
proportional to test-count reduction (~73% of 295 function objects eliminated).
Source: Baseline §3 M-3.

**Initial expected grade per charter §6.1**: D (serial 374s stored = 6.2min maps
to B on raw time, but durations 14 days stale AND slowest CI shard 447s > 300s
threshold → D by weakest criterion). Entropy-assessor applies rubric definitively.

---

## §9 Findings — Parallelization Health (PERF OVERLAY)

Charter §6.2 grading rubric applies. Initial expected grade: **F**.

**F-PH-1: `--dist=loadfile` band-aid in `pyproject.toml:113` since 2026-04-10**
`addopts = "--dist=loadfile"` was added at commit `c5d2930d` (2026-04-10) as a
band-aid for module-level state in two specific files. Confirmed undrifted at
Baseline §5.
Source: Swarm Lane 1 §1; Swarm §4.1; Baseline §5 anchor 1.

**F-PH-2: 11 module-level singletons in `_reset_registry` at `system_context.py:28`**
`src/autom8_asana/core/system_context.py:28` defines
`_reset_registry: list[Callable[[], None]] = []` — a module-level global.
11 subsystems register reset callbacks. Full subsystem table:

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

Confirmed undrifted at Baseline §5.
Source: Swarm §4.2; Baseline §5 anchor 2.

**F-PH-3: Hypothesis DB at `~/.hypothesis/examples` is process-global with no per-worker isolation**
`test_openapi_fuzz.py:72-81` configures Hypothesis settings. Hypothesis DB
defaults to `~/.hypothesis/examples`, a process-global path. Under xdist
parallel workers, multiple workers compete for DB access.
Source: Swarm Lane 1 §4; Swarm §4.3 (unblock cost item 2).

**F-PH-4: `tests/test_openapi_fuzz.py:113-115` creates `app`/`schema` at module level**
Lines 113-115: `app = _create_fuzz_app()` and `schema = from_asgi("/openapi.json",
app=app)`. Module-level initialization means these objects are shared across
workers when the file is imported by multiple xdist processes.
Confirmed undrifted at Baseline §5.
Source: Swarm Lane 1 §5; Baseline §5 anchor 3.

**F-PH-5: 4 module-level `os.environ` mutations across conftests**
Four conftest files perform module-level `os.environ` mutations (not scoped to
fixtures). These create cross-test state pollution under parallel execution.
Source: Swarm Lane 1 §5.
Severity: MED (secondary hazard; not the primary blocker but amplifies xdist
instability risk under --dist=load). Canonical-category tag: PARALLELIZATION-HEALTH.

**F-PH-6: xdist worker distribution — top file holds 272 tests vs 23.9 mean**
Under `--dist=loadfile`, `test_insights_formatter.py` (272 tests) is 11.4× the
per-file mean (13,605 / ~570 = ~23.9). However, duration-axis imbalance is the
real worker-pinning bottleneck: `test_openapi_fuzz.py` holds 29.8% of total
duration on one worker (F-SV-4). Test-count imbalance for formatter file is
misleading because its 272 tests total only 0.23s stored duration.
Source: Baseline §3 M-6.

**Initial expected grade per charter §6.2**: F (loadfile band-aid + 11-singleton
structural blocker with > 5 registered singletons + 3-5× parallelism ceiling
unrealized → F by rubric row). Entropy-assessor applies rubric definitively.

---

## §10 Cross-Finding Correlations

The following compound severities represent cases where multiple findings
reinforce each other and should receive elevated weight in entropy-assessor
grading:

- **F-PH-2 + F-FH-3 + F-PH-1 (keystone compound)**: the 11 module-level
  singletons (F-PH-2) are the direct cause of the 300K reset-operation cost
  per run (F-FH-3), which is the direct cause of the `--dist=loadfile` band-aid
  (F-PH-1). These three findings are not independent — they are one structural
  chain. CHANGE-T1A (refactor `_reset_registry` to worker-local) is the single
  keystone that dissolves all three. Per charter §7.1 sequencing invariant.

- **F-SV-4 + F-PH-4 (highest-leverage near-term compound)**: `test_openapi_fuzz.py`
  is simultaneously the largest single-file duration (111.46s = 29.8% of stored
  total, F-SV-4) AND the source of the module-level app/schema state that blocks
  --dist=load transition (F-PH-4). CHANGE-T1C + CHANGE-T2A together target both
  dimensions: fixing module-level state (T1C) enables the file to run under
  --dist=load, while reducing `SCHEMATHESIS_MAX_EXAMPLES` (T2A) cuts its budget
  from 250s to ~50s. This is the highest-leverage compound in the engagement.

- **F-MD-1 + F-MD-3 (correctness debt, bounded pace impact)**: 97.8% unspec rate
  (F-MD-1) combined with 11 bespoke MockTask divergences (F-MD-3) represents
  correctness debt estimated at 2-8% pace impact (Swarm Lane 5 §7 + Swarm §7).
  These findings combine to indicate a mock-discipline culture gap, not just an
  isolated instance. Route to /hygiene per charter §10; do not act in perf-track
  Phase 3/4 unless they surface as residual bottleneck post-Tier-1.

- **F-SV-2 + CI overhead gap (CI improvement gated on /sre)**: slowest CI shard
  p50 = 447.0s (F-SV-2). Theoretical pytest-internal floor = ~94s. The ~353s gap
  is infrastructure overhead in `autom8y/autom8y-workflows/
  satellite-ci-reusable.yml@c88caabd` (Baseline §4 critical observation). Even
  if Tier-1+2 changes eliminate all pytest-internal cost above the 94s floor, CI
  shard duration will only drop by that ~94s delta, not by 353s. The dominant CI
  wall-clock saving requires /sre-track work on the reusable workflow.

---

## §11 Cross-Rite Routing Pre-Classification

Mirroring charter §10 routing, with finding IDs:

| Target rite | Finding IDs | Items |
|---|---|---|
| **/hygiene** | F-MD-1, F-MD-3, F-CG-3, F-CG-4 | Mock spec= adoption (97.8% unspec); MockTask consolidation (11 bespoke); uncovered packages (4); uncovered modules (9) |
| **/sre** | F-CG-1, F-CG-2, F-SV-2 (CI gap component), F-PH-6 (CI overhead attribution) | Coverage-threshold theater; missing post-merge aggregation; CI overhead gap ~353s; 4→8 shard expansion question |
| **/10x-dev** | (CP-01 carry-forward) | `tests/unit/lambda_handlers/test_import_safety.py` lazy-load regression guard per charter §10 — not in this inventory; named for routing completeness |

---

## §12 Findings the Entropy-Assessor Should Ignore

The following dimensions were explicitly closed by the Explore swarm. Phase-2
grading should not consume attention on them; they are not open questions.

- **Real I/O** (Swarm Lane 4 §5): zero network/redis/AWS calls in unit suite.
  All I/O is mocked correctly.
- **Asyncio overhead** (Swarm Lane 4 §8): bounded at 5-15s aggregate for
  ~2,000+ async tests. Not a primary lever.
- **Sleep blocking** (Swarm Lane 4 §1): `tests/unit/cache/test_memory_backend.py:15`
  uses `_fast_clock` fixture to patch `time.sleep`. Real blocking budget < 50s.
- **Skip/xfail collection cost** (Swarm Lane 4 §6): 20 xfail/skip sites;
  collection overhead is negligible.
- **Iteration-heavy `range(100)` loops** (Swarm Lane 4 §7): lightweight list
  construction, not compute. Not a cost driver.
- **Mock teardown discipline** (Swarm Lane 5 §6): 5.2:1 context-manager-to-
  decorator ratio is sound; no `patch.stopall()` debt. Closed positive.

---

## §13 Drift-Audit Attestation

Per charter §4.1 Pattern-6 carry-forward discipline: the 4 Tier-1 anchor
file:line targets were confirmed UNDRIFTED at baseline capture (2026-04-29,
Baseline §5). Confirmation is verbatim in that artifact:

| Anchor | File:Line | State at Baseline |
|---|---|---|
| `--dist=loadfile` addopts | `pyproject.toml:113` | CONFIRMED — exact text `addopts = "--dist=loadfile"` |
| `_reset_registry` module-level | `src/autom8_asana/core/system_context.py:28` | CONFIRMED — exact text `_reset_registry: list[Callable[[], None]] = []` |
| `app`/`schema` module-level | `tests/test_openapi_fuzz.py:113-115` | CONFIRMED — `app = _create_fuzz_app()` at 113; `schema = from_asgi(...)` at 115 |
| `reset_all_singletons` autouse | `tests/conftest.py:193-204` | CONFIRMED — `@pytest.fixture(autouse=True)` / `def reset_all_singletons():` / `SystemContext.reset_all()` / yield / `SystemContext.reset_all()` |

Inventory authorship adds zero further drift surface (read-only synthesis only).
Consolidation-planner MUST re-run drift-audit at planner dispatch per charter
§4.1 and §7.3.

---

## §14 Source Manifest

| Role | Artifact | Path |
|---|---|---|
| Governing charter | Pythia inaugural consult (perf-track) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md` |
| Swarm synthesis (5-lane opportunity map) | Lane 1 (parallelization blast radius) §1-4.3 | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/EXPLORE-SWARM-SYNTHESIS-perf-2026-04-29.md` |
| — | Lane 2 (fixture cost surface) §1, §5, §6 | same file |
| — | Lane 3 (CI shape and shard topology) §2, §3 | same file |
| — | Lane 4 (slow-tail pathology) §1-3, §5-9 | same file |
| — | Lane 5 (mock cost surface) §1, §3, §4, §6-7 | same file |
| Empirical baseline (rigor anchor) | Suite-internal M-1 through M-4, M-6 | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/BASELINE-test-perf-2026-04-29.md` |
| — | CI wallclock M-5 (5-run extraction) | same file |
| — | Tier-1 anchor drift audit §5 | same file |
| — | Triangulation notes §6 | same file |
| — | Phase-5 PASS gate anchors §7 | same file |
| Persistent knowledge (coverage gaps) | test-coverage.md (F-CG-3, F-CG-4, F-SA-1, F-SA-4, F-MD-3) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/test-coverage.md` |

---

*Inventory authored 2026-04-29 by test-cartographer. STRONG evidence-grade per
multi-source corroboration rule: STRONG-graded empirical baseline +
5-lane rite-disjoint Explore swarm. Synthesis only; no target-codebase files
modified. Drift-audit attestation carried forward from Baseline §5. Ready for
entropy-assessor Phase 2 consumption.*
