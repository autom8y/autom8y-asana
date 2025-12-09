"""Tests for the backward compatibility layer.

Per TDD-0006: Verify deprecation warnings and legacy import support.
Per ADR-0011: Verify deprecation warning strategy.
Per ADR-0012: Verify public API surface definition.
"""

from __future__ import annotations

import importlib
import sys
import warnings
from typing import Any

import pytest


class TestCompatDeprecationWarnings:
    """Test that _compat module emits correct deprecation warnings."""

    def test_model_import_emits_deprecation_warning(self) -> None:
        """Verify importing a model from _compat emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            # Import via _compat
            from autom8_asana._compat import Task

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "Importing 'Task' from 'autom8_asana._compat' is deprecated" in str(
                w[0].message
            )
            assert "from autom8_asana import Task" in str(w[0].message)
            assert "1.0.0" in str(w[0].message)

            # Verify it's the correct class
            from autom8_asana.models import Task as CanonicalTask

            assert Task is CanonicalTask

    def test_client_import_emits_deprecation_warning(self) -> None:
        """Verify importing a client from _compat emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            from autom8_asana._compat import TasksClient

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert (
                "Importing 'TasksClient' from 'autom8_asana._compat' is deprecated"
                in str(w[0].message)
            )
            assert "from autom8_asana.clients import TasksClient" in str(w[0].message)

            # Verify it's the correct class
            from autom8_asana.clients import TasksClient as CanonicalTasksClient

            assert TasksClient is CanonicalTasksClient

    def test_protocol_import_emits_deprecation_warning(self) -> None:
        """Verify importing a protocol from _compat emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            from autom8_asana._compat import AuthProvider

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert (
                "Importing 'AuthProvider' from 'autom8_asana._compat' is deprecated"
                in str(w[0].message)
            )

            # Verify it's the correct class
            from autom8_asana.protocols import AuthProvider as CanonicalAuthProvider

            assert AuthProvider is CanonicalAuthProvider

    def test_exception_import_emits_deprecation_warning(self) -> None:
        """Verify importing an exception from _compat emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            from autom8_asana._compat import AsanaError

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert (
                "Importing 'AsanaError' from 'autom8_asana._compat' is deprecated"
                in str(w[0].message)
            )

            # Verify it's the correct class
            from autom8_asana import AsanaError as CanonicalAsanaError

            assert AsanaError is CanonicalAsanaError

    def test_config_import_emits_deprecation_warning(self) -> None:
        """Verify importing config from _compat emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            from autom8_asana._compat import AsanaConfig

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert (
                "Importing 'AsanaConfig' from 'autom8_asana._compat' is deprecated"
                in str(w[0].message)
            )

            # Verify it's the correct class
            from autom8_asana import AsanaConfig as CanonicalAsanaConfig

            assert AsanaConfig is CanonicalAsanaConfig

    def test_main_client_import_emits_deprecation_warning(self) -> None:
        """Verify importing AsanaClient from _compat emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            from autom8_asana._compat import AsanaClient

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert (
                "Importing 'AsanaClient' from 'autom8_asana._compat' is deprecated"
                in str(w[0].message)
            )

            # Verify it's the correct class
            from autom8_asana import AsanaClient as CanonicalAsanaClient

            assert AsanaClient is CanonicalAsanaClient

    def test_batch_import_emits_deprecation_warning(self) -> None:
        """Verify importing batch classes from _compat emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)

            from autom8_asana._compat import BatchRequest

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert (
                "Importing 'BatchRequest' from 'autom8_asana._compat' is deprecated"
                in str(w[0].message)
            )

            # Verify it's the correct class
            from autom8_asana import BatchRequest as CanonicalBatchRequest

            assert BatchRequest is CanonicalBatchRequest


class TestCompatImportsWork:
    """Test that all aliased imports actually work and return correct types."""

    def test_all_model_aliases_resolve(self) -> None:
        """Verify all model aliases resolve to correct classes."""
        model_names = [
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
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import autom8_asana._compat as compat
            import autom8_asana.models as models

            for name in model_names:
                compat_class = getattr(compat, name)
                canonical_class = getattr(models, name)
                assert compat_class is canonical_class, f"{name} mismatch"

    def test_all_client_aliases_resolve(self) -> None:
        """Verify all client aliases resolve to correct classes."""
        client_names = [
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
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import autom8_asana._compat as compat
            import autom8_asana.clients as clients

            for name in client_names:
                compat_class = getattr(compat, name)
                canonical_class = getattr(clients, name)
                assert compat_class is canonical_class, f"{name} mismatch"

    def test_all_protocol_aliases_resolve(self) -> None:
        """Verify all protocol aliases resolve to correct classes."""
        protocol_names = [
            "AuthProvider",
            "CacheProvider",
            "LogProvider",
            "ItemLoader",
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import autom8_asana._compat as compat
            import autom8_asana.protocols as protocols

            for name in protocol_names:
                compat_class = getattr(compat, name)
                canonical_class = getattr(protocols, name)
                assert compat_class is canonical_class, f"{name} mismatch"

    def test_all_exception_aliases_resolve(self) -> None:
        """Verify all exception aliases resolve to correct classes."""
        exception_names = [
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
        ]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import autom8_asana
            import autom8_asana._compat as compat

            for name in exception_names:
                compat_class = getattr(compat, name)
                canonical_class = getattr(autom8_asana, name)
                assert compat_class is canonical_class, f"{name} mismatch"


class TestCompatUnknownAttribute:
    """Test that unknown attributes raise AttributeError."""

    def test_unknown_attribute_raises_attribute_error(self) -> None:
        """Verify accessing unknown attribute raises AttributeError."""
        import autom8_asana._compat as compat

        with pytest.raises(AttributeError) as exc_info:
            _ = compat.NonExistentClass

        assert "module 'autom8_asana._compat' has no attribute 'NonExistentClass'" in str(
            exc_info.value
        )


class TestCompatModuleAll:
    """Test that __all__ is correctly defined."""

    def test_all_contains_expected_names(self) -> None:
        """Verify __all__ contains all expected export names."""
        import autom8_asana._compat as compat

        assert hasattr(compat, "__all__")
        all_names = set(compat.__all__)

        # Check some expected names
        expected_subset = {
            "Task",
            "Project",
            "AsanaClient",
            "TasksClient",
            "AuthProvider",
            "AsanaError",
            "AsanaConfig",
            "BatchRequest",
        }

        assert expected_subset.issubset(all_names), (
            f"Missing names: {expected_subset - all_names}"
        )


class TestSdkStandalone:
    """Test that SDK works standalone without autom8 dependencies.

    Per FR-COMPAT-006: SDK works standalone without autom8 dependencies.
    """

    def test_sdk_imports_without_autom8(self) -> None:
        """Verify SDK can be imported without any autom8 modules present."""
        # The fact that we got here means autom8 is not required
        # Verify the core imports work
        from autom8_asana import (
            AsanaClient,
            AsanaConfig,
            AsanaError,
            AuthProvider,
            CacheProvider,
            LogProvider,
            Task,
        )

        # Verify we can create config (no network needed)
        config = AsanaConfig()
        assert config.base_url == "https://app.asana.com/api/1.0"

    def test_no_autom8_imports_in_sdk(self) -> None:
        """Verify SDK modules don't import from autom8 package."""
        import autom8_asana

        # Check that no autom8 modules are imported
        autom8_modules = [name for name in sys.modules if name.startswith("autom8.")]
        assert len(autom8_modules) == 0, (
            f"autom8 modules should not be imported: {autom8_modules}"
        )


