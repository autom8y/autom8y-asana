"""Example: Error Handling for Insights API

Demonstrates:
- Exception hierarchy for insights API
- Handling validation errors (InsightsValidationError)
- Handling not found errors (InsightsNotFoundError)
- Handling service errors (InsightsServiceError)
- Graceful degradation with stale cache fallback
- Circuit breaker behavior

Requirements:
- AUTOM8_DATA_TOKEN environment variable set (S2S JWT token)

Usage:
    export AUTOM8_DATA_TOKEN="your_s2s_token_here"
    python examples/insights/error_handling.py

Output:
    Examples of different error scenarios and handling strategies
"""

import asyncio

from autom8_asana.clients.data import DataServiceClient
from autom8_asana.exceptions import (
    InsightsError,
    InsightsNotFoundError,
    InsightsServiceError,
    InsightsValidationError,
)


async def demonstrate_validation_error() -> None:
    """Show InsightsValidationError handling."""
    print("\n=== InsightsValidationError ===")
    print("Raised for invalid inputs (400-level errors)")

    async with DataServiceClient() as client:
        try:
            # Invalid factory name will trigger validation error
            await client.get_insights_async(
                factory="invalid_factory",
                office_phone="+17705551234",
                vertical="chiropractic",
            )
        except InsightsValidationError as e:
            print(f"\nCaught InsightsValidationError:")
            print(f"  Message: {e}")
            print(f"  Field: {e.field}")
            print(f"  Request ID: {e.request_id}")

            # Handle specific validation errors
            if e.field == "factory":
                print("\nValid factories: account, ads, adsets, campaigns, etc.")

        try:
            # Invalid phone format will also trigger validation error
            await client.get_insights_async(
                factory="account",
                office_phone="not-a-phone",  # Invalid E.164 format
                vertical="chiropractic",
            )
        except InsightsValidationError as e:
            print(f"\nPhone validation error:")
            print(f"  Field: {e.field}")
            print(f"  Message: {e}")


async def demonstrate_not_found_error() -> None:
    """Show InsightsNotFoundError handling."""
    print("\n=== InsightsNotFoundError ===")
    print("Raised when no data exists for the business (404)")

    async with DataServiceClient() as client:
        try:
            # Non-existent business
            await client.get_insights_async(
                factory="account",
                office_phone="+10000000000",  # Unlikely to exist
                vertical="unknown_vertical",
            )
        except InsightsNotFoundError as e:
            print(f"\nCaught InsightsNotFoundError:")
            print(f"  Message: {e}")
            print(f"  Request ID: {e.request_id}")

            # Graceful handling - return empty result
            print("\nGraceful handling: Return empty DataFrame instead")
            return None


async def demonstrate_service_error() -> None:
    """Show InsightsServiceError handling."""
    print("\n=== InsightsServiceError ===")
    print("Raised for upstream service failures (5xx, timeouts)")

    # Note: This would normally occur when autom8_data is unavailable
    # We show the error handling pattern here

    example_code = '''
    try:
        response = await client.get_insights_async(
            factory="account",
            office_phone="+17705551234",
            vertical="chiropractic",
        )
    except InsightsServiceError as e:
        print(f"Service error: {e}")
        print(f"  Reason: {e.reason}")  # timeout, circuit_breaker, server_error
        print(f"  Status code: {e.status_code}")  # 500, 502, 503, 504

        # Handle based on reason
        if e.reason == "circuit_breaker":
            print("Service is degraded - try again later")
        elif e.reason == "timeout":
            print("Request timed out - consider smaller query")
        else:
            print("Server error - retry with exponential backoff")
    '''
    print("\nExample handling pattern:")
    print(example_code)


