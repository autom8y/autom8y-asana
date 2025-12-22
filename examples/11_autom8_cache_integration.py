"""Example: autom8 Cache Integration

Demonstrates:
- Creating Redis cache provider for autom8 integration
- Migrating load_task_collection() to SDK caching
- Pre-warming cache for high-traffic projects
- Monitoring cache health and metrics
- Graceful degradation when Redis unavailable

Requirements:
- Redis server running (local or ElastiCache)
- Environment variables configured (see Environment section)

Environment:
    export REDIS_HOST="localhost"  # Or ElastiCache endpoint
    export REDIS_PORT="6379"
    export REDIS_SSL="false"       # Set "true" for ElastiCache

Usage:
    # With local Redis
    docker run -d -p 6379:6379 redis:7
    python examples/11_autom8_cache_integration.py

    # With mock data (no Redis required)
    python examples/11_autom8_cache_integration.py --mock

Output:
    Cache integration examples with metrics
"""

from __future__ import annotations

import asyncio
import os
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Any


# Mock implementations for demonstration without actual Redis/Asana
# In production, these would be actual API calls


@dataclass
class MockTask:
    """Mock task for demonstration."""

    gid: str
    name: str
    modified_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "name": self.name,
            "modified_at": self.modified_at,
        }


MOCK_TASKS = [
    MockTask("1001", "Task Alpha", "2025-01-15T10:00:00Z"),
    MockTask("1002", "Task Beta", "2025-01-15T11:00:00Z"),
    MockTask("1003", "Task Gamma", "2025-01-15T12:00:00Z"),
    MockTask("1004", "Task Delta", "2025-01-15T13:00:00Z"),
    MockTask("1005", "Task Epsilon", "2025-01-15T14:00:00Z"),
]


async def mock_batch_api(gids: list[str]) -> dict[str, str]:
    """Mock batch API that returns modified_at timestamps.

    In production, this calls Asana's batch API:
    POST /batch with GET /tasks/{gid}?opt_fields=modified_at
    """
    await asyncio.sleep(0.01)  # Simulate network latency
    result = {}
    for gid in gids:
        for task in MOCK_TASKS:
            if task.gid == gid:
                result[gid] = task.modified_at
                break
    return result


async def mock_task_fetcher(gids: list[str]) -> list[dict[str, Any]]:
    """Mock task fetcher that returns full task data.

    In production, this fetches tasks from Asana API.
    """
    await asyncio.sleep(0.05)  # Simulate network latency
    result = []
    for gid in gids:
        for task in MOCK_TASKS:
            if task.gid == gid:
                result.append(task.to_dict())
                break
    return result


async def mock_project_task_fetcher(project_gid: str) -> list[dict[str, Any]]:
    """Mock project task fetcher.

    In production, this fetches all tasks from a project.
    """
    await asyncio.sleep(0.1)  # Simulate network latency
    return [task.to_dict() for task in MOCK_TASKS]


# ============================================================================
# Example: Creating Cache Provider
# ============================================================================


def example_create_provider(use_mock: bool = True) -> None:
    """Demonstrate creating a cache provider for autom8."""
    print("\n=== Example 1: Creating Cache Provider ===")

    if use_mock:
        print("Running with mock data (no Redis required)")
        print("To use real Redis, run without --mock flag")
        return

    try:
        from autom8_asana.cache.autom8_adapter import (
            create_autom8_cache_provider,
            check_redis_health,
        )

        # Create provider from environment variables
        cache = create_autom8_cache_provider()

        # Check health
        health = check_redis_health(cache)

        if health["healthy"]:
            print("Redis connection established successfully")
            print(f"Metrics: {health['metrics']}")
        else:
            print(f"Redis connection failed: {health['error']}")

    except Exception as e:
        print(f"Error creating cache provider: {e}")
        print("\nEnsure Redis is running and environment variables are set:")
        print("  export REDIS_HOST='localhost'")
        print("  export REDIS_PORT='6379'")
        print("  export REDIS_SSL='false'")


# ============================================================================
# Example: Migrating Task Collection Loading
# ============================================================================


