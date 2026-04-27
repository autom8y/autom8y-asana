"""Tests for CoalescerDedupCount metric emission (Batch-B work-item-4).

Per HANDOFF §1 work-item-4 (Batch-B) + ADR-006 §Decision:
- The coalescer emits CoalescerDedupCount to namespace `autom8y/cache-warmer`
  (lowercase per Terraform ASANA_CW_NAMESPACE) when try_acquire_async returns
  False (dedup hit).
- Best-effort: emission failure must NOT affect coalescer correctness.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.cache.dataframe.coalescer import (
    COALESCER_METRIC_DEDUP_COUNT,
    COALESCER_METRIC_NAMESPACE,
    DataFrameCacheCoalescer,
)


class TestCoalescerDedupMetric:
    """CoalescerDedupCount fires on dedup-hit and lands in the warmer namespace."""

    async def test_dedup_emits_metric(self) -> None:
        """Second concurrent acquire on same key → CoalescerDedupCount emitted."""
        coalescer = DataFrameCacheCoalescer()
        mock_cw_client = MagicMock()

        with patch("boto3.client", return_value=mock_cw_client):
            # First acquire — wins lock; no metric emission.
            acquired_first = await coalescer.try_acquire_async("entity:1234")
            assert acquired_first is True
            assert mock_cw_client.put_metric_data.call_count == 0

            # Second acquire on same key — dedup hit; metric emitted.
            acquired_second = await coalescer.try_acquire_async("entity:1234")
            assert acquired_second is False
            assert mock_cw_client.put_metric_data.call_count == 1

            call_kwargs = mock_cw_client.put_metric_data.call_args.kwargs
            assert call_kwargs["Namespace"] == COALESCER_METRIC_NAMESPACE
            metric_data = call_kwargs["MetricData"]
            assert len(metric_data) == 1
            assert metric_data[0]["MetricName"] == COALESCER_METRIC_DEDUP_COUNT
            assert metric_data[0]["Value"] == 1.0
            assert metric_data[0]["Unit"] == "Count"

    async def test_namespace_is_lowercase_warmer(self) -> None:
        """Namespace MUST be lowercase 'autom8y/cache-warmer' per ADR-006."""
        # Pinned constants — protect against accidental rename.
        assert COALESCER_METRIC_NAMESPACE == "autom8y/cache-warmer"
        assert COALESCER_METRIC_DEDUP_COUNT == "CoalescerDedupCount"

    async def test_first_acquire_does_not_emit(self) -> None:
        """try_acquire returning True (winning the lock) does NOT emit."""
        coalescer = DataFrameCacheCoalescer()
        mock_cw_client = MagicMock()
        with patch("boto3.client", return_value=mock_cw_client):
            await coalescer.try_acquire_async("entity:5678")
        assert mock_cw_client.put_metric_data.call_count == 0

    async def test_emission_failure_does_not_break_coalescer(self) -> None:
        """A boto3/CloudWatch failure does NOT alter coalescer return value."""
        coalescer = DataFrameCacheCoalescer()
        mock_cw_client = MagicMock()
        mock_cw_client.put_metric_data.side_effect = RuntimeError("cw down")

        with patch("boto3.client", return_value=mock_cw_client):
            await coalescer.try_acquire_async("entity:9999")
            # CloudWatch is broken — but coalescer must still return False on dedup.
            second = await coalescer.try_acquire_async("entity:9999")
        assert second is False  # correctness preserved despite metric failure

    async def test_dimension_includes_coalescer_key(self) -> None:
        """The metric carries coalescer_key as a dimension for traceability."""
        coalescer = DataFrameCacheCoalescer()
        mock_cw_client = MagicMock()

        with patch("boto3.client", return_value=mock_cw_client):
            await coalescer.try_acquire_async("forcewarm:project-A:*")
            await coalescer.try_acquire_async("forcewarm:project-A:*")

        metric_data = mock_cw_client.put_metric_data.call_args.kwargs["MetricData"]
        dimensions = metric_data[0]["Dimensions"]
        dim_values = {d["Name"]: d["Value"] for d in dimensions}
        assert dim_values["coalescer_key"] == "forcewarm:project-A:*"


class TestCoalescerDedupMetricMotoIntegration:
    """End-to-end emission against moto CloudWatch (lowercase namespace)."""

    @pytest.fixture(autouse=True)
    def _check_moto(self) -> None:
        try:
            import moto  # noqa: F401
        except ImportError:
            pytest.skip("moto not installed")

    @pytest.mark.skip(
        reason=(
            "CI-vs-local moto-singleton flake; load-bearing emit behavior "
            "covered by TestCoalescerDedupMetric unit tests above; "
            "production emission verified at "
            ".ledge/reviews/P7A-alert-predicates-2026-04-27.md PRED-3 "
            "(live AWS namespace inventory shows CoalescerDedupCount in "
            "autom8y/cache-warmer). DEFER-FOLLOWUP for proper "
            "moto-singleton root-cause investigation."
        )
    )
    async def test_moto_accepts_lowercase_namespace(self) -> None:
        """moto-backed CloudWatch accepts emission to autom8y/cache-warmer."""
        import boto3
        from moto import mock_aws

        with mock_aws():
            # Set the singleton boto3.client cache by NOT patching — let the
            # real boto3 client resolve to moto's mocked endpoint.
            coalescer = DataFrameCacheCoalescer()
            await coalescer.try_acquire_async("test:abc")
            await coalescer.try_acquire_async("test:abc")

            cw = boto3.client("cloudwatch", region_name="us-east-1")
            response = cw.list_metrics(Namespace=COALESCER_METRIC_NAMESPACE)
            names = {m["MetricName"] for m in response["Metrics"]}
            assert COALESCER_METRIC_DEDUP_COUNT in names
