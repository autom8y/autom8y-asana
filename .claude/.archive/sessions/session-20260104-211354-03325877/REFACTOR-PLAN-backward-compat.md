# Refactoring Plan: Backward Compatibility Cleanup

---
title: Refactoring Plan - Greenfield Backward Compat Cleanup
scope: src/autom8_asana/, tests/unit/
generated_at: 2026-01-04T21:45:00Z
generated_by: architect-enforcer (hygiene-pack)
initiative: Greenfield Backward Compat Cleanup
session_id: session-20260104-211354-03325877
source_artifact: SMELL-REPORT-backward-compat.md
total_refactors: 6
phases: 3
estimated_loc_removed: ~759
---

## Executive Summary

This refactoring plan removes backward compatibility artifacts to achieve a greenfield state. All identified smells have been architecturally evaluated and confirmed as safe for removal with no external consumer impact.

**Architectural Assessment:**
- This is a greenfield project with no external consumers
- All deprecated code paths emit warnings but are not actively used
- Boundary separation between `settings.py` / `config.py` / `client.py` will be preserved
- Public API surface (`AsanaClient`, `AsanaConfig`, etc.) remains unchanged

---

## Architectural Analysis

### Boundary Health Assessment

| Module | Role | Health After Cleanup |
|--------|------|---------------------|
| `settings.py` | Pydantic Settings - env var reading | IMPROVED - removes unused fields |
| `config.py` | Runtime dataclass configuration | IMPROVED - removes indirection function |
| `client.py` | Client facade - consumes config | IMPROVED - simplified workspace resolution |

### Root Cause Clusters

1. **ECS Deployment Pattern (Obsolete)**: The `ASANA_TOKEN_KEY` and `ASANA_WORKSPACE_KEY` indirection was designed for ECS deployments with platform naming conventions. This pattern is no longer used.

2. **Static GID Constants (Superseded)**: The `custom_fields.py` module was an MVP solution replaced by dynamic `cf:FieldName` resolution per ADR-0034.

3. **Orphaned Module Tests**: The `_compat.py` module was deleted but its test file remained.

### Public API Impact

| API Surface | Change | Breaking? |
|-------------|--------|-----------|
| `AsanaClient(token=...)` | No change | No |
| `AsanaClient(workspace_gid=...)` | No change | No |
| `AsanaConfig.token_key` | Becomes constant "ASANA_PAT" | No |
| `ASANA_PAT` env var | Remains the canonical way | No |
| `ASANA_WORKSPACE_GID` env var | Remains the canonical way | No |
| `ASANA_TOKEN_KEY` env var | Stops working (was deprecated) | **Expected** |
| `ASANA_WORKSPACE_KEY` env var | Stops working (was deprecated) | **Expected** |

**Justification for "Expected" Breaking Changes:**
- Both deprecated env vars emitted `DeprecationWarning` since introduction
- Documentation marked them as deprecated
- Greenfield project with no external consumers
- Users were warned to migrate to direct env var usage

---

## Refactoring Phases

### Phase 1: Dead Code Removal (Low Risk)

Delete files with zero production dependencies. Safe to delete without modifying other files.

#### RF-001: Delete orphaned test_compat.py

**Smell ID**: DC-MOD-001
**Risk Level**: LOW
**Blast Radius**: Single file

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_compat.py` (410 lines)
- Imports deleted module `autom8_asana._compat`
- All tests will fail on import

**After State:**
- File deleted
- No references to deleted `_compat` module

**Invariants:**
- No production code affected
- Test suite still runs (excluding this file)
- No import cycles created/broken

**Verification:**
```bash
# Pre-condition: File exists
test -f tests/unit/test_compat.py && echo "EXISTS"

# Action: Delete file
rm tests/unit/test_compat.py

# Post-condition: File gone, tests pass
! test -f tests/unit/test_compat.py && echo "DELETED"
pytest tests/unit/ -x --ignore=tests/unit/test_compat.py -q 2>/dev/null | tail -5
```

**Rollback:**
```bash
git checkout HEAD -- tests/unit/test_compat.py
```

---

#### RF-002: Delete deprecated custom_fields.py

**Smell ID**: DC-MOD-002
**Risk Level**: LOW
**Blast Radius**: Single file

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/custom_fields.py` (132 lines)
- Contains 16 `PLACEHOLDER_*` constants
- Emits `DeprecationWarning` on import
- Zero production imports (verified via grep)

