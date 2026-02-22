# S5 Refactoring Contracts: Deep Slop Triage

**Date**: 2026-02-19
**Sprint**: Deep Slop Triage (16 items)
**Agent**: architect-enforcer
**Input**: REMEDY-deep-triage-2026-02.md (code-smeller findings)
**Test Baseline**: 10,552 passed, 46 skipped, 2 xfailed

---

## Architectural Assessment

### Classification

The 16 items break into three tiers:

1. **Security/Correctness (2 items)**: RS-M01 (regex injection), RS-M02 (PII leakage) -- genuine runtime risk, must be addressed first.
2. **Automated cleanup (8 items)**: RS-A01 through RS-A08 -- mechanical changes with zero behavioral risk; any competent grep+edit can execute these.
3. **Manual cleanup (6 items)**: RS-M03 through RS-M15 -- require judgment calls on scope or verification gates.

### Boundary Health

All 16 items are **local** concerns. None crosses architectural boundaries, changes public API contracts, or affects module structure. This is pure slop cleanup -- residual comments, stale imports, dead code, and two correctness issues that slipped through prior passes.

### Root Causes

- **Spike artifacts**: SPIKE-BREAK-CIRCULAR-DEP tags left in production code (RS-A04, RS-A05, RS-A06)
- **Migration residue**: TYPE_CHECKING imports pointing to deleted `models/core.py` (RS-A02), stale `_mask_canonical_key` import path (RS-M04)
- **Incomplete extraction**: dead `_parse_content_disposition_filename` in client.py after it was already extracted to `_endpoints/export.py` (RS-A03)
- **Overly broad exceptions**: `(ValueError, Exception)` where `Exception` subsumes `ValueError` (RS-M08)

---

## Batch 1 -- Blocking (Security + Correctness)

### RF-DST-001: Regex injection in `generate_entity_name`

**ID**: RS-M01

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py`
- **Lines 82-96**:

```python
    if business_name:
        # Replace [Business Name] variants
        result = re.sub(
            r"\[business\s*name\]",
            business_name,
            result,
            flags=re.IGNORECASE,
        )

    if unit_name:
        # Replace [Unit Name] or [Business Unit Name] variants
        result = re.sub(
            r"\[(business\s*)?unit\s*name\]",
            unit_name,
            result,
            flags=re.IGNORECASE,
        )
```

**Problem**: `re.sub()` interprets the replacement string for backreference sequences. A business name like `"Acme \1 Corp"` or `"Price: $100"` (where `$` is not special in Python's `re.sub` but `\1` is) would corrupt the output. The `\1` would be interpreted as a group backreference, producing an empty string or raising `re.error` depending on whether group 1 exists in the pattern.

**After State**:
- Same file, lines 82-96 replaced:

```python
    if business_name:
        # Replace [Business Name] variants
        # Use lambda to avoid backreference interpretation in replacement string
        result = re.sub(
            r"\[business\s*name\]",
            lambda m: business_name,
            result,
            flags=re.IGNORECASE,
        )

    if unit_name:
        # Replace [Unit Name] or [Business Unit Name] variants
        # Use lambda to avoid backreference interpretation in replacement string
        result = re.sub(
            r"\[(business\s*)?unit\s*name\]",
            lambda m: unit_name,
            result,
            flags=re.IGNORECASE,
        )
```

**Invariants**:
- All existing tests pass without modification
- For normal business/unit names (no backslash sequences), output is identical
- For names containing `\1`, `\2`, etc., output now correctly includes the literal backslash sequence

**Test Requirement**: Add a regression test for a business name containing `r"\1"`:

```python
# In tests for generate_entity_name:
def test_business_name_with_backslash_sequence():
    result = generate_entity_name(
        "Process - [Business Name]",
        business=type("B", (), {"name": r"Acme \1 Corp"})(),
        unit=None,
    )
    assert result == r"Process - Acme \1 Corp"
```

**Verification**:
1. Run: `pytest tests/ -k "generate_entity_name or creation" -x`
2. Confirm all existing tests pass
3. Confirm new regression test passes

**Risk**: LOW. The lambda pattern is the standard Python idiom for literal replacement strings. No import changes, no signature changes, no behavioral change for any name that does not contain backslash-digit sequences.

---

### RF-DST-002: PII leakage in `gid_push.py` log output

**ID**: RS-M02

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/gid_push.py`
- **Line 232**: `"response_text": response.text[:500],` -- logs raw HTTP response body that may echo back phone numbers or PII from the request payload
- **Lines 242, 254**: `"error": str(e),` -- logs exception messages that may contain PII from the request URL or payload

