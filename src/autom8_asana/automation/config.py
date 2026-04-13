"""Configuration for Automation Layer.

Per TDD-AUTOMATION-LAYER: Configuration dataclass for automation settings.
Per FR-006: Part of AsanaConfig for automation settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from autom8_asana.errors import ConfigurationError


@dataclass(frozen=True)
class AssigneeConfig:
    """Configurable assignee resolution cascade for pipeline stages.

    Mirrors the lifecycle AssigneeConfig pattern (lifecycle/config.py) adapted
    for the automation pipeline's Python-configured (non-YAML) stages.

    Per ADR-0113: Rep Field Cascade Pattern.
    Per FR-ASSIGN-001 through FR-ASSIGN-006.

    Attributes:
        assignee_gid: Fixed assignee GID (highest priority after assignee_source).
            When set, this GID is used directly without rep field lookup.
        assignee_source: Field name to look up on source_process or unit for a
            stage-specific assignee (lifecycle step 1). Automation stages do not
            currently use YAML-driven field lookup, so this defaults to None.
            Included for parity with lifecycle AssigneeConfig.

    Resolution order (when both None — the common automation case):
        1. assignee_source field on source_process / unit  (skipped if None)
        2. assignee_gid fixed GID                          (skipped if None)
        3. unit.rep[0]
        4. business.rep[0]
    """

    assignee_gid: str | None = None
    assignee_source: str | None = None


@dataclass
class PipelineStage:
    """Configuration for a pipeline stage.

    Per G3 Gap Fix: Defines target project and section placement for pipeline tasks.
    Per G4 Gap Fix: Supports due date configuration relative to today.

    Attributes:
        project_gid: Target Asana project GID for this pipeline stage.
        template_section: Section name containing template tasks (default: "Template").
        target_section: Section to place new tasks in (default: "Opportunity").
            New tasks are moved to this section after creation.
            Case-insensitive matching is used.
        due_date_offset_days: Days from today to set as due date (default: None).
            When None, no due date is set on new tasks.
            When specified, due date = today + offset_days.
            Supports 0 (today), positive (future), and negative (past) values.
        assignee_gid: Optional fixed assignee GID (default: None).
            When set, this GID is used directly as the assignee.
            When None, falls back to rep field cascade (Unit.rep -> Business.rep).
        business_cascade_fields: Fields to cascade from Business (default: None).
            When None, uses FieldSeeder defaults.
            When specified, overrides defaults completely.
        unit_cascade_fields: Fields to cascade from Unit (default: None).
            When None, uses FieldSeeder defaults.
            When specified, overrides defaults completely.
        process_carry_through_fields: Fields to carry through from source Process (default: None).
            When None, uses FieldSeeder defaults.
            When specified, overrides defaults completely.
        field_name_mapping: Maps source field names to target field names (default: empty).
            Use when source and target projects have different custom field names.
            Example: {"Office Phone": "Business Phone"} maps source "Office Phone"
            to target "Business Phone".

    Example:
        stage = PipelineStage(
            project_gid="1234567890123",
            template_section="Template",
            target_section="Opportunity",
            due_date_offset_days=7,  # Due in 7 days
            assignee_gid="123456789",  # Fixed assignee
            business_cascade_fields=["Company Name", "Phone"],  # Custom fields
        )
    """

    project_gid: str
    template_section: str = "Template"
    target_section: str = "Opportunity"
    due_date_offset_days: int | None = None
    assignee_gid: str | None = None
    business_cascade_fields: list[str] | None = None
    unit_cascade_fields: list[str] | None = None
    process_carry_through_fields: list[str] | None = None
    field_name_mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class AutomationConfig:
    """Configuration for Automation Layer.

    Per FR-006: Part of AsanaConfig for automation settings.

    Attributes:
        enabled: Master switch for automation (default: True).
            When False, AutomationEngine.evaluate_async() returns empty list.
        max_cascade_depth: Maximum nested automation depth (default: 5).
            Prevents circular trigger chains per FR-011.
        rules_source: Where to load rules from ("inline", "file", "api").
            V1 only supports "inline" (programmatic registration).
        pipeline_stages: ProcessType to PipelineStage mapping.
            Provides full configuration including target section placement.

    Example:
        config = AutomationConfig(
            enabled=True,
            pipeline_stages={
                "onboarding": PipelineStage(
                    project_gid="9876543210987",
                    target_section="Opportunity",
                ),
            },
        )
    """

    enabled: bool = True
    max_cascade_depth: int = 5
    rules_source: str = "inline"  # "inline" | "file" | "api"
    pipeline_stages: dict[str, PipelineStage] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration.

        Raises:
            ConfigurationError: If max_cascade_depth < 1 or rules_source invalid.
        """
        if self.max_cascade_depth < 1:
            raise ConfigurationError(
                f"max_cascade_depth must be at least 1, got {self.max_cascade_depth}"
            )
        if self.rules_source not in ("inline", "file", "api"):
            raise ConfigurationError(
                f"rules_source must be 'inline', 'file', or 'api', "
                f"got {self.rules_source!r}"
            )

    def get_pipeline_stage(self, process_type: str) -> PipelineStage | None:
        """Get pipeline stage configuration for a process type.

        Args:
            process_type: Process type name (e.g., "onboarding", "sales").

        Returns:
            PipelineStage if configured, None otherwise.
        """
        return self.pipeline_stages.get(process_type)
