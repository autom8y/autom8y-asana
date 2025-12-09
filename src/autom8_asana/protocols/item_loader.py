"""Protocol for lazy loading additional resource data.

Per TDD-0002 and ADR-0004: SDK provides the protocol, not the implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class ItemLoader(Protocol):
    """Protocol for lazy loading additional resource data.

    The SDK provides this protocol as a hook for consumers who want
    lazy loading behavior. The SDK does NOT provide an implementation.

    Per ADR-0004:
    - SDK provides minimal AsanaResource base class
    - autom8 monolith implements lazy loading via this protocol
    - New microservices can implement their own or skip lazy loading

    Example implementation (in autom8, NOT in SDK):
        class Autom8ItemLoader:
            def __init__(self, cache: TaskCache, client: AsanaClient):
                self._cache = cache
                self._client = client

            async def load_async(
                self,
                resource: AsanaResource,
                fields: list[str] | None = None,
            ) -> dict[str, Any]:
                # Check cache first
                cached = self._cache.get(resource.gid)
                if cached:
                    return cached

                # Fetch from API
                data = await self._client.tasks.get_async(
                    resource.gid,
                    opt_fields=fields,
                    raw=True,
                )
                self._cache.set(resource.gid, data)
                return data

    Usage in autom8's Item class:
        class Item(AsanaResource):
            _loader: ItemLoader | None = None

            def __getattr__(self, name: str) -> Any:
                if self._loader and name in self._lazy_fields:
                    data = asyncio.run(self._loader.load_async(self, [name]))
                    return data.get(name)
                raise AttributeError(name)
    """

    async def load_async(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Load additional data for a resource.

        Args:
            resource: The resource to load data for (has gid, resource_type)
            fields: Optional list of specific fields to load. If None,
                load all available fields.

        Returns:
            Dict containing the loaded field values.

        Raises:
            NotFoundError: If resource doesn't exist
            AsanaError: On API/cache errors
        """
        ...

    def load(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sync version of load_async.

        Args:
            resource: The resource to load data for
            fields: Optional list of specific fields to load

        Returns:
            Dict containing the loaded field values.
        """
        ...
