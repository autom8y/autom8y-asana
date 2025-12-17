# SESSION 5: P2 Custom Field Access + P3 Name Resolution

**Document ID:** SESSION-5-IMPLEMENTATION-CONTEXT
**Status:** Ready for Engineer
**Date:** 2025-12-12
**Scope:** Phase 2 (CustomFieldAccessor enhancement) + Phase 3 (NameResolver implementation)
**Dependencies:** Session 4 P1 complete (12 direct methods)
**Quality Gate:** [Will be verified before handoff]

---

## Executive Summary

**Session 4 (P1) is COMPLETE.** 12 direct methods implemented and tested. P1 is foundation.

**Session 5 contains TWO PHASES that can be worked SEQUENTIALLY:**

1. **P2: Custom Field Access** - Enhance `CustomFieldAccessor` with dictionary syntax (`__getitem__`, `__setitem__`, `__delitem__`)
2. **P3: Name Resolution** - New `NameResolver` class with per-SaveSession caching

**Both phases are independently designed and can proceed without blocking each other.** However, **recommend P2 first** (2-3 hours), then P3 (3-4 hours).

**Total Estimated Time:** 5-7 hours for both phases (can be split across sessions if needed).

---

## PHASE 2: Custom Field Access (P2)

### What P2 Delivers

Users can now use dictionary-style access for custom fields:

```python
# Before (verbose)
task.custom_fields.get("Priority")
task.custom_fields.set("Priority", "High")
task.custom_fields.remove("Priority")

# After (intuitive)
value = task.custom_fields["Priority"]  # __getitem__
task.custom_fields["Priority"] = "High"  # __setitem__
del task.custom_fields["Priority"]  # __delitem__
```

### P2 Scope (Minimal)

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`

**Changes:** Add 3 dunder methods (~30 lines total)

```python
# 1. Sentinel for missing values
_MISSING = object()

# 2. __getitem__ (8-10 lines)
def __getitem__(self, name_or_gid: str) -> Any:
    """Get custom field value using dictionary syntax."""
    result = self.get(name_or_gid, default=_MISSING)
    if result is _MISSING:
        raise KeyError(name_or_gid)
    return result

# 3. __setitem__ (4-6 lines)
def __setitem__(self, name_or_gid: str, value: Any) -> None:
    """Set custom field value using dictionary syntax."""
    self.set(name_or_gid, value)

# 4. __delitem__ (3-5 lines)
def __delitem__(self, name_or_gid: str) -> None:
    """Delete custom field using dictionary syntax."""
    self.remove(name_or_gid)
```

### Why This Design

**Chosen: Enhance CustomFieldAccessor (add dunder methods to existing class)**

**Why not create a wrapper class?**
- No duplication (wrapper would just delegate)
- Single instance model (no new wrappers created per access)
- Backward compatible (existing `.get()`, `.set()` unchanged)
- Type preservation automatic (delegates to existing `_extract_value()`)
- Change tracking automatic (delegates to existing `_modifications` dict)

**Reference:** ADR-0062-custom-field-accessor-enhancement.md

### P2 Implementation Details

#### File Location
- **Target:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`
- **Current State:** Lines 1-180 (has `get()`, `set()`, `remove()` methods)
- **Insert Location:** After `remove()` method (around line 95), before `to_list()` (around line 97)

#### Existing Dependencies (Don't Modify)

Already available in CustomFieldAccessor:

```python
self._data: list[dict[str, Any]]  # Original fields from API
self._resolver: DefaultCustomFieldResolver | None  # Optional resolver
self._modifications: dict[str, Any]  # Tracks changes (gid -> new_value)
self._name_to_gid: dict[str, str]  # Cache for name->gid

# Existing methods (don't change):
def get(self, name_or_gid: str, default: Any = None) -> Any
def set(self, name_or_gid: str, value: Any) -> None
def remove(self, name_or_gid: str) -> None
def _resolve_gid(self, name_or_gid: str) -> str  # Handles name->gid conversion
def _extract_value(self, field: dict) -> Any  # Extracts typed value
```

#### Type Preservation (Automatic)

When you call `self.get()` inside `__getitem__()`, the existing code handles all type preservation:

```
Field API format: {"gid": "123", "text_value": "High"} or {"number_value": 42}
                          ↓
_extract_value() reads appropriate key (text_value, number_value, enum_value, etc.)
                          ↓
__getitem__ returns extracted value (type: str, int, dict, Decimal, None, etc.)
```

