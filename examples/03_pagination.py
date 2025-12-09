"""Example: Pagination with PageIterator

Demonstrates:
- Lazy pagination with async for
- Collecting all items with .collect()
- Taking first N items with .take(n)
- Getting only the first item with .first()
- Optimizing response size with opt_fields
- Memory-efficient iteration over large result sets
- Early exit patterns

Requirements:
- ASANA_PAT environment variable set
- Valid project GID with multiple tasks (provide via --project arg)

Usage:
    export ASANA_PAT="your_token_here"
    python examples/03_pagination.py --project PROJECT_GID

Output:
    Tasks retrieved using different pagination patterns
"""

import asyncio
from argparse import ArgumentParser

from autom8_asana import AsanaClient
from _config import get_project_gid, get_config_instructions


async def demonstrate_async_for(client: AsanaClient, project_gid: str) -> None:
    """Iterate tasks using async for - most memory efficient."""
    print("\n=== Pattern 1: async for (Lazy, Memory Efficient) ===")

    # PageIterator fetches pages on demand as you iterate
    # Only one page is buffered in memory at a time
    count = 0
    async for task in client.tasks.list_async(project=project_gid):
        count += 1
        print(f"  {count}. {task.name} (GID: {task.gid})")

        # Early exit example - stop after 5 tasks
        if count >= 5:
            print(f"  ... (stopping after {count} tasks)")
            break

    print(f"Processed {count} tasks (lazy iteration)")


async def demonstrate_collect(client: AsanaClient, project_gid: str) -> None:
    """Collect all tasks into a list - simple but loads everything."""
    print("\n=== Pattern 2: .collect() (Eager, Simple) ===")

    # Fetch ALL tasks and load into memory
    # Use when you need the full list and memory isn't a concern
    all_tasks = await client.tasks.list_async(project=project_gid).collect()

    print(f"Collected {len(all_tasks)} total tasks")
    for i, task in enumerate(all_tasks[:3], 1):
        print(f"  {i}. {task.name}")

    if len(all_tasks) > 3:
        print(f"  ... and {len(all_tasks) - 3} more")


async def demonstrate_take(client: AsanaClient, project_gid: str) -> None:
    """Take first N tasks - efficient for "top N" queries."""
    print("\n=== Pattern 3: .take(n) (First N Items) ===")

    # Fetch only first 3 tasks - stops pagination early
    # More efficient than .collect() when you only need a subset
    first_three = await client.tasks.list_async(project=project_gid).take(3)

    print(f"Retrieved first {len(first_three)} tasks:")
    for i, task in enumerate(first_three, 1):
        print(f"  {i}. {task.name}")


async def demonstrate_first(client: AsanaClient, project_gid: str) -> None:
    """Get only the first task - most efficient for single item."""
    print("\n=== Pattern 4: .first() (Single Item) ===")

    # Fetch only the first task - stops immediately after first page
    # Returns None if no tasks exist
    first_task = await client.tasks.list_async(project=project_gid).first()

    if first_task:
        print(f"First task: {first_task.name}")
        print(f"  GID: {first_task.gid}")
        print(f"  Completed: {first_task.completed}")
    else:
        print("No tasks found in project")


async def demonstrate_opt_fields(client: AsanaClient, project_gid: str) -> None:
    """Request specific fields to optimize response size."""
    print("\n=== Pattern 5: Optimized with opt_fields ===")

    # Request only fields you need - reduces payload size
    # Especially important for large datasets
    tasks = await client.tasks.list_async(
        project=project_gid,
        opt_fields=["name", "completed", "due_on"],
    ).take(3)

    print(f"Retrieved {len(tasks)} tasks with minimal fields:")
    for task in tasks:
        print(f"  - {task.name}")
        print(f"    Due: {task.due_on or 'No date'}")
        print(f"    Complete: {task.completed}")


async def main(project_gid: str) -> None:
    """Run all pagination examples."""
    print("autom8_asana SDK - Pagination Examples")
    print("\nPageIterator provides lazy, memory-efficient pagination.")
    print("Choose the pattern that fits your use case.")

    async with AsanaClient() as client:
        # Pattern 1: async for (most flexible)
        await demonstrate_async_for(client, project_gid)

        # Pattern 2: collect() (simplest)
        await demonstrate_collect(client, project_gid)

        # Pattern 3: take(n) (first N)
        await demonstrate_take(client, project_gid)

        # Pattern 4: first() (single item)
        await demonstrate_first(client, project_gid)

        # Pattern 5: Field optimization
        await demonstrate_opt_fields(client, project_gid)

    print("\n=== Complete ===")
    print("Key Takeaways:")
    print("  - Use 'async for' when you might exit early")
    print("  - Use '.collect()' when you need all items as a list")
    print("  - Use '.take(n)' for first N items")
    print("  - Use '.first()' for single item or existence check")
    print("  - Use 'opt_fields' to minimize payload size")


if __name__ == "__main__":
    parser = ArgumentParser(description="Demonstrate pagination patterns")
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
