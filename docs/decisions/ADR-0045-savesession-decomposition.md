# ADR-0045: SaveSession Decomposition & Optimization

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-19
- **Consolidated From**: ADR-0121, ADR-0122
- **Related**: [reference/SAVESESSION.md](/Users/tomtenuta/Code/autom8_asana/docs/decisions/reference/SAVESESSION.md), PRD-SPRINT-4-SAVESESSION-DECOMPOSITION, TDD-SPRINT-4-SAVESESSION-DECOMPOSITION

## Context

SaveSession (`persistence/session.py`) grew to 2193 lines with 50 methods, exhibiting "god class" symptoms. The codebase needed an 82% line reduction (2193 → ~400 lines) while preserving 100% backward compatibility.

Two fundamental questions required resolution:
1. **Extraction Strategy**: Should we create a package structure or refactor in-place?
2. **Boilerplate Reduction**: How to eliminate 920 lines of identical action method patterns?

Forces at play:
- 18 action methods (920 lines, 42% of class) follow identical boilerplate
- Tests access private attributes (`_state`, `_healing_queue`, `_auto_heal`)
- Import path `autom8_asana.persistence.session.SaveSession` must remain unchanged
- SaveSession components tightly integrated (unlike detection tiers)
- Healing logic exists in two places (standalone utilities + session methods)
- Action methods differ only in configuration (type, parameters, docstrings)

### Comparison to Detection Decomposition

Sprint 3 used package extraction for detection.py:
- 1125 lines → `detection/` package with tier submodules
- Conceptually independent tiers (structural, content, metadata)
- Each tier testable in isolation
- Clear boundaries between layers

SaveSession differs:
- Components share state (`_pending_actions`, `_healing_queue`)
- Tight coupling between tracking, actions, and commit
- Not layered architecture (more orchestration than tiers)

## Decision

### In-Place Refactoring with Sibling Module Extraction

1. **Keep SaveSession in `session.py`** (not a package)
2. **Create `persistence/actions.py`** for ActionBuilder infrastructure
3. **Expand `persistence/healing.py`** to include HealingManager class
4. **Add inspection properties** to SaveSession for test access
5. **Clean up commit logic inline** (not separate module)

**File Structure:**
```
persistence/
  ├── session.py          # SaveSession class (~400 lines)
  ├── actions.py          # ActionBuilder + registry (NEW, ~150 lines)
  ├── healing.py          # HealingManager + utilities (EXPANDED, ~200 lines)
  ├── models.py           # Unchanged
  └── pipeline.py         # Unchanged
```

**Line Reduction Breakdown:**
- ActionBuilder extraction: 770 lines → ~20 lines (declarations)
- HealingManager extraction: 115 lines → ~30 lines (delegation)
- Inline cleanup: ~900 lines (docstrings, redundant code)
- **Total: 2193 → ~400 lines (82% reduction)**

### ActionBuilder Descriptor Pattern

Replace 18 action methods with descriptor-based factory:

**Before (920 lines):**
```python
class SaveSession:
    def add_tag(self, task: AsanaResource, tag: str | NameGid) -> SaveSession:
        """Add a tag to a task.

        Args:
            task: The task to add the tag to
            tag: Tag GID or NameGid

        Returns:
            self for method chaining
        """
        self._ensure_active()
        target_gid = tag.gid if isinstance(tag, NameGid) else tag
        target_name = tag.name if isinstance(tag, NameGid) else None
        operation = ActionOperation(
            task=task,
            action=ActionType.ADD_TAG,
            target=NameGid(target_gid, target_name)
        )
        self._pending_actions.append(operation)
        logger.debug(f"Queued add_tag: {task.gid} + {target_gid}")
        return self

    def remove_tag(self, task: AsanaResource, tag: str | NameGid) -> SaveSession:
        """Remove a tag from a task.

        Args:
            task: The task to remove the tag from
            tag: Tag GID or NameGid

        Returns:
            self for method chaining
        """
        self._ensure_active()
        target_gid = tag.gid if isinstance(tag, NameGid) else tag
        target_name = tag.name if isinstance(tag, NameGid) else None
        operation = ActionOperation(
            task=task,
            action=ActionType.REMOVE_TAG,
            target=NameGid(target_gid, target_name)
        )
        self._pending_actions.append(operation)
        logger.debug(f"Queued remove_tag: {task.gid} + {target_gid}")
        return self

    # ... 16 more identical patterns
```

**After (~150 lines total in actions.py + 20 lines in session.py):**

