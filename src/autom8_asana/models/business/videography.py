"""Videography entity - minimal typed model for VideographyHolder children.

Per TDD-HARDENING-A/FR-STUB-003: Minimal typed model providing type-safe
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
    from autom8_asana.models.business.business import Business, VideographyHolder


class Videography(BusinessEntity):
    """Videography entity - child of VideographyHolder.

    Per TDD-HARDENING-A/FR-STUB-003: Minimal typed model providing type-safe
    children and bidirectional navigation.
    Per TDD-HARDENING-C: Uses descriptor-based navigation.

    Videography represents video production records. This stub provides
    proper typing and navigation without custom field accessors
    (per FR-STUB-010).

    Navigation:
        - videography_holder: Navigate to parent VideographyHolder
        - business: Navigate to root Business

    Example:
        business = await Business.from_gid_async(client, gid)
        for video in business.videography_holder.children:
            print(f"Videography: {video.name}")
            assert video.business is business
    """

    _videography_holder: VideographyHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    # Navigation descriptors (TDD-HARDENING-C, ADR-0075)
    # IMPORTANT: Declared WITHOUT type annotations to avoid Pydantic field creation
    business = ParentRef["Business"](holder_attr="_videography_holder")
    videography_holder = HolderRef["VideographyHolder"]()

    # _invalidate_refs() inherited from BusinessEntity (ADR-0076)


__all__ = ["Videography"]
