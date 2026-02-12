#!/usr/bin/env python3
"""Create Task with Subtasks

Demonstrates creating a parent task and child subtasks using SaveSession.
Shows how to use set_parent() to establish parent-child relationships and
commit all entities in a single batch with proper dependency ordering.

Prerequisites:
    pip install autom8-asana
    export ASANA_PAT="your_token"
    export ASANA_WORKSPACE_GID="your_workspace_gid"

Related docs:
    - docs/guides/save-session.md
"""
import asyncio
import os

from autom8_asana import AsanaClient
from autom8_asana.models import Task
from autom8_asana.persistence import SaveSession


async def main():
    """Create a parent task with three subtasks in one batch."""
    # Get credentials from environment
    token = os.getenv("ASANA_PAT")
    workspace_gid = os.getenv("ASANA_WORKSPACE_GID")

    if not token or not workspace_gid:
        print("Error: ASANA_PAT and ASANA_WORKSPACE_GID must be set")
        return

    # Create client and session
    async with AsanaClient(token=token) as client:
        async with SaveSession(client) as session:
            # Create parent task with temporary GID
            # SaveSession will replace temp GIDs with real GIDs after creation
            parent = Task(
                gid="temp_parent",
                name="Project Planning",
                notes="Main planning task for Q1 deliverables",
                workspace={"gid": workspace_gid}
            )

            # Track parent for creation
            session.track(parent)

            # Create subtasks with temporary GIDs
            subtask1 = Task(
                gid="temp_subtask_1",
                name="Research requirements",
                notes="Gather stakeholder input and document requirements",
                workspace={"gid": workspace_gid}
            )

            subtask2 = Task(
                gid="temp_subtask_2",
                name="Draft proposal",
                notes="Create initial proposal document",
                workspace={"gid": workspace_gid}
            )

            subtask3 = Task(
                gid="temp_subtask_3",
                name="Review with team",
                notes="Schedule review meeting and collect feedback",
                workspace={"gid": workspace_gid}
            )

            # Track all subtasks
            session.track(subtask1)
            session.track(subtask2)
            session.track(subtask3)

            # Establish parent-child relationships
            # These will be executed during commit, after entity creation
            session.set_parent(subtask1, parent)
            session.set_parent(subtask2, parent)
            session.set_parent(subtask3, parent)

            # Optionally add a comment to the parent task
            session.add_comment(
                parent,
                "Created parent task with 3 subtasks for Q1 planning"
            )

            # Commit all changes in optimized batches
            # SaveSession handles dependency ordering automatically:
            # 1. Parent task is created first (no dependencies)
            # 2. Subtasks are created next (depend on parent)
            # 3. Parent-child relationships are established via set_parent actions
            # 4. Comment is added to parent task
            try:
                result = await session.commit_async()

                if result.success:
                    print("Success! All entities created.")
                    print(f"Created {len(result.succeeded)} entities:")

                    # Show created entities with their real GIDs
                    for entity in result.succeeded:
                        entity_type = "Parent" if entity.gid == parent.gid else "Subtask"
                        print(f"  - {entity_type}: {entity.name} (GID: {entity.gid})")

                    # Check action results (set_parent and add_comment)
                    if result.action_results:
                        print(f"\nExecuted {len(result.action_results)} actions:")
                        for action_result in result.action_results:
                            status = "SUCCESS" if action_result.success else "FAILED"
                            print(f"  - {action_result.action.action.value}: {status}")

                    print(f"\nParent task URL: https://app.asana.com/0/0/{parent.gid}")

                elif result.partial:
                    # Partial success - some entities created, some failed
                    print(f"Partial success: {len(result.succeeded)} succeeded, {len(result.failed)} failed")

                    for error in result.failed:
                        print(f"Failed: {error.entity.name}")
                        print(f"  Error: {error.error}")
                else:
                    # Total failure
                    print("All operations failed:")
                    for error in result.failed:
                        print(f"  - {error.entity.name}: {error.error}")

            except Exception as e:
                print(f"Commit failed with exception: {e}")
                raise


if __name__ == "__main__":
    asyncio.run(main())
