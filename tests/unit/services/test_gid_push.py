"""Unit tests for GID mapping push to autom8_data."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from autom8y_http import TimeoutException

from autom8_asana.services.gid_lookup import GidLookupIndex
from autom8_asana.services.gid_push import (
    GID_PUSH_ENABLED_ENV_VAR,
    GidPushResponse,
    _is_push_enabled,
    extract_mappings_from_index,
    push_gid_mappings_to_data_service,
)

# ============================================================================
# Tests for extract_mappings_from_index
# ============================================================================


class TestExtractMappingsFromIndex:
    """Tests for canonical_key parsing and mapping extraction."""

    def test_extracts_valid_pv1_entries(self) -> None:
        """Standard pv1:phone:vertical entries are extracted."""
        index = GidLookupIndex(
            lookup_dict={
                "pv1:+15551234567:dental": "1111111111111111",
                "pv1:+15559876543:chiropractic": "2222222222222222",
            },
            created_at=datetime.now(UTC),
        )

        mappings = extract_mappings_from_index(index)

        assert len(mappings) == 2
        assert {
            "phone": "+15551234567",
            "vertical": "dental",
            "task_gid": "1111111111111111",
        } in mappings
        assert {
            "phone": "+15559876543",
            "vertical": "chiropractic",
            "task_gid": "2222222222222222",
        } in mappings

    def test_skips_non_pv1_entries(self) -> None:
        """Entries not starting with 'pv1' are skipped."""
        index = GidLookupIndex(
            lookup_dict={
                "pv1:+15551234567:dental": "1111111111111111",
                "pv2:+15559876543:chiropractic": "2222222222222222",
                "other:format": "3333333333333333",
            },
            created_at=datetime.now(UTC),
        )

        mappings = extract_mappings_from_index(index)

        assert len(mappings) == 1
        assert mappings[0]["phone"] == "+15551234567"

    def test_skips_entries_with_wrong_part_count(self) -> None:
        """Entries with != 3 colon-separated parts are skipped."""
        index = GidLookupIndex(
            lookup_dict={
                "pv1:+15551234567:dental": "1111111111111111",
                "pv1:+15559876543": "2222222222222222",  # Only 2 parts
                "pv1:a:b:c": "3333333333333333",  # 4 parts
            },
            created_at=datetime.now(UTC),
        )

        mappings = extract_mappings_from_index(index)

        assert len(mappings) == 1
        assert mappings[0]["phone"] == "+15551234567"

    def test_empty_index_returns_empty_list(self) -> None:
        """Empty index produces no mappings."""
        index = GidLookupIndex(
            lookup_dict={},
            created_at=datetime.now(UTC),
        )

        mappings = extract_mappings_from_index(index)

        assert mappings == []


# ============================================================================
# Tests for _is_push_enabled
# ============================================================================


class TestIsPushEnabled:
    """Tests for feature flag check."""

    def test_enabled_by_default(self) -> None:
        """Push is enabled when env var is not set."""
        with patch.dict("os.environ", {}, clear=True):
            assert _is_push_enabled() is True

    def test_enabled_when_set_to_true(self) -> None:
        """Push is enabled when env var is 'true'."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "true"}):
            assert _is_push_enabled() is True

    def test_disabled_when_set_to_false(self) -> None:
        """Push is disabled when env var is 'false'."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "false"}):
            assert _is_push_enabled() is False

    def test_disabled_when_set_to_zero(self) -> None:
        """Push is disabled when env var is '0'."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "0"}):
            assert _is_push_enabled() is False

    def test_disabled_when_set_to_no(self) -> None:
        """Push is disabled when env var is 'no'."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "no"}):
            assert _is_push_enabled() is False

    def test_enabled_when_set_to_arbitrary_string(self) -> None:
        """Push is enabled when env var is any non-falsy value."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "yes"}):
            assert _is_push_enabled() is True


# ============================================================================
# Tests for push_gid_mappings_to_data_service
# ============================================================================


