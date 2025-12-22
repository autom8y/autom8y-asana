# ADR-0122: Action Method Factory Pattern

## Metadata
- **Status**: Proposed
- **Author**: Architect (Claude)
- **Date**: 2025-12-19
- **Deciders**: SDK Team
- **Related**: [PRD-SPRINT-4-SAVESESSION-DECOMPOSITION](/docs/requirements/PRD-SPRINT-4-SAVESESSION-DECOMPOSITION.md), [TDD-SPRINT-4-SAVESESSION-DECOMPOSITION](/docs/design/TDD-SPRINT-4-SAVESESSION-DECOMPOSITION.md), ADR-0121, ADR-0107

## Context

SaveSession has 18 action methods (920 lines, 42% of total) that follow nearly identical patterns:

```python
def add_tag(self, task: AsanaResource, tag: AsanaResource | str) -> SaveSession:
    self._ensure_open()
    if isinstance(tag, str):
        target = NameGid(gid=tag)
    else:
        target = NameGid(gid=tag.gid, name=getattr(tag, "name", None))
    validate_gid(target.gid, "tag_gid")
    action = ActionOperation(task=task, action=ActionType.ADD_TAG, target=target)
    self._pending_actions.append(action)
    if self._log:
        self._log.debug("session_add_tag", task_gid=task.gid, tag_gid=target.gid)
    return self
```

