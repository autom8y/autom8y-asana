# HYG-004: Documentation Debt & Code Marker Findings

**Scan Date**: 2026-02-04
**Scope**: `src/autom8_asana/` (tests excluded)
**Scanner**: Code Smeller agent (HYG-004)

---

## Summary

| Category | Count | Critical | Moderate | Minor |
|----------|-------|----------|----------|-------|
| todo-marker | 4 | 1 | 3 | 0 |
| commented-code | 3 | 0 | 1 | 2 |
| missing-docstring | 66 | 0 | 18 | 48 |
| magic-number | 8 | 0 | 5 | 3 |
| missing-type-hint | 0 | 0 | 0 | 0 |
| missing-class-docstring | 1 | 0 | 0 | 1 |
| **Total** | **82** | **1** | **27** | **54** |

---

## Findings

### TODO/FIXME/HACK Markers

| ID | File | Line | Category | Severity | Description | Marker-Text |
|----|------|------|----------|----------|-------------|-------------|
| DOC-001 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_invalidate.py` | 105 | todo-marker | critical | TieredCacheProvider called without required `hot_tier` argument; suppressed with `type: ignore[call-arg]`. Indicates a broken code path. | `# TODO: Fix this - TieredCacheProvider requires hot_tier argument` |
| DOC-002 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/unit.py` | 90 | todo-marker | moderate | Stub returning None; office derivation deferred pending team input on business logic. | `# TODO: Implement office derivation from business.office_phone lookup` |
| DOC-003 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/unit.py` | 113 | todo-marker | moderate | Stub returning None; vertical_id derivation deferred pending Vertical model mapping. | `# TODO: Implement vertical_id derivation from Vertical model` |
| DOC-004 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/unit.py` | 136 | todo-marker | moderate | Stub returning None; max_pipeline_stage derivation deferred pending UnitHolder model. | `# TODO: Implement max_pipeline_stage derivation from UnitHolder` |

### Commented-Out Code

| ID | File | Line | Category | Severity | Description | Marker-Text |
|----|------|------|----------|----------|-------------|-------------|
| DOC-005 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/definitions/__init__.py` | 14-15 | commented-code | moderate | Commented-out imports for `unit` and `business` metric definitions. Labeled "Future definition modules" but no timeline or tracking ticket. | `# from autom8_asana.metrics.definitions import unit  # noqa: F401` / `# from autom8_asana.metrics.definitions import business  # noqa: F401` |
| DOC-006 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/base.py` | 664 | commented-code | minor | Dead-branch comment `# else: should not happen, indicates bug` -- unreachable else case is noted but not defended (no assertion or raise). | `# else: should not happen, indicates bug` |
| DOC-007 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/engine.py` | 150 | commented-code | minor | Inline narrative comment spanning multiple lines explaining why section moves skip dirty-field detection. Not actual dead code, but reads like temporarily-removed logic documentation. | `# from CRUD operations. A Process moved to a section has no dirty fields, so it` |

### Missing Docstrings (Public Functions/Methods)

Grouped by module for readability. All severity **minor** unless the function is part of a public SDK API surface.

