#!/usr/bin/env python3
"""Example: SaveSession Basics - Unit of Work Pattern

Demonstrates the core SaveSession workflow:
1. Track entities for change detection
2. Modify fields directly (name, notes, etc.)
3. Use action methods for relationships (tags, projects, sections)
4. Commit all changes in a single batch

Why SaveSession?
- Batching: Multiple updates combined into optimized API calls
- Ordering: Parent entities saved before children automatically
- Partial Failure: Know exactly what succeeded vs failed

Without SaveSession, updating 5 task fields + adding a tag + moving to a section
would require 7 separate API calls. With SaveSession, this becomes 2 calls:
one batch for field updates, one for the action (tag/section).

Requirements:
- ASANA_PAT environment variable set
- ASANA_WORKSPACE_GID environment variable set
- ASANA_PROJECT_GID environment variable set (optional, for full demo)

Usage:
    export ASANA_PAT="your_token_here"
    export ASANA_WORKSPACE_GID="your_workspace_gid"
    python examples/12_save_session_basics.py
"""

import asyncio
from argparse import ArgumentParser

from _config import get_config_instructions, get_project_gid, get_workspace_gid

from autom8_asana import AsanaClient, Task
from autom8_asana.persistence import (
    EntityState,
    PartialSaveError,
    SaveSession,
)


async def demonstrate_basic_workflow(client: AsanaClient, workspace_gid: str) -> str:
    """Basic track-modify-commit workflow.

    Returns the created task GID for use in subsequent demos.
    """
    print("\n=== Basic Workflow: Track -> Modify -> Commit ===")

    # Create a test task first (using direct API, not SaveSession)
    task = await client.tasks.create_async(
        name="SaveSession Demo Task",
        workspace=workspace_gid,
        notes="Original notes",
    )
    print(f"Created test task: {task.gid}")

    # Now demonstrate SaveSession workflow
    async with SaveSession(client) as session:
        # Step 1: Track - Register entity for change detection
        # This captures a snapshot of the current state
        session.track(task)
        print(f"Tracked task (state: {session.get_state(task).value})")

        # Step 2: Modify - Change fields directly on the model
        # These changes are queued, NOT sent to API yet
        task.name = "Updated via SaveSession"
        task.notes = "Modified notes demonstrating SaveSession"
        print(f"Modified task (state: {session.get_state(task).value})")

        # Inspect what changed before committing
        changes = session.get_changes(task)
        print(f"Pending changes: {list(changes.keys())}")
        for field, (old_val, new_val) in changes.items():
            print(f"  {field}: '{old_val}' -> '{new_val}'")

        # Step 3: Commit - Send all changes in optimized batch
        # This is where the actual API call happens
        result = await session.commit_async()

        if result.success:
            print(f"Commit succeeded! Updated {len(result.succeeded)} entities")
            print(f"Task state after commit: {session.get_state(task).value}")
        else:
            print(f"Commit failed: {len(result.failed)} errors")

    return task.gid


async def demonstrate_create_workflow(
    client: AsanaClient, workspace_gid: str
) -> str | None:
    """Create new entities with SaveSession.

    Returns the created task GID.
    """
    print("\n=== CREATE: Making New Entities ===")

    async with SaveSession(client) as session:
        # Create a new Task model (not yet in Asana)
        # Note: No gid means this is a new entity
        new_task = Task(
            name="New Task via SaveSession",
            notes="This task was created through SaveSession",
        )

        # Track registers it for creation
        session.track(new_task)
        print(f"New task state: {session.get_state(new_task).value}")

        # Set additional properties before commit
        new_task.due_on = "2024-12-31"

        # Need workspace for creation
        # The SDK determines this from the task's workspace field
        # For creation, we set it via the task model
        from autom8_asana.models import NameGid

        new_task.workspace = NameGid(gid=workspace_gid)

        # Commit creates the task
        result = await session.commit_async()

        if result.success:
            # After commit, the task has a real GID from Asana
            print(f"Created task with GID: {new_task.gid}")
            print(f"Task state after commit: {session.get_state(new_task).value}")
            return new_task.gid
        else:
            print("Failed to create task")
            for error in result.failed:
                print(f"  Error: {error.error}")
            return None


