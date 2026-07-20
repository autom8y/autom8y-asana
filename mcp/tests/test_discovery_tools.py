"""Thin discovery tier (C1): list_entity_types + describe_entity."""

from __future__ import annotations

from asana_mcp.tools.discovery import describe_entity_handler, list_entity_types_handler


async def test_list_entity_types(fake_ctx):
    result = await list_entity_types_handler(fake_ctx)
    assert result["count"] == 2
    assert {e["entity_type"] for e in result["entity_types"]} == {"offer", "unit"}
    assert result["entity_types"][0]["project_gid"] == "1200653012566782"
    assert "describe_entity" in result["hint"]


async def test_describe_entity_composes_fields_relations_sections(fake_ctx):
    result = await describe_entity_handler(fake_ctx, "offer")
    assert result["entity_type"] == "offer"
    # schema grounding the LLM needs to build predicates
    assert {f["name"] for f in result["fields"]} >= {"office_phone", "vertical"}
    assert result["relations"][0]["target"] == "unit"
    assert {s["section_name"] for s in result["sections"]} == {"active", "inactive"}
