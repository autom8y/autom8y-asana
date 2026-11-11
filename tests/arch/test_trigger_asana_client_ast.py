"""CW-1: no route to the full AsanaClient from ``autom8_asana/trigger/``, outside the graph.

The package root re-exports ``AsanaClient`` as an attribute
(``src/autom8_asana/__init__.py``), so ``import autom8_asana`` followed by
``autom8_asana.AsanaClient`` is an edge to the package root only, and import-linter
cannot see it. This AST scan over every module under ``trigger/`` refuses:

* any import of the name ``AsanaClient``, from any module;
* any import of the module ``autom8_asana.client`` (``import`` or ``from autom8_asana
  import client``);
* any attribute access ``<expr>.AsanaClient``;
* a dynamic lookup (``getattr``, ``__import__``, ``importlib.import_module``) whose string
  argument names ``AsanaClient`` or ``autom8_asana.client``.

It also closes the hole CW-5 leaves in the contracts. Import-linter contracts name
modules, so forbidding ``autom8_asana.auth.bot_pat`` does not catch
``from autom8_asana.auth import get_bot_pat`` (the package re-exports it,
auth/__init__.py). Any import of ``autom8_asana.auth`` or its submodules, and any
``.bot_pat`` attribute, is refused here. Nothing in trigger/ needs auth.

Teeth: each planted source is flagged; the real tree and a clean source pass.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TRIGGER_DIR = Path(__file__).resolve().parents[2] / "src" / "autom8_asana" / "trigger"

_CLIENT_NAME = "AsanaClient"
_CLIENT_MODULE = "autom8_asana.client"
_AUTH_PACKAGE = "autom8_asana.auth"
_DYNAMIC = {"getattr", "__import__", "import_module"}


def _is_or_under(module: str, root: str) -> bool:
    return module == root or module.startswith(root + ".")


def violations(source: str, filename: str = "<planted>") -> list[str]:
    tree = ast.parse(source, filename=filename)
    found: list[str] = []
    for node in ast.walk(tree):
        line = f"{filename}:{getattr(node, 'lineno', 0)}"
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_or_under(alias.name, _CLIENT_MODULE) or _is_or_under(
                    alias.name, _AUTH_PACKAGE
                ):
                    found.append(f"{line} import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                full = f"{module}.{alias.name}" if module else alias.name
                if alias.name == _CLIENT_NAME:
                    found.append(f"{line} imports {_CLIENT_NAME} from {module}")
                elif _is_or_under(module, _CLIENT_MODULE) or _is_or_under(full, _CLIENT_MODULE):
                    found.append(f"{line} imports from {_CLIENT_MODULE}")
                elif _is_or_under(module, _AUTH_PACKAGE) or _is_or_under(full, _AUTH_PACKAGE):
                    found.append(f"{line} imports from {_AUTH_PACKAGE}")
        elif isinstance(node, ast.Attribute) and node.attr in (_CLIENT_NAME, "bot_pat"):
            found.append(f"{line} attribute .{node.attr}")
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name in _DYNAMIC:
                for arg in node.args:
                    if (
                        isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)
                        and (
                            _CLIENT_NAME in arg.value
                            or _is_or_under(arg.value, _CLIENT_MODULE)
                            or _is_or_under(arg.value, _AUTH_PACKAGE)
                        )
                    ):
                        found.append(f"{line} dynamic lookup of {arg.value!r}")
    return found


def _trigger_modules() -> list[Path]:
    modules = sorted(TRIGGER_DIR.glob("*.py"))
    assert TRIGGER_DIR / "registration.py" in modules, "positive control: registration.py"
    return modules


def test_trigger_package_has_no_route_to_asana_client_or_auth() -> None:
    found: list[str] = []
    for path in _trigger_modules():
        found += violations(path.read_text(), str(path.relative_to(TRIGGER_DIR.parents[1])))
    assert found == [], "\n".join(found)


PLANTED = {
    "root-attribute": "import autom8_asana\nc = autom8_asana.AsanaClient\n",
    "aliased-root-attribute": "import autom8_asana as a\nc = a.AsanaClient()\n",
    "from-root": "from autom8_asana import AsanaClient\n",
    "from-client-module": "from autom8_asana.client import AsanaClient as C\n",
    "client-module-import": "import autom8_asana.client\n",
    "client-module-from-root": "from autom8_asana import client\n",
    "getattr": "import autom8_asana\nc = getattr(autom8_asana, 'AsanaClient')\n",
    "import-module": "import importlib\nm = importlib.import_module('autom8_asana.client')\n",
    "lazy-in-function": "def f():\n    from autom8_asana import AsanaClient\n    return AsanaClient\n",
    "auth-package-reexport": "from autom8_asana.auth import get_bot_pat\n",
    "auth-root-from": "from autom8_asana import auth\n",
    "auth-bot-pat-module": "import autom8_asana.auth.bot_pat\n",
    "bot-pat-attribute": "import autom8_asana\np = autom8_asana.auth.bot_pat\n",
}


@pytest.mark.parametrize("name", sorted(PLANTED))
def test_planted_route_is_flagged(name: str) -> None:
    assert violations(PLANTED[name]), f"{name} was not flagged"


def test_clean_twin_passes() -> None:
    clean = (
        "from autom8_asana.trigger.ports_webhooks import WebhooksClient\n"
        "from autom8_asana.errors import AsanaError\n"
        '"""A docstring may say AsanaClient."""\n'
        "x = 'AsanaClient is mentioned in a message'\n"
    )
    assert violations(clean) == []
