"""Re-export shim -- canonical module: ``autom8_asana.services.wire.intake_create_models``.

Moved below the API layer (S5 untangle-imports) so lower layers can use these
definitions without importing the api package. Kept so existing importers
(api modules, tests) resolve unchanged; every name is the same object.
"""

from autom8_asana.services.wire.intake_create_models import (
    IntakeAddress,
    IntakeBusinessCreateRequest,
    IntakeBusinessCreateResponse,
    IntakeContact,
    IntakeProcessConfig,
    IntakeRouteRequest,
    IntakeRouteResponse,
    IntakeSocialProfile,
)

__all__ = [
    "IntakeAddress",
    "IntakeBusinessCreateRequest",
    "IntakeBusinessCreateResponse",
    "IntakeContact",
    "IntakeProcessConfig",
    "IntakeRouteRequest",
    "IntakeRouteResponse",
    "IntakeSocialProfile",
]
