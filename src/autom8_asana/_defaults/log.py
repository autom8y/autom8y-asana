"""Default logging provider."""

from __future__ import annotations

import logging
from typing import Any


class DefaultLogProvider:
    """Default logging provider using Python's logging module.

    Creates a logger named 'autom8_asana' with standard configuration.
    """

    def __init__(self, level: int = logging.INFO) -> None:
        """Initialize logger.

        Args:
            level: Logging level (default INFO)
        """
        self._logger = logging.getLogger("autom8_asana")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            self._logger.addHandler(handler)
        self._logger.setLevel(level)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(msg, *args, **kwargs)
