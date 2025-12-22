# ADR-0107: NameGid for ActionOperation Targets

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-18
- **Deciders**: Architect, Principal Engineer
- **Related**: ADR-0006 (NameGid Standalone Model), ADR-0042 (Action Operation Types), TDD-AUTOMATION-LAYER

## Context

`ActionOperation` currently stores target references as bare GID strings:

```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None  # Only stores GID
    extra_params: dict[str, Any] = field(default_factory=dict)
```

This creates two problems:

### Problem 1: Lost Information

When a task is moved to a section, the section's name is lost:

```python
# Current code creates ActionOperation with only GID
action = ActionOperation(
    task=task,
    action=ActionType.MOVE_TO_SECTION,
    target_gid="1234567890",  # Section name is lost!
)
```

The automation engine then has to work around this by storing the section name in `extra_params`:

```python
# engine.py - Workaround to get section name
section_name = action_op.extra_params.get("section_name")
if section_name:
    context["section"] = section_name.lower()
```

### Problem 2: Inconsistent with SDK Patterns

The SDK consistently uses `NameGid` for all resource references:

- `Task.assignee: NameGid | None`
- `Task.projects: list[NameGid]`
- `Task.memberships[].section: NameGid`
- `SaveSession` methods accept `NameGid | str` parameters

But `ActionOperation.target_gid` breaks this pattern by storing only the GID string.

### Problem 3: Automation Trigger Failures

The automation layer needs to match on section names (e.g., trigger when task moves to "Converted" section). With only GIDs stored, the engine must:

1. Look in `extra_params` for manually-stored names (brittle)
2. Make additional API calls to resolve names (expensive)
3. Fail to match if name is unavailable

## Decision

Replace `target_gid: str | None` with `target: NameGid | None` in `ActionOperation`.

### New Structure

```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target: NameGid | None = None  # Preserves both gid and name
    extra_params: dict[str, Any] = field(default_factory=dict)
```

### API Call Adaptation

The `to_api_call()` method extracts the GID when needed:

```python
def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
    # Access the GID via target.gid
    match self.action:
        case ActionType.ADD_TAG:
            return (
                "POST",
                f"/tasks/{task_gid}/addTag",
                {"data": {"tag": self.target.gid}},  # Extract GID
            )
        # ... similar for other action types
```

### Creation Sites

Session methods will create `NameGid` from inputs:

```python
def move_to_section(
    self,
    task: AsanaResource,
    section: Section | NameGid | str,
    ...
) -> SaveSession:
    # Build NameGid preserving name when available
    if isinstance(section, str):
        target = NameGid(gid=section)
    elif isinstance(section, NameGid):
        target = section
    else:  # Section object
        target = NameGid(gid=section.gid, name=section.name)

    action = ActionOperation(
        task=task,
        action=ActionType.MOVE_TO_SECTION,
        target=target,  # Full NameGid
    )
```

### Automation Integration

The engine accesses section name directly:

```python
def _build_event_context(self, entity, event, result):
    if event == "section_changed":
        for action in result.action_results:
            action_op = action.action
            if action_op.action == ActionType.MOVE_TO_SECTION:
                # Direct access to name - no extra_params lookup
                context["section_gid"] = action_op.target.gid
                if action_op.target.name:
                    context["section"] = action_op.target.name.lower()
```

## Rationale

**Why NameGid over str?**
- Preserves name information without information loss
- Consistent with all other SDK resource references
- NameGid is frozen/immutable like ActionOperation
- NameGid provides `__hash__` and `__eq__` for identity

**Why not store name in extra_params?**
- `extra_params` is for positioning parameters (insert_before/after)
- Name is core identity information, not an "extra" parameter
- Type safety: `extra_params: dict[str, Any]` has no type guarantees

**Why change ActionOperation specifically?**
- ActionOperation is the only place storing bare GIDs
- It's an internal data structure (not public API)
- Change is self-contained to persistence layer

## Alternatives Considered

### Alternative A: Store Name in extra_params

- **Description**: Add `section_name`, `tag_name`, etc. to extra_params
- **Pros**: No dataclass change; backwards compatible
- **Cons**: Type-unsafe; inconsistent; clutters extra_params
- **Why not chosen**: Treats symptom not cause; perpetuates inconsistency

### Alternative B: Add Separate name Field

- **Description**: `ActionOperation(target_gid, target_name, ...)`
- **Pros**: Explicit fields; no new type
- **Cons**: Duplicates NameGid; two fields for one concept
- **Why not chosen**: NameGid already exists for this exact purpose

### Alternative C: Make target Union Type

- **Description**: `target: NameGid | AsanaResource | str | None`
- **Pros**: Maximum flexibility in what can be stored
- **Cons**: Complex type; requires resolution logic everywhere
- **Why not chosen**: NameGid is the canonical reference type

## Consequences

### Positive

- **Pattern consistency**: ActionOperation follows SDK conventions
- **Information preservation**: Section/tag/project names flow through
- **Automation support**: Rules can match on names without extra lookups
- **Type safety**: NameGid provides structure vs bare string

### Negative

- **Breaking change**: 14 `to_api_call()` references need `target.gid`
- **Test updates**: Fixtures must use `target=NameGid(...)` syntax
- **Resolution in executor**: Temp GID resolution must preserve name

### Neutral

- Field rename: `target_gid` -> `target`
- Type change: `str | None` -> `NameGid | None`
- 11 creation sites in session.py need updating

## Implementation Notes

### Files to Modify

1. **models.py**: ActionOperation dataclass + to_api_call()
2. **session.py**: All 11 action creation methods
3. **action_executor.py**: Temp GID resolution preserving name
4. **engine.py**: Use `target.name` instead of extra_params lookup

### Temp GID Resolution

When resolving temp GIDs, preserve the name:

```python
def _resolve_temp_gids(self, action, gid_map):
    target = action.target
    if target and target.gid.startswith("temp_") and target.gid in gid_map:
        # Preserve name while updating GID
        target = NameGid(gid=gid_map[target.gid], name=target.name)
```

### Backwards Compatibility

This is an internal refactor. The public API (`session.move_to_section()`, etc.) accepts the same types as before. Only the internal storage changes.

## Compliance

- ActionOperation MUST use `target: NameGid | None` for target references
- `to_api_call()` MUST extract GID via `self.target.gid`
- Session methods MUST create NameGid preserving name when available
- Action executor MUST preserve name during temp GID resolution
- Automation engine MUST use `target.name` for section matching
- Tests MUST use `target=NameGid(...)` in ActionOperation fixtures
