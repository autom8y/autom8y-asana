"""Bilateral contract test: validates client parsing of server wire format.

Companion to autom8y-data's test_cross_repo_insights_contract.py, which
validates the SERVER emits correct wire format. This test validates the
CLIENT correctly parses that format.

The wire format fixture must match the server's InsightsResponse
serialized with model_dump(exclude_none=True, by_alias=True).

Prerequisite: P1 (meta/metadata fix) must be deployed on the server
before this test can validate a live response. This test validates
the parsing logic against a synthetic fixture matching the post-P1
wire format.

Server contract test location (for cross-reference):
  autom8y-data/tests/api/test_cross_repo_insights_contract.py
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from autom8_asana.clients.data._response import parse_success_response
from autom8_asana.clients.data.models import InsightsMetadata, InsightsResponse

# ---------------------------------------------------------------------------
# Wire Format Fixture
# ---------------------------------------------------------------------------
# Matches server InsightsResponse.model_dump(exclude_none=True, by_alias=True)
# after P1 fix. The "metadata" key (not "meta") is the post-fix wire format.
#
# Server InsightsResponseMeta fields:
#   request_id, duration_ms, cache_hit, cache_layer, frame_type, period, entity_count
#
# When cache_hit=False, cache_layer=None is excluded by exclude_none=True.

WIRE_FORMAT_FIXTURE = {
    "data": [
        {
            "office_phone": "+19259998806",
            "vertical": "chiropractic",
            "spend": 1500.00,
            "leads": 25,
            "scheds": 10,
            "convs": 5,
            "cps": 150.00,
            "cpl": 60.00,
        }
    ],
    "metadata": {
        "request_id": "test-req-001",
        "duration_ms": 42.5,
        "cache_hit": False,
        "frame_type": "offer",
        "period": "T30",
        "entity_count": 1,
    },
    "metric_types": {
        "spend": "CURRENCY",
        "cps": "CURRENCY",
        "cpl": "CURRENCY",
        "leads": "COUNT",
        "scheds": "COUNT",
        "convs": "COUNT",
    },
}

# Variant with cache_hit=True and cache_layer present
WIRE_FORMAT_FIXTURE_CACHED = {
    "data": [
        {
            "office_phone": "+19259998806",
            "vertical": "chiropractic",
            "spend": 1500.00,
            "leads": 25,
            "scheds": 10,
            "convs": 5,
            "cps": 150.00,
            "cpl": 60.00,
        }
    ],
    "metadata": {
        "request_id": "test-req-002",
        "duration_ms": 1.2,
        "cache_hit": True,
        "cache_layer": "L1",
        "frame_type": "offer",
        "period": "T30",
        "entity_count": 1,
    },
    "metric_types": {
        "spend": "CURRENCY",
        "cps": "CURRENCY",
        "cpl": "CURRENCY",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_http_response(body: dict) -> MagicMock:
    """Create a mock autom8y_http.Response with .json() returning body.

    This mocks the actual object passed to parse_success_response,
    exercising the real parsing path (option (a) from TDD).
    """
    mock_response = MagicMock()
    mock_response.json.return_value = body
    mock_response.status_code = 200
    return mock_response


def _parse_fixture(body: dict, request_id: str = "test-req-001") -> InsightsResponse:
    """Parse a wire format fixture through the client's actual parsing path."""
    mock_response = _mock_http_response(body)
    return parse_success_response(mock_response, request_id, log=None)


# ---------------------------------------------------------------------------
# Tests: Client parses server wire format correctly
# ---------------------------------------------------------------------------


