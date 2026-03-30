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

    @pytest.mark.asyncio
    async def test_push_disabled_returns_false(
        self, sample_index: GidLookupIndex
    ) -> None:
        """Returns False when push is disabled via feature flag."""
        with patch.dict("os.environ", {GID_PUSH_ENABLED_ENV_VAR: "false"}):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_skips_when_no_data_service_url(
        self, sample_index: GidLookupIndex
    ) -> None:
        """Returns False when AUTOM8Y_DATA_URL is not configured."""
        with patch.dict("os.environ", {}, clear=True):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_skips_when_no_auth_token(self, sample_index: GidLookupIndex) -> None:
        """Returns False when auth token is not available."""
        with patch.dict(
            "os.environ", {"AUTOM8Y_DATA_URL": "http://localhost:8000"}, clear=True
        ):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=sample_index,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_index_returns_true(self, empty_index: GidLookupIndex) -> None:
        """Returns True (no-op success) when index has no mappings."""
        with patch.dict("os.environ", {"AUTOM8Y_DATA_URL": "http://localhost:8000"}):
            result = await push_gid_mappings_to_data_service(
                project_gid="1201081073731555",
                index=empty_index,
                auth_token="test-token",
            )

        assert result is True

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_payload_mapping_shape(self, sample_index: GidLookupIndex) -> None:
        """Each mapping in the payload has phone, vertical, task_gid keys."""
        mock_response = httpx.Response(
            status_code=200,
            json={"accepted": 2, "replaced": 0},
        )

        captured_payload: dict | None = None

        async def capture_post(
            url: str, *, json: dict, headers: dict
        ) -> httpx.Response:
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_false(
        self, sample_index: GidLookupIndex
    ) -> None:
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_trailing_slash_in_url_handled(
        self, sample_index: GidLookupIndex
    ) -> None:
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

    @pytest.mark.asyncio
    async def test_http_error_response_text_is_masked(self) -> None:
        """Phone numbers in HTTP error response body are masked in warning log."""
        phone_in_body = "error: +15551234567 not found"
        mock_response = httpx.Response(
            status_code=500,
            text=phone_in_body,
        )

        logged_extra: dict | None = None

        def capture_warning(
            event: str, extra: dict | None = None, **kwargs: object
        ) -> None:
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

from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.services.gid_push import (
    PIPELINE_TYPE_BY_PROJECT_GID,
    extract_status_from_dataframe,
)

# Known project GID for "unit" pipeline type
_UNIT_GID = "1201081073731555"
_UNKNOWN_GID = "9999999999999999"

# Expected output keys for every entry dict
_EXPECTED_KEYS = {
    "phone",
    "vertical",
    "pipeline_type",
    "account_activity",
    "pipeline_section",
    "stage_entered_at",
}


def _make_classifier(mapping: dict[str, AccountActivity | None]):
    """Create a mock classifier with a controlled classify() method."""
    mock = MagicMock()
    mock.classify.side_effect = lambda s: mapping.get(s)
    return mock


