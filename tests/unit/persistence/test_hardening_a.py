"""Unit tests for TDD-HARDENING-A Foundation changes.

Per TDD-HARDENING-A: Tests for exception hierarchy, stub models,
logging context, and observability protocol.
"""

from __future__ import annotations

import logging

import pytest

from autom8_asana.persistence.errors import (
    GidValidationError,
    PositioningConflictError,
    SaveOrchestrationError,
)


class TestGidValidationError:
    """Tests for GidValidationError exception."""

    def test_inherits_from_save_orchestration_error(self) -> None:
        """GidValidationError inherits from SaveOrchestrationError."""
        error = GidValidationError("Invalid GID")
        assert isinstance(error, SaveOrchestrationError)

    def test_error_message_stored(self) -> None:
        """Error message is stored correctly."""
        error = GidValidationError("GID must be numeric")
        assert str(error) == "GID must be numeric"

    def test_can_be_caught_as_save_orchestration_error(self) -> None:
        """GidValidationError can be caught as SaveOrchestrationError."""
        with pytest.raises(SaveOrchestrationError):
            raise GidValidationError("test")


class TestPositioningConflictError:
    """Tests for PositioningConflictError export."""

    def test_is_exported_from_persistence_init(self) -> None:
        """PositioningConflictError is exported from persistence module."""
        from autom8_asana.persistence import PositioningConflictError as Exported

        assert Exported is PositioningConflictError

    def test_inherits_from_save_orchestration_error(self) -> None:
        """PositioningConflictError inherits from SaveOrchestrationError."""
        error = PositioningConflictError(insert_before="123", insert_after="456")
        assert isinstance(error, SaveOrchestrationError)


class TestRootLevelExport:
    """Tests for root-level exception exports."""

    def test_gid_validation_error_exported_at_root(self) -> None:
        """GidValidationError is exported from autom8_asana package."""
        from autom8_asana import GidValidationError as RootExport

        assert RootExport is GidValidationError


class TestLogContext:
    """Tests for LogContext dataclass."""

    def test_creation_with_all_fields(self) -> None:
        """LogContext can be created with all fields."""
        from autom8_asana.observability.context import LogContext

        ctx = LogContext(
            correlation_id="abc123",
            operation="track",
            entity_gid="1234567890",
            entity_type="task",
            duration_ms=45.2,
        )
        assert ctx.correlation_id == "abc123"
        assert ctx.operation == "track"
        assert ctx.entity_gid == "1234567890"
        assert ctx.entity_type == "task"
        assert ctx.duration_ms == 45.2

    def test_to_dict_excludes_none_values(self) -> None:
        """to_dict() excludes None values."""
        from autom8_asana.observability.context import LogContext

        ctx = LogContext(operation="commit", entity_gid="123")
        d = ctx.to_dict()
        assert d == {"operation": "commit", "entity_gid": "123"}
        assert "correlation_id" not in d

    def test_with_duration_creates_copy(self) -> None:
        """with_duration() creates a new LogContext with duration set."""
        from autom8_asana.observability.context import LogContext

        ctx = LogContext(correlation_id="abc", operation="track")
        ctx2 = ctx.with_duration(100.5)

        assert ctx2 is not ctx
        assert ctx2.duration_ms == 100.5
        assert ctx2.correlation_id == "abc"
        assert ctx.duration_ms is None  # Original unchanged

    def test_exported_from_observability_init(self) -> None:
        """LogContext is exported from observability module."""
        from autom8_asana.observability import LogContext

        assert LogContext is not None


class TestDefaultLogProviderEnhanced:
    """Tests for enhanced DefaultLogProvider."""

    def test_extra_parameter_supported(self) -> None:
        """DefaultLogProvider methods accept extra parameter."""
        from autom8_asana._defaults.log import DefaultLogProvider
        from autom8_asana.observability.context import LogContext

        # Create provider with DEBUG level
        provider = DefaultLogProvider(level=logging.DEBUG)
        ctx = LogContext(correlation_id="test123")

        # These should not raise
        provider.debug("Test %s", "message", extra=ctx.to_dict())
        provider.info("Test %s", "message", extra=ctx.to_dict())
        provider.warning("Test %s", "message", extra=ctx.to_dict())
        provider.error("Test %s", "message", extra=ctx.to_dict())

    def test_is_enabled_for_check(self) -> None:
        """isEnabledFor() checks logger level."""
        from autom8_asana._defaults.log import DefaultLogProvider

        provider = DefaultLogProvider(level=logging.WARNING)

        assert provider.isEnabledFor(logging.WARNING)
        assert provider.isEnabledFor(logging.ERROR)
        assert not provider.isEnabledFor(logging.DEBUG)
        assert not provider.isEnabledFor(logging.INFO)

    def test_custom_logger_name(self) -> None:
        """DefaultLogProvider accepts custom logger name."""
        from autom8_asana._defaults.log import DefaultLogProvider

        provider = DefaultLogProvider(name="custom_logger")
        assert provider._logger.name == "custom_logger"


