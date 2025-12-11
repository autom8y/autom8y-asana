# Best Practices & Patterns

Recommended patterns for using the autom8_asana SDK effectively.

---

## Relationship Fields

Tags, projects, followers, and dependencies are managed through action methods.

### The Pattern

```python
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async with AsanaClient() as client:
    task = await client.tasks.get_async("task_gid")

    async with SaveSession(client) as session:
        # Use action methods for relationships
        session.add_tag(task, "tag_gid")
        session.add_to_project(task, "project_gid")
        session.add_follower(task, "user_gid")
        session.add_dependency(task, "other_task_gid")

        await session.commit_async()
```

### Why Action Methods?

Asana's API requires dedicated endpoints for relationship changes. These fields cannot be modified through the standard task update endpoint:

| Field | Add Method | Remove Method |
|-------|-----------|---------------|
| `tags` | `session.add_tag(task, tag)` | `session.remove_tag(task, tag)` |
| `projects` | `session.add_to_project(task, project)` | `session.remove_from_project(task, project)` |
| `followers` | `session.add_follower(task, user)` | `session.remove_follower(task, user)` |
| `dependencies` | `session.add_dependency(task, other)` | `session.remove_dependency(task, other)` |
| `memberships` | `session.add_to_project()` | `session.remove_from_project()` |

The SDK enforces this at commit time to prevent silent failures.

### Common Mistake

Attempting to modify these fields directly raises `UnsupportedOperationError`:

```python
# This will fail at commit time
task.tags = [tag1, tag2]           # Raises UnsupportedOperationError
task.tags.append(tag)              # Raises UnsupportedOperationError
task.projects = [project]          # Raises UnsupportedOperationError
task.followers.append(user)        # Raises UnsupportedOperationError
```

---

## Change Tracking

Always track entities before modifying them.

### The Pattern

```python
async with SaveSession(client) as session:
    # 1. Track first - captures a snapshot
    session.track(task)

    # 2. Then modify - changes are detected against the snapshot
    task.name = "Updated Name"
    task.notes = "New notes"

    # 3. Commit - only changed fields are sent to API
    await session.commit_async()
```

### Why Track First?

SaveSession uses snapshot-based change detection. When you call `track()`, it captures the entity's current state. At commit time, it compares the current state against the snapshot and sends only the changed fields.

### Common Mistake

Modifying before tracking results in silent no-ops:

```python
# Changes silently discarded - no error, but nothing saved
task.name = "New Name"
session.track(task)  # Snapshot captured AFTER modification
await session.commit_async()  # No changes detected!

# Correct order
session.track(task)  # Snapshot captured BEFORE modification
task.name = "New Name"
await session.commit_async()  # Change detected and saved
```

---

## Session Lifecycle

Use context managers and commit before exiting.

### The Pattern

```python
async with SaveSession(client) as session:
    # Session is OPEN
    session.track(task)
    task.name = "Updated"

    await session.commit_async()
    # Session is COMMITTED (can still use it)

    session.track(another_task)
    await session.commit_async()  # Second commit works

# Session is CLOSED after exiting context
```

### Session States

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| **OPEN** | Inside context manager, before commit | track, modify, action methods, commit |
| **COMMITTED** | After commit, still inside context | track, modify, action methods, commit again |
| **CLOSED** | After exiting context manager | None - all operations raise `SessionClosedError` |

### Important Notes

- **No auto-commit**: Uncommitted changes are discarded when exiting the context
- **Multiple commits allowed**: You can commit multiple times within one session
- **Sessions are not reusable**: Once closed, create a new session

### Common Mistake

Using a session after it's closed:

```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    # Forgot to commit!

# Session closed, changes discarded silently

session.track(another_task)  # Raises SessionClosedError
```

---

## Positioning Operations

Use `insert_before` OR `insert_after`, never both.

### The Pattern

```python
async with SaveSession(client) as session:
    # Position before another task
    session.add_to_project(task, project, insert_before="other_task_gid")

    # OR position after another task
    session.move_to_section(task, section, insert_after="reference_task_gid")

    await session.commit_async()
```

### Available Positioning Parameters

| Method | Supports Positioning |
|--------|---------------------|
| `add_to_project()` | `insert_before`, `insert_after` |
| `move_to_section()` | `insert_before`, `insert_after` |
| `set_parent()` | `insert_before`, `insert_after` (among siblings) |
| `reorder_subtask()` | `insert_before`, `insert_after` |

### Common Mistake

Specifying both positioning parameters raises `PositioningConflictError`:

```python
# This fails immediately
session.add_to_project(
    task,
    project,
    insert_before="task_a",
    insert_after="task_b"  # Cannot specify both!
)
# Raises: PositioningConflictError
```

---

## Partial Failure Handling

Always check results for partial failures.

### The Pattern

```python
result = await session.commit_async()

if result.success:
    print(f"All {len(result.succeeded)} operations succeeded")
elif result.partial:
    print(f"Partial success: {len(result.succeeded)} ok, {len(result.failed)} failed")
    for error in result.failed:
        print(f"  {error.entity.gid}: {error.error}")
else:
    print("All operations failed")
```

### Why Check Partial?

When batching multiple operations, some may succeed while others fail. Checking only `result.success` misses partial failures:

```python
# Incomplete check - misses partial failures
if result.success:
    print("All saved!")
# What if 3 succeeded and 2 failed? This would print nothing.

# Complete check
if result.success:
    print("All saved!")
elif result.partial:
    handle_partial_failure(result)
else:
    handle_total_failure(result)
```

### Alternative: Raise on Any Failure

```python
from autom8_asana.persistence.exceptions import PartialSaveError

result = await session.commit_async()

try:
    result.raise_on_failure()
except PartialSaveError as e:
    print(f"Failed operations: {len(e.result.failed)}")
```

---

## Dependency Cycles

Dependencies must form a DAG (directed acyclic graph).

### The Pattern

```python
async with SaveSession(client) as session:
    # Linear chain: A -> B -> C (A depends on B, B depends on C)
    session.add_dependency(task_a, task_b)
    session.add_dependency(task_b, task_c)

    await session.commit_async()
```

### Why No Cycles?

Task dependencies represent "must complete before" relationships. A cycle means "A must complete before B, and B must complete before A" - which is impossible.

### Common Mistake

Creating circular dependencies raises `CyclicDependencyError`:

```python
# This creates a cycle: A -> B -> A
session.add_dependency(task_a, task_b)  # A depends on B
session.add_dependency(task_b, task_a)  # B depends on A (CYCLE!)
await session.commit_async()  # Raises CyclicDependencyError
```

---

## Parameter Types

Action methods accept both entity objects and GID strings.

### The Pattern

```python
async with SaveSession(client) as session:
    # Both work - entity objects
    session.add_tag(task, tag_object)
    session.add_to_project(task, project_object)

    # Both work - GID strings
    session.add_tag(task, "1234567890")
    session.add_to_project(task, "9876543210")

    # Mixing is fine too
    session.add_tag(task_object, "tag_gid")

    await session.commit_async()
```

### Why Both?

Flexibility. Sometimes you have entity objects from previous queries; sometimes you only have GIDs. The SDK accepts both, normalizing to GIDs internally.

---

## Comment Validation

Comments require non-empty content.

### The Pattern

```python
async with SaveSession(client) as session:
    # Plain text
    session.add_comment(task, "This is a comment")

    # Rich HTML with fallback
    session.add_comment(
        task,
        "Fallback text",
        html_text="<body><strong>Rich</strong> content</body>"
    )

    await session.commit_async()
```

### Common Mistake

Empty comments raise `ValueError`:

```python
# Fails immediately
session.add_comment(task, "")  # Raises ValueError

# Also fails - both empty
session.add_comment(task, "", html_text="")  # Raises ValueError
```

---

## Thread Safety

Share clients, not sessions.

### The Pattern

```python
# Safe: share client across threads
client = AsanaClient()

def worker(task_gid):
    # Each thread creates its own session
    with SaveSession(client) as session:
        task = client.tasks.get(task_gid)
        session.track(task)
        task.name = "Updated"
        session.commit()
```

### Thread Safety Summary

| Component | Thread-Safe? | Notes |
|-----------|-------------|-------|
| `AsanaClient` | Yes | Safe to share across threads |
| `SaveSession` | No | Use one session per thread |
| Rate Limiter | Yes | Uses internal locking |

---

## Reference: Rate Limiting

The SDK implements automatic rate limiting.

| Parameter | Value |
|-----------|-------|
| Rate Limit | 1500 requests per 60 seconds |
| Algorithm | Token bucket |
| Wait Behavior | Automatic (SDK waits when limit approached) |

You do not need to implement rate limiting in your code.

---

## Reference: Retry Behavior

The SDK automatically retries transient failures.

| Parameter | Default Value |
|-----------|---------------|
| Max Retries | 3 |
| Base Delay | 0.1 seconds |
| Max Delay | 60 seconds |
| Backoff | Exponential (2x per retry) |
| Jitter | Enabled (0.5x to 1.5x random factor) |
| Retryable Status Codes | 429, 503, 504 |

For 429 (rate limited) responses, the SDK respects `Retry-After` headers.

---

## Reference: Exception Hierarchy

All SDK exceptions inherit from a base class:

```
AsanaError (base)
    |
    +-- SaveOrchestrationError (base for save errors)
    |       |
    |       +-- SessionClosedError
    |       +-- CyclicDependencyError
    |       +-- DependencyResolutionError
    |       +-- PartialSaveError
    |       +-- UnsupportedOperationError
    |       +-- PositioningConflictError
    |
    +-- NotFoundError
    +-- AuthenticationError
    +-- RateLimitError
    +-- ValidationError
    +-- ConfigurationError
```

### Catching by Category

```python
from autom8_asana.exceptions import AsanaError
from autom8_asana.persistence.exceptions import SaveOrchestrationError

try:
    await session.commit_async()
except SaveOrchestrationError as e:
    # Catches all save-related errors
    print(f"Save failed: {e}")
except AsanaError as e:
    # Catches all SDK errors
    print(f"SDK error: {e}")
```

---

## What's Next?

- **[Common Workflows](workflows.md)**: Copy-paste recipes for typical operations
- **[SaveSession Guide](save-session.md)**: Deep dive into SaveSession features
- **[SDK Adoption Guide](sdk-adoption.md)**: Migrating from other Asana libraries
