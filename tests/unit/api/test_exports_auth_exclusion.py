"""Regression test for DEF-08: ``/api/v1/exports`` PAT auth middleware exclusion.

Origin: review rite Phase 1.1 remediation (R-1) per
``.ledge/handoffs/HANDOFF-review-to-10xdev-2026-04-28.md`` §3 Item R-1.

Defect (DEF-08): ``/api/v1/exports`` was absent from
``jwt_auth_config.exclude_paths`` at ``src/autom8_asana/api/main.py:381-388``.
Without exclusion, the JWT middleware rejects PAT-authenticated requests
before ``pat_router`` DI fires — producing a silent 401 on the load-bearing
user path that Vince and every future caller depend on.

Patch: add ``/api/v1/exports/*`` to the PAT-tag route-tree exclusion list,
co-located with neighboring PAT routes (``/api/v1/dataframes/*``,
``/api/v1/offers/*``, etc.).

This test exists to prevent regression of the exact bug class (new PAT
route landed without an exclude_paths entry). It introspects the live
middleware stack and asserts membership of the exports prefix; it does
NOT mock the middleware. Per scar-tissue scope SCAR-WS8, exclude_paths
sync with router registration is a structural invariant.
"""

from __future__ import annotations

import os
import pytest

# Match the env hygiene that ``tests/test_openapi_endpoint.py`` uses: the
# fleet JWTAuthMiddleware production-URL guard requires an idempotency
# backend before ``create_app`` can build its middleware stack.
os.environ.setdefault("IDEMPOTENCY_STORE_BACKEND", "noop")

from autom8_asana.api.main import create_app


def _get_jwt_exclude_paths() -> list[str]:
    """Introspect the live middleware stack and return JWT exclude_paths.

    The asana app factory registers ``JWTAuthMiddleware`` via
    ``create_fleet_app(... jwt_auth=jwt_auth_config)``. The middleware ends
    up in ``app.user_middleware`` with its kwargs (including
    ``exclude_paths``) preserved. Reading from the live app is the truthy
    source — it survives any future refactor of how ``jwt_auth_config``
    is constructed inside ``create_app``.
    """
    app = create_app()
    for mw in app.user_middleware:
        if mw.cls.__name__ == "JWTAuthMiddleware":
            return list(mw.kwargs.get("exclude_paths", []))
    raise AssertionError(
        "JWTAuthMiddleware not found in app.user_middleware — the asana "
        "app factory contract has changed; re-anchor this test against "
        "the new auth-middleware seam before disabling it."
    )


@pytest.mark.scar
def test_exports_route_tree_excluded_from_jwt_auth() -> None:
    """``/api/v1/exports/*`` MUST be in JWT exclude_paths (DEF-08 regression).

    R-1 acceptance criterion AC-R1-3: structural test asserting
    ``/api/v1/exports`` membership in the exclude_paths set.
    """
    exclude_paths = _get_jwt_exclude_paths()
    assert "/api/v1/exports/*" in exclude_paths, (
        "DEF-08 regression: '/api/v1/exports/*' is missing from "
        "JWTAuthConfig.exclude_paths. PAT-authenticated requests to the "
        "exports surface will be rejected with 401 before pat_router DI "
        "fires. Add the entry to src/autom8_asana/api/main.py near the "
        "other PAT-tag route trees (dataframes, offers, tasks, projects). "
        f"Currently configured: {exclude_paths!r}"
    )


@pytest.mark.scar
def test_pat_route_trees_co_excluded_consistently() -> None:
    """Every PAT-tag route tree present in the app must be JWT-excluded.

    This is the broader scar-tissue invariant (SCAR-WS8): exclude_paths
    must stay in sync with PAT-tagged router registrations. Asserting all
    expected PAT route trees co-exist as exclusions catches the regression
    pattern at the *family* level, not just the single missing entry that
    R-1 closes.
    """
    exclude_paths = _get_jwt_exclude_paths()
    expected_pat_route_trees = {
        "/api/v1/tasks/*",
        "/api/v1/projects/*",
        "/api/v1/sections/*",
        "/api/v1/users/*",
        "/api/v1/workspaces/*",
        "/api/v1/dataframes/*",
        "/api/v1/offers/*",
        "/api/v1/exports/*",
    }
    missing = expected_pat_route_trees - set(exclude_paths)
    assert not missing, (
        f"PAT-tag route trees missing from JWT exclude_paths: {sorted(missing)}. "
        f"Each missing entry produces silent 401s on PAT-authenticated "
        f"requests. Add to src/autom8_asana/api/main.py exclude_paths list."
    )