**After State**:

Add import at top of file (after line 18):

```python
from autom8_asana.clients.data._pii import mask_pii_in_string
```

Replace line 232:

```python
                "response_text": mask_pii_in_string(response.text[:500]),
```

Replace line 242:

```python
                "error": mask_pii_in_string(str(e)),
```

Replace line 254:

```python
                "error": mask_pii_in_string(str(e)),
```

**Circular Import Check**: `gid_push.py` imports from `autom8_asana.services.gid_lookup`. The `_pii` module imports only `re` from the stdlib. There is no import cycle -- `clients.data._pii` does not import from `services`. VERIFIED SAFE.

**Invariants**:
- Same log event names (`gid_push_failed`, `gid_push_timeout`, `gid_push_error`)
- Same log levels (warning, warning, error)
- Same return values (False, False, False)
- Same exception propagation behavior (none -- all caught)
- Log output now masks E.164 phone numbers via `_PHONE_PATTERN`

**Verification**:
1. Run: `pytest tests/ -k "gid_push" -x`
2. Manually verify no circular import: `python -c "from autom8_asana.services.gid_push import push_gid_mappings_to_data_service"`

**Risk**: LOW. `mask_pii_in_string` is a proven function with 14 existing tests. Adding it to 3 log sites is mechanical.

---

## Batch 2 -- AUTO Patches

### RF-DST-003: Add missing re-exports to `clients/data/__init__.py`

**ID**: RS-A01

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/__init__.py`
- `client.py` imports and uses `BatchInsightsResponse`, `BatchInsightsResult`, and `ExportResult` from `clients/data/models.py`, but `__init__.py` does not re-export them. External consumers must use the deep import path.

**After State**:

Replace the imports block (lines 14-19):

```python
from autom8_asana.clients.data.models import (
    BatchInsightsResponse,
    BatchInsightsResult,
    ColumnInfo,
    ExportResult,
    InsightsMetadata,
    InsightsRequest,
    InsightsResponse,
)
```

Replace the `__all__` list (lines 21-35):

```python
__all__ = [
    # Client class (per Story 1.5)
    "DataServiceClient",
    # Config classes (per Story 1.3)
    "CircuitBreakerConfig",
    "ConnectionPoolConfig",
    "DataServiceConfig",
    "RetryConfig",
    "TimeoutConfig",
    # Model classes
    "BatchInsightsResponse",
    "BatchInsightsResult",
    "ColumnInfo",
    "ExportResult",
    "InsightsMetadata",
    "InsightsRequest",
    "InsightsResponse",
]
```

**Invariants**:
- All existing imports from `autom8_asana.clients.data` continue to work
- No behavioral change -- purely additive re-exports

**Verification**:
1. `python -c "from autom8_asana.clients.data import BatchInsightsResponse, BatchInsightsResult, ExportResult"`
2. Run: `pytest tests/unit/clients/data/ -x`

**Risk**: NONE. Additive change only.

---

### RF-DST-004: Fix stale TYPE_CHECKING imports

**ID**: RS-A02

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py`, line 21:
  ```python
      from autom8_asana.models.core import Task
  ```
  `models/core.py` does not exist. This import is never executed at runtime (inside `TYPE_CHECKING` block), but it is wrong for type checkers and IDE navigation.

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/templates.py`, line 17:
  ```python
      from autom8_asana.models.core import Section, Task
  ```
  Same issue.

**After State**:

In `creation.py`, replace line 21:
```python
    from autom8_asana.models.task import Task
```

In `templates.py`, replace line 17:
```python
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task
```

**Invariants**:
- Zero runtime behavior change (TYPE_CHECKING block is never executed)
- `models/task.py` exports `class Task(AsanaResource)` at line 27 -- VERIFIED
- `models/section.py` exports `class Section(AsanaResource)` at line 24 -- VERIFIED

**Verification**:
1. Run: `pytest tests/ -k "creation or template" -x`
2. Run: `mypy src/autom8_asana/core/creation.py src/autom8_asana/automation/templates.py --no-error-summary` (should have no new errors from these imports)

**Risk**: NONE. TYPE_CHECKING block only.

---

### RF-DST-005: Remove dead `_parse_content_disposition_filename` from `client.py`

**ID**: RS-A03

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py`
- **Lines 1250-1261**: Module-level function `_parse_content_disposition_filename` that is dead code. The same function already exists in `_endpoints/export.py` (lines 27-38) and is used there (line 148). The copy in `client.py` has zero callers.
- **Line 15**: `import re` is used ONLY by this dead function (verified: the only `re.` usage in client.py is line 1260).

