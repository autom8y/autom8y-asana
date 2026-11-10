"""Import-linter layer contracts for the D6 trigger package (A C-12).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 section 2. The contracts live
in ``pyproject.toml``: live ones under ``[tool.importlinter]``, and ones whose source
modules have not landed yet under ``[tool.importlinter-pending]``. Import-linter treats a
missing source module as a configuration error, so a contract cannot be live before its
module exists.

What these tests hold:

* The live contracts are KEPT against the real ``autom8_asana`` package.
* Teeth: for every contract, live or pending, a synthetic package that plants each
  forbidden import in each source module is reported BROKEN, with exactly the planted
  pairs. Its clean twin, which also keeps the allowed paths (the store exception, the
  ports adapter, and an indirect path to the full client), is reported KEPT. The synthetic
  contract is the pyproject entry with only the root package renamed, so the teeth test
  the real definitions.
* No vacuous pass. A source expression may not be a wildcard (a wildcard that matches
  nothing is silently empty in import-linter 2.16). Every live source must exist. A pending
  contract fails the suite as soon as a module matching its landing patterns appears, until
  the contract is moved into ``[tool.importlinter]``. A live contract fails if a matching
  module is not covered by its sources. An absent external forbidden package must be one of
  the declared known-absent names, so a misspelled name cannot sit unbound.
* If import-linter is not installed these tests FAIL; they never skip.

Every import-linter run is a subprocess on the current interpreter with an explicit
``PYTHONPATH``, so the graph is built from this checkout's ``src/`` and no conftest fixture
is needed.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import tomllib
from functools import cache
from pathlib import Path
from typing import Any

import pytest

try:
    import grimp  # noqa: F401
    import importlinter  # noqa: F401

    _IMPORT_LINTER_ERROR: str | None = None
except ImportError as exc:  # pragma: no cover - exercised by the missing-dependency run
    _IMPORT_LINTER_ERROR = f"{type(exc).__name__}: {exc}"

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
PYPROJECT = REPO_ROOT / "pyproject.toml"
ROOT = "autom8_asana"
SYNTHETIC_ROOT = "plantpkg"

EXPECTED_CONTRACTS = frozenset(
    {
        "trigger-decide-readonly",
        "trigger-registration-webhooks-only",
        "trigger-aws-only-in-stores",
    }
)

# Module-name patterns (fnmatch) that mean a contract's source modules have landed. While the
# contract is pending, any match fails the suite. Once live, every match must be covered.
LANDING_PATTERNS: dict[str, tuple[str, ...]] = {
    "trigger-decide-readonly": (
        "autom8_asana.trigger.decision*",
        "autom8_asana.trigger.tag_registry*",
        "autom8_asana.trigger.sweeper*",
        "autom8_asana.trigger.resolver_adapter*",
        "autom8_asana.api.routes.asana_hook*",
    ),
    "trigger-registration-webhooks-only": ("autom8_asana.trigger.registration*",),
    "trigger-aws-only-in-stores": ("autom8_asana.trigger*",),
}

# External forbidden packages that nothing in src imports today. Import-linter skips a
# forbidden external that is not in the graph, which is correct (it binds once imported),
# but it would also silently accept a misspelled name. Any absent name must be listed here.
KNOWN_ABSENT_EXTERNALS = frozenset(
    {
        "aiobotocore",
        "sqlalchemy",
        "asyncpg",
        "psycopg",
        "psycopg2",
        "pymysql",
        "aiomysql",
        "twilio",
        "facebook_business",
    }
)

_PENDING_ONLY_KEYS = frozenset({"lands_with"})
_BROKEN_PAIR = re.compile(r"^(\S+) is not allowed to import (\S+):$", re.MULTILINE)


def _require_import_linter() -> None:
    if _IMPORT_LINTER_ERROR is not None:
        pytest.fail(
            "import-linter is a required dev dependency for the trigger layer contracts "
            f"(A C-12) and could not be imported: {_IMPORT_LINTER_ERROR}",
            pytrace=False,
        )


@cache
def _pyproject() -> dict[str, Any]:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def _live_contracts() -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = _pyproject()["tool"]["importlinter"]["contracts"]
    return contracts


def _pending_contracts() -> list[dict[str, Any]]:
    pending = _pyproject()["tool"].get("importlinter-pending", {})
    contracts: list[dict[str, Any]] = pending.get("contracts", [])
    return contracts


def _all_contracts() -> list[dict[str, Any]]:
    return _live_contracts() + _pending_contracts()


def _env_with_path(path: Path) -> dict[str, str]:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(path) if not existing else f"{path}{os.pathsep}{existing}"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    env["COLUMNS"] = "200"
    return env


def _run_lint_imports(config: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the lint-imports CLI on the current interpreter, with caching off."""
    return subprocess.run(  # noqa: S603 - fixed argv on sys.executable, no shell
        [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports_command; lint_imports_command()",
            "--config",
            str(config),
            "--no-cache",
        ],
        cwd=cwd,
        env=_env_with_path(cwd),
        capture_output=True,
        text=True,
        timeout=50,
        check=False,
    )


