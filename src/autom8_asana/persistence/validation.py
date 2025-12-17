"""Input validation utilities for SaveSession and client methods.

Per TDD-TRIAGE-FIXES Issue #5: Fail-fast GID validation.
"""

from autom8_asana.persistence.exceptions import GidValidationError


def validate_gid(gid: str, param_name: str = "gid") -> None:
    """Validate GID format and raise clear error on invalid.

    Per TDD-TRIAGE-FIXES Issue #5: Fail-fast GID validation.

    Args:
        gid: The GID to validate (must be string).
        param_name: Parameter name for error message (e.g., "task_gid", "tag_gid").

    Raises:
        GidValidationError: If GID is invalid.

    Valid GID Format:
    - Non-empty string
    - Numeric characters only (0-9)
    - Length between 1 and 64 characters

    Examples:
        >>> validate_gid("1234567890")  # Valid GID - succeeds
        >>> validate_gid("abc123")      # Invalid - raises GidValidationError
        >>> validate_gid("")            # Invalid - raises GidValidationError
        >>> validate_gid(123)           # Invalid - raises GidValidationError (must be string)
    """
    # Check if input is a string
    if not isinstance(gid, str):
        raise GidValidationError(
            f"Invalid {param_name}: GID must be string, got {type(gid).__name__}. "
            f"GIDs must be non-empty numeric strings (1-64 digits). "
            f"Got: {type(gid).__name__}."
        )

    # Check if empty
    if not gid:
        raise GidValidationError(
            f"Invalid {param_name}: GID cannot be empty. "
            f"GIDs must be non-empty numeric strings (1-64 digits)."
        )

    # Check if numeric (digits only)
    if not gid.isdigit():
        raise GidValidationError(
            f"Invalid {param_name}: '{gid}'. "
            f"GIDs must be non-empty numeric strings (1-64 digits). "
            f"Got: {type(gid).__name__} with value '{gid}'."
        )

    # Check length
    if len(gid) > 64:
        raise GidValidationError(
            f"Invalid {param_name}: '{gid}' ({len(gid)} chars). "
            f"GID length must be 1-64 characters."
        )


__all__ = ["validate_gid"]
