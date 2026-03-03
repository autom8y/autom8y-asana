---
type: audit
---
# SLOP-CHOP-DEEP Gate Verdict

**Phase**: 5 — Verdict
**Specialist**: gate-keeper
**Date**: 2026-02-25
**Scope**: `src/autom8_asana/` + `tests/` + `src/autom8_query_cli.py`
**Complexity**: MODULE+ (all five phases executed)
**Initiative Context**: Post ASANA-HYGIENE + REM-ASANA-ARCH + REM-HYGIENE + COMPAT-PURGE
**Test Baseline**: 11,655 passed, 0 failed

---

## VERDICT: CONDITIONAL-PASS

**Exit Code**: 0
**Blocking Findings**: 4 (all have clear remediation paths, effort < 1 sprint combined)
**Advisory Findings**: 15 (10 logic/test/code + 6 temporal, including 2 deferred and 2 cross-rite referrals)
**Auto-Fixable Blocking Findings**: 1 of 4 (WS-DEPS / HH-DEEP-002)
**Manual Blocking Findings**: 3 of 4 (WS-HEALTH-MOCK, WS-METRICS x2)

All four blocking findings have unambiguous remediation paths with a combined effort of 2–3 days. No finding requires architectural decisions or external dependencies. The codebase is structurally sound after four major initiatives; the blocking findings are contained to a single test file and a single CLI module.

---

## Blocking Findings — Evidence Chains

### Blocking Finding 1: Undeclared PyYAML production dependency (HH-DEEP-002)

- **Detection**: HH-DEEP-002 — `import yaml` appears at module level in 3 production files (`lifecycle/config.py:24`, `automation/polling/config_loader.py:30`, `query/saved.py:16`). `pyproject.toml` `[project.dependencies]` does not declare `pyyaml`. `uv.lock` confirms PyYAML is only present as a transitive dependency of `moto` (dev extra only).
- **Analysis**: N/A (detection finding — dependency manifest verification, not behavioral analysis)
- **Decay**: N/A
- **Remedy**: WS-DEPS (AUTO) — Insert `"pyyaml>=6.0.0"` into `pyproject.toml` `[project.dependencies]`, run `uv lock`. Effort: 5 minutes.
- **Production Impact**: `ImportError: No module named 'yaml'` on clean-environment deployment for `autom8-query run <name>` (CLI), lifecycle YAML config parsing on service startup, and polling config loader when polling mode is activated. Failure is silent in dev/test environments where `moto` installs PyYAML transitively.

### Blocking Finding 2: Fragile mock target in health check tests (HH-DEEP-001)

- **Detection**: HH-DEEP-001 (HIGH / PROBABLE) — 6 tests in `tests/unit/api/test_health.py` (lines 274, 289, 304, 319, 328, 342) patch `"httpx.AsyncClient.get"` at the httpx class level. Production code in `api/routes/health.py:176-182` wraps all JWKS HTTP calls through `Autom8yHttpClient`, not direct `httpx`.
- **Analysis**: Runtime introspection confirmed the tests work today because `autom8y_http` re-exports httpx exceptions directly and `raw()` returns a plain `httpx.AsyncClient`. HIGH severity because: (a) patch bypasses `Autom8yHttpClient` entirely — any exception-wrapping change silently invalidates the exception-path branches, (b) breaks if `raw()` ever returns a subclass or proxy, (c) contradicts the canonical mock pattern established by H-001/H-002 fixes in REM-HYGIENE.
- **Decay**: N/A
- **Remedy**: WS-HEALTH-MOCK (MANUAL) — Replace all 6 `patch("httpx.AsyncClient.get")` calls with `patch("autom8_asana.api.routes.health.Autom8yHttpClient")` and wire the three-level async context manager chain. Template provided in remedy-plan. Reference: `tests/unit/clients/data/test_client.py` (established pattern from H-001 fix). Effort: 2–4 hours.
- **Files**: `tests/unit/api/test_health.py` lines 274, 289, 304, 319, 328, 342

### Blocking Finding 3: Metrics CLI dollar-sign format hardcoded for all aggregations (LS-DEEP-001)

