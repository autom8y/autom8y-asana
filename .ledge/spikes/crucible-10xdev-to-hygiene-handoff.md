---
type: handoff
status: complete
from_rite: 10x-dev
to_rite: hygiene
initiative: project-crucible
sprint_completed: 5
sprint_next: 6
created: 2026-04-15
agent: qa-adversary
role: initiative-measurement + cross-rite handoff producer
measurement_head: c0acf12f
---

# Cross-Rite Handoff: 10x-dev to Hygiene

## Handoff Summary

Project Crucible's 10x-dev phase (sprints 2-5) is complete. This handoff
transfers initiative state to the hygiene rite for sprint-6 (final verification).

**Throughline**: "autom8y-asana's test function count is reduced to ~5,000 without
dropping coverage below 80%, achieving CI wall-clock under 60 seconds with existing
4-shard infrastructure"

**Initiative status**: The throughline's quantitative targets were not met. The
initiative delivered genuine engineering improvements (scar safety, fixture cleanup,
framework waste removal, CI filter) but the test function count (12,320) is 2.2x
above the target range (4,500-5,500).

---

## Section 1: Measurement Summary

### Scorecard

| # | Criterion | Target | Actual | Verdict |
|---|-----------|--------|--------|---------|
| 1 | Test function count | 4,500 - 5,500 | 12,320 | FAIL |
| 2 | Coverage floor | >= 80% | 87.59% | PASS |
| 3 | CI wall-clock (4-shard) | < 60s | ~180-240s (est.) | FAIL |
| 4 | Parametrize rate | >= 8% | 1.06% | FAIL |
| 5 | Local fixture ratio | <= 50% | 92.5% | FAIL |
| 6 | MockCacheProvider ratio | <= 2:1 | 1.5:1 | PASS |
| 7 | 33 scar tests survive | 33/33 | 342 pass (all SCAR files) | PASS |
| 8 | @pytest.mark.slow PR exclusion | Excluded | Conditional PR-only | PASS |

**Score**: 4 PASS / 4 FAIL

### Key Numbers

- **Test functions**: 13,072 (pre-Crucible) -> 12,320 (current) = -752 (-5.8%)
- **Coverage**: 87.59% (>= 80% maintained throughout)
- **Parametrize decorators**: 112 -> 130 (+18)
- **MockCacheProvider**: 9:1 -> 1.5:1
- **SCAR tests**: 342 pass, 0 regressions
- **Crucible commits**: 35 (6 predecessor + 6 S1 + 13 S2 + 8 S3 + 8 S4)
- **Slow-marked tests**: 23 functions, correctly excluded from PR gate only

---

## Section 2: Commit Inventory by Sprint

### Predecessor (asana-test-rationalization): 6 commits
```
4af13bda CHANGE-001 — move schemathesis xdist patch to pytest_configure hook
8ed4e601 CHANGE-002 — convert test_workflow_handler.py sync tests to async
affbf5a5 CHANGE-003 — re-enable xdist parallel execution
af32c278 CHANGE-004 — install pytest-split, generate .test_durations, 4-shard CI
b25023e2 CHANGE-006 — apply WS-gamma stash (BLE001 enforcement)
51fd809d CHANGE-007 — remove 2,588 redundant @pytest.mark.asyncio markers
```

### Sprint-1 (hygiene: fixture topology): 6 commits
```
f0231b98 RF-001 — remove unused MockClientBuilder (80 lines)
778ba707 RF-002 — fix S9 double-reset in api/conftest.py
03e54aa7 RF-003 — extend shared MockCacheProvider with get_metrics()
28b1375d RF-004 — create CacheDomainMockProvider in cache/conftest.py
f22b0066 RF-005 — consolidate persistence/ MockCacheProvider variants
5b4565d3 RF-006 — add client_factory fixture to clients/conftest.py
```

