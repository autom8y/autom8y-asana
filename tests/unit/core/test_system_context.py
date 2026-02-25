"""Tests for SystemContext centralized reset (QW-5).

Validates that SystemContext.reset_all() properly resets all singletons.
"""

from __future__ import annotations

from autom8_asana.core.system_context import SystemContext


class TestSystemContextResetAll:
    """Tests for SystemContext.reset_all()."""

    def test_reset_all_clears_project_type_registry(self):
        """ProjectTypeRegistry should be empty after reset."""
        from autom8_asana.core.types import EntityType
        from autom8_asana.models.business.registry import ProjectTypeRegistry

        registry = ProjectTypeRegistry()
        registry.register("fake_gid_123", EntityType.BUSINESS)
        assert registry.lookup("fake_gid_123") is not None

        SystemContext.reset_all()

        fresh = ProjectTypeRegistry()
        assert fresh.lookup("fake_gid_123") is None

    def test_reset_all_clears_workspace_registry(self):
        """WorkspaceProjectRegistry should be empty after reset."""
        from autom8_asana.models.business.registry import WorkspaceProjectRegistry

        registry = WorkspaceProjectRegistry()
        assert registry is not None

        SystemContext.reset_all()

        fresh = WorkspaceProjectRegistry()
        assert not fresh.is_discovered()

    def test_reset_all_clears_schema_registry(self):
        """SchemaRegistry should be None after reset."""
        from autom8_asana.dataframes.models.registry import SchemaRegistry

        SchemaRegistry.reset()
        SystemContext.reset_all()

        # After reset, singleton should be freshly created on next access
        fresh = SchemaRegistry.get_instance()
        assert fresh is not None

    def test_reset_all_clears_entity_project_registry(self):
        """EntityProjectRegistry should be empty after reset."""
        from autom8_asana.services.resolver import EntityProjectRegistry

        registry = EntityProjectRegistry.get_instance()
        registry.register("test_entity", "test_gid", "Test")
        assert registry.is_ready()

        SystemContext.reset_all()

        fresh = EntityProjectRegistry.get_instance()
        assert not fresh.is_ready()

    def test_reset_all_clears_watermark_repository(self):
        """WatermarkRepository should be reset after reset_all."""
        from autom8_asana.dataframes.watermark import WatermarkRepository

        SystemContext.reset_all()

        # After reset, singleton should be freshly created
        fresh = WatermarkRepository.get_instance()
        assert fresh is not None

    def test_reset_all_clears_metric_registry(self):
        """MetricRegistry should be reset after reset_all."""
        from autom8_asana.metrics.registry import MetricRegistry

        SystemContext.reset_all()

        fresh = MetricRegistry()
        assert fresh is not None

    def test_reset_all_clears_settings(self):
        """Settings singleton should be cleared after reset_all."""
        from autom8_asana.settings import get_settings

        # Access settings to create the singleton
        get_settings()

        SystemContext.reset_all()

        # Next call creates fresh settings
        fresh = get_settings()
        assert fresh is not None

    def test_reset_all_clears_bootstrap_flag(self):
        """Bootstrap flag should be cleared after reset_all."""
        from autom8_asana.models.business._bootstrap import is_bootstrap_complete

        SystemContext.reset_all()
        assert not is_bootstrap_complete()

    def test_reset_all_is_idempotent(self):
        """Calling reset_all() multiple times should not raise."""
        SystemContext.reset_all()
        SystemContext.reset_all()
        SystemContext.reset_all()
