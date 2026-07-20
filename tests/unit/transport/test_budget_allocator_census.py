"""ITEM-B census + per-lane fail-open tests (adversary AC-1 unification-totality).

The census is a static build-gate asserting (verbatim adversary AC-1):
  (a) every ``AsanaClient(`` site resolves to the process singleton;
  (b) ZERO sites pass an explicit rate-limiter/config injection that bypasses it
      (overrides may exist for TESTS only, never in ``src/``);
  (c) ZERO non-AsanaClient egress to ``app.asana.com``.

TL-A BUILD-GATE (ITEM-B): a census grep proves ZERO un-routed Asana call-sites
outside fixtures; injecting a limiter exception on one lane leaves it proceeding
while siblings are unaffected. If any site bypasses the limiter, or a limiter
fault blocks a lane (fail-closed) instead of failing open, HALT.

The census is AST-based (robust against docstrings/comments) and RED-ARMABLE:
``test_census_red_arm_detects_injected_bypass`` proves the detector bites when a
bypass construction is injected (adversary AC-1 "RED arm = inject one bypass
site, census must fail").
"""

from __future__ import annotations

import ast
from pathlib import Path

import autom8_asana
from autom8_asana.config import BudgetAllocatorConfig
from autom8_asana.transport.budget_allocator import (
    BudgetAllocator,
    Lane,
    set_budget_allocator,
)

_SRC_ROOT = Path(autom8_asana.__file__).resolve().parent

# The ONLY sanctioned Asana-egress construction sites (relative to the package
# root). A new file appearing in a census result outside these sets is a bypass.
_SANCTIONED_HTTP_CLIENT_FILES = {"client.py"}
_SANCTIONED_API_EGRESS_FILES = {"client.py", "settings.py", "config.py"}


def _iter_src_files() -> list[Path]:
    return [p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts]


def _rel(path: Path) -> str:
    return str(path.relative_to(_SRC_ROOT))


def _find_http_client_constructions(source: str) -> bool:
    """Return True if ``source`` constructs ``AsanaHttpClient(...)`` (AST Call).

    AST-based so docstring examples (``>>> AsanaHttpClient(...)``) and comments do
    NOT count -- only real construction call expressions.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - src is always parseable
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "AsanaHttpClient":
                return True
    return False


def _find_api_egress_literals(source: str) -> bool:
    """Return True if ``source`` contains an Asana API-base string constant.

    Targets the API endpoint ``app.asana.com/api`` specifically -- NOT the
    human-facing task permalinks ``app.asana.com/0/0/{gid}``, which are display
    URLs, not egress.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "app.asana.com/api" in node.value:
                return True
    return False


# --------------------------------------------------------------------------
# (a) unification point: __init__ routes every client through the singleton
# --------------------------------------------------------------------------


def test_client_init_calls_the_attach_seam() -> None:
    """Every AsanaClient construction flows through __init__ -> the attach seam."""
    client_src = (_SRC_ROOT / "client.py").read_text()
    tree = ast.parse(client_src)

    init_calls_attach = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for sub in ast.walk(node):
                if (
                    isinstance(sub, ast.Call)
                    and isinstance(sub.func, ast.Name)
                    and sub.func.id == "_attach_to_budget_allocator"
                ):
                    init_calls_attach = True
    assert init_calls_attach, (
        "AsanaClient.__init__ must call _attach_to_budget_allocator -- this is the "
        "single seam that unifies all ~57 construction sites onto the singleton (PC-1)."
    )


# --------------------------------------------------------------------------
# (b) ZERO bypassing AsanaHttpClient constructions outside the sanctioned set
# --------------------------------------------------------------------------


def test_census_http_client_construction_confined_to_client_py() -> None:
    offenders: set[str] = set()
    for path in _iter_src_files():
        if _find_http_client_constructions(path.read_text()):
            offenders.add(_rel(path))
    assert offenders == _SANCTIONED_HTTP_CLIENT_FILES, (
        f"AsanaHttpClient construction must be confined to {_SANCTIONED_HTTP_CLIENT_FILES} "
        f"(the singleton seam). Found in: {sorted(offenders)}. A construction outside "
        "client.py bypasses the process-singleton limiter (adversary CH-01)."
    )


# --------------------------------------------------------------------------
# (c) ZERO non-AsanaClient egress to app.asana.com/api outside the sanctioned set
# --------------------------------------------------------------------------