- **Detection**: N/A (logic analysis finding)
- **Analysis**: LS-DEEP-001 (HIGH / HIGH confidence) — `src/autom8_asana/metrics/__main__.py:102` unconditionally formats all aggregation output as `${total:,.2f}` regardless of `MetricExpr.agg`. `count` aggregation produces an integer row count (not a dollar amount) but displays as `$42.00`. Current production metrics use `agg="sum"` on financial columns, masking the bug. The `MetricRegistry` is designed to accept arbitrary metrics; any `count` metric registered now or in future will silently produce incorrect output.
- **Decay**: N/A
- **Remedy**: WS-METRICS (MANUAL) — Replace lines 95–102 in `src/autom8_asana/metrics/__main__.py` to branch on `metric.expr.agg`: `count` formats as integer `{int(total):,}`, others format as `${total:,.2f}`. Add None guard for `mean`/`min`/`max` on empty DataFrames (see Blocking Finding 4). Effort: 4–6 hours including tests.
- **File**: `src/autom8_asana/metrics/__main__.py:102`

### Blocking Finding 4: Metrics CLI crash on empty DataFrame with mean/min/max aggregation (LS-DEEP-002)

- **Detection**: N/A (logic analysis finding)
- **Analysis**: LS-DEEP-002 (HIGH / MEDIUM confidence) — `src/autom8_asana/metrics/__main__.py:95-102` calls `getattr(result[col], agg)()` then passes the result directly to `f"${total:,.2f}"`. When the DataFrame is empty, `mean()`, `min()`, and `max()` return `None`. The format string `{None:,.2f}` raises `TypeError: unsupported format character`. `MetricExpr.__post_init__` validates `agg` against `SUPPORTED_AGGS = frozenset({"sum", "count", "mean", "min", "max"})`, confirming `mean`/`min`/`max` are supported and reachable code paths. Current production metrics use `agg="sum"` which returns `0` on empty, masking the crash.
- **Decay**: N/A
- **Remedy**: WS-METRICS (MANUAL, same workstream as LS-DEEP-001) — Add `if total is None: formatted = "N/A (no data)"` guard before the format string. Remedy-plan provides the full replacement block at `src/autom8_asana/metrics/__main__.py:95-102`. Add tests: `test_count_metric_formats_as_integer` and `test_empty_dataframe_mean_returns_no_data`. Effort: included in the 4–6 hour WS-METRICS estimate.
- **File**: `src/autom8_asana/metrics/__main__.py:95-102`

---

## Remediation Requirements Before PASS

The following must be completed before this verdict converts to PASS:

1. **WS-DEPS** (AUTO, 5 min): Add `"pyyaml>=6.0.0"` to `pyproject.toml` `[project.dependencies]`, run `uv lock`. Verify `uv lock` shows pyyaml under autom8y-asana's direct dependencies.

2. **WS-HEALTH-MOCK** (MANUAL, 2–4 hrs): Rework 6 mock sites in `tests/unit/api/test_health.py` to patch `"autom8_asana.api.routes.health.Autom8yHttpClient"` with proper three-level async context manager wiring. All health tests must pass after changes.

3. **WS-METRICS** (MANUAL, 4–6 hrs): Replace lines 95–102 in `src/autom8_asana/metrics/__main__.py` to fix format routing and add None guard. Add 2 targeted tests in `tests/unit/metrics/`. All metrics tests must pass.

Combined total: ~2–3 days. All three workstreams are independent and can be parallelized.

---

## Advisory Findings Summary

The following findings do not block merge. They are documented for follow-on action.

### Advisory: Auto-fixable (execute in WS-TEST-QUALITY and WS-TEMPORAL)

