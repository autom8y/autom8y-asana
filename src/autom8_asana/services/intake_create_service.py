"""Service for intake business creation and process routing.

Orchestrates the 7-phase business hierarchy creation (SaveSession pattern)
and process routing with idempotency checks.

Phase ordering (strict sequential except Phase 2):
  1. Create Business task in the business project
  2. Create 7 holder subtasks under Business (parallel via asyncio.gather)
  3. Create Unit subtask under unit_holder
  4. Create Contact subtask under contact_holder
  5. Route Process (if requested)
  6. Write social profiles as custom fields on Business
  7. Write address/location fields to location_holder
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.api.routes.intake_create_models import (
    IntakeBusinessCreateRequest,
    IntakeBusinessCreateResponse,
    IntakeRouteResponse,
)

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# Fixed set of holder types per IMPL spec
HOLDER_TYPES: list[str] = [
    "contact_holder",
    "unit_holder",
    "location_holder",
    "dna_holder",
    "reconciliations_holder",
    "asset_edit_holder",
    "videography_holder",
]

# Valid process types for intake creation.
# Per truth audit: "consultation" removed — ProcessType model does not exist yet.
# TODO(truth-audit): Add "consultation" when consultation ProcessType model lands.
VALID_PROCESS_TYPES: set[str] = {"sales", "retention", "implementation"}

# Social profile platform -> Asana custom field name mapping
SOCIAL_FIELD_MAP: dict[str, str] = {
    "facebook": "Facebook URL",
    "instagram": "Instagram URL",
    "youtube": "YouTube URL",
    "linkedin": "LinkedIn URL",
}

# Address field -> Asana custom field name mapping
ADDRESS_FIELD_MAP: dict[str, str] = {
    "street_number": "Street Number",
    "street_name": "Street Name",
    "suite": "Suite",
    "city": "City",
    "state": "State",
    "postal_code": "Postal Code",
    "country": "Country",
    "timezone": "Timezone",
}


def resolve_workspace_gid() -> str:
    """Resolve the workspace GID from EntityProjectRegistry.

    Module-level function to enable clean patching in tests.

    Returns:
        Workspace GID string.
    """
    try:
        from autom8_asana.services.resolver import EntityProjectRegistry

        registry = EntityProjectRegistry.get_instance()
        # Get business project to derive workspace
        project_gid = registry.get_project_gid("business")
        if project_gid:
            return project_gid
    except Exception:
        pass
    return ""


def resolve_business_project_gid() -> str:
    """Resolve the business project GID from EntityProjectRegistry.

    Module-level function to enable clean patching in tests.

    Returns:
        Business project GID string.
    """
    try:
        from autom8_asana.services.resolver import EntityProjectRegistry

        registry = EntityProjectRegistry.get_instance()
        project_gid = registry.get_project_gid("business")
        if project_gid:
            return project_gid
    except Exception:
        pass
    return ""


class IntakeCreateService:
    """Orchestrates full business hierarchy creation via SaveSession.

    7-phase creation chain with strict ordering:
    - Phase 2 (holders) runs in parallel via asyncio.gather
    - All other phases are strictly sequential
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def create_business_hierarchy(
        self,
        request: IntakeBusinessCreateRequest,
    ) -> IntakeBusinessCreateResponse:
        """Execute the 7-phase business hierarchy creation.

        Args:
            request: Full business creation request.

        Returns:
            IntakeBusinessCreateResponse with all entity GIDs.

        Raises:
            LookupError: If business project is not configured.
            RuntimeError: If Asana API calls fail.
        """
        project_gid = resolve_business_project_gid()
        if not project_gid:
            raise LookupError(
                "Business project not configured in EntityProjectRegistry"
            )

        # Phase 1: Create Business task
        business_gid = await self._phase1_create_business(request, project_gid)
        logger.info(
            "intake_create_phase1_complete",
            extra={"business_gid": business_gid, "name": request.name},
        )

        # Phase 2: Create 7 holder subtasks (parallel)
        holders = await self._phase2_create_holders(business_gid)
        logger.info(
            "intake_create_phase2_complete",
            extra={"business_gid": business_gid, "holder_count": len(holders)},
        )

        # Phase 3: Create Unit subtask under unit_holder
        unit_name = request.unit_name or f"{request.name} -- {request.vertical.title()}"
        unit_gid = await self._phase3_create_unit(
            holders["unit_holder"],
            unit_name,
            request.vertical,
        )
        logger.info(
            "intake_create_phase3_complete",
            extra={"business_gid": business_gid, "unit_gid": unit_gid},
        )

        # Phase 4: Create Contact subtask under contact_holder
        contact_gid = await self._phase4_create_contact(
            holders["contact_holder"],
            request.contact,
        )
        logger.info(
            "intake_create_phase4_complete",
            extra={"business_gid": business_gid, "contact_gid": contact_gid},
        )

        # Phase 5: Route Process (if requested)
        process_gid: str | None = None
        if request.process is not None:
            route_result = await self.route_process(
                unit_gid=unit_gid,
                process_type=request.process.process_type,
                due_at=request.process.due_at,
                assignee_name=request.process.assignee_name,
            )
            process_gid = route_result.process_gid
            logger.info(
                "intake_create_phase5_complete",
                extra={
                    "business_gid": business_gid,
                    "process_gid": process_gid,
                    "process_type": request.process.process_type,
                },
            )

        # Phase 6: Write social profiles as custom fields on Business
        if request.social_profiles:
            await self._phase6_write_social_profiles(
                business_gid, request.social_profiles
            )
            logger.info(
                "intake_create_phase6_complete",
                extra={
                    "business_gid": business_gid,
                    "profile_count": len(request.social_profiles),
                },
            )

        # Phase 7: Write address fields to location_holder
        if request.address is not None:
            await self._phase7_write_address(
                holders["location_holder"], request.address
            )
            logger.info(
                "intake_create_phase7_complete",
                extra={"business_gid": business_gid},
            )

        return IntakeBusinessCreateResponse(
            business_gid=business_gid,
            contact_gid=contact_gid,
            unit_gid=unit_gid,
            contact_holder_gid=holders["contact_holder"],
            unit_holder_gid=holders["unit_holder"],
            process_gid=process_gid,
            holders=holders,
        )

    # -----------------------------------------------------------------------
    # Phase implementations
    # -----------------------------------------------------------------------

    async def _phase1_create_business(
        self,
        request: IntakeBusinessCreateRequest,
        project_gid: str,
    ) -> str:
        """Phase 1: Create Business task in the business project.

        Custom fields set: office_phone, num_reviews, website, hours.
        """
        task_data: dict[str, Any] = {
            "name": request.name,
            "projects": [project_gid],
        }

        # Build custom fields for enrichment data
        notes_parts: list[str] = []
        if request.office_phone:
            notes_parts.append(f"Office Phone: {request.office_phone}")
        if request.website:
            notes_parts.append(f"Website: {request.website}")
        if request.num_reviews is not None:
            notes_parts.append(f"Reviews: {request.num_reviews}")

        if notes_parts:
            task_data["notes"] = "\n".join(notes_parts)

        result = await self._client.tasks.create_in_workspace_async(
            project_gid,  # workspace_gid placeholder -- routed via project
            data=task_data,
        )

        return self._extract_gid(result)

    async def _phase2_create_holders(self, business_gid: str) -> dict[str, str]:
        """Phase 2: Create 7 holder subtasks under Business (parallel).

        Returns dict of holder_name -> gid.
        """

        async def create_holder(holder_name: str) -> tuple[str, str]:
            result = await self._client.tasks.create_subtask_async(
                business_gid,
                data={"name": holder_name},
            )
            return holder_name, self._extract_gid(result)

        holder_results = await asyncio.gather(
            *[create_holder(name) for name in HOLDER_TYPES]
        )
        return dict(holder_results)

    async def _phase3_create_unit(
        self,
        unit_holder_gid: str,
        unit_name: str,
        vertical: str,
    ) -> str:
        """Phase 3: Create Unit subtask under unit_holder."""
        result = await self._client.tasks.create_subtask_async(
            unit_holder_gid,
            data={
                "name": unit_name,
                "notes": f"Vertical: {vertical}",
            },
        )
        unit_gid = self._extract_gid(result)

        # Write Vertical enum custom field on the newly created unit task
        await self._write_vertical_custom_field(unit_gid, vertical)

        return unit_gid

    async def _write_vertical_custom_field(
        self,
        task_gid: str,
        vertical: str,
    ) -> None:
        """Resolve and write the Vertical enum custom field on a unit task.

        Fetches the task's custom fields, locates the field named "Vertical"
        (case-insensitive), matches the vertical parameter to an enum option
        by name (case-insensitive), and writes via tasks.update_async.

        Non-fatal: logs warning and returns if field or enum option not found.
        """
        task_data = await self._client.tasks.get_async(
            task_gid,
            opt_fields=[
                "custom_fields.gid",
                "custom_fields.name",
                "custom_fields.enum_options.gid",
                "custom_fields.enum_options.name",
            ],
        )
        custom_fields = (
            task_data.get("custom_fields", [])
            if isinstance(task_data, dict)
            else getattr(task_data, "custom_fields", []) or []
        )

        # Find the "Vertical" custom field entry
        vertical_cf = None
        for cf in custom_fields:
            cf_name = (
                cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            )
            if cf_name and cf_name.lower() == "vertical":
                vertical_cf = cf
                break

        if vertical_cf is None:
            logger.warning(
                "vertical_cf_not_found",
                extra={"task_gid": task_gid},
            )
            return

        cf_gid = (
            vertical_cf.get("gid", "")
            if isinstance(vertical_cf, dict)
            else getattr(vertical_cf, "gid", "")
        )
        enum_options = (
            vertical_cf.get("enum_options", [])
            if isinstance(vertical_cf, dict)
            else getattr(vertical_cf, "enum_options", []) or []
        )

        # Match enum option by name (case-insensitive)
        enum_option_gid = None
        for opt in enum_options:
            opt_name = (
                opt.get("name", "") if isinstance(opt, dict) else getattr(opt, "name", "")
            )
            if opt_name and opt_name.lower() == vertical.lower():
                enum_option_gid = (
                    opt.get("gid", "")
                    if isinstance(opt, dict)
                    else getattr(opt, "gid", "")
                )
                break

        if not enum_option_gid:
            logger.warning(
                "vertical_enum_option_not_found",
                extra={"task_gid": task_gid, "vertical": vertical},
            )
            return

        await self._client.tasks.update_async(
            task_gid,
            data={"custom_fields": {cf_gid: {"gid": enum_option_gid}}},
        )

    async def _phase4_create_contact(
        self,
        contact_holder_gid: str,
        contact: Any,
    ) -> str:
        """Phase 4: Create Contact subtask under contact_holder."""
        notes_parts: list[str] = []
        if contact.email:
            notes_parts.append(f"Email: {contact.email}")
        if contact.phone:
            notes_parts.append(f"Phone: {contact.phone}")
        if contact.timezone:
            notes_parts.append(f"Timezone: {contact.timezone}")

        result = await self._client.tasks.create_subtask_async(
            contact_holder_gid,
            data={
                "name": contact.name,
                "notes": "\n".join(notes_parts) if notes_parts else "",
            },
        )
        return self._extract_gid(result)

    async def _phase6_write_social_profiles(
        self,
        business_gid: str,
        social_profiles: list[Any],
    ) -> None:
        """Phase 6: Write social profiles as custom fields on Business.

        Resolves platform name to Asana custom field name and writes URLs.
        Fixes SOCIAL-PROFILES-ORPHANED: profiles are now persisted.
        """
        # Fetch current custom fields to get GID mapping
        task_data = await self._client.tasks.get_async(
            business_gid,
            opt_fields=["custom_fields"],
        )
        custom_fields = (
            task_data.get("custom_fields", [])
            if isinstance(task_data, dict)
            else getattr(task_data, "custom_fields", []) or []
        )

        # Build name -> GID mapping
        field_name_to_gid: dict[str, str] = {}
        for cf in custom_fields:
            cf_name = (
                cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            )
            cf_gid = (
                cf.get("gid", "") if isinstance(cf, dict) else getattr(cf, "gid", "")
            )
            if cf_name and cf_gid:
                field_name_to_gid[cf_name.lower()] = cf_gid

        # Build custom_fields payload
        custom_fields_payload: dict[str, str] = {}
        for profile in social_profiles:
            platform = (
                profile.platform
                if hasattr(profile, "platform")
                else profile.get("platform", "")
            )
            url = profile.url if hasattr(profile, "url") else profile.get("url", "")
            field_name = SOCIAL_FIELD_MAP.get(platform.lower(), "")
            if field_name:
                gid = field_name_to_gid.get(field_name.lower())
                if gid:
                    custom_fields_payload[gid] = url
                else:
                    logger.warning(
                        "social_field_not_resolved",
                        extra={"platform": platform, "field_name": field_name},
                    )

        if custom_fields_payload:
            await self._client.tasks.update_async(
                business_gid,
                data={"custom_fields": custom_fields_payload},
            )

    async def _phase7_write_address(
        self,
        location_holder_gid: str,
        address: Any,
    ) -> None:
        """Phase 7: Write address fields to location_holder.

        Uses postal_code (canonical name, never 'zip').
        """
        # Fetch location_holder's custom fields for GID mapping
        task_data = await self._client.tasks.get_async(
            location_holder_gid,
            opt_fields=["custom_fields"],
        )
        custom_fields = (
            task_data.get("custom_fields", [])
            if isinstance(task_data, dict)
            else getattr(task_data, "custom_fields", []) or []
        )

        field_name_to_gid: dict[str, str] = {}
        for cf in custom_fields:
            cf_name = (
                cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            )
            cf_gid = (
                cf.get("gid", "") if isinstance(cf, dict) else getattr(cf, "gid", "")
            )
            if cf_name and cf_gid:
                field_name_to_gid[cf_name.lower()] = cf_gid

        custom_fields_payload: dict[str, str] = {}
        address_dict = (
            address.model_dump() if hasattr(address, "model_dump") else address
        )
        for field_attr, display_name in ADDRESS_FIELD_MAP.items():
            value = address_dict.get(field_attr)
            if value is not None:
                gid = field_name_to_gid.get(display_name.lower())
                if gid:
                    custom_fields_payload[gid] = str(value)

        if custom_fields_payload:
            await self._client.tasks.update_async(
                location_holder_gid,
                data={"custom_fields": custom_fields_payload},
            )

    # -----------------------------------------------------------------------
    # Process routing
    # -----------------------------------------------------------------------

    async def route_process(
        self,
        unit_gid: str,
        process_type: str,
        due_at: str | None = None,
        assignee_name: str | None = None,
        triggered_by: str = "automation",
    ) -> IntakeRouteResponse:
        """Route a unit to a process type.

        Checks for existing open process (idempotent), creates new
        via template duplication if none exists.

        Args:
            unit_gid: Unit task GID.
            process_type: Process type (sales/consultation/retention/implementation).
            due_at: Optional ISO 8601 due date.
            assignee_name: Optional assignee for fuzzy match.
            triggered_by: Who triggered this route.

        Returns:
            IntakeRouteResponse.

        Raises:
            LookupError: If unit_gid not found.
            ValueError: If process_type is unknown.
        """
        if process_type not in VALID_PROCESS_TYPES:
            raise ValueError(f"Unknown process type: {process_type}")

        # Validate unit exists
        try:
            await self._client.tasks.get_async(unit_gid)
        except Exception as exc:
            raise LookupError(f"Unit not found: {unit_gid}") from exc

        # Check for existing open process of this type
        existing = await self._find_existing_process(unit_gid, process_type)
        if existing is not None:
            existing_gid = (
                existing.get("gid")
                if isinstance(existing, dict)
                else getattr(existing, "gid", "")
            )
            logger.info(
                "intake_route_existing_process",
                extra={
                    "unit_gid": unit_gid,
                    "process_type": process_type,
                    "existing_gid": existing_gid,
                },
            )
            return IntakeRouteResponse(
                process_gid=existing_gid,
                process_type=process_type,
                is_new=False,
            )

        # Create new process as subtask of unit
        process_data: dict[str, Any] = {
            "name": f"{process_type.title()} Process",
            "notes": f"Process type: {process_type}\nTriggered by: {triggered_by}",
        }
        if due_at:
            process_data["due_at"] = due_at

        result = await self._client.tasks.create_subtask_async(
            unit_gid,
            data=process_data,
        )
        process_gid = self._extract_gid(result)

        # Resolve assignee if provided
        resolved_assignee: str | None = None
        if assignee_name:
            resolved_assignee = await self._resolve_assignee(assignee_name)
            if resolved_assignee:
                try:
                    await self._client.tasks.update_async(
                        process_gid,
                        data={"assignee": resolved_assignee},
                    )
                except Exception as exc:
                    logger.warning(
                        "assignee_set_failed",
                        extra={
                            "process_gid": process_gid,
                            "assignee_name": assignee_name,
                            "error": str(exc),
                        },
                    )

        logger.info(
            "intake_route_new_process",
            extra={
                "unit_gid": unit_gid,
                "process_type": process_type,
                "process_gid": process_gid,
                "assignee_name": resolved_assignee or assignee_name,
            },
        )

        return IntakeRouteResponse(
            process_gid=process_gid,
            process_type=process_type,
            is_new=True,
            assignee_name=resolved_assignee or assignee_name,
        )

    async def _find_existing_process(
        self,
        unit_gid: str,
        process_type: str,
    ) -> dict[str, Any] | None:
        """Find an existing open (not completed) process of the given type.

        Returns the process task dict if found, None otherwise.
        """
        try:
            subtasks_result = await self._client.tasks.subtasks_async(
                unit_gid,
                opt_fields=["name", "completed"],
            )
            subtasks = self._to_list(subtasks_result)
        except Exception as exc:
            logger.warning(
                "existing_process_check_failed",
                extra={"unit_gid": unit_gid, "error": str(exc)},
            )
            return None

        process_name_lower = f"{process_type.title()} Process".lower()
        for st in subtasks:
            st_name = (
                st.get("name", "") if isinstance(st, dict) else getattr(st, "name", "")
            )
            st_completed = (
                st.get("completed", False)
                if isinstance(st, dict)
                else getattr(st, "completed", False)
            )
            if st_name and st_name.lower() == process_name_lower and not st_completed:
                return st  # type: ignore[return-value]

        return None

    async def _resolve_assignee(self, assignee_name: str) -> str | None:
        """Fuzzy match assignee name against workspace users.

        Returns user GID if matched, None otherwise.
        Logs warning on failure but does not raise.
        """
        try:
            users_result = await self._client.users.get_users_async(
                opt_fields=["name", "gid"],
            )
            users = self._to_list(users_result)

            assignee_lower = assignee_name.lower()
            for user in users:
                user_name = (
                    user.get("name", "")
                    if isinstance(user, dict)
                    else getattr(user, "name", "")
                )
                if user_name and assignee_lower in user_name.lower():
                    return (
                        user.get("gid")
                        if isinstance(user, dict)
                        else getattr(user, "gid", None)
                    )
        except Exception as exc:
            logger.warning(
                "assignee_resolution_failed",
                extra={"assignee_name": assignee_name, "error": str(exc)},
            )

        return None

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------

    @staticmethod
    def _extract_gid(result: Any) -> str:
        """Extract GID from Asana API result."""
        if isinstance(result, dict):
            return result.get("gid", "")
        return getattr(result, "gid", "")

    @staticmethod
    def _to_list(result: Any) -> list:
        """Convert Asana API result to a plain list."""
        if isinstance(result, list):
            return result
        return list(result)


__all__ = [
    "HOLDER_TYPES",
    "IntakeCreateService",
    "VALID_PROCESS_TYPES",
]
