"""Auto-import all metric definition modules.

When this package is imported (by MetricRegistry._ensure_initialized),
all submodules are imported, triggering their module-level registration
with the MetricRegistry singleton.

To add new metrics: create a new .py file in this directory that
instantiates Metric objects and calls MetricRegistry().register().
"""

from autom8_asana.metrics.definitions import offer  # noqa: F401
