# Principal Engineer Memory

## Pydantic Forward Reference Pattern (2026-02-23)

**Critical**: All model files in `src/autom8_asana/models/` use `from __future__ import annotations` with `NameGid` imported only under `TYPE_CHECKING`. This makes `NameGid` invisible at runtime. Pydantic v2 cannot resolve the forward reference string without `model_rebuild(_types_namespace={"NameGid": NameGid})`.

**Resolution locations**:
- `src/autom8_asana/models/__init__.py` -- resolves for application code paths
- `tests/conftest.py` `_bootstrap_session` fixture -- resolves for test code that imports directly from submodules

**Key insight**: `Task.model_rebuild()` propagates to ALL subclasses (BusinessEntity, Offer, DNA, etc.) automatically.

## Pre-existing Test Failures (2026-02-23)

~203 test failures are pre-existing and documented in `.wip/REMEDY-tests-unit-p1.md`:
- `test_routes_dataframes.py` (42 failures) -- API route changes not reflected in tests (422 vs 200)
- `test_client.py` (12 failures) -- httpx mock target issue (H-001 in remedy report)
- `test_contract_alignment.py` (21 failures) -- contract tests referencing wrong APIs
- Various other API route tests returning 422 instead of expected 200

These are NOT caused by RF-010/011/012 directory reorg. They predate those commits.

## Git Stash Warning

Using `git stash` + `git checkout <ref> -- tests/` + `git stash pop` leaves behind untracked files from the stash that won't be cleaned by `git checkout HEAD -- tests/`. Must manually remove stale files after stash pop. Avoid this pattern; use worktrees instead.

## Test Baseline

Current healthy baseline with model_rebuild fix: ~11,123 passed, ~203 failed, 46 skipped, 0 errors.
The "10,552 passed" baseline referenced in MEMORY.md predates the RF-008/009 adversarial test triage.
