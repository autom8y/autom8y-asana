"""Core type definitions shared across the codebase.

EntityType was extracted from ``models.business.detection.types`` to break the
core <-> models bidirectional package dependency. Models re-exports it for
backward compatibility.
"""

from __future__ import annotations

from enum import Enum


class EntityType(Enum):
    """Types of entities in the business model hierarchy.

    Per TDD-DETECTION: Complete enumeration of all business model entity types.

    This enum covers:
    - Root entity: BUSINESS
    - Holder types: *_HOLDER variants for container tasks
    - Leaf entities: CONTACT, OFFER, PROCESS, LOCATION, HOURS
    - Composite: UNIT (has nested holders)
    - Fallback: UNKNOWN for unrecognized entities
    """

    # Root entity
    BUSINESS = "business"

    # Leaf entities (asset_edit)
    ASSET_EDIT = "asset_edit"

    # Business-level holders
    CONTACT_HOLDER = "contact_holder"
    UNIT_HOLDER = "unit_holder"
    LOCATION_HOLDER = "location_holder"
    DNA_HOLDER = "dna_holder"
    RECONCILIATIONS_HOLDER = "reconciliations_holder"
    ASSET_EDIT_HOLDER = "asset_edit_holder"
    VIDEOGRAPHY_HOLDER = "videography_holder"

    # Unit-level holders
    OFFER_HOLDER = "offer_holder"
    PROCESS_HOLDER = "process_holder"

    # Composite entity (has nested holders)
    UNIT = "unit"

    # Leaf entities
    CONTACT = "contact"
    OFFER = "offer"
    PROCESS = "process"
    LOCATION = "location"
    HOURS = "hours"

    # Fallback
    UNKNOWN = "unknown"
