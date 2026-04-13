"""Tests for M-03: Topological sort cycle-break fires with a warning log.

Verifies that when cascade_warm_phases() encounters a cycle in the
dependency graph, it logs a warning with diagnostic details instead
of silently breaking the cycle.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_descriptor(name: str, *, priority: int = 10, is_provider: bool = False) -> MagicMock:
    """Create a mock EntityDescriptor for warmable_entities()."""
    desc = MagicMock()
    desc.name = name
    desc.warm_priority = priority
    desc.cascading_field_provider = is_provider
    desc.effective_schema_key = f"Test{name.title()}"
    desc.get_model_class.return_value = type(f"Mock{name.title()}", (), {})
    return desc


def _make_schema(cascade_columns: list[tuple[str, str]]) -> MagicMock:
    """Create a mock schema with specific cascade columns."""
    schema = MagicMock()
    schema.get_cascade_columns.return_value = cascade_columns
    return schema


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCascadeCycleDetectionLogging:
    """M-03: cycle-break in topological sort must emit a warning."""

    def test_cycle_detected_logs_warning(self) -> None:
        """When two entities form a circular dependency, logger.warning fires
        with 'cascade_topological_cycle_detected'."""
        from autom8_asana.dataframes.cascade_utils import cascade_warm_phases

        # Set up two entities: alpha depends on beta, beta depends on alpha
        desc_alpha = _make_descriptor("alpha", priority=1, is_provider=True)
        desc_beta = _make_descriptor("beta", priority=2, is_provider=True)

        alpha_model = desc_alpha.get_model_class()
        beta_model = desc_beta.get_model_class()

        # Entity registry
        mock_entity_registry = MagicMock()
        mock_entity_registry.all_descriptors.return_value = [desc_alpha, desc_beta]
        mock_entity_registry.warmable_entities.return_value = [desc_alpha, desc_beta]

        # Cascading field registry: alpha provides "FieldA", beta provides "FieldB"
        field_def_a = MagicMock()
        field_def_a.name = "FieldA"
        field_def_a.source_field = None

        field_def_b = MagicMock()
        field_def_b.name = "FieldB"
        field_def_b.source_field = None

        cascade_registry = {
            "field_a": (alpha_model, field_def_a),
            "field_b": (beta_model, field_def_b),
        }

        # Schema registry: alpha consumes FieldB (from beta), beta consumes FieldA (from alpha)
        schema_alpha = _make_schema([("col_b", "FieldB")])  # alpha depends on beta
        schema_beta = _make_schema([("col_a", "FieldA")])  # beta depends on alpha

        mock_schema_registry = MagicMock()

        def _get_schema(key: str) -> MagicMock:
            if key == "TestAlpha":
                return schema_alpha
            if key == "TestBeta":
                return schema_beta
            raise KeyError(key)

        mock_schema_registry.get_schema.side_effect = _get_schema

        with (
            patch(
                "autom8_asana.core.entity_registry.get_registry",
                return_value=mock_entity_registry,
            ),
            patch(
                "autom8_asana.dataframes.models.registry.SchemaRegistry.get_instance",
                return_value=mock_schema_registry,
            ),
            patch(
                "autom8_asana.models.business.fields.get_cascading_field_registry",
                return_value=cascade_registry,
            ),
            patch("autom8_asana.dataframes.cascade_utils.logger") as mock_logger,
        ):
            phases = cascade_warm_phases()

        # Cycle-break should have fired: all entities land in one phase
        assert len(phases) == 1
        assert sorted(phases[0]) == ["alpha", "beta"]

        # Verify the warning was logged
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c[0][0] == "cascade_topological_cycle_detected"
        ]
        assert len(warning_calls) == 1
        extra = warning_calls[0][1]["extra"]
        assert extra["remaining_count"] == 2
        assert sorted(extra["remaining_entities"]) == ["alpha", "beta"]
        assert extra["phase_count"] == 0  # no phases completed before cycle

    def test_no_cycle_does_not_log_warning(self) -> None:
        """Normal (acyclic) dependency graph should NOT trigger the warning."""
        from autom8_asana.dataframes.cascade_utils import cascade_warm_phases

        # Set up: alpha provides, beta consumes (no cycle)
        desc_alpha = _make_descriptor("alpha", priority=1, is_provider=True)
        desc_beta = _make_descriptor("beta", priority=2, is_provider=False)

        alpha_model = desc_alpha.get_model_class()

        mock_entity_registry = MagicMock()
        mock_entity_registry.all_descriptors.return_value = [desc_alpha, desc_beta]
        mock_entity_registry.warmable_entities.return_value = [desc_alpha, desc_beta]

        field_def_a = MagicMock()
        field_def_a.name = "FieldA"
        field_def_a.source_field = None

        cascade_registry = {
            "field_a": (alpha_model, field_def_a),
        }

        # Beta depends on alpha (consumes FieldA), but alpha has no deps
        schema_alpha = _make_schema([])
        schema_beta = _make_schema([("col_a", "FieldA")])

        mock_schema_registry = MagicMock()

        def _get_schema(key: str) -> MagicMock:
            if key == "TestAlpha":
                return schema_alpha
            if key == "TestBeta":
                return schema_beta
            raise KeyError(key)

        mock_schema_registry.get_schema.side_effect = _get_schema

        with (
            patch(
                "autom8_asana.core.entity_registry.get_registry",
                return_value=mock_entity_registry,
            ),
            patch(
                "autom8_asana.dataframes.models.registry.SchemaRegistry.get_instance",
                return_value=mock_schema_registry,
            ),
            patch(
                "autom8_asana.models.business.fields.get_cascading_field_registry",
                return_value=cascade_registry,
            ),
            patch("autom8_asana.dataframes.cascade_utils.logger") as mock_logger,
        ):
            phases = cascade_warm_phases()

        # Should produce 2 phases (alpha first, beta second), no cycle
        assert len(phases) == 2
        assert phases[0] == ["alpha"]
        assert phases[1] == ["beta"]

        # No cycle warning
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c[0][0] == "cascade_topological_cycle_detected"
        ]
        assert len(warning_calls) == 0

    def test_cycle_break_extra_contains_diagnostic_fields(self) -> None:
        """The warning extra dict must include remaining_count, remaining_entities,
        and phase_count for operational debugging."""
        from autom8_asana.dataframes.cascade_utils import cascade_warm_phases

        # Three entities: a->b->c->a (three-way cycle)
        desc_a = _make_descriptor("a", priority=1, is_provider=True)
        desc_b = _make_descriptor("b", priority=2, is_provider=True)
        desc_c = _make_descriptor("c", priority=3, is_provider=True)

        model_a = desc_a.get_model_class()
        model_b = desc_b.get_model_class()
        model_c = desc_c.get_model_class()

        mock_entity_registry = MagicMock()
        mock_entity_registry.all_descriptors.return_value = [desc_a, desc_b, desc_c]
        mock_entity_registry.warmable_entities.return_value = [desc_a, desc_b, desc_c]

        field_a = MagicMock()
        field_a.name = "FA"
        field_a.source_field = None
        field_b = MagicMock()
        field_b.name = "FB"
        field_b.source_field = None
        field_c = MagicMock()
        field_c.name = "FC"
        field_c.source_field = None

        cascade_registry = {
            "fa": (model_a, field_a),
            "fb": (model_b, field_b),
            "fc": (model_c, field_c),
        }

        # a consumes FC (from c), b consumes FA (from a), c consumes FB (from b)
        schema_a = _make_schema([("col_c", "FC")])
        schema_b = _make_schema([("col_a", "FA")])
        schema_c = _make_schema([("col_b", "FB")])

        mock_schema_registry = MagicMock()

        def _get_schema(key: str) -> MagicMock:
            return {"TestA": schema_a, "TestB": schema_b, "TestC": schema_c}[key]

        mock_schema_registry.get_schema.side_effect = _get_schema

        with (
            patch(
                "autom8_asana.core.entity_registry.get_registry",
                return_value=mock_entity_registry,
            ),
            patch(
                "autom8_asana.dataframes.models.registry.SchemaRegistry.get_instance",
                return_value=mock_schema_registry,
            ),
            patch(
                "autom8_asana.models.business.fields.get_cascading_field_registry",
                return_value=cascade_registry,
            ),
            patch("autom8_asana.dataframes.cascade_utils.logger") as mock_logger,
        ):
            phases = cascade_warm_phases()

        # All three land in a single phase due to cycle break
        assert len(phases) == 1
        assert sorted(phases[0]) == ["a", "b", "c"]

        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c[0][0] == "cascade_topological_cycle_detected"
        ]
        assert len(warning_calls) == 1
        extra = warning_calls[0][1]["extra"]
        assert "remaining_count" in extra
        assert "remaining_entities" in extra
        assert "phase_count" in extra
        assert extra["remaining_count"] == 3
