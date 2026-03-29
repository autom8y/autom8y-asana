"""Tests for cross-registry consistency validation (QW-4).

Validates that validate_cross_registry_consistency() detects mismatches
between EntityRegistry, ProjectTypeRegistry, and EntityProjectRegistry.
"""

from __future__ import annotations

import pytest

from autom8_asana.core.registry_validation import (
    RegistryValidationResult,
    validate_cross_registry_consistency,
)


class TestRegistryValidationResult:
    """Unit tests for RegistryValidationResult."""

    def test_ok_when_no_errors(self):
        result = RegistryValidationResult()
        assert result.ok is True

    def test_ok_with_warnings_only(self):
        result = RegistryValidationResult(warnings=["some warning"])
        assert result.ok is True

    def test_not_ok_with_errors(self):
        result = RegistryValidationResult(errors=["some error"])
        assert result.ok is False


class TestValidateCrossRegistryConsistency:
    """Tests for the cross-registry validation function."""

    def test_skips_all_checks_when_disabled(self):
        """When all checks disabled, should return ok with no issues."""
        result = validate_cross_registry_consistency(
            check_project_type_registry=False,
            check_entity_project_registry=False,
            check_pipeline_type_registry=False,
        )
        assert result.ok is True
        assert result.errors == []
        assert result.warnings == []

    def test_project_type_registry_populated_matches(self):
        """After bootstrap, ProjectTypeRegistry should match EntityRegistry."""
        from autom8_asana.models.business._bootstrap import register_all_models

        register_all_models()

        result = validate_cross_registry_consistency(
            check_project_type_registry=True,
            check_entity_project_registry=False,
        )
        assert result.ok is True
        assert result.errors == []

    def test_project_type_registry_empty_reports_errors(self):
        """Without bootstrap, ProjectTypeRegistry is empty -> errors."""
        from unittest.mock import patch

        # Prevent lazy bootstrap from auto-populating the registry
        with patch(
            "autom8_asana.models.business._bootstrap.is_bootstrap_complete",
            return_value=True,
        ):
            result = validate_cross_registry_consistency(
                check_project_type_registry=True,
                check_entity_project_registry=False,
                check_pipeline_type_registry=False,
            )
        # EntityRegistry has descriptors with GIDs and entity_types, but
        # ProjectTypeRegistry is empty (reset by autouse fixture).
        # Only descriptors with both GID AND entity_type produce errors.
        assert not result.ok
        assert len(result.errors) > 0

    def test_entity_project_registry_not_ready_warns(self):
        """When EntityProjectRegistry is not initialized, should warn."""
        result = validate_cross_registry_consistency(
            check_project_type_registry=False,
            check_entity_project_registry=True,
        )
        assert result.ok is True  # Warnings don't fail
        assert any("not yet initialized" in w for w in result.warnings)

    def test_entity_project_registry_populated_matches(self):
        """When EntityProjectRegistry has correct entries, no errors."""
        from autom8_asana.core.entity_registry import get_registry
        from autom8_asana.services.resolver import EntityProjectRegistry

        # Populate EntityProjectRegistry with entries matching EntityRegistry
        ep_registry = EntityProjectRegistry.get_instance()
        entity_registry = get_registry()
        for desc in entity_registry.all_descriptors():
            if desc.primary_project_gid is not None:
                ep_registry.register(
                    entity_type=desc.name,
                    project_gid=desc.primary_project_gid,
                    project_name=desc.display_name,
                )

        result = validate_cross_registry_consistency(
            check_project_type_registry=False,
            check_entity_project_registry=True,
        )
        assert result.ok is True
        assert result.errors == []

    def test_entity_project_registry_gid_mismatch_errors(self):
        """When EntityProjectRegistry has wrong GID, should error."""
        from autom8_asana.core.entity_registry import get_registry
        from autom8_asana.services.resolver import EntityProjectRegistry

        ep_registry = EntityProjectRegistry.get_instance()
        entity_registry = get_registry()

        # Register one entity with WRONG GID
        for desc in entity_registry.all_descriptors():
            if desc.primary_project_gid is not None:
                gid = desc.primary_project_gid
                if desc.name == "unit":
                    gid = "9999999999999999"  # Wrong GID
                ep_registry.register(
                    entity_type=desc.name,
                    project_gid=gid,
                    project_name=desc.display_name,
                )

        result = validate_cross_registry_consistency(
            check_project_type_registry=False,
            check_entity_project_registry=True,
        )
        assert not result.ok
        assert any("unit" in e and "9999999999999999" in e for e in result.errors)

    def test_full_validation_after_bootstrap(self):
        """Full validation with bootstrap should pass ProjectTypeRegistry check."""
        from autom8_asana.models.business._bootstrap import register_all_models

        register_all_models()

        result = validate_cross_registry_consistency(
            check_project_type_registry=True,
            check_entity_project_registry=False,
            check_pipeline_type_registry=False,
        )
        assert result.ok is True


class TestPipelineTypeRegistryValidation:
    """Tests for PIPELINE_TYPE_BY_PROJECT_GID cross-validation (SIG-012)."""

    def test_pipeline_type_check_finds_matching_gid(self):
        """GID '1201081073731555' maps to 'unit' in both registries — no error."""
        result = validate_cross_registry_consistency(
            check_project_type_registry=False,
            check_entity_project_registry=False,
            check_pipeline_type_registry=True,
        )
        # The 'unit' GID exists in both registries with matching names.
        # No errors should be produced for this GID.
        assert result.ok is True
        # But there should be warnings for process pipeline GIDs not in EntityRegistry
        assert len(result.warnings) > 0

    def test_pipeline_type_warns_about_unregistered_gids(self):
        """Process pipeline GIDs not in EntityRegistry produce warnings."""
        result = validate_cross_registry_consistency(
            check_project_type_registry=False,
            check_entity_project_registry=False,
            check_pipeline_type_registry=True,
        )
        # 8 of 9 PIPELINE_TYPE GIDs are process pipelines not in EntityRegistry
        pipeline_warnings = [
            w for w in result.warnings
            if "PIPELINE_TYPE_BY_PROJECT_GID" in w
        ]
        assert len(pipeline_warnings) == 8  # sales, onboarding, outreach, etc.
        # Verify one specific warning
        assert any("sales" in w for w in pipeline_warnings)

    def test_pipeline_type_detects_name_mismatch(self):
        """If a shared GID has different names, an error is produced."""
        from unittest.mock import patch

        # Patch PIPELINE_TYPE_BY_PROJECT_GID to have a name mismatch
        # GID 1201081073731555 is 'unit' in EntityRegistry
        tampered = {"1201081073731555": "wrong_name"}

        with patch(
            "autom8_asana.services.gid_push.PIPELINE_TYPE_BY_PROJECT_GID",
            tampered,
        ):
            result = validate_cross_registry_consistency(
                check_project_type_registry=False,
                check_entity_project_registry=False,
                check_pipeline_type_registry=True,
            )
        assert not result.ok
        assert any(
            "wrong_name" in e and "unit" in e
            for e in result.errors
        )

    def test_pipeline_type_check_disabled(self):
        """When check_pipeline_type_registry=False, no pipeline warnings."""
        result = validate_cross_registry_consistency(
            check_project_type_registry=False,
            check_entity_project_registry=False,
            check_pipeline_type_registry=False,
        )
        pipeline_warnings = [
            w for w in result.warnings
            if "PIPELINE_TYPE_BY_PROJECT_GID" in w
        ]
        assert pipeline_warnings == []