_GRAPH_PROBE = """
import importlib.util, json, sys
import grimp
spec = importlib.util.find_spec(sys.argv[1])
graph = grimp.build_graph(sys.argv[1], include_external_packages=True, cache_dir=None)
internal = sorted(m for m in graph.modules if m == sys.argv[1] or m.startswith(sys.argv[1] + "."))
external = sorted(m for m in graph.modules if m not in set(internal))
print(json.dumps({"origin": spec.origin, "internal": internal, "external": external}))
"""


@cache
def _real_graph() -> dict[str, Any]:
    """Module names of this checkout's autom8_asana, and the external roots it imports."""
    proc = subprocess.run(  # noqa: S603 - fixed argv on sys.executable, no shell
        [sys.executable, "-c", _GRAPH_PROBE, ROOT],
        cwd=SRC_DIR,
        env=_env_with_path(SRC_DIR),
        capture_output=True,
        text=True,
        timeout=50,
        check=False,
    )
    assert proc.returncode == 0, f"graph probe failed:\n{proc.stderr}"
    data: dict[str, Any] = json.loads(proc.stdout)
    origin = Path(data["origin"]).resolve()
    assert origin.is_relative_to(SRC_DIR.resolve()), (
        f"graph built from {origin}, not from this checkout's src/ ({SRC_DIR})"
    )
    return data


def _covered_by(module: str, sources: list[str]) -> bool:
    return any(module == s or module.startswith(s + ".") for s in sources)


# ---------------------------------------------------------------------------
# Configuration shape
# ---------------------------------------------------------------------------


def test_import_linter_is_installed() -> None:
    _require_import_linter()


def test_contract_set_matches_design() -> None:
    _require_import_linter()
    live = [c["name"] for c in _live_contracts()]
    pending = [c["name"] for c in _pending_contracts()]
    assert len(live) == len(set(live)), f"duplicate live contract: {live}"
    assert not set(live) & set(pending), (
        f"contract both live and pending: {set(live) & set(pending)}"
    )
    assert set(live) | set(pending) == EXPECTED_CONTRACTS
    assert set(LANDING_PATTERNS) == EXPECTED_CONTRACTS
    session = _pyproject()["tool"]["importlinter"]
    assert session["root_package"] == ROOT
    assert session["include_external_packages"] is True
    for contract in _all_contracts():
        assert contract["type"] == "forbidden", contract["name"]
        assert contract["allow_indirect_imports"] is True, contract["name"]
    for contract in _live_contracts():
        assert not _PENDING_ONLY_KEYS & contract.keys(), (
            f"{contract['name']}: drop {sorted(_PENDING_ONLY_KEYS)} when moving a contract live"
        )


def test_no_wildcard_source_expressions() -> None:
    """A wildcard source that matches nothing resolves to no modules, a vacuous pass."""
    _require_import_linter()
    for contract in _all_contracts():
        wild = [s for s in contract["source_modules"] if "*" in s]
        assert not wild, f"{contract['name']}: wildcard source expressions are not allowed: {wild}"


