"""Onboarding walkthrough workflow package (3rd data-attachment-bridge sibling).

Per PRD/TDD/ADR (seam A2 x B1): attaches a personalized, gated walkthrough deck
to onboarding tasks whose Calendar Provider triggers a walkthrough.
"""

from __future__ import annotations

from autom8_asana.automation.workflows.onboarding_walkthrough.constants import (
    WALKTHROUGH_DECK_DEFAULT,
    WALKTHROUGH_DECK_MAP,
    WALKTHROUGH_ENABLED_ENV_VAR,
    WALKTHROUGH_TRIGGER_VALUES,
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
    "WALKTHROUGH_DECK_MAP",
    "WALKTHROUGH_ENABLED_ENV_VAR",
    "WALKTHROUGH_TRIGGER_VALUES",
    "OnboardingWalkthroughWorkflow",
    "ProducerFreezeError",
    "freeze_walkthrough_deck",
]