async def example_migrate_task_collection(use_mock: bool = True) -> None:
    """Demonstrate migrating load_task_collection() to SDK caching."""
    print("\n=== Example 2: Migrating Task Collection Loading ===")

    # Sample task dicts (as would come from project query)
    task_dicts = [{"gid": task.gid} for task in MOCK_TASKS]

    print(f"Input: {len(task_dicts)} task GIDs to load")

    if use_mock:
        # Demonstrate the flow without actual Redis
        print("\nMock demonstration of migration flow:")
        print("1. Extract GIDs from task_dicts")
        print("2. Fetch current modified_at via batch API (25s TTL cached)")
        print("3. Check staleness against Redis cache")
        print("4. Fetch stale tasks from API")
        print("5. Update Redis cache with fresh data")
        print("6. Return merged task list")

        # Simulate the result
        print("\nSimulated MigrationResult:")
        print(f"  total_tasks: {len(task_dicts)}")
        print("  cache_hits: 0 (cold cache)")
        print(f"  cache_misses: {len(task_dicts)}")
        print("  hit_rate: 0.0%")
        print(f"  tasks: [{len(task_dicts)} task dicts returned]")
        return

    try:
        from autom8_asana.cache.autom8_adapter import (
            create_autom8_cache_provider,
            migrate_task_collection_loading,
        )

        cache = create_autom8_cache_provider()

        # First call - cache is cold, all misses
        print("\n--- First Call (Cold Cache) ---")
        result = await migrate_task_collection_loading(
            task_dicts=task_dicts,
            cache=cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        print(f"Total tasks: {result.total_tasks}")
        print(f"Cache hits: {result.cache_hits}")
        print(f"Cache misses: {result.cache_misses}")
        print(f"Hit rate: {result.hit_rate:.1f}%")
        print(f"Tasks returned: {len(result.tasks)}")

        # Second call - cache is warm, all hits (within TTL)
        print("\n--- Second Call (Warm Cache) ---")
        result2 = await migrate_task_collection_loading(
            task_dicts=task_dicts,
            cache=cache,
            batch_api=mock_batch_api,
            task_fetcher=mock_task_fetcher,
        )

        print(f"Total tasks: {result2.total_tasks}")
        print(f"Cache hits: {result2.cache_hits}")
        print(f"Cache misses: {result2.cache_misses}")
        print(f"Hit rate: {result2.hit_rate:.1f}%")

    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example: Pre-Warming Cache
# ============================================================================


async def example_warm_cache(use_mock: bool = True) -> None:
    """Demonstrate pre-warming cache for high-traffic projects."""
    print("\n=== Example 3: Pre-Warming Cache ===")

    if use_mock:
        print("Mock demonstration of cache warming:")
        print("  Project GID: project_123")
        print(f"  Tasks warmed: {len(MOCK_TASKS)}")
        print("\nUse warm_project_tasks() after deployment to")
        print("reduce cache miss spike for high-traffic projects.")
        return

    try:
        from autom8_asana.cache.autom8_adapter import (
            create_autom8_cache_provider,
            warm_project_tasks,
        )

        cache = create_autom8_cache_provider()

        # Warm cache for a project
        warmed = await warm_project_tasks(
            cache=cache,
            project_gid="project_123",
            task_fetcher=mock_project_task_fetcher,
        )

        print(f"Warmed {warmed} tasks for project_123")

    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example: Monitoring and Health Checks
# ============================================================================


async def example_monitoring(use_mock: bool = True) -> None:
    """Demonstrate monitoring cache health and metrics."""
    print("\n=== Example 4: Monitoring and Health Checks ===")

    if use_mock:
        print("Mock demonstration of health check:")
        print("  healthy: True")
        print("  metrics:")
        print("    total_hits: 100")
        print("    total_misses: 25")
        print("    total_writes: 125")
        print("    total_errors: 0")
        print("    hit_rate: 80.0%")
        print("\nIntegrate check_redis_health() into your /health endpoint")
        return

    try:
        from autom8_asana.cache.autom8_adapter import (
            create_autom8_cache_provider,
            check_redis_health,
        )

        cache = create_autom8_cache_provider()
        health = check_redis_health(cache)

        print(f"Healthy: {health['healthy']}")
        if health["metrics"]:
            print("Metrics:")
            for key, value in health["metrics"].items():
                print(f"  {key}: {value}")

        if health["error"]:
            print(f"Error: {health['error']}")

    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example: Production Integration Pattern
# ============================================================================


def example_production_pattern() -> None:
    """Show production integration pattern for autom8."""
    print("\n=== Example 5: Production Integration Pattern ===")

    code = '''
# Production pattern for autom8 services

from autom8_asana.cache.autom8_adapter import (
    create_autom8_cache_provider,
    migrate_task_collection_loading,
    check_redis_health,
    MigrationResult,
)

# Initialize cache provider once (singleton pattern)
_cache = None

def get_cache():
    """Get or create cache provider singleton."""
    global _cache
    if _cache is None:
        _cache = create_autom8_cache_provider()
    return _cache


# Replace legacy load_task_collection()
async def load_task_collection(task_dicts: list[dict]) -> list[dict]:
    """Load tasks using SDK cache instead of legacy S3."""
    cache = get_cache()

    result: MigrationResult = await migrate_task_collection_loading(
        task_dicts=task_dicts,
        cache=cache,
        batch_api=get_batch_modifications,  # Your batch API
        task_fetcher=fetch_tasks,           # Your task fetcher
    )

    # Log metrics for monitoring
    LOG.info(
        "task_collection_loaded",
        total=result.total_tasks,
        hits=result.cache_hits,
        misses=result.cache_misses,
        hit_rate=f"{result.hit_rate:.1f}%",
    )

    return result.tasks


# Add to health check endpoint
@app.route("/health")
async def health():
    cache_health = check_redis_health(get_cache())
    return {
        "status": "healthy" if cache_health["healthy"] else "degraded",
        "cache": cache_health,
    }
'''

    print(code)


# ============================================================================
# Example: Graceful Degradation
# ============================================================================


async def example_graceful_degradation(use_mock: bool = True) -> None:
    """Demonstrate graceful degradation when Redis unavailable."""
    print("\n=== Example 6: Graceful Degradation ===")

    print("When Redis is unavailable, the SDK enters degraded mode:")
    print("  - Cache operations return miss/no-op")
    print("  - API calls continue to function (100% miss)")
    print("  - No data loss (cache is not source of truth)")
    print("  - Auto-reconnection attempts every 30 seconds")

    code = '''
# Graceful degradation pattern

async def load_tasks_with_fallback(task_dicts: list[dict]) -> list[dict]:
    """Load tasks with graceful fallback if cache unavailable."""
    try:
        cache = get_cache()

        # Check if cache is healthy
        if not cache.is_healthy():
            LOG.warning("cache_unhealthy", action="falling_back_to_api")
            return await fetch_all_tasks(task_dicts)

        # Normal path with caching
        result = await migrate_task_collection_loading(...)
        return result.tasks

    except Exception as e:
        LOG.error("cache_error", error=str(e), action="falling_back_to_api")
        # Fallback: fetch directly from API
        return await fetch_all_tasks(task_dicts)
'''

    print(code)


# ============================================================================
# Main
# ============================================================================


async def main(use_mock: bool = True) -> None:
    """Run all autom8 cache integration examples."""
    print("autom8_asana SDK - autom8 Cache Integration Examples")
    print("=" * 60)

    # Check environment
    redis_host = os.environ.get("REDIS_HOST")
    if not use_mock and not redis_host:
        print("\nWARNING: REDIS_HOST not set")
        print("Examples will show code patterns but skip live operations")
        print("Set REDIS_HOST=localhost to run with local Redis")
        use_mock = True

    # Example 1: Creating provider
    example_create_provider(use_mock)

    # Example 2: Migrating task collection
    await example_migrate_task_collection(use_mock)

    # Example 3: Pre-warming cache
    await example_warm_cache(use_mock)

    # Example 4: Monitoring
    await example_monitoring(use_mock)

    # Example 5: Production pattern
    example_production_pattern()

    # Example 6: Graceful degradation
    await example_graceful_degradation(use_mock)

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("""
Key Integration Steps:
1. Set environment variables (REDIS_HOST, REDIS_PORT, REDIS_SSL)
2. Import SDK adapter: from autom8_asana.cache.autom8_adapter import ...
3. Create cache provider: cache = create_autom8_cache_provider()
4. Replace load_task_collection() with migrate_task_collection_loading()
5. Add health check: check_redis_health(cache)
6. Optional: Pre-warm high-traffic projects with warm_project_tasks()

For complete migration guide, see:
  docs/guides/autom8-migration.md

For architecture decisions, see:
  docs/decisions/ADR-0025-migration-strategy.md
""")


if __name__ == "__main__":
    parser = ArgumentParser(description="autom8 cache integration examples")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run with mock data (no Redis required)",
    )
    args = parser.parse_args()

    asyncio.run(main(use_mock=args.mock))
