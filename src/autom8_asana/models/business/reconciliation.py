"""Reconciliation entity - minimal typed model for ReconciliationsHolder children.

Per TDD-HARDENING-A/FR-STUB-002: Minimal typed model providing type-safe
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
    from autom8_asana.models.business.business import Business, ReconciliationHolder


class Reconciliation(BusinessEntity):
    """Reconciliation entity - child of ReconciliationHolder.

    Per TDD-HARDENING-A/FR-STUB-002: Minimal typed model providing type-safe
    children and bidirectional navigation.
    Per TDD-HARDENING-C: Uses descriptor-based navigation.

    Reconciliations represent financial reconciliation records. This stub
    provides proper typing and navigation without custom field accessors
    (per FR-STUB-010).

    Navigation:
        - reconciliation_holder: Navigate to parent ReconciliationHolder
        - business: Navigate to root Business

    Example:
        business = await Business.from_gid_async(client, gid)
        for recon in business.reconciliation_holder.children:
            print(f"Reconciliation: {recon.name}")
            assert recon.business is business
    """

    _reconciliation_holder: ReconciliationHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    business = ParentRef["Business"](holder_attr="_reconciliation_holder")
    reconciliation_holder = HolderRef["ReconciliationHolder"]()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)


__all__ = ["Reconciliation"]
