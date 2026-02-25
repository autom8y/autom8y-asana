"""Logging configuration for autom8_asana.

This module provides a centralized logging configuration using the autom8y-log SDK
with auto-format detection for optimal developer experience.

Auto-format detection (autom8y-log 0.3.0+):
- TTY detected (dev terminal): colored console output
- No TTY (CI/production): JSON output for log aggregation

Environment variables:
- LOG_LEVEL: Override log level (DEBUG, INFO, WARNING, ERROR)
- LOG_FORMAT: Override format ("json", "console", or "auto")
- NO_COLOR: Disable colors even with TTY
- FORCE_COLOR: Force colors even without TTY

Stdlib Logging Interception:
    This module configures autom8y-log with `intercept_stdlib=True`, which redirects
    all standard library logging calls through the structured logging pipeline.

    This means modules can use standard logging without explicit SDK imports:

        import logging
        logger = logging.getLogger(__name__)
        logger.info("message")  # Intercepted and routed through autom8y-log

    Third-party libraries (httpx, uvicorn, etc.) that use stdlib logging are
    automatically integrated into the structured logging system. No action needed.

Usage:
    # At application startup (e.g., in api/main.py)
    from autom8_asana.core.logging import configure
    configure()

    # In any module
    from autom8_asana.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("message", key="value")
"""

from __future__ import annotations

from typing import Any

from autom8y_log import LogConfig, configure_logging, get_logger, reset_logging

__all__ = ["configure", "get_logger", "reset_logging"]

_configured = False


def configure(
    level: str = "INFO",
    format: str = "auto",
    intercept_stdlib: bool = True,
    additional_processors: list[Any] | None = None,
) -> None:
    """Configure logging for autom8_asana.

    Should be called once at application startup. Subsequent calls are ignored.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Default: INFO
        format: Output format. Default: "auto"
            - "auto": colored console in dev (TTY), JSON in CI/production
            - "json": always JSON output
            - "console": always colored console output
        intercept_stdlib: Redirect stdlib logging through autom8y-log. Default: True
            This ensures all logging calls (including third-party libraries)
            go through the structured logging pipeline.
        additional_processors: Optional list of structlog processors to inject
            into the processor chain. Useful for custom filtering (e.g.,
            sensitive data redaction). Processors must follow the structlog
            processor protocol: (logger, method_name, event_dict) -> event_dict.

    Example:
        # In api/main.py lifespan - auto-format detection (recommended)
        from autom8_asana.core.logging import configure
        configure()

        # With custom processors (e.g., sensitive field filtering)
        configure(additional_processors=[my_filter_processor])
    """
    global _configured
    if _configured:
        return

    # format="auto" gives:
    # - Colored console output in dev (TTY detected)
    # - JSON output in CI/production (no TTY)
    config = LogConfig(
        backend="structlog",
        level=level,  # type: ignore[arg-type]
        format=format,  # type: ignore[arg-type]
        intercept_stdlib=intercept_stdlib,
    )
    configure_logging(config, additional_processors=additional_processors)
    _configured = True
