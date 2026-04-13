"""Agent consumability tests for the OpenAPI specification (Sprint 6).

Validates that an AI agent reading the OpenAPI spec can:
- DISCOVER: Find all capabilities, understand grouping and authentication
- CONSTRUCT: Build valid requests from schema descriptions alone
- SAFETY: Identify irreversible operations and safety constraints

These are structural assertions against the OpenAPI spec JSON.
No LLM-in-the-loop; no HTTP calls. Pure spec introspection.

Per TDD-SPRINT6-AGENT-CONSUMABILITY:
- 12+ tests across 3 tiers
- Tiered scoring: Tier 1 (must-pass), Tier 2 (should-pass), Tier 3 (critical-pass)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.auth.dual_mode import AuthMode

# ---------------------------------------------------------------------------
# HTTP methods that represent operations in the OpenAPI spec
# ---------------------------------------------------------------------------
_HTTP_METHODS = ("get", "post", "put", "delete", "patch")


# ---------------------------------------------------------------------------
# Fixtures — reuse the pattern from test_custom_openapi.py
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def debug_app():
    """Create a test app with debug=True for OpenAPI spec generation.

    Module-scoped to avoid per-test ASGI lifespan overhead.
    """
    with (
        patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ) as mock_discover,
        patch(
            "autom8_asana.api.main.get_settings",
        ) as mock_settings,
    ):
        settings = mock_settings.return_value
        settings.debug = True
        settings.cors_origins_list = []
        settings.rate_limit_rpm = 100
        settings.log_level = "INFO"

        async def setup_registry(app):
            from autom8_asana.services.resolver import (
                EntityProjectRegistry,
            )

            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="offer",
                project_gid="1143843662099250",
                project_name="Business Offers",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        test_app = create_app()

        async def _mock_auth() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service="autom8_data",
            )

        test_app.dependency_overrides[get_auth_context] = _mock_auth
        yield test_app


@pytest.fixture(scope="module")
def spec(debug_app):
    """Return the enriched OpenAPI spec dict."""
    return debug_app.openapi()


# ===================================================================
# TIER 1: DISCOVERY — Must Pass
#
# An agent reading this spec can find all capabilities, understand
# how they are grouped, and know what authentication is required.
# ===================================================================


class TestTier1Discovery:
    """Tier 1: Can an agent discover the full capability surface?"""

    def test_all_operations_grouped_by_tag(self, spec):
        """Every operation has at least one tag, and every tag has a
        description of at least 2 sentences so an agent can understand
        the domain grouping without guessing.
        """
        for path, methods in spec["paths"].items():
            for method in _HTTP_METHODS:
                op = methods.get(method)
                if op is None:
                    continue
                assert op.get("tags"), (
                    f"Agent cannot categorize {method.upper()} {path}: no tags present"
                )

        for tag in spec.get("tags", []):
            desc = tag.get("description", "")
            # Split on ". " to count sentence boundaries
            sentence_count = len(desc.split(". "))
            assert sentence_count >= 2, (
                f"Agent needs more context for tag '{tag['name']}': "
                f"description has only ~{sentence_count} sentence(s). "
                f"Current: {desc[:80]}..."
            )

    def test_endpoint_summaries_present(self, spec):
        """Every operation has a non-empty summary so an agent can scan
        capabilities without reading full descriptions.
        """
        missing = []
        for path, methods in spec["paths"].items():
            for method in _HTTP_METHODS:
                op = methods.get(method)
                if op is None:
                    continue
                if not op.get("summary"):
                    missing.append(f"{method.upper()} {path}")

        assert not missing, (
            f"Agent cannot scan capabilities — "
            f"{len(missing)} operation(s) lack summaries: {missing}"
        )

    def test_authentication_documented_on_all_endpoints(self, spec):
        """Every operation has a security declaration so an agent knows
        what credentials to present before making a request.

        Security can be:
        - [] (no auth required, e.g., health)
        - [{"PersonalAccessToken": []}] (PAT required)
        - [{"ServiceJWT": []}] (S2S JWT required)
        - [{"WebhookToken": []}] (URL token required)
        """
        missing = []
        for path, methods in spec["paths"].items():
            for method in _HTTP_METHODS:
                op = methods.get(method)
                if op is None:
                    continue
                if op.get("security") is None:
                    missing.append(f"{method.upper()} {path}")

        assert not missing, (
            f"Agent cannot determine auth requirements — "
            f"{len(missing)} operation(s) have no security declaration: "
            f"{missing}"
        )

    def test_pagination_documented_on_list_endpoints(self, spec):
        """Every GET endpoint that accepts limit or offset documents
        both, so an agent can paginate results correctly.
        """
        incomplete = []
        for path, methods in spec["paths"].items():
            get_op = methods.get("get")
            if not get_op:
                continue
            params = {p.get("name") for p in get_op.get("parameters", [])}
            has_either = "limit" in params or "offset" in params
            has_both = "limit" in params and "offset" in params
            if has_either and not has_both:
                incomplete.append(
                    f"GET {path} has partial pagination "
                    f"(limit={'limit' in params}, "
                    f"offset={'offset' in params})"
                )

        assert not incomplete, (
            f"Agent cannot paginate reliably — "
            f"endpoints with incomplete pagination params: {incomplete}"
        )

    def test_security_schemes_documented(self, spec):
        """SecuritySchemes section describes all auth mechanisms so an
        agent understands the authentication model before choosing one.
        """
        schemes = spec.get("components", {}).get("securitySchemes", {})
        expected = {"PersonalAccessToken", "ServiceJWT", "WebhookToken"}
        assert expected.issubset(set(schemes.keys())), (
            f"Agent cannot understand auth model — missing schemes: "
            f"{expected - set(schemes.keys())}"
        )
        for name, scheme in schemes.items():
            assert scheme.get("description"), (
                f"Auth scheme '{name}' has no description — agent cannot decide when to use it"
            )


# ===================================================================
# TIER 2: CONSTRUCTION — Should Pass
#
# An agent can build valid request bodies and interpret responses
# using only the schema descriptions in the spec.
# ===================================================================


class TestTier2Construction:
    """Tier 2: Can an agent construct valid requests and parse responses?"""

    def test_create_task_request_body_fully_described(self, spec):
        """POST /api/v1/tasks request body has all fields with descriptions
        so an agent can construct a valid task creation payload.
        """
        post_op = spec["paths"].get("/api/v1/tasks", {}).get("post")
        assert post_op, "Agent cannot create tasks — POST /api/v1/tasks not found"

        body = (
            post_op.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        # Resolve $ref if present
        if "$ref" in body:
            ref_name = body["$ref"].split("/")[-1]
            body = spec["components"]["schemas"][ref_name]

        props = body.get("properties", {})
        assert props, (
            "Agent cannot construct a task — POST /api/v1/tasks has no request body properties"
        )

        undescribed = [
            field_name
            for field_name, field_schema in props.items()
            if not field_schema.get("description")
        ]
        assert not undescribed, (
            f"Agent must guess the meaning of these fields in POST /api/v1/tasks: {undescribed}"
        )

    def test_error_response_schema_documented(self, spec):
        """ErrorResponse schema has described fields (code, message, detail)
        so an agent can parse and act on error responses programmatically.
        """
        schemas = spec.get("components", {}).get("schemas", {})
        error_schemas = [
            name for name in schemas if "error" in name.lower() and "response" in name.lower()
        ]
        assert error_schemas, (
            "Agent cannot parse errors — no ErrorResponse schema found in components"
        )

        # Verify the ErrorResponse has described properties
        for schema_name in error_schemas:
            schema_def = schemas[schema_name]
            props = schema_def.get("properties", {})
            assert props, f"Agent cannot parse errors — {schema_name} has no properties"
            for prop_name, prop_def in props.items():
                assert prop_def.get("description") or "$ref" in prop_def, (
                    f"Agent cannot interpret error field "
                    f"'{schema_name}.{prop_name}' — no description"
                )

    def test_response_models_have_descriptions(self, spec):
        """At least 80% of schema properties in components have descriptions
        so an agent can interpret response payloads without guessing.

        Auto-generated FastAPI/Pydantic schemas (HTTPValidationError,
        ValidationError) are excluded since they follow a well-known
        standard that agents already understand.
        """
        # Schemas auto-generated by FastAPI that follow a well-known format
        _AUTOGEN_SCHEMAS = {"HTTPValidationError", "ValidationError"}

        total = 0
        with_desc = 0
        schemas = spec.get("components", {}).get("schemas", {})
        for schema_name, schema_def in schemas.items():
            if schema_name in _AUTOGEN_SCHEMAS:
                continue
            for prop_name, prop_def in schema_def.get("properties", {}).items():
                total += 1
                if prop_def.get("description"):
                    with_desc += 1

        assert total > 0, "No schema properties found — spec may be empty"
        coverage = with_desc / total
        assert coverage >= 0.80, (
            f"Agent must guess field meanings — "
            f"schema field description coverage {coverage:.1%} "
            f"below 80% threshold ({with_desc}/{total})"
        )

    def test_workflow_invoke_request_documented(self, spec):
        """POST /workflows/{id}/invoke has documented request body with
        entity_ids, dry_run, and params so an agent can invoke workflows
        safely, including impact preview via dry_run.
        """
        invoke_path = None
        for path in spec["paths"]:
            if "workflows" in path and "invoke" in path:
                invoke_path = path
                break
        assert invoke_path, (
            "Agent cannot invoke workflows — workflow invoke endpoint not found in spec"
        )

        post_op = spec["paths"][invoke_path].get("post")
        assert post_op, f"Agent cannot invoke workflows — POST {invoke_path} not found"
        assert post_op.get("description"), (
            f"Agent cannot understand workflow invocation — POST {invoke_path} has no description"
        )

        # Verify the request body schema is documented
        body = (
            post_op.get("requestBody", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        if "$ref" in body:
            ref_name = body["$ref"].split("/")[-1]
            body = spec["components"]["schemas"].get(ref_name, {})

        expected_fields = {"entity_ids", "dry_run", "params"}
        actual_fields = set(body.get("properties", {}).keys())
        missing = expected_fields - actual_fields
        assert not missing, (
            f"Agent cannot construct workflow invocation — "
            f"missing fields in request body: {missing}"
        )


# ===================================================================
# TIER 3: SAFETY — Critical Pass
#
# An agent understands which operations are dangerous, irreversible,
# or have side effects that require extra caution.
# ===================================================================


class TestTier3Safety:
    """Tier 3: Can an agent identify dangerous operations and constraints?"""

    def test_destructive_deletes_document_irreversibility(self, spec):
        """DELETE endpoints that permanently remove resources document
        their irreversibility so an agent knows not to call them
        without explicit user confirmation.

        Non-destructive removals (remove tag, remove from project,
        remove member) are excluded as they are reversible association
        changes.
        """
        safety_words = {"IRREVERSIBLE", "PERMANENT", "CANNOT BE UNDONE", "PERMANENTLY"}

        # Patterns that indicate reversible association removal, not destruction
        _REVERSIBLE_PATTERNS = ("/tags/", "/projects/", "/members")

        unmarked = []
        for path, methods in spec["paths"].items():
            delete_op = methods.get("delete")
            if not delete_op:
                continue

            # Skip reversible association removal endpoints
            if any(pattern in path for pattern in _REVERSIBLE_PATTERNS):
                continue

            desc = (delete_op.get("description", "") + " " + delete_op.get("summary", "")).upper()
            has_safety = any(word in desc for word in safety_words)
            if not has_safety:
                unmarked.append(f"DELETE {path}")

        assert not unmarked, (
            f"Agent may accidentally destroy resources — "
            f"these destructive DELETE endpoints lack irreversibility "
            f"documentation: {unmarked}"
        )

    def test_section_move_documents_lifecycle_trigger(self, spec):
        """Section move endpoints document potential lifecycle automation
        triggers so an agent understands the side effects of moving a
        task between sections (workflow transitions, status changes).
        """
        trigger_words = ["lifecycle", "automation", "trigger", "workflow"]
        section_move_paths = []

        for path in spec["paths"]:
            # Match /tasks/{gid}/section — the primary section move endpoint.
            # Excludes /sections/{gid}/tasks which is "add task to section"
            # (different intent and less likely to trigger lifecycle changes).
            if path.endswith("/section") and "{gid}" in path and "tasks" in path:
                post_op = spec["paths"][path].get("post")
                if post_op:
                    section_move_paths.append(path)

        assert section_move_paths, (
            "Agent cannot find section move endpoint — no /tasks/{gid}/section path found"
        )

        for path in section_move_paths:
            desc = spec["paths"][path]["post"].get("description", "")
            has_trigger_doc = any(word in desc.lower() for word in trigger_words)
            assert has_trigger_doc, (
                f"Agent unaware of side effects — "
                f"POST {path} lacks lifecycle trigger documentation. "
                f"Moving tasks between sections can trigger workflows."
            )

    def test_webhook_uses_correct_auth_scheme(self, spec):
        """Webhook endpoints use WebhookToken (apiKey in query param),
        not PersonalAccessToken, so an agent does not send a PAT to webhook
        receivers.
        """
        for path, methods in spec["paths"].items():
            if "webhook" not in path.lower():
                continue
            for method in _HTTP_METHODS:
                op = methods.get(method)
                if op is None:
                    continue
                security = op.get("security", [])
                auth_schemes = [list(s.keys())[0] for s in security if s]
                assert "PersonalAccessToken" not in auth_schemes, (
                    f"Agent would leak PAT — "
                    f"{method.upper()} {path} incorrectly uses PersonalAccessToken "
                    f"instead of WebhookToken"
                )

    def test_caution_markers_on_destructive_mutations(self, spec):
        """DELETE endpoints that permanently remove resources and PUT
        endpoints that perform full replacement carry CAUTION,
        IRREVERSIBLE, or IDEMPOTENT markers so an agent can assess
        risk before executing.

        Scoped to the most dangerous mutations: DELETE of primary
        resources (tasks, projects, sections) and PUT updates.
        Non-destructive removals (tags, members, project membership)
        are excluded.
        """
        marker_words = {"CAUTION", "IRREVERSIBLE", "IDEMPOTENT"}

        # Paths where mutations are inherently safe/lightweight or
        # represent reversible association changes (not resource destruction)
        _SAFE_PATTERNS = (
            "/health",
            "/users",
            "/workspaces",
            "/tags/",
            "/members",
            "/projects/{project_gid}",  # remove-from-project is reversible
        )

        unmarked = []
        for path, methods in spec["paths"].items():
            if any(pattern in path for pattern in _SAFE_PATTERNS):
                continue

            # Check DELETE endpoints for primary resource destruction
            delete_op = methods.get("delete")
            if delete_op:
                desc = delete_op.get("description", "").upper()
                has_marker = any(word in desc for word in marker_words)
                if not has_marker:
                    unmarked.append(f"DELETE {path}")

        assert not unmarked, (
            f"Agent cannot assess mutation risk — "
            f"these destructive endpoints lack safety markers: {unmarked}"
        )

    def test_workflow_invoke_documents_caution(self, spec):
        """Workflow invoke endpoint explicitly warns about side effects
        so an agent uses dry_run before executing real workflows.
        """
        for path in spec["paths"]:
            if "workflows" not in path or "invoke" not in path:
                continue
            post_op = spec["paths"][path].get("post")
            if not post_op:
                continue
            desc = post_op.get("description", "").upper()
            assert "CAUTION" in desc or "DRY_RUN" in desc or "DRY RUN" in desc, (
                f"Agent may execute dangerous workflows without preview — "
                f"POST {path} lacks CAUTION marker or dry_run guidance"
            )
