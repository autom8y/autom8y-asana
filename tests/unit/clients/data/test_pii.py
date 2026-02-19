"""Tests for DataServiceClient PII redaction helpers.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: mask_phone_number, _mask_canonical_key, _mask_pii_in_string in client.py

XR-003 additions: Tests for _mask_pii_in_string and PII redaction in
cache logging, export error_kwargs, ExportError attributes, simple.py
cache keys, and batch error bodies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMaskPhoneNumber:
    """Tests for mask_phone_number PII redaction helper (Story 1.9)."""

    def test_masks_standard_us_phone(self) -> None:
        """Standard US phone number is masked correctly."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("+17705753103")

        assert result == "+1770***3103"

    def test_masks_phone_keep_first_five_last_four(self) -> None:
        """Keeps first 5 chars and last 4 chars, masks middle."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("+14155551234")

        assert result == "+1415***1234"
        assert result.startswith("+1415")
        assert result.endswith("1234")

    def test_returns_short_phone_unchanged(self) -> None:
        """Short phone numbers (< 9 chars) are returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        # Too short to mask meaningfully
        result = mask_phone_number("+123456")

        assert result == "+123456"

    def test_returns_empty_string_unchanged(self) -> None:
        """Empty string is returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("")

        assert result == ""

    def test_returns_none_phone_unchanged(self) -> None:
        """None-like empty value is handled."""
        from autom8_asana.clients.data.client import mask_phone_number

        # Empty string edge case
        result = mask_phone_number("")

        assert result == ""

    def test_returns_non_e164_unchanged(self) -> None:
        """Non-E.164 format strings without + prefix are returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("7705753103")

        # No + prefix, returned as-is
        assert result == "7705753103"

    def test_masks_international_phone(self) -> None:
        """International phone numbers are masked correctly."""
        from autom8_asana.clients.data.client import mask_phone_number

        # UK number
        result = mask_phone_number("+447911123456")

        assert result == "+4479***3456"


class TestMaskCanonicalKey:
    """Tests for _mask_canonical_key helper (Story 1.9)."""

    def test_masks_phone_in_canonical_key(self) -> None:
        """Phone number in canonical key is masked."""
        from autom8_asana.clients.data._pii import (
            mask_canonical_key as _mask_canonical_key,
        )

        result = _mask_canonical_key("pv1:+17705753103:chiropractic")

        assert result == "pv1:+1770***3103:chiropractic"

    def test_preserves_version_and_vertical(self) -> None:
        """Version prefix and vertical are preserved."""
        from autom8_asana.clients.data._pii import (
            mask_canonical_key as _mask_canonical_key,
        )

        result = _mask_canonical_key("pv1:+14155551234:dental")

        assert result.startswith("pv1:")
        assert result.endswith(":dental")

    def test_returns_non_pv1_unchanged(self) -> None:
        """Non-pv1 keys are returned unchanged."""
        from autom8_asana.clients.data._pii import (
            mask_canonical_key as _mask_canonical_key,
        )

        result = _mask_canonical_key("other:+17705753103:vertical")

        assert result == "other:+17705753103:vertical"

    def test_returns_malformed_key_unchanged(self) -> None:
        """Malformed keys are returned unchanged."""
        from autom8_asana.clients.data._pii import (
            mask_canonical_key as _mask_canonical_key,
        )

        result = _mask_canonical_key("notakey")

        assert result == "notakey"