async def demonstrate_stale_cache_fallback() -> None:
    """Show stale cache fallback behavior."""
    print("\n=== Stale Cache Fallback ===")
    print("When service fails, stale cached data may be returned")

    example_code = '''
    # With cache provider configured, stale data is returned on failure
    response = await client.get_insights_async(
        factory="account",
        office_phone="+17705551234",
        vertical="chiropractic",
    )

    # Check if response is from stale cache
    if response.metadata.is_stale:
        print("Warning: Using stale cached data")
        print(f"  Cached at: {response.metadata.cached_at}")
        print(f"  Warnings: {response.warnings}")

        # Data may be outdated but still useful for display
        df = response.to_dataframe()
        # ... use with appropriate staleness indication in UI
    '''
    print("\nStale cache behavior:")
    print(example_code)


async def demonstrate_circuit_breaker() -> None:
    """Show circuit breaker behavior."""
    print("\n=== Circuit Breaker ===")
    print("Protects against cascade failures when service is degraded")

    async with DataServiceClient() as client:
        # Monitor circuit breaker state
        print(f"\nCircuit breaker state: {client.circuit_breaker.state}")
        print(f"Failure count: {client.circuit_breaker.failure_count}")

        example_code = '''
        # When circuit is open, requests fail fast
        try:
            response = await client.get_insights_async(...)
        except InsightsServiceError as e:
            if e.reason == "circuit_breaker":
                # Circuit is open - service appears degraded
                # Don't retry immediately, wait for recovery
                print(f"Circuit breaker open: {e}")
                # Consider using cached data or showing degraded state
        '''
        print("\nCircuit breaker handling:")
        print(example_code)


async def comprehensive_error_handling() -> None:
    """Show comprehensive error handling pattern."""
    print("\n=== Comprehensive Error Handling Pattern ===")

    async with DataServiceClient() as client:

        async def get_insights_safe(
            phone: str,
            vertical: str,
            factory: str = "account",
        ) -> dict | None:
            """Get insights with comprehensive error handling.

            Returns dict with data and metadata, or None on failure.
            """
            try:
                response = await client.get_insights_async(
                    factory=factory,
                    office_phone=phone,
                    vertical=vertical,
                )

                return {
                    "data": response.to_dataframe(),
                    "is_stale": response.metadata.is_stale,
                    "row_count": response.metadata.row_count,
                    "request_id": response.request_id,
                }

            except InsightsValidationError as e:
                # Log validation errors (likely a bug in calling code)
                print(f"Validation error for {phone}: {e.field} - {e}")
                return None

            except InsightsNotFoundError:
                # No data for this business - not an error
                print(f"No insights data for {phone}")
                return None

            except InsightsServiceError as e:
                # Service issues - log and degrade gracefully
                print(f"Service error ({e.reason}) for {phone}: {e}")
                return None

            except InsightsError as e:
                # Catch-all for any other insights errors
                print(f"Unexpected insights error for {phone}: {e}")
                return None

        # Example usage
        result = await get_insights_safe("+17705551234", "chiropractic")
        if result:
            print(f"\nGot {result['row_count']} rows (stale={result['is_stale']})")
        else:
            print("\nNo data available - showing empty state")


async def main() -> None:
    """Run all error handling examples."""
    print("autom8_asana SDK - Insights Error Handling Examples")
    print("=" * 50)

    # Validation errors
    await demonstrate_validation_error()

    # Not found errors
    await demonstrate_not_found_error()

    # Service errors (pattern only)
    await demonstrate_service_error()

    # Stale cache (pattern only)
    await demonstrate_stale_cache_fallback()

    # Circuit breaker
    await demonstrate_circuit_breaker()

    # Comprehensive pattern
    await comprehensive_error_handling()

    print("\n" + "=" * 50)
    print("Key Takeaways:")
    print("  - InsightsValidationError: Bad inputs (factory, phone, period)")
    print("  - InsightsNotFoundError: No data for business (expected case)")
    print("  - InsightsServiceError: Service unavailable (retry or degrade)")
    print("  - All inherit from InsightsError (catch-all)")
    print("  - Check is_stale for cache fallback responses")
    print("  - Monitor circuit_breaker.state for service health")


if __name__ == "__main__":
    asyncio.run(main())
