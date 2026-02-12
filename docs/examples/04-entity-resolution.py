"""Resolve business identifiers to Asana task GIDs via REST API.

This example demonstrates the entity resolution API:
- Discovering queryable fields via schema endpoint
- Single entity resolution with phone + vertical
- Batch resolution with multiple criteria
- Handling resolution results (found, not found, ambiguous)

The resolution API maps business identifiers (phone number + vertical)
to Asana task GIDs without requiring direct SDK access.

Usage:
    export API_BASE_URL=http://localhost:8000
    export SERVICE_TOKEN=your_s2s_jwt_token_here
    .venv/bin/python docs/examples/04-entity-resolution.py

Prerequisites:
- Python 3.10+
- httpx installed
- autom8_asana API server running
- Valid S2S JWT token (PATs are not supported)
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx


async def get_entity_schema(
    client: httpx.AsyncClient,
    entity_type: str,
) -> dict:
    """Fetch queryable fields for an entity type.

    The schema endpoint returns metadata about which fields can be used
    in resolution criteria and what fields can be returned in results.

    Args:
        client: Authenticated HTTP client
        entity_type: Entity type (unit, business, offer, contact)

    Returns:
        Schema response with queryable_fields list

    Raises:
        httpx.HTTPStatusError: On 404 (unknown entity) or 401 (auth failure)
    """
    url = f"/v1/resolve/{entity_type}/schema"

    print(f"GET {url}")
    response = await client.get(url)
    response.raise_for_status()

    return response.json()


async def resolve_single(
    client: httpx.AsyncClient,
    entity_type: str,
    criterion: dict,
) -> dict:
    """Resolve a single criterion to a task GID.

    Args:
        client: Authenticated HTTP client
        entity_type: Entity type (unit, business, offer, contact)
        criterion: Single resolution criterion (e.g., {"phone": "+1...", "vertical": "dental"})

    Returns:
        Resolution response with results list

    Raises:
        httpx.HTTPStatusError: On 404, 401, 422, or 503
    """
    url = f"/v1/resolve/{entity_type}"

    payload = {"criteria": [criterion]}

    print(f"POST {url}")
    print(f"  Criteria: {criterion}")

    response = await client.post(url, json=payload)
    response.raise_for_status()

    return response.json()


async def resolve_batch(
    client: httpx.AsyncClient,
    entity_type: str,
    criteria: list[dict],
) -> dict:
    """Resolve multiple criteria in a single request.

    The API processes up to 1000 criteria per request. Results are returned
    in the same order as the input criteria.

    Args:
        client: Authenticated HTTP client
        entity_type: Entity type (unit, business, offer, contact)
        criteria: List of resolution criteria (max 1000)

    Returns:
        Resolution response with results list

    Raises:
        httpx.HTTPStatusError: On 404, 401, 422, or 503
    """
    url = f"/v1/resolve/{entity_type}"

    payload = {"criteria": criteria}

    print(f"POST {url}")
    print(f"  Criteria count: {len(criteria)}")

    response = await client.post(url, json=payload)
    response.raise_for_status()

    return response.json()


def print_schema_info(schema: dict) -> None:
    """Display schema information in a readable format."""
    print(f"\nEntity Type: {schema['entity_type']}")
    print(f"Schema Version: {schema['version']}")
    print(f"\nQueryable Fields ({len(schema['queryable_fields'])}):")

    for field in schema["queryable_fields"]:
        desc = f" - {field['description']}" if field.get("description") else ""
        print(f"  {field['name']:<20} ({field['type']}){desc}")


def print_resolution_results(response: dict) -> None:
    """Display resolution results in a readable format."""
    meta = response["meta"]
    results = response["results"]

    print(f"\nResolution Summary:")
    print(f"  Entity Type: {meta['entity_type']}")
    print(f"  Project GID: {meta['project_gid']}")
    print(f"  Resolved: {meta['resolved_count']}")
    print(f"  Unresolved: {meta['unresolved_count']}")

    if meta.get("criteria_schema"):
        print(f"  Criteria Fields: {', '.join(meta['criteria_schema'])}")

    print(f"\nResults ({len(results)}):")

    for i, result in enumerate(results, start=1):
        # Display resolution outcome
        if result["gid"]:
            print(f"  [{i}] FOUND")
            print(f"      GID: {result['gid']}")

            # Show all matching GIDs if multiple matches
            if result.get("gids") and len(result["gids"]) > 1:
                print(f"      All GIDs: {', '.join(result['gids'])}")
                print(f"      Match Count: {result['match_count']} (AMBIGUOUS)")

        else:
            error_code = result.get("error", "UNKNOWN")
            print(f"  [{i}] NOT FOUND")
            print(f"      Error: {error_code}")

        # Display enriched field data if present (Phase 2 feature)
        if result.get("data"):
            print(f"      Data: {result['data']}")


async def main() -> None:
    """Execute the entity resolution examples."""

    # Step 1: Get credentials from environment
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    service_token = os.getenv("SERVICE_TOKEN")

    if not service_token:
        print("ERROR: SERVICE_TOKEN environment variable not set")
        print("Set it with: export SERVICE_TOKEN=your_s2s_jwt_token_here")
        print("\nNote: This endpoint requires S2S JWT tokens. PATs are not supported.")
        sys.exit(1)

    print("=" * 70)
    print("Entity Resolution API Example")
    print("=" * 70)
    print(f"API Base URL: {api_base_url}")
    print(f"Entity Type: unit")

    # Step 2: Create authenticated HTTP client
    headers = {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(
        base_url=api_base_url,
        headers=headers,
        timeout=30.0,
    ) as client:

        try:
            # Step 3: Discover schema
            print("\n" + "=" * 70)
            print("STEP 1: Discover queryable fields")
            print("=" * 70)

            schema = await get_entity_schema(client, "unit")
            print_schema_info(schema)

            # Step 4: Single resolution
            print("\n" + "=" * 70)
            print("STEP 2: Resolve single unit")
            print("=" * 70)

            single_criterion = {
                "phone": "+15551234567",
                "vertical": "dental",
            }

            single_response = await resolve_single(
                client,
                "unit",
                single_criterion,
            )
            print_resolution_results(single_response)

            # Step 5: Batch resolution
            print("\n" + "=" * 70)
            print("STEP 3: Batch resolve multiple units")
            print("=" * 70)

            batch_criteria = [
                {"phone": "+15551234567", "vertical": "dental"},
                {"phone": "+15559876543", "vertical": "medical"},
                {"phone": "+15555555555", "vertical": "legal"},  # Likely not found
            ]

            batch_response = await resolve_batch(
                client,
                "unit",
                batch_criteria,
            )
            print_resolution_results(batch_response)

            # Step 6: Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)

            print("\nKey Observations:")
            print("  - Schema endpoint returns valid criterion fields dynamically")
            print("  - Single and batch resolution use the same endpoint")
            print("  - Results maintain input order (result[i] matches criteria[i])")
            print("  - Unresolved criteria return gid=null with error code")
            print("  - Ambiguous matches return first GID + all GIDs + match count")

            print("\nNext Steps:")
            print("  - Use resolved GIDs with Asana API (tasks.get_async)")
            print("  - Handle NOT_FOUND by creating new entities")
            print("  - Handle AMBIGUOUS by adding discriminators to criteria")
            print("  - Batch requests for efficiency (up to 1000 criteria)")

        except httpx.HTTPStatusError as exc:
            # Handle HTTP errors with detailed information
            print(f"\nHTTP ERROR: {exc.response.status_code}")

            try:
                error_detail = exc.response.json()
                print(f"Error Code: {error_detail.get('error', 'UNKNOWN')}")
                print(f"Message: {error_detail.get('message', 'No message')}")

                # Display available entity types on 404
                if exc.response.status_code == 404:
                    if available := error_detail.get("available_types"):
                        print(f"Available Types: {', '.join(available)}")

            except Exception:
                # Fallback if response body is not JSON
                print(f"Response: {exc.response.text}")

            sys.exit(1)

        except httpx.RequestError as exc:
            # Handle connection errors
            print(f"\nCONNECTION ERROR: {exc}")
            print(f"\nIs the API server running at {api_base_url}?")
            sys.exit(1)

        except Exception as exc:
            # Handle unexpected errors
            print(f"\nUNEXPECTED ERROR: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
