"""Business entity seeding factory.

Per ADR-0099: Find-or-create pattern for complete hierarchy creation.
Per TDD-PROCESS-PIPELINE Phase 3.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel

from autom8_asana.models.business.process import ProcessType

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.contact import Contact
    from autom8_asana.models.business.process import Process
    from autom8_asana.models.business.unit import Unit

__all__ = [
    "BusinessSeeder",
    "SeederResult",
    "BusinessData",
    "ContactData",
    "ProcessData",
]

logger = logging.getLogger(__name__)


def _temp_gid(prefix: str = "seed") -> str:
    """Generate a temporary GID for new entities.

    Per FR-SEED-003: Temp GIDs are replaced with real GIDs after commit.
    """
    return f"temp_{prefix}_{uuid.uuid4().hex[:8]}"


class BusinessData(BaseModel):
    """Input data for Business entity creation.

    Per FR-SEED-001, FR-SEED-002.
    """

    name: str
    company_id: str | None = None
    business_address_line_1: str | None = None
    business_city: str | None = None
    business_state: str | None = None
    business_zip: str | None = None
    vertical: str | None = None


class ContactData(BaseModel):
    """Input data for Contact entity creation.

    Per FR-SEED-010.
    """

    full_name: str
    contact_email: str | None = None
    contact_phone: str | None = None


class ProcessData(BaseModel):
    """Input data for Process entity creation.

    Per FR-SEED-005, FR-SEED-006.
    Per ADR-0101: initial_state removed (process inherits section from hierarchy).
    """

    name: str
    process_type: ProcessType
    assigned_to: str | None = None  # User GID
    due_date: str | None = None  # ISO format date
    notes: str | None = None


@dataclass
class SeederResult:
    """Result of BusinessSeeder.seed_async().

    Per FR-SEED-007.
    Per ADR-0101: added_to_pipeline removed (canonical project IS the pipeline).
    """

    business: "Business"
    unit: "Unit"
    process: "Process"
    contact: "Contact | None" = None
    created_business: bool = False
    created_unit: bool = False
    created_contact: bool = False
    warnings: list[str] = field(default_factory=list)


class BusinessSeeder:
    """Factory for creating complete business entity hierarchies.

    Per ADR-0099: Find-or-create pattern with SaveSession integration.
    Per FR-SEED-001 through FR-SEED-011.

    Example:
        seeder = BusinessSeeder(client)
        result = await seeder.seed_async(
            business=BusinessData(name="Acme Corp", company_id="ACME-001"),
            process=ProcessData(
                name="Demo Call - Acme",
                process_type=ProcessType.SALES,
                initial_state=ProcessSection.SCHEDULED,
            ),
            contact=ContactData(full_name="John Doe", contact_email="john@acme.com"),
        )
        # result.business, result.unit, result.process, result.contact
    """

    def __init__(self, client: "AsanaClient") -> None:
        """Initialize seeder with Asana client.

        Args:
            client: AsanaClient instance for API operations
        """
        self._client = client

    async def seed_async(
        self,
        business: BusinessData,
        process: ProcessData,
        *,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """Seed complete business hierarchy with process.

        Creates or finds:
        1. Business entity (by company_id or name)
        2. Unit entity under Business
        3. Process entity under Unit's ProcessHolder
        4. Optionally creates Contact under Business

        Per FR-SEED-001 through FR-SEED-011.
        Per ADR-0101: Process inherits project membership through hierarchy.

        Args:
            business: Business entity data
            process: Process entity data
            contact: Optional contact data
            unit_name: Optional unit name (defaults to business name)

        Returns:
            SeederResult with all created/found entities

        Note:
            Find-by-company_id and find-by-name are stubbed for MVP.
            Always creates new entities. Enhancement path: implement
            actual search in future phase.
        """
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.contact import Contact
        from autom8_asana.models.business.process import Process
        from autom8_asana.models.business.unit import Unit

        warnings: list[str] = []
        created_business = False
        created_unit = False
        created_contact = False

        # Phase 1: Find or create Business
        # NOTE: MVP stubs find methods - always creates new
        existing_business = await self._find_business_async(business)

        if existing_business is not None:
            biz = existing_business
            logger.info(
                "Found existing Business", extra={"gid": biz.gid, "name": biz.name}
            )
        else:
            # Create new Business with temp GID
            biz = Business(gid=_temp_gid("biz"), name=business.name)
            if business.company_id:
                biz.company_id = business.company_id
            if business.vertical:
                biz.vertical = business.vertical
            if business.business_address_line_1:
                biz.business_address_line_1 = business.business_address_line_1
            if business.business_city:
                biz.business_city = business.business_city
            if business.business_state:
                biz.business_state = business.business_state
            if business.business_zip:
                biz.business_zip = business.business_zip
            created_business = True
            logger.info("Creating new Business", extra={"name": business.name})

        # Phase 2: Find or create Unit
        unit_display_name = unit_name or business.name

        # Check if Business has existing units
        existing_unit: Unit | None = None
        if not created_business and hasattr(biz, "units") and biz.units:
            # Try to find unit by name
            for u in biz.units:
                if u.name and unit_display_name in u.name:
                    existing_unit = u
                    break

        if existing_unit is not None:
            unit = existing_unit
            logger.info(
                "Found existing Unit", extra={"gid": unit.gid, "name": unit.name}
            )
        else:
            unit = Unit(gid=_temp_gid("unit"), name=f"{unit_display_name} - Unit")
            created_unit = True
            logger.info("Creating new Unit", extra={"name": unit.name})

        # Phase 3: Create Process with temp GID
        proc = Process(gid=_temp_gid("proc"), name=process.name)
        if process.assigned_to:
            # Assignee expects NameGid format
            from autom8_asana.models.common import NameGid

            proc.assignee = NameGid(gid=process.assigned_to)
        if process.due_date:
            proc.due_on = process.due_date
        if process.notes:
            proc.notes = process.notes
        logger.info(
            "Creating new Process",
            extra={"name": process.name, "type": process.process_type.value},
        )

        # Phase 4: Create Contact if provided
        contact_entity: Contact | None = None
        if contact is not None:
            contact_entity = Contact(gid=_temp_gid("contact"), name=contact.full_name)
            if contact.contact_email:
                contact_entity.contact_email = contact.contact_email
            if contact.contact_phone:
                contact_entity.contact_phone = contact.contact_phone
            created_contact = True
            logger.info("Creating new Contact", extra={"name": contact.full_name})

        # Phase 5: Commit via SaveSession
        async with self._client.save_session() as session:
            # Track Business (creates if new)
            session.track(biz)

            # Set up Unit under Business
            if created_unit:
                # Unit needs to be under Business's UnitHolder
                # For MVP, we create as subtask relationship via parent NameGid
                from autom8_asana.models.common import NameGid

                unit.parent = NameGid(gid=biz.gid)
                session.track(unit)

            # Set up Process under Unit
            from autom8_asana.models.common import NameGid

            proc.parent = NameGid(gid=unit.gid)
            session.track(proc)

            # Set up Contact under Business
            if contact_entity is not None:
                contact_entity.parent = NameGid(gid=biz.gid)
                session.track(contact_entity)

            # Per ADR-0101: Process inherits project membership from hierarchy
            # No separate pipeline project addition needed

            # Commit all changes
            await session.commit_async()

        return SeederResult(
            business=biz,
            unit=unit,
            process=proc,
            contact=contact_entity,
            created_business=created_business,
            created_unit=created_unit,
            created_contact=created_contact,
            warnings=warnings,
        )

    def seed(
        self,
        business: BusinessData,
        process: ProcessData,
        *,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """Synchronous wrapper for seed_async().

        Per FR-SEED-009.
        """
        from autom8_asana.transport.sync import sync_wrapper

        @sync_wrapper("seed_async")
        async def _seed_sync() -> SeederResult:
            return await self.seed_async(
                business=business,
                process=process,
                contact=contact,
                unit_name=unit_name,
            )

        return _seed_sync()

    async def _find_business_async(self, data: BusinessData) -> "Business | None":
        """Find existing Business by company_id or name.

        NOTE: MVP stub - always returns None (creates new).
        Enhancement path: Implement actual Asana search API call.

        Per FR-SEED-002.
        """
        # TODO: Phase 2 enhancement - implement actual search
        # 1. Search by company_id custom field if provided
        # 2. Fall back to name search
        # 3. Return matched Business or None
        return None
