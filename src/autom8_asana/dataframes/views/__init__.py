"""View plugins for unified cache materialization.

Per TDD-UNIFIED-CACHE-001 Phase 2: View plugins that consume UnifiedTaskStore
to provide DataFrame and cascade field materialization.

This package provides:
- CascadeViewPlugin: Resolves cascading fields using unified cache
- DataFrameViewPlugin: Materializes DataFrames from cached tasks
"""

from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin
from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin

__all__ = [
    "CascadeViewPlugin",
    "DataFrameViewPlugin",
]