# ---------------------------------------------------------------------------
# The real package
# ---------------------------------------------------------------------------


def test_live_contracts_kept_on_real_package() -> None:
    _require_import_linter()
    proc = _run_lint_imports(PYPROJECT, SRC_DIR)
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, f"lint-imports failed (rc={proc.returncode}):\n{output}"
    for contract in _live_contracts():
        assert re.search(rf"^{re.escape(contract['name'])} KEPT\b", output, re.MULTILINE), (
            f"{contract['name']} was not reported KEPT:\n{output}"
        )
    assert f"Contracts: {len(_live_contracts())} kept, 0 broken." in output, output


def test_live_sources_exist() -> None:
    _require_import_linter()
    internal = set(_real_graph()["internal"])
    for contract in _live_contracts():
        for source in contract["source_modules"]:
            assert source in internal, f"{contract['name']}: source {source} matches no module"


def test_live_contracts_cover_every_landed_module() -> None:
    _require_import_linter()
    internal = _real_graph()["internal"]
    for contract in _live_contracts():
        patterns = LANDING_PATTERNS[contract["name"]]
        landed = [m for m in internal if any(fnmatch.fnmatchcase(m, p) for p in patterns)]
        uncovered = [m for m in landed if not _covered_by(m, contract["source_modules"])]
        assert not uncovered, (
            f"{contract['name']}: modules {uncovered} match its landing patterns but are not "
            "in source_modules; add them"
        )


def test_pending_contracts_have_not_landed() -> None:
    """Fails once a pending contract's module exists, until the contract is moved live."""
    _require_import_linter()
    internal = _real_graph()["internal"]
    for contract in _pending_contracts():
        patterns = LANDING_PATTERNS[contract["name"]]
        landed = [m for m in internal if any(fnmatch.fnmatchcase(m, p) for p in patterns)]
        assert not landed, (
            f"{contract['name']} is pending, but {landed} landed. Move the contract from "
            "[tool.importlinter-pending] into [tool.importlinter] (drop lands_with) and list "
            "every landed module in its source_modules."
        )


def test_forbidden_modules_resolve() -> None:
    """Internal forbidden modules exist; absent externals are only the declared ones."""
    _require_import_linter()
    graph = _real_graph()
    internal, external = set(graph["internal"]), set(graph["external"])
    for contract in _all_contracts():
        for forbidden in contract["forbidden_modules"]:
            if forbidden == ROOT or forbidden.startswith(ROOT + "."):
                assert forbidden in internal, f"{contract['name']}: {forbidden} does not exist"
            else:
                assert "." not in forbidden, (
                    f"{contract['name']}: {forbidden} is not a root package"
                )
                assert forbidden in external or forbidden in KNOWN_ABSENT_EXTERNALS, (
                    f"{contract['name']}: external {forbidden} is neither imported by src nor "
                    "declared in KNOWN_ABSENT_EXTERNALS (misspelled?)"
                )


# ---------------------------------------------------------------------------
# Teeth: planted imports in a synthetic package
# ---------------------------------------------------------------------------


def _rename(name: str) -> str:
    if name == ROOT or name.startswith(ROOT + "."):
        return SYNTHETIC_ROOT + name[len(ROOT) :]
    return name


def _is_internal(name: str) -> bool:
    return name == SYNTHETIC_ROOT or name.startswith(SYNTHETIC_ROOT + ".")


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    raise TypeError(f"unsupported config value: {value!r}")


