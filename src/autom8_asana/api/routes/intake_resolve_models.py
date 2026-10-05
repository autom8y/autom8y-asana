"""Re-export shim -- canonical module: ``autom8_asana.services.wire.intake_resolve_models``.

Moved below the API layer (S5 untangle-imports) so lower layers can use these
definitions without importing the api package. Kept so existing importers
(api modules, tests) resolve unchanged; every name is the same object.
"""

from autom8_asana.services.wire.intake_resolve_models import (
    BusinessByEmailResolveRequest,
    BusinessByEmailResolveResponse,
    BusinessResolveRequest,
    BusinessResolveResponse,
    ContactResolveRequest,
    ContactResolveResponse,
)

__all__ = [
    "BusinessByEmailResolveRequest",
    "BusinessByEmailResolveResponse",
    "BusinessResolveRequest",
    "BusinessResolveResponse",
    "ContactResolveRequest",
    "ContactResolveResponse",
]
