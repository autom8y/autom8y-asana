"""CW-1 / CW-5: no route to the full AsanaClient or the auth package, outside the graph.

The package root re-exports ``AsanaClient`` as an attribute
(``src/autom8_asana/__init__.py``), so ``import autom8_asana`` followed by
``autom8_asana.AsanaClient`` is an edge to the package root only, and import-linter
cannot see it. Import-linter contracts also name modules, so forbidding
``autom8_asana.auth.bot_pat`` does not catch ``from autom8_asana.auth import get_bot_pat``
(the package re-exports it, auth/__init__.py). Nothing in trigger/ or the hook route needs
auth or the full client.

Scope: every module under ``autom8_asana/trigger/``, recursively (subpackages included),
plus the hook route ``api/routes/asana_hook.py``, which is a trigger-decide-readonly
source (auth-bench A3-4).

Refused, each with a planted case that must be flagged:

* any import of the name ``AsanaClient``, from any module;
* any import of ``autom8_asana.client`` or of the ``autom8_asana.auth`` package or its
  submodules, absolute OR RELATIVE (``from ..auth import get_bot_pat``,
  ``from .. import client``): relative imports are resolved against the file's package;
* any attribute ``<expr>.AsanaClient``, ``<expr>.bot_pat`` or ``<expr>.get_bot_pat``;
* any attribute chain rooted at a name bound to an ``autom8_asana`` module that reaches
  ``autom8_asana.client`` or ``autom8_asana.auth`` (``autom8_asana.auth.bot_pat``,
  ``a.client.AsanaClient`` after ``import autom8_asana as a``);
* a dynamic lookup (``getattr``, ``__import__``, ``importlib.import_module``) whose string
  argument names a forbidden module, its relative form (resolved against the ``package``
  argument or the file's package), ``AsanaClient``, or a short name: ``auth``, ``client``,
  ``bot_pat``, ``get_bot_pat``;
* any module-cache lookup (``sys.modules``, ``from sys import modules``), except the one
  pinned site: ``ports_webhooks._full_client_class``, which reads the SDK webhooks class
  for an identity check and never builds a client;
* any star import.

Not catchable statically, and not claimed: a name assembled at run time (string
concatenation, formatting, ``chr`` arithmetic, data read from a file or the environment)
and passed to a dynamic lookup. The import-linter contracts, the runtime class checks
(R-A5b) and review carry that residue.

Teeth: each planted source is flagged; the real tree and a clean source pass.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
TRIGGER_DIR = SRC / "autom8_asana" / "trigger"
HOOK_ROUTE = SRC / "autom8_asana" / "api" / "routes" / "asana_hook.py"

_ROOT = "autom8_asana"
_CLIENT_NAME = "AsanaClient"
_FORBIDDEN_MODULES = ("autom8_asana.client", "autom8_asana.auth")
_FORBIDDEN_ATTRIBUTES = frozenset({_CLIENT_NAME, "bot_pat", "get_bot_pat"})
_SHORT_NAMES = frozenset({"auth", "client", "bot_pat", "get_bot_pat", _CLIENT_NAME})
_DYNAMIC = frozenset({"getattr", "__import__", "import_module"})
# The one sanctioned module-cache lookup: (path under src/, enclosing function).
_SANCTIONED_MODULE_CACHE = frozenset(
    {("autom8_asana/trigger/ports_webhooks.py", "_full_client_class")}
)


def _is_or_under(module: str, root: str) -> bool:
    return module == root or module.startswith(root + ".")


def _forbidden(module: str) -> bool:
    return any(_is_or_under(module, root) for root in _FORBIDDEN_MODULES)


def _package_of(filename: str) -> str:
    """The dotted package a file under src/ belongs to ("" for a planted source)."""
    path = Path(filename)
    if path.is_absolute() or not filename.endswith(".py"):
        return f"{_ROOT}.trigger"  # planted sources stand in for a trigger module
    # A module's package and an __init__'s package are both the containing directory.
    return ".".join(path.with_suffix("").parts[:-1])


def _resolve_relative(level: int, module: str | None, package: str) -> str:
    """Resolve ``from <'.' * level><module> import ...`` against ``package``."""
    if level == 0:
        return module or ""
    parts = package.split(".")
    base = parts[: len(parts) - (level - 1)] if level > 1 else parts
    return ".".join([*base, module] if module else base)


def _resolve_string(name: str, package: str) -> str:
    """A string passed to ``import_module``: resolve a leading-dot relative name."""
    if not name.startswith("."):
        return name
    level = len(name) - len(name.lstrip("."))
    return _resolve_relative(level, name.lstrip(".") or None, package)


def _bindings(tree: ast.AST, package: str) -> dict[str, str]:
    """Local names bound to ``autom8_asana`` modules by import statements."""
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _is_or_under(alias.name, _ROOT):
                    continue
                if alias.asname:
                    bound[alias.asname] = alias.name
                else:
                    bound[alias.name.split(".")[0]] = _ROOT
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_relative(node.level, node.module, package)
            if not _is_or_under(base, _ROOT):
                continue
            for alias in node.names:
                if alias.name != "*":
                    bound[alias.asname or alias.name] = f"{base}.{alias.name}"
    return bound


def _sys_names(tree: ast.AST) -> set[str]:
    """Local names bound to the ``sys`` module (``import sys``, ``import sys as x``)."""
    names = {"sys"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sys":
                    names.add(alias.asname or "sys")
    return names


def _is_dynamic_sys(node: ast.expr) -> bool:
    """``__import__('sys')`` or ``import_module('sys')``: a call that returns ``sys``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
    return name in _DYNAMIC and "sys" in _string_arg(node)


