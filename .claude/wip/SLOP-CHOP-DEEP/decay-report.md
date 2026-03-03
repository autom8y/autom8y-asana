---
type: audit
---
# SLOP-CHOP-DEEP Decay Report

**Phase**: 3 — Decay
**Specialist**: cruft-cutter
**Date**: 2026-02-25
**Scope**: `src/autom8_asana/` + `tests/`
**Initiative Context**: Post ASANA-HYGIENE + REM-ASANA-ARCH + REM-HYGIENE + COMPAT-PURGE

---

## Executive Summary

Four major initiatives completed between 2026-02-23 and 2026-02-25 left behind a modest set of temporal artifacts. COMPAT-PURGE removed 27 shims but left 3 backward-compatible enum aliases with no active callers outside the cache module's own re-export chain. REM-ASANA-ARCH refactoring left initiative-tag comments (`REM-ASANA-ARCH WS-DFEX`, `TDD-SPRINT-3-DETECTION-DECOMPOSITION`) embedded in module docstrings and test headers — these are architecture-ghost style comments that correctly described the refactoring motivation but no longer serve a navigational purpose. Workspace switching tests (8 named skips from WS-WSISO) are properly formed and CURRENT.

No initiative comment artifacts were found for ASANA-HYGIENE, REM-HYGIENE, or any WS-* workstream names. No resolved TODOs, ticket references (JIRA/GitHub), or stale ADR-010 supersession references were found. The deprecated query endpoint comment is actively ops-gated (D-002, CloudWatch gate, sunset 2026-06-01) and is excluded from findings.

| Staleness Tier | Count |
|----------------|-------|
| TIER-1 (STALE — outlived context, safe to remove) | 4 |
| TIER-2 (AGING — context partially expired, needs verification) | 2 |

**Temporal debt density**: LOW. The codebase has an active history of stripping ephemeral comment artifacts (commit `0a85d67`, 2026-02-19: "strip spike tags, hotfix prefixes, and migration notes from comments"). The remaining debt is concentrated in two areas: initiative-tag docstrings from REM-ASANA-ARCH (now completed) and post-freshness-consolidation backward-compat aliases with zero active callers.

---

## Staleness Tiers

- **TIER-1** (Provably stale — resolution signal present): 4 findings
- **TIER-2** (Probably stale — time heuristic, no resolution signal or public API uncertainty): 2 findings

---

## Findings

### CC-DEEP-001: REM-ASANA-ARCH WS-DFEX initiative tag in module docstrings (provably stale)

- **Staleness**: TIER-1
- **Category**: initiative-artifact (architecture-ghost comment)
- **Files**:
  - `src/autom8_asana/services/dataframe_service.py:325`
  - `src/autom8_asana/services/dataframe_service.py:387`
  - `src/autom8_asana/persistence/holder_construction.py:21`
  - `src/autom8_asana/core/registry.py:6`
  - `tests/unit/dataframes/test_public_api.py:3`
  - `tests/unit/persistence/test_holder_construction.py:71`
- **Original Context**: REM-ASANA-ARCH initiative, workstream WS-DFEX (DataFrameService extraction). The `Per R-006 (REM-ASANA-ARCH WS-DFEX):` and `Per R-009 (REM-ASANA-ARCH WS-DFEX):` annotations were initiative tracking markers written during the sprint to tie code to sprint requirements.
- **Evidence of Staleness**: REM-ASANA-ARCH is COMPLETE (MEMORY.md: "CLOSED (2026-02-23 to 2026-02-24)"). Git confirms: `be55d21` (2026-02-24) introduced `R-006` in `dataframe_service.py`; `8418d9c` (2026-02-24) introduced `R-009` in `holder_construction.py`. The sprint is closed; these are now architecture-ghost comments. The behavior they describe (service functions replacing model convenience methods; self-registration pattern) is fully stable and documented by the code itself. The initiative tag adds no current navigational value.

  Example at `src/autom8_asana/services/dataframe_service.py:325-326`:
  ```python
  Per R-006 (REM-ASANA-ARCH WS-DFEX): Service function replacing model
  convenience methods.
  ```
  Example at `src/autom8_asana/core/registry.py:6-7`:
  ```python
  Per R-009 (REM-ASANA-ARCH WS-DFEX): Each Holder module self-registers via
  register_holder() at module level, following the register_reset() pattern.
  ```
  Example at `tests/unit/dataframes/test_public_api.py:3`:
  ```python
  Per TDD-0009 Phase 5 / R-006 (REM-ASANA-ARCH WS-DFEX):
  ```
  Example at `tests/unit/persistence/test_holder_construction.py:71`:
  ```python
  Per R-009 (REM-ASANA-ARCH WS-DFEX): Completeness gate ensuring no Holder
  ```

