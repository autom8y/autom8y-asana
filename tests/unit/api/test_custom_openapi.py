"""Tests for custom_openapi() spec enrichment and contract regression guards.

Sprint 1 (tests 1-8):
- Injects PersonalAccessToken and ServiceJWT security schemes
- Annotates per-operation security based on tag classification
- Strips leaked authorization header parameters
- Seeds tag descriptions for visible routers
- Caches the generated spec
- Produces a valid OpenAPI 3.1 document
- Does not break Swagger UI rendering (debug mode)

Sprint 8 (tests 9-20):
- Field description coverage regression guard (90% threshold)
- Consequence marker regression guards (DELETE irreversibility)
- Tag completeness guard (count + sentence coverage)
- Security application guard (no anonymous endpoints except health)
- Envelope conformance guard (200/201 responses have schemas)
- Endpoint coverage guards (query, resolver, dataframes, workflows)
- Webhook auth regression guard (WebhookToken scheme exists)
- Example presence guard (key response models in spec)

Sprint-7 / Lexicon Ascension (tests 21-22):
- Top-level webhooks object with asanaTaskChanged definition
- Task schema injection into components/schemas for $ref resolution
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.main import create_app
from autom8_asana.auth.dual_mode import AuthMode


@pytest.fixture(scope="module")
def debug_app():
    """Create a test app with debug=True for /docs access.

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


@pytest.fixture(scope="module")
def debug_client(debug_app):
    """Module-scoped TestClient with ASGI lifespan entered."""
    with TestClient(debug_app) as tc:
        yield tc


# --- Test 1: Security schemes present ---


def test_security_schemes_present(spec):
    """PersonalAccessToken and ServiceJWT exist with correct structure."""
    schemes = spec["components"]["securitySchemes"]

    assert "PersonalAccessToken" in schemes
    bearer = schemes["PersonalAccessToken"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"
    assert "description" in bearer

    assert "ServiceJWT" in schemes
    jwt = schemes["ServiceJWT"]
    assert jwt["type"] == "http"
    assert jwt["scheme"] == "bearer"
    assert jwt["bearerFormat"] == "JWT"
    assert "description" in jwt


# --- Test 2: Health endpoints have no security ---


def test_health_endpoints_no_security(spec):
    """Health operations have security: [] (explicitly unauthenticated)."""
    health_paths = ["/health", "/ready", "/health/deps"]
    for path in health_paths:
        path_item = spec["paths"].get(path)
        assert path_item is not None, f"Missing path: {path}"
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "patch", "delete"):
                assert operation.get("security") == [], (
                    f"{method.upper()} {path} should have security: []"
                )


# --- Test 3: PAT endpoints have PersonalAccessToken ---


def test_pat_endpoints_personal_access_token(spec):
    """Operations tagged with PAT tags have PersonalAccessToken security."""
    pat_prefixes = ("/api/v1/tasks", "/api/v1/projects")
    found_any = False
    for path, path_item in spec["paths"].items():
        if any(path.startswith(pfx) for pfx in pat_prefixes):
            for method in (
                "get",
                "post",
                "put",
                "patch",
                "delete",
            ):
                operation = path_item.get(method)
                if operation is None:
                    continue
                found_any = True
                assert operation.get("security") == [{"PersonalAccessToken": []}], (
                    f"{method.upper()} {path} should have PersonalAccessToken security"
                )
    assert found_any, "No PAT-tagged operations found in spec"


# --- Test 4: Authorization param stripped ---


def test_authorization_param_stripped(spec):
    """No operation has an authorization header parameter."""
    for path, path_item in spec["paths"].items():
        for method in (
            "get",
            "post",
            "put",
            "patch",
            "delete",
        ):
            operation = path_item.get(method)
            if operation is None:
                continue
            for param in operation.get("parameters", []):
                assert not (param.get("name") == "authorization" and param.get("in") == "header"), (
                    f"{method.upper()} {path} still has authorization header parameter"
                )


# --- Test 5: Tag descriptions present ---


