"""Two-sided contract for the R-03 phone field annotations.

OfficePhoneField (enrollment intent, leads consumer) and LeadPhoneField
(landing receipt Booking) carry an E.164 pattern. A well-formed value passes;
a malformed value is refused. The NewType wrap used at the construction sites
is identity at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from autom8y_api_schemas import (
    LeadPhone,
    LeadPhoneField,
    OfficePhone,
    OfficePhoneField,
)
from pydantic import TypeAdapter, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

VALID = "+15555550100"  # obviously fake E.164


class TestPhoneFieldContract:
    @pytest.mark.parametrize("field", [OfficePhoneField, LeadPhoneField])
    def test_valid_e164_passes(self, field: Any) -> None:
        assert TypeAdapter(field).validate_python(VALID) == VALID

    @pytest.mark.parametrize("field", [OfficePhoneField, LeadPhoneField])
    @pytest.mark.parametrize("bad", ["555-0100", "not-a-phone"])
    def test_malformed_refused(self, field: Any, bad: str) -> None:
        with pytest.raises(ValidationError):
            TypeAdapter(field).validate_python(bad)

    @pytest.mark.parametrize("wrap", [OfficePhone, LeadPhone])
    def test_newtype_wrap_is_identity_at_runtime(self, wrap: Callable[[str], str]) -> None:
        wrapped = wrap(VALID)
        assert wrapped == VALID
        assert isinstance(wrapped, str)
