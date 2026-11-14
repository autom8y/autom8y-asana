"""The single definition of Unit activity, one fixture per case of the rule.

Cases: a marketing Unit read from its Offers; a non-marketing Unit read from its
own section by legacy's lists; Engaged counted apart from activating; a Unit with
no products; an unknown section; plus the name fold and the frame column.
"""

from __future__ import annotations

import polars as pl
import pytest

from autom8_asana.models.business.activity import (
    LEGACY_UNIT_SECTIONS,
    OFFER_CLASSIFIER,
    AccountActivity,
)
from autom8_asana.models.business.unit_activity import (
    PRODUCTS_NULL_SHARE_LIMIT,
    SETTLED_OFFER_SECTIONS,
    UNIT_ACTIVITY_COLUMN,
    UnitActivityInputError,
    classify_offer_section,
    classify_unit_activity,
    classify_unit_section,
    is_marketing_unit,
    snake_lower,
    with_unit_activity,
)

MARKETING = ["Meta Marketing"]
NON_MARKETING = ["Videography"]
NO_PRODUCTS: list[str] = []

PHONE_A = "+15550100001"
PHONE_B = "+15550100002"


def _unit(products, section, offers=()):
    return classify_unit_activity(products=products, unit_section=section, offer_sections=offers)


# ---------------------------------------------------------------------------
# The fold
# ---------------------------------------------------------------------------


class TestSnakeLowerFold:
    @pytest.mark.parametrize(
        ("raw", "folded"),
        [
            ("OPTIMIZE - Human Review", "optimize_human_review"),
            ("Month 1", "month_1"),
            ("No  Start", "no_start"),
            ("  Sales Process  ", "sales_process"),
            ("NEW.LAUNCH-REVIEW", "new_launch_review"),
            ("tab\tand\u00a0nbsp", "tab_and_nbsp"),
            ("REJECTIONS / REVIEW", "rejections_/_review"),
            ("sales_process", "sales_process"),
        ],
    )
    def test_folds_separators_case_and_outer_runs(self, raw: str, folded: str) -> None:
        assert snake_lower(raw) == folded

    def test_fold_is_idempotent(self) -> None:
        once = snake_lower("OPTIMIZE - Human Review")
        assert snake_lower(once) == once

    def test_slash_without_spaces_does_not_match_the_spaced_name(self) -> None:
        """Legacy's own limit, kept: the fold does not touch a slash."""
        assert snake_lower("REJECTIONS/REVIEW") != snake_lower("REJECTIONS / REVIEW")


# ---------------------------------------------------------------------------
# The marketing test
# ---------------------------------------------------------------------------


class TestIsMarketingUnit:
    @pytest.mark.parametrize("products", [["Meta Marketing"], ["MARKETING"], ["x", "marketing"]])
    def test_a_product_naming_marketing_in_any_case_is_marketing(self, products) -> None:
        assert is_marketing_unit(products) is True

    def test_products_without_marketing_are_not_marketing(self) -> None:
        assert is_marketing_unit(["Videography", "Website"]) is False

    def test_an_empty_list_is_a_unit_with_no_products(self) -> None:
        assert is_marketing_unit([]) is False

    def test_a_missing_products_value_is_unknown(self) -> None:
        assert is_marketing_unit(None) is None

    def test_a_bare_string_is_one_product_not_its_characters(self) -> None:
        assert is_marketing_unit("Marketing") is True
        assert is_marketing_unit("m") is False


# ---------------------------------------------------------------------------
# Case 1: a marketing Unit is read from its Offers
# ---------------------------------------------------------------------------


class TestMarketingUnitReadsItsOffers:
    def test_highest_offer_group_wins(self) -> None:
        offers = ["INACTIVE", "IMPLEMENTING", "ACTIVE", "COMPLETE"]
        assert _unit(MARKETING, "Unengaged", offers) is AccountActivity.ACTIVE

    def test_activating_offer_beats_inactive_and_ignored(self) -> None:
        offers = ["INACTIVE", "IMPLEMENTING", "Sales Process"]
        assert _unit(MARKETING, "Active", offers) is AccountActivity.ACTIVATING

    def test_own_section_is_not_read(self) -> None:
        """An Active own section does not lift a Unit whose Offers are inactive."""
        assert _unit(MARKETING, "Active", ["INACTIVE"]) is AccountActivity.INACTIVE

    def test_only_ignored_offers_give_ignored(self) -> None:
        assert _unit(MARKETING, "Onboarding", ["COMPLETE", "PLAYS"]) is AccountActivity.IGNORED

    def test_no_offers_gives_no_activity(self) -> None:
        assert _unit(MARKETING, "Active", []) is None

    def test_offer_sections_are_folded(self) -> None:
        assert _unit(MARKETING, None, ["optimize-human review"]) is AccountActivity.ACTIVE