No new logic needed—just delegate to existing `get()`.

#### Change Tracking (Automatic)

When you call `self.set()` inside `__setitem__()`, the existing code tracks changes:

```
self._modifications[gid] = value  (happens in existing set())
                          ↓
Task.save_async() calls SaveSession with modifications
                          ↓
SaveSession.ChangeTracker detects changes
                          ↓
API update sent with custom_fields payload
```

No new tracking logic needed—just delegate to existing `set()`.

### P2 Testing Requirements

**File:** `/Users/tomtenuta/Code/autom8_asana/tests/unit/models/test_custom_field_accessor.py` (already exists)

**Tests to add:**

```python
# 1. __getitem__ returns value for existing field
def test_custom_field_getitem_returns_existing_value():
    """__getitem__ returns value for existing field."""
    # Setup
    accessor = CustomFieldAccessor(data=[
        {"gid": "cf_123", "name": "Priority", "text_value": "High"}
    ])

    # Execute & Verify
    assert accessor["Priority"] == "High"
    assert accessor["cf_123"] == "High"  # By GID also works

# 2. __getitem__ raises KeyError for missing field
def test_custom_field_getitem_raises_keyerror_for_missing():
    """__getitem__ raises KeyError if field not found."""
    accessor = CustomFieldAccessor(data=[])
    with pytest.raises(KeyError):
        _ = accessor["NonExistent"]

# 3. __setitem__ sets value and marks dirty
def test_custom_field_setitem_marks_dirty():
    """__setitem__ sets value and marks field as dirty."""
    accessor = CustomFieldAccessor(data=[
        {"gid": "cf_123", "name": "Priority"}
    ])

    # Execute
    accessor["Priority"] = "Urgent"

    # Verify value set
    assert accessor["Priority"] == "Urgent"
    # Verify dirty tracking
    assert accessor.has_changes()

# 4. __delitem__ removes field
def test_custom_field_delitem_removes_field():
    """__delitem__ marks field for removal (set to None)."""
    accessor = CustomFieldAccessor(data=[
        {"gid": "cf_123", "name": "Priority", "text_value": "High"}
    ])

    # Execute
    del accessor["Priority"]

    # Verify marked for removal (returns None)
    assert accessor["Priority"] is None
    # Verify dirty tracking
    assert accessor.has_changes()

# 5. Type preservation in __getitem__/__setitem__
def test_custom_field_dict_syntax_preserves_types():
    """Dictionary syntax preserves field types (enum, number, text, date)."""
    from decimal import Decimal

    # Text field
    accessor = CustomFieldAccessor(data=[
        {"gid": "cf_text", "name": "Category", "text_value": "Internal"}
    ])
    assert isinstance(accessor["Category"], str)

    # Number field
    accessor = CustomFieldAccessor(data=[
        {"gid": "cf_num", "name": "MRR", "number_value": 1000.50}
    ])
    assert isinstance(accessor["MRR"], (int, float, Decimal))

    # Enum field (returns dict with gid + name)
    accessor = CustomFieldAccessor(data=[
        {"gid": "cf_enum", "name": "Status", "enum_value": {"gid": "e_123", "name": "Active"}}
    ])
    result = accessor["Status"]
    assert isinstance(result, dict)
    assert result.get("gid") == "e_123"

# 6. Backward compatibility (old .get/.set still work with new dunder methods)
def test_custom_field_mixed_syntax():
    """Can mix old .get()/.set() with new [] syntax."""
    accessor = CustomFieldAccessor(data=[
        {"gid": "cf_123", "name": "Priority"}
    ])

    # Old syntax
    accessor.set("Priority", "High")
    assert accessor.get("Priority") == "High"

    # New syntax (reads same field)
    assert accessor["Priority"] == "High"

    # New syntax
    accessor["Priority"] = "Urgent"

    # Old syntax (reads same field)
    assert accessor.get("Priority") == "Urgent"

# 7. Integration with save (changes via __setitem__ are persisted)
@pytest.mark.asyncio
async def test_custom_field_setitem_persisted_in_save(client_with_session):
    """Changes via __setitem__ are tracked and persisted in SaveSession."""
    client, session = client_with_session

    # Create task with custom field
    task = Task(gid="task_123", name="Test", custom_fields=[
        {"gid": "cf_123", "name": "Priority"}
    ])
    session.track(task)

    # Modify via dict syntax
    task.custom_fields["Priority"] = "High"

    # Verify change is tracked
    assert session.is_tracked(task)
    # Verify dirty detection sees the change
    assert task.custom_fields.has_changes()

    # (Actual save not tested here; that's QA responsibility)
```

