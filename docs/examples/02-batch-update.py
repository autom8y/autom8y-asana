"""Batch update custom fields on multiple tasks in a project.

This example demonstrates:
- Authenticating with AsanaClient using a PAT
- Fetching multiple tasks from a project
- Batch-updating custom fields across those tasks
- Proper error handling for API failures

Usage:
    export ASANA_PAT=your_token_here
    export PROJECT_GID=1234567890123456
    export CUSTOM_FIELD_GID=0987654321098765
    .venv/bin/python docs/examples/02-batch-update.py

Prerequisites:
- Python 3.10+
- autom8_asana installed
- Valid Asana PAT with write access to the specified project
- Project must have the specified custom field
"""
from __future__ import annotations

import asyncio
import os
import sys


async def main() -> None:
    """Fetch tasks from a project and batch-update a custom field."""

    # Step 1: Get required configuration from environment
    token = os.getenv("ASANA_PAT")
    project_gid = os.getenv("PROJECT_GID")
    custom_field_gid = os.getenv("CUSTOM_FIELD_GID")

    if not token:
        print("ERROR: ASANA_PAT environment variable not set")
        print("Set it with: export ASANA_PAT=your_token_here")
        sys.exit(1)

    if not project_gid:
        print("ERROR: PROJECT_GID environment variable not set")
        print("Set it with: export PROJECT_GID=1234567890123456")
        sys.exit(1)

    if not custom_field_gid:
        print("ERROR: CUSTOM_FIELD_GID environment variable not set")
        print("Set it with: export CUSTOM_FIELD_GID=0987654321098765")
        sys.exit(1)

    # Step 2: Create the AsanaClient
    # The client uses the token for all API requests
    from autom8_asana.client import AsanaClient

    async with AsanaClient(token=token) as client:
        try:
            # Step 3: Verify authentication
            print("Authenticating...")
            user = await client.users.me_async()
            print(f"Authenticated as: {user.name} ({user.email})\n")

            # Step 4: Fetch tasks from the project
            # Request specific fields to minimize payload size
            print(f"Fetching tasks from project {project_gid}...")
            opt_fields = [
                "name",
                "gid",
                "completed",
                "custom_fields",
                "custom_fields.name",
                "custom_fields.gid",
                "custom_fields.display_value",
            ]

            # Use PageIterator to handle pagination automatically
            task_iterator = client.tasks.list_async(
                project=project_gid,
                opt_fields=opt_fields,
                limit=50,  # Fetch up to 50 tasks per page
            )

            # Collect incomplete tasks that need updating
            # For large datasets, consider streaming instead of collecting all at once
            all_tasks = []
            async for task in task_iterator:
                if not task.completed:
                    all_tasks.append(task)

                # Limit to first 100 incomplete tasks for this example
                if len(all_tasks) >= 100:
                    break

            print(f"Found {len(all_tasks)} incomplete tasks\n")

            if not all_tasks:
                print("No incomplete tasks to update")
                return

            # Step 5: Batch update custom field on all tasks
            # This demonstrates updating multiple tasks efficiently
            print(f"Updating custom field {custom_field_gid} on {len(all_tasks)} tasks...")

            # Track success and failure counts
            success_count = 0
            failure_count = 0
            errors = []

            # Update tasks one by one
            # For true batch operations, see client.batch.execute_async()
            for i, task in enumerate(all_tasks, start=1):
                try:
                    # Update the custom field
                    # The custom_fields parameter expects a dict mapping field GID to value
                    await client.tasks.update_async(
                        task.gid,
                        custom_fields={custom_field_gid: "Updated via SDK"},
                    )
                    success_count += 1

                    # Progress indicator every 10 tasks
                    if i % 10 == 0:
                        print(f"  Progress: {i}/{len(all_tasks)} tasks processed")

                except Exception as exc:
                    # Don't fail the entire batch on individual task errors
                    failure_count += 1
                    error_msg = f"Failed to update task {task.gid} ({task.name}): {exc}"
                    errors.append(error_msg)
                    print(f"  WARNING: {error_msg}")

            # Step 6: Report results
            print(f"\nBatch update complete:")
            print(f"  Successfully updated: {success_count} tasks")
            print(f"  Failed: {failure_count} tasks")

            if errors:
                print(f"\nErrors encountered:")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"  - {error}")
                if len(errors) > 5:
                    print(f"  ... and {len(errors) - 5} more errors")

        except Exception as exc:
            # Handle top-level errors (authentication, project not found, etc.)
            print(f"ERROR: {exc}")
            sys.exit(1)


async def batch_api_example() -> None:
    """Example using the Batch API for more efficient bulk updates.

    The Batch API groups multiple operations into fewer HTTP requests,
    improving performance for large-scale updates.
    """
    token = os.getenv("ASANA_PAT")
    project_gid = os.getenv("PROJECT_GID")
    custom_field_gid = os.getenv("CUSTOM_FIELD_GID")

    if not token or not project_gid or not custom_field_gid:
        return

    from autom8_asana.batch import BatchRequest
    from autom8_asana.client import AsanaClient

    async with AsanaClient(token=token) as client:
        print("\nBatch API Example:")
        print("Fetching tasks...")

        # Fetch tasks to update
        task_iterator = client.tasks.list_async(project=project_gid, limit=20)
        tasks = []
        async for task in task_iterator:
            if not task.completed:
                tasks.append(task)
            if len(tasks) >= 10:
                break

        if not tasks:
            print("No tasks to update")
            return

        print(f"Creating batch requests for {len(tasks)} tasks...")

        # Create batch requests
        # Each request updates the custom field on one task
        batch_requests = [
            BatchRequest(
                path=f"/tasks/{task.gid}",
                method="PUT",
                data={"custom_fields": {custom_field_gid: "Batch updated"}},
            )
            for task in tasks
        ]

        # Execute batch requests
        # Asana groups these into chunks of 10 operations per HTTP request
        print("Executing batch update...")
        results = await client.batch.execute_async(batch_requests)

        # Process results
        success_count = sum(1 for r in results if r.status_code == 200)
        failure_count = len(results) - success_count

        print(f"Batch update complete:")
        print(f"  Success: {success_count}")
        print(f"  Failed: {failure_count}")


if __name__ == "__main__":
    # Run the main batch update example
    asyncio.run(main())

    # Uncomment to see the Batch API example:
    # asyncio.run(batch_api_example())