# ---------------------------------------------------------------------------
# Case 2: a non-marketing Unit is read from its own section, by legacy's lists
# ---------------------------------------------------------------------------


class TestNonMarketingUnitReadsItsOwnSection:
    @pytest.mark.parametrize(
        ("section", "expected"),
        [
            ("Month 1", AccountActivity.ACTIVE),
            ("Consulting", AccountActivity.ACTIVE),
            ("Active", AccountActivity.ACTIVE),
            ("Onboarding", AccountActivity.ACTIVATING),
            ("Implementing", AccountActivity.ACTIVATING),
            ("Delayed", AccountActivity.ACTIVATING),
            ("Preview", AccountActivity.ACTIVATING),
            ("Unengaged", AccountActivity.INACTIVE),
            ("Scheduled", AccountActivity.INACTIVE),
            ("Paused", AccountActivity.INACTIVE),
            ("Cancelled", AccountActivity.INACTIVE),
            ("No Start", AccountActivity.INACTIVE),
            ("Templates", AccountActivity.IGNORED),
        ],
    )
    def test_each_legacy_list_name_takes_its_group(self, section, expected) -> None:
        assert _unit(NON_MARKETING, section, ["ACTIVE"]) is expected

    def test_offers_are_not_read(self) -> None:
        assert (
            _unit(NON_MARKETING, "Paused", ["ACTIVE", "IMPLEMENTING"]) is AccountActivity.INACTIVE
        )

    def test_own_section_is_folded(self) -> None:
        assert _unit(NON_MARKETING, "MONTH-1", []) is AccountActivity.ACTIVE

    @pytest.mark.parametrize("section", ["Next Steps", "Account Review", "Account Error"])
    def test_names_legacy_lists_nowhere_give_no_activity(self, section) -> None:
        assert _unit(NON_MARKETING, section, []) is None


# ---------------------------------------------------------------------------
# Case 3: Engaged is counted apart from activating
# ---------------------------------------------------------------------------


class TestEngagedIsCountedApart:
    def test_engaged_is_in_legacys_inactive_list_only(self) -> None:
        holding = [a for a, names in LEGACY_UNIT_SECTIONS.items() if "Engaged" in names]
        assert holding == [AccountActivity.INACTIVE]

    def test_a_non_marketing_unit_in_engaged_is_inactive_never_activating(self) -> None:
        assert _unit(NON_MARKETING, "Engaged", []) is AccountActivity.INACTIVE

    def test_a_marketing_unit_in_engaged_takes_its_offers(self) -> None:
        assert _unit(MARKETING, "Engaged", ["ACTIVE"]) is AccountActivity.ACTIVE
        assert _unit(MARKETING, "Engaged", ["INACTIVE"]) is AccountActivity.INACTIVE
        assert _unit(MARKETING, "Engaged", []) is None


# ---------------------------------------------------------------------------
# Case 4: a Unit with no products
# ---------------------------------------------------------------------------


class TestUnitWithNoProducts:
    def test_no_products_reads_its_own_section_like_a_non_marketing_unit(self) -> None:
        assert _unit(NO_PRODUCTS, "Onboarding", ["ACTIVE"]) is AccountActivity.ACTIVATING
        assert _unit(NO_PRODUCTS, "Engaged", ["ACTIVE"]) is AccountActivity.INACTIVE

    def test_a_missing_products_value_gives_no_activity(self) -> None:
        assert _unit(None, "Active", ["ACTIVE"]) is None


# ---------------------------------------------------------------------------
# Case 5: an unknown section
# ---------------------------------------------------------------------------


class TestUnknownSection:
    def test_unknown_own_section_gives_no_activity(self) -> None:
        assert _unit(NON_MARKETING, "Some New Section", []) is None
        assert _unit(NON_MARKETING, None, []) is None

    def test_unknown_offer_sections_are_skipped(self) -> None:
        assert _unit(MARKETING, None, ["Some New Section", "INACTIVE"]) is AccountActivity.INACTIVE

    def test_only_unknown_offer_sections_give_no_activity(self) -> None:
        assert _unit(MARKETING, "Active", ["Some New Section", None, ""]) is None


