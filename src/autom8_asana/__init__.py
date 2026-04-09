# ruff: noqa: E402
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

# Default providers (for AWS deployments per ADR-VAULT-001)
from autom8_asana._defaults import (
    EnvAuthProvider,
    SecretsManagerAuthProvider,
)
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

# Dataframe Layer (TDD-0009) -- lazy-loaded to avoid pulling in polars
# for consumers that only need the core API client.
_DATAFRAME_EXPORTS = {
    "BASE_SCHEMA",
    "CONTACT_SCHEMA",
    "LAZY_THRESHOLD",
    "UNIT_SCHEMA",
    "BaseExtractor",
    "CachedRow",
    "ColumnDef",
    "ContactExtractor",
    "ContactRow",
    "CustomFieldResolver",
    "DataFrameBuilder",
    "DataFrameCacheIntegration",
    "DataFrameError",
    "DataFrameSchema",
    "DefaultCustomFieldResolver",
    "ExtractionError",
    "FailingResolver",
    "MockCustomFieldResolver",
    "NameNormalizer",
    "ProgressiveProjectBuilder",
    "SchemaNotFoundError",
    "SchemaRegistry",
    "SchemaVersionError",
    "SectionDataFrameBuilder",
    "TaskRow",
    "TypeCoercionError",
    "UnitExtractor",
    "UnitRow",
}


def __getattr__(name: str) -> object:
    if name in _DATAFRAME_EXPORTS:
        import autom8_asana.dataframes as _df

        return getattr(_df, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


from autom8_asana.exceptions import (
    AsanaError,
    AuthenticationError,
    ConfigurationError,
    ForbiddenError,
    GoneError,
    HydrationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SyncInAsyncContextError,
    TimeoutError,
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

# Observability (per TDD-0007, ADR-0013)
from autom8_asana.observability import (
    CorrelationContext,
    error_handler,
    generate_correlation_id,
)

# TDD-HARDENING-A: GID validation exception at root level (FR-EXC-006)
from autom8_asana.persistence.exceptions import GidValidationError

# Protocols (for type checking and custom implementations)
from autom8_asana.protocols import (
    AuthProvider,
    CacheProvider,
    ItemLoader,
    LogProvider,
    ObservabilityHook,  # TDD-HARDENING-A/FR-OBS-009
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
    "GidValidationError",  # TDD-HARDENING-A (FR-EXC-006)
    "GoneError",
    "HydrationError",
    "NotFoundError",
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
    "ObservabilityHook",  # TDD-HARDENING-A/FR-OBS-009
    # Auth providers (ADR-VAULT-001)
    "EnvAuthProvider",
    "SecretsManagerAuthProvider",
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
    # Dataframe Layer (TDD-0009)
    # Constants
    "LAZY_THRESHOLD",
    # Row Models
    "TaskRow",
    "UnitRow",
    "ContactRow",
    # Schema Models
    "DataFrameSchema",
    "ColumnDef",
    "SchemaRegistry",
    # Built-in Schemas
    "BASE_SCHEMA",
    "UNIT_SCHEMA",
    "CONTACT_SCHEMA",
    # Builders
    "DataFrameBuilder",
    "SectionDataFrameBuilder",
    "ProgressiveProjectBuilder",
    # Extractors
    "BaseExtractor",
    "UnitExtractor",
    "ContactExtractor",
    # Resolver (TDD-0009.1)  # noqa: ERA001
    "CustomFieldResolver",
    "DefaultCustomFieldResolver",
    "MockCustomFieldResolver",
    "FailingResolver",
    "NameNormalizer",
    # Cache Integration
    "CachedRow",
    "DataFrameCacheIntegration",
    # Dataframe Exceptions
    "DataFrameError",
    "SchemaNotFoundError",
    "ExtractionError",
    "TypeCoercionError",
    "SchemaVersionError",
]
