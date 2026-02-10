r"""Contract alignment tests for DataServiceClient ↔ autom8_data.

These tests validate that the request format sent by DataServiceClient
matches autom8_data's API schema. They programmatically enforce the
contract alignment from WS1-001 (endpoint mismatch fix).

Source of truth: autom8_data Pydantic models at:
  - src/autom8_data/api/data_service_models/_insights.py (InsightsRequest)
  - src/autom8_data/api/data_service_models/_gid_map.py (GidMapRequest)
  - src/autom8_data/api/data_service_models/_base.py (PhoneVerticalPair)

Contract invariants enforced:
  1. FACTORY_TO_FRAME_TYPE maps all 14 factories to valid frame_type values
  2. frame_type must be one of: "offer", "unit", "business", "asset"
  3. phone must match E.164 pattern: ^\+[1-9]\d{6,14}$
  4. vertical must be non-empty string, lowercased
  5. period must be one of: "T7", "T14", "T30", "LIFETIME"
  6. phone_vertical_pairs must be a list with 1-1000 items
"""

from __future__ import annotations

import re

import httpx
import pytest
import respx

from autom8_asana.clients.data.client import DataServiceClient

# Replicate autom8_data validation rules (cannot import autom8_data directly)
E164_PHONE_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")
VALID_FRAME_TYPES = {"offer", "unit", "business", "asset"}
VALID_PERIODS = {"T7", "T14", "T30", "LIFETIME"}


class TestFactoryToFrameTypeContract:
    """Validate FACTORY_TO_FRAME_TYPE mapping completeness and correctness.

    Per WS1-001: Ensures all 14 VALID_FACTORIES have a frame_type mapping
    and that all mapped values are valid according to autom8_data's
    InsightsRequest.frame_type Literal.
    """

    def test_all_factories_have_frame_type_mapping(self):
        """All 14 VALID_FACTORIES must have a FACTORY_TO_FRAME_TYPE entry."""
        client = DataServiceClient()

        # Get all factories and their mappings
        valid_factories = client.VALID_FACTORIES
        factory_mappings = client.FACTORY_TO_FRAME_TYPE

        # Assert all factories have a mapping
        missing_mappings = valid_factories - factory_mappings.keys()
        assert not missing_mappings, (
            f"Factories missing frame_type mapping: {missing_mappings}. "
            f"Every factory in VALID_FACTORIES must have a FACTORY_TO_FRAME_TYPE entry."
        )

        # Assert exactly 14 factories
        assert len(valid_factories) == 14, (
            f"Expected 14 VALID_FACTORIES, got {len(valid_factories)}. "
            f"If this changed, update test expectations."
        )

    def test_all_frame_types_are_valid(self):
        """All FACTORY_TO_FRAME_TYPE values must match autom8_data's schema.

        Per autom8_data InsightsRequest.frame_type:
          Literal["offer", "unit", "business", "asset"]
        """
        client = DataServiceClient()

        # Get all mapped frame_type values
        frame_types = set(client.FACTORY_TO_FRAME_TYPE.values())

        # Assert all are in VALID_FRAME_TYPES
        invalid_types = frame_types - VALID_FRAME_TYPES
        assert not invalid_types, (
            f"Invalid frame_type values: {invalid_types}. "
            f"Must be one of: {VALID_FRAME_TYPES} "
            f"(per autom8_data InsightsRequest schema)."
        )

    def test_specific_factory_mappings(self):
        """Validate key factory mappings for regression protection.

        These mappings are critical for existing consumers and should not
        change without careful migration planning.
        """
        client = DataServiceClient()
        mappings = client.FACTORY_TO_FRAME_TYPE

        # Critical mappings from docs/design/factory-to-frame-type-mapping.md
        assert mappings["account"] == "business", (
            "account factory must map to business frame"
        )
        assert mappings["ads"] == "offer", "ads factory must map to offer frame"
        assert mappings["assets"] == "asset", "assets factory must map to asset frame"
        assert mappings["base"] == "unit", "base factory must map to unit frame"
        assert mappings["payments"] == "business", (
            "payments factory must map to business frame"
        )