### P2 Success Criteria

| Criterion | How to Verify |
|-----------|---------------|
| `__getitem__` works | Test returns value for existing field, raises KeyError for missing |
| `__setitem__` works | Test sets value, marks dirty, tracks in _modifications |
| `__delitem__` works | Test removes field (sets to None), marks dirty |
| Type preservation | Test all types (text, number, enum, date) are preserved |
| Change tracking | Test has_changes() reflects dict syntax changes |
| Backward compatible | Test mixed usage of old .get()/.set() and new [] syntax |
| Integration | Test changes via [] are included in save payloads |
| No regressions | All existing CustomFieldAccessor tests pass |

### P2 Execution Plan

1. **Add sentinel and dunder methods** (~20 minutes)
   - Add `_MISSING = object()` at class level
   - Implement `__getitem__`, `__setitem__`, `__delitem__`

2. **Write tests** (~40 minutes)
   - Test each dunder method (get/set/delete)
   - Test type preservation
   - Test backward compatibility
   - Test integration with save

3. **Run verification** (~10 minutes)
   - `pytest tests/unit/models/test_custom_field_accessor.py -v`
   - `mypy src/autom8_asana/models/custom_field_accessor.py`
   - `ruff check src/autom8_asana/models/custom_field_accessor.py`

**Total P2 Time:** ~70 minutes (2-3 hours including debugging/refinement)

---

## PHASE 3: Name Resolution (P3)

### What P3 Delivers

Users can resolve human-readable names to GIDs for common resources:

```python
# Before (verbose, manual GID lookup)
workspace_gid = client.default_workspace_gid
async for tag in client.tags.list_for_workspace_async(workspace_gid):
    if tag.name.lower() == "Urgent".lower():
        tag_gid = tag.gid
        break

# After (simple, automatic)
resolver = NameResolver(client)
tag_gid = await resolver.resolve_tag_async("Urgent")

# Works within SaveSession too:
async with SaveSession(client) as session:
    tag_gid = await session.name_resolver.resolve_tag_async("Urgent")  # Cached
    assignee_gid = await session.name_resolver.resolve_assignee_async("alice@example.com")
```

### P3 Scope

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/name_resolver.py` (NEW)

**New class:** `NameResolver`

**Methods (8 total: 4 async + 4 sync):**

```python
async def resolve_tag_async(self, name_or_gid: str, project_gid: str | None = None) -> str
async def resolve_section_async(self, name_or_gid: str, project_gid: str) -> str
async def resolve_project_async(self, name_or_gid: str, workspace_gid: str) -> str
async def resolve_assignee_async(self, name_or_gid: str, workspace_gid: str) -> str

def resolve_tag(self, name_or_gid: str, project_gid: str | None = None) -> str
def resolve_section(self, name_or_gid: str, project_gid: str) -> str
def resolve_project(self, name_or_gid: str, workspace_gid: str) -> str
def resolve_assignee(self, name_or_gid: str, workspace_gid: str) -> str
```

### Why Per-SaveSession Caching

**Problem:** Resolving multiple names in batch operations causes duplicate API calls:

```python
async with SaveSession(client) as session:
    tag_gid_1 = await resolver.resolve_tag_async("Urgent")      # API: list all tags
    tag_gid_2 = await resolver.resolve_tag_async("Backlog")     # API: list all tags AGAIN (wasteful)
    project_gid = await resolver.resolve_project_async("Q4")     # API: list all projects
```

**Solution:** Cache results within SaveSession context:

```python
async with SaveSession(client) as session:
    tag_gid_1 = await session.name_resolver.resolve_tag_async("Urgent")      # API: list tags once
    tag_gid_2 = await session.name_resolver.resolve_tag_async("Backlog")     # Cache hit (0 API calls)
    project_gid = await session.name_resolver.resolve_project_async("Q4")   # API: list projects once
```

**Why not per-Client TTL cache?**
- **Staleness risk:** Tags renamed/deleted after cache created
- **Complex TTL selection:** Too short (misses benefit), too long (staleness)
- **Over-engineered for MVP:** Per-session sufficient for typical batch ops

**Reference:** ADR-0060-name-resolution-caching-strategy.md

### P3 Implementation Details

#### File Location

**Target:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/name_resolver.py` (NEW FILE)

#### NameResolver Class Structure