| ID | Severity | File | Description |
|----|----------|------|-------------|
| LS-DEEP-004 | MEDIUM | `tests/unit/metrics/test_adversarial.py:183,190`; `tests/unit/query/test_saved_queries.py:188,201`; `tests/unit/query/test_adversarial_hierarchy.py:248`; `tests/unit/query/test_adversarial.py:1135` | 6 occurrences of `pytest.raises(Exception)` where comments document the correct specific type. Tighten to `ColumnNotFoundError`, `SchemaError`, or `ValidationError`. |
| LS-DEEP-009 | LOW | `src/autom8_asana/query/__main__.py:452` | `isinstance(error, (OSError, PermissionError))` is redundant — `PermissionError` is a subclass of `OSError`. Remove `PermissionError` from the tuple. Behavior is correct; change is cosmetic. |
| CC-DEEP-001..006 | TEMPORAL | Multiple (see decay-report) | Initiative-tag docstrings (`REM-ASANA-ARCH WS-DFEX`, `TDD-SPRINT-3-DETECTION-DECOMPOSITION`, `SPIKE-BREAK-CIRCULAR-DEP`) and dead freshness aliases (`FreshnessClassification`, `FreshnessStatus`, `FreshnessMode`) with zero active callers. Pure comment/alias removal, no behavioral change. |

### Advisory: Manual (address in WS-QUERY)

| ID | Severity | File | Description |
|----|----------|------|-------------|
| LS-DEEP-003 | MEDIUM | `src/autom8_asana/query/__main__.py:273-372` | `execute_live_rows` and `execute_live_aggregate` are near-identical copy-paste (~45 LOC, 4 token delta). Extract `_execute_live` helper. Maintenance burden only. |
| LS-DEEP-008 | LOW | `src/autom8_asana/query/__main__.py:477-482` | `_get_output_stream` opens a file handle and returns it bare. All current callers use `try/finally` correctly. Latent leak risk if future caller opens stream before query execution. Convert to context manager or document caller contract. |
| LS-DEEP-010 | LOW | `src/autom8_asana/query/__main__.py:994-1008` | `list-queries` discovery silently swallows all exceptions. A YAML syntax error in a saved query file produces no user-visible diagnostic. Narrow `except Exception` to `(YAMLError, JSONDecodeError, ValidationError)` and log warnings for other exceptions. |

### Advisory: Deferred (with triggers)

| ID | Severity | Description | Trigger |
|----|----------|-------------|---------|
| LS-DEEP-005 / RS-021 | MEDIUM | `HierarchyAwareResolver.resolve_batch` cache miss (`fetch_count=4`, expected `2`) is in `autom8y_cache` library, not this repo. Skip annotation with external attribution is appropriate. | File upstream issue on `autom8y-cache`, then update skip reason with issue URL. |
| LS-DEEP-006 / D-015 | MEDIUM | `_extract_vertical_id` and `_extract_max_pipeline_stage` always return `None`. Schema advertises fields as available; CLI `fields unit` output is misleading. Interim: update schema descriptions to say `"Planned: stub returns None pending Vertical/UnitHolder model access"`. Full implementation requires Vertical + UnitHolder model access. | Vertical model and UnitHolder model become accessible from extractor context. |

---

## CI Output

