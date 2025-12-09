"""Base client class for all resource clients."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import LogProvider
    from autom8_asana.transport.http import AsyncHTTPClient


class BaseClient:
    """Base class for resource-specific clients.

    Provides common functionality:
    - Access to HTTP transport
    - Access to providers (auth, cache, log)
    - Request building helpers
    - Response parsing helpers
    """

    def __init__(
        self,
        http: AsyncHTTPClient,
        config: AsanaConfig,
        auth_provider: AuthProvider,
        cache_provider: CacheProvider | None = None,
        log_provider: LogProvider | None = None,
    ) -> None:
        """Initialize base client.

        Args:
            http: HTTP client for making requests
            config: SDK configuration
            auth_provider: Authentication provider
            cache_provider: Optional cache provider
            log_provider: Optional log provider
        """
        self._http = http
        self._config = config
        self._auth = auth_provider
        self._cache = cache_provider
        self._log = log_provider

    def _build_opt_fields(self, opt_fields: list[str] | None) -> dict[str, Any]:
        """Build opt_fields query parameter.

        Args:
            opt_fields: List of field names to include

        Returns:
            Query params dict with opt_fields formatted for Asana API
        """
        if not opt_fields:
            return {}
        return {"opt_fields": ",".join(opt_fields)}

    def _log_operation(self, operation: str, resource_gid: str | None = None) -> None:
        """Log an operation if logger is available."""
        if self._log:
            if resource_gid:
                self._log.debug(f"{self.__class__.__name__}.{operation}({resource_gid})")
            else:
                self._log.debug(f"{self.__class__.__name__}.{operation}()")