**After State**:

Delete lines 1250-1261 entirely:
```python
def _parse_content_disposition_filename(header: str) -> str | None:
    """Extract filename from Content-Disposition header.

    Args:
        header: Content-Disposition header value.

    Returns:
        Filename string or None if not parseable.
    """
    # Pattern: attachment; filename="conversations_17705753103_20260210.csv"
    match = re.search(r'filename="?([^";\s]+)"?', header)
    return match.group(1) if match else None
```

Delete `import re` from line 15 (the only usage was in the deleted function).

**Invariants**:
- `_endpoints/export.py` continues to use its own copy of this function -- UNAFFECTED
- No caller in `client.py` references `_parse_content_disposition_filename` -- VERIFIED by grep
- `import re` removal is safe because the only `re.` usage in client.py is line 1260 (inside the deleted function)

**Verification**:
1. Run: `pytest tests/unit/clients/data/ -x`
2. `grep -n "re\." src/autom8_asana/clients/data/client.py` should return zero matches after removal

**Risk**: NONE. Dead code removal.

---

### RF-DST-006: Strip SPIKE-BREAK-CIRCULAR-DEP tags

**ID**: RS-A04

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/gid_push.py`, lines 1-9 (module docstring):
  ```python
  """Push GID mappings to autom8_data after index rebuild.

  Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: After the cache warmer rebuilds
  GID indexes, push the mapping snapshot to autom8_data's sync endpoint
  so autom8_data can serve GID lookups locally without calling back to
  autom8_asana.

  The push is best-effort: failure does NOT fail the cache warmer.
  """
  ```

- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_warmer.py`, line 243:
  ```python
      Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: After cache warming, iterate over
  ```
- Same file, lines 711-712:
  ```python
        # GID mapping push (Phase 3: SPIKE-BREAK-CIRCULAR-DEP)
  ```

**After State**:

In `gid_push.py`, replace the module docstring (lines 1-9):
```python
"""Push GID mappings to autom8_data after index rebuild.

After the cache warmer rebuilds GID indexes, push the mapping snapshot
to autom8_data's sync endpoint so autom8_data can serve GID lookups
locally without calling back to autom8_asana.

The push is best-effort: failure does NOT fail the cache warmer.
"""
```

In `cache_warmer.py`, replace line 243:
```python
    After cache warming, iterate over
```

In `cache_warmer.py`, replace lines 711-712:
```python
        # GID mapping push
```

**Invariants**: Zero behavioral change. Comment/docstring only.

**Verification**: `pytest tests/ -k "gid_push or cache_warmer" -x`

**Risk**: NONE. Documentation only.

---

### RF-DST-007: Strip HOTFIX: prefix from comments

**ID**: RS-A05

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_warmer.py`
- **Lines 56-60**: `_ensure_bootstrap()` docstring:
  ```python
    """Lazy bootstrap initialization for Lambda cold starts.

    HOTFIX: Moved from module-level import to avoid import chain failures
    when autom8y_cache has missing modules. The bootstrap populates
    ProjectTypeRegistry for Tier 1 detection.
    """
  ```
- **Line 829**: `# HOTFIX: Lazy bootstrap to avoid import chain failures`
- **Line 902**: `# HOTFIX: Lazy bootstrap to avoid import chain failures`

**After State**:

Replace lines 56-60:
```python
    """Lazy bootstrap initialization for Lambda cold starts.

    Moved from module-level import to avoid import chain failures
    when autom8y_cache has missing modules. The bootstrap populates
    ProjectTypeRegistry for Tier 1 detection.
    """
```

Replace line 829:
```python
    # Lazy bootstrap to avoid import chain failures
```

Replace line 902:
```python
    # Lazy bootstrap to avoid import chain failures
```

**Invariants**: Zero behavioral change. Comment text only.

**Verification**: `pytest tests/ -k "cache_warmer" -x`

**Risk**: NONE. Documentation only.

---

### RF-DST-008: Replace migration note docstring in `freshness.py`