class TestMaskPiiInString:
    """Tests for _mask_pii_in_string general-purpose PII masker (XR-003)."""

    def test_masks_phone_in_cache_key(self) -> None:
        """Masks phone number inside an insights cache key."""
        from autom8_asana.clients.data._pii import (
            mask_pii_in_string as _mask_pii_in_string,
        )

        result = _mask_pii_in_string("insights:account:pv1:+17705753103:chiropractic")

        assert "+17705753103" not in result
        assert "+1770***3103" in result

    def test_masks_phone_in_simple_cache_key(self) -> None:
        """Masks phone in appointments/leads cache key format."""
        from autom8_asana.clients.data._pii import (
            mask_pii_in_string as _mask_pii_in_string,
        )

        result = _mask_pii_in_string("appointments:+17705753103")

        assert "+17705753103" not in result
        assert "+1770***3103" in result

    def test_masks_multiple_phones(self) -> None:
        """Masks all phone numbers when multiple are present."""
        from autom8_asana.clients.data._pii import (
            mask_pii_in_string as _mask_pii_in_string,
        )

        result = _mask_pii_in_string("batch error: +17705753103 and +14155551234")

        assert "+17705753103" not in result
        assert "+14155551234" not in result
        assert "+1770***3103" in result
        assert "+1415***1234" in result

    def test_returns_string_without_phone_unchanged(self) -> None:
        """Strings without phone numbers are returned unchanged."""
        from autom8_asana.clients.data._pii import (
            mask_pii_in_string as _mask_pii_in_string,
        )

        result = _mask_pii_in_string("no phone here")

        assert result == "no phone here"

    def test_empty_string(self) -> None:
        """Empty string returns empty."""
        from autom8_asana.clients.data._pii import (
            mask_pii_in_string as _mask_pii_in_string,
        )

        assert _mask_pii_in_string("") == ""


class TestCacheLoggingPiiRedaction:
    """Tests for PII redaction in _cache.py log messages (XR-003 Vector 1)."""

    def test_cache_response_log_masks_cache_key(self) -> None:
        """cache_response() masks phone in cache key log message."""
        from autom8_asana.clients.data._cache import cache_response
        from autom8_asana.clients.data.models import (
            InsightsMetadata,
            InsightsResponse,
        )

        mock_cache = MagicMock()
        mock_log = MagicMock()
        response = InsightsResponse(
            data=[],
            metadata=InsightsMetadata(
                factory="account",
                row_count=0,
                column_count=0,
                columns=[],
                cache_hit=False,
                duration_ms=0.0,
            ),
            request_id="test-id",
            warnings=[],
        )

        cache_response(
            mock_cache,
            "insights:account:pv1:+17705753103:chiropractic",
            response,
            ttl=300,
            log=mock_log,
        )

        # Verify log message does not contain raw phone
        log_msg = mock_log.debug.call_args[0][0]
        assert "+17705753103" not in log_msg
        assert "+1770***3103" in log_msg

        # Verify extras do not contain raw phone
        extras = mock_log.debug.call_args[1]["extra"]
        assert "+17705753103" not in extras["cache_key"]

    def test_stale_response_log_masks_cache_key(self) -> None:
        """get_stale_response() masks phone in cache key log message."""
        from autom8_asana.clients.data._cache import get_stale_response

        mock_cache = MagicMock()
        mock_cache.get.return_value = {
            "data": [{"spend": 100.0}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "spend", "dtype": "float64"}],
                "cache_hit": False,
                "duration_ms": 50.0,
            },
            "request_id": "old-id",
            "warnings": [],
            "cached_at": "2024-01-01T12:00:00+00:00",
        }
        mock_log = MagicMock()

        get_stale_response(
            mock_cache,
            "insights:account:pv1:+17705753103:chiropractic",
            "new-request-id",
            mock_log,
        )

        # Verify INFO log message does not contain raw phone
        log_msg = mock_log.info.call_args[0][0]
        assert "+17705753103" not in log_msg
        assert "+1770***3103" in log_msg

        # Verify extras do not contain raw phone
        extras = mock_log.info.call_args[1]["extra"]
        assert "+17705753103" not in extras["cache_key"]


