# Common Workflows

Recipes for typical autom8_asana operations. All examples are copy-paste ready.

**Prerequisites**: Understand [Core Concepts](concepts.md) first.

---

## Recipe 1: Update Multiple Tasks in Batch

### When to use
Modify several tasks at once without making individual API calls for each.

### The Pattern

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def batch_update():
    async with AsanaClient() as client:
        # Fetch tasks to update
        task1 = await client.tasks.get_async("task_gid_1")
        task2 = await client.tasks.get_async("task_gid_2")
        task3 = await client.tasks.get_async("task_gid_3")

        async with SaveSession(client) as session:
            # Track all entities before modifying
            session.track(task1)
            session.track(task2)
            session.track(task3)

            # Make modifications
            task1.name = "Updated Task 1"
            task1.notes = "New notes"
            task2.completed = True
            task3.due_on = "2024-12-31"

            # Single commit for all changes
            result = await session.commit_async()
            print(f"Updated {len(result.succeeded)} tasks")

asyncio.run(batch_update())
```

### Why this works
SaveSession collects all tracked entity modifications and sends them in optimized batches. Three tasks with changes become a single batched API operation instead of three separate calls.

### See Also
- [SaveSession Guide](save-session.md) for commit options
- [Recipe 5: Handle Partial Failures](#recipe-5-handle-partial-failures) for error handling

---

## Recipe 2: Add Tags to Tasks

### When to use
Attach one or more tags to tasks. Tags require action methods - direct assignment does not work.

### The Pattern

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def add_tags():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            # Use action methods for tags - NOT direct assignment
            session.add_tag(task, "tag_gid_1")
            session.add_tag(task, "tag_gid_2")

            # Can also pass Tag objects instead of GID strings
            # tag = await client.tags.get_async("tag_gid")
            # session.add_tag(task, tag)

            await session.commit_async()
            print("Tags added successfully")

asyncio.run(add_tags())
```

### Why this works
Asana's API requires dedicated endpoints for tag operations. The SDK enforces this with action methods. Attempting `task.tags = [...]` or `task.tags.append(...)` raises `UnsupportedOperationError` at commit time.

