"""DNA entity - minimal typed model for DNAHolder children.

Per TDD-HARDENING-A/FR-STUB-001: Minimal typed model providing type-safe
children and bidirectional navigation.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
Per TDD-lifecycle-engine: Added 4 custom field descriptors for lifecycle support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    ParentRef,
    TextField,
)

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business, DNAHolder


class DNA(BusinessEntity):
    """DNA entity - child of DNAHolder.

    Per TDD-HARDENING-A/FR-STUB-001: Minimal typed model providing type-safe
    children and bidirectional navigation.
    Per TDD-HARDENING-C: Uses descriptor-based navigation.
    Per TDD-lifecycle-engine: Minimum viable modeling for lifecycle support.
    Adds 4 custom fields from production usage (dna_priority, intercom_link,
    tier_reached, automation).

    DNA represents domain-specific content within the DNA holder. This stub
    provides proper typing and navigation with minimal custom field accessors.

    Navigation:
        - dna_holder: Navigate to parent DNAHolder
        - business: Navigate to root Business

    Example:
        business = await Business.from_gid_async(client, gid)
        for dna in business.dna_holder.children:
            print(f"DNA: {dna.name}")
            assert dna.business is business
    """

    _dna_holder: DNAHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    business = ParentRef["Business"](holder_attr="_dna_holder")
    dna_holder = HolderRef["DNAHolder"]()

    # Custom field descriptors (minimum viable for lifecycle)
    # Per TDD-lifecycle-engine: 4 descriptors for lifecycle automation
    dna_priority = EnumField(field_name="DNA Priority")
    intercom_link = TextField(field_name="Intercom Link")
    tier_reached = EnumField(field_name="Tier Reached")
    automation = EnumField()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)


__all__ = ["DNA"]
