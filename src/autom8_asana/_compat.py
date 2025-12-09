"""Backward compatibility layer for gradual migration.

This module provides aliases for old import paths. All imports from this
module emit deprecation warnings guiding users to the new canonical paths.

Migration Guide:
    # Old (deprecated):
    from autom8_asana._compat import Task
    from autom8_asana._compat import TasksClient

    # New (canonical):
    from autom8_asana import Task
    from autom8_asana.clients import TasksClient

This module will be removed in version 1.0.0.

Per TDD-0006: Backward Compatibility Layer.
Per ADR-0011: Deprecation Warning Strategy.
"""

from __future__ import annotations

import importlib
import logging
import warnings
from typing import TYPE_CHECKING, Any

# Version when this module will be removed
_REMOVAL_VERSION = "1.0.0"

# Logger for import tracking
_logger = logging.getLogger("autom8_asana._compat")

# Mapping of old names to (new_module_path, new_import_statement)
_MODEL_ALIASES: dict[str, tuple[str, str]] = {
    "AsanaResource": ("autom8_asana.models", "from autom8_asana.models import AsanaResource"),
    "NameGid": ("autom8_asana.models", "from autom8_asana.models import NameGid"),
    "PageIterator": ("autom8_asana.models", "from autom8_asana.models import PageIterator"),
    "Task": ("autom8_asana.models", "from autom8_asana import Task"),
    "Project": ("autom8_asana.models", "from autom8_asana import Project"),
    "Section": ("autom8_asana.models", "from autom8_asana import Section"),
    "User": ("autom8_asana.models", "from autom8_asana import User"),
    "Workspace": ("autom8_asana.models", "from autom8_asana import Workspace"),
    "CustomField": ("autom8_asana.models", "from autom8_asana import CustomField"),
    "CustomFieldEnumOption": ("autom8_asana.models", "from autom8_asana import CustomFieldEnumOption"),
    "CustomFieldSetting": ("autom8_asana.models", "from autom8_asana import CustomFieldSetting"),
    "Attachment": ("autom8_asana.models", "from autom8_asana import Attachment"),
    "Goal": ("autom8_asana.models", "from autom8_asana import Goal"),
    "GoalMembership": ("autom8_asana.models", "from autom8_asana import GoalMembership"),
    "GoalMetric": ("autom8_asana.models", "from autom8_asana import GoalMetric"),
    "Portfolio": ("autom8_asana.models", "from autom8_asana import Portfolio"),
    "Story": ("autom8_asana.models", "from autom8_asana import Story"),
    "Tag": ("autom8_asana.models", "from autom8_asana import Tag"),
    "Team": ("autom8_asana.models", "from autom8_asana import Team"),
    "TeamMembership": ("autom8_asana.models", "from autom8_asana import TeamMembership"),
    "Webhook": ("autom8_asana.models", "from autom8_asana import Webhook"),
    "WebhookFilter": ("autom8_asana.models", "from autom8_asana import WebhookFilter"),
}

_CLIENT_ALIASES: dict[str, tuple[str, str]] = {
    "TasksClient": ("autom8_asana.clients", "from autom8_asana.clients import TasksClient"),
    "ProjectsClient": ("autom8_asana.clients", "from autom8_asana.clients import ProjectsClient"),
    "SectionsClient": ("autom8_asana.clients", "from autom8_asana.clients import SectionsClient"),
    "UsersClient": ("autom8_asana.clients", "from autom8_asana.clients import UsersClient"),
    "WorkspacesClient": ("autom8_asana.clients", "from autom8_asana.clients import WorkspacesClient"),
    "CustomFieldsClient": ("autom8_asana.clients", "from autom8_asana.clients import CustomFieldsClient"),
    "WebhooksClient": ("autom8_asana.clients", "from autom8_asana.clients import WebhooksClient"),
    "TeamsClient": ("autom8_asana.clients", "from autom8_asana.clients import TeamsClient"),
    "AttachmentsClient": ("autom8_asana.clients", "from autom8_asana.clients import AttachmentsClient"),
    "TagsClient": ("autom8_asana.clients", "from autom8_asana.clients import TagsClient"),
    "GoalsClient": ("autom8_asana.clients", "from autom8_asana.clients import GoalsClient"),
    "PortfoliosClient": ("autom8_asana.clients", "from autom8_asana.clients import PortfoliosClient"),
    "StoriesClient": ("autom8_asana.clients", "from autom8_asana.clients import StoriesClient"),
    "BaseClient": ("autom8_asana.clients", "from autom8_asana.clients import BaseClient"),
}

