"""FieldWriteService -- orchestrates the validate-resolve-write-invalidate pipeline.

Per TDD-ENTITY-WRITE-API Section 3.3:
    Stateless, request-scoped orchestrator for the entity write pipeline.
    Keeps the route handler thin.

Per TDD Section 4 (Data Flow):
    1. Lookup writable entity info from EntityWriteRegistry.
    2. Fetch task with custom_fields + enum_options + memberships.
    3. Verify task membership in entity type's project.
    4. Construct FieldResolver from task's custom field data.
    5. Resolve all fields (core + custom).
    6. Build Asana API payload (core fields + custom_fields dict).
    7. Execute single TasksClient.update_async() call.
    8. Optionally re-fetch for updated field values.
    9. Emit MutationEvent for cache invalidation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
)
from autom8_asana.exceptions import NotFoundError
from autom8_asana.resolution.field_resolver import FieldResolver, ResolvedField
from autom8_asana.resolution.write_registry import (
    CORE_FIELD_NAMES,
    EntityWriteRegistry,
    WritableEntityInfo,
)
from autom8_asana.services.errors import (
    EntityTypeMismatchError,
    NoValidFieldsError,
    TaskNotFoundError,
)

if TYPE_CHECKING:
    from autom8_asana.cache.integration.mutation_invalidator import (
        MutationInvalidator,
    )
    from autom8_asana.client import AsanaClient

logger = get_logger(__name__)

# Opt fields requested when fetching the target task.
# Includes custom field data needed for resolution and membership for validation.
_TASK_OPT_FIELDS: list[str] = [
    "custom_fields",
    "custom_fields.name",
    "custom_fields.resource_subtype",
    "custom_fields.enum_options",
    "custom_fields.text_value",
    "custom_fields.number_value",
    "custom_fields.enum_value",
    "custom_fields.multi_enum_values",
    "memberships.project.gid",
    "name",
    "assignee",
    "due_on",
    "completed",
    "notes",
]


@dataclass(frozen=True, slots=True)
class WriteFieldsResult:
    """Result of a field write operation.

    Attributes:
        gid: Task GID.
        entity_type: Entity type string.
        field_results: Per-field resolution results.
        fields_written: Count of successfully written fields.
        fields_skipped: Count of skipped/errored fields.
        updated_fields: Echoed or re-fetched field values (None unless requested).
    """

    gid: str
    entity_type: str
    field_results: list[ResolvedField]
    fields_written: int
    fields_skipped: int
    updated_fields: dict[str, Any] | None = None


class FieldWriteService:
    """Orchestrates the validate -> resolve -> write -> invalidate pipeline.

    Stateless. Constructed per-request.

    The service does NOT manage authentication or entity type validation.
    Those concerns live in the route handler (auth dependency) and
    the route's direct registry check. This service receives a pre-validated
    entity type and executes the write.
    """

    def __init__(
        self,
        client: AsanaClient,
        write_registry: EntityWriteRegistry,
    ) -> None:
        self._client = client
        self._write_registry = write_registry

    async def write_async(
        self,
        entity_type: str,
        gid: str,
        fields: dict[str, Any],
        list_mode: str = "replace",
        include_updated: bool = False,
        mutation_invalidator: MutationInvalidator | None = None,
    ) -> WriteFieldsResult:
        """Execute the complete write pipeline.

        Steps:
        1. Lookup writable entity info from EntityWriteRegistry.
        2. Fetch task with custom_fields + enum_options + memberships.
        3. Verify task membership in entity type's project.
        4. Construct FieldResolver from task's custom field data.
        5. Resolve all fields (core + custom).
        6. Build Asana API payload (core fields + custom_fields dict).
        7. Execute single TasksClient.update_async() call.
        8. Optionally re-fetch for updated field values.
        9. Emit MutationEvent for cache invalidation.

        Args:
            entity_type: Validated entity type string.
            gid: Task GID to write to.
            fields: Dict of field_name -> value from request.
            list_mode: "replace" or "append".
            include_updated: If True, re-fetch and return current values.
            mutation_invalidator: Optional invalidator for fire-and-forget
                cache invalidation.

        Returns:
            WriteFieldsResult with per-field results and counts.

        Raises:
            TaskNotFoundError: Task GID does not exist.
            EntityTypeMismatchError: Task not in entity's project.
            NoValidFieldsError: All fields failed validation.
            RateLimitError: Asana rate limit hit (propagated for upstream handling).
        """
        # [1] Registry lookup
        write_info = self._write_registry.get(entity_type)
        if write_info is None:
            # Defensive -- caller should validate before calling
            msg = f"Entity type '{entity_type}' is not writable"
            raise ValueError(msg)

        # [2] Fetch task
        task_data = await self._fetch_task(gid)

        # [3] Verify project membership
        self._verify_membership(gid, task_data, write_info)

        # [4] Construct FieldResolver
        custom_fields_data = task_data.get("custom_fields") or []
        resolver = FieldResolver(
            custom_fields_data=custom_fields_data,
            descriptor_index=write_info.descriptor_index,
            core_fields=CORE_FIELD_NAMES,
        )

        # [5] Resolve fields
        resolved_fields = resolver.resolve_fields(fields, list_mode)

        # [6] Build payload
        core_payload, custom_payload = self._build_payload(resolved_fields)

        fields_written = len(core_payload) + len(custom_payload)
        fields_skipped = len(resolved_fields) - fields_written

        if fields_written == 0:
            raise NoValidFieldsError("All fields failed resolution -- nothing to write")

        # [7] Execute Asana update (single API call)
        update_kwargs: dict[str, Any] = {**core_payload}
        if custom_payload:
            update_kwargs["custom_fields"] = custom_payload

        await self._client.tasks.update_async(gid, raw=True, **update_kwargs)

        # [8] Optionally re-fetch for updated values
        #     Invalidate the task's cache entry first so the refetch reads
        #     fresh data from Asana, not the stale pre-write cache entry
        #     populated by _fetch_task() in step [2].  (Fixes D-EW-001)
        updated_fields: dict[str, Any] | None = None
        if include_updated:
            from autom8_asana.cache.models.entry import EntryType

            self._client.tasks._cache_invalidate(gid, [EntryType.TASK])
            updated_fields = await self._refetch_updated(
                gid, resolved_fields, write_info
            )

        # [9] Fire-and-forget cache invalidation
        if mutation_invalidator is not None:
            event = MutationEvent(
                entity_kind=EntityKind.TASK,
                entity_gid=gid,
                mutation_type=MutationType.UPDATE,
                project_gids=[write_info.project_gid],
            )
            asyncio.create_task(
                self._invalidate_cache(mutation_invalidator, event),
                name=f"invalidate_{gid}",
            )

        return WriteFieldsResult(
            gid=gid,
            entity_type=entity_type,
            field_results=resolved_fields,
            fields_written=fields_written,
            fields_skipped=fields_skipped,
            updated_fields=updated_fields,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_task(self, gid: str) -> dict[str, Any]:
        """Fetch task with custom fields and memberships.

        Raises TaskNotFoundError on Asana 404.
        Lets RateLimitError propagate.
        """
        try:
            result = await self._client.tasks.get_async(
                gid, raw=True, opt_fields=_TASK_OPT_FIELDS
            )
            return result
        except NotFoundError as exc:
            raise TaskNotFoundError(gid) from exc

    @staticmethod
    def _verify_membership(
        gid: str,
        task_data: dict[str, Any],
        write_info: WritableEntityInfo,
    ) -> None:
        """Verify task belongs to entity type's project.

        Raises EntityTypeMismatchError if no membership matches.
        """
        memberships = task_data.get("memberships") or []
        actual_project_gids: list[str] = []
        for m in memberships:
            if isinstance(m, dict):
                project = m.get("project")
                if isinstance(project, dict) and project.get("gid"):
                    actual_project_gids.append(project["gid"])

        if write_info.project_gid not in actual_project_gids:
            raise EntityTypeMismatchError(
                gid=gid,
                expected_project=write_info.project_gid,
                actual_projects=actual_project_gids,
            )

    @staticmethod
    def _build_payload(
        resolved_fields: list[ResolvedField],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Separate resolved fields into core and custom payloads.

        Returns:
            Tuple of (core_payload, custom_payload).
        """
        core_payload: dict[str, Any] = {}
        custom_payload: dict[str, Any] = {}

        for rf in resolved_fields:
            if rf.status != "resolved":
                continue
            if rf.is_core:
                core_payload[rf.matched_name] = rf.value  # type: ignore[index]  # matched_name validated non-None when resolved
            else:
                custom_payload[rf.gid] = rf.value  # type: ignore[index]  # gid validated non-None when resolved

        return core_payload, custom_payload

    async def _refetch_updated(
        self,
        gid: str,
        resolved_fields: list[ResolvedField],
        write_info: WritableEntityInfo,
    ) -> dict[str, Any]:
        """Re-fetch task and build updated_fields dict.

        Maps custom field GIDs back to business field names.
        """
        task_data = await self._client.tasks.get_async(
            gid, raw=True, opt_fields=_TASK_OPT_FIELDS
        )
        updated: dict[str, Any] = {}

        # Build GID -> input_name map for custom fields
        gid_to_name: dict[str, str] = {}
        for rf in resolved_fields:
            if rf.status == "resolved" and rf.gid:
                gid_to_name[rf.gid] = rf.input_name

        # Extract custom field values
        for cf in task_data.get("custom_fields") or []:
            cf_gid = cf.get("gid", "")
            if cf_gid in gid_to_name:
                field_name = gid_to_name[cf_gid]
                # Return the appropriate value based on field type
                subtype = cf.get("resource_subtype", "")
                if subtype == "text":
                    updated[field_name] = cf.get("text_value")
                elif subtype == "number":
                    updated[field_name] = cf.get("number_value")
                elif subtype == "enum":
                    enum_val = cf.get("enum_value")
                    updated[field_name] = (
                        enum_val.get("name") if isinstance(enum_val, dict) else None
                    )
                elif subtype == "multi_enum":
                    multi = cf.get("multi_enum_values") or []
                    updated[field_name] = [
                        opt.get("name") for opt in multi if isinstance(opt, dict)
                    ]
                else:
                    updated[field_name] = cf.get("display_value")

        # Extract core field values
        for rf in resolved_fields:
            if rf.status == "resolved" and rf.is_core and rf.matched_name:
                updated[rf.matched_name] = task_data.get(rf.matched_name)

        return updated

    @staticmethod
    async def _invalidate_cache(
        invalidator: MutationInvalidator,
        event: MutationEvent,
    ) -> None:
        """Fire-and-forget cache invalidation with error suppression."""
        try:
            await invalidator.invalidate_async(event)
        except Exception:
            logger.warning(
                "entity_write_cache_invalidation_failed",
                extra={
                    "entity_gid": event.entity_gid,
                    "project_gids": event.project_gids,
                },
            )
