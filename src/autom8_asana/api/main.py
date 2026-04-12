"""FastAPI application factory.

Per TDD-I5: This module is the thin app factory shell after decomposition.
Startup/shutdown logic lives in lifespan.py, initialization in startup.py,
and preload subsystem in preload/.

Per TDD-ASANA-SATELLITE:
- FR-SVC-001: FastAPI application factory with lifespan
- FR-SVC-002: Request ID middleware
- FR-SVC-003: Request logging middleware
- FR-SVC-004: CORS middleware with configurable origins
- FR-SVC-005: Service-level rate limiting via SlowAPI

Per ADR-ASANA-007:
- SDK client lifecycle is per-request (via dependencies)
- No persistent client state in app.state

Per TDD-SPRINT1-CUSTOM-OPENAPI:
- custom_openapi() post-processes the OpenAPI spec to inject dual-mode
  security schemes, per-operation security annotations, authorization
  parameter stripping, and tag descriptions.

Design Principles:
- Thin API layer that delegates to SDK
- Request tracing via X-Request-ID header
- Centralized error handling
- Structured JSON logging
"""

import os
from typing import Any

from autom8y_api_middleware import (
    CORSConfig,
    FleetAppConfig,
    JWTAuthConfig,
    RateLimitConfig,
    RouterMount,
    create_fleet_app,
)
from autom8y_log import get_logger
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette.middleware import Middleware