Each method differs only in:
- `ActionType` enum value
- Parameter name (`tag`, `project`, `user`, etc.)
- Validation requirements (some need `validate_gid`, others don't)
- Positioning support (some have `insert_before`/`insert_after`)
- Target presence (some like `add_like` have no target)

**The key question**: How should we consolidate these 18 methods into reusable infrastructure while preserving exact public API signatures?

Forces at play:
- All methods must return `self` for fluent chaining
- All methods must preserve exact function signatures
- Type hints must be accurate for IDE support
- Docstrings must be accessible via `help()`
- 5 methods have custom logic beyond the pattern (add_comment, set_parent, reorder_subtask, add_followers, remove_followers)
- Performance cannot regress (<5% latency increase)

## Decision

We will use a **descriptor-based factory pattern** with configuration registry:

```python
# In SaveSession class:
add_tag = ActionBuilder("add_tag")
remove_tag = ActionBuilder("remove_tag")
add_to_project = ActionBuilder("add_to_project")
# ... 13 total ActionBuilder declarations

# 5 methods with custom logic remain explicit:
def add_comment(self, task, text, *, html_text=None) -> SaveSession: ...
def set_parent(self, task, parent, *, insert_before=None, insert_after=None) -> SaveSession: ...
def reorder_subtask(self, task, *, insert_before=None, insert_after=None) -> SaveSession: ...
def add_followers(self, task, users) -> SaveSession: ...
def remove_followers(self, task, users) -> SaveSession: ...
```

ActionBuilder is a Python descriptor that:
1. Reads configuration from `ACTION_REGISTRY` at class definition time
2. Returns a bound method when accessed on an instance
3. Generates method body based on ActionVariant (NO_TARGET, TARGET_REQUIRED, POSITIONING)

## Rationale

### Why Descriptors Over Other Approaches?

| Criterion | Decorator | Metaclass | Factory Function | **Descriptor** |
|-----------|-----------|-----------|------------------|----------------|
| Signature preservation | Hard (wraps) | Hard (generates) | Medium | **Easy** |
| IDE support | Poor | Poor | Medium | **Good** |
| `help()` works | No (shows wrapper) | Yes | Medium | **Yes** |
| Runtime cost | Per-call | Class load | Per-call | **Per-call (cached)** |
| Complexity | Low | High | Medium | **Medium** |
| Type hints | Lost | Complex | Partial | **Preserved** |

**Key insight**: Descriptors are the Python mechanism for defining how attribute access works. They are used by `property`, `classmethod`, `staticmethod`, and Django ORM fields. The pattern is well-established and understood.

### How Descriptors Preserve Signatures

```python
class ActionBuilder:
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self  # Access on class returns descriptor
        return self._make_method(obj)  # Access on instance returns bound method

    def _make_method(self, session):
        def method(task, target):
            # ... generated body
            return session
        method.__doc__ = self._config.docstring
        method.__name__ = self._action_name
        return method
```

When you call `session.add_tag(task, tag)`:
1. Python looks up `add_tag` on the `SaveSession` class
2. Finds `ActionBuilder` descriptor
3. Calls `ActionBuilder.__get__(session, SaveSession)`
4. Returns generated method bound to `session`
5. Calls generated method with `(task, tag)`

### Why Three ActionVariants?

Analysis of 18 methods reveals three distinct patterns:

**NO_TARGET** (2 methods): No second parameter
- `add_like(task) -> SaveSession`
- `remove_like(task) -> SaveSession`

**TARGET_REQUIRED** (9 methods): Second parameter is entity/GID
- `add_tag(task, tag) -> SaveSession`
- `remove_tag(task, tag) -> SaveSession`
- `add_dependency(task, depends_on) -> SaveSession`
- `remove_dependency(task, depends_on) -> SaveSession`
- `add_follower(task, user) -> SaveSession`
- `remove_follower(task, user) -> SaveSession`
- `add_dependent(task, dependent_task) -> SaveSession`
- `remove_dependent(task, dependent_task) -> SaveSession`
- `remove_from_project(task, project) -> SaveSession`

**POSITIONING** (4 methods): Has `insert_before`/`insert_after` kwargs
- `add_to_project(task, project, *, insert_before=None, insert_after=None) -> SaveSession`
- `move_to_section(task, section, *, insert_before=None, insert_after=None) -> SaveSession`
- `set_parent(task, parent, *, insert_before=None, insert_after=None) -> SaveSession` [has custom logic]
- Methods with positioning conflict validation per ADR-0047

### Why Keep 5 Methods Explicit?

These methods have logic beyond the standard pattern:

| Method | Custom Logic |
|--------|-------------|
| `add_comment` | Validates non-empty text; has `html_text` parameter |
| `set_parent` | `parent=None` means promote to top-level |
| `reorder_subtask` | Validates task has parent before calling set_parent |
| `add_followers` | Loops over list, calls add_follower for each |
| `remove_followers` | Loops over list, calls remove_follower for each |

Attempting to parameterize these would add complexity without reducing lines.

### Why Configuration Registry Over Parameters?

Instead of:
```python
add_tag = ActionBuilder(ActionType.ADD_TAG, variant=ActionVariant.TARGET_REQUIRED, ...)
```

We use:
```python
add_tag = ActionBuilder("add_tag")  # Looks up in ACTION_REGISTRY
```

Benefits:
- Class definition stays clean (20 lines instead of 100+)
- Configuration centralized and easy to audit
- Adding new action = add registry entry + descriptor declaration
- Type checker can validate registry completeness

### Performance Considerations

Descriptor access has per-call cost for method generation. Mitigation options:

1. **Cache bound methods**: Store generated method in instance `__dict__`
2. **Pre-generate at class definition**: Use `__set_name__` to modify class
3. **Accept small overhead**: Method generation is lightweight

For MVP, we accept small overhead. Benchmarks in Phase 2 will determine if caching is needed.

## Alternatives Considered

### Alternative 1: Decorator-Based Generation

- **Description**: Define decorators that transform minimal function stubs:
  ```python
  @action_method(ActionType.ADD_TAG, variant=ActionVariant.TARGET_REQUIRED)
  def add_tag(self, task, tag): pass
  ```
- **Pros**:
  - Familiar decorator syntax
  - Explicit method signatures in code
- **Cons**:
  - Decorator wraps the function, breaking `help()`
  - Type hints on stub may not propagate
  - Still 18 stub definitions
- **Why not chosen**: Wrapping breaks introspection. We want `help(session.add_tag)` to show the real docstring.

### Alternative 2: Metaclass Generation

- **Description**: Use `__init_subclass__` or custom metaclass to generate methods:
  ```python
  class SaveSession(metaclass=ActionMethodsMeta):
      ACTION_METHODS = ["add_tag", "remove_tag", ...]
  ```
- **Pros**:
  - Methods generated once at class definition
  - No per-call overhead
  - Clean class body
- **Cons**:
  - Metaclass inheritance is complex
  - Harder to debug (magic generation)
  - Per TDD-0024, metaclasses have maintenance cost
- **Why not chosen**: Metaclass pattern evaluated in ADR-0024 patterns sprint. Decision was: use for "single source of truth" patterns only. Action methods don't meet that bar.

### Alternative 3: Code Generation (Pre-Commit)

- **Description**: Script generates method code, checked into source:
  ```bash
  python scripts/generate_action_methods.py > src/.../session_actions.py
  ```
- **Pros**:
  - Zero runtime cost
  - Full type hints and docstrings
  - IDE sees real code
- **Cons**:
  - Generated code must stay in sync
  - Two sources of truth (template + generated)
  - Merge conflicts on generated file
- **Why not chosen**: Synchronization burden. Developers must remember to regenerate after config changes.

### Alternative 4: functools.partialmethod

- **Description**: Use `partialmethod` to create bound methods:
  ```python
  def _action_impl(self, task, target, action_type): ...
  add_tag = partialmethod(_action_impl, action_type=ActionType.ADD_TAG)
  ```
- **Pros**:
  - Built-in Python tool
  - Simple implementation
- **Cons**:
  - Cannot handle different signatures (NO_TARGET vs POSITIONING)
  - Loss of docstring
  - Type hints don't propagate
- **Why not chosen**: Different method signatures require different implementations. partialmethod can't handle this.

### Alternative 5: Keep Methods, Reduce Boilerplate Only

- **Description**: Extract common operations to helpers:
  ```python
  def add_tag(self, task, tag):
      return self._register_action(task, tag, ActionType.ADD_TAG, "tag_gid")
  ```
- **Pros**:
  - Minimal pattern change
  - Explicit method definitions
- **Cons**:
  - Still 18 method definitions (~40 lines each with docstrings)
  - Only ~50% line reduction
  - Doesn't meet 82% PRD target
- **Why not chosen**: Does not achieve line reduction goal. We need method generation, not just helper extraction.

## Consequences

### Positive

- **920 -> ~150 lines**: 83% reduction in action method code
- **Single source of truth**: ACTION_REGISTRY defines all action behavior
- **Consistent behavior**: All generated methods follow same pattern
- **Easy to extend**: Adding action = registry entry + one-line declaration
- **Preserved API**: All public signatures unchanged
- **IDE support**: `help()` and type hints work correctly

### Negative

- **Learning curve**: Descriptor pattern may be unfamiliar
- **Debug complexity**: Stack traces include descriptor machinery
- **5 explicit methods**: Some methods still manual (cannot unify all 18)
- **Runtime cost**: Per-call method generation (likely negligible)

### Neutral

- **New module**: `persistence/actions.py` (~150 lines) added
- **Test changes**: ActionBuilder needs dedicated tests
- **Documentation**: Pattern must be documented for contributors

## Compliance

How do we ensure this decision is followed?

1. **New action methods**: Must use ActionBuilder unless custom logic required
2. **Registry completeness**: Test validates all ActionType values have registry entries
3. **Signature tests**: Compare `inspect.signature()` before/after
4. **Performance gate**: Benchmark must show <5% regression

## Implementation Checklist

- [ ] Create `persistence/actions.py` with ActionBuilder
- [ ] Define ACTION_REGISTRY with 13 configurations
- [ ] Replace 13 methods in SaveSession with ActionBuilder declarations
- [ ] Keep 5 methods with custom logic explicit
- [ ] Add `test_action_builder.py` with signature verification
- [ ] Run benchmarks to verify performance
- [ ] Update docstrings in ACTION_REGISTRY

## Example: Adding a New Action Method

Future developers adding a new action (e.g., `add_attachment`) would:

1. Add ActionType enum value in `models.py`:
   ```python
   class ActionType(str, Enum):
       ADD_ATTACHMENT = "add_attachment"
   ```

2. Add registry entry in `actions.py`:
   ```python
   ACTION_REGISTRY["add_attachment"] = ActionConfig(
       action_type=ActionType.ADD_ATTACHMENT,
       variant=ActionVariant.TARGET_REQUIRED,
       target_param="attachment",
       log_event="session_add_attachment",
       docstring="Add an attachment to a task...",
   )
   ```

3. Add declaration in `session.py`:
   ```python
   add_attachment = ActionBuilder("add_attachment")
   ```

4. Add tests in `test_session.py` and `test_action_builder.py`

Total: ~10 lines of code vs. ~50 lines for manual method.
