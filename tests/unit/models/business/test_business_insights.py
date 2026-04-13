"""Tests for Business.get_insights_async method.

Per Story 3.1: Tests for Business entity insights integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.errors import InsightsValidationError
from autom8_asana.models.business.business import Business


class TestBusinessGetInsightsAsync:
    """Tests for Business.get_insights_async convenience method."""

    @pytest.fixture
    def mock_data_client(self) -> MagicMock:
        """Create a mock DataServiceClient."""
        client = MagicMock()
        client.get_insights_async = AsyncMock()
        return client

    @pytest.fixture
    def mock_insights_response(self) -> MagicMock:
        """Create a mock InsightsResponse."""
        response = MagicMock()
        response.data = [{"metric": "spend", "value": 1000.0}]
        response.metadata = MagicMock()
        return response

    @pytest.fixture
    def valid_business(self) -> Business:
        """Create a Business with valid office_phone and vertical."""
        return Business(
            gid="123",
            name="Acme Corp",
            custom_fields=[
                {"gid": "cf1", "name": "Office Phone", "text_value": "+17705551234"},
                {
                    "gid": "cf2",
                    "name": "Vertical",
                    "enum_value": {"gid": "v1", "name": "Chiropractic"},
                },
            ],
        )

    @pytest.mark.asyncio
    async def test_valid_business_returns_insights_response(
        self,
        valid_business: Business,
        mock_data_client: MagicMock,
        mock_insights_response: MagicMock,
    ) -> None:
        """Valid business with office_phone and vertical returns InsightsResponse."""
        mock_data_client.get_insights_async.return_value = mock_insights_response

        result = await valid_business.get_insights_async(mock_data_client)

        assert result is mock_insights_response
        mock_data_client.get_insights_async.assert_called_once_with(
            factory="account",
            office_phone="+17705551234",
            vertical="Chiropractic",
        )

    @pytest.mark.asyncio
    async def test_missing_office_phone_raises_validation_error(
        self,
        mock_data_client: MagicMock,
    ) -> None:
        """Business without office_phone raises InsightsValidationError."""
        business = Business(
            gid="123",
            name="Acme Corp",
            custom_fields=[
                {
                    "gid": "cf2",
                    "name": "Vertical",
                    "enum_value": {"gid": "v1", "name": "Chiropractic"},
                },
            ],
        )

        with pytest.raises(InsightsValidationError) as exc_info:
            await business.get_insights_async(mock_data_client)

        assert exc_info.value.field == "office_phone"
        assert "office_phone" in str(exc_info.value)
        mock_data_client.get_insights_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_vertical_raises_validation_error(
        self,
        mock_data_client: MagicMock,
    ) -> None:
        """Business without vertical raises InsightsValidationError."""
        business = Business(
            gid="123",
            name="Acme Corp",
            custom_fields=[
                {"gid": "cf1", "name": "Office Phone", "text_value": "+17705551234"},
            ],
        )

        with pytest.raises(InsightsValidationError) as exc_info:
            await business.get_insights_async(mock_data_client)

        assert exc_info.value.field == "vertical"
        assert "vertical" in str(exc_info.value)
        mock_data_client.get_insights_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_string_office_phone_raises_validation_error(
        self,
        mock_data_client: MagicMock,
    ) -> None:
        """Business with empty string office_phone raises InsightsValidationError."""
        business = Business(
            gid="123",
            name="Acme Corp",
            custom_fields=[
                {"gid": "cf1", "name": "Office Phone", "text_value": ""},
                {
                    "gid": "cf2",
                    "name": "Vertical",
                    "enum_value": {"gid": "v1", "name": "Chiropractic"},
                },
            ],
        )

        with pytest.raises(InsightsValidationError) as exc_info:
            await business.get_insights_async(mock_data_client)

        assert exc_info.value.field == "office_phone"
        mock_data_client.get_insights_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_string_vertical_raises_validation_error(
        self,
        mock_data_client: MagicMock,
    ) -> None:
        """Business with empty string vertical raises InsightsValidationError.

        Note: EnumField returns the enum_value name, so an empty string would
        require a specially crafted enum_value. Testing None vertical case.
        """
        business = Business(
            gid="123",
            name="Acme Corp",
            custom_fields=[
                {"gid": "cf1", "name": "Office Phone", "text_value": "+17705551234"},
                {
                    "gid": "cf2",
                    "name": "Vertical",
                    "enum_value": None,  # None enum_value -> None vertical
                },
            ],
        )

        with pytest.raises(InsightsValidationError) as exc_info:
            await business.get_insights_async(mock_data_client)

        assert exc_info.value.field == "vertical"
        mock_data_client.get_insights_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_kwargs_passed_through_to_client(
        self,
        valid_business: Business,
        mock_data_client: MagicMock,
        mock_insights_response: MagicMock,
    ) -> None:
        """Additional kwargs are passed through to client.get_insights_async."""
        mock_data_client.get_insights_async.return_value = mock_insights_response

        await valid_business.get_insights_async(
            mock_data_client,
            factory="campaigns",
            period="t30",
            metrics=["spend", "impressions"],
            refresh=True,
        )

        mock_data_client.get_insights_async.assert_called_once_with(
            factory="campaigns",
            office_phone="+17705551234",
            vertical="Chiropractic",
            period="t30",
            metrics=["spend", "impressions"],
            refresh=True,
        )

    @pytest.mark.asyncio
    async def test_default_factory_is_account(
        self,
        valid_business: Business,
        mock_data_client: MagicMock,
        mock_insights_response: MagicMock,
    ) -> None:
        """Default factory is 'account' when not specified."""
        mock_data_client.get_insights_async.return_value = mock_insights_response

        await valid_business.get_insights_async(mock_data_client)

        call_kwargs = mock_data_client.get_insights_async.call_args[1]
        assert call_kwargs["factory"] == "account"

    @pytest.mark.asyncio
    async def test_period_not_included_when_none(
        self,
        valid_business: Business,
        mock_data_client: MagicMock,
        mock_insights_response: MagicMock,
    ) -> None:
        """Period is not included in call when None (uses client default)."""
        mock_data_client.get_insights_async.return_value = mock_insights_response

        await valid_business.get_insights_async(mock_data_client, period=None)

        call_kwargs = mock_data_client.get_insights_async.call_args[1]
        assert "period" not in call_kwargs

    @pytest.mark.asyncio
    async def test_period_included_when_specified(
        self,
        valid_business: Business,
        mock_data_client: MagicMock,
        mock_insights_response: MagicMock,
    ) -> None:
        """Period is included in call when explicitly specified."""
        mock_data_client.get_insights_async.return_value = mock_insights_response

        await valid_business.get_insights_async(mock_data_client, period="lifetime")

        call_kwargs = mock_data_client.get_insights_async.call_args[1]
        assert call_kwargs["period"] == "lifetime"