class TestAsanaSdkDependency:
    """Test that asana SDK is available as a dependency.

    Per FR-COMPAT-007: Keep asana (official SDK) as a dependency.
    """

    def test_asana_package_importable(self) -> None:
        """Verify asana package can be imported."""
        import asana

        # Verify it has expected attributes
        assert hasattr(asana, "Client") or hasattr(asana, "ApiClient")


class TestPublicApiSurface:
    """Test public API surface definition.

    Per ADR-0012: Public API surface should be clearly defined.
    """

    def test_root_package_has_all(self) -> None:
        """Verify root package defines __all__."""
        import autom8_asana

        assert hasattr(autom8_asana, "__all__")
        assert len(autom8_asana.__all__) > 0

    def test_models_package_has_all(self) -> None:
        """Verify models package defines __all__."""
        import autom8_asana.models

        assert hasattr(autom8_asana.models, "__all__")
        assert "Task" in autom8_asana.models.__all__

    def test_clients_package_has_all(self) -> None:
        """Verify clients package defines __all__."""
        import autom8_asana.clients

        assert hasattr(autom8_asana.clients, "__all__")
        assert "TasksClient" in autom8_asana.clients.__all__

    def test_protocols_package_has_all(self) -> None:
        """Verify protocols package defines __all__."""
        import autom8_asana.protocols

        assert hasattr(autom8_asana.protocols, "__all__")
        assert "AuthProvider" in autom8_asana.protocols.__all__

    def test_internal_modules_have_underscore_prefix(self) -> None:
        """Verify internal modules use underscore prefix convention."""
        import autom8_asana._defaults
        import autom8_asana._compat

        # These should be importable but marked as internal
        assert autom8_asana._defaults is not None
        assert autom8_asana._compat is not None

    def test_exceptions_module_has_all(self) -> None:
        """Verify exceptions module defines __all__."""
        import autom8_asana.exceptions

        assert hasattr(autom8_asana.exceptions, "__all__")
        assert "AsanaError" in autom8_asana.exceptions.__all__

    def test_config_module_has_all(self) -> None:
        """Verify config module defines __all__."""
        import autom8_asana.config

        assert hasattr(autom8_asana.config, "__all__")
        assert "AsanaConfig" in autom8_asana.config.__all__
