"""Drift guards for RE-2 write-class authorization.

Two structural guards, each proved in BOTH polarities (a guard that cannot fail
is not a guard):

**GUARD-1 — coverage.** Every route that DECLARES an Asana side effect must
carry a write-authz dependency. This closes UV-P-5 of the design structurally
rather than by hand:

    "[UV-P: no route outside the five enumerated write classes reaches an Asana
     write through a path this review did not trace ...]"

That UV-P returned NOT NULL during this build. The design enumerated five write
classes across six routes; the derived sweep found **26** declared
`asana_api` side-effect routes. Hand-enumeration was the wrong instrument. The
guard below derives the write surface from the same declaration the routes
already publish, so a future write route that forgets the gate fails CI instead
of silently joining the unauthorized surface.

Known limitation, stated rather than papered over: the guard trusts
`x-fleet-side-effects`. A route that performs an Asana write WITHOUT declaring
one is invisible to it. That residual is carried as UV-P-S14-1 in the receipt —
it is narrower than the hand-enumeration it replaces, not zero.

**GUARD-2 — axis ban.** The `has_scope` / `require_scope` family must never
appear in `src/`. Per CORRECTION-3 those primitives short-circuit True on
`scope == "*"` (`autom8y_auth/claims.py:220-222`), so a write gate built on them
is fail-open. The fleet auth service documents the same hazard and routes around
it (`services/auth/service-accounts.yaml:682-683`). The ban makes the axis ruling
durable: a later contributor cannot quietly reintroduce the fail-open axis.
"""

from __future__ import annotations

import ast
import pathlib
import re
from typing import Any, NamedTuple

import pytest
from fastapi.routing import APIRoute

SRC = pathlib.Path(__file__).resolve().parents[3] / "src"


# ---------------------------------------------------------------------------
# GUARD-1 — every declared Asana write route carries the gate
# ---------------------------------------------------------------------------


class RouteFacts(NamedTuple):
    """The two facts the coverage predicate needs, decoupled from FastAPI."""

    name: str
    declares_asana_write: bool
    has_write_authz_dep: bool


def ungated_write_routes(routes: list[RouteFacts]) -> list[str]:
    """Return the names of routes that declare an Asana write but carry no gate.

    Pure function so the guard can be exercised against synthetic input — which
    is what lets the test below prove the guard actually discriminates.
    """
    return [r.name for r in routes if r.declares_asana_write and not r.has_write_authz_dep]


def _declares_asana_write(route: APIRoute) -> bool:
    extra: dict[str, Any] = getattr(route, "openapi_extra", None) or {}
    effects = extra.get("x-fleet-side-effects") or []
    return any(isinstance(e, dict) and e.get("type") == "asana_api" for e in effects)


def _has_write_authz_dep(route: APIRoute) -> bool:
    return any(
        "write_authz" in getattr(d.dependency, "__name__", "") for d in (route.dependencies or [])
    )


@pytest.fixture(scope="module")
def real_route_facts() -> list[RouteFacts]:
    """Facts derived from the REAL application, not a fixture of one."""
    from autom8_asana.api.main import create_app

    app = create_app()
    return [
        RouteFacts(
            name=f"{sorted(r.methods or [])} {r.path}",
            declares_asana_write=_declares_asana_write(r),
            has_write_authz_dep=_has_write_authz_dep(r),
        )
        for r in app.routes
        if isinstance(r, APIRoute)
    ]


class TestGuard1WriteRouteCoverage:
    def test_green_every_declared_asana_write_route_is_gated(
        self, real_route_facts: list[RouteFacts]
    ) -> None:
        ungated = ungated_write_routes(real_route_facts)
        assert ungated == [], (
            "Asana write routes reachable without write-class authorization "
            f"(RE-2/SEC-001 regression): {ungated}"
        )

    def test_the_write_surface_is_non_empty(self, real_route_facts: list[RouteFacts]) -> None:
        """Anti-vacuity: a guard over an empty set passes trivially.

        Without this, deleting `x-fleet-side-effects` everywhere would turn
        GUARD-1 green while removing all protection — an unearned GREEN of
        exactly the kind this build is meant to refuse.
        """
        declared = [r for r in real_route_facts if r.declares_asana_write]
        assert len(declared) >= 26, (
            f"expected >=26 declared Asana write routes, found {len(declared)}"
        )

    def test_red_guard_trips_on_a_synthetic_ungated_write_route(self) -> None:
        """RED teeth: the guard must FAIL when a write route loses its gate.

        Exercised against synthetic input — no defect is injected into
        production code (that would be G-THEATER). The fixture is deliberately
        broken; the guard must correctly reject it.
        """
        synthetic = [
            RouteFacts("POST /gated", declares_asana_write=True, has_write_authz_dep=True),
            RouteFacts("POST /forgotten", declares_asana_write=True, has_write_authz_dep=False),
            RouteFacts("GET /read", declares_asana_write=False, has_write_authz_dep=False),
        ]
        assert ungated_write_routes(synthetic) == ["POST /forgotten"]

    def test_red_guard_does_not_trip_on_reads(self) -> None:
        """Discrimination: the guard must not demand gates on read routes."""
        synthetic = [
            RouteFacts("GET /a", declares_asana_write=False, has_write_authz_dep=False),
            RouteFacts("GET /b", declares_asana_write=False, has_write_authz_dep=False),
        ]
        assert ungated_write_routes(synthetic) == []