| ID | File | Line | Category | Severity | Description | Marker-Text |
|----|------|------|----------|----------|-------------|-------------|
| DOC-008 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 32 | missing-docstring | moderate | `get_async` -- public async section getter (overload 1 of 4) has no docstring. | -- |
| DOC-009 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 41 | missing-docstring | moderate | `get_async` -- public async section getter (overload 2 of 4) has no docstring. | -- |
| DOC-010 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 50 | missing-docstring | moderate | `get` -- public sync section getter (overload 1 of 2) has no docstring. | -- |
| DOC-011 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 59 | missing-docstring | moderate | `get` -- public sync section getter (overload 2 of 2) has no docstring. | -- |
| DOC-012 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 121 | missing-docstring | moderate | `create_async` -- public async section creation (overload 1). | -- |
| DOC-013 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 132 | missing-docstring | moderate | `create_async` -- public async section creation (overload 2). | -- |
| DOC-014 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 143 | missing-docstring | moderate | `create` -- public sync section creation (overload 1). | -- |
| DOC-015 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 154 | missing-docstring | moderate | `create` -- public sync section creation (overload 2). | -- |
| DOC-016 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 203 | missing-docstring | moderate | `update_async` -- public async section update (overload 1). | -- |
| DOC-017 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 212 | missing-docstring | moderate | `update_async` -- public async section update (overload 2). | -- |
| DOC-018 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 221 | missing-docstring | moderate | `update` -- public sync section update (overload 1). | -- |
| DOC-019 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | 230 | missing-docstring | moderate | `update` -- public sync section update (overload 2). | -- |
| DOC-020 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 117 | missing-docstring | moderate | `asset_approval` -- public property on business model. | -- |
| DOC-021 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 126 | missing-docstring | moderate | `asset_id` -- public property on business model. | -- |
| DOC-022 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 136 | missing-docstring | moderate | `editor` -- public property on business model. | -- |
| DOC-023 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 146 | missing-docstring | moderate | `reviewer` -- public property on business model. | -- |
| DOC-024 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 160 | missing-docstring | minor | `offer_id` -- public property on business model. | -- |
| DOC-025 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 169 | missing-docstring | minor | `raw_assets` -- public property on business model. | -- |
| DOC-026 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 184 | missing-docstring | minor | `review_all_ads` -- public property on business model. | -- |
| DOC-027 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 199 | missing-docstring | minor | `score` -- public property on business model. | -- |
| DOC-028 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 214 | missing-docstring | minor | `specialty` -- public property on business model. | -- |
| DOC-029 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 226 | missing-docstring | minor | `template_id` -- public property on business model. | -- |
| DOC-030 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/asset_edit.py` | 235 | missing-docstring | minor | `videos_paid` -- public property on business model. | -- |
| DOC-031 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | 39 | missing-docstring | minor | `to_dict` on query error class (repeated across 8 error subclasses at lines 39, 56, 73, 96, 114, 128, 142, 160). | -- |
| DOC-032 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | 56 | missing-docstring | minor | `to_dict` on query error class. | -- |
| DOC-033 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | 73 | missing-docstring | minor | `to_dict` on query error class. | -- |
| DOC-034 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | 96 | missing-docstring | minor | `to_dict` on query error class. | -- |
| DOC-035 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | 114 | missing-docstring | minor | `to_dict` on query error class. | -- |
| DOC-036 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | 128 | missing-docstring | minor | `to_dict` on query error class. | -- |
| DOC-037 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | 142 | missing-docstring | minor | `to_dict` on query error class. | -- |
| DOC-038 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | 160 | missing-docstring | minor | `to_dict` on query error class. | -- |
| DOC-039 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 71 | missing-docstring | minor | `status_hint` property on EntityNotFoundError. | -- |
| DOC-040 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 89 | missing-docstring | minor | `error_code` property on UnknownEntityError. | -- |
| DOC-041 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 92 | missing-docstring | minor | `to_dict` on UnknownEntityError. | -- |
| DOC-042 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 116 | missing-docstring | minor | `error_code` property on UnknownSectionError. | -- |
| DOC-043 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 119 | missing-docstring | minor | `to_dict` on UnknownSectionError. | -- |
| DOC-044 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 138 | missing-docstring | minor | `status_hint` property on EntityValidationError. | -- |
| DOC-045 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 158 | missing-docstring | minor | `error_code` property on InvalidFieldError. | -- |
| DOC-046 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 162 | missing-docstring | minor | `status_hint` property on InvalidFieldError. | -- |
| DOC-047 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 165 | missing-docstring | minor | `to_dict` on InvalidFieldError. | -- |
| DOC-048 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 178 | missing-docstring | minor | `error_code` property on InvalidParameterError. | -- |
| DOC-049 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 202 | missing-docstring | minor | `error_code` property on CacheNotReadyError. | -- |
| DOC-050 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 206 | missing-docstring | minor | `status_hint` property on CacheNotReadyError. | -- |
| DOC-051 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 214 | missing-docstring | minor | `error_code` property on ServiceNotConfiguredError. | -- |
| DOC-052 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/errors.py` | 218 | missing-docstring | minor | `status_hint` property on ServiceNotConfiguredError. | -- |
| DOC-053 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/_defaults/auth.py` | 92 | missing-docstring | minor | `get_secret` on default auth provider. | -- |
| DOC-054 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframes.py` | 179 | missing-docstring | minor | `load_single` helper in dataframe cache integration. | -- |
| DOC-055 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/loader.py` | 162 | missing-docstring | minor | `load_single` helper in cache loader. | -- |
| DOC-056 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/events.py` | 46 | missing-docstring | minor | `callback` inner function in event model. | -- |
| DOC-057 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` | 71 | missing-docstring | minor | `decorator` inner function in dataframe cache decorator. | -- |
| DOC-058 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` | 75 | missing-docstring | minor | `cached_resolve` inner function in dataframe cache decorator. | -- |
| DOC-059 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/batch.py` | 355 | missing-docstring | minor | `decorator` inner function in batch cache. | -- |
| DOC-060 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/batch.py` | 359 | missing-docstring | minor | `wrapper` inner function in batch cache. | -- |
| DOC-061 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/hierarchy_warmer.py` | 71 | missing-docstring | minor | `bounded_coro` helper in hierarchy warmer. | -- |
| DOC-062 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/base.py` | 66 | missing-docstring | minor | `bounded_coro` helper in base builder. | -- |
| DOC-063 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/resolver/cascading.py` | 88 | missing-docstring | minor | `fetch_one` in cascading resolver. | -- |
| DOC-064 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/entrypoint.py` | 26 | missing-docstring | minor | `log_info` utility function. | -- |
| DOC-065 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/entrypoint.py` | 30 | missing-docstring | minor | `log_error` utility function. | -- |
| DOC-066 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | 457 | missing-docstring | minor | `get_project_gid` helper in cache warmer. | -- |
| DOC-067 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/holder_factory.py` | 200 | missing-docstring | minor | `getter` inner function in holder factory. | -- |
| DOC-068 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/hours.py` | 56 | missing-docstring | minor | `decorator` inner function in hours model. | -- |
| DOC-069 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/hours.py` | 57 | missing-docstring | minor | `getter` inner function in hours model. | -- |
| DOC-070 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/hours.py` | 65 | missing-docstring | minor | `setter` inner function in hours model. | -- |
| DOC-071 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/actions.py` | 603 | missing-docstring | minor | `method` dynamically generated in persistence actions. | -- |
| DOC-072 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/actions.py` | 635 | missing-docstring | minor | `method` dynamically generated in persistence actions. | -- |
| DOC-073 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/actions.py` | 682 | missing-docstring | minor | `method` dynamically generated in persistence actions. | -- |
| DOC-074 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/healing.py` | 438 | missing-docstring | minor | `heal_one` in persistence healing. | -- |
| DOC-075 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/join.py` | 37 | missing-docstring | minor | `validate_select_not_empty` validator. | -- |
| DOC-076 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/retry.py` | 185 | missing-docstring | minor | `max_attempts` property on retry config. | -- |
| DOC-077 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/polling/config_loader.py` | 232 | missing-docstring | minor | `replace_match` helper in config loader. | -- |

