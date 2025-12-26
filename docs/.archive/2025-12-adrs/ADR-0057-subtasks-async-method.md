# ADR-0057: Add subtasks_async Method to TasksClient

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-SDKDEMO, TDD-0002 (Models Pagination), ADR-0050 (Holder Lazy Loading)

## Context

BUG-3 identified that `TasksClient` is missing the `subtasks_async()` method. The demo script and business model code expect this method:

```python
# Demo script (demo_sdk_operations.py:1500)
iterator = client.tasks.subtasks_async(recon_holder.gid, opt_fields=["name", "gid"])

# Business model (unit.py:326)
# Phase 2: Implement when TasksClient.get_subtasks_async() is available
```

The method does not exist, causing `AttributeError: 'TasksClient' object has no attribute 'subtasks_async'`.

### Expected API Endpoint

The Asana API provides: `GET /tasks/{task_gid}/subtasks`

This returns subtasks of a parent task, supporting pagination with `offset` and `limit` parameters.

### Existing Patterns

`TasksClient.list_async()` demonstrates the pagination pattern:
- Returns `PageIterator[Task]`
- Uses `self._http.get_paginated()` for pagination handling
- Builds params from function arguments
- Returns typed `Task` models via `Task.model_validate()`

```python
# tasks.py:421-486
def list_async(self, *, project: str | None = None, ...) -> PageIterator[Task]:
    async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
        params = self._build_opt_fields(opt_fields)
        # ... build params ...
        data, next_offset = await self._http.get_paginated("/tasks", params=params)
        tasks = [Task.model_validate(t) for t in data]
        return tasks, next_offset
    return PageIterator(fetch_page, page_size=min(limit, 100))
```

### Forces at Play

1. **Pattern consistency**: New method should match existing `list_async()` pattern
2. **Return type consistency**: Should return `PageIterator[Task]` like other list methods
3. **Method naming**: Demo expects `subtasks_async()`, not `list_subtasks_async()` or `get_subtasks_async()`
4. **Opt fields support**: Must support `opt_fields` parameter for field selection

## Decision

**Add `subtasks_async()` method to TasksClient** following the exact pattern of `list_async()`:

```python
def subtasks_async(
    self,
    task_gid: str,
    *,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Task]:
    """Get subtasks of a parent task.

    Per ADR-0057: Fetch subtasks via GET /tasks/{task_gid}/subtasks.

    Args:
        task_gid: Parent task GID.
        opt_fields: Fields to include in response.
        limit: Number of items per page (default 100, max 100).

    Returns:
        PageIterator[Task] - async iterator over subtask Task objects.

    Example:
        # Iterate all subtasks
        async for subtask in client.tasks.subtasks_async(parent_gid):
            print(subtask.name)

        # Get first 10
        subtasks = await client.tasks.subtasks_async(parent_gid).take(10)

        # Collect all
        all_subtasks = await client.tasks.subtasks_async(parent_gid).collect()
    """
```

## Rationale

### Why `subtasks_async` Not `list_subtasks_async`?

1. **Demo compatibility**: The demo script already uses `subtasks_async()`
2. **Business model references**: Code comments reference `subtasks_async()` (e.g., `demo_business_model.py:511`)
3. **Conciseness**: `subtasks_async()` is cleaner than `list_subtasks_async()`
4. **Consistency with other SDKs**: Many SDKs use `subtasks()` rather than `list_subtasks()`

### Why No Sync Wrapper?

The method returns `PageIterator[Task]` which is inherently async. A sync version would require collecting all results, changing the API contract. This is consistent with `list_async()` which also has no sync wrapper.

### Why PageIterator Return Type?

1. **Memory efficiency**: Large subtask lists are fetched lazily
2. **Pattern consistency**: Matches `list_async()` return type
3. **API parity**: Provides same `.take()`, `.collect()` methods

## Implementation Specification

### File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

**Change 1**: Add `subtasks_async()` method after `list_async()` (around line 487)