```python
# In persistence/actions.py

class ActionVariant(Enum):
    """Variant of action operation determining parameter handling."""
    NO_TARGET = "no_target"           # Likes (no target param)
    TARGET_REQUIRED = "target_required"  # Tags, followers (target param)
    POSITIONING = "positioning"       # Projects, sections (target + insert_*)

@dataclass
class ActionConfig:
    """Configuration for an action method."""
    action_type: ActionType
    variant: ActionVariant
    target_param: str  # Parameter name ("tag", "user", "project", etc.)
    log_event: str     # Log event name
    docstring: str     # Method docstring

# Registry of action configurations
ACTION_REGISTRY: dict[str, ActionConfig] = {
    "add_tag": ActionConfig(
        action_type=ActionType.ADD_TAG,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="tag",
        log_event="session_add_tag",
        docstring="Add a tag to a task.",
    ),
    "remove_tag": ActionConfig(
        action_type=ActionType.REMOVE_TAG,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="tag",
        log_event="session_remove_tag",
        docstring="Remove a tag from a task.",
    ),
    # ... 16 more configurations
}

class ActionBuilder:
    """Descriptor that builds action methods from configuration."""

    def __init__(self, action_name: str):
        self.action_name = action_name
        self.config = ACTION_REGISTRY[action_name]

    def __set_name__(self, owner, name):
        self.method_name = name

    def __get__(self, obj, objtype=None):
        """Return bound method that executes action."""
        if obj is None:
            return self

        config = self.config

        def action_method(
            task: AsanaResource,
            target: str | NameGid | None = None,
            **kwargs
        ) -> SaveSession:
            # Implementation based on variant
            match config.variant:
                case ActionVariant.NO_TARGET:
                    # Likes - no target
                    operation = ActionOperation(
                        task=task,
                        action=config.action_type,
                        target=None
                    )
                case ActionVariant.TARGET_REQUIRED:
                    # Tags, followers - require target
                    if target is None:
                        raise ValueError(f"{config.target_param} required")
                    target_gid = target.gid if isinstance(target, NameGid) else target
                    target_name = target.name if isinstance(target, NameGid) else None
                    operation = ActionOperation(
                        task=task,
                        action=config.action_type,
                        target=NameGid(target_gid, target_name)
                    )
                case ActionVariant.POSITIONING:
                    # Projects, sections - target + positioning
                    if target is None:
                        raise ValueError(f"{config.target_param} required")
                    target_gid = target.gid if isinstance(target, NameGid) else target
                    target_name = target.name if isinstance(target, NameGid) else None
                    extra_params = {}
                    if "insert_before" in kwargs:
                        extra_params["insert_before"] = kwargs["insert_before"]
                    if "insert_after" in kwargs:
                        extra_params["insert_after"] = kwargs["insert_after"]
                    operation = ActionOperation(
                        task=task,
                        action=config.action_type,
                        target=NameGid(target_gid, target_name),
                        extra_params=extra_params
                    )

            obj._ensure_active()
            obj._pending_actions.append(operation)
            logger.debug(f"Queued {config.log_event}: {task.gid}")
            return obj

        # Preserve docstring and signature
        action_method.__doc__ = config.docstring
        action_method.__name__ = self.method_name
        return action_method

# In persistence/session.py

from autom8_asana.persistence.actions import ActionBuilder

class SaveSession:
    # Descriptor declarations (18 lines replace 920 lines)
    add_tag = ActionBuilder("add_tag")
    remove_tag = ActionBuilder("remove_tag")
    add_follower = ActionBuilder("add_follower")
    remove_follower = ActionBuilder("remove_follower")
    add_to_project = ActionBuilder("add_to_project")
    remove_from_project = ActionBuilder("remove_from_project")
    move_to_section = ActionBuilder("move_to_section")
    add_like = ActionBuilder("add_like")
    remove_like = ActionBuilder("remove_like")
    # ... 9 more total
```

**Descriptor Benefits:**
- Signature preservation (descriptors return bound methods)
- IDE support (`help()` and type hints work)
- Single source of truth (ACTION_REGISTRY)
- 920 → ~150 lines (83% reduction)
- New actions: add one registry entry

## Rationale

### Why In-Place Over Package Extraction?

| Factor | Package Approach | In-Place Approach | Winner |
|--------|-----------------|-------------------|--------|
| Import path stability | Requires `__init__.py` re-exports | No changes needed | **In-place** |
| Test disruption | Tests must update imports | Tests unchanged | **In-place** |
| Code review | Many new files, complex diffs | Fewer focused changes | **In-place** |
| IDE navigation | Harder to find SaveSession | SaveSession discoverable | **In-place** |
| Rollback | Delete package, restore file | Revert individual modules | **In-place** |
| Mental model | Facade + submodules | Core class + helpers | **In-place** |

