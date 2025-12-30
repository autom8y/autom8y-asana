"""Example: Single Insights Request

Demonstrates:
- Basic DataServiceClient usage with async context manager
- Fetching account insights for a single business
- Accessing response metadata and converting to DataFrame

Requirements:
- AUTOM8_DATA_TOKEN environment variable set (S2S JWT token)
- Valid business phone number and vertical

Usage:
    export AUTOM8_DATA_TOKEN="your_s2s_token_here"
    python examples/insights/single_request.py

Output:
    Insights data for the specified business, including row count and DataFrame
"""

import asyncio

from autom8_asana.clients.data import DataServiceClient


async def main() -> None:
    """Fetch insights for a single business."""
    print("autom8_asana SDK - Single Insights Request Example")
    print("=" * 50)

    async with DataServiceClient() as client:
        # Fetch account insights for a business
        # Parameters:
        #   factory: The insights factory (account, ads, campaigns, etc.)
        #   office_phone: E.164 formatted phone number
        #   vertical: Business vertical (chiropractic, dental, etc.)
        #   period: Time period (lifetime, t30, l7, etc.)
        response = await client.get_insights_async(
            factory="account",
            office_phone="+17705551234",
            vertical="chiropractic",
            period="t30",
        )

        # Access response metadata
        print(f"\nFactory: {response.metadata.factory}")
        print(f"Period: {response.metadata.insights_period}")
        print(f"Row count: {response.metadata.row_count}")
        print(f"Column count: {response.metadata.column_count}")
        print(f"Cache hit: {response.metadata.cache_hit}")
        print(f"Request ID: {response.request_id}")

        # Check for any warnings
        if response.warnings:
            print(f"\nWarnings: {response.warnings}")

        # Convert to pandas DataFrame for analysis
        df = response.to_dataframe()
        print(f"\nDataFrame shape: {df.shape}")
        print("\nDataFrame preview:")
        print(df.head())

        # Access raw data if needed
        print(f"\nRaw data rows: {len(response.data)}")


async def with_custom_options() -> None:
    """Demonstrate advanced query options."""
    print("\n" + "=" * 50)
    print("Advanced Options Example")
    print("=" * 50)

    async with DataServiceClient() as client:
        # Request with custom metrics and dimensions
        response = await client.get_insights_async(
            factory="account",
            office_phone="+17705551234",
            vertical="chiropractic",
            period="lifetime",
            # Force refresh from source (bypass autom8_data cache)
            refresh=True,
            # Optional: specify metrics to include
            # metrics=["spend", "leads", "cpl"],
            # Optional: group by dimensions
            # dimensions=["date"],
        )

        print(f"Retrieved {response.metadata.row_count} rows")
        print(f"Columns: {[col.name for col in response.metadata.columns]}")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(with_custom_options())
