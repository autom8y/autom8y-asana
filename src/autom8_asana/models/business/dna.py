"""DNA entity - minimal typed model for DNAHolder children.

Per TDD-HARDENING-A/FR-STUB-001: Minimal typed model providing type-safe
children and bidirectional navigation.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation pattern.
Per ADR-0075: Navigation descriptors for property consolidation.
Per ADR-0076: Auto-invalidation on parent reference change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity
from autom8_asana.models.business.descriptors import HolderRef, ParentRef

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business, DNAHolder


class DNA(BusinessEntity):
    """DNA entity - child of DNAHolder.

    Per TDD-HARDENING-A/FR-STUB-001: Minimal typed model providing type-safe
    children and bidirectional navigation.
    Per TDD-HARDENING-C: Uses descriptor-based navigation.

    DNA represents domain-specific content within the DNA holder. This stub
    provides proper typing and navigation without custom field accessors
    (per FR-STUB-010).

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

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)


__all__ = ["DNA"]
