"""Onboarding walkthrough workflow package (3rd data-attachment-bridge sibling).

Per PRD/TDD/ADR (seam A2 x B1): attaches a personalized, gated walkthrough deck
to ACTIVE calendar-integration onboarding tasks. Selection is provider-agnostic
(rulings 2026-07-02): ANY present Calendar Provider value onboards via the
universal ``WALKTHROUGH_DECK_DEFAULT``; the provider is metadata, not a gate.
"""

from __future__ import annotations

from autom8_asana.automation.workflows.onboarding_walkthrough.constants import (
    WALKTHROUGH_DECK_DEFAULT,
    WALKTHROUGH_DECK_OVERRIDES,
    WALKTHROUGH_ENABLED_ENV_VAR,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.producer import (
    ProducerFreezeError,
    freeze_walkthrough_deck,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.workflow import (
    OnboardingWalkthroughWorkflow,
)

__all__ = [
    "WALKTHROUGH_DECK_DEFAULT",
    "WALKTHROUGH_DECK_OVERRIDES",
    "WALKTHROUGH_ENABLED_ENV_VAR",
    "OnboardingWalkthroughWorkflow",
    "ProducerFreezeError",
    "freeze_walkthrough_deck",
]
