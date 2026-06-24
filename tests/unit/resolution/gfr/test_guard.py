"""Tests for the GFR central guard (TDD §6.1, §12.3, §9.3 guard.py row).

CRITICAL: covers the cache-only RED proof (INVARIANT I3, B5, new_hole 3 scoping),
the identity-path purity check (INVARIANT I1 — the anti-regression hinge for the
collision-closure gate), field-legality (FM5), and the structural grep-zero
assertion that no office_phone literal sits on the identity code path (PT-03).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.query.join import JoinSpec
from autom8_asana.query.models import Comparison, Op, RowsRequest
from autom8_asana.resolution.gfr import engine as engine_mod
from autom8_asana.resolution.gfr import guard as guard_mod
from autom8_asana.resolution.gfr.errors import GuardViolationError, UnresolvedError
from autom8_asana.resolution.gfr.models import (
    FieldPlan,
    HopClass,
    ResolutionPlan,
)
from tests.unit.resolution.gfr.conftest import (
    make_hydration_result,
    make_rows_response,
)

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]


class TestFieldLegality:
    def test_legal_field_passes(self) -> None:
        guard_mod.assert_field_legal("company_id")  # no raise

    def test_illegal_field_raises_unknown_field(self) -> None:
        with pytest.raises(UnresolvedError) as exc:
            guard_mod.assert_field_legal("not_a_real_column")
        assert exc.value.reason == "unknown-field"


class TestCacheOnlyClassification:
    def test_offer_is_cache_only(self) -> None:
        # offer-domain descriptor: body_parameterized=False => cache-only.
        assert guard_mod.is_cache_only("offer") is True

    def test_business_is_cache_only(self) -> None:
        assert guard_mod.is_cache_only("business") is True

    def test_unregistered_entity_defaults_cache_only(self) -> None:
        # Safe default: no API fallback for an unknown entity.
        assert guard_mod.is_cache_only("totally-unknown-entity") is True


class TestIdentityPurityRequest:
    def test_gid_exact_request_with_no_join_is_pure(self) -> None:
        req = RowsRequest(
            where=Comparison(field="gid", op=Op.EQ, value="B_correct"),
            select=["company_id"],
            join=None,
        )
        guard_mod.assert_request_identity_pure(req)  # no raise

    def test_company_id_via_office_phone_join_is_rejected(self) -> None:
        # The v1 trap: reach company_id via an office_phone value-join.
        req = RowsRequest(
            select=["gid"],
            join=JoinSpec(entity_type="business", select=["company_id"], on="office_phone"),
        )
        with pytest.raises(GuardViolationError):
            guard_mod.assert_request_identity_pure(req)

    def test_company_id_via_data_service_join_is_rejected(self) -> None:
        req = RowsRequest(
            select=["gid"],
            join=JoinSpec(
                entity_type="spend",
                select=["company_id"],
                source="data-service",
                factory="spend",
            ),
        )
        with pytest.raises(GuardViolationError):
            guard_mod.assert_request_identity_pure(req)

    def test_non_identity_phone_join_is_allowed(self) -> None:
        # A phone-scoped ENRICHMENT join that does NOT select an identity field
        # is permitted (INVARIANT I1 forbids only identity-via-phone).
        req = RowsRequest(
            select=["gid"],
            join=JoinSpec(entity_type="business", select=["booking_type"], on="office_phone"),
        )
        guard_mod.assert_request_identity_pure(req)  # no raise


class TestIdentityPurityPlan:
    def test_business_owned_identity_plan_is_pure(self) -> None:
        plan = ResolutionPlan(
            entry_entity_type="offer",
            field_plans=[
                FieldPlan(
                    owner="business",
                    fields=["company_id"],
                    hop=HopClass.PARENT_CHAIN,
                    is_identity=True,
                )
            ],
        )
        guard_mod.assert_plan_identity_pure(plan)  # no raise

    def test_non_business_identity_owner_is_rejected(self) -> None:
        plan = ResolutionPlan(
            entry_entity_type="offer",
            field_plans=[
                FieldPlan(
                    owner="offer",  # identity must be Business-only
                    fields=["company_id"],
                    hop=HopClass.LOCAL,
                    is_identity=True,
                )
            ],
        )
        with pytest.raises(GuardViolationError):
            guard_mod.assert_plan_identity_pure(plan)


class TestCacheOnlyRedProof:
    """RED proof (B5, new_hole 3): offer-domain data-frame miss => no API fallback.

    The call-count delta is measured over the POST-ENTRY data-frame phase ONLY:
    the baseline is taken AFTER _fetch_and_anchor_async returns. The legitimate
    entry+chain reads are EXCLUDED — a test that counts total reads and expects
    zero would FALSE-FAIL on the entry budget (the explicit new_hole-3 scoping).
    """

    @pytest.mark.asyncio
    async def test_offer_domain_frame_miss_fires_zero_post_entry_api_calls(
        self, mock_client
    ) -> None:
        # The entry phase anchors an offer to its Business; the post-entry
        # data-frame read is an empty frame (the miss). execute_rows returns an
        # empty RowsResponse and the engine raises business-row-not-found with
        # NO further Asana-API call (no frame fallback wired — INVARIANT I3).
        anchor_result = make_hydration_result(
            business_gid="B", entry_type=EntityType.OFFER, path_len=3
        )

        # A mock QueryEngine whose execute_rows returns an empty frame. It does
        # NOT touch the AsanaClient — proving no post-entry API fallback fires.
        empty_response = make_rows_response(rows=[])
        query_engine = AsyncMock()
        query_engine.execute_rows = AsyncMock(return_value=empty_response)

        with patch(
            "autom8_asana.resolution.gfr.entry.hydrate_from_gid_async",
            AsyncMock(return_value=anchor_result),
        ):
            # Baseline AFTER the entry phase would return: we assert the client
            # gets ZERO additional reads through the post-entry phase by checking
            # the mock client's task getter is never called post-entry. Since the
            # entry hydrate is patched out (its reads are inside it), any client
            # read here would be a post-entry violation.
            mock_client.tasks.get_async.reset_mock()
            with pytest.raises(UnresolvedError) as exc:
                await engine_mod.resolve_async(
                    "O",
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                )
        assert exc.value.reason == "business-row-not-found"
        # Cache-only HARD line: ZERO post-entry Asana-API reads on the miss.
        assert mock_client.tasks.get_async.await_count == 0


def _executable_string_literals(module) -> list[str]:
    """Return all string-literal values in EXECUTABLE code (not docstrings).

    Parses the module with ``ast`` and collects ``ast.Constant`` string values,
    EXCLUDING module/class/function docstrings (the first statement of a body
    when it is a bare string expression). This isolates the structural question
    — does the running code use the literal? — from prose that merely explains
    the invariant. A grep that counted docstring mentions would FALSE-FAIL on the
    very comments documenting INVARIANT I1, so AST is the honest probe.
    """
    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstring_nodes.add(id(body[0].value))

    literals: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_nodes
        ):
            literals.append(node.value)
    return literals


class TestStructuralGrepZero:
    """PT-03 grep-zero: no office_phone literal in EXECUTABLE identity-path code.

    INVARIANT I1 structural lint: the identity reach is the parent chain +
    gid-exact row ONLY. The engine, planner, and posture modules — the running
    identity code path — must construct NO ``office_phone`` literal in executable
    code (docstrings explaining the invariant are excluded, via AST). The guard
    module references ``office_phone`` only as the FORBIDDEN-key constant it
    rejects (the defense), and never as a ``JoinSpec(on="office_phone")``.
    """

    def test_engine_module_executable_code_has_no_office_phone(self) -> None:
        assert "office_phone" not in _executable_string_literals(engine_mod)

    def test_planner_and_posture_executable_code_have_no_office_phone(self) -> None:
        from autom8_asana.resolution.gfr import planner as planner_mod
        from autom8_asana.resolution.gfr import posture as posture_mod

        for mod in (planner_mod, posture_mod):
            literals = _executable_string_literals(mod)
            assert "office_phone" not in literals, f"office_phone literal in {mod.__name__}"

    def test_guard_office_phone_only_as_forbidden_key_constant(self) -> None:
        # In executable code the ONLY office_phone literal is the forbidden-key
        # constant (the defense). It is never used to construct a JoinSpec on the
        # identity path.
        literals = _executable_string_literals(guard_mod)
        assert literals.count("office_phone") == 1, "guard uses office_phone only as the constant"
        guard_src = Path(guard_mod.__file__).read_text(encoding="utf-8")
        assert not re.search(r"JoinSpec\([^)]*office_phone", guard_src)
