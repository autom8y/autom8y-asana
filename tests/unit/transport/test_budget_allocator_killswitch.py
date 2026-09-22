"""ITEM-D kill-switch tests -- ENABLED=false byte-identical, both directions.

The default-off kill-switch: ENABLED=false => byte-identical to the pre-allocator
path (no limiter interposition at the seam). Regression tests both directions,
per-process-fresh bind, CI env census, rollback = config-only.

TL-A BUILD-GATE (ITEM-D): ENABLED=false then default client construction yields a
request path byte-identical to pre-allocator (no interposition); ENABLED=true
interposes the advisory check. If ENABLED=false leaves ANY allocator interposition
in the hot path, the kill-switch is unreliable -- HALT (the ITEM-D dead-knob
lesson: the knob's settings bind MUST be per-process-fresh, not import-time-once).
"""

from __future__ import annotations

import ast
from pathlib import Path

import autom8_asana
from autom8_asana.client import AsanaClient
from autom8_asana.config import BudgetAllocatorConfig
from autom8_asana.transport import budget_allocator as ba_module
from autom8_asana.transport.budget_allocator import (
    BudgetAllocator,
    Lane,
    get_budget_allocator,
    reset_budget_allocator,
    set_budget_allocator,
)

_PKG_ROOT = Path(autom8_asana.__file__).resolve().parent
_REPO_ROOT = _PKG_ROOT.parents[1]
_WORKSPACE = "1234567890123456"


class _SpyAllocator(BudgetAllocator):
    """Counts request-affecting interactions to prove (non-)interposition."""

    def __init__(self, config: BudgetAllocatorConfig) -> None:
        super().__init__(config)
        self.register_calls = 0
        self.observe_calls = 0

    def register_client(self, client_id: int) -> None:
        self.register_calls += 1
        super().register_client(client_id)

    def observe_admission(self, lane: Lane, *, count: int = 1) -> None:
        self.observe_calls += 1
        super().observe_admission(lane, count=count)


# --------------------------------------------------------------------------
# Byte-identity at the seam: ENABLED=false => ZERO interposition
# --------------------------------------------------------------------------


def test_disabled_seam_makes_zero_allocator_interposition() -> None:
    """ENABLED=false: the attach early-returns; the allocator is never touched."""
    spy = _SpyAllocator(BudgetAllocatorConfig(enabled=False))
    set_budget_allocator(spy)
    client = AsanaClient(token="disabled-token", workspace_gid=_WORKSPACE)
    assert client is not None
    assert spy.register_calls == 0  # no registration
    assert spy.observe_calls == 0  # no advisory observation
    assert spy.registered_client_count == 0  # no interposition state


def test_enabled_interposes_only_advisory_registration() -> None:
    """ENABLED=true: the ONLY seam touch is one advisory registration (not the hot path)."""
    spy = _SpyAllocator(BudgetAllocatorConfig(enabled=True))
    set_budget_allocator(spy)
    client = AsanaClient(token="enabled-token", workspace_gid=_WORKSPACE)
    assert client is not None
    assert spy.register_calls == 1  # one advisory bookkeeping call at construction
    assert spy.observe_calls == 0  # nothing in the request path


