# SaveSession Guide

SaveSession implements the Unit of Work pattern for batched Asana operations. It collects changes to multiple entities and saves them in optimized batches with dependency ordering.

## Overview

SaveSession provides:
- **Deferred saves**: Changes are collected and executed together at commit time
- **Dependency ordering**: Parent entities are saved before children automatically
- **Batch optimization**: Multiple operations are grouped into efficient API batches
- **Change tracking**: Only modified fields are sent to the API
- **Action methods**: Safe way to modify relationships (tags, projects, etc.)

---

## Basic Workflow

1. Create a session with `async with SaveSession(client)`
2. Track entities with `session.track(entity)`
3. Make modifications to tracked entities
4. Commit changes with `result = await session.commit_async()`

### Basic Example

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def update_tasks():
    async with AsanaClient() as client:
        # Fetch tasks
        task1 = await client.tasks.get_async("task_gid_1")
        task2 = await client.tasks.get_async("task_gid_2")

        async with SaveSession(client) as session:
            # Track entities for change detection
            session.track(task1)
            session.track(task2)

            # Make modifications
            task1.name = "Updated Task 1"
            task1.notes = "New notes for task 1"
            task2.completed = True

            # Commit all changes in optimized batches
            result = await session.commit_async()

            if result.success:
                print(f"Saved {len(result.succeeded)} entities")
            else:
                print(f"Failed: {len(result.failed)} errors")

asyncio.run(update_tasks())
```

---

## Complete Example with Actions

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
from autom8_asana.models import Task

async def comprehensive_example():
    async with AsanaClient() as client:
        # Get resources
        task = await client.tasks.get_async("task_gid")
        tag = await client.tags.get_async("tag_gid")
        project = await client.projects.get_async("project_gid")
        section = await client.sections.get_async("section_gid")

        async with SaveSession(client) as session:
            # Track the task for field modifications
            session.track(task)

            # Modify direct fields (will be batched)
            task.name = "Important Task"
            task.notes = "Updated via SDK"
            task.due_on = "2024-12-31"

            # Queue action operations (executed after field updates)
            session.add_tag(task, tag)
            session.add_to_project(task, project)
            session.move_to_section(task, section)
            session.add_comment(task, "Automated update from SDK")

            # Commit everything
            result = await session.commit_async()

            # Handle result
            if result.success:
                print("All operations completed successfully")
            elif result.partial:
                print(f"Partial success: {len(result.succeeded)} ok, {len(result.failed)} failed")
                for error in result.failed:
                    print(f"  Error: {error.error}")
            else:
                print("All operations failed")

asyncio.run(comprehensive_example())
```

---

## Action Methods Reference

Action methods modify relationships that cannot be changed via direct field assignment. They return `self` for fluent chaining.

### Tags

```python
# Add a tag to a task
session.add_tag(task, tag)
session.add_tag(task, "tag_gid")  # GID string also works

# Remove a tag from a task
session.remove_tag(task, tag)
```

### Projects

```python
# Add task to a project (at end)
session.add_to_project(task, project)

# Add with positioning
session.add_to_project(task, project, insert_before="other_task_gid")
session.add_to_project(task, project, insert_after="other_task_gid")

# Remove task from project
session.remove_from_project(task, project)
```

### Sections

```python
# Move task to a section (at end)
session.move_to_section(task, section)

# Move with positioning
session.move_to_section(task, section, insert_before="other_task_gid")
session.move_to_section(task, section, insert_after="other_task_gid")
```

### Dependencies

```python
# Make task dependent on another (task cannot complete until depends_on completes)
session.add_dependency(task, depends_on_task)

# Remove dependency
session.remove_dependency(task, depends_on_task)

# Inverse: make dependent_task wait for task
session.add_dependent(task, dependent_task)

# Remove dependent
session.remove_dependent(task, dependent_task)
```

### Followers

```python
# Add a single follower
session.add_follower(task, user)
session.add_follower(task, "user_gid")

# Remove a follower
session.remove_follower(task, user)

# Add multiple followers
session.add_followers(task, [user1, user2, "user3_gid"])

# Remove multiple followers
session.remove_followers(task, [user1, user2])
```

### Parent and Subtasks

```python
# Convert a task to a subtask
session.set_parent(task, parent_task)

# With positioning among siblings
session.set_parent(task, parent_task, insert_before=sibling_task)
session.set_parent(task, parent_task, insert_after=sibling_task)

# Promote subtask to top-level task
session.set_parent(task, None)

# Reorder a subtask within its parent
session.reorder_subtask(subtask, insert_after=other_subtask)
```

### Other Actions

```python
# Like a task (as authenticated user)
session.add_like(task)

# Unlike a task
session.remove_like(task)

# Add a comment (story)
session.add_comment(task, "Plain text comment")

# Add a rich HTML comment
session.add_comment(
    task,
    "Fallback plain text",
    html_text="<body><strong>Rich</strong> HTML content</body>"
)
```

---

## Fluent Chaining

Action methods return `self` for chaining:

```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"

    # Chain multiple actions
    (session
        .add_tag(task, tag1)
        .add_tag(task, tag2)
        .add_to_project(task, project)
        .move_to_section(task, section)
        .add_follower(task, user)
        .add_comment(task, "Setup complete"))

    await session.commit_async()
```

---

## Event Hooks

Register callbacks for save lifecycle events using decorators.

