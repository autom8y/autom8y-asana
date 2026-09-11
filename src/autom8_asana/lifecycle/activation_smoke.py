"""Onboarding activation smoke -- a referent-injected gate on the activating transition.

WHAT THIS IS
------------
The first *dated* placement-transition observer in this fleet. Nothing observed
the activating transition before this module, and not by omission: the upstream
``AccountStatus`` registry is ACTIVE-ONLY ("rows exist ONLY for business units
classified as ACTIVE or ACTIVATING; absence of a row = inactive") refreshed by a
4-hourly snapshot REPLACE, so a subject's disappearance is UN-DATED and there is
no instant at which a placement became terminal. That is a structural property of
a REPLACE-snapshot registry, not a gap someone forgot to fill. (Established by the
``identity-activity-substrate`` lane, ``autom8y-data`` origin/main 20c26cb8, quoting
``core/models/_platform.py`` via ``_identity_observations.py:772-778``. Attributed,
not re-derived here.)

The consequence for this module is the whole point of it: because the substrate
cannot date the transition, THE INSTANT THIS HOOK RECORDS IS THE ASSET.
``ActivationTransition.observed_at`` is not decoration -- it is the only dated
placement-transition fact either lane holds.

THE REFERENT IS INJECTED. THIS MODULE PICKS NO VOCABULARY.
----------------------------------------------------------
At least four ``activating`` vocabularies exist across at least three grains, and
two of them govern the SAME project while classifying ``Engaged`` and ``Scheduled``
OPPOSITELY. Which one is authoritative is an OPEN operator/architect fork (F-2).

A hook that hard-codes one of them would resolve that fork by implementation --
silently, invisibly, and with the authority of running code. So this module takes
the referent as a parameter: project, grain, bucket-set, matcher, and aggregation
rule all arrive from the caller. ``LifecycleReferent`` is the whole of the
configuration surface, and there is no default instance in this module.

Two vocabularies classifying the same section name oppositely within one project is
a COLLAPSE-IN across separately-keyed grains. Per the substrate lane's ADR
(section 4.1:1400-1404) attaching OUT is permitted under a row-count and
key-sequence assertion, while collapsing IN is STRUCTURALLY REJECTED absent a
DECLARED AGGREGATION RULE, and a finer identity may never be minted from a coarser
key. So ``aggregation_rule`` is a first-class input here too: a referent configured
with multiple grain readings and no rule cannot collapse them -- it raises
(``AggregationRuleAbsent``) and the gate refuses. A hook configured with a grain but
no aggregation rule is configured into the failure that ADR names.

BIND BY NAME, NEVER BY POSITION
-------------------------------
Inherited as law from the sibling defect in ``autom8y``
``services/account-status-recon/src/account_status_recon/readiness.py``: there,
``OFFER_CONSTITUENTS`` (:43) is stable and iterated by name, but the parallel
``completeness_checks_list`` (:992) is built under an ``if ... is not None`` filter
that DROPS constituents, and ``CompletenessCheck`` carries no identity field -- so
index 0 is ``"active"`` on one call and ``"activating"`` on the next and nothing
downstream can tell which. That module's own fix was to preserve identity per
record (``offer_constituent_signals``, :46).

This module makes the same class of error unconstructable rather than merely
avoided:

* ``CheckOutcome.check`` is a required identity field, and it is stamped BY THE
  HOOK from the check's declared name -- a probe cannot forget to name itself,
  because a probe never gets to name itself (it returns a ``ProbeVerdict``, which
  has no identity field at all).
* ``SmokeReport`` exposes ``outcome_for(name)`` and ``by_name``. It has no
  ``__getitem__`` and no positional accessor. Reading a result by index is not
  merely discouraged; there is no API for it.
* ``CheckOutcome.kind`` may never be blank -- ``__post_init__`` refuses to
  construct one. A refusal that cannot name its kind cannot exist.

TWO-SIDED BY CONSTRUCTION
-------------------------
``guard()`` is the gate. A healthy pipe returns ``permitted=True``; a broken pipe
returns ``permitted=False`` carrying the failing check's NAME and KIND. Both sides
are mechanism, not convention.

Note especially: a smoke with ZERO declared checks REFUSES
(``kind="no_checks_declared"``). An empty check-set is the vacuous-pass failure
mode -- a gate that permits everything because it asks nothing -- and it is the
single most likely way this mechanism would rot into theatre. It fails closed.

STATUS: NOT WIRED. This module is importable and tested but no production caller
constructs it. Arming it is an operator lever, deliberately not taken here --
see the accompanying build artifact for the arming path and its blast radius.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)

__all__ = [
    "OK_KIND",
    "ActivationDecision",
    "ActivationSmokeHook",
    "ActivationTransition",
    "AggregationRule",
    "AggregationRuleAbsent",
    "CheckOutcome",
    "LifecycleReferent",
    "ProbeVerdict",
    "ReferentError",
    "SmokeCheck",
    "SmokeContext",
    "SmokeReport",
    "VocabularyViolation",
    "default_pipe_checks",
]

#: The reserved kind stamped on a passing check. Always allowed; never needs to be
#: declared in a check's own closed failure vocabulary.
OK_KIND = "ok"

#: Decision kinds emitted by the gate itself (as opposed to by a failing check).
#: A refusal whose kind is not one of these came from a check, and names it.
DECISION_KIND_PERMITTED = "activation_permitted"
DECISION_KIND_NOT_APPLICABLE = "not_an_activation_transition"
DECISION_KIND_NO_CHECKS = "no_checks_declared"
DECISION_KIND_VOCABULARY = "referent_vocabulary_violation"
DECISION_KIND_AGGREGATION = "aggregation_rule_absent"

GATE_KINDS: frozenset[str] = frozenset(
    {
        DECISION_KIND_PERMITTED,
        DECISION_KIND_NOT_APPLICABLE,
        DECISION_KIND_NO_CHECKS,
        DECISION_KIND_VOCABULARY,
        DECISION_KIND_AGGREGATION,
    }
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ReferentError(Exception):
    """Base: the injected referent cannot answer the question asked of it."""


class VocabularyViolation(ReferentError):
    """A matcher returned a bucket outside the referent's declared bucket set.

    Fail-closed: an unrecognised bucket is never coerced, defaulted, or dropped.
    The referent declares a CLOSED vocabulary; a matcher that leaves it is a
    configuration error, and the gate refuses rather than guessing which of the
    four ``activating`` vocabularies was intended.
    """


class AggregationRuleAbsent(ReferentError):
    """A collapse across grain readings was attempted with no declared rule.

    Structurally rejected per the substrate ADR section 4.1:1400-1404. Attaching
    OUT is permitted; collapsing IN without a declared aggregation rule is not.
    """


# ---------------------------------------------------------------------------
# The injected referent
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AggregationRule:
    """A DECLARED rule for collapsing several grain readings into one bucket.

    Attributes:
        name: Human-nameable identity of the rule, carried into logs and
            decisions so a collapsed reading can always be traced to the rule
            that produced it.
        collapse: Maps a non-empty sequence of bucket names to a single bucket
            name. Must return a member of the referent's ``bucket_set``; the
            referent re-checks this, so a rule cannot mint a bucket that the
            declared vocabulary does not contain.
    """

    name: str
    collapse: Callable[[Sequence[str]], str]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("AggregationRule.name must be non-blank")


@dataclass(frozen=True)
class LifecycleReferent:
    """WHICH lifecycle vocabulary this hook is reading -- supplied, never assumed.

    This is the entire configuration surface of the hook. There is deliberately
    no module-level default instance and no fallback: constructing a hook
    requires the caller to have decided which vocabulary it means, at which
    grain, under which aggregation rule.

    Attributes:
        name: Identity of this vocabulary, e.g. ``"offers-1143843662099250"``.
            Stamped onto every transition and decision so a downstream reader can
            always tell which of the competing vocabularies produced a verdict.
        grain: The grain this referent reads -- ``"offer"``, ``"unit"``,
            ``"process_pipeline"``, ``"business_unit"``, or any other. A free
            string, NOT an enum: an enum here would silently cap the expressible
            grains at the ones known on the day this module was written, which is
            the same error as hard-coding the vocabulary.
        bucket_set: The CLOSED vocabulary of bucket names. A matcher returning
            anything outside this set raises ``VocabularyViolation``.
        activating_buckets: The subset of ``bucket_set`` that constitutes
            "activating". Must be a non-empty subset. This is the one knob that
            makes the four competing vocabularies expressible without choosing
            between them.
        matcher: Section name -> bucket name, or ``None`` for "this section is
            not classified by this referent". Injected; this module ships none.
        project_gid: Asana project GID scoping the referent, or ``None`` for a
            referent that is not project-scoped (e.g. a business-unit-grain
            vocabulary read from a data-service table rather than a project).
        aggregation_rule: How to collapse multiple grain readings into one.
            ``None`` means NO COLLAPSE IS PERMITTED -- ``collapse()`` will raise
            rather than pick.
    """

    name: str
    grain: str
    bucket_set: frozenset[str]
    activating_buckets: frozenset[str]
    matcher: Callable[[str], str | None]
    project_gid: str | None = None
    aggregation_rule: AggregationRule | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("LifecycleReferent.name must be non-blank")
        if not self.grain.strip():
            raise ValueError("LifecycleReferent.grain must be non-blank")
        if not self.bucket_set:
            raise ValueError("LifecycleReferent.bucket_set must be non-empty")
        if not self.activating_buckets:
            raise ValueError(
                "LifecycleReferent.activating_buckets must be non-empty -- a referent "
                "that names no activating bucket can never observe an activation, "
                "which is a silently-dark hook"
            )
        stray = self.activating_buckets - self.bucket_set
        if stray:
            raise ValueError(
                f"activating_buckets {sorted(stray)} are not in bucket_set "
                f"{sorted(self.bucket_set)} -- the activating subset may never mint a "
                "bucket the declared vocabulary does not contain"
            )

    def classify(self, section_name: str) -> str | None:
        """Bucket for ``section_name`` under THIS referent, or None if unclassified.

        Raises:
            VocabularyViolation: the matcher returned a bucket outside
                ``bucket_set``. Fail-closed on purpose -- see the class docstring.
        """
        bucket = self.matcher(section_name)
        if bucket is None:
            return None
        if bucket not in self.bucket_set:
            raise VocabularyViolation(
                f"referent {self.name!r} matcher returned bucket {bucket!r} for section "
                f"{section_name!r}, which is outside the declared bucket_set "
                f"{sorted(self.bucket_set)}"
            )
        return bucket

    def is_activating(self, bucket: str | None) -> bool:
        """True iff ``bucket`` is one of this referent's activating buckets."""
        return bucket is not None and bucket in self.activating_buckets

    def collapse(self, buckets: Sequence[str]) -> str:
        """Collapse several grain readings into one bucket.

        A single reading is not a collapse and is returned as-is (attaching OUT).
        More than one reading requires a DECLARED aggregation rule (collapsing IN).

        Raises:
            AggregationRuleAbsent: more than one reading and no declared rule.
            VocabularyViolation: the rule returned a bucket outside ``bucket_set``
                -- a rule may not mint a finer identity than the vocabulary holds.
        """
        if not buckets:
            raise ValueError("collapse() requires at least one bucket reading")
        distinct = set(buckets)
        if len(distinct) == 1:
            return next(iter(distinct))
        if self.aggregation_rule is None:
            raise AggregationRuleAbsent(
                f"referent {self.name!r} was asked to collapse {sorted(distinct)} across "
                f"grain {self.grain!r} with no declared aggregation_rule; collapsing IN "
                "across separately-keyed grains is structurally rejected"
            )
        collapsed = self.aggregation_rule.collapse(tuple(buckets))
        if collapsed not in self.bucket_set:
            raise VocabularyViolation(
                f"aggregation rule {self.aggregation_rule.name!r} returned bucket "
                f"{collapsed!r}, which is outside bucket_set {sorted(self.bucket_set)}"
            )
        return collapsed