**Key Insight:**
- Detection tiers are conceptually independent (structural ≠ content ≠ metadata)
- SaveSession components tightly integrated (tracking + actions + commit are one flow)
- Package structure better for layers, not for orchestration

### Why ActionBuilder Descriptor Pattern?

**Alternative Considered: Mixin Classes**
```python
class ActionMixin:
    def add_tag(self, task, tag): ...
    def remove_tag(self, task, tag): ...

class SaveSession(ActionMixin, HealingMixin):
    ...
```

**Rejected Because:**
- Multiple inheritance MRO complexity
- Mixins share instance state (tight coupling)
- Doesn't reduce boilerplate (still 18 methods)
- Harder to test mixins in isolation

**ActionBuilder Advantages:**
1. **Single Source of Truth**: ACTION_REGISTRY defines all behavior
2. **Boilerplate Elimination**: 83% line reduction (920 → 150)
3. **Type Safety**: ActionVariant enum catches missing patterns
4. **Extensibility**: New actions = one registry entry
5. **Testability**: ActionBuilder testable independently
6. **IDE Support**: Descriptors provide proper signatures and docstrings

### Why Expand healing.py (Not Create New Module)?

**Current State:**
- `persistence/healing.py` (~80 lines): Standalone utilities
- `session.py` (~165 lines): `_should_heal()`, `_queue_healing()`, `_execute_healing_async()`

**Creating third location** (e.g., `session/healing.py`) would:
- Fragment healing logic across three files
- Complicate imports
- Confuse ownership

**Merging into existing `healing.py`:**
- Single source of truth for all healing
- Standalone utilities remain available
- Session delegates to `HealingManager.execute_async()`
- Clear ownership

### Why Keep commit Logic Inline?

After ActionBuilder (770 lines) + HealingManager (115 lines) extraction:
- `commit_async()` size: ~100 lines
- Phase ordering critical (DEF-001 fix, selective clearing)
- Extracting adds indirection without meaningful simplification

**Better Approach:**
- Clean up with private helper methods inline
- Keep related logic together
- Avoid over-abstraction

## Alternatives Considered

### Alternative 1: Package Structure (Like Detection)

**Description**: Create `persistence/session/` package with `__init__.py`, `actions.py`, `state.py`, `healing.py`, `commit.py`.

**Pros**:
- Consistent with ADR-0120 detection pattern
- Clear module boundaries
- Easy to extend with new submodules

**Cons**:
- Requires `__init__.py` re-exports to maintain API
- Tests must update imports or use re-exports
- Adds complexity for tightly-coupled code
- More files to navigate
- Facade pattern overhead

**Why not chosen**: SaveSession components more integrated than detection tiers. Package structure adds complexity without proportional benefit.

### Alternative 2: Code Generation

**Description**: Use code generation script to produce 18 action methods from YAML config.

**Pros**:
- Full methods in source (grep-able)
- No descriptor magic
- Clear signatures

**Cons**:
- Build step complexity
- Generated code harder to debug
- Merges create conflicts
- Not truly single source of truth

**Why not chosen**: Descriptor pattern provides same benefits without build complexity.

### Alternative 3: String-Based dispatch

**Description**: Single `_execute_action(action_name: str, ...)` method dispatched from wrappers.

**Pros**:
- Very small implementation
- Easy to extend

**Cons**:
- No type safety
- IDE doesn't know methods exist
- No autocomplete
- Runtime errors for typos

**Why not chosen**: Type safety and IDE support too valuable to sacrifice.

### Alternative 4: Mixin Classes

**Description**: Define `ActionMixin`, `HealingMixin`, `CommitMixin`, compose into SaveSession.

**Pros**:
- Methods stay on SaveSession
- No import path changes
- Clear separation by concern

**Cons**:
- Multiple inheritance MRO complexity
- Mixins share instance state (coupling)
- Doesn't reduce boilerplate (18 methods still written)
- Harder to test mixins in isolation

**Why not chosen**: Mixins work for orthogonal concerns. SaveSession concerns share state making clean mixin boundaries difficult.

### Alternative 5: Keep Everything in session.py

**Description**: Reduce line count through shorter docstrings, less logging, consolidation only.

**Pros**:
- No structural changes
- Lowest risk
- Everything in one place

**Cons**:
- Cannot achieve 82% reduction target
- Boilerplate remains
- Cognitive load unchanged
- 2193 lines still "god class"

**Why not chosen**: Does not meet PRD targets. The 18 action methods are fundamentally boilerplate that should be generated.

## Consequences

### Positive

