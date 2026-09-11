"""The OFFER-grain referent: derived from the classifier, equivalent to the aggregation.

Three things are proven here, and nothing else:

1. The referent is DERIVED from ``OFFER_CLASSIFIER`` -- every registered section
   classifies inside the declared vocabulary, the three activating sections land in
   the activating bucket, and nothing else does.
2. ``collapse()`` is EQUIVALENT to ``Business.max_offer_activity`` on the same
   inputs (G6 cross-method equivalence), including the ordering edge cases.
3. Under this referent the smoke is TWO-SIDED: a healthy pipe activates, a broken
   pipe is refused and names the break. Same mechanism, different facts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from autom8_asana.lifecycle.activation_referent import (
    OFFER_AGGREGATION_RULE_NAME,
    OFFER_REFERENT_NAME,
    offer_grain_hook,
    offer_grain_referent,
)
from autom8_asana.lifecycle.activation_smoke import (
    DECISION_KIND_NOT_APPLICABLE,
    DECISION_KIND_PERMITTED,
    VocabularyViolation,
)
from autom8_asana.models.business.activity import (
    ACTIVITY_PRIORITY,
    OFFER_CLASSIFIER,
    AccountActivity,
)
from autom8_asana.models.business.business import Business
from autom8_asana.models.business.offer import Offer
from autom8_asana.models.business.unit import Unit, UnitHolder

ACTIVATING_SECTIONS = ("ACTIVATING", "IMPLEMENTING", "NEW LAUNCH REVIEW")
NON_ACTIVATING_SECTIONS = ("ACTIVE", "STAGED", "INACTIVE", "ACCOUNT ERROR", "Sales Process")

_FIXED_NOW = datetime(2026, 9, 11, 15, 0, tzinfo=UTC)


def _clock() -> datetime:
    return _FIXED_NOW


def _business_with_offer_activities(*unit_offer_activities: list) -> Business:
    """Mirror of the #431 test helper: units each carrying offers with given activities."""
    units = []
    for acts in unit_offer_activities:
        unit = MagicMock(spec=Unit)
        unit.offers = [MagicMock(spec=Offer, account_activity=a) for a in acts]
        units.append(unit)
    holder = MagicMock(spec=UnitHolder)
    holder.units = units
    biz = Business(gid="biz-referent-equiv", name="Referent Equivalence")
    biz._unit_holder = holder
    return biz


# ---------------------------------------------------------------------------
# 1. Derived from the classifier
# ---------------------------------------------------------------------------


def test_referent_is_named_for_the_offer_project_and_grain() -> None:
    referent = offer_grain_referent()
    assert referent.name == OFFER_REFERENT_NAME == f"offers-{OFFER_CLASSIFIER.project_gid}"
    assert referent.grain == "offer"
    assert referent.project_gid == OFFER_CLASSIFIER.project_gid == "1143843662099250"
    assert referent.aggregation_rule is not None
    assert referent.aggregation_rule.name == OFFER_AGGREGATION_RULE_NAME


def test_every_registered_offer_section_classifies_inside_the_vocabulary() -> None:
    """No registered section can raise VocabularyViolation: the vocabulary is derived."""
    referent = offer_grain_referent()
    registered = OFFER_CLASSIFIER.sections_for(*AccountActivity)
    assert registered, "the classifier registers at least one section"
    for section in registered:
        bucket = referent.classify(section)
        assert bucket in referent.bucket_set, (section, bucket)


@pytest.mark.parametrize("section", ACTIVATING_SECTIONS)
def test_the_activating_group_is_the_activating_bucket(section: str) -> None:
    referent = offer_grain_referent()
    assert referent.is_activating(referent.classify(section)), section


@pytest.mark.parametrize("section", NON_ACTIVATING_SECTIONS)
def test_nothing_outside_the_activating_group_is_activating(section: str) -> None:
    referent = offer_grain_referent()
    bucket = referent.classify(section)
    assert bucket is not None, f"{section!r} is registered in OFFER_CLASSIFIER"
    assert not referent.is_activating(bucket), section


def test_an_unregistered_section_is_unclassified_not_a_violation() -> None:
    referent = offer_grain_referent()
    assert referent.classify("NOT A SECTION ANYONE DECLARED") is None


def test_classification_is_case_insensitive_like_the_classifier() -> None:
    referent = offer_grain_referent()
    assert referent.classify("activating") == referent.classify("ACTIVATING") == "activating"


# ---------------------------------------------------------------------------
# 2. Equivalent to Business.max_offer_activity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unit_offer_activities",
    [
        ([AccountActivity.ACTIVATING],),
        ([AccountActivity.ACTIVATING], [AccountActivity.INACTIVE, AccountActivity.ACTIVE]),
        ([AccountActivity.IGNORED, AccountActivity.INACTIVE], [AccountActivity.ACTIVATING]),
        ([AccountActivity.INACTIVE], [AccountActivity.IGNORED]),
        (list(ACTIVITY_PRIORITY)[::-1],),
        ([AccountActivity.ACTIVE, AccountActivity.ACTIVE],),
    ],
)
def test_collapse_equals_max_offer_activity_on_the_same_offers(unit_offer_activities) -> None:
    """G6: same inputs, two methods, one answer."""
    referent = offer_grain_referent()
    business = _business_with_offer_activities(*unit_offer_activities)
    buckets = [a.value for acts in unit_offer_activities for a in acts]

    via_property = business.max_offer_activity
    via_referent = referent.collapse(buckets)

    assert via_property is not None
    assert via_referent == via_property.value