### Sprint-2 (hygiene: framework waste removal): 13 commits
```
4b139a88 CRU-S2-001 — remove framework-testing waste from test_models.py
a17c23ec CRU-S2-002 — remove framework-testing waste from test_common_models.py
e81eeca3 CRU-S2-003 — remove framework-testing waste from test_base.py
d2fb8fcd CRU-S2-004 — remove framework-testing waste from test_activity.py
5d8bfc86 CRU-S2-005 — remove framework-testing waste from test_unit.py and test_offer.py
084f4db6 CRU-S2-006 — remove framework-testing waste from test_resolution.py
4d5fdb01 CRU-S2-007 — remove framework-testing waste from test_business.py
a38cf250 CRU-S2-008 — remove framework-testing waste from test_seeder.py
1194b1a1 CRU-S2-009 — remove framework-testing waste from test_process.py
ac2e5048 CRU-S2-010 — remove framework-testing waste from test_contact.py, test_location.py, test_hours.py
1e8708c5 CRU-S2-011 — remove framework-testing waste from test_asset_edit.py
ffcbe7a1 CRU-S2-012 — remove framework-testing waste from test_patterns.py
8a0bab6a CRU-S2-013 — remove framework-testing waste from client test files
```

### Sprint-3 (10x-dev: parametrize tier1/tier2): 8 commits
```
f71528f8 CRU-S3-002 — parametrize tier1 get_async raw (3->1)
3ee4965c CRU-S3-003 — parametrize tier1 get sync (3->1)
7a9bbdb8 CRU-S3-004 — parametrize tier1 list_async (3->1)
c2dc6111 CRU-S3-005 — parametrize tier1 model imports (7->1)
8539ef35 CRU-S3-006 — parametrize users me_async raw (2->1)
ead47d10 CRU-S3-007 — parametrize tier1 memberships + add_task (4->2)
3337c2bb CRU-S3-010 — parametrize tier2 get_async model (7->1)
105e26a2 CRU-S3-011 — parametrize tier2 create_async model (4->1)
```

### Sprint-4 (10x-dev: extended parametrize + CI filter): 8 commits
```
4103330f CRU-S4-001 — exclude slow from PR gate
3897180e CRU-S4-002 — parametrize tasks get_async raw (2->1)
1e3ddc35 CRU-S4-003 — parametrize tasks get_sync raw (2->1)
d906c967 CRU-S4-004 — parametrize tasks create_async raw (2->1)
3ee4c04c CRU-S4-005 — parametrize tasks update_async raw (2->1)
98bc19cb CRU-S4-006 — parametrize tasks sync wrappers raw (4->2)
2e5cb573 CRU-S4-007 — parametrize cache TTL boundary cases (6->1)
c0acf12f CRU-S4-001b — make @pytest.mark.slow exclusion PR-only (DEF-S4-001 fix)
```

### Sprint-5 (10x-dev: measurement): 0 code commits

---

## Section 3: Deferred Track C Packages

The shape file's sprint-4 planned "extended parametrize across 5 packages."
Sprint-4 executed micro-audit on cache/ only (1 PROCEED out of 32 functions
audited) and focused Track B on test_tasks_client.py. The following packages
were deferred with documented rationale:

### dataframes/ (1,170 test functions)
- **Scar density**: HIGH (SCAR-005, SCAR-006, SCAR-007 regression tests)
- **Micro-audit status**: NOT STARTED
- **Pre-audit signals**: High genuine diversity expected (builders, validators, extractors each have distinct testing patterns)
- **Parametrize candidates**: Likely few -- cascade validator tests are scar-intentional structure

### automation/ (1,110 test functions)
- **Scar density**: LOW
- **Micro-audit status**: NOT STARTED
- **Pre-audit signals**: Sprint-4 spot-check found `test_polling_scheduler.py` with for-loop timezone test (natural parametrize candidate). Suggests moderate opportunity.
- **Parametrize candidates**: Moderate (polling, workflows, pipelines have structural repetition)

### persistence/ (982 test functions)
- **Scar density**: HIGH (SCAR-010, SCAR-010b, session concurrency)
- **Micro-audit status**: NOT STARTED
- **Pre-audit signals**: Bespoke mock environments for scar tests; consolidation requires careful analysis
- **Parametrize candidates**: Low to moderate (scar-heavy territory)