**After State:**
- File deleted
- `dataframes/models/__init__.py` unchanged (never exported this module)

**Invariants:**
- Zero production import references
- `dataframes/models/` package continues to export same symbols
- No `PLACEHOLDER_*` constants referenced anywhere

**Verification:**
```bash
# Pre-condition: No production imports
grep -r "from autom8_asana.dataframes.models.custom_fields" src/ --include="*.py" | wc -l
# Expected: 0

# Pre-condition: File exists
test -f src/autom8_asana/dataframes/models/custom_fields.py && echo "EXISTS"

# Action: Delete file
rm src/autom8_asana/dataframes/models/custom_fields.py

# Post-condition: File gone
! test -f src/autom8_asana/dataframes/models/custom_fields.py && echo "DELETED"

# Post-condition: Package still works
python -c "from autom8_asana.dataframes.models import ColumnDef, DataFrameSchema, TaskRow"
```

**Rollback:**
```bash
git checkout HEAD -- src/autom8_asana/dataframes/models/custom_fields.py
```

---

### Phase 2: Config Refactoring (Medium Risk)

Remove indirection patterns from production code. Requires coordinated changes across multiple files.

**Phase 2 Rollback Point:** Before starting Phase 2, ensure Phase 1 is committed. If any Phase 2 refactor fails verification, revert entire Phase 2.

---

#### RF-003: Remove ASANA_TOKEN_KEY indirection from config.py

**Smell ID**: DRY-CFG-001 (partial)
**Risk Level**: MEDIUM
**Blast Radius**: config.py

**Before State:**
```python
# config.py:473-491
def _default_token_key() -> str:
    """Resolve default token key from environment or use ASANA_PAT.
    ...
    """
    settings = get_settings()
    if settings.asana.token_key:
        return settings.asana.token_key
    return "ASANA_PAT"

# config.py:537-538
@dataclass
class AsanaConfig:
    token_key: str = field(default_factory=_default_token_key)
```

**After State:**
```python
# config.py - DELETE _default_token_key function entirely (lines 473-491)

# config.py:537 - Replace default_factory with constant
@dataclass
class AsanaConfig:
    token_key: str = "ASANA_PAT"  # Direct value, no indirection
```

**Invariants:**
- `AsanaConfig().token_key` always returns `"ASANA_PAT"`
- `AsanaClient` continues to work with `ASANA_PAT` env var
- No import changes to config.py

**Verification:**
```bash
# Pre-condition: Function exists
grep -n "def _default_token_key" src/autom8_asana/config.py

# Post-condition: Function removed
! grep -q "def _default_token_key" src/autom8_asana/config.py

# Post-condition: AsanaConfig works
python -c "from autom8_asana.config import AsanaConfig; c = AsanaConfig(); assert c.token_key == 'ASANA_PAT', f'Got {c.token_key}'"

# Post-condition: Tests pass
pytest tests/unit/test_config.py -v -k "not deprecated" --tb=short
```

**Rollback:**
```bash
git checkout HEAD -- src/autom8_asana/config.py
```

---

#### RF-004: Remove ASANA_TOKEN_KEY from settings.py

**Smell ID**: DRY-CFG-001 (complete)
**Risk Level**: MEDIUM
**Blast Radius**: settings.py

**Before State:**
```python
# settings.py:91-111
class AsanaSettings(BaseSettings):
    # ...
    token_key: str | None = Field(
        default=None,
        description="DEPRECATED: Legacy indirection key for PAT lookup",
    )

    @field_validator("token_key", mode="after")
    @classmethod
    def warn_token_key_deprecated(cls, v: str | None) -> str | None:
        """Emit deprecation warning if ASANA_TOKEN_KEY is set."""
        if v is not None:
            warnings.warn(
                "ASANA_TOKEN_KEY is deprecated. Set ASANA_PAT directly.",
                DeprecationWarning,
                stacklevel=2,
            )
        return v
```

**After State:**
```python
# settings.py - REMOVE:
# - token_key field (lines 92-95)
# - warn_token_key_deprecated validator (lines 101-111)
# - ASANA_TOKEN_KEY reference in docstring (lines 12, 61)

class AsanaSettings(BaseSettings):
    # token_key field REMOVED
    # warn_token_key_deprecated validator REMOVED
```

