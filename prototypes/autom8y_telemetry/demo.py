"""Demo script showing autom8y-telemetry POC integration.

This demonstrates the end-to-end integration pattern:
1. Initialize telemetry (one-line setup)
2. Create rate limiter
3. Make instrumented HTTP request
4. Observe spans in console output

Run: python prototypes/autom8y_telemetry/demo.py

NOTE: Requires opentelemetry packages installed:
    pip install opentelemetry-api opentelemetry-sdk httpx
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import POC modules
from telemetry import init_telemetry, start_span
from http_client import TelemetryHTTPClient
from rate_limiter import TokenBucketRateLimiter


async def main():
    """Run demo showing telemetry integration."""
    print("=== autom8y-telemetry POC Demo ===\n")

    # Step 1: Initialize telemetry (one-line setup)
    print("1. Initializing telemetry...")
    tracer = init_telemetry("autom8y-telemetry-demo")
    print("   ✓ Telemetry initialized with console exporter\n")

    # Step 2: Create rate limiter
    print("2. Creating rate limiter...")
    rate_limiter = TokenBucketRateLimiter(
        max_tokens=10,
        refill_period=1.0,
    )
    print(f"   ✓ Rate limiter created: {rate_limiter.get_stats()}\n")

    # Step 3: Create instrumented HTTP client
    print("3. Creating instrumented HTTP client...")
    async with TelemetryHTTPClient(
        rate_limiter=rate_limiter,
        base_url="https://httpbin.org",
    ) as client:
        print("   ✓ HTTP client created with rate limiting + OTel spans\n")

        # Step 4: Make HTTP request with automatic instrumentation
        print("4. Making HTTP request to httpbin.org...")
        print("   (Watch for span output below)\n")

        with start_span("demo_operation") as span:
            span.set_attribute("demo.version", "1.0")
            span.set_attribute("demo.type", "poc")

            # This creates nested span automatically
            response = await client.get("/get", params={"demo": "true"})

            span.set_attribute("response.status", response.status_code)
            print(f"   ✓ Response received: HTTP {response.status_code}\n")

    # Step 5: Show final stats
    print("5. Final rate limiter stats:")
    stats = rate_limiter.get_stats()
    print(f"   - Available tokens: {stats['available_tokens']:.1f}")
    print(f"   - Utilization: {stats['utilization']:.1%}")
    print(f"   - Refill rate: {stats['refill_rate']:.1f} tokens/sec\n")

    print("=== Demo Complete ===")
    print("\nCheck console output above for OpenTelemetry span exports.")
    print("You should see two spans:")
    print("  1. 'demo_operation' (parent span)")
    print("  2. 'HTTP GET' (nested span for HTTP request)")
    print("\nEach span includes trace_id, span_id, and custom attributes.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ModuleNotFoundError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("\nInstall required packages:")
        print("  pip install opentelemetry-api opentelemetry-sdk httpx\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