async def demonstrate_action_methods(
    client: AsanaClient, task_gid: str, project_gid: str | None
) -> None:
    """Demonstrate action methods for relationships.

    Action methods handle relationships that require dedicated API endpoints:
    - Tags (add_tag, remove_tag)
    - Projects (add_to_project, remove_from_project)
    - Sections (move_to_section)
    - Dependencies (add_dependency, remove_dependency)
    - Followers (add_follower, remove_follower)
    - Comments (add_comment)
    - Likes (add_like, remove_like)
    """
    print("\n=== RELATIONSHIPS: Action Methods ===")

    if not project_gid:
        print("Skipping: No project GID provided")
        print("Set ASANA_PROJECT_GID to demonstrate relationship operations")
        return

    # Fetch the task and project
    task = await client.tasks.get_async(task_gid)
    project = await client.projects.get_async(project_gid)

    # Get sections from the project
    sections = await client.sections.list_async(project=project_gid).collect()
    if not sections:
        print("Skipping: Project has no sections")
        return

    section = sections[0]  # Use first section

    async with SaveSession(client) as session:
        # You can combine field updates with action methods
        session.track(task)
        task.notes = "Updated notes with relationship changes"

        # Action methods for relationships
        # These are executed AFTER field updates during commit

        # Add task to project with section placement
        session.add_to_project(task, project)
        session.move_to_section(task, section)

        # Add a comment
        session.add_comment(task, "Automated update via SaveSession demo")

        # Action methods return self for fluent chaining
        (
            session.add_like(task)  # Like the task as authenticated user
        )

        # Preview what will happen
        crud_ops, action_ops = session.preview()
        print(f"Planned CRUD operations: {len(crud_ops)}")
        print(f"Planned action operations: {len(action_ops)}")
        for action in action_ops:
            print(f"  {action.action.value} on task {action.task.gid}")

        # Commit everything
        result = await session.commit_async()

        if result.success:
            print("All operations succeeded!")
        elif result.partial:
            print(
                f"Partial success: {len(result.succeeded)} ok, {len(result.failed)} failed"
            )
        else:
            print("All operations failed")


async def demonstrate_change_tracking(client: AsanaClient, task_gid: str) -> None:
    """Demonstrate change tracking methods."""
    print("\n=== Change Tracking: get_changes() and get_state() ===")

    task = await client.tasks.get_async(task_gid)

    async with SaveSession(client) as session:
        # Before tracking - can't get state
        # session.get_state(task)  # Would raise ValueError

        # Track the entity
        session.track(task)

        # Initial state is CLEAN (no changes)
        state = session.get_state(task)
        print(f"Initial state: {state.value}")
        assert state == EntityState.CLEAN

        # Get changes (empty dict for clean entity)
        changes = session.get_changes(task)
        print(f"Changes before modification: {changes}")

        # Modify the entity
        original_name = task.name
        task.name = "Temporarily Modified"

        # State changes to MODIFIED
        state = session.get_state(task)
        print(f"State after modification: {state.value}")
        assert state == EntityState.MODIFIED

        # Get changes shows what changed
        changes = session.get_changes(task)
        print(f"Changes after modification: {changes}")
        # Output: {'name': ('Original Name', 'Temporarily Modified')}

        # Revert the change (for demo purposes)
        task.name = original_name
        state = session.get_state(task)
        print(f"State after reverting: {state.value}")
        # If we revert to original value, state goes back to CLEAN

        # No commit needed since we reverted


async def demonstrate_partial_failure_handling(
    client: AsanaClient, workspace_gid: str
) -> None:
    """Demonstrate handling partial failures."""
    print("\n=== Error Handling: Partial Failures ===")

    # Create a task for this demo
    task = await client.tasks.create_async(
        name="Partial Failure Demo",
        workspace=workspace_gid,
    )

    async with SaveSession(client) as session:
        session.track(task)
        task.name = "Updated Name"

        # Also try an action that might fail (invalid tag GID)
        session.add_tag(task, "invalid_tag_gid_that_does_not_exist")

        result = await session.commit_async()

        # Check result properties
        print(f"Success: {result.success}")
        print(f"Partial: {result.partial}")
        print(f"Total operations: {result.total_count}")
        print(f"Succeeded: {len(result.succeeded)}")
        print(f"Failed: {len(result.failed)}")

        # Inspect failures
        for error in result.failed:
            print("\nFailed operation:")
            print(f"  Entity: {type(error.entity).__name__} ({error.entity.gid})")
            print(f"  Operation: {error.operation.value}")
            print(f"  Error: {error.error}")

        # Alternative: Raise exception on any failure
        try:
            result.raise_on_failure()
        except PartialSaveError as e:
            print(f"\nPartialSaveError raised: {len(e.result.failed)} failures")

    # Cleanup
    await client.tasks.delete_async(task.gid)


