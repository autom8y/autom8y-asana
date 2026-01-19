"""Explicit model registration for ProjectRegistry.

Per TDD-registry-consolidation: Replaces __init_subclass__ auto-registration
with deterministic bootstrap that runs at module import time.

This module is imported by models/business/__init__.py to ensure
registration happens before any detection calls.

IMPORTANT: This is the ONLY place where entity types should be registered.
Do NOT add registration logic to __init_subclass__ or other hooks.
"""

from __future__ import annotations

from autom8y_log import get_logger

logger = get_logger(__name__)

_BOOTSTRAP_COMPLETE = False


def register_all_models() -> None:
    """Register all entity types from model PRIMARY_PROJECT_GID attributes.

    Per TDD-registry-consolidation Phase 1: Model-first registration.

    This function:
    1. Imports all entity model classes
    2. Reads PRIMARY_PROJECT_GID from each class
    3. Registers non-None GIDs with ProjectRegistry
    4. Logs registration summary

    Called once at module import time from models/business/__init__.py.
    Idempotent: subsequent calls are no-ops.
    """
    global _BOOTSTRAP_COMPLETE

    if _BOOTSTRAP_COMPLETE:
        logger.debug("register_all_models already complete, skipping")
        return

    # Import registry and detection types INSIDE the function
    # to avoid circular imports at module load time
    from autom8_asana.models.business.detection.types import EntityType
    from autom8_asana.models.business.registry import get_registry

    # Import all entity model classes INSIDE the function
    # to avoid circular imports at module load time
    from autom8_asana.models.business.business import (
        AssetEditHolder,
        Business,
        DNAHolder,
        ReconciliationHolder,
        VideographyHolder,
    )
    from autom8_asana.models.business.contact import Contact, ContactHolder
    from autom8_asana.models.business.unit import Unit, UnitHolder
    from autom8_asana.models.business.offer import Offer, OfferHolder
    from autom8_asana.models.business.location import Location, LocationHolder
    from autom8_asana.models.business.hours import Hours
    from autom8_asana.models.business.process import Process, ProcessHolder

    # Entity type -> Model class mapping
    # Order matters: more specific types first (holders before parents)
    # Tuple format: (EntityType, model_class)
    ENTITY_MODELS: list[tuple[EntityType, type]] = [
        # Root entities
        (EntityType.BUSINESS, Business),
        (EntityType.UNIT, Unit),
        (EntityType.CONTACT, Contact),
        (EntityType.OFFER, Offer),
        (EntityType.LOCATION, Location),
        (EntityType.HOURS, Hours),
        (EntityType.PROCESS, Process),
        # Asset Edit (extends Process, has own project)
        # Note: AssetEdit doesn't have a dedicated EntityType, it's detected via project
        # Holders - Business level
        (EntityType.CONTACT_HOLDER, ContactHolder),
        (EntityType.UNIT_HOLDER, UnitHolder),
        (EntityType.LOCATION_HOLDER, LocationHolder),
        (EntityType.DNA_HOLDER, DNAHolder),
        (EntityType.RECONCILIATIONS_HOLDER, ReconciliationHolder),
        (EntityType.ASSET_EDIT_HOLDER, AssetEditHolder),
        (EntityType.VIDEOGRAPHY_HOLDER, VideographyHolder),
        # Holders - Unit level
        (EntityType.OFFER_HOLDER, OfferHolder),
        (EntityType.PROCESS_HOLDER, ProcessHolder),
    ]

    registry = get_registry()
    registered_count = 0
    skipped_count = 0

    for entity_type, model_class in ENTITY_MODELS:
        gid = getattr(model_class, "PRIMARY_PROJECT_GID", None)

        if gid is None:
            logger.debug(
                "model_no_primary_gid",
                extra={
                    "entity_type": entity_type.name,
                    "model_class": model_class.__name__,
                },
            )
            skipped_count += 1
            continue

        try:
            registry.register(gid, entity_type)
            registered_count += 1
        except ValueError as e:
            # Duplicate GID - log warning but continue
            logger.warning(
                "model_registration_conflict",
                extra={
                    "entity_type": entity_type.name,
                    "model_class": model_class.__name__,
                    "project_gid": gid,
                    "error": str(e),
                },
            )

    _BOOTSTRAP_COMPLETE = True

    logger.info(
        "model_registration_complete",
        extra={
            "registered_count": registered_count,
            "skipped_count": skipped_count,
            "total_models": len(ENTITY_MODELS),
        },
    )


def is_bootstrap_complete() -> bool:
    """Check if model bootstrap has been run.

    Returns:
        True if register_all_models() has completed, False otherwise.
    """
    return _BOOTSTRAP_COMPLETE


def reset_bootstrap() -> None:
    """Reset bootstrap state for testing.

    This allows tests to re-run registration after resetting the registry.
    """
    global _BOOTSTRAP_COMPLETE
    _BOOTSTRAP_COMPLETE = False
    logger.debug("bootstrap_reset")