class TestObservabilityHook:
    """Tests for ObservabilityHook protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """ObservabilityHook is runtime checkable."""
        from autom8_asana.protocols.observability import ObservabilityHook

        class MyHook:
            async def on_request_start(
                self, method: str, path: str, correlation_id: str
            ) -> None:
                pass

            async def on_request_end(
                self, method: str, path: str, status: int, duration_ms: float
            ) -> None:
                pass

            async def on_request_error(
                self, method: str, path: str, error: Exception
            ) -> None:
                pass

            async def on_rate_limit(self, retry_after_seconds: int) -> None:
                pass

            async def on_circuit_breaker_state_change(
                self, old_state: str, new_state: str
            ) -> None:
                pass

            async def on_retry(
                self, attempt: int, max_attempts: int, error: Exception
            ) -> None:
                pass

        assert isinstance(MyHook(), ObservabilityHook)

    def test_exported_from_protocols_init(self) -> None:
        """ObservabilityHook is exported from protocols module."""
        from autom8_asana.protocols import ObservabilityHook

        assert ObservabilityHook is not None

    def test_exported_from_root_init(self) -> None:
        """ObservabilityHook is exported from root package."""
        from autom8_asana import ObservabilityHook

        assert ObservabilityHook is not None


class TestNullObservabilityHook:
    """Tests for NullObservabilityHook default implementation."""

    @pytest.mark.asyncio
    async def test_all_methods_are_noop(self) -> None:
        """All NullObservabilityHook methods are no-ops."""
        from autom8_asana._defaults.observability import NullObservabilityHook

        hook = NullObservabilityHook()

        # All these should complete without error
        await hook.on_request_start("GET", "/tasks/123", "corr-id")
        await hook.on_request_end("GET", "/tasks/123", 200, 50.0)
        await hook.on_request_error("GET", "/tasks/123", Exception("test"))
        await hook.on_rate_limit(60)
        await hook.on_circuit_breaker_state_change("closed", "open")
        await hook.on_retry(1, 3, Exception("retry"))

    def test_exported_from_defaults_init(self) -> None:
        """NullObservabilityHook is exported from _defaults module."""
        from autom8_asana._defaults import NullObservabilityHook

        assert NullObservabilityHook is not None


class TestAsanaClientObservability:
    """Tests for AsanaClient observability integration."""

    def test_accepts_observability_hook_parameter(self) -> None:
        """AsanaClient accepts observability_hook parameter."""

        # This should not raise TypeError
        # We can't fully instantiate without auth, but we can check the signature
        import inspect

        from autom8_asana.client import AsanaClient

        sig = inspect.signature(AsanaClient.__init__)
        assert "observability_hook" in sig.parameters

    def test_observability_property_exposed(self) -> None:
        """AsanaClient exposes observability property."""
        from autom8_asana.client import AsanaClient

        assert hasattr(AsanaClient, "observability")


class TestStubModels:
    """Tests for stub business models."""

    def test_dna_exists_and_inherits_from_business_entity(self) -> None:
        """DNA model exists and inherits from BusinessEntity."""
        from autom8_asana.models.business import DNA
        from autom8_asana.models.business.base import BusinessEntity

        assert issubclass(DNA, BusinessEntity)

    def test_reconciliation_exists_and_inherits(self) -> None:
        """Reconciliation model exists and inherits from BusinessEntity."""
        from autom8_asana.models.business import Reconciliation
        from autom8_asana.models.business.base import BusinessEntity

        assert issubclass(Reconciliation, BusinessEntity)

    def test_videography_exists_and_inherits(self) -> None:
        """Videography model exists and inherits from BusinessEntity."""
        from autom8_asana.models.business import Videography
        from autom8_asana.models.business.base import BusinessEntity

        assert issubclass(Videography, BusinessEntity)

    def test_stub_models_exported_from_business_init(self) -> None:
        """All stub models are exported from business __init__."""
        from autom8_asana.models.business import DNA, Reconciliation, Videography

        assert DNA is not None
        assert Reconciliation is not None
        assert Videography is not None

    def test_dna_has_navigation_properties(self) -> None:
        """DNA has dna_holder and business navigation properties."""
        from autom8_asana.models.business import DNA

        dna = DNA(gid="123")
        assert hasattr(dna, "dna_holder")
        assert hasattr(dna, "business")
        assert dna.dna_holder is None
        assert dna.business is None

    def test_reconciliation_has_navigation_properties(self) -> None:
        """Reconciliation has reconciliation_holder and business properties."""
        from autom8_asana.models.business import Reconciliation

        recon = Reconciliation(gid="123")
        assert hasattr(recon, "reconciliation_holder")
        assert hasattr(recon, "business")
        assert recon.reconciliation_holder is None
        assert recon.business is None

    def test_videography_has_navigation_properties(self) -> None:
        """Videography has videography_holder and business properties."""
        from autom8_asana.models.business import Videography

        video = Videography(gid="123")
        assert hasattr(video, "videography_holder")
        assert hasattr(video, "business")
        assert video.videography_holder is None
        assert video.business is None


class TestAPICleanup:
    """Tests for API surface cleanup."""

    def test_private_functions_not_in_all(self) -> None:
        """Private functions are not exported in __all__."""
        from autom8_asana.models.business import __all__

        # These were removed per TDD-HARDENING-A/FR-ALL-*
        assert "_traverse_upward_async" not in __all__
        assert "_convert_to_typed_entity" not in __all__
        assert "_is_recoverable" not in __all__