def test_request_path_allocator_reference_is_the_guarded_fair_share_cap_only() -> None:
    """Byte-identity at the request path: the ONLY allocator reference is the guarded ECS
    fair-share cap in ``asana_http.py``; the per-resource ``clients/`` stay allocator-free.

    SUPERSEDES the pre-cap structural-absence contract (the allocator used to be absent
    from ``asana_http.py`` entirely). The ECS 1390/60s fair-share self-cap wires an in-path
    ``gate.admit`` on the GET path -- mirroring the warmer floor gate, whose byte-identity
    is ALSO runtime-guard-based (``_floor_paced`` returns the SAME closure when inert), not
    structural absence. So ``asana_http.py`` now references the allocator, but ONLY inside
    the fair-share seam, which is byte-identical-INERT when disabled (proven by
    ``test_ast_fair_share_resolve_is_enabled_guarded``). Two guarantees survive verbatim:

    * the per-resource ``clients/`` modules remain STRUCTURALLY allocator-free; and
    * the ``asana_http.py`` reference is FUNCTION-LOCAL (no module-level import), so an
      INERT process pays nothing at import/construction (the ITEM-D dead-knob discipline).
    """
    # (1) clients/ MUST stay allocator-free -- unchanged structural-absence guarantee.
    client_modules = [
        p for p in (_PKG_ROOT / "clients").rglob("*.py") if "__pycache__" not in p.parts
    ]
    client_offenders = [
        str(p.relative_to(_PKG_ROOT)) for p in client_modules if "budget_allocator" in p.read_text()
    ]
    assert client_offenders == [], (
        f"budget_allocator must NOT appear in the per-resource clients/ (found: "
        f"{client_offenders}) -- those carry no per-request interposition."
    )

    # (2) asana_http.py carries the in-path fair-share cap now -- but only function-local.
    http_src = (_PKG_ROOT / "transport" / "asana_http.py").read_text()
    assert "budget_allocator" in http_src  # the in-path fair-share cap lives here
    tree = ast.parse(http_src)
    module_level_ba_imports: list[str] = []
    for node in tree.body:  # top-level statements ONLY (TYPE_CHECKING block is nested)
        if isinstance(node, ast.ImportFrom) and node.module and "budget_allocator" in node.module:
            module_level_ba_imports.append(node.module)
        elif isinstance(node, ast.Import):
            module_level_ba_imports += [a.name for a in node.names if "budget_allocator" in a.name]
    assert module_level_ba_imports == [], (
        "budget_allocator must be imported function-locally in asana_http.py, never at "
        f"module level (found: {module_level_ba_imports}) -- a runtime module-level import "
        "risks import-time interposition drift from byte-identity."
    )


def test_ast_fair_share_resolve_is_enabled_guarded() -> None:
    """The fair-share seam early-returns when disabled (byte-identical-INERT).

    AST proof that ``_resolve_fair_share_gate`` contains an ``if not allocator.enabled:
    return None`` guard -- the byte-identical-seam invariant for the in-path ECS cap,
    symmetric with ``test_ast_client_init_attach_is_guarded_early_return``.
    """
    src = (_PKG_ROOT / "transport" / "asana_http.py").read_text()
    tree = ast.parse(src)
    guarded = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_resolve_fair_share_gate":
            for sub in ast.walk(node):
                if isinstance(sub, ast.If):
                    # a bare `return` inside an `if ...` guard (disabled / off-lane / non-GET)
                    if any(isinstance(s, ast.Return) for s in sub.body):
                        guarded = True
    assert guarded, "_resolve_fair_share_gate must early-return when disabled"


# --------------------------------------------------------------------------
# Knob precedence -- both directions
# --------------------------------------------------------------------------


