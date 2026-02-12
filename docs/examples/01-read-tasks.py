"""Read tasks from a project and display their properties.

This beginner example demonstrates:
- Creating an AsanaClient with a token from environment
- Fetching the current user
- Listing tasks in a project with pagination
- Accessing task properties and custom fields
- Both async and sync usage patterns

Usage:
    export ASANA_PAT=your_token_here
    export PROJECT_GID=1234567890123456
    .venv/bin/python docs/examples/01-read-tasks.py

Prerequisites:
- Python 3.10+
- autom8_asana installed
- Valid Asana PAT with read access to the specified project
"""
from __future__ import annotations

import asyncio
import os
import sys


async def main() -> None:
    """Fetch and display tasks from a project."""

    # Step 1: Get credentials from environment
    token = os.getenv("ASANA_PAT")
    project_gid = os.getenv("PROJECT_GID")

    if not token:
        print("ERROR: ASANA_PAT environment variable not set")
        print("Set it with: export ASANA_PAT=your_token_here")
        sys.exit(1)

    if not project_gid:
        print("ERROR: PROJECT_GID environment variable not set")
        print("Set it with: export PROJECT_GID=1234567890123456")
        sys.exit(1)

    # Step 2: Create the AsanaClient
    # The client automatically uses the token for authentication
    from autom8_asana.client import AsanaClient

    client = AsanaClient(token=token)

    try:
        # Step 3: Get current user information
        # This verifies authentication works
        print("Fetching current user...")
        user = await client.users.me_async()
        print(f"Authenticated as: {user.name} ({user.email})")
        print()

        # Step 4: List tasks in the project
        # The list_async() method returns a PageIterator that handles pagination automatically
        print(f"Fetching tasks from project {project_gid}...")

        # Specify which fields to include in the response
        # This reduces payload size and improves performance
        opt_fields = [
            "name",
            "gid",
            "assignee",
            "assignee.name",
            "completed",
            "due_on",
            "custom_fields",
            "custom_fields.name",
            "custom_fields.display_value",
        ]

        # Create the page iterator
        # This fetches tasks lazily as you iterate
        task_iterator = client.tasks.list_async(
            project=project_gid,
            opt_fields=opt_fields,
            limit=20,  # Fetch 20 tasks per page
        )

        # Step 5: Iterate through tasks and display information
        task_count = 0
        async for task in task_iterator:
            task_count += 1

            # Display basic task information
            print(f"Task {task_count}: {task.name}")
            print(f"  GID: {task.gid}")

            # Display assignee (may be None for unassigned tasks)
            if task.assignee:
                print(f"  Assignee: {task.assignee.name}")
            else:
                print(f"  Assignee: Unassigned")

            # Display completion status
            status = "Complete" if task.completed else "Incomplete"
            print(f"  Status: {status}")

            # Display due date if present
            if task.due_on:
                print(f"  Due: {task.due_on}")

            # Display custom fields if present
            if task.custom_fields:
                print(f"  Custom Fields:")
                for field in task.custom_fields:
                    # Display the field name and its current value
                    # display_value provides a human-readable string representation
                    print(f"    {field.name}: {field.display_value}")

            print()

            # Limit output for this example
            if task_count >= 10:
                break

        print(f"Displayed {task_count} tasks")

    except Exception as exc:
        # Handle authentication failures and other errors
        print(f"ERROR: {exc}")
        sys.exit(1)


async def sync_example() -> None:
    """Example using synchronous methods instead of async.

    The SDK supports both patterns. Use async for better concurrency,
    use sync for simpler code in non-async contexts.
    """
    token = os.getenv("ASANA_PAT")
    project_gid = os.getenv("PROJECT_GID")

    if not token or not project_gid:
        return

    from autom8_asana.client import AsanaClient

    client = AsanaClient(token=token)

    # Synchronous call - blocks until complete
    user = client.users.me()
    print(f"Sync example - authenticated as: {user.name}")

    # Note: list_async() returns an iterator, so you still use 'async for'
    # even in the sync pattern. To collect all items synchronously:
    task_iterator = client.tasks.list_async(project=project_gid, limit=5)

    # Use collect() to fetch all items (use with caution on large datasets)
    import asyncio
    tasks = asyncio.run(task_iterator.collect())
    print(f"Sync example - fetched {len(tasks)} tasks")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

    # Uncomment to see the sync example:
    # asyncio.run(sync_example())
