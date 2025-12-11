"""Example: Task CRUD Operations

Demonstrates:
- Creating tasks with different parameters
- Reading tasks (typed models vs raw dicts)
- Updating task fields
- Deleting tasks

Requirements:
- ASANA_PAT environment variable set
- Valid workspace GID (provide via --workspace arg)

Usage:
    export ASANA_PAT="your_token_here"
    python examples/02_task_crud.py --workspace WORKSPACE_GID

Output:
    Task creation, updates, and deletion with GIDs and status
"""

import asyncio
from argparse import ArgumentParser

from _config import get_config_instructions, get_workspace_gid

from autom8_asana import AsanaClient


async def demonstrate_create(client: AsanaClient, workspace_gid: str) -> str:
    """Create a new task and return its GID."""
    print("\n=== CREATE ===")

    # Create a task with minimal fields
    task = await client.tasks.create_async(
        name="Example Task - CRUD Demo",
        workspace=workspace_gid,
        notes="This task demonstrates basic CRUD operations",
    )

    print(f"Created task: {task.name}")
    print(f"  GID: {task.gid}")
    print(f"  Completed: {task.completed}")

    # Access typed model fields
    print(f"  Created at: {task.created_at}")

    return task.gid


async def demonstrate_read(client: AsanaClient, task_gid: str) -> None:
    """Read a task using both typed model and raw dict access."""
    print("\n=== READ ===")

    # Method 1: Get as typed Task model (default, recommended)
    task = await client.tasks.get_async(task_gid)
    print(f"Task (typed model): {task.name}")
    print(f"  Assignee: {task.assignee.name if task.assignee else 'Unassigned'}")
    print(f"  Due date: {task.due_on or 'No due date'}")

    # Method 2: Get as raw dict (for dynamic access)
    task_dict = await client.tasks.get_async(task_gid, raw=True)
    print(f"\nTask (raw dict): {task_dict['name']}")
    print(f"  Resource type: {task_dict.get('resource_type')}")

    # Sync equivalent (runs async in background)
    # task_sync = client.tasks.get(task_gid)
    # print(f"Sync access: {task_sync.name}")


async def demonstrate_update(client: AsanaClient, task_gid: str) -> None:
    """Update task fields."""
    print("\n=== UPDATE ===")

    # Update multiple fields at once
    updated_task = await client.tasks.update_async(
        task_gid,
        name="Updated Task Name",
        notes="Updated description with more details",
        completed=False,
    )

    print(f"Updated task: {updated_task.name}")
    print(f"  Notes: {updated_task.notes}")
    print(f"  Modified at: {updated_task.modified_at}")

    # Update again - mark as completed
    completed_task = await client.tasks.update_async(
        task_gid,
        completed=True,
    )
    print(f"\nMarked as completed: {completed_task.completed}")


async def demonstrate_delete(client: AsanaClient, task_gid: str) -> None:
    """Delete a task."""
    print("\n=== DELETE ===")

    # Delete returns None on success
    await client.tasks.delete_async(task_gid)
    print(f"Deleted task: {task_gid}")

    # Verify deletion - this will raise NotFoundError
    try:
        await client.tasks.get_async(task_gid)
        print("ERROR: Task should have been deleted!")
    except Exception:
        print("Verified: Task no longer exists")


async def main(workspace_gid: str) -> None:
    """Run all CRUD examples."""
    print("autom8_asana SDK - Task CRUD Examples")

    async with AsanaClient() as client:
        # Create
        task_gid = await demonstrate_create(client, workspace_gid)

        # Read
        await demonstrate_read(client, task_gid)

        # Update
        await demonstrate_update(client, task_gid)

        # Delete
        await demonstrate_delete(client, task_gid)

    print("\n=== Complete ===")
    print("All CRUD operations demonstrated successfully.")


if __name__ == "__main__":
    parser = ArgumentParser(description="Demonstrate task CRUD operations")
    parser.add_argument(
        "--workspace",
        default=get_workspace_gid(),
        help="Workspace GID (or set ASANA_WORKSPACE_GID env var)",
    )
    args = parser.parse_args()

    if not args.workspace:
        print("ERROR: No workspace GID provided")
        print(get_config_instructions())
        exit(1)

    asyncio.run(main(args.workspace))
