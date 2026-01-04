# Code Smell Report: Backward Compatibility Cleanup

---
title: Code Smell Report - Backward Compatibility Cleanup
scope: src/autom8_asana/, tests/unit/
generated_at: 2026-01-04T21:20:00Z
generated_by: code-smeller (hygiene-pack)
initiative: Greenfield Backward Compat Cleanup
session_id: session-20260104-211354-03325877
total_smells: 6
severity_breakdown:
  critical: 0
  high: 2
  medium: 3
  low: 1
categories:
  - Dead Code
  - DRY Violations
  - Process Smells
---

## Executive Summary

This smell report validates the prior reconnaissance and confirms the current state of backward compatibility code in the autom8_asana codebase. The goal is to achieve a greenfield state by removing all backward compatibility artifacts.

**Verification Status**:
- `src/autom8_asana/_compat.py` - CONFIRMED DELETED (git shows deleted, file does not exist)
- `src/autom8_asana/transport/http.py` - CONFIRMED DELETED (file does not exist)
- `src/autom8_asana/dataframes/models/custom_fields.py` - CONFIRMED EXISTS (133 LOC, zero production imports)
- Env var indirection (ASANA_TOKEN_KEY, ASANA_WORKSPACE_KEY) - CONFIRMED EXISTS in production code

---

## Dead Code

### DC-MOD-001: Orphaned test file for deleted _compat module

**smell_id**: DC-MOD-001
**smell_type**: DC-MOD
**category**: Dead Code
**severity**: HIGH
**priority**: P2
**score**: 12

**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_compat.py:1-411` (entire file)

**Description**: Test file `test_compat.py` tests the deleted `_compat.py` module. The source module has been removed but its 411-line test file remains. All tests in this file will fail on import since `autom8_asana._compat` no longer exists.

**Evidence**:
```python
# Line 25: Imports deleted module
from autom8_asana._compat import Task

# Line 391-396: References deleted module
def test_internal_modules_have_underscore_prefix(self) -> None:
    import autom8_asana._compat  # Will fail - module deleted
```

**Factors**:
- Impact: 3 (tests will fail, blocks CI if not skipped)
- Frequency: 3 (every test run)
- Blast Radius: 1 (single file)
- Fix Complexity: 1 (safe to delete entirely)

**Detection Method**: Glob + Read (automated)

**Recommendation**: DELETE entire file `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_compat.py`

---

### DC-MOD-002: Deprecated custom_fields.py with placeholder constants

**smell_id**: DC-MOD-002
**smell_type**: DC-MOD
**category**: Dead Code
**severity**: MEDIUM
**priority**: P3
**score**: 8

**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/custom_fields.py:1-133` (entire file)

**Description**: Module contains 16 PLACEHOLDER_* constants that were never populated with real GIDs. Per ADR-0034, this module is deprecated in favor of dynamic `source="cf:FieldName"` resolution. Zero production imports exist.

**Evidence**:
```python
# Lines 36-42: Emits deprecation warning on import
warnings.warn(
    "autom8_asana.dataframes.models.custom_fields is deprecated. "
    "Use dynamic resolution with source='cf:FieldName' in schemas instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Lines 49-108: All constants are placeholders
MRR_GID: str = "PLACEHOLDER_MRR_GID"
WEEKLY_AD_SPEND_GID: str = "PLACEHOLDER_WEEKLY_AD_SPEND_GID"
# ... 14 more PLACEHOLDER_* constants
```

**Import Verification**:
```
grep "from autom8_asana\.dataframes\.models\.custom_fields" src/
# Result: Only self-reference in docstring (line 20)
```

**Factors**:
- Impact: 2 (dead code, but no runtime effect)
- Frequency: 1 (never imported)
- Blast Radius: 1 (single file)
- Fix Complexity: 1 (safe to delete)

**Detection Method**: Grep import search (automated)

**Recommendation**: DELETE entire file `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/custom_fields.py`

---

## DRY Violations / Complexity

### DRY-CFG-001: ASANA_TOKEN_KEY env var indirection pattern

**smell_id**: DRY-CFG-001
**smell_type**: DRY-CFG
**category**: DRY Violations
**severity**: HIGH
**priority**: P2
**score**: 14

**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py:473-491` (`_default_token_key` function)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py:503-507` (docstring references)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py:537-538` (field default_factory)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py:92-111` (field + validator)

**Description**: The ASANA_TOKEN_KEY indirection pattern (env var pointing to another env var name) is deprecated but still wired into production code. This adds unnecessary complexity and confusing behavior.

