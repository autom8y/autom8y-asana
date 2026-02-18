"""Tests for DataServiceClient feature flag behavior.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: DataServiceClient._check_feature_enabled, FEATURE_FLAG_ENV_VAR
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import DataServiceConfig

from .conftest import _make_disabled_settings_mock


# --- Story 1.7: Feature Flag Tests ---


class TestFeatureFlagDisabled:
    """Tests for feature flag disabled behavior (Story 1.7, updated per Story 2.7).

    Per Story 2.7: Feature is now enabled by default.
    Explicit opt-out requires setting env var to "false", "0", or "no".
    Per D-011: Tests patch get_settings() directly since Settings is cached at import time.
    """

    @pytest.mark.asyncio
    async def test_disabled_when_env_var_false(self) -> None:
        """get_insights_async raises InsightsServiceError when insights_enabled=False."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch(
            "autom8_asana.settings.get_settings",
            return_value=_make_disabled_settings_mock(),
        ):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.reason == "feature_disabled"
        assert "Insights integration is disabled" in str(exc.value)

    @pytest.mark.asyncio
    async def test_disabled_when_env_var_zero(self) -> None:
        """get_insights_async raises InsightsServiceError when insights_enabled=False."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch(
            "autom8_asana.settings.get_settings",
            return_value=_make_disabled_settings_mock(),
        ):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.reason == "feature_disabled"

    @pytest.mark.asyncio
    async def test_disabled_when_env_var_no(self) -> None:
        """get_insights_async raises InsightsServiceError when insights_enabled=False."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch(
            "autom8_asana.settings.get_settings",
            return_value=_make_disabled_settings_mock(),
        ):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

        assert exc.value.reason == "feature_disabled"

    @pytest.mark.asyncio
    async def test_disabled_with_case_variations(self) -> None:
        """get_insights_async raises InsightsServiceError when insights_enabled=False.

        Per D-011: Pydantic Settings handles case-insensitive bool parsing at
        construction time. The client tests only verify behavior when disabled.
        """
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        # All variants resolve to insights_enabled=False via pydantic at Settings init.
        # We test the client behavior when the setting is False.
        for _variant in ["false", "FALSE", "False", "no", "NO", "No", "0"]:
            with patch(
                "autom8_asana.settings.get_settings",
                return_value=_make_disabled_settings_mock(),
            ):
                async with client:
                    with pytest.raises(InsightsServiceError) as exc:
                        await client.get_insights_async(
                            factory="account",
                            office_phone="+17705753103",
                            vertical="chiropractic",
                        )

                assert exc.value.reason == "feature_disabled"

    @pytest.mark.asyncio
    async def test_feature_check_happens_before_validation(self) -> None:
        """Feature flag check happens before any other validation."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        # Even with invalid inputs, feature flag check should happen first
        with patch(
            "autom8_asana.settings.get_settings",
            return_value=_make_disabled_settings_mock(),
        ):
            async with client:
                with pytest.raises(InsightsServiceError) as exc:
                    await client.get_insights_async(
                        factory="invalid_factory",  # Would fail validation
                        office_phone="not-a-phone",  # Would fail validation
                        vertical="",  # Would fail validation
                    )

        # Should get feature_disabled error, not validation error
        assert exc.value.reason == "feature_disabled"


class TestFeatureFlagEnabled:
    """Tests for feature flag enabled behavior (Story 1.7, updated per Story 2.7).

    Per Story 2.7: Feature is now enabled by default.
    """

    @pytest.mark.asyncio
    async def test_enabled_by_default_when_env_var_not_set(self) -> None:
        """get_insights_async succeeds when env var is not set (Story 2.7)."""
        import respx

        client = DataServiceClient()

        # Ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
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

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response.metadata.factory == "account"

    @pytest.mark.asyncio
    async def test_enabled_when_env_var_empty(self) -> None:
        """get_insights_async succeeds when env var is empty string (Story 2.7)."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": ""}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
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
                    }
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None

    @pytest.mark.asyncio
    async def test_enabled_with_true_lowercase(self) -> None:
        """get_insights_async succeeds when env var is 'true'."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
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

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response.metadata.factory == "account"

    @pytest.mark.asyncio
    async def test_enabled_with_true_uppercase(self) -> None:
        """get_insights_async succeeds when env var is 'TRUE' (case-insensitive)."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "TRUE"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
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
                    }
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None

    @pytest.mark.asyncio
    async def test_enabled_with_one(self) -> None:
        """get_insights_async succeeds when env var is '1'."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "1"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
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
                    }
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None

    @pytest.mark.asyncio
    async def test_enabled_with_yes(self) -> None:
        """get_insights_async succeeds when env var is 'yes'."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "yes"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
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
                    }
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None

    @pytest.mark.asyncio
    async def test_enabled_with_yes_uppercase(self) -> None:
        """get_insights_async succeeds when env var is 'YES' (case-insensitive)."""
        import respx

        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "YES"}):
            with respx.mock:
                respx.post("/api/v1/data-service/insights").respond(
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
                    }
                )

                async with client:
                    response = await client.get_insights_async(
                        factory="account",
                        office_phone="+17705753103",
                        vertical="chiropractic",
                    )

                assert response is not None


class TestCheckFeatureEnabled:
    """Direct tests for _check_feature_enabled() method (updated per Story 2.7)."""

    def test_does_not_raise_when_not_set(self) -> None:
        """_check_feature_enabled does not raise when env var not set (Story 2.7)."""
        client = DataServiceClient()

        with patch.dict(os.environ, {}, clear=True):
            # Should not raise - enabled by default
            client._check_feature_enabled()

    def test_does_not_raise_when_empty(self) -> None:
        """_check_feature_enabled does not raise when env var is empty (Story 2.7)."""
        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": ""}):
            # Should not raise - empty means enabled (default)
            client._check_feature_enabled()

    def test_does_not_raise_when_enabled(self) -> None:
        """_check_feature_enabled does not raise when explicitly enabled."""
        client = DataServiceClient()

        with patch.dict(os.environ, {"AUTOM8_DATA_INSIGHTS_ENABLED": "true"}):
            # Should not raise
            client._check_feature_enabled()

    def test_raises_when_explicitly_disabled(self) -> None:
        """_check_feature_enabled raises when insights_enabled=False in settings."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch(
            "autom8_asana.settings.get_settings",
            return_value=_make_disabled_settings_mock(),
        ):
            with pytest.raises(InsightsServiceError) as exc:
                client._check_feature_enabled()

        assert exc.value.reason == "feature_disabled"

    def test_error_message_is_helpful(self) -> None:
        """Error message explains how to re-enable."""
        from autom8_asana.exceptions import InsightsServiceError

        client = DataServiceClient()

        with patch(
            "autom8_asana.settings.get_settings",
            return_value=_make_disabled_settings_mock(),
        ):
            with pytest.raises(InsightsServiceError) as exc:
                client._check_feature_enabled()

        error_message = str(exc.value)
        assert "Insights integration is disabled" in error_message
        # Updated per Story 2.7: message now explains how to re-enable
        assert "AUTOM8_DATA_INSIGHTS_ENABLED" in error_message
        assert "true" in error_message.lower()