# ---------------------------------------------------------------------------
# The dated transition -- the asset
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivationTransition:
    """A placement transition INTO an activating bucket, with its instant.

    ``observed_at`` is the point of this whole module: the upstream registry is a
    REPLACE snapshot and cannot date a placement change, so this timestamp is the
    only dated placement-transition fact in the fleet. It is stamped by the hook's
    injected clock at observation time.

    ``referent_name`` travels with the record because four vocabularies disagree;
    a transition without the name of the vocabulary that classified it is an
    ambiguous fact wearing the costume of a definite one.
    """

    subject_gid: str
    referent_name: str
    grain: str
    from_section: str | None
    to_section: str
    from_bucket: str | None
    to_bucket: str
    observed_at: datetime


# ---------------------------------------------------------------------------
# Checks -- identity-bearing by construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProbeVerdict:
    """What a probe returns. Deliberately carries NO identity field.

    A probe cannot name itself, so a probe cannot MISname itself. The hook stamps
    the declared check name onto the resulting ``CheckOutcome``. This is the
    structural inversion of the sibling defect where records were built
    conditionally and carried no identity, leaving index 0 meaning different
    things on different calls.
    """

    passed: bool
    kind: str = OK_KIND
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("ProbeVerdict.kind must be non-blank")
        if self.passed and self.kind != OK_KIND:
            raise ValueError(
                f"a passing ProbeVerdict must carry kind {OK_KIND!r}, got {self.kind!r}"
            )
        if not self.passed and self.kind == OK_KIND:
            raise ValueError(
                f"a failing ProbeVerdict may not carry the reserved pass kind {OK_KIND!r} "
                "-- a refusal must name its kind"
            )


