"""Contact and ContactHolder models.

Per TDD-BIZMODEL: Contact entity with owner detection and 19 custom fields.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per FR-MODEL-004: Owner detection via OWNER_POSITIONS set.
Per FR-MODEL-005: Name parsing via nameparser integration.
Per FR-HOLDER-001, FR-HOLDER-002: ContactHolder with contacts property and owner detection.
Per ADR-0052: Cached upward references with explicit invalidation.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    ParentRef,
    TextField,
)
from autom8_asana.models.business.holder_factory import HolderFactory
from autom8_asana.models.business.mixins import UpwardTraversalMixin

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business


class Contact(BusinessEntity, UpwardTraversalMixin):
    """Contact entity within a ContactHolder.

    Per TDD-BIZMODEL: Represents a person associated with a Business.
    One contact can be designated as the "owner" via the position field.
    Per TDD-SPRINT-1 Phase 2: Uses UpwardTraversalMixin for to_business_async.

    Owner detection uses case-insensitive matching against OWNER_POSITIONS.

    Attributes:
        OWNER_POSITIONS: Set of position values indicating business ownership.

    Example:
        contact = business.contact_holder.contacts[0]
        if contact.is_owner:
            print(f"Owner: {contact.full_name}")
    """

    # Per TDD-DETECTION: Primary project GID for entity type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1200775689604552"

    # Owner position values (case-insensitive)
    OWNER_POSITIONS: ClassVar[set[str]] = {
        "owner",
        "ceo",
        "founder",
        "president",
        "principal",
    }

    # Cached upward references (ADR-0052)
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    business = ParentRef["Business"](holder_attr="_contact_holder")
    contact_holder = HolderRef["ContactHolder"]()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)

    # --- Custom Field Descriptors (ADR-0081, TDD-PATTERNS-A) ---
    # Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    # Per ADR-0082: Fields class is auto-generated from these descriptors.

    # Text fields (16)
    build_call_link = TextField()
    campaign = TextField()
    city = TextField()
    contact_email = TextField()
    contact_phone = TextField()
    contact_url = TextField(field_name="Contact URL")
    content = TextField()
    dashboard_user = TextField()
    employee_id = TextField(field_name="Employee ID")
    medium = TextField()
    nickname = TextField()
    prefix = TextField()
    profile_photo_url = TextField(field_name="Profile Photo URL")
    source = TextField()
    suffix = TextField()
    term = TextField()

    # Enum fields (3)
    position = EnumField()
    time_zone = EnumField()
    text_communication = EnumField()

    # --- Owner Detection ---

    @property
    def is_owner(self) -> bool:
        """Check if this contact is the business owner.

        Per FR-MODEL-004: Detects owner via position field matching.

        Returns:
            True if position field matches owner/ceo/founder/president/principal.
        """
        position = self.position
        if position is None:
            return False
        return position.lower().strip() in self.OWNER_POSITIONS

    # --- Upward Traversal (TDD-HYDRATION Phase 2, TDD-SPRINT-1 Phase 2) ---
    # to_business_async inherited from UpwardTraversalMixin

    def _update_refs_from_hydrated_business(self, business: Business) -> None:
        """Update Contact references to point to hydrated hierarchy.

        Per TDD-SPRINT-1 Phase 2: Hook for UpwardTraversalMixin.

        Args:
            business: The hydrated Business instance.
        """
        if business._contact_holder is not None:
            self._contact_holder = business._contact_holder
            self._business = business

    # --- Name Parsing (FR-MODEL-005) ---

    @property
    def full_name(self) -> str:
        """Full name derived from Task.name.

        Returns:
            Task name or empty string.
        """
        return self.name or ""

    @property
    def first_name(self) -> str | None:
        """First name (parsed from Task.name).

        Uses nameparser if available, otherwise splits on space.

        Returns:
            First name or None.
        """
        try:
            from nameparser import HumanName  # type: ignore[import-not-found]

            parsed = HumanName(self.name or "")
            return parsed.first or None
        except ImportError:
            # Fallback: split on space
            parts = (self.name or "").split()
            return parts[0] if parts else None

    @property
    def last_name(self) -> str | None:
        """Last name (parsed from Task.name).

        Uses nameparser if available, otherwise splits on space.

        Returns:
            Last name or None.
        """
        try:
            from nameparser import HumanName

            parsed = HumanName(self.name or "")
            return parsed.last or None
        except ImportError:
            # Fallback: split on space
            parts = (self.name or "").split()
            return parts[-1] if len(parts) > 1 else None

    @property
    def display_name(self) -> str:
        """Display name with optional prefix/suffix.

        Returns:
            Full name with prefix/suffix if set.
        """
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(self.name or "")
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts).strip()

    @property
    def preferred_name(self) -> str:
        """Nickname if set, otherwise first name.

        Returns:
            Preferred name for addressing contact.
        """
        return self.nickname or self.first_name or self.name or ""


class ContactHolder(
    HolderFactory,
    child_type="Contact",
    parent_ref="_contact_holder",
    children_attr="_contacts",
    semantic_alias="contacts",
):
    """Holder task containing Contact children.

    Per FR-HOLDER-001: ContactHolder extends Task with _contacts PrivateAttr.
    Per FR-HOLDER-002: Provides owner property for owner detection.
    Per TDD-SPRINT-1: Migrated to HolderFactory pattern.
    """

    # Per TDD-DETECTION: Primary project GID for holder type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201500116978260"

    @property
    def owner(self) -> Contact | None:
        """Get the owner contact (if any).

        Per FR-HOLDER-002: Returns first contact with is_owner=True.

        Returns:
            Owner Contact or None if no owner found.
        """
        for contact in self.children:
            if contact.is_owner:
                result: Contact = contact
                return result
        return None


# Self-register ContactHolder with HOLDER_REGISTRY (R-009)
from autom8_asana.core.registry import register_holder  # noqa: E402

register_holder("contact_holder", ContactHolder)
