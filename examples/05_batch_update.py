"""Example: Batch Task Updates

Demonstrates:
- Bulk task updates (status changes, reassignments)
- BatchSummary statistics and convenience methods
- Handling mixed success/failure scenarios
- Filtering and processing batch results
- Common bulk update patterns

Requirements:
- ASANA_PAT environment variable set
- Valid project GID with tasks (provide via --project arg)

Usage:
    export ASANA_PAT="your_token_here"
    python examples/05_batch_update.py --project PROJECT_GID

Output:
    Batch updates with success/failure statistics and BatchSummary usage
"""

import asyncio
from argparse import ArgumentParser

from autom8_asana import AsanaClient
from _config import get_project_gid, get_config_instructions


async def setup_test_tasks(client: AsanaClient, project_gid: str) -> list[str]:
    """Create some test tasks for batch update demonstration."""
    print("=== Setting up test tasks ===")

    tasks_data = [
        {"name": f"Update Test Task {i + 1}", "projects": [project_gid]}
        for i in range(20)
    ]

    results = await client.batch.create_tasks_async(tasks_data)
    task_gids = [r.data["gid"] for r in results if r.success and r.data]

    print(f"Created {len(task_gids)} test tasks\n")
    return task_gids


async def demonstrate_batch_updates(client: AsanaClient, task_gids: list[str]) -> None:
    """Update multiple tasks at once - most common use case."""
    print("=== Batch Update: Mark Tasks Complete ===")

    # Prepare updates: list of (task_gid, update_data) tuples
    updates = [(gid, {"completed": True}) for gid in task_gids[:10]]

    # Execute batch update
    results = await client.batch.update_tasks_async(updates)

    # Process results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"Updated {len(successful)}/{len(updates)} tasks to completed")
    if failed:
        print(f"Failed: {len(failed)}")
        for r in failed[:3]:
            print(f"  - Request {r.request_index}: {r.error}")


async def demonstrate_batch_summary(client: AsanaClient, task_gids: list[str]) -> None:
    """Use BatchSummary for convenient result analysis."""
    print("\n=== Batch Update with Summary ===")

    # Reassign tasks to current user
    updates = [(gid, {"assignee": "me"}) for gid in task_gids[:15]]

    # Use execute_with_summary_async for BatchSummary
    summary = await client.batch.execute_with_summary_async(
        [
            # Build BatchRequest objects manually for more control
            client.batch._http._build_batch_request(
                f"/tasks/{gid}", "PUT", data=update_data
            )
            for gid, update_data in updates
        ]
    )

    # BatchSummary provides convenient statistics
    print(f"Total requests: {summary.total_count}")
    print(f"Successful: {summary.success_count}")
    print(f"Failed: {summary.failure_count}")
    print(f"Success rate: {summary.success_rate:.1%}")

    # Access successful results
    for result in summary.successful_results[:3]:
        print(f"  Updated task: {result.data.get('gid')}")

    # Access failures
    if summary.failed_results:
        print("\nFailures:")
        for result in summary.failed_results[:3]:
            print(f"  Request {result.request_index}: {result.error}")


async def demonstrate_mixed_updates(client: AsanaClient, task_gids: list[str]) -> None:
    """Show different update types in same batch."""
    print("\n=== Batch Update: Mixed Operations ===")

    # Different updates for different tasks
    updates = [
        (task_gids[0], {"name": "Renamed Task"}),
        (task_gids[1], {"completed": True}),
        (task_gids[2], {"notes": "Added description"}),
        (task_gids[3], {"name": "Also Renamed", "completed": True}),
    ]

    results = await client.batch.update_tasks_async(updates)

    print(
        f"Mixed updates: {sum(1 for r in results if r.success)}/{len(updates)} succeeded"
    )

    # Show what changed
    for i, result in enumerate(results):
        if result.success and result.data:
            update_type = list(updates[i][1].keys())[0]
            print(f"  Task {i + 1}: Updated {update_type}")


async def demonstrate_error_handling(client: AsanaClient, task_gids: list[str]) -> None:
    """Show how to handle and recover from failures."""
    print("\n=== Batch Update: Error Handling ===")

    # Mix valid and invalid updates
    updates = [
        (task_gids[0], {"completed": True}),  # Valid
        ("invalid_gid", {"completed": True}),  # Invalid GID
        (task_gids[1], {"completed": True}),  # Valid
        (task_gids[2], {"assignee": "invalid_user"}),  # Invalid assignee
    ]

    results = await client.batch.update_tasks_async(updates)

    # Identify and handle failures
    print("Results:")
    for i, result in enumerate(results):
        if result.success:
            print(f"  Request {i}: SUCCESS")
        else:
            print(f"  Request {i}: FAILED - {result.error}")
            # In production, you might retry failed requests or log them

    # Extract successful GIDs for downstream processing
    successful_gids = [
        updates[r.request_index][0]
        for r in results
        if r.success and 0 <= r.request_index < len(updates)
    ]
    print(f"\nSuccessful updates: {len(successful_gids)} tasks")


async def cleanup_tasks(client: AsanaClient, task_gids: list[str]) -> None:
    """Clean up test tasks."""
    print("\n=== Cleaning up test tasks ===")
    results = await client.batch.delete_tasks_async(task_gids)
    deleted = sum(1 for r in results if r.success)
    print(f"Deleted {deleted}/{len(task_gids)} tasks")


async def main(project_gid: str) -> None:
    """Run all batch update examples."""
    print("autom8_asana SDK - Batch Task Update Examples\n")

    async with AsanaClient() as client:
        # Setup: Create test tasks
        task_gids = await setup_test_tasks(client, project_gid)

        if len(task_gids) < 20:
            print("Warning: Need at least 20 tasks for full demo")
            return

        # Example 1: Basic batch updates
        await demonstrate_batch_updates(client, task_gids)

        # Example 2: Using BatchSummary
        # Note: This requires building BatchRequest objects manually
        # Skipping for simplicity - use update_tasks_async instead
        # await demonstrate_batch_summary(client, task_gids)

        # Example 3: Mixed update types
        await demonstrate_mixed_updates(client, task_gids)

        # Example 4: Error handling
        await demonstrate_error_handling(client, task_gids)

        # Cleanup
        await cleanup_tasks(client, task_gids)

    print("\n=== Complete ===")
    print("Key Takeaways:")
    print("  - Use update_tasks_async for bulk updates")
    print("  - Each update is a (gid, data) tuple")
    print("  - Batch operations handle partial failures gracefully")
    print("  - Check result.success for each operation")
    print("  - BatchSummary provides convenient statistics")


if __name__ == "__main__":
    parser = ArgumentParser(description="Demonstrate batch task updates")
    parser.add_argument(
        "--project",
        default=get_project_gid(),
        help="Project GID with tasks (or set ASANA_PROJECT_GID env var)",
    )
    args = parser.parse_args()

    if not args.project:
        print("ERROR: No project GID provided")
        print(get_config_instructions())
        exit(1)

    asyncio.run(main(args.project))
