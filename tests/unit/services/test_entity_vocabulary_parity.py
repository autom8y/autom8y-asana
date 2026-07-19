"""Entity-vocabulary parity contract (G3, SAT-1 regression guard).

Born from the asana-mcp-v1 limb-(a) witness (2026-07-19): the introspection
surface (GET /v1/query/entities via query.introspection.list_entities)
advertised the seven pipeline entities while the execution surface
(POST /v1/query/{entity_type}/rows|aggregate via get_resolvable_entities)
rejected them with UNKNOWN_ENTITY_TYPE — a vocabulary split invisible to
per-surface tests. Evidence dossier:
.sos/wip/asana-mcp-v1.limb-a-witness-evidence-digest.md.

Contract (two-sided):
1. PARITY: every entity the introspection surface advertises is queryable by
   the execution surface (introspection vocabulary is a subset of the
   execution vocabulary; execution MAY additionally accept body-parameterized
   names such as "project"/"section" that introspection does not list).
2. TEETH: a truly-unknown entity type is still rejected, and the rejection
   carries the full execution vocabulary so callers can self-correct.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.query.introspection import list_entities
from autom8_asana.services.entity_service import EntityService
from autom8_asana.services.errors import UnknownEntityError
from autom8_asana.services.resolver import (
    EntityProjectRegistry,
    get_resolvable_entities,
)

PIPELINE_ENTITIES = {
    "process_sales",
    "process_outreach",
    "process_onboarding",
    "process_implementation",
    "process_month1",
    "process_retention",
    "process_reactivation",
}

# The pre-cure execution vocabulary — must remain resolvable (no regression).
PRE_CURE_VOCABULARY = {
    "asset_edit",
    "asset_edit_holder",
    "business",
    "contact",
    "offer",
    "project",
    "section",
    "unit",
}


@pytest.fixture(autouse=True)
def _reset_registries() -> None:
    """Singleton hygiene: parity runs against freshly-derived vocabularies."""
    SchemaRegistry.reset()
    EntityProjectRegistry.reset()
    yield
    SchemaRegistry.reset()
    EntityProjectRegistry.reset()


class TestIntrospectionExecutionParity:
    """Side 1 — the parity invariant that SAT-1 violated."""

    def test_introspection_vocabulary_subset_of_execution(self) -> None:
        """Every advertised entity type is queryable (the SAT-1 guard)."""
        advertised = {row["entity_type"] for row in list_entities()}
        executable = get_resolvable_entities()

        missing = advertised - executable
        assert not missing, (
            f"Introspection advertises entity types the execution surface "
            f"rejects (SAT-1 regression): {sorted(missing)}. "
            f"Execution vocabulary: {sorted(executable)}"
        )

    def test_all_pipeline_entities_resolvable(self) -> None:
        """The seven pipeline entities are queryable; the schema-holder parent
        'process' (no servable schema of its own) is not; the pre-cure
        vocabulary is preserved untouched."""
        executable = get_resolvable_entities()

        assert PIPELINE_ENTITIES <= executable, (
            f"Missing pipelines: {sorted(PIPELINE_ENTITIES - executable)}"
        )
        assert "process" not in executable
        assert PRE_CURE_VOCABULARY <= executable, (
            f"Pre-cure vocabulary regressed: "
            f"{sorted(PRE_CURE_VOCABULARY - executable)}"
        )

    def test_pascal_schema_key_resolves_shared_process_schema(self) -> None:
        """Field validation's to_pascal_case lookup lands on the real shared
        PROCESS_SCHEMA (not the '*' fallback) for every pipeline key."""
        registry = SchemaRegistry.get_instance()
        for pipeline in sorted(PIPELINE_ENTITIES):
            key = "".join(w.capitalize() for w in pipeline.split("_"))
            assert registry.get_schema(key).name == "process", (
                f"{key} did not resolve the shared process schema"
            )


class TestUnknownEntityTeeth:
    """Side 2 — the broken input is still rejected, diagnosably."""

    def test_unknown_entity_rejected_with_full_vocabulary(self) -> None:
        service = EntityService(
            entity_registry=get_registry(),
            project_registry=EntityProjectRegistry.get_instance(),
        )
        with patch.object(EntityService, "_acquire_bot_pat", return_value="test-pat"):
            with pytest.raises(UnknownEntityError) as exc_info:
                service.validate_entity_type("zz_definitely_unknown")

        err = exc_info.value
        assert err.available == sorted(get_resolvable_entities())
        # The rejection must carry the CURED vocabulary — this is the exact
        # recovery hint the limb-(a) agent never received (MCP-1 pairing).
        assert "process_sales" in err.available

    def test_process_entity_validates_with_registry_gid(self) -> None:
        """validate_entity_type resolves a pipeline entity end-to-end with the
        EntityRegistry-routed project GID (no body override needed)."""
        service = EntityService(
            entity_registry=get_registry(),
            project_registry=EntityProjectRegistry.get_instance(),
        )
        expected_gid = get_registry().get("process_sales").primary_project_gid
        assert expected_gid is not None

        with patch.object(EntityService, "_acquire_bot_pat", return_value="test-pat"):
            ctx = service.validate_entity_type("process_sales")

        assert ctx.entity_type == "process_sales"
        assert ctx.project_gid == expected_gid
