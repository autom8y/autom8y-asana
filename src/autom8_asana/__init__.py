"""autom8_asana - Async-first Asana API client.

Example:
    from autom8_asana import AsanaClient

    # Standalone usage (reads ASANA_PAT from environment)
    client = AsanaClient()
    task = client.tasks.get("task_gid")

    # Async usage
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")
"""

from autom8_asana.batch import BatchClient, BatchRequest, BatchResult, BatchSummary
from autom8_asana.client import AsanaClient
from autom8_asana.config import (
    AsanaConfig,
    ConcurrencyConfig,
    ConnectionPoolConfig,
    RateLimitConfig,
    RetryConfig,
    TimeoutConfig,
)
from autom8_asana.exceptions import (
    AsanaError,
    AuthenticationError,
    ConfigurationError,
    ForbiddenError,
    GoneError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SyncInAsyncContextError,
    TimeoutError,
)

# Protocols (for type checking and custom implementations)
from autom8_asana.protocols import AuthProvider, CacheProvider, ItemLoader, LogProvider

# Observability (per TDD-0007, ADR-0013)
from autom8_asana.observability import (
    CorrelationContext,
    error_handler,
    generate_correlation_id,
)

# Models (Pydantic v2, per ADR-0005, TDD-0002, TDD-0004)
from autom8_asana.models import (
    AsanaResource,
    Attachment,
    CustomField,
    CustomFieldEnumOption,
    CustomFieldSetting,
    Goal,
    GoalMembership,
    GoalMetric,
    NameGid,
    PageIterator,
    Portfolio,
    Project,
    Section,
    Story,
    Tag,
    Task,
    Team,
    TeamMembership,
    User,
    Webhook,
    WebhookFilter,
    Workspace,
)

__version__ = "0.1.0"

__all__ = [
    # Main client
    "AsanaClient",
    # Configuration
    "AsanaConfig",
    "RateLimitConfig",
    "RetryConfig",
    "ConcurrencyConfig",
    "TimeoutConfig",
    "ConnectionPoolConfig",
    # Exceptions
    "AsanaError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "GoneError",
    "RateLimitError",
    "ServerError",
    "TimeoutError",
    "ConfigurationError",
    "SyncInAsyncContextError",
    # Protocols
    "AuthProvider",
    "CacheProvider",
    "ItemLoader",
    "LogProvider",
    # Observability
    "CorrelationContext",
    "error_handler",
    "generate_correlation_id",
    # Batch API
    "BatchClient",
    "BatchRequest",
    "BatchResult",
    "BatchSummary",
    # Models - Base
    "AsanaResource",
    "NameGid",
    "PageIterator",
    # Models - Tier 1
    "CustomField",
    "CustomFieldEnumOption",
    "CustomFieldSetting",
    "Project",
    "Section",
    "Task",
    "User",
    "Workspace",
    # Models - Tier 2
    "Attachment",
    "Goal",
    "GoalMembership",
    "GoalMetric",
    "Portfolio",
    "Story",
    "Tag",
    "Team",
    "TeamMembership",
    "Webhook",
    "WebhookFilter",
]
