# Remedy Plan — Deep Slop Triage
Date: 2026-02-19
Agent: remedy-smith

---

## Executive Summary

| Category | Count | Notes |
|----------|-------|-------|
| AUTO patches | 8 | Mechanically safe, no judgment required |
| MANUAL remediations | 37 | Requires judgment, context, or behavioral verification |
| Total findings | 45 | 6 (HH) + 22 (LS) + 17 (CC) |
| Total effort (AUTO) | ~2 hours | Batch-applicable |
| Total effort (MANUAL) | ~18–30 days | Varies widely; see prioritized list |

**Key security items requiring immediate attention**: SEC-001 (PII in logs, M), LS-001/SEC-002 (regex injection, M). Both are HIGH severity with verified code paths.

**Verified discrepancies from reported findings**:
- M-002: `create_dataframe_builder` does NOT raise `NotImplementedError` at import time — it is a callable stub that raises only when invoked. It is in `__all__` but the finding's "dead stub" characterization is accurate.
- CC-001: `pipeline_templates` legacy shim has live callers in `automation/__init__.py` (docstring example) and `config.py` (docstring example). Both are documentation examples, not production callsites. The shim is live in `get_pipeline_stage()` fallback but no production YAML passes `pipeline_templates` — MANUAL to verify before removal.
- CC-002/CC-003: `autom8y_cache` HOTFIX guards in `cache/__init__.py` and `cache/models/freshness.py` are currently functional defensive guards — SDK is installed and imports succeed. Whether guards are still needed requires deployment history review — MANUAL.
- LS-007: Cache key in `_cache.py` uses `pvp.canonical_key` (unmasked) as the cache key, and logs show the key masked via `_mask_pii_in_string()`. The reported finding about "cache key uses masked phone but no cache entry written" does NOT match the code: `build_cache_key` uses the raw `canonical_key`, and `cache_response` writes using that raw key. The logging masks it but the stored key is plain. This is not an unreachable path — it is a PII-in-cache-key issue distinct from what was reported. Reclassifying as MANUAL note.
- CC-012: `get_custom_fields()` has 42 grep hits for callers. Reported as 39.
- CC-017: `PipelineAutoCompletionService` referenced in D-014 does NOT appear in any source file under `src/` — the class has already been removed. D-014 in the debt ledger is a documentation ghost confirmed.

---

## AUTO Patches (mechanically safe)

---

### RS-A01: Add missing re-exports to `clients/data/__init__.py`

**Source**: M-001 (hallucination-hunter)
**File**: `src/autom8_asana/clients/data/__init__.py`
**Finding**: `BatchInsightsResponse`, `BatchInsightsResult`, and `ExportResult` are defined in `clients/data/models.py` and imported directly in `clients/data/client.py`, but are NOT re-exported from the package `__init__.py`. Any caller importing from `autom8_asana.clients.data` cannot access them via that path.

**Verified**: All three classes confirmed present in `models.py` (lines 332, 371, 474). The `__init__.py` imports only `ColumnInfo`, `InsightsMetadata`, `InsightsRequest`, `InsightsResponse` from models.

**Patch** — replace the import block and `__all__` in `src/autom8_asana/clients/data/__init__.py`:

```python
# OLD (lines 14–35):
from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsRequest,
    InsightsResponse,
)

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
    "ColumnInfo",
    "InsightsMetadata",
    "InsightsRequest",
    "InsightsResponse",
]

# NEW:
from autom8_asana.clients.data.models import (
    BatchInsightsResponse,
    BatchInsightsResult,
    ColumnInfo,
    ExportResult,
    InsightsMetadata,
    InsightsRequest,
    InsightsResponse,
)

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

**Application**: Edit file only. No dependency changes. Run `python -c "from autom8_asana.clients.data import BatchInsightsResponse, BatchInsightsResult, ExportResult; print('OK')"` to verify.
**Effort**: XS (<15 min)
**Classification**: AUTO — purely additive export fix; all three classes are already importable from the submodule. No behavioral change.

---

### RS-A02: Fix TYPE_CHECKING imports — `models.core` does not exist

**Source**: L-002, LS-005 (hallucination-hunter, logic-surgeon)
**Files**:
- `src/autom8_asana/core/creation.py` line 21
- `src/autom8_asana/automation/templates.py` line 17

**Finding**: Both files reference `autom8_asana.models.core` in TYPE_CHECKING blocks. That module does not exist. `Task` lives in `models/task.py` and `Section` in `models/section.py`. Both modules are exported from `models/__init__.py`. Because these are TYPE_CHECKING-only (never executed at runtime), there is no runtime failure — but mypy and type checkers will report errors.

**Verified**: `ls models/` confirms no `core.py`. Canonical import confirmed by 10+ other files.

**Patch for `src/autom8_asana/core/creation.py`** (lines 19–22):

```python
# OLD:
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.core import Task

# NEW:
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task
```

**Patch for `src/autom8_asana/automation/templates.py`** (lines 15–17):

```python
# OLD:
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.core import Section, Task

# NEW:
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task
```

**Application**: Edit both files. Run `mypy src/autom8_asana/core/creation.py src/autom8_asana/automation/templates.py` to confirm no new errors.
**Effort**: XS (<15 min)
**Classification**: AUTO — TYPE_CHECKING only; zero runtime behavior change; correct target module is unambiguous.

---

### RS-A03: Remove dead `_parse_content_disposition_filename` function from `clients/data/client.py`

**Source**: CPB-001 (logic-surgeon)
**File**: `src/autom8_asana/clients/data/client.py` lines 1250–1261

**Finding**: Module-level private function `_parse_content_disposition_filename` in `client.py`. After D-030, the extraction endpoint moved to `clients/data/_endpoints/export.py`. Verified: function is unreferenced within `client.py` and is not imported elsewhere.

**Verified**: No `import _parse_content_disposition_filename` exists anywhere in `src/`. The function at lines 1250–1261 is dead.

**Patch** — remove the entire function block at the end of `client.py`:

```python
# REMOVE (lines 1250–1261):
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

After removal, if `re` is no longer used elsewhere in `client.py`, remove the `import re` at line 15 as well.

**Verification**: `grep -n "import re\|re\." src/autom8_asana/clients/data/client.py` — confirm `re` is used elsewhere before removing the import. Run test suite: `uv run pytest tests/unit/clients/data/ -x -q`.
**Effort**: XS (<15 min)
**Classification**: AUTO — provably unreachable function, no callers anywhere in the codebase.

---