**Invariants:**
- `AsanaSettings` no longer has `token_key` attribute
- Module docstring updated to remove ASANA_TOKEN_KEY reference
- Class docstring updated to remove ASANA_TOKEN_KEY reference

**Verification:**
```bash
# Pre-condition: Field exists
grep -n "token_key:" src/autom8_asana/settings.py

# Post-condition: Field removed
! grep -q "token_key:" src/autom8_asana/settings.py

# Post-condition: Validator removed
! grep -q "warn_token_key_deprecated" src/autom8_asana/settings.py

# Post-condition: Settings work
python -c "from autom8_asana.settings import get_settings; s = get_settings(); assert not hasattr(s.asana, 'token_key'), 'token_key still exists'"

# Post-condition: Tests pass
pytest tests/unit/test_settings.py -v -k "not token_key" --tb=short
```

**Rollback:**
```bash
git checkout HEAD -- src/autom8_asana/settings.py
```

---

#### RF-005: Remove ASANA_WORKSPACE_KEY indirection from client.py

**Smell ID**: DRY-CFG-002 (partial)
**Risk Level**: MEDIUM
**Blast Radius**: client.py

**Before State:**
```python
# client.py:14-47
def _get_workspace_gid_from_env() -> str | None:
    """Get workspace GID from environment.

    Supports ASANA_WORKSPACE_KEY indirection for backward compatibility
    ...
    """
    settings = get_settings()

    # Legacy: Check for ASANA_WORKSPACE_KEY indirection first
    if settings.asana.workspace_key:
        return os.environ.get(settings.asana.workspace_key)

    if settings.asana.workspace_gid:
        return settings.asana.workspace_gid

    return None
```

**After State:**
```python
# client.py - SIMPLIFY to:
def _get_workspace_gid_from_env() -> str | None:
    """Get workspace GID from ASANA_WORKSPACE_GID environment variable.

    Returns:
        Workspace GID if ASANA_WORKSPACE_GID is set, None otherwise.
    """
    settings = get_settings()
    return settings.asana.workspace_gid
```

**Invariants:**
- Function still exists (called from `AsanaClient.__init__`)
- Returns `None` if `ASANA_WORKSPACE_GID` not set
- Returns GID string if `ASANA_WORKSPACE_GID` is set
- No `os.environ.get()` call for indirection

**Verification:**
```bash
# Post-condition: Indirection removed
! grep -q "workspace_key" src/autom8_asana/client.py

# Post-condition: Function simplified
grep -A5 "def _get_workspace_gid_from_env" src/autom8_asana/client.py

# Post-condition: Client works with direct env var
ASANA_WORKSPACE_GID=1234567890123456 python -c "
from autom8_asana.client import _get_workspace_gid_from_env
result = _get_workspace_gid_from_env()
assert result == '1234567890123456', f'Got {result}'
print('OK')
"
```

**Rollback:**
```bash
git checkout HEAD -- src/autom8_asana/client.py
```

---

#### RF-006: Remove ASANA_WORKSPACE_KEY from settings.py

**Smell ID**: DRY-CFG-002 (complete)
**Risk Level**: MEDIUM
**Blast Radius**: settings.py (already modified in RF-004)

**Before State:**
```python
# settings.py:96-123
class AsanaSettings(BaseSettings):
    # ...
    workspace_key: str | None = Field(
        default=None,
        description="DEPRECATED: Legacy indirection key for workspace GID lookup",
    )

    @field_validator("workspace_key", mode="after")
    @classmethod
    def warn_workspace_key_deprecated(cls, v: str | None) -> str | None:
        """Emit deprecation warning if ASANA_WORKSPACE_KEY is set."""
        if v is not None:
            warnings.warn(
                "ASANA_WORKSPACE_KEY is deprecated. Set ASANA_WORKSPACE_GID directly.",
                DeprecationWarning,
                stacklevel=2,
            )
        return v
```

**After State:**
```python
# settings.py - REMOVE:
# - workspace_key field (lines 96-99)
# - warn_workspace_key_deprecated validator (lines 113-123)
# - ASANA_WORKSPACE_KEY reference in docstring (lines 13, 62)

class AsanaSettings(BaseSettings):
    # workspace_key field REMOVED
    # warn_workspace_key_deprecated validator REMOVED
```

