"""Example: Error Handling and Observability

Demonstrates:
- Exception hierarchy and specific error types
- Accessing error details and correlation IDs
- Graceful degradation patterns
- Retry logic for transient failures
- Validation errors
- Production-ready error handling

Requirements:
- ASANA_PAT environment variable set
- Valid workspace GID (provide via --workspace arg)

Usage:
    export ASANA_PAT="your_token_here"
    python examples/10_error_handling.py --workspace WORKSPACE_GID

Output:
    Examples of different error types and handling strategies
"""

import asyncio
from argparse import ArgumentParser

from autom8_asana import AsanaClient
from autom8_asana.errors import (
    AsanaError,
    AuthenticationError,
    NotFoundError,
)
from _config import get_workspace_gid, get_config_instructions


async def demonstrate_not_found_error(client: AsanaClient) -> None:
    """Show NotFoundError handling."""
    print("\n=== NotFoundError (404) ===")

    try:
        # Try to get a task that doesn't exist
        await client.tasks.get_async("invalid_task_gid")
    except NotFoundError as e:
        print(f"Caught NotFoundError: {e.message}")
        print(f"  Status code: {e.status_code}")
        print(f"  Errors: {e.errors}")

        # Graceful degradation - return None or default value
        print("\nGraceful handling: Return None instead of crashing")
        return None


async def demonstrate_rate_limit_error(client: AsanaClient) -> None:
    """Show RateLimitError handling with retry logic."""
    print("\n=== RateLimitError (429) ===")

    print("RateLimitError includes retry_after attribute:")
    print("  - Tells you how long to wait before retrying")
    print("  - SDK handles most rate limiting automatically")
    print("  - This example shows manual handling if needed")

    example_code = """
try:
    task = await client.tasks.get_async("123")
except RateLimitError as e:
    if e.retry_after:
        print(f"Rate limited. Retry after {e.retry_after} seconds")
        await asyncio.sleep(e.retry_after)
        task = await client.tasks.get_async("123")  # Retry
    else:
        print("Rate limited. Wait and retry later")
"""
    print(example_code)


async def demonstrate_authentication_error() -> None:
    """Show AuthenticationError handling."""
    print("\n=== AuthenticationError (401) ===")

    try:
        # Create client with invalid token
        client = AsanaClient(token="invalid_token")
        await client.tasks.get_async("123")
    except AuthenticationError as e:
        print(f"Caught AuthenticationError: {e.message}")
        print(f"  Status code: {e.status_code}")
        print("\nAction: Check your ASANA_PAT token")
        print("  - Verify token is valid")
        print("  - Ensure token hasn't expired")
        print("  - Check token has required permissions")


async def demonstrate_forbidden_error(client: AsanaClient) -> None:
    """Show ForbiddenError handling."""
    print("\n=== ForbiddenError (403) ===")

    print("ForbiddenError occurs when:")
    print("  - Token lacks required permissions")
    print("  - Workspace/project access denied")
    print("  - Resource is in a premium-only workspace")

    print("\nHandling:")
    example_code = """
try:
    project = await client.projects.get_async("private_project_gid")
except ForbiddenError as e:
    print(f"Access denied: {e.message}")
    # Check user permissions or request access
"""
    print(example_code)


async def demonstrate_correlation_id(client: AsanaClient, workspace_gid: str) -> None:
    """Show how to access correlation IDs for debugging."""
    print("\n=== Correlation IDs for Debugging ===")

    try:
        # Make a request
        task = await client.tasks.create_async(
            name="Error Handling Example",
            workspace=workspace_gid,
        )

        # Delete it
        await client.tasks.delete_async(task.gid)

        # Try to access it (will 404)
        await client.tasks.get_async(task.gid)

    except NotFoundError as e:
        # Correlation ID is in the response headers
        if e.response:
            request_id = e.response.headers.get("X-Request-Id")
            print(f"Request failed with correlation ID: {request_id}")
            print("  - Include this ID when contacting Asana support")
            print("  - Helps Asana engineers debug the issue")
            print("  - Available on all AsanaError instances")


async def demonstrate_server_error() -> None:
    """Show ServerError handling."""
    print("\n=== ServerError (5xx) ===")

    print("ServerError indicates Asana API issues:")
    print("  - 500: Internal server error")
    print("  - 502: Bad gateway")
    print("  - 503: Service unavailable")

    print("\nHandling with exponential backoff:")
    example_code = """
import asyncio

max_retries = 3
for attempt in range(max_retries):
    try:
        task = await client.tasks.get_async("123")
        break
    except ServerError as e:
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            print(f"Server error, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
        else:
            print("Max retries exceeded")
            raise
"""
    print(example_code)