```json
{
  "verdict": "CONDITIONAL-PASS",
  "exit_code": 0,
  "pass": "2026-02-25",
  "scope": "MODULE+",
  "initiative": "SLOP-CHOP-DEEP",
  "test_baseline": {
    "passed": 11655,
    "failed": 0
  },
  "summary": {
    "total_findings": 19,
    "blocking": 4,
    "advisory": 15,
    "auto_fixable_blocking": 1,
    "manual_blocking": 3,
    "deferred": 2,
    "by_category": {
      "hallucination_dependency_drift": 1,
      "hallucination_fragile_mock": 1,
      "logic_error": 2,
      "test_degradation": 1,
      "copy_paste_bloat": 1,
      "security_anti_pattern": 1,
      "file_handle_pattern": 1,
      "silent_exception_swallow": 1,
      "external_library_cache_miss": 1,
      "always_null_stubs": 1,
      "temporal_debt": 6
    }
  },
  "blocking_findings": [
    {
      "id": "HH-DEEP-002",
      "severity": "MEDIUM",
      "confidence": "DEFINITE",
      "category": "dependency-drift",
      "description": "PyYAML imported in 3 production files; not declared in pyproject.toml [project.dependencies]",
      "files": [
        "src/autom8_asana/lifecycle/config.py:24",
        "src/autom8_asana/automation/polling/config_loader.py:30",
        "src/autom8_asana/query/saved.py:16"
      ],
      "remedy": "WS-DEPS (AUTO) -- add pyyaml>=6.0.0 to pyproject.toml, run uv lock",
      "effort": "5 minutes"
    },
    {
      "id": "HH-DEEP-001",
      "severity": "HIGH",
      "confidence": "PROBABLE",
      "category": "orphaned-mock",
      "description": "6 health check tests patch httpx.AsyncClient.get at class level, bypassing Autom8yHttpClient abstraction",
      "files": [
        "tests/unit/api/test_health.py:274",
        "tests/unit/api/test_health.py:289",
        "tests/unit/api/test_health.py:304",
        "tests/unit/api/test_health.py:319",
        "tests/unit/api/test_health.py:328",
        "tests/unit/api/test_health.py:342"
      ],
      "remedy": "WS-HEALTH-MOCK (MANUAL) -- rework to patch autom8_asana.api.routes.health.Autom8yHttpClient",
      "effort": "2-4 hours"
    },
    {
      "id": "LS-DEEP-001",
      "severity": "HIGH",
      "confidence": "HIGH",
      "category": "logic-error",
      "description": "Metrics CLI hardcodes dollar-sign formatting for all aggregations including count",
      "files": [
        "src/autom8_asana/metrics/__main__.py:102"
      ],
      "remedy": "WS-METRICS (MANUAL) -- branch on metric.expr.agg; format count as integer",
      "effort": "4-6 hours including tests"
    },
    {
      "id": "LS-DEEP-002",
      "severity": "HIGH",
      "confidence": "MEDIUM",
      "category": "logic-error",
      "description": "Metrics CLI crashes with TypeError when mean/min/max aggregation returns None on empty DataFrame",
      "files": [
        "src/autom8_asana/metrics/__main__.py:95-102"
      ],
      "remedy": "WS-METRICS (MANUAL) -- add None guard before format string; display N/A (no data)",
      "effort": "included in WS-METRICS estimate"
    }
  ],
  "advisory_findings": [
    {
      "id": "LS-DEEP-003",
      "severity": "MEDIUM",
      "description": "execute_live_rows / execute_live_aggregate are near-identical copy-paste (~45 LOC)",
      "workstream": "WS-QUERY (MANUAL)"
    },
    {
      "id": "LS-DEEP-004",
      "severity": "MEDIUM",
      "description": "6 occurrences of pytest.raises(Exception) in new test modules; specific types documented in comments",
      "workstream": "WS-TEST-QUALITY (AUTO)"
    },
    {
      "id": "LS-DEEP-005",
      "severity": "MEDIUM",
      "description": "RS-021: HierarchyAwareResolver.resolve_batch cache miss is in autom8y-cache library, not this repo",
      "workstream": "DEFERRED -- file upstream issue, update skip reason"
    },
    {
      "id": "LS-DEEP-006",
      "severity": "MEDIUM",
      "description": "D-015: vertical_id and max_pipeline_stage always return None; schema advertises fields as available",
      "workstream": "DEFERRED -- interim schema description update + full implementation trigger"
    },
    {
      "id": "LS-DEEP-007",
      "severity": "MEDIUM",
      "description": "Saved query path loading lacks symlink/traversal guard; low risk in CLI context, HIGH if exposed via API",
      "workstream": "REFERRAL -- security rite"
    },
    {
      "id": "LS-DEEP-008",
      "severity": "LOW",
      "description": "_get_output_stream file handle leak pattern; latent risk for future callers",
      "workstream": "WS-QUERY (MANUAL)"
    },
    {
      "id": "LS-DEEP-009",
      "severity": "LOW",
      "description": "PermissionError redundant in isinstance(error, (OSError, PermissionError)); PermissionError is OSError subclass",
      "workstream": "WS-TEST-QUALITY (AUTO)"
    },
    {
      "id": "LS-DEEP-010",
      "severity": "LOW",
      "description": "list-queries discovery silently swallows all exceptions; YAML syntax errors produce no user diagnostic",
      "workstream": "WS-QUERY (MANUAL)"
    },
    {
      "id": "CC-DEEP-001",
      "severity": "TEMPORAL",
      "description": "REM-ASANA-ARCH WS-DFEX initiative tags in module docstrings (6 files)",
      "workstream": "WS-TEMPORAL (AUTO)"
    },
    {
      "id": "CC-DEEP-002",
      "severity": "TEMPORAL",
      "description": "TDD-SPRINT-3-DETECTION-DECOMPOSITION tags across all 8 detection package files",
      "workstream": "WS-TEMPORAL (AUTO)"
    },
    {
      "id": "CC-DEEP-003",
      "severity": "TEMPORAL",
      "description": "FreshnessClassification alias with zero active callers (post-consolidation)",
      "workstream": "WS-TEMPORAL (AUTO)"
    },
    {
      "id": "CC-DEEP-004",
      "severity": "TEMPORAL",
      "description": "FreshnessStatus alias with zero active callers (post-consolidation)",
      "workstream": "WS-TEMPORAL (AUTO)"
    },
    {
      "id": "CC-DEEP-005",
      "severity": "TEMPORAL",
      "description": "FreshnessMode alias in __all__ with zero active callers; interview resolution: REMOVE",
      "workstream": "WS-TEMPORAL (AUTO)"
    },
    {
      "id": "CC-DEEP-006",
      "severity": "TEMPORAL",
      "description": "SPIKE-BREAK-CIRCULAR-DEP initiative tags in 2 test file headers; prior strip commit missed these",
      "workstream": "WS-TEMPORAL (AUTO)"
    },
    {
      "id": "LS-009-024",
      "severity": "MEDIUM",
      "description": "16 copy-paste test clusters from P1 remain (test_unit_schema, test_normalizers, test_pii); ~600-800 LOC",
      "workstream": "REFERRAL -- hygiene rite"
    }
  ],
  "cross_rite_referrals": [
    {
      "target_rite": "security",
      "finding": "LS-DEEP-007",
      "concern": "query/saved.py:94-114 accepts user-provided file paths without containment to expected directories. yaml.safe_load and Pydantic validation mitigate deserialization attacks but not file-read scope. Low risk in current CLI-only context; HIGH if run subcommand is ever exposed via API or web interface."
    },
    {
      "target_rite": "hygiene",
      "finding": "LS-009-024",
      "concern": "16 copy-paste test clusters deferred from P1 remain: test_unit_schema.py (10 column-existence tests), test_normalizers.py (9 normalization tests), test_pii.py (5 phone masking tests). Tests are functionally correct. Parametrization would reduce ~600-800 LOC. Maintenance burden only."
    }
  ]
}
```

