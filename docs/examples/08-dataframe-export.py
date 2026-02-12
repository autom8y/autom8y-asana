#!/usr/bin/env python3
"""Export DataFrames from Asana project data.

This example demonstrates:
- Fetching task data as structured DataFrames via REST API
- Using different schema types for specialized data extraction
- Content negotiation for JSON vs Polars serialization formats
- Pagination through large result sets
- Processing DataFrame data with Polars

Available schemas:
- base: Generic task properties (name, gid, completed, etc.)
- unit: Unit-specific task data
- contact: Contact-specific task data
- business: Business-specific task data
- offer: Offer-specific task data
- asset_edit: Asset edit task data
- asset_edit_holder: Asset edit holder task data

Usage:
    export API_BASE_URL="http://localhost:8000"
    export ASANA_PAT="your_token_here"
    export PROJECT_GID="1234567890123456"
    .venv/bin/python docs/examples/08-dataframe-export.py

Prerequisites:
- Python 3.10+
- httpx, polars installed
- autom8_asana API server running
- Valid Asana PAT with read access

Related docs:
    - docs/design/TDD-dynamic-schema-api.md
    - src/autom8_asana/api/routes/dataframes.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any


async def fetch_dataframe_json(
    base_url: str,
    token: str,
    project_gid: str,
    schema: str = "base",
    limit: int = 100,
) -> dict[str, Any]:
    """Fetch project tasks as DataFrame in JSON format.

    Args:
        base_url: API base URL (e.g., "http://localhost:8000")
        token: Asana PAT for Bearer authentication
        project_gid: Asana project GID
        schema: Schema name for extraction (default: "base")
        limit: Number of items per page (default: 100, max: 100)

    Returns:
        Response dict with "data" (list of records) and "meta" (pagination info)
    """
    import httpx

    url = f"{base_url}/api/v1/dataframes/project/{project_gid}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    params = {
        "schema": schema,
        "limit": limit,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


async def fetch_dataframe_polars(
    base_url: str,
    token: str,
    project_gid: str,
    schema: str = "base",
    limit: int = 100,
):
    """Fetch project tasks as DataFrame in Polars format.

    This format is more efficient for clients that can deserialize
    Polars DataFrames directly, avoiding JSON record conversion.

    Args:
        base_url: API base URL
        token: Asana PAT for Bearer authentication
        project_gid: Asana project GID
        schema: Schema name for extraction (default: "base")
        limit: Number of items per page (default: 100, max: 100)

    Returns:
        Polars DataFrame with task data
    """
    import httpx
    import polars as pl
    from io import StringIO

    url = f"{base_url}/api/v1/dataframes/project/{project_gid}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/x-polars-json",
    }
    params = {
        "schema": schema,
        "limit": limit,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()

        # Response contains {"data": polars_json_string, "meta": {...}}
        response_data = response.json()
        polars_json = response_data["data"]

        # Deserialize the Polars JSON format
        df = pl.read_json(StringIO(polars_json))
        return df, response_data["meta"]


async def fetch_dataframe_paginated(
    base_url: str,
    token: str,
    project_gid: str,
    schema: str = "base",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Fetch all pages of DataFrame data and combine into single list.

    Args:
        base_url: API base URL
        token: Asana PAT for Bearer authentication
        project_gid: Asana project GID
        schema: Schema name for extraction (default: "base")
        limit: Number of items per page (default: 50, max: 100)

    Returns:
        List of all records across all pages
    """
    import httpx

    all_records = []
    offset = None

    url = f"{base_url}/api/v1/dataframes/project/{project_gid}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        while True:
            # Build request params with optional offset
            params: dict[str, Any] = {
                "schema": schema,
                "limit": limit,
            }
            if offset is not None:
                params["offset"] = offset

            # Fetch the current page
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            response_data = response.json()
            data = response_data["data"]
            meta = response_data["meta"]

            # Append records from this page
            all_records.extend(data)

            # Check for more pages
            pagination = meta.get("pagination", {})
            has_more = pagination.get("has_more", False)
            offset = pagination.get("next_offset")

            print(f"  Fetched page: {len(data)} records (total: {len(all_records)})")

            if not has_more or offset is None:
                break

    return all_records


async def main() -> None:
    """Demonstrate DataFrame export in multiple formats."""

    # Get configuration from environment
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
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

    print(f"API Base URL: {base_url}")
    print(f"Project GID: {project_gid}")
    print()

    try:
        # Example 1: Fetch DataFrame in JSON format
        print("Example 1: Fetching DataFrame as JSON records...")
        print("=" * 60)

        response = await fetch_dataframe_json(
            base_url=base_url,
            token=token,
            project_gid=project_gid,
            schema="base",
            limit=10,
        )

        records = response["data"]
        meta = response["meta"]

        print(f"Request ID: {meta['request_id']}")
        print(f"Fetched {len(records)} records")

        # Display first few records
        for idx, record in enumerate(records[:3], 1):
            print(f"\nRecord {idx}:")
            print(f"  GID: {record.get('gid')}")
            print(f"  Name: {record.get('name')}")
            print(f"  Completed: {record.get('completed')}")

        print()

        # Example 2: Fetch DataFrame in Polars format (more efficient)
        print("\nExample 2: Fetching DataFrame in Polars format...")
        print("=" * 60)

        df, meta = await fetch_dataframe_polars(
            base_url=base_url,
            token=token,
            project_gid=project_gid,
            schema="base",
            limit=10,
        )

        print(f"Request ID: {meta['request_id']}")
        print(f"DataFrame shape: {df.shape} (rows, columns)")
        print(f"\nColumns: {df.columns}")
        print(f"\nFirst 3 rows:")
        print(df.head(3))

        # Demonstrate Polars operations
        print(f"\nCompleted tasks: {df.filter(df['completed'] == True).height}")
        print(f"Incomplete tasks: {df.filter(df['completed'] == False).height}")

        print()

        # Example 3: Pagination through large result sets
        print("\nExample 3: Paginating through all records...")
        print("=" * 60)

        all_records = await fetch_dataframe_paginated(
            base_url=base_url,
            token=token,
            project_gid=project_gid,
            schema="base",
            limit=20,  # Small page size to demonstrate pagination
        )

        print(f"\nTotal records fetched: {len(all_records)}")

        # Example 4: Using specialized schemas
        print("\nExample 4: Using specialized schemas...")
        print("=" * 60)

        # Try fetching with different schemas
        # Note: The actual data returned depends on the schema extractors
        schemas_to_try = ["base", "unit", "business"]

        for schema_name in schemas_to_try:
            try:
                response = await fetch_dataframe_json(
                    base_url=base_url,
                    token=token,
                    project_gid=project_gid,
                    schema=schema_name,
                    limit=5,
                )
                records = response["data"]
                print(f"  Schema '{schema_name}': {len(records)} records")

                # Show columns available in first record
                if records:
                    columns = list(records[0].keys())
                    print(f"    Columns: {', '.join(columns[:5])}...")

            except Exception as exc:
                # Schema may not be applicable to this project's tasks
                print(f"  Schema '{schema_name}': Error - {exc}")

        print()

    except Exception as exc:
        print(f"ERROR: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
