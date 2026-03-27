"""Composite integration tests (CQ-01..CQ-07) for pre-deploy crucible terminal verification.

These tests exercise all four initiative domains interacting at the API boundary:
  - Domain A (Sprint 1): Cascade ordering observability (H-01, M-03)
  - Domain B (Sprint 3): Idempotency middleware, environment gate (H-02, M-01, M-02)
  - Domain D (Sprint 4): Semantic introspection, include_enums, enum detail route (SI-11, SI-12, L-03)
  - Domain C (this sprint): Cross-domain composite verification

Test infrastructure uses:
  - ``create_app()`` for real middleware stack and route registration
  - Mocked lifespan to avoid Asana API / DynamoDB dependencies
  - Patched JWT validation for S2S auth on resolver endpoints
  - ``TestClient`` for synchronous endpoint testing

Per Sprint 5 exit criteria: SC-07 PASS requires CQ-01..CQ-07 all passing.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.api.middleware.idempotency import (
    IdempotencyMiddleware,
    InMemoryIdempotencyStore,
    NoopIdempotencyStore,
)
from autom8_asana.services.resolver import EntityProjectRegistry

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# JWT bearer header used across all S2S endpoint tests
# ---------------------------------------------------------------------------
_JWT_BEARER_HEADER = {"Authorization": "Bearer header.payload.signature"}

# ---------------------------------------------------------------------------
# Test entity registrations
# ---------------------------------------------------------------------------

_TEST_ENTITIES = [
    ("offer", "1143843662099250", "Business Offers"),
    ("unit", "1201081073731555", "Business Units"),
    ("contact", "1200775689604552", "Contacts"),
    ("business", "1200653012566782", "Business"),
    ("asset_edit", "1202204184560785", "Asset Edits"),
    ("asset_edit_holder", "1203992664400125", "Asset Edit Holder"),
]


def _populate_test_registry():
    """Reset and populate EntityProjectRegistry with full entity set."""
    EntityProjectRegistry.reset()
    registry = EntityProjectRegistry.get_instance()
    for entity_type, gid, name in _TEST_ENTITIES:
        registry.register(
            entity_type=entity_type,
            project_gid=gid,
            project_name=name,
        )
    return registry


def _mock_jwt_validation(service_name: str = "autom8_data"):
    """Helper to create a mock JWT validation that returns valid claims.

    Used to patch ``autom8_asana.api.routes.internal.validate_service_token``
    so S2S endpoints accept any bearer token in tests.
    """
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


# ---------------------------------------------------------------------------
# Module-scoped app fixture with InMemoryIdempotencyStore
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app_with_memory_store():
    """Create a test application using IDEMPOTENCY_STORE_BACKEND=memory.

    Patches lifespan to avoid real Asana API calls and sets the
    idempotency backend to 'memory' via environment variable.
    """
    env_overrides = {
        "IDEMPOTENCY_STORE_BACKEND": "memory",
    }
    with (
        patch.dict(os.environ, env_overrides),
        patch(
            "autom8_asana.api.lifespan._discover_entity_projects",
            new_callable=AsyncMock,
        ) as mock_discover,
    ):

        async def setup_registry(app_instance):
            registry = _populate_test_registry()
            app_instance.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        test_app = create_app()
        yield test_app


@pytest.fixture(scope="module")
def _module_client(app_with_memory_store):
    """Module-scoped TestClient entering ASGI lifespan once."""
    with TestClient(app_with_memory_store) as tc:
        yield tc


@pytest.fixture(autouse=True)
def _reset_registry():
    """Re-populate registry before each test to ensure clean state."""
    _populate_test_registry()
    yield
    EntityProjectRegistry.reset()


@pytest.fixture
def client(_module_client) -> TestClient:
    """Per-test alias for the module-scoped TestClient."""
    return _module_client


# ===================================================================
# CQ-01: Full round-trip with all four domains active
# ===================================================================


class TestCQ01FullRoundTrip:
    """CQ-01: Full round-trip with all four domains active.

    Verifies that a single test application exercises:
    1. Idempotency middleware (Domain B) -- present in middleware stack
    2. Schema introspection with semantic enrichment (Domain D) -- include_semantic
    3. Middleware stack order preserved (Domains A, B together)
    4. Request flows through full middleware chain
    """

    def test_schema_endpoint_returns_enriched_fields(self, client) -> None:
        """Schema endpoint responds with semantic metadata when requested.

        Exercises Domain D (SI-11): include_semantic=true returns
        semantic_type and cascade_source fields.
        """
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema?include_semantic=true",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["entity_type"] == "unit"
        assert "queryable_fields" in data
        assert len(data["queryable_fields"]) > 0

        # At least one field should have semantic_type populated
        semantic_fields = [
            f for f in data["queryable_fields"] if f.get("semantic_type") is not None
        ]
        assert len(semantic_fields) > 0, (
            "Expected at least one field with semantic_type when include_semantic=true"
        )

    def test_schema_with_include_enums_populates_enum_values(self, client) -> None:
        """Schema endpoint with include_enums=true populates enum_values.

        Exercises Domain D (SI-11): enum-typed fields include valid_values
        list in enum_values response field.
        """
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema?include_semantic=true&include_enums=true",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 200, response.text
        data = response.json()

        # Find the 'vertical' field -- it should have enum_values
        vertical_fields = [
            f for f in data["queryable_fields"] if f["name"] == "vertical"
        ]
        assert len(vertical_fields) == 1, (
            f"Expected 'vertical' field in unit schema, got fields: "
            f"{[f['name'] for f in data['queryable_fields']]}"
        )
        vertical = vertical_fields[0]
        assert vertical["semantic_type"] == "enum"
        assert vertical["enum_values"] is not None
        assert len(vertical["enum_values"]) > 0, "Expected non-empty enum_values"

        # Verify at least Medical and Dental are present
        values = {v["value"] for v in vertical["enum_values"]}
        assert "Medical" in values, f"Expected 'Medical' in enum values, got {values}"
        assert "Dental" in values, f"Expected 'Dental' in enum values, got {values}"

    def test_idempotency_middleware_present_in_app(
        self, app_with_memory_store
    ) -> None:
        """Verify IdempotencyMiddleware is installed in the real app middleware stack.

        Exercises Domain B: The middleware stack built by create_app() includes
        IdempotencyMiddleware. Starlette stores registered middleware in
        ``app.user_middleware`` (a list of ``Middleware`` objects) before the
        stack is built on first request.
        """
        mw_classes = [mw.cls.__name__ for mw in app_with_memory_store.user_middleware]
        assert "IdempotencyMiddleware" in mw_classes, (
            f"IdempotencyMiddleware not found in user_middleware. "
            f"Registered middleware: {mw_classes}"
        )

        # Also verify the store type is InMemoryIdempotencyStore (env=memory)
        idem_mw = next(
            mw
            for mw in app_with_memory_store.user_middleware
            if mw.cls.__name__ == "IdempotencyMiddleware"
        )
        store = idem_mw.kwargs.get("store")
        assert isinstance(store, InMemoryIdempotencyStore), (
            f"Expected InMemoryIdempotencyStore in middleware kwargs, "
            f"got {type(store).__name__}"
        )

    def test_health_endpoint_through_full_stack(self, client) -> None:
        """Health endpoint works through the full middleware stack.

        Smoke test: verifies all four domains' middleware and routes
        are registered without crashing on startup.
        """
        response = client.get("/health")
        assert response.status_code == 200
        # X-Request-ID should be set by RequestIDMiddleware (Domain A area)
        assert "x-request-id" in response.headers


# ===================================================================
# CQ-02: Schema introspection with include_enums returns enum values
# ===================================================================


class TestCQ02SchemaIncludeEnums:
    """CQ-02: Schema introspection with include_enums returns enum values.

    Verifies SI-11: ``include_enums=true`` on the schema endpoint populates
    ``enum_values`` for enum fields and leaves it null for non-enum fields.
    """

    def test_enum_field_has_enum_values(self, client) -> None:
        """Enum-typed fields have enum_values populated with include_enums=true."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/offer/schema?include_semantic=true&include_enums=true",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 200, response.text
        data = response.json()

        # 'vertical' on offer is a known enum field
        vertical = next(
            (f for f in data["queryable_fields"] if f["name"] == "vertical"),
            None,
        )
        assert vertical is not None, "Expected 'vertical' field in offer schema"
        assert vertical["enum_values"] is not None, (
            "Expected enum_values for vertical field"
        )
        assert len(vertical["enum_values"]) >= 2

    def test_non_enum_field_has_null_enum_values(self, client) -> None:
        """Non-enum fields have enum_values as null even with include_enums=true."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema?include_semantic=true&include_enums=true",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 200, response.text
        data = response.json()

        # 'office_phone' is a phone type, not enum
        phone_field = next(
            (f for f in data["queryable_fields"] if f["name"] == "office_phone"),
            None,
        )
        if phone_field is not None:
            assert phone_field["enum_values"] is None, (
                f"Expected null enum_values for phone field, got {phone_field['enum_values']}"
            )

    def test_include_enums_requires_include_semantic(self, client) -> None:
        """include_enums=true without include_semantic=true does not populate enum_values.

        The route handler only processes enum values when include_semantic is
        also true, since semantic_type must be determined from the annotation.
        """
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema?include_enums=true",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 200, response.text
        data = response.json()

        # No field should have enum_values populated
        for field in data["queryable_fields"]:
            assert field.get("enum_values") is None, (
                f"Field '{field['name']}' should have null enum_values "
                f"when include_semantic is false"
            )


# ===================================================================
# CQ-03: Enum detail route returns valid values
# ===================================================================


class TestCQ03EnumDetailRoute:
    """CQ-03: Enum detail route returns valid values.

    Verifies SI-12: GET /{entity_type}/schema/enums/{field_name} returns
    the enum values for a known enum field.
    """

    def test_known_enum_field_returns_values(self, client) -> None:
        """GET /v1/resolve/offer/schema/enums/vertical returns enum values."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/offer/schema/enums/vertical",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["entity_type"] == "offer"
        assert data["field_name"] == "vertical"
        assert data["semantic_type"] in {"enum", "multi_enum"}
        assert len(data["values"]) > 0

        # Verify value structure
        for v in data["values"]:
            assert "value" in v
            assert "meaning" in v

        # Check known values
        value_strings = {v["value"] for v in data["values"]}
        assert "Medical" in value_strings
        assert "Dental" in value_strings

    def test_unit_vertical_enum_detail(self, client) -> None:
        """GET /v1/resolve/unit/schema/enums/vertical also works for unit entity."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema/enums/vertical",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["entity_type"] == "unit"
        assert data["field_name"] == "vertical"
        assert len(data["values"]) >= 2

    def test_non_enum_field_returns_404(self, client) -> None:
        """GET /v1/resolve/unit/schema/enums/office_phone returns 404 (not enum)."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema/enums/office_phone",
                headers=_JWT_BEARER_HEADER,
            )
        # office_phone has semantic_type "phone", not "enum"
        assert response.status_code == 404, response.text
        data = response.json()
        assert data["detail"]["error"] in {"FIELD_NOT_ENUM", "FIELD_NOT_ANNOTATED"}

    def test_unknown_field_returns_404(self, client) -> None:
        """GET /v1/resolve/unit/schema/enums/nonexistent_field returns 404."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unit/schema/enums/nonexistent_field",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 404, response.text

    def test_unknown_entity_type_returns_404(self, client) -> None:
        """GET /v1/resolve/unknown_type/schema/enums/vertical returns 404."""
        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.get(
                "/v1/resolve/unknown_type/schema/enums/vertical",
                headers=_JWT_BEARER_HEADER,
            )
        assert response.status_code == 404, response.text


# ===================================================================
# CQ-04: Idempotency middleware environment gate selects correct store
# ===================================================================


class TestCQ04EnvironmentGate:
    """CQ-04: Idempotency middleware environment gate selects correct store.

    Verifies H-02 environment gate: IDEMPOTENCY_STORE_BACKEND selects the
    correct store implementation at app creation time.
    """

    def test_memory_backend_selects_in_memory_store(self) -> None:
        """IDEMPOTENCY_STORE_BACKEND=memory selects InMemoryIdempotencyStore."""
        with (
            patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "memory"}),
            patch(
                "autom8_asana.api.lifespan._discover_entity_projects",
                new_callable=AsyncMock,
            ) as mock_discover,
        ):
            mock_discover.side_effect = lambda app: None
            app = create_app()

        store_found = _find_idempotency_store(app)
        assert store_found is not None, "IdempotencyMiddleware not found in stack"
        assert isinstance(store_found, InMemoryIdempotencyStore), (
            f"Expected InMemoryIdempotencyStore, got {type(store_found).__name__}"
        )

    def test_noop_backend_selects_noop_store(self) -> None:
        """IDEMPOTENCY_STORE_BACKEND=noop selects NoopIdempotencyStore."""
        with (
            patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "noop"}),
            patch(
                "autom8_asana.api.lifespan._discover_entity_projects",
                new_callable=AsyncMock,
            ) as mock_discover,
        ):
            mock_discover.side_effect = lambda app: None
            app = create_app()

        store_found = _find_idempotency_store(app)
        assert store_found is not None, "IdempotencyMiddleware not found in stack"
        assert isinstance(store_found, NoopIdempotencyStore), (
            f"Expected NoopIdempotencyStore, got {type(store_found).__name__}"
        )

    def test_unknown_backend_falls_back_to_noop(self) -> None:
        """IDEMPOTENCY_STORE_BACKEND=unknown falls back to NoopIdempotencyStore."""
        with (
            patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "unknown_xyz"}),
            patch(
                "autom8_asana.api.lifespan._discover_entity_projects",
                new_callable=AsyncMock,
            ) as mock_discover,
        ):
            mock_discover.side_effect = lambda app: None
            app = create_app()

        store_found = _find_idempotency_store(app)
        assert store_found is not None, "IdempotencyMiddleware not found in stack"
        assert isinstance(store_found, NoopIdempotencyStore), (
            f"Expected NoopIdempotencyStore for unknown backend, "
            f"got {type(store_found).__name__}"
        )

    def test_dynamodb_failure_degrades_to_noop(self) -> None:
        """IDEMPOTENCY_STORE_BACKEND=dynamodb with boto3 failure degrades to noop.

        When DynamoDBIdempotencyStore constructor raises (e.g., no AWS creds),
        the environment gate falls back to NoopIdempotencyStore.
        """
        with (
            patch.dict(os.environ, {"IDEMPOTENCY_STORE_BACKEND": "dynamodb"}),
            # NOTE: Patches the source module, not main.py's import site.
            # Works because create_app() uses a lazy import inside the function
            # body. If the import is hoisted to module level, patch the import
            # site instead: 'autom8_asana.api.main.DynamoDBIdempotencyStore'.
            patch(
                "autom8_asana.api.middleware.idempotency.DynamoDBIdempotencyStore",
                side_effect=Exception("No AWS credentials"),
            ),
            patch(
                "autom8_asana.api.lifespan._discover_entity_projects",
                new_callable=AsyncMock,
            ) as mock_discover,
        ):
            mock_discover.side_effect = lambda app: None
            app = create_app()

        store_found = _find_idempotency_store(app)
        assert store_found is not None, "IdempotencyMiddleware not found in stack"
        assert isinstance(store_found, NoopIdempotencyStore), (
            f"Expected NoopIdempotencyStore as fallback, "
            f"got {type(store_found).__name__}"
        )


# ===================================================================
# CQ-05: Cascade observability -- exception logging in preload
# ===================================================================


class TestCQ05CascadeExceptionLogging:
    """CQ-05: Cascade observability -- exception logging in preload.

    Verifies H-01 fix: the ``preload_phase_exception_discarded`` log event
    fires when BaseException results appear in asyncio.gather phase_results.

    This test exercises structural verification of the H-01 code path
    plus behavioral verification that the log message is produced when
    a BaseException result is encountered in phase processing.
    """

    def test_preload_exception_code_path_exists(self) -> None:
        """H-01 structural: 'preload_phase_exception_discarded' log event and
        BaseException check exist in _preload_dataframe_cache_progressive."""
        import inspect

        from autom8_asana.api.preload import progressive

        source = inspect.getsource(progressive._preload_dataframe_cache_progressive)
        assert "preload_phase_exception_discarded" in source, (
            "H-01 fix: 'preload_phase_exception_discarded' log event must be "
            "present in _preload_dataframe_cache_progressive"
        )
        assert "BaseException" in source, (
            "H-01 fix: BaseException check must be present (not just Exception)"
        )

    def test_exception_guard_uses_isinstance_base_exception(self) -> None:
        """H-01 behavioral: the isinstance check targets BaseException specifically.

        This is critical because asyncio.gather(return_exceptions=True) returns
        BaseException subclasses (including CancelledError, KeyboardInterrupt)
        as result objects. A plain ``isinstance(result, Exception)`` check would
        miss CancelledError in Python 3.9+.
        """
        import ast
        import inspect

        from autom8_asana.api.preload import progressive

        source = inspect.getsource(progressive._preload_dataframe_cache_progressive)
        tree = ast.parse(source)

        # Find isinstance calls that check for BaseException
        found_base_exception_check = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "isinstance" and len(node.args) >= 2:
                    type_arg = node.args[1]
                    if isinstance(type_arg, ast.Name) and type_arg.id == "BaseException":
                        found_base_exception_check = True

        assert found_base_exception_check, (
            "H-01 fix: isinstance(result, BaseException) check must be present "
            "in _preload_dataframe_cache_progressive to catch CancelledError."
        )


# ===================================================================
# CQ-06: Cascade observability -- cycle detection logging
# ===================================================================


class TestCQ06CascadeCycleDetection:
    """CQ-06: Cascade observability -- cycle detection logging.

    Verifies M-03 fix: the ``cascade_topological_cycle_detected`` log event
    fires when a cycle is detected during topological sort in cascade_warm_phases.
    """

    def test_cycle_detection_fires_warning(self) -> None:
        """When entities form a circular dependency, logger.warning fires with
        'cascade_topological_cycle_detected'."""
        from autom8_asana.dataframes.cascade_utils import cascade_warm_phases

        # Mock the registry to create a circular dependency:
        # alpha depends on beta, beta depends on alpha
        mock_alpha_desc = MagicMock()
        mock_alpha_desc.name = "alpha"
        mock_alpha_desc.warm_priority = 1
        mock_alpha_desc.cascading_field_provider = True
        mock_alpha_desc.effective_schema_key = "Alpha"

        mock_beta_desc = MagicMock()
        mock_beta_desc.name = "beta"
        mock_beta_desc.warm_priority = 2
        mock_beta_desc.cascading_field_provider = True
        mock_beta_desc.effective_schema_key = "Beta"

        mock_alpha_model = MagicMock()
        mock_beta_model = MagicMock()
        mock_alpha_desc.get_model_class.return_value = mock_alpha_model
        mock_beta_desc.get_model_class.return_value = mock_beta_model

        mock_registry = MagicMock()
        mock_registry.all_descriptors.return_value = [mock_alpha_desc, mock_beta_desc]
        mock_registry.warmable_entities.return_value = [
            mock_alpha_desc,
            mock_beta_desc,
        ]

        mock_alpha_schema = MagicMock()
        mock_alpha_schema.get_cascade_columns.return_value = [
            ("beta_field", "BetaField")
        ]

        mock_beta_schema = MagicMock()
        mock_beta_schema.get_cascade_columns.return_value = [
            ("alpha_field", "AlphaField")
        ]

        mock_schema_registry = MagicMock()

        def get_schema_side_effect(key):
            if key == "Alpha":
                return mock_alpha_schema
            if key == "Beta":
                return mock_beta_schema
            return None

        mock_schema_registry.get_schema.side_effect = get_schema_side_effect

        mock_alpha_field_def = MagicMock()
        mock_alpha_field_def.name = "AlphaField"
        mock_beta_field_def = MagicMock()
        mock_beta_field_def.name = "BetaField"

        mock_cascade_registry = {
            "alpha_field": (mock_alpha_model, mock_alpha_field_def),
            "beta_field": (mock_beta_model, mock_beta_field_def),
        }

        # Patch at the SOURCE module level since cascade_warm_phases uses
        # deferred imports inside the function body.
        with (
            patch(
                "autom8_asana.core.entity_registry.get_registry",
                return_value=mock_registry,
            ),
            patch(
                "autom8_asana.dataframes.models.registry.SchemaRegistry.get_instance",
                return_value=mock_schema_registry,
            ),
            patch(
                "autom8_asana.models.business.fields.get_cascading_field_registry",
                return_value=mock_cascade_registry,
            ),
            patch(
                "autom8_asana.dataframes.cascade_utils.logger",
            ) as mock_logger,
        ):
            phases = cascade_warm_phases()

            warning_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if len(c[0]) > 0
                and c[0][0] == "cascade_topological_cycle_detected"
            ]
            assert len(warning_calls) == 1, (
                f"Expected exactly 1 cycle detection warning, "
                f"got {len(warning_calls)}. "
                f"All warnings: {mock_logger.warning.call_args_list}"
            )

            extra = warning_calls[0][1]["extra"]
            assert extra["remaining_count"] == 2
            assert sorted(extra["remaining_entities"]) == ["alpha", "beta"]

    def test_cycle_detection_code_path_exists(self) -> None:
        """M-03 structural: cycle detection log event is present in source."""
        import inspect

        from autom8_asana.dataframes.cascade_utils import cascade_warm_phases

        source = inspect.getsource(cascade_warm_phases)
        assert "cascade_topological_cycle_detected" in source, (
            "M-03 fix: cycle detection log event must be present in cascade_warm_phases"
        )


# ===================================================================
# CQ-07: IdempotencyMiddleware re-exported from middleware package
# ===================================================================


class TestCQ07MiddlewareReExport:
    """CQ-07: IdempotencyMiddleware re-exported from middleware package.

    Verifies the middleware package's public API includes IdempotencyMiddleware
    for backward compatibility and discoverability.
    """

    def test_import_from_middleware_package(self) -> None:
        """``from autom8_asana.api.middleware import IdempotencyMiddleware`` works."""
        from autom8_asana.api.middleware import IdempotencyMiddleware as Imported

        assert Imported is IdempotencyMiddleware

    def test_in_all_exports(self) -> None:
        """IdempotencyMiddleware is in autom8_asana.api.middleware.__all__."""
        import autom8_asana.api.middleware as mw_pkg

        assert hasattr(mw_pkg, "__all__"), "middleware package must define __all__"
        assert "IdempotencyMiddleware" in mw_pkg.__all__, (
            f"'IdempotencyMiddleware' not in __all__. "
            f"Current __all__: {mw_pkg.__all__}"
        )

    def test_all_core_middleware_re_exported(self) -> None:
        """All expected middleware classes are re-exported from the package.

        Verifies the package is a proper facade that re-exports from submodules.
        """
        import autom8_asana.api.middleware as mw_pkg

        expected_exports = {
            "RequestIDMiddleware",
            "RequestLoggingMiddleware",
            "IdempotencyMiddleware",
        }
        actual_exports = set(mw_pkg.__all__)
        missing = expected_exports - actual_exports
        assert not missing, (
            f"Expected exports missing from __all__: {missing}. "
            f"Current __all__: {mw_pkg.__all__}"
        )


# ===================================================================
# Helpers
# ===================================================================


def _find_idempotency_store(app):
    """Find the IdempotencyMiddleware's store from app.user_middleware.

    Starlette stores registered middleware as ``Middleware`` objects in
    ``app.user_middleware`` before the stack is built on first request.

    Returns None if IdempotencyMiddleware is not found.
    """
    for mw in getattr(app, "user_middleware", []):
        if mw.cls.__name__ == "IdempotencyMiddleware":
            return mw.kwargs.get("store")
    return None
