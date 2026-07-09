"""Pure domain layer for autom8_asana.

Modules here depend on NOTHING in the infrastructure layer (no client, no
config, no I/O). They codify contracts (enums, validators, pure functions) that
the application/service layer satisfies. See Clean-Architecture / DIP: the
domain defines the shape; infrastructure points inward at it, never the reverse.
"""

from autom8_asana.domain.forwarding_stage import (
    RECEIPT_KIND_TO_STAGE,
    ForwardingStage,
    StageDisposition,
    StageRankTable,
    StageTransitionValidator,
    TransitionDecision,
    TransitionOutcome,
)

__all__ = [
    "RECEIPT_KIND_TO_STAGE",
    "ForwardingStage",
    "StageDisposition",
    "StageRankTable",
    "StageTransitionValidator",
    "TransitionDecision",
    "TransitionOutcome",
]
