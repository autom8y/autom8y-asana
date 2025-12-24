#!/usr/bin/env python3
"""Demo: Parallel Section Fetch Performance with Cache Optimization.

Demonstrates the Watermark Cache and Task-level cache performance improvements:
- Parallel section fetch vs. serial pagination
- Task-level cache hit/miss behavior
- Cache metrics and performance timing
- Zero-configuration usage

Usage:
    # By project name (will resolve GID automatically)
    python scripts/demo_parallel_fetch.py --name "Business Offers"

    # By project GID
    python scripts/demo_parallel_fetch.py --gid 1205571477139891

    # Compare serial vs parallel
    python scripts/demo_parallel_fetch.py --name "Business Offers" --compare

    # Show verbose cache metrics
    python scripts/demo_parallel_fetch.py --name "Business Offers" --metrics
"""

from __future__ import annotations

import argparse
import asyncio
import time
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from autom8_asana.client import AsanaClient


async def resolve_project_gid(client: AsanaClient, name: str, workspace_gid: str) -> str | None:
    """Resolve project name to GID (case-insensitive)."""
    name_lower = name.lower()
    async for project in client.projects.list_async(
        workspace=workspace_gid, opt_fields=["name"]
    ):
        if project.name and project.name.lower() == name_lower:
            gid: str = project.gid
            return gid
    return None


def print_cache_metrics(
    cold_time: float,
    warm_time: float,
    task_count: int,
    show_metrics: bool = False,
) -> None:
    """Print cache performance metrics.

    Args:
        cold_time: Time for cold fetch in seconds.
        warm_time: Time for warm fetch in seconds.
        task_count: Number of tasks fetched.
        show_metrics: If True, show detailed metrics breakdown.
    """
    print(f"\n{'-'*60}")
    print("CACHE METRICS SUMMARY")
    print(f"{'-'*60}")

    # Calculate hit rate (approximation: warm time << cold time means high hit rate)
    if cold_time > 0:
        speedup = cold_time / warm_time if warm_time > 0 else float("inf")
        estimated_hit_rate = max(0.0, min(1.0, 1.0 - (warm_time / cold_time)))
    else:
        speedup = 1.0
        estimated_hit_rate = 0.0

    print(f"  Tasks: {task_count}")
    print(f"  Cold fetch time: {cold_time:.2f}s")
    print(f"  Warm fetch time: {warm_time:.2f}s")
    print(f"  Cache speedup: {speedup:.1f}x faster")
    print(f"  Estimated hit rate: {estimated_hit_rate:.0%}")

    # Performance target validation
    print(f"\n  Performance Targets:")
    warm_target_met = warm_time < 1.0
    print(f"    Warm fetch < 1.0s: {'PASS' if warm_target_met else 'FAIL'} ({warm_time:.2f}s)")

    if show_metrics:
        print(f"\n  Timing Breakdown (estimated):")
        lookup_time = warm_time * 0.1  # ~10% for cache lookup
        extract_time = warm_time * 0.9  # ~90% for extraction
        print(f"    Cache lookup: ~{lookup_time*1000:.0f}ms")
        print(f"    DataFrame extraction: ~{extract_time*1000:.0f}ms")

        print(f"\n  Cache Efficiency:")
        api_time_saved = cold_time - warm_time
        print(f"    API time saved: {api_time_saved:.2f}s")
        print(f"    API calls avoided: ~{task_count} task fetches")


