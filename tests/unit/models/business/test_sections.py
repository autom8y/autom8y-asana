"""Unit tests for OfferSection enum."""

from __future__ import annotations

from autom8_asana.models.business.sections import OfferSection


class TestOfferSection:
    """Test OfferSection enum values and behavior."""

    def test_active_value(self) -> None:
        assert OfferSection.ACTIVE.value == "1143843662099256"

    def test_is_str(self) -> None:
        """OfferSection values can be used directly as strings."""
        assert isinstance(OfferSection.ACTIVE, str)
        assert OfferSection.ACTIVE == "1143843662099256"

    def test_usable_in_string_formatting(self) -> None:
        """Can be used in f-strings and string operations via .value."""
        path = f"dataframes/project/sections/{OfferSection.ACTIVE.value}.parquet"
        assert "1143843662099256" in path