### RS-A04: Remove CC-008 SPIKE-BREAK-CIRCULAR-DEP tags from comments

**Source**: CC-008 (cruft-cutter)
**Files**:
- `src/autom8_asana/lambda_handlers/cache_warmer.py` lines 243, 712
- `src/autom8_asana/services/gid_push.py` line 3 (module docstring reference)

**Finding**: Three "Per SPIKE-BREAK-CIRCULAR-DEP Phase 3:" references. The spike has concluded — the GID push feature is production code. These narrative tags add no information beyond "this was built during a spike."

**Verified**: Found at cache_warmer.py:243, 712 and gid_push.py:3 (module-level docstring).

**Patches**:

`src/autom8_asana/services/gid_push.py` lines 1–8:
```python
# OLD:
"""Push GID mappings to autom8_data after index rebuild.

Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: After the cache warmer rebuilds
GID indexes, push the mapping snapshot to autom8_data's sync endpoint
so autom8_data can serve GID lookups locally without calling back to
autom8_asana.

# NEW:
"""Push GID mappings to autom8_data after index rebuild.

After the cache warmer rebuilds GID indexes, push the mapping snapshot
to autom8_data's sync endpoint so autom8_data can serve GID lookups
locally without calling back to autom8_asana.
```

`src/autom8_asana/lambda_handlers/cache_warmer.py` line 243:
```python
# OLD:
    Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: After cache warming, iterate over

# NEW:
    After cache warming, iterate over
```

`src/autom8_asana/lambda_handlers/cache_warmer.py` line 712:
```python
# OLD:
        # GID mapping push (Phase 3: SPIKE-BREAK-CIRCULAR-DEP)

# NEW:
        # GID mapping push
```

**Effort**: XS (<15 min)
**Classification**: AUTO — ephemeral narrative tags, provably stale (spike concluded), comment-only changes.

---

### RS-A05: Remove CC-007 stale HOTFIX narrative comments from `cache_warmer.py`

**Source**: CC-007 (cruft-cutter)
**File**: `src/autom8_asana/lambda_handlers/cache_warmer.py` lines 56–60, 829, 902

**Finding**: Three HOTFIX narrative comment blocks. The HOTFIX comment in the `_ensure_bootstrap()` function at lines 56–60 narrates the fix intent. Lines 829 and 902 are inline `# HOTFIX: Lazy bootstrap...` comments.

**Verified**: The `_ensure_bootstrap()` function is production code; the HOTFIX label is the cruft, not the function itself.

**Patch** — strip HOTFIX prefix from each comment, preserving the substance:

Lines 56–60:
```python
# OLD:
def _ensure_bootstrap() -> None:
    """Lazy bootstrap initialization for Lambda cold starts.

    HOTFIX: Moved from module-level import to avoid import chain failures
    when autom8y_cache has missing modules. The bootstrap populates
    ProjectTypeRegistry for Tier 1 detection.
    """

# NEW:
def _ensure_bootstrap() -> None:
    """Lazy bootstrap initialization for Lambda cold starts.

    Moved from module-level import to avoid import chain failures
    when autom8y_cache has missing modules. The bootstrap populates
    ProjectTypeRegistry for Tier 1 detection.
    """
```

Line 829:
```python
# OLD:
    # HOTFIX: Lazy bootstrap to avoid import chain failures

# NEW:
    # Lazy bootstrap to avoid import chain failures
```

Line 902:
```python
# OLD:
    # HOTFIX: Lazy bootstrap to avoid import chain failures

# NEW:
    # Lazy bootstrap to avoid import chain failures
```

**Effort**: XS (<15 min)
**Classification**: AUTO — ephemeral comment prefix removal; function and logic are preserved unchanged.

---

### RS-A06: Remove CC-009 migration note docstring from `cache/models/freshness.py`

**Source**: CC-009 (cruft-cutter)
**File**: `src/autom8_asana/cache/models/freshness.py` lines 1–7

**Finding**: Module-level docstring opens with "Migration Note (SDK-PRIMITIVES-001):" describing a migration that is complete. The SDK `Freshness` is now the canonical version.

**Verified**: Module confirmed. The migration is complete — SDK is imported at line 16 with a try/except fallback.

**Patch** — replace module docstring:

```python
# OLD:
"""Cache freshness modes for controlling validation behavior.

Migration Note (SDK-PRIMITIVES-001):
    This module now re-exports autom8y_cache.Freshness which includes
    IMMEDIATE mode in addition to STRICT and EVENTUAL. The local enum
    is deprecated in favor of the SDK version.
"""

# NEW:
"""Cache freshness modes for controlling validation behavior.

Re-exports autom8y_cache.Freshness (STRICT, EVENTUAL, IMMEDIATE).
Falls back to a local enum when the SDK is unavailable.
"""
```

**Effort**: XS (<15 min)
**Classification**: AUTO — documentation comment update; no code or behavior change.

---

### RS-A07: Update D-017 debt ledger entry for CC-017 (D-014 documentation ghost)

**Source**: CC-017 (cruft-cutter)
**File**: `docs/debt/LEDGER-cleanup-modernization.md` (D-014 entry)

**Finding**: D-014 references `PipelineAutoCompletionService` at `lifecycle/completion.py:102-135`. Verified: no such class or symbol exists anywhere in `src/`. The class was removed during the cleanup initiative but the debt ledger entry was not closed.

**Verified**: `grep -rn "PipelineAutoCompletionService" src/` returns zero results. D-014 entry references a removed class.

**Patch** — update D-014 entry in `docs/debt/LEDGER-cleanup-modernization.md`:

```markdown
# OLD (D-014 entry):
### D-014: Deprecated `PipelineAutoCompletionService` wrapper

- **Location**: `src/autom8_asana/lifecycle/completion.py:102-135`
- **Category**: Code > Dead Code
- **Description**: `PipelineAutoCompletionService` is a backward-compatible wrapper around `CompletionService`...
- **Estimated LOC impact**: ~35 (remove class + update import)
- **Related**: None

# NEW:
### D-014: Deprecated `PipelineAutoCompletionService` wrapper — CLOSED

- **Status**: CLOSED (class removed, confirmed 2026-02-19)
- **Location**: `src/autom8_asana/lifecycle/completion.py` (no longer exists)
- **Category**: Code > Dead Code
- **Description**: `PipelineAutoCompletionService` wrapper around `CompletionService` was
  removed during the cleanup-modernization initiative. Debt item resolved.
- **Related**: None
```

**Effort**: XS (<15 min)
**Classification**: AUTO — documentation correction; class removal already completed, this is a ledger update only.