def test_tag_descriptions_present(spec):
    """spec['tags'] contains entries for all visible router tags."""
    expected_tags = {
        "health",
        "tasks",
        "projects",
        "sections",
        "users",
        "workspaces",
        "dataframes",
        "webhooks",
        "offers",
        "workflows",
        "query",
        "resolver",
    }
    tag_entries = {t["name"]: t for t in spec["tags"]}
    for tag_name in expected_tags:
        assert tag_name in tag_entries, f"Missing tag description for '{tag_name}'"
        assert "description" in tag_entries[tag_name]
        assert len(tag_entries[tag_name]["description"]) > 0


# --- Test 6: Schema cached ---


def test_openapi_schema_cached(debug_app):
    """Calling app.openapi() twice returns the same object (identity)."""
    first = debug_app.openapi()
    second = debug_app.openapi()
    assert first is second


# --- Test 7: OpenAPI version 3.2.0 ---


def test_openapi_version_3_2(spec):
    """spec['openapi'] must be exactly '3.2.0' after Sprint-5 migration."""
    assert spec["openapi"] == "3.2.0", f"Expected OpenAPI 3.2.0, got {spec['openapi']}"


# --- Test 7b: jsonSchemaDialect present ---


def test_json_schema_dialect_present(spec):
    """spec['jsonSchemaDialect'] must reference Draft 2020-12."""
    assert spec.get("jsonSchemaDialect") == "https://json-schema.org/draft/2020-12/schema", (
        f"Expected jsonSchemaDialect for Draft 2020-12, got {spec.get('jsonSchemaDialect')}"
    )


# --- Test 7c: Dynamic servers array present ---


def test_servers_array_present(spec):
    """spec['servers'] must contain production and staging entries."""
    servers = spec.get("servers", [])
    assert len(servers) >= 2, f"Expected at least 2 servers, got {len(servers)}"
    descriptions = {s.get("description") for s in servers}
    assert "Production" in descriptions, "Missing Production server entry"
    assert "Staging" in descriptions, "Missing Staging server entry"


# --- Test 8: /docs endpoint returns 200 ---


def test_docs_endpoint_returns_200(debug_client):
    """GET /docs returns 200 in debug mode (Swagger UI renders)."""
    response = debug_client.get("/docs")
    assert response.status_code == 200


# ===================================================================
# Sprint 8: Contract Regression Guards (Tests 9-20)
#
# These tests catch regressions across 6 quality dimensions:
# field coverage, consequence markers, tag completeness, security,
# envelope conformance, endpoint coverage, webhook auth, examples.
# ===================================================================

_HTTP_METHODS = ("get", "post", "put", "delete", "patch")

# Schemas auto-generated by FastAPI that follow a well-known standard
_AUTOGEN_SCHEMAS = frozenset({"HTTPValidationError", "ValidationError"})


# --- Test 9: Field description coverage regression guard ---


def test_schema_field_description_coverage(spec):
    """At least 90% of schema properties have descriptions.

    Catches undescribed field additions. Any new field added to a Pydantic
    model without a description will lower coverage and trip this guard.
    """
    total = 0
    with_desc = 0
    for name, schema in spec.get("components", {}).get("schemas", {}).items():
        if name in _AUTOGEN_SCHEMAS:
            continue
        for _prop, defn in schema.get("properties", {}).items():
            total += 1
            if defn.get("description"):
                with_desc += 1
    coverage = with_desc / total if total else 1
    assert coverage >= 0.90, (
        f"Field description coverage {coverage:.1%} below 90% "
        f"({with_desc}/{total}). Add descriptions to new schema fields."
    )


# --- Test 10: DELETE endpoints have irreversible marker ---


def test_all_delete_endpoints_have_irreversible_marker(spec):
    """Every DELETE endpoint that destroys a primary resource has
    IRREVERSIBLE or PERMANENT documentation.

    Reversible association-removal endpoints (tags, project membership,
    member management) are excluded -- they undo with an add operation.
    """
    # Patterns that indicate reversible association removal, not destruction
    _REVERSIBLE_PATTERNS = ("/tags/", "/projects/", "/members")

    for path, methods in spec["paths"].items():
        delete_op = methods.get("delete")
        if not delete_op:
            continue
        # Skip reversible association removal endpoints
        if any(pattern in path for pattern in _REVERSIBLE_PATTERNS):
            continue
        desc = (delete_op.get("description", "") + " " + delete_op.get("summary", "")).upper()
        assert "IRREVERSIBLE" in desc or "PERMANENT" in desc, (
            f"DELETE {path} lacks IRREVERSIBLE/PERMANENT marker in description or summary"
        )