@dataclass(frozen=True)
class CheckOutcome:
    """One check's result, carrying its own identity.

    ``check`` is the identity field whose absence caused the sibling defect. It is
    required, non-blank, and stamped by the hook.
    """

    check: str
    passed: bool
    kind: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.check.strip():
            raise ValueError("CheckOutcome.check must be non-blank -- results carry identity")
        if not self.kind.strip():
            raise ValueError("CheckOutcome.kind must be non-blank -- a refusal names its kind")


@dataclass(frozen=True)
class SmokeContext:
    """What probes read. ``facts`` is injected, so the smoke runs pipe-free."""

    transition: ActivationTransition
    facts: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SmokeCheck:
    """A named check with a CLOSED failure vocabulary.

    Attributes:
        name: Identity of the check. Unique within a hook; stamped onto outcomes.
        kinds: The closed set of failure kinds this check may emit. A probe that
            returns a kind outside this set is a configuration error and the gate
            refuses -- the failure vocabulary is not open at runtime.
        probe: Reads a ``SmokeContext`` and returns a ``ProbeVerdict``.
    """

    name: str
    kinds: frozenset[str]
    probe: Callable[[SmokeContext], ProbeVerdict]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("SmokeCheck.name must be non-blank")
        if not self.kinds:
            raise ValueError(
                f"SmokeCheck {self.name!r} declares no failure kinds -- a check that "
                "cannot name why it failed cannot refuse anything"
            )
        if OK_KIND in self.kinds:
            raise ValueError(
                f"SmokeCheck {self.name!r} may not declare the reserved pass kind {OK_KIND!r} "
                "as a failure kind"
            )


