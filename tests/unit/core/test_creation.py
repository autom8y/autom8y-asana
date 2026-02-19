"""Unit tests for shared creation primitives.

Covers generate_entity_name placeholder replacement logic, including
the regression test for backslash-sequence safety (RF-DST-001).
"""

from __future__ import annotations

from autom8_asana.core.creation import generate_entity_name


class _Obj:
    """Simple object with a name attribute for testing."""

    def __init__(self, name: str) -> None:
        self.name = name


class TestGenerateEntityName:
    """Tests for generate_entity_name placeholder substitution."""

    def test_business_name_placeholder_replaced(self) -> None:
        """[Business Name] is replaced with business.name."""
        result = generate_entity_name(
            "Process - [Business Name]",
            business=_Obj("Acme Corp"),
            unit=None,
        )
        assert result == "Process - Acme Corp"

    def test_unit_name_placeholder_replaced(self) -> None:
        """[Unit Name] is replaced with unit.name."""
        result = generate_entity_name(
            "Process - [Unit Name]",
            business=None,
            unit=_Obj("Dental"),
        )
        assert result == "Process - Dental"

    def test_business_unit_name_placeholder_replaced(self) -> None:
        """[Business Unit Name] is replaced with unit.name."""
        result = generate_entity_name(
            "Process - [Business Unit Name]",
            business=None,
            unit=_Obj("Dental"),
        )
        assert result == "Process - Dental"

    def test_both_placeholders_replaced(self) -> None:
        """Both [Business Name] and [Unit Name] are replaced."""
        result = generate_entity_name(
            "[Business Name] - [Unit Name] Process",
            business=_Obj("Acme"),
            unit=_Obj("Dental"),
        )
        assert result == "Acme - Dental Process"

    def test_no_template_returns_fallback(self) -> None:
        """None template returns fallback_name."""
        result = generate_entity_name(
            None,
            business=_Obj("Acme"),
            unit=None,
        )
        assert result == "New Process"

    def test_empty_template_returns_fallback(self) -> None:
        """Empty string template returns fallback_name."""
        result = generate_entity_name(
            "",
            business=_Obj("Acme"),
            unit=None,
        )
        assert result == "New Process"

    def test_custom_fallback_name(self) -> None:
        """Custom fallback_name is used when template is None."""
        result = generate_entity_name(
            None,
            business=None,
            unit=None,
            fallback_name="New Task",
        )
        assert result == "New Task"

    def test_no_business_no_unit_returns_template(self) -> None:
        """Template with no matching values returns template unchanged."""
        result = generate_entity_name(
            "Plain Process Name",
            business=None,
            unit=None,
        )
        assert result == "Plain Process Name"

    def test_business_name_with_backslash_sequence(self) -> None:
        """Regression test: business name containing \\1 is not treated as backreference.

        Without the lambda replacement fix, re.sub would interpret \\1 as a
        group backreference and produce corrupt output or raise re.error.
        """
        result = generate_entity_name(
            "Process - [Business Name]",
            business=_Obj(r"Acme \1 Corp"),
            unit=None,
        )
        assert result == r"Process - Acme \1 Corp"

    def test_unit_name_with_backslash_sequence(self) -> None:
        """Regression test: unit name containing \\1 is not treated as backreference."""
        result = generate_entity_name(
            "Process - [Unit Name]",
            business=None,
            unit=_Obj(r"Unit \1"),
        )
        assert result == r"Process - Unit \1"

    def test_case_insensitive_business_name(self) -> None:
        """[BUSINESS NAME] and [business name] are both replaced."""
        result = generate_entity_name(
            "[BUSINESS NAME] process",
            business=_Obj("Acme"),
            unit=None,
        )
        assert result == "Acme process"

    def test_placeholder_with_extra_spaces(self) -> None:
        """[Business  Name] with extra whitespace is replaced."""
        result = generate_entity_name(
            "Process [Business  Name]",
            business=_Obj("Acme"),
            unit=None,
        )
        assert result == "Process Acme"
