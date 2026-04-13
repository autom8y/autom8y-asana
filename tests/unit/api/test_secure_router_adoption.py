"""AST regression test for SecureRouter adoption in business-logic routes.

Per TDD-fleet-api-sovereignty-s2 §4.1.1 (OQ-S2-C ratification): every asana
router mounted under a path requiring ``require_business_scope`` MUST use
``SecureRouter`` (injected via the ``pat_router`` / ``s2s_router`` factory
helpers in ``_security.py``), except for routers whose prefixes fall under
``DEFAULT_EXCLUDE_PATHS`` (health/readiness/docs/openapi/metrics) or that
have a documented alternate-authentication exemption.

This test walks the ``src/autom8_asana/api/routes/`` module tree with ``ast``
and asserts that no raw ``APIRouter(...)`` construction exists in a route
module unless that module is on the explicit exemption allowlist below.

The exemption allowlist is intentionally small and closed-world: adding a
new entry requires a conscious decision and a code review. New routers
default to SecureRouter via ``pat_router`` / ``s2s_router``.

Background: the S2 sprint audit found that all 18 business-logic routers
in ``api/routes/`` had already adopted ``pat_router`` / ``s2s_router``; only
two files retained raw ``APIRouter``:

- ``health.py`` — serves /health, /ready, /health/deps (DEFAULT_EXCLUDE_PATHS)
- ``webhooks.py`` — SC-02 exemption: uses HMAC URL-token auth (``?token=``),
  not Bearer JWT, so SecureRouter's JWT security scheme metadata would be
  actively wrong for the OpenAPI spec. Documented inline at webhooks.py:36-38.

The test protects against a future engineer reintroducing a raw APIRouter
in a business-logic route without realizing the sweep.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Route module discovery
# ---------------------------------------------------------------------------

# Resolve the routes directory relative to this test file so the check works
# from any pytest invocation directory (CI, local, devbox).
_THIS_FILE = pathlib.Path(__file__).resolve()
# parents[0]=api  parents[1]=unit  parents[2]=tests  parents[3]=repo root
_REPO_ROOT = _THIS_FILE.parents[3]
_ROUTES_DIR = _REPO_ROOT / "src" / "autom8_asana" / "api" / "routes"


# ---------------------------------------------------------------------------
# Exemption allowlist
# ---------------------------------------------------------------------------

# Modules that are permitted to construct raw ``APIRouter``. Each entry MUST
# have a justification comment. Expanding this list requires reviewer sign-off.
#
# Keys are module filenames (relative to routes/). Values are the human-
# readable exemption reason.
EXEMPT_MODULES: dict[str, str] = {
    # Health router serves /health, /ready, /health/deps — all in
    # DEFAULT_EXCLUDE_PATHS. SecureRouter would inject JWT security metadata
    # into the OpenAPI spec for public liveness endpoints, which would be
    # incorrect. See TDD-fleet-api-sovereignty-s2 §4.1.1.
    "health.py": "DEFAULT_EXCLUDE_PATHS (/health, /ready, /health/deps)",
    # Webhooks use HMAC URL-token verification (``?token=<secret>``), not
    # Bearer JWT. SecureRouter would inject a JWT requirement into the spec
    # that is actively wrong for the webhook authentication model. The
    # /api/v1/webhooks/* prefix is excluded from JWTAuthMiddleware at the
    # app level (see api/main.py:299). See webhooks.py:36-38 for the inline
    # SC-02 exemption note and OQ-3 in the fleet-api-sovereignty TDD.
    "webhooks.py": "SC-02 HMAC URL-token auth (not Bearer JWT)",
}


# ---------------------------------------------------------------------------
# AST visitor helpers
# ---------------------------------------------------------------------------


def _iter_route_module_files() -> list[pathlib.Path]:
    """Return every ``.py`` route module file under ``api/routes/``.

    Excludes ``__init__.py`` (aggregator) and ``_security.py`` (factory
    definitions themselves, which legitimately reference SecureRouter
    internals).
    """
    if not _ROUTES_DIR.is_dir():
        pytest.fail(
            f"Routes directory not found at {_ROUTES_DIR}. Test environment may be misconfigured.",
        )
    files: list[pathlib.Path] = []
    for path in sorted(_ROUTES_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        if path.name == "_security.py":
            # The factory module itself does not construct APIRouter — it
            # returns SecureRouter — but skip defensively anyway.
            continue
        files.append(path)
    return files


def _find_apirouter_constructions(tree: ast.AST) -> list[int]:
    """Return line numbers of every ``APIRouter(...)`` call in ``tree``.

    Matches both bare ``APIRouter(...)`` and ``fastapi.APIRouter(...)`` forms.
    Does NOT match ``SecureRouter(...)``, ``pat_router(...)``,
    ``s2s_router(...)``, or any other identifier.
    """
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Bare ``APIRouter(...)`` — e.g. ``from fastapi import APIRouter``.
        bare_call = isinstance(func, ast.Name) and func.id == "APIRouter"
        # Qualified ``fastapi.APIRouter(...)``.
        qualified_call = (
            isinstance(func, ast.Attribute)
            and func.attr == "APIRouter"
            and isinstance(func.value, ast.Name)
            and func.value.id == "fastapi"
        )
        if bare_call or qualified_call:
            lines.append(node.lineno)
    return lines


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_routes_dir_exists() -> None:
    """Sanity: the routes directory must exist at the expected location."""
    assert _ROUTES_DIR.is_dir(), (
        f"Expected routes directory at {_ROUTES_DIR}. Did the package layout change?"
    )


def test_no_raw_apirouter_in_business_logic_routes() -> None:
    """Every non-exempt route module must avoid raw ``APIRouter``.

    Any raw ``APIRouter(...)`` construction in a non-exempt module is a
    regression: the module should use ``pat_router()`` or ``s2s_router()``
    from ``api.routes._security`` instead.
    """
    violations: list[tuple[str, int]] = []
    discovered_files: list[str] = []

    for path in _iter_route_module_files():
        rel = path.relative_to(_ROUTES_DIR).as_posix()
        discovered_files.append(rel)

        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        apirouter_lines = _find_apirouter_constructions(tree)

        if not apirouter_lines:
            continue

        if rel in EXEMPT_MODULES:
            # Exempt module: raw APIRouter is allowed. Do not record as a
            # violation. A separate test asserts the exemption list matches
            # the files that actually use raw APIRouter so the allowlist
            # does not drift.
            continue

        for lineno in apirouter_lines:
            violations.append((rel, lineno))

    assert not violations, (
        "Raw `APIRouter(...)` found in business-logic route modules. "
        "Use `pat_router()` or `s2s_router()` from "
        "`autom8_asana.api.routes._security` instead, OR add the module "
        "to `EXEMPT_MODULES` in this test with a justification. "
        f"Violations: {violations}. "
        f"Scanned files: {discovered_files}."
    )


def test_exemption_allowlist_matches_actual_raw_apirouter_users() -> None:
    """The exemption allowlist must not be stale.

    Every entry in ``EXEMPT_MODULES`` must correspond to a module that
    actually constructs a raw ``APIRouter``. If an exempt module is
    refactored to use ``SecureRouter``, its exemption entry should be
    removed so the allowlist tracks reality.
    """
    actual_raw_users: set[str] = set()
    for path in _iter_route_module_files():
        rel = path.relative_to(_ROUTES_DIR).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _find_apirouter_constructions(tree):
            actual_raw_users.add(rel)

    stale_exemptions = set(EXEMPT_MODULES.keys()) - actual_raw_users
    assert not stale_exemptions, (
        f"EXEMPT_MODULES contains stale entries: {sorted(stale_exemptions)}. "
        "These modules no longer use raw APIRouter and should be removed "
        "from the allowlist."
    )


def test_exemption_allowlist_coverage() -> None:
    """Documented belt-and-braces: at least the two known exemptions exist.

    This test fails loudly if the allowlist shrinks below its S2 baseline
    (health + webhooks), which would indicate either a refactor that
    obsoleted the exemption or an accidental deletion that silently broke
    the audit.
    """
    expected = {"health.py", "webhooks.py"}
    missing = expected - set(EXEMPT_MODULES.keys())
    assert not missing, (
        f"Expected EXEMPT_MODULES to include {sorted(expected)} as the S2 "
        f"baseline, but missing: {sorted(missing)}. If you intentionally "
        "removed an exemption (e.g., by migrating that file to SecureRouter), "
        "update this test's expected set to match."
    )
