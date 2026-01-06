"""Unit tests for PhoneVerticalPair model.

Per TDD-INSIGHTS-001 Section 4.1: Tests for PhoneVerticalPair model including
E.164 validation, canonical_key property, tuple unpacking, hashing, and
from_business factory method.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from autom8_asana.exceptions import InsightsValidationError
from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair


class TestPhoneVerticalPairConstruction:
    """Tests for PhoneVerticalPair model construction."""

    def test_valid_construction(self) -> None:
        """PhoneVerticalPair accepts valid E.164 phone and vertical."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        assert pvp.office_phone == "+17705753103"
        assert pvp.vertical == "chiropractic"

    def test_strips_whitespace(self) -> None:
        """PhoneVerticalPair strips whitespace from inputs."""
        pvp = PhoneVerticalPair(
            office_phone=" +17705753103 ",
            vertical=" chiropractic ",
        )
        assert pvp.office_phone == "+17705753103"
        assert pvp.vertical == "chiropractic"


class TestE164Validation:
    """Tests for E.164 phone number validation."""

    @pytest.mark.parametrize(
        "phone",
        [
            "+17705753103",  # US number
            "+442071234567",  # UK number
            "+8613812345678",  # China number
            "+81312345678",  # Japan number
            "+91",  # Minimum: + and 2 digits (country + 1)
            "+123456789012345",  # Maximum: 15 digits
        ],
    )
    def test_valid_e164_formats(self, phone: str) -> None:
        """E.164 validation accepts valid phone formats."""
        pvp = PhoneVerticalPair(office_phone=phone, vertical="test")
        assert pvp.office_phone == phone

    @pytest.mark.parametrize(
        "phone,reason",
        [
            ("17705753103", "missing plus sign"),
            ("+07705753103", "starts with zero after plus"),
            ("+1", "too short - only 1 digit after plus"),
            ("+1234567890123456", "too long - 16 digits"),
            ("+1-770-575-3103", "contains dashes"),
            ("+1 770 575 3103", "contains spaces"),
            ("+1(770)5753103", "contains parentheses"),
            ("", "empty string"),
            ("+", "only plus sign"),
            ("+abc12345", "contains letters"),
        ],
    )
    def test_invalid_e164_formats(self, phone: str, reason: str) -> None:
        """E.164 validation rejects invalid phone formats."""
        with pytest.raises(ValidationError) as exc_info:
            PhoneVerticalPair(office_phone=phone, vertical="test")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("office_phone",)
        assert "Invalid E.164 format" in str(errors[0]["msg"])


class TestCanonicalKey:
    """Tests for canonical_key property."""

    def test_canonical_key_format(self) -> None:
        """canonical_key returns pv1:{phone}:{vertical} format."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        assert pvp.canonical_key == "pv1:+17705753103:chiropractic"

    def test_canonical_key_different_values(self) -> None:
        """canonical_key reflects different phone/vertical combinations."""
        pvp1 = PhoneVerticalPair(office_phone="+17705753103", vertical="dental")
        pvp2 = PhoneVerticalPair(office_phone="+12125551234", vertical="chiropractic")

        assert pvp1.canonical_key == "pv1:+17705753103:dental"
        assert pvp2.canonical_key == "pv1:+12125551234:chiropractic"
        assert pvp1.canonical_key != pvp2.canonical_key

    def test_canonical_key_normalizes_vertical_to_lowercase(self) -> None:
        """canonical_key normalizes vertical to lowercase for case-insensitive matching.

        Regression test: gid_lookup index builds with lowercase verticals,
        so canonical_key must also lowercase to ensure lookups match.
        """
        # Mixed case vertical
        pvp_mixed = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="Chiropractic",
        )
        # All uppercase vertical
        pvp_upper = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="CHIROPRACTIC",
        )
        # Already lowercase vertical
        pvp_lower = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )

        # All should produce the same canonical_key (lowercase vertical)
        expected_key = "pv1:+17705753103:chiropractic"
        assert pvp_mixed.canonical_key == expected_key
        assert pvp_upper.canonical_key == expected_key
        assert pvp_lower.canonical_key == expected_key

        # All three canonical keys should be equal
        assert pvp_mixed.canonical_key == pvp_upper.canonical_key == pvp_lower.canonical_key


class TestTupleUnpacking:
    """Tests for tuple unpacking backward compatibility."""

    def test_iter_returns_phone_vertical(self) -> None:
        """iter() returns phone and vertical in order."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        items = list(pvp)
        assert items == ["+17705753103", "chiropractic"]

    def test_tuple_unpacking(self) -> None:
        """Tuple unpacking works: phone, vertical = pvp."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        phone, vertical = pvp
        assert phone == "+17705753103"
        assert vertical == "chiropractic"

    def test_getitem_index_zero(self) -> None:
        """pvp[0] returns office_phone."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        assert pvp[0] == "+17705753103"

    def test_getitem_index_one(self) -> None:
        """pvp[1] returns vertical."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        assert pvp[1] == "chiropractic"

    def test_getitem_index_error(self) -> None:
        """pvp[2] raises IndexError."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        with pytest.raises(IndexError):
            _ = pvp[2]

    def test_negative_index(self) -> None:
        """Negative indices work per Python tuple semantics."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        assert pvp[-1] == "chiropractic"
        assert pvp[-2] == "+17705753103"


class TestHashing:
    """Tests for hashing and dict key usage."""

    def test_hash_is_stable(self) -> None:
        """Same phone/vertical produces same hash."""
        pvp1 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        pvp2 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        assert hash(pvp1) == hash(pvp2)

    def test_hash_differs_for_different_values(self) -> None:
        """Different phone/vertical produces different hash."""
        pvp1 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        pvp2 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="dental",
        )
        assert hash(pvp1) != hash(pvp2)

    def test_usable_as_dict_key(self) -> None:
        """PhoneVerticalPair can be used as dict key."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        data = {pvp: "test_value"}
        assert data[pvp] == "test_value"

    def test_usable_in_set(self) -> None:
        """PhoneVerticalPair can be used in set."""
        pvp1 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        pvp2 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        pvp3 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="dental",
        )

        pvp_set = {pvp1, pvp2, pvp3}
        # pvp1 and pvp2 are equal, so set should have 2 elements
        assert len(pvp_set) == 2