class TestClientParsesServerWireFormat:
    """Validate parse_success_response handles the post-P1 wire format.

    These tests exercise the actual parsing path in _response.py,
    not just model construction. The mock wraps the wire format dict
    in a Response-like object so parse_success_response calls .json()
    and processes the result through its full logic.
    """

    def test_metadata_is_populated(self) -> None:
        """InsightsMetadata must be populated (not empty defaults) from server metadata."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert isinstance(result.metadata, InsightsMetadata)
        # duration_ms should reflect the server value, not the default of 0.0
        assert result.metadata.duration_ms == 42.5

    def test_metadata_factory_is_unknown(self) -> None:
        """InsightsMetadata.factory is 'unknown' because server does not emit it.

        The server's InsightsResponseMeta has no 'factory' field.
        The client reads metadata_dict.get("factory", "unknown").
        After P1 fix, the client correctly receives metadata but 'factory'
        will still be "unknown" because the server never sends that key.

        TODO: factory field not emitted by server -- see architecture-report.md.
        This is a known gap. Phase 1 cross-service enrichment should decide
        whether the server should add a factory field or the client should
        derive it from frame_type.
        """
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.factory == "unknown", (
            "Server wire format does not include 'factory' field. "
            "Client should default to 'unknown'. If this assertion fails, "
            "the server has started emitting 'factory' and this test should "
            "be updated to assert the actual value."
        )

    def test_metadata_frame_type_populated(self) -> None:
        """InsightsMetadata.frame_type must reflect the server's frame_type value."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.frame_type == "offer"

    def test_metadata_cache_hit_false(self) -> None:
        """InsightsMetadata.cache_hit must reflect the server value (False)."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.cache_hit is False

    def test_metadata_cache_hit_true(self) -> None:
        """InsightsMetadata.cache_hit must reflect the server value (True)."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE_CACHED, request_id="test-req-002")

        assert result.metadata.cache_hit is True

    def test_metadata_duration_ms_populated(self) -> None:
        """InsightsMetadata.duration_ms must reflect the server's value."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.duration_ms == 42.5

    def test_metadata_columns_empty_when_absent(self) -> None:
        """When server omits columns (exclude_none), client defaults to empty list.

        The server's InsightsResponseMeta does not have a 'columns' field.
        The client reads metadata_dict.get("columns", []) and constructs
        ColumnInfo objects. With no columns key, this defaults to [].
        """
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.columns == []
        assert result.metadata.column_count == 0

    def test_metadata_row_count_defaults_to_zero(self) -> None:
        """row_count defaults to 0 since server metadata does not include it.

        The server sends 'entity_count', not 'row_count'. The client reads
        metadata_dict.get("row_count", 0). This is a field mapping gap:
        server uses entity_count, client uses row_count.
        """
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        # Server has entity_count=1 but client reads row_count (absent), defaults to 0
        assert result.metadata.row_count == 0

    def test_data_rows_preserved(self) -> None:
        """Data rows must pass through parsing unchanged."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert len(result.data) == 1
        row = result.data[0]
        assert row["office_phone"] == "+19259998806"
        assert row["vertical"] == "chiropractic"
        assert row["spend"] == 1500.00
        assert row["leads"] == 25
        assert row["scheds"] == 10
        assert row["convs"] == 5
        assert row["cps"] == 150.00
        assert row["cpl"] == 60.00

    def test_data_rows_count(self) -> None:
        """Number of data rows must match the fixture."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert len(result.data) == 1

    def test_request_id_set_from_argument(self) -> None:
        """request_id on InsightsResponse comes from the function argument, not metadata."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE, request_id="custom-req-id")

        assert result.request_id == "custom-req-id"

    def test_warnings_default_to_empty(self) -> None:
        """When server response has no warnings key, client defaults to empty list."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.warnings == []

    def test_metric_types_not_in_client_model(self) -> None:
        """metric_types is in the server response but not consumed by client parsing.

        The client's parse_success_response reads body.get("data"),
        body.get("metadata"), and body.get("warnings"). It does NOT
        read body.get("metric_types"). This field is silently dropped
        during parsing. Phase 1 may need to surface this if consumers
        need type-aware formatting.
        """
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        # InsightsResponse model does not have a metric_types field
        assert not hasattr(result, "metric_types") or "metric_types" not in result.model_fields


class TestClientParsesEmptyResponse:
    """Validate parse_success_response handles empty data gracefully."""

    def test_empty_data_parses_successfully(self) -> None:
        """Server returns empty data for non-existent PVPs."""
        empty_fixture = {
            "data": [],
            "metadata": {
                "request_id": "test-req-empty",
                "duration_ms": 5.0,
                "cache_hit": False,
                "frame_type": "offer",
                "period": "T30",
                "entity_count": 0,
            },
        }

        result = _parse_fixture(empty_fixture, request_id="test-req-empty")

        assert len(result.data) == 0
        assert result.metadata.cache_hit is False
        assert result.metadata.frame_type == "offer"
        assert result.metadata.duration_ms == 5.0


class TestClientParsesOptionalServerFields:
    """Validate that optional fields absent from server response default gracefully.

    Server InsightsResponseMeta fields not consumed by client:
      - cache_layer: harmlessly ignored (extra="ignore" on InsightsMetadata)
      - entity_count: not mapped to any client field

    Client InsightsMetadata fields absent from server:
      - factory: defaults to "unknown"
      - insights_period: defaults to None
      - row_count: defaults to 0
      - column_count: defaults to 0
      - columns: defaults to []
      - sort_history: defaults to None
      - is_stale: defaults to False
      - cached_at: defaults to None
    """

    def test_sort_history_defaults_to_none(self) -> None:
        """sort_history not in server metadata, defaults to None."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.sort_history is None

    def test_is_stale_defaults_to_false(self) -> None:
        """is_stale not in server metadata, defaults to False."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.is_stale is False

    def test_cached_at_defaults_to_none(self) -> None:
        """cached_at not in server metadata, defaults to None."""
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.cached_at is None

    def test_insights_period_defaults_to_none(self) -> None:
        """insights_period not in server metadata (server uses 'period'), defaults to None.

        The server sends 'period' (e.g., "T30"), but the client reads
        metadata_dict.get("insights_period"), which is absent. This is
        a field naming mismatch between server and client metadata schemas.
        """
        result = _parse_fixture(WIRE_FORMAT_FIXTURE)

        assert result.metadata.insights_period is None


class TestBatchPathParsesServerWireFormat:
    """Validate build_entity_response (batch parsing path) handles server wire format.

    The batch path in _endpoints/batch.py uses build_entity_response which
    reads response_metadata dict directly (not via parse_success_response).
    This tests that path handles the same wire format fixture.
    """

    def test_batch_entity_response_metadata_populated(self) -> None:
        """build_entity_response must populate InsightsMetadata from server metadata."""
        from autom8_asana.clients.data._endpoints.batch import build_entity_response

        metadata_dict = WIRE_FORMAT_FIXTURE["metadata"]
        rows = WIRE_FORMAT_FIXTURE["data"]

        result = build_entity_response(
            rows=rows,
            response_metadata=metadata_dict,
            request_id="test-batch-001",
            warnings=[],
        )

        assert isinstance(result, InsightsResponse)
        assert result.metadata.frame_type == "offer"
        assert result.metadata.cache_hit is False
        assert result.metadata.duration_ms == 42.5

    def test_batch_entity_response_factory_unknown(self) -> None:
        """build_entity_response also defaults factory to 'unknown'.

        TODO: factory field not emitted by server -- see architecture-report.md.
        Same gap as the single-request parsing path.
        """
        from autom8_asana.clients.data._endpoints.batch import build_entity_response

        metadata_dict = WIRE_FORMAT_FIXTURE["metadata"]
        rows = WIRE_FORMAT_FIXTURE["data"]

        result = build_entity_response(
            rows=rows,
            response_metadata=metadata_dict,
            request_id="test-batch-001",
            warnings=[],
        )

        assert result.metadata.factory == "unknown", (
            "Server wire format does not include 'factory' field. "
            "build_entity_response should default to 'unknown'."
        )

    def test_batch_entity_response_row_count_from_rows(self) -> None:
        """build_entity_response sets row_count from len(rows), not metadata."""
        from autom8_asana.clients.data._endpoints.batch import build_entity_response

        metadata_dict = WIRE_FORMAT_FIXTURE["metadata"]
        rows = WIRE_FORMAT_FIXTURE["data"]

        result = build_entity_response(
            rows=rows,
            response_metadata=metadata_dict,
            request_id="test-batch-001",
            warnings=[],
        )

        # batch path computes row_count = len(rows), unlike single path
        assert result.metadata.row_count == 1

    def test_batch_entity_response_data_preserved(self) -> None:
        """build_entity_response must preserve data rows."""
        from autom8_asana.clients.data._endpoints.batch import build_entity_response

        metadata_dict = WIRE_FORMAT_FIXTURE["metadata"]
        rows = WIRE_FORMAT_FIXTURE["data"]

        result = build_entity_response(
            rows=rows,
            response_metadata=metadata_dict,
            request_id="test-batch-001",
            warnings=[],
        )

        assert len(result.data) == 1
        assert result.data[0]["spend"] == 1500.00
