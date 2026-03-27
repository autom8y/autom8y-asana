---
name: formatting_check_ci_failure
description: ruff format --check and ruff check CI failure patterns on cascade dataframe layer files; blocked Stage 1 across Rounds 1 and 2 for the 2026-03-26 PATCH release
type: project
---

In the 2026-03-26 PATCH release, Stage 1 (`ci / Lint & Type Check`) has now failed across two consecutive rounds due to ruff violations in `src/autom8_asana/dataframes/builders/cascade_validator.py`.

**Round 1 (commit bbba220):** Formatting gate (step 9, `ruff format --check`) failed. 5 files would be reformatted. Fix: run `ruff format` on all 5 files.

**Round 2 (commit e528dc1):** Formatting gate PASSED (step 9 success -- fix confirmed). Lint gate (step 10, `ruff check`) FAILED with 3 violations in `cascade_validator.py`:
- I001 -- import block un-sorted at line ~114 (the in-function import block reordered by the formatter, now exposing isort order)
- F401 -- unused `import re` at line ~414
- F841 -- unused variable `total_rows = len(df)` at line ~416

Note: `ruff format` and `ruff check` are separate tools. Running only `ruff format` does not fix import ordering (I001), unused imports (F401), or unused variables (F841). Both must exit 0 locally before pushing.

In Round 2: ci/Test and ci/Integration Tests both passed. The only blocker is lint. Stage 2 (Satellite Dispatch) fired but concluded skipped. Stage 3 not reached.

**Why:** The cascade dataframe layer is a recurring source of format/lint drift. When new logic is introduced in this layer (cascade source normalization, phone normalization), the formatter is not consistently run locally before push, and ruff check is not run at all. This is the third CI failure pattern from this area.

**How to apply:** When monitoring any push that touches `cascade_validator.py` or other cascade dataframe files and Stage 1 fails:
1. Check step 9 first (Check formatting). If failed: `uv run ruff format .`
2. Then check step 10 (Run linting). If failed: `uv run ruff check --fix .` for auto-fixable; handle F841 manually.
3. Run both commands locally before pushing, in order. Do not run only one.
Classification for lint violations: `regression`, recommendation: `fix_and_retry`.