**ID**: RS-A06

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/freshness.py`, lines 1-7:
  ```python
  """Cache freshness modes for controlling validation behavior.

  Migration Note (SDK-PRIMITIVES-001):
      This module now re-exports autom8y_cache.Freshness which includes
      IMMEDIATE mode in addition to STRICT and EVENTUAL. The local enum
      is deprecated in favor of the SDK version.
  """
  ```

**After State**:

Replace lines 1-7:
```python
"""Cache freshness modes for controlling validation behavior.

Re-exports autom8y_cache.Freshness which includes STRICT, EVENTUAL,
and IMMEDIATE modes. Falls back to a local enum when the SDK import
is unavailable (Lambda version mismatch scenarios).
"""
```

**Invariants**: Zero behavioral change. Docstring text only.

**Verification**: `pytest tests/ -k "freshness" -x`

**Risk**: NONE. Documentation only.

---

### RF-DST-009: Close D-014 in debt ledger

**ID**: RS-A07

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/docs/debt/LEDGER-cleanup-modernization.md`
- **Lines 207-213**: D-014 entry says `PipelineAutoCompletionService` wrapper exists in `lifecycle/completion.py:102-135`.
- **Verification**: `PipelineAutoCompletionService` has zero matches in `src/` -- the class was already removed. D-014 is resolved but not marked as such.

**After State**:

Add `[CLOSED]` to the D-014 header line and append a note:

Replace line 207:
```markdown
### D-014: Deprecated `PipelineAutoCompletionService` wrapper [CLOSED]
```

Append after line 213:
```markdown
- **Status**: CLOSED (2026-02-19). Class already removed from `lifecycle/completion.py`. Confirmed zero references in `src/`.
```

**Invariants**: No code change. Ledger documentation update only.

**Verification**: `grep -rn "PipelineAutoCompletionService" src/` should return zero matches (already verified).

**Risk**: NONE.

---

### RF-DST-010: Remove dead `expected_type` deprecated parameter

**ID**: RS-A08

**Gate**: VERIFY ZERO CALLERS FIRST.

**Caller Verification**:
- `grep -rn "expected_type=" src/` -- **ZERO MATCHES** (verified above)
- The `expected_type` parameter has a default of `None` in both protocol and implementation.
- No caller passes `expected_type=` as a keyword argument.
- The parameter is positional at position 3, but since no caller uses it by position either (all callers use keyword `column_def=`), removal of the default-None parameter is safe.

**DECISION**: DEFER. While there are zero explicit callers, removing a parameter from a Protocol is a public API change. Any external consumer implementing `CustomFieldResolver` would break if their `get_value` signature includes `expected_type`. The parameter has `None` as default, costs nothing at runtime, and the deprecation comment serves as documentation. The risk/reward ratio does not justify removal in a slop cleanup pass.

**Recommendation**: Leave `expected_type` in place. Remove it when the Protocol is next revised for a feature change.

---

## Batch 3 -- Low-Effort Manual

### RF-DST-011: Remove `create_dataframe_builder` dead stub

**ID**: RS-M03

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/builders/__init__.py`
- **Lines 71-108**: Function `create_dataframe_builder` that unconditionally raises `NotImplementedError`. Zero callers in `src/` or `tests/` (verified by grep).
- **Line 20**: Module docstring lists it: `- create_dataframe_builder: Factory function for creating DataFrame builder`
- **Line 133**: `__all__` includes `"create_dataframe_builder"`
- **Lines 66-68**: `TYPE_CHECKING` imports for the function signature:
  ```python
  if TYPE_CHECKING:
      from autom8_asana.cache.providers.unified import UnifiedTaskStore
      from autom8_asana.clients.tasks import TasksClient
  ```

**After State**:

Delete lines 66-68 (TYPE_CHECKING block -- only used by the dead function):
```python
if TYPE_CHECKING:
    from autom8_asana.cache.providers.unified import UnifiedTaskStore
    from autom8_asana.clients.tasks import TasksClient
```

Delete lines 71-108 (the entire function body).

Remove from module docstring (line 20):
Replace:
```python
    - create_dataframe_builder: Factory function for creating DataFrame builder
```
With nothing (delete the line).

Remove from `__all__` (lines 132-133):
Delete:
```python
    # Factory
    "create_dataframe_builder",
