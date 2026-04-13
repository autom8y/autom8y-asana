"""Tests for lifecycle configuration loading, validation, and navigation.

Per TDD-lifecycle-engine-hardening Section 2.1:
- Pydantic validation at load time
- DAG integrity checking
- Navigation methods for stage routing

Covers FR-CONFIG-001, FR-CONFIG-002, FR-CONFIG-003.
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from autom8_asana.lifecycle.config import (
    AssigneeConfig,
    InitActionConfig,
    LifecycleConfig,
    LifecycleConfigModel,
    SeedingConfig,
    StageConfig,
    TransitionConfig,
    ValidationRuleConfig,
    WiringRuleConfig,
    load_config,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

YAML_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "lifecycle_stages.yaml"


@pytest.fixture
def config_path() -> Path:
    """Path to the real lifecycle_stages.yaml."""
    return YAML_CONFIG_PATH


@pytest.fixture
def lifecycle_config(config_path: Path) -> LifecycleConfig:
    """Lifecycle configuration loaded from production YAML."""
    return LifecycleConfig(config_path)


@pytest.fixture
def minimal_yaml(tmp_path: Path) -> Path:
    """Write a minimal valid YAML for testing."""
    data = {
        "stages": {
            "alpha": {
                "name": "alpha",
                "project_gid": "111",
                "pipeline_stage": 1,
                "transitions": {
                    "converted": "beta",
                    "did_not_convert": None,
                },
            },
            "beta": {
                "name": "beta",
                "project_gid": "222",
                "pipeline_stage": 2,
                "transitions": {
                    "converted": None,
                    "did_not_convert": "alpha",
                },
            },
        },
    }
    path = tmp_path / "test_config.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
    return path


# ---------------------------------------------------------------------------
# 1. Valid YAML loads successfully with all fields
# ---------------------------------------------------------------------------


class TestYamlLoadsSuccessfully:
    """Test that the production YAML loads and validates."""

    def test_all_stages_loaded(self, lifecycle_config: LifecycleConfig) -> None:
        """All 9 stages are present."""
        expected = {
            "outreach",
            "sales",
            "onboarding",
            "implementation",
            "month1",
            "retention",
            "reactivation",
            "account_error",
            "expansion",
        }
        assert set(lifecycle_config.stages.keys()) == expected

    def test_stage_basic_fields(self, lifecycle_config: LifecycleConfig) -> None:
        """Stage basic fields loaded correctly."""
        sales = lifecycle_config.get_stage("sales")
        assert sales is not None
        assert sales.name == "sales"
        assert sales.project_gid == "1200944186565610"
        assert sales.pipeline_stage == 2
        assert sales.template_section == "TEMPLATE"
        assert sales.target_section == "OPPORTUNITY"
        assert sales.due_date_offset_days == 0

    def test_due_date_offset(self, lifecycle_config: LifecycleConfig) -> None:
        """Onboarding has 14-day due date offset, Implementation has 30."""
        onboarding = lifecycle_config.get_stage("onboarding")
        assert onboarding is not None
        assert onboarding.due_date_offset_days == 14

        impl = lifecycle_config.get_stage("implementation")
        assert impl is not None
        assert impl.due_date_offset_days == 30

    def test_transitions_loaded(self, lifecycle_config: LifecycleConfig) -> None:
        """Transitions are loaded for each stage."""
        sales = lifecycle_config.get_stage("sales")
        assert sales is not None
        assert sales.transitions.converted == "onboarding"
        assert sales.transitions.did_not_convert == "outreach"

    def test_cascading_sections_loaded(self, lifecycle_config: LifecycleConfig) -> None:
        """Cascading sections are loaded."""
        sales = lifecycle_config.get_stage("sales")
        assert sales is not None
        assert sales.cascading_sections.offer == "Sales Process"
        assert sales.cascading_sections.unit == "Next Steps"
        assert sales.cascading_sections.business == "OPPORTUNITY"

    def test_partial_cascading_sections(self, lifecycle_config: LifecycleConfig) -> None:
        """Stages with partial cascading sections leave others as None."""
        retention = lifecycle_config.get_stage("retention")
        assert retention is not None
        assert retention.cascading_sections.offer is None
        assert retention.cascading_sections.unit == "Account Review"
        assert retention.cascading_sections.business is None

    def test_self_loop_loaded(self, lifecycle_config: LifecycleConfig) -> None:
        """Self-loop config loaded for outreach and reactivation."""
        outreach = lifecycle_config.get_stage("outreach")
        assert outreach is not None
        assert outreach.self_loop is not None
        assert outreach.self_loop.max_iterations == 5
        assert outreach.self_loop.delay_schedule == []

        reactivation = lifecycle_config.get_stage("reactivation")
        assert reactivation is not None
        assert reactivation.self_loop is not None
        assert reactivation.self_loop.max_iterations == 5
        assert reactivation.self_loop.delay_schedule == [90, 180, 360]

    def test_no_self_loop_for_sales(self, lifecycle_config: LifecycleConfig) -> None:
        """Sales has no self-loop config."""
        sales = lifecycle_config.get_stage("sales")
        assert sales is not None
        assert sales.self_loop is None

    def test_wiring_rules_loaded(self, lifecycle_config: LifecycleConfig) -> None:
        """Dependency wiring rules loaded correctly."""
        rules = lifecycle_config.get_wiring_rules("pipeline_default")
        assert rules is not None
        assert len(rules.dependents) == 2
        assert rules.dependents[0]["entity_type"] == "unit"
        assert rules.dependents[1]["entity_type"] == "offer_holder"
        assert len(rules.dependencies) == 1
        assert rules.dependencies[0]["source"] == "dna_holder"
        assert rules.dependencies[0]["filter"] == "open_plays"


# ---------------------------------------------------------------------------
# 2. New fields (TDD-hardening additions)
# ---------------------------------------------------------------------------


class TestNewFields:
    """Test new fields added by TDD-lifecycle-engine-hardening."""

    def test_dnc_action_per_stage(self, lifecycle_config: LifecycleConfig) -> None:
        """Each stage has the correct dnc_action."""
        assert lifecycle_config.get_stage("sales").dnc_action == "create_new"
        assert lifecycle_config.get_stage("onboarding").dnc_action == "reopen"
        assert lifecycle_config.get_stage("outreach").dnc_action == "deferred"
        assert lifecycle_config.get_stage("implementation").dnc_action == "create_new"

    def test_auto_complete_prior(self, lifecycle_config: LifecycleConfig) -> None:
        """auto_complete_prior is set per transition."""
        sales = lifecycle_config.get_stage("sales")
        assert sales.transitions.auto_complete_prior is True

        outreach = lifecycle_config.get_stage("outreach")
        assert outreach.transitions.auto_complete_prior is False

        onboarding = lifecycle_config.get_stage("onboarding")
        assert onboarding.transitions.auto_complete_prior is True

        impl = lifecycle_config.get_stage("implementation")
        assert impl.transitions.auto_complete_prior is True

    def test_assignee_source_per_stage(self, lifecycle_config: LifecycleConfig) -> None:
        """Assignee source is set per stage."""
        assert lifecycle_config.get_stage("sales").assignee.assignee_source == "rep"
        assert lifecycle_config.get_stage("outreach").assignee.assignee_source == "rep"
        assert (
            lifecycle_config.get_stage("onboarding").assignee.assignee_source
            == "onboarding_specialist"
        )
        assert (
            lifecycle_config.get_stage("implementation").assignee.assignee_source
            == "implementation_lead"
        )

    def test_validation_config_onboarding(self, lifecycle_config: LifecycleConfig) -> None:
        """Onboarding has pre-transition validation."""
        onboarding = lifecycle_config.get_stage("onboarding")
        assert onboarding.validation is not None
        assert onboarding.validation.pre_transition is not None
        assert onboarding.validation.pre_transition.required_fields == ["Contact Phone"]
        assert onboarding.validation.pre_transition.mode == "warn"
        assert onboarding.validation.post_transition is None

    def test_no_validation_for_sales(self, lifecycle_config: LifecycleConfig) -> None:
        """Sales has no validation config."""
        sales = lifecycle_config.get_stage("sales")
        assert sales.validation is None

    def test_seeding_config(self, lifecycle_config: LifecycleConfig) -> None:
        """Seeding config loaded for stages with computed fields."""
        onboarding = lifecycle_config.get_stage("onboarding")
        assert onboarding.seeding.computed_fields == {"Launch Date": "today"}
        assert onboarding.seeding.exclude_fields == []

        sales = lifecycle_config.get_stage("sales")
        assert sales.seeding.computed_fields == {}
        assert sales.seeding.exclude_fields == []

    def test_implementation_init_actions_enhanced(self, lifecycle_config: LifecycleConfig) -> None:
        """Implementation init actions include new fields."""
        impl = lifecycle_config.get_stage("implementation")
        assert len(impl.init_actions) == 3

        # play_creation with new fields
        play_action = impl.init_actions[0]
        assert play_action.type == "play_creation"
        assert play_action.play_type == "backend_onboard_a_business"
        assert play_action.project_gid == "1207507299545000"
        assert play_action.holder_type == "dna_holder"
        assert play_action.reopen_if_completed_within_days == 90
        assert play_action.wire_as_dependency is True

        # entity_creation with new fields
        entity_action = impl.init_actions[1]
        assert entity_action.type == "entity_creation"
        assert entity_action.entity_type == "asset_edit"
        assert entity_action.project_gid == "1203992664400125"
        assert entity_action.holder_type == "asset_edit_holder"
        assert entity_action.wire_as_dependency is True

        # create_comment
        comment_action = impl.init_actions[2]
        assert comment_action.type == "create_comment"

    def test_onboarding_init_actions_enhanced(self, lifecycle_config: LifecycleConfig) -> None:
        """Onboarding products_check has holder_type."""
        onboarding = lifecycle_config.get_stage("onboarding")
        assert len(onboarding.init_actions) == 2

        products_check = onboarding.init_actions[0]
        assert products_check.type == "products_check"
        assert products_check.condition == "video*"
        assert products_check.action == "request_source_videographer"
        assert products_check.project_gid == "1207984018149338"
        assert products_check.holder_type == "videography_holder"


# ---------------------------------------------------------------------------
# 3. YAML correction: Implementation DNC routing
# ---------------------------------------------------------------------------


class TestImplementationDncCorrection:
    """Test that Implementation DNC routes to outreach, not sales."""

    def test_implementation_dnc_target(self, lifecycle_config: LifecycleConfig) -> None:
        """Implementation did_not_convert routes to outreach (CORRECTED)."""
        impl = lifecycle_config.get_stage("implementation")
        assert impl.transitions.did_not_convert == "outreach"

    def test_implementation_converted_is_terminal(self, lifecycle_config: LifecycleConfig) -> None:
        """Implementation converted is terminal (null) for stages 1-4."""
        impl = lifecycle_config.get_stage("implementation")
        assert impl.transitions.converted is None


# ---------------------------------------------------------------------------
# 4. get_stage() returns correct config
# ---------------------------------------------------------------------------


class TestGetStage:
    """Test get_stage navigation."""

    def test_returns_stage_config(self, lifecycle_config: LifecycleConfig) -> None:
        """Returns StageConfig for valid stage name."""
        stage = lifecycle_config.get_stage("onboarding")
        assert isinstance(stage, StageConfig)
        assert stage.name == "onboarding"

    def test_returns_none_for_unknown(self, lifecycle_config: LifecycleConfig) -> None:
        """Returns None for unknown stage name."""
        assert lifecycle_config.get_stage("nonexistent") is None

    def test_returns_none_when_unloaded(self) -> None:
        """Returns None when no config loaded."""
        config = LifecycleConfig()
        assert config.get_stage("sales") is None


# ---------------------------------------------------------------------------
# 5. get_target_stage() routes correctly for all 8 paths
# ---------------------------------------------------------------------------


class TestGetTargetStage:
    """Test all 8 transition paths (4 CONVERTED + 4 DNC) for stages 1-4."""

    # CONVERTED paths
    def test_outreach_converted_to_sales(self, lifecycle_config: LifecycleConfig) -> None:
        """Outreach CONVERTED -> Sales."""
        target = lifecycle_config.get_target_stage("outreach", "converted")
        assert target is not None
        assert target.name == "sales"

    def test_sales_converted_to_onboarding(self, lifecycle_config: LifecycleConfig) -> None:
        """Sales CONVERTED -> Onboarding (PCR absorption)."""
        target = lifecycle_config.get_target_stage("sales", "converted")
        assert target is not None
        assert target.name == "onboarding"

    def test_onboarding_converted_to_implementation(
        self, lifecycle_config: LifecycleConfig
    ) -> None:
        """Onboarding CONVERTED -> Implementation."""
        target = lifecycle_config.get_target_stage("onboarding", "converted")
        assert target is not None
        assert target.name == "implementation"

    def test_implementation_converted_terminal(self, lifecycle_config: LifecycleConfig) -> None:
        """Implementation CONVERTED -> None (terminal for stages 1-4)."""
        target = lifecycle_config.get_target_stage("implementation", "converted")
        assert target is None

    # DNC paths
    def test_outreach_dnc_self_loop(self, lifecycle_config: LifecycleConfig) -> None:
        """Outreach DNC -> Outreach (self-loop)."""
        target = lifecycle_config.get_target_stage("outreach", "did_not_convert")
        assert target is not None
        assert target.name == "outreach"

    def test_sales_dnc_to_outreach(self, lifecycle_config: LifecycleConfig) -> None:
        """Sales DNC -> Outreach (create new)."""
        target = lifecycle_config.get_target_stage("sales", "did_not_convert")
        assert target is not None
        assert target.name == "outreach"

    def test_onboarding_dnc_to_sales(self, lifecycle_config: LifecycleConfig) -> None:
        """Onboarding DNC -> Sales (reopen)."""
        target = lifecycle_config.get_target_stage("onboarding", "did_not_convert")
        assert target is not None
        assert target.name == "sales"

    def test_implementation_dnc_to_outreach(self, lifecycle_config: LifecycleConfig) -> None:
        """Implementation DNC -> Outreach (CORRECTED from sales)."""
        target = lifecycle_config.get_target_stage("implementation", "did_not_convert")
        assert target is not None
        assert target.name == "outreach"

    # Edge cases
    def test_unknown_source_returns_none(self, lifecycle_config: LifecycleConfig) -> None:
        """Unknown source stage returns None."""
        assert lifecycle_config.get_target_stage("nonexistent", "converted") is None

    def test_terminal_stage_returns_none(self, lifecycle_config: LifecycleConfig) -> None:
        """Terminal transitions return None."""
        assert lifecycle_config.get_target_stage("month1", "converted") is None
        assert lifecycle_config.get_target_stage("month1", "did_not_convert") is None

    def test_invalid_outcome_returns_none(self, lifecycle_config: LifecycleConfig) -> None:
        """Invalid outcome attribute returns None (getattr fallback)."""
        assert lifecycle_config.get_target_stage("sales", "invalid_outcome") is None


# ---------------------------------------------------------------------------
# 6. get_dnc_action() returns correct action per stage
# ---------------------------------------------------------------------------


class TestGetDncAction:
    """Test get_dnc_action returns correct DNC behavior."""

    def test_sales_create_new(self, lifecycle_config: LifecycleConfig) -> None:
        assert lifecycle_config.get_dnc_action("sales") == "create_new"

    def test_onboarding_reopen(self, lifecycle_config: LifecycleConfig) -> None:
        assert lifecycle_config.get_dnc_action("onboarding") == "reopen"

    def test_outreach_deferred(self, lifecycle_config: LifecycleConfig) -> None:
        assert lifecycle_config.get_dnc_action("outreach") == "deferred"

    def test_implementation_create_new(self, lifecycle_config: LifecycleConfig) -> None:
        assert lifecycle_config.get_dnc_action("implementation") == "create_new"

    def test_unknown_stage_raises_key_error(self, lifecycle_config: LifecycleConfig) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            lifecycle_config.get_dnc_action("nonexistent")


# ---------------------------------------------------------------------------
# 7. get_transition() returns TransitionConfig
# ---------------------------------------------------------------------------


class TestGetTransition:
    """Test get_transition returns the TransitionConfig for a stage."""

    def test_returns_transition_config(self, lifecycle_config: LifecycleConfig) -> None:
        transition = lifecycle_config.get_transition("sales", "converted")
        assert isinstance(transition, TransitionConfig)
        assert transition.converted == "onboarding"
        assert transition.did_not_convert == "outreach"
        assert transition.auto_complete_prior is True

    def test_returns_none_for_unknown_stage(self, lifecycle_config: LifecycleConfig) -> None:
        assert lifecycle_config.get_transition("nonexistent", "converted") is None


# ---------------------------------------------------------------------------
# 8. DAG integrity validation
# ---------------------------------------------------------------------------


class TestDagIntegrity:
    """Test DAG integrity check catches invalid transition targets."""

    def test_unknown_converted_target(self, tmp_path: Path) -> None:
        """Unknown stage in converted target raises ValueError."""
        data = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "transitions": {
                        "converted": "nonexistent",
                        "did_not_convert": None,
                    },
                },
            },
        }
        path = tmp_path / "bad_dag.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(ValueError, match="DAG integrity check failed"):
            LifecycleConfig(path)

    def test_unknown_dnc_target(self, tmp_path: Path) -> None:
        """Unknown stage in did_not_convert target raises ValueError."""
        data = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "transitions": {
                        "converted": None,
                        "did_not_convert": "ghost",
                    },
                },
            },
        }
        path = tmp_path / "bad_dag.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(ValueError, match="DAG integrity check failed"):
            LifecycleConfig(path)

    def test_error_message_includes_stage_and_target(self, tmp_path: Path) -> None:
        """Error message identifies the offending stage and target."""
        data = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "transitions": {
                        "converted": "missing_stage",
                        "did_not_convert": None,
                    },
                },
            },
        }
        path = tmp_path / "bad_dag.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(ValueError, match="'alpha'.*'missing_stage'"):
            LifecycleConfig(path)

    def test_multiple_dag_errors_reported(self, tmp_path: Path) -> None:
        """Multiple DAG errors are reported together."""
        data = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "transitions": {
                        "converted": "ghost1",
                        "did_not_convert": "ghost2",
                    },
                },
            },
        }
        path = tmp_path / "bad_dag.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(ValueError) as exc_info:
            LifecycleConfig(path)

        error_msg = str(exc_info.value)
        assert "ghost1" in error_msg
        assert "ghost2" in error_msg

    def test_valid_dag_passes(self, minimal_yaml: Path) -> None:
        """Valid DAG with cross-references passes."""
        config = LifecycleConfig(minimal_yaml)
        assert config.get_stage("alpha") is not None
        assert config.get_stage("beta") is not None

    def test_production_yaml_passes_dag_check(self, config_path: Path) -> None:
        """Production YAML passes DAG integrity check."""
        config = LifecycleConfig(config_path)
        assert len(config.stages) > 0


# ---------------------------------------------------------------------------
# 9. Pydantic validation errors
# ---------------------------------------------------------------------------


class TestPydanticValidation:
    """Test Pydantic catches malformed YAML at load time."""

    def test_missing_transitions_key(self, tmp_path: Path) -> None:
        """Missing required 'transitions' key raises ValidationError."""
        data = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "project_gid": "111",
                    # transitions is required but missing
                },
            },
        }
        path = tmp_path / "no_transitions.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(ValidationError):
            LifecycleConfig(path)

    def test_wrong_type_pipeline_stage(self, tmp_path: Path) -> None:
        """Non-integer pipeline_stage raises ValidationError."""
        data = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "pipeline_stage": "not_a_number",
                    "transitions": {"converted": None, "did_not_convert": None},
                },
            },
        }
        path = tmp_path / "bad_type.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(ValidationError):
            LifecycleConfig(path)

    def test_invalid_dnc_action_value(self, tmp_path: Path) -> None:
        """Invalid dnc_action literal raises ValidationError."""
        data = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "dnc_action": "invalid_value",
                    "transitions": {"converted": None, "did_not_convert": None},
                },
            },
        }
        path = tmp_path / "bad_dnc.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(ValidationError):
            LifecycleConfig(path)

    def test_invalid_validation_mode(self, tmp_path: Path) -> None:
        """Invalid validation mode literal raises ValidationError."""
        data = {
            "stages": {
                "alpha": {
                    "name": "alpha",
                    "transitions": {"converted": None, "did_not_convert": None},
                    "validation": {
                        "pre_transition": {
                            "required_fields": ["Name"],
                            "mode": "crash",  # Invalid
                        },
                    },
                },
            },
        }
        path = tmp_path / "bad_mode.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)

        with pytest.raises(ValidationError):
            LifecycleConfig(path)

    def test_empty_yaml_raises(self, tmp_path: Path) -> None:
        """Empty YAML raises an error at load time."""
        path = tmp_path / "empty.yaml"
        path.write_text("")

        with pytest.raises((ValidationError, AttributeError, TypeError)):
            LifecycleConfig(path)

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Missing file raises FileNotFoundError."""
        path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            LifecycleConfig(path)


