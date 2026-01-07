"""Business entity seeding factory.

Per ADR-0099: Find-or-create pattern for complete hierarchy creation.
Per TDD-PROCESS-PIPELINE Phase 3.
Per TDD-entity-creation: Business deduplication via SearchService.
"""

from __future__ import annotations

from autom8y_log import get_logger
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel

from autom8_asana.models.business.process import ProcessType

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.contact import Contact
    from autom8_asana.models.business.matching import Candidate, MatchingConfig
    from autom8_asana.models.business.process import Process
    from autom8_asana.models.business.unit import Unit
    from autom8_asana.search.models import SearchHit

__all__ = [
    "BusinessSeeder",
    "SeederResult",
    "BusinessData",
    "ContactData",
    "ProcessData",
]

logger = get_logger(__name__)


def _temp_gid(prefix: str = "seed") -> str:
    """Generate a temporary GID for new entities.

    Per FR-SEED-003: Temp GIDs are replaced with real GIDs after commit.
    """
    return f"temp_{prefix}_{uuid.uuid4().hex[:8]}"


class BusinessData(BaseModel):
    """Input data for Business entity creation.

    Per FR-SEED-001, FR-SEED-002.
    Enhanced with additional matching fields for v2.
    All new fields are optional for backward compatibility.
    """

    name: str
    company_id: str | None = None
    business_address_line_1: str | None = None
    business_city: str | None = None
    business_state: str | None = None
    business_zip: str | None = None
    vertical: str | None = None

    # New fields for v2 composite matching (optional)
    email: str | None = None  # Business email
    phone: str | None = None  # Business phone
    domain: str | None = None  # Website domain


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
    Enhanced with composite matching for v2.

    Example:
        seeder = BusinessSeeder(client)
        result = await seeder.seed_async(
            business=BusinessData(name="Acme Corp", company_id="ACME-001"),
            process=ProcessData(
                name="Demo Call - Acme",
                process_type=ProcessType.SALES,
            ),
            contact=ContactData(full_name="John Doe", contact_email="john@acme.com"),
        )
        # result.business, result.unit, result.process, result.contact

        # With composite matching fields
        result = await seeder.seed_async(
            business=BusinessData(
                name="Acme Corp",
                email="info@acme.com",
                phone="555-123-4567",
                domain="acme.com",
            ),
            process=ProcessData(name="Demo", process_type=ProcessType.SALES),
        )
    """

    def __init__(
        self,
        client: "AsanaClient",
        *,
        matching_config: "MatchingConfig | None" = None,
    ) -> None:
        """Initialize seeder with Asana client.

        Args:
            client: AsanaClient instance for API operations.
            matching_config: Optional matching configuration.
                If None, loads from environment via MatchingConfig.from_env().
        """
        from autom8_asana.models.business.matching import MatchingConfig, MatchingEngine

        self._client = client
        self._matching_config = matching_config or MatchingConfig.from_env()
        self._matching_engine = MatchingEngine(self._matching_config)

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
        """Find existing Business by company_id, name, or composite matching.

        Per TDD-entity-creation: Multi-tier matching strategy.
        Per TDD-BusinessSeeder-v2: Enhanced with composite matching.
        Per ADR-ENTITY-001: Uses SearchService for efficient lookup.

        Search order:
        1. Exact match on company_id (if provided) - Tier 1
        2. Composite matching using MatchingEngine - Tier 2

        Args:
            data: Business data to match against.

        Returns:
            Matched Business or None if no match found.

        Example:
            business = await self._find_business_async(
                BusinessData(name="Joe's Pizza", company_id="ACME-001")
            )
        """
        # Tier 1: company_id exact match (primary key lookup)
        if data.company_id:
            hit = await self._search_by_company_id(data.company_id)
            if hit:
                logger.info(
                    "Business match found by company_id",
                    extra={
                        "match_type": "exact_company_id",
                        "query_name": data.name,
                        "query_company_id": data.company_id,
                        "matched_gid": hit.gid,
                    },
                )
                return await self._load_business(hit.gid)

        # Tier 2: Composite matching via MatchingEngine
        try:
            match_result = await self._find_by_composite_match(data)
            if match_result:
                return match_result
        except Exception as e:
            # Graceful degradation - log and continue to create new
            logger.warning(
                "Composite matching failed, will create new business",
                extra={
                    "query_name": data.name,
                    "error": str(e),
                },
            )

        # No match found
        logger.debug(
            "No Business match found",
            extra={
                "match_type": "none",
                "query_name": data.name,
                "query_company_id": data.company_id,
            },
        )
        return None

    async def _find_by_composite_match(
        self, data: BusinessData
    ) -> "Business | None":
        """Find business using composite matching.

        Per TDD-BusinessSeeder-v2: Uses MatchingEngine for probabilistic matching.

        Args:
            data: Business data to match against.

        Returns:
            Matched Business or None if no match above threshold.
        """
        from autom8_asana.models.business.matching import (
            CompositeBlockingRule,
        )

        # Get candidates from search
        candidates = await self._get_match_candidates(data)
        if not candidates:
            return None

        # Apply blocking rules to filter candidates
        blocking_rule = CompositeBlockingRule()
        filtered_candidates = blocking_rule.filter_candidates(data, candidates)

        if not filtered_candidates:
            logger.debug(
                "No candidates passed blocking rules",
                extra={"query_name": data.name, "total_candidates": len(candidates)},
            )
            return None

        # Find best match using MatchingEngine
        match_result = self._matching_engine.find_best_match(data, filtered_candidates)

        if match_result and match_result.is_match:
            logger.info(
                "Business match found by composite matching",
                extra=match_result.to_log_dict(),
            )
            return await self._load_business(match_result.candidate_gid)

        return None

    async def _get_match_candidates(self, data: BusinessData) -> list["Candidate"]:
        """Get candidate businesses for matching.

        Retrieves potential matches from SearchService and converts to Candidates.

        Args:
            data: Business data to match against.

        Returns:
            List of Candidate objects for comparison.
        """
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.matching import Candidate

        candidates: list[Candidate] = []

        try:
            # Search for businesses with similar name tokens
            # Use name search as the primary candidate source
            result = await self._client.search.find_async(
                Business.PRIMARY_PROJECT_GID,
                {"name": data.name},  # Fuzzy matching handled by engine
                entity_type="Business",
                limit=50,  # Reasonable limit for candidates
            )

            for hit in result.hits:
                candidate = Candidate(
                    gid=hit.gid,
                    name=hit.name,
                    email=hit.matched_fields.get("email"),
                    phone=hit.matched_fields.get("phone"),
                    domain=hit.matched_fields.get("domain"),
                    city=hit.matched_fields.get("business_city"),
                    state=hit.matched_fields.get("business_state"),
                    zip_code=hit.matched_fields.get("business_zip"),
                    company_id=hit.matched_fields.get("company_id"),
                )
                candidates.append(candidate)

        except Exception as e:
            logger.warning(
                "Failed to get match candidates",
                extra={"query_name": data.name, "error": str(e)},
            )

        return candidates

    async def _search_by_company_id(self, company_id: str) -> "SearchHit | None":
        """Search for Business by company_id.

        Per TDD-entity-creation: Tier 1 exact match on company_id field.

        Args:
            company_id: Company ID to search for.

        Returns:
            SearchHit if found, None otherwise.
        """
        from autom8_asana.models.business.business import Business

        try:
            # Use SearchService to find by Company ID custom field
            # Note: Business.PRIMARY_PROJECT_GID is the Business project
            hit = await self._client.search.find_one_async(
                Business.PRIMARY_PROJECT_GID,
                {"Company ID": company_id},
                entity_type="Business",
            )
            return hit
        except ValueError:
            # Multiple matches found - log warning and return first
            logger.warning(
                "Multiple businesses found with same company_id",
                extra={"company_id": company_id},
            )
            result = await self._client.search.find_async(
                Business.PRIMARY_PROJECT_GID,
                {"Company ID": company_id},
                entity_type="Business",
                limit=1,
            )
            return result.hits[0] if result.hits else None
        except Exception as e:
            # Graceful degradation - log and return None
            logger.warning(
                "Search by company_id failed",
                extra={"company_id": company_id, "error": str(e)},
            )
            return None

    async def _search_by_name(self, name: str) -> "SearchHit | None":
        """Search for Business by exact name match.

        Per TDD-entity-creation: Tier 2 exact match on name field.

        Args:
            name: Business name to search for.

        Returns:
            SearchHit if found, None otherwise.
        """
        from autom8_asana.models.business.business import Business

        try:
            # Use SearchService to find by name field
            hit = await self._client.search.find_one_async(
                Business.PRIMARY_PROJECT_GID,
                {"name": name},
                entity_type="Business",
            )
            return hit
        except ValueError:
            # Multiple matches found - log warning and return first
            logger.warning(
                "Multiple businesses found with same name",
                extra={"business_name": name},
            )
            result = await self._client.search.find_async(
                Business.PRIMARY_PROJECT_GID,
                {"name": name},
                entity_type="Business",
                limit=1,
            )
            return result.hits[0] if result.hits else None
        except Exception as e:
            # Graceful degradation - log and return None
            logger.warning(
                "Search by name failed",
                extra={"business_name": name, "error": str(e)},
            )
            return None

    async def _load_business(self, gid: str) -> "Business":
        """Load Business entity by GID.

        Per TDD-entity-creation: Loads full Business for matched GID.

        Args:
            gid: Business task GID.

        Returns:
            Fully loaded Business entity.
        """
        from autom8_asana.models.business.business import Business

        # Load without hydration for seeding purposes
        # (we just need the entity, not the full hierarchy)
        return await Business.from_gid_async(self._client, gid, hydrate=False)
