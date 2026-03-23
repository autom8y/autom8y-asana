---
name: env_var_refactor_ci_failure_pattern
description: Pattern observed when env var renames or tooling-only pushes break formatting or tests — affects which files to check after any config/tooling change in autom8y-asana
type: project
---

On 2026-03-15, the PATCH release (env var AUTOM8Y_ prefix standardization) failed CI with two regression categories:

1. `src/autom8_asana/settings.py` was modified but not formatted — `ruff format --check` failed. The file needs `ruff format` run after any settings edits.

2. 13 unit tests broke because they set env vars using old names (pre-rename) that settings.py no longer reads. Test files affected: `tests/unit/cache/dataframe/test_decorator.py`, `tests/unit/cache/dataframe/test_memory_tier_cgroup.py`, `tests/unit/clients/data/test_config.py`, `tests/unit/dataframes/builders/test_cascade_validator.py`, `tests/unit/test_settings_url_guard.py`.

**Why:** The env var rename (adding AUTOM8Y_ prefix to Tier 2 vars) was applied to the source but not propagated to the test fixtures that set env vars by name. Integration tests passed because they use real env infrastructure.

**How to apply:** After any config/settings rename in autom8y-asana, flag these test files as requiring update before the release CI will pass. Also flag `ruff format src/autom8_asana/settings.py` as a required pre-commit step.

---

On 2026-03-15 Round 6 (tooling sync push), the Test workflow failed again at `ci / Lint & Type Check / Check formatting`. Two files were unformatted:
- `src/autom8_asana/cache/models/entry.py`
- `src/autom8_asana/resolution/field_resolver.py`

The `ci / Test` and `ci / Integration Tests` jobs both passed — only the formatting gate failed. This caused Satellite Dispatch (run 23111003389) to trigger but immediately skip its dispatch job (trigger condition requires Test conclusion == success). Stage 3 was never reached.

**Why:** The tooling sync push included changes to or near these files without running `ruff format` first. The ruff version in CI was 0.15.4.

**How to apply:** Before any push to autom8y-asana, always run `uv run ruff format . --check` locally. If any files would be reformatted, run `uv run ruff format .` and commit those changes. This is especially important for tooling-only or config-only pushes where it's tempting to skip local validation. The formatting gate is not transient — retrying CI without fixing the files produces the same failure.