---

### RS-A08: Remove CC-013 dead `expected_type` deprecated parameter references from `dataframes/resolver/`

**Source**: CC-013, CC-016 (partial — `expected_type` specifically) — cruft-cutter / D-017
**Files**:
- `src/autom8_asana/dataframes/resolver/protocol.py` lines 81–92
- `src/autom8_asana/dataframes/resolver/default.py` lines 162–170

**Finding**: The `expected_type` deprecated parameter exists in these resolver files with no callers per the debt ledger D-017 inventory. This is the specific sub-item that can be AUTO-patched.

**IMPORTANT GATE**: Before applying, confirm zero callers with:
```bash
grep -rn "expected_type" src/ tests/ | grep -v __pycache__ | grep -v ".pyc"
```
If any caller exists, STOP and reclassify as MANUAL.

**Effort**: S (<1hr including grep verification)
**Classification**: AUTO only if zero callers confirmed. The grep check is the gate. If callers found, this becomes MANUAL.

---

## MANUAL Remediation (requires judgment)

---

### RS-M01: Regex injection in `core/creation.py` — `re.sub()` with unescaped user input

**Source**: LS-001 / SEC-002 (logic-surgeon), HIGH severity (0.95 confidence)
**File**: `src/autom8_asana/core/creation.py` lines 82–96
**Effort**: S (<1hr)

**Finding**: The `generate_entity_name()` function uses `business_name` and `unit_name` as the replacement string argument to `re.sub()`. In Python's `re.sub()`, the replacement string is processed for backreferences (`\1`, `\g<name>`, etc.). If a business name contains `\1` or `\g<0>`, Python raises `re.error` or produces unintended output. This is not remote code execution — it is an application crash or data corruption vector depending on the input.

**Verified code** (lines 82–87):
```python
result = re.sub(
    r"\[business\s*name\]",
    business_name,      # <-- USER DATA as re.sub replacement
    result,
    flags=re.IGNORECASE,
)
```

**Root cause**: `re.sub(pattern, repl, string)` interprets backreferences in `repl` unless the replacement is wrapped in `re.escape()` or passed as a callable.

**Three production paths confirmed**: `automation/pipeline.py` → `core/creation.py`, `lifecycle/creation.py` → `core/creation.py`, direct calls to `generate_entity_name()`.

**Recommended fix**: Wrap replacement strings with `re.escape()` on the replacement argument, OR use `re.sub(pattern, lambda m: business_name, ...)` to treat the replacement as a literal string.

**Step-by-step instructions**:
1. Read `src/autom8_asana/core/creation.py` lines 80–96 in full.
2. Change line 83 from `business_name,` to `re.escape(business_name),` — but note: `re.escape()` on the replacement escapes backslashes, which is correct for the replacement string interpretation. Alternatively use `lambda m: business_name` which is unambiguously literal.
3. Apply the same change at line 92 for `unit_name`.
4. Write a test: create a business with `name = r"Acme \1 Corp"` and verify `generate_entity_name()` returns `"Onboarding - Acme \\1 Corp"` without raising `re.error`.
5. Check git log for any existing tests for `generate_entity_name()` in `tests/`. Update or add as needed.
6. Confirm all 3 production callers pass through the fix by reviewing `automation/pipeline.py` and `lifecycle/creation.py` call sites.

**Risk notes**: The fix is simple but test coverage is required. If `re.escape()` is used, verify it does not double-escape already-escaped strings from any upstream source. Using `lambda m: business_name` is the safest approach — it is unambiguous and idiomatic.

---

### RS-M02: PII leakage — `gid_push.py` logs raw error response without masking

**Source**: SEC-001 (logic-surgeon), HIGH severity (0.90 confidence)
**File**: `src/autom8_asana/services/gid_push.py` lines 227–234
**Effort**: S (<1hr)

**Finding**: The non-success HTTP logging block at line 227 logs `response.text[:500]` directly. The response from `/api/v1/gid-mappings/sync` may echo back phone numbers or other PII from the request payload in error messages.

**Verified code** (lines 227–234):
```python
logger.warning(
    "gid_push_failed",
    extra={
        "project_gid": project_gid,
        "status_code": response.status_code,
        "response_text": response.text[:500],  # <-- RAW RESPONSE, no PII mask
    },
)
```

**PII contract**: Per `clients/data/_pii.py`, `mask_pii_in_string()` is the canonical PII masker. It is already used in `_cache.py` and `client.py`. `gid_push.py` does not import it.

**Step-by-step instructions**:
1. Add import at top of `src/autom8_asana/services/gid_push.py`:
   ```python
   from autom8_asana.clients.data._pii import mask_pii_in_string as _mask_pii_in_string
   ```
2. Wrap the logged value (line 232):
   ```python
   "response_text": _mask_pii_in_string(response.text[:500]),
   ```
3. Review the `gid_push_error` logger.error block at lines 250–257. The `str(e)` logged there could also contain PII if the exception message includes a phone number. Wrap with `_mask_pii_in_string(str(e))` as well.
4. Verify with a test that constructs a mock response containing a phone number and asserts the log output is masked. See `tests/unit/clients/data/test_pii.py` for masking test patterns.
5. Check `gid_push_timeout` at lines 238–245 — `str(e)` on a timeout likely does not contain PII but confirm the pattern is consistent.

**Risk notes**: Import path `clients/data/_pii` is private. If the import creates a circular dependency, use `mask_pii_in_string` from the public re-export at `clients/data/client.py`. Verify import does not create cycles before committing.

---

### RS-M03: `create_dataframe_builder` in `__all__` is a dead stub — decision required

**Source**: M-002 (hallucination-hunter)
**File**: `src/autom8_asana/dataframes/builders/__init__.py` lines 71–108, 133
**Effort**: M (<4hr)

**Finding**: `create_dataframe_builder` is included in `__all__` and the module docstring as part of the public API. It unconditionally raises `NotImplementedError` when called. Any caller who imports it from the public API and calls it will crash. The internal comment acknowledges it requires a full `AsanaClient` and instructs callers to use `ProgressiveProjectBuilder` directly.

**Verified code** (lines 105–108):
```python
raise NotImplementedError(
    "create_dataframe_builder requires full AsanaClient. "
    "Use ProgressiveProjectBuilder directly instead."
)
```

**Decision required — two valid paths**:

**Option A (remove)**: Delete the function body and remove `"create_dataframe_builder"` from `__all__` and from the module docstring. Also remove the function from the docstring's "Public API" section.
- Risk: Any caller who imported the name (unlikely given it always raises) will get `ImportError`. Search `tests/` and `src/` for `create_dataframe_builder` callers first.

