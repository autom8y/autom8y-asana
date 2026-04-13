"""Entity project discovery service.

Extracts the core discovery logic from api/main.py so it can be reused
by both the API startup and standalone scripts (e.g. warm_cache.py).

Requires environment variables:
    ASANA_PAT or ASANA_BOT_PAT - Asana Personal Access Token
    ASANA_WORKSPACE_GID - Workspace GID
"""

from __future__ import annotations

from autom8y_log import get_logger

from autom8_asana.config import get_workspace_gid
from autom8_asana.services.resolver import EntityProjectRegistry

logger = get_logger(__name__)


def _normalize_project_name(name: str) -> str:
    """Normalize project name for entity type matching.

    Handles common patterns:
    - "Business Units" -> "unit"
    - "Business Offers" -> "offer"
    - "Contacts" -> "contact"
    - "Business" -> "business"
    - "Units" -> "unit_holder" (per ADR-HOTFIX-entity-collision)
    - "Paid Content" -> "asset_edit" (non-standard project name)
    """
    EXPLICIT_MAPPINGS: dict[str, str] = {
        "paid content": "asset_edit",
    }

    normalized = name.lower().strip()

    if normalized in EXPLICIT_MAPPINGS:
        return EXPLICIT_MAPPINGS[normalized]

    if normalized == "units":
        return "unit_holder"

    if normalized == "business":
        return "business"
    normalized = normalized.removeprefix("business ")
    if normalized.endswith("es") and len(normalized) > 3:
        normalized = normalized[:-2]
    elif normalized.endswith("s") and len(normalized) > 2:
        normalized = normalized[:-1]
    return normalized


def _match_entity_type(project_name: str, entity_types: list[str]) -> str | None:
    """Match a project name to an entity type."""
    normalized = _normalize_project_name(project_name)
    if normalized in entity_types:
        return normalized
    return None


async def discover_entity_projects_async() -> EntityProjectRegistry:
    """Discover and register entity type -> project mappings.

    Requires ASANA_PAT/ASANA_BOT_PAT and ASANA_WORKSPACE_GID env vars.
    Populates and returns the singleton EntityProjectRegistry.

    Discovery flow (discovery-first, model-select):
    1. Get bot PAT for Asana API access
    2. Run WorkspaceProjectRegistry discovery (get all projects with real names)
    3. Use model PRIMARY_PROJECT_GID to SELECT which discovered project maps to each entity type
    4. For remaining discovered projects, use name normalization as fallback
    5. Fail-fast on collision (multiple projects map to same entity type)

    Returns:
        Populated EntityProjectRegistry singleton.

    Raises:
        RuntimeError: If collision detected or discovery fails critically.
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.models.business import (
        AssetEditHolder,
        Business,
        Contact,
        Offer,
        Unit,
        UnitHolder,
        get_workspace_registry,
    )
    from autom8_asana.models.business.asset_edit import AssetEdit

    # Get bot PAT for S2S Asana access
    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        logger.warning(
            "entity_resolver_no_bot_pat",
            extra={
                "error": str(e),
                "detail": "Entity resolver will not be available without bot PAT",
            },
        )
        return EntityProjectRegistry.get_instance()

    workspace_gid = get_workspace_gid()

    if not workspace_gid:
        logger.warning(
            "entity_resolver_no_workspace",
            extra={
                "detail": "ASANA_WORKSPACE_GID not set, entity resolver discovery skipped",
            },
        )
        return EntityProjectRegistry.get_instance()

    # Model class -> entity_type mapping
    ENTITY_MODEL_MAP: dict[str, type] = {
        "unit": Unit,
        "unit_holder": UnitHolder,
        "business": Business,
        "offer": Offer,
        "contact": Contact,
        "asset_edit": AssetEdit,
        "asset_edit_holder": AssetEditHolder,
    }

    entity_registry = EntityProjectRegistry.get_instance()

    async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
        # --- Phase 1: Discovery (get all projects with real names) ---
        workspace_registry = get_workspace_registry()
        await workspace_registry.discover_async(client)

        discovered_projects = workspace_registry.get_all_projects()
        gid_to_name: dict[str, str] = {gid: name for name, gid in discovered_projects.items()}

        # --- Phase 2: Model-Select (PRIMARY_PROJECT_GID selects from discovered) ---
        registered_from_model: set[str] = set()
        model_gids_used: set[str] = set()

        for entity_type, model_class in ENTITY_MODEL_MAP.items():
            model_gid = getattr(model_class, "PRIMARY_PROJECT_GID", None)
            if model_gid:
                project_name = gid_to_name.get(model_gid)
                if project_name:
                    entity_registry.register(
                        entity_type=entity_type,
                        project_gid=model_gid,
                        project_name=project_name,
                    )
                    registered_from_model.add(entity_type)
                    model_gids_used.add(model_gid)
                    logger.info(
                        "entity_project_registered_from_model",
                        extra={
                            "entity_type": entity_type,
                            "project_gid": model_gid,
                            "project_name": project_name,
                            "model_class": model_class.__name__,
                            "source": "PRIMARY_PROJECT_GID",
                        },
                    )
                else:
                    entity_registry.register(
                        entity_type=entity_type,
                        project_gid=model_gid,
                        project_name=f"[gid:{model_gid}]",
                    )
                    registered_from_model.add(entity_type)
                    model_gids_used.add(model_gid)
                    logger.warning(
                        "entity_model_gid_not_in_discovery",
                        extra={
                            "entity_type": entity_type,
                            "model_gid": model_gid,
                            "model_class": model_class.__name__,
                            "detail": "Registered with placeholder name - project may not exist or bot lacks access",
                        },
                    )

        # --- Phase 3: Discovery Fallback (fill gaps via name normalization) ---
        ENTITY_TYPES: list[str] = list(ENTITY_MODEL_MAP.keys())

        for project_name, project_gid in discovered_projects.items():
            if project_gid in model_gids_used:
                continue

            matched_type = _match_entity_type(project_name, ENTITY_TYPES)
            if matched_type:
                if matched_type in registered_from_model:
                    existing_gid = entity_registry.get_project_gid(matched_type)
                    error_msg = (
                        f"Entity collision detected: '{project_name}' (GID {project_gid}) "
                        f"normalizes to entity_type '{matched_type}' which is already "
                        f"registered from model with GID {existing_gid}. "
                        f"Fix: Update _normalize_project_name() to handle this case."
                    )
                    logger.error(
                        "entity_collision_fail_fast",
                        extra={
                            "entity_type": matched_type,
                            "discovered_project": project_name,
                            "discovered_gid": project_gid,
                            "model_gid": existing_gid,
                        },
                    )
                    raise RuntimeError(error_msg)
                else:
                    entity_registry.register(
                        entity_type=matched_type,
                        project_gid=project_gid,
                        project_name=project_name,
                    )
                    logger.info(
                        "entity_project_registered_from_discovery",
                        extra={
                            "entity_type": matched_type,
                            "project_gid": project_gid,
                            "project_name": project_name,
                            "source": "discovery_fallback",
                        },
                    )

        # Log any entity types not found
        registered = set(entity_registry.get_all_entity_types())
        for entity_type in ENTITY_TYPES:
            if entity_type not in registered:
                logger.warning(
                    "entity_project_not_found",
                    extra={"entity_type": entity_type},
                )

        logger.info(
            "entity_resolver_discovery_complete",
            extra={
                "registered_types": entity_registry.get_all_entity_types(),
                "model_registered": list(registered_from_model),
                "discovery_registered": list(registered - registered_from_model),
                "is_ready": entity_registry.is_ready(),
            },
        )

    return entity_registry