from .config import get_settings
from .errors import register_exception_handlers
from .lifespan import lifespan  # noqa: F401
from .rate_limit import limiter
from .routes import (
    admin_router,
    dataframes_router,
    entity_write_router,
    fleet_query_router_api_v1,
    fleet_query_router_v1,
    health_router,
    intake_create_router,
    intake_custom_fields_router,
    intake_resolve_router,
    internal_router,
    matching_router,
    projects_router,
    query_introspection_router,
    query_router,
    resolver_router,
    section_timelines_router,
    sections_router,
    tasks_router,
    users_router,
    webhooks_router,
    workflows_router,
    workspaces_router,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# OpenAPI security classification sets (ADR-SPRINT1-001: tag-based)
#
# When adding a new router, add its tag to the appropriate set below.
# If a tag is not in any set, its operations receive no security annotation
# in the spec (safe default: appears unauthenticated in documentation).
# ---------------------------------------------------------------------------

# Tags whose operations require PAT Bearer auth
_PAT_TAGS: frozenset[str] = frozenset(
    {
        "tasks",
        "projects",
        "sections",
        "users",
        "workspaces",
        "dataframes",
        "offers",
        "workflows",
    }
)

# Tags whose operations use URL token auth (query parameter)
_TOKEN_TAGS: frozenset[str] = frozenset({"webhooks"})

# Tags whose operations require S2S JWT auth
_S2S_TAGS: frozenset[str] = frozenset(
    {
        "resolver",
        "query",
        "admin",
        "internal",
        "entity-write",
        "intake-resolve",
        "intake-custom-fields",
        "intake-create",
        "matching",
    }
)

# Tags whose operations require no auth
_NO_AUTH_TAGS: frozenset[str] = frozenset({"health"})

# Tag descriptions for include_in_schema=True routers
_TAG_DESCRIPTIONS: dict[str, str] = {
    "health": (
        "Platform health probes. Three tiers: /health (liveness — always 200, "
        "no I/O), /ready (readiness — 503 while cache warms), and /health/deps "
        "(dependency probe — checks JWKS reachability and bot PAT configuration). "
        "No authentication required."
    ),
    "tasks": (
        "Full lifecycle management for Asana tasks. "
        "Supports CRUD operations, subtask and dependent enumeration, "
        "task duplication, tag management, section moves, assignee changes, "
        "and multi-project membership. "
        "Requires PAT Bearer authentication. "
        "List endpoints use cursor-based pagination."
    ),
    "projects": (
        "Manage Asana projects within a workspace. "
        "Supports CRUD operations, section listing, and member management "
        "(add/remove). "
        "Requires PAT Bearer authentication. "
        "List endpoints use cursor-based pagination."
    ),
    "sections": (
        "Manage sections within Asana projects. "
        "Sections organize tasks into swimlanes or workflow stages. "
        "Supports CRUD operations, adding tasks to sections, and "
        "reordering sections within a project. "
        "Requires PAT Bearer authentication."
    ),
    "users": (
        "Resolve and enumerate Asana users. "
        "Supports fetching the current authenticated user, looking up a "
        "user by GID, and listing all users in a workspace. "
        "Requires PAT Bearer authentication."
    ),
    "workspaces": (
        "Access Asana workspace information. "
        "Supports listing all workspaces accessible to the authenticated "
        "user and retrieving a single workspace by GID. "
        "Workspace GIDs are required by project and user list endpoints. "
        "Requires PAT Bearer authentication."
    ),
    "dataframes": (
        "Fetch Asana task data as structured DataFrames for analytical use. "
        "Schema-based extraction maps custom fields to typed columns "
        "(base, unit, contact, business, offer, asset_edit, asset_edit_holder). "
        "Use GET /api/v1/dataframes/schemas to discover available schemas and "
        "their column definitions. Supports JSON records (default) or "
        "Polars-serialized output via Accept header content negotiation. "
        "Requires PAT Bearer authentication."
    ),
    "webhooks": (
        "Receive inbound task notifications from Asana Rules actions. "
        "The /inbound endpoint accepts full task JSON payloads, verifies "
        "a URL token (timing-safe), and enqueues background processing "
        "for cache invalidation and dispatch. "
        "Returns 200 immediately to prevent Asana retries. "
        "Authentication via ?token= query parameter."
    ),
    "offers": (
        "Offer activity timeline reporting for the Business Offers project. "
        "Computes active_section_days and billable_section_days per offer "
        "by replaying Asana section history over a date range. "
        "Results are cached after first computation (warm path < 2s). "
        "Requires PAT Bearer authentication."
    ),
    "workflows": (
        "Invoke registered automation workflows against specific Asana entities. "
        "Use GET /api/v1/workflows to discover available workflow IDs before "
        "invoking. Supports dry-run mode for impact preview, per-workflow "
        "parameter overrides, and a 120-second execution timeout. "
        "Rate limited to 10 requests per minute. "
        "Every invocation is audit logged with caller context. "
        "Requires PAT Bearer authentication."
    ),
    "query": (
        "Schema introspection for the composable query engine. "
        "Discover queryable entity types, their fields, relations, sections, "
        "and data-source factories. Read-only introspection endpoints that "
        "enable agents to understand the data model without executing queries. "
        "Requires S2S JWT authentication."
    ),
    "resolver": (
        "Entity resolution service. Resolve business identifiers (phone, "
        "vertical, offer ID) to Asana task GIDs with metadata-rich responses "
        "including match confidence and available fields. Supports batch "
        "resolution and schema discovery for each entity type. "
        "Requires S2S JWT authentication."
    ),
}


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application with:
        - Fleet-standard middleware stack (via create_fleet_app)
        - IdempotencyMiddleware (extra_middleware)
        - Rate limiting via SlowAPI
        - Platform observability (metrics, tracing, log correlation)
        - Health route + all domain routers
        - Exception handlers
    """
    settings = get_settings()

    # --- Build IdempotencyMiddleware for extra_middleware ---
    from autom8_asana.api.middleware.idempotency import (
        DynamoDBIdempotencyStore,
        IdempotencyMiddleware,
        InMemoryIdempotencyStore,
        NoopIdempotencyStore,
    )

    idempotency_backend = os.environ.get("IDEMPOTENCY_STORE_BACKEND", "dynamodb")
    idempotency_store: (
        DynamoDBIdempotencyStore | InMemoryIdempotencyStore | NoopIdempotencyStore
    )
    if idempotency_backend == "dynamodb":
        table_name = os.environ.get("IDEMPOTENCY_TABLE_NAME", "autom8-idempotency-keys")
        table_region = os.environ.get("IDEMPOTENCY_TABLE_REGION", "us-east-1")
        try:
            idempotency_store = DynamoDBIdempotencyStore(
                table_name=table_name,
                region=table_region,
            )
            logger.info(
                "idempotency_store_configured",
                extra={
                    "backend": "dynamodb",
                    "table": table_name,
                    "region": table_region,
                },
            )
        except Exception as e:
            logger.warning(
                "idempotency_store_degraded",
                extra={"backend": "dynamodb", "error": str(e), "fallback": "noop"},
            )
            idempotency_store = NoopIdempotencyStore()
    elif idempotency_backend == "memory":
        idempotency_store = InMemoryIdempotencyStore()
        logger.info("idempotency_store_configured", extra={"backend": "memory"})
    elif idempotency_backend == "noop":
        idempotency_store = NoopIdempotencyStore()
        logger.info("idempotency_store_configured", extra={"backend": "noop"})
    else:
        logger.warning(
            "idempotency_store_unknown_backend",
            extra={"backend": idempotency_backend, "fallback": "noop"},
        )
        idempotency_store = NoopIdempotencyStore()

    # --- Build CORS config ---
    cors_config = None
    if settings.cors_origins_list:
        cors_config = CORSConfig(
            allow_origins=settings.cors_origins_list,
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Request-ID",
                "Idempotency-Key",
            ],
        )

    # --- JWT auth config ---
    # PKG-009 / AUDIT-010: Fleet baseline JWTAuthMiddleware.
    # PAT routes MUST be excluded -- the middleware validates JWTs only.
    jwt_auth_config = JWTAuthConfig(
        exclude_paths=[
            # Health / docs (standard fleet exclusions)
            "/health",
            "/ready",
            "/health/*",
            "/docs/*",
            "/redoc",
            "/openapi.json",
            "/metrics",
            # Webhooks: URL-token auth via ?token=, not Bearer
            "/api/v1/webhooks/*",
            # PAT-tag route trees (handled by dual-mode get_auth_context DI)
            "/api/v1/tasks/*",
            "/api/v1/projects/*",
            "/api/v1/sections/*",
            "/api/v1/users/*",
            "/api/v1/workspaces/*",
            "/api/v1/dataframes/*",
            "/api/v1/offers/*",
        ],
        # W3.5b-3-alpha-1 (fleet-api-sovereignty D3): opt in to ADR-07 §7.1
        # precedence (bypass_scope_enforcement -> business_id -> reject)
        # after successful signature validation. Excluded routes above
        # continue to bypass auth entirely.
        require_business_scope=True,
    )

    app = create_fleet_app(
        config=FleetAppConfig(
            title="autom8_asana API",
            description="REST API for Asana integration via autom8_asana SDK",
            version="0.1.0",
            service_name="asana",
            redoc_url="/redoc",
        ),
        routers=[
            RouterMount(router=health_router),
            RouterMount(router=users_router),
            RouterMount(router=workspaces_router),
            RouterMount(router=dataframes_router),
            RouterMount(router=tasks_router),
            RouterMount(router=projects_router),
            RouterMount(router=sections_router),
            RouterMount(router=internal_router),
            # Intake resolve endpoints BEFORE resolver_router so explicit paths
            # match before the wildcard /v1/resolve/{entity_type} pattern.
            RouterMount(router=intake_resolve_router),
            RouterMount(router=resolver_router),
            RouterMount(router=query_introspection_router),
            # S3 D4: fleet-canonical FleetQuery surface, dual-mounted
            # at /v1/query/entities and /api/v1/query/entities per
            # TDD-fleet-api-sovereignty-s3 section 7.4.3.
            #
            # IMPORTANT: fleet routes MUST mount BEFORE query_router so
            # that POST /v1/query/entities matches the fleet handler
            # rather than the legacy /v1/query/{entity_type} wildcard
            # (which would treat "entities" as a path parameter and
            # validate the body against the legacy QueryRequest model
            # without a `filters` field, surfacing a 422 extra_forbidden
            # error). FastAPI matches routes in registration order.
            RouterMount(router=fleet_query_router_v1),
            RouterMount(router=fleet_query_router_api_v1),
            RouterMount(router=query_router),
            RouterMount(router=admin_router),
            RouterMount(router=webhooks_router),
            RouterMount(router=workflows_router),
            RouterMount(router=entity_write_router),
            RouterMount(router=section_timelines_router),
            RouterMount(router=intake_custom_fields_router),
            RouterMount(router=intake_create_router),
            RouterMount(router=matching_router),
        ],
        lifespan=lifespan,
        cors=cors_config,
        jwt_auth=jwt_auth_config,
        rate_limit=RateLimitConfig(limiter=limiter),
        extra_middleware=[
            Middleware(IdempotencyMiddleware, store=idempotency_store),
        ],
    )

    # Register domain-specific Prometheus metrics on the default registry.
    try:
        import autom8_asana.api.metrics  # noqa: F401 - register domain metrics

        logger.info(
            "domain_metrics_registered",
            extra={"service_name": "asana"},
        )
    except ImportError:
        pass

    # --- Exception Handlers ---
    register_exception_handlers(app)

    # --- Custom OpenAPI spec enrichment (TDD-SPRINT1-CUSTOM-OPENAPI) ---
    def custom_openapi() -> dict[str, Any]:
        """Post-process the auto-generated OpenAPI spec.

        Enrichment steps:
        1. Inject ``PersonalAccessToken`` and ``ServiceJWT`` security schemes.
        2. Annotate per-operation security based on tag classification.
        3. Strip leaked ``authorization`` header parameters.
        4. Seed tag descriptions for Sprint 3.

        The function runs once per process lifetime; FastAPI caches the
        result on ``app.openapi_schema``.
        """
        if app.openapi_schema:
            return app.openapi_schema

        spec = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            openapi_version="3.2.0",
        )

        # OAS 3.2.0 metadata
        spec["jsonSchemaDialect"] = "https://json-schema.org/draft/2020-12/schema"
        spec["servers"] = [
            {"url": "https://asana.api.autom8y.io", "description": "Production"},
            {"url": "https://asana.staging.api.autom8y.io", "description": "Staging"},
        ]

        # 1. Inject security schemes
        components = spec.setdefault("components", {})
        components["securitySchemes"] = {
            "PersonalAccessToken": {
                "type": "http",
                "scheme": "bearer",
                "description": (
                    "Asana Personal Access Token (PAT). The token"
                    " is passed directly to the Asana API. Use for"
                    " standard resource endpoints (/api/v1/*)."
                ),
            },
            "ServiceJWT": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": (
                    "Service-to-service JWT issued by the autom8y"
                    " auth service. The service validates the JWT"
                    " against its JWKS endpoint and uses a bot PAT"
                    " for downstream Asana API calls. Use for"
                    " internal service endpoints (/v1/*)."
                ),
            },
            "WebhookToken": {
                "type": "apiKey",
                "in": "query",
                "name": "token",
                "description": (
                    "URL token for inbound webhook authentication."
                    " Passed as ?token=<secret> query parameter."
                    " Verified via timing-safe comparison against"
                    " ASANA_WEBHOOK_INBOUND_TOKEN."
                ),
            },
        }

        # 2-3. Per-operation security annotation + parameter stripping
        for _path, path_item in spec.get("paths", {}).items():
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

                # Inject 400 Bad Request (Mandate 3)
                # Documentation-based for pydantic validation and SDK GidValidationError mapping
                if "400" not in operation.get("responses", {}):
                    operation.setdefault("responses", {})["400"] = {
                        "description": "Bad Request (Validation Error)",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    }

                # Inject 401/403 (Mandate 3) - Core security status codes
                if "401" not in operation.get("responses", {}):
                    operation.setdefault("responses", {})["401"] = {
                        "description": "Unauthorized (Missing or Invalid Token)",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    }
                if "403" not in operation.get("responses", {}):
                    operation.setdefault("responses", {})["403"] = {
                        "description": "Forbidden (Insufficient Permissions)",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    }
                if "404" not in operation.get("responses", {}):
                    operation.setdefault("responses", {})["404"] = {
                        "description": "Not Found (Resource or Schema not found)",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    }

                tags = set(operation.get("tags", []))

                # Apply security annotation (ADR-SPRINT1-001)
                if tags & _NO_AUTH_TAGS:
                    operation["security"] = []
                elif tags & _TOKEN_TAGS:
                    operation["security"] = [{"WebhookToken": []}]
                elif tags & _S2S_TAGS:
                    operation["security"] = [{"ServiceJWT": []}]
                elif tags & _PAT_TAGS:
                    operation["security"] = [{"PersonalAccessToken": []}]
                else:
                    # PKG-009 / AUDIT-010: Fail closed on unknown tags. Any
                    # route whose tag is not classified into _NO_AUTH_TAGS,
                    # _TOKEN_TAGS, _S2S_TAGS, or _PAT_TAGS must explicitly
                    # opt in. Silent fall-through previously left the route
                    # documented as anonymous, which is a fail-open posture.
                    raise ValueError(
                        f"Unknown OpenAPI tag(s): {sorted(tags)}. Add to "
                        "_PAT_TAGS, _S2S_TAGS, _TOKEN_TAGS, or _NO_AUTH_TAGS "
                        "in autom8_asana.api.main."
                    )

                # Strip authorization header param (ADR-SPRINT1-002)
                if "parameters" in operation:
                    operation["parameters"] = [
                        p
                        for p in operation["parameters"]
                        if not (
                            p.get("name") == "authorization" and p.get("in") == "header"
                        )
                    ]
                    if not operation["parameters"]:
                        del operation["parameters"]

        # 4. Seed tag descriptions
        spec["tags"] = [
            {"name": tag, "description": desc}
            for tag, desc in _TAG_DESCRIPTIONS.items()
        ]

        # Sprint-6 (Lexicon Ascension): Annotate QUERY method candidates.
        # The following POST endpoints are semantically QUERY operations
        # (safe, idempotent, carry request body for complex filter/aggregate
        # expressions). They use POST due to httptools parser limitations,
        # missing FastAPI @app.query() decorator, and zero tooling support.
        #
        # These POST routes have include_in_schema=False (internal S2S
        # endpoints), so they do not appear in the generated spec paths.
        # We document them via a top-level extension and annotate any
        # visible query-related operations.
        #
        # RQ-1 verdict: HOLD.
        # See .ledge/spikes/lexicon-ascension-rnd-rq-findings.md
        _query_method_candidates = [
            {
                "path": "/v1/query/{entity_type}/rows",
                "method": "POST",
                "description": (
                    "Filtered row retrieval with composable predicates. "
                    "Zero side effects, idempotent."
                ),
                "in_schema": False,
            },
            {
                "path": "/v1/query/{entity_type}/aggregate",
                "method": "POST",
                "description": (
                    "Aggregate entity data with grouping and metric computation. "
                    "Zero side effects, idempotent."
                ),
                "in_schema": False,
            },
            {
                "path": "/v1/matching/query",
                "method": "POST",
                "description": (
                    "Matching query for scored business candidates. "
                    "Read-only against cached DataFrame, idempotent."
                ),
                "in_schema": False,
            },
        ]

        spec["x-query-method-candidates"] = _query_method_candidates
        spec["x-query-method-blocked-by"] = [
            "httptools parser does not support QUERY method",
            "IETF draft-ietf-httpbis-safe-method-w-body not yet RFC",
            "FastAPI has no @app.query() decorator",
            "Swagger UI and ReDoc cannot render QUERY operations",
        ]
        spec["x-query-method-ready-when"] = (
            "FastAPI ships @app.query() with httptools support"
        )

        # Annotate visible query introspection GET endpoints as safe reads.
        # These are already GET (inherently safe/idempotent) but the extension
        # marks them as part of the query subsystem for tooling discovery.
        for path_key, path_item in spec.get("paths", {}).items():
            if path_key.startswith("/v1/query"):
                for method_key in ("get", "post"):
                    op = path_item.get(method_key)
                    if op is not None:
                        op["x-idempotent"] = True
                        op["x-safe"] = True

        # 6. Inject inbound webhook definition (Sprint-7: Lexicon Ascension)
        #
        # The Task model is not referenced by any route's response_model (the
        # webhook endpoint parses raw JSON), so its schema is absent from the
        # auto-generated spec.  We generate it from the Pydantic model and
        # inject it into components/schemas, then reference it from the
        # top-level ``webhooks`` object per OpenAPI 3.1+/3.2.0.
        from autom8_asana.models.task import Task as _TaskModel

        task_schema = _TaskModel.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )

        # Extract $defs (nested models like NameGid, AsanaResource) and merge
        # into components/schemas so $ref pointers resolve correctly.
        task_defs = task_schema.pop("$defs", {})
        for def_name, def_schema in task_defs.items():
            components.setdefault("schemas", {})[def_name] = def_schema

        # Register the Task schema itself (without $defs, which are now
        # top-level in components/schemas).
        components.setdefault("schemas", {})["Task"] = task_schema

        # 7. Inject shared registry types required by fleet schema governance
        #
        # Routes use SuccessResponse[T] as parametrized generics, so FastAPI
        # generates schema names like "SuccessResponse_list_AsanaResource__"
        # but NOT the base SuccessResponse type.  ErrorResponse / ErrorDetail
        # may already appear via error_responses.py, but we inject all three
        # unconditionally so the fleet validation gate always passes.
        from autom8_asana.api.models import (
            ErrorDetail,
            ErrorResponse,
            SuccessResponse,
        )

        for _registry_model in (SuccessResponse, ErrorResponse, ErrorDetail):
            _schema = _registry_model.model_json_schema(
                ref_template="#/components/schemas/{model}"
            )
            _defs = _schema.pop("$defs", {})
            for _def_name, _def_schema in _defs.items():
                components.setdefault("schemas", {})[_def_name] = _def_schema
            components.setdefault("schemas", {})[_registry_model.__name__] = _schema

        spec["webhooks"] = {
            "asanaTaskChanged": {
                "post": {
                    "summary": "Asana task change notification",
                    "description": (
                        "Received when an Asana Rules action fires on task "
                        "mutation. Payload is a complete Asana task JSON "
                        "object. Authentication is via URL token query "
                        "parameter."
                    ),
                    "operationId": "receiveAsanaTaskWebhook",
                    "tags": ["webhooks"],
                    "security": [{"WebhookToken": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Task"}
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Webhook received and acknowledged"},
                        "401": {"description": "Invalid webhook token"},
                        "422": {"description": "Invalid payload"},
                    },
                }
            }
        }

        app.openapi_schema = spec
        return spec

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app


# Allow running directly with uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "autom8_asana.api.main:create_app",
        host="0.0.0.0",
        port=8000,
        factory=True,
        reload=True,
    )