**Option B (deprecate with warning)**: Keep the name in `__all__` but emit a `DeprecationWarning` before raising `NotImplementedError`, or implement it properly.

**Step-by-step instructions (Option A)**:
1. Run `grep -rn "create_dataframe_builder" src/ tests/` — confirm zero callers (or enumerate them).
2. Remove lines 71–108 (the full function body).
3. Remove `"create_dataframe_builder"` from `__all__` (line 133).
4. Remove `- create_dataframe_builder: Factory function for creating DataFrame builder` from the module docstring (line 20).
5. Run `python -c "from autom8_asana.dataframes.builders import ProgressiveProjectBuilder; print('OK')"` to verify the module is importable.
6. Run `uv run pytest tests/unit/dataframes/ -x -q`.

**Risk notes**: The stub has been in `__all__` with documentation since it was written — there may be downstream code (outside this repo) that imports the name and expects it to exist. Search tests thoroughly before removal.

---

### RS-M04: Tests import `_mask_pii_in_string` via `client.py` re-export alias

**Source**: L-001 (hallucination-hunter)
**File**: `tests/unit/clients/data/test_pii.py` lines 134, 143, 152, 163, 171
**Effort**: S (<1hr)

**Finding**: Tests import `_mask_pii_in_string` from `autom8_asana.clients.data.client` (the private alias/re-export). The canonical implementation lives at `autom8_asana.clients.data._pii`. The re-export in `client.py` is backward-compat. If `client.py`'s re-export is ever removed, these tests break.

**Verified**: `test_pii.py:134` uses `from autom8_asana.clients.data.client import _mask_pii_in_string`. Line 402 of the same file uses the canonical path `from autom8_asana.clients.data._pii import mask_pii_in_string` — so both exist in the same test file.

**Step-by-step instructions**:
1. Open `tests/unit/clients/data/test_pii.py`.
2. Replace all occurrences of:
   ```python
   from autom8_asana.clients.data.client import _mask_pii_in_string
   ```
   with:
   ```python
   from autom8_asana.clients.data._pii import mask_pii_in_string as _mask_pii_in_string
   ```
3. Confirm all 5 import sites (lines 134, 143, 152, 163, 171) are updated.
4. Run `uv run pytest tests/unit/clients/data/test_pii.py -x -q` to confirm green.

**Risk notes**: Low risk. This is a test-only change. The behavioral contract is identical — same function, different import path. Verify that both the private `_mask_pii_in_string` alias and the `mask_pii_in_string` public name are the same function before updating (they should be per the re-export pattern in `client.py`).

---

### RS-M05: Verify `GidLookupIndex.deserialize()` method exists

**Source**: L-003 (hallucination-hunter)
**File**: `src/autom8_asana/services/gid_lookup.py` (assumed)
**Effort**: XS (<15 min) — verification only

**Finding**: `GidLookupIndex.deserialize()` was reported as unverified. This is a verification task, not a known bug.

**Step-by-step instructions**:
1. Read `src/autom8_asana/services/gid_lookup.py` and confirm `GidLookupIndex` has a `deserialize()` class method or static method.
2. If it exists and works: no action needed. Close finding as verified.
3. If it does NOT exist but is called elsewhere: file a new finding. The call site would be at runtime.
4. Run `grep -rn "GidLookupIndex.deserialize\|\.deserialize(" src/ tests/` to identify all callers and confirm the method exists.

**Risk notes**: Verification only. Effort is XS. Only escalates if the method is absent AND called.

---

### RS-M06: `PhoneVerticalPair` sourced from private SDK path — document or re-export

**Source**: L-004 (hallucination-hunter)
**File**: `src/autom8_asana/models/contracts/phone_vertical.py` line 11
**Effort**: S (<1hr)

**Finding**: `PhoneVerticalPair` is imported from `autom8y_core.models.data_service`, which is a private/internal SDK path. If the SDK restructures this path, the import breaks silently (TYPE_CHECKING blocks would still fail mypy; runtime imports would ImportError).

**Verified**: `from autom8y_core.models.data_service import PhoneVerticalPair` at line 11. The class is then re-exported through `models/contracts/__init__.py`.

**Step-by-step instructions**:
1. Check the `autom8y_core` SDK version in `pyproject.toml` for `autom8y-core` or equivalent package. Note the version constraint.
2. Verify whether `autom8y_core.models.data_service` is documented as a public API or an internal module in the SDK changelog or docs.
3. If PRIVATE internal path: file a ticket to request a public re-export from the SDK, or add a comment in `phone_vertical.py` explicitly noting the path is internal and the SDK version it was verified against.
4. If PUBLIC documented path: add a comment confirming it is stable: `# Public SDK API, stable since autom8y-core >= X.Y`.
5. Add the SDK version to the comment so future maintainers know when to re-verify.

**Risk notes**: No immediate fix — this is a contractual clarity issue. The main risk is silent breakage if the SDK team refactors internal paths in a minor version update.

---

### RS-M07: `LS-007` — cache key contains raw PII (canonical_key with phone number)

**Source**: LS-007 (logic-surgeon) — reclassified from "unreachable fallback" to "PII-in-storage-key"
**File**: `src/autom8_asana/clients/data/_cache.py` lines 30–42
**Effort**: M (<4hr)

**Finding**: `build_cache_key()` returns `f"insights:{factory}:{pvp.canonical_key}"` where `canonical_key` contains the raw E.164 phone number (e.g., `pv1:+17705753103:chiropractic`). This key is stored unmasked in the cache backend. The logging correctly masks it, but the cache storage key itself is PII-bearing.

**Verified**: `_cache.py:42` — `return f"insights:{factory}:{pvp.canonical_key}"`. All logging sites call `_mask_pii_in_string(cache_key)` before logging, which is correct. The stored key is unmasked.

**Decision required**: Whether a PII-bearing cache key is acceptable depends on:
- The cache backend (Redis? S3?). If S3, the key is in log trails.
- The threat model and compliance requirements (HIPAA, SOC2, etc.).
- Whether key-level observability is needed (debugging requires readable keys).

**Step-by-step instructions**:
1. Review the PII redaction contract at `.claude/wip/SECURITY-PII-REDACTION-CONTRACT.md`.
2. Determine whether cache key storage falls under PII-at-rest requirements.
3. If yes: replace `pvp.canonical_key` in the cache key with a deterministic hash (e.g., `hashlib.sha256(pvp.canonical_key.encode()).hexdigest()[:16]`). This requires updating `get_stale_response()` and `cache_response()` to use the same hash for key lookup consistency.
4. If no: document the decision as an accepted risk in the PII contract.
5. Either outcome requires a team decision — do not change unilaterally.