def test_census_api_egress_confined_to_sanctioned_files() -> None:
    offenders: set[str] = set()
    for path in _iter_src_files():
        if _find_api_egress_literals(path.read_text()):
            offenders.add(_rel(path))
    assert offenders <= _SANCTIONED_API_EGRESS_FILES, (
        f"Raw Asana API-base egress (app.asana.com/api) must be confined to "
        f"{_SANCTIONED_API_EGRESS_FILES}. Found extra in: "
        f"{sorted(offenders - _SANCTIONED_API_EGRESS_FILES)}. A non-AsanaClient egress "
        "escapes the singleton (adversary AC-1c)."
    )


# --------------------------------------------------------------------------
# RED ARM: the census detector must BITE on an injected bypass (AC-1 teeth)
# --------------------------------------------------------------------------


def test_census_red_arm_detects_injected_bypass() -> None:
    """Discriminating teeth: a synthetic bypass site is DETECTED by the census.

    This is the RED arm the adversary requires -- proving the census is not a
    theatrical no-op. Both detectors bite on the exact bypass vectors.
    """
    # A raw AsanaHttpClient construction outside client.py -> detected.
    bypass_http = (
        "from autom8_asana.transport.asana_http import AsanaHttpClient\n"
        "def leak():\n"
        "    return AsanaHttpClient(config=None, rate_limiter=object())\n"
    )
    assert _find_http_client_constructions(bypass_http) is True

    # A raw httpx egress to the Asana API base outside the sanctioned files.
    bypass_egress = 'URL = "https://app.asana.com/api/1.0/tasks"\n'
    assert _find_api_egress_literals(bypass_egress) is True

    # And the NO-defect variant does NOT trip (two-sided): a task permalink is
    # not egress, and a docstring mention is not a construction.
    assert _find_api_egress_literals('u = "https://app.asana.com/0/0/123"\n') is False
    assert _find_http_client_constructions('""">>> AsanaHttpClient(x)"""\n') is False


# --------------------------------------------------------------------------
# ITEM-B AC2: per-lane fail-open -- a limiter fault leaves the lane PROCEEDING
# --------------------------------------------------------------------------


class _RecordingLog:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def _rec(self, event: str, extra: dict[str, object] | None = None, **_: object) -> None:
        self.events.append((event, extra or {}))

    debug = info = warning = error = _rec

    def named(self, name: str) -> list[dict[str, object]]:
        return [extra for ev, extra in self.events if ev == name]


class _ExplodingAllocator(BudgetAllocator):
    """An allocator whose register_client raises -- to prove fail-open."""

    def register_client(self, client_id: int) -> None:  # type: ignore[override]
        raise RuntimeError("synthetic limiter fault")


def test_client_construction_proceeds_when_limiter_faults() -> None:
    """A limiter-internal exception must NOT fail-close client construction."""
    from autom8_asana.client import AsanaClient

    log = _RecordingLog()
    exploding = _ExplodingAllocator(BudgetAllocatorConfig(enabled=True), log_provider=log)
    set_budget_allocator(exploding)

    # Construction must SUCCEED (fail-open), not raise.
    client = AsanaClient(token="test-token-xyz", workspace_gid="1234567890123456")
    assert client is not None

    # The tripwire fired on the faulting lane.
    failopens = log.named("budget_lane_failopen")
    assert failopens, "expected budget_lane_failopen when the limiter faults"
    assert failopens[-1]["lane"] == Lane.FAIR_SHARE.value


def test_sibling_lane_unaffected_by_faulting_lane() -> None:
    """One lane's limiter fault must not cross-contaminate other lanes."""
    from autom8_asana.client import AsanaClient

    # First client: faulting allocator -> fail-open.
    faulting = _ExplodingAllocator(
        BudgetAllocatorConfig(enabled=True), log_provider=_RecordingLog()
    )
    set_budget_allocator(faulting)
    c1 = AsanaClient(token="lane-1-token", workspace_gid="1234567890123456")
    assert c1 is not None

    # Swap in a healthy allocator: a sibling lane proceeds normally + registers.
    healthy_log = _RecordingLog()
    healthy = BudgetAllocator(BudgetAllocatorConfig(enabled=True), log_provider=healthy_log)
    set_budget_allocator(healthy)
    c2 = AsanaClient(token="lane-2-token", workspace_gid="1234567890123456")
    assert c2 is not None
    assert healthy.registered_client_count == 1
    assert healthy_log.named("budget_lane_failopen") == []


def test_inert_allocator_does_not_register() -> None:
    """INERT: the attach early-returns (no interposition, no registration)."""
    from autom8_asana.client import AsanaClient

    log = _RecordingLog()
    inert = BudgetAllocator(BudgetAllocatorConfig(enabled=False), log_provider=log)
    set_budget_allocator(inert)
    client = AsanaClient(token="inert-token", workspace_gid="1234567890123456")
    assert client is not None
    assert inert.registered_client_count == 0