class TestImmutability:
    """Tests for frozen model behavior."""

    def test_cannot_modify_office_phone(self) -> None:
        """Modifying office_phone raises ValidationError."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        with pytest.raises(ValidationError):
            pvp.office_phone = "+12125551234"  # type: ignore[misc]

    def test_cannot_modify_vertical(self) -> None:
        """Modifying vertical raises ValidationError."""
        pvp = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        with pytest.raises(ValidationError):
            pvp.vertical = "dental"  # type: ignore[misc]


class TestFromBusiness:
    """Tests for from_business class method."""

    def test_from_business_success(self) -> None:
        """from_business creates PhoneVerticalPair from Business entity."""
        # Mock Business with office_phone and vertical attributes
        business = MagicMock()
        business.office_phone = "+17705753103"
        business.vertical = "chiropractic"

        pvp = PhoneVerticalPair.from_business(business)

        assert pvp.office_phone == "+17705753103"
        assert pvp.vertical == "chiropractic"

    def test_from_business_missing_office_phone(self) -> None:
        """from_business raises InsightsValidationError when office_phone is None."""
        business = MagicMock()
        business.office_phone = None
        business.vertical = "chiropractic"

        with pytest.raises(InsightsValidationError) as exc_info:
            PhoneVerticalPair.from_business(business)

        assert "office_phone is required" in str(exc_info.value)
        assert exc_info.value.field == "office_phone"

    def test_from_business_empty_office_phone(self) -> None:
        """from_business raises InsightsValidationError when office_phone is empty."""
        business = MagicMock()
        business.office_phone = ""
        business.vertical = "chiropractic"

        with pytest.raises(InsightsValidationError) as exc_info:
            PhoneVerticalPair.from_business(business)

        assert "office_phone is required" in str(exc_info.value)
        assert exc_info.value.field == "office_phone"

    def test_from_business_missing_vertical(self) -> None:
        """from_business raises InsightsValidationError when vertical is None."""
        business = MagicMock()
        business.office_phone = "+17705753103"
        business.vertical = None

        with pytest.raises(InsightsValidationError) as exc_info:
            PhoneVerticalPair.from_business(business)

        assert "vertical is required" in str(exc_info.value)
        assert exc_info.value.field == "vertical"

    def test_from_business_empty_vertical(self) -> None:
        """from_business raises InsightsValidationError when vertical is empty."""
        business = MagicMock()
        business.office_phone = "+17705753103"
        business.vertical = ""

        with pytest.raises(InsightsValidationError) as exc_info:
            PhoneVerticalPair.from_business(business)

        assert "vertical is required" in str(exc_info.value)
        assert exc_info.value.field == "vertical"


class TestEquality:
    """Tests for equality comparison."""

    def test_equal_instances(self) -> None:
        """Two PhoneVerticalPairs with same values are equal."""
        pvp1 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        pvp2 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        assert pvp1 == pvp2

    def test_not_equal_different_phone(self) -> None:
        """PhoneVerticalPairs with different phones are not equal."""
        pvp1 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        pvp2 = PhoneVerticalPair(
            office_phone="+12125551234",
            vertical="chiropractic",
        )
        assert pvp1 != pvp2

    def test_not_equal_different_vertical(self) -> None:
        """PhoneVerticalPairs with different verticals are not equal."""
        pvp1 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        pvp2 = PhoneVerticalPair(
            office_phone="+17705753103",
            vertical="dental",
        )
        assert pvp1 != pvp2