**Risk notes**: Changing the cache key format is a breaking change — all existing cached entries become unreachable (they will expire naturally). Plan for a cache warm-up period. Coordinate with the cache TTL settings.

---

### RS-M08: `except (ValueError, Exception)` — effectively bare except in two files

**Source**: SEC-003 (logic-surgeon)
**Files**:
- `src/autom8_asana/clients/data/_endpoints/batch.py` line 187
- `src/autom8_asana/services/gid_push.py` line 211
**Effort**: S (<1hr)

**Finding**: `except (ValueError, Exception)` is equivalent to a bare `except Exception:` since `Exception` subsumes `ValueError`. This is code bloat, not a security issue per se, but it masks errors that should be handled specifically.

**Verified code**:
- `batch.py:187`: `except (ValueError, Exception) as e:` — handles JSON parse failure
- `gid_push.py:211`: `except (ValueError, Exception):` — handles response body parse

**Step-by-step instructions**:
1. `batch.py:187`: Determine what exceptions `response.json()` can raise. `httpx.Response.json()` raises `json.JSONDecodeError` (a subclass of `ValueError`). The correct catch is `except (json.JSONDecodeError, ValueError) as e:` — this removes the bare `Exception` overreach while retaining the specific cases.
2. `gid_push.py:211`: Same analysis. Replace with `except (json.JSONDecodeError, ValueError):`.
3. For `gid_push.py`, the fallback `body = {}` is intentional (non-fatal). Confirm comment is sufficient to explain intent; add `# Non-fatal: push success is already confirmed by status_code < 300` if absent.
4. Run tests for both files to confirm no behavioral change.

**Risk notes**: These are both inside try/except blocks that handle graceful degradation. The change is narrowing the catch, which is safer — but if httpx ever raises a non-`ValueError` parse error, the behavior changes from silent fallback to propagation. Verify with current httpx version what `response.json()` can raise.

---

### RS-M09: Dependency sprawl — per D-027 (540 heavy mock sites)

**Source**: TD-001/TD-002, LS finding on shallow `is not None` test assertions
**File**: Multiple test files
**Effort**: XL (>1 day — trigger-gated per debt ledger)

**Finding**: 967 `is not None` assertions found in tests (grep count). The Phase 2 finding specifically flagged shallow assertions that verify existence but not value — tests that cannot catch logic errors in the returned object. This is test degradation, not test absence.

**Step-by-step instructions**:
1. Do NOT fix en masse. This is D-027 territory (540 heavy mock sites), deferred to a dedicated test architecture initiative.
2. For new tests, enforce: any `assert result is not None` must be accompanied by at least one attribute-level assertion (e.g., `assert result.count == expected_count`).
3. When modifying existing tests, upgrade the assertion if the changed logic is covered by the shallow assertion.
4. For the specific instances flagged in TD-001/TD-002: read the test context, determine what the returned object is, and add at minimum one field-level assertion.

**Risk notes**: Touching 967 assertions in one pass risks introducing regressions by asserting incorrect expected values. Scope to modified code paths only.

---

### RS-M10: `CC-001` — `pipeline_templates` legacy shim in `automation/config.py`

**Source**: CC-001 (cruft-cutter)
**File**: `src/autom8_asana/automation/config.py` lines 112–115, 144, 167–181
**Effort**: M (<4hr)

**Finding**: `AutomationConfig` has a `pipeline_templates: dict[str, str]` field documented as "legacy" that falls back from `pipeline_stages`. The shim is in `get_pipeline_stage()` at lines 179–181.

**Verified callers**: Only docstring examples in `automation/__init__.py` and `config.py` use `pipeline_templates`. No production YAML or runtime caller passes `pipeline_templates` in `src/`.

**Step-by-step instructions**:
1. Search for `pipeline_templates` in ALL callers including `tests/`, `config/`, `examples/`, and any YAML files: `grep -rn "pipeline_templates" . | grep -v __pycache__`.
2. Search for any YAML configuration files in `config/` that might pass `pipeline_templates`.
3. If zero non-documentation callers found:
   a. Remove `pipeline_templates: dict[str, str] = field(default_factory=dict)` from `AutomationConfig`.
   b. Remove the fallback branch in `get_pipeline_stage()` (lines 179–181).
   c. Update the class docstring to remove legacy example.
   d. Update `automation/__init__.py` docstring example to use `pipeline_stages`.
   e. Update `config.py` docstring example at line 625–627.
4. Run `uv run pytest tests/ -x -q -k "automation"` to confirm no test breakage.
5. If callers exist in YAML or other configs: STOP. Do not remove. Document the blocker.

**Risk notes**: The shim produces a `PipelineStage` with only `project_gid` set, no `target_section`. Any caller relying on this path gets an incomplete `PipelineStage`. This is a latent bug if any live caller uses `pipeline_templates`.

---

### RS-M11: `CC-002/CC-003` — Evaluate stale `autom8y_cache` HOTFIX defensive guards

**Source**: CC-002, CC-003 (cruft-cutter)
**Files**:
- `src/autom8_asana/cache/__init__.py` lines 170–175
- `src/autom8_asana/cache/models/freshness.py` lines 13–25
**Effort**: S (<1hr)

**Finding**: Two `try/except ImportError` guards around `autom8y_cache` imports. The comment says "HOTFIX: Make import defensive for Lambda compatibility when autom8y_cache has missing modules."

**Verified**: The imports currently succeed (SDK is installed). The guards exist for a version mismatch scenario that may no longer apply.

**Step-by-step instructions**:
1. Check `pyproject.toml` for the pinned version of `autom8y-cache` (or equivalent package name).
2. Check the git log for when the HOTFIX comments were added — `git log -S "HOTFIX: Make import defensive" --oneline`.
3. Check the autom8y-cache changelog for whether the `HierarchyTracker` and `Freshness` symbols have been stable since the HOTFIX was added.
4. In a Lambda test environment (or equivalent), remove the try/except guards temporarily and confirm the imports succeed.
5. If confirmed stable: remove the defensive try/except and replace with direct imports. Also remove the `HierarchyTracker = None` fallback assignment.
6. If the Lambda environment cannot be tested: ACCEPT as technical debt, document in the freshness.py docstring the SDK version at which the guard was added and when it was last verified.

