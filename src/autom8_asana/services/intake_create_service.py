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
from autom8_asana.core.project_registry import UNIT_PROJECT

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# Name of the Business Units section a freshly-created unit is pinned into
# (BR-3). Resolved to a live GID BY NAME at intake time -- never a hardcoded
# section GID -- so an Asana section rename fails LOUD instead of silently
# landing the unit in the project's first section ("Templates"), which every
# reconciliation reader excludes (an unresolvable-unit birth). "Onboarding" is
# an "activating" bucket in the section registry, so an Onboarding unit is
# active under /v1/resolve/unit(active_only=True).
ONBOARDING_SECTION_NAME = "Onboarding"

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
# "canary" (2026-08-11, CARD-CANARY-ROUTE-422): the ECO-R1 synthetic process type
# the calendly-intake canary routes to (event_stages.yaml canary_synthetic →
# process_type: canary; spec §1.4). The route path is generic post-validation —
# first run creates ONE "Canary Process" subtask under the seeded canary unit
# (keeper task 1217301971794137), every later run REUSES it (is_new=false), so
# no per-run state accrues. No ProcessType model is required: routing has no
# per-type template (unlike the consultation gap above, which is an
# intake-create process-block concern).
VALID_PROCESS_TYPES: set[str] = {"sales", "retention", "implementation", "canary"}

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
    except Exception:  # noqa: BLE001
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
    except Exception:  # noqa: BLE001
        pass
    return ""


