"""D6 test adapters stay in tests/: fixtures PM-2 and PM-4 (TDD r4.6 sections 2a, 9; A C-11).

PM-2: the in-memory registry and key-store adapters (``tests/unit/trigger/adapters.py``)
are absent from the built wheel and the image, and not importable from the image's
``sys.path``; a twin shows them present in the test tree.

* Wheel: hatch builds the wheel from ``[tool.hatch.build.targets.wheel]``. The adapter file
  must sit under none of its ``packages`` / ``only-include`` / ``force-include`` sources.
* Image: the runtime image gets only what the Dockerfile COPYs from the build context.
  No COPY source may cover the adapter file.
* ``sys.path``: with only ``src/`` on the path (the image's layout), the adapter module
  does not resolve.

PM-4 (auth A2 condition, teeth per auth A2-3): no adapter registry, entry point, default
instance or ``dependency_overrides`` in ``src/``.

* The AST half scans EVERY module under ``src/``, recursively (warden-bench F-3 on #541:
  ``api/lifespan.py`` and ``api/startup.py`` are where wiring would go; auth-bench A3-3:
  all of ``src/``). It flags an import from ``tests``, ``dependency_overrides``, a name or
  string naming an adapter, a CLASS DEFINITION named like an adapter (auth-bench A3-3),
  and module-level default instances and registries of the D6 classes. The one sanctioned
  ``tests`` import is the substrate-v2 operator tool's use of
  ``tests.harness.substrate_gate`` (``substrate/live.py``, ``substrate/parity_run.py``);
  it is pinned by file, and no other ``tests`` import passes.
* The entry-point half reads package metadata (``[project.scripts]``,
  ``[project.gui-scripts]``, ``[project.entry-points.*]``), which is what hatch writes into
  the wheel's ``entry_points.txt``. It also asserts the metadata declares no DYNAMIC entry
  points or scripts (``[project] dynamic``) and that no build hook is configured that
  could add one (``[tool.hatch.build.hooks]``, per-target ``hooks``,
  ``[tool.hatch.metadata.hooks]``, a ``hatch_build.py``), and that the build backend is
  plain hatchling with no hook plugin (auth-bench A3-3).

Each check has a planted violation that it must flag.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
PACKAGE = SRC / "autom8_asana"
ADAPTER_FILE = PurePosixPath("tests/unit/trigger/adapters.py")
ADAPTER_MODULE = "tests.unit.trigger.adapters"
ADAPTER_NAMES = frozenset({"InMemoryHookRegistry", "InMemoryKeyHookStore", "adapters"})
CONSTRUCTED_NAMES = frozenset(
    {
        "HookStore",
        "HookRegistry",
        "Registrar",
        "Reconciler",
        "WebhooksClient",
        "build_shadow_registration",
        "ShadowReceiver",
        "Sweeper",
        "build_shadow_receiver",
        "InMemoryHookRegistry",
        "InMemoryKeyHookStore",
    }
)
# Modules PM-4 must reach (positive controls for the recursive scan; warden F-3).
REQUIRED_SCANNED = (
    "autom8_asana/__init__.py",
    "autom8_asana/entrypoint.py",
    "autom8_asana/api/main.py",
    "autom8_asana/api/dependencies.py",
    "autom8_asana/api/lifespan.py",
    "autom8_asana/api/startup.py",
    "autom8_asana/trigger/registration.py",
    "autom8_asana/trigger/receiver.py",
    "autom8_asana/api/routes/asana_hook.py",
)
# The one sanctioned src -> tests import (the substrate-v2 operator tool; see the mypy
# override in pyproject.toml). Pinned by file; the module must sit under this prefix.
SANCTIONED_TESTS_IMPORTS: dict[str, str] = {
    "autom8_asana/substrate/live.py": "tests.harness.substrate_gate",
    "autom8_asana/substrate/parity_run.py": "tests.harness.substrate_gate",
}


# ---------------------------------------------------------------------------
# PM-2: wheel
# ---------------------------------------------------------------------------


def _covers(source: str, target: PurePosixPath) -> bool:
    src = PurePosixPath(source.strip().rstrip("/") or ".")
    return str(src) in (".", "") or target == src or src in target.parents


def wheel_violations(pyproject: dict[str, Any]) -> list[str]:
    wheel = (
        pyproject.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
    )
    sources: list[str] = list(wheel.get("packages", [])) + list(wheel.get("only-include", []))
    sources += list(wheel.get("include", []))
    sources += list(wheel.get("force-include", {}).keys())
    if not sources:
        return ["no explicit wheel sources: hatch would fall back to discovery"]
    return [s for s in sources if _covers(s, ADAPTER_FILE) or s.strip("/").startswith("tests")]


def _pyproject() -> dict[str, Any]:
    with (REPO / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def test_adapters_are_absent_from_the_wheel_sources() -> None:
    """PM-2 (D6 TDD fixture or review id)."""
    config = _pyproject()
    packages = config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert "src/autom8_asana" in packages, "positive control: the real package is packaged"
    assert wheel_violations(config) == []


@pytest.mark.parametrize(
    "wheel",
    [
        {"packages": ["src/autom8_asana", "tests"]},
        {"packages": ["src/autom8_asana"], "force-include": {"tests/unit/trigger": "x"}},
        {"packages": ["src/autom8_asana"], "only-include": ["tests/unit/trigger/adapters.py"]},
        {"packages": ["."]},
        {},
    ],
    ids=["packages-tests", "force-include", "only-include", "whole-tree", "discovery"],
)
def test_planted_wheel_source_covering_the_adapters_is_flagged(wheel: dict[str, Any]) -> None:
    """PM-2 teeth (D6 TDD fixture or review id)."""
    planted = {"tool": {"hatch": {"build": {"targets": {"wheel": wheel}}}}}
    assert wheel_violations(planted), wheel


# ---------------------------------------------------------------------------
# PM-2: image
# ---------------------------------------------------------------------------

_COPY = re.compile(r"^\s*COPY\s+(.*)$", re.IGNORECASE)


def image_violations(dockerfile: str) -> list[str]:
    found: list[str] = []
    for line in dockerfile.splitlines():
        match = _COPY.match(line)
        if not match:
            continue
        parts = [p for p in match.group(1).split() if p]
        if any(p.startswith("--from=") for p in parts):
            continue  # a stage or image copy, not the build context
        args = [p for p in parts if not p.startswith("--")]
        for source in args[:-1]:
            if _covers(source, ADAPTER_FILE) or source.strip("./").startswith("tests"):
                found.append(line.strip())
    return found


def test_adapters_are_absent_from_the_image() -> None:
    """PM-2 (D6 TDD fixture or review id)."""
    dockerfile = (REPO / "Dockerfile").read_text()
    assert "COPY --link src ./src" in dockerfile, "positive control: the image copies src"
    assert image_violations(dockerfile) == []


@pytest.mark.parametrize(
    "line",
    [
        "COPY . .",
        "COPY --link tests ./tests",
        "COPY tests/unit/trigger/adapters.py /app/",
        "COPY ./ /app",
    ],
)
def test_planted_image_copy_covering_the_adapters_is_flagged(line: str) -> None:
    """PM-2 teeth (D6 TDD fixture or review id)."""
    assert image_violations(f"FROM base\n{line}\n") == [line]


# ---------------------------------------------------------------------------
# PM-2: importable only from the test tree
# ---------------------------------------------------------------------------

_PROBE = (
    "import importlib.util, sys\n"
    "try:\n"
    "    spec = importlib.util.find_spec(sys.argv[1])\n"
    "except ModuleNotFoundError:\n"
    "    spec = None\n"
    "print('FOUND' if spec is not None else 'ABSENT')\n"
)


def _probe(pythonpath: Path, cwd: Path) -> str:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = str(pythonpath)
    proc = subprocess.run(  # noqa: S603 - fixed argv on sys.executable, no shell
        [sys.executable, "-P", "-c", _PROBE, ADAPTER_MODULE],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=50,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def test_adapters_are_not_importable_from_the_image_path(tmp_path: Path) -> None:
    """PM-2 (D6 TDD fixture or review id)."""
    assert _probe(SRC, tmp_path) == "ABSENT"


def test_adapters_are_importable_from_the_test_tree(tmp_path: Path) -> None:
    """PM-2 twin (D6 TDD fixture or review id)."""
    assert (REPO / ADAPTER_FILE).is_file()
    assert _probe(REPO, tmp_path) == "FOUND"


# ---------------------------------------------------------------------------
# PM-4: no adapter registry, default instance or dependency_overrides in src
# ---------------------------------------------------------------------------


def _called_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        func = node.func
        return func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
    return None


def _tests_import_sanctioned(filename: str, module: str) -> bool:
    prefix = SANCTIONED_TESTS_IMPORTS.get(filename)
    return prefix is not None and (module == prefix or module.startswith(prefix + "."))


def src_violations(source: str, filename: str = "<planted>") -> list[str]:
    tree = ast.parse(source, filename=filename)
    found: list[str] = []
    for node in ast.walk(tree):
        line = f"{filename}:{getattr(node, 'lineno', 0)}"
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tests":
            if not _tests_import_sanctioned(filename, node.module or ""):
                found.append(f"{line} imports from tests")
        elif isinstance(node, ast.Import) and any(
            a.name.split(".")[0] == "tests" and not _tests_import_sanctioned(filename, a.name)
            for a in node.names
        ):
            found.append(f"{line} imports tests")
        elif isinstance(node, ast.ClassDef) and node.name in ADAPTER_NAMES - {"adapters"}:
            found.append(f"{line} defines adapter class {node.name}")
        elif isinstance(node, ast.Attribute) and node.attr == "dependency_overrides":
            found.append(f"{line} dependency_overrides")
        elif isinstance(node, ast.Name) and node.id in ADAPTER_NAMES - {"adapters"}:
            found.append(f"{line} names adapter {node.id}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if ADAPTER_MODULE in node.value or any(
                n in node.value for n in ADAPTER_NAMES - {"adapters"}
            ):
                found.append(f"{line} string names an adapter")
    # Default instances and registries: module-level statements only.
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
            value = stmt.value
            if _called_name(value) in CONSTRUCTED_NAMES:
                found.append(f"{filename}:{stmt.lineno} default instance")
            if isinstance(value, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
                refs = {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}
                if refs & CONSTRUCTED_NAMES:
                    found.append(f"{filename}:{stmt.lineno} adapter registry")
    return found


def _scanned_modules() -> list[Path]:
    modules = sorted(SRC.rglob("*.py"))
    scanned = {path.relative_to(SRC).as_posix() for path in modules}
    missing = [name for name in REQUIRED_SCANNED if name not in scanned]
    assert missing == [], f"positive control: the recursive scan misses {missing}"
    return modules


def test_src_has_no_adapter_wiring() -> None:
    """PM-4, warden-bench F-3, auth-bench A3-3 (D6 TDD fixture or review id)."""
    found: list[str] = []
    for path in _scanned_modules():
        found += src_violations(path.read_text(), path.relative_to(SRC).as_posix())
    assert found == [], "\n".join(found)


def test_sanctioned_tests_imports_are_real_and_narrow() -> None:
    """PM-4: Each pinned src -> tests import exists, and the same import elsewhere is flagged."""
    for filename, prefix in SANCTIONED_TESTS_IMPORTS.items():
        assert prefix in (SRC / filename).read_text(), f"stale sanction: {filename}"
        planted = f"from {prefix}.parity import x\n"
        assert src_violations(planted, filename) == []
        assert src_violations(planted, "autom8_asana/api/lifespan.py"), filename
    assert src_violations("from tests.unit.trigger import adapters\n", filename)


PLANTED_SRC = {
    "import-adapter": "from tests.unit.trigger.adapters import InMemoryKeyHookStore\n",
    "dependency-overrides": "app.dependency_overrides[get_store] = lambda: store\n",
    "default-store": "from x import HookStore\n_default = HookStore()\n",
    "default-reconciler": "RECONCILER = build_shadow_registration(environ={})\n",
    "adapter-registry": "ADAPTERS = {'test': InMemoryHookRegistry, 'production': HookRegistry}\n",
    "string-registry": "PLUGINS = {'test': 'tests.unit.trigger.adapters:InMemoryKeyHookStore'}\n",
    # auth-bench A3-3: a class named like an adapter, defined in src.
    "class-definition": "class InMemoryHookRegistry:\n    pass\n",
    "class-definition-nested": "def f():\n    class InMemoryKeyHookStore:\n        pass\n",
    "default-receiver": "RECEIVER = build_shadow_receiver(environ={})\n",
    "default-sweeper": "from x import Sweeper\nSWEEPER = Sweeper()\n",
}


@pytest.mark.parametrize("name", sorted(PLANTED_SRC))
def test_planted_src_violation_is_flagged(name: str) -> None:
    """PM-4 teeth, auth-bench A3-3 (D6 TDD fixture or review id)."""
    assert src_violations(PLANTED_SRC[name]), name


def test_clean_construction_source_passes_the_wiring_scan() -> None:
    """PM-4 twin (D6 TDD fixture or review id)."""
    clean = "from x import HookStore\n\ndef build() -> HookStore:\n    return HookStore()\n"
    assert src_violations(clean) == []


def entry_point_violations(pyproject: dict[str, Any]) -> list[str]:
    project = pyproject.get("project", {})
    groups: dict[str, dict[str, str]] = {
        "scripts": project.get("scripts", {}),
        "gui-scripts": project.get("gui-scripts", {}),
        **{f"entry-points.{k}": v for k, v in project.get("entry-points", {}).items()},
    }
    found: list[str] = []
    for group, entries in groups.items():
        for name, target in entries.items():
            if (
                target.split(".")[0].split(":")[0] == "tests"
                or "autom8_asana.trigger" in target
                or any(n in target for n in ADAPTER_NAMES - {"adapters"})
            ):
                found.append(f"{group}: {name} = {target}")
    return found


def test_package_metadata_has_no_adapter_entry_point() -> None:
    """PM-4 (D6 TDD fixture or review id)."""
    config = _pyproject()
    assert config["project"]["scripts"], "positive control: the metadata has entry points"
    assert entry_point_violations(config) == []


_ENTRY_POINT_FIELDS = frozenset({"scripts", "gui-scripts", "entry-points"})


def dynamic_entry_point_violations(pyproject: dict[str, Any], repo: Path) -> list[str]:
    """auth-bench A3-3: nothing can add an entry point at build time."""
    found: list[str] = []
    dynamic = set(pyproject.get("project", {}).get("dynamic", []) or [])
    if dynamic & _ENTRY_POINT_FIELDS:
        found.append(f"[project] dynamic declares {sorted(dynamic & _ENTRY_POINT_FIELDS)}")
    hatch = pyproject.get("tool", {}).get("hatch", {})
    if hatch.get("build", {}).get("hooks"):
        found.append("[tool.hatch.build.hooks] is configured")
    for target, cfg in hatch.get("build", {}).get("targets", {}).items():
        if isinstance(cfg, dict) and cfg.get("hooks"):
            found.append(f"[tool.hatch.build.targets.{target}.hooks] is configured")
    if hatch.get("metadata", {}).get("hooks"):
        found.append("[tool.hatch.metadata.hooks] is configured")
    build = pyproject.get("build-system", {})
    if build.get("build-backend") != "hatchling.build":
        found.append(f"build backend is {build.get('build-backend')!r}, not hatchling.build")
    extra = [r for r in build.get("requires", []) if not str(r).startswith("hatchling")]
    if extra:
        found.append(f"build-system requires more than hatchling: {extra}")
    if (repo / "hatch_build.py").exists():
        found.append("hatch_build.py exists (hatch's default custom build hook)")
    return found


def test_no_dynamic_entry_points_or_build_hooks() -> None:
    """PM-4, auth-bench A3-3 (D6 TDD fixture or review id)."""
    config = _pyproject()
    assert config["build-system"]["build-backend"] == "hatchling.build", "positive control"
    assert dynamic_entry_point_violations(config, REPO) == []


@pytest.mark.parametrize(
    "planted",
    [
        {"project": {"dynamic": ["entry-points"]}},
        {"project": {"dynamic": ["version", "scripts"]}},
        {"tool": {"hatch": {"build": {"hooks": {"custom": {}}}}}},
        {"tool": {"hatch": {"build": {"targets": {"wheel": {"hooks": {"custom": {}}}}}}}},
        {"tool": {"hatch": {"metadata": {"hooks": {"custom": {}}}}}},
        {"build-system": {"build-backend": "setuptools.build_meta"}},
        {"build-system": {"build-backend": "hatchling.build", "requires": ["hatchling", "x"]}},
    ],
    ids=[
        "dynamic-entry-points",
        "dynamic-scripts",
        "build-hook",
        "target-hook",
        "metadata-hook",
        "other-backend",
        "hook-plugin",
    ],
)
def test_planted_dynamic_entry_point_or_build_hook_is_flagged(
    planted: dict[str, Any], tmp_path: Path
) -> None:
    """PM-4 teeth, auth-bench A3-3 (D6 TDD fixture or review id)."""
    base: dict[str, Any] = {"build-system": {"build-backend": "hatchling.build"}}
    config = {**base, **planted}
    assert dynamic_entry_point_violations(config, tmp_path), planted


def test_planted_hatch_build_file_is_flagged(tmp_path: Path) -> None:
    """PM-4 teeth, auth-bench A3-3 (D6 TDD fixture or review id)."""
    config = {"build-system": {"build-backend": "hatchling.build", "requires": ["hatchling"]}}
    assert dynamic_entry_point_violations(config, tmp_path) == [], "twin: clean tree"
    (tmp_path / "hatch_build.py").write_text("")
    assert dynamic_entry_point_violations(config, tmp_path)


@pytest.mark.parametrize(
    "project",
    [
        {
            "entry-points": {
                "autom8.hooks": {"store": "tests.unit.trigger.adapters:InMemoryKeyHookStore"}
            }
        },
        {"entry-points": {"pytest11": {"d6": "autom8_asana.trigger.registration"}}},
        {
            "scripts": {
                "hook-reconcile": "autom8_asana.trigger.registration:build_shadow_registration"
            }
        },
        {"gui-scripts": {"x": "pkg:InMemoryHookRegistry"}},
    ],
    ids=["adapter-plugin", "trigger-plugin", "trigger-script", "adapter-gui-script"],
)
def test_planted_adapter_entry_point_is_flagged(project: dict[str, Any]) -> None:
    """PM-4 teeth (D6 TDD fixture or review id)."""
    assert entry_point_violations({"project": project})