### Missing Class Docstrings

| ID | File | Line | Category | Severity | Description | Marker-Text |
|----|------|------|----------|----------|-------------|-------------|
| DOC-078 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/dataframes.py` | 496 | missing-docstring | minor | `SectionProxy` class missing docstring. | -- |

### Magic Numbers

| ID | File | Line | Category | Severity | Description | Marker-Text |
|----|------|------|----------|----------|-------------|-------------|
| DOC-079 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/custom_fields.py` | 96 | magic-number | moderate | Inline `ttl=1800` (30 min) with no named constant. Same value at `sections.py:112` and `sections.py:331`. Should be a shared constant or config value. | `self._cache_set(custom_field_gid, data, EntryType.CUSTOM_FIELD, ttl=1800)` |
| DOC-080 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py` | 90 | magic-number | moderate | Inline `ttl=3600` (1 hour) with no named constant for user cache TTL. | `self._cache_set(user_gid, data, EntryType.USER, ttl=3600)` |
| DOC-081 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/settings.py` | 151 | magic-number | moderate | `batch_check_ttl: int = 25` -- unexplained default; no comment or ADR reference for why 25 seconds. | `batch_check_ttl: int = 25` |
| DOC-082 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/settings.py` | 152 | magic-number | moderate | `reconnect_interval: int = 30` -- unexplained default; no comment on why 30 seconds. | `reconnect_interval: int = 30` |
| DOC-083 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/compute.py` | 96 | magic-number | moderate | `pl.Config(tbl_rows=200, tbl_cols=10, fmt_str_lengths=30)` -- display config magic numbers with no explanation for the specific limits. | `with pl.Config(tbl_rows=200, tbl_cols=10, fmt_str_lengths=30):` |
| DOC-084 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/auth/bot_pat.py` | 78 | magic-number | minor | `len(pat) < 10` -- minimum PAT length threshold with no documented rationale. | `if len(pat) < 10:` |
| DOC-085 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | 603 | magic-number | minor | Inline `ttl_seconds=3600` -- commented as "1 hour" but should reference config or constant. | `ttl_seconds=3600,  # 1 hour` |
| DOC-086 | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/config.py` | 303 | magic-number | minor | Fallback `cache_ttl = 300` inside error handler -- silently defaults on invalid input. | `cache_ttl = 300  # Default on invalid input` |