def _chain_base(node: ast.Attribute) -> ast.expr:
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current


def _chain(node: ast.Attribute) -> tuple[str | None, list[str]]:
    attrs: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        attrs.append(current.attr)
        current = current.value
    root = current.id if isinstance(current, ast.Name) else None
    return root, list(reversed(attrs))


def _enclosing_functions(tree: ast.AST) -> dict[int, str]:
    """Map node id -> name of the innermost enclosing function."""
    owner: dict[int, str] = {}

    def visit(node: ast.AST, current: str) -> None:
        for child in ast.iter_child_nodes(node):
            name = (
                child.name if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) else current
            )
            owner[id(child)] = name
            visit(child, name)

    visit(tree, "")
    return owner


def _string_arg(node: ast.Call) -> list[str]:
    return [
        arg.value
        for arg in [*node.args, *(kw.value for kw in node.keywords)]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    ]


def _package_kwarg(node: ast.Call, default: str) -> str:
    for kw in node.keywords:
        if kw.arg == "package" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
        return str(node.args[1].value)
    return default


def violations(source: str, filename: str = "<planted>") -> list[str]:
    tree = ast.parse(source, filename=filename)
    package = _package_of(filename)
    bound = _bindings(tree, package)
    sys_names = _sys_names(tree)
    owner = _enclosing_functions(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        line = f"{filename}:{getattr(node, 'lineno', 0)}"
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _forbidden(alias.name):
                    found.append(f"{line} import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_relative(node.level, node.module, package)
            for alias in node.names:
                if alias.name == "*":
                    found.append(f"{line} star import from {base or '.'}")
                    continue
                full = f"{base}.{alias.name}" if base else alias.name
                if alias.name == _CLIENT_NAME:
                    found.append(f"{line} imports {_CLIENT_NAME} from {base}")
                elif _forbidden(base) or _forbidden(full):
                    found.append(f"{line} imports from {full}")
                elif base == "sys" and alias.name == "modules":
                    found.append(f"{line} module-cache import from sys")
        elif isinstance(node, ast.Attribute):
            if node.attr in _FORBIDDEN_ATTRIBUTES:
                found.append(f"{line} attribute .{node.attr}")
            root, attrs = _chain(node)
            if attrs[:1] == ["modules"] and (
                root in sys_names or _is_dynamic_sys(_chain_base(node))
            ):
                site = (filename, owner.get(id(node), ""))
                if site not in _SANCTIONED_MODULE_CACHE:
                    found.append(f"{line} module-cache lookup sys.modules")
            elif root in bound:
                dotted = ".".join([bound[root], *attrs])
                if _forbidden(dotted):
                    found.append(f"{line} attribute chain to {dotted}")
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name not in _DYNAMIC:
                continue
            if (
                name == "getattr"
                and node.args
                and (
                    (isinstance(node.args[0], ast.Name) and node.args[0].id in sys_names)
                    or _is_dynamic_sys(node.args[0])
                )
                and "modules" in _string_arg(node)
            ):
                found.append(f"{line} module-cache lookup getattr(sys, 'modules')")
            target_package = _package_kwarg(node, package)
            for value in _string_arg(node):
                resolved = _resolve_string(value, target_package)
                if (
                    value in _SHORT_NAMES
                    or _CLIENT_NAME in value
                    or _forbidden(value)
                    or _forbidden(resolved)
                ):
                    found.append(f"{line} dynamic lookup of {value!r}")
    return found


def _scanned_modules() -> list[Path]:
    modules = sorted(TRIGGER_DIR.rglob("*.py"))
    assert TRIGGER_DIR / "registration.py" in modules, "positive control: registration.py"
    assert TRIGGER_DIR / "receiver.py" in modules, "positive control: receiver.py"
    assert HOOK_ROUTE.is_file(), "positive control: the hook route"
    return [*modules, HOOK_ROUTE]


def test_trigger_package_has_no_route_to_asana_client_or_auth() -> None:
    found: list[str] = []
    for path in _scanned_modules():
        found += violations(path.read_text(), str(path.relative_to(SRC)))
    assert found == [], "\n".join(found)


def test_the_sanctioned_module_cache_site_is_real() -> None:
    """The one allowlisted sys.modules lookup exists where it is pinned (no stale entry)."""
    ((path, function),) = _SANCTIONED_MODULE_CACHE
    tree = ast.parse((SRC / path).read_text())
    functions = {
        n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert function in functions
    assert "sys.modules" in ast.unparse(functions[function])
    # Moved anywhere else, the same lookup is flagged.
    moved = "import sys\n\ndef other():\n    return sys.modules.get('x')\n"
    assert violations(moved, path)


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
    # auth-bench A3-4
    "relative-auth": "from ..auth import get_bot_pat\n",
    "relative-auth-module": "from ..auth.bot_pat import get_bot_pat as g\n",
    "relative-client": "from .. import client\n",
    "relative-client-class": "from ..client import AsanaClient\n",
    "relative-root-then-chain": "from .. import auth as a\nv = a.service_token\n",
    "attribute-chain-auth": "import autom8_asana\nm = autom8_asana.auth.dual_mode\n",
    "attribute-chain-client": "import autom8_asana.trigger as t\nimport autom8_asana as r\nx = r.client\n",
    "attribute-get-bot-pat": "from x import y\nv = y.get_bot_pat()\n",
    "short-string-auth": "import autom8_asana\nm = getattr(autom8_asana, 'auth')\n",
    "short-string-bot-pat": "m = getattr(mod, 'bot_pat')\n",
    "short-string-get-bot-pat": "f = getattr(mod, 'get_bot_pat')\n",
    "short-string-client": "import autom8_asana\nm = getattr(autom8_asana, 'client')\n",
    "dunder-import": "m = __import__('autom8_asana.auth')\n",
    "relative-import-module": (
        "import importlib\nm = importlib.import_module('..auth', package='autom8_asana.trigger')\n"
    ),
    "relative-import-module-dunder-package": (
        "from importlib import import_module\nm = import_module('..client', __package__)\n"
    ),
    "module-cache-index": "import sys\nm = sys.modules['autom8_asana.auth']\n",
    "module-cache-get": "import sys\nm = sys.modules.get('somewhere')\n",
    "module-cache-from-sys": "from sys import modules\nm = modules['x']\n",
    "module-cache-sys-alias": "import sys as system\nm = system.modules['autom8_asana.auth']\n",
    "module-cache-getattr": "import sys\nm = getattr(sys, 'modules')['x']\n",
    "module-cache-getattr-alias": "import sys as s\nm = getattr(s, 'modules')['x']\n",
    "module-cache-dunder-import": "m = __import__('sys').modules['x']\n",
    "module-cache-import-module": "import importlib\nm = importlib.import_module('sys').modules['x']\n",
    "star-import": "from autom8_asana.errors import *\n",
    "star-import-relative": "from .hook_store import *\n",
}


@pytest.mark.parametrize("name", sorted(PLANTED))
def test_planted_route_is_flagged(name: str) -> None:
    assert violations(PLANTED[name]), f"{name} was not flagged"


def test_planted_source_in_a_trigger_subpackage_is_scanned(tmp_path: Path) -> None:
    """A module in a subfolder of trigger/ is found by the recursive scan."""
    nested = TRIGGER_DIR / "actions"
    assert not nested.exists(), "trigger/actions exists now; this case must change"
    found = sorted(TRIGGER_DIR.rglob("*.py"))
    assert all(p.is_relative_to(TRIGGER_DIR) for p in found)
    # rglob reaches a planted nested file in a copy of the layout.
    planted = tmp_path / "trigger" / "actions" / "launch.py"
    planted.parent.mkdir(parents=True)
    # One level deeper, so the auth package is three dots up.
    planted.write_text("from ...auth import get_bot_pat\n")
    assert planted in sorted((tmp_path / "trigger").rglob("*.py"))
    assert violations(planted.read_text(), "autom8_asana/trigger/actions/launch.py")


def test_relative_imports_resolve_against_the_file_package() -> None:
    """``..`` from trigger/ is the root package; from api/routes/ it is api."""
    assert _resolve_relative(2, "auth", "autom8_asana.trigger") == "autom8_asana.auth"
    assert _resolve_relative(1, "hook_store", "autom8_asana.trigger") == (
        "autom8_asana.trigger.hook_store"
    )
    assert _resolve_relative(2, None, "autom8_asana.api.routes") == "autom8_asana.api"
    assert violations("from ...auth import get_bot_pat\n", "autom8_asana/api/routes/x.py")
    # Twin: the same relative form inside the trigger package that names a sibling passes.
    assert violations("from .hook_store import handle_fingerprint\n") == []


def test_clean_twin_passes() -> None:
    clean = (
        "from autom8_asana.trigger.ports_webhooks import WebhooksClient\n"
        "from autom8_asana.errors import AsanaError\n"
        "from .hook_store import handle_fingerprint\n"
        "import boto3\n"
        "import sys as system\n"
        "argv = system.argv\n"
        "c = boto3.client('dynamodb')\n"
        "v = getattr(obj, 'name', None)\n"
        '"""A docstring may say AsanaClient."""\n'
        "x = 'AsanaClient is mentioned in a message'\n"
    )
    assert violations(clean) == []