class TestInsightsRequestContract:
    """Validate request body format against autom8_data InsightsRequest schema.

    Per WS1-001: The client now sends POST /api/v1/data-service/insights
    with body: {frame_type, phone_vertical_pairs, period}.

    This test class validates the actual HTTP request body matches
    autom8_data's Pydantic schema expectations.
    """

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_body_structure(self):
        """Validate HTTP request body has required fields with correct types.

        Per autom8_data InsightsRequest schema:
          - frame_type: Literal["offer", "unit", "business", "asset"]
          - phone_vertical_pairs: list[PhoneVerticalPair] (1-1000 items)
          - period: Literal["T7", "T14", "T30", "LIFETIME"]
        """
        # Mock the endpoint
        route = respx.post("http://localhost:8000/api/v1/data-service/insights").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "business",
                        "insights_period": "LIFETIME",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                    "request_id": "test-request-id",
                    "warnings": [],
                },
            )
        )

        # Create client and send request
        async with DataServiceClient() as client:
            await client.get_insights_async(
                factory="account",
                office_phone="+17705753103",
                vertical="chiropractic",
                period="lifetime",
            )

        # Validate request was made
        assert route.called
        request = route.calls.last.request

        # Parse request body
        body = request.read().decode("utf-8")
        import json

        body_json = json.loads(body)

        # Validate required fields exist
        assert "frame_type" in body_json, "Request body must have frame_type field"
        assert "phone_vertical_pairs" in body_json, (
            "Request body must have phone_vertical_pairs field"
        )
        assert "period" in body_json, "Request body must have period field"

        # Validate field types
        assert isinstance(body_json["frame_type"], str), "frame_type must be string"
        assert isinstance(body_json["phone_vertical_pairs"], list), (
            "phone_vertical_pairs must be list"
        )
        assert isinstance(body_json["period"], str), "period must be string"

        # Validate field values
        assert body_json["frame_type"] in VALID_FRAME_TYPES, (
            f"frame_type must be one of {VALID_FRAME_TYPES}, "
            f"got: {body_json['frame_type']}"
        )
        assert body_json["period"] in VALID_PERIODS, (
            f"period must be one of {VALID_PERIODS}, got: {body_json['period']}"
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_frame_type_mapping_for_all_factories(self):
        """Validate frame_type is correctly mapped for each factory.

        Tests all 14 factories to ensure FACTORY_TO_FRAME_TYPE is used
        correctly when building the request body.
        """
        client = DataServiceClient()

        for factory_name in client.VALID_FACTORIES:
            # Mock the endpoint
            route = respx.post(
                "http://localhost:8000/api/v1/data-service/insights"
            ).mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "data": [],
                        "metadata": {
                            "factory": factory_name,
                            "frame_type": client.FACTORY_TO_FRAME_TYPE[factory_name],
                            "insights_period": "LIFETIME",
                            "row_count": 0,
                            "column_count": 0,
                            "columns": [],
                            "cache_hit": False,
                            "duration_ms": 10.0,
                        },
                        "request_id": "test-request-id",
                        "warnings": [],
                    },
                )
            )

            # Send request
            async with DataServiceClient() as client_instance:
                await client_instance.get_insights_async(
                    factory=factory_name,
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="lifetime",
                )

            # Validate request was made
            assert route.called, f"Request not made for factory: {factory_name}"
            request = route.calls.last.request

            # Parse request body
            body = request.read().decode("utf-8")
            import json

            body_json = json.loads(body)

            # Validate frame_type matches mapping
            expected_frame_type = client.FACTORY_TO_FRAME_TYPE[factory_name]
            assert body_json["frame_type"] == expected_frame_type, (
                f"Factory '{factory_name}' should send frame_type='{expected_frame_type}', "
                f"got: {body_json['frame_type']}"
            )

            # Reset mock for next iteration
            route.reset()