```python
"""Name resolution for resources (tags, sections, projects, users).

Per ADR-0060: Per-SaveSession caching for performance (5-10x API reduction).
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING
from difflib import get_close_matches

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

class NameResolver:
    """Resolve resource names to GIDs with per-session caching.

    Supports polymorphic input (name_or_gid: str):
    - If input looks like GID (20+ alphanumeric chars): return as-is
    - Otherwise: Fetch resources, find matching name, cache GID, return it

    Cache Structure:
    - Key: f"{resource_type}:{scope}:{name.lower()}"
    - Value: GID
    - Lifetime: Duration of SaveSession (cleared on context exit)
    """

    def __init__(
        self,
        client: AsanaClient,
        session_cache: dict[str, str] | None = None
    ):
        """Initialize resolver.

        Args:
            client: AsanaClient instance
            session_cache: Per-SaveSession cache dict (None = new empty dict)
        """
        self._client = client
        self._cache: dict[str, str] = session_cache or {}

    async def resolve_tag_async(
        self,
        name_or_gid: str,
        project_gid: str | None = None
    ) -> str:
        """Resolve tag name to GID (workspace-scoped).

        Args:
            name_or_gid: Tag name or GID (e.g., "Urgent" or "1234567890abcdef")
            project_gid: Unused (tags are workspace-scoped, not project-scoped)

        Returns:
            Tag GID

        Raises:
            NameNotFoundError: If name not found (with suggestions)

        Example:
            >>> gid = await resolver.resolve_tag_async("Urgent")
            >>> # Or passthrough if already GID:
            >>> gid = await resolver.resolve_tag_async("1234567890abcdef1234")
        """
        # Passthrough if looks like GID
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        # Check cache
        cache_key = f"tag:{self._client.default_workspace_gid}:{name_or_gid.lower()}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all tags in workspace
        workspace_gid = self._client.default_workspace_gid
        all_tags = []
        async for tag in self._client.tags.list_for_workspace_async(workspace_gid):
            all_tags.append(tag)

        # Find exact match (case-insensitive, whitespace-tolerant)
        for tag in all_tags:
            if tag.name.lower().strip() == name_or_gid.lower().strip():
                self._cache[cache_key] = tag.gid
                return tag.gid

        # Not found - suggest alternatives
        available_names = [tag.name for tag in all_tags]
        suggestions = get_close_matches(
            name_or_gid,
            available_names,
            n=3,
            cutoff=0.6
        )

        from autom8_asana.exceptions import NameNotFoundError

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="tag",
            scope=workspace_gid,
            suggestions=suggestions,
            available_names=available_names,
        )

    async def resolve_section_async(
        self,
        name_or_gid: str,
        project_gid: str
    ) -> str:
        """Resolve section name to GID (project-scoped).

        Args:
            name_or_gid: Section name or GID
            project_gid: Project context (sections scoped to projects)

        Returns:
            Section GID

        Raises:
            NameNotFoundError: If name not found
        """
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        cache_key = f"section:{project_gid}:{name_or_gid.lower()}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all sections in project
        all_sections = []
        async for section in self._client.sections.list_by_project_async(project_gid):
            all_sections.append(section)

        # Find exact match
        for section in all_sections:
            if section.name.lower().strip() == name_or_gid.lower().strip():
                self._cache[cache_key] = section.gid
                return section.gid

        # Not found
        available_names = [s.name for s in all_sections]
        suggestions = get_close_matches(name_or_gid, available_names, n=3, cutoff=0.6)

        from autom8_asana.exceptions import NameNotFoundError

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="section",
            scope=project_gid,
            suggestions=suggestions,
            available_names=available_names,
        )

    async def resolve_project_async(
        self,
        name_or_gid: str,
        workspace_gid: str
    ) -> str:
        """Resolve project name to GID (workspace-scoped).

        Args:
            name_or_gid: Project name or GID
            workspace_gid: Workspace context

        Returns:
            Project GID

        Raises:
            NameNotFoundError: If name not found
        """
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        cache_key = f"project:{workspace_gid}:{name_or_gid.lower()}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all projects in workspace
        all_projects = []
        async for project in self._client.projects.list_for_workspace_async(workspace_gid):
            all_projects.append(project)

        # Find exact match
        for project in all_projects:
            if project.name.lower().strip() == name_or_gid.lower().strip():
                self._cache[cache_key] = project.gid
                return project.gid

        # Not found
        available_names = [p.name for p in all_projects]
        suggestions = get_close_matches(name_or_gid, available_names, n=3, cutoff=0.6)

        from autom8_asana.exceptions import NameNotFoundError

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="project",
            scope=workspace_gid,
            suggestions=suggestions,
            available_names=available_names,
        )

    async def resolve_assignee_async(
        self,
        name_or_gid: str,
        workspace_gid: str
    ) -> str:
        """Resolve user name or email to GID (workspace-scoped).

        Args:
            name_or_gid: User name, email, or GID
            workspace_gid: Workspace context

        Returns:
            User GID

        Raises:
            NameNotFoundError: If name/email not found
        """
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        cache_key = f"user:{workspace_gid}:{name_or_gid.lower()}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all users in workspace
        all_users = []
        async for user in self._client.users.list_by_workspace_async(workspace_gid):
            all_users.append(user)

        # Find match by name or email (case-insensitive)
        for user in all_users:
            if (user.name.lower().strip() == name_or_gid.lower().strip() or
                user.email.lower().strip() == name_or_gid.lower().strip()):
                self._cache[cache_key] = user.gid
                return user.gid

        # Not found
        available = [f"{u.name} ({u.email})" for u in all_users]
        suggestions = get_close_matches(name_or_gid, available, n=3, cutoff=0.6)

        from autom8_asana.exceptions import NameNotFoundError

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="user",
            scope=workspace_gid,
            suggestions=suggestions,
            available_names=available,
        )

    # Sync wrappers (using @sync_wrapper decorator)
    def resolve_tag(
        self,
        name_or_gid: str,
        project_gid: str | None = None
    ) -> str:
        """Resolve tag (sync)."""
        return self._resolve_tag_sync(name_or_gid, project_gid)

    @sync_wrapper("resolve_tag_async")
    async def _resolve_tag_sync(
        self,
        name_or_gid: str,
        project_gid: str | None = None
    ) -> str:
        return await self.resolve_tag_async(name_or_gid, project_gid)

    def resolve_section(self, name_or_gid: str, project_gid: str) -> str:
        """Resolve section (sync)."""
        return self._resolve_section_sync(name_or_gid, project_gid)

    @sync_wrapper("resolve_section_async")
    async def _resolve_section_sync(
        self,
        name_or_gid: str,
        project_gid: str
    ) -> str:
        return await self.resolve_section_async(name_or_gid, project_gid)

    def resolve_project(self, name_or_gid: str, workspace_gid: str) -> str:
        """Resolve project (sync)."""
        return self._resolve_project_sync(name_or_gid, workspace_gid)

    @sync_wrapper("resolve_project_async")
    async def _resolve_project_sync(
        self,
        name_or_gid: str,
        workspace_gid: str
    ) -> str:
        return await self.resolve_project_async(name_or_gid, workspace_gid)

    def resolve_assignee(self, name_or_gid: str, workspace_gid: str) -> str:
        """Resolve assignee (sync)."""
        return self._resolve_assignee_sync(name_or_gid, workspace_gid)

    @sync_wrapper("resolve_assignee_async")
    async def _resolve_assignee_sync(
        self,
        name_or_gid: str,
        workspace_gid: str
    ) -> str:
        return await self.resolve_assignee_async(name_or_gid, workspace_gid)

    @staticmethod
    def _looks_like_gid(value: str) -> bool:
        """Check if value looks like an Asana GID.

        GIDs are 20+ character alphanumeric strings (may contain underscores).
        """
        if len(value) < 20:
            return False
        # Remove underscores and check if remaining is alphanumeric
        return value.replace("_", "").isalnum()
```

