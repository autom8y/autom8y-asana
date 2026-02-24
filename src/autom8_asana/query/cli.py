"""In-package CLI shim.  Delegates to :mod:`autom8_query_cli`.

The real entry point lives at ``src/autom8_query_cli.py`` -- OUTSIDE the
autom8_asana package -- so that environment variables can be set before
autom8_asana/__init__.py is loaded.

This module exists so ``python -m autom8_asana.query.cli`` still works
(with the caveat that import-time log noise from autom8_asana/__init__.py
cannot be suppressed, since that module loads before this one).

For fully clean output, use::

    autom8-query <subcommand> [options]      # console_scripts entry point
    python -m autom8_query_cli <subcommand>  # equivalent standalone
"""

from __future__ import annotations

import sys

from autom8_asana.query.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
