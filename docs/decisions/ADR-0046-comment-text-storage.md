# ADR-0046: Comment Text Storage Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0007 (FR-CMT-001 through FR-CMT-009), TDD-0012, ADR-0044 (extra_params Field), ADR-0035 (Unit of Work)

## Context

PRD-0007 requires adding `session.add_comment(task, text, *, html_text=None)` to the SaveSession API. Per the Unit of Work pattern (ADR-0035), comments must use deferred execution - they are queued when `add_comment()` is called but not created until `commit()`.

This creates a storage requirement: the comment text and optional html_text must be persisted somewhere between queue time and execution time.

The Asana API for creating comments:

```
POST /tasks/{task_gid}/stories
Body: {
    "data": {
        "text": "Plain text comment",
        "html_text": "<body>Rich text comment</body>"  // Optional
    }
}
```

### Forces at Play

1. **Deferred execution**: Comment text must survive from queue to commit
2. **Immutable ActionOperation**: The dataclass is frozen; text storage must work within this constraint
3. **Consistency with ADR-0044**: We've established extra_params for action-specific data
4. **Simplicity**: Avoid creating new types for what is essentially string storage
5. **API payload generation**: `to_api_call()` must access text to build request body
6. **Type safety**: Would prefer typed fields, but must balance against complexity

## Decision

Store comment text and html_text in the `extra_params` field of ActionOperation, consistent with the pattern established in ADR-0044.

```python
# In SaveSession.add_comment()
def add_comment(
    self,
    task: Task | str,
    text: str,
    *,
    html_text: str | None = None,
) -> SaveSession:
    """Add a comment to a task with deferred execution."""
    self._ensure_open()

    if not text and not html_text:
        raise ValueError("Comment must have text or html_text")

    task_entity = self._resolve_task(task)
    action = ActionOperation(
        task=task_entity,
        action=ActionType.ADD_COMMENT,
        target_gid=task_entity.gid,  # Task GID for reference
        extra_params={"text": text, "html_text": html_text},  # Comment storage
    )
    self._pending_actions.append(action)
    return self
```

### Payload Generation in to_api_call()

```python
def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
    task_gid = self.task.gid if hasattr(self.task, 'gid') else str(self.task)

    match self.action:
        case ActionType.ADD_COMMENT:
            comment_data: dict[str, Any] = {}
            if self.extra_params.get("text"):
                comment_data["text"] = self.extra_params["text"]
            if self.extra_params.get("html_text"):
                comment_data["html_text"] = self.extra_params["html_text"]
            return ("POST", f"/tasks/{task_gid}/stories", {"data": comment_data})
```

### Validation at Queue Time

```python
# In add_comment(), before creating ActionOperation:
if not text and not html_text:
    raise ValueError("Comment must have text or html_text")
```

This ensures empty comments are rejected immediately (fail-fast), not at commit time.

## Rationale

### Why extra_params Over Separate CommentOperation Class?

A dedicated class would provide stronger typing:

```python
@dataclass(frozen=True)
class CommentOperation:
    task: AsanaResource
    text: str
    html_text: str | None = None

    def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
        ...
```

However:

1. **Type proliferation**: Adds another class to the action operation family
2. **Collection complexity**: `_pending_actions: list[ActionOperation | CommentOperation]`
3. **Inconsistent with ADR-0044**: We've already decided extra_params handles action-specific data
4. **Execution path unchanged**: ActionExecutor processes all actions the same way; only payload differs
5. **Minimal type safety gain**: `text` is already validated at queue time

### Why extra_params Over Direct Fields on ActionOperation?

Adding `text` and `html_text` fields directly:

```python
@dataclass(frozen=True)
class ActionOperation:
    text: str | None = None        # Only for ADD_COMMENT
    html_text: str | None = None   # Only for ADD_COMMENT
```

Problems:

1. **Irrelevant fields**: 13 of 14 action types would ignore these fields
2. **Field explosion**: Each new action type with unique data adds fields
3. **Confusing API**: `ActionOperation(action=ActionType.ADD_TAG, text="???")`
4. **ADR-0044 violation**: We chose extra_params specifically to avoid this pattern

### Why Store html_text Even When None?

```python
extra_params={"text": text, "html_text": html_text}  # html_text may be None
```

Benefits:

1. **Consistent key presence**: `to_api_call()` can always check both keys
2. **Explicit optionality**: `None` vs. missing key both work, but None is explicit
3. **Debugging**: All comment data visible in extra_params inspection
4. **Simplicity**: One code path, not conditional key insertion