### See Also
- [Best Practices: Relationship Fields](patterns.md#relationship-fields) for why action methods are required
- [SaveSession Action Methods](save-session.md#action-methods-reference) for full reference

---

## Recipe 3: Create Task with Parent (Subtask)

### When to use
Create a new subtask under an existing parent task.

### The Pattern

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
from autom8_asana.models import Task

async def create_subtask():
    async with AsanaClient() as client:
        # Get the parent task
        parent_task = await client.tasks.get_async("parent_task_gid")

        async with SaveSession(client) as session:
            # Create the new subtask
            subtask = Task(name="Subtask Name", notes="Subtask details")
            session.track(subtask)

            # Set parent-child relationship
            session.set_parent(subtask, parent_task)

            # Commit - dependency ordering ensures parent exists first
            result = await session.commit_async()
            print(f"Created subtask with GID: {subtask.gid}")

asyncio.run(create_subtask())
```

### Why this works
SaveSession automatically orders operations by dependency. Even when creating both parent and child in the same commit, the parent is saved first. The `set_parent()` action method handles the Asana API's parent assignment endpoint.

### See Also
- [SaveSession: Parent and Subtasks](save-session.md#parent-and-subtasks) for positioning options
- [Recipe 8: Create Task with Dependencies](#recipe-8-create-task-with-dependencies) for task dependencies

---

## Recipe 4: Move Task to Section

### When to use
Move a task to a specific section within a project, optionally with positioning.

### The Pattern

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def move_to_section():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            # Move to section (at end by default)
            session.move_to_section(task, "section_gid")

            await session.commit_async()
            print("Task moved to section")

asyncio.run(move_to_section())

# With positioning
async def move_with_position():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            # Move before a specific task
            session.move_to_section(
                task,
                "section_gid",
                insert_before="other_task_gid"
            )
            # OR move after a specific task
            # session.move_to_section(
            #     task,
            #     "section_gid",
            #     insert_after="other_task_gid"
            # )

            await session.commit_async()

asyncio.run(move_with_position())
```

### Why this works
Section placement uses Asana's dedicated endpoint for moving tasks within projects. The `insert_before` and `insert_after` parameters map directly to Asana's positioning API.

**Important**: Do not specify both `insert_before` and `insert_after` - this raises `PositioningConflictError`.

### See Also
- [Best Practices: Positioning Operations](patterns.md#positioning-operations) for positioning rules
- [SaveSession: Sections](save-session.md#sections) for full method signature

---

## Recipe 5: Handle Partial Failures

### When to use
When some operations might fail while others succeed, and you need to handle each case.

### The Pattern

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
from autom8_asana.persistence.exceptions import PartialSaveError

async def handle_partial_failures():
    async with AsanaClient() as client:
        tasks = [
            await client.tasks.get_async(gid)
            for gid in ["gid_1", "gid_2", "gid_3"]
        ]

        async with SaveSession(client) as session:
            for task in tasks:
                session.track(task)
                task.name = f"Updated: {task.name}"

            result = await session.commit_async()

            # Check result status
            if result.success:
                print(f"All {len(result.succeeded)} tasks updated")
            elif result.partial:
                print(f"Partial success: {len(result.succeeded)} ok, {len(result.failed)} failed")

                # Handle succeeded
                for entity in result.succeeded:
                    print(f"  OK: {entity.gid}")

                # Handle failures with details
                for error in result.failed:
                    print(f"  FAILED: {error.entity.gid}")
                    print(f"    Operation: {error.operation.value}")
                    print(f"    Error: {error.error}")
            else:
                print("All operations failed")

asyncio.run(handle_partial_failures())

# Alternative: Raise on any failure
async def raise_on_failure():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            session.track(task)
            task.name = "Updated"

            result = await session.commit_async()

            try:
                result.raise_on_failure()
                print("All operations succeeded")
            except PartialSaveError as e:
                print(f"Some operations failed: {len(e.result.failed)}")
                for error in e.result.failed:
                    print(f"  {error.entity.gid}: {error.error}")

asyncio.run(raise_on_failure())
```

### Why this works
SaveResult provides three status properties: `success` (all worked), `partial` (some worked), and neither (all failed). The `failed` list contains detailed error information for each failed operation. Call `raise_on_failure()` to convert any failure into an exception.

### See Also
- [SaveSession: SaveResult Handling](save-session.md#saveresult-handling) for result properties
- [Best Practices: Partial Failure Handling](patterns.md#partial-failure-handling) for best practices

---

## Recipe 6: Add Comments to Tasks

### When to use
Add a comment (story) to a task, with optional rich HTML formatting.

### The Pattern

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def add_comments():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            # Plain text comment
            session.add_comment(task, "This is a plain text comment")

            # Rich HTML comment with fallback text
            session.add_comment(
                task,
                "Fallback text for email notifications",
                html_text="<body><strong>Bold</strong> and <em>italic</em> text</body>"
            )

            await session.commit_async()
            print("Comments added")

asyncio.run(add_comments())
```

### Why this works
Comments are added via Asana's stories endpoint. The `add_comment()` action method queues the story creation for execution at commit time. The `html_text` parameter enables rich formatting.

**Important**: At least one of `text` or `html_text` must be non-empty. Empty comments raise `ValueError`.

### See Also
- [SaveSession: Other Actions](save-session.md#other-actions) for comment options
- [Best Practices](patterns.md) for comment validation rules

---

## Recipe 7: Manage Followers

### When to use
Add or remove followers from tasks, individually or in bulk.

### The Pattern

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def manage_followers():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            # Add single follower (by GID)
            session.add_follower(task, "user_gid")

            # Remove a follower
            session.remove_follower(task, "other_user_gid")

            await session.commit_async()
            print("Followers updated")

asyncio.run(manage_followers())

# Bulk follower operations
async def bulk_followers():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            # Add multiple followers at once
            session.add_followers(task, [
                "user_gid_1",
                "user_gid_2",
                "user_gid_3"
            ])

            # Remove multiple followers
            session.remove_followers(task, ["user_gid_4", "user_gid_5"])

            await session.commit_async()

asyncio.run(bulk_followers())
```

### Why this works
Follower operations use Asana's dedicated endpoints for adding/removing followers. Like tags and projects, followers cannot be modified by direct assignment - action methods are required.

### See Also
- [SaveSession: Followers](save-session.md#followers) for full method signatures
- [Best Practices: Relationship Fields](patterns.md#relationship-fields) for why action methods are required

---

## Recipe 8: Create Task with Dependencies

### When to use
Create tasks that depend on each other (task B cannot be completed until task A is done).

### The Pattern

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
from autom8_asana.models import Task

async def create_with_dependencies():
    async with AsanaClient() as client:
        async with SaveSession(client) as session:
            # Create the prerequisite task
            prerequisite = Task(name="Phase 1: Research")
            session.track(prerequisite)

            # Create the dependent task
            dependent = Task(name="Phase 2: Implementation")
            session.track(dependent)

            # Set dependency: dependent cannot complete until prerequisite is done
            session.add_dependency(dependent, prerequisite)

            # Add to project
            session.add_to_project(prerequisite, "project_gid")
            session.add_to_project(dependent, "project_gid")

            # Commit - prerequisite is saved first due to dependency ordering
            result = await session.commit_async()

            print(f"Prerequisite GID: {prerequisite.gid}")
            print(f"Dependent GID: {dependent.gid}")

asyncio.run(create_with_dependencies())

# Add dependency between existing tasks
async def link_existing_tasks():
    async with AsanaClient() as client:
        task_a = await client.tasks.get_async("task_a_gid")
        task_b = await client.tasks.get_async("task_b_gid")

        async with SaveSession(client) as session:
            # Task B depends on Task A
            session.add_dependency(task_b, task_a)

            await session.commit_async()
            print("Dependency added")

asyncio.run(link_existing_tasks())
```

### Why this works
Dependencies use Asana's task dependency API. SaveSession automatically determines the correct save order based on dependency relationships. Attempting to create a cycle (A depends on B, B depends on A) raises `CyclicDependencyError`.

### See Also
- [SaveSession: Dependencies](save-session.md#dependencies) for method signatures
- [Best Practices: Dependency Cycles](patterns.md#dependency-cycles) for cycle detection

---

## Combined Workflow: Complete Task Setup

A realistic example combining multiple recipes into a complete task setup:

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession
from autom8_asana.models import Task

async def complete_task_setup():
    async with AsanaClient() as client:
        # Fetch project resources
        project = await client.projects.get_async("project_gid")
        section = await client.sections.get_async("section_gid")
        tag = await client.tags.get_async("tag_gid")

        async with SaveSession(client) as session:
            # Create parent task
            parent = Task(
                name="Epic: New Feature",
                notes="Parent task for feature implementation"
            )
            session.track(parent)
            parent.due_on = "2024-12-31"

            # Create subtasks
            subtask1 = Task(name="Design")
            subtask2 = Task(name="Implement")
            subtask3 = Task(name="Test")

            for subtask in [subtask1, subtask2, subtask3]:
                session.track(subtask)
                session.set_parent(subtask, parent)

            # Set dependencies: Implement depends on Design, Test depends on Implement
            session.add_dependency(subtask2, subtask1)
            session.add_dependency(subtask3, subtask2)

            # Add to project and section
            session.add_to_project(parent, project)
            session.move_to_section(parent, section)

            # Add tags
            session.add_tag(parent, tag)

            # Add comment
            session.add_comment(parent, "Created via autom8_asana SDK")

            # Add followers
            session.add_follower(parent, "user_gid")

            # Commit everything
            result = await session.commit_async()

            if result.success:
                print(f"Created epic with {len([subtask1, subtask2, subtask3])} subtasks")
                print(f"Epic GID: {parent.gid}")
            else:
                print(f"Failed: {len(result.failed)} errors")
                for error in result.failed:
                    print(f"  {error.entity.gid}: {error.error}")

asyncio.run(complete_task_setup())
```

---

## What's Next?

- **[SaveSession Deep Dive](save-session.md)**: Event hooks, change inspection, dependency ordering
- **[Best Practices](patterns.md)**: Recommended patterns and common mistakes to avoid
- **[SDK Adoption Guide](sdk-adoption.md)**: Migrating from other Asana libraries