def _synthetic_contract(contract: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in contract.items():
        if key in _PENDING_ONLY_KEYS:
            continue
        if key in ("source_modules", "forbidden_modules"):
            out[key] = [_rename(v) for v in value]
        elif key == "ignore_imports":
            out[key] = [" -> ".join(_rename(p.strip()) for p in v.split("->")) for v in value]
        else:
            out[key] = value
    return out


def _write_module(root: Path, dotted: str, body: str = "") -> None:
    parts = dotted.split(".")
    for i in range(1, len(parts)):
        init = root.joinpath(*parts[:i], "__init__.py")
        init.parent.mkdir(parents=True, exist_ok=True)
        init.touch()
    path = root.joinpath(*parts[:-1], parts[-1] + ".py")
    package_init = root.joinpath(*parts, "__init__.py")
    target = package_init if package_init.exists() else path
    existing = target.read_text() if target.exists() else ""
    target.write_text(existing + body)


def _source_site(source: str) -> str:
    """The module that receives planted imports: the module itself, or a child of a package."""
    real = source.replace(SYNTHETIC_ROOT, ROOT, 1).split(".")
    if SRC_DIR.joinpath(*real, "__init__.py").exists():
        return source + ".planted_site"
    return source


def _build_synthetic(tmp_path: Path, contract: dict[str, Any], *, planted: bool) -> Path:
    """Write plantpkg plus a one-contract config; return the config path."""
    syn = _synthetic_contract(contract)
    internal_forbidden = [f for f in syn["forbidden_modules"] if _is_internal(f)]
    for forbidden in internal_forbidden:
        _write_module(tmp_path, forbidden, '"""Forbidden stand-in."""\n')
    # The ports adapter imports the full client: an indirect path that must stay allowed.
    ports = f"{SYNTHETIC_ROOT}.trigger.ports"
    _write_module(tmp_path, ports, "".join(f"import {f}\n" for f in internal_forbidden))
    # Ignored imports (the store exception) are present in both twins.
    for line in syn.get("ignore_imports", []):
        importer, imported = (p.strip() for p in line.split("->"))
        _write_module(tmp_path, importer, f"import {imported}\n")
    for source in syn["source_modules"]:
        _write_module(tmp_path, source, '"""Source module."""\n')
        site = _source_site(source)
        body = f"import {ports}\n"
        if planted:
            body += "".join(f"import {f}\n" for f in syn["forbidden_modules"])
        _write_module(tmp_path, site, body)

    lines = [
        "[tool.importlinter]",
        f"root_package = {_toml_value(SYNTHETIC_ROOT)}",
        "include_external_packages = true",
        "",
        "[[tool.importlinter.contracts]]",
    ]
    lines += [f"{key} = {_toml_value(value)}" for key, value in syn.items()]
    config = tmp_path / "synthetic.toml"
    config.write_text("\n".join(lines) + "\n")
    return config


def _expected_pairs(contract: dict[str, Any]) -> set[tuple[str, str]]:
    """Import-linter reports each broken pair by source expression and forbidden module."""
    syn = _synthetic_contract(contract)
    return {(s, f) for s in syn["source_modules"] for f in syn["forbidden_modules"]}


_CONTRACT_IDS = [c["name"] for c in _all_contracts()]


@pytest.mark.parametrize("name", _CONTRACT_IDS)
def test_planted_forbidden_import_is_broken(name: str, tmp_path: Path) -> None:
    _require_import_linter()
    contract = next(c for c in _all_contracts() if c["name"] == name)
    config = _build_synthetic(tmp_path, contract, planted=True)
    proc = _run_lint_imports(config, tmp_path)
    output = proc.stdout + proc.stderr
    assert proc.returncode == 1, f"expected BROKEN (rc=1), got rc={proc.returncode}:\n{output}"
    assert re.search(rf"^{re.escape(name)} BROKEN\b", output, re.MULTILINE), output
    reported = set(_BROKEN_PAIR.findall(output))
    assert reported == _expected_pairs(contract), (
        f"missing: {sorted(_expected_pairs(contract) - reported)}\n"
        f"unexpected: {sorted(reported - _expected_pairs(contract))}"
    )


@pytest.mark.parametrize("name", _CONTRACT_IDS)
def test_clean_twin_is_kept(name: str, tmp_path: Path) -> None:
    _require_import_linter()
    contract = next(c for c in _all_contracts() if c["name"] == name)
    config = _build_synthetic(tmp_path, contract, planted=False)
    proc = _run_lint_imports(config, tmp_path)
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, f"expected KEPT (rc=0), got rc={proc.returncode}:\n{output}"
    assert re.search(rf"^{re.escape(name)} KEPT\b", output, re.MULTILINE), output