@dataclass(frozen=True)
class SmokeReport:
    """The full set of check outcomes, addressable ONLY by name.

    There is no ``__getitem__`` and no positional accessor on this class. That is
    the point: the sibling defect was a positional read of a conditionally-built
    list. Here, position is not an addressing mode.
    """

    outcomes: tuple[CheckOutcome, ...]

    def __post_init__(self) -> None:
        names = [outcome.check for outcome in self.outcomes]
        if len(names) != len(set(names)):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            raise ValueError(
                f"duplicate check names in report: {duplicates} -- name-keyed lookup "
                "requires unique identities"
            )

    @property
    def by_name(self) -> Mapping[str, CheckOutcome]:
        """Name-keyed view of the outcomes."""
        return {outcome.check: outcome for outcome in self.outcomes}

    def outcome_for(self, name: str) -> CheckOutcome:
        """The outcome named ``name``.

        Raises:
            KeyError: no check by that name ran. Deliberately loud: under the
                sibling defect a dropped constituent silently became whichever
                record happened to land at that index. Here, absence is absence.
        """
        try:
            return self.by_name[name]
        except KeyError:
            raise KeyError(
                f"no check named {name!r} in this report; ran: {sorted(self.by_name)}"
            ) from None

    @property
    def failures(self) -> tuple[CheckOutcome, ...]:
        """Failing outcomes, in declared check order."""
        return tuple(outcome for outcome in self.outcomes if not outcome.passed)

    @property
    def passed(self) -> bool:
        """True iff at least one check ran and every check passed.

        The ``at least one`` clause is load-bearing: an empty report is a smoke
        that asked nothing, and a gate that permits on silence is the vacuous-pass
        failure mode this module exists to refuse.
        """
        return bool(self.outcomes) and all(outcome.passed for outcome in self.outcomes)


