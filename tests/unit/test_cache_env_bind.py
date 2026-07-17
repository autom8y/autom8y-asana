"""F-2 regression: the documented ASANA_CACHE_* knobs BIND on the default path.

Per ADR-taskcache-projection-coverage-2026-07-08 fork (e): config.py's
``AsanaConfig.cache`` default_factory is now ``CacheConfig.from_env``, making
``ASANA_CACHE_ENABLED=false`` the zero-code-mutation operator kill-switch for
the cache (and the PHE coverage machinery). Before the bind these knobs were
documented but DEAD on the default ``AsanaClient()`` path -- this suite was
impossible to write truthfully pre-fix.

Precedence pins (must stay byte-identical): explicit ``AsanaConfig(cache=...)``
bypasses the default_factory; explicit ``AsanaClient(cache_provider=...)`` wins
over everything (factory.create_cache_provider explicit_provider precedence).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana._defaults.cache import NullCacheProvider
from autom8_asana.cache.integration.factory import create_cache_provider
from autom8_asana.client import AsanaClient
from autom8_asana.config import AsanaConfig, CacheConfig

if TYPE_CHECKING:
    import pytest


class TestEnvKillSwitch:
    """ASANA_CACHE_ENABLED=false disables the default AsanaClient cache."""

    def test_cache_enabled_false_yields_null_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """THE kill-switch: env false => default client gets NullCacheProvider.

        Pre-bind this test failed (the env var was documented but never read
        on the default path -- F-2's dead knob)."""
        monkeypatch.setenv("ASANA_CACHE_ENABLED", "false")

        client = AsanaClient(token="test-token")

        assert isinstance(client._cache_provider, NullCacheProvider)

    def test_cache_provider_none_yields_null_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ASANA_CACHE_PROVIDER", "none")

        client = AsanaClient(token="test-token")

        assert isinstance(client._cache_provider, NullCacheProvider)

    def test_unset_env_auto_detect_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clean env => the bound default selects exactly what the pre-bind
        auto-detect chain selected for a plain CacheConfig()."""
        monkeypatch.delenv("ASANA_CACHE_ENABLED", raising=False)
        monkeypatch.delenv("ASANA_CACHE_PROVIDER", raising=False)

        client = AsanaClient(token="test-token")
        pre_bind_equivalent = create_cache_provider(CacheConfig())

        assert type(client._cache_provider) is type(pre_bind_equivalent)
        assert not isinstance(client._cache_provider, NullCacheProvider)

    def test_from_env_reads_fresh_not_singleton(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The kill-switch must be reliable: from_env constructs fresh settings
        per call (a cached/singleton read would freeze the first value)."""
        monkeypatch.setenv("ASANA_CACHE_ENABLED", "false")
        assert AsanaConfig().cache.enabled is False

        monkeypatch.setenv("ASANA_CACHE_ENABLED", "true")
        assert AsanaConfig().cache.enabled is True


class TestExplicitPrecedenceUntouched:
    """Programmatic config/provider still beat the env bind."""

    def test_explicit_config_bypasses_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASANA_CACHE_ENABLED", "false")

        explicit = AsanaConfig(cache=CacheConfig(enabled=True, provider="memory"))
        client = AsanaClient(token="test-token", config=explicit)

        assert not isinstance(client._cache_provider, NullCacheProvider)

    def test_explicit_provider_wins_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ASANA_CACHE_ENABLED", "false")

        sentinel = NullCacheProvider()
        client = AsanaClient(token="test-token", cache_provider=sentinel)

        assert client._cache_provider is sentinel

    def test_explicit_null_provider_still_works(self) -> None:
        """NFR-COMPAT-004: the pre-bind workaround keeps working unchanged."""
        client = AsanaClient(token="test-token", cache_provider=NullCacheProvider())

        assert isinstance(client._cache_provider, NullCacheProvider)