# ---------------------------------------------------------------------------
# The Offer read: OFFER_CLASSIFIER plus the settled names
# ---------------------------------------------------------------------------


class TestOfferRead:
    def test_agrees_with_offer_classifier_on_every_name_it_knows(self) -> None:
        for activity in AccountActivity:
            for name in OFFER_CLASSIFIER.sections_for(activity):
                assert classify_offer_section(name) is activity, name

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("LAUNCH ERROR", AccountActivity.ACTIVATING),
            ("SYSTEM ERROR", AccountActivity.ACTIVE),
            ("ADD NEW OFFER", AccountActivity.IGNORED),
        ],
    )
    def test_settled_names_take_their_settled_group(self, name, expected) -> None:
        assert classify_offer_section(name) is expected
        assert SETTLED_OFFER_SECTIONS[name] is expected

    def test_settled_names_do_not_change_offer_classifier(self) -> None:
        for name in SETTLED_OFFER_SECTIONS:
            assert OFFER_CLASSIFIER.classify(name) is None, name

    @pytest.mark.parametrize(
        ("live_name", "expected"),
        [
            ("PLAYS", AccountActivity.IGNORED),
            ("ACTIVATING", AccountActivity.ACTIVATING),
            ("ACCOUNT ERROR", AccountActivity.INACTIVE),
            ("IMPLEMENTING", AccountActivity.ACTIVATING),
            ("PERFORMANCE CONCERNS", AccountActivity.IGNORED),
            ("AWAITING REP UPDATE", AccountActivity.INACTIVE),
            ("ADD NEW OFFER", AccountActivity.IGNORED),
            ("NEW LAUNCH REVIEW", AccountActivity.ACTIVATING),
            ("OPTIMIZE - Human Review", AccountActivity.ACTIVE),
            ("STAGING", AccountActivity.ACTIVE),
            ("STAGED", AccountActivity.ACTIVE),
            ("ACTIVE", AccountActivity.ACTIVE),
            ("MANUAL", AccountActivity.ACTIVE),
            ("INACTIVE", AccountActivity.INACTIVE),
            ("Sales Process", AccountActivity.IGNORED),
            ("COMPLETE", AccountActivity.IGNORED),
        ],
    )
    def test_every_live_offer_section_has_a_group(self, live_name, expected) -> None:
        assert classify_offer_section(live_name) is expected

    def test_unit_read_and_offer_read_are_separate_lists(self) -> None:
        assert classify_unit_section("ACTIVATING") is None
        assert classify_offer_section("Onboarding") is None


# ---------------------------------------------------------------------------
# The frame column
# ---------------------------------------------------------------------------


def _units(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "office_phone": pl.Utf8,
            "vertical": pl.Utf8,
            "section": pl.Utf8,
            "products": pl.List(pl.Utf8),
        },
        orient="row",
    )


def _offers(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={"office_phone": pl.Utf8, "vertical": pl.Utf8, "section": pl.Utf8},
        orient="row",
    )


