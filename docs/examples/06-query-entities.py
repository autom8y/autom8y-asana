#!/usr/bin/env python3
"""Query Cached Entities

Demonstrates using the query API to fetch entity data with filters and
section-based filtering. Shows both simple row queries and filtered queries
using the composable predicate system.

Prerequisites:
    pip install autom8y-asana httpx
    export SERVICE_TOKEN="your_service_token"
    export API_BASE_URL="http://localhost:8000"  # or production URL

Related docs:
    - docs/guides/entity-query.md
"""
import asyncio
import os

import httpx


async def main():
    """Query entities using the query API."""
    # Get configuration from environment
    service_token = os.getenv("SERVICE_TOKEN")
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    if not service_token:
        print("Error: SERVICE_TOKEN must be set")
        return

    # Set up API client with service authentication
    headers = {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(base_url=api_base_url, headers=headers, timeout=30.0) as client:
        # Example 1: Simple query - fetch all businesses
        print("=" * 60)
        print("Example 1: Fetch all businesses")
        print("=" * 60)

        response = await client.post(
            "/v1/query/business/rows",
            json={
                "limit": 10,
                "offset": 0
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Total businesses: {data['meta']['total_count']}")
            print(f"Returned: {data['meta']['returned_count']}")
            print(f"Query time: {data['meta']['query_ms']}ms\n")

            print("First 3 businesses:")
            for row in data["data"][:3]:
                print(f"  - {row.get('Business Name', 'N/A')} (GID: {row.get('gid', 'N/A')})")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        # Example 2: Filtered query with WHERE clause
        print("\n" + "=" * 60)
        print("Example 2: Query offers in a specific section")
        print("=" * 60)

        # Query offers in "Sales Process" section with active status
        response = await client.post(
            "/v1/query/offer/rows",
            json={
                "section": "Sales Process",  # Section filter
                "where": {
                    "op": "eq",
                    "field": "Status",
                    "value": "Active"
                },
                "limit": 5
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Active offers in Sales Process: {data['meta']['returned_count']}")
            print(f"Query time: {data['meta']['query_ms']}ms\n")

            for row in data["data"]:
                offer_name = row.get("Offer Name", "N/A")
                status = row.get("Status", "N/A")
                vertical = row.get("Vertical", "N/A")
                print(f"  - {offer_name}")
                print(f"    Status: {status}, Vertical: {vertical}")
        elif response.status_code == 503:
            print("Cache not warmed. Please wait and retry.")
            print(response.json())
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        # Example 3: Compound query with AND predicates
        print("\n" + "=" * 60)
        print("Example 3: Query units with compound filters")
        print("=" * 60)

        # Query units that are both in "Next Steps" section AND have a specific vertical
        response = await client.post(
            "/v1/query/unit/rows",
            json={
                "section": "Next Steps",
                "where": {
                    "and": [
                        {
                            "op": "eq",
                            "field": "Vertical",
                            "value": "Dental"
                        },
                        {
                            "op": "ne",
                            "field": "Status",
                            "value": "Paused"
                        }
                    ]
                },
                "limit": 10
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Matching units: {data['meta']['returned_count']}")
            print(f"Query time: {data['meta']['query_ms']}ms\n")

            if data["data"]:
                for row in data["data"]:
                    unit_name = row.get("Unit Name", "N/A")
                    status = row.get("Status", "N/A")
                    vertical = row.get("Vertical", "N/A")
                    print(f"  - {unit_name}")
                    print(f"    Status: {status}, Vertical: {vertical}")
            else:
                print("  No units matched the criteria")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        # Example 4: Pagination - fetch next page of results
        print("\n" + "=" * 60)
        print("Example 4: Pagination example")
        print("=" * 60)

        # First page
        response = await client.post(
            "/v1/query/business/rows",
            json={
                "limit": 5,
                "offset": 0
            }
        )

        if response.status_code == 200:
            data = response.json()
            total = data['meta']['total_count']
            print(f"Total businesses: {total}")
            print(f"Page 1 (0-5): {data['meta']['returned_count']} results")

            # Second page
            response = await client.post(
                "/v1/query/business/rows",
                json={
                    "limit": 5,
                    "offset": 5
                }
            )

            if response.status_code == 200:
                data = response.json()
                print(f"Page 2 (5-10): {data['meta']['returned_count']} results")
                print(f"Query time: {data['meta']['query_ms']}ms")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

        print("\n" + "=" * 60)
        print("Query examples complete")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
