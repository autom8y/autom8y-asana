"""Example: Batch Insights Request

Demonstrates:
- Fetching insights for multiple businesses in a single call
- Using PhoneVerticalPair for type-safe business identifiers
- Handling partial failures in batch responses
- Combining results into a single DataFrame

Requirements:
- AUTOM8_DATA_TOKEN environment variable set (S2S JWT token)
- Valid business phone numbers and verticals

Usage:
    export AUTOM8_DATA_TOKEN="your_s2s_token_here"
    python examples/insights/batch_request.py

Output:
    Batch results showing success/failure counts and combined DataFrame
"""

import asyncio

from autom8_asana.clients.data import DataServiceClient
from autom8_asana.models.contracts import PhoneVerticalPair


async def main() -> None:
    """Fetch insights for multiple businesses concurrently."""
    print("autom8_asana SDK - Batch Insights Request Example")
    print("=" * 50)

    # Define businesses to query using PhoneVerticalPair
    # This provides type-safe phone number validation (E.164 format)
    pairs = [
        PhoneVerticalPair(office_phone="+17705551234", vertical="chiropractic"),
        PhoneVerticalPair(office_phone="+17705555678", vertical="dental"),
        PhoneVerticalPair(office_phone="+14155559999", vertical="medspa"),
    ]

    async with DataServiceClient() as client:
        # Fetch insights for all businesses concurrently
        # max_concurrency controls parallel request limit (default: 10)
        batch_response = await client.get_insights_batch_async(
            pairs=pairs,
            factory="account",
            period="t30",
            max_concurrency=5,
        )

        # Check results summary
        print(f"\nBatch Results:")
        print(f"  Total requests: {batch_response.total_count}")
        print(f"  Successful: {batch_response.success_count}")
        print(f"  Failed: {batch_response.failure_count}")
        print(f"  Request ID: {batch_response.request_id}")

        # Access individual results by canonical key
        for pvp in pairs:
            result = batch_response.results.get(pvp.canonical_key)
            if result and result.success:
                print(f"\n{pvp.canonical_key}:")
                print(f"  Rows: {result.response.metadata.row_count}")
            elif result:
                print(f"\n{pvp.canonical_key}: FAILED")
                print(f"  Error: {result.error}")

        # Combine all successful results into a single DataFrame
        # Each row includes a _pvp_key column for identification
        if batch_response.success_count > 0:
            combined_df = batch_response.to_dataframe()
            print(f"\nCombined DataFrame shape: {combined_df.shape}")
            print("\nDataFrame preview:")
            print(combined_df.head())


async def handle_partial_failures() -> None:
    """Demonstrate handling of partial failures in batch requests."""
    print("\n" + "=" * 50)
    print("Partial Failure Handling Example")
    print("=" * 50)

    # Mix of valid and potentially invalid businesses
    pairs = [
        PhoneVerticalPair(office_phone="+17705551234", vertical="chiropractic"),
        PhoneVerticalPair(office_phone="+10000000000", vertical="unknown"),  # May fail
    ]

    async with DataServiceClient() as client:
        batch_response = await client.get_insights_batch_async(
            pairs=pairs,
            factory="account",
        )

        # Process only successful results
        successful_results = [
            result for result in batch_response.results.values()
            if result.success
        ]

        print(f"\nProcessed {len(successful_results)} successful results")

        # Log failures for investigation
        failed_results = [
            (key, result.error)
            for key, result in batch_response.results.items()
            if not result.success
        ]

        if failed_results:
            print("\nFailed requests (for investigation):")
            for key, error in failed_results:
                print(f"  {key}: {error}")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(handle_partial_failures())
