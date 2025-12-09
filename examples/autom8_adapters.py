"""Example protocol adapters for autom8 integration.

These examples show how autom8 can implement the SDK's protocols
to integrate with its existing infrastructure (SecretManager, TaskCache, LOG).

Copy and adapt these to your autom8 codebase. They are not part of the SDK
package itself - they are documentation examples only.

Per TDD-0006: Protocol adapter examples for autom8 integration.
Per ADR-0001: Protocol-based extensibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # These imports are autom8-specific and not available in the SDK.
    # They are shown for documentation purposes only.
    pass


class SecretManagerAuthProvider:
    """AuthProvider adapter wrapping autom8's ENV.SecretManager.

    This adapter allows the SDK to retrieve Asana credentials from
    autom8's centralized secret management infrastructure.

    Example usage in autom8:
        from autom8_asana import AsanaClient
        from your_adapters import SecretManagerAuthProvider

        client = AsanaClient(auth_provider=SecretManagerAuthProvider())
        task = await client.tasks.get_async("task_gid")
    """

    def __init__(self, secret_manager: Any | None = None) -> None:
        """Initialize with optional secret manager override.

        Args:
            secret_manager: Custom secret manager instance.
                           If None, imports ENV.SecretManager from autom8.
        """
        if secret_manager is not None:
            self._sm = secret_manager
        else:
            # This import only works within autom8 context
            from autom8.core.env import ENV  # type: ignore[import-not-found]

            self._sm = ENV.SecretManager

    def get_secret(self, key: str) -> str:
        """Retrieve secret from autom8's SecretManager.

        This method satisfies the AuthProvider protocol.

        Args:
            key: Secret key (e.g., "ASANA_PAT")

        Returns:
            Secret value as string.

        Raises:
            AuthenticationError: If secret not found or retrieval fails.
        """
        try:
            value = self._sm.get(key)
            if value is None:
                from autom8_asana import AuthenticationError

                raise AuthenticationError(f"Secret '{key}' not found in SecretManager")
            return str(value)
        except Exception as e:
            from autom8_asana import AuthenticationError

            raise AuthenticationError(
                f"Failed to retrieve secret '{key}': {e}"
            ) from e


class S3CacheProvider:
    """CacheProvider adapter wrapping autom8's TaskCache (S3-backed).

    This adapter allows the SDK to use autom8's distributed cache
    infrastructure for caching API responses.

    Example usage in autom8:
        from autom8_asana import AsanaClient
        from your_adapters import SecretManagerAuthProvider, S3CacheProvider

        client = AsanaClient(
            auth_provider=SecretManagerAuthProvider(),
            cache_provider=S3CacheProvider(),
        )
    """

    def __init__(
        self, task_cache: Any | None = None, prefix: str = "asana_sdk:"
    ) -> None:
        """Initialize with optional TaskCache override.

        Args:
            task_cache: Custom cache instance.
                       If None, imports TaskCache from autom8.
            prefix: Key prefix for namespacing SDK cache entries.
                   Default: "asana_sdk:"
        """
        if task_cache is not None:
            self._cache = task_cache
        else:
            # This import only works within autom8 context
            from autom8.apis.aws_api.task_cache import TaskCache  # type: ignore[import-not-found]

            self._cache = TaskCache
        self._prefix = prefix

    def _prefixed_key(self, key: str) -> str:
        """Add prefix to cache key for namespacing."""
        return f"{self._prefix}{key}"

    def get(self, key: str) -> dict[str, Any] | None:
        """Get value from S3-backed cache.

        This method satisfies the CacheProvider protocol.

        Args:
            key: Cache key.

        Returns:
            Cached dict or None if not found or on error.
        """
        try:
            return self._cache.get(self._prefixed_key(key))  # type: ignore[no-any-return]
        except Exception:
            # Cache failures should not break SDK operations
            return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in S3-backed cache.

        This method satisfies the CacheProvider protocol.

        Args:
            key: Cache key.
            value: Dict to cache.
            ttl: TTL in seconds (may be ignored by TaskCache implementation).
        """
        try:
            self._cache.set(self._prefixed_key(key), value, ttl=ttl)
        except Exception:
            # Cache failures should not break SDK operations
            pass

    def delete(self, key: str) -> None:
        """Delete value from cache.

        This method satisfies the CacheProvider protocol.

        Args:
            key: Cache key to delete.
        """
        try:
            self._cache.delete(self._prefixed_key(key))
        except Exception:
            # Cache failures should not break SDK operations
            pass


