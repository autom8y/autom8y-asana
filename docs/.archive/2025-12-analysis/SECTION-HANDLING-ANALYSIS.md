# Section Handling Patterns: Architectural Analysis

> **Status**: Analysis Complete
> **Reviewer**: Architect Role
> **Date**: 2025-12-18
> **Scope**: Deep review of section representation and name retention across SDK

---

## Executive Summary

The SDK has an architectural gap in section handling: **section names are lost during move operations**. While `session.move_to_section()` accepts both `Section` objects and GID strings, only the GID is stored in `ActionOperation`. When the automation engine builds event context, it cannot retrieve the section name without an additional API call.

This contrasts with other entities (projects, tags, users) where name information is retained via the `NameGid` pattern. The gap impacts:
1. **Automation triggers** - Cannot match on section name (e.g., "converted")
2. **Logging/observability** - GID-only logs are not human-readable
3. **Developer experience** - Requires manual lookup for semantic understanding

**Recommendation**: Extend `ActionOperation.extra_params` to include `section_name` when available, with `NameGid` standardization for section references.

---

## 1. Current State Assessment

### 1.1 Section Model (`models/section.py`)

The `Section` model is well-defined and follows SDK patterns:

```python
class Section(AsanaResource):
    """Asana Section resource model."""
    resource_type: str | None = Field(default="section")
    name: str | None = None
    project: NameGid | None = None  # Uses NameGid pattern
    created_at: str | None = None
```

**Observations**:
- Section model has `name` property
- Uses `NameGid` for project reference (correct pattern)
- Section objects retrieved via `SectionsClient.get()` have full name

### 1.2 SaveSession.move_to_section()

```python
def move_to_section(
    self,
    task: AsanaResource,
    section: AsanaResource | str,  # Accepts Section object OR GID string
    *,
    insert_before: str | None = None,
    insert_after: str | None = None,
) -> SaveSession:
```

**Implementation**:
```python
section_gid = section if isinstance(section, str) else section.gid  # Name discarded!

action = ActionOperation(
    task=task,
    action=ActionType.MOVE_TO_SECTION,
    target_gid=section_gid,  # Only GID stored
    extra_params=extra_params,  # Position only, no section_name
)
```

**Gap Identified**: When `Section` object is passed, its `name` property is discarded. Only GID is retained.

### 1.3 ActionOperation Structure

```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None  # GID only, no name
    extra_params: dict[str, Any] = field(default_factory=dict)
```

**Current extra_params usage for MOVE_TO_SECTION**:
- `insert_before`: positioning GID
- `insert_after`: positioning GID

**Missing**: `section_name` field

### 1.4 Automation Engine Event Context

```python
def _build_event_context(self, entity, event, result):
    context: dict[str, Any] = {"event": event}

    if event == "section_changed":
        for action in result.action_results:
            if action_op.action == ActionType.MOVE_TO_SECTION:
                section_gid = action_op.target_gid
                context["section_gid"] = section_gid

                # Try to get section name from extra_params
                section_name = action_op.extra_params.get("section_name")
                if section_name:
                    context["section"] = section_name.lower()  # NOT POPULATED!
                break
```

**The code expects `section_name` in `extra_params` but it's never set.**

---

## 2. Gap Analysis

### 2.1 Information Flow Trace

```
[User Code]
    |
    v
session.move_to_section(task, section_obj)  # Section has name
    |
    | section_gid = section.gid  --> NAME LOST HERE
    v
ActionOperation(target_gid=section_gid)  # Name not stored
    |
    v
[Commit Phase]
    |
    v
ActionExecutor._execute_single_action()
    |
    v
[API Call: POST /sections/{gid}/addTask]
    |
    v
ActionResult(action=action_operation)  # Still no name
    |
    v
[Automation Phase]
    |
    v
_build_event_context()
    |
    | extra_params.get("section_name")  --> None
    v
context["section"] = ???  --> NOT SET
    |
    v
[Rule Matching]
    |
    | if event_context.get("section") == "converted":  --> FAILS
    v
Rule NOT triggered (false negative)
```

### 2.2 Comparison with Other Entity Patterns

| Entity | Reference Type | Name Retention | Pattern |
|--------|---------------|----------------|---------|
| **Project** | `NameGid` | Yes | `task.projects[0].name` |
| **User/Assignee** | `NameGid` | Yes | `task.assignee.name` |
| **Tag** | `NameGid` | Yes | `task.tags[0].name` |
| **Parent** | `NameGid` | Yes | `task.parent.name` |
| **Followers** | `list[NameGid]` | Yes | `task.followers[0].name` |
| **Section** | `str` (GID only) | **No** | Only GID in ActionOperation |

### 2.3 NameResolver Pattern

`NameResolver` supports sections:

```python
async def resolve_section_async(
    self,
    name_or_gid: str,
    project_gid: str,
) -> str:
    """Resolve section name to GID (project-scoped)."""
```

**Problem**: This resolves name -> GID, but we need GID -> name for event context.

The resolver could be extended with:
```python
async def lookup_section_name_async(
    self,
    section_gid: str,
    project_gid: str,
) -> str | None:
    """Lookup section name from GID (reverse resolution)."""
```

But this requires an API call at automation time, which is inefficient.

---

## 3. Recommended Solution

### 3.1 Primary Approach: Store Section Name in ActionOperation

