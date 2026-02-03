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

    def test_from_name_exact(self) -> None:
        assert OfferSection.from_name("ACTIVE") is OfferSection.ACTIVE

    def test_from_name_case_insensitive(self) -> None:
        assert OfferSection.from_name("active") is OfferSection.ACTIVE
        assert OfferSection.from_name("Active") is OfferSection.ACTIVE

    def test_from_name_not_found(self) -> None:
        assert OfferSection.from_name("nonexistent") is None
