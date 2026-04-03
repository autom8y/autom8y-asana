"""Tests for cross-service enrichment wiring (Phase 1 completion).

Covers:
- SavedJoinSpec extension: source, factory, period fields + validation
- YAML loading: offers_with_spend.yaml round-trip through SavedQuery → JoinSpec
- CLI argument parsing: --join-source, --join-factory, --join-period
- Data client creation helper: _create_data_client_if_needed
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from autom8_asana.query.join import JoinSpec
from autom8_asana.query.saved import SavedJoinSpec, SavedQuery, load_saved_query

# ---------------------------------------------------------------------------
# SavedJoinSpec Extension Tests
# ---------------------------------------------------------------------------


class TestSavedJoinSpecExtension:
    """Validate SavedJoinSpec mirrors JoinSpec's cross-service fields."""

    def test_default_source_is_entity(self) -> None:
        spec = SavedJoinSpec(entity_type="business", select=["booking_type"])
        assert spec.source == "entity"
        assert spec.factory is None
        assert spec.period == "LIFETIME"

    def test_data_service_source_with_factory(self) -> None:
        spec = SavedJoinSpec(
            entity_type="spend",
            select=["spend", "cps"],
            source="data-service",
            factory="spend",
            period="T30",
        )
        assert spec.source == "data-service"
        assert spec.factory == "spend"
        assert spec.period == "T30"

    def test_data_service_requires_factory(self) -> None:
        with pytest.raises(ValidationError, match="factory is required"):
            SavedJoinSpec(
                entity_type="spend",
                select=["spend"],
                source="data-service",
            )

    def test_entity_source_rejects_factory(self) -> None:
        with pytest.raises(ValidationError, match="factory is only valid"):
            SavedJoinSpec(
                entity_type="business",
                select=["booking_type"],
                source="entity",
                factory="spend",
            )

    def test_model_dump_produces_join_spec_compatible_dict(self) -> None:
        """SavedJoinSpec.model_dump() round-trips through JoinSpec."""
        saved = SavedJoinSpec(
            entity_type="spend",
            select=["spend", "cps"],
            source="data-service",
            factory="spend",
            period="T30",
            on="office_phone",
        )
        data = saved.model_dump(exclude_none=True)
        # Must be parseable by JoinSpec
        join = JoinSpec(**data)
        assert join.source == "data-service"
        assert join.factory == "spend"
        assert join.period == "T30"
        assert join.on == "office_phone"

    def test_entity_join_backward_compatible(self) -> None:
        """Entity joins still work exactly as before."""
        saved = SavedJoinSpec(
            entity_type="business",
            select=["booking_type"],
        )
        data = saved.model_dump(exclude_none=True)
        join = JoinSpec(**data)
        assert join.source == "entity"
        assert join.factory is None


# ---------------------------------------------------------------------------
# YAML Loading Tests
# ---------------------------------------------------------------------------


class TestSavedQueryYAMLLoading:
    """Verify offers_with_spend.yaml loads and flows to JoinSpec."""

    def test_load_offers_with_spend_yaml(self) -> None:
        """The actual offers_with_spend.yaml file loads successfully."""
        yaml_path = (
            Path(__file__).parent.parent.parent.parent
            / "queries"
            / "offers_with_spend.yaml"
        )
        if not yaml_path.exists():
            pytest.skip("offers_with_spend.yaml not found")
        saved = load_saved_query(yaml_path)
        assert saved.name == "offers_with_spend"
        assert saved.join is not None
        assert saved.join.source == "data-service"
        assert saved.join.factory == "spend"
        assert saved.join.period == "T30"
        assert "spend" in saved.join.select

    def test_saved_query_join_to_rows_request(self) -> None:
        """SavedQuery join flows through to RowsRequest via model_dump."""
        from autom8_asana.query.models import RowsRequest

        saved = SavedQuery(
            name="test",
            entity_type="offer",
            classification="active",
            join=SavedJoinSpec(
                entity_type="spend",
                select=["spend", "cps"],
                source="data-service",
                factory="spend",
                period="T30",
            ),
        )
        # Simulate the flow from handle_run (line 1059 in __main__.py)
        request_data: dict[str, Any] = {
            "classification": saved.classification,
            "limit": saved.limit,
            "offset": saved.offset,
        }
        if saved.join:
            request_data["join"] = saved.join.model_dump(exclude_none=True)

        request = RowsRequest.model_validate(request_data)
        assert request.join is not None
        assert request.join.source == "data-service"
        assert request.join.factory == "spend"