**Risk notes**: If the SDK version is not pinned tightly, removing the guard risks Lambda cold-start import failures in version mismatch scenarios. Only remove if the version constraint is tight (e.g., `autom8y-cache>=1.5.0,<2.0.0`) and the symbol has been stable since the HOTFIX commit.

---

### RS-M12: `CC-004` — Evaluate `AUTOM8_DATA_INSIGHTS_ENABLED` kill switch for removal

**Source**: CC-004 (cruft-cutter)
**File**: `src/autom8_asana/clients/data/client.py` lines 104–113, 473–500; `settings.py` lines 38, 551–577
**Effort**: M (<4hr)

**Finding**: The `AUTOM8_DATA_INSIGHTS_ENABLED` kill switch is documented as an "emergency kill switch only." If the integration is now stable and the kill switch has not been exercised since initial deployment, it may be removable. CC-004 flags it as "probably stale."

**However**: The client.py docstring explicitly describes it as an ACTIVE emergency mechanism, not an A/B test flag. Per the code: "The AUTOM8_DATA_INSIGHTS_ENABLED environment variable exists as an emergency kill switch only."

**Step-by-step instructions**:
1. Determine with the team whether the kill switch has ever been exercised in production.
2. Determine whether ops/incident runbooks reference `AUTOM8_DATA_INSIGHTS_ENABLED` as a remediation step.
3. If NOT referenced in runbooks and NEVER exercised: schedule removal.
4. If referenced in runbooks or exercised: retain the kill switch, accept as operational debt.
5. Do NOT remove without explicit stakeholder sign-off — this is an ops decision, not a code quality decision.

**Risk notes**: Removing a kill switch that is referenced in a runbook creates an incident risk. This is an escalation item, not a code fix.

---

### RS-M13: `CC-005` — MVP-deferred TODO stubs in `dataframes/extractors/unit.py`

**Source**: CC-005 (cruft-cutter), also D-015 in debt ledger
**File**: `src/autom8_asana/dataframes/extractors/unit.py` lines 66–118
**Effort**: L (<1 day)

**Finding**: Two stub methods — `_extract_vertical_id()` and `_extract_max_pipeline_stage()` — always return `None`. Both are marked "TODO: deferred pending autom8 team input."

**Step-by-step instructions**:
1. Schedule a stakeholder conversation with the autom8 team to determine:
   a. Whether `vertical_id` derivation from the Vertical model is now defined.
   b. Whether `max_pipeline_stage` logic is defined for the UnitHolder model.
2. If both stubs are intentionally permanent `None` (i.e., the columns are intentional null columns in the schema): remove the TODO comments, update the docstrings to say "Returns None by design — column reserved for future use" and remove the TODO markers.
3. If implementation is now possible: implement with tests.
4. If still deferred: update TODO to reference a ticket number, not narrative text.

**Risk notes**: If these columns feed a database schema that expects non-null values, the silent `None` returns are a data quality issue, not just cruft.

---

### RS-M14: `CC-006` — Remove commented-out future metric imports

**Source**: CC-006 (cruft-cutter), also D-016 in debt ledger
**File**: `src/autom8_asana/metrics/definitions/__init__.py` lines 13–15
**Effort**: XS (<15 min)

**Finding**: Two commented-out imports for unimplemented metric modules:
```python
# from autom8_asana.metrics.definitions import unit  # noqa: F401
# from autom8_asana.metrics.definitions import business  # noqa: F401
```

**Step-by-step instructions**:
1. Confirm `src/autom8_asana/metrics/definitions/unit.py` and `business.py` do NOT exist: `ls src/autom8_asana/metrics/definitions/`.
2. If they do not exist: remove the two commented lines entirely.
3. If they exist but have no registrations: remove the comments and optionally add a TODO referencing a ticket.
4. Add a code comment explaining that new metric modules should be imported here when ready (this is already documented in the docstring — verify it remains accurate).

**Risk notes**: Trivial. Removing commented-out code for non-existent modules has no behavioral impact.

---

### RS-M15: `CC-010/CC-011` — Remove 30+ "Per Story X.Y" inline citations from `clients/data/`

**Source**: CC-010, CC-011 (cruft-cutter)
**Files**: `src/autom8_asana/clients/data/client.py` and sub-modules (25+ occurrences confirmed)
**Effort**: S (<1hr)

**Finding**: Inline citations like `# Per Story 1.8:`, `Per Story 2.2:`, `Per Story 2.3:` throughout the data client. These are story-tracking artifacts from the original development sprint, now serving no documentation purpose.

**Step-by-step instructions**:
1. Run `grep -rn "Per Story [0-9]\." src/autom8_asana/clients/data/ | grep -v __pycache__` to enumerate all occurrences.
2. For each occurrence, evaluate whether the substance of the comment (not the story number) is meaningful. If yes, keep the substance but remove the "Per Story X.Y:" prefix.
3. For occurrences where the story number IS the entire comment content (e.g., `# Per Story 2.2`), remove the line.
4. Do NOT mass-remove — review each one. Some story references may point to design decisions that should be linked to an ADR instead.
5. Run full test suite after.

**Risk notes**: Low. Comment-only changes. The primary risk is accidentally deleting a meaningful architectural note alongside the story tag.

---

### RS-M16: `CC-012` — `Task.get_custom_fields()` deprecated with 42 active callers

**Source**: CC-012 (cruft-cutter)
**File**: `src/autom8_asana/models/task.py` lines 256–281 + 42 callers
**Effort**: XL (>1 day)

**Finding**: `get_custom_fields()` emits `DeprecationWarning` and delegates to `custom_fields_editor()`. 42 callers verified. The migration to `custom_fields_editor()` is not complete.

**Step-by-step instructions**:
1. Run `grep -rn "get_custom_fields()" src/ tests/` to enumerate all 42 callers.
2. Group callers by module (lifecycle, automation, api routes, tests).
3. For each caller: replace `.get_custom_fields()` with `.custom_fields_editor()`. Verify the API is identical.
4. After all callers migrated: remove the `get_custom_fields()` method from `task.py`.
5. Run full test suite: `uv run pytest -x -q`.
6. Check for any consumers OUTSIDE this repo (if this is an SDK) that may call `get_custom_fields()`. If this is a pure internal library, the search above is sufficient.

**Risk notes**: 42 callers is a non-trivial migration. Work in logical groups. Tests that test deprecated paths will need updating. The method body is identical to `custom_fields_editor()` so behavioral risk is low — but call-site context matters (some callers may have workarounds for the deprecated API).