def resolve_unit_holder_project_gid() -> str:
    """Resolve the Units (``unit_holder``) project GID from EntityProjectRegistry.

    Module-level function to enable clean patching in tests, mirroring
    :func:`resolve_business_project_gid`. The GID is sourced from the
    ``unit_holder`` entity descriptor's ``primary_project_gid`` (the Units
    project) via the registry -- never hard-coded here (BR3B / DIC O-B1).

    Returns:
        Units project GID string, or "" if unresolvable.
    """
    try:
        from autom8_asana.services.resolver import EntityProjectRegistry

        registry = EntityProjectRegistry.get_instance()
        project_gid = registry.get_project_gid("unit_holder")
        if project_gid:
            return project_gid
    except Exception:  # noqa: BLE001
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
            raise LookupError("Business project not configured in EntityProjectRegistry")

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
            await self._phase6_write_social_profiles(business_gid, request.social_profiles)
            logger.info(
                "intake_create_phase6_complete",
                extra={
                    "business_gid": business_gid,
                    "profile_count": len(request.social_profiles),
                },
            )

        # Phase 7: Write address fields to location_holder
        if request.address is not None:
            await self._phase7_write_address(holders["location_holder"], request.address)
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
        """Phase 1: Create the Business task and stamp its Office Phone field.

        The task is created with ``name``/``projects``; ``office_phone``,
        ``website`` and ``num_reviews`` are additionally echoed into the
        human-readable notes blob. ``hours`` is not persisted.

        The ``Office Phone`` custom field (``cf:Office Phone``) is then stamped
        post-create via fetch-then-update (see
        :meth:`_phase1b_stamp_office_phone`). That custom field is the SINGLE
        source of the business resolver index key, so a notes-only write would
        leave the index row null and break the create->resolve round-trip for
        net-new offices. No other custom field is set here: ``website`` /
        ``num_reviews`` remain notes-only, and ``company_id`` is not a create
        input.
        """
        task_data: dict[str, Any] = {
            "name": request.name,
            "projects": [project_gid],
        }

        # Echo enrichment data into the human-readable notes blob.
        notes_parts: list[str] = []
        if request.office_phone:
            notes_parts.append(f"Office Phone: {request.office_phone}")
        if request.website:
            notes_parts.append(f"Website: {request.website}")
        if request.num_reviews is not None:
            notes_parts.append(f"Reviews: {request.num_reviews}")

        if notes_parts:
            task_data["notes"] = "\n".join(notes_parts)

        result = await self._client.tasks.create_async(
            name=task_data["name"],
            projects=task_data.get("projects"),
            notes=task_data.get("notes"),
        )
        business_gid = self._extract_gid(result)
        # Emit the created gid BEFORE the CF stamp so a stamp failure leaves a
        # FINDABLE orphan in the logs, not an invisible one (DEF-QA-2).
        logger.info(
            "intake_create_phase1_business_created",
            extra={"business_gid": business_gid},
        )

        # Stamp cf:Office Phone on the just-created Business task. office_phone
        # is a required request field, so this write is unconditional.
        await self._phase1b_stamp_office_phone(business_gid, request.office_phone)

        return business_gid

    async def _phase1b_stamp_office_phone(
        self,
        business_gid: str,
        office_phone: str,
    ) -> None:
        """Stamp the Office Phone custom field on the Business task.

        Post-create fetch-then-update, mirroring
        :meth:`_phase6_write_social_profiles`: fetch the task's custom fields,
        resolve the ``Office Phone`` field gid by name (case-insensitive), and
        write the E.164 value with the text-CF payload shape ``{gid: value}``
        (NOT the enum-option shape ``{gid: {"gid": option}}``).

        ``cf:Office Phone`` is the single source of the business resolver index
        key (``dataframes/schemas/business.py``), so this write is what makes an
        intake-created business resolvable by its office phone on the next
        booking.

        Non-fatal: logs a warning and returns if the field gid cannot be
        resolved, consistent with the other custom-field writers in this
        service (the two-sided regression test is the real guard).
        """
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
            cf_name = cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            cf_gid = cf.get("gid", "") if isinstance(cf, dict) else getattr(cf, "gid", "")
            if cf_name and cf_gid:
                # strip() so a trailing/leading-space CF rename ("Office Phone ")
                # cannot silently miss and mint an unresolvable business (DEF-QA-3).
                field_name_to_gid[cf_name.strip().lower()] = cf_gid

        office_phone_gid = field_name_to_gid.get("office phone")
        if not office_phone_gid:
            logger.warning(
                "office_phone_cf_not_found",
                extra={"business_gid": business_gid},
            )
            return

        # A write failure here (Asana API error) MUST propagate loud, never be
        # swallowed: a silent stamp failure is an unresolvable-orphan birth.
        # Emit a findable failure event, then re-raise (DEF-QA-1 / DEF-QA-2).
        try:
            await self._client.tasks.update_async(
                business_gid,
                custom_fields={office_phone_gid: office_phone},
            )
        except Exception:
            logger.exception(
                "office_phone_cf_stamp_failed",
                extra={"business_gid": business_gid},
            )
            raise

    async def _phase2_create_holders(self, business_gid: str) -> dict[str, str]:
        """Phase 2: Create 7 holder subtasks under Business (parallel).

        The ``unit_holder`` is additionally created as a MEMBER of the Units
        project (BR3B / DIC O-B1) so an intake-created office enters Domain B's
        intent frame as a Custom Cal Status carrier. Membership is established
        at creation time via the ``projects`` argument.

        MEMBERSHIP ONLY -- we write NO field value. Membership confers PRESENCE
        (empty) of all of the Units project's custom fields immediately and
        race-free; a value-write would re-open the inherited-CF projection race
        (PR-4) AND would touch the walled Custom GHL ID field (RUL-6), so it is
        deliberately NOT done here. Only ``unit_holder`` joins Units -- the other
        six holders keep their own projects and are created as bare subtasks
        (unchanged).

        Returns dict of holder_name -> gid.
        """
        # BR3B: resolve the Units project GID fail-LOUD and assert its
        # single-section invariant BEFORE any holder is created. A missing
        # registration or a drifted section layout REFUSES the intake rather
        # than silently birthing the unit_holder outside Domain B's frame (or in
        # an excluded section -- the "Templates" silent-green trap SUB-1 hit on
        # the unit path).
        units_project_gid = resolve_unit_holder_project_gid()
        if not units_project_gid:
            raise LookupError("Units project (unit_holder) not configured in EntityProjectRegistry")
        await self._assert_units_single_section(units_project_gid)

        async def create_holder(holder_name: str) -> tuple[str, str]:
            # Only the unit_holder joins the Units project (BR3B), by MEMBERSHIP
            # at creation time. The other six holders have their own projects and
            # are created as bare subtasks -- their call is byte-identical to the
            # pre-BR3B path (no ``projects`` argument).
            if holder_name == "unit_holder":
                result = await self._client.tasks.create_async(
                    name=holder_name,
                    parent=business_gid,
                    projects=[units_project_gid],
                )
            else:
                result = await self._client.tasks.create_async(
                    name=holder_name,
                    parent=business_gid,
                )
            return holder_name, self._extract_gid(result)

        holder_results = await asyncio.gather(*[create_holder(name) for name in HOLDER_TYPES])
        return dict(holder_results)

    async def _assert_units_single_section(self, units_project_gid: str) -> None:
        """Assert the Units project has exactly one section (BR3B tripwire).

        The ``unit_holder`` joins Units by MEMBERSHIP ALONE -- no explicit
        section placement -- which is only safe while Units has a single flat
        section (``Untitled section``). A section-less membership add lands the
        task in the project's FIRST section, so a second section would silently
        route new holders into an unintended (possibly reconciliation-excluded)
        bucket: the "Templates" silent-green trap that BR-3 had to place
        explicitly around on the unit path.

        Here membership alone suffices, so this tripwire REFUSES the intake LOUD
        if the single-section invariant ever breaks, rather than silently
        birthing the holder in an unpinned section. It reads the LIVE project
        definition (never a hard-coded section GID).

        Raises:
            RuntimeError: If the Units project does not have exactly one section.
        """
        sections = await self._client.projects.get_sections_async(
            units_project_gid,
            opt_fields=["name", "gid"],
        ).collect()
        section_names = [
            (section.get("name", "") if isinstance(section, dict) else getattr(section, "name", ""))
            or ""
            for section in sections
        ]
        if len(section_names) != 1:
            raise RuntimeError(
                f"Units project {units_project_gid} expected exactly one section for "
                f"membership-only placement; found {len(section_names)}: {section_names}. "
                "BR3B single-section invariant broken -- refusing to birth the unit_holder "
                "in an unpinned section."
            )

    async def _phase3_create_unit(
        self,
        unit_holder_gid: str,
        unit_name: str,
        vertical: str,
    ) -> str:
        """Phase 3: Create Unit subtask under unit_holder.

        The unit is created as a subtask of ``unit_holder`` and then ALSO added
        to the Business Units project in the Onboarding section (BR-3). The
        project-add is what makes the unit carry the project's ``Vertical``
        custom field and appear in the unit index / resolve. It MUST happen
        BEFORE :meth:`_write_vertical_custom_field`: the Vertical CF is only
        applicable to a task once it is a member of the Vertical-defining
        project.
        """
        result = await self._client.tasks.create_async(
            name=unit_name,
            parent=unit_holder_gid,
            notes=f"Vertical: {vertical}",
        )
        unit_gid = self._extract_gid(result)

        # BR-3: carry the Vertical field onto the unit by adding it to the
        # Business Units project (Onboarding section) BEFORE writing the CF. A
        # bare subtask has no Vertical CF, so the old fetch-then-write no-op'd
        # silently and left the unit unindexable on its 2nd key column
        # ("vertical", unit.py:64 -> cf:Vertical).
        await self._place_unit_in_business_units(unit_gid)

        # Write Vertical enum custom field on the unit (now a project member).
        await self._write_vertical_custom_field(unit_gid, vertical)

        return unit_gid

    async def _place_unit_in_business_units(self, unit_gid: str) -> None:
        """Add the unit to the Business Units project, pinned to Onboarding.

        Two-step by design (BR-3 / A'-1):

        1. Resolve the Onboarding section GID BY NAME from the LIVE project
           definition and fail LOUD if it is absent -- resolved FIRST, before
           any mutation, so a missing section never leaves the unit stranded in
           the excluded "Templates" section.
        2. ``add_to_project_async`` establishes project membership; the client's
           ``section_gid`` argument is a no-op on the SaveSession path
           (``task_operations.add_to_project`` drops it), so it CANNOT be relied
           on to place the section -- a section-less add lands in the project's
           FIRST section ("Templates"), which every reconciliation reader
           EXCLUDES. ``move_to_section_async`` then explicitly places the unit
           in Onboarding.

        Landing in "Templates" is the silent-green trap this method exists to
        avoid: the Vertical CF readback (L1) would still pass, but the unit
        would never appear in the unit index and ``/v1/resolve/unit`` would
        return NOT_FOUND.
        """
        section_gid = await self._resolve_onboarding_section_gid()
        # Membership first (lands in the default/first section), then explicit
        # placement into Onboarding. The transient default-section membership is
        # invisible to the SCHEDULED reconciliation sweep.
        await self._client.tasks.add_to_project_async(unit_gid, UNIT_PROJECT)
        await self._client.tasks.move_to_section_async(
            unit_gid,
            section_gid,
            UNIT_PROJECT,
        )

    async def _resolve_onboarding_section_gid(self) -> str:
        """Resolve the Onboarding section GID BY NAME from the LIVE project.

        Reads the Business Units project's sections (the project DEFINITION,
        per O6) and matches ``Onboarding`` case/space-insensitively. Fails LOUD
        (raises) if no such section exists -- refusing the silent Templates
        landing (A'-1).

        Raises:
            RuntimeError: If the Business Units project has no Onboarding
                section.
        """
        sections = await self._client.projects.get_sections_async(
            UNIT_PROJECT,
            opt_fields=["name", "gid"],
        ).collect()

        available: list[str] = []
        for section in sections:
            name = (
                section.get("name", "")
                if isinstance(section, dict)
                else getattr(section, "name", "")
            ) or ""
            available.append(name)
            if name.strip().lower() == ONBOARDING_SECTION_NAME.lower():
                gid = (
                    section.get("gid", "")
                    if isinstance(section, dict)
                    else getattr(section, "gid", "")
                )
                if gid:
                    return str(gid)

        raise RuntimeError(
            f"Business Units project {UNIT_PROJECT} has no "
            f"{ONBOARDING_SECTION_NAME!r} section; refusing to add the unit. A "
            "section-less project add lands in the excluded 'Templates' "
            "section, which silently drops the unit from the unit index and "
            f"/v1/resolve/unit. Available sections: {sorted(set(available))}"
        )

    async def _write_vertical_custom_field(
        self,
        task_gid: str,
        vertical: str,
    ) -> None:
        """Resolve and write the Vertical enum custom field on a unit task.

        Resolves the ``Vertical`` field gid and the target enum-option gid from
        the Business Units project's custom-field DEFINITION (O6) -- NOT from a
        fresh read of ``task_gid``. The task was added to the project moments
        ago (:meth:`_place_unit_in_business_units`); Asana's inherited-CF
        projection lags membership by up to ~26h, so a fresh task read can
        return ``custom_fields == []`` and the field-name match would no-op
        (the BR-3 / PR-4 read-your-own-write race). The project field
        definition is stable and race-free, and membership makes the write
        itself land immediately.

        Non-fatal: logs a warning and returns if the field or the enum option
        is not in the project definition (matches the other CF writers in this
        service -- the two-sided regression test is the real guard).
        """
        settings = await self._client.custom_fields.get_settings_for_project_async(
            UNIT_PROJECT,
            opt_fields=[
                "custom_field.gid",
                "custom_field.name",
                "custom_field.enum_options.gid",
                "custom_field.enum_options.name",
            ],
        ).collect()

        # Find the "Vertical" custom field in the PROJECT definition.
        cf_gid = ""
        enum_options: list[Any] = []
        for setting in settings:
            cf = (
                setting.get("custom_field")
                if isinstance(setting, dict)
                else getattr(setting, "custom_field", None)
            )
            if cf is None:
                continue
            cf_name = (
                cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            ) or ""
            if cf_name.lower() == "vertical":
                cf_gid = (
                    cf.get("gid", "") if isinstance(cf, dict) else getattr(cf, "gid", "")
                ) or ""
                enum_options = (
                    cf.get("enum_options", [])
                    if isinstance(cf, dict)
                    else getattr(cf, "enum_options", []) or []
                )
                break

        if not cf_gid:
            logger.warning(
                "vertical_cf_not_found_in_project",
                extra={"task_gid": task_gid, "project_gid": UNIT_PROJECT},
            )
            return

        # Match enum option by name (case-insensitive)
        enum_option_gid = ""
        for opt in enum_options:
            opt_name = (
                opt.get("name", "") if isinstance(opt, dict) else getattr(opt, "name", "")
            ) or ""
            if opt_name.lower() == vertical.lower():
                enum_option_gid = (
                    opt.get("gid", "") if isinstance(opt, dict) else getattr(opt, "gid", "")
                ) or ""
                break

        if not enum_option_gid:
            logger.warning(
                "vertical_enum_option_not_found",
                extra={"task_gid": task_gid, "vertical": vertical},
            )
            return

        # Enum CF WRITE value is the PLAIN option gid string (ADR F-1 ruling),
        # NOT the nested {"gid": ...} READ shape. Mirrors the forwarding-stage
        # writer (receipts_service.py) which lands a plain option gid.
        await self._client.tasks.update_async(
            task_gid,
            custom_fields={cf_gid: enum_option_gid},
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

        result = await self._client.tasks.create_async(
            name=contact.name,
            parent=contact_holder_gid,
            notes="\n".join(notes_parts) if notes_parts else "",
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
            cf_name = cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            cf_gid = cf.get("gid", "") if isinstance(cf, dict) else getattr(cf, "gid", "")
            if cf_name and cf_gid:
                field_name_to_gid[cf_name.lower()] = cf_gid

        # Build custom_fields payload
        custom_fields_payload: dict[str, str] = {}
        for profile in social_profiles:
            platform = (
                profile.platform if hasattr(profile, "platform") else profile.get("platform", "")
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
                custom_fields=custom_fields_payload,
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
            cf_name = cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            cf_gid = cf.get("gid", "") if isinstance(cf, dict) else getattr(cf, "gid", "")
            if cf_name and cf_gid:
                field_name_to_gid[cf_name.lower()] = cf_gid

        custom_fields_payload: dict[str, str] = {}
        address_dict = address.model_dump() if hasattr(address, "model_dump") else address
        for field_attr, display_name in ADDRESS_FIELD_MAP.items():
            value = address_dict.get(field_attr)
            if value is not None:
                gid = field_name_to_gid.get(display_name.lower())
                if gid:
                    custom_fields_payload[gid] = str(value)

        if custom_fields_payload:
            await self._client.tasks.update_async(
                location_holder_gid,
                custom_fields=custom_fields_payload,
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
                existing.get("gid") if isinstance(existing, dict) else getattr(existing, "gid", "")
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
                process_gid=str(existing_gid or ""),
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

        create_kwargs: dict[str, Any] = {
            "name": process_data["name"],
            "parent": unit_gid,
            "notes": process_data.get("notes"),
        }
        if "due_at" in process_data:
            create_kwargs["due_at"] = process_data["due_at"]
        result = await self._client.tasks.create_async(**create_kwargs)
        process_gid = self._extract_gid(result)

        # Resolve assignee if provided
        resolved_assignee: str | None = None
        if assignee_name:
            resolved_assignee = await self._resolve_assignee(assignee_name)
            if resolved_assignee:
                try:
                    await self._client.tasks.update_async(
                        process_gid,
                        assignee=resolved_assignee,
                    )
                except Exception as exc:  # noqa: BLE001
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
            ).collect()
            subtasks = self._to_list(subtasks_result)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "existing_process_check_failed",
                extra={"unit_gid": unit_gid, "error": str(exc)},
            )
            return None

        process_name_lower = f"{process_type.title()} Process".lower()
        for st in subtasks:
            st_name = st.get("name", "") if isinstance(st, dict) else getattr(st, "name", "")
            st_completed = (
                st.get("completed", False)
                if isinstance(st, dict)
                else getattr(st, "completed", False)
            )
            if st_name and st_name.lower() == process_name_lower and not st_completed:
                return dict(st) if not isinstance(st, dict) else st

        return None

    async def _resolve_assignee(self, assignee_name: str) -> str | None:
        """Fuzzy match assignee name against workspace users.

        Returns user GID if matched, None otherwise.
        Logs warning on failure but does not raise.
        """
        try:
            workspace_gid = resolve_workspace_gid()
            users_result = await self._client.users.list_for_workspace_async(
                workspace_gid,
                opt_fields=["name", "gid"],
            ).collect()
            users = self._to_list(users_result)

            assignee_lower = assignee_name.lower()
            for user in users:
                user_name = (
                    user.get("name", "") if isinstance(user, dict) else getattr(user, "name", "")
                )
                if user_name and assignee_lower in user_name.lower():
                    return user.get("gid") if isinstance(user, dict) else getattr(user, "gid", None)
        except Exception as exc:  # noqa: BLE001
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
            return str(result.get("gid", ""))
        return getattr(result, "gid", "")

    @staticmethod
    def _to_list(result: Any) -> list[Any]:
        """Convert Asana API result to a plain list."""
        if isinstance(result, list):
            return result
        return list(result)


__all__ = [
    "HOLDER_TYPES",
    "IntakeCreateService",
    "VALID_PROCESS_TYPES",
]