_PROTOCOL_ALIASES: dict[str, tuple[str, str]] = {
    "AuthProvider": ("autom8_asana.protocols", "from autom8_asana import AuthProvider"),
    "CacheProvider": ("autom8_asana.protocols", "from autom8_asana import CacheProvider"),
    "LogProvider": ("autom8_asana.protocols", "from autom8_asana import LogProvider"),
    "ItemLoader": ("autom8_asana.protocols", "from autom8_asana import ItemLoader"),
}

_EXCEPTION_ALIASES: dict[str, tuple[str, str]] = {
    "AsanaError": ("autom8_asana.exceptions", "from autom8_asana import AsanaError"),
    "AuthenticationError": ("autom8_asana.exceptions", "from autom8_asana import AuthenticationError"),
    "RateLimitError": ("autom8_asana.exceptions", "from autom8_asana import RateLimitError"),
    "NotFoundError": ("autom8_asana.exceptions", "from autom8_asana import NotFoundError"),
    "ForbiddenError": ("autom8_asana.exceptions", "from autom8_asana import ForbiddenError"),
    "GoneError": ("autom8_asana.exceptions", "from autom8_asana import GoneError"),
    "ServerError": ("autom8_asana.exceptions", "from autom8_asana import ServerError"),
    "TimeoutError": ("autom8_asana.exceptions", "from autom8_asana import TimeoutError"),
    "ConfigurationError": ("autom8_asana.exceptions", "from autom8_asana import ConfigurationError"),
    "SyncInAsyncContextError": ("autom8_asana.exceptions", "from autom8_asana import SyncInAsyncContextError"),
}

_CONFIG_ALIASES: dict[str, tuple[str, str]] = {
    "AsanaConfig": ("autom8_asana.config", "from autom8_asana import AsanaConfig"),
    "RateLimitConfig": ("autom8_asana.config", "from autom8_asana import RateLimitConfig"),
    "RetryConfig": ("autom8_asana.config", "from autom8_asana import RetryConfig"),
    "ConcurrencyConfig": ("autom8_asana.config", "from autom8_asana import ConcurrencyConfig"),
    "TimeoutConfig": ("autom8_asana.config", "from autom8_asana import TimeoutConfig"),
    "ConnectionPoolConfig": ("autom8_asana.config", "from autom8_asana import ConnectionPoolConfig"),
}

_MAIN_ALIASES: dict[str, tuple[str, str]] = {
    "AsanaClient": ("autom8_asana.client", "from autom8_asana import AsanaClient"),
}

_BATCH_ALIASES: dict[str, tuple[str, str]] = {
    "BatchClient": ("autom8_asana.batch", "from autom8_asana import BatchClient"),
    "BatchRequest": ("autom8_asana.batch", "from autom8_asana import BatchRequest"),
    "BatchResult": ("autom8_asana.batch", "from autom8_asana import BatchResult"),
    "BatchSummary": ("autom8_asana.batch", "from autom8_asana import BatchSummary"),
}

# Combined mapping for lookup
_ALL_ALIASES: dict[str, tuple[str, str]] = {
    **_MODEL_ALIASES,
    **_CLIENT_ALIASES,
    **_PROTOCOL_ALIASES,
    **_EXCEPTION_ALIASES,
    **_CONFIG_ALIASES,
    **_MAIN_ALIASES,
    **_BATCH_ALIASES,
}


