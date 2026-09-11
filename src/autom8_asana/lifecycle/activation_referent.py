"""The OFFER-grain referent for the activation smoke -- the ruled vocabulary.

WHY THIS MODULE EXISTS
----------------------
``activation_smoke.py`` deliberately ships NO default referent: four ``activating``
vocabularies exist across three grains and the module refuses to pick one by
implementation. The pick was made by ruling instead:

* sitting VIII **R-127** rejected the BusinessUnit-grain premise ("status comes from
  section groups defined in the Offer entities");
* sitting VIII **R-132** ruled the fourth leg's referent is the OFFER grain, with the
  Business aggregation built FIRST (``Business.max_offer_activity``, asana #431);
* sitting IX **R-135** folded clause (d) into the READ epoch on that referent.

So this module is the ONE place the ruled vocabulary is spelled out, and it is
spelled out by REFERENCE, not by copy: the bucket set, the section→bucket matcher
and the aggregation rule are all derived from ``OFFER_CLASSIFIER`` and
``ACTIVITY_PRIORITY`` in ``models/business/activity.py``. A section added to the
classifier is classified here without an edit; a reordering of ``ACTIVITY_PRIORITY``
reorders the collapse here without an edit. Two copies of one vocabulary would be
the collapse-in defect the smoke module was built to refuse.

CROSS-METHOD EQUIVALENCE (G6)
-----------------------------
``offer_grain_referent().collapse(...)`` and ``Business.max_offer_activity`` MUST
agree on every input: same ordering (ACTIVE > ACTIVATING > INACTIVE > IGNORED),
same tie behaviour, same ``None``-free domain. ``tests/unit/lifecycle/
test_activation_referent.py`` asserts that on the same objects, not by inspection.

WHAT "ACTIVATING" MEANS HERE
----------------------------
Exactly the classifier's ``activating`` group -- at authoring time
``{ACTIVATING, IMPLEMENTING, NEW LAUNCH REVIEW}`` in project ``1143843662099250``.
A transition is an ACTIVATION when it crosses INTO that bucket from any other bucket
or from an unclassified section. Moving within the bucket (``ACTIVATING`` →
``IMPLEMENTING``) is not an activation; leaving it (``IMPLEMENTING`` → ``ACTIVE``)
is not one either. Those are the smoke module's laws, restated so a reader of this
file need not open the other one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.lifecycle.activation_smoke import (
    ActivationSmokeHook,
    AggregationRule,
    LifecycleReferent,
    SmokeCheck,
    default_pipe_checks,
)
from autom8_asana.models.business.activity import (
    ACTIVITY_PRIORITY,
    OFFER_CLASSIFIER,
    AccountActivity,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from datetime import datetime

__all__ = [
    "OFFER_AGGREGATION_RULE_NAME",
    "OFFER_REFERENT_NAME",
    "offer_grain_hook",
    "offer_grain_referent",
]

#: Stamped on every transition and decision produced under this referent, so a
#: reader of the log plane can always tell WHICH vocabulary classified it.
OFFER_REFERENT_NAME = f"offers-{OFFER_CLASSIFIER.project_gid}"

#: The declared aggregation rule -- named for the property it mirrors.
OFFER_AGGREGATION_RULE_NAME = "max_offer_activity"


def _offer_matcher(section_name: str) -> str | None:
    """Section name -> bucket name under ``OFFER_CLASSIFIER``; ``None`` if unregistered."""
    activity = OFFER_CLASSIFIER.classify(section_name)
    return None if activity is None else activity.value


def _max_offer_activity_collapse(buckets: Sequence[str]) -> str:
    """Highest-priority bucket wins -- the same rule as ``Business.max_offer_activity``.

    ``ACTIVITY_PRIORITY`` is the single source of the ordering for both.
    """
    activities = [AccountActivity(bucket) for bucket in buckets]
    return min(activities, key=ACTIVITY_PRIORITY.index).value


def offer_grain_referent() -> LifecycleReferent:
    """The ruled referent: Offer grain, ``OFFER_CLASSIFIER`` vocabulary, max-collapse.

    Built fresh on each call (the referent is a frozen value object; there is no
    module-level singleton to mutate).
    """
    return LifecycleReferent(
        name=OFFER_REFERENT_NAME,
        grain="offer",
        bucket_set=frozenset(activity.value for activity in AccountActivity),
        activating_buckets=frozenset({AccountActivity.ACTIVATING.value}),
        matcher=_offer_matcher,
        project_gid=OFFER_CLASSIFIER.project_gid,
        aggregation_rule=AggregationRule(
            name=OFFER_AGGREGATION_RULE_NAME,
            collapse=_max_offer_activity_collapse,
        ),
    )


def offer_grain_hook(
    *,
    checks: Sequence[SmokeCheck] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> ActivationSmokeHook:
    """An ``ActivationSmokeHook`` bound to the ruled referent.

    ``checks`` defaults to ``default_pipe_checks()`` (the four-check end-to-end pipe
    proof). Pass an explicit sequence to narrow or widen it; pass ``()`` only in a
    test that wants to prove the empty-smoke refusal.
    """
    return ActivationSmokeHook(
        offer_grain_referent(),
        default_pipe_checks() if checks is None else checks,
        clock=clock,
    )