---

## PR Comment Body

```
## SLOP-CHOP-DEEP Quality Gate: CONDITIONAL-PASS

**Verdict**: CONDITIONAL-PASS | **Exit Code**: 0 | **Date**: 2026-02-25

All 4 blocking findings have clear remediation paths (combined effort ~2-3 days). No architectural decisions required. The codebase is structurally sound; findings are contained to `pyproject.toml`, one test file, and one CLI module.

### Blocking Findings (must resolve before PASS)

| ID | Severity | File | Description | Remedy |
|----|----------|------|-------------|--------|
| HH-DEEP-002 | MEDIUM | `pyproject.toml` | PyYAML undeclared in production deps; `ImportError` on clean deployment | AUTO: add `pyyaml>=6.0.0`, `uv lock` |
| HH-DEEP-001 | HIGH | `tests/unit/api/test_health.py:274-342` | 6 health tests patch `httpx.AsyncClient.get` (bypasses `Autom8yHttpClient`); silent failure risk on any `autom8y_http` version change | MANUAL: rework to `patch("autom8_asana.api.routes.health.Autom8yHttpClient")` |
| LS-DEEP-001 | HIGH | `metrics/__main__.py:102` | Hardcoded `$` format for all aggregations; `count` metrics display as `$42.00` | MANUAL: branch on `metric.expr.agg` |
| LS-DEEP-002 | HIGH | `metrics/__main__.py:95-102` | `TypeError` crash when `mean`/`min`/`max` aggregation runs on empty DataFrame | MANUAL: add `None` guard; display `N/A (no data)` |

### Advisory (no gate impact)

- **WS-TEST-QUALITY (AUTO)**: 6 `pytest.raises(Exception)` -- narrow to specific types. 1 redundant `PermissionError` in isinstance.
- **WS-TEMPORAL (AUTO)**: 6 temporal debt items -- initiative tags (`REM-ASANA-ARCH WS-DFEX`, `TDD-SPRINT-3-DETECTION-DECOMPOSITION`, `SPIKE-BREAK-CIRCULAR-DEP`) and dead freshness aliases (`FreshnessClassification`, `FreshnessStatus`, `FreshnessMode`).
- **WS-QUERY (MANUAL)**: `execute_live_rows`/`execute_live_aggregate` copy-paste, file handle pattern, silent exception swallow in `list-queries`.
- **Deferred**: RS-021 cache miss in `autom8y_cache` (upstream issue needed). D-015 always-null stubs (interim schema description update).
- **Referrals**: security (path loading in `query/saved.py`), hygiene (16 copy-paste test clusters from P1).

### Trend

This pass (SLOP-CHOP-DEEP) is a significant improvement over P1 (SLOP-CHOP-TESTS-P1, 2026-02-23):
- P1: 28 DEFECT findings, 13 blocking, CONDITIONAL-PASS
- DEEP: 4 blocking, 0 CRITICAL, no phantom imports, COMPAT-PURGE orphan sweep clean

Four initiatives resolved all P1 blocking items and reduced overall debt density substantially.
```

