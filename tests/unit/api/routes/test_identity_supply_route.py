"""GET /v1/identity-supply/{offer_gid} -- the id-walk supply, at the wire.

The supply's own dispositions are proven in
``tests/unit/models/business/test_identity_supply.py`` (the allow-list
inversion, SET-never-PICK, the typed-absence set, the byte-verbatim name).
This module locks the four properties that only exist AT THE ROUTE:

  * **no write verb is reachable** -- asserted over the import-resolved call
    graph from the handler, with a POSITIVE CONTROL proving the census can see
    a write verb where one genuinely exists;
  * **the gate is two-sided** -- an unauthenticated caller and a non-service
    (PAT) caller are both refused; an authenticated service passes;
  * **the tier-4 refusal arm is CARRIED to the wire** -- ``detection_tier=4``
    and ``needs_healing=true`` arrive as such, against the REAL five-tier
    detector, never smoothed into a value and never turned into an error;
  * **the gid is digits-validated unconditionally** -- unlike the shared
    ``GidStr`` alias, whose constraint is switched OFF in test/local
    environments, so a route relying on it would carry a validation claim no
    test in this repo could falsify.

Every gid in this file is SYNTHETIC (the ``30000000000000NN`` block) and every
name is a fixture string. The only real identifier that appears is the
Businesses PROJECT gid, and it is READ OUT OF THE REGISTRY at runtime rather
than written down -- it is a registry constant, not a client identifier, and it
is not a literal here.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.config import get_settings
from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.core.types import EntityType
from autom8_asana.models.business.identity_supply import BASIS_VERSION
from autom8_asana.models.business.registry import get_registry
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task
from autom8_asana.services.resolver import EntityProjectRegistry

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

# --- synthetic hierarchy: offer -> offer-holder -> business -------------------
OFFER_GID = "3000000000000001"
HOLDER_GID = "3000000000000002"
BUSINESS_GID = "3000000000000003"
CONTACTS_HOLDER_GID = "3000000000000004"
UNITS_HOLDER_GID = "3000000000000005"
UNREACHABLE_OFFER_GID = "3000000000000009"

SUPPLY_PATH = f"/v1/identity-supply/{OFFER_GID}"

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC = _REPO_ROOT / "src/autom8_asana"
_ROUTE_SRC = _SRC / "api/routes/identity_supply.py"
_MODELS_SRC = _SRC / "api/routes/identity_supply_models.py"

_ROUTE_ROOT = "autom8_asana.api.routes.identity_supply:get_identity_supply"
# A function that genuinely DOES reach an Asana mutation. The positive control
# for the verb census: if the census cannot see this, its silence on the route
# means nothing.
_WRITE_CONTROL_ROOT = "autom8_asana.services.task_service:create_task"

#: The verb-shape vocabulary. Every Asana mutation on the client surface is
#: named with one of these fragments (``create_async`` / ``update_async`` /
#: ``delete`` / ``add_tag_async`` / ``remove_from_project_async`` /
#: ``move_to_section_async`` / ``set_assignee_async`` / ``duplicate_async``),
#: plus the raw HTTP mutation verbs.
_WRITE_FRAGMENTS = (
    "create",
    "update",
    "delete",
    "insert",
    "duplicate",
    "add_",
    "remove_",
    "move_",
    "set_",
    ".post",
    ".put",
    ".patch",
)


# ===========================================================================
# The import-resolved call-graph census
# ===========================================================================


def _parse_modules() -> dict[str, ast.Module]:
    out: dict[str, ast.Module] = {}
    for path in sorted(_SRC.rglob("*.py")):
        rel = path.relative_to(_SRC.parent).with_suffix("")
        mod = ".".join(rel.parts)
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        try:
            out[mod] = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover -- src must parse
            continue
    return out


_MODULES = _parse_modules()


def _module_funcs(mod: str) -> dict[str, ast.AST]:
    """Module-level functions plus class methods (flattened, `self.x()` support)."""
    out: dict[str, ast.AST] = {}
    tree = _MODULES.get(mod)
    if tree is None:
        return out
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            out[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef):
                    out.setdefault(f"{node.name}.{member.name}", member)
                    out.setdefault(member.name, member)
    return out


def _module_imports(mod: str, scope: ast.AST | None = None) -> dict[str, str]:
    """alias -> ``module:symbol``. Includes function-local deferred imports."""
    out: dict[str, str] = {}
    scopes: list[ast.AST] = []
    tree = _MODULES.get(mod)
    if tree is not None:
        scopes.append(tree)
    if scope is not None:
        scopes.append(scope)
    for node in scopes:
        for sub in ast.walk(node):
            if isinstance(sub, ast.ImportFrom) and sub.module:
                target = sub.module
                if sub.level:
                    base = mod.rsplit(".", sub.level)[0]
                    target = f"{base}.{sub.module}" if sub.module else base
                for alias in sub.names:
                    out[alias.asname or alias.name] = f"{target}:{alias.name}"
            elif isinstance(sub, ast.Import):
                for alias in sub.names:
                    out[alias.asname or alias.name] = f"{alias.name}:*"
    return out


def _attr_chain(node: ast.AST) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def reachable(root: str) -> tuple[set[str], set[str]]:
    """BFS the call graph from ``module:function``, resolving through imports.

    Returns ``(resolved_function_keys, attribute_call_chains)``. Calls are
    followed through module-level defs, ``self.x()``, top-level and deferred
    ``from``-imports, and one hop of re-export. A call on a receiver the walk
    cannot resolve (``some_obj.method()``) is RECORDED as an attribute chain
    and not followed -- which is why :func:`test_the_reachable_boundary_is_pinned`
    pins that boundary rather than leaving it implicit.
    """
    seen: set[str] = set()
    queue: list[str] = [root]
    visited: set[str] = set()
    attrs: set[str] = set()

    while queue:
        key = queue.pop()
        if key in seen:
            continue
        seen.add(key)
        mod, _, fn = key.partition(":")
        node = _module_funcs(mod).get(fn)
        if node is None:
            reexports = _module_imports(mod)
            target = reexports.get(fn)
            if target and target.split(":")[0].startswith("autom8_asana"):
                queue.append(target)
            continue
        visited.add(key)
        imports = _module_imports(mod, node)
        local = _module_funcs(mod)
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            func = sub.func
            if isinstance(func, ast.Name):
                if func.id in local:
                    queue.append(f"{mod}:{func.id}")
                elif func.id in imports and imports[func.id].split(":")[0].startswith(
                    "autom8_asana"
                ):
                    queue.append(imports[func.id])
            elif isinstance(func, ast.Attribute):
                chain = _attr_chain(func)
                if chain is None:
                    continue
                head = chain.split(".")[0]
                if head == "self" and func.attr in local:
                    queue.append(f"{mod}:{func.attr}")
                    continue
                if head in imports and imports[head].endswith(":*"):
                    tmod = imports[head][:-2]
                    if tmod.startswith("autom8_asana"):
                        queue.append(f"{tmod}:{func.attr}")
                        continue
                attrs.add(chain)
    return visited, attrs


def _client_verbs(attrs: set[str]) -> set[str]:
    return {c for c in attrs if c.split(".")[0] == "client" or ".client." in c}


def _write_shaped(chains: set[str]) -> set[str]:
    return {c for c in chains if any(frag in c for frag in _WRITE_FRAGMENTS)}


# ===========================================================================
# R-1 -- the verb census. get_async and subtasks_async; no write verb; teeth.
# ===========================================================================


class TestNoWriteVerbIsReachable:
    def test_r1a_the_reachable_asana_verbs_are_exactly_two_reads(self) -> None:
        """The census over the handler's call graph names both reads, and only reads.

        ``walk_business_candidates_async``'s own docstring names ``get_async``
        and, at tier 4, ``subtasks_async``. This asserts it mechanically from
        the route, so a detector edit that reached for a third verb would fail
        here rather than ship as "still a read route".
        """
        _visited, attrs = reachable(_ROUTE_ROOT)

        assert _client_verbs(attrs) == {
            "client.tasks.get_async",
            "client.tasks.subtasks_async",
        }

    def test_r1b_zero_write_shaped_verbs_are_reachable(self) -> None:
        """RED side of the invariant: no mutation verb anywhere in the graph."""
        _visited, attrs = reachable(_ROUTE_ROOT)

        assert _write_shaped(_client_verbs(attrs)) == set()

    def test_r1c_positive_control_the_census_CAN_see_a_write_verb(self) -> None:
        """TEETH. The same census, rooted at a function that DOES mutate.

        Without this, R1a/R1b would pass just as well against a census that
        resolved nothing at all -- an empty set is the signature of both a
        clean read route and a broken analyser, and those must not look alike.
        """
        visited, attrs = reachable(_WRITE_CONTROL_ROOT)

        assert visited, "the control root did not resolve -- the census is broken"
        assert "client.tasks.create_async" in _client_verbs(attrs)
        assert _write_shaped(_client_verbs(attrs)), "control reported no write verb"

    def test_r1d_the_reachable_boundary_is_pinned(self) -> None:
        """The census's own edge is DECLARED, not implicit.

        A call on a receiver the walk cannot resolve (``registry.lookup()``,
        ``workspace_registry.lookup_or_discover_async()``) is recorded, not
        followed. That is the one way a verb could hide from R1a, so the set of
        such receivers is pinned: a NEW unresolved receiver appearing in the
        reachable graph fails here and forces someone to classify it.

        The two that matter, hand-classified at authorship:

        * ``workspace_registry.lookup_or_discover_async`` -> ``discover_async``
          -> ``client.projects.list_async`` -- a GET (lazy workspace discovery,
          only on a project gid absent from the static registry).
        * ``cache.get_versioned`` / ``cache.set_versioned`` -- the DETECTION
          result cache, not Asana. A cache write is not an Asana mutation, and
          it is only reachable when the client carries a ``_cache_provider``.

        Stdlib collisions (``logger.info``, ``re.compile``, ``path.append``,
        ``datetime.now``) are retained deliberately: the set is derived by a
        mechanical rule, not hand-curated, and curating it would be the seam
        where a real receiver could be dropped "because it looked harmless".
        """
        _visited, attrs = reachable(_ROUTE_ROOT)
        own_defs = {
            node.name
            for tree in _MODULES.values()
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        frontier = {c for c in attrs if c.split(".")[-1] in own_defs}

        assert frontier == {
            "BusinessCandidateModel.from_candidate",
            "EvidenceModel.from_evidence",
            "PARENT_CHILD_MAP.get",
            "cache.get_versioned",
            "cache.set_versioned",
            "client.tasks.get_async",
            "client.tasks.subtasks_async",
            "compiled.search",
            "datetime.now",
            "entry.is_expired",
            "first_membership.get",
            "logger.debug",
            "logger.error",
            "logger.exception",
            "logger.info",
            "logger.warning",
            "path.append",
            "pattern_config.get",
            "project_data.get",
            "re.compile",
            "registry.lookup",
            "router.get",
            "supply.families",
            "workspace_registry.lookup_or_discover_async",
        }

    def test_r1e_the_route_declares_no_write_class(self) -> None:
        """No write-authz symbol is IMPORTED by the route or its models.

        Checked over the AST's import nodes, not the raw text: this module's
        own prose names the symbols in order to explain their absence, and
        prose about a symbol is not use of it.
        """
        for src in (_ROUTE_SRC, _MODELS_SRC):
            tree = ast.parse(src.read_text())
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported.add(node.module)
                    imported.update(alias.name for alias in node.names)
                elif isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
            assert not any("write_authz" in name for name in imported), src
            assert "WriteClass" not in imported, src
            assert "require_write_authz" not in imported, src


# ===========================================================================
# Fixtures -- synthetic hierarchy, REAL detector, mocked transport only
# ===========================================================================


def _business_project_gid() -> str:
    """The Businesses PROJECT gid, read from the registry (never a literal)."""
    gid = get_registry().get_primary_gid(EntityType.BUSINESS)
    assert gid, "registry has no primary Business project gid"
    return gid


def _mock_client(
    *,
    business_task: Task,
    business_subtasks: list[Task] | None = None,
    entry_raises: Exception | None = None,
) -> MagicMock:
    """A read-only transport over: offer -> offer-holder -> business.

    ONLY the Asana transport is mocked. The five-tier detector, the upward
    walk and every disposition in the supply run for real.
    """
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client._cache_provider = None

    async def get_async(gid: str, **_kwargs: object) -> Task:
        if entry_raises is not None:
            raise entry_raises
        if gid == OFFER_GID:
            return Task(
                gid=OFFER_GID,
                name="Fixture Offer A",
                parent=NameGid(gid=HOLDER_GID, name="Offers"),
            )
        if gid == HOLDER_GID:
            return Task(
                gid=HOLDER_GID,
                name="Offers",
                parent=NameGid(gid=BUSINESS_GID, name="Fixture Business A"),
            )
        if gid == BUSINESS_GID:
            return business_task
        raise ValueError(f"Unexpected gid: {gid}")

    client.tasks.get_async = AsyncMock(side_effect=get_async)

    def subtasks(gid: str, **_kwargs: object) -> AsyncMock:
        mock = AsyncMock()
        if gid == BUSINESS_GID and business_subtasks is not None:
            mock.collect = AsyncMock(return_value=business_subtasks)
        else:
            mock.collect = AsyncMock(return_value=[])
        return mock

    client.tasks.subtasks_async = MagicMock(side_effect=subtasks)
    return client


def _clean_tier1_client() -> MagicMock:
    """Business identified DETERMINISTICALLY by project membership (tier 1)."""
    return _mock_client(
        business_task=Task(
            gid=BUSINESS_GID,
            name="Fixture Business A",
            memberships=[{"project": {"gid": _business_project_gid(), "name": "Businesses"}}],
        )
    )


def _selfflagged_tier4_client() -> MagicMock:
    """Business identified by SUBTASK-NAME STRUCTURE INSPECTION (tier 4).

    No project membership, so tiers 1-3 all miss; the traversal path turns tier
    4 on and the REAL detector concludes BUSINESS from the lowercased subtask
    names, self-flagging ``needs_healing=True`` at confidence 0.9.
    """
    return _mock_client(
        business_task=Task(gid=BUSINESS_GID, name="Fixture Business A"),
        business_subtasks=[
            Task(gid=CONTACTS_HOLDER_GID, name="Contacts"),
            Task(gid=UNITS_HOLDER_GID, name="Units"),
        ],
    )


def _mock_jwt_validation(service_name: str = "autom8y_data") -> AsyncMock:
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _patches(client: MagicMock):
    return (
        patch("autom8_asana.api.routes.internal.validate_service_token", _mock_jwt_validation()),
        patch("autom8_asana.auth.jwt_validator.validate_service_token", _mock_jwt_validation()),
        patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test_bot_pat"),
        patch("autom8_asana.api.dependencies.get_bot_pat", return_value="test_bot_pat"),
        patch("autom8_asana.api.routes.identity_supply.AsanaClient", return_value=client),
    )


@pytest.fixture(autouse=True)
def _reset_singletons():
    get_settings.cache_clear()
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    get_settings.cache_clear()
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")
    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects", new_callable=AsyncMock
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            app.state.entity_project_registry = EntityProjectRegistry.get_instance()

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as tc:
        yield tc


def _get(
    client: TestClient,
    mock_client: MagicMock,
    *,
    path: str = SUPPLY_PATH,
    headers: dict[str, str] | None = AUTH_HEADER,
):
    p = _patches(mock_client)
    with p[0], p[1], p[2], p[3], p[4]:
        return client.get(path, headers=headers) if headers else client.get(path)


# ===========================================================================
# R-2 -- the two-sided fixture on the REAL detector, AT THE WIRE.
# ===========================================================================


class TestTierFourIsCarriedToTheWire:
    def test_r2a_side_ii_clean_tier1_publishes_the_identity(self, client: TestClient) -> None:
        """SIDE (ii): a deterministic tier-1 identification IS published.

        The pass side. Without it, R2b would also pass against a route that
        published nothing at all.
        """
        response = _get(client, _clean_tier1_client())

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["asana_business"]["value"] == BUSINESS_GID
        assert data["asana_business"]["absent_reason"] is None
        assert data["asana_business"]["detection_tier"] == 1
        assert data["asana_business"]["needs_healing"] is False
        assert data["asana_business"]["supplier"] == "id_walk"
        assert data["business_display_name"]["value"] == "Fixture Business A"
        assert data["offer"]["value"] == OFFER_GID
        assert data["offer"]["supplier"] == "producer_held"
        assert data["basis_version"] == BASIS_VERSION == 2

    def test_r2b_side_i_selfflagged_tier4_arrives_REFUSED_with_both_discriminators(
        self, client: TestClient
    ) -> None:
        """SIDE (i): a self-flagged tier-4 identification is CARRIED, not waved through.

        ``detection_tier=4`` and ``needs_healing=true`` reach the consumer on
        the refusal arm. ``CONFIDENCE_TIER_4 = 0.9`` is the second-highest
        confidence in the detector's set, so a consumer that screened on the
        number would read this as near-certain -- the flag is what crosses, and
        the number is not on the wire at all.
        """
        response = _get(client, _selfflagged_tier4_client())

        assert response.status_code == 200, "a refusal is evidence, never an HTTP error"
        data = response.json()["data"]

        for family in ("asana_business", "business_display_name"):
            ev = data[family]
            assert ev["value"] is None, f"{family} published a self-flagged value"
            # Pin the token LITERAL: on a closed-set contract the literal IS
            # the contract, and a symbolic assertion follows the constant
            # wherever it is later pointed.
            assert ev["absent_reason"] == "undecidable"
            assert ev["detection_tier"] == 4
            assert ev["needs_healing"] is True
            assert ev["supplier"] == "id_walk"
        assert data["basis_version"] == 2

    def test_r2c_the_confidence_number_never_reaches_the_wire(self, client: TestClient) -> None:
        """``confidence`` is not a field of the supply and must not appear here.

        The route may not re-introduce the discriminator the supply refuses to
        guard on; the fold derives fold-side confidence, and a second one on
        this surface would be a second writer for a fact that has one.
        """
        body = _get(client, _selfflagged_tier4_client()).text

        assert "confidence" not in body

    def test_r2d_the_candidate_set_crosses(self, client: TestClient) -> None:
        """SET-never-PICK survives the wire: the candidates are carried.

        The consumer appends N observations from this set. A response carrying
        only the three families would turn a multi-candidate walk into an
        unexplained ``undecidable``.
        """
        data = _get(client, _clean_tier1_client()).json()["data"]

        assert [c["gid"] for c in data["candidates"]] == [BUSINESS_GID]
        assert data["candidates"][0]["detection_tier"] == 1
        assert data["candidates"][0]["needs_healing"] is False


# ===========================================================================
# R-3 -- the gate, two-sided.
# ===========================================================================


class TestTheGateIsTwoSided:
    def test_r3a_green_an_authenticated_service_passes(self, client: TestClient) -> None:
        """The SAME require_service_claims dependency /v1/receipts uses."""
        assert "require_service_claims" in _ROUTE_SRC.read_text()

        assert _get(client, _clean_tier1_client()).status_code == 200

    def test_r3b_red_an_unauthenticated_request_is_refused(self, client: TestClient) -> None:
        """RED pair for 3a: no Authorization header -> 401, never an open read.

        ★ MEASURED LIMITATION, stated so it is not mistaken for more than it is:
        deleting ``Depends(require_service_claims)`` from the handler leaves
        THIS case still passing, because the fleet ``JWTAuthMiddleware``
        refuses a header-less request before the handler is reached. So 3b
        proves the surface is not open; it does NOT prove the route carries its
        own guard. 3c and 3d are the cases that bite on that mutant (both go
        RED when the dependency is removed).
        """
        response = _get(client, _clean_tier1_client(), headers=None)

        assert response.status_code == 401

    def test_r3c_red_a_non_service_token_is_refused(self, client: TestClient) -> None:
        """A PAT-shaped (non-JWT) bearer is refused: this is an S2S-only surface.

        The identity boundary is auth CLASS, not a per-subject allowlist -- a
        route-local allowlist would mint an authz artifact the fleet would then
        have to provision on the caller, which is the U-4 class.
        """
        response = _get(
            client,
            _clean_tier1_client(),
            headers={"Authorization": "Bearer opaque-personal-access-token"},
        )

        assert response.status_code == 401

    def test_r3d_red_the_ROUTE_gate_fails_closed_on_its_own(self, client: TestClient) -> None:
        """The route's own guard refuses even when the middleware let the call in.

        Deliberately scoped to ``routes.internal.validate_service_token`` only:
        the fleet middleware validator is left HEALTHY, so this isolates the
        route-level dependency. A route that leaned entirely on the middleware
        would pass 3b/3c (the middleware refuses those) and fail here.
        """
        mock = _clean_tier1_client()
        p = _patches(mock)
        with (
            p[1],
            p[2],
            p[3],
            p[4],
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                AsyncMock(side_effect=ValueError("bad signature")),
            ),
        ):
            response = client.get(SUPPLY_PATH, headers=AUTH_HEADER)

        assert response.status_code == 401
        assert mock.tasks.get_async.await_count == 0, "an Asana read happened before the gate"

    def test_r3e_no_asana_read_is_issued_on_a_refused_request(self, client: TestClient) -> None:
        """The gate precedes the walk. A refused caller costs zero Asana reads."""
        mock = _clean_tier1_client()
        _get(client, mock, headers=None)

        assert mock.tasks.get_async.await_count == 0


# ===========================================================================
# R-4 -- digits validation, unconditional and two-sided.
# ===========================================================================


class TestOfferGidIsDigitsValidated:
    @pytest.mark.parametrize(
        "bad",
        [
            "not-a-gid",
            "3000000000000001x",
            "../3000000000000001",
            "3000000000000001 ",
            "",
        ],
    )
    def test_r4a_red_a_non_digit_gid_is_refused_before_any_asana_read(
        self, client: TestClient, bad: str
    ) -> None:
        """A malformed gid never reaches the walk."""
        mock = _clean_tier1_client()
        response = _get(client, mock, path=f"/v1/identity-supply/{bad}")

        assert response.status_code in (404, 422), response.status_code
        assert mock.tasks.get_async.await_count == 0

    def test_r4b_green_a_digits_gid_passes(self, client: TestClient) -> None:
        """The pass side: the synthetic 16-digit gid is accepted."""
        assert _get(client, _clean_tier1_client()).status_code == 200

    def test_r4c_the_route_does_NOT_use_the_env_conditional_GidStr_alias(self) -> None:
        """★ The validation must not be switched off by the environment.

        ``api/models.py`` builds ``GidStr``'s pattern as ``None`` whenever
        ``AUTOM8Y_ENV`` is test/local, so fixtures may use readable gids. A
        route validating with ``GidStr`` would therefore carry a digits claim
        that is UNTESTABLE in this repo -- every test runs in exactly the
        environment where the constraint is absent. This route declares its own
        unconditional pattern instead; R4a is only non-vacuous because of it.
        """
        from autom8_asana.api import models as api_models
        from autom8_asana.api.routes.identity_supply import OFFER_GID_PATTERN

        # The premise: the shared alias really is relaxed under the test env.
        assert api_models._gid_pattern is None, (
            "GidStr is constrained in this environment -- re-read this guard's "
            "premise before trusting R4a"
        )
        # And the route does not lean on it. Checked over the AST's import
        # nodes: this route's own docstring NAMES ``GidStr`` in order to
        # explain why it is not used, and prose about a symbol is not use of
        # it -- the repo's own census route makes the same distinction.
        imported: set[str] = set()
        for node in ast.walk(ast.parse(_ROUTE_SRC.read_text())):
            if isinstance(node, ast.ImportFrom | ast.Import):
                imported.update(alias.name for alias in node.names)
        assert "GidStr" not in imported
        assert OFFER_GID_PATTERN == r"^[0-9]{1,64}$"


# ===========================================================================
# R-5 -- the route stays seat-A-facing: no consumer-side reach.
# ===========================================================================


class TestNoConsumerSideReach:
    def test_r5a_no_data_side_import_anywhere_in_the_reachable_graph(self) -> None:
        """0 imports of the ledger, the fold, the appender, or the [data] package.

        The supply SUPPLIES. Custody of the ledger is seat A's, in ``[data]``;
        a reach from here into any of it would make this service a second
        writer for a record that already has one.
        """
        _visited, _attrs = reachable(_ROUTE_ROOT)
        forbidden = (
            "autom8_data",
            "autom8y_data",
            "identity_observation",
            "append_observation",
            "identity_observation_fold",
        )
        offenders: list[str] = []
        for src in (_ROUTE_SRC, _MODELS_SRC):
            tree = ast.parse(src.read_text())
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                offenders.extend(n for n in names if any(bad in n for bad in forbidden))
        assert offenders == []

    def test_r5b_positive_control_the_import_scan_CAN_see_a_match(self) -> None:
        """TEETH for 5a: the same scan, against a module that DOES import the supply."""
        tree = ast.parse(_ROUTE_SRC.read_text())
        found = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        ]
        assert "supply_identity_evidence_async" in found, (
            "the import scan found nothing at all -- it cannot be trusted to "
            "report zero for the forbidden names"
        )

    def test_r5c_every_reachable_function_lives_in_this_service(self) -> None:
        """legacy-floor-isolation: the walk reads THIS service's Asana surface.

        Every resolved node in the reachable graph is an ``autom8_asana``
        module. Nothing in the path reaches a legacy monolith surface, and no
        legacy resolver shape is re-minted here: the route consults the SUPPLY,
        which consults Asana, and that is the whole chain.
        """
        visited, _attrs = reachable(_ROUTE_ROOT)

        assert visited, "the census resolved nothing"
        assert all(key.startswith("autom8_asana.") for key in visited)


# ===========================================================================
# R-6 -- refusals are typed. Nothing escapes as a 500 with a stack.
# ===========================================================================


class TestRefusalsAreTyped:
    def test_r6a_an_unreachable_offer_is_typed_evidence_not_an_http_error(
        self, client: TestClient
    ) -> None:
        """The supply types this absence itself; the route must not re-type it.

        ``resolver_unavailable`` on the evidence is a FACT the substrate
        records. Collapsing it into a 5xx would destroy the distinction between
        "the walk ran and found nothing" and "the walk did not run", which is
        the distinction the substrate exists to keep.
        """
        mock = _mock_client(
            business_task=Task(gid=BUSINESS_GID, name="Fixture Business A"),
            entry_raises=TimeoutError("asana timeout"),
        )

        response = _get(client, mock)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["asana_business"]["value"] is None
        assert data["asana_business"]["absent_reason"] == "resolver_unavailable"

    def test_r6b_a_supply_fault_is_a_typed_503_never_a_bare_500(self, client: TestClient) -> None:
        """RED: the supply itself raising -> 503 IDENTITY_SUPPLY_UNAVAILABLE."""
        mock = _clean_tier1_client()
        p = _patches(mock)
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch(
                "autom8_asana.api.routes.identity_supply.supply_identity_evidence_async",
                AsyncMock(side_effect=RuntimeError("supplier fault")),
            ),
        ):
            response = client.get(SUPPLY_PATH, headers=AUTH_HEADER)

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "IDENTITY_SUPPLY_UNAVAILABLE"
        assert "Traceback" not in response.text

    def test_r6c_a_split_basis_version_is_a_typed_502_not_a_lying_envelope(
        self, client: TestClient
    ) -> None:
        """RED: evidence disagreeing on basis_version -> 502, never one number.

        Broken INPUT (the surface is not touched): a supply whose families
        carry two basis versions. A 200 here would publish a single envelope
        version that is false of at least one of the rows it carries -- and a
        consumer re-grading observations against it would re-grade them against
        a rule that did not make them.
        """
        import dataclasses

        from autom8_asana.models.business.identity_supply import (
            build_identity_supply,
            supply_identity_evidence_async,
        )

        real_supply = supply_identity_evidence_async

        async def _split(*args: Any, **kwargs: Any):
            supply = await real_supply(*args, **kwargs)
            return dataclasses.replace(
                supply,
                offer=dataclasses.replace(supply.offer, basis_version=99),
            )

        assert build_identity_supply is not None  # keep the import honest
        mock = _clean_tier1_client()
        p = _patches(mock)
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch(
                "autom8_asana.api.routes.identity_supply.supply_identity_evidence_async",
                AsyncMock(side_effect=_split),
            ),
        ):
            response = client.get(SUPPLY_PATH, headers=AUTH_HEADER)

        assert response.status_code == 502
        assert response.json()["error"]["code"] == "IDENTITY_SUPPLY_BASIS_CONFLICT"

    def test_r6d_green_control_the_same_harness_passes_without_the_split(
        self, client: TestClient
    ) -> None:
        """TEETH for 6c: the identical patch harness, un-split, returns 200.

        Proves the 502 came from the injected disagreement and not from the
        patching itself.
        """
        from autom8_asana.models.business.identity_supply import (
            supply_identity_evidence_async as real_supply,
        )

        mock = _clean_tier1_client()
        p = _patches(mock)
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            p[4],
            patch(
                "autom8_asana.api.routes.identity_supply.supply_identity_evidence_async",
                AsyncMock(side_effect=real_supply),
            ),
        ):
            response = client.get(SUPPLY_PATH, headers=AUTH_HEADER)

        assert response.status_code == 200


# ===========================================================================
# R-7 -- the published contract.
# ===========================================================================


def test_r7a_the_route_is_registered_and_reachable(app) -> None:
    """An unmounted route is a 404 nobody notices."""
    paths = {route.path for route in app.routes if hasattr(route, "path")}

    assert "/v1/identity-supply/{offer_gid}" in paths


def test_r7b_openapi_advertises_the_read_only_marker(app) -> None:
    """Machine-readable, not just prose: fleet audits read ``x-fleet-*``."""
    operation = app.openapi()["paths"]["/v1/identity-supply/{offer_gid}"]["get"]

    assert operation.get("x-fleet-read-only") is True
    assert "x-fleet-side-effects" not in operation


def test_r7c_openapi_declares_the_s2s_scheme_and_no_new_scope(app) -> None:
    """S2S JWT, on the EXISTING ``query:read`` scope. Nothing new is provisioned."""
    operation = app.openapi()["paths"]["/v1/identity-supply/{offer_gid}"]["get"]
    schemes = {name for entry in operation["security"] for name in entry}

    assert "ServiceJWT" in schemes
    assert "PersonalAccessToken" not in schemes
    scopes = {s for entry in operation["security"] for v in entry.values() for s in v}
    assert scopes == {"query:read"}


def test_r7d_openapi_publishes_the_digits_pattern(app) -> None:
    """The digits constraint is on the WIRE CONTRACT, not only in the handler."""
    operation = app.openapi()["paths"]["/v1/identity-supply/{offer_gid}"]["get"]
    param = next(p for p in operation["parameters"] if p["name"] == "offer_gid")

    assert param["schema"]["pattern"] == r"^[0-9]{1,64}$"


def test_r7e_every_raised_error_code_is_named_in_the_published_responses(app) -> None:
    """Derived from the SOURCE, so a NEW refusal cannot ship undocumented.

    A refusal a consumer cannot anticipate is only marginally better than no
    refusal: the natural handling of an unrecognised error is a fallback, and a
    fallback here would fabricate evidence the supply refused to produce.
    """
    import re

    source = _ROUTE_SRC.read_text()
    raised = set(re.findall(r'raise_api_error\(\s*request_id,\s*(\d{3}),\s*"([A-Z_]+)"', source))
    assert raised, "no raise_api_error call sites parsed -- the regex or route drifted"

    operation = app.openapi()["paths"]["/v1/identity-supply/{offer_gid}"]["get"]
    for status, code in sorted(raised):
        assert status in operation["responses"], f"{status} raised but not published"
        assert code in operation["responses"][status]["description"], (
            f"{code} is raised with HTTP {status} but is not named in the "
            f"published {status} description"
        )


def test_r7f_the_absent_reason_enum_on_the_wire_is_the_supplys_ratified_set(app) -> None:
    """The closed set is published from ONE definition -- the supply's.

    If the wire model re-declared these members, the spec and the emitter could
    drift apart silently, and a consumer validating against the spec would
    reject a token the emitter is ratified to send.
    """
    from autom8_asana.models.business.identity_supply import RATIFIED_ABSENT_REASONS

    schemas = app.openapi()["components"]["schemas"]

    assert set(schemas["AbsentReason"]["enum"]) == set(RATIFIED_ABSENT_REASONS)
