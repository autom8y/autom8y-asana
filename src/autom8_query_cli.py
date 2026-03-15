#!/usr/bin/env python
"""Standalone CLI entry point for autom8_asana.query.

Sets required environment variables BEFORE importing the package tree,
bypassing the settings guard (AUTOM8Y_DATA_URL production check) and
suppressing import-time log noise (structlog JSON from HolderFactory,
schema warnings, etc.).

Invocation (after ``pip install -e .``):
    autom8-query <subcommand> [options]

This module lives OUTSIDE the autom8_asana package so that importing it
does not trigger autom8_asana/__init__.py.  The env-var setup in main()
therefore runs before any autom8_asana code is loaded.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    """CLI entry point with pre-import environment setup."""
    # G-01: Bypass settings guard for offline CLI.
    os.environ.setdefault("AUTOM8Y_DATA_URL", "http://offline-cli.local")
    os.environ.setdefault("ASANA_WORKSPACE_GID", "offline")
    # G-02: Suppress import-time structlog noise.
    # autom8y_log reads LOG_LEVEL during its auto-configure step.
    os.environ.setdefault("LOG_LEVEL", "ERROR")

    from autom8_asana.query.__main__ import main as _main

    return _main()


if __name__ == "__main__":
    sys.exit(main())
