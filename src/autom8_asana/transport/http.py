"""HTTP transport module - legacy AsyncHTTPClient removed.

Per TDD-ASANA-HTTP-MIGRATION-001/FR-005: The legacy AsyncHTTPClient has been
removed in favor of autom8y-http platform SDK. Use AsanaHttpClient instead.

This module is preserved for import compatibility but no longer contains
implementation code. All transport logic has migrated to autom8y-http.
"""

from __future__ import annotations

# This module previously contained AsyncHTTPClient but it has been removed.
# For backward compatibility, imports of AsyncHTTPClient from this module
# are handled by __init__.py's __getattr__ deprecation mechanism.
