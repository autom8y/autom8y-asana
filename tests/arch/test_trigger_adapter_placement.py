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
instance or ``dependency_overrides`` in ``src/``. The AST half scans ``trigger/`` and the
named wiring modules (package root, entrypoint, the API app and its dependencies). The
entry-point half reads package metadata (``[project.scripts]``, ``[project.gui-scripts]``,
``[project.entry-points.*]``), which is what hatch writes into the wheel's
``entry_points.txt``. Each check has a planted violation that it must flag.
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
        "InMemoryHookRegistry",
        "InMemoryKeyHookStore",
    }
)
# The wiring modules PM-4 scans besides trigger/ (where an override or default would go).
WIRING_MODULES = ("__init__.py", "entrypoint.py", "api/main.py", "api/dependencies.py")


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


def test_pm2_adapters_absent_from_wheel_sources() -> None:
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
def test_pm2_planted_wheel_source_is_flagged(wheel: dict[str, Any]) -> None:
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


def test_pm2_adapters_absent_from_image() -> None:
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
def test_pm2_planted_image_copy_is_flagged(line: str) -> None:
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


def test_pm2_not_importable_from_the_image_path(tmp_path: Path) -> None:
    assert _probe(SRC, tmp_path) == "ABSENT"


def test_pm2_twin_present_in_the_test_tree(tmp_path: Path) -> None:
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


def src_violations(source: str, filename: str = "<planted>") -> list[str]:
    tree = ast.parse(source, filename=filename)
    found: list[str] = []
    for node in ast.walk(tree):
        line = f"{filename}:{getattr(node, 'lineno', 0)}"
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tests":
            found.append(f"{line} imports from tests")
        elif isinstance(node, ast.Import) and any(
            a.name.split(".")[0] == "tests" for a in node.names
        ):
            found.append(f"{line} imports tests")
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
    trigger = sorted((PACKAGE / "trigger").glob("*.py"))
    assert PACKAGE / "trigger" / "registration.py" in trigger, "positive control"
    return trigger + [PACKAGE / name for name in WIRING_MODULES]


def test_pm4_src_has_no_adapter_wiring() -> None:
    found: list[str] = []
    for path in _scanned_modules():
        found += src_violations(path.read_text(), str(path.relative_to(SRC)))
    assert found == [], "\n".join(found)


PLANTED_SRC = {
    "import-adapter": "from tests.unit.trigger.adapters import InMemoryKeyHookStore\n",
    "dependency-overrides": "app.dependency_overrides[get_store] = lambda: store\n",
    "default-store": "from x import HookStore\n_default = HookStore()\n",
    "default-reconciler": "RECONCILER = build_shadow_registration(environ={})\n",
    "adapter-registry": "ADAPTERS = {'test': InMemoryHookRegistry, 'production': HookRegistry}\n",
    "string-registry": "PLUGINS = {'test': 'tests.unit.trigger.adapters:InMemoryKeyHookStore'}\n",
}


@pytest.mark.parametrize("name", sorted(PLANTED_SRC))
def test_pm4_planted_src_violation_is_flagged(name: str) -> None:
    assert src_violations(PLANTED_SRC[name]), name


def test_pm4_twin_clean_source_passes() -> None:
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


def test_pm4_package_metadata_has_no_adapter_entry_point() -> None:
    config = _pyproject()
    assert config["project"]["scripts"], "positive control: the metadata has entry points"
    assert entry_point_violations(config) == []


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
def test_pm4_planted_entry_point_is_flagged(project: dict[str, Any]) -> None:
    assert entry_point_violations({"project": project})
