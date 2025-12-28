"""Validation types for Pipeline Automation.

Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT/ADR-0018: ValidationResult for
pre/post transition validation with graceful degradation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Outcome of a transition validation.

    Per ADR-0018: Used for pre/post transition validation.
    Warnings are advisory; errors can optionally block transition.

    Attributes:
        valid: True if validation passed, False if critical errors found.
        errors: List of error messages (may block transition if validate_mode="block").
        warnings: List of warning messages (advisory, never blocks).

    Example:
        # Successful validation
        result = ValidationResult.success()
        assert result.valid is True

        # Failed validation with errors
        result = ValidationResult.failure(["Missing required field: deal_value"])
        assert result.valid is False
        assert "deal_value" in result.errors[0]

        # Validation with warnings (still valid)
        result = ValidationResult(valid=True, warnings=["Field 'notes' is empty"])
        assert result.valid is True
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def success(cls) -> ValidationResult:
        """Create a successful validation result.

        Returns:
            ValidationResult with valid=True and empty errors/warnings.
        """
        return cls(valid=True)

    @classmethod
    def failure(cls, errors: list[str]) -> ValidationResult:
        """Create a failed validation result.

        Args:
            errors: List of error messages explaining the failure.

        Returns:
            ValidationResult with valid=False and the provided errors.
        """
        return cls(valid=False, errors=errors)

    def __bool__(self) -> bool:
        """Return True if validation passed.

        Enables using ValidationResult directly in boolean context:
            if result:
                proceed_with_transition()
        """
        return self.valid

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        if self.valid:
            if self.warnings:
                return f"ValidationResult(valid=True, warnings={len(self.warnings)})"
            return "ValidationResult(valid=True)"
        return f"ValidationResult(valid=False, errors={self.errors})"
