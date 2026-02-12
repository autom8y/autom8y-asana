#!/usr/bin/env python3
"""Cache warming and inspection operations.

This example demonstrates:
- Triggering manual cache refresh for entity types
- Incremental vs. full rebuild strategies
- Inspecting cache status and metrics
- Service-to-service authentication with JWT tokens
- Background task monitoring

The cache refresh endpoint is an admin operation that requires
service-to-service JWT authentication. It accepts requests to
refresh cache for one or all entity types.

Refresh strategies:
- Incremental (default): Resumes from existing manifests, only fetches changed sections
- Full rebuild: Deletes all cached data and triggers Lambda cache warmer

Usage:
    export API_BASE_URL="http://localhost:8000"
    export SERVICE_TOKEN="your_s2s_jwt_token"
    export ENTITY_TYPE="offer"  # Optional, defaults to all types
    .venv/bin/python docs/examples/09-cache-warming.py

Prerequisites:
- Python 3.10+
- httpx installed
- autom8_asana API server running
- Valid S2S JWT token with admin permissions

Related docs:
    - src/autom8_asana/api/routes/admin.py
    - docs/design/TDD-cache-freshness-remediation.md
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any


async def refresh_cache(
    base_url: str,
    service_token: str,
    entity_type: str | None = None,
    force_full_rebuild: bool = False,
) -> dict[str, Any]:
    """Trigger cache refresh via admin endpoint.

    This operation runs asynchronously in the background and returns
    immediately with 202 Accepted.

    Args:
        base_url: API base URL (e.g., "http://localhost:8000")
        service_token: S2S JWT token for authentication
        entity_type: Specific entity type to refresh (None = all types)
        force_full_rebuild: If True, delete all cache and rebuild from scratch

    Returns:
        Response dict with refresh details and refresh_id for tracking
    """
    import httpx

    url = f"{base_url}/v1/admin/cache/refresh"
    headers = {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "entity_type": entity_type,
        "force_full_rebuild": force_full_rebuild,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def check_health(base_url: str) -> dict[str, Any]:
    """Check API health status.

    The health endpoint provides information about cache initialization,
    registry readiness, and other system status.

    Args:
        base_url: API base URL

    Returns:
        Health status dict
    """
    import httpx

    url = f"{base_url}/health"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_cache_metrics(
    base_url: str,
    service_token: str,
) -> dict[str, Any]:
    """Fetch cache metrics from internal admin endpoint.

    Note: This is a hypothetical endpoint for demonstration.
    Actual implementation may vary.

    Args:
        base_url: API base URL
        service_token: S2S JWT token for authentication

    Returns:
        Cache metrics dict
    """
    import httpx

    # Hypothetical metrics endpoint
    url = f"{base_url}/v1/admin/cache/metrics"
    headers = {
        "Authorization": f"Bearer {service_token}",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                # Endpoint not yet implemented
                return {
                    "error": "Metrics endpoint not available",
                    "status": "not_implemented",
                }
            raise


async def monitor_refresh_progress(
    base_url: str,
    refresh_id: str,
    max_wait_seconds: int = 60,
) -> None:
    """Poll health endpoint to monitor cache refresh progress.

    This is a simplified monitoring approach. Production systems
    would use structured logging, metrics, or event streams.

    Args:
        base_url: API base URL
        refresh_id: Refresh ID returned from cache refresh request
        max_wait_seconds: Maximum time to wait for completion
    """
    start_time = time.time()
    poll_interval = 5  # seconds

    print(f"Monitoring refresh {refresh_id}...")
    print(f"Polling every {poll_interval} seconds (max {max_wait_seconds}s)")

    while time.time() - start_time < max_wait_seconds:
        # Check health status (simplified - real implementation would
        # check specific refresh status via dedicated endpoint)
        health = await check_health(base_url)

        status = health.get("status", "unknown")
        print(f"  [{int(time.time() - start_time)}s] Health status: {status}")

        if status == "healthy":
            # In a real system, we'd check if this specific refresh_id
            # has completed via a dedicated status endpoint
            print("  System is healthy (refresh may be complete)")

        # Wait before next poll
        await asyncio.sleep(poll_interval)

    print("Monitoring timeout reached")


async def main() -> None:
    """Demonstrate cache warming and inspection operations."""

    # Get configuration from environment
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    service_token = os.getenv("SERVICE_TOKEN")
    entity_type = os.getenv("ENTITY_TYPE")  # Optional

    if not service_token:
        print("ERROR: SERVICE_TOKEN environment variable not set")
        print("Set it with: export SERVICE_TOKEN=your_s2s_jwt_token")
        sys.exit(1)

    print(f"API Base URL: {base_url}")
    print(f"Entity Type: {entity_type or '(all types)'}")
    print()

    try:
        # Example 1: Check system health before refresh
        print("Example 1: Checking system health...")
        print("=" * 60)

        health = await check_health(base_url)
        print(f"Status: {health.get('status')}")
        print(f"Timestamp: {health.get('timestamp')}")

        # Display cache-related health info if available
        cache_status = health.get("cache", {})
        if cache_status:
            print(f"Cache initialized: {cache_status.get('initialized', False)}")

        print()

        # Example 2: Trigger incremental cache refresh
        print("\nExample 2: Triggering incremental cache refresh...")
        print("=" * 60)

        refresh_response = await refresh_cache(
            base_url=base_url,
            service_token=service_token,
            entity_type=entity_type,
            force_full_rebuild=False,
        )

        print(f"Status: {refresh_response['status']}")
        print(f"Message: {refresh_response['message']}")
        print(f"Refresh ID: {refresh_response['refresh_id']}")
        print(f"Entity Types: {', '.join(refresh_response['entity_types'])}")
        print(f"Force Full Rebuild: {refresh_response['force_full_rebuild']}")

        refresh_id = refresh_response['refresh_id']

        print("\nCache refresh initiated in background")
        print("Note: Refresh runs asynchronously and may take several minutes")

        print()

        # Example 3: Monitor refresh progress (simplified)
        print("\nExample 3: Monitoring refresh progress...")
        print("=" * 60)

        # Wait a moment for refresh to start
        await asyncio.sleep(2)

        # Monitor for a short period (in production, you'd wait longer)
        try:
            await monitor_refresh_progress(
                base_url=base_url,
                refresh_id=refresh_id,
                max_wait_seconds=20,  # Short timeout for demo
            )
        except asyncio.TimeoutError:
            print("Monitoring timed out (refresh continues in background)")

        print()

        # Example 4: Check cache metrics (if available)
        print("\nExample 4: Checking cache metrics...")
        print("=" * 60)

        metrics = await get_cache_metrics(
            base_url=base_url,
            service_token=service_token,
        )

        if metrics.get("status") == "not_implemented":
            print("Cache metrics endpoint not yet implemented")
        else:
            print(f"Cache metrics: {metrics}")

        print()

        # Example 5: Trigger full rebuild (commented out - destructive operation)
        print("\nExample 5: Full rebuild (demonstration only)...")
        print("=" * 60)
        print("Full rebuild is a destructive operation that:")
        print("  1. Deletes all cached data (memory, S3 manifests, parquet files)")
        print("  2. Triggers Lambda cache warmer for rebuild")
        print("  3. Prevents OOM by delegating to Lambda")
        print()
        print("To trigger full rebuild, uncomment the code below:")
        print()
        print("# full_rebuild_response = await refresh_cache(")
        print("#     base_url=base_url,")
        print("#     service_token=service_token,")
        print("#     entity_type=entity_type,")
        print("#     force_full_rebuild=True,")
        print("# )")
        print("# print(f'Full rebuild initiated: {full_rebuild_response}')")

        print()

        # Example 6: Error handling
        print("\nExample 6: Error handling...")
        print("=" * 60)

        # Demonstrate invalid entity type
        try:
            await refresh_cache(
                base_url=base_url,
                service_token=service_token,
                entity_type="invalid_entity_type",
                force_full_rebuild=False,
            )
        except Exception as exc:
            print(f"Expected error for invalid entity type: {exc}")
            # Parse error response if available
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    error_data = exc.response.json()
                    print(f"  Error code: {error_data.get('error')}")
                    print(f"  Message: {error_data.get('message')}")
                except Exception:
                    pass

        print()
        print("Cache warming examples complete!")

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