# ---------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActivationDecision:
    """Whether activation may proceed, and -- always -- why.

    ``kind`` is never blank, on either side. On refusal it is either a gate kind
    (``no_checks_declared``, ``referent_vocabulary_violation``,
    ``aggregation_rule_absent``) or the failing check's own declared kind, with
    ``refused_check`` naming which check produced it.
    """

    permitted: bool
    applicable: bool
    kind: str
    subject_gid: str
    referent_name: str
    refused_check: str | None = None
    transition: ActivationTransition | None = None
    report: SmokeReport | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("ActivationDecision.kind must be non-blank -- a decision names itself")
        if not self.applicable and self.kind != DECISION_KIND_NOT_APPLICABLE:
            raise ValueError(
                f"a non-applicable decision must carry kind {DECISION_KIND_NOT_APPLICABLE!r}"
            )
        if self.applicable and self.permitted and self.kind != DECISION_KIND_PERMITTED:
            raise ValueError(
                f"a permitting decision must carry kind {DECISION_KIND_PERMITTED!r}, "
                f"got {self.kind!r}"
            )
        if self.applicable and not self.permitted and self.kind == DECISION_KIND_PERMITTED:
            raise ValueError("a refusing decision may not carry the permitted kind")
        if self.refused_check is not None and self.permitted:
            raise ValueError("a permitting decision may not name a refused check")