def test_collapse_ordering_is_activity_priority_and_nothing_else() -> None:
    referent = offer_grain_referent()
    everything = [a.value for a in ACTIVITY_PRIORITY]
    assert referent.collapse(everything) == ACTIVITY_PRIORITY[0].value == "active"
    assert referent.collapse(["ignored", "inactive"]) == "inactive"
    assert referent.collapse(["ignored", "activating"]) == "activating"


def test_collapse_never_mints_a_bucket_outside_the_vocabulary() -> None:
    referent = offer_grain_referent()
    for pair in (("activating", "active"), ("inactive", "ignored"), ("active", "ignored")):
        assert referent.collapse(list(pair)) in referent.bucket_set


def test_a_foreign_bucket_is_refused_by_the_referent_not_silently_collapsed() -> None:
    """A rule is re-checked by the referent; a stray reading cannot pass through."""
    referent = offer_grain_referent()
    with pytest.raises((VocabularyViolation, ValueError)):
        referent.collapse(["activating", "onboarding"])  # a UNIT-grain word, not an offer one


# ---------------------------------------------------------------------------
# 3. Two-sided under the ruled referent
# ---------------------------------------------------------------------------


def _healthy_facts() -> dict:
    return {
        "office_name": "an office the pipe named",
        "failure_probe": {"office_name": "an office the pipe named", "kind": "no_slots"},
        "pipe_proof_at": _FIXED_NOW - timedelta(minutes=10),
    }


def test_crossing_into_activating_is_observed_with_the_referent_name() -> None:
    hook = offer_grain_hook(clock=_clock)
    transition = hook.observe(
        subject_gid="offer-1", to_section="ACTIVATING", from_section="Sales Process"
    )
    assert transition is not None
    assert transition.referent_name == OFFER_REFERENT_NAME
    assert transition.grain == "offer"
    assert transition.to_bucket == "activating"
    assert transition.from_bucket == "ignored"
    assert transition.observed_at == _FIXED_NOW


@pytest.mark.parametrize(
    ("from_section", "to_section"),
    [
        ("ACTIVATING", "IMPLEMENTING"),  # within the bucket: not an activation
        ("IMPLEMENTING", "ACTIVE"),  # leaving the bucket: not an activation
        ("STAGED", "ACTIVE"),  # never near the bucket
    ],
)
def test_moves_that_do_not_enter_activating_are_not_observed(from_section, to_section) -> None:
    hook = offer_grain_hook(clock=_clock)
    assert (
        hook.observe(subject_gid="offer-1", to_section=to_section, from_section=from_section)
        is None
    )


def test_reentering_activating_from_active_is_an_activation_by_the_hook_law() -> None:
    """The hook counts any crossing INTO the bucket. A regression from ACTIVE is a crossing.

    Pinned deliberately: if the epoch later rules that re-entry is not an activation,
    this test is the line that changes, not a silent behaviour.
    """
    hook = offer_grain_hook(clock=_clock)
    transition = hook.observe(subject_gid="offer-1", to_section="ACTIVATING", from_section="ACTIVE")
    assert transition is not None and transition.from_bucket == "active"


def test_healthy_pipe_activates_under_the_offer_referent() -> None:
    hook = offer_grain_hook(clock=_clock)
    decision = hook.guard(
        subject_gid="offer-1",
        to_section="ACTIVATING",
        from_section="Sales Process",
        facts=_healthy_facts(),
    )
    assert decision.permitted and decision.applicable
    assert decision.kind == DECISION_KIND_PERMITTED
    assert decision.referent_name == OFFER_REFERENT_NAME
    assert decision.report is not None and decision.report.passed


@pytest.mark.parametrize(
    ("broken_fact", "expected_check", "expected_kind"),
    [
        ("office_name", "office_named", "office_unresolved"),
        ("failure_probe", "failure_path_names_office", "failure_probe_absent"),
        ("pipe_proof_at", "pipe_proof_fresh", "pipe_proof_absent"),
    ],
)
def test_broken_pipe_is_refused_and_names_the_break(
    broken_fact, expected_check, expected_kind
) -> None:
    facts = _healthy_facts()
    del facts[broken_fact]
    hook = offer_grain_hook(clock=_clock)
    decision = hook.guard(
        subject_gid="offer-1", to_section="ACTIVATING", from_section="Sales Process", facts=facts
    )
    assert not decision.permitted and decision.applicable
    assert decision.refused_check == expected_check
    assert decision.kind == expected_kind


def test_the_two_sides_differ_only_in_facts() -> None:
    """Same hook, same transition, same referent; only the facts differ."""
    hook = offer_grain_hook(clock=_clock)
    kwargs = {"subject_gid": "offer-1", "to_section": "ACTIVATING", "from_section": "STAGED"}
    healthy = hook.guard(**kwargs, facts=_healthy_facts())
    broken = hook.guard(**kwargs, facts={})
    assert healthy.permitted and not broken.permitted
    assert healthy.transition == broken.transition


def test_a_non_activation_move_does_not_gate_even_with_no_facts() -> None:
    hook = offer_grain_hook(clock=_clock)
    decision = hook.guard(subject_gid="offer-1", to_section="ACTIVE", from_section="IMPLEMENTING")
    assert decision.permitted and not decision.applicable
    assert decision.kind == DECISION_KIND_NOT_APPLICABLE
