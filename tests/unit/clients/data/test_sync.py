"""Tests for DataServiceClient sync wrapper infrastructure.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: DataServiceClient.get_insights, _run_sync, sync context manager
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig

# --- Story 2.6: Sync Wrapper Tests ---


@pytest.mark.usefixtures("enable_insights_feature")
class TestSyncWrapper:
    """Tests for get_insights sync wrapper and sync context manager."""

    def test_sync_wrapper_works(self) -> None:
        """Sync method works from sync context."""
        import respx

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                json={
                    "data": [{"spend": 100.0}],
                    "metadata": {
                        "factory": "account",
                        "row_count": 1,
                        "column_count": 1,
                        "columns": [{"name": "spend", "dtype": "float64"}],
                        "cache_hit": False,
                        "duration_ms": 50.0,
                    },
                }
            )

            # Note: use sync context manager (not async)
            with client:
                response = client.get_insights(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )
                assert response.metadata.factory == "account"
                assert response.metadata.row_count == 1

    async def test_sync_wrapper_raises_in_async_context(self) -> None:
        """Sync wrapper raises SyncInAsyncContextError in async context."""
        from autom8_asana.errors import SyncInAsyncContextError

        client = DataServiceClient()

        async with client:
            with pytest.raises(SyncInAsyncContextError) as exc:
                client.get_insights(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        assert "get_insights" in str(exc.value)
        assert "get_insights_async" in str(exc.value)

    def test_sync_wrapper_passes_all_parameters(self) -> None:
        """Sync method passes all parameters to async method."""
        from datetime import date

        import respx

        client = DataServiceClient()
        captured_body: dict[str, Any] = {}

        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json

            captured_body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "data": [],
                    "metadata": {
                        "factory": "account",
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "cache_hit": False,
                        "duration_ms": 10.0,
                    },
                },
            )

        with respx.mock:
            respx.post("/api/v1/data-service/insights").mock(side_effect=capture_request)

            with client:
                client.get_insights(
                    factory="account",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                    period="t30",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    metrics=["spend", "leads"],
                    dimensions=["day"],
                    groups=["platform"],
                    break_down=["campaign"],
                    refresh=True,
                    filters={"platform": "facebook"},
                )

        # Verify all parameters were passed through in new autom8_data format
        assert captured_body["frame_type"] == "business"
        assert captured_body["phone_vertical_pairs"] == [
            {"phone": "+17705753103", "vertical": "chiropractic"}
        ]
        assert captured_body["period"] == "T30"
        assert captured_body["start_date"] == "2024-01-01"
        assert captured_body["end_date"] == "2024-12-31"
        assert captured_body["metrics"] == ["spend", "leads"]
        assert captured_body["dimensions"] == ["day"]
        assert captured_body["groups"] == ["platform"]
        assert captured_body["break_down"] == ["campaign"]
        assert captured_body["refresh"] is True
        assert captured_body["filters"] == {"platform": "facebook"}

    def test_sync_context_manager_works(self) -> None:
        """Sync context manager (__enter__/__exit__) works in sync context."""
        client = DataServiceClient()

        # Should not raise
        with client as entered:
            assert entered is client
            assert client.is_initialized is False  # lazy init

    async def test_sync_exit_raises_in_async_context(self) -> None:
        """Sync __exit__ raises SyncInAsyncContextError in async context."""
        from autom8_asana.errors import SyncInAsyncContextError

        client = DataServiceClient()

        # Enter works (just returns self)
        entered = client.__enter__()
        assert entered is client

        # Exit should raise in async context
        with pytest.raises(SyncInAsyncContextError) as exc:
            client.__exit__(None, None, None)

        assert "__exit__" in str(exc.value)
        assert "__aexit__" in str(exc.value)

    def test_sync_wrapper_propagates_validation_errors(self) -> None:
        """Sync wrapper propagates InsightsValidationError correctly."""
        from autom8_asana.errors import InsightsValidationError

        client = DataServiceClient()

        with client:
            with pytest.raises(InsightsValidationError) as exc:
                client.get_insights(
                    factory="invalid_factory",
                    office_phone="+17705753103",
                    vertical="chiropractic",
                )

        assert "Invalid factory" in str(exc.value)

    def test_sync_wrapper_propagates_service_errors(self) -> None:
        """Sync wrapper propagates InsightsServiceError correctly."""
        import respx

        from autom8_asana.errors import InsightsServiceError

        client = DataServiceClient()

        with respx.mock:
            respx.post("/api/v1/data-service/insights").respond(
                status_code=500,
                json={"error": "Internal server error"},
            )

            with client:
                with pytest.raises(InsightsServiceError) as exc:
                    client.get_insights(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.status_code == 500