async def demonstrate_comparison_without_session(
    client: AsanaClient, workspace_gid: str
) -> None:
    """Show the difference vs doing operations without SaveSession.

    WITHOUT SaveSession (7 API calls):
    1. tasks.update(name=...)
    2. tasks.update(notes=...)
    3. tasks.update(due_on=...)
    4. tasks.update(completed=...)
    5. tasks.addTag(...)
    6. tasks.addProject(...)
    7. sections.addTask(...)

    WITH SaveSession (2 API calls):
    1. Batch update (name, notes, due_on, completed)
    2. Action operations (tag, project, section - still individual but optimized)

    The field updates are batched into a single API call.
    """
    print("\n=== Comparison: With vs Without SaveSession ===")
    print(
        """
Without SaveSession, updating 4 fields + 3 relationships = 7 API calls:
  1. tasks.update(name=...)
  2. tasks.update(notes=...)
  3. tasks.update(due_on=...)
  4. tasks.update(completed=...)
  5. tasks.addTag(...)
  6. tasks.addProject(...)
  7. sections.addTask(...)

With SaveSession:
  - Field updates batched: 1 API call for all 4 fields
  - Relationship actions: 3 API calls (cannot be batched by Asana API)
  - Total: 4 API calls instead of 7

For field-only updates, the savings are even greater:
  - 10 field changes = 1 API call with SaveSession
  - 10 field changes = 10 API calls without
"""
    )


async def main(workspace_gid: str, project_gid: str | None) -> None:
    """Run all SaveSession examples."""
    print("autom8_asana SDK - SaveSession Basics")
    print("=" * 50)

    async with AsanaClient() as client:
        # 1. Basic workflow
        task_gid = await demonstrate_basic_workflow(client, workspace_gid)

        # 2. Create workflow
        new_task_gid = await demonstrate_create_workflow(client, workspace_gid)

        # 3. Action methods (relationships)
        await demonstrate_action_methods(client, task_gid, project_gid)

        # 4. Change tracking
        await demonstrate_change_tracking(client, task_gid)

        # 5. Partial failure handling
        await demonstrate_partial_failure_handling(client, workspace_gid)

        # 6. Comparison explanation
        await demonstrate_comparison_without_session(client, workspace_gid)

        # Cleanup demo tasks
        print("\n=== Cleanup ===")
        await client.tasks.delete_async(task_gid)
        print(f"Deleted task: {task_gid}")
        if new_task_gid:
            await client.tasks.delete_async(new_task_gid)
            print(f"Deleted task: {new_task_gid}")

    print("\n" + "=" * 50)
    print("SaveSession Basics Complete!")
    print("\nKey Takeaways:")
    print("  - Track entities BEFORE modifying them")
    print("  - Use direct assignment for field updates (task.name = ...)")
    print("  - Use action methods for relationships (session.add_tag(...))")
    print("  - Always check result.success or result.partial after commit")
    print("  - get_changes() shows pending modifications before commit")
    print("  - get_state() shows entity lifecycle (NEW, CLEAN, MODIFIED, DELETED)")


if __name__ == "__main__":
    parser = ArgumentParser(description="Demonstrate SaveSession Unit of Work pattern")
    parser.add_argument(
        "--workspace",
        default=get_workspace_gid(),
        help="Workspace GID (or set ASANA_WORKSPACE_GID env var)",
    )
    parser.add_argument(
        "--project",
        default=get_project_gid(),
        help="Project GID for relationship demos (or set ASANA_PROJECT_GID env var)",
    )
    args = parser.parse_args()

    if not args.workspace:
        print("ERROR: No workspace GID provided")
        print(get_config_instructions())
        exit(1)

    asyncio.run(main(args.workspace, args.project))
