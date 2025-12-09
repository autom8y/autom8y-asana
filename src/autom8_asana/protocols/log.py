"""Logging provider protocol."""

from typing import Any, Protocol


class LogProvider(Protocol):
    """Protocol for logging, compatible with Python's logging.Logger.

    Any logging.Logger instance satisfies this protocol automatically.
    Custom implementations can add structured logging, correlation IDs, etc.
    """

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        ...

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        ...
