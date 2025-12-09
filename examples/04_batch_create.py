"""Example: Batch Task Creation

Demonstrates:
- Bulk task creation with automatic chunking (10 per batch)
- Handling partial failures in batch operations
- Extracting created GIDs from results
- Performance comparison with sequential creation
- BatchResult success/failure handling

Requirements:
- ASANA_PAT environment variable set
- Valid project GID (provide via --project arg)

Usage:
    export ASANA_PAT="your_token_here"
    python examples/04_batch_create.py --project PROJECT_GID

Output:
    Batch creation of 50 tasks with success/failure statistics
"""

import asyncio
import time
from argparse import ArgumentParser

from autom8_asana import AsanaClient
from _config import get_project_gid, get_config_instructions


async def batch_create_tasks(
    client: AsanaClient, project_gid: str, count: int = 50
) -> list[str]:
    """Create multiple tasks efficiently using batch API.

    The batch API automatically chunks requests into groups of 10
    (Asana's batch size limit) and executes them sequentially.

    Returns:
        List of created task GIDs (only successful creations)
    """
    print(f"\n=== Batch Creating {count} Tasks ===")

    # Prepare task data - each dict represents one task
    tasks_data = [
        {
            "name": f"Batch Task {i+1}",
            "projects": [project_gid],
            "notes": f"This is task number {i+1} from batch creation",
        }
        for i in range(count)
    ]

    # Execute batch create - automatically chunks into groups of 10
    start_time = time.time()
    results = await client.batch.create_tasks_async(tasks_data)
    elapsed = time.time() - start_time

    # Process results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"\nBatch complete in {elapsed:.2f}s")
    print(f"  Succeeded: {len(successful)}/{count}")
    print(f"  Failed: {len(failed)}/{count}")

    # Extract created task GIDs from successful results
    created_gids = [r.data["gid"] for r in successful if r.data]

    # Show any failures
    if failed:
        print("\nFailures:")
        for result in failed[:3]:  # Show first 3 failures
            print(f"  Request {result.request_index}: {result.error}")
        if len(failed) > 3:
            print(f"  ... and {len(failed) - 3} more failures")

    return created_gids


async def sequential_create_tasks(
    client: AsanaClient, project_gid: str, count: int = 10
) -> list[str]:
    """Create tasks one at a time for comparison.

    This is slower but useful for comparison to show the
    performance benefit of batch operations.
    """
    print(f"\n=== Sequential Creating {count} Tasks (for comparison) ===")

    created_gids: list[str] = []

    start_time = time.time()
    for i in range(count):
        task = await client.tasks.create_async(
            name=f"Sequential Task {i+1}",
            projects=[project_gid],
        )
        created_gids.append(task.gid)
    elapsed = time.time() - start_time

    print(f"Sequential complete in {elapsed:.2f}s")
    print(f"  Average: {elapsed/count:.3f}s per task")

    return created_gids


async def demonstrate_partial_failure(client: AsanaClient, project_gid: str) -> None:
    """Show how batch API handles partial failures.

    Even if some tasks fail validation or creation, others
    in the batch still succeed.
    """
    print("\n=== Demonstrating Partial Failure Handling ===")

    # Mix of valid and invalid task data
    tasks_data = [
        {"name": "Valid Task 1", "projects": [project_gid]},
        {"name": "Valid Task 2", "projects": [project_gid]},
        {"name": ""},  # Invalid: empty name
        {"name": "Valid Task 3", "projects": [project_gid]},
        {"projects": [project_gid]},  # Invalid: missing name
    ]

    results = await client.batch.create_tasks_async(tasks_data)

    print("\nResults per request:")
    for i, result in enumerate(results):
        if result.success:
            print(f"  Request {i}: SUCCESS - Created GID {result.data['gid']}")
        else:
            print(f"  Request {i}: FAILED - {result.error}")

    successful_count = sum(1 for r in results if r.success)
    print(f"\nTotal: {successful_count}/5 succeeded (partial success is OK)")


async def cleanup_tasks(client: AsanaClient, task_gids: list[str]) -> None:
    """Clean up created tasks using batch delete."""
    if not task_gids:
        return

    print(f"\n=== Cleaning Up {len(task_gids)} Tasks ===")

    # Batch delete is also available
    results = await client.batch.delete_tasks_async(task_gids)

    successful = sum(1 for r in results if r.success)
    print(f"Deleted {successful}/{len(task_gids)} tasks")


async def main(project_gid: str) -> None:
    """Run all batch creation examples."""
    print("autom8_asana SDK - Batch Task Creation Examples")

    async with AsanaClient() as client:
        # Example 1: Batch create 50 tasks
        batch_gids = await batch_create_tasks(client, project_gid, count=50)

        # Example 2: Sequential create 10 tasks (for comparison)
        sequential_gids = await sequential_create_tasks(client, project_gid, count=10)

        # Example 3: Partial failure handling
        await demonstrate_partial_failure(client, project_gid)

        # Cleanup all created tasks
        all_gids = batch_gids + sequential_gids
        await cleanup_tasks(client, all_gids)

    print("\n=== Complete ===")
    print("Key Takeaways:")
    print("  - Batch API chunks requests automatically (10 per batch)")
    print("  - Much faster than sequential for bulk operations")
    print("  - Partial failures don't stop the batch")
    print("  - Check result.success for each operation")
    print("  - Extract data with result.data['gid']")


if __name__ == "__main__":
    parser = ArgumentParser(description="Demonstrate batch task creation")
    parser.add_argument(
        "--project",
        default=get_project_gid(),
        help="Project GID for tasks (or set ASANA_PROJECT_GID env var)",
    )
    args = parser.parse_args()

    if not args.project:
        print("ERROR: No project GID provided")
        print(get_config_instructions())
        exit(1)

    asyncio.run(main(args.project))
