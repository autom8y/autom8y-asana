"""Thin, FleetQuery-shaped DISCOVERY tier (C1): list_entity_types + describe_entity.

These are the uniform discovery tools an agent uses to GROUND on the schema
before building predicates — limb-(a) steps 1-2 (list -> describe). Kept thin and
fleet-shaped per the two-tier grain ruling (C1); the rich per-satellite power
lives in the query tools.
"""

from __future__ import annotations

from typing import Any

from asana_mcp.context import SidecarContext
from asana_mcp.envelopes import unwrap_outer
from asana_mcp.tools._common import ensure_ready, get_json


async def list_entity_types_handler(ctx: SidecarContext) -> dict[str, Any]:
    """GET /v1/query/entities -> the discovery root."""
    await ensure_ready(ctx)
    entities = unwrap_outer(await get_json(ctx, "/v1/query/entities"))
    return {
        "entity_types": entities,  # [{entity_type, display_name, project_gid, category}]
        "count": len(entities) if isinstance(entities, list) else None,
        "hint": (
            "Call describe_entity(entity_type) next to get fields + relations, then "
            "query_rows / query_aggregate to answer the business question."
        ),
    }


async def describe_entity_handler(ctx: SidecarContext, entity_type: str) -> dict[str, Any]:
    """Compose /fields + /relations (+ best-effort /sections) for schema grounding."""
    await ensure_ready(ctx)
    fields = unwrap_outer(await get_json(ctx, f"/v1/query/{entity_type}/fields"))
    relations = unwrap_outer(await get_json(ctx, f"/v1/query/{entity_type}/relations"))
    # /sections is only defined for entity types with a SectionClassifier; a 404
    # there is non-fatal to schema grounding, so it is best-effort.
    sections: Any
    try:
        sections = unwrap_outer(await get_json(ctx, f"/v1/query/{entity_type}/sections"))
    except Exception:  # noqa: BLE001 — best-effort; absence is fine
        sections = None
    return {
        "entity_type": entity_type,
        "fields": fields,  # [{name, dtype, nullable, description}]
        "relations": relations,  # [{target, direction, default_join_key, cardinality, description}]
        "sections": sections,  # [{section_name, classification}] or None
    }


def register(mcp: Any, ctx: SidecarContext) -> None:
    """Mount-seam item 2: register(mcp, ctx). Thin adapter over the pure handlers."""

    @mcp.tool(
        name="list_entity_types",
        description=(
            "Discovery root: list the business entity types you can query (business, "
            "contact, offer, unit, process, ...). Each entry has entity_type, "
            "display_name, project_gid, category. Start here."
        ),
    )
    async def list_entity_types() -> dict[str, Any]:
        return await list_entity_types_handler(ctx)

    @mcp.tool(
        name="describe_entity",
        description=(
            "Schema grounding for one entity type: its fields (name, dtype, nullable, "
            "description), joinable relations, and sections. Use this to learn which "
            "columns you can filter and select in query_rows / query_aggregate."
        ),
    )
    async def describe_entity(entity_type: str) -> dict[str, Any]:
        return await describe_entity_handler(ctx, entity_type)
