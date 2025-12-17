# Migration Guide: @async_method Decorator

Per TDD-DESIGN-PATTERNS-D: Guide for migrating client methods to use the `@async_method` decorator.

---

## Overview

The `@async_method` decorator generates async/sync method pairs from a single async implementation, reducing code duplication by ~40%.

### Before and After Comparison

**Before (manual pattern - ~71 lines per method with raw):**
```python
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
async def get_async(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

@error_handler
async def get_async(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    """Get a section by GID."""
    data = await self._http.get(f"/sections/{gid}")
    if raw:
        return data
    return Section.model_validate(data)

@overload
def get(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
def get(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

def get(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    """Get a section by GID (sync)."""
    return self._get_sync(gid, raw=raw)

@sync_wrapper("get_async")
async def _get_sync(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    """Internal sync wrapper."""
    if raw:
        return await self.get_async(gid, raw=True)
    return await self.get_async(gid, raw=False)
```

**After (with @async_method - ~25 lines):**
```python
# Type overloads (required for IDE support)
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
async def get_async(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

@overload
def get(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
def get(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

# Single implementation generates both variants
@async_method
@error_handler
async def get(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    """Get a section by GID."""
    data = await self._http.get(f"/sections/{gid}")
    if raw:
        return data
    return Section.model_validate(data)
```

---

## Migration Steps

### Step 1: Add Import

Add the `async_method` import:

```python
from autom8_asana.patterns import async_method
```

Remove the old `sync_wrapper` import if no longer needed:

```python
# REMOVE: from autom8_asana.transport.sync import sync_wrapper
```

### Step 2: Consolidate Overloads

For methods with a `raw` parameter, keep **4 overloads** (2 for async, 2 for sync):

```python
# Async overloads
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ...) -> Model: ...

@overload
async def get_async(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

# Sync overloads
@overload
def get(self, gid: str, *, raw: Literal[False] = ...) -> Model: ...

@overload
def get(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...
```

### Step 3: Add @async_method Decorator

Replace the async implementation and remove the sync wrapper:

```python
@async_method
@error_handler  # If using error_handler, it goes AFTER @async_method
async def get(self, gid: str, *, raw: bool = False) -> Model | dict[str, Any]:
    """Get a resource by GID."""
    data = await self._http.get(f"/resource/{gid}")
    if raw:
        return data
    return Model.model_validate(data)
```

**Important**: Use the base name (e.g., `get`), not `get_async`. The decorator generates:
- `get_async()` - async variant
- `get()` - sync wrapper

### Step 4: Remove Old Code

Delete the following for each migrated method:
- The old `get_async()` implementation (replaced by @async_method on `get`)
- The `get()` sync wrapper method
- The `_get_sync()` internal helper

### Step 5: Verify

Run tests to ensure behavior is preserved:

```bash
pytest tests/ -k "your_client_name" -v
```

---

## Methods Without Raw Parameter

For methods without a `raw` parameter (like `delete`), no overloads are needed:

**Before:**
```python
@error_handler
async def delete_async(self, gid: str) -> None:
    """Delete a resource."""
    await self._http.delete(f"/resource/{gid}")

@sync_wrapper("delete_async")
async def _delete_sync(self, gid: str) -> None:
    """Internal sync wrapper."""
    await self.delete_async(gid)

def delete(self, gid: str) -> None:
    """Delete a resource (sync)."""
    self._delete_sync(gid)
```

**After:**
```python
@async_method
@error_handler
async def delete(self, gid: str) -> None:
    """Delete a resource."""
    await self._http.delete(f"/resource/{gid}")
```

---

## Decorator Order

When stacking decorators, `@async_method` must be **outermost** (first):

```python
@async_method      # 1. Must be first
@error_handler     # 2. Other decorators after
async def get(self, gid: str) -> Model:
    ...
```

---

## PageIterator Methods

**Do NOT use @async_method for PageIterator methods**. These return iterators, not awaitables:

```python
# Keep as-is - returns PageIterator, not a coroutine result
def list_for_project_async(self, project_gid: str) -> PageIterator[Section]:
    """List sections with pagination."""
    ...
```

---

## Clients to Migrate

| Client | Priority | Est. Savings |
|--------|----------|--------------|
| SectionsClient | DONE | 234 lines |
| TagsClient | P1 | ~200 lines |
| ProjectsClient | P1 | ~250 lines |
| TasksClient | P2 | ~350 lines |
| UsersClient | P2 | ~150 lines |
| TeamsClient | P2 | ~150 lines |
| AttachmentsClient | P3 | ~150 lines |
| GoalsClient | P3 | ~200 lines |
| PortfoliosClient | P3 | ~200 lines |
| StoriesClient | P3 | ~150 lines |
| WebhooksClient | P3 | ~150 lines |
| WorkspacesClient | P3 | ~100 lines |
| CustomFieldsClient | P3 | ~200 lines |

**Total estimated savings: ~2,000+ lines**

---

## Common Mistakes

### 1. Wrong Decorator Order

```python
# WRONG - @async_method must be first
@error_handler
@async_method
async def get(self, gid: str) -> Model:
    ...

# CORRECT
@async_method
@error_handler
async def get(self, gid: str) -> Model:
    ...
```

### 2. Using Async Name

```python
# WRONG - use base name, not async name
@async_method
async def get_async(self, gid: str) -> Model:
    ...

# CORRECT - decorator adds _async suffix
@async_method
async def get(self, gid: str) -> Model:
    ...
```

### 3. Missing Overloads for Raw Parameter

If a method has `raw: bool`, you MUST include 4 overloads for type safety:

```python
# Required for mypy/IDE support
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ...) -> Model: ...

@overload
async def get_async(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

@overload
def get(self, gid: str, *, raw: Literal[False] = ...) -> Model: ...

@overload
def get(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...
```

---

## References

- PRD-DESIGN-PATTERNS-D: Requirements
- TDD-DESIGN-PATTERNS-D: Technical design
- SectionsClient: Reference implementation