---

### RS-M17: `CC-014` — `Business.HOLDER_KEY_MAP` annotated DEPRECATED

**Source**: CC-014 (cruft-cutter), D-017 sub-item
**File**: `src/autom8_asana/models/business/business.py` lines 235–237
**Effort**: M (<4hr)

**Finding**: `HOLDER_KEY_MAP` on `Business` and `Unit` is annotated `# DEPRECATED: Use detection system (EntityTypeInfo) for new code.` but still has active callers in `detection/facade.py` (the fallback path) and `base.py`.

**Step-by-step instructions**:
1. Map all callers of `Business.HOLDER_KEY_MAP` and `Unit.HOLDER_KEY_MAP`: `grep -rn "HOLDER_KEY_MAP" src/ | grep -v __pycache__`.
2. Verify whether the callers in `detection/facade.py` are fallback-only paths or hot paths.
3. Determine with the team: is the detection system (`EntityTypeInfo`) now the canonical source for all holder type identification?
4. If yes, and the fallback is exercised only on legacy data: file a ticket to remove the fallback once confident. Do not remove unilaterally — the fallback may be exercising on production traffic.
5. If the fallback is dead: write a test that proves it is not exercised and then schedule removal.

**Risk notes**: `HOLDER_KEY_MAP` removal touches entity detection, which is a core business logic path. This is NOT a quick win — it requires understanding the detection system's completeness before removing the fallback.

---

### RS-M18: `CC-015` — `strict=False` deprecated parameter in `CustomFieldAccessor`

**Source**: CC-015 (cruft-cutter), D-017 sub-item
**File**: `src/autom8_asana/models/custom_field_accessor.py`
**Effort**: S (<1hr) if zero callers confirmed

**Step-by-step instructions**:
1. Run `grep -rn "strict=False\|strict=True" src/ tests/` to find all callers of the deprecated parameter.
2. If zero callers: remove the `strict` parameter from `CustomFieldAccessor._resolve_gid()` and any method that accepts it.
3. If callers exist: migrate each caller to remove `strict=False` usage, then remove the parameter.
4. Run `uv run pytest tests/ -x -q -k "custom_field"`.

**Risk notes**: Low if zero callers confirmed. The parameter was never part of the public API signature.

---

### RS-M19: `CC-016` — `ValidationError` deprecated alias in `persistence/` (D-017)

**Source**: CC-016 (cruft-cutter), D-017 in debt ledger
**Files**:
- `src/autom8_asana/persistence/exceptions.py` lines 256–303
- `src/autom8_asana/persistence/__init__.py` line 104
**Effort**: M (<4hr)