```

**Invariants**:
- Zero callers exist -- verified by grep across `src/` and `tests/`
- All other exports from `__init__.py` remain unchanged
- `ProgressiveProjectBuilder` (the recommended replacement) is unaffected

**Verification**:
1. Run: `pytest tests/ -k "dataframe" -x`
2. `python -c "from autom8_asana.dataframes.builders import ProgressiveProjectBuilder"` (still works)
3. `python -c "from autom8_asana.dataframes.builders import create_dataframe_builder"` (should raise ImportError)

**Risk**: LOW. Dead code removal. If any external consumer imported this name, they would get `ImportError` instead of `NotImplementedError` at call time -- a marginal behavior change from "crash when called" to "crash when imported."

---

### RF-DST-012: Fix test imports in `test_pii.py`

**ID**: RS-M04

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/tests/unit/clients/data/test_pii.py`
- Lines 134, 143, 153, 163, 171: Import `_mask_pii_in_string` from `autom8_asana.clients.data.client`:
  ```python
  from autom8_asana.clients.data.client import _mask_pii_in_string
  ```
  This works because `client.py` re-exports from `_pii.py`:
  ```python
  from autom8_asana.clients.data._pii import (
      mask_pii_in_string as _mask_pii_in_string,
  )
  ```
  But the canonical location is `_pii.py`. Tests should import from the canonical module.

**After State**:

Replace all 5 occurrences of:
```python
        from autom8_asana.clients.data.client import _mask_pii_in_string
```
With:
```python
        from autom8_asana.clients.data._pii import mask_pii_in_string as _mask_pii_in_string
```

**Invariants**:
- Same function is called (it is literally the same object)
- All 5 tests in `TestMaskPiiInString` pass identically

**Verification**:
1. Run: `pytest tests/unit/clients/data/test_pii.py -x -v`
2. Confirm all tests pass

**Risk**: NONE. Import path change only; same underlying function.

---

### RF-DST-013: Verify `GidLookupIndex.deserialize()` exists

**ID**: RS-M05

**Verification Result**: `GidLookupIndex.deserialize()` exists at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/gid_lookup.py`, lines 176-236. It is a `@classmethod` that accepts `data: dict[str, Any]` and returns `GidLookupIndex`. It validates version, created_at, entry_count, and lookup keys.

**Action**: NONE REQUIRED. The method exists and is correctly implemented. This item is closed by verification.

---

### RF-DST-014: Narrow bare excepts in `batch.py` and `gid_push.py`

**ID**: RS-M08

**Before State**:

**Site 1**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/batch.py`, line 187:
```python
    except (ValueError, Exception) as e:
```
`Exception` subsumes `ValueError`, making the tuple redundant. The intent is to catch JSON parse errors from `response.json()`. The actual exceptions thrown by httpx `response.json()` are `json.JSONDecodeError` (subclass of `ValueError`) and potentially `UnicodeDecodeError`. Using `(json.JSONDecodeError, ValueError)` is more precise but functionally equivalent. However, since this is a boundary catch (parse failure in external response), narrowing to `ValueError` alone is sufficient because `json.JSONDecodeError` is a `ValueError` subclass.

**Site 2**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/gid_push.py`, line 211:
```python
            except (ValueError, Exception):
```
Same pattern. `response.json()` from httpx.

**After State**:

In `batch.py`, replace line 187:
```python
    except ValueError as e:
```

In `gid_push.py`, replace line 211:
```python
            except ValueError:
```

**Invariants**:
- Same behavior for the expected failure mode (`json.JSONDecodeError`, which is `ValueError`)
- The removed `Exception` catch was redundant -- `ValueError` is already an `Exception` subclass
- NOTE: This narrows the catch. If `response.json()` were to throw something other than `ValueError` (e.g., `UnicodeDecodeError`), it would now propagate. In `batch.py`, this would surface as an unhandled error in the batch request. In `gid_push.py`, it would be caught by the outer `except Exception` at line 247-257. Both are acceptable because `UnicodeDecodeError` from `response.json()` indicates a fundamentally broken response that should not be silently swallowed.

**Verification**:
1. Run: `pytest tests/unit/clients/data/ -x` (covers batch.py)
2. Run: `pytest tests/ -k "gid_push" -x`

**Risk**: LOW. The narrowing is correct and the outer catch in `gid_push.py` provides a safety net. In `batch.py`, the caller's error handling in `client.py` catches exceptions at the chunk level.

---

### RF-DST-015: Remove commented-out future metric imports

**ID**: RS-M14

**Before State**:
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/metrics/definitions/__init__.py`, lines 13-15:
  ```python
  # Future definition modules:
  # from autom8_asana.metrics.definitions import unit  # noqa: F401
  # from autom8_asana.metrics.definitions import business  # noqa: F401
  ```

**After State**:

Delete lines 13-15 entirely. The file becomes:

```python
"""Auto-import all metric definition modules.

When this package is imported (by MetricRegistry._ensure_initialized),
all submodules are imported, triggering their module-level registration
with the MetricRegistry singleton.

To add new metrics: create a new .py file in this directory that
instantiates Metric objects and calls MetricRegistry().register().
"""

from autom8_asana.metrics.definitions import offer  # noqa: F401
```

**Invariants**: Zero behavioral change. Commented-out code removal.

**Verification**: `pytest tests/ -k "metrics" -x`

**Risk**: NONE.

---

### RF-DST-016: Strip "Per Story X.Y" inline citations from `clients/data/` modules

**ID**: RS-M15

**Before State**:
- 25 occurrences of `Per Story X.Y:` across 6 files in `src/autom8_asana/clients/data/`:
  - `client.py`: 12 occurrences
  - `_endpoints/insights.py`: 4 occurrences
  - `_cache.py`: 3 occurrences
  - `_response.py`: 3 occurrences
  - `_pii.py`: 2 occurrences
  - `_metrics.py`: 1 occurrence

**After State**:
Replace each `Per Story X.Y: ` prefix with nothing, preserving the rest of the sentence. Examples:

```
Per Story 1.9: Redact phone numbers in logs.
```
becomes:
```
Redact phone numbers in logs.
```

```
Per Story 1.8: Cache successful responses and fall back to stale cache
```
becomes:
```
Cache successful responses and fall back to stale cache
```

```
Per Story 2.6: Returns self for use in sync with block.
```
becomes:
```
Returns self for use in sync with block.
```

**Rule**: Delete the `Per Story X.Y: ` prefix (including the trailing space). If the result starts mid-sentence, capitalize the first letter. If the `Per Story` reference is in a standalone comment line with no other content, delete the entire line. If the `Per Story` reference is in a docstring alongside other text, remove only the prefix.

**Invariants**: Zero behavioral change. Documentation cleanup only.

**Verification**:
1. `grep -rn "Per Story" src/autom8_asana/clients/data/` should return zero matches after cleanup
2. Run: `pytest tests/unit/clients/data/ -x`

**Risk**: NONE. Documentation only. The Janitor must review each occurrence individually to ensure the remaining text is grammatically correct after prefix removal.

---

## Commit Grouping

### Commit 1: Security fixes (RS-M01, RS-M02)

```
fix(core,services): prevent regex injection and mask PII in gid_push logs
```

Files:
- `src/autom8_asana/core/creation.py` (lambda replacement)
- `src/autom8_asana/services/gid_push.py` (mask_pii_in_string import + 3 call sites)
- `tests/` (new regression test for backslash business name)

Gate: `pytest tests/ -k "creation or gid_push" -x`

### Commit 2: Stale imports and dead code (RS-A02, RS-A03, RS-A01)

```
fix(clients,core,automation): fix stale TYPE_CHECKING imports and remove dead code
```

Files:
- `src/autom8_asana/core/creation.py` (TYPE_CHECKING import fix)
- `src/autom8_asana/automation/templates.py` (TYPE_CHECKING import fix)
- `src/autom8_asana/clients/data/client.py` (remove `_parse_content_disposition_filename` + `import re`)
- `src/autom8_asana/clients/data/__init__.py` (add 3 re-exports)

Gate: `pytest tests/unit/clients/data/ -x && pytest tests/ -k "creation or template" -x`

### Commit 3: Comment/docstring cleanup (RS-A04, RS-A05, RS-A06, RS-M14)

```
style: strip spike tags, hotfix prefixes, and migration notes from comments
```

Files:
- `src/autom8_asana/services/gid_push.py` (docstring)
- `src/autom8_asana/lambda_handlers/cache_warmer.py` (3 comment sites)
- `src/autom8_asana/cache/models/freshness.py` (docstring)
- `src/autom8_asana/metrics/definitions/__init__.py` (remove commented imports)

Gate: `pytest tests/ -k "gid_push or cache_warmer or freshness or metrics" -x`

### Commit 4: Dead stub removal and test import fix (RS-M03, RS-M04)

```
fix(dataframes,tests): remove dead create_dataframe_builder stub, fix test imports
```

Files:
- `src/autom8_asana/dataframes/builders/__init__.py` (remove function, TYPE_CHECKING, __all__ entry, docstring line)
- `tests/unit/clients/data/test_pii.py` (update 5 import paths)

Gate: `pytest tests/unit/clients/data/test_pii.py -x && pytest tests/ -k "dataframe" -x`