### core/ (355 test functions)
- **Scar density**: VERY HIGH (entity registry, project registry, retry)
- **Micro-audit status**: NOT STARTED
- **Pre-audit signals**: Scar regression tests dominate this package
- **Parametrize candidates**: Very low (most tests are intentionally distinct scar gates)

### cache/ remaining (1,296 test functions, excluding TTL edge cases already done)
- **Scar density**: MODERATE (SCAR-004 adjacent)
- **Micro-audit status**: PARTIAL (test_entry.py audited; 31 other files not audited)
- **Pre-audit signals**: Sprint-4 micro-audit found high genuine diversity
- **Parametrize candidates**: Low based on test_entry.py micro-audit extrapolation

---

## Section 4: Open Items

### 4.1 RF-007: Local Fixture Promotion (DEFERRED)
- **Current**: 590 local fixtures / 638 total = 92.5%
- **Target**: <= 350 local / ~50% ratio
- **Status**: Identified in sprint-1 as needing methodology redesign. Never executed.
- **Approach needed**: Automated analysis of which local fixtures are consumed by multiple
  test functions within the same file (promotion candidates) vs. single-consumer fixtures
  (leave local). The 240-fixture reduction target requires promoting ~40% of local fixtures.
- **Risk**: Bulk promotion without adoption analysis could create conftest bloat.

### 4.2 SCAR-026: spec= Enforcement (~4,561 MagicMock instances)
- **Status**: Cataloged in sprint-2 behavior audit but not executed in any sprint.
- **Nature**: Adding `spec=` to MagicMock instances is additive (improves correctness
  without reducing function count). It does not contribute to the throughline.
- **Scope**: 4,561 MagicMock usages across the test suite. Bulk conversion is
  mechanically straightforward but requires verification that spec= does not
  break tests relying on permissive mock attributes.

### 4.3 S10: OpenAPI Contract Debt (47 xfail-masked violations)
- **Status**: Pre-existing. Documented in `tests/test_openapi_fuzz.py:30-56`.
- **Nature**: 47 schemathesis contract violations masked by module-level `xfail`.
  Categories: RejectedPositiveData, httpx.InvalidURL (control chars), UnsupportedMethodResponse,
  IgnoredAuth, AcceptedNegativeData.
- **Routing**: This is an architecture concern (OpenAPI spec vs implementation contract),
  not a test rationalization item. Should route to an architect rite.

### 4.4 Track C Extended Parametrize Residue
- **Status**: 5 packages (dataframes/, automation/, persistence/, core/, cache/) were
  not micro-audited for parametrize opportunity.
- **Estimated opportunity**: Based on sprint-3/4 experience (15-35% reduction per
  micro-audited file, with most files at the low end), optimistic estimate is
  ~500-1,000 function reduction across all 5 packages. This would bring the count
  to ~11,300-11,800 -- still far above the 5,500 target.
- **Assessment**: Parametrize alone cannot achieve the throughline target. The
  remaining ~7,000 functions would require either (a) discovering that the
  copy-paste hypothesis holds in unaudited packages (unlikely given sprint-3/4
  evidence), or (b) fundamentally different reduction strategies (e.g., test
  generation from OpenAPI spec, property-based testing replacing example-based tests).

### 4.5 Sprint-5 Shape Exit Criteria Not Met
- The shape file's sprint-5 mission was "test taxonomy -- add @pytest.mark.fast markers,
  fix the @pytest.mark.slow CI filter gap, and configure the fast-only PR gate."
- Only the slow CI filter fix was implemented (CRU-S4-001b).
- @pytest.mark.fast markers were NOT added.
- Fast-only PR gate was NOT configured.
- Sprint-5 was repurposed as a measurement sprint rather than a taxonomy sprint.

---

## Section 5: Sprint-6 Mission (Hygiene Verification)

Sprint-6 is the final hygiene sprint per the shape file. Its mission:

1. **Re-run full measurement**: Independent verification of all metrics from this report
2. **Verify CI green on GitHub Actions**: Confirm the full suite passes in actual CI
   (not just local), including slow tests on push-to-main
