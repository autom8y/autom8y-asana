"""Regression test for WS-B1: ``/api/v1/tags`` PAT auth middleware exclusion.

Origin: asana-mcp-postfelt-hardening / WS-B1 (TAG-1) satellite tags read
surface. Mirrors the DEF-08 / SCAR-WS8 pattern established by
``test_exports_auth_exclusion.py``.

Scar (SCAR-WS8): a NEW PAT route tree that is absent from
``jwt_auth_config.exclude_paths`` (``src/autom8_asana/api/main.py``) is rejected
by ``JWTAuthMiddleware`` BEFORE ``pat_router`` DI fires -- a silent 401 on the
load-bearing user/S2S path. The ``/api/v1/tags`` tree was added in the same
commit as its exclusion; this test prevents regression of that coupling.

It introspects the live middleware stack and asserts membership of the tags
prefix; it does NOT mock the middleware.
"""

from __future__ import annotations

import os

import pytest

# Match the env hygiene that ``test_exports_auth_exclusion.py`` uses: the fleet
# JWTAuthMiddleware production-URL guard requires an idempotency backend before
# ``create_app`` can build its middleware stack.
os.environ.setdefault("IDEMPOTENCY_STORE_BACKEND", "noop")

from autom8_asana.api.main import create_app


def _get_jwt_exclude_paths() -> list[str]:
    """Introspect the live middleware stack and return JWT exclude_paths."""
    app = create_app()
    for mw in app.user_middleware:
        if mw.cls.__name__ == "JWTAuthMiddleware":
            return list(mw.kwargs.get("exclude_paths", []))
    raise AssertionError(
        "JWTAuthMiddleware not found in app.user_middleware -- the asana app "
        "factory contract has changed; re-anchor this test against the new "
        "auth-middleware seam before disabling it."
    )


@pytest.mark.scar
def test_tags_route_tree_excluded_from_jwt_auth() -> None:
    """``/api/v1/tags/*`` MUST be in JWT exclude_paths (WS-B1 / SCAR-WS8).

    Without the exclusion, PAT- and S2S-JWT-authenticated requests to the tags
    surface are rejected with 401 before ``pat_router`` DI fires -- breaking
    the name->GID resolution the composite write path depends on.
    """
    exclude_paths = _get_jwt_exclude_paths()
    assert "/api/v1/tags/*" in exclude_paths, (
        "SCAR-WS8 regression: '/api/v1/tags/*' is missing from "
        "JWTAuthConfig.exclude_paths. PAT/S2S requests to the tags surface will "
        "be rejected with 401 before pat_router DI fires. Add the entry to "
        "src/autom8_asana/api/main.py near the other PAT-tag route trees "
        f"(tasks, projects, workspaces, exports). Currently configured: {exclude_paths!r}"
    )