- **Severity**: TEMPORAL (advisory)
- **Interview**: NO

---

### CC-DEEP-002: TDD-SPRINT-3-DETECTION-DECOMPOSITION initiative tag across detection package (probably stale)

- **Staleness**: TIER-2
- **Category**: initiative-artifact (architecture-ghost comment)
- **Files** (8 files, every module in the detection package):
  - `src/autom8_asana/models/business/detection/__init__.py:3`
  - `src/autom8_asana/models/business/detection/tier1.py:3`
  - `src/autom8_asana/models/business/detection/tier2.py:3`
  - `src/autom8_asana/models/business/detection/tier3.py:3`
  - `src/autom8_asana/models/business/detection/tier4.py:3`
  - `src/autom8_asana/models/business/detection/types.py:3`
  - `src/autom8_asana/models/business/detection/config.py:3`
  - `src/autom8_asana/models/business/detection/facade.py:3`
- **Original Context**: Sprint 3 of an earlier development phase. Git confirms this sprint shipped in commit `d805780` (2025-12-22): "feat(detection): Decompose monolithic detection into tiered package (Sprint 3)". The `TDD-SPRINT-3-DETECTION-DECOMPOSITION` tag marks every module in the detection package as part of that decomposition effort.
- **Evidence of Staleness**: Commit `d805780` is from 2025-12-22 — over 2 months ago. The tag appears in every one of the 8 detection package files. No document named `TDD-SPRINT-3-DETECTION-DECOMPOSITION` exists in `docs/spikes/`. The detection package is stable and fully exercised. The sprint concluded months before the recent initiative wave.

  This is TIER-2 rather than TIER-1 because no explicit cleanup commit was found that removed the tag — it was never stripped. The sprint concluded but left these module-level annotations unreachable by the 2026-02-19 spike-tag stripping commit (which targeted only `gid_push.py` and `cache_warmer.py`).

  Example at `src/autom8_asana/models/business/detection/facade.py:3`:
  ```python
  Per TDD-SPRINT-3-DETECTION-DECOMPOSITION: Central orchestration for tiered detection.
  ```

- **Severity**: TEMPORAL (advisory)
- **Interview**: NO

---

### CC-DEEP-003: FreshnessClassification backward-compat alias with zero active callers (provably stale)

- **Staleness**: TIER-1
- **Category**: deprecation-cruft (post-consolidation alias with no external consumers)
- **Files**:
  - `src/autom8_asana/cache/models/freshness_stamp.py:20-21`
  - `src/autom8_asana/cache/models/__init__.py:47-51` (re-exports it)
- **Original Context**: Freshness enum consolidation (commit `04b4b03`, 2026-02-23). Four legacy enums were consolidated into two (`FreshnessIntent`, `FreshnessState`). `FreshnessClassification` was established as a backward-compatible alias for `FreshnessState` to avoid breaking import sites during the transition.
- **Evidence of Staleness**: Caller analysis across all of `src/autom8_asana/` and `tests/`:
  - Zero callers import `FreshnessClassification` from any path in production source
  - Zero callers import `FreshnessClassification` in tests
  - The only references are the alias definition (`freshness_stamp.py:21`) and the re-export in `cache/models/__init__.py`
  - The `freshness_unified.py` docstring references `FreshnessClassification` in migration mapping comments only (documentary text, not runtime use)

  The sister cleanup commit `83fa971` (2026-02-25) deleted `cache/models/freshness.py` (the `Freshness` alias module). `FreshnessClassification` was not swept in that commit, leaving it stranded with no callers.

  `src/autom8_asana/cache/models/freshness_stamp.py:20-21`:
  ```python
  # Backward-compatible alias. New code should use FreshnessState directly.
  FreshnessClassification = FreshnessState
  ```