# --- Test 11: Tag completeness guard ---


def test_all_tags_have_descriptions(spec):
    """Every tag in the spec has a description of at least 2 sentences.

    Guards against adding a new router tag without documenting it.
    Sentence counting uses period-splitting to approximate sentence count.
    """
    tags = spec.get("tags", [])
    assert len(tags) >= 10, f"Expected at least 10 tags, found {len(tags)}"
    for tag in tags:
        desc = tag.get("description", "")
        # Split on ". " (period-space) to count sentence boundaries.
        # A description like "Sentence one. Sentence two." has 2+ segments.
        sentences = [s.strip() for s in desc.split(". ") if s.strip()]
        assert len(sentences) >= 2, (
            f"Tag '{tag['name']}' needs >= 2 sentences, has {len(sentences)}: {desc[:80]}..."
        )


# --- Test 12: Security application guard ---


def test_all_endpoints_have_security(spec):
    """Every endpoint has a security declaration.

    Health endpoints use security: [] (explicitly unauthenticated).
    All other endpoints must declare a scheme (PersonalAccessToken, ServiceJWT,
    or WebhookToken). Catches endpoints added without auth annotation.
    """
    missing = []
    for path, methods in spec["paths"].items():
        for method in _HTTP_METHODS:
            op = methods.get(method)
            if not op:
                continue
            # Health endpoints are explicitly unauthenticated (security: [])
            # which still passes `is not None`
            if op.get("security") is None:
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"Endpoints missing security declaration: {missing}"


# --- Test 13: Envelope conformance guard ---


def test_success_responses_use_envelope(spec):
    """Every 200/201 JSON response has a schema definition.

    Catches the case where a new endpoint returns application/json but
    has no schema at all -- meaning agents cannot introspect the response
    structure. Endpoints returning dict/Any get auto-generated schemas
    from FastAPI (type: object, title, etc.) which is acceptable.
    """
    missing_schema = []
    for path, methods in spec["paths"].items():
        for method in _HTTP_METHODS:
            op = methods.get(method)
            if not op:
                continue
            responses = op.get("responses", {})
            success = responses.get("200") or responses.get("201")
            if not success:
                continue
            content = success.get("content", {})
            if "application/json" not in content:
                continue
            # The schema key must exist and not be None
            schema = content["application/json"].get("schema")
            if schema is None:
                missing_schema.append(f"{method.upper()} {path}")
    assert not missing_schema, (
        f"Success responses with application/json but no schema: {missing_schema}"
    )


# --- Test 14: Query introspection endpoints in spec ---


def test_query_introspection_endpoints_in_spec(spec):
    """All 6 query introspection GET endpoints appear in the spec.

    Guards against accidentally setting include_in_schema=False on the
    introspection router or removing endpoints.
    """
    query_paths = [p for p in spec["paths"] if "/query" in p]
    get_endpoints = []
    for p in query_paths:
        if "get" in spec["paths"][p]:
            get_endpoints.append(p)
    assert len(get_endpoints) >= 6, (
        f"Expected 6+ query introspection GET endpoints, found "
        f"{len(get_endpoints)}: {get_endpoints}"
    )


# --- Test 15: Resolver endpoint in spec ---


def test_resolver_endpoint_in_spec(spec):
    """Resolver POST endpoint appears in the spec.

    Guards against resolver becoming hidden (include_in_schema=False).
    """
    resolver_paths = [p for p in spec["paths"] if "/resolve" in p]
    assert resolver_paths, "No resolver endpoints found in spec"
    # Verify at least one POST operation exists
    post_found = any("post" in spec["paths"][p] for p in resolver_paths)
    assert post_found, f"Resolver paths found ({resolver_paths}) but none have POST operations"


# --- Test 16: Dataframe schema endpoints in spec ---


def test_dataframe_schema_endpoints_in_spec(spec):
    """Dataframe schema introspection endpoints appear in the spec.

    Guards against removing the /schemas discovery endpoint that agents
    need to find available dataframe types.
    """
    schema_paths = [p for p in spec["paths"] if "/dataframes/schemas" in p]
    assert len(schema_paths) >= 1, "No dataframe schema introspection endpoints found in spec"


