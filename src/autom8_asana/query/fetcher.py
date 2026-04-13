"""DataServiceJoinFetcher: fetches analytics data for cross-service join enrichment.

Given a primary DataFrame with office_phone (and optionally vertical),
batch-fetches metrics from DataServiceClient and returns a pl.DataFrame
suitable for left-join via execute_join().

Per SPIKE.md Phase 1: This fetcher relies on DataServiceClient.get_insights_batch_async()
which handles internal PVP chunking. With max_batch_size=500 (P2 prerequisite),
4000 offers = 8 HTTP requests (~800ms). If max_batch_size is ever lowered below
the typical unique PVP count, the fetcher must implement pre-chunking (P3, deferred).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger
from autom8y_telemetry import trace_computation

if TYPE_CHECKING:
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.models.contracts import PhoneVerticalPair

logger = get_logger(__name__)


class DataServiceJoinFetcher:
    """Fetches data-service metrics as a pl.DataFrame for join enrichment.

    Given a primary DataFrame with office_phone (and optionally vertical),
    batch-fetches metrics from DataServiceClient and returns a DataFrame
    suitable for left-join via execute_join().
    """

    def __init__(self, data_client: DataServiceClient) -> None:
        self._client = data_client

    @trace_computation(
        "data_service.fetch_join",
        record_dataframe_shape=True,
        df_param="primary_df",
        engine="autom8y-asana",
    )
    async def fetch_for_join(
        self,
        primary_df: pl.DataFrame,
        factory: str,
        period: str,
        join_key: str = "office_phone",
    ) -> pl.DataFrame:
        """Extract phone/vertical pairs from primary, batch-fetch, return DataFrame.

        Args:
            primary_df: Filtered primary entity DataFrame (has office_phone column).
            factory: DataService factory name (e.g., "spend", "leads", "campaigns").
            period: Period filter (e.g., "T30", "LIFETIME").
            join_key: Column to extract phone/vertical pairs from.

        Returns:
            pl.DataFrame with office_phone, vertical, and metric columns.
            Empty DataFrame if no pairs to fetch or all fetches fail.
        """
        from opentelemetry import trace as _otel_trace

        _span = _otel_trace.get_current_span()
        _fetch_start = time.perf_counter()

        pairs = self._extract_pvps(primary_df, join_key)
        if not pairs:
            logger.info(
                "data_service_join_no_pvps",
                extra={"factory": factory, "join_key": join_key},
            )
            _span.set_attribute(
                "computation.duration_ms", (time.perf_counter() - _fetch_start) * 1000
            )
            _span.set_attribute("computation.batch.success_count", 0)
            _span.set_attribute("computation.batch.failure_count", 0)
            return pl.DataFrame()

        logger.info(
            "data_service_join_fetch_start",
            extra={
                "factory": factory,
                "period": period,
                "unique_pvps": len(pairs),
            },
        )

        batch_response = await self._client.get_insights_batch_async(
            pairs=pairs,
            factory=factory,
            period=period,
        )

        frames: list[pl.DataFrame] = []
        for result in batch_response.results.values():
            if result.success and result.response is not None:
                df = result.response.to_dataframe()
                if df.height > 0:
                    frames.append(df)

        _span.set_attribute("computation.batch.success_count", batch_response.success_count)
        _span.set_attribute("computation.batch.failure_count", batch_response.failure_count)

        if not frames:
            logger.warning(
                "data_service_join_no_results",
                extra={
                    "factory": factory,
                    "period": period,
                    "total_pvps": len(pairs),
                    "success_count": batch_response.success_count,
                    "failure_count": batch_response.failure_count,
                },
            )
            _span.set_attribute(
                "computation.duration_ms", (time.perf_counter() - _fetch_start) * 1000
            )
            return pl.DataFrame()

        combined = pl.concat(frames)

        logger.info(
            "data_service_join_fetch_complete",
            extra={
                "factory": factory,
                "period": period,
                "rows": combined.height,
                "columns": combined.width,
                "success_count": batch_response.success_count,
                "failure_count": batch_response.failure_count,
            },
        )

        _span.set_attribute("computation.duration_ms", (time.perf_counter() - _fetch_start) * 1000)
        return combined

    def _extract_pvps(self, df: pl.DataFrame, join_key: str) -> list[PhoneVerticalPair]:
        """Extract unique (phone, vertical) pairs from DataFrame.

        Args:
            df: Primary entity DataFrame.
            join_key: Column containing phone numbers.

        Returns:
            List of unique PhoneVerticalPair instances.
        """
        from autom8_asana.models.contracts import PhoneVerticalPair

        if join_key not in df.columns:
            return []

        has_vertical = "vertical" in df.columns
        select_cols = [join_key] + (["vertical"] if has_vertical else [])

        # Deduplicate before iterating
        unique_df = df.select(select_cols).unique()

        pairs: list[PhoneVerticalPair] = []
        for row in unique_df.to_dicts():
            phone = row.get(join_key)
            if not phone:
                continue
            vertical = row.get("vertical", "unknown") if has_vertical else "unknown"
            if not vertical:
                vertical = "unknown"
            pairs.append(PhoneVerticalPair(phone=str(phone), vertical=str(vertical)))

        return pairs