- **Severity**: TEMPORAL (advisory)
- **Interview**: NO

---

### CC-DEEP-004: FreshnessStatus backward-compat alias with zero active callers (provably stale)

- **Staleness**: TIER-1
- **Category**: deprecation-cruft (post-consolidation alias with no external consumers)
- **File**: `src/autom8_asana/cache/integration/dataframe_cache.py:18-19`
- **Original Context**: Same freshness consolidation sprint as CC-DEEP-003 (commit `04b4b03`, 2026-02-23). `FreshnessStatus` was the pre-consolidation name used in `dataframe_cache.py`.
- **Evidence of Staleness**: Caller analysis across all of `src/autom8_asana/` and `tests/`:
  - Zero callers import `FreshnessStatus` from any path
  - Not re-exported in `cache/__init__.py` or `cache/integration/__init__.py`
  - Only references are the alias definition and the migration mapping in `freshness_unified.py` (documentary text)

  `src/autom8_asana/cache/integration/dataframe_cache.py:18-19`:
  ```python
  # Backward-compatible alias. New code should use FreshnessState directly.
  FreshnessStatus = FreshnessState
  ```

- **Severity**: TEMPORAL (advisory)
- **Interview**: NO

---

### CC-DEEP-005: FreshnessMode backward-compat alias — re-exported in __all__ but no internal callers (probably stale)

- **Staleness**: TIER-2
- **Category**: deprecation-cruft (post-consolidation alias still in public re-export chain)
- **Files**:
  - `src/autom8_asana/cache/integration/freshness_coordinator.py:20-21`
  - `src/autom8_asana/cache/integration/__init__.py:13` (re-exports it)
  - `src/autom8_asana/cache/__init__.py:107` (re-exports it at package level, in `__all__`)
- **Original Context**: Freshness consolidation (commit `04b4b03`, 2026-02-23). `FreshnessMode` was the pre-consolidation name in `freshness_coordinator.py`. It was established as an alias for `FreshnessIntent`.
- **Evidence of Staleness**:
  - Zero production source files in `src/autom8_asana/` import `FreshnessMode` from any path
  - Zero test files use `FreshnessMode` at a call site (one test class is named `TestFreshnessMode` at `tests/unit/cache/test_freshness_coordinator.py:108`, but its body uses `FreshnessIntent` throughout)
  - `cache/__init__.py` exports it in `__all__` at line 269, making it part of the declared public surface

  This is TIER-2 rather than TIER-1 because `FreshnessMode` is in `__all__`. It is possible this was intentionally retained for external consumers of this package (other services). Without runtime import data confirming no external SDK consumers use it, it cannot be classified as provably stale.

  `src/autom8_asana/cache/integration/freshness_coordinator.py:20-21`:
  ```python
  # Backward-compatible alias. New code should use FreshnessIntent directly.
  FreshnessMode = FreshnessIntent
  ```

- **Severity**: TEMPORAL (advisory)
- **Interview**: YES — confirm whether `FreshnessMode` is intentionally retained as a public API alias for external consumers, or safe to remove alongside CC-DEEP-003 and CC-DEEP-004.

---

### CC-DEEP-006: SPIKE-BREAK-CIRCULAR-DEP initiative tag in test module docstrings (probably stale)

- **Staleness**: TIER-2
- **Category**: initiative-artifact (architecture-ghost comment referencing a missing spike document)
- **Files**:
  - `tests/unit/services/test_gid_push.py:3-4`
  - `tests/unit/lambda_handlers/test_cache_warmer_gid_push.py:3-4`
- **Original Context**: The GID push feature (`feat: push GID mappings to autom8_data after cache rebuild`, commit `b9c2269`, 2026-02-16) was preceded by a spike to break a circular dependency between `autom8_asana` and `autom8_data`. The test files reference this spike as `SPIKE-BREAK-CIRCULAR-DEP Phase 3`.
- **Evidence of Staleness**: No document named `SPIKE-BREAK-CIRCULAR-DEP` exists in `docs/spikes/`. The feature shipped 9 days ago. A prior cleanup commit (`0a85d67`, 2026-02-19) already stripped this same spike tag from source files: "Remove SPIKE-BREAK-CIRCULAR-DEP narrative tags from gid_push.py and cache_warmer.py (spike concluded, feature shipped)". That strip covered the source files only — the test file headers were missed.

  This is TIER-2 rather than TIER-1 because the spike document is absent, making it impossible to confirm the spike's completion date from internal evidence. The prior strip commit establishes intent but is not a resolution signal for these specific files.

  `tests/unit/services/test_gid_push.py:3-5`:
  ```python
  Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: Tests for the push function that
  sends GID mappings to autom8_data after cache warmer rebuilds.
  ```
  `tests/unit/lambda_handlers/test_cache_warmer_gid_push.py:3-5`:
  ```python
  Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: Tests that the cache warmer
  calls the GID push function after successfully warming entities, and
  that push failures do not affect the warmer's success status.
  ```

