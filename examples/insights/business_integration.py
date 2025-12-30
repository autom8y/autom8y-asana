"""Example: Business Entity Insights Integration

Demonstrates:
- Loading a Business entity from Asana
- Using Business.get_insights_async() convenience method
- Automatic phone/vertical extraction from Business fields

Requirements:
- ASANA_PAT environment variable set
- AUTOM8_DATA_TOKEN environment variable set
- Valid Business task GID with office_phone and vertical fields populated

Usage:
    export ASANA_PAT="your_asana_token"
    export AUTOM8_DATA_TOKEN="your_s2s_token"
    python examples/insights/business_integration.py --gid BUSINESS_GID

Output:
    Business details and associated insights data
"""

import asyncio
from argparse import ArgumentParser

from autom8_asana import AsanaClient
from autom8_asana.clients.data import DataServiceClient
from autom8_asana.models.business.business import Business


async def main(business_gid: str) -> None:
    """Load a Business and fetch its insights."""
    print("autom8_asana SDK - Business Entity Insights Integration")
    print("=" * 50)

    # Create both clients
    async with AsanaClient() as asana_client:
        # Load the Business entity (includes full hierarchy hydration)
        print(f"\nLoading Business: {business_gid}")
        business = await Business.from_gid_async(asana_client, business_gid)

        print(f"Business name: {business.name}")
        print(f"Office phone: {business.office_phone}")
        print(f"Vertical: {business.vertical}")

        # Validate Business has required fields for insights
        if not business.office_phone:
            print("\nError: Business does not have office_phone set")
            print("Cannot fetch insights without office_phone field")
            return

        if not business.vertical:
            print("\nError: Business does not have vertical set")
            print("Cannot fetch insights without vertical field")
            return

        # Fetch insights using the Business convenience method
        async with DataServiceClient() as data_client:
            print("\nFetching account insights...")
            response = await business.get_insights_async(
                client=data_client,
                factory="account",
                period="lifetime",
            )

            print(f"\nInsights for {business.name}:")
            print(f"  Row count: {response.metadata.row_count}")
            print(f"  Cache hit: {response.metadata.cache_hit}")
            print(f"  Request ID: {response.request_id}")

            # Convert to DataFrame
            df = response.to_dataframe()
            print(f"\nDataFrame columns: {list(df.columns)}")
            print("\nData preview:")
            print(df.head())


async def with_multiple_factories(business_gid: str) -> None:
    """Fetch different insight types for a Business."""
    print("\n" + "=" * 50)
    print("Multiple Factories Example")
    print("=" * 50)

    async with AsanaClient() as asana_client:
        business = await Business.from_gid_async(asana_client, business_gid)

        if not business.office_phone or not business.vertical:
            print("Skipping: Business missing required fields")
            return

        async with DataServiceClient() as data_client:
            # Fetch different insight types
            factories = ["account", "leads", "spend"]

            for factory in factories:
                try:
                    response = await business.get_insights_async(
                        client=data_client,
                        factory=factory,
                        period="t30",
                    )
                    print(f"\n{factory.upper()} insights:")
                    print(f"  Rows: {response.metadata.row_count}")
                except Exception as e:
                    print(f"\n{factory.upper()} insights: Error - {e}")


async def without_hydration(business_gid: str) -> None:
    """Load Business without full hydration (faster for insights-only use)."""
    print("\n" + "=" * 50)
    print("Without Hydration Example (Faster)")
    print("=" * 50)

    async with AsanaClient() as asana_client:
        # Skip hydration when you only need insights
        # This is faster as it doesn't load contacts, units, etc.
        business = await Business.from_gid_async(
            asana_client,
            business_gid,
            hydrate=False,  # Skip holder hydration
        )

        print(f"Business: {business.name}")
        print(f"Contacts loaded: {len(business.contacts)}")  # Will be 0

        # Insights still work - only needs office_phone and vertical
        if business.office_phone and business.vertical:
            async with DataServiceClient() as data_client:
                response = await business.get_insights_async(
                    client=data_client,
                    factory="account",
                )
                print(f"Insights rows: {response.metadata.row_count}")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Demonstrate Business entity insights integration"
    )
    parser.add_argument(
        "--gid",
        required=True,
        help="Business task GID from Asana",
    )
    args = parser.parse_args()

    asyncio.run(main(args.gid))
    asyncio.run(with_multiple_factories(args.gid))
    asyncio.run(without_hydration(args.gid))
