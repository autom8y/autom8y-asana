# Complexity Audit — XR-001

**Date**: 2026-02-18
**Tool**: `ruff check --select C901` (McCabe cyclomatic complexity)
**Threshold**: 15 (19 findings)
**Baseline**: 64 findings at default threshold 10
**Commit**: `be4c23a` (main)
**Source**: ARCH-REVIEW-1, Section 3.1, item XR-001

---

## Ranked Table (complexity >= 15)

| Rank | Score | Function | File | Line |
|------|-------|----------|------|------|
| 1 | **35** | `_preload_dataframe_cache_progressive` | `api/preload/progressive.py` | 67 |
| 2 | **29** | `_execute_batch_request` | `clients/data/client.py` | 1092 |
| 3 | **25** | `_validate_registry_integrity` | `core/entity_registry.py` | 694 |
| 4 | **24** | `_warm_cache_async` | `lambda_handlers/cache_warmer.py` | 334 |
| 5 | **23** | `_preload_dataframe_cache` | `api/preload/legacy.py` | 26 |
| 6 | **23** | `_coerce_value` | `dataframes/builders/fields.py` | 110 |
| 7 | **22** | `_execute_insights_request` | `clients/data/client.py` | 1465 |
| 8 | **21** | `execute_async` | `automation/pipeline.py` | 188 |
| 9 | **20** | `seed_async` | `models/business/seeder.py` | 162 |
| 10 | **20** | `dataframe_cache` | `cache/dataframe/decorator.py` | 26 |
| 11 | **19** | `warm_ancestors_async` | `cache/integration/hierarchy_warmer.py` | 103 |
| 12 | **19** | `decorator` | `cache/dataframe/decorator.py` | 71 |
| 13 | **18** | `execute_rows` | `query/engine.py` | 62 |
| 14 | **18** | `_extract_raw_value` | `dataframes/resolver/default.py` | 247 |
| 15 | **18** | `__init_subclass__` | `models/business/base.py` | 239 |
| 16 | **17** | `compute_reorder_plan` | `persistence/reorder.py` | 111 |
| 17 | **16** | `resolve_entities` | `api/routes/resolver.py` | 149 |
| 18 | **16** | `_validate_type` | `models/custom_field_accessor.py` | 405 |
| 19 | **16** | `_apply_section_delta` | `dataframes/builders/freshness.py` | 296 |

## Hotspot Clusters

| Cluster | Functions | Avg Score | Notes |
|---------|-----------|-----------|-------|
| **Data client** | `_execute_batch_request`, `_execute_insights_request` | 25.5 | Retry + pagination + error handling interleaved |
| **Preload** | `_preload_dataframe_cache_progressive`, `_preload_dataframe_cache` | 29.0 | Sequential warm-up with error recovery; legacy is candidate for removal |
| **Cache/DataFrame** | `dataframe_cache`, `decorator`, `_coerce_value`, `_apply_section_delta` | 19.5 | Decorator pair (26+19=45 combined); coercion is type-switch heavy |
| **Business model** | `seed_async`, `__init_subclass__`, `_extract_raw_value` | 18.7 | Metaclass introspection + field extraction |
| **Pipeline** | `execute_async` | 21.0 | Core automation orchestrator |

## Summary

- **Top 3** (`>= 25`): progressive preload, batch request, registry validation — each > 2.5x threshold
- **Preload pair** (ranks 1, 5) could share extraction logic; legacy is marked for deprecation
- **Decorator pair** (ranks 10, 12) in `cache/dataframe/decorator.py` total 39 — single-file hotspot
- All paths in `src/` — no test files flagged