- **Severity**: TEMPORAL (advisory)
- **Interview**: NO — the prior strip commit (`0a85d67`) established the project convention: once a spike concludes and the feature ships, spike narrative tags are stripped. These two test file headers are a clean-up miss.

---

## Clean Areas

The following areas were scanned and found free of temporal debt:

**Initiative comment sweep (src/ and tests/) — CLEAN for:**
- `COMPAT-PURGE` — 0 references in `src/` or `tests/`
- `ASANA-HYGIENE` — 0 references in `src/` or `tests/`
- `REM-HYGIENE` — 0 references in `src/` or `tests/`
- All WS-PARAM, WS-HTTPX, WS-EXCEPT, WS-INTEG, WS-OVERMOCK, WS-SLOP2, WS-REEXPORT, WS-DEAD, WS-DEPRECATED, WS-DUALPATH, WS-BESPOKE, WS-GETCF, WS-DP01, WS-HW02, WS-HW03 workstream names — 0 references in `src/` or `tests/`

**TODO annotation sweep — CLEAN:**
- `TODO(COMPAT-PURGE)` — 0 occurrences
- Pattern `TODO.*remove|delete|cleanup|migrate|after` — 0 occurrences in `src/` or `tests/`

**ADR reference sweep — CLEAN:**
- ADR-010 (superseded by ADR-0067) — 0 references; all ADR-010x references found are the unrelated ADR-0101..ADR-0119 series (different numbering format)
- No stale superseded ADR citations found

**Stale skip marker sweep — CLEAN:**
- WS-WSISO workspace switching skips (`tests/integration/test_workspace_switching.py:39-154`): 8 named skips are properly formed with behavioral rationale describing features NOT YET IMPLEMENTED (workspace isolation), not a completed migration. These are CURRENT.
- RS-021 skip (`tests/integration/test_platform_performance.py:208-212`): Named skip with external-library attribution. CURRENT. Consistent with LS-DEEP-005 finding in the analysis report.
- All other `pytest.mark.skip` / `pytest.mark.skipif` annotations are conditional on runtime environment (ASANA_PAT, MOTO_AVAILABLE, FAKEREDIS_AVAILABLE, _HAS_HYPOTHESIS) — environmental guards, not temporal artifacts.

**Feature flag sweep — CLEAN:**
- `AUTOM8_DATA_INSIGHTS_ENABLED` — active runtime circuit-breaker for DataServiceClient
- `AUTOM8_AUDIT_ENABLED` — active runtime flag for conversation audit workflow
- `AUTOM8_EXPORT_ENABLED` — active runtime flag for insights export workflow
- `GID_PUSH_ENABLED` (`services/gid_push.py`) — active runtime flag for GID push
- `S3_ENABLED` (tiered cache) — active runtime flag for S3 cold tier
- None are always-on/always-off. All are externally configurable runtime toggles.

**Deprecated API endpoint — OPS-GATED (excluded from findings):**
- `POST /v1/query/{entity_type}` (deprecated, sunset 2026-06-01): D-002 / D-QUERY, CloudWatch gate. Comments in `api/routes/query.py:7,425` and `api/main.py:175` are accurate, current, and ops-gated per project protocol.

**Backward-compatibility comments describing ACTIVE patterns — CLEAN (not cruft):**
- `services/resolution_result.py`: `gid` property for single-GID API consumers — actively used in `api/routes/resolver.py:352`
- `settings.py:763`: `ASANA_ENVIRONMENT` env var — active configuration path
- `api/dependencies.py:543`: `AUTOM8_DATA_API_KEY` for Lambda/ECS — active deployment path
- `HOLDER_KEY_MAP` DEPRECATED comment — intentional resilience fallback, in CLOSED list
- Cache `enabled=False` circuit breaker — intentional opt-in design, in CLOSED list
- Cache dual-method APIs — dual-purpose, in CLOSED list