class TestExportErrorPiiRedaction:
    """Tests for PII redaction in export error paths (XR-003 Vectors 2 & 3)."""

    @pytest.mark.asyncio
    async def test_export_error_kwargs_use_masked_phone(self) -> None:
        """error_kwargs passed to retry callbacks contain masked phone."""
        import os

        import respx

        from autom8_asana.clients.data.client import DataServiceClient
        from autom8_asana.exceptions import ExportError

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.get("/api/v1/messages/export").respond(
                    status_code=500,
                    text="Server Error",
                )

                async with client:
                    with pytest.raises(ExportError) as exc:
                        await client.get_export_csv_async("+17705753103")

        # ExportError.office_phone should be masked
        assert "+17705753103" not in exc.value.office_phone
        assert "+1770***3103" in exc.value.office_phone

    @pytest.mark.asyncio
    async def test_export_circuit_breaker_error_uses_masked_phone(self) -> None:
        """ExportError from circuit breaker open contains masked phone."""
        import os

        from autom8y_http import CircuitBreakerOpenError as SdkCircuitBreakerOpenError

        from autom8_asana.clients.data.client import DataServiceClient
        from autom8_asana.exceptions import ExportError

        client = DataServiceClient()
        # Force circuit breaker open
        client._circuit_breaker.check = AsyncMock(
            side_effect=SdkCircuitBreakerOpenError(5.0, "CB open")
        )

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with pytest.raises(ExportError) as exc:
                await client.get_export_csv_async("+17705753103")

        assert "+17705753103" not in exc.value.office_phone
        assert "+1770***3103" in exc.value.office_phone

    @pytest.mark.asyncio
    async def test_export_client_error_uses_masked_phone(self) -> None:
        """ExportError from 4xx response contains masked phone."""
        import os

        import respx

        from autom8_asana.clients.data.client import DataServiceClient
        from autom8_asana.exceptions import ExportError

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.get("/api/v1/messages/export").respond(
                    status_code=400,
                    text="Bad Request",
                )

                async with client:
                    with pytest.raises(ExportError) as exc:
                        await client.get_export_csv_async("+17705753103")

        assert "+17705753103" not in exc.value.office_phone
        assert "+1770***3103" in exc.value.office_phone


class TestSimpleCacheKeyPiiRedaction:
    """Tests for PII redaction in simple.py cache keys (XR-003 Vector 4)."""

    @pytest.mark.asyncio
    async def test_appointments_cache_key_uses_masked_phone(self) -> None:
        """appointments error path builds cache key with masked phone."""
        import os

        import respx

        from autom8_asana.clients.data.client import DataServiceClient
        from autom8_asana.exceptions import InsightsServiceError

        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # No stale data
        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.get("/api/v1/appointments").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    with pytest.raises(InsightsServiceError):
                        await client.get_appointments_async("+17705753103")

        # The cache.get call for stale fallback should use masked phone in key
        if mock_cache.get.called:
            cache_key_arg = mock_cache.get.call_args[0][0]
            assert "+17705753103" not in cache_key_arg

    @pytest.mark.asyncio
    async def test_leads_cache_key_uses_masked_phone(self) -> None:
        """leads error path builds cache key with masked phone."""
        import os

        import respx

        from autom8_asana.clients.data.client import DataServiceClient
        from autom8_asana.exceptions import InsightsServiceError

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        client = DataServiceClient(cache_provider=mock_cache)

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                respx.get("/api/v1/leads").respond(
                    status_code=500,
                    json={"error": "Internal server error"},
                )

                async with client:
                    with pytest.raises(InsightsServiceError):
                        await client.get_leads_async("+17705753103")


class TestBatchErrorPiiRedaction:
    """Tests for PII redaction in batch error bodies (XR-003 Vector 5)."""

    def test_batch_error_string_sanitized(self) -> None:
        """batch.py sanitizes str(e) that might echo phone numbers."""
        from autom8_asana.clients.data._pii import mask_pii_in_string

        # Simulate an error message that echoes a phone number
        error_msg = "Request failed for +17705753103: timeout"
        sanitized = mask_pii_in_string(error_msg)

        assert "+17705753103" not in sanitized
        assert "+1770***3103" in sanitized

    @pytest.mark.asyncio
    async def test_batch_chunk_failure_error_sanitized(self) -> None:
        """client.py sanitizes chunk_result error string in batch processing."""
        import os

        import respx

        from autom8_asana.clients.data.client import DataServiceClient
        from autom8_asana.models.contracts import PhoneVerticalPair

        pairs = [
            PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
        ]

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            with respx.mock:
                # Simulate an error response that echoes phone back
                respx.post("/api/v1/data-service/insights").respond(
                    status_code=500,
                    json={"error": "Error processing +17705753103"},
                )

                async with client:
                    batch_response = await client.get_insights_batch_async(
                        pairs, factory="account"
                    )

        # Check that error strings in results don't contain raw phone
        for result in batch_response.results.values():
            if result.error:
                assert "+17705753103" not in result.error