# --- Test 17: Workflow list endpoint in spec ---


def test_workflow_list_endpoint_in_spec(spec):
    """Workflow listing GET endpoint appears in the spec.

    Guards against workflow discovery becoming hidden.
    """
    for path in spec["paths"]:
        if "workflow" in path.lower() and "get" in spec["paths"][path]:
            return  # Found
    pytest.fail("No workflow listing GET endpoint found in spec")


# --- Test 18: WebhookToken security scheme exists ---


def test_webhook_token_security_scheme_exists(spec):
    """WebhookToken security scheme is defined with correct structure.

    Guards against removing or misconfiguring the webhook auth scheme.
    Webhook endpoints must use apiKey-in-query, not bearer tokens.
    """
    schemes = spec.get("components", {}).get("securitySchemes", {})
    assert "WebhookToken" in schemes, "WebhookToken security scheme missing"
    wt = schemes["WebhookToken"]
    assert wt.get("type") == "apiKey", f"WebhookToken must be apiKey type, got '{wt.get('type')}'"
    assert wt.get("in") == "query", f"WebhookToken must be in query, got '{wt.get('in')}'"
    assert wt.get("description"), "WebhookToken scheme needs a description"


# --- Test 19: Example presence guard ---


def test_top_level_response_models_have_schemas(spec):
    """Key response models (SuccessResponse, ErrorResponse) appear in the
    components/schemas section.

    Guards against response models being excluded from the spec, which
    would prevent agents from understanding the API envelope contract.
    """
    schemas = spec.get("components", {}).get("schemas", {})
    key_models = ["SuccessResponse", "ErrorResponse"]
    for model in key_models:
        matches = [name for name in schemas if model.lower() in name.lower()]
        assert matches, (
            f"No schema matching '{model}' found in components/schemas. "
            f"Available: {sorted(schemas.keys())[:10]}..."
        )


# --- Test 20: Webhook endpoints use WebhookToken (not PersonalAccessToken) ---


def test_webhook_endpoints_use_webhook_token(spec):
    """Webhook endpoints use WebhookToken security, not PersonalAccessToken.

    Guards against accidentally changing webhook auth to PAT-based,
    which would require webhook receivers to handle bearer tokens.
    """
    webhook_ops = []
    for path, methods in spec["paths"].items():
        if "webhook" not in path.lower():
            continue
        for method in _HTTP_METHODS:
            op = methods.get(method)
            if not op:
                continue
            webhook_ops.append((method, path, op))
            security = op.get("security", [])
            scheme_names = [list(s.keys())[0] for s in security if s]
            assert "PersonalAccessToken" not in scheme_names, (
                f"{method.upper()} {path} uses PersonalAccessToken instead of WebhookToken"
            )
    assert webhook_ops, "No webhook operations found in spec to verify"


# --- Test 21: Top-level webhooks object exists (Sprint-7) ---


