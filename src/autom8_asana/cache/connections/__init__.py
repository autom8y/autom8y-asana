"""Connection lifecycle management for cache backends.

Re-exports key types for convenient import:

    from autom8_asana.cache.connections import (
        RedisConnectionManager,
        S3ConnectionManager,
        ConnectionRegistry,
    )

Design reference: docs/design/TDD-connection-lifecycle-management.md
"""

from autom8_asana.cache.connections.redis import RedisConnectionManager
from autom8_asana.cache.connections.registry import ConnectionRegistry
from autom8_asana.cache.connections.s3 import S3ConnectionManager

__all__ = [
    "RedisConnectionManager",
    "S3ConnectionManager",
    "ConnectionRegistry",
]