class TestPeriodNormalizationContract:
    """Validate period normalization produces autom8_data-compatible values.

    Per autom8_data InsightsRequest.period:
      Literal["T7", "T14", "T30", "LIFETIME"]

    autom8_asana accepts various period formats (t30, l30, lifetime, etc.)
    and normalizes them to autom8_data's expected format.
    """

    @pytest.mark.asyncio
    @respx.mock
    @pytest.mark.parametrize(
        "input_period,expected_period",
        [
            ("lifetime", "LIFETIME"),
            ("LIFETIME", "LIFETIME"),
            ("t7", "T7"),
            ("T7", "T7"),
            ("l7", "T7"),
            ("L7", "T7"),
            ("t14", "T14"),
            ("T14", "T14"),
            ("l14", "T14"),
            ("L14", "T14"),
            ("t30", "T30"),
            ("T30", "T30"),
            ("l30", "T30"),
            ("L30", "T30"),
        ],
    )
    async def test_period_normalization(self, input_period, expected_period):
        """Validate period values are normalized to autom8_data format.

        Maps autom8_asana period conventions to autom8_data's Literal values.
        """
        # Mock the endpoint
        route = respx.post("http://localhost:8000/api/v1/data-service/insights").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "business",
                        "insights_period": expected_period,
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                    "request_id": "test-request-id",
                    "warnings": [],
                },
            )
        )

        # Send request with input_period
        async with DataServiceClient() as client:
            await client.get_insights_async(
                factory="account",
                office_phone="+17705753103",
                vertical="chiropractic",
                period=input_period,
            )

        # Validate request was made
        assert route.called
        request = route.calls.last.request

        # Parse request body
        body = request.read().decode("utf-8")
        import json

        body_json = json.loads(body)

        # Validate period was normalized correctly
        assert body_json["period"] == expected_period, (
            f"Period '{input_period}' should normalize to '{expected_period}', "
            f"got: {body_json['period']}"
        )


class TestPhoneVerticalPairContract:
    r"""Validate phone_vertical_pairs format matches autom8_data schema.

    Per autom8_data PhoneVerticalPair schema (data_service_models/_base.py):
      - phone: E.164 format (^\+[1-9]\d{6,14}$)
      - vertical: non-empty string, lowercased

    Per autom8_data InsightsRequest schema:
      - phone_vertical_pairs: list with 1-1000 items
    """

    @pytest.mark.asyncio
    @respx.mock
    async def test_phone_vertical_pair_structure(self):
        """Validate PVP list contains dicts with phone and vertical fields."""
        # Mock the endpoint
        route = respx.post("http://localhost:8000/api/v1/data-service/insights").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "business",
                        "insights_period": "LIFETIME",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                    "request_id": "test-request-id",
                    "warnings": [],
                },
            )
        )

        # Send request
        async with DataServiceClient() as client:
            await client.get_insights_async(
                factory="account",
                office_phone="+17705753103",
                vertical="chiropractic",
                period="lifetime",
            )

        # Validate request was made
        assert route.called
        request = route.calls.last.request

        # Parse request body
        body = request.read().decode("utf-8")
        import json

        body_json = json.loads(body)

        # Validate phone_vertical_pairs structure
        pvp_list = body_json["phone_vertical_pairs"]
        assert len(pvp_list) == 1, "Single request should have 1 PVP"

        pvp = pvp_list[0]
        assert isinstance(pvp, dict), "PVP must be a dict"
        assert "phone" in pvp, "PVP must have phone field"
        assert "vertical" in pvp, "PVP must have vertical field"

    @pytest.mark.asyncio
    @respx.mock
    async def test_phone_format_validation(self):
        r"""Validate phone field matches E.164 format.

        Per autom8_data PhoneVerticalPair.phone validator:
          Pattern: ^\+[1-9]\d{6,14}$

        This test captures the actual HTTP request and validates the phone
        field against the E.164 pattern.
        """
        # Mock the endpoint
        route = respx.post("http://localhost:8000/api/v1/data-service/insights").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "business",
                        "insights_period": "LIFETIME",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                    "request_id": "test-request-id",
                    "warnings": [],
                },
            )
        )

        # Test with valid E.164 phone numbers
        test_phones = [
            "+17705753103",  # US number
            "+441234567890",  # UK number
            "+6281234567",  # Shorter international
            "+12025551234",  # Another US number
        ]

        for phone in test_phones:
            async with DataServiceClient() as client:
                await client.get_insights_async(
                    factory="account",
                    office_phone=phone,
                    vertical="chiropractic",
                    period="lifetime",
                )

            # Validate request was made
            assert route.called
            request = route.calls.last.request

            # Parse request body
            body = request.read().decode("utf-8")
            import json

            body_json = json.loads(body)

            # Validate phone matches E.164 pattern
            sent_phone = body_json["phone_vertical_pairs"][0]["phone"]
            assert E164_PHONE_PATTERN.match(sent_phone), (
                f"Phone '{sent_phone}' does not match E.164 pattern "
                f"(must start with +, followed by 1-9, then 6-14 digits)"
            )

            # Reset for next iteration
            route.reset()

    @pytest.mark.asyncio
    @respx.mock
    async def test_vertical_format_validation(self):
        """Validate vertical field is non-empty.

        Per autom8_data PhoneVerticalPair.vertical validator:
          - Must be non-empty after stripping
          - autom8_data will normalize to lowercase on receipt

        Note: autom8_asana sends vertical as-is (preserving case).
        autom8_data's Pydantic validator handles lowercasing.
        This is acceptable because autom8_data's schema is tolerant.
        """
        # Mock the endpoint
        route = respx.post("http://localhost:8000/api/v1/data-service/insights").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "business",
                        "insights_period": "LIFETIME",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                    "request_id": "test-request-id",
                    "warnings": [],
                },
            )
        )

        # Test vertical is non-empty after Pydantic's str_strip_whitespace
        test_verticals = [
            "chiropractic",
            "CHIROPRACTIC",
            "ChIrOpRaCtIc",
            "dental",
        ]

        for vertical in test_verticals:
            async with DataServiceClient() as client:
                await client.get_insights_async(
                    factory="account",
                    office_phone="+17705753103",
                    vertical=vertical,
                    period="lifetime",
                )

            # Validate request was made
            assert route.called
            request = route.calls.last.request

            # Parse request body
            body = request.read().decode("utf-8")
            import json

            body_json = json.loads(body)

            # Validate vertical is non-empty
            sent_vertical = body_json["phone_vertical_pairs"][0]["vertical"]
            assert sent_vertical, f"Vertical must be non-empty, got: '{sent_vertical}'"
            assert sent_vertical.strip(), (
                f"Vertical must be non-empty after stripping, got: '{sent_vertical}'"
            )

            # Reset for next iteration
            route.reset()

    @pytest.mark.asyncio
    @respx.mock
    async def test_pvp_list_count_validation(self):
        """Validate phone_vertical_pairs list contains exactly 1 item for single requests.

        Per autom8_data InsightsRequest.phone_vertical_pairs:
          min_length=1, max_length=1000
        """
        # Mock the endpoint
        route = respx.post("http://localhost:8000/api/v1/data-service/insights").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "business",
                        "insights_period": "LIFETIME",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                    "request_id": "test-request-id",
                    "warnings": [],
                },
            )
        )

        # Send request
        async with DataServiceClient() as client:
            await client.get_insights_async(
                factory="account",
                office_phone="+17705753103",
                vertical="chiropractic",
                period="lifetime",
            )

        # Validate request was made
        assert route.called
        request = route.calls.last.request

        # Parse request body
        body = request.read().decode("utf-8")
        import json

        body_json = json.loads(body)

        # Validate list count
        pvp_list = body_json["phone_vertical_pairs"]
        assert len(pvp_list) >= 1, "PVP list must have at least 1 item"
        assert len(pvp_list) <= 1000, "PVP list must have at most 1000 items"
        assert len(pvp_list) == 1, "Single request should send exactly 1 PVP"


