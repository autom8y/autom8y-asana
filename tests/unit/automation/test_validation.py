"""Unit tests for ValidationResult.

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT: Test validation dataclass.
"""

from __future__ import annotations

from autom8_asana.automation.validation import ValidationResult


class TestValidationResultDataclass:
    """Tests for ValidationResult dataclass."""

    def test_success_factory_creates_valid_result(self) -> None:
        """Test success() creates a valid result with no errors."""
        result = ValidationResult.success()

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_failure_factory_creates_invalid_result(self) -> None:
        """Test failure() creates an invalid result with errors."""
        errors = ["Missing field: deal_value", "Empty field: close_date"]
        result = ValidationResult.failure(errors)

        assert result.valid is False
        assert result.errors == errors
        assert result.warnings == []

    def test_manual_construction_with_warnings(self) -> None:
        """Test manual construction with warnings."""
        result = ValidationResult(
            valid=True,
            warnings=["Field 'notes' is empty"],
        )

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == ["Field 'notes' is empty"]

    def test_manual_construction_with_errors_and_warnings(self) -> None:
        """Test manual construction with both errors and warnings."""
        result = ValidationResult(
            valid=False,
            errors=["Critical error"],
            warnings=["Minor issue"],
        )

        assert result.valid is False
        assert result.errors == ["Critical error"]
        assert result.warnings == ["Minor issue"]


class TestValidationResultBoolConversion:
    """Tests for ValidationResult boolean conversion."""

    def test_valid_result_is_truthy(self) -> None:
        """Test that valid results are truthy."""
        result = ValidationResult.success()
        assert bool(result) is True

    def test_invalid_result_is_falsy(self) -> None:
        """Test that invalid results are falsy."""
        result = ValidationResult.failure(["Error"])
        assert bool(result) is False

    def test_can_use_in_if_statement(self) -> None:
        """Test that ValidationResult can be used directly in if statements."""
        success = ValidationResult.success()
        failure = ValidationResult.failure(["Error"])

        # These should work without explicit .valid check
        passed = bool(success)
        assert passed is True

        passed = bool(failure)
        assert passed is False


class TestValidationResultRepr:
    """Tests for ValidationResult string representation."""

    def test_repr_valid_no_warnings(self) -> None:
        """Test repr for valid result with no warnings."""
        result = ValidationResult.success()
        assert repr(result) == "ValidationResult(valid=True)"

    def test_repr_valid_with_warnings(self) -> None:
        """Test repr for valid result with warnings."""
        result = ValidationResult(valid=True, warnings=["Warning 1", "Warning 2"])
        assert repr(result) == "ValidationResult(valid=True, warnings=2)"

    def test_repr_invalid(self) -> None:
        """Test repr for invalid result."""
        result = ValidationResult.failure(["Error 1", "Error 2"])
        assert repr(result) == "ValidationResult(valid=False, errors=['Error 1', 'Error 2'])"


class TestValidationResultEdgeCases:
    """Edge case tests for ValidationResult."""

    def test_failure_with_empty_errors_list(self) -> None:
        """Test failure factory with empty errors list still creates invalid result."""
        result = ValidationResult.failure([])
        assert result.valid is False
        assert result.errors == []

    def test_defaults_are_empty_lists(self) -> None:
        """Test that errors and warnings default to empty lists."""
        result = ValidationResult(valid=True)
        assert result.errors == []
        assert result.warnings == []

    def test_lists_are_not_shared_between_instances(self) -> None:
        """Test that default lists are not shared between instances."""
        result1 = ValidationResult(valid=True)
        result2 = ValidationResult(valid=True)

        result1.errors.append("Error added to result1")

        # result2 should not be affected
        assert result2.errors == []