3. **Compute wall-clock from actual CI runs**: Measure wall-clock from 3 consecutive
   GitHub Actions runs (the shape file requires "3 consecutive GitHub Actions runs")
4. **Produce permanent `.ledge/reviews/crucible-verification-report.md`**: This is
   the permanent initiative artifact. The sprint-5 measurement report (.sos/wip/) is
   ephemeral; the sprint-6 report (.ledge/reviews/) is permanent.
5. **Entropy delta**: Compute before/after for signal classes S12-S17 per shape file
6. **Issue final verdict**: PASS, CONDITIONAL-PASS, or FAIL per shape file criteria

### Inputs for sprint-6
- This handoff artifact
- Sprint-5 measurement report at `.sos/wip/crucible/sprint-5-measurement-report.md`
- All sprint artifacts in `.sos/wip/crucible/`
- Shape file at `.sos/wip/frames/project-crucible-17-second-frontier.shape.md`

### Expected verdict guidance from shape file
> "A CONDITIONAL-PASS is acceptable if function count is in range and coverage is
> maintained but CI wall-clock is between 60-120 seconds. A FAIL requires the
> function count or coverage to be outside bounds."

Given that function count (12,320) is outside bounds, the expected sprint-6 verdict
is **FAIL** on the throughline's quantitative criteria. However, the initiative
delivered genuine engineering improvements that should be documented in the
permanent report.

---

## Section 6: Session Transition

To resume with hygiene rite:
1. Restart Claude Code with hygiene rite context
2. `/sos resume` to restore session state
3. Load this handoff: `Read(".ledge/spikes/crucible-10xdev-to-hygiene-handoff.md")`
4. Load measurement report: `Read(".sos/wip/crucible/sprint-5-measurement-report.md")`
5. Execute sprint-6 per shape file exit criteria

---

## Section 7: Honest Assessment

### Where the initiative stands vs the throughline

The throughline is **not met**. Four of eight success criteria fail. The most
important failure is the test function count (12,320 vs 4,500-5,500 target),
which cascades into the wall-clock and parametrize rate failures.

### What was achieved

The initiative delivered three categories of genuine value:

1. **Safety infrastructure** (zero scar regressions across 35 commits). This
   established the discipline of micro-audit before modification, scar-sweep
   verification after every commit, and structured deferral when risk exceeds
   benefit. This methodology survives the initiative.

2. **Fixture architecture cleanup** (MockCacheProvider 9:1 to 1.5:1, S9 double-reset
   fix, MockClientBuilder removal, client_factory addition). These are permanent
   improvements to the test architecture that reduce confusion and maintenance burden.

3. **CI filter configuration** (slow exclusion with correct PR-only conditional,
   xdist enabled, 4-shard matrix). The CI infrastructure is correctly configured
   for the test suite's current size.

### What was aspirational

The throughline's quantitative targets were based on the hypothesis that ~60% of
test functions were consolidatable copy-paste. The micro-audit process in sprints
3 and 4 empirically tested this hypothesis and found it to be false. The actual
consolidation rate was 15-35% per file for the best candidates, and many files
had near-zero consolidation opportunity.

The initiative correctly pivoted from "hit the number" to "follow the micro-audit
evidence." This was the right engineering decision. The throughline was aspirational;
the micro-audit findings are empirical.

### What a corrected throughline would look like

Based on the empirical evidence from sprints 3 and 4:
- **Achievable function count**: ~10,000-11,000 (with full Track C micro-audit across all 5 deferred packages)
- **Achievable parametrize rate**: ~2-3% (based on actual consolidation ratios)
- **Achievable wall-clock**: ~120-180s (4-shard, with reduced function count)
- **Local fixture ratio**: requires separate initiative (bulk promotion analysis)

The original throughline assumed a 2.5x reduction. The evidence supports a 1.2-1.3x
reduction via parametrize alone. Reaching the original target would require
fundamentally different strategies (property-based testing, test generation,
large-scale test deletion with explicit coverage acceptance).