**SPIKE document references in src/ — CLEAN (with CC-DEEP-006 exception):**
- All `Per SPIKE-*` references in source point to documents confirmed present in `docs/spikes/`: SPIKE-stale-while-revalidate-freshness, SPIKE-dynamic-api-criteria, SPIKE-formatter-protocol-moonshot, SPIKE-cache-freshness-consolidation. These are in-repo architectural design citations, not ephemeral external tickets.

**HOTFIX annotations — CURRENT (not stale):**
- `cache/__init__.py:143,187` and `cache/models/__init__.py:38`: Three `# HOTFIX: Make import defensive for Lambda compatibility...` annotations added 2026-02-25 as part of `fix(cache): remove Freshness backward-compat alias module`. These reflect an active defensive pattern for a real Lambda deployment constraint, not stale hotfix labels.

**Pre-migration fallback (`insights_export.py`) — CURRENT (not cruft):**
- `src/autom8_asana/automation/workflows/insights_export.py:410`: "This is the pre-migration enumeration logic, preserved verbatim for resilience when section resolution or section-level fetch fails." The fallback at `_enumerate_offers_fallback()` is actively called on 3 code paths (lines 346, 354, 381) and is a live degraded-mode fallback, not a dead migration stub. Not temporal debt.

---

## Interview Escalation Items

### CC-DEEP-005 Escalation: FreshnessMode public API surface intent

**Question**: Is `FreshnessMode` intentionally retained in `cache/__init__.__all__` as a public backward-compatible alias for external consumers of this package (e.g., other services importing `from autom8_asana.cache import FreshnessMode`), or is it safe to remove alongside `FreshnessClassification` (CC-DEEP-003) and `FreshnessStatus` (CC-DEEP-004)?

**Context**: Zero callers found within `src/autom8_asana/` or `tests/`. However, `FreshnessMode` is in `__all__` at the package level (`cache/__init__.py:269`), which may indicate intentional retention for external consumers. A runtime import audit of downstream services would be definitive.

---

## Staleness Score Methodology

Each finding scored on four signals:

| Signal | Role |
|--------|------|
| Initiative completion evidence (MEMORY.md COMPLETE/CLOSED, git commit confirming shipment) | Primary — enables TIER-1 |
| Active caller analysis (grep across src/ and tests/ for all import paths) | Corroborating — required for alias findings |
| Time since last modification (90-day default heuristic) | Secondary — enables TIER-2 when primary absent |
| Resolution commit presence (explicit cleanup or strip commit) | Confirming |

**TIER-1 (Provably stale)**: Initiative completion signal confirmed + caller analysis showing zero active callers.

**TIER-2 (Probably stale)**: Initiative completion signal confirmed but missing explicit cleanup commit, OR public API surface uncertainty prevents caller analysis from being definitive.

---

## Handoff Checklist

- [x] Each finding includes file path, line number, temporal evidence (git dates, initiative status, caller analysis)
- [x] Ephemeral comments classified by type: initiative-artifact (CC-DEEP-001, CC-DEEP-002, CC-DEEP-006), deprecation-cruft (CC-DEEP-003, CC-DEEP-004, CC-DEEP-005)
- [x] Every finding labeled TIER-1 or TIER-2 with evidence
- [x] Alias shims include full caller analysis (zero external callers confirmed for CC-DEEP-003/004; CC-DEEP-005 escalated)
- [x] Staleness scores assigned with methodology documented
- [x] WS-WSISO and RS-021 named skips verified as CURRENT — excluded from findings
- [x] Deprecated query endpoint confirmed OPS-GATED — excluded from findings
- [x] CLOSED list items (HOLDER_KEY_MAP, cache dual-methods, strict=False, connection_manager, ADR-0067 divergence, SaveSession) verified and excluded
- [x] HOTFIX annotations verified as CURRENT (added 2026-02-25) — excluded from findings
- [x] Pre-migration fallback in insights_export.py verified as active degraded-mode path — excluded

**Ready for remedy-smith.**