### Commit 5: Narrow bare excepts (RS-M08)

```
fix(clients,services): narrow overly broad exception catches in JSON parsing
```

Files:
- `src/autom8_asana/clients/data/_endpoints/batch.py` (line 187)
- `src/autom8_asana/services/gid_push.py` (line 211)

Gate: `pytest tests/unit/clients/data/ -x && pytest tests/ -k "gid_push" -x`

### Commit 6: Story citation cleanup (RS-M15)

```
style(clients/data): strip Per Story X.Y inline citations from docstrings
```

Files:
- `src/autom8_asana/clients/data/client.py`
- `src/autom8_asana/clients/data/_endpoints/insights.py`
- `src/autom8_asana/clients/data/_cache.py`
- `src/autom8_asana/clients/data/_response.py`
- `src/autom8_asana/clients/data/_pii.py`
- `src/autom8_asana/clients/data/_metrics.py`

Gate: `pytest tests/unit/clients/data/ -x`

### Commit 7: Debt ledger update (RS-A07)

```
docs(debt): close D-014 in ledger (class already removed)
```

Files:
- `docs/debt/LEDGER-cleanup-modernization.md`

Gate: None (documentation only).

---

## Deferred Items

| ID | Reason | Trigger |
|----|--------|---------|
| RS-A08 | Protocol parameter removal is a public API change | Next Protocol revision for feature work |
| RS-M05 | Verification confirmed method exists; no action needed | N/A (closed) |

---

## Full Commit Sequence

```
Commit 1: RF-DST-001 + RF-DST-002 (security)
  Gate: pytest tests/ -k "creation or gid_push" -x

Commit 2: RF-DST-003 + RF-DST-004 + RF-DST-005 (imports/dead code)
  Gate: pytest tests/unit/clients/data/ -x && pytest tests/ -k "creation or template" -x

Commit 3: RF-DST-006 + RF-DST-007 + RF-DST-008 + RF-DST-015 (comments)
  Gate: pytest tests/ -k "gid_push or cache_warmer or freshness or metrics" -x

Commit 4: RF-DST-011 + RF-DST-012 (dead stub + test imports)
  Gate: pytest tests/unit/clients/data/test_pii.py -x && pytest tests/ -k "dataframe" -x

Commit 5: RF-DST-014 (narrow excepts)
  Gate: pytest tests/unit/clients/data/ -x && pytest tests/ -k "gid_push" -x

Commit 6: RF-DST-016 (story citations)
  Gate: pytest tests/unit/clients/data/ -x

Commit 7: RF-DST-009 (ledger update)
  Gate: None

Final Gate:
  pytest tests/ -x --timeout=300
  Expected: 10,552+ passed, 46 skipped, 2 xfailed
```

### Dependency Graph

```
Commit 1 (security) -- BLOCKING, must be first
  |
  v
Commit 2 (imports/dead code) -- independent of 1 but sequenced for merge hygiene
  |
  v
Commit 3 (comments) -- touches gid_push.py (also touched in 1 and 5), so must follow 1
  |
  v
Commit 4 (dead stub + test imports) -- independent
  |
  v
Commit 5 (narrow excepts) -- touches gid_push.py and batch.py (also in 1,3), so must follow 3
  |
  v
Commit 6 (story citations) -- touches client.py (also in 2), so must follow 2
  |
  v
Commit 7 (ledger) -- independent, last for cleanliness
```

---

## Risk Matrix

| Commit | Items | Blast Radius | Failure Detection | Rollback Cost | Risk |
|--------|-------|-------------|-------------------|---------------|------|
| 1 | RS-M01, RS-M02 | `creation.py`, `gid_push.py` | Existing + new regression test | Single commit revert | MEDIUM |
| 2 | RS-A01, RS-A02, RS-A03 | `__init__.py`, `creation.py`, `templates.py`, `client.py` | Import tests, existing suite | Single commit revert | LOW |
| 3 | RS-A04, RS-A05, RS-A06, RS-M14 | 4 files, comments only | Grep for removed strings | Single commit revert | NONE |
| 4 | RS-M03, RS-M04 | `builders/__init__.py`, `test_pii.py` | Import tests, existing suite | Single commit revert | LOW |
| 5 | RS-M08 | `batch.py`, `gid_push.py` | Existing exception handling tests | Single commit revert | LOW |
| 6 | RS-M15 | 6 files in `clients/data/`, comments only | Grep for "Per Story" | Single commit revert | NONE |
| 7 | RS-A07 | Documentation only | Visual inspection | Single commit revert | NONE |