#### Integration with SaveSession

**In SaveSession.__init__()** (around line 100):

```python
# Add to __init__
from autom8_asana.clients.name_resolver import NameResolver

self._name_cache: dict[str, str] = {}
self._name_resolver = NameResolver(self._client, self._name_cache)

@property
def name_resolver(self) -> NameResolver:
    """Get name resolver for this session (cached per-session)."""
    return self._name_resolver
```

**This allows:**

```python
async with SaveSession(client) as session:
    # Use name resolver (shared cache within session)
    tag_gid = await session.name_resolver.resolve_tag_async("Urgent")
    assignee_gid = await session.name_resolver.resolve_assignee_async("alice@example.com")
```

### P3 Testing Requirements

**File:** `/Users/tomtenuta/Code/autom8_asana/tests/unit/clients/test_name_resolver.py` (NEW)

**Tests to add:**

```python
@pytest.mark.asyncio
async def test_resolve_tag_by_name(client_with_mock):
    """resolve_tag_async returns GID for matching tag name."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    # Mock tag list
    mock_tag = Tag(gid="tag_123", name="Urgent")
    client.tags.list_for_workspace_async = mock_async_generator([mock_tag])

    # Execute
    gid = await resolver.resolve_tag_async("Urgent")

    # Verify
    assert gid == "tag_123"

@pytest.mark.asyncio
async def test_resolve_tag_passthrough_gid(client_with_mock):
    """resolve_tag_async passes through GID if input looks like GID."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    gid = "12345678901234567890"  # 20 char "GID"
    result = await resolver.resolve_tag_async(gid)

    assert result == gid  # No API call, just passthrough

@pytest.mark.asyncio
async def test_resolve_tag_case_insensitive(client_with_mock):
    """resolve_tag_async matches case-insensitively."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    mock_tag = Tag(gid="tag_123", name="Urgent")
    client.tags.list_for_workspace_async = mock_async_generator([mock_tag])

    # Execute with different case
    gid = await resolver.resolve_tag_async("urgent")

    assert gid == "tag_123"

@pytest.mark.asyncio
async def test_resolve_tag_raises_not_found(client_with_mock):
    """resolve_tag_async raises NameNotFoundError for missing tag."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    mock_tag = Tag(gid="tag_123", name="Urgent")
    client.tags.list_for_workspace_async = mock_async_generator([mock_tag])

    # Execute with non-existent name
    with pytest.raises(NameNotFoundError):
        await resolver.resolve_tag_async("NonExistent")

@pytest.mark.asyncio
async def test_resolve_tag_cache_hit(client_with_mock):
    """resolve_tag_async uses cache on second call (no API call)."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    mock_tag = Tag(gid="tag_123", name="Urgent")
    client.tags.list_for_workspace_async = mock_async_generator([mock_tag])

    # First call - API call made
    gid1 = await resolver.resolve_tag_async("Urgent")

    # Verify API was called
    assert client.tags.list_for_workspace_async.called

    # Reset mock to verify no second call
    client.tags.list_for_workspace_async.reset_mock()

    # Second call - should use cache
    gid2 = await resolver.resolve_tag_async("Urgent")

    # Verify no second API call
    assert not client.tags.list_for_workspace_async.called
    assert gid1 == gid2 == "tag_123"

@pytest.mark.asyncio
async def test_resolve_section_by_project(client_with_mock):
    """resolve_section_async returns GID for section in project."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    mock_section = Section(gid="sec_123", name="Backlog")
    client.sections.list_by_project_async = mock_async_generator([mock_section])

    gid = await resolver.resolve_section_async("Backlog", "project_456")

    assert gid == "sec_123"

@pytest.mark.asyncio
async def test_resolve_project_by_workspace(client_with_mock):
    """resolve_project_async returns GID for project in workspace."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    mock_project = Project(gid="proj_123", name="Q4 Planning")
    client.projects.list_for_workspace_async = mock_async_generator([mock_project])

    gid = await resolver.resolve_project_async("Q4 Planning", "workspace_789")

    assert gid == "proj_123"

@pytest.mark.asyncio
async def test_resolve_assignee_by_email(client_with_mock):
    """resolve_assignee_async matches user by email."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    mock_user = User(gid="user_123", name="Alice", email="alice@example.com")
    client.users.list_by_workspace_async = mock_async_generator([mock_user])

    gid = await resolver.resolve_assignee_async("alice@example.com", "workspace_789")

    assert gid == "user_123"

def test_resolve_tag_sync_wrapper(client_with_mock):
    """resolve_tag (sync) delegates to resolve_tag_async."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    mock_tag = Tag(gid="tag_123", name="Urgent")
    client.tags.list_for_workspace_async = mock_async_generator([mock_tag])

    # Execute sync
    gid = resolver.resolve_tag("Urgent")

    assert gid == "tag_123"

@pytest.mark.asyncio
async def test_resolve_suggestions_on_not_found(client_with_mock):
    """resolve_tag_async includes suggestions in NameNotFoundError."""
    client, mock = client_with_mock
    resolver = NameResolver(client)

    mock_tag = Tag(gid="tag_123", name="Urgent")
    client.tags.list_for_workspace_async = mock_async_generator([mock_tag])

    try:
        await resolver.resolve_tag_async("Urgant")  # Typo
    except NameNotFoundError as e:
        assert "Urgent" in e.suggestions  # Should suggest "Urgent"
    else:
        pytest.fail("NameNotFoundError not raised")
```

