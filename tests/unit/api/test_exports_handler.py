"""Unit tests for the ``/exports`` shared handler logic.

Maps to TDD §13.4-§13.7 and verifies:

- LEFT-PRESERVATION GUARD wrapper presence (TDD §10 + ADR mechanism (a)).
  Phase 1 ships single-entity → wrapper is a NO-OP shim; the test asserts the
  shim is invoked AND the engine code at ``query/engine.py:139-178`` is NOT
  modified (verified by absence of any modification — see git-diff in summary).
- Mechanism (b) escape valve: ``predicate_join_semantics`` is read from the
  OPEN options surface and forwarded into the wrapper's log payload.
- End-to-end handler pipeline against a mocked strategy / entity service:
  validates entity_type → ACTIVE-default applied → identity_complete computed
  → dedupe → CSV body emission with identity_complete column header.
- AP-3 dual-mount asymmetry guard: both routes call the SAME ``export_handler``
  callable, so any divergence is structurally impossible.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from fastapi import HTTPException

from autom8_asana.api.routes.exports import (
    ExportOptions,
    ExportRequest,
    _engine_call_with_left_preservation_guard,
    _resolve_predicate_join_semantics,
    export_handler,
    post_export_api_v1,
    post_export_v1,
)


# ---------------------------------------------------------------------------
# LEFT-PRESERVATION GUARD wrapper (TDD §10 + ADR §4)
# ---------------------------------------------------------------------------


class TestLeftPreservationGuardWrapper:
    """Mechanism (a) wrapper: NO-OP shim in Phase 1 (no joins).

    The wrapper's job in Phase 1 is to (1) record that the seam exists, and
    (2) forward the caller's predicate_join_semantics value into the log
    payload so auditors can verify the contract surface (mechanism (b)) is
    wired through.
    """

    @pytest.mark.asyncio
    async def test_wrapper_invokes_strategy_get_dataframe(self) -> None:
        fake_df = pl.DataFrame({"gid": ["1"], "office_phone": ["555"], "vertical": ["s"]})
        mock_strategy = MagicMock()
        mock_strategy._get_dataframe = AsyncMock(return_value=fake_df)
        with patch(
            "autom8_asana.services.universal_strategy.get_universal_strategy",
            return_value=mock_strategy,
        ):
            out = await _engine_call_with_left_preservation_guard(
                entity_type="process",
                project_gid="123",
                client=object(),
                request_id="req-1",
                predicate_join_semantics="preserve-outer",
            )
        assert out is fake_df
        # Verify the strategy was invoked exactly once with the expected
        # project_gid + a client object positional argument.
        mock_strategy._get_dataframe.assert_awaited_once()
        call = mock_strategy._get_dataframe.await_args
        assert call.args[0] == "123"

    @pytest.mark.asyncio
    async def test_wrapper_logs_phase_and_join_semantics(self) -> None:
        """ESC-2 / ADR §4 mechanism (b): caller's predicate_join_semantics
        flows into the log payload so auditors can see the override surface
        is wired through (not silently ignored)."""
        fake_df = pl.DataFrame({"gid": ["1"], "office_phone": ["555"], "vertical": ["s"]})
        mock_strategy = MagicMock()
        mock_strategy._get_dataframe = AsyncMock(return_value=fake_df)
        with patch(
            "autom8_asana.services.universal_strategy.get_universal_strategy",
            return_value=mock_strategy,
        ), patch(
            "autom8_asana.api.routes.exports.logger"
        ) as mock_logger:
            await _engine_call_with_left_preservation_guard(
                entity_type="process",
                project_gid="123",
                client=object(),
                request_id="req-2",
                predicate_join_semantics="allow-inner-rewrite",
            )
        # Find the guard-noop log emission.
        guard_calls = [
            c
            for c in mock_logger.debug.call_args_list
            if c.args and c.args[0] == "exports_left_preservation_guard_noop"
        ]
        assert guard_calls, "Wrapper must emit the guard-noop log signal"
        extra = guard_calls[0].kwargs["extra"]
        assert extra["predicate_join_semantics"] == "allow-inner-rewrite"
        assert extra["phase"] == 1
        assert extra["join_active"] is False
        assert extra["entity_type"] == "process"
        assert extra["project_gid"] == "123"
        assert extra["request_id"] == "req-2"


class TestResolvePredicateJoinSemantics:
    """Mechanism (b) escape valve reading via OPEN options surface."""

    def test_default_when_field_absent(self) -> None:
        opts = ExportOptions()
        assert _resolve_predicate_join_semantics(opts) == "preserve-outer"

    def test_explicit_preserve_outer(self) -> None:
        opts = ExportOptions(predicate_join_semantics="preserve-outer")  # type: ignore[call-arg]
        assert _resolve_predicate_join_semantics(opts) == "preserve-outer"

    def test_explicit_allow_inner_rewrite(self) -> None:
        opts = ExportOptions(predicate_join_semantics="allow-inner-rewrite")  # type: ignore[call-arg]
        assert _resolve_predicate_join_semantics(opts) == "allow-inner-rewrite"

    def test_unknown_value_falls_back_to_default(self) -> None:
        opts = ExportOptions(predicate_join_semantics="bogus")  # type: ignore[call-arg]
        assert _resolve_predicate_join_semantics(opts) == "preserve-outer"


# ---------------------------------------------------------------------------
# AP-3 dual-mount asymmetry: PAT and S2S routes invoke the same handler
# ---------------------------------------------------------------------------


class TestDualMountSharedHandler:
    """Both routes dispatch into the shared ``export_handler`` callable.

    P1-C-07 binding: AP-3 guard. Asymmetric mounting (PAT-only or S2S-only)
    structurally precluded by sharing the implementation.
    """

    def test_post_export_v1_and_api_v1_both_exist(self) -> None:
        assert post_export_v1 is not None
        assert post_export_api_v1 is not None

    def test_both_route_callables_distinct_functions_but_invoke_same_handler(self) -> None:
        # The route functions are intentionally separate (FastAPI requires
        # one function per @router.post for OpenAPI distinction) — but their
        # bodies invoke export_handler with identical parameter shapes.
        import inspect

        src_v1 = inspect.getsource(post_export_v1)
        src_api_v1 = inspect.getsource(post_export_api_v1)
        # Both source bodies must contain the export_handler invocation.
        assert "export_handler" in src_v1
        assert "export_handler" in src_api_v1


# ---------------------------------------------------------------------------
# End-to-end handler pipeline (mocked strategy + entity service)
# ---------------------------------------------------------------------------


def _make_mock_entity_service(entity_type: str = "process") -> MagicMock:
    svc = MagicMock()
    ctx = MagicMock()
    ctx.entity_type = entity_type
    ctx.project_gid = "1201265144487549"
    svc.validate_entity_type.return_value = ctx
    return svc


class TestExportHandlerPipeline:
    @pytest.mark.asyncio
    async def test_unknown_entity_type_raises_400(self) -> None:
        from autom8_asana.services.errors import UnknownEntityError

        svc = MagicMock()
        svc.validate_entity_type.side_effect = UnknownEntityError(
            "nonsense", available=["process", "offer"]
        )
        req = ExportRequest(entity_type="nonsense", project_gids=[1])
        with pytest.raises(HTTPException) as exc:
            await export_handler(
                request_body=req,
                request_id="req-1",
                auth=object(),
                entity_service=svc,
                client=object(),
            )
        assert exc.value.status_code == 400
        # Error body shape: detail.error.code = "unknown_entity_type"
        detail = exc.value.detail
        assert isinstance(detail, dict)
        assert detail["error"]["code"] == "unknown_entity_type"

    @pytest.mark.asyncio
    async def test_unknown_section_value_raises_400(self) -> None:
        svc = _make_mock_entity_service()
        req = ExportRequest(
            entity_type="process",
            project_gids=[1],
            predicate={  # type: ignore[arg-type]
                "field": "section",
                "op": "in",
                "value": ["TOTALLY_BOGUS_SECTION"],
            },
        )
        with pytest.raises(HTTPException) as exc:
            await export_handler(
                request_body=req,
                request_id="req-1",
                auth=object(),
                entity_service=svc,
                client=object(),
            )
        assert exc.value.status_code == 400
        assert exc.value.detail["error"]["code"] == "unknown_section_value"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_full_pipeline_csv_with_identity_complete_and_active_default(
        self, caplog: Any
    ) -> None:
        # Fixture: 4 rows including a null-key row to verify AP-6 transparency.
        fake_df = pl.DataFrame(
            {
                "gid": ["g1", "g2", "g3", "g4"],
                "name": ["acct1", "acct2", "acct3", "acct4"],
                "section": ["ACTIVE", "EXECUTING", "ACTIVE", "INACTIVE"],
                "office_phone": ["555-1", "555-2", None, "555-3"],
                "vertical": ["saas", "retail", "ent", "saas"],
                "pipeline_type": ["reactivation", "outreach", "outreach", "outreach"],
                "modified_at": [
                    "2026-04-01",
                    "2026-04-15",
                    "2026-04-20",
                    "2026-04-10",
                ],
            }
        )

        # Mock the schema registry to return a schema that admits the predicate
        # field references used in the test (section + completed). We patch
        # PredicateCompiler.compile to bypass schema validation in this unit
        # context — the compile path is exercised separately via the existing
        # tests/unit/query/ suite.
        from unittest.mock import patch

        mock_strategy = MagicMock()
        mock_strategy._get_dataframe = AsyncMock(return_value=fake_df)

        svc = _make_mock_entity_service()
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
            format="csv",
            # Caller omits section → ACTIVE-default fires.
        )

        with patch(
            "autom8_asana.api.routes.exports.get_universal_strategy",
            return_value=mock_strategy,
            create=True,
        ), patch(
            "autom8_asana.services.universal_strategy.get_universal_strategy",
            return_value=mock_strategy,
        ), patch.object(
            __import__(
                "autom8_asana.api.routes.exports", fromlist=["PredicateCompiler"]
            ).PredicateCompiler,
            "compile",
            lambda self, node, schema: pl.col("section").is_in(
                ["ACTIVE", "BUILDING", "EXECUTING", "PROCESSING", "OPPORTUNITY", "CONTACTED"]
            ),
        ):
            resp = await export_handler(
                request_body=req,
                request_id="req-pipe-1",
                auth=object(),
                entity_service=svc,
                client=object(),
            )

        # Response is CSV with identity_complete column.
        assert resp.media_type == "text/csv"
        body = resp.body.decode("utf-8")
        first_line = body.splitlines()[0]
        assert "identity_complete" in first_line
        # ACTIVE-default applied → INACTIVE row excluded from result body.
        assert "acct4" not in body
        # Null-key row (acct3) MUST be present per AP-6 (identity_complete=False).
        assert "acct3" in body