# ---------------------------------------------------------------------------
# CLI Argument Parsing Tests
# ---------------------------------------------------------------------------


class TestCLIJoinArgParsing:
    """Verify new CLI flags parse correctly."""

    def test_parse_join_with_data_service_params(self) -> None:
        from autom8_asana.query.__main__ import _parse_join

        result = _parse_join(
            "spend:spend,cps",
            join_on="office_phone",
            source="data-service",
            factory="spend",
            period="T30",
        )
        assert result["source"] == "data-service"
        assert result["factory"] == "spend"
        assert result["period"] == "T30"
        assert result["entity_type"] == "spend"
        assert result["select"] == ["spend", "cps"]
        assert result["on"] == "office_phone"

    def test_parse_join_entity_source_no_extra_fields(self) -> None:
        from autom8_asana.query.__main__ import _parse_join

        result = _parse_join("business:booking_type", join_on=None)
        assert "source" not in result
        assert "factory" not in result
        assert "period" not in result

    def test_parse_join_data_service_requires_factory(self) -> None:
        from autom8_asana.query.__main__ import CLIError, _parse_join

        with pytest.raises(CLIError, match="--join-factory is required"):
            _parse_join(
                "spend:spend",
                join_on=None,
                source="data-service",
                factory=None,
            )

    def test_add_join_args_registers_new_flags(self) -> None:
        import argparse

        from autom8_asana.query.__main__ import _add_join_args

        parser = argparse.ArgumentParser()
        _add_join_args(parser)
        args = parser.parse_args(
            [
                "--join",
                "spend:spend,cps",
                "--join-source",
                "data-service",
                "--join-factory",
                "spend",
                "--join-period",
                "T30",
            ]
        )
        assert args.join_source == "data-service"
        assert args.join_factory == "spend"
        assert args.join_period == "T30"


# ---------------------------------------------------------------------------
# Data Client Creation Helper Tests
# ---------------------------------------------------------------------------


class TestCreateDataClientIfNeeded:
    """Verify _create_data_client_if_needed behavior."""

    def test_returns_none_for_entity_join(self) -> None:
        from autom8_asana.query.__main__ import _create_data_client_if_needed

        result = _create_data_client_if_needed(
            {"entity_type": "business", "select": ["booking_type"]}
        )
        assert result is None

    def test_returns_none_for_no_join(self) -> None:
        from autom8_asana.query.__main__ import _create_data_client_if_needed

        assert _create_data_client_if_needed(None) is None

    def test_creates_client_for_data_service(self) -> None:
        from autom8_asana.query.__main__ import _create_data_client_if_needed

        with (
            patch("autom8_asana.clients.data.client.DataServiceClient") as mock_cls,
            patch(
                "autom8_asana.auth.service_token.ServiceTokenAuthProvider",
                side_effect=ValueError("no key"),
            ),
        ):
            mock_cls.return_value = "mock_client"
            result = _create_data_client_if_needed(
                {"source": "data-service", "factory": "spend"}
            )
        assert result == "mock_client"

    def test_creates_client_with_auth_provider(self) -> None:
        """When SERVICE_CLIENT_ID/SECRET are available, auth_provider is passed."""
        from autom8_asana.query.__main__ import _create_data_client_if_needed

        mock_auth = object()
        with (
            patch("autom8_asana.clients.data.client.DataServiceClient") as mock_cls,
            patch(
                "autom8_asana.auth.service_token.ServiceTokenAuthProvider",
                return_value=mock_auth,
            ),
        ):
            mock_cls.return_value = "mock_client"
            _create_data_client_if_needed(
                {"source": "data-service", "factory": "spend"}
            )
        mock_cls.assert_called_once_with(auth_provider=mock_auth)

    def test_raises_cli_error_on_init_failure(self) -> None:
        from autom8_asana.query.__main__ import CLIError, _create_data_client_if_needed

        with (
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                side_effect=RuntimeError("no config"),
            ),
            patch(
                "autom8_asana.auth.service_token.ServiceTokenAuthProvider",
                side_effect=ValueError("no key"),
            ),
            pytest.raises(CLIError, match="Data-service joins require"),
        ):
            _create_data_client_if_needed(
                {"source": "data-service", "factory": "spend"}
            )