### P3 Success Criteria

| Criterion | How to Verify |
|-----------|---------------|
| resolve_tag_async works | Test returns GID for matching tag, raises NameNotFoundError for missing |
| resolve_section_async works | Test returns GID for section in project |
| resolve_project_async works | Test returns GID for project in workspace |
| resolve_assignee_async works | Test returns GID for user by name or email |
| GID passthrough | Test _looks_like_gid() and passthrough behavior |
| Case-insensitive | Test matching works regardless of case |
| Caching works | Test second call doesn't make API call (cache hit) |
| Error handling | Test NameNotFoundError with suggestions |
| Sync wrappers | Test all resolve_*() sync methods work |
| Integration with SaveSession | Test session.name_resolver accessible and cached |
| No regressions | All existing tests pass |

### P3 Execution Plan

1. **Create NameResolver class** (~60 minutes)
   - Copy template structure above
   - Implement resolve_tag_async, resolve_section_async, resolve_project_async, resolve_assignee_async
   - Implement all 4 sync wrappers
   - Implement _looks_like_gid() helper

2. **Integrate with SaveSession** (~20 minutes)
   - Add _name_cache and _name_resolver to SaveSession.__init__()
   - Add name_resolver property

3. **Write tests** (~50 minutes)
   - Test each resolve_*_async method
   - Test caching behavior
   - Test GID passthrough
   - Test error cases with suggestions
   - Test sync wrappers
   - Test integration with SaveSession

