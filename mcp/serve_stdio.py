#!/usr/bin/env python3
"""Stdio launcher for the asana_mcp sidecar — the Claude Code witness mount entrypoint.

REFERENCE / THROWAWAY POSTURE (charter §5.3): NOT production code. At tech-transfer this
is a REFERENCE IMPLEMENTATION ONLY — reimplement against production contracts.

MODES
  (default)  Build the instrumented server and serve it over stdio (the MCP mount a
             Claude Code client spawns). Banner suppressed so nothing contaminates the
             JSON-RPC stdout stream.
  --smoke    Build the server, list its tools + the write-surface flag state, print a
             JSON inventory, exit 0. MECHANICAL verification only — NOT a witness act.
             Add --fake-token to inject a fake S2S provider so the smoke mints NOTHING.

LIVE S2S MINT (default mode, no --fake-token)
  The sidecar's default provider mints lazily via ``autom8y_core.TokenManager.from_env()``
  on the FIRST outbound request. ``Config.from_env`` reads the credential pair from:
      AUTOM8Y_DATA_SERVICE_CLIENT_ID   | CLIENT_ID       (client id)
      AUTOM8Y_DATA_SERVICE_CLIENT_SECRET | CLIENT_SECRET (client secret)
  NOTE (constraint discovered at witness prep): these are NOT the ``SERVICE_CLIENT_ID`` /
  ``SERVICE_CLIENT_SECRET`` names the deployed satellite env uses. The operator MAPS them
  at witness time — see the go-runbook (`asana-mcp-v1.witness-go-runbook.md`) step 2.

STANDING FENCES (held): never imports the autom8_asana domain SDK; zero direct Asana
calls (speaks HTTP only to the satellite REST surface via ctx.http). The write surface is
EXPOSURE-GATED on ASANA_MCP_ENABLE_WRITE_SURFACE (default OFF); this launcher never sets it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys


def _install_fake_token_provider() -> None:
    """Smoke-only: replace the live S2S provider with a fake (no mint, no autom8y_core call)."""
    import asana_mcp.bridge as bridge

    async def _fake() -> str:
        return "fake.s2s.jwt.NOT-A-REAL-MINT"

    bridge._default_token_provider = lambda: _fake  # type: ignore[attr-defined]


def _build():
    from asana_mcp.assembly import build_instrumented_server

    return build_instrumented_server()


async def _smoke(fake: bool) -> int:
    if fake:
        _install_fake_token_provider()
    mcp = _build()
    tools = await mcp.list_tools()  # FastMCP 3.4.4 public API
    names = sorted(t.name for t in tools)
    flag = os.environ.get("ASANA_MCP_ENABLE_WRITE_SURFACE", "")
    inventory = {
        "server": "asana-mcp",
        "write_surface_flag_env": flag or "(unset -> OFF)",
        "write_tool_present": "asana_complete_tagged_task" in names,
        "tool_count": len(names),
        "tools": names,
    }
    print(json.dumps(inventory, indent=2))
    return 0


def _serve() -> int:
    mcp = _build()
    # stdio is the Claude Code mount transport; banner OFF keeps stdout clean for JSON-RPC.
    mcp.run(transport="stdio", show_banner=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="asana_mcp stdio launcher (reference POC).")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Build + list tools + flag state as JSON, then exit (mechanical, not a witness).",
    )
    parser.add_argument(
        "--fake-token",
        action="store_true",
        help="Smoke only: inject a fake token provider so no live S2S mint occurs.",
    )
    args = parser.parse_args(argv)
    if args.smoke:
        return asyncio.run(_smoke(args.fake_token))
    if args.fake_token:
        print("--fake-token is only valid with --smoke", file=sys.stderr)
        return 2
    return _serve()


if __name__ == "__main__":
    raise SystemExit(main())