class TestExtractStatusFromDataframe:
    """Tests for extract_status_from_dataframe.

    Covers all 6 early-exit branches, the active-only filter (SD-02),
    output shape validation, and classifier fallback behavior.

    Ref: H-03 from CASE-account-status-state-projection.md
    """

    # ------------------------------------------------------------------
    # Branch 1: Unknown project GID
    # ------------------------------------------------------------------

    def test_unknown_project_gid_returns_empty(self) -> None:
        """GID not in PIPELINE_TYPE_BY_PROJECT_GID returns empty list."""
        df = pl.DataFrame({"office_phone": ["+15551234567"], "section": ["Active"]})
        result = extract_status_from_dataframe(df, _UNKNOWN_GID, "unit")
        assert result == []

    # ------------------------------------------------------------------
    # Branch 2: Missing required columns
    # ------------------------------------------------------------------

    def test_missing_office_phone_column_returns_empty(self) -> None:
        """DataFrame without office_phone column returns empty list."""
        df = pl.DataFrame({"name": ["Test Business"], "section": ["Active"]})

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Active": AccountActivity.ACTIVE}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert result == []

    # ------------------------------------------------------------------
    # Branch 3: Empty/falsy phone values
    # ------------------------------------------------------------------

    def test_empty_phone_skipped(self) -> None:
        """Rows with empty or None phone values are skipped."""
        df = pl.DataFrame(
            {
                "office_phone": ["", None, "+15551234567"],
                "section": ["Active", "Active", "Active"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Active": AccountActivity.ACTIVE}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        # Only the third row (valid phone) should produce an entry
        assert len(result) == 1
        assert result[0]["phone"] == "+15551234567"

    # ------------------------------------------------------------------
    # Branch 4: No section name found
    # ------------------------------------------------------------------

    def test_no_section_name_skipped(self) -> None:
        """Row with no section_name column and no memberships is skipped."""
        df = pl.DataFrame({"office_phone": ["+15551234567"]})

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert result == []

    def test_section_from_section_name_column(self) -> None:
        """Section name is extracted from the section_name column when present."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "vertical": ["chiropractic"],
                "section": ["Month 1"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Month 1": AccountActivity.ACTIVE}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        assert result[0]["pipeline_section"] == "Month 1"
        assert result[0]["account_activity"] == "active"

    def test_section_from_memberships_dict(self) -> None:
        """Section name is extracted from memberships when section_name column absent.

        Uses a real list-typed memberships column to exercise the branch.
        The `if memberships is not None:` guard (fixed from `if memberships:`)
        handles Polars list scalars without raising TypeError.
        """
        memberships_data = [
            {
                "section": {"name": "Onboarding", "gid": "123"},
                "project": {"gid": _UNIT_GID},
            }
        ]
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "memberships": [memberships_data],  # list column — Polars Object dtype
            }
        )

        with (
            patch(
                "autom8_asana.models.business.activity.get_classifier",
                return_value=_make_classifier(
                    {"Onboarding": AccountActivity.ACTIVATING}
                ),
            ),
            patch(
                "autom8_asana.models.business.activity.extract_section_name",
                return_value="Onboarding",
            ),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        assert result[0]["pipeline_section"] == "Onboarding"
        assert result[0]["account_activity"] == "activating"

    # ------------------------------------------------------------------
    # Branch 5: Classifier returns None (unknown section)
    # ------------------------------------------------------------------

    def test_unknown_section_classified_as_none_skipped(self) -> None:
        """Section name that classifier doesn't recognize is skipped."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "section": ["UNKNOWN_SECTION"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"UNKNOWN_SECTION": None}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert result == []

    # ------------------------------------------------------------------
    # Branch 6: Active-only filter (SD-02)
    # ------------------------------------------------------------------

    def test_inactive_section_filtered_out(self) -> None:
        """Section classified as INACTIVE is not persisted (SD-02)."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "section": ["Paused"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Paused": AccountActivity.INACTIVE}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert result == []

    def test_ignored_section_filtered_out(self) -> None:
        """Section classified as IGNORED is not persisted (SD-02)."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "section": ["Templates"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Templates": AccountActivity.IGNORED}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert result == []

    def test_active_section_persisted(self) -> None:
        """Section classified as ACTIVE is persisted (SD-02)."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "section": ["Active"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Active": AccountActivity.ACTIVE}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        assert result[0]["account_activity"] == "active"

    def test_activating_section_persisted(self) -> None:
        """Section classified as ACTIVATING is persisted (SD-02)."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "section": ["Implementing"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Implementing": AccountActivity.ACTIVATING}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        assert result[0]["account_activity"] == "activating"

    # ------------------------------------------------------------------
    # Output shape validation
    # ------------------------------------------------------------------

    def test_output_entry_keys_and_types(self) -> None:
        """Every entry dict has the expected 6 keys with correct types."""
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "vertical": ["chiropractic"],
                "section": ["Active"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Active": AccountActivity.ACTIVE}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        entry = result[0]

        # All expected keys present
        assert set(entry.keys()) == _EXPECTED_KEYS

        # Type checks
        assert isinstance(entry["phone"], str)
        assert isinstance(entry["vertical"], str)
        assert isinstance(entry["pipeline_type"], str)
        assert isinstance(entry["account_activity"], str)
        assert isinstance(entry["pipeline_section"], str)
        assert isinstance(entry["stage_entered_at"], str)

        # Value checks
        assert entry["phone"] == "+15551234567"
        assert entry["vertical"] == "chiropractic"
        assert entry["pipeline_type"] == "unit"
        assert entry["account_activity"] == "active"
        assert entry["pipeline_section"] == "Active"

    def test_vertical_defaults_to_empty_string(self) -> None:
        """Row with no vertical column or None vertical defaults to ''."""
        # No vertical column at all
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "section": ["Active"],
            }
        )

        with patch(
            "autom8_asana.models.business.activity.get_classifier",
            return_value=_make_classifier({"Active": AccountActivity.ACTIVE}),
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unit")

        assert len(result) == 1
        assert result[0]["vertical"] == ""

    # ------------------------------------------------------------------
    # Classifier fallback
    # ------------------------------------------------------------------

    def test_unknown_entity_type_warns_and_skips(self) -> None:
        """Entity type not recognized by get_classifier logs warning and returns empty.

        Per TC-5: silent UNIT_CLASSIFIER fallback replaced with warn+skip
        to eliminate incorrect classification of process pipeline rows.
        """
        df = pl.DataFrame(
            {
                "office_phone": ["+15551234567"],
                "section": ["Active"],
            }
        )

        with (
            patch(
                "autom8_asana.models.business.activity.get_classifier",
                return_value=None,  # Unknown entity type
            ) as mock_get,
            patch(
                "autom8_asana.services.gid_push.logger",
            ) as mock_logger,
        ):
            result = extract_status_from_dataframe(df, _UNIT_GID, "unknown_entity")

        # get_classifier was called with the entity type
        mock_get.assert_called_once_with("unknown_entity")
        # Warning was logged
        mock_logger.warning.assert_called_once_with(
            "process_pipeline_no_classifier",
            extra={
                "entity_type": "unknown_entity",
                "project_gid": _UNIT_GID,
            },
        )
        # No entries returned (warn+skip, not fallback)
        assert result == []
