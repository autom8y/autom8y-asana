"""Re-export shim -- canonical module: ``autom8_asana.core.api_exceptions``.

Moved below the API layer (S5 untangle-imports) so lower layers can use these
definitions without importing the api package. Kept so existing importers
(api modules, tests) resolve unchanged; every name is the same object.
"""

from autom8_asana.core.api_exceptions import (
    ApiAuthError,
    ApiDataFrameBuildError,
    ApiError,
    ApiServiceUnavailableError,
)

__all__ = [
    "ApiError",
    "ApiAuthError",
    "ApiServiceUnavailableError",
    "ApiDataFrameBuildError",
]