Alternative (only include if present):

```python
extra_params = {"text": text}
if html_text:
    extra_params["html_text"] = html_text
```

This works but adds conditional logic without benefit.

### Why Validate at Queue Time?

Per FR-CMT-008, empty comments should raise an error during queuing:

```python
if not text and not html_text:
    raise ValueError("Comment must have text or html_text")
```

Benefits:

1. **Fail-fast**: Developer sees error immediately, not at commit
2. **Clear attribution**: Error traceback points to `add_comment()` call
3. **No wasted operations**: Empty comment doesn't consume an action slot
4. **Consistent with ADR-0047**: Positioning validation also happens at queue time

## Alternatives Considered

### Alternative 1: CommentOperation Dataclass

**Description**: Create a separate `CommentOperation` dataclass with `text` and `html_text` fields.

**Pros**:
- Strong typing for comment fields
- Self-documenting structure
- IDE autocomplete for text/html_text

**Cons**:
- New type to maintain
- Union types in `_pending_actions`
- Inconsistent with extra_params pattern (ADR-0044)
- More code for marginal type safety benefit

**Why not chosen**: ADR-0044 established extra_params as the mechanism for action-specific data. Creating a special case for comments breaks this pattern.

### Alternative 2: Store Text in target_gid

**Description**: Repurpose target_gid as text storage for comments (it's not a GID for comments anyway).

```python
action = ActionOperation(
    task=task_entity,
    action=ActionType.ADD_COMMENT,
    target_gid=text,  # Abuse: store comment text here
)
```

**Pros**:
- No new fields needed
- Existing structure works

**Cons**:
- Semantic confusion: target_gid should be a GID, not arbitrary text
- Can't store both text and html_text
- Breaks naming convention
- Confuses maintainers

**Why not chosen**: Abuses the type system and field semantics. target_gid should contain GIDs.

### Alternative 3: Separate Comment Queue

**Description**: Store comments in a separate `_pending_comments` list.

```python
class SaveSession:
    _pending_actions: list[ActionOperation]
    _pending_comments: list[tuple[AsanaResource, str, str | None]]
```

**Pros**:
- Clear separation of concerns
- No extra_params needed for comments

**Cons**:
- Two queues to manage
- Execution order complexity (when do comments execute?)
- Violates unified action model
- More code paths to test

**Why not chosen**: Comments are actions - they should follow the same queuing and execution pattern as other actions.

### Alternative 4: JSON String in extra_params

**Description**: Store comment text as JSON-serialized string.

```python
extra_params={"comment_json": '{"text": "...", "html_text": "..."}'}
```

**Pros**:
- Single key in extra_params
- Easily extensible

**Cons**:
- Unnecessary serialization overhead
- Harder to inspect during debugging
- Requires json.loads() in to_api_call()
- Over-engineering for simple key-value storage

**Why not chosen**: Comment text is already strings. Wrapping strings in JSON is pointless complexity.

## Consequences

### Positive

1. **Consistent with ADR-0044**: Comment storage follows established extra_params pattern
2. **Simple implementation**: Dict key-value storage, no new types
3. **Unified execution**: Comments flow through ActionExecutor like all other actions
4. **Clear API**: `add_comment(task, text, html_text=...)` is intuitive
5. **Fail-fast validation**: Empty comments rejected immediately

### Negative

1. **No static typing for text fields**: extra_params["text"] is Any, not str
2. **Documentation burden**: Must document that ADD_COMMENT uses text/html_text keys
3. **Typo risk**: `extra_params["txt"]` silently fails (mitigated by tests)

### Neutral

1. **to_api_call() handles extraction**: Each action type's case documents expected keys
2. **html_text is optional in Asana API**: SDK mirrors this with optional parameter
3. **Comment order preserved**: FIFO queue order, comments appear in creation order

## Compliance

### Enforcement

- **SaveSession.add_comment()**: Always stores text and html_text in extra_params
- **Unit tests**: Verify extra_params contains expected keys after add_comment()
- **Unit tests**: Verify to_api_call() generates correct payload
- **Integration tests**: Verify comments appear on tasks after commit

### Documentation

- SaveSession.add_comment() docstring explains deferred execution
- ActionOperation docstring lists comment storage pattern
- TDD-0012 specifies the extra_params keys for ADD_COMMENT
