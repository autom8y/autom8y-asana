"""Generate OpenAPI spec from the live FastAPI app.

Usage:
    uv run python scripts/generate_openapi.py           # Regenerate committed spec
    uv run python scripts/generate_openapi.py --check   # Verify no drift (CI mode)

Environment:
    Sets AUTOM8Y_ENV=local and AUTH_DEV_MODE=true before importing so the
    app factory initializes without real credentials or external connections.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

# Environment must be configured BEFORE any app imports touch pydantic-settings.
os.environ.setdefault("AUTOM8Y_ENV", "local")
os.environ.setdefault("AUTH_DEV_MODE", "true")

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "api-reference", "openapi.json")
SPEC_PATH = os.path.normpath(SPEC_PATH)


def _generate_spec() -> str:
    """Import the app, extract the OpenAPI dict, return deterministic JSON."""
    from autom8_asana.api.main import create_app

    app = create_app()
    spec = app.openapi()
    return json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write(content: str) -> None:
    """Write spec to the committed path."""
    os.makedirs(os.path.dirname(SPEC_PATH), exist_ok=True)
    with open(SPEC_PATH, "w") as f:
        f.write(content)
    print(f"Wrote {SPEC_PATH}")


def _check(content: str) -> bool:
    """Compare generated spec against committed file. Return True if identical."""
    if not os.path.exists(SPEC_PATH):
        print(f"ERROR: committed spec not found at {SPEC_PATH}", file=sys.stderr)
        return False

    with open(SPEC_PATH) as f:
        committed = f.read()

    if committed == content:
        print("OpenAPI spec is up to date.")
        return True

    # Write to temp file for diff context
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    print(
        f"ERROR: OpenAPI spec drift detected.\n"
        f"  Committed: {SPEC_PATH}\n"
        f"  Generated: {tmp_path}\n"
        f"  Run 'just spec-gen' to regenerate.",
        file=sys.stderr,
    )
    return False


def main() -> None:
    check_mode = "--check" in sys.argv
    content = _generate_spec()

    if check_mode:
        if not _check(content):
            sys.exit(1)
    else:
        _write(content)


if __name__ == "__main__":
    main()
