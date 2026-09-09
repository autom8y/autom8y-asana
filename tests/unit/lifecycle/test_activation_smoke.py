"""Unit tests for the referent-injected onboarding activation smoke.

Three things are under test, in descending order of what they protect:

1. THE REFERENT IS INJECTED. Four-plus competing ``activating`` vocabularies are
   constructed here and driven through the SAME mechanism, including two that
   govern one project and classify ``Engaged``/``Scheduled`` OPPOSITELY. The
   mechanism yields opposite verdicts and privileges neither. A build that
   hard-coded one vocabulary would fail ``test_opposing_vocabularies_*``.
2. THE GATE IS TWO-SIDED. A healthy pipe permits; a broken pipe refuses and names
   the failing check and its kind. Both directions are asserted, pipe-free: the
   two sides differ only in the injected ``facts``.
3. BINDING IS BY NAME, NEVER BY POSITION. The sibling defect in ASR
   (``readiness.py:992``, conditionally-built list + identity-less record) is
   reproduced against this mechanism and shown to be unconstructable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autom8_asana.lifecycle.activation_smoke import (
    OK_KIND,
    ActivationDecision,
    ActivationSmokeHook,
    AggregationRule,
    AggregationRuleAbsent,
    CheckOutcome,
    LifecycleReferent,
    ProbeVerdict,
    SmokeCheck,
    SmokeReport,
    VocabularyViolation,
    default_pipe_checks,
)
from autom8_asana.models.business.activity import OFFER_CLASSIFIER, UNIT_CLASSIFIER

FIXED_NOW = datetime(2026, 9, 9, 12, 0, 0, tzinfo=UTC)


def _clock() -> datetime:
    return FIXED_NOW


def _matcher_from(classifier) -> callable:  # noqa: ANN001 -- test helper over a frozen dataclass
    def _match(section_name: str) -> str | None:
        result = classifier.classify(section_name)
        return None if result is None else str(result.value)

    return _match


def _mapping_matcher(mapping: dict[str, str]):
    """Case-insensitive section -> bucket matcher built from a literal dict."""
    lowered = {key.lower(): value for key, value in mapping.items()}

    def _match(section_name: str) -> str | None:
        return lowered.get(section_name.lower())

    return _match


# ---------------------------------------------------------------------------
# The four-plus vocabularies, each built as an INJECTED referent
# ---------------------------------------------------------------------------

FOUR_BUCKETS = frozenset({"active", "activating", "inactive", "ignored"})


def offers_referent() -> LifecycleReferent:
    """Vocabulary 1: offers grain, project 1143843662099250."""
    return LifecycleReferent(
        name="offers-1143843662099250",
        grain="offer",
        project_gid="1143843662099250",
        bucket_set=FOUR_BUCKETS,
        activating_buckets=frozenset({"activating"}),
        matcher=_matcher_from(OFFER_CLASSIFIER),
    )


def units_referent() -> LifecycleReferent:
    """Vocabulary 2: units grain, project 1201081073731555.

    This one places ``Engaged`` and ``Scheduled`` in ``activating``.
    """
    return LifecycleReferent(
        name="units-1201081073731555",
        grain="unit",
        project_gid="1201081073731555",
        bucket_set=FOUR_BUCKETS,
        activating_buckets=frozenset({"activating"}),
        matcher=_matcher_from(UNIT_CLASSIFIER),
    )


def units_opposing_referent() -> LifecycleReferent:
    """Vocabulary 3: the SAME project, opposing ``Engaged``/``Scheduled``.

    F-2 is open precisely because a second vocabulary governs project
    1201081073731555 and does NOT treat ``Engaged``/``Scheduled`` as activating.
    These tests do not assert which reading is authoritative -- that is the
    operator's fork. They assert only that BOTH are expressible as referents and
    that the mechanism reports them as the disagreement they are.
    """
    return LifecycleReferent(
        name="units-1201081073731555-opposing",
        grain="unit",
        project_gid="1201081073731555",
        bucket_set=FOUR_BUCKETS,
        activating_buckets=frozenset({"activating"}),
        matcher=_mapping_matcher(
            {
                "Onboarding": "activating",
                "Implementing": "activating",
                "Engaged": "inactive",
                "Scheduled": "inactive",
                "Active": "active",
            }
        ),
    )


def process_pipeline_referent() -> LifecycleReferent:
    """Vocabulary 4: a process-pipeline grain (one of nine)."""
    return LifecycleReferent(
        name="process-pipeline-webdev",
        grain="process_pipeline",
        project_gid="1200000000000001",
        bucket_set=FOUR_BUCKETS,
        activating_buckets=frozenset({"activating"}),
        matcher=_mapping_matcher(
            {
                "SCHEDULED": "activating",
                "REQUESTED": "activating",
                "DELAYED": "activating",
                "ACTIVE": "active",
                "OPPORTUNITY": "active",
                "INACTIVE": "inactive",
                "TEMPLATE": "ignored",
            }
        ),
    )


def business_unit_two_member_referent() -> LifecycleReferent:
    """Vocabulary 5: a TWO-MEMBER vocabulary at business-unit grain, no project.

    Mirrors the shape of the data-service fetch pools -- ``{"active",
    "activating"}`` with no project scoping at all. Included because a
    parameterization that can only express four-bucket project-scoped section
    vocabularies would silently exclude this whole family.
    """
    return LifecycleReferent(
        name="business-unit-fetch-pools",
        grain="business_unit",
        project_gid=None,
        bucket_set=frozenset({"active", "activating"}),
        activating_buckets=frozenset({"activating"}),
        matcher=_mapping_matcher({"ACTIVATING": "activating", "ACTIVE": "active"}),
    )


ALL_REFERENTS = [
    offers_referent,
    units_referent,
    units_opposing_referent,
    process_pipeline_referent,
    business_unit_two_member_referent,
]


# ---------------------------------------------------------------------------
# Facts fixtures -- the ONLY difference between a healthy and a broken pipe
# ---------------------------------------------------------------------------


def healthy_facts() -> dict:
    return {
        "office_name": "Cedar Park Chiropractic",
        "failure_probe": {"office_name": "Cedar Park Chiropractic", "kind": "no_slots_returned"},
        "pipe_proof_at": FIXED_NOW - timedelta(minutes=5),
    }


def _hook(referent: LifecycleReferent, checks=None) -> ActivationSmokeHook:
    return ActivationSmokeHook(
        referent,
        default_pipe_checks() if checks is None else checks,
        clock=_clock,
    )


# ===========================================================================
# 1. THE REFERENT IS INJECTED
# ===========================================================================


@pytest.mark.parametrize("factory", ALL_REFERENTS, ids=lambda f: f().name)
def test_every_vocabulary_is_expressible_as_an_injected_referent(factory) -> None:
    """All five vocabularies drive the SAME mechanism with no code change."""
    referent = factory()
    hook = _hook(referent)
    assert hook.referent.name == referent.name
    assert hook.referent.activating_buckets <= hook.referent.bucket_set


def test_offers_and_units_activating_sets_differ_but_both_are_honoured() -> None:
    """The offers and units vocabularies disagree on section names; both work."""
    offers = _hook(offers_referent())
    units = _hook(units_referent())

    # "ACTIVATING" is an offers section; it means nothing in the units vocabulary.
    assert offers.observe(subject_gid="g1", to_section="ACTIVATING") is not None
    assert units.observe(subject_gid="g1", to_section="ACTIVATING") is None

    # "Onboarding" is a units section; it means nothing in the offers vocabulary.
    assert units.observe(subject_gid="g1", to_section="Onboarding") is not None
    assert offers.observe(subject_gid="g1", to_section="Onboarding") is None


@pytest.mark.parametrize("section", ["Engaged", "Scheduled"])
def test_opposing_vocabularies_over_one_project_yield_opposite_verdicts(section: str) -> None:
    """THE F-2 FENCE.

    Two referents over project 1201081073731555 classify ``Engaged``/``Scheduled``
    oppositely. The mechanism reports both faithfully. If this module had picked a
    vocabulary, one of these two assertions would be impossible to satisfy.
    """
    permissive = _hook(units_referent())
    opposing = _hook(units_opposing_referent())

    assert permissive.referent.project_gid == opposing.referent.project_gid

    permissive_transition = permissive.observe(subject_gid="g1", to_section=section)
    opposing_transition = opposing.observe(subject_gid="g1", to_section=section)

    assert permissive_transition is not None, f"{section} is activating under the units vocabulary"
    assert opposing_transition is None, f"{section} is NOT activating under the opposing vocabulary"

    # And the transition that IS recorded names the vocabulary that recorded it,
    # so a downstream reader is never handed an unattributed activation fact.
    assert permissive_transition.referent_name == "units-1201081073731555"


def test_module_ships_no_default_referent() -> None:
    """A hook cannot be constructed without an explicit referent."""
    with pytest.raises(TypeError):
        ActivationSmokeHook()  # type: ignore[call-arg]


def test_activating_bucket_outside_bucket_set_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="not in bucket_set"):
        LifecycleReferent(
            name="bad",
            grain="offer",
            bucket_set=frozenset({"active", "inactive"}),
            activating_buckets=frozenset({"activating"}),
            matcher=_mapping_matcher({}),
        )


def test_referent_naming_no_activating_bucket_is_refused() -> None:
    """A referent with an empty activating set is a silently-dark hook."""
    with pytest.raises(ValueError, match="must be non-empty"):
        LifecycleReferent(
            name="dark",
            grain="offer",
            bucket_set=FOUR_BUCKETS,
            activating_buckets=frozenset(),
            matcher=_mapping_matcher({}),
        )


def test_matcher_leaving_the_declared_vocabulary_fails_closed() -> None:
    """An out-of-vocabulary bucket is never coerced or dropped."""
    referent = LifecycleReferent(
        name="leaky",
        grain="offer",
        bucket_set=FOUR_BUCKETS,
        activating_buckets=frozenset({"activating"}),
        matcher=_mapping_matcher({"WEIRD": "some_fifth_bucket"}),
    )
    with pytest.raises(VocabularyViolation, match="outside the declared bucket_set"):
        referent.classify("WEIRD")

    # And the GATE turns that into a refusal rather than an escape.
    decision = _hook(referent).guard(subject_gid="g1", to_section="WEIRD", facts=healthy_facts())
    assert decision.permitted is False
    assert decision.kind == "referent_vocabulary_violation"
    assert decision.kind.strip()


# ---------------------------------------------------------------------------
# The aggregation rule is an input too (collapse-IN is structurally rejected)
# ---------------------------------------------------------------------------


def test_single_reading_is_not_a_collapse() -> None:
    """Attaching OUT is permitted with no rule."""
    assert units_referent().collapse(["activating"]) == "activating"
    assert units_referent().collapse(["activating", "activating"]) == "activating"


def test_collapsing_in_without_a_declared_rule_is_refused() -> None:
    with pytest.raises(AggregationRuleAbsent, match="no declared aggregation_rule"):
        units_referent().collapse(["activating", "inactive"])


def test_collapsing_in_with_a_declared_rule_succeeds_and_is_named() -> None:
    rule = AggregationRule(
        name="highest-priority-wins",
        collapse=lambda buckets: "activating" if "activating" in buckets else "inactive",
    )
    referent = LifecycleReferent(
        name="units-collapsed",
        grain="unit",
        bucket_set=FOUR_BUCKETS,
        activating_buckets=frozenset({"activating"}),
        matcher=_matcher_from(UNIT_CLASSIFIER),
        aggregation_rule=rule,
    )
    assert referent.collapse(["activating", "inactive"]) == "activating"
    assert referent.aggregation_rule is not None
    assert referent.aggregation_rule.name == "highest-priority-wins"


def test_aggregation_rule_may_not_mint_a_bucket_outside_the_vocabulary() -> None:
    """A finer identity may never be minted from a coarser key."""
    rule = AggregationRule(name="minter", collapse=lambda buckets: "brand_new_bucket")
    referent = LifecycleReferent(
        name="units-minting",
        grain="unit",
        bucket_set=FOUR_BUCKETS,
        activating_buckets=frozenset({"activating"}),
        matcher=_matcher_from(UNIT_CLASSIFIER),
        aggregation_rule=rule,
    )
    with pytest.raises(VocabularyViolation, match="outside bucket_set"):
        referent.collapse(["activating", "inactive"])


# ===========================================================================
# 2. THE GATE IS TWO-SIDED
# ===========================================================================


def test_healthy_pipe_permits_activation() -> None:
    decision = _hook(units_referent()).guard(
        subject_gid="unit-42",
        to_section="Onboarding",
        from_section="Unengaged",
        facts=healthy_facts(),
    )
    assert decision.permitted is True
    assert decision.applicable is True
    assert decision.kind == "activation_permitted"
    assert decision.refused_check is None
    assert decision.report is not None
    assert decision.report.passed is True


@pytest.mark.parametrize(
    ("mutate", "expected_check", "expected_kind"),
    [
        pytest.param(
            lambda facts: facts.pop("office_name"),
            "office_named",
            "office_unresolved",
            id="office-never-resolved",
        ),
        pytest.param(
            lambda facts: facts.__setitem__("office_name", "   "),
            "office_named",
            "office_name_blank",
            id="office-resolves-blank",
        ),
        pytest.param(
            lambda facts: facts.pop("failure_probe"),
            "failure_path_names_office",
            "failure_probe_absent",
            id="failure-path-unproven",
        ),
        pytest.param(
            lambda facts: facts.__setitem__("failure_probe", {"office_name": "", "kind": "x"}),
            "failure_path_names_office",
            "failure_office_blank",
            id="failure-path-goes-blank",
        ),
        pytest.param(
            lambda facts: facts.__setitem__(
                "failure_probe", {"office_name": "Cedar Park Chiropractic", "kind": ""}
            ),
            "failure_path_names_office",
            "failure_kind_blank",
            id="failure-names-office-but-not-kind",
        ),
        pytest.param(
            lambda facts: facts.pop("pipe_proof_at"),
            "pipe_proof_fresh",
            "pipe_proof_absent",
            id="no-proof-at-all",
        ),
        pytest.param(
            lambda facts: facts.__setitem__("pipe_proof_at", FIXED_NOW - timedelta(days=3)),
            "pipe_proof_fresh",
            "pipe_proof_stale",
            id="proof-is-stale",
        ),
    ],
)
def test_broken_pipe_refuses_activation_and_names_the_break(
    mutate, expected_check: str, expected_kind: str
) -> None:
    """THE REFUSAL SIDE. Same mechanism, same referent -- only the facts differ."""
    facts = healthy_facts()
    mutate(facts)

    decision = _hook(units_referent()).guard(
        subject_gid="unit-42",
        to_section="Onboarding",
        from_section="Unengaged",
        facts=facts,
    )

    assert decision.permitted is False
    assert decision.applicable is True
    assert decision.refused_check == expected_check
    assert decision.kind == expected_kind
    assert decision.kind.strip(), "a refusal must never carry a blank kind"
    assert decision.detail.strip(), "a refusal must never carry a blank detail"
    # The refusal still names the subject -- never blank, per the realization bar.
    assert decision.subject_gid == "unit-42"
    assert decision.referent_name == "units-1201081073731555"


def test_the_two_sides_differ_only_in_facts() -> None:
    """Pipe-free two-sided control: identical hook, identical call, opposite verdict."""
    hook = _hook(units_referent())
    call = {"subject_gid": "unit-42", "to_section": "Onboarding", "from_section": "Unengaged"}

    healthy = hook.guard(**call, facts=healthy_facts())

    broken_facts = healthy_facts()
    broken_facts["office_name"] = ""
    broken = hook.guard(**call, facts=broken_facts)

    assert healthy.permitted is True
    assert broken.permitted is False
    assert healthy.transition is not None and broken.transition is not None
    # Both sides observed the SAME transition; only the proof differed.
    assert healthy.transition.to_bucket == broken.transition.to_bucket == "activating"


def test_empty_check_set_refuses_rather_than_vacuously_permits() -> None:
    """The untaken-zero guard, built into the mechanism.

    A smoke that asks nothing is the most likely way this gate rots into theatre.
    It fails closed.
    """
    hook = ActivationSmokeHook(units_referent(), (), clock=_clock)
    decision = hook.guard(subject_gid="unit-42", to_section="Onboarding", facts=healthy_facts())
    assert decision.permitted is False
    assert decision.kind == "no_checks_declared"


def test_an_empty_report_does_not_report_itself_as_passed() -> None:
    """The SECOND line of defence against the vacuous pass.

    ``guard()`` short-circuits on an empty check-set before a report is ever
    built, so this property was unpinned until a mutation probe at the constraint
    altitude removed the ``bool(self.outcomes)`` clause and the suite stayed
    GREEN. ``all(())`` is ``True``; an empty report must not inherit that.
    """
    assert SmokeReport(outcomes=()).passed is False
    assert SmokeReport(outcomes=()).failures == ()


def test_a_raising_probe_is_a_failure_never_a_skip() -> None:
    def _boom(context) -> ProbeVerdict:
        raise RuntimeError("upstream exploded")

    hook = ActivationSmokeHook(
        units_referent(),
        (SmokeCheck(name="explodes", kinds=frozenset({"boom"}), probe=_boom),),
        clock=_clock,
    )
    decision = hook.guard(subject_gid="unit-42", to_section="Onboarding", facts={})
    assert decision.permitted is False
    assert decision.refused_check == "explodes"
    assert "upstream exploded" in decision.detail


def test_a_probe_returning_an_undeclared_kind_is_refused() -> None:
    """The failure vocabulary is closed at runtime, not open."""

    def _off_vocabulary(context) -> ProbeVerdict:
        return ProbeVerdict(passed=False, kind="a_kind_nobody_declared")

    hook = ActivationSmokeHook(
        units_referent(),
        (SmokeCheck(name="sloppy", kinds=frozenset({"declared_kind"}), probe=_off_vocabulary),),
        clock=_clock,
    )
    decision = hook.guard(subject_gid="unit-42", to_section="Onboarding", facts={})
    assert decision.permitted is False
    assert decision.kind == "referent_vocabulary_violation"
    assert "a_kind_nobody_declared" in decision.detail


def test_non_activating_move_is_not_applicable_and_does_not_gate() -> None:
    decision = _hook(units_referent()).guard(
        subject_gid="unit-42", to_section="Paused", facts=healthy_facts()
    )
    assert decision.applicable is False
    assert decision.kind == "not_an_activation_transition"
    assert decision.transition is None


def test_activating_to_activating_is_not_an_activation_transition() -> None:
    """Only a crossing INTO the set is an activation; movement within is not."""
    hook = _hook(units_referent())
    assert (
        hook.observe(subject_gid="u", from_section="Onboarding", to_section="Implementing") is None
    )
    assert (
        hook.observe(subject_gid="u", from_section="Unengaged", to_section="Onboarding") is not None
    )


# ---------------------------------------------------------------------------
# Never blank -- structurally
# ---------------------------------------------------------------------------


def test_a_blank_kind_outcome_cannot_be_constructed() -> None:
    with pytest.raises(ValueError, match="kind must be non-blank"):
        CheckOutcome(check="x", passed=False, kind="  ")


def test_an_identity_less_outcome_cannot_be_constructed() -> None:
    with pytest.raises(ValueError, match="check must be non-blank"):
        CheckOutcome(check="", passed=False, kind="some_kind")


def test_a_failing_verdict_may_not_wear_the_pass_kind() -> None:
    with pytest.raises(ValueError, match="must name its kind"):
        ProbeVerdict(passed=False, kind=OK_KIND)


def test_a_blank_kind_decision_cannot_be_constructed() -> None:
    with pytest.raises(ValueError, match="kind must be non-blank"):
        ActivationDecision(
            permitted=False, applicable=True, kind="", subject_gid="g", referent_name="r"
        )


# ===========================================================================
# 3. THE POSITIONAL-BIND PIN (the hard gate)
# ===========================================================================
#
# Sibling defect, verified at autom8y origin/main
# services/account-status-recon/src/account_status_recon/readiness.py:
#   :43   OFFER_CONSTITUENTS = ("active", "activating")   -- stable, iterated by name
#   :992  completeness_checks_list = [...]                -- built under `if ... is not None`
# and CompletenessCheck carries no identity field, so index 0 is "active" on one
# call and "activating" on the next. The two-sided proof below reproduces exactly
# that shift against THIS mechanism and shows name-binding survives it.


def test_name_lookup_is_invariant_under_declaration_order() -> None:
    """Reordering the checks does not move any result."""
    checks = default_pipe_checks()
    forward = ActivationSmokeHook(units_referent(), checks, clock=_clock)
    reversed_ = ActivationSmokeHook(units_referent(), tuple(reversed(checks)), clock=_clock)

    facts = healthy_facts()
    facts["office_name"] = ""

    a = forward.guard(subject_gid="u", to_section="Onboarding", facts=facts)
    b = reversed_.guard(subject_gid="u", to_section="Onboarding", facts=facts)

    assert a.report is not None and b.report is not None
    # Positions differ...
    assert a.report.outcomes[0].check != b.report.outcomes[0].check
    # ...and the name-keyed reads are identical.
    for name in ("subject_identified", "office_named", "pipe_proof_fresh"):
        assert a.report.outcome_for(name).passed == b.report.outcome_for(name).passed
        assert a.report.outcome_for(name).kind == b.report.outcome_for(name).kind


def test_index_zero_shifts_identity_under_filtering_while_name_binding_holds() -> None:
    """THE TWO-SIDED POSITIONAL PROOF.

    Build the report the way the sibling defect builds it -- conditionally,
    dropping entries. Index 0 names a DIFFERENT check on the two calls, exactly as
    ``completeness_checks_list`` does. Name lookup is unaffected, and the dropped
    check's absence surfaces as an error rather than as a neighbour's value.
    """
    full = SmokeReport(
        outcomes=(
            CheckOutcome(check="subject_identified", passed=True, kind=OK_KIND),
            CheckOutcome(check="office_named", passed=False, kind="office_name_blank"),
        )
    )
    filtered = SmokeReport(
        outcomes=(CheckOutcome(check="office_named", passed=False, kind="office_name_blank"),)
    )

    # SIDE A -- the positional read shifts meaning between the two calls.
    assert full.outcomes[0].check == "subject_identified"
    assert filtered.outcomes[0].check == "office_named"
    assert full.outcomes[0].check != filtered.outcomes[0].check

    # SIDE B -- the name-keyed read does not.
    assert full.outcome_for("office_named").kind == "office_name_blank"
    assert filtered.outcome_for("office_named").kind == "office_name_blank"

    # And the dropped check is ABSENT, not silently substituted by its neighbour.
    with pytest.raises(KeyError, match="no check named 'subject_identified'"):
        filtered.outcome_for("subject_identified")


def test_report_exposes_no_positional_accessor() -> None:
    """Position is not an addressing mode on the report."""
    report = SmokeReport(outcomes=(CheckOutcome(check="a", passed=True, kind=OK_KIND),))
    assert not hasattr(report, "__getitem__")
    with pytest.raises(TypeError):
        report[0]  # type: ignore[index]


def test_every_outcome_carries_its_identity() -> None:
    """The field whose absence caused the sibling defect is required and stamped."""
    hook = _hook(units_referent())
    transition = hook.observe(subject_gid="u", to_section="Onboarding")
    assert transition is not None
    report = hook.run(transition, healthy_facts())

    assert {outcome.check for outcome in report.outcomes} == set(hook.check_names)
    for outcome in report.outcomes:
        assert outcome.check.strip()
        assert outcome.kind.strip()


def test_probes_cannot_name_themselves() -> None:
    """A probe has no identity field, so it cannot misname its own result."""
    assert not hasattr(ProbeVerdict(passed=True), "check")

    def _liar(context) -> ProbeVerdict:
        return ProbeVerdict(passed=False, kind="declared_kind")

    hook = ActivationSmokeHook(
        units_referent(),
        (SmokeCheck(name="the_real_name", kinds=frozenset({"declared_kind"}), probe=_liar),),
        clock=_clock,
    )
    decision = hook.guard(subject_gid="u", to_section="Onboarding", facts={})
    assert decision.refused_check == "the_real_name"


def test_duplicate_check_names_are_refused() -> None:
    """Name-keyed lookup requires unique identities."""
    check = SmokeCheck(
        name="dupe", kinds=frozenset({"k"}), probe=lambda ctx: ProbeVerdict(passed=True)
    )
    with pytest.raises(ValueError, match="duplicate check names"):
        ActivationSmokeHook(units_referent(), (check, check), clock=_clock)


# ===========================================================================
# 4. THE DATED INSTANT -- the asset this hook mints
# ===========================================================================


def test_transition_carries_the_instant_from_the_injected_clock() -> None:
    """The upstream registry cannot date a placement change; this hook can."""
    transition = _hook(units_referent()).observe(
        subject_gid="unit-42", from_section="Unengaged", to_section="Onboarding"
    )
    assert transition is not None
    assert transition.observed_at == FIXED_NOW
    assert transition.observed_at.tzinfo is not None, "an undated/naive instant is not an asset"


def test_transition_names_the_vocabulary_and_grain_that_produced_it() -> None:
    transition = _hook(process_pipeline_referent()).observe(
        subject_gid="proc-9", to_section="SCHEDULED"
    )
    assert transition is not None
    assert transition.referent_name == "process-pipeline-webdev"
    assert transition.grain == "process_pipeline"
    assert transition.to_bucket == "activating"
    assert transition.from_bucket is None
