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

from autom8_asana.models.business.base import BusinessEntity, HolderMixin
from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    ParentRef,
    TextField,
)
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import Business


class Contact(BusinessEntity):
    """Contact entity within a ContactHolder.

    Per TDD-BIZMODEL: Represents a person associated with a Business.
    One contact can be designated as the "owner" via the position field.

    Owner detection uses case-insensitive matching against OWNER_POSITIONS.

    Attributes:
        OWNER_POSITIONS: Set of position values indicating business ownership.

    Example:
        contact = business.contact_holder.contacts[0]
        if contact.is_owner:
            print(f"Owner: {contact.full_name}")
    """

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

    # --- Upward Traversal (TDD-HYDRATION Phase 2) ---

    async def to_business_async(
        self,
        client: AsanaClient,
        *,
        hydrate_full: bool = True,
        partial_ok: bool = False,
    ) -> Business:
        """Navigate to containing Business and optionally hydrate full hierarchy.

        Per ADR-0069: Instance method for upward navigation.
        Per FR-UP-001: Contact upward traversal.
        Per ADR-0070: partial_ok controls fail-fast vs partial success behavior.

        Path: Contact -> ContactHolder -> Business (2 levels up)

        This method traverses the parent chain to find the Business root,
        then optionally hydrates the full Business hierarchy. After hydration,
        this Contact instance's references are updated to point to the
        hydrated hierarchy.

        Args:
            client: AsanaClient for API calls.
            hydrate_full: If True (default), hydrate full Business hierarchy
                after finding it. If False, only populates the path traversed.
            partial_ok: If True, continue on partial failures during hydration.
                If False (default), raise HydrationError on any failure.

        Returns:
            Business instance (fully hydrated if hydrate_full=True).

        Raises:
            HydrationError: If traversal fails (no parent, cycle detected,
                max depth exceeded) or if hydration fails and partial_ok=False.

        Example:
            contact = Contact.model_validate(task_data)
            business = await contact.to_business_async(client)

            # Business is fully hydrated
            print(f"Business: {business.name}")
            for unit in business.units:
                print(f"  Unit: {unit.name}")

            # Contact references are updated
            assert contact.business is business
        """
        from autom8_asana.exceptions import HydrationError
        from autom8_asana.models.business.hydration import _traverse_upward_async

        # Traverse upward to find Business
        business, path = await _traverse_upward_async(self, client)

        # Hydrate full hierarchy if requested
        if hydrate_full:
            try:
                await business._fetch_holders_async(client)
            except Exception as e:
                if partial_ok:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        "Hydration failed with partial_ok=True",
                        extra={"business_gid": business.gid, "error": str(e)},
                    )
                else:
                    if isinstance(e, HydrationError):
                        raise
                    raise HydrationError(
                        f"Downward hydration failed for Business {business.gid}: {e}",
                        entity_gid=business.gid,
                        entity_type="business",
                        phase="downward",
                        cause=e,
                    ) from e

        # Update this Contact's references to point to hydrated hierarchy
        # Find the ContactHolder in the hydrated Business
        if business._contact_holder is not None:
            self._contact_holder = business._contact_holder
            self._business = business

        return business

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

class ContactHolder(Task, HolderMixin[Contact]):
    """Holder task containing Contact children.

    Per FR-HOLDER-001: ContactHolder extends Task with _contacts PrivateAttr.
    Per FR-HOLDER-002: Provides owner property for owner detection.
    Per TDD-HARDENING-C: Uses ClassVar configuration for generic _populate_children().
    """

    # ClassVar configuration (TDD-HARDENING-C)
    CHILD_TYPE: ClassVar[type[Contact]] = Contact
    PARENT_REF_NAME: ClassVar[str] = "_contact_holder"
    CHILDREN_ATTR: ClassVar[str] = "_contacts"

    # Children storage
    _contacts: list[Contact] = PrivateAttr(default_factory=list)

    # Back-reference to parent Business (ADR-0052)
    _business: Business | None = PrivateAttr(default=None)

    # _populate_children() inherited from HolderMixin (TDD-HARDENING-C)

    @property
    def contacts(self) -> list[Contact]:
        """All Contact children.

        Returns:
            List of Contact entities.
        """
        return self._contacts

    @property
    def owner(self) -> Contact | None:
        """Get the owner contact (if any).

        Per FR-HOLDER-002: Returns first contact with is_owner=True.

        Returns:
            Owner Contact or None if no owner found.
        """
        for contact in self._contacts:
            if contact.is_owner:
                return contact
        return None

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business.

        Returns:
            Business entity or None if not populated.
        """
        return self._business
