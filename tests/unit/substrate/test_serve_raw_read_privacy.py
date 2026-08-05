"""[H17] structural tooth — the store's raw byte-reader is private to serve/rebuild/observe.

"store.read_current / load_dataframe are module-private to substrate.{serve,rebuild};
an import-layer tooth forbids importing them elsewhere ... Rebuilder + parity harness
reach raw bytes via a DISTINCT non-serving capability." A CONSUMER (adapter, service
route, MCP) must obtain a number ONLY through the ``SubstrateReader`` gate — never by
reaching the raw byte reader past the freshness check.

QA F-2 (MEDIUM, tooth-completeness) HARDENING: the original tooth caught a DIRECT
``import substrate.store`` but a REACHABILITY bypass stayed green — a module that imports
only the ``ArtifactStore`` Protocol (a package-root export) and calls ``.read_current`` on
an INJECTED concrete store trips no import-name check. This tooth now scans
``.read_current`` / ``.load_dataframe`` ATTRIBUTE-access sites tree-wide (reachability, not
import-name) against the seam allowlist, and a meta-test plants the qa's injected-store
bypass to prove the tooth now BITES it.

KNOWN LIMITATION (deliberately not chased): a fully-dynamic access —
``getattr(store, "read_" + "current")`` or ``importlib.import_module(...)`` string
construction — evades AST attribute-name matching. This tooth targets DRIFT (an honest
engineer adding a layer, the exact RC-C "guard missed a layer" recurrence class), NOT
sabotage; a determined author has many paths and the structural guarantee is the typed
``SubstrateReader`` gate, not this lint.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
_AUTOM8 = _SRC / "autom8_asana"
_SUBSTRATE = _AUTOM8 / "substrate"
_SUBSTRATE_STORE_MODULE = "autom8_asana.substrate.store"

# The ONLY modules permitted to import the v2 store's contract surface: the three inward
# consumers named in the seam (serve, rebuild, observe) + the store's own definition home
# + the package __init__ that RE-EXPORTS the contract types (Protocol/exceptions/type
# aliases — not a raw read) + the WU-3 arming composition root (live, prov_sweep) that WIRES
# an injected store into rebuild/observe as a TYPE for construction (``store: S3ArtifactStore``
# for the ``SubstrateRebuilder`` caller / ``ArtifactStore`` for the sweep evaluator) — never a
# raw ``.read_current`` (they are absent from ``_ALLOWED_READ_CURRENT_CALLERS`` below, and the
# F-2 reachability tooth would BITE if they ever reached the raw byte reader). Paths rel to src/.
_ALLOWED_STORE_IMPORTERS = {
    "autom8_asana/substrate/serve.py",
    "autom8_asana/substrate/rebuild.py",
    "autom8_asana/substrate/observe.py",
    "autom8_asana/substrate/store.py",
    "autom8_asana/substrate/__init__.py",
    "autom8_asana/substrate/live.py",
    "autom8_asana/substrate/prov_sweep.py",
}

# The ONLY modules permitted to REACH the raw byte reader (call ``.read_current``): the
# seam's inward consumers + the store's definition home. __init__ re-exports contract
# TYPES but never calls read_current, so it is not on this (call-site) allowlist.
_ALLOWED_READ_CURRENT_CALLERS = {
    "autom8_asana/substrate/serve.py",
    "autom8_asana/substrate/rebuild.py",
    "autom8_asana/substrate/observe.py",
    "autom8_asana/substrate/store.py",
}


def _imports_substrate_store(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == _SUBSTRATE_STORE_MODULE:
            return True
        if isinstance(node, ast.Import) and any(
            alias.name == _SUBSTRATE_STORE_MODULE for alias in node.names
        ):
            return True
    return False


def _source_accesses_attr(source: str, attr_name: str) -> bool:
    """True iff the source has an ``ast.Attribute`` access ``.{attr_name}`` (reachability)."""
    return any(
        isinstance(n, ast.Attribute) and n.attr == attr_name for n in ast.walk(ast.parse(source))
    )


def _modules_accessing_attr(attr_name: str) -> set[str]:
    """src modules (rel to src/) that ATTRIBUTE-access ``.{attr_name}`` — import-name-agnostic."""
    return {
        py.relative_to(_SRC).as_posix()
        for py in _AUTOM8.rglob("*.py")
        if _source_accesses_attr(py.read_text(), attr_name)
    }


def _modules_importing_name(root: Path, name: str) -> set[str]:
    hits: set[str] = set()
    for py in root.rglob("*.py"):
        for node in ast.walk(ast.parse(py.read_text())):
            if isinstance(node, ast.ImportFrom) and any(a.name == name for a in node.names):
                hits.add(py.relative_to(_SRC).as_posix())
    return hits


# ------------------------------------------------------ import-name tooth (kept) ---


def test_substrate_store_is_imported_only_by_serve_rebuild_observe() -> None:
    """No module outside {serve, rebuild, observe, store, __init__} imports the v2 store."""
    importers = {
        py.relative_to(_SRC).as_posix()
        for py in _AUTOM8.rglob("*.py")
        if _imports_substrate_store(ast.parse(py.read_text()))
    }
    unexpected = importers - _ALLOWED_STORE_IMPORTERS
    assert not unexpected, (
        f"module(s) import the v2 store outside the seam allowlist: {sorted(unexpected)}. "
        "A consumer must go through substrate.serve.SubstrateReader ([H17])."
    )


def test_serve_adapters_do_not_import_the_store() -> None:
    """The consumer-facing adapter module reaches numbers ONLY through the reader gate."""
    adapters = _SUBSTRATE / "serve_adapters.py"
    assert not _imports_substrate_store(ast.parse(adapters.read_text())), (
        "serve_adapters.py must NOT import substrate.store — the adapters hold a SubstrateReader "
        "([H17])."
    )


# ---------------------------------------- reachability tooth (F-2 strengthening) ---


def test_read_current_reachable_only_from_the_seam() -> None:
    """TREE-WIDE: any ``.read_current`` call site must be inside {serve, rebuild, observe, store}.

    Reachability, not import-name: this catches an injected-store consumer (imports only the
    root ``ArtifactStore`` Protocol, calls ``.read_current`` on the injected instance) — the
    exact QA F-2 bypass — regardless of how the store reference was obtained.
    """
    callers = _modules_accessing_attr("read_current")
    unexpected = callers - _ALLOWED_READ_CURRENT_CALLERS
    assert not unexpected, (
        f"module(s) reach the raw byte reader (.read_current) outside the seam: {sorted(unexpected)}. "
        "A consumer must call SubstrateReader.read, never store.read_current ([H17]/C2)."
    )


def test_the_reachability_tooth_bites_the_injected_store_bypass() -> None:
    """PLANTED OFFENDER (QA F-2 vector a): must be DETECTED; the compliant control must not.

    The offender imports ONLY the package-root Protocol (no ``substrate.store`` import — so the
    import-name tooth is BLIND) and calls ``.read_current`` on an INJECTED store. The
    reachability scan flags it. Since a would-be offender module lives OUTSIDE the caller
    allowlist, ``test_read_current_reachable_only_from_the_seam`` above WOULD go RED on it.
    """
    offender = (
        "from autom8_asana.substrate import ArtifactStore\n"
        "class SneakyAdapter:\n"
        "    def __init__(self, store: ArtifactStore) -> None:\n"
        "        self._store = store\n"
        "    async def read(self, aid):\n"
        "        raw, proof = await self._store.read_current(aid)  # BYPASS the gate\n"
        "        return raw\n"
    )
    compliant = (
        "class GoodAdapter:\n"
        "    def __init__(self, reader) -> None:\n"
        "        self._reader = reader\n"
        "    async def read(self, aid):\n"
        "        return await self._reader.read(aid)  # through the gate\n"
    )
    # The old import-name tooth is BLIND to the bypass (it imports the root Protocol only)...
    assert not _imports_substrate_store(ast.parse(offender))
    # ...but the reachability tooth BITES it, and stays SILENT on the compliant control.
    assert _source_accesses_attr(offender, "read_current"), (
        "reachability tooth failed to bite the bypass"
    )
    assert not _source_accesses_attr(compliant, "read_current"), (
        "reachability tooth false-positived"
    )


def test_substrate_package_never_reaches_v1_load_dataframe() -> None:
    """No substrate (v2) module reaches around into v1's raw ``load_dataframe`` reader.

    Scoped to substrate/ — v1's own ``load_dataframe`` callers (api/preload, dataframes/…)
    are legitimate and out of scope (they delete at S11). The store.py / serve_adapters.py
    string mentions of ``load_dataframe`` are DOCSTRING prose (Str nodes), not accesses/imports,
    so the AST scan correctly ignores them.
    """
    accessors = {
        py.relative_to(_SRC).as_posix()
        for py in _SUBSTRATE.rglob("*.py")
        if _source_accesses_attr(py.read_text(), "load_dataframe")
    }
    importers = _modules_importing_name(_SUBSTRATE, "load_dataframe")
    assert not accessors, (
        f"substrate module(s) call .load_dataframe (v1 raw reader): {sorted(accessors)}"
    )
    assert not importers, f"substrate module(s) import load_dataframe: {sorted(importers)}"
