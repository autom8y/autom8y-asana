# Quick Start

Get your first SaveSession commit working in under 5 minutes.

**Prerequisites**: Read [Core Concepts](concepts.md) first to understand the mental model.

---

## Prerequisites

- Python 3.10+
- Asana Personal Access Token (PAT)
- A workspace GID (for creating tasks)

## Step 1: Install and Configure (1 minute)

Install the SDK:

```bash
pip install autom8y-asana
```

Set your Asana PAT as an environment variable:

```bash
# Bash/Zsh (add to ~/.bashrc or ~/.zshrc for persistence)
export ASANA_PAT="your_token_here"

# Optional: Set workspace for examples
export ASANA_WORKSPACE_GID="your_workspace_gid"
```

To find your workspace GID, look at any Asana URL: `https://app.asana.com/0/WORKSPACE_GID/PROJECT_GID`

---

## Step 2: Read Data (1 minute)

Reading data uses the Client directly. No SaveSession needed.

```python
import asyncio
from autom8_asana import AsanaClient

async def read_task():
    async with AsanaClient() as client:
        # READ: Fetch a task by GID
        task = await client.tasks.get_async("your_task_gid")
        print(f"Task: {task.name}")
        print(f"Completed: {task.completed}")

asyncio.run(read_task())
```

---

## Step 3: Update Fields (2 minutes)

Modifying data requires SaveSession. The pattern is: **track, modify, commit**.

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def update_task():
    async with AsanaClient() as client:
        # READ: Fetch the task
        task = await client.tasks.get_async("your_task_gid")

        async with SaveSession(client) as session:
            # 1. Track: Register for change detection
            session.track(task)

            # 2. Modify: Change fields directly
            task.name = "Updated Task Name"
            task.notes = "Updated via autom8_asana SDK"

            # 3. Commit: Send all changes in one batch
            result = await session.commit_async()

            if result.success:
                print(f"Updated task: {task.name}")
            else:
                print(f"Failed: {result.failed}")

asyncio.run(update_task())
```

Key insight: Changes are **queued** when you modify fields, not sent immediately. The API call happens at `commit_async()`.

---

## Step 4: Add Relationships (1 minute)

Relationships (tags, projects, sections) use action methods instead of direct assignment.

```python
import asyncio
from autom8_asana import AsanaClient
from autom8_asana.persistence import SaveSession

async def add_relationships():
    async with AsanaClient() as client:
        # READ: Fetch existing resources
        task = await client.tasks.get_async("your_task_gid")

        async with SaveSession(client) as session:
            # RELATIONSHIPS: Use action methods (not direct assignment)
            session.add_tag(task, "tag_gid")
            session.add_to_project(task, "project_gid")
            session.move_to_section(task, "section_gid")

            # Commit all relationship changes
            result = await session.commit_async()

            if result.success:
                print("Relationships updated!")

asyncio.run(add_relationships())
```

Why action methods? Relationships require dedicated API endpoints. The SDK handles this automatically.

---

## Complete Example

Here's a full script combining all four operation types:

```python
#!/usr/bin/env python3
"""Complete SaveSession example demonstrating all operation types."""

import asyncio
from autom8_asana import AsanaClient, Task
from autom8_asana.persistence import SaveSession

async def main():
    async with AsanaClient() as client:
        # ----- READ: Fetch existing data -----
        project = await client.projects.get_async("project_gid")
        section = await client.sections.get_async("section_gid")

        async with SaveSession(client) as session:
            # ----- CREATE: Make a new task -----
            new_task = Task(name="New Feature Request")
            session.track(new_task)

            # ----- UPDATE: Set properties -----
            new_task.notes = "Description of the feature"
            new_task.due_on = "2024-12-31"

            # ----- RELATIONSHIPS: Add associations -----
            session.add_to_project(new_task, project)
            session.move_to_section(new_task, section)

            # ----- COMMIT: Execute everything -----
            result = await session.commit_async()

            if result.success:
                print(f"Created task with GID: {new_task.gid}")
            elif result.partial:
                print(f"Partial success: {len(result.succeeded)} ok, {len(result.failed)} failed")
            else:
                print("All operations failed")

asyncio.run(main())
```

---

## Handling Results

Every `commit_async()` returns a `SaveResult`:

```python
result = await session.commit_async()

# Check status
if result.success:
    print("All operations succeeded")
elif result.partial:
    print("Some succeeded, some failed")

# Inspect failures
for error in result.failed:
    print(f"Entity: {error.entity.gid}")
    print(f"Operation: {error.operation.value}")
    print(f"Error: {error.error}")

# Or raise an exception on any failure
from autom8_asana.persistence import PartialSaveError
try:
    result.raise_on_failure()
except PartialSaveError as e:
    print(f"Save failed: {e}")
```

---

## What's Next?

- **[Workflows Guide](workflows.md)**: Common recipes and patterns
- **[SaveSession Deep Dive](save-session.md)**: Event hooks, change inspection, dependency ordering
- **[Best Practices](patterns.md)**: Recommended patterns and common mistakes to avoid

---

## Quick Reference

| Operation Type | Pattern | Example |
|---------------|---------|---------|
| **READ** | Client directly | `await client.tasks.get_async(gid)` |
| **CREATE** | SaveSession + track | `session.track(Task(name="New"))` |
| **UPDATE** | SaveSession + track + assign | `task.name = "Updated"` |
| **RELATIONSHIPS** | SaveSession + action method | `session.add_tag(task, tag)` |