# ---------------------------------------------------------------------------
# GUARD-2 — the fail-open axis stays out of src/
# ---------------------------------------------------------------------------

# Matches attribute/call use of the wildcard-bearing scope predicates. Written
# to catch `claims.has_scope(...)`, `require_scope(...)`, and imports thereof.
FAIL_OPEN_AXIS = re.compile(r"\b(has_scope|require_scope)\b")

# The axis ruling is ABOUT these primitives, so the module that documents it and
# the tests that pin the upstream hazard must be allowed to name them.
AXIS_BAN_EXEMPT = {"write_authz.py"}


def _docstring_lines(text: str) -> set[int]:
    """Line numbers occupied by module/class/function docstrings.

    The ban is on CODE that calls the refused primitives, not on PROSE that
    explains why they are refused — the axis ruling has to be documentable at
    the sites it governs. Docstrings are located structurally via AST rather
    than by regex, so this exemption cannot be abused: a real `has_scope(...)`
    call is never a docstring node.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:  # pragma: no cover - scanned sources must parse
        return set()
    covered: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None) or []
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                covered.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return covered


def fail_open_axis_hits(sources: dict[str, str]) -> list[str]:
    """Return "path:line" for every use of the refused scope axis.

    Pure over a {path: source} mapping so the guard can be run against synthetic
    input and shown to discriminate.
    """
    hits: list[str] = []
    for path, text in sorted(sources.items()):
        if pathlib.Path(path).name in AXIS_BAN_EXEMPT:
            continue
        skip = _docstring_lines(text)
        for lineno, line in enumerate(text.split("\n"), 1):
            if lineno in skip or line.strip().startswith("#"):
                continue
            if FAIL_OPEN_AXIS.search(line):
                hits.append(f"{path}:{lineno}")
    return hits


class TestGuard2FailOpenAxisBan:
    def test_green_src_does_not_use_the_fail_open_scope_axis(self) -> None:
        sources = {str(p.relative_to(SRC)): p.read_text() for p in SRC.rglob("*.py")}
        assert sources, "no sources scanned — guard would be vacuous"
        hits = fail_open_axis_hits(sources)
        assert hits == [], (
            "has_scope/require_scope reintroduced into src/. These short-circuit "
            "True on scope == '*' (autom8y_auth/claims.py:220-222) and are "
            "fail-open for authorization. Use the identity allowlist "
            "(api/write_authz.py) or has_permission_no_wildcard instead. "
            f"Hits: {hits}"
        )

    def test_red_guard_trips_on_synthetic_has_scope_use(self) -> None:
        """RED teeth: the ban must FAIL when the refused axis appears."""
        synthetic = {
            "routes/evil.py": (
                "def gate(claims):\n"
                "    if not claims.has_scope('asana:write'):\n"
                "        raise Forbidden\n"
            )
        }
        assert fail_open_axis_hits(synthetic) == ["routes/evil.py:2"]

    def test_red_guard_trips_on_require_scope_dependency(self) -> None:
        synthetic = {"routes/evil.py": "from autom8y_auth import require_scope\n"}
        assert fail_open_axis_hits(synthetic) == ["routes/evil.py:1"]

    def test_docstring_exemption_is_not_a_bypass(self) -> None:
        """The prose exemption must not shelter an adjacent real call.

        GUARD-2 skips docstring lines so the axis ruling can be documented at
        the sites it governs. That exemption would be a hole if a call could
        hide behind a docstring in the same function — it cannot.
        """
        synthetic = {
            "routes/sneaky.py": (
                "def gate(claims):\n"
                '    """We must never use has_scope here — it is fail-open."""\n'
                "    return claims.has_scope('asana:write')\n"
            )
        }
        assert fail_open_axis_hits(synthetic) == ["routes/sneaky.py:3"]

    def test_guard_does_not_trip_on_the_safe_axis(self) -> None:
        """Discrimination: `has_permission` is the SAFE axis and must pass."""
        synthetic = {
            "routes/good.py": (
                "def gate(claims):\n"
                "    if not claims.has_permission('asana:write'):\n"
                "        raise Forbidden\n"
            )
        }
        assert fail_open_axis_hits(synthetic) == []