---

## Janitor Notes

### Commit Convention

```
fix(<scope>): <description>    -- for behavioral changes (commits 1, 2, 4, 5)
style(<scope>): <description>  -- for comment/docstring-only changes (commits 3, 6)
docs(<scope>): <description>   -- for documentation-only changes (commit 7)
```

### Critical Ordering

Commit 1 (security) MUST be first. The regex injection is a correctness issue that should land before any other changes to `creation.py`. The PII fix in `gid_push.py` is also security-relevant.

### File Collision Awareness

`gid_push.py` is modified in commits 1, 3, and 5. The Janitor must apply changes in order. If cherry-picking, resolve conflicts manually.

`client.py` is modified in commits 2 and 6. Same applies.

### Test for RS-M01

The Janitor must create a test file or add a test case. Suggested location: add to existing `creation.py` tests, or create `tests/unit/core/test_creation.py` if it does not exist. The test must use a business name containing `r"\1"` to verify the lambda pattern works.

### RS-M15 Execution Strategy

For the 25 "Per Story X.Y" occurrences: use `replace_all` where the pattern is identical, but manually review each file because the surrounding text varies. Do not use a blind regex replace -- some occurrences are at the start of a docstring line, others are mid-sentence.

---

## Completion Checklist

- [x] Every smell classified (14 addressed, 1 deferred with reason, 1 closed by verification)
- [x] Each refactoring has before/after contract documented
- [x] Invariants and verification criteria specified per item
- [x] Refactorings sequenced with explicit dependencies
- [x] Rollback points identified (every commit is independently revertible)
- [x] Risk assessment complete for each commit
- [x] All file paths and line numbers verified against actual source via Read tool

---

## Attestation

| Artifact | Verified | Method |
|----------|----------|--------|
| `creation.py` lines 82-96 (regex sub) | Yes | Read tool, confirmed exact code |
| `gid_push.py` lines 232, 242, 254 (PII) | Yes | Read tool, confirmed `str(e)` and `response.text[:500]` |
| `gid_push.py` line 211 (bare except) | Yes | Read tool, confirmed `(ValueError, Exception)` |
| `batch.py` line 187 (bare except) | Yes | Read tool, confirmed `(ValueError, Exception)` |
| `creation.py` line 21 TYPE_CHECKING | Yes | Read tool, confirmed `from autom8_asana.models.core import Task` |
| `templates.py` line 17 TYPE_CHECKING | Yes | Read tool, confirmed `from autom8_asana.models.core import Section, Task` |
| `models/core.py` does not exist | Yes | Glob tool returned no files |
| `models/task.py:27` has `class Task` | Yes | Grep tool confirmed |
| `models/section.py:24` has `class Section` | Yes | Grep tool confirmed |
| `client.py` lines 1250-1261 dead function | Yes | Read tool + grep confirmed zero callers in client.py |
| `client.py` `import re` only usage line 1260 | Yes | Grep for `re\.` in client.py confirmed single match |
| `_endpoints/export.py` has its own copy | Yes | Grep confirmed at line 27 + used at line 148 |
| `__init__.py` missing re-exports | Yes | Read tool confirmed only 4 model re-exports |
| `create_dataframe_builder` zero callers | Yes | Grep across src/ and tests/ confirmed |
| `PipelineAutoCompletionService` zero matches in src/ | Yes | Grep confirmed |
| `expected_type=` zero callers | Yes | Grep confirmed |
| `GidLookupIndex.deserialize()` exists | Yes | Read tool, lines 176-236 |
| `mask_pii_in_string` in `_pii.py` no circular import | Yes | Read tool confirmed `_pii.py` imports only `re` |
| `Per Story X.Y` count: 25 across 6 files | Yes | Grep with count mode confirmed |
| `cache_warmer.py` SPIKE tag at line 243, 711-712 | Yes | Read tool confirmed |
| `cache_warmer.py` HOTFIX at lines 56-60, 829, 902 | Yes | Read tool confirmed |
| `freshness.py` migration note docstring | Yes | Read tool, lines 1-7 confirmed |
| `metrics/definitions/__init__.py` commented imports | Yes | Read tool, lines 13-15 confirmed |
| `test_pii.py` import path lines 134,143,153,163,171 | Yes | Read tool confirmed `from autom8_asana.clients.data.client import _mask_pii_in_string` |