---

## Trend Analysis

### P1 vs DEEP Comparison

| Metric | SLOP-CHOP-TESTS-P1 (2026-02-23) | SLOP-CHOP-DEEP (2026-02-25) | Delta |
|--------|----------------------------------|------------------------------|-------|
| Total findings | 28 | 19 | -9 |
| Blocking | 13 | 4 | -9 |
| CRITICAL | 0 | 0 | 0 |
| HIGH (blocking) | 10 | 3 | -7 |
| Phantom imports resolved | 2 (H-001, H-002) | 0 new phantoms | clean |
| Test baseline | 11,121 passed | 11,655 passed | +534 |
| Verdict | CONDITIONAL-PASS | CONDITIONAL-PASS | same tier |

### Debt Trajectory

**Improving.** The codebase is demonstrably reducing technical debt across successive slop-chop passes.

- All 13 P1 blocking items were resolved by the four intervening initiatives (confirmed by carry-forward checks in detection and analysis reports).
- COMPAT-PURGE eliminated 27 backward-compatibility shims and re-exports; the orphan sweep found zero surviving references to removed symbols.
- REM-ASANA-ARCH broke 6 of 13 bidirectional import cycles; the import surface is cleaner.
- P1 broad-exception-assertion findings (LS-025, LS-026, LS-027) were partially resolved by REM-HYGIENE; 6 new occurrences appeared in AUTOM8_QUERY / metrics test modules (LS-DEEP-004), indicating test hygiene discipline is inconsistent in new modules.
- New blocking findings (LS-DEEP-001, LS-DEEP-002) are concentrated in the metrics CLI — a new module introduced during ASANA_DATA initiative. These represent first-pass quality gaps in new code, not regressions in existing code.

**Temporal debt density**: LOW. Only 6 temporal findings across a codebase with 4 major recent initiatives. The codebase has an active convention of stripping initiative tags post-completion (commit `0a85d67`); the detected remnants are cleanup misses.

**Accumulation risk areas**:
- New CLI modules (`query/__main__.py`, `metrics/__main__.py`) are accumulating advisory-level issues (copy-paste, broad exception swallow, format assumptions) that should be addressed before they become structural patterns. Route to hygiene rite.
- `pytest.raises(Exception)` pattern in new test modules suggests the team's exception-narrowing discipline from REM-HYGIENE has not been applied consistently to newer test files. Recommend adding a pre-commit or CI lint rule for this pattern.

