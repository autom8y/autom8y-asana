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
    # Snapshot the canonical module object before forcing a fresh re-import.
    # Popping + re-importing creates a NEW module object (new __dict__, a new
    # UniversalResolutionStrategy class, fresh module-level _tracer/logger).
    # Other test files bind `UniversalResolutionStrategy` at COLLECTION time to
    # THIS (pre-pop) object; if the re-imported object is left in sys.modules,
    # their resolve() runs against the old object's globals while their fixtures
    # patch/rebind the new one -> spans/logs vanish from the test's exporter/mock.
    # Under xdist this manifests as the intermittent universal_strategy span/log
    # flake whenever this test co-tenants a worker before them. Restore the
    # canonical object in finally so the eviction is invisible to the session.
    # See .know/defer-watch.yaml ob-universal-strategy-span-xdist + SCAR-CW-001.
    original = sys.modules.get(_MODULE)
    sys.modules.pop(_MODULE, None)
    try:
        with patch("autom8_asana.settings.get_settings", MagicMock()) as mock_get_settings:
            importlib.import_module(_MODULE)
            assert mock_get_settings.call_count == 0, (
                "Importing universal_strategy triggered get_settings() "
                f"({mock_get_settings.call_count} call(s)) — SCAR-CW-001 CP-01 regression"
            )
    finally:
        # Re-pin the collection-time module object as the canonical one. The
        # fresh re-import (asserted above) replaced TWO references: the
        # sys.modules entry AND the parent package's attribute
        # (autom8_asana.services.universal_strategy). Both must be restored:
        # `from x.y import Z` resolves via sys.modules, but `import x.y.z as w`
        # binds via the PARENT package attribute. Restoring only sys.modules
        # leaves the parent attribute pointing at the throwaway re-import, so
        # other tests' fixtures (`import ... as`) rebind a different module
        # object than their collection-time class uses -> spans/logs vanish
        # from the test's exporter/mock. This is the universal_strategy xdist
        # span/log flake (.know/defer-watch.yaml ob-universal-strategy-span-xdist).
        if original is not None:
            sys.modules[_MODULE] = original
            _parent_name, _, _attr = _MODULE.rpartition(".")
            _parent = sys.modules.get(_parent_name)
            if _parent is not None:
                setattr(_parent, _attr, original)


def test_module_importable_and_exposes_cache_accessor() -> None:
    """The deferred-load module still exposes its public cache accessor."""
    mod = importlib.import_module(_MODULE)
    assert hasattr(mod, "get_shared_index_cache")
