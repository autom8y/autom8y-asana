"""Re-export shim -- canonical module: ``autom8_asana.core.api_settings``.

``ApiSettings`` moved below the API layer (S5 untangle-imports) because
``automation/forwarding_stage_backfill`` consumes it too. ``get_settings`` is
kept as an alias of ``get_api_settings`` -- the SAME lru_cache object, so
``get_settings.cache_clear()`` and identity-keyed overrides keep working. New
code should call ``get_api_settings`` (distinct from ``autom8_asana.settings.
get_settings``, which returns the SDK ``Settings``).
"""

from autom8_asana.core.api_settings import ApiSettings, get_api_settings

get_settings = get_api_settings

__all__ = ["ApiSettings", "get_api_settings", "get_settings"]