**Evidence**:
```python
# config.py:473-491 - Indirection function
def _default_token_key() -> str:
    """Resolve default token key from environment or use ASANA_PAT.
    Note: ASANA_TOKEN_KEY indirection is deprecated. Prefer setting ASANA_PAT directly.
    """
    settings = get_settings()
    if settings.asana.token_key:
        return settings.asana.token_key  # Returns the KEY NAME, not the token
    return "ASANA_PAT"

# settings.py:101-111 - Deprecation validator
@field_validator("token_key", mode="after")
def warn_token_key_deprecated(cls, v: str | None) -> str | None:
    if v is not None:
        warnings.warn(
            "ASANA_TOKEN_KEY is deprecated. Set ASANA_PAT directly.",
            DeprecationWarning,
        )
    return v
```

**Factors**:
- Impact: 3 (confusing API, potential user errors)
- Frequency: 2 (affects every client instantiation with env var)
- Blast Radius: 2 (config.py + settings.py)
- Fix Complexity: 2 (requires removing field, validator, and function)

**Detection Method**: Grep pattern search (automated)

**Recommendation**:
1. Remove `token_key` field from `AsanaSettings`
2. Remove `warn_token_key_deprecated` validator
3. Remove `_default_token_key()` function
4. Simplify `AsanaConfig.token_key` to always be `"ASANA_PAT"`

---

### DRY-CFG-002: ASANA_WORKSPACE_KEY env var indirection pattern

**smell_id**: DRY-CFG-002
**smell_type**: DRY-CFG
**category**: DRY Violations
**severity**: MEDIUM
**priority**: P3
**score**: 10

**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py:14-47` (`_get_workspace_gid_from_env` function)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py:233-234` (usage in __init__)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py:96-123` (field + validator)

**Description**: Parallel indirection pattern for workspace GID. ASANA_WORKSPACE_KEY points to another env var containing the actual GID. This adds complexity that should be removed.

**Evidence**:
```python
# client.py:14-47
def _get_workspace_gid_from_env() -> str | None:
    """Supports ASANA_WORKSPACE_KEY indirection for backward compatibility"""
    settings = get_settings()
    # Legacy: Check for ASANA_WORKSPACE_KEY indirection first
    if settings.asana.workspace_key:
        return os.environ.get(settings.asana.workspace_key)
    if settings.asana.workspace_gid:
        return settings.asana.workspace_gid
    return None

# settings.py:113-123 - Deprecation validator
@field_validator("workspace_key", mode="after")
def warn_workspace_key_deprecated(cls, v: str | None) -> str | None:
    if v is not None:
        warnings.warn(
            "ASANA_WORKSPACE_KEY is deprecated. Set ASANA_WORKSPACE_GID directly.",
            DeprecationWarning,
        )
    return v
```

**Factors**:
- Impact: 2 (confusing but less critical than token)
- Frequency: 2 (affects workspace resolution)
- Blast Radius: 2 (client.py + settings.py)
- Fix Complexity: 2 (requires removing field, validator, and function)

**Detection Method**: Grep pattern search (automated)

**Recommendation**:
1. Remove `workspace_key` field from `AsanaSettings`
2. Remove `warn_workspace_key_deprecated` validator
3. Simplify `_get_workspace_gid_from_env()` to only check `settings.asana.workspace_gid`

---

## Process Smells

### PR-TEST-001: Orphaned tests for deprecated indirection patterns

**smell_id**: PR-TEST-001
**smell_type**: PR-TEST
**category**: Process Smells
**severity**: MEDIUM
**priority**: P3
**score**: 7

**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_client.py:367-467` (`TestWorkspaceGidIndirection` class)
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_settings.py:339-384` (`TestDeprecatedFields` class)

**Description**: Test classes exist specifically to test the deprecated indirection patterns. Once the patterns are removed, these tests become dead code.

**Evidence**:
```python
# test_client.py:367-467
class TestWorkspaceGidIndirection:
    """Tests for ASANA_WORKSPACE_KEY indirection pattern."""
    def test_get_workspace_gid_with_indirection(...):
        monkeypatch.setenv("ASANA_WORKSPACE_KEY", "WORKSPACE_GID")
        # Tests the pattern we're removing
    def test_ecs_deployment_pattern(...):
        # Tests ECS-specific indirection that's being deprecated