**Modify `SaveSession.move_to_section()`** to extract and store section name:

```python
def move_to_section(
    self,
    task: AsanaResource,
    section: AsanaResource | str,
    *,
    insert_before: str | None = None,
    insert_after: str | None = None,
) -> SaveSession:
    self._ensure_open()

    if insert_before is not None and insert_after is not None:
        raise PositioningConflictError(insert_before, insert_after)

    # Extract both GID and name
    if isinstance(section, str):
        section_gid = section
        section_name = None  # Unknown when passed as string
    else:
        section_gid = section.gid
        section_name = getattr(section, 'name', None)  # Preserve name!

    # Build extra_params with position AND name
    extra_params: dict[str, str] = {}
    if insert_before is not None:
        extra_params["insert_before"] = insert_before
    if insert_after is not None:
        extra_params["insert_after"] = insert_after
    if section_name is not None:
        extra_params["section_name"] = section_name  # NEW!

    action = ActionOperation(
        task=task,
        action=ActionType.MOVE_TO_SECTION,
        target_gid=section_gid,
        extra_params=extra_params,
    )
    self._pending_actions.append(action)

    # Logging now includes name for observability
    if self._log:
        self._log.debug(
            "session_move_to_section",
            task_gid=task.gid,
            section_gid=section_gid,
            section_name=section_name,  # NEW!
        )

    return self
```

**Benefits**:
- Zero additional API calls
- No schema changes to ActionOperation (uses existing extra_params)
- Backward compatible (graceful degradation when name unknown)
- Automation engine already expects this pattern

### 3.2 Secondary Approach: NameGid for Section References

For stronger typing, consider introducing `SectionRef` or using `NameGid`:

```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None
    target_name: str | None = None  # NEW: Optional name for all targets
    extra_params: dict[str, Any] = field(default_factory=dict)
```

**Or** use NameGid as target:

```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target: NameGid | str | None = None  # NameGid carries both
    extra_params: dict[str, Any] = field(default_factory=dict)
```

**Trade-off**: More invasive change, but provides consistent pattern across all entity types.

### 3.3 Tertiary Approach: Lazy Resolution

Add reverse lookup to `NameResolver`:

```python
async def get_section_name_async(
    self,
    section_gid: str,
) -> str | None:
    """Get section name from GID (with caching)."""
    cache_key = f"section_name:{section_gid}"
    if cached := self._cache.get(cache_key):
        return cached

    # Fetch section
    section = await self._client.sections.get_async(section_gid)
    if section.name:
        self._cache[cache_key] = section.name
    return section.name
```

**Then in automation engine**:
```python
section_name = action_op.extra_params.get("section_name")
if not section_name and action_op.target_gid:
    # Lazy resolution
    section_name = await client.name_resolver.get_section_name_async(
        action_op.target_gid
    )
```

**Trade-off**: Adds API call, but handles GID-only case.

---

## 4. Implementation Options (Ranked)

| Option | Complexity | DX Improvement | API Calls | Breaking Change |
|--------|------------|----------------|-----------|-----------------|
| **A. extra_params** | Low | Medium | 0 | No |
| **B. target_name field** | Medium | High | 0 | Minor (additive) |
| **C. NameGid target** | High | High | 0 | Yes (signature) |
| **D. Lazy resolution** | Medium | Medium | 1 | No |

**Recommended**: Option A as immediate fix, Option B for v2.0

---

## 5. ADR Draft

### ADR-0107: Section Name Retention in ActionOperation

**Status**: Proposed

**Context**:
The automation layer needs section names to match trigger conditions (e.g., "when task moves to 'Converted'"). Currently, `session.move_to_section()` only stores section GID in `ActionOperation`, losing name information.

**Decision**:
Store section name in `ActionOperation.extra_params["section_name"]` when a `Section` object is passed to `move_to_section()`. When only GID is passed, the name remains `None` (graceful degradation).

**Consequences**:
- Positive: Automation rules can match on semantic section names
- Positive: Logging includes human-readable section names
- Positive: Zero additional API calls
- Neutral: When GID-only is passed, name unavailable (acceptable)
- Negative: Pattern inconsistency (projects use NameGid, sections use extra_params)

**Alternatives Considered**:
1. Add `target_name` field to ActionOperation - cleaner but more invasive
2. Use NameGid for all targets - most consistent but breaking change
3. Lazy resolution in automation - adds API latency

---

## 6. Impact Assessment

### 6.1 Files to Modify (Option A)

| File | Change |
|------|--------|
| `persistence/session.py` | Extract section_name in move_to_section() |
| `automation/engine.py` | Already expects section_name (no change) |

### 6.2 Test Coverage

Existing tests in:
- `tests/unit/persistence/test_session.py` - add test for section_name
- `tests/unit/automation/test_engine.py` - add test for section_changed event

### 6.3 Documentation

- Update TDD-0011 action operations
- Update automation layer docs

---

## 7. Conclusion

The section name retention gap is a straightforward fix with Option A (extra_params). The automation engine already expects this pattern; we just need to populate it in `SaveSession.move_to_section()`.

For long-term consistency, consider Option B (add `target_name` field) in a future version to align with the NameGid pattern used elsewhere.

**Recommended Action**: Implement Option A as a quick fix, create tracking issue for Option B in next major version.