def _deprecated_import(name: str, new_import: str) -> None:
    """Emit deprecation warning for legacy import.

    Args:
        name: The attribute name being imported.
        new_import: The recommended import statement.
    """
    _logger.warning(
        "Deprecated import: '%s' from 'autom8_asana._compat'. Use '%s' instead.",
        name,
        new_import,
    )
    warnings.warn(
        f"Importing '{name}' from 'autom8_asana._compat' is deprecated. "
        f"Use '{new_import}' instead. "
        f"This alias will be removed in version {_REMOVAL_VERSION}.",
        DeprecationWarning,
        stacklevel=3,  # Points to the actual import statement in user code
    )


def __getattr__(name: str) -> Any:
    """Lazy attribute access with deprecation warnings.

    Args:
        name: Attribute name being accessed.

    Returns:
        The requested class/object from the canonical location.

    Raises:
        AttributeError: If name is not a known alias.
    """
    if name in _ALL_ALIASES:
        module_path, new_import = _ALL_ALIASES[name]
        _deprecated_import(name, new_import)

        # Perform the actual import
        module = importlib.import_module(module_path)
        return getattr(module, name)

    raise AttributeError(f"module 'autom8_asana._compat' has no attribute '{name}'")


# For IDE support and static analysis
__all__ = [
    # Models
    "AsanaResource",
    "NameGid",
    "PageIterator",
    "Task",
    "Project",
    "Section",
    "User",
    "Workspace",
    "CustomField",
    "CustomFieldEnumOption",
    "CustomFieldSetting",
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
    # Clients
    "TasksClient",
    "ProjectsClient",
    "SectionsClient",
    "UsersClient",
    "WorkspacesClient",
    "CustomFieldsClient",
    "WebhooksClient",
    "TeamsClient",
    "AttachmentsClient",
    "TagsClient",
    "GoalsClient",
    "PortfoliosClient",
    "StoriesClient",
    "BaseClient",
    # Protocols
    "AuthProvider",
    "CacheProvider",
    "LogProvider",
    "ItemLoader",
    # Exceptions
    "AsanaError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ForbiddenError",
    "GoneError",
    "ServerError",
    "TimeoutError",
    "ConfigurationError",
    "SyncInAsyncContextError",
    # Configuration
    "AsanaConfig",
    "RateLimitConfig",
    "RetryConfig",
    "ConcurrencyConfig",
    "TimeoutConfig",
    "ConnectionPoolConfig",
    # Main client
    "AsanaClient",
    # Batch API
    "BatchClient",
    "BatchRequest",
    "BatchResult",
    "BatchSummary",
]


# TYPE_CHECKING block for static analysis tools
if TYPE_CHECKING:
    from autom8_asana import (
        AsanaClient,
        AsanaConfig,
        AsanaError,
        Attachment,
        AuthenticationError,
        AuthProvider,
        BatchClient,
        BatchRequest,
        BatchResult,
        BatchSummary,
        CacheProvider,
        ConcurrencyConfig,
        ConfigurationError,
        ConnectionPoolConfig,
        CustomField,
        CustomFieldEnumOption,
        CustomFieldSetting,
        ForbiddenError,
        Goal,
        GoalMembership,
        GoalMetric,
        GoneError,
        ItemLoader,
        LogProvider,
        NotFoundError,
        Portfolio,
        Project,
        RateLimitConfig,
        RateLimitError,
        RetryConfig,
        Section,
        ServerError,
        Story,
        SyncInAsyncContextError,
        Tag,
        Task,
        Team,
        TeamMembership,
        TimeoutConfig,
        TimeoutError,
        User,
        Webhook,
        WebhookFilter,
        Workspace,
    )
    from autom8_asana.clients import (
        AttachmentsClient,
        BaseClient,
        CustomFieldsClient,
        GoalsClient,
        PortfoliosClient,
        ProjectsClient,
        SectionsClient,
        StoriesClient,
        TagsClient,
        TasksClient,
        TeamsClient,
        UsersClient,
        WebhooksClient,
        WorkspacesClient,
    )
    from autom8_asana.models import AsanaResource, NameGid, PageIterator