# ---------------------------------------------------------------------------
# The hook
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ActivationSmokeHook:
    """Observes the activating transition and gates activation on a pipe proof.

    Construction requires a referent. There is no default. That is the F-2 fence
    expressed in the type system: you cannot build this hook without having
    decided, explicitly and namefully, which vocabulary you mean.
    """

    def __init__(
        self,
        referent: LifecycleReferent,
        checks: Sequence[SmokeCheck] = (),
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        names = [check.name for check in checks]
        if len(names) != len(set(names)):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            raise ValueError(f"duplicate check names: {duplicates}")
        self._referent = referent
        self._checks: tuple[SmokeCheck, ...] = tuple(checks)
        self._by_name: dict[str, SmokeCheck] = {check.name: check for check in self._checks}
        self._clock = clock or _utc_now

    @property
    def referent(self) -> LifecycleReferent:
        return self._referent

    @property
    def check_names(self) -> tuple[str, ...]:
        """Declared check names, in declared order. Order is for REPORTING only."""
        return tuple(self._by_name)

    def check_for(self, name: str) -> SmokeCheck:
        """The declared check named ``name`` -- name-keyed, never positional."""
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"no check named {name!r}; declared: {sorted(self._by_name)}") from None

    # -- observation ----------------------------------------------------

    def observe(
        self,
        *,
        subject_gid: str,
        to_section: str,
        from_section: str | None = None,
    ) -> ActivationTransition | None:
        """Record the transition if it enters an activating bucket, else None.

        A move that is already inside the activating set (activating -> activating)
        is NOT an activation transition: the subject did not activate, it moved
        within a bucket. Only a crossing INTO the set counts, which is what makes
        the recorded instant meaningful.

        Raises:
            VocabularyViolation: the matcher left the declared bucket set.
        """
        to_bucket = self._referent.classify(to_section)
        if to_bucket is None or not self._referent.is_activating(to_bucket):
            return None
        from_bucket = self._referent.classify(from_section) if from_section is not None else None
        if self._referent.is_activating(from_bucket):
            return None
        return ActivationTransition(
            subject_gid=subject_gid,
            referent_name=self._referent.name,
            grain=self._referent.grain,
            from_section=from_section,
            to_section=to_section,
            from_bucket=from_bucket,
            to_bucket=to_bucket,
            observed_at=self._clock(),
        )

    # -- the smoke ------------------------------------------------------

    def run(
        self,
        transition: ActivationTransition,
        facts: Mapping[str, Any] | None = None,
    ) -> SmokeReport:
        """Run every declared check, stamping each outcome with its check name."""
        context = SmokeContext(transition=transition, facts=dict(facts or {}))
        outcomes: list[CheckOutcome] = []
        for check in self._checks:
            outcomes.append(self._run_one(check, context))
        return SmokeReport(outcomes=tuple(outcomes))

    def _run_one(self, check: SmokeCheck, context: SmokeContext) -> CheckOutcome:
        """Run one check, converting any escape into a named refusal.

        A probe that raises is a FAILED check, never a skipped one. The sibling
        defect's lesson generalises: a check that vanishes from the report is
        indistinguishable from a check that passed.
        """
        try:
            verdict = check.probe(context)
        # BROAD-CATCH: a raising probe is a FAILED check, never a skipped one.
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "activation_smoke_probe_raised",
                check=check.name,
                referent=context.transition.referent_name,
                subject_gid=context.transition.subject_gid,
                exc_info=True,
            )
            return CheckOutcome(
                check=check.name,
                passed=False,
                kind=DECISION_KIND_VOCABULARY,
                detail=f"probe raised {type(exc).__name__}: {exc}",
            )
        if not verdict.passed and verdict.kind not in check.kinds:
            return CheckOutcome(
                check=check.name,
                passed=False,
                kind=DECISION_KIND_VOCABULARY,
                detail=(
                    f"probe returned undeclared kind {verdict.kind!r}; "
                    f"declared: {sorted(check.kinds)}"
                ),
            )
        return CheckOutcome(
            check=check.name,
            passed=verdict.passed,
            kind=verdict.kind,
            detail=verdict.detail,
        )

    # -- the gate -------------------------------------------------------

    def guard(
        self,
        *,
        subject_gid: str,
        to_section: str,
        from_section: str | None = None,
        facts: Mapping[str, Any] | None = None,
    ) -> ActivationDecision:
        """Decide whether this subject may activate. Two-sided; never blank.

        Returns a permitting decision only when the transition is an activation,
        at least one check ran, and every check passed. Every other outcome is a
        refusal that names its kind, and -- where a check produced it -- its check.
        """
        try:
            transition = self.observe(
                subject_gid=subject_gid,
                to_section=to_section,
                from_section=from_section,
            )
        except AggregationRuleAbsent as exc:
            return self._refuse(subject_gid, DECISION_KIND_AGGREGATION, detail=str(exc))
        except VocabularyViolation as exc:
            return self._refuse(subject_gid, DECISION_KIND_VOCABULARY, detail=str(exc))

        if transition is None:
            return ActivationDecision(
                permitted=True,
                applicable=False,
                kind=DECISION_KIND_NOT_APPLICABLE,
                subject_gid=subject_gid,
                referent_name=self._referent.name,
                detail=(
                    f"section {to_section!r} does not enter an activating bucket under "
                    f"referent {self._referent.name!r}"
                ),
            )

        if not self._checks:
            return self._refuse(
                subject_gid,
                DECISION_KIND_NO_CHECKS,
                transition=transition,
                detail=(
                    "no checks declared -- an empty smoke proves nothing and is refused "
                    "rather than permitted"
                ),
            )

        report = self.run(transition, facts)
        if report.passed:
            logger.info(
                "activation_smoke_permitted",
                referent=self._referent.name,
                grain=self._referent.grain,
                subject_gid=subject_gid,
                to_section=to_section,
                observed_at=transition.observed_at.isoformat(),
                checks=len(report.outcomes),
            )
            return ActivationDecision(
                permitted=True,
                applicable=True,
                kind=DECISION_KIND_PERMITTED,
                subject_gid=subject_gid,
                referent_name=self._referent.name,
                transition=transition,
                report=report,
            )

        first_failure = report.failures[0]
        logger.warning(
            "activation_smoke_refused",
            referent=self._referent.name,
            grain=self._referent.grain,
            subject_gid=subject_gid,
            to_section=to_section,
            observed_at=transition.observed_at.isoformat(),
            refused_check=first_failure.check,
            kind=first_failure.kind,
        )
        return ActivationDecision(
            permitted=False,
            applicable=True,
            kind=first_failure.kind,
            subject_gid=subject_gid,
            referent_name=self._referent.name,
            refused_check=first_failure.check,
            transition=transition,
            report=report,
            detail=first_failure.detail,
        )

    def _refuse(
        self,
        subject_gid: str,
        kind: str,
        *,
        transition: ActivationTransition | None = None,
        detail: str = "",
    ) -> ActivationDecision:
        logger.warning(
            "activation_smoke_refused",
            referent=self._referent.name,
            grain=self._referent.grain,
            subject_gid=subject_gid,
            kind=kind,
            detail=detail,
        )
        return ActivationDecision(
            permitted=False,
            applicable=True,
            kind=kind,
            subject_gid=subject_gid,
            referent_name=self._referent.name,
            transition=transition,
            detail=detail,
        )


