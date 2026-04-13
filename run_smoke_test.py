#!/usr/bin/env python3
"""Smoke test runner: full pipeline execution + local HTML save.

Runs the insights export handler against a single offer (full upload to Asana),
and also saves the generated HTML locally for analysis.

Modes (controlled by SMOKE_MODE env var):
  production (default) -- hits https://data.api.autom8y.io/ with a real JWT
  local                -- hits http://localhost:5200 (local dev stack via `just dev-up data`)

Examples:
  .venv/bin/python run_smoke_test.py                          # production
  SMOKE_MODE=local .venv/bin/python run_smoke_test.py         # local dev stack
  SMOKE_MODE=local AUTOM8_DATA_URL=http://localhost:5201 ...  # custom port
"""

import json
import os
import pathlib
import sys
import time
from datetime import UTC, datetime
from unittest.mock import patch

# Ensure the package is importable
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

OFFER_GID = os.environ.get("SMOKE_TEST_OFFER", "1211403363567747")
OUTPUT_DIR = pathlib.Path("smoke_output")

# Mode selection: "local" targets local dev stack, anything else hits production
_SMOKE_MODE = os.environ.get("SMOKE_MODE", "production").lower()

if _SMOKE_MODE == "local":
    # Local dev stack: data service at localhost:5200, no real JWT needed.
    # Do NOT set AUTOM8Y_ENV or ASANA_ENVIRONMENT -- leaves the asana guard dormant
    # (the explicit-only guard only fires when ASANA_ENVIRONMENT is explicitly set).
    os.environ.setdefault("AUTOM8_DATA_URL", "http://localhost:5200")
    os.environ.setdefault("AUTOM8_DATA_API_KEY", "local-dev-token")
else:
    # Production: allow production URL in local invocation
    os.environ["AUTOM8Y_ENV"] = "production"


def _ensure_data_api_token() -> None:
    """Exchange service credentials for data API bearer token if not already set.

    Uses platform autom8y_core.TokenManager for S2S JWT exchange.
    Reads SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET from environment
    (ServiceAccount convention). Falls back to SERVICE_API_KEY via Config.from_env().
    """
    if _SMOKE_MODE == "local":
        return  # Local dev stack does not require JWT auth

    if os.environ.get("AUTOM8_DATA_API_KEY"):
        return

    from autom8y_core import Config, TokenManager

    try:
        config = Config.from_env()
    except ValueError:
        raise RuntimeError(
            "SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET not found in environment. "
            "Set them or source .env/production."
        )

    manager = TokenManager(config)
    token = manager.get_token()
    manager.close()

    os.environ["AUTOM8_DATA_API_KEY"] = token
    print(f"  Auth token acquired (length: {len(token)})")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    _ensure_data_api_token()

    # Fix forward references: many models use NameGid under TYPE_CHECKING.
    # Inject NameGid into each module's namespace so Pydantic can resolve it.
    from autom8_asana.models import common as _common_mod

    NameGid = _common_mod.NameGid  # noqa: N806

    import autom8_asana.models.business.base as _base_mod
    import autom8_asana.models.task as _task_mod

    _task_mod.NameGid = NameGid  # type: ignore[attr-defined]
    _base_mod.NameGid = NameGid  # type: ignore[attr-defined]
    _task_mod.Task.model_rebuild()
    _base_mod.BusinessEntity.model_rebuild()

    # Rebuild all models that inherit from Task / use NameGid
    import autom8_asana.models.attachment as _attach_mod
    import autom8_asana.models.project as _project_mod
    import autom8_asana.models.section as _section_mod
    import autom8_asana.models.story as _story_mod
    from autom8_asana.models.attachment import Attachment
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.offer import Offer
    from autom8_asana.models.business.unit import Unit
    from autom8_asana.models.project import Project
    from autom8_asana.models.section import Section
    from autom8_asana.models.story import Story

    for mod in [_attach_mod, _project_mod, _section_mod, _story_mod]:
        mod.NameGid = NameGid  # type: ignore[attr-defined]

    for cls in [Business, Offer, Unit, Attachment, Project, Section, Story]:
        cls.model_rebuild()

    # Increase read timeout for heavy analytics queries (default 30s is too low)
    from autom8_asana.clients.data import config as _data_config

    _orig_timeout_init = _data_config.TimeoutConfig.__post_init__
    # Replace the frozen dataclass default by creating a new default factory
    _data_config.DataServiceConfig.__dataclass_fields__["timeout"].default_factory = lambda: (
        _data_config.TimeoutConfig(connect=10.0, read=120.0, write=30.0, pool=10.0)
    )

    # Capture HTML during compose_report — must patch in insights_export module
    # because it imports compose_report as a direct name binding
    captured_html: dict[str, str] = {}
    from autom8_asana.automation.workflows import insights_export as _export_mod

    original_compose = _export_mod.compose_report

    def capturing_compose(report_data):
        html = original_compose(report_data)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        offer_gid = getattr(report_data, "offer_gid", "unknown")
        filename = f"insights_export_{offer_gid}_{ts}.html"
        local_path = OUTPUT_DIR / filename
        local_path.write_text(html, encoding="utf-8")
        size_kb = len(html.encode("utf-8")) / 1024
        print(f"\n  HTML saved: {local_path} ({size_kb:.1f} KB)")
        captured_html[offer_gid] = str(local_path)
        return html

    # Import and run the handler with compose_report patched
    from autom8_asana.lambda_handlers.insights_export import handler

    event = {
        "entity_ids": [OFFER_GID],
        "dry_run": False,
    }

    data_url = os.environ.get("AUTOM8_DATA_URL", "(production default)")
    print("Starting insights export smoke test")
    print(f"  Offer: {OFFER_GID}")
    print(f"  SMOKE_MODE: {_SMOKE_MODE}")
    print("  Mode: FULL (upload to Asana + local save)")
    print(f"  Data API: {data_url}")
    print(f"  Time: {datetime.now(UTC).isoformat()}")
    print()

    start = time.monotonic()

    with patch.object(_export_mod, "compose_report", capturing_compose):
        result = handler(event, None)

    elapsed = time.monotonic() - start

    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"Response: {json.dumps(json.loads(result.get('body', '{}')), indent=2)}")

    if captured_html:
        print("\nLocal HTML files:")
        for gid, path in captured_html.items():
            print(f"  {gid}: {path}")
    else:
        print("\nWARNING: No HTML was captured (compose_report may not have been called)")

    # Exit with appropriate code
    body = json.loads(result.get("body", "{}"))
    if body.get("status") == "error" or result.get("statusCode") != 200:
        print(f"\nFAILED: {body.get('error', 'unknown error')}")
        sys.exit(1)
    elif body.get("status") == "skipped":
        print(f"\nSKIPPED: {body.get('reason', 'unknown')}")
        sys.exit(2)
    else:
        print("\nSUCCESS")


if __name__ == "__main__":
    main()