4. **Run verification** (~10 minutes)
   - `pytest tests/unit/clients/test_name_resolver.py -v`
   - `pytest tests/unit/persistence/test_session.py -v` (verify SaveSession integration)
   - `mypy src/autom8_asana/clients/name_resolver.py`
   - `ruff check src/autom8_asana/clients/name_resolver.py`

**Total P3 Time:** ~140 minutes (3-4 hours including debugging/refinement)

---

## Integration Points

### P2 ↔ P3 (No Dependency)

P2 and P3 are completely independent:

- **P2** enhances CustomFieldAccessor (models layer)
- **P3** adds NameResolver (clients layer)
- **No cross-dependencies** (can work in any order)

**Recommendation:** P2 first (simpler, smaller), then P3 (more complex).

### Both P2 & P3 ↔ P1 (Downstream)

Both phases depend on P1 being complete:

- **P1 provides:** Direct methods (add_tag_async, etc.)
- **P2 builds on:** P1 methods use custom field changes (P2 syntax)
- **P3 builds on:** P1 methods use name resolution (P3 caching)

But P2 and P3 **don't need P1 directly**—they just provide enhanced syntax that P1 benefits from.

### Future Integration (P4, P5)

- **P4 (Task.save_async):** Uses P2 custom field changes, P3 name resolution
- **P5 (AsanaClient constructor):** Uses P3 name resolution for workspace detection

---

## Testing Strategy

### Unit Tests (P2 + P3)

- **CustomFieldAccessor tests:** Test dunder methods in isolation
- **NameResolver tests:** Test resolve_*_async methods with mocked client
- **SaveSession integration:** Test name_resolver property accessible within session

### Integration Tests (Post-Implementation)

- **QA will verify:** Custom field dict syntax works end-to-end
- **QA will verify:** Name resolution works with actual Asana API
- **QA will verify:** SaveSession caching behavior in realistic scenarios

### Backward Compatibility

- **P2:** All existing CustomFieldAccessor.get()/.set()/.remove() tests must pass
- **P3:** No impact on existing SaveSession (new, additive feature)

---

## Quality Gates

### P2 Quality Gate

**Before moving to P3, verify:**

- [ ] All CustomFieldAccessor dunder methods implemented
- [ ] All P2 tests pass (`pytest tests/unit/models/test_custom_field_accessor.py`)
- [ ] Type checking passes (`mypy src/autom8_asana/models/custom_field_accessor.py`)
- [ ] Linting passes (`ruff check src/autom8_asana/models/custom_field_accessor.py`)
- [ ] No regressions in existing tests (`pytest tests/unit/models/`)
- [ ] Backward compatible (old .get/.set still work)

### P3 Quality Gate

**Before handoff to QA, verify:**