# ---------------------------------------------------------------------------
# A default check suite -- injectable, pipe-free, end-to-end shaped
# ---------------------------------------------------------------------------
#
# These read ONLY from the injected ``facts`` mapping and the transition itself.
# No network, no credential, no clock beyond the hook's injected one. That is what
# makes the two-sided control in the accompanying tests pipe-free: the healthy and
# broken pipes differ only in the facts handed to the same mechanism.


def _probe_subject_identified(context: SmokeContext) -> ProbeVerdict:
    if not context.transition.subject_gid.strip():
        return ProbeVerdict(passed=False, kind="subject_gid_blank", detail="subject_gid is blank")
    return ProbeVerdict(passed=True)


def _probe_office_named(context: SmokeContext) -> ProbeVerdict:
    if "office_name" not in context.facts:
        return ProbeVerdict(
            passed=False,
            kind="office_unresolved",
            detail="no office_name fact was supplied for this subject",
        )
    name = context.facts["office_name"]
    if not isinstance(name, str) or not name.strip():
        return ProbeVerdict(
            passed=False,
            kind="office_name_blank",
            detail="office_name resolved to a blank value",
        )
    return ProbeVerdict(passed=True)


def _probe_failure_path_names_office(context: SmokeContext) -> ProbeVerdict:
    """The two-sided half: prove the FAILURE path also names the office, with a kind.

    A pipe that names the office on success and goes blank on failure is exactly
    the pipe the realization predicate refuses. So the smoke asks the pipe to
    demonstrate its failure path before letting the account activate.
    """
    probe = context.facts.get("failure_probe")
    if not isinstance(probe, Mapping):
        return ProbeVerdict(
            passed=False,
            kind="failure_probe_absent",
            detail="no failure_probe fact was supplied; the failure path is unproven",
        )
    office = probe.get("office_name")
    if not isinstance(office, str) or not office.strip():
        return ProbeVerdict(
            passed=False,
            kind="failure_office_blank",
            detail="the failure path did not name the office",
        )
    kind = probe.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        return ProbeVerdict(
            passed=False,
            kind="failure_kind_blank",
            detail="the failure path named the office but not the kind of failure",
        )
    return ProbeVerdict(passed=True)


def _make_freshness_probe(max_age: timedelta) -> Callable[[SmokeContext], ProbeVerdict]:
    def _probe(context: SmokeContext) -> ProbeVerdict:
        proof_at = context.facts.get("pipe_proof_at")
        if not isinstance(proof_at, datetime):
            return ProbeVerdict(
                passed=False,
                kind="pipe_proof_absent",
                detail="no pipe_proof_at timestamp was supplied",
            )
        if proof_at.tzinfo is None:
            return ProbeVerdict(
                passed=False,
                kind="pipe_proof_absent",
                detail="pipe_proof_at is naive; an undated proof is not a proof",
            )
        age = context.transition.observed_at - proof_at
        if age > max_age:
            return ProbeVerdict(
                passed=False,
                kind="pipe_proof_stale",
                detail=f"pipe proof is {age} old, exceeding {max_age}",
            )
        return ProbeVerdict(passed=True)

    return _probe


def default_pipe_checks(*, max_proof_age: timedelta = timedelta(hours=1)) -> tuple[SmokeCheck, ...]:
    """A four-check end-to-end pipe proof. Order is reporting order ONLY.

    Nothing in this module addresses these by position; they are returned as a
    tuple for stable reporting, and every consumer looks them up by name.
    """
    return (
        SmokeCheck(
            name="subject_identified",
            kinds=frozenset({"subject_gid_blank"}),
            probe=_probe_subject_identified,
        ),
        SmokeCheck(
            name="office_named",
            kinds=frozenset({"office_unresolved", "office_name_blank"}),
            probe=_probe_office_named,
        ),
        SmokeCheck(
            name="failure_path_names_office",
            kinds=frozenset({"failure_probe_absent", "failure_office_blank", "failure_kind_blank"}),
            probe=_probe_failure_path_names_office,
        ),
        SmokeCheck(
            name="pipe_proof_fresh",
            kinds=frozenset({"pipe_proof_absent", "pipe_proof_stale"}),
            probe=_make_freshness_probe(max_proof_age),
        ),
    )
