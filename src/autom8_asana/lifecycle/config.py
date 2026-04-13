# src/autom8_asana/lifecycle/config.py

"""Pydantic config models + YAML loader + DAG validation.

Per TDD-lifecycle-engine-hardening Section 2.1:
- Pydantic BaseModel replaces frozen dataclasses
- Startup validation with DAG integrity checking
- Fail-fast on malformed YAML

FR Coverage: FR-CONFIG-001, FR-CONFIG-002, FR-CONFIG-003, NFR-003, NFR-004

Error Contract:
- pydantic.ValidationError on malformed YAML at load time
- ValueError on DAG integrity failure
- FileNotFoundError if YAML file is missing
- All three are hard-fail at startup. No runtime config errors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class SelfLoopConfig(BaseModel):
    """Configuration for self-loop stages."""

    max_iterations: int = 5
    delay_schedule: list[int] = Field(default_factory=list)


class InitActionConfig(BaseModel):
    """Configuration for init-time actions on a stage."""

    type: str
    condition: str | None = None
    play_type: str | None = None
    project_gid: str | None = None
    entity_type: str | None = None
    action: str | None = None
    # Reopen-or-create params
    reopen_if_completed_within_days: int | None = None
    always_create_new: bool = False
    # Comment template
    comment_template: str | None = None
    # Holder type for hierarchy placement
    holder_type: str | None = None
    # Dependency wiring flag
    wire_as_dependency: bool = False


class ValidationRuleConfig(BaseModel):
    """Validation rules for a transition."""

    required_fields: list[str] = Field(default_factory=list)
    mode: Literal["warn", "block"] = "warn"


class ValidationConfig(BaseModel):
    """Pre/post validation for a stage."""

    pre_transition: ValidationRuleConfig | None = None
    post_transition: ValidationRuleConfig | None = None


class CascadingSectionConfig(BaseModel):
    """Sections to set on related entities."""

    offer: str | None = None
    unit: str | None = None
    business: str | None = None


class TransitionConfig(BaseModel):
    """Transition routing for a stage."""

    converted: str | None = None
    did_not_convert: str | None = None
    # Explicit per-transition auto-completion (FR-COMPLETE-001)
    auto_complete_prior: bool = False


class SeedingConfig(BaseModel):
    """Field seeding configuration per stage."""

    exclude_fields: list[str] = Field(default_factory=list)
    computed_fields: dict[str, str] = Field(default_factory=dict)
    # e.g., {"Launch Date": "today", "Status": "New"}


class AssigneeConfig(BaseModel):
    """Assignee resolution per stage."""

    assignee_source: str | None = None  # e.g., "rep", "onboarding_specialist"
    assignee_gid: str | None = None  # fixed fallback GID


class StageConfig(BaseModel):
    """Complete configuration for a lifecycle stage."""

    name: str
    project_gid: str | None = None
    pipeline_stage: int = 0
    template_section: str = "TEMPLATE"
    template_section_gid: str | None = None
    target_section: str = "OPPORTUNITY"
    due_date_offset_days: int = 0

    transitions: TransitionConfig
    cascading_sections: CascadingSectionConfig = Field(default_factory=CascadingSectionConfig)
    init_actions: list[InitActionConfig] = Field(default_factory=list)
    self_loop: SelfLoopConfig | None = None
    validation: ValidationConfig | None = None
    seeding: SeedingConfig = Field(default_factory=SeedingConfig)
    assignee: AssigneeConfig = Field(default_factory=AssigneeConfig)

    # DNC routing behavior
    dnc_action: Literal["create_new", "reopen", "deferred"] = "create_new"


class WiringRuleConfig(BaseModel):
    """Dependency wiring rule."""

    dependents: list[dict[str, str]] = Field(default_factory=list)
    dependencies: list[dict[str, str]] = Field(default_factory=list)
    dependency_of: str | None = None


class LifecycleConfigModel(BaseModel):
    """Top-level Pydantic model for lifecycle_stages.yaml."""

    stages: dict[str, StageConfig]
    dependency_wiring: dict[str, WiringRuleConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dag_integrity(self) -> LifecycleConfigModel:
        """Validate that all transition targets reference defined stages."""
        stage_names = set(self.stages.keys())
        errors: list[str] = []
        for name, stage in self.stages.items():
            if stage.transitions.converted and stage.transitions.converted not in stage_names:
                errors.append(
                    f"Stage '{name}' converted target "
                    f"'{stage.transitions.converted}' is not a defined stage"
                )
            if (
                stage.transitions.did_not_convert
                and stage.transitions.did_not_convert not in stage_names
            ):
                errors.append(
                    f"Stage '{name}' did_not_convert target "
                    f"'{stage.transitions.did_not_convert}' is not a defined stage"
                )
        if errors:
            raise ValueError(f"DAG integrity check failed: {'; '.join(errors)}")
        return self


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (contains config/)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config" / "lifecycle_stages.yaml").exists():
            return current
        current = current.parent
    msg = "Could not locate project root containing config/lifecycle_stages.yaml"
    raise FileNotFoundError(msg)


def load_config(path: Path | None = None) -> LifecycleConfig:
    """Load lifecycle configuration from YAML.

    Args:
        path: Path to YAML file. Defaults to config/lifecycle_stages.yaml
              relative to the project root.

    Returns:
        LifecycleConfig instance with validated configuration.

    Raises:
        pydantic.ValidationError: On malformed config.
        ValueError: On DAG integrity failure.
        FileNotFoundError: If config file missing.
    """
    if path is None:
        root = _find_project_root()
        path = root / "config" / "lifecycle_stages.yaml"
    return LifecycleConfig(path)


class LifecycleConfig:
    """Loads and provides access to lifecycle stage configuration.

    Validates at load time via Pydantic. Raises ValidationError on
    malformed YAML (fail-fast, not fail-at-transition).
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._model: LifecycleConfigModel | None = None
        if config_path:
            self._load(config_path)

    def _load(self, path: Path) -> None:
        """Load and validate configuration from YAML file.

        Raises:
            pydantic.ValidationError: On malformed config.
            ValueError: On DAG integrity failure.
            FileNotFoundError: If config file missing.
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        # Inject stage names into stage dicts before validation
        for name, stage_data in data.get("stages", {}).items():
            stage_data["name"] = name

        self._model = LifecycleConfigModel.model_validate(data)

    def get_stage(self, name: str) -> StageConfig | None:
        """Get stage configuration by name.

        Args:
            name: Stage name (e.g., "sales", "onboarding").

        Returns:
            StageConfig if found, None otherwise.
        """
        if self._model is None:
            return None
        return self._model.stages.get(name)

    def get_target_stage(self, source_stage: str, outcome: str) -> StageConfig | None:
        """Get target stage for a transition.

        Args:
            source_stage: Current stage name (e.g., "sales").
            outcome: Transition outcome ("converted" or "did_not_convert").

        Returns:
            Target StageConfig, or None if terminal.
        """
        source = self.get_stage(source_stage)
        if source is None:
            return None
        target_name = getattr(source.transitions, outcome, None)
        if target_name is None:
            return None
        return self.get_stage(target_name)

    def get_transition(self, source_stage: str, outcome: str) -> TransitionConfig | None:
        """Get transition config for a stage and outcome.

        Args:
            source_stage: Current stage name (e.g., "sales").
            outcome: Transition outcome ("converted" or "did_not_convert").

        Returns:
            TransitionConfig if source stage exists, None otherwise.
        """
        source = self.get_stage(source_stage)
        if source is None:
            return None
        return source.transitions

    def get_dnc_action(self, source_stage: str) -> str:
        """Get DNC routing action for a stage.

        Args:
            source_stage: Stage name (e.g., "onboarding").

        Returns:
            "create_new", "reopen", or "deferred".

        Raises:
            KeyError: If source_stage is not defined.
        """
        stage = self.get_stage(source_stage)
        if stage is None:
            raise KeyError(f"Stage '{source_stage}' is not defined")
        return stage.dnc_action

    def get_wiring_rules(self, entity_type: str) -> WiringRuleConfig | None:
        """Get wiring rules for an entity type.

        Args:
            entity_type: Entity type key (e.g., "pipeline_default").

        Returns:
            WiringRuleConfig if found, None otherwise.
        """
        if self._model is None:
            return None
        return self._model.dependency_wiring.get(entity_type)

    @property
    def stages(self) -> dict[str, StageConfig]:
        """All stage configurations keyed by name."""
        if self._model is None:
            return {}
        return self._model.stages

    def build_derivation_table(self) -> dict[str, str]:
        """Build process-type -> unit-section derivation table from YAML config.

        Returns a mapping of stage name to unit section for all stages that
        define a ``cascading_sections.unit`` value.  Used by the reconciliation
        processor to derive the expected unit section from the latest active
        process pipeline type.

        Per ADR-derivation-table-hardcoded-dict: this is the single source of
        truth once all stages define their ``unit`` cascading section.
        """
        table: dict[str, str] = {}
        for name, stage in self.stages.items():
            if stage.cascading_sections and stage.cascading_sections.unit:
                table[name] = stage.cascading_sections.unit
        return table