**Invariants:**
- `AsanaSettings` no longer has `workspace_key` attribute
- Docstrings updated to remove ASANA_WORKSPACE_KEY references

**Verification:**
```bash
# Post-condition: Field removed
! grep -q "workspace_key:" src/autom8_asana/settings.py

# Post-condition: Validator removed
! grep -q "warn_workspace_key_deprecated" src/autom8_asana/settings.py

# Post-condition: Settings work
python -c "from autom8_asana.settings import get_settings; s = get_settings(); assert not hasattr(s.asana, 'workspace_key'), 'workspace_key still exists'"
```

**Rollback:**
```bash
git checkout HEAD -- src/autom8_asana/settings.py
```

---

### Phase 3: Test Cleanup (Low Risk)

Remove tests for deleted functionality. Must run AFTER Phase 2 production changes.

**Phase 3 Rollback Point:** Before starting Phase 3, ensure Phase 2 is committed. Phase 3 is independent of Phase 2 rollback.

---

#### RF-007: Delete TestWorkspaceGidIndirection test class

**Smell ID**: PR-TEST-001 (partial)
**Risk Level**: LOW
**Blast Radius**: test_client.py

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_client.py:367-467`
- `TestWorkspaceGidIndirection` class (~100 lines)
- Tests deprecated indirection pattern

**After State:**
- Class `TestWorkspaceGidIndirection` deleted
- Other test classes in file unchanged

**Invariants:**
- Other tests in `test_client.py` still pass
- No imports of deleted test class

**Verification:**
```bash
# Pre-condition: Class exists
grep -n "class TestWorkspaceGidIndirection" tests/unit/test_client.py

# Post-condition: Class removed
! grep -q "class TestWorkspaceGidIndirection" tests/unit/test_client.py

# Post-condition: File still valid Python
python -m py_compile tests/unit/test_client.py

# Post-condition: Other tests pass
pytest tests/unit/test_client.py -v -k "not Indirection" --tb=short
```

**Rollback:**
```bash
git checkout HEAD -- tests/unit/test_client.py
```

---

#### RF-008: Delete TestDeprecatedFields test class

**Smell ID**: PR-TEST-001 (complete)
**Risk Level**: LOW
**Blast Radius**: test_settings.py

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_settings.py:339-390`
- `TestDeprecatedFields` class (~51 lines)
- Tests deprecated field warnings

**After State:**
- Class `TestDeprecatedFields` deleted
- Other test classes in file unchanged

**Invariants:**
- Other tests in `test_settings.py` still pass
- No imports of deleted test class

**Verification:**
```bash
# Pre-condition: Class exists
grep -n "class TestDeprecatedFields" tests/unit/test_settings.py

# Post-condition: Class removed
! grep -q "class TestDeprecatedFields" tests/unit/test_settings.py

# Post-condition: File still valid Python
python -m py_compile tests/unit/test_settings.py

# Post-condition: Other tests pass
pytest tests/unit/test_settings.py -v -k "not Deprecated" --tb=short
```

**Rollback:**
```bash
git checkout HEAD -- tests/unit/test_settings.py
```

---

#### RF-009: Update documentation references

**Smell ID**: PR-DOCS-001
**Risk Level**: LOW
**Blast Radius**: config.py, settings.py docstrings

**Before State:**
Docstrings reference deprecated patterns:
- `config.py:503-522` - AsanaConfig docstring mentions ASANA_TOKEN_KEY
- `settings.py:11-13` - Module docstring lists ASANA_TOKEN_KEY, ASANA_WORKSPACE_KEY
- `settings.py:61-62` - AsanaSettings docstring references deprecated keys

**After State:**
- Remove all ASANA_TOKEN_KEY references from docstrings
- Remove all ASANA_WORKSPACE_KEY references from docstrings
- Update examples to show direct env var usage only

**Invariants:**
- No code logic changes
- Docstrings accurate for current behavior
- No grep hits for "ASANA_TOKEN_KEY" or "ASANA_WORKSPACE_KEY"

**Verification:**
```bash
# Post-condition: No deprecated key references
! grep -q "ASANA_TOKEN_KEY" src/autom8_asana/config.py
! grep -q "ASANA_TOKEN_KEY" src/autom8_asana/settings.py
! grep -q "ASANA_WORKSPACE_KEY" src/autom8_asana/settings.py
! grep -q "ASANA_WORKSPACE_KEY" src/autom8_asana/client.py
```