```python
    def subtasks_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Task]:
        """Get subtasks of a parent task with automatic pagination.

        Per ADR-0057: Fetch subtasks via GET /tasks/{task_gid}/subtasks.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            task_gid: Parent task GID.
            opt_fields: Fields to include in response.
            limit: Number of items per page (default 100, max 100).

        Returns:
            PageIterator[Task] - async iterator over subtask Task objects.

        Example:
            # Iterate all subtasks
            async for subtask in client.tasks.subtasks_async(parent_gid):
                print(subtask.name)

            # Get first 10
            subtasks = await client.tasks.subtasks_async(parent_gid).take(10)

            # Collect all
            all_subtasks = await client.tasks.subtasks_async(parent_gid).collect()
        """
        self._log_operation("subtasks_async", task_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            """Fetch a single page of subtasks."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/tasks/{task_gid}/subtasks", params=params
            )
            tasks = [Task.model_validate(t) for t in data]
            return tasks, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))
```

### Method Signature

```python
def subtasks_async(
    self,
    task_gid: str,
    *,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Task]:
```

### Location in File

Insert after `list_async()` method (after line 487 in current file), before any other methods.

### No New Imports Required

All required imports are already present in `tasks.py`:
- `PageIterator` from `autom8_asana.models`
- `Task` from `autom8_asana.models`

## Alternatives Considered

### Alternative A: `list_subtasks_async()`

**Description**: Name method `list_subtasks_async()` for consistency with `list_async()`

**Pros**:
- Consistent with `list_*` naming pattern
- Clear semantic meaning

**Cons**:
- Breaking: Demo code uses `subtasks_async()`
- More verbose
- Business model comments reference `subtasks_async()`

**Why not chosen**: Would break existing code and documentation

### Alternative B: `get_subtasks_async()`

**Description**: Name method `get_subtasks_async()`

**Pros**:
- Some business model comments reference this name
- Matches "get a list of subtasks" semantics

**Cons**:
- `get_*` usually returns a single item (e.g., `get_async(task_gid)`)
- Demo code uses `subtasks_async()`

**Why not chosen**: Semantic mismatch - `get_*` implies single item retrieval

### Alternative C: Add Sync Wrapper

**Description**: Add `subtasks()` sync method that collects all results

**Pros**:
- Sync API parity

**Cons**:
- Different return type than async version (list vs PageIterator)
- Memory risk for large subtask lists
- Not consistent with `list_async()` which has no sync version

**Why not chosen**: API inconsistency and memory concerns

## Consequences

### Positive

1. **Demo works**: Demo script subtask operations function correctly
2. **Business model unlocked**: Business hierarchy prefetching can be implemented
3. **Pattern consistent**: Follows established `list_async()` pattern
4. **Memory efficient**: PageIterator avoids loading all subtasks at once

### Negative

1. **No sync version**: Sync contexts must use `asyncio.run()` or equivalent
2. **Name precedent**: Establishes `subtasks_async` over `list_subtasks_async` pattern

### Neutral

1. **API expansion**: Adds one new public method to TasksClient
2. **Test coverage**: Requires new unit tests for the method

## Test Verification

After implementation, verify:

1. **Basic iteration**: `async for subtask in client.tasks.subtasks_async(parent_gid)` works
2. **Empty parent**: Task with no subtasks returns empty iterator
3. **opt_fields**: Custom fields are included when requested
4. **Pagination**: Tasks with many subtasks paginate correctly
5. **take() method**: `await client.tasks.subtasks_async(gid).take(5)` returns max 5 items
6. **collect() method**: `await client.tasks.subtasks_async(gid).collect()` returns full list
7. **Invalid GID**: Non-existent task GID raises appropriate error

## Compliance

### Enforcement

- **Unit tests**: Test method with mock HTTP client
- **Integration test**: Demo script subtask operations pass
- **Type checking**: mypy validates `PageIterator[Task]` return type

### Documentation

- Docstring includes usage examples
- Method follows established pattern, so existing `list_async()` docs apply
