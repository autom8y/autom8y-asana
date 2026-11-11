"""The D6 hook environment marker, ``ASANA_HOOK_ENVIRONMENT`` (TDD section 2a, W D-2).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.6, section 2a ("The
marker") and section 9 fixtures PM-1, PM-3 and PM-5.

One variable, read once when a consumer is constructed, compared EXACTLY. There is no
trimming and no case folding, so ``" local "``, ``"local\\n"`` and ``"Production"`` are
all unrecognized. Each side has its own positive value:

* ``production``: ``hook_store`` may write (its task-role check still applies), and
  building any test adapter raises.
* ``test`` or ``local``: the test adapters may build, and ``hook_store`` refuses to write.
* Anything else, absent and empty included: both refuse, loudly. The refusal is a typed
  error plus one ``hook_environment_refused`` log event that names the variable and
  whether it was absent, empty or unrecognized. The value itself is never logged.

There is no silent skip and no noop fallback anywhere on this path.

The shadow flag ``ASANA_HOOK_SHADOW_ENABLED`` is read here too, because startup with the
flag on must fail on a refused marker (section 2a). The flag is on only when it is
exactly ``"1"``.
"""

from __future__ import annotations

import os
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)

MARKER_ENV_VAR: Final[str] = "ASANA_HOOK_ENVIRONMENT"
SHADOW_FLAG_ENV_VAR: Final[str] = "ASANA_HOOK_SHADOW_ENABLED"
SHADOW_FLAG_ON: Final[str] = "1"


class HookEnvironment(StrEnum):
    """The three recognized marker values. Nothing else is recognized."""

    PRODUCTION = "production"
    TEST = "test"
    LOCAL = "local"


class MarkerCondition(StrEnum):
    """Why a marker read refused. Never carries the value."""

    ABSENT = "absent"
    EMPTY = "empty"
    UNRECOGNIZED = "unrecognized"
    WRONG_SIDE = "wrong_side"


class HookEnvironmentRefused(RuntimeError):
    """The marker does not permit the requested side (store write or test adapter)."""

    def __init__(self, *, consumer: str, condition: MarkerCondition) -> None:
        self.consumer = consumer
        self.condition = condition
        super().__init__(
            f"{consumer} refused: {MARKER_ENV_VAR} is {condition.value} "
            f"(the store writes only on exactly {HookEnvironment.PRODUCTION.value!r}; "
            f"test adapters build only on exactly {HookEnvironment.TEST.value!r} or "
            f"{HookEnvironment.LOCAL.value!r})"
        )


_RECOGNIZED: Final[dict[str, HookEnvironment]] = {e.value: e for e in HookEnvironment}


def _environ(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def _refuse(consumer: str, condition: MarkerCondition) -> HookEnvironmentRefused:
    logger.error(
        "hook_environment_refused",
        extra={
            "variable": MARKER_ENV_VAR,
            "condition": condition.value,
            "consumer": consumer,
        },
    )
    return HookEnvironmentRefused(consumer=consumer, condition=condition)


def read_hook_environment(
    *, consumer: str, environ: Mapping[str, str] | None = None
) -> HookEnvironment:
    """Read the marker once and return its recognized value, or refuse loudly.

    Absent, empty and unrecognized values raise :class:`HookEnvironmentRefused` after one
    ``hook_environment_refused`` log event. The comparison is exact.
    """
    env = _environ(environ)
    if MARKER_ENV_VAR not in env:
        raise _refuse(consumer, MarkerCondition.ABSENT)
    raw = env[MARKER_ENV_VAR]
    if raw == "":
        raise _refuse(consumer, MarkerCondition.EMPTY)
    recognized = _RECOGNIZED.get(raw)
    if recognized is None:
        raise _refuse(consumer, MarkerCondition.UNRECOGNIZED)
    return recognized


def require_production(
    *, consumer: str, environ: Mapping[str, str] | None = None
) -> HookEnvironment:
    """Return the marker only if it is exactly ``production``; otherwise refuse."""
    marker = read_hook_environment(consumer=consumer, environ=environ)
    if marker is not HookEnvironment.PRODUCTION:
        raise _refuse(consumer, MarkerCondition.WRONG_SIDE)
    return marker


def require_test_adapter_environment(
    *, consumer: str, environ: Mapping[str, str] | None = None
) -> HookEnvironment:
    """Return the marker only if it is exactly ``test`` or ``local``; otherwise refuse.

    Every test adapter (in-memory registry, test-key store) calls this in its
    constructor. Those adapters live under ``tests/`` only (PM-2).
    """
    marker = read_hook_environment(consumer=consumer, environ=environ)
    if marker is HookEnvironment.PRODUCTION:
        raise _refuse(consumer, MarkerCondition.WRONG_SIDE)
    return marker


def shadow_flag_on(environ: Mapping[str, str] | None = None) -> bool:
    """``True`` only when ``ASANA_HOOK_SHADOW_ENABLED`` is exactly ``"1"``."""
    return _environ(environ).get(SHADOW_FLAG_ENV_VAR) == SHADOW_FLAG_ON


def assert_shadow_startup(environ: Mapping[str, str] | None = None) -> HookEnvironment | None:
    """The startup gate. Returns ``None`` (shadow off) or the recognized marker.

    With the shadow flag on, a refused marker raises, so startup fails (section 2a). With
    the flag off this reads nothing else and returns ``None``.
    """
    if not shadow_flag_on(environ):
        return None
    return read_hook_environment(consumer="shadow_startup", environ=environ)