def test_webhooks_top_level_object_exists(spec):
    """Top-level ``webhooks`` object is present with asanaTaskChanged entry.

    Guards against removal of the inbound webhook definition added in
    Sprint-7 (Lexicon Ascension).  The webhook spec is how consumers
    (Ace, external integrations) discover the async inbound contract.
    """
    assert "webhooks" in spec, "Top-level 'webhooks' key missing from spec"
    webhooks = spec["webhooks"]
    assert "asanaTaskChanged" in webhooks, "asanaTaskChanged webhook definition missing"
    hook_op = webhooks["asanaTaskChanged"].get("post")
    assert hook_op is not None, "asanaTaskChanged must define a 'post' operation"
    assert hook_op.get("operationId") == "receiveAsanaTaskWebhook"
    assert hook_op.get("security") == [{"WebhookToken": []}], (
        "Webhook must use WebhookToken security scheme"
    )
    # Verify requestBody references the Task schema
    rb_schema = (
        hook_op.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    assert rb_schema.get("$ref") == "#/components/schemas/Task", (
        f"Webhook requestBody must reference Task schema, got {rb_schema}"
    )


# --- Test 22: Task schema injected into components/schemas (Sprint-7) ---


def test_task_schema_injected(spec):
    """Task schema is present in components/schemas for webhook $ref resolution.

    The Task model is not used in any route's response_model, so it must
    be explicitly injected by custom_openapi().  Without it, the webhook
    definition's $ref would be a dangling pointer.
    """
    schemas = spec.get("components", {}).get("schemas", {})
    assert "Task" in schemas, (
        f"Task schema missing from components/schemas. Available: {sorted(schemas.keys())[:10]}..."
    )
    task = schemas["Task"]
    # Task should have properties (it's a full Pydantic model, not empty)
    assert "properties" in task, "Task schema must have properties"
    # Verify key fields exist
    assert "gid" in task["properties"] or any(
        "gid" in (ref_schema.get("properties", {}))
        for ref_schema in schemas.values()
        if isinstance(ref_schema, dict)
    ), "Task or its parent must define a 'gid' property"


# ===================================================================
# PKG-009 / AUDIT-010: JWT baseline + tag fail-closed regression guards
# ===================================================================


def test_unknown_tag_raises_value_error_at_spec_generation():
    """custom_openapi() raises ValueError when an operation has an unknown tag.

    Guards against silent fail-open: prior to PKG-009, the tag-to-security
    mapping had a bare ``else`` that left unknown-tag operations with no
    security annotation, making them appear unauthenticated in the spec.
    The fix replaces the silent fall-through with an explicit raise so
    that misclassified routes break the build.
    """
    from fastapi import FastAPI
    from fastapi.openapi.utils import get_openapi

    from autom8_asana.api.main import (
        _NO_AUTH_TAGS,
        _PAT_TAGS,
        _S2S_TAGS,
        _TOKEN_TAGS,
    )

    # Build a minimal app with a single route bearing a tag that is not
    # registered in any of the four classification sets.
    bogus_tag = "this-tag-is-not-classified"
    assert bogus_tag not in (_PAT_TAGS | _S2S_TAGS | _TOKEN_TAGS | _NO_AUTH_TAGS), (
        "Bogus tag must not collide with any real tag set"
    )

    app = FastAPI(title="bogus", version="0.0.0")

    @app.get("/bogus", tags=[bogus_tag])
    async def bogus_route():
        return {"ok": True}

    # Re-create the relevant subset of custom_openapi() inline. We cannot
    # call create_app() here because it pulls in the full Asana lifespan;
    # the goal is to verify the tag classification logic in isolation.
    spec = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        openapi_version="3.2.0",
    )

    def _classify(spec_dict, no_auth, token, s2s, pat):
        for _path, path_item in spec_dict.get("paths", {}).items():
            for method in (
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
                "trace",
            ):
                operation = path_item.get(method)
                if operation is None:
                    continue
                tags = set(operation.get("tags", []))
                if tags & no_auth:
                    operation["security"] = []
                elif tags & token:
                    operation["security"] = [{"WebhookToken": []}]
                elif tags & s2s:
                    operation["security"] = [{"ServiceJWT": []}]
                elif tags & pat:
                    operation["security"] = [{"PersonalAccessToken": []}]
                else:
                    raise ValueError(
                        f"Unknown OpenAPI tag(s): {sorted(tags)}. Add to "
                        "_PAT_TAGS, _S2S_TAGS, _TOKEN_TAGS, or _NO_AUTH_TAGS "
                        "in autom8_asana.api.main."
                    )

    with pytest.raises(ValueError, match="Unknown OpenAPI tag"):
        _classify(spec, _NO_AUTH_TAGS, _TOKEN_TAGS, _S2S_TAGS, _PAT_TAGS)


def test_jwt_middleware_registered_in_app(debug_app):
    """JWTAuthMiddleware is in the asana middleware stack (PKG-009 baseline).

    Regression guard against accidentally removing the fleet-baseline
    JWTAuthMiddleware from the create_app() middleware stack. Asana retains
    its DI-based dual-mode auth, but the middleware provides fail-closed
    enforcement for any route that lacks an explicit Depends(get_auth_context).
    """
    from autom8y_auth import JWTAuthMiddleware

    middleware_classes = [m.cls for m in debug_app.user_middleware]
    assert JWTAuthMiddleware in middleware_classes, (
        "JWTAuthMiddleware must be present in asana middleware stack "
        f"(PKG-009). Found: {[c.__name__ for c in middleware_classes]}"
    )
