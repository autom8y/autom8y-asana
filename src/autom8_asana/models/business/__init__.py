"""Business Model Layer - Domain entities for the autom8_asana SDK.

Per TDD-BIZMODEL: Provides typed Business, Contact, Unit, Offer, Process and
supporting classes for navigating the Asana task hierarchy with strong typing.
Per TDD-HARDENING-C: Migrated to descriptor-based navigation and ClassVar configuration.

Phase 1 + 2 + 3 + Hardening Exports:
    - Business: Root entity with 7 holder properties and 19 typed fields
    - Contact: Contact entity with owner detection and 19 typed fields
    - ContactHolder: Holder task containing Contact children
    - Unit: Unit entity with nested holders and 31 typed fields
    - UnitHolder: Holder task containing Unit children
    - Offer: Offer entity with ad status and 39 typed fields
    - OfferHolder: Holder task containing Offer children
    - Process: Process base entity (forward-compatible for Phase 2 subclasses)
    - ProcessHolder: Holder task containing Process children
    - ProcessType: Enum for process type determination
    - Location: Location entity with address fields
    - LocationHolder: Holder task containing Location children
    - Hours: Operating hours entity
    - DNAHolder: Stub holder for DNA children
    - ReconciliationHolder: Stub holder for Reconciliation children (renamed)
    - ReconciliationsHolder: DEPRECATED alias for ReconciliationHolder
    - AssetEditHolder: Stub holder for Asset Edit children
    - VideographyHolder: Stub holder for Videography children
    - BusinessEntity: Base class for business entities
    - HolderMixin: Mixin for holder tasks with typed children
    - CascadingFieldDef: Definition for fields that cascade to descendants
    - InheritedFieldDef: Definition for fields inherited from parents

Example:
    from autom8_asana.models.business import Business, Unit, Offer, Location

    async with client.save_session() as session:
        session.track(business, recursive=True)

        # Navigate hierarchy
        for unit in business.units:
            print(f"{unit.vertical}: ${unit.mrr} MRR")
            for offer in unit.offers:
                if offer.has_active_ads:
                    print(f"  Active: {offer.name}")

        # Access location and hours
        if business.address:
            print(f"Address: {business.address.full_address}")
        if business.hours:
            print(f"Monday: {business.hours.monday_hours}")

        # Access typed fields
        business.company_id = "ACME-001"
        await session.commit_async()
"""

from autom8_asana.models.business.asset_edit import AssetEdit
from autom8_asana.models.business.base import BusinessEntity, HolderMixin
from autom8_asana.models.business.business import (
    AssetEditHolder,
    Business,
    DNAHolder,
    ReconciliationHolder,
    ReconciliationsHolder,  # DEPRECATED: Use ReconciliationHolder
    VideographyHolder,
)

# TDD-HARDENING-A/FR-STUB-009: Export new stub models
from autom8_asana.models.business.dna import DNA
from autom8_asana.models.business.reconciliation import Reconciliation
from autom8_asana.models.business.videography import Videography
from autom8_asana.models.business.resolution import (
    ResolutionResult,
    ResolutionStrategy,
    resolve_offers,
    resolve_offers_async,
    resolve_units,
    resolve_units_async,
)
from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.business.detection import (
    HOLDER_NAME_MAP,
    EntityType,
    detect_by_name,
    detect_entity_type_async,
)
from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    WorkspaceProjectRegistry,
    get_registry,
    get_workspace_registry,
)
from autom8_asana.models.business.hydration import (
    HydrationBranch,
    HydrationFailure,
    HydrationResult,
    hydrate_from_gid_async,
    # Private functions still available via module, not exported in __all__
    # _convert_to_typed_entity, _is_recoverable, _traverse_upward_async
)
from autom8_asana.models.business.fields import CascadingFieldDef, InheritedFieldDef
from autom8_asana.models.business.mixins import (
    FinancialFieldsMixin,
    SharedCascadingFieldsMixin,
)
from autom8_asana.models.business.hours import Hours
from autom8_asana.models.business.location import Location, LocationHolder
from autom8_asana.models.business.offer import Offer, OfferHolder
from autom8_asana.models.business.process import (
    Process,
    ProcessHolder,
    ProcessSection,
    ProcessType,
)
from autom8_asana.models.business.seeder import (
    BusinessData,
    BusinessSeeder,
    ContactData,
    ProcessData,
    SeederResult,
)
from autom8_asana.models.business.unit import Unit, UnitHolder

__all__ = [
    # Models
    "Business",
    "Contact",
    "ContactHolder",
    "Unit",
    "UnitHolder",
    "Offer",
    "OfferHolder",
    "Process",
    "ProcessHolder",
    "ProcessSection",
    "ProcessType",
    # Business Seeder (TDD-PROCESS-PIPELINE Phase 3)
    "BusinessSeeder",
    "SeederResult",
    "BusinessData",
    "ContactData",
    "ProcessData",
    # AssetEdit (Phase 4 - Resolution)
    "AssetEdit",
    # Phase 3 Models
    "Location",
    "LocationHolder",
    "Hours",
    # Stub Holders
    "DNAHolder",
    "ReconciliationHolder",
    "ReconciliationsHolder",  # DEPRECATED: Use ReconciliationHolder
    "AssetEditHolder",
    "VideographyHolder",
    # TDD-HARDENING-A/FR-STUB-009: Stub Models
    "DNA",
    "Reconciliation",
    "Videography",
    # Base classes
    "BusinessEntity",
    "HolderMixin",
    # Field definitions
    "CascadingFieldDef",
    "InheritedFieldDef",
    # Field mixins (TDD-SPRINT-1)
    "SharedCascadingFieldsMixin",
    "FinancialFieldsMixin",
    # Detection (Phase 2 - Hydration)
    "EntityType",
    "HOLDER_NAME_MAP",
    "detect_by_name",
    "detect_entity_type_async",
    # Registry (TDD-DETECTION Phase 1, TDD-WORKSPACE-PROJECT-REGISTRY Phase 1)
    "ProjectTypeRegistry",
    "WorkspaceProjectRegistry",
    "get_registry",
    "get_workspace_registry",
    # Hydration (Phase 3 - Result Dataclasses)
    # Per TDD-HARDENING-A/FR-ALL-*: Private functions removed from __all__
    "HydrationResult",
    "HydrationBranch",
    "HydrationFailure",
    "hydrate_from_gid_async",
    # Resolution (Phase 4)
    "ResolutionStrategy",
    "ResolutionResult",
    # Batch Resolution (Phase 5 - ADR-0073)
    "resolve_units_async",
    "resolve_offers_async",
    "resolve_units",
    "resolve_offers",
]