- **Minimal Disruption**: Import path unchanged, tests work as-is
- **Massive Reduction**: 82% line reduction (2193 → ~400)
- **Clear Extraction**: ActionBuilder and HealingManager have distinct responsibilities
- **Testable Components**: ActionBuilder and HealingManager unit tested independently
- **Type Safety**: ActionVariant enum catches missing patterns
- **Single Source of Truth**: ACTION_REGISTRY defines all action behavior
- **Extensibility**: New actions = one registry entry
- **IDE Support**: Descriptors provide proper signatures and docstrings
- **Single Healing Location**: All healing logic in `persistence/healing.py`

### Negative

- **session.py Still Central**: ~400 lines remain in one file
- **New Module to Learn**: `actions.py` introduces ActionBuilder pattern
- **Descriptor Complexity**: Intermediate Python concept (not beginner-friendly)
- **HealingManager Coupling**: SaveSession depends on HealingManager
- **Debugging Descriptors**: Stack traces show descriptor machinery

### Neutral

- **Line Count**: 82% reduction via different distribution than package approach
- **File Count**: +1 new file (`actions.py`), healing.py expanded
- **Test Coverage**: Existing tests pass; new tests for ActionBuilder
- **Documentation**: ActionBuilder pattern needs explanation

## Compliance

### Enforcement

1. **Code Review**: ActionBuilder usage required for new action methods
2. **Test Presence**: `test_action_builder.py` must exist and pass
3. **Line Count Gate**: session.py must remain under 500 lines post-extraction
4. **Import Validation**: No direct imports from `persistence/session/` (package does not exist)
5. **Registry Completeness**: All action methods must have ACTION_REGISTRY entry

### Verification

**After Implementation:**
```bash
# Verify line counts
wc -l src/autom8_asana/persistence/session.py  # Should be ~400
wc -l src/autom8_asana/persistence/actions.py  # Should be ~150
wc -l src/autom8_asana/persistence/healing.py  # Should be ~200

# Verify import path unchanged
python -c "from autom8_asana.persistence.session import SaveSession"

# Verify all tests pass
pytest tests/unit/persistence/test_session*.py -v
pytest tests/unit/persistence/test_actions.py -v
```

**Testing:**
- All existing session tests pass unchanged
- New tests for ActionBuilder descriptor
- New tests for HealingManager
- Integration tests verify action methods still work
- Test coverage maintained at 90%+

## Implementation Guidance

### Adding New Action Type

**Step 1: Define ActionType**
```python
# In persistence/models.py
class ActionType(Enum):
    # ... existing types
    ADD_ATTACHMENT = "add_attachment"
```

**Step 2: Add Registry Entry**
```python
# In persistence/actions.py
ACTION_REGISTRY["add_attachment"] = ActionConfig(
    action_type=ActionType.ADD_ATTACHMENT,
    variant=ActionVariant.TARGET_REQUIRED,
    target_param="attachment",
    log_event="session_add_attachment",
    docstring="Add an attachment to a task.",
)
```

**Step 3: Declare Descriptor**
```python
# In persistence/session.py
class SaveSession:
    # ... existing descriptors
    add_attachment = ActionBuilder("add_attachment")
```

**Done!** Method available with full IDE support.

### Using ActionBuilder Directly

**For Testing:**
```python
def test_action_builder():
    """Test ActionBuilder descriptor pattern."""
    builder = ActionBuilder("add_tag")
    assert builder.config.action_type == ActionType.ADD_TAG
    assert builder.config.variant == ActionVariant.TARGET_REQUIRED

    # Test bound method creation
    session = SaveSession(client)
    method = builder.__get__(session, SaveSession)
    assert callable(method)

    # Execute method
    task = Task(gid="task_123")
    tag = "tag_456"
    result = method(task, tag)
    assert result is session  # Method chaining
```

### HealingManager Usage

**Session Integration:**
```python
# In SaveSession.commit_async()
if self._auto_heal and self._healing_queue:
    healing_manager = HealingManager(self._client)
    healing_results = await healing_manager.execute_async(
        self._healing_queue
    )
    # Process healing results...
```

**Standalone Usage:**
```python
# Direct healing without SaveSession
manager = HealingManager(client)
operations = [
    HealingOperation(entity=task, issue=CustomFieldMissing(...))
]
results = await manager.execute_async(operations)
```

## Cross-References

**Related ADRs:**
- ADR-0040: Unit of Work Pattern (SaveSession foundation)
- ADR-0041: Dependency Ordering (commit pipeline)
- ADR-0042: Error Handling (result handling)
- ADR-0043: Action Operations (action types and operations)
- ADR-0044: Lifecycle & Integration (healing, cache invalidation)

**Related Documents:**
- PRD-SPRINT-4-SAVESESSION-DECOMPOSITION: Requirements for decomposition
- TDD-SPRINT-4-SAVESESSION-DECOMPOSITION: Technical design for refactoring
- REF-savesession-lifecycle: Session state machine and phases
