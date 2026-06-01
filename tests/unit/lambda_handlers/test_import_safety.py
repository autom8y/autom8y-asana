"""Import-safety regression for universal_strategy (SCAR-CW-001 CP-01).

Importing ``autom8_asana.services.universal_strategy`` must NOT trigger
``get_settings()`` / Pydantic settings construction at import time. The
dynamic-index cache TTL is read lazily at first cache construction
(``get_shared_index_cache``), not at module scope, so importing the module
before any preflight/settings gate is side-effect free.

See ``.know/scar-tissue.md`` SCAR-CW-001 (CP-01 deferred-settings-load defect).
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

_MODULE = "autom8_asana.services.universal_strategy"


def test_import_does_not_load_settings() -> None:
    """Re-importing universal_strategy must not call get_settings()."""
    # Warm transitive dependencies first so only the target module body
    # re-executes under the patch (isolates the assertion to this module).
    importlib.import_module(_MODULE)
    sys.modules.pop(_MODULE, None)

    with patch("autom8_asana.settings.get_settings", MagicMock()) as mock_get_settings:
        importlib.import_module(_MODULE)
        assert mock_get_settings.call_count == 0, (
            "Importing universal_strategy triggered get_settings() "
            f"({mock_get_settings.call_count} call(s)) — SCAR-CW-001 CP-01 regression"
        )


def test_module_importable_and_exposes_cache_accessor() -> None:
    """The deferred-load module still exposes its public cache accessor."""
    mod = importlib.import_module(_MODULE)
    assert hasattr(mod, "get_shared_index_cache")