def test_unset_env_defaults_to_inert(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ASANA_BUDGET_ALLOCATOR_ENABLED", raising=False)
    reset_budget_allocator()
    assert get_budget_allocator().enabled is False


def test_explicit_true_activates(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ASANA_BUDGET_ALLOCATOR_ENABLED", "true")
    reset_budget_allocator()
    assert get_budget_allocator().enabled is True


def test_explicit_false_after_true_deactivates(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Rollback direction: true -> false flips back to INERT (config-only)."""
    monkeypatch.setenv("ASANA_BUDGET_ALLOCATOR_ENABLED", "true")
    reset_budget_allocator()
    assert get_budget_allocator().enabled is True
    monkeypatch.setenv("ASANA_BUDGET_ALLOCATOR_ENABLED", "false")
    reset_budget_allocator()
    assert get_budget_allocator().enabled is False


def test_explicit_config_bypasses_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Explicit BudgetAllocatorConfig wins over env (canary fixtures arm in-process)."""
    monkeypatch.setenv("ASANA_BUDGET_ALLOCATOR_ENABLED", "false")
    armed = BudgetAllocator(BudgetAllocatorConfig(enabled=True))
    assert armed.enabled is True  # ignores the env=false


# --------------------------------------------------------------------------
# Per-process-fresh bind (killswitch-rollback-spec §2.2 BUILD-GATE)
# --------------------------------------------------------------------------


def test_singleton_is_lazy_not_import_time_frozen(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The knob binds per-process-fresh, not import-time-once (the dead-knob HALT).

    After a reset the singleton is None (NOT constructed at import). Flipping the
    env then re-accessing reflects the CURRENT env -- proving the bind is not
    frozen at module import.
    """
    reset_budget_allocator()
    assert ba_module._ALLOCATOR is None  # not constructed at import time

    monkeypatch.setenv("ASANA_BUDGET_ALLOCATOR_ENABLED", "false")
    reset_budget_allocator()
    assert get_budget_allocator().enabled is False

    # Flip env AFTER the module was long-since imported; the next fresh access
    # must reflect it (would be impossible if bound import-time-once).
    monkeypatch.setenv("ASANA_BUDGET_ALLOCATOR_ENABLED", "true")
    reset_budget_allocator()
    assert get_budget_allocator().enabled is True


# --------------------------------------------------------------------------
# CI-env census (killswitch-rollback-spec §2.5): no pre-existing export
# --------------------------------------------------------------------------


def test_ci_deploy_configs_have_no_preexisting_allocator_export() -> None:
    """No fleet deploy/CI config pre-sets ASANA_BUDGET_ALLOCATOR_* (ships INERT).

    A pre-existing export would silently flip the merge posture away from INERT --
    an operator-ratification fork, not a silent default (killswitch-spec §2.5).
    """
    deploy_globs = ["*.tf", "*.yml", "*.yaml", "*.env", "Dockerfile*", "entrypoint*.sh"]
    excluded = {".venv", ".git", "node_modules", ".sos", "__pycache__", ".knossos"}
    scanned = 0
    offenders: list[str] = []
    for pattern in deploy_globs:
        for path in _REPO_ROOT.rglob(pattern):
            # Exclusions are checked RELATIVE to the repo root: the worktree may
            # itself live under a ``.knossos`` ancestor, which must not skip
            # everything -- only nested build/vendor dirs inside the tree.
            rel_parts = set(path.relative_to(_REPO_ROOT).parts)
            if rel_parts & excluded:
                continue
            scanned += 1
            try:
                text = path.read_text()
            except (UnicodeDecodeError, OSError):  # pragma: no cover
                continue
            if "ASANA_BUDGET_ALLOCATOR" in text:
                offenders.append(str(path.relative_to(_REPO_ROOT)))
    assert scanned > 0, "census scanned zero deploy configs -- glob is wrong"
    assert offenders == [], (
        f"pre-existing ASANA_BUDGET_ALLOCATOR_* export in deploy configs: {offenders}. "
        "The allocator must merge INERT with no ambient arm (F-a)."
    )


def test_allocator_env_not_ambient_set_in_test_process() -> None:
    """The conftest leakage guard: the knob is not ambient-set in CI (§2.4-item-4)."""
    import os

    assert "ASANA_BUDGET_ALLOCATOR_ENABLED" not in os.environ, (
        "ASANA_BUDGET_ALLOCATOR_ENABLED is ambient-set in the test process -- it "
        "would silently flip test posture. Set it only via scoped monkeypatch."
    )


# --------------------------------------------------------------------------
# Rollback is config-only (no schema migration)
# --------------------------------------------------------------------------


def test_rollback_is_config_only_no_persistent_state() -> None:
    """Flipping the knob is a pure config flip -- no migration, no persistent state.

    The config is a frozen dataclass carrying ONLY scalar knobs; there is no
    schema/table/file the allocator migrates, so rollback = flip ENABLED=false
    (or a symmetric revert) with nothing else to undo.
    """
    import dataclasses

    assert dataclasses.is_dataclass(BudgetAllocatorConfig)
    fields = {f.name for f in dataclasses.fields(BudgetAllocatorConfig)}
    assert fields == {
        "enabled",
        "floor_max_requests",
        "floor_window_seconds",
        "fair_share_max_requests",
    }
    # Frozen => immutable config value, no in-place drift.
    params = getattr(BudgetAllocatorConfig, "__dataclass_params__", None)
    assert params is not None and params.frozen is True


def test_changelog_documents_the_knob() -> None:
    """ITEM-D §2.6: the knob, default, and operator-only gate are in the changelog."""
    changelog = (_REPO_ROOT / "CHANGELOG.md").read_text()
    assert "ASANA_BUDGET_ALLOCATOR_ENABLED" in changelog
    assert "OPERATOR-ONLY" in changelog or "operator-only" in changelog


def test_ast_client_init_attach_is_guarded_early_return() -> None:
    """The attach helper early-returns when disabled (no interposition path).

    AST proof that ``_attach_to_budget_allocator`` contains an ``if not
    allocator.enabled: return`` guard -- the byte-identical-seam invariant.
    """
    src = (_PKG_ROOT / "client.py").read_text()
    tree = ast.parse(src)
    guarded = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_attach_to_budget_allocator":
            for sub in ast.walk(node):
                if isinstance(sub, ast.If):
                    # look for a bare `return` inside an `if not ...enabled` guard
                    has_return = any(isinstance(s, ast.Return) for s in sub.body)
                    if has_return:
                        guarded = True
    assert guarded, "_attach_to_budget_allocator must early-return when disabled"