**Rollback:**
```bash
git checkout HEAD -- src/autom8_asana/config.py src/autom8_asana/settings.py src/autom8_asana/client.py
```

---

## Risk Matrix

| Phase | Refactor | Blast Radius | Rollback Cost | Detection Method |
|-------|----------|--------------|---------------|------------------|
| 1 | RF-001 | Single file | Immediate | Import error |
| 1 | RF-002 | Single file | Immediate | Import error |
| 2 | RF-003 | config.py | Immediate | Unit tests |
| 2 | RF-004 | settings.py | Immediate | Unit tests |
| 2 | RF-005 | client.py | Immediate | Unit tests |
| 2 | RF-006 | settings.py | Immediate | Unit tests |
| 3 | RF-007 | test_client.py | Immediate | Test discovery |
| 3 | RF-008 | test_settings.py | Immediate | Test discovery |
| 3 | RF-009 | Docstrings | N/A | grep |

---

## Commit Strategy

### Recommended Commit Sequence

```
Phase 1: Dead code deletion (1 commit)
  chore: remove orphaned backward compat files
  - Delete tests/unit/test_compat.py (orphaned tests for deleted _compat module)
  - Delete src/autom8_asana/dataframes/models/custom_fields.py (deprecated static GIDs)

Phase 2: Config refactoring (1 commit)
  refactor: remove deprecated env var indirection patterns
  - Remove ASANA_TOKEN_KEY indirection from config.py
  - Remove ASANA_TOKEN_KEY field/validator from settings.py
  - Simplify _get_workspace_gid_from_env() in client.py
  - Remove ASANA_WORKSPACE_KEY field/validator from settings.py

  BREAKING: ASANA_TOKEN_KEY and ASANA_WORKSPACE_KEY env vars no longer work.
  Use ASANA_PAT and ASANA_WORKSPACE_GID directly.

Phase 3: Test cleanup (1 commit)
  test: remove deprecated indirection pattern tests
  - Delete TestWorkspaceGidIndirection from test_client.py
  - Delete TestDeprecatedFields from test_settings.py
  - Update docstrings to remove deprecated env var references
```

---

## Janitor Notes

### Critical Ordering

1. **Phase 1 must complete before Phase 2** - Tests in Phase 1 are orphaned and will fail
2. **Phase 2 production changes must complete before Phase 3 test changes** - Tests test production code
3. **RF-003 before RF-004** - config.py calls settings, but change is isolated
4. **RF-005 can run parallel to RF-003/RF-004** - client.py has independent logic
5. **RF-006 must follow RF-004** - Both modify settings.py

### Test Requirements

After each phase, run:
```bash
# Full test suite excluding known-orphaned tests
pytest tests/unit/ --ignore=tests/unit/test_compat.py -v --tb=short
```

### Commit Message Convention

Use conventional commits with scope:
- `chore(cleanup):` for dead code removal
- `refactor(config):` for configuration changes
- `test(cleanup):` for test file changes

Include `BREAKING CHANGE:` footer for Phase 2 commit.

---

## Verification Attestation

| Artifact | Path | Status |
|----------|------|--------|
| Smell Report | `.claude/sessions/session-20260104-211354-03325877/SMELL-REPORT-backward-compat.md` | Read and analyzed |
| config.py | `src/autom8_asana/config.py` | Read (604 lines) |
| settings.py | `src/autom8_asana/settings.py` | Read (474 lines) |
| client.py | `src/autom8_asana/client.py` | Read (1065 lines) |
| custom_fields.py | `src/autom8_asana/dataframes/models/custom_fields.py` | Read (132 lines) |
| test_compat.py | `tests/unit/test_compat.py` | Read (410 lines) |
| test_client.py (partial) | `tests/unit/test_client.py:360-479` | Read |
| test_settings.py (partial) | `tests/unit/test_settings.py:330-404` | Read |
| dataframes/models/__init__.py | `src/autom8_asana/dataframes/models/__init__.py` | Read - confirms no custom_fields export |
| Production grep for custom_fields | `src/autom8_asana/` | Confirmed zero imports of deprecated module |

---

**Handoff**: Ready for janitor to execute refactoring plan. All contracts specified with verification criteria.