def _make_push_mocks(
    mock_http_cls: MagicMock,
    *,
    post_return: object | None = None,
    post_side_effect: object | None = None,
) -> AsyncMock:
    """Build the two-layer Autom8yHttpClient mock chain.

    Returns the mock_raw_client whose .post is the assertion target.
    """
    mock_raw_client = AsyncMock()
    if post_side_effect is not None:
        mock_raw_client.post.side_effect = post_side_effect
    elif post_return is not None:
        mock_raw_client.post.return_value = post_return

    mock_raw_cm = AsyncMock()
    mock_raw_cm.__aenter__.return_value = mock_raw_client

    mock_outer = MagicMock()
    mock_outer.raw.return_value = mock_raw_cm

    mock_http_cls.return_value = AsyncMock()
    mock_http_cls.return_value.__aenter__.return_value = mock_outer

    return mock_raw_client


class TestPushGidMappingsToDataService:
    """Tests for the async push function."""

    @pytest.fixture
    def sample_index(self) -> GidLookupIndex:
        """Create a sample GidLookupIndex with valid entries."""
        return GidLookupIndex(
            lookup_dict={
                "pv1:+15551234567:dental": "1111111111111111",
                "pv1:+15559876543:chiropractic": "2222222222222222",
            },
            created_at=datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC),
        )

    @pytest.fixture
    def empty_index(self) -> GidLookupIndex:
        """Create an empty GidLookupIndex."""
        return GidLookupIndex(
            lookup_dict={},
            created_at=datetime(2026, 2, 16, 12, 0, 0, tzinfo=UTC),
        )

    async def test_push_disabled_returns_false(self, sample_index: GidLookupIndex) -> None:
        """Returns False when push is disabled via feature flag."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "false"}):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    async def test_skips_when_no_data_service_url(self, sample_index: GidLookupIndex) -> None:
        """Returns False when AUTOM8Y_DATA_URL is not configured."""
        with patch.dict("os.environ", {}, clear=True):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    async def test_skips_when_no_auth_token(self, sample_index: GidLookupIndex) -> None:
        """Returns False when auth token is not available."""
        with patch.dict("os.environ", {"AUTOM8Y_DATA_URL": "http://localhost:8000"}, clear=True):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    async def test_empty_index_returns_true(self, empty_index: GidLookupIndex) -> None:
        """Returns True (no-op success) when index has no mappings."""
        with patch.dict("os.environ", {"AUTOM8Y_DATA_URL": "http://localhost:8000"}):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=empty_index,
                auth_token="test-token",
            )

        assert result is True

    async def test_successful_push(self, sample_index: GidLookupIndex) -> None:
        """Returns True and sends correct payload on HTTP 200."""
        mock_response = httpx.Response(
            status_code=200,
            json={"accepted": 2, "replaced": 0, "meta": {"request_id": "abc"}},
        )

        with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
            mock_raw_client = _make_push_mocks(mock_http_cls, post_return=mock_response)

            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is True

        # Verify the POST was called with correct URL and payload
        mock_raw_client.post.assert_called_once()
        call_args = mock_raw_client.post.call_args
        assert call_args.args[0] == "http://localhost:8000/api/v1/gid-mappings/sync"

        payload = call_args.kwargs["json"]
        assert payload["project_gid"] == "1201081073731555"
        assert payload["entry_count"] == 2
        assert payload["source_timestamp"] == "2026-02-16T12:00:00+00:00"
        assert len(payload["mappings"]) == 2

        # Verify auth header
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-token"

    async def test_payload_mapping_shape(self, sample_index: GidLookupIndex) -> None:
        """Each mapping in the payload has phone, vertical, task_gid keys."""
        mock_response = httpx.Response(
            status_code=200,
            json={"accepted": 2, "replaced": 0},
        )

        captured_payload: dict | None = None

        async def capture_post(url: str, *, json: dict, headers: dict) -> httpx.Response:
            nonlocal captured_payload
            captured_payload = json
            return mock_response

        with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
            mock_raw_client = _make_push_mocks(mock_http_cls)
            mock_raw_client.post = capture_post

            await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert captured_payload is not None
        for mapping in captured_payload["mappings"]:
            assert "phone" in mapping
            assert "vertical" in mapping
            assert "task_gid" in mapping

    async def test_http_error_returns_false(self, sample_index: GidLookupIndex) -> None:
        """Returns False on HTTP 500 error (non-blocking)."""
        mock_response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
        )

        with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
            _make_push_mocks(mock_http_cls, post_return=mock_response)

            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is False

    async def test_timeout_returns_false(self, sample_index: GidLookupIndex) -> None:
        """Returns False on HTTP timeout (non-blocking)."""
        with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
            _make_push_mocks(
                mock_http_cls,
                post_side_effect=TimeoutException("timed out"),
            )

            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is False

    async def test_unexpected_exception_returns_false(self, sample_index: GidLookupIndex) -> None:
        """Returns False on unexpected exceptions (non-blocking)."""
        with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
            _make_push_mocks(
                mock_http_cls,
                post_side_effect=RuntimeError("unexpected"),
            )

            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is False

    async def test_url_override(self, sample_index: GidLookupIndex) -> None:
        """data_service_url parameter overrides environment variable."""
        mock_response = httpx.Response(status_code=200, json={"accepted": 2})

        with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
            mock_raw_client = _make_push_mocks(mock_http_cls, post_return=mock_response)

            await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
                data_service_url="https://custom-url.example.com",
                auth_token="test-token",
            )

        call_args = mock_raw_client.post.call_args
        assert "custom-url.example.com" in call_args.args[0]

    async def test_trailing_slash_in_url_handled(self, sample_index: GidLookupIndex) -> None:
        """Trailing slash in base URL does not cause double-slash."""
        mock_response = httpx.Response(status_code=200, json={"accepted": 2})

        with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
            mock_raw_client = _make_push_mocks(mock_http_cls, post_return=mock_response)

            await push_gid_mappings_to_data_service(
                project_gid="test-gid",
                index=sample_index,
                data_service_url="http://localhost:8000/",
                auth_token="test-token",
            )

        call_args = mock_raw_client.post.call_args
        url = call_args.args[0]
        assert "//" not in url.replace("http://", "")


class TestPiiMaskingInLogs:
    """Verify that PII masking is applied to log fields in gid_push."""

    async def test_http_error_response_text_is_masked(self) -> None:
        """Phone numbers in HTTP error response body are masked in warning log."""
        phone_in_body = "error: +15551234567 not found"
        mock_response = httpx.Response(
            status_code=500,
            text=phone_in_body,
        )

        logged_extra: dict | None = None

        def capture_warning(event: str, extra: dict | None = None, **kwargs: object) -> None:
            nonlocal logged_extra
            if event == "gid_push_failed":
                logged_extra = extra or {}

        index = GidLookupIndex(
            lookup_dict={"pv1:+15551234567:dental": "1111111111111111"},
            created_at=__import__("datetime").datetime(
                2026, 2, 16, 12, 0, 0, tzinfo=__import__("datetime").timezone.utc
            ),
        )

        with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
            _make_push_mocks(mock_http_cls, post_return=mock_response)

            with patch("autom8_asana.services.gid_push.logger") as mock_logger:
                mock_logger.warning.side_effect = capture_warning
                await push_gid_mappings_to_data_service(
                    project_gid="test-gid",
                    index=index,
                    data_service_url="http://localhost:8000",
                    auth_token="test-token",
                )

        assert logged_extra is not None
        response_text = logged_extra.get("response_text", "")
        assert "+15551234567" not in response_text, (
            "Phone number should be masked in gid_push_failed log"
        )


# ============================================================================
# Tests for GidPushResponse contract model
# ============================================================================


class TestGidPushResponse:
    """ASN-7: POST /api/v1/gid-mappings/sync response."""

    def test_valid_response_both_fields(self):
        resp = GidPushResponse.model_validate({"accepted": 10, "replaced": 3})
        assert resp.accepted == 10
        assert resp.replaced == 3

    def test_missing_fields_default_to_none(self):
        resp = GidPushResponse.model_validate({})
        assert resp.accepted is None
        assert resp.replaced is None

    def test_partial_fields(self):
        resp = GidPushResponse.model_validate({"accepted": 5})
        assert resp.accepted == 5
        assert resp.replaced is None

    def test_extra_fields_ignored(self):
        resp = GidPushResponse.model_validate(
            {
                "accepted": 7,
                "replaced": 2,
                "timestamp": "2026-02-22T12:00:00",
                "unknown": True,
            }
        )
        assert resp.accepted == 7
        assert resp.replaced == 2
        assert not hasattr(resp, "timestamp")
        assert not hasattr(resp, "unknown")

    def test_null_fields(self):
        resp = GidPushResponse.model_validate({"accepted": None, "replaced": None})
        assert resp.accepted is None
        assert resp.replaced is None

    def test_string_coercion_to_int(self):
        """Pydantic v2 coerces compatible types by default."""
        resp = GidPushResponse.model_validate({"accepted": "12", "replaced": "0"})
        assert resp.accepted == 12
        assert resp.replaced == 0


# ============================================================================
# Tests for extract_status_from_dataframe (H-03 remediation)
# ============================================================================

import polars as pl

from autom8_asana.models.business.unit_activity import UNIT_ACTIVITY_COLUMN
from autom8_asana.services.gid_push import (
    PIPELINE_TYPE_BY_PROJECT_GID,
    extract_status_from_dataframe,
)

# Known project GID for "unit" pipeline type
_UNIT_GID = "1201081073731555"
_UNKNOWN_GID = "9999999999999999"
# A process-pipeline project, looked up rather than restated.
_SALES_GID = next(gid for gid, kind in PIPELINE_TYPE_BY_PROJECT_GID.items() if kind == "sales")

# Expected output keys for every entry dict
_EXPECTED_KEYS = {
    "phone",
    "vertical",
    "pipeline_type",
    "account_activity",
    "pipeline_section",
    "stage_entered_at",
}


def _logger_fake():
    """A logger fake with the real logger protocol's interface."""
    from unittest.mock import create_autospec

    from autom8y_log import LoggerProtocol

    return create_autospec(LoggerProtocol, instance=True)