async def demonstrate_timeout_error() -> None:
    """Show TimeoutError handling."""
    print("\n=== TimeoutError ===")

    print("TimeoutError occurs when request takes too long:")
    print("  - Network issues")
    print("  - Slow API responses")
    print("  - Large data transfers")

    print("\nHandling:")
    example_code = """
from autom8_asana import AsanaClient
from autom8_asana.config import AsanaConfig, TimeoutConfig

# Configure custom timeout
config = AsanaConfig(
    timeout=TimeoutConfig(
        total=30.0,  # 30 second total timeout
        connect=5.0,  # 5 second connect timeout
    )
)

client = AsanaClient(config=config)

try:
    task = await client.tasks.get_async("123")
except TimeoutError as e:
    print(f"Request timed out: {e.message}")
    # Retry or handle appropriately
"""
    print(example_code)


async def demonstrate_validation_error() -> None:
    """Show validation error handling (Pydantic)."""
    print("\n=== Validation Errors ===")

    print("Pydantic ValidationError for invalid data:")
    print("  - Invalid GID format")
    print("  - Missing required fields")
    print("  - Type mismatches")

    example_code = """
from pydantic import ValidationError

try:
    # Create task with invalid data
    task = await client.tasks.create_async(
        name="",  # Empty name - invalid
        workspace="workspace_gid",
    )
except ValidationError as e:
    print(f"Validation error: {e}")
    # Handle validation issues before sending to API
"""
    print(example_code)


async def demonstrate_graceful_degradation(
    client: AsanaClient, workspace_gid: str
) -> None:
    """Show graceful degradation pattern."""
    print("\n=== Graceful Degradation Pattern ===")

    async def get_task_safe(task_gid: str) -> dict | None:
        """Get task with graceful degradation.

        Returns None instead of raising exception if task not found.
        """
        try:
            return await client.tasks.get_async(task_gid)
        except NotFoundError:
            return None
        except AsanaError as e:
            # Log error but don't crash
            print(f"Warning: Failed to fetch task {task_gid}: {e.message}")
            return None

    # Example usage
    task = await client.tasks.create_async(
        name="Graceful Degradation Example",
        workspace=workspace_gid,
    )

    # This works
    result = await get_task_safe(task.gid)
    print(f"Found task: {result.name if result else None}")

    # Delete task
    await client.tasks.delete_async(task.gid)

    # This returns None instead of crashing
    result = await get_task_safe(task.gid)
    print(f"Task after deletion: {result}")

    print("\nPattern: Return None/default instead of raising")
    print("  - Prevents cascade failures")
    print("  - Enables partial success")
    print("  - Better UX for end users")


async def main(workspace_gid: str) -> None:
    """Run all error handling examples."""
    print("autom8_asana SDK - Error Handling Examples")

    async with AsanaClient() as client:
        # Example 1: NotFoundError
        await demonstrate_not_found_error(client)

        # Example 2: RateLimitError
        await demonstrate_rate_limit_error(client)

        # Example 3: AuthenticationError (separate client)
        # await demonstrate_authentication_error()  # Skipped - would fail

        # Example 4: ForbiddenError
        await demonstrate_forbidden_error(client)

        # Example 5: Correlation IDs
        await demonstrate_correlation_id(client, workspace_gid)

        # Example 6: ServerError
        await demonstrate_server_error()

        # Example 7: TimeoutError
        await demonstrate_timeout_error()

        # Example 8: Validation errors
        await demonstrate_validation_error()

        # Example 9: Graceful degradation
        await demonstrate_graceful_degradation(client, workspace_gid)

    print("\n=== Complete ===")
    print("Key Takeaways:")
    print("  - Catch specific exceptions (NotFoundError, RateLimitError, etc.)")
    print("  - Access error details via .message, .status_code, .errors")
    print("  - Use correlation IDs (X-Request-Id) for debugging")
    print("  - Implement graceful degradation for non-critical failures")
    print("  - Use exponential backoff for transient errors")
    print("  - RateLimitError includes retry_after hint")
    print("  - All exceptions inherit from AsanaError")


if __name__ == "__main__":
    parser = ArgumentParser(description="Demonstrate error handling patterns")
    parser.add_argument(
        "--workspace",
        default=get_workspace_gid(),
        help="Workspace GID (or set ASANA_WORKSPACE_GID env var)",
    )
    args = parser.parse_args()

    if not args.workspace:
        print("ERROR: No workspace GID provided")
        print(get_config_instructions())
        exit(1)

    asyncio.run(main(args.workspace))