async def demo_parallel_fetch(
    project_gid: str,
    project_name: str | None = None,
    compare: bool = False,
    verbose: bool = False,
    show_metrics: bool = False,
) -> None:
    """Run the parallel fetch demonstration.

    Args:
        project_gid: GID of the project to fetch.
        project_name: Optional name for display.
        compare: If True, run both serial and parallel for comparison.
        verbose: Enable verbose output.
        show_metrics: If True, show detailed cache metrics.
    """
    client = AsanaClient()

    try:
        # Get project
        print(f"\n{'='*60}")
        print("  Parallel Section Fetch Demo")
        print(f"{'='*60}")

        project = await client.projects.get_async(
            project_gid,
            opt_fields=["name", "gid"]
        )
        display_name = project_name or project.name
        print(f"\nProject: {display_name} ({project_gid})")

        # Count sections first
        sections = await client.sections.list_for_project_async(
            project_gid, opt_fields=["name"]
        ).collect()
        print(f"Sections: {len(sections)}")
        for s in sections[:5]:
            print(f"  - {s.name}")
        if len(sections) > 5:
            print(f"  ... and {len(sections) - 5} more")

        print(f"\n{'-'*60}")
        print("PARALLEL FETCH (new method)")
        print(f"{'-'*60}")

        # Parallel fetch (cold)
        start = time.perf_counter()
        df_parallel = await project.to_dataframe_parallel_async(
            client,
            task_type="*",  # All task types
            use_cache=False,  # Skip cache for fair comparison
        )
        parallel_time = time.perf_counter() - start

        print(f"Tasks fetched: {len(df_parallel)}")
        print(f"Time (cold): {parallel_time:.2f}s")
        print(f"Columns: {df_parallel.columns[:5]}..." if len(df_parallel.columns) > 5 else f"Columns: {df_parallel.columns}")

        if verbose and len(df_parallel) > 0:
            print(f"\nFirst 3 tasks:")
            print(df_parallel.select(["gid", "name"]).head(3))

        if compare:
            print(f"\n{'-'*60}")
            print("SERIAL FETCH (original method)")
            print(f"{'-'*60}")

            # Serial fetch using original method
            start = time.perf_counter()
            df_serial = await project.to_dataframe_parallel_async(
                client,
                task_type="*",
                use_parallel_fetch=False,  # Force serial
                use_cache=False,
            )
            serial_time = time.perf_counter() - start

            print(f"Tasks fetched: {len(df_serial)}")
            print(f"Time (serial): {serial_time:.2f}s")

            # Comparison
            print(f"\n{'-'*60}")
            print("COMPARISON")
            print(f"{'-'*60}")
            print(f"Parallel: {parallel_time:.2f}s")
            print(f"Serial:   {serial_time:.2f}s")
            if serial_time > 0:
                speedup = serial_time / parallel_time
                print(f"Speedup:  {speedup:.1f}x faster")

        # Demonstrate cache (warm fetch)
        print(f"\n{'-'*60}")
        print("CACHE DEMONSTRATION")
        print(f"{'-'*60}")

        print("\nFirst fetch (cache miss - populates cache):")
        start = time.perf_counter()
        df1 = await project.to_dataframe_parallel_async(
            client,
            task_type="*",
            use_cache=True,  # Enable cache
        )
        cold_time = time.perf_counter() - start
        print(f"  Tasks: {len(df1)}, Time: {cold_time:.2f}s")

        print("\nSecond fetch (cache hit - should be faster):")
        start = time.perf_counter()
        df2 = await project.to_dataframe_parallel_async(
            client,
            task_type="*",
            use_cache=True,
        )
        warm_time = time.perf_counter() - start
        print(f"  Tasks: {len(df2)}, Time: {warm_time:.2f}s")

        if cold_time > 0:
            print(f"\n  Cache speedup: {cold_time/warm_time:.1f}x faster")

        # Print detailed cache metrics
        print_cache_metrics(
            cold_time=cold_time,
            warm_time=warm_time,
            task_count=len(df1),
            show_metrics=show_metrics,
        )

        print(f"\n{'='*60}")
        print("  Demo Complete")
        print(f"{'='*60}\n")

    finally:
        await client.close()


async def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Demo: Parallel Section Fetch Performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # By project name
    python scripts/demo_parallel_fetch.py --name "Business Offers"

    # By project GID
    python scripts/demo_parallel_fetch.py --gid 1205571477139891

    # Compare serial vs parallel timing
    python scripts/demo_parallel_fetch.py --name "Business Offers" --compare

    # Verbose output
    python scripts/demo_parallel_fetch.py --name "Business Offers" -v

    # Show detailed cache metrics
    python scripts/demo_parallel_fetch.py --name "Business Offers" --metrics
"""
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", "-n", help="Project name to fetch (case-insensitive)")
    group.add_argument("--gid", "-g", help="Project GID to fetch")

    parser.add_argument("--compare", "-c", action="store_true",
                       help="Compare serial vs parallel fetch times")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show verbose output")
    parser.add_argument("--metrics", "-m", action="store_true",
                       help="Show detailed cache metrics and timing breakdown")
    parser.add_argument("--workspace", "-w", default="1143357799778608",
                       help="Workspace GID (default: 1143357799778608)")

    args = parser.parse_args()

    project_gid = args.gid
    project_name = args.name

    # Resolve name to GID if needed
    if args.name and not args.gid:
        print(f"Resolving project name: '{args.name}'...")
        client = AsanaClient()
        try:
            project_gid = await resolve_project_gid(client, args.name, args.workspace)
            if not project_gid:
                print(f"Error: Could not find project named '{args.name}'")
                return 1
            print(f"Found: {project_gid}")
        finally:
            await client.close()

    await demo_parallel_fetch(
        project_gid=project_gid,
        project_name=project_name,
        compare=args.compare,
        verbose=args.verbose,
        show_metrics=args.metrics,
    )

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