def _unit_frame(**columns: list) -> pl.DataFrame:
    """A Unit frame as the push sees it: the activity column already computed."""
    return pl.DataFrame(columns, schema_overrides={UNIT_ACTIVITY_COLUMN: pl.Utf8})


class TestExtractStatusFromDataframe:
    """Tests for extract_status_from_dataframe.

    A Unit frame's activity is read from its ``unit_activity`` column, never
    re-derived from its section. Other entity types are classified from their
    section. Covers the early exits, the active-only filter (SD-02) and the
    output shape.

    Ref: H-03 from CASE-account-status-state-projection.md
    """

    # ------------------------------------------------------------------
    # Early exits
    # ------------------------------------------------------------------

    def test_unknown_project_gid_returns_empty(self) -> None:
        df = _unit_frame(
            office_phone=["+15551234567"], section=["Active"], unit_activity=["active"]
        )
        assert extract_status_from_dataframe(df, _UNKNOWN_GID, "unit") == []

    def test_missing_office_phone_column_returns_empty(self) -> None:
        df = _unit_frame(name=["Test Business"], section=["Active"], unit_activity=["active"])
        assert extract_status_from_dataframe(df, _UNIT_GID, "unit") == []

    def test_empty_phone_skipped(self) -> None:
        df = _unit_frame(
            office_phone=["", None, "+15551234567"],
            section=["Active", "Active", "Active"],
            unit_activity=["active", "active", "active"],
        )
        result = extract_status_from_dataframe(df, _UNIT_GID, "unit")
        assert [e["phone"] for e in result] == ["+15551234567"]

    def test_no_section_name_skipped(self) -> None:
        """The row's own section is still required for the pipeline_section label."""
        df = _unit_frame(office_phone=["+15551234567"], unit_activity=["active"])
        assert extract_status_from_dataframe(df, _UNIT_GID, "unit") == []

    def test_unit_frame_without_activity_column_yields_nothing(self) -> None:
        """No column, no rows: the section is never used as a fallback."""
        df = pl.DataFrame({"office_phone": ["+15551234567"], "section": ["Active"]})

        with patch("autom8_asana.services.gid_push.logger", new=_logger_fake()) as mock_logger:
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert result == []
        mock_logger.warning.assert_called_once()
        assert mock_logger.warning.call_args.args[0] == "status_extract_unit_activity_absent"

    # ------------------------------------------------------------------
    # The unit activity comes from the column, not the section
    # ------------------------------------------------------------------

    def test_unit_activity_is_read_from_the_column_not_the_section(self) -> None:
        df = _unit_frame(
            office_phone=["+15551234567", "+15551234568"],
            vertical=["dental", "dental"],
            section=["Engaged", "Active"],
            unit_activity=["active", None],
        )

        result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        assert result[0]["phone"] == "+15551234567"
        assert result[0]["account_activity"] == "active"
        assert result[0]["pipeline_section"] == "Engaged"

    def test_section_from_memberships_labels_the_entry(self) -> None:
        memberships_data = [
            {
                "section": {"name": "Onboarding", "gid": "123"},
                "project": {"gid": _UNIT_GID},
            }
        ]
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "memberships": [memberships_data],
                UNIT_ACTIVITY_COLUMN: ["activating"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.extract_section_name",
            autospec=True,
            return_value="Onboarding",
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        assert result[0]["pipeline_section"] == "Onboarding"
        assert result[0]["account_activity"] == "activating"

    def test_an_unknown_activity_value_fails_loudly(self) -> None:
        df = _unit_frame(office_phone=["+15551234567"], section=["Active"], unit_activity=["busy"])
        with pytest.raises(ValueError, match="busy"):
            extract_status_from_dataframe(df, _UNIT_GID, "unit")

    # ------------------------------------------------------------------
    # Active-only filter (SD-02)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("activity", ["inactive", "ignored", None])
    def test_non_billable_unit_rows_are_not_persisted(self, activity) -> None:
        df = _unit_frame(
            office_phone=["+15551234567"], section=["Active"], unit_activity=[activity]
        )
        assert extract_status_from_dataframe(df, _UNIT_GID, "unit") == []

    @pytest.mark.parametrize("activity", ["active", "activating"])
    def test_billable_unit_rows_are_persisted(self, activity) -> None:
        df = _unit_frame(
            office_phone=["+15551234567"], section=["Paused"], unit_activity=[activity]
        )
        result = extract_status_from_dataframe(df, _UNIT_GID, "unit")
        assert [e["account_activity"] for e in result] == [activity]

    # ------------------------------------------------------------------
    # Output shape validation
    # ------------------------------------------------------------------

    def test_output_entry_keys_and_types(self) -> None:
        df = _unit_frame(
            office_phone=["+15551234567"],
            vertical=["chiropractic"],
            section=["Active"],
            unit_activity=["active"],
        )

        result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        entry = result[0]
        assert set(entry.keys()) == _EXPECTED_KEYS
        for key in _EXPECTED_KEYS:
            assert isinstance(entry[key], str), key
        assert entry["phone"] == "+15551234567"
        assert entry["vertical"] == "chiropractic"
        assert entry["pipeline_type"] == "unit"
        assert entry["account_activity"] == "active"
        assert entry["pipeline_section"] == "Active"

    def test_vertical_defaults_to_empty_string(self) -> None:
        df = _unit_frame(
            office_phone=["+15551234567"], section=["Active"], unit_activity=["active"]
        )
        result = extract_status_from_dataframe(df, _UNIT_GID, "unit")
        assert len(result) == 1
        assert result[0]["vertical"] == ""

    # ------------------------------------------------------------------
    # Non-unit entity types classify their own section
    # ------------------------------------------------------------------

    def test_process_pipeline_rows_classify_their_section(self) -> None:
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567", "+15551234568"],
                "section": ["ACTIVE", "INACTIVE"],
            }
        )

        result = extract_status_from_dataframe(df, _SALES_GID, "sales")

        assert [(e["phone"], e["account_activity"]) for e in result] == [("+15551234567", "active")]
        assert result[0]["pipeline_type"] == "sales"

    def test_unknown_entity_type_warns_and_skips(self) -> None:
        """Per TC-5: an entity type with no classifier warns and skips, no fallback."""
        df = pl.DataFrame({"office_phone": ["+15551234567"], "section": ["Active"]})

        with patch("autom8_asana.services.gid_push.logger", new=_logger_fake()) as mock_logger:
            result = extract_status_from_dataframe(df, _UNIT_GID, "unknown_entity")

        mock_logger.warning.assert_called_once_with(
            "process_pipeline_no_classifier",
            extra={
                "entity_type": "unknown_entity",
                "project_gid": _UNIT_GID,
            },
        )
        assert result == []