# ---------------------------------------------------------------------------
# 10. Default path resolution and load_config()
# ---------------------------------------------------------------------------


class TestLoadConfig:
    """Test load_config() and default path resolution."""

    def test_load_config_default_path(self) -> None:
        """load_config() with no path uses default."""
        config = load_config()
        assert len(config.stages) > 0
        assert config.get_stage("sales") is not None

    def test_load_config_explicit_path(self, config_path: Path) -> None:
        """load_config() with explicit path works."""
        config = load_config(config_path)
        assert len(config.stages) > 0

    def test_load_config_bad_path(self, tmp_path: Path) -> None:
        """load_config() with bad path raises."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")


# ---------------------------------------------------------------------------
# 11. Minimal YAML (custom fixture)
# ---------------------------------------------------------------------------


class TestMinimalConfig:
    """Test loading minimal valid configs."""

    def test_minimal_yaml_loads(self, minimal_yaml: Path) -> None:
        """Minimal 2-stage config loads and validates."""
        config = LifecycleConfig(minimal_yaml)
        alpha = config.get_stage("alpha")
        assert alpha is not None
        assert alpha.project_gid == "111"
        assert alpha.pipeline_stage == 1

    def test_minimal_navigation(self, minimal_yaml: Path) -> None:
        """Minimal config navigation works."""
        config = LifecycleConfig(minimal_yaml)
        target = config.get_target_stage("alpha", "converted")
        assert target is not None
        assert target.name == "beta"

        target = config.get_target_stage("beta", "did_not_convert")
        assert target is not None
        assert target.name == "alpha"

    def test_minimal_defaults(self, minimal_yaml: Path) -> None:
        """Minimal config uses defaults for optional fields."""
        config = LifecycleConfig(minimal_yaml)
        alpha = config.get_stage("alpha")
        assert alpha.template_section == "TEMPLATE"
        assert alpha.target_section == "OPPORTUNITY"
        assert alpha.due_date_offset_days == 0
        assert alpha.dnc_action == "create_new"
        assert alpha.init_actions == []
        assert alpha.self_loop is None
        assert alpha.validation is None
        assert alpha.seeding.exclude_fields == []
        assert alpha.seeding.computed_fields == {}
        assert alpha.assignee.assignee_source is None
        assert alpha.assignee.assignee_gid is None
        assert alpha.cascading_sections.offer is None
        assert alpha.cascading_sections.unit is None
        assert alpha.cascading_sections.business is None


# ---------------------------------------------------------------------------
# 12. Pydantic model classes (unit tests)
# ---------------------------------------------------------------------------


class TestPydanticModels:
    """Test individual Pydantic model construction."""

    def test_stage_config_requires_name_and_transitions(self) -> None:
        """StageConfig requires name and transitions."""
        config = StageConfig(
            name="test",
            transitions=TransitionConfig(),
        )
        assert config.name == "test"
        assert config.transitions.converted is None

    def test_init_action_config_fields(self) -> None:
        """InitActionConfig accepts all new fields."""
        action = InitActionConfig(
            type="play_creation",
            holder_type="dna_holder",
            reopen_if_completed_within_days=90,
            wire_as_dependency=True,
            comment_template="Transition from {source} to {target}",
        )
        assert action.holder_type == "dna_holder"
        assert action.reopen_if_completed_within_days == 90
        assert action.wire_as_dependency is True
        assert "Transition" in action.comment_template

    def test_validation_rule_config_defaults(self) -> None:
        """ValidationRuleConfig defaults to warn mode."""
        rule = ValidationRuleConfig()
        assert rule.mode == "warn"
        assert rule.required_fields == []

    def test_seeding_config_defaults(self) -> None:
        """SeedingConfig defaults are empty."""
        seeding = SeedingConfig()
        assert seeding.exclude_fields == []
        assert seeding.computed_fields == {}

    def test_assignee_config_defaults(self) -> None:
        """AssigneeConfig defaults are None."""
        assignee = AssigneeConfig()
        assert assignee.assignee_source is None
        assert assignee.assignee_gid is None

    def test_lifecycle_config_model_validates_dag(self) -> None:
        """LifecycleConfigModel runs DAG validation."""
        with pytest.raises(ValueError, match="DAG integrity"):
            LifecycleConfigModel(
                stages={
                    "a": StageConfig(
                        name="a",
                        transitions=TransitionConfig(converted="missing"),
                    ),
                }
            )

    def test_wiring_rule_config(self) -> None:
        """WiringRuleConfig constructs correctly."""
        rule = WiringRuleConfig(
            dependents=[{"entity_type": "unit"}],
            dependencies=[{"source": "dna_holder", "filter": "open_plays"}],
            dependency_of="implementation",
        )
        assert len(rule.dependents) == 1
        assert rule.dependency_of == "implementation"


# ---------------------------------------------------------------------------
# 13. stages property
# ---------------------------------------------------------------------------


class TestStagesProperty:
    """Test the stages property."""

    def test_stages_returns_all(self, lifecycle_config: LifecycleConfig) -> None:
        """stages property returns all configured stages."""
        stages = lifecycle_config.stages
        assert isinstance(stages, dict)
        assert "sales" in stages
        assert "onboarding" in stages

    def test_stages_empty_when_unloaded(self) -> None:
        """stages property returns empty dict when no config loaded."""
        config = LifecycleConfig()
        assert config.stages == {}


# ---------------------------------------------------------------------------
# 14. Unloaded config edge cases
# ---------------------------------------------------------------------------


class TestUnloadedConfig:
    """Test behavior when LifecycleConfig has no loaded model."""

    def test_get_stage_returns_none(self) -> None:
        config = LifecycleConfig()
        assert config.get_stage("sales") is None

    def test_get_target_stage_returns_none(self) -> None:
        config = LifecycleConfig()
        assert config.get_target_stage("sales", "converted") is None

    def test_get_transition_returns_none(self) -> None:
        config = LifecycleConfig()
        assert config.get_transition("sales", "converted") is None

    def test_get_wiring_rules_returns_none(self) -> None:
        config = LifecycleConfig()
        assert config.get_wiring_rules("pipeline_default") is None
