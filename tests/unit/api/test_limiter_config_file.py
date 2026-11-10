"""The rate limiter never loads settings from a config file.

``Limiter`` reads a settings file from the working directory by default when
one is present. asana configures the limiter from code and the environment
only, so it must always name a fixed path that never exists.
"""

from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING, Any

from autom8_asana.api import rate_limit

if TYPE_CHECKING:
    import pytest


def test_limiter_config_filename_is_a_fixed_absent_non_dotenv_path() -> None:
    path = rate_limit.LIMITER_CONFIG_FILENAME
    assert os.path.isabs(path)
    assert not os.path.exists(path)
    assert not os.path.basename(path).startswith(".env")


def test_build_limiter_passes_the_fixed_config_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import slowapi.extension as extension

    seen: list[Any] = []
    real_config = extension.Config

    def spy(env_file: Any = None, *args: Any, **kwargs: Any) -> Any:
        seen.append(env_file)
        return real_config(env_file, *args, **kwargs)

    monkeypatch.setattr(extension, "Config", spy)
    rate_limit._build_limiter()

    assert seen == [rate_limit.LIMITER_CONFIG_FILENAME]


def test_module_limiter_holds_no_file_values() -> None:
    assert rate_limit.limiter.app_config.file_values == {}


def test_build_limiter_emits_no_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        rate_limit._build_limiter()
