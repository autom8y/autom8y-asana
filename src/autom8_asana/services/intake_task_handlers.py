"""Intake pipeline handlers for project and section entity types.

Sprint 2 receiver-surface — Item E (AC-R5).
Resolves S-09 shortcut from Sprint 1 close report:66 / HANDOFF §5 Precondition 3.

ProjectTaskHandler and SectionTaskHandler route inbound webhook/event payloads
to ProgressiveProjectBuilder for the 'project' and 'section' entity types.

COUPLING CONSTRAINT (AC-R5):
    project_gid is resolved from the event payload (event["project_gid"]),
    NOT from EntityProjectRegistry.get_project_gid().
    Reason: Item A1 enables arbitrary-GID flow — any caller may supply a
    fleet-specific project GID that does not exist in the registry. The
    registry is populated at lifespan startup from the workspace API (Item C /
    PG-02), but intake events may arrive with GIDs that were unknown at startup
    (e.g., newly created Asana projects). Payload-extraction preserves that
    semantic without coupling to the singleton registry at handler time.

Deliberate shortcuts (prototype):
    - No AuthN/AuthZ at handler boundary (authentication is at the Lambda/API
      gateway layer upstream of these handlers).
    - No idempotency guard — duplicate events cause duplicate builds. Production
      should add an idempotency key keyed on (project_gid, entity_type, watermark).
    - No retry/backoff — build failures propagate as exceptions; Lambda handler
      wraps with its own error handling.
    - SectionPersistence is created via create_section_persistence() each call
      (same factory as the read path — DEF-005 guard). Production could cache
      the instance across invocations if the Lambda container is warm.

Production remediation notes:
    - Replace bare exception logging with structured error recovery and
      dead-letter-queue routing.
    - Add idempotency key check before triggering a build.
    - Wire EntityDetector (S-08) to route arbitrary Asana task events to the
      correct handler based on project membership, not static entity_type label.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.auth.bot_pat import get_bot_pat
from autom8_asana.dataframes.builders import ProgressiveProjectBuilder
from autom8_asana.dataframes.models.registry import get_schema
from autom8_asana.dataframes.resolver.default import DefaultCustomFieldResolver
from autom8_asana.dataframes.section_persistence import create_section_persistence
from autom8_asana.services.gid_lookup import build_gid_index_data

if TYPE_CHECKING:
    from autom8_asana.dataframes.builders.build_result import BuildResult

logger = get_logger(__name__)


def _get_workspace_gid() -> str | None:
    """Resolve ASANA_WORKSPACE_GID from environment (patchable in tests).

    Tries autom8y_config first; falls back to os.environ for local/test runs.
    This function lives at module scope so tests can patch it via
    ``autom8_asana.services.intake_task_handlers._get_workspace_gid``.
    """
    try:
        from autom8y_config.lambda_extension import resolve_secret_from_env

        return resolve_secret_from_env("ASANA_WORKSPACE_GID")
    except ImportError:
        import os

        return os.environ.get("ASANA_WORKSPACE_GID")


# Key used by callers to pass the Asana project GID in the event payload.
# Both handlers enforce that this key is present and non-empty.
EVENT_KEY_PROJECT_GID = "project_gid"


@dataclass(frozen=True)
class IntakeEventPayload:
    """Validated payload extracted from a raw intake event dict.

    Constructed by ProjectTaskHandler._extract_payload() and
    SectionTaskHandler._extract_payload(). Immutable after construction.

    Attributes:
        project_gid: Asana project GID from the event payload. Always a
            non-empty string — handlers reject events without this key.
        entity_type: Entity type label for this handler ("project" or "section").
        dry_run: If True, skip write operations (pass-through to builder).
    """

    project_gid: str
    entity_type: str
    dry_run: bool = False


class _BaseIntakeHandler:
    """Base intake handler — shared payload extraction and build dispatch.

    Subclasses set `ENTITY_TYPE` class attribute; no other customization needed
    for project/section parity (both use ProgressiveProjectBuilder with the same
    call signature).

    The handler is intentionally stateless at the class level. Each `handle_async`
    call creates its own AsanaClient and SectionPersistence instances so Lambda
    warm-container reuse does not bleed credentials or S3 state across invocations.
    """

    ENTITY_TYPE: str  # set by concrete subclass

    @classmethod
    def _extract_payload(cls, event: dict[str, Any]) -> IntakeEventPayload:
        """Extract and validate the event payload.

        Args:
            event: Raw Lambda event dict or API request body.

        Returns:
            Validated IntakeEventPayload.

        Raises:
            ValueError: If project_gid is missing or empty in the event.
        """
        raw_gid = event.get(EVENT_KEY_PROJECT_GID)
        if not raw_gid or not isinstance(raw_gid, str) or not raw_gid.strip():
            raise ValueError(
                f"{cls.__name__}: event missing required key '{EVENT_KEY_PROJECT_GID}'. "
                f"Received keys: {sorted(event.keys())}. "
                "project_gid must be resolved from the event payload — "
                "NOT from EntityProjectRegistry (AC-R5 coupling constraint)."
            )
        return IntakeEventPayload(
            project_gid=raw_gid.strip(),
            entity_type=cls.ENTITY_TYPE,
            dry_run=bool(event.get("dry_run", False)),
        )

    @classmethod
    async def handle_async(cls, event: dict[str, Any]) -> BuildResult:
        """Handle an intake event by triggering a progressive build.

        Extracts project_gid from the event payload (NEVER from
        EntityProjectRegistry) and delegates to ProgressiveProjectBuilder.

        AC-R5 coupling constraint: project_gid MUST come from
        event["project_gid"]. Do not add a registry fallback here.

        Args:
            event: Raw event dict containing at minimum {"project_gid": "<gid>"}.
                Optional keys: "dry_run" (bool).

        Returns:
            BuildResult from ProgressiveProjectBuilder.build_progressive_async().

        Raises:
            ValueError: If event["project_gid"] is missing or empty.
            RuntimeError: If required environment variables are absent
                (ASANA_BOT_PAT / ASANA_WORKSPACE_GID).
        """
        # --- Payload extraction (AC-R5: from event, not registry) ---
        payload = cls._extract_payload(event)

        logger.info(
            "intake_task_handler_started",
            extra={
                "entity_type": payload.entity_type,
                "project_gid": payload.project_gid,
                "dry_run": payload.dry_run,
                "handler": cls.__name__,
            },
        )

        # --- Lazy imports: AsanaClient and settings are kept lazy to avoid
        # circular imports at module load time (AsanaClient transitively imports
        # many services, and settings pulls in environment). ---
        # AsanaClient is kept lazy to avoid circular import at module load time.
        from autom8_asana import AsanaClient

        # --- Resolve credentials from environment ---
        bot_pat = get_bot_pat()
        workspace_gid = _get_workspace_gid()
        if not workspace_gid:
            raise RuntimeError(
                f"{cls.__name__}: ASANA_WORKSPACE_GID not set — "
                "cannot build progressive DataFrame without workspace context."
            )

        # --- Schema resolution ---
        # Use snake_case→PascalCase conversion matching the preload progressive pattern.
        task_type = "".join(part.capitalize() for part in payload.entity_type.split("_"))
        schema = get_schema(task_type)

        # --- Storage and persistence (DEF-005 guard: same factory as read path) ---
        # create_section_persistence() reads get_settings().s3 — same config as
        # EntityQueryService.section_persistence lazy property (query_service.py:314-319).
        persistence = create_section_persistence()

        resolver = DefaultCustomFieldResolver()

        async with (
            persistence,
            AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client,
        ):
            builder = ProgressiveProjectBuilder(
                client=client,
                project_gid=payload.project_gid,
                entity_type=payload.entity_type,
                schema=schema,
                persistence=persistence,
                resolver=resolver,
                index_builder=build_gid_index_data,
            )
            result = await builder.build_progressive_async()

        logger.info(
            "intake_task_handler_complete",
            extra={
                "entity_type": payload.entity_type,
                "project_gid": payload.project_gid,
                "status": result.status.value if result.status else "unknown",
                "total_rows": result.total_rows,
                "sections_built": result.sections_built,
                "sections_resumed": result.sections_resumed,
                "handler": cls.__name__,
            },
        )
        return result


class ProjectTaskHandler(_BaseIntakeHandler):
    """Intake handler for 'project' entity type.

    Receives webhook/Lambda events with {"project_gid": "<16-digit-gid>"}
    and triggers ProgressiveProjectBuilder for the Asana projects list project.

    AC-R5: project_gid resolved from event payload only — NEVER from registry.
    Item A1 enables arbitrary-GID flow; this handler honors that semantic by
    extracting the GID from the inbound event rather than consulting
    EntityProjectRegistry, which may not have the specific GID registered.

    Usage (Lambda handler context):
        result = await ProjectTaskHandler.handle_async(event)

    Example event payload:
        {
            "project_gid": "1200653012566782",
            "dry_run": false
        }
    """

    ENTITY_TYPE = "project"


class SectionTaskHandler(_BaseIntakeHandler):
    """Intake handler for 'section' entity type.

    Receives webhook/Lambda events with {"project_gid": "<16-digit-gid>"}
    and triggers ProgressiveProjectBuilder for the Asana sections list project.

    AC-R5: project_gid resolved from event payload only — NEVER from registry.

    Usage (Lambda handler context):
        result = await SectionTaskHandler.handle_async(event)

    Example event payload:
        {
            "project_gid": "1200653012566783",
            "dry_run": false
        }
    """

    ENTITY_TYPE = "section"