- [ ] NameResolver class implemented with 4 async + 4 sync methods
- [ ] SaveSession integration complete (name_resolver property)
- [ ] All P3 tests pass (`pytest tests/unit/clients/test_name_resolver.py`)
- [ ] Type checking passes (`mypy src/autom8_asana/clients/name_resolver.py`)
- [ ] Linting passes (`ruff check src/autom8_asana/clients/name_resolver.py`)
- [ ] No regressions in existing tests (`pytest tests/unit/`)
- [ ] Cache behavior verified (hits/misses correct)

---

## Success Criteria for Session 5

### P2 Success

- Dictionary-style access works: `task.custom_fields["Priority"] = "High"`
- KeyError raised for missing fields: `task.custom_fields["NonExistent"]`
- Type preservation automatic (enum, number, text, date all work)
- Change tracking automatic (has_changes() detects dict syntax changes)
- Backward compatible (old .get()/.set() unchanged)

### P3 Success

- Name resolution works for tags, sections, projects, assignees
- GID passthrough (input looks like GID: return as-is)
- Per-SaveSession caching (5-10x API reduction in batch ops)
- Helpful error messages with suggestions (typos forgiven)
- Sync wrappers work (resolve_tag, resolve_section, etc.)

### Overall Session 5 Success

**All P2 + P3 tests passing + No regressions + Type/lint clean + Ready for QA**

---

## What NOT to Do in Session 5

This session implements ONLY P2 + P3. Do NOT:

- **P4:** Don't add Task.save(), Task.refresh() methods
- **P5:** Don't enhance AsanaClient constructor
- **P1 Fixes:** Don't modify P1 methods (Session 4 complete)
- **Refactoring:** Don't refactor existing code (new features only)
- **Doc Updates:** Don't create user-facing docs (that's post-QA)

---

## File Locations (Copy-Paste Ready)

### P2 Implementation

```
Target: /Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py
Insert location: After remove() method (line 95), before to_list() (line 97)
Changes: Add _MISSING sentinel + 3 dunder methods (~30 lines)
```

### P2 Tests

```
Target: /Users/tomtenuta/Code/autom8_asana/tests/unit/models/test_custom_field_accessor.py
Changes: Add tests for __getitem__, __setitem__, __delitem__
```

### P3 Implementation

```
Target: /Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/name_resolver.py (NEW FILE)
New file with NameResolver class
```

### P3 SaveSession Integration

```
Target: /Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py
In __init__() (around line 100):
  - Import NameResolver
  - Add self._name_cache = {}
  - Add self._name_resolver = NameResolver(...)
  - Add @property name_resolver
```

### P3 Tests

```
Target: /Users/tomtenuta/Code/autom8_asana/tests/unit/clients/test_name_resolver.py (NEW FILE)
New file with NameResolver tests
Also update: /tests/unit/persistence/test_session.py (verify SaveSession.name_resolver)
```

---

## References

### Design Documents

- **ADR-0062:** CustomFieldAccessor Enhancement vs. Wrapper
  `/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0062-custom-field-accessor-enhancement.md`

- **ADR-0060:** Name Resolution Caching Strategy
  `/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0060-name-resolution-caching-strategy.md`

### Requirements

- **PRD-SDKUX:** SDK Usability Overhaul Requirements
  `/Users/tomtenuta/Code/autom8_asana/docs/design/PRD-SDKUX.md`

- **TDD-SDKUX:** SDK Usability Overhaul Design (Full Spec)
  `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-SDKUX.md` (§2 P2, §3 P3)

---

## Execution Recommendation

**Ready to proceed immediately with @principal-engineer for Session 5 (P2 + P3).**

### Sequencing Options

**Option A: Sequential (Recommended)**
1. P2 first (2-3 hours) → QA gate → Commit
2. P3 second (3-4 hours) → QA gate → Commit

**Option B: Parallel (If resources available)**
1. Work on P2 and P3 simultaneously (P2 simpler, gets done first)
2. Could split to 2 engineers if needed (no dependency)

**Recommendation:** Sequential (cleaner history, easier to debug if issues).

---

## Engineer Handoff Checklist

Before invoking @principal-engineer, verify:

- [ ] P1 (Session 4) is COMPLETE and committed
- [ ] TDD-SDKUX §2 (P2) and §3 (P3) are clear
- [ ] ADR-0062 (CustomFieldAccessor) understood
- [ ] ADR-0060 (Name Resolution Caching) understood
- [ ] File locations confirmed
- [ ] Test patterns understood
- [ ] No blockers from P1 implementation
- [ ] Team ready to proceed

**If all checked: Engineer ready for immediate Session 5 start.**

---
