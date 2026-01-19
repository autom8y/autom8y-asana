"""Example: Protocol Adapters for Custom Integration

Demonstrates:
- Implementing custom AuthProvider for secret management
- Implementing custom CacheProvider for caching
- Implementing custom LogProvider for logging
- Composing custom providers in AsanaClient
- Integration patterns for autom8

Requirements:
- ASANA_PAT environment variable set (for demonstration)
- Understanding of Protocol-based design

Usage:
    export ASANA_PAT="your_token_here"
    python examples/09_protocol_adapters.py

Output:
    Custom provider implementations and usage examples

Note:
    See examples/autom8_adapters.py for production-ready implementations
    that integrate with autom8's existing infrastructure.
"""

import asyncio
import time
from typing import Any


# ============================================================================
# Custom AuthProvider Example
# ============================================================================


class SimpleAuthProvider:
    """Simple AuthProvider that retrieves secrets from a dict.

    In production, this would integrate with your secret management system
    (Vault, AWS Secrets Manager, autom8's SecretManager, etc.).
    """

    def __init__(self, secrets: dict[str, str]) -> None:
        """Initialize with a dict of secrets.

        Args:
            secrets: Dict mapping secret keys to values
        """
        self._secrets = secrets

    def get_secret(self, key: str) -> str:
        """Retrieve a secret by key.

        Args:
            key: The secret key to retrieve

        Returns:
            The secret value

        Raises:
            KeyError: If the secret key doesn't exist
        """
        if key not in self._secrets:
            raise KeyError(f"Secret '{key}' not found")
        return self._secrets[key]


# ============================================================================
# Custom CacheProvider Example
# ============================================================================


class SimpleCacheProvider:
    """Simple in-memory cache with TTL support.

    In production, you might use Redis, Memcached, or autom8's TaskCache.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """Initialize cache with default TTL.

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]

        # Check if expired
        if time.time() > expiry:
            del self._cache[key]
            return None

        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
        """
        ttl = ttl or self._default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        """Remove a value from cache.

        Args:
            key: Cache key to remove
        """
        self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


# ============================================================================
# Custom LogProvider Example
# ============================================================================


class SimpleLogProvider:
    """Simple logging provider that prints to stdout.

    In production, you would integrate with your logging system
    (Python logging, structlog, autom8's LOG, etc.).
    """

    def __init__(self, level: str = "INFO") -> None:
        """Initialize logger with log level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        self._level = level.upper()
        self._levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}

    def _should_log(self, level: str) -> bool:
        """Check if message should be logged based on configured level."""
        return self._levels.get(level, 1) >= self._levels.get(self._level, 1)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        if self._should_log("DEBUG"):
            print(f"[DEBUG] {message}", kwargs if kwargs else "")

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        if self._should_log("INFO"):
            print(f"[INFO] {message}", kwargs if kwargs else "")

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        if self._should_log("WARNING"):
            print(f"[WARNING] {message}", kwargs if kwargs else "")

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        if self._should_log("ERROR"):
            print(f"[ERROR] {message}", kwargs if kwargs else "")


# ============================================================================
# Examples
# ============================================================================


async def example_custom_auth() -> None:
    """Demonstrate custom AuthProvider."""
    print("\n=== Example 1: Custom AuthProvider ===")

    # Create auth provider with secrets
    auth_provider = SimpleAuthProvider(
        secrets={
            "asana_pat": "your_token_here_from_secret_manager",
            "other_secret": "some_other_value",
        }
    )

    # Use with AsanaClient
    # Note: This example won't actually connect since the token is fake
    print("Created custom AuthProvider")
    print("  - Retrieves secrets from custom source")
    print("  - Integrates with existing secret management")
    print("  - See examples/autom8_adapters.py for autom8 integration")


async def example_custom_cache() -> None:
    """Demonstrate custom CacheProvider."""
    print("\n=== Example 2: Custom CacheProvider ===")

    # Create cache provider
    cache_provider = SimpleCacheProvider(default_ttl=60)

    # Store and retrieve values
    await cache_provider.set("task:123", {"name": "Example Task"})
    cached_value = await cache_provider.get("task:123")

    print(f"Cached value: {cached_value}")
    print("Custom cache provider:")
    print("  - Controls caching strategy")
    print("  - Can use Redis, Memcached, etc.")
    print("  - TTL-based expiration")


async def example_custom_log() -> None:
    """Demonstrate custom LogProvider."""
    print("\n=== Example 3: Custom LogProvider ===")

    # Create log provider
    log_provider = SimpleLogProvider(level="INFO")

    # Log messages
    log_provider.debug("This won't show (level=INFO)")
    log_provider.info("SDK operation started")
    log_provider.warning("Rate limit approaching")
    log_provider.error("API request failed")

    print("\nCustom log provider:")
    print("  - Routes logs to your logging system")
    print("  - Structured logging support")
    print("  - Integration with observability tools")


async def example_composition() -> None:
    """Demonstrate composing multiple custom providers."""
    print("\n=== Example 4: Composing Custom Providers ===")

    # This shows how to use all custom providers together
    # In production, these would integrate with your infrastructure

    example_code = """
# Production example with all custom providers
from autom8_asana import AsanaClient

client = AsanaClient(
    auth_provider=YourAuthProvider(),      # Your secret management
    cache_provider=YourCacheProvider(),    # Your caching layer
    log_provider=YourLogProvider(),        # Your logging system
)

async with client:
    # SDK uses your providers for all operations
    task = await client.tasks.get_async("123")
"""

    print(example_code)


async def example_autom8_integration() -> None:
    """Show autom8-specific integration patterns."""
    print("\n=== Example 5: autom8 Integration ===")

    print("For autom8 integration, see examples/autom8_adapters.py:")
    print("\n1. SecretManagerAuthProvider")
    print("   - Integrates with ENV.SecretManager")
    print("   - Retrieves ASANA_PAT from autom8's secret store")
    print("\n2. TaskCacheAdapter")
    print("   - Wraps autom8.core.cache.TaskCache")
    print("   - Uses existing Redis infrastructure")
    print("\n3. LogAdapter")
    print("   - Routes to autom8.core.log.LOG")
    print("   - Maintains consistent logging format")

    print("\nUsage in autom8:")
    autom8_example = """
from examples.autom8_adapters import (
    SecretManagerAuthProvider,
    TaskCacheAdapter,
    LogAdapter,
)
from autom8_asana import AsanaClient

client = AsanaClient(
    auth_provider=SecretManagerAuthProvider(),
    cache_provider=TaskCacheAdapter(),
    log_provider=LogAdapter(),
)
"""
    print(autom8_example)


async def main() -> None:
    """Run all protocol adapter examples."""
    print("autom8_asana SDK - Protocol Adapters Examples")
    print("\nProtocols enable seamless integration with your infrastructure.")

    # Example 1: Custom auth
    await example_custom_auth()

    # Example 2: Custom cache
    await example_custom_cache()

    # Example 3: Custom log
    await example_custom_log()

    # Example 4: Composition
    await example_composition()

    # Example 5: autom8 integration
    await example_autom8_integration()

    print("\n=== Complete ===")
    print("Key Takeaways:")
    print("  - Protocols define interfaces, not implementations")
    print("  - Implement AuthProvider to integrate secret management")
    print("  - Implement CacheProvider for custom caching strategies")
    print("  - Implement LogProvider to route logs to your system")
    print("  - Compose providers for complete infrastructure integration")
    print("  - See examples/autom8_adapters.py for production examples")


if __name__ == "__main__":
    asyncio.run(main())