---

## ROI-Ranked Priority Summary

Ranked by `(severity x frequency x blast_radius) / fix_complexity`:

| Priority | IDs | Category | ROI Rationale |
|----------|-----|----------|---------------|
| 1 | DOC-001 | todo-marker | **Critical**: Broken constructor call behind `type: ignore`. Will fail at runtime if cache_invalidate Lambda is invoked. Single-file fix. |
| 2 | DOC-079, DOC-080, DOC-085 | magic-number | **High ROI**: TTL values scattered across 4+ files with no shared constant. Extract to config once, reference everywhere. Low fix complexity, high consistency gain. |
| 3 | DOC-008 to DOC-019 | missing-docstring | **Moderate ROI**: 12 public SDK methods in `clients/sections.py` with zero docstrings. High user-facing impact; batch-fixable with a docstring template. |
| 4 | DOC-005 | commented-code | **Moderate**: Commented-out metric imports suggest incomplete feature rollout. Should be tracked in backlog or removed. |
| 5 | DOC-002 to DOC-004 | todo-marker | **Low urgency**: Stub implementations are intentionally deferred and well-documented. Track in backlog to prevent drift. |
| 6 | DOC-020 to DOC-030 | missing-docstring | **Low ROI**: Business model property docstrings. Pattern is clear from types; docstrings add marginal value. |
| 7 | DOC-031 to DOC-052 | missing-docstring | **Lowest ROI**: `to_dict`, `error_code`, `status_hint` on error classes. Method names are self-documenting; parent class docstring covers pattern. |

---

## Cross-References

- **DOC-001** relates to architectural concern: `TieredCacheProvider` API changed but downstream Lambda handler not updated. Flag for Architect Enforcer.
- **DOC-079/080/085** are a DRY violation cluster: TTL values should come from `config.py` DEFAULT_ENTITY_TTLS or CacheSettings, not inline literals.
- **DOC-002/003/004** are grouped as a single deferred-feature block in `extractors/unit.py`.
- **DOC-008 through DOC-019** are all in `clients/sections.py` and represent a systematic gap in one file.

---

## Notes

- **Type hints**: No public functions were found missing return type annotations. The codebase has strong type hint discipline.
- **`type: ignore` suppressions**: 30+ instances found across the codebase (see DOC-001 for the most critical). Most are legitimate narrow suppressions for library interop, but `cache_invalidate.py:106` suppresses `[call-arg]` which indicates an actual API mismatch.
- **Excluded from scan**: Test files, `__pycache__`, third-party vendored code, generated files.
- **`* 1000` time conversions**: ~80+ instances of `(time.monotonic() - start) * 1000` for ms conversion. This is an idiomatic pattern, not a magic number concern. No finding raised.