class TestWithUnitActivity:
    def test_adds_the_column_for_every_case(self) -> None:
        units = _units(
            [
                (PHONE_A, "dental", "Engaged", MARKETING),
                (PHONE_A, "chiropractic", "Engaged", NON_MARKETING),
                (PHONE_B, "dental", "Onboarding", NO_PRODUCTS),
                (PHONE_B, "chiropractic", "Active", None),
                (None, "dental", "Active", MARKETING),
            ]
        )
        offers = _offers(
            [
                (PHONE_A, "dental", "INACTIVE"),
                (PHONE_A, "dental", "IMPLEMENTING"),
                (PHONE_A, "chiropractic", "ACTIVE"),
            ]
        )

        out = with_unit_activity(units, offers)

        assert out[UNIT_ACTIVITY_COLUMN].to_list() == [
            "activating",
            "inactive",
            "activating",
            None,
            None,
        ]
        assert out.drop(UNIT_ACTIVITY_COLUMN).equals(units)

    def test_offers_join_on_phone_and_vertical(self) -> None:
        units = _units([(PHONE_A, "dental", "Paused", MARKETING)])
        other_vertical = _offers([(PHONE_A, "chiropractic", "ACTIVE")])
        same_vertical = _offers([(PHONE_A, "dental", "ACTIVE")])

        assert with_unit_activity(units, other_vertical)[UNIT_ACTIVITY_COLUMN].to_list() == [None]
        assert with_unit_activity(units, same_vertical)[UNIT_ACTIVITY_COLUMN].to_list() == [
            "active"
        ]

    def test_a_null_vertical_joins_a_null_vertical(self) -> None:
        units = _units([(PHONE_A, None, None, MARKETING)])
        offers = _offers([(PHONE_A, None, "STAGED")])
        assert with_unit_activity(units, offers)[UNIT_ACTIVITY_COLUMN].to_list() == ["active"]

    def test_an_empty_offer_frame_is_refused(self) -> None:
        units = _units([(PHONE_A, "dental", "Active", NON_MARKETING)])
        with pytest.raises(UnitActivityInputError, match="no rows"):
            with_unit_activity(units, _offers([]))

    def test_a_unit_frame_without_products_is_refused(self) -> None:
        units = _units([(PHONE_A, "dental", "Active", MARKETING)]).drop("products")
        offers = _offers([(PHONE_A, "dental", "ACTIVE")])
        with pytest.raises(UnitActivityInputError, match="products"):
            with_unit_activity(units, offers)

    def test_an_offer_frame_without_section_is_refused(self) -> None:
        units = _units([(PHONE_A, "dental", "Active", MARKETING)])
        offers = _offers([(PHONE_A, "dental", "ACTIVE")]).drop("section")
        with pytest.raises(UnitActivityInputError, match="section"):
            with_unit_activity(units, offers)


def _null_share_frames(null_products: int, total: int) -> tuple[pl.DataFrame, pl.DataFrame]:
    """``total`` non-marketing Units in Active; the first ``null_products`` are null."""
    rows = [
        (f"+1555010{i:04d}", "dental", "Active", None if i < null_products else NON_MARKETING)
        for i in range(total)
    ]
    return _units(rows), _offers([(PHONE_A, "dental", "ACTIVE")])


class TestProductsNullShareLimit:
    def test_the_limit_is_half(self) -> None:
        assert PRODUCTS_NULL_SHARE_LIMIT == 0.5

    def test_a_present_all_null_column_is_refused(self) -> None:
        units, offers = _null_share_frames(null_products=4, total=4)
        assert units["products"].null_count() == units.height
        with pytest.raises(UnitActivityInputError, match="products is null for 4 of 4 units"):
            with_unit_activity(units, offers)

    @pytest.mark.parametrize(
        ("null_products", "refused"),
        [(49, False), (50, False), (51, True)],
        ids=["just-under", "exactly-half-is-read", "just-over"],
    )
    def test_refused_only_when_more_than_half_are_null(
        self, null_products: int, refused: bool
    ) -> None:
        units, offers = _null_share_frames(null_products=null_products, total=100)
        if refused:
            with pytest.raises(UnitActivityInputError, match="more than the 50% limit"):
                with_unit_activity(units, offers)
            return
        out = with_unit_activity(units, offers)
        activity = out[UNIT_ACTIVITY_COLUMN].to_list()
        assert activity[:null_products] == [None] * null_products
        assert activity[null_products:] == ["active"] * (100 - null_products)

    def test_an_empty_unit_frame_is_refused(self) -> None:
        """Zero Units would push a snapshot with no Unit rows, so it is refused."""
        units, offers = _null_share_frames(null_products=0, total=0)
        with pytest.raises(UnitActivityInputError, match="the unit frame has no rows"):
            with_unit_activity(units, offers)

    def test_a_one_unit_frame_is_read(self) -> None:
        units, offers = _null_share_frames(null_products=0, total=1)
        assert with_unit_activity(units, offers)[UNIT_ACTIVITY_COLUMN].to_list() == ["active"]

    def test_empty_lists_are_not_null(self) -> None:
        """A Unit with no products is a resolved value, so it never counts toward the limit."""
        rows = [(f"+1555010{i:04d}", "dental", "Active", NO_PRODUCTS) for i in range(3)]
        rows.append((PHONE_B, "dental", "Active", None))
        out = with_unit_activity(_units(rows), _offers([(PHONE_A, "dental", "ACTIVE")]))
        assert out[UNIT_ACTIVITY_COLUMN].to_list() == ["active", "active", "active", None]
