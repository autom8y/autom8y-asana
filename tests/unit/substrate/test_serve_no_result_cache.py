"""[H16]/C2 structural tooth — NO result-cache above the freshness gate.

C2 FREEZE: "caching of ServedNumber/Provable results above the gate is FORBIDDEN —
only proof-validated bytes may be tiered." AV-2 was the "result-cache re-creates
false-fresh from memory" finding; this tooth makes the memoization surface
structurally absent, not merely absent-by-vigilance. The complementary BEHAVIORAL
proof (is_provable re-runs every read) lives in
``test_serve.test_gate_reruns_is_provable_every_read_no_result_cache`` and the
adapter-level no-cache proof in
``test_serve_adapters.test_adapters_do_not_cache_a_double_call`` (QA F-3).

DEFENCE-IN-DEPTH (three complementary teeth; QA F-3 known-limitation): (1) the
decorator-name scan catches ``@lru_cache``/``@cache`` by local name; an ALIASED
functools memoizer (``from functools import lru_cache as _x``) evades that scan by
local name but is caught by (2) the functools-import scan, which keys on
``alias.name`` (the ORIGINAL name, not the ``as`` binding). A fully hand-rolled
memoizer (no functools) evades both name scans but needs somewhere to STORE results —
caught by (3) the reader-attribute allowlist (a result-cache attribute is forbidden)
plus the behavioral double-call tests. A fully-dynamic obfuscated cache is out of
scope (targets DRIFT, not sabotage).
"""

from __future__ import annotations

import ast
from pathlib import Path

from autom8_asana.substrate.freshness import is_provable
from autom8_asana.substrate.serve import GatedSubstrateReader

_SUBSTRATE = Path(__file__).resolve().parents[3] / "src" / "autom8_asana" / "substrate"
_SERVE = _SUBSTRATE / "serve.py"
_ADAPTERS = _SUBSTRATE / "serve_adapters.py"

# functools memoization decorators — a Provable/ServedNumber-returning read decorated
# with any of these would cache a verdict above the gate (the forbidden surface).
_CACHING_DECORATORS = {"lru_cache", "cache", "cached_property", "cached", "memoize"}

# The GatedSubstrateReader holds ONLY injected collaborators + config — no result store.
_ALLOWED_READER_ATTRS = {
    "_store",
    "_is_provable",
    "_digest_of_frame",
    "_emitter",
    "_now",
    "_future_skew_tolerance_seconds",
}


class _UnusedStore:
    """A stand-in store — the reader ctor only stashes the ref; read is never called here."""

    async def read_current(self, aid: object) -> tuple[bytes, object]:
        raise NotImplementedError


def _decorator_ids(tree: ast.AST) -> list[str]:
    ids: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                if isinstance(target, ast.Name):
                    ids.append(target.id)
                elif isinstance(target, ast.Attribute):
                    ids.append(target.attr)
    return ids


def test_no_caching_decorator_on_any_serve_function() -> None:
    """No read/serve function is memoized with a caching decorator (the C2-forbidden surface)."""
    for path in (_SERVE, _ADAPTERS):
        tree = ast.parse(path.read_text())
        offenders = [d for d in _decorator_ids(tree) if d in _CACHING_DECORATORS]
        assert not offenders, (
            f"{path.name} decorates a serve fn with {offenders} (C2 forbids a result-cache)"
        )


def test_serve_module_does_not_import_a_memoizer() -> None:
    """The forbidden ``functools.lru_cache``/``cache`` are not even imported into serve.py."""
    tree = ast.parse(_SERVE.read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "functools":
            imported.update(alias.name for alias in node.names)
    assert imported.isdisjoint(_CACHING_DECORATORS), (
        f"serve.py imports a memoizer {imported & _CACHING_DECORATORS} — no result-cache above the gate (C2)"
    )


def test_reader_holds_no_result_cache_attribute() -> None:
    """The reader instance carries only collaborators/config — no ServedNumber store surface."""
    reader = GatedSubstrateReader(
        store=_UnusedStore(),  # type: ignore[arg-type]
        is_provable=is_provable,
        digest_of_frame=lambda _: "d",
    )
    attrs = set(vars(reader))
    assert attrs == _ALLOWED_READER_ATTRS, (
        f"unexpected reader attribute(s): {attrs - _ALLOWED_READER_ATTRS}"
    )
    assert not any(
        token in name for name in attrs for token in ("cache", "memo", "result", "served")
    ), "a cache-like attribute name would be a result-cache surface (C2)"
