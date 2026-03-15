---
name: env_var_refactor_ci_failure_pattern
description: Pattern observed when env var renames break unit tests and formatting — affects which test files to check after any settings/config refactor
type: project
---

On 2026-03-15, the PATCH release (env var AUTOM8Y_ prefix standardization) failed CI with two regression categories:

1. `src/autom8_asana/settings.py` was modified but not formatted — `ruff format --check` failed. The file needs `ruff format` run after any settings edits.

2. 13 unit tests broke because they set env vars using old names (pre-rename) that settings.py no longer reads. Test files affected: `tests/unit/cache/dataframe/test_decorator.py`, `tests/unit/cache/dataframe/test_memory_tier_cgroup.py`, `tests/unit/clients/data/test_config.py`, `tests/unit/dataframes/builders/test_cascade_validator.py`, `tests/unit/test_settings_url_guard.py`.

**Why:** The env var rename (adding AUTOM8Y_ prefix to Tier 2 vars) was applied to the source but not propagated to the test fixtures that set env vars by name. Integration tests passed because they use real env infrastructure.

**How to apply:** After any config/settings rename in autom8y-asana, flag these test files as requiring update before the release CI will pass. Also flag `ruff format src/autom8_asana/settings.py` as a required pre-commit step.
