"""Unit tests for AutomationConfig.

Per TDD-AUTOMATION-LAYER: Test configuration validation.
"""

from __future__ import annotations

import pytest

from autom8_asana.automation.config import AutomationConfig, PipelineStage
from autom8_asana.exceptions import ConfigurationError


class TestAutomationConfig:
    """Tests for AutomationConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = AutomationConfig()

        assert config.enabled is True
        assert config.max_cascade_depth == 5
        assert config.rules_source == "inline"
        assert config.pipeline_templates == {}

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = AutomationConfig(
            enabled=False,
            max_cascade_depth=3,
            rules_source="file",
            pipeline_templates={"sales": "123", "onboarding": "456"},
        )

        assert config.enabled is False
        assert config.max_cascade_depth == 3
        assert config.rules_source == "file"
        assert config.pipeline_templates == {"sales": "123", "onboarding": "456"}

    @pytest.mark.parametrize(
        "depth",
        [
            pytest.param(0, id="zero"),
            pytest.param(-1, id="negative"),
        ],
    )
    def test_max_cascade_depth_validation_invalid(self, depth: int) -> None:
        """Test that max_cascade_depth < 1 raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            AutomationConfig(max_cascade_depth=depth)

        assert "max_cascade_depth must be at least 1" in str(exc_info.value)

    def test_max_cascade_depth_one_is_valid(self) -> None:
        """Test that max_cascade_depth=1 is valid."""
        config = AutomationConfig(max_cascade_depth=1)
        assert config.max_cascade_depth == 1

    def test_rules_source_validation_invalid(self) -> None:
        """Test that invalid rules_source raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            AutomationConfig(rules_source="database")

        assert "rules_source must be 'inline', 'file', or 'api'" in str(exc_info.value)

    @pytest.mark.parametrize(
        "source",
        [
            pytest.param("inline", id="inline"),
            pytest.param("file", id="file"),
            pytest.param("api", id="api"),
        ],
    )
    def test_rules_source_valid_values(self, source: str) -> None:
        """Test that valid rules_source values are accepted."""
        config = AutomationConfig(rules_source=source)
        assert config.rules_source == source

    def test_pipeline_templates_mutable(self) -> None:
        """Test that pipeline_templates can be modified."""
        config = AutomationConfig()
        config.pipeline_templates["new_pipeline"] = "789"

        assert config.pipeline_templates == {"new_pipeline": "789"}


class TestPipelineStage:
    """Tests for PipelineStage dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        stage = PipelineStage(project_gid="123456")

        assert stage.project_gid == "123456"
        assert stage.template_section == "Template"
        assert stage.target_section == "Opportunity"
        assert stage.due_date_offset_days is None
        assert stage.assignee_gid is None
        assert stage.business_cascade_fields is None
        assert stage.unit_cascade_fields is None
        assert stage.process_carry_through_fields is None

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        stage = PipelineStage(
            project_gid="123456",
            template_section="My Templates",
            target_section="New Leads",
            due_date_offset_days=7,
            assignee_gid="user123",
            business_cascade_fields=["Field 1", "Field 2"],
            unit_cascade_fields=["Field 3"],
            process_carry_through_fields=["Field 4", "Field 5"],
        )

        assert stage.project_gid == "123456"
        assert stage.template_section == "My Templates"
        assert stage.target_section == "New Leads"
        assert stage.due_date_offset_days == 7
        assert stage.assignee_gid == "user123"
        assert stage.business_cascade_fields == ["Field 1", "Field 2"]
        assert stage.unit_cascade_fields == ["Field 3"]
        assert stage.process_carry_through_fields == ["Field 4", "Field 5"]

    def test_due_date_offset_zero(self) -> None:
        """Test due_date_offset_days=0 means today."""
        stage = PipelineStage(
            project_gid="123456",
            due_date_offset_days=0,
        )
        assert stage.due_date_offset_days == 0

    def test_due_date_offset_negative(self) -> None:
        """Test negative due_date_offset_days for past dates."""
        stage = PipelineStage(
            project_gid="123456",
            due_date_offset_days=-3,
        )
        assert stage.due_date_offset_days == -3

    def test_get_pipeline_stage_from_config(self) -> None:
        """Test getting PipelineStage from AutomationConfig."""
        config = AutomationConfig(
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="123456",
                    due_date_offset_days=7,
                    assignee_gid="user123",
                ),
            },
        )

        stage = config.get_pipeline_stage("onboarding")
        assert stage is not None
        assert stage.project_gid == "123456"
        assert stage.due_date_offset_days == 7
        assert stage.assignee_gid == "user123"

    def test_get_pipeline_stage_fallback_to_templates(self) -> None:
        """Test get_pipeline_stage falls back to pipeline_templates."""
        config = AutomationConfig(
            pipeline_templates={"onboarding": "789"},
        )

        stage = config.get_pipeline_stage("onboarding")
        assert stage is not None
        assert stage.project_gid == "789"
        # Defaults for fallback stage
        assert stage.due_date_offset_days is None
        assert stage.assignee_gid is None

    def test_get_pipeline_stage_prefers_stages_over_templates(self) -> None:
        """Test that pipeline_stages takes precedence over pipeline_templates."""
        config = AutomationConfig(
            pipeline_templates={"onboarding": "old_gid"},
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="new_gid",
                    due_date_offset_days=5,
                ),
            },
        )

        stage = config.get_pipeline_stage("onboarding")
        assert stage is not None
        assert stage.project_gid == "new_gid"
        assert stage.due_date_offset_days == 5