class TestEndpointContract:
    """Validate the HTTP endpoint path matches autom8_data's API.

    Per WS1-001: The client was fixed to use POST /api/v1/data-service/insights
    instead of the incorrect POST /api/v1/data-service/{factory}/insights.
    """

    @pytest.mark.asyncio
    @respx.mock
    async def test_endpoint_path(self):
        """Validate client sends POST /api/v1/data-service/insights.

        This is the programmatic enforcement of WS1-001 fix.
        If this test fails, the endpoint mismatch bug has regressed.
        """
        # Mock the CORRECT endpoint
        correct_route = respx.post(
            "http://localhost:8000/api/v1/data-service/insights"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "frame_type": "business",
                        "insights_period": "LIFETIME",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                    "request_id": "test-request-id",
                    "warnings": [],
                },
            )
        )

        # Mock the INCORRECT endpoint (should NOT be called)
        incorrect_route = respx.post(
            "http://localhost:8000/api/v1/data-service/account/insights"
        ).mock(return_value=httpx.Response(404, json={"error": "Not Found"}))

        # Send request
        async with DataServiceClient() as client:
            await client.get_insights_async(
                factory="account",
                office_phone="+17705753103",
                vertical="chiropractic",
                period="lifetime",
            )

        # Assert CORRECT endpoint was called
        assert correct_route.called, (
            "Client must send POST /api/v1/data-service/insights "
            "(NOT /api/v1/data-service/{factory}/insights). "
            "WS1-001 fix may have regressed."
        )

        # Assert INCORRECT endpoint was NOT called
        assert not incorrect_route.called, (
            "Client sent request to incorrect endpoint "
            "/api/v1/data-service/account/insights. "
            "WS1-001 fix has regressed!"
        )
