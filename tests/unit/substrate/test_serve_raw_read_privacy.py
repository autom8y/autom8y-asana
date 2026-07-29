"""[H17] structural tooth — the store's raw byte-reader is private to serve/rebuild/observe.

"store.read_current / load_dataframe are module-private to substrate.{serve,rebuild};
an import-layer tooth forbids importing them elsewhere ... Rebuilder + parity harness
reach raw bytes via a DISTINCT non-serving capability." A CONSUMER (adapter, service
route, MCP) must obtain a number ONLY through the ``SubstrateReader`` gate — never by
importing ``substrate.store`` and reading raw bytes past the freshness check.

This scans the whole ``src/autom8_asana`` tree (AST, mirroring the concurrency-guard
pattern) so a future consumer that reaches into the v2 store is caught at import
altitude, not by review vigilance.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
_AUTOM8 = _SRC / "autom8_asana"
_SUBSTRATE_STORE_MODULE = "autom8_asana.substrate.store"

# The ONLY modules permitted to import the v2 store's raw reader: the three inward
# consumers named in the seam (serve, rebuild, observe) + the store's own definition
# home + the package __init__ that RE-EXPORTS the contract types (Protocol/exceptions/
# type aliases — not a raw read). Paths are relative to src/.
_ALLOWED_STORE_IMPORTERS = {
    "autom8_asana/substrate/serve.py",
    "autom8_asana/substrate/rebuild.py",
    "autom8_asana/substrate/observe.py",
    "autom8_asana/substrate/store.py",
    "autom8_asana/substrate/__init__.py",
}


def _imports_substrate_store(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == _SUBSTRATE_STORE_MODULE:
            return True
        if isinstance(node, ast.Import):
            if any(alias.name == _SUBSTRATE_STORE_MODULE for alias in node.names):
                return True
    return False


def test_substrate_store_is_imported_only_by_serve_rebuild_observe() -> None:
    """No module outside {serve, rebuild, observe, store, __init__} imports the v2 store."""
    importers: set[str] = set()
    for py in _AUTOM8.rglob("*.py"):
        rel = py.relative_to(_SRC).as_posix()
        if _imports_substrate_store(ast.parse(py.read_text())):
            importers.add(rel)
    unexpected = importers - _ALLOWED_STORE_IMPORTERS
    assert not unexpected, (
        f"module(s) reach the v2 store's raw reader outside the seam allowlist: {sorted(unexpected)}. "
        "A consumer must go through substrate.serve.SubstrateReader, never substrate.store ([H17])."
    )


def test_serve_adapters_do_not_import_the_store() -> None:
    """The consumer-facing adapter module reaches numbers ONLY through the reader gate."""
    adapters = _AUTOM8 / "substrate" / "serve_adapters.py"
    assert not _imports_substrate_store(ast.parse(adapters.read_text())), (
        "serve_adapters.py must NOT import substrate.store — the adapters hold a SubstrateReader, "
        "so a plane-blind / gate-blind raw read is unconstructable at the consumer surface ([H17])."
    )


def test_serve_adapters_never_call_read_current() -> None:
    """Belt-and-suspenders: the adapters call the reader's ``read``, never ``read_current``.

    AST-based (attribute-access nodes only) so a docstring MENTION of ``read_current``
    — the prose explaining WHY it is forbidden — is correctly ignored; only a real
    ``.read_current`` access trips it.
    """
    adapters = _AUTOM8 / "substrate" / "serve_adapters.py"
    tree = ast.parse(adapters.read_text())
    accesses = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "read_current"
    ]
    assert not accesses, (
        "an adapter accesses .read_current — that would bypass the freshness gate ([H17]/C2)."
    )
