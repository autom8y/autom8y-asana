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

from dataclasses import dataclass
from enum import StrEnum
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
            from nameparser import HumanName

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


# --- Ranked contact-card value objects (contact-synthesis-card-on-play, ADR §5) ---
# These live in the entity layer (not the workflow module) because
# ``ContactHolder.ranked_contacts()`` below constructs them: siting ``ContactCard``
# in ``contact_synthesis.py`` would create a circular import (that module imports
# ``ContactHolder`` from here). Keeping them here also makes ``ranked_contacts()``
# an entity-internal derivation with ZERO imports outside this module (ADR §10 AP-F;
# TDD §1 constraint). Build errata D1-D4 note in the TDD records this placement.


class Provenance(StrEnum):
    """Source tier for a ranked contact card entry (ADR §5).

    Phase-1 is Asana-only: every ``ContactCard`` carries ``ASANA``. ``EMPLOYEES`` and
    ``CORROBORATED`` are Phase-2 tiers activated purely in the workflow/service layer
    (``ContactSynthesis``) with NO reshape of this dataclass or the ranker (HANDOFF P-1).
    """

    ASANA = "asana"
    EMPLOYEES = "employees"
    CORROBORATED = "corroborated"


@dataclass
class ContactCard:
    """One ranked, provenance-annotated contact-card entry (ADR §5; TDD §3).

    A pure value object: the deterministic output of ``ContactHolder.ranked_contacts()``.
    ``rank_reason`` is MANDATORY on every card (rendered as ``<em>``) — it is the human
    picker's signal for why a row is ranked where it is, and is required even at n=1
    (94% single-contact modal case; ADR §10 AP-E).
    """

    full_name: str
    nickname: str | None
    contact_email: str | None
    role: str | None
    provenance: Provenance
    rank: int
    rank_reason: str


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

    # --- Ranked contact card (contact-synthesis-card-on-play, ADR §6; TDD §4) ---

    # Static position-weight map over the Position enum. Absent key -> weight 0.
    # Keys are lowercase; ``position`` values are matched case-insensitively (below),
    # mirroring ``Contact.is_owner`` which lowercases before comparing.
    _POSITION_WEIGHT: ClassVar[dict[str, int]] = {
        "owner": 5,
        "ceo": 5,
        "founder": 5,
        "president": 4,
        "principal": 4,
        "manager": 3,
        "director": 3,
    }

    def ranked_contacts(self) -> list[ContactCard]:
        """Return this holder's contacts as a deterministically ranked card list.

        Pure deterministic ordering over ``self.children``. No I/O, no external data,
        no rendering, no client/SDK imports (ADR §10 AP-F; TDD §1). Extends the
        ``owner`` precedent above — same bounded scope, one pure derivation.

        Ranking is a stable tuple sort, every term derived from recorded facts
        (operator ruling: no model inference; ADR §6):

        1. ``is_owner`` DESC
        2. position-weight DESC (static map; case-insensitive; absent -> 0)
        3. has-email DESC
        4. corroborated DESC (Phase-2; constant 0 at Phase-1)
        5. ``full_name`` alpha ASC (deterministic tie-break -> total order)

        Every card carries ``provenance=ASANA`` (Phase-1) and a non-empty
        ``rank_reason`` (mandatory even at n=1).

        Returns:
            Ranked ``ContactCard`` list, rank 1-based in sorted order.
        """

        def _sort_key(c: Contact) -> tuple[int, int, int, int, str]:
            position_key = (c.position or "").lower().strip()
            return (
                -int(c.is_owner),  # Tier 1: is_owner DESC
                -self._POSITION_WEIGHT.get(position_key, 0),  # Tier 2: position-weight DESC
                -int(c.contact_email is not None),  # Tier 3: has-email DESC
                0,  # Tier 4: corroborated (Phase-2; 0 at Phase-1)
                c.full_name or "",  # Tier 5: alpha ASC
            )

        def _rank_reason(c: Contact) -> str:
            if c.is_owner:
                return f"owner/{c.position}" if c.position else "owner"
            if c.position:
                return c.position
            if c.contact_email:
                return "has email on file"
            return "sole contact on file"  # n=1 case (94% of offices; ADR §6 AP-E)

        sorted_children = sorted(self.children, key=_sort_key)
        return [
            ContactCard(
                full_name=c.full_name or "",
                nickname=c.nickname or c.preferred_name,
                contact_email=c.contact_email,
                role=c.position,
                provenance=Provenance.ASANA,
                rank=i + 1,
                rank_reason=_rank_reason(c),
            )
            for i, c in enumerate(sorted_children)
        ]


# Self-register ContactHolder with HOLDER_REGISTRY (R-009)
from autom8_asana.core.registry import register_holder  # noqa: E402

register_holder("contact_holder", ContactHolder)