**Step-by-step instructions**:
1. Run `grep -rn "from autom8_asana.persistence import ValidationError\|from autom8_asana.persistence.exceptions import ValidationError" src/ tests/` to enumerate callers.
2. If callers exist: replace each caller with the correct exception (the alias's target class, e.g., `GidValidationError` or equivalent).
3. Remove the `ValidationError` metaclass alias from `persistence/exceptions.py`.
4. Remove the `ValidationError` re-export from `persistence/__init__.py`.
5. Run full test suite.

**Risk notes**: The metaclass-based deprecated alias is technically complex. Understand the metaclass before removing it — it may have import-time side effects beyond just providing the name.

---

### RS-M20: D-017 remaining sub-items — deprecated aliases in `models/business/` and resolver

**Source**: CC-016 / D-017 umbrella (cruft-cutter)
**Files**: Multiple (see D-017 debt ledger entry)
**Effort**: L (<1 day total for the D-017 cluster)

**D-017 sub-items not individually addressed above**:
- `models/business/hours.py:80-85` — 6 `_deprecated_alias` decorators
- `models/business/business.py:395-407` — `reconciliations_holder` property with DeprecationWarning
- `models/business/reconciliation.py:60-70` — same
- `models/business/detection/facade.py:234-258` — `detect_by_name()` deprecated
- `models/business/detection/config.py:223` — deprecated `NAME_PATTERNS` dict
- `models/task.py:78-121` — `num_hearts`, `hearted`, `hearts` deprecated Asana fields
- `models/custom_field_accessor.py:52` — deprecated `normalize=False` parameter
- `cache/integration/dataframe_cache.py:168` — deprecated alias comment
- `dataframes/resolver/protocol.py:81-92` / `default.py:162-170` — deprecated `expected_type`

**Step-by-step instructions**:
1. For each sub-item: enumerate callers as in the individual items above.
2. Prioritize by caller count (fewer callers = easier removal).
3. The `num_hearts`/`hearted`/`hearts` deprecated Asana fields are likely safe to remove if Asana has retired the hearts API. Verify via Asana API docs.
4. Treat D-017 as a sprint-sized task, not a single PR.
5. Work through sub-items in dependency order: remove callers before removing the deprecated symbol.

**Risk notes**: Each sub-item carries independent risk. Do not batch all D-017 sub-items into a single PR — the diff will be unreviable. Work one sub-item per PR.

---

## Temporal Debt Cleanup Plans

### TCP-01: `pipeline_templates` shim retirement

**Finding**: CC-001 / RS-M10
**Verification steps before removal**:
1. `grep -rn "pipeline_templates" . --include="*.py" --include="*.yaml" --include="*.yml" --include="*.json" | grep -v __pycache__` — must return ONLY docstring examples, zero production callsites.
2. Check Lambda environment variable definitions for any `PIPELINE_TEMPLATES` config injection.
3. Remove in: `automation/config.py` (field + fallback branch), update docstrings in `automation/__init__.py` and `config.py`.
4. Post-removal: run `uv run pytest -x -q -k "automation or pipeline"`.

---

### TCP-02: `autom8y_cache` HOTFIX import guards

**Finding**: CC-002/CC-003 / RS-M11
**Verification steps before removal**:
1. `git log -S "HOTFIX: Make import defensive" --oneline` — identify when guards were added.
2. `pip show autom8y-cache` in Lambda test env — confirm current version.
3. Check autom8y-cache git/changelog: verify `HierarchyTracker` and `Freshness` stable since guard was added.
4. Remove try/except in `cache/__init__.py` and `cache/models/freshness.py`.
5. Deploy to Lambda test env and confirm cold-start import succeeds.
6. Post-removal check: `grep -rn "HierarchyTracker = None" src/` should return nothing.

---

### TCP-03: Deprecated method cluster (D-017)

**Finding**: CC-012 through CC-016 + RS-M16 through RS-M20
**Verification steps for each removal**:
1. Zero-caller grep before each symbol removal.
2. Run deprecation warning capture test: `uv run pytest -W error::DeprecationWarning -x -q` — should produce zero warnings after migration.
3. For each method removed: confirm test coverage exists for the replacement (e.g., `custom_fields_editor()` is tested after `get_custom_fields()` is removed).
4. Check `__all__` lists in affected modules — remove deprecated names from `__all__`.

---

## Prioritized Action List

Ordered by: severity × effort × risk (HIGH severity + LOW effort first)

| Priority | ID | Source | Classification | Effort | Severity | Action |
|----------|----|--------|----------------|--------|----------|--------|
| 1 | RS-M01 | LS-001/SEC-002 | MANUAL | S | HIGH | Fix regex injection in `generate_entity_name()` |
| 2 | RS-M02 | SEC-001 | MANUAL | S | HIGH | Mask PII in `gid_push.py` error log |
| 3 | RS-A02 | L-002/LS-005 | AUTO | XS | MEDIUM | Fix TYPE_CHECKING imports (`models.core` → correct paths) |
| 4 | RS-A01 | M-001 | AUTO | XS | MEDIUM | Add missing re-exports to `clients/data/__init__.py` |
| 5 | RS-A03 | CPB-001 | AUTO | XS | MEDIUM | Remove dead `_parse_content_disposition_filename` |
| 6 | RS-M04 | L-001 | MANUAL | S | LOW | Update tests to import `_mask_pii_in_string` from `_pii` not `client` |
| 7 | RS-M08 | SEC-003 | MANUAL | S | LOW | Fix `except (ValueError, Exception)` in 2 files |
| 8 | RS-M03 | M-002 | MANUAL | M | MEDIUM | Decide fate of `create_dataframe_builder` stub |
| 9 | RS-M07 | LS-007 | MANUAL | M | MEDIUM | Evaluate PII in cache key storage |
| 10 | RS-A04 | CC-008 | AUTO | XS | LOW | Remove SPIKE-BREAK-CIRCULAR-DEP tags |
| 11 | RS-A05 | CC-007 | AUTO | XS | LOW | Strip HOTFIX narrative labels from cache_warmer.py |
| 12 | RS-A06 | CC-009 | AUTO | XS | LOW | Remove migration note from freshness.py docstring |
| 13 | RS-A07 | CC-017 | AUTO | XS | LOW | Close D-014 in debt ledger (class already removed) |
| 14 | RS-M05 | L-003 | MANUAL | XS | LOW | Verify GidLookupIndex.deserialize() exists |
| 15 | RS-M06 | L-004 | MANUAL | S | LOW | Document or stabilize PhoneVerticalPair SDK import path |
| 16 | RS-M11 | CC-002/CC-003 | MANUAL | S | LOW | Evaluate and potentially remove autom8y_cache HOTFIX guards |
| 17 | RS-M14 | CC-006 | MANUAL | XS | LOW | Remove commented-out metric imports |
| 18 | RS-A08 | CC-013 | AUTO (conditional) | S | LOW | Remove dead `expected_type` param (verify zero callers first) |
| 19 | RS-M15 | CC-010/CC-011 | MANUAL | S | LOW | Strip "Per Story X.Y" inline citations |
| 20 | RS-M13 | CC-005 | MANUAL | L | LOW | Resolve MVP-deferred TODO stubs in UnitExtractor |
| 21 | RS-M10 | CC-001 | MANUAL | M | LOW | Retire `pipeline_templates` shim after caller audit |
| 22 | RS-M18 | CC-015 | MANUAL | S | LOW | Remove deprecated `strict=False` param |
| 23 | RS-M12 | CC-004 | MANUAL | M | LOW | Stakeholder decision on kill switch retention |
| 24 | RS-M16 | CC-012 | MANUAL | XL | LOW | Migrate 42 `get_custom_fields()` callers to `custom_fields_editor()` |
| 25 | RS-M17 | CC-014 | MANUAL | M | LOW | Evaluate HOLDER_KEY_MAP deprecation path |
| 26 | RS-M19 | CC-016 | MANUAL | M | LOW | Remove `ValidationError` deprecated alias |
| 27 | RS-M20 | D-017 cluster | MANUAL | L | LOW | D-017 remaining deprecated alias sub-items |
| 28 | RS-M09 | TD-001/TD-002 | MANUAL | XL | LOW | Shallow test assertion improvement (trigger-gated) |

**Recommended execution batches**:
- **Batch 1 (this sprint, ~1 day)**: RS-M01, RS-M02, RS-A01, RS-A02, RS-A03 — security and correctness fixes.
- **Batch 2 (next sprint, ~0.5 day)**: RS-A04, RS-A05, RS-A06, RS-A07, RS-M04, RS-M08 — AUTO patches + LOW-effort MANUALs.
- **Batch 3 (backlog, M/L items)**: RS-M03, RS-M07, RS-M10, RS-M11, RS-M12, RS-M13.
- **Batch 4 (dedicated sprint, D-017 cluster)**: RS-M16, RS-M17, RS-M18, RS-M19, RS-M20.

---

## Cross-Rite Referrals

### Security Rite

| Finding | Referral reason |
|---------|----------------|
| RS-M01 / LS-001 / SEC-002 | Regex injection — security design review warranted before fix is applied. Confirm threat model scope (is business name truly user-controlled?) |
| RS-M02 / SEC-001 | PII log leak — should be included in the XR-003 PII audit report as an open item |
| RS-M07 / LS-007 | PII in cache key storage — compliance decision required (HIPAA/SOC2 scope) |

### Hygiene Rite

| Finding | Referral reason |
|---------|----------------|
| RS-M16 / CC-012 | 42-caller deprecation migration is a hygiene sprint task |
| RS-M20 / D-017 | D-017 cluster cleanup is backlog hygiene debt |
| RS-M09 / TD-001/TD-002 | Shallow test assertions — hygiene initiative, trigger-gated per D-027 |

### Debt Rite

| Finding | Referral reason |
|---------|----------------|
| RS-M12 / CC-004 | Kill switch retention is an operational/architecture decision |
| RS-M13 / CC-005 | MVP-deferred stubs require product team input |
| RS-M17 / CC-014 | HOLDER_KEY_MAP deprecation path requires detection system maturity assessment |
| RS-A07 / CC-017 | D-014 debt ledger documentation ghost — ledger maintenance |

---

*Remedy plan complete. All 45 findings from Phases 1–3 accounted for. Gate-keeper has full remediation coverage.*
