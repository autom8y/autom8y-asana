"""Cross-service identifier for business scoping.

Per ADR-INS-001: Owned by autom8_asana, not a shared package.
Per parent spike: Version-prefixed canonical_key (pv1:) for future migration.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterator

from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business


class PhoneVerticalPair(BaseModel):
    """Immutable identifier for a business by phone number and vertical.

    This model represents the unique business identifier used for cross-service
    communication with autom8_data satellite service. It provides:
    - E.164 phone number validation
    - Version-prefixed canonical key for caching/routing
    - Tuple unpacking for backward compatibility
    - Hashability for use as dict key

    Attributes:
        office_phone: E.164 formatted phone number (e.g., +17705753103)
        vertical: Business vertical (e.g., chiropractic, dental)

    Example:
        >>> pvp = PhoneVerticalPair(
        ...     office_phone="+17705753103",
        ...     vertical="chiropractic"
        ... )
        >>> pvp.canonical_key
        'pv1:+17705753103:chiropractic'
        >>> phone, vertical = pvp  # tuple unpacking
        >>> pvp[0]  # index access
        '+17705753103'
    """

    model_config = ConfigDict(
        frozen=True,  # Immutable for hashability
        str_strip_whitespace=True,
    )

    office_phone: str
    vertical: str

    @field_validator("office_phone")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        """Validate E.164 phone format.

        Per ITU-T E.164: + followed by 1-15 digits, where the first digit
        after + must be non-zero (country code cannot start with 0).

        Args:
            v: Phone number string to validate.

        Returns:
            Validated phone number.

        Raises:
            ValueError: If phone format is invalid.
        """
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError(
                f"Invalid E.164 format: {v}. "
                f"Expected format: +[country][number] (e.g., +17705753103)"
            )
        return v

    @property
    def canonical_key(self) -> str:
        """Version-prefixed cache/routing key.

        Per parent spike ADR-PVP-002: pv1: prefix enables graceful
        migration to pv2: if multi-tenant requirements emerge.

        Returns:
            Canonical key in format 'pv1:{phone}:{vertical}'.
        """
        return f"pv1:{self.office_phone}:{self.vertical}"

    # --- Backward compatibility with tuple unpacking (per legacy namedtuple) ---

    def __iter__(self) -> Iterator[str]:  # type: ignore[override]
        """Enable tuple unpacking: phone, vertical = pvp.

        Note: This intentionally overrides Pydantic's __iter__ to provide
        tuple-like behavior for backward compatibility with legacy namedtuple.

        Returns:
            Iterator over (office_phone, vertical).
        """
        return iter((self.office_phone, self.vertical))

    def __getitem__(self, index: int) -> str:
        """Enable index access: pvp[0], pvp[1].

        Args:
            index: 0 for office_phone, 1 for vertical.

        Returns:
            Field value at index.

        Raises:
            IndexError: If index is out of range.
        """
        return (self.office_phone, self.vertical)[index]

    def __hash__(self) -> int:
        """Enable use as dict key / set member.

        Returns:
            Hash based on (office_phone, vertical) tuple.
        """
        return hash((self.office_phone, self.vertical))

    @classmethod
    def from_business(cls, business: "Business") -> "PhoneVerticalPair":
        """Create PhoneVerticalPair from Business entity.

        This factory method extracts office_phone and vertical from a
        Business model instance, validating that both required fields
        are present.

        Args:
            business: Business model with office_phone and vertical fields.

        Returns:
            PhoneVerticalPair instance.

        Raises:
            InsightsValidationError: If office_phone or vertical is None.
        """
        from autom8_asana.exceptions import InsightsValidationError

        if not business.office_phone:
            raise InsightsValidationError(
                "Cannot create PhoneVerticalPair: office_phone is required",
                field="office_phone",
            )
        if not business.vertical:
            raise InsightsValidationError(
                "Cannot create PhoneVerticalPair: vertical is required",
                field="vertical",
            )
        return cls(
            office_phone=business.office_phone,
            vertical=business.vertical,
        )