# test_settings.py:339-384
class TestDeprecatedFields:
    """Tests for deprecated field warnings."""
    def test_token_key_emits_deprecation_warning(...):
        # Tests warning emission we're removing
    def test_workspace_key_emits_deprecation_warning(...):
        # Tests warning emission we're removing
```

**Factors**:
- Impact: 2 (tests dead features)
- Frequency: 1 (tests still pass until code removed)
- Blast Radius: 2 (2 test files)
- Fix Complexity: 1 (delete test classes after production code removed)

**Detection Method**: Grep class names (semi-automated)

**Recommendation**: DELETE after removing production code:
- `TestWorkspaceGidIndirection` (test_client.py:367-467, ~100 lines)
- `TestDeprecatedFields` (test_settings.py:339-384, ~45 lines)

---

### PR-DOCS-001: Documentation references to deprecated patterns

**smell_id**: PR-DOCS-001
**smell_type**: PR-DOCS
**category**: Process Smells
**severity**: LOW
**priority**: P4
**score**: 4

**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py:503-522` (AsanaConfig docstring)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py:11-13` (module docstring)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/settings.py:61-62` (class docstring)

**Description**: Docstrings still document the deprecated ASANA_TOKEN_KEY and ASANA_WORKSPACE_KEY patterns. These should be removed when the patterns are removed.

**Evidence**:
```python
# config.py:503-522
"""
Attributes:
    token_key: Environment variable name containing the Asana PAT.
        Defaults to reading ASANA_TOKEN_KEY env var, falling back to "ASANA_PAT".
        In ECS deployments with autom8y naming convention, set
        ASANA_TOKEN_KEY=BOT_PAT to read from the injected secret.
...
    # ECS deployment: Set ASANA_TOKEN_KEY=BOT_PAT in environment
    # SDK will automatically read from BOT_PAT env var
"""
```

**Factors**:
- Impact: 1 (documentation only)
- Frequency: 1 (reading docs)
- Blast Radius: 2 (multiple files)
- Fix Complexity: 1 (update docstrings)

**Detection Method**: Code review (manual)

**Recommendation**: Update docstrings to remove all ASANA_TOKEN_KEY and ASANA_WORKSPACE_KEY references when cleaning up production code.

---

## Prioritized Remediation Order

Based on ROI scoring (severity x frequency x blast_radius / fix_complexity):

| Priority | Smell ID | Description | Action | Estimated LOC |
|----------|----------|-------------|--------|---------------|
| 1 | DC-MOD-001 | test_compat.py orphaned tests | DELETE file | -411 |
| 2 | DC-MOD-002 | custom_fields.py dead module | DELETE file | -133 |
| 3 | DRY-CFG-001 | ASANA_TOKEN_KEY indirection | REFACTOR config.py, settings.py | -30 |
| 4 | DRY-CFG-002 | ASANA_WORKSPACE_KEY indirection | REFACTOR client.py, settings.py | -40 |
| 5 | PR-TEST-001 | Indirection test classes | DELETE after #3, #4 | -145 |
| 6 | PR-DOCS-001 | Documentation cleanup | UPDATE docstrings | ~0 (rewrites) |

**Total Estimated Removal**: ~759 lines of backward compatibility code

---

## Boundary Violation Flags for Architect Enforcer

The following items require architectural judgment:

1. **DRY-CFG-001 / DRY-CFG-002**: The env var indirection pattern crosses the config/settings/client boundary. Architect Enforcer should validate that removing this doesn't break the clean separation between:
   - `settings.py` (Pydantic Settings - reads env vars)
   - `config.py` (AsanaConfig dataclass - runtime configuration)
   - `client.py` (AsanaClient - consumes configuration)

2. **DC-MOD-002**: Verify `custom_fields.py` deletion doesn't require a stub for external package compatibility. The `dataframes/models/` directory structure should be reviewed.

---

## Verification Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| _compat.py deleted | src/autom8_asana/_compat.py | File does not exist (git deleted) |
| transport/http.py deleted | src/autom8_asana/transport/http.py | File does not exist |
| custom_fields.py exists | src/autom8_asana/dataframes/models/custom_fields.py | 133 LOC, zero prod imports |
| test_compat.py orphaned | tests/unit/test_compat.py | 411 LOC, imports deleted module |
| Token indirection active | config.py, settings.py | Confirmed in production code |
| Workspace indirection active | client.py, settings.py | Confirmed in production code |

---

**Handoff**: Ready for architect-enforcer to produce Refactor-plan based on prioritized remediation order.
