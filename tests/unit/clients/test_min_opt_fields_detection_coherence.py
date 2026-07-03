"""Fetch >= detector coherence property (the #195 planner>=gate pattern for fetch-vs-detector).

Detection consumes membership subfields off a task that a narrow-first ``get_async``
may have cached. If the fetch-supply set (``_MINIMUM_OPT_FIELDS``) ever drops below the
detection denominator (``DETECTION_MEMBERSHIP_OPT_FIELDS``), a narrow-first cache entry
silently starves detection -- exactly the opt_fields-blind cache poisoning this fix cured.

The two constants are authored INDEPENDENTLY (the supply guarantee is not built by
importing the denominator), so this property is a genuine drift bridge rather than a
tautology: if a future detector begins consuming a new membership subfield, the author
extends ``DETECTION_MEMBERSHIP_OPT_FIELDS`` and this test goes RED until the supply set
is widened to match.
"""

from __future__ import annotations

from autom8_asana.clients.tasks import _MINIMUM_OPT_FIELDS
from autom8_asana.models.business.fields import (
    DETECTION_MEMBERSHIP_OPT_FIELDS,
    DETECTION_OPT_FIELDS,
)


class TestFetchSupplyCoversDetectionDenominator:
    def test_minimum_opt_fields_superset_of_detection_denominator(self) -> None:
        """Every membership subfield detection consumes is guaranteed by the narrow-fetch
        minimum set -- so a narrow-first cache entry cannot starve detection."""
        assert DETECTION_MEMBERSHIP_OPT_FIELDS <= _MINIMUM_OPT_FIELDS, (
            "fetch-supply set _MINIMUM_OPT_FIELDS dropped below the detection "
            f"denominator; missing: {DETECTION_MEMBERSHIP_OPT_FIELDS - _MINIMUM_OPT_FIELDS}"
        )

    def test_denominator_is_reflected_in_detection_field_set(self) -> None:
        """The denominator is runtime-load-bearing: it is genuinely present in the
        detection opt_fields tuple (not a test-only shadow constant)."""
        assert set(DETECTION_OPT_FIELDS) >= DETECTION_MEMBERSHIP_OPT_FIELDS

    def test_denominator_holds_exactly_the_two_get_path_detection_subfields(self) -> None:
        """Anchor the denominator to its two get()-path consumers; section.name is
        deliberately excluded (a LIST/sweep + explicit offer/unit-fetch consumer)."""
        assert (
            frozenset({"memberships.project.gid", "memberships.project.name"})
            == DETECTION_MEMBERSHIP_OPT_FIELDS
        )
        assert "memberships.section.name" not in _MINIMUM_OPT_FIELDS
