"""Constraint 5 (load-bearing): the MCP process NEVER imports the autom8_asana
domain SDK. Proven two ways — a static AST scan (no false positives from the many
DOCSTRING mentions of autom8_asana) and a clean-subprocess runtime import check.

This is the sprint-2 side of the import-safety assertion; sprint-4 owns the full
regression harness (joint per the shape sprint-2 exit criteria).
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "asana_mcp"
MCP_ROOT = Path(__file__).resolve().parents[1]


def _import_roots(pyfile: Path) -> set[str]:
    tree = ast.parse(pyfile.read_text())
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_no_static_autom8_asana_import():
    offenders = {}
    for pyfile in PKG.rglob("*.py"):
        roots = _import_roots(pyfile)
        if "autom8_asana" in roots:
            offenders[str(pyfile)] = roots
    assert not offenders, f"CONSTRAINT 5 VIOLATED — autom8_asana imported in: {offenders}"


def test_runtime_import_pulls_neither_domain_sdk_nor_core():
    """Import the whole package in a clean subprocess and assert autom8_asana is
    absent from sys.modules (the fence) AND autom8y_core is absent (proving the
    bridge import is lazy — C9a no import-time heavy pull)."""
    code = (
        "import importlib, sys\n"
        "for m in ['asana_mcp','asana_mcp.server','asana_mcp.bridge','asana_mcp.context',"
        "'asana_mcp.settings','asana_mcp.envelopes','asana_mcp.errors','asana_mcp.schemas',"
        "'asana_mcp.tools.discovery','asana_mcp.tools.query','asana_mcp.tools.resolve']:\n"
        "    importlib.import_module(m)\n"
        "assert 'autom8_asana' not in sys.modules, 'FENCE BREACH: autom8_asana imported'\n"
        "assert 'autom8y_core' not in sys.modules, 'C9a: autom8y_core pulled at import time'\n"
        "print('IMPORT_SAFE')\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(MCP_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert "IMPORT_SAFE" in proc.stdout