class LogAdapter:
    """LogProvider adapter wrapping autom8's LOG.

    This adapter allows the SDK to use autom8's logging infrastructure
    for consistent log formatting and aggregation.

    Example usage in autom8:
        from autom8_asana import AsanaClient
        from your_adapters import SecretManagerAuthProvider, LogAdapter

        client = AsanaClient(
            auth_provider=SecretManagerAuthProvider(),
            log_provider=LogAdapter(),
        )
    """

    def __init__(self, logger: Any | None = None, prefix: str = "[asana_sdk]") -> None:
        """Initialize with optional logger override.

        Args:
            logger: Custom logger instance.
                   If None, imports LOG from autom8.
            prefix: Prefix for log messages. Default: "[asana_sdk]"
        """
        if logger is not None:
            self._log = logger
        else:
            # This import only works within autom8 context
            from autom8.core.log import LOG  # type: ignore[import-not-found]

            self._log = LOG
        self._prefix = prefix

    def _format_msg(self, msg: str) -> str:
        """Add prefix to message for easy filtering."""
        return f"{self._prefix} {msg}"

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message.

        This method satisfies the LogProvider protocol.
        """
        self._log.debug(self._format_msg(msg), *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message.

        This method satisfies the LogProvider protocol.
        """
        self._log.info(self._format_msg(msg), *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message.

        This method satisfies the LogProvider protocol.
        """
        self._log.warning(self._format_msg(msg), *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message.

        This method satisfies the LogProvider protocol.
        """
        self._log.error(self._format_msg(msg), *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback.

        This method satisfies the LogProvider protocol.
        """
        self._log.exception(self._format_msg(msg), *args, **kwargs)


def create_autom8_client(
    **config_overrides: Any,
) -> "AsanaClient":  # noqa: F821 - forward reference
    """Create AsanaClient with full autom8 integration.

    This convenience function creates an AsanaClient configured with
    all autom8 infrastructure adapters.

    Example:
        client = create_autom8_client()
        task = await client.tasks.get_async("task_gid")

        # With custom config
        client = create_autom8_client(timeout_seconds=60)

    Args:
        **config_overrides: Override default AsanaConfig settings.
                           Passed directly to AsanaConfig constructor.

    Returns:
        AsanaClient configured for autom8 integration.
    """
    from autom8_asana import AsanaClient, AsanaConfig

    config = AsanaConfig(**config_overrides) if config_overrides else None

    return AsanaClient(
        auth_provider=SecretManagerAuthProvider(),
        cache_provider=S3CacheProvider(),
        log_provider=LogAdapter(),
        config=config,
    )


# Example: Creating a minimal adapter for testing
class MockAuthProvider:
    """Simple auth provider for testing/development.

    This is an example of a minimal AuthProvider implementation
    that reads from environment variables.
    """

    def __init__(self, token: str | None = None) -> None:
        """Initialize with optional explicit token.

        Args:
            token: Explicit token. If None, reads from ASANA_PAT env var.
        """
        self._token = token

    def get_secret(self, key: str) -> str:
        """Get secret, returning explicit token or reading from env."""
        if self._token is not None:
            return self._token

        import os

        value = os.environ.get(key)
        if value is None:
            from autom8_asana import AuthenticationError

            raise AuthenticationError(f"Environment variable '{key}' not set")
        return value