### on_pre_save

Called before each entity is saved. Can raise exceptions to abort the save.

```python
async with SaveSession(client) as session:
    @session.on_pre_save
    def validate(entity, operation):
        from autom8_asana.persistence.models import OperationType
        if operation == OperationType.CREATE and not entity.name:
            raise ValueError("Task must have a name")

    session.track(new_task)
    await session.commit_async()  # Raises ValueError if validation fails
```

### on_post_save

Called after each entity is successfully saved. Cannot abort (save already happened).

```python
async with SaveSession(client) as session:
    @session.on_post_save
    async def notify(entity, operation, response_data):
        print(f"Saved {entity.gid}: {operation.value}")
        await send_webhook_notification(entity.gid)

    session.track(task)
    await session.commit_async()
```

### on_error

Called when an entity save fails. For logging/notification only.

```python
async with SaveSession(client) as session:
    @session.on_error
    def log_error(entity, operation, exception):
        print(f"Failed to {operation.value} {entity.gid}: {exception}")

    session.track(task)
    await session.commit_async()
```

---

## Inspecting Changes

### get_changes()

Returns field-level changes for a tracked entity:

```python
session.track(task)
task.name = "New Name"
task.notes = "New Notes"

changes = session.get_changes(task)
# {"name": ("Old Name", "New Name"), "notes": (None, "New Notes")}

for field, (old, new) in changes.items():
    print(f"{field}: '{old}' -> '{new}'")
```

### get_state()

Returns the lifecycle state of a tracked entity:

```python
from autom8_asana.persistence.models import EntityState

session.track(task)
state = session.get_state(task)  # EntityState.CLEAN

task.name = "Modified"
state = session.get_state(task)  # EntityState.MODIFIED

session.delete(task)
state = session.get_state(task)  # EntityState.DELETED
```

States:
- `NEW`: Entity has a temp GID, will be created
- `CLEAN`: Entity is tracked but unchanged
- `MODIFIED`: Entity has pending changes
- `DELETED`: Entity is marked for deletion

### preview()

Preview planned operations without executing:

```python
session.track(task)
task.name = "Updated"
session.add_tag(task, tag)

crud_ops, action_ops = session.preview()

print("CRUD Operations:")
for op in crud_ops:
    print(f"  {op.operation.value} {op.entity.gid} at level {op.dependency_level}")

print("Action Operations:")
for action in action_ops:
    print(f"  {action.action.value} on {action.task.gid}")
```

### get_dependency_order()

See how entities will be saved by dependency level:

```python
session.track(parent_task)
session.track(subtask)  # subtask.parent = parent_task

levels = session.get_dependency_order()
# [[parent_task], [subtask]]
# Parent at level 0, subtask at level 1

for level_idx, entities in enumerate(levels):
    print(f"Level {level_idx}: {[e.gid for e in entities]}")
```

---

## SaveResult Handling

`commit_async()` returns a `SaveResult` object:

```python
result = await session.commit_async()

# Check overall status
if result.success:
    print("All operations succeeded")
elif result.partial:
    print("Some operations succeeded, some failed")
else:
    print("All operations failed")

# Access succeeded entities
for entity in result.succeeded:
    print(f"Saved: {entity.gid}")

# Access failed operations
for error in result.failed:
    print(f"Failed: {error.entity.gid}")
    print(f"  Operation: {error.operation.value}")
    print(f"  Error: {error.error}")
    print(f"  Payload: {error.payload}")

# Get counts
print(f"Total: {result.total_count}")
print(f"Succeeded: {len(result.succeeded)}")
print(f"Failed: {len(result.failed)}")

# Raise exception if any failures
try:
    result.raise_on_failure()
except PartialSaveError as e:
    print(f"Partial save failed: {e.result.failed}")
```

---

## Best Practices

### 1. Always Use Context Managers

```python
# CORRECT
async with SaveSession(client) as session:
    # operations
    await session.commit_async()

# WRONG - manual management risks resource leaks
session = SaveSession(client)
# forgot to close...
```

### 2. Track Before Modifying

```python
# CORRECT
session.track(task)
task.name = "New Name"

# WRONG - changes not tracked, silently discarded
task.name = "New Name"
session.track(task)  # Too late, snapshot captured here
```

### 3. Check Results for Partial Failures

```python
result = await session.commit_async()

# Don't assume success
if not result.success:
    if result.partial:
        # Handle partial failure
        handle_failures(result.failed)
    else:
        # Total failure
        raise Exception("All saves failed")
```

### 4. Use Action Methods for Relationships

```python
# CORRECT - use action methods
session.add_tag(task, tag)
session.add_to_project(task, project)

# WRONG - direct modification raises UnsupportedOperationError
task.tags.append(tag)
task.projects = [project]
```

### 5. Commit Before Exiting Context

```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    await session.commit_async()  # Don't forget!

# If you exit without commit, changes are discarded
```

---

## Sync API

For non-async codebases, use the sync wrappers:

```python
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

with AsanaClient() as client:
    task = client.tasks.get("task_gid")

    with SaveSession(client) as session:
        session.track(task)
        task.name = "Updated"
        result = session.commit()  # Note: no await, no _async suffix

        if result.success:
            print("Saved!")
```

Note: Sync wrappers cannot be called from an async context. Doing so raises `SyncInAsyncContextError`.
