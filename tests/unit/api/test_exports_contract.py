"""Contract tests for ``ExportRequest`` / ``ExportOptions`` Pydantic models.

Maps to TDD §13.1 contract tests + PRD AC-12 / AC-13 / AC-15:

- AC-12: ExportRequest contract has NO ``join`` / ``target_entity`` / etc.
- AC-13: ``options.predicate_join_semantics`` future field admits cleanly via
  the OPEN ``extra="allow"`` substructure (P1-C-02 binding).
- AC-15: No LazyFrame consumer surface in the contract (eager-only — P1-C-06).
- AC-16: Both routers exist and are exported.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.api.routes.exports import (
    PHASE_1_DEFAULT_COLUMNS,
    ExportOptions,
    ExportRequest,
    exports_router_api_v1,
    exports_router_v1,
)
from autom8_asana.query.models import Comparison, Op


# ---------------------------------------------------------------------------
# AC-12: single-entity hard-lock (no join surface)
# ---------------------------------------------------------------------------


class TestExportRequestForbiddenFields:
    """P1-C-01 binding: contract MUST NOT admit cross-entity join fields."""

    def test_join_field_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            ExportRequest(
                entity_type="process",
                project_gids=[1],
                join={"target_entity": "offer", "how": "left"},  # type: ignore[arg-type]
            )
        # extra="forbid" on top-level model surfaces "join" as forbidden
        assert "join" in str(exc.value).lower() or "extra" in str(exc.value).lower()

    def test_target_entity_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExportRequest(
                entity_type="process",
                project_gids=[1],
                target_entity="offer",  # type: ignore[arg-type]
            )

    def test_predicate_target_resolution_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExportRequest(
                entity_type="process",
                project_gids=[1],
                predicate_target_resolution="entity",  # type: ignore[arg-type]
            )


class TestExportRequestRequiredFields:
    def test_entity_type_required(self) -> None:
        with pytest.raises(ValidationError):
            ExportRequest(project_gids=[1])  # type: ignore[call-arg]

    def test_project_gids_required(self) -> None:
        with pytest.raises(ValidationError):
            ExportRequest(entity_type="process")  # type: ignore[call-arg]

    def test_project_gids_min_length_one(self) -> None:
        with pytest.raises(ValidationError):
            ExportRequest(entity_type="process", project_gids=[])

    def test_minimal_valid_request(self) -> None:
        req = ExportRequest(entity_type="process", project_gids=[1])
        assert req.entity_type == "process"
        assert req.project_gids == [1]
        assert req.predicate is None
        assert req.format == "json"
        assert req.options.include_incomplete_identity is True
        assert req.options.dedupe_key == ["office_phone", "vertical"]


class TestExportRequestFormatField:
    @pytest.mark.parametrize("fmt", ["json", "csv", "parquet"])
    def test_admitted_formats(self, fmt: str) -> None:
        req = ExportRequest(entity_type="process", project_gids=[1], format=fmt)  # type: ignore[arg-type]
        assert req.format == fmt

    def test_unsupported_format_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExportRequest(entity_type="process", project_gids=[1], format="xml")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AC-13: OPEN options substructure (P1-C-02)
# ---------------------------------------------------------------------------


class TestExportOptionsForwardCompat:
    """AC-13: options MUST admit Phase 2 ``predicate_join_semantics`` cleanly.

    Closed enum on options (extra="forbid") would FAIL these tests and is
    explicitly REFUSED per spike-handoff §6 P1-C-02 + PRD §6.4.
    """

    def test_options_extra_allow_admits_unknown_member(self) -> None:
        opts = ExportOptions(predicate_join_semantics="preserve-outer")  # type: ignore[call-arg]
        assert opts.model_extra == {"predicate_join_semantics": "preserve-outer"}

    def test_export_request_admits_phase2_field_via_options(self) -> None:
        # The Phase 2 ExportRequest pattern from ADR §4 + spike §3.
        req = ExportRequest(
            entity_type="process",
            project_gids=[1201265144487549],
            options={"predicate_join_semantics": "allow-inner-rewrite"},  # type: ignore[arg-type]
        )
        assert req.options.model_extra is not None
        assert req.options.model_extra.get("predicate_join_semantics") == "allow-inner-rewrite"

    def test_options_admits_arbitrary_phase2_additive_fields(self) -> None:
        # Any future additive member must NOT cause validation error.
        opts = ExportOptions(some_future_phase_2_field="any_value")  # type: ignore[call-arg]
        assert opts.model_extra is not None
        assert "some_future_phase_2_field" in opts.model_extra


# ---------------------------------------------------------------------------
# AC-15: Eager-only consumer surface (no LazyFrame in the contract)
# ---------------------------------------------------------------------------


def test_no_lazyframe_in_contract_signature() -> None:
    """AC-15: ExportRequest contract field annotations contain no LazyFrame."""
    # Inspect the model's JSON schema — LazyFrame would surface as a
    # foreign / non-serializable type, but Pydantic would have rejected it
    # at class-definition time. This is a structural assertion that the
    # contract is purely eager-DataFrame-friendly.
    import polars as pl

    schema_json = ExportRequest.model_json_schema()
    schema_str = str(schema_json)
    assert "LazyFrame" not in schema_str
    # Spot-check the import is available so test failure is meaningful.
    assert pl is not None


# ---------------------------------------------------------------------------
# AC-16: dual-mount router pair exported and constructed via correct factories
# ---------------------------------------------------------------------------


def test_both_routers_exist_and_are_distinct_instances() -> None:
    assert exports_router_v1 is not None
    assert exports_router_api_v1 is not None
    assert exports_router_v1 is not exports_router_api_v1


def test_v1_router_uses_v1_prefix() -> None:
    assert exports_router_v1.prefix == "/v1/exports"


def test_api_v1_router_uses_api_v1_prefix() -> None:
    assert exports_router_api_v1.prefix == "/api/v1/exports"


def test_v1_router_security_scheme_is_service_jwt() -> None:
    """ESC-2 verification surface: S2S route uses ServiceJWT scheme."""
    # SecureRouter exposes the security scheme via a private attribute; access
    # via getattr fallback to keep the assertion stable across SecureRouter
    # internals.
    scheme = getattr(exports_router_v1, "security_scheme", None) or getattr(
        exports_router_v1, "_security_scheme", None
    )
    assert scheme is not None
    assert scheme.scheme_name == "ServiceJWT"


def test_api_v1_router_security_scheme_is_pat() -> None:
    """ESC-2 verification surface: PAT route uses PersonalAccessToken scheme."""
    scheme = getattr(exports_router_api_v1, "security_scheme", None) or getattr(
        exports_router_api_v1, "_security_scheme", None
    )
    assert scheme is not None
    assert scheme.scheme_name == "PersonalAccessToken"


def test_dual_mount_handler_callable_count() -> None:
    """Both routers register exactly one POST endpoint at the empty suffix."""
    routes_v1 = [r for r in exports_router_v1.routes if hasattr(r, "methods")]
    routes_api_v1 = [r for r in exports_router_api_v1.routes if hasattr(r, "methods")]
    assert len(routes_v1) == 1
    assert len(routes_api_v1) == 1
    # Both POST.
    assert "POST" in routes_v1[0].methods
    assert "POST" in routes_api_v1[0].methods


# ---------------------------------------------------------------------------
# Predicate body acceptance (AST stays free-form per P1-C-03)
# ---------------------------------------------------------------------------


class TestExportRequestPredicateBodyAcceptance:
    def test_simple_comparison_predicate_admitted(self) -> None:
        req = ExportRequest(
            entity_type="process",
            project_gids=[1],
            predicate={"field": "section", "op": "in", "value": ["ACTIVE"]},  # type: ignore[arg-type]
        )
        assert isinstance(req.predicate, Comparison)
        assert req.predicate.op == Op.IN

    def test_date_op_between_admitted(self) -> None:
        # Sprint 2 additive Op enum member — AST shape unchanged.
        req = ExportRequest(
            entity_type="process",
            project_gids=[1],
            predicate={"field": "due_on", "op": "between", "value": ["2026-01-01", "2026-04-01"]},  # type: ignore[arg-type]
        )
        assert isinstance(req.predicate, Comparison)
        assert req.predicate.op == Op.BETWEEN

    def test_and_group_predicate_admitted(self) -> None:
        req = ExportRequest(
            entity_type="process",
            project_gids=[1],
            predicate={  # type: ignore[arg-type]
                "and": [
                    {"field": "section", "op": "in", "value": ["ACTIVE"]},
                    {"field": "completed", "op": "eq", "value": False},
                ]
            },
        )
        assert req.predicate is not None


def test_phase_1_default_columns_includes_identity_components() -> None:
    """PRD §5.2 minimum projection includes the identity-key components."""
    assert "office_phone" in PHASE_1_DEFAULT_COLUMNS
    assert "vertical" in PHASE_1_DEFAULT_COLUMNS
    assert "gid" in PHASE_1_DEFAULT_COLUMNS
    assert "section" in PHASE_1_DEFAULT_COLUMNS