### Slop Concentration Heatmap

| Module Area | Slop Count (this pass) | Trend |
|-------------|------------------------|-------|
| `metrics/__main__.py` | 2 blocking (LS-DEEP-001, LS-DEEP-002) | NEW -- first-pass quality gap |
| `query/__main__.py` | 3 advisory (LS-DEEP-003, LS-DEEP-008, LS-DEEP-010) | NEW -- advisory only |
| `tests/unit/api/test_health.py` | 1 blocking (HH-DEEP-001) | NEW -- mock pattern debt |
| `pyproject.toml` | 1 blocking (HH-DEEP-002) | NEW -- dependency manifest gap |
| `tests/unit/metrics/` + `tests/unit/query/` | 1 advisory (LS-DEEP-004, 6 occurrences) | RECURRING -- same pattern from P1 resurfaces in new modules |
| `cache/` (freshness aliases) | 3 temporal | CLEANUP MISS from consolidation |
| `models/business/detection/` | 1 temporal (CC-DEEP-002) | CLEANUP MISS from Sprint 3 |
| Pre-existing copy-paste clusters (16 test files) | Carry-forward advisory | UNCHANGED since P1 -- routed to hygiene |

**Highest-concentration area**: `src/autom8_asana/metrics/__main__.py` is the highest-density slop file in this pass (2 blocking findings, 1 file, ~8 lines). This is a single focused fix.

---

## Cross-Rite Referrals

### Referral 1: security rite

**Finding**: LS-DEEP-007
**Files**: `src/autom8_asana/query/saved.py:94-114`, `src/autom8_asana/query/__main__.py:1052-1064`
**Concern**: The `run` subcommand accepts a user-provided file path argument (`query_path = Path(query_arg)`). `load_saved_query` calls `path.read_text()` without checking that the path is contained within expected directories (`./queries/` or `~/.autom8/queries/`). `yaml.safe_load` mitigates YAML deserialization attacks. The risk is reading arbitrary files and returning parse errors.

**Current risk level**: LOW — this is a developer CLI tool; the user explicitly provides the path on their own machine.
**Elevated risk condition**: HIGH if the `run` subcommand or saved-query path acceptance is ever exposed through a web interface, API endpoint, or multi-tenant deployment. The `--live` mode extension path (ADR-AQ-007) warrants specific evaluation here.

**Action requested**: Evaluate whether path containment (resolve against allowed base directories; reject traversal) should be added preemptively given the `--live` mode roadmap.

---

### Referral 2: hygiene rite

**Finding**: LS-009 through LS-024 (carry-forward from P1)
**Files**: `tests/unit/dataframes/test_unit_schema.py` (10 column-existence tests), `tests/unit/dataframes/test_normalizers.py` (9 normalization tests), `tests/unit/dataframes/test_pii.py` (5 phone masking tests)
**Concern**: 16 copy-paste test clusters remain from P1. Tests are functionally correct. Parametrizing these clusters would reduce approximately 600–800 LOC and eliminate the maintenance burden of updating N locations when a pattern changes.

**New context since P1**: The `pytest.raises(Exception)` pattern has recurred in 6 new test files introduced during AUTOM8_QUERY and metrics initiatives (LS-DEEP-004). This suggests the copy-paste / weak-assertion pattern is recurring in new test modules rather than being contained. A hygiene initiative that addresses the parametrization backlog and introduces a lint rule or test review checklist for exception narrowing would have compounding value.

**Action requested**: Schedule parametrization cleanup and add tooling/process to prevent recurrence in new test modules.

---

## Verdict Statement

This codebase does not merit FAIL. The four blocking findings are well-contained, all have clear remediation paths, and the combined effort is under one sprint for a single developer. The structural work from four major initiatives is sound. CONDITIONAL-PASS is the correct verdict.

Complete WS-DEPS, WS-HEALTH-MOCK, and WS-METRICS. Rerun the gate. This becomes PASS.