class TestServiceTokenAuthProvider:
    """Tests for ServiceTokenAuthProvider (auth/service_token.py)."""

    def test_get_secret_returns_token(self) -> None:
        """get_secret() returns JWT from TokenManager."""
        with (
            patch("autom8y_core.Config") as mock_config_cls,
            patch("autom8y_core.TokenManager") as mock_tm_cls,
            patch.dict(
                "os.environ",
                {
                    "SERVICE_CLIENT_ID": "test-cid-123",
                    "SERVICE_CLIENT_SECRET": "test-secret-456",
                },
            ),
        ):
            mock_manager = mock_tm_cls.return_value
            mock_manager.get_token.return_value = "jwt-token-abc"

            from autom8_asana.auth.service_token import ServiceTokenAuthProvider

            provider = ServiceTokenAuthProvider()
            token = provider.get_secret("AUTOM8Y_DATA_API_KEY")

        assert token == "jwt-token-abc"
        mock_config_cls.assert_called_once_with(
            client_id="test-cid-123",
            client_secret="test-secret-456",
            auth_url="https://auth.api.autom8y.io",
            service_name="autom8y-asana",
        )

    def test_raises_on_missing_service_key(self) -> None:
        """Raises ValueError when SERVICE_CLIENT_ID/SECRET is not set."""
        with (
            patch.dict("os.environ", {}, clear=False),
            pytest.raises(
                ValueError,
                match="SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET are required",
            ),
        ):
            # Ensure service credentials are not in env
            import os

            os.environ.pop("SERVICE_CLIENT_ID", None)
            os.environ.pop("SERVICE_CLIENT_SECRET", None)

            from autom8_asana.auth.service_token import ServiceTokenAuthProvider

            ServiceTokenAuthProvider()

    def test_close_delegates_to_manager(self) -> None:
        """close() calls TokenManager.close()."""
        with (
            patch("autom8y_core.Config"),
            patch("autom8y_core.TokenManager") as mock_tm_cls,
            patch.dict(
                "os.environ",
                {
                    "SERVICE_CLIENT_ID": "test-cid",
                    "SERVICE_CLIENT_SECRET": "test-secret",
                },
            ),
        ):
            from autom8_asana.auth.service_token import ServiceTokenAuthProvider

            provider = ServiceTokenAuthProvider()
            provider.close()
            mock_tm_cls.return_value.close.assert_called_once()


class TestBatchErrorHandlerStrCoercion:
    """Tests for batch.py error handler dict coercion fix."""

    def test_dict_detail_does_not_crash(self) -> None:
        """FastAPI 422 returns detail as list[dict] — must not crash PII masking."""
        from autom8_asana.clients.data._pii import mask_pii_in_string

        # Simulate what the error handler does after the fix
        detail = [
            {"type": "missing", "loc": ["body", "frame_type"], "msg": "Field required"}
        ]
        result = mask_pii_in_string(str(detail))
        assert "Field required" in result

    def test_string_error_still_works(self) -> None:
        """Normal string errors continue to be masked correctly."""
        from autom8_asana.clients.data._pii import mask_pii_in_string

        result = mask_pii_in_string("Error for +14105298010")
        assert "+14105298010" not in result
