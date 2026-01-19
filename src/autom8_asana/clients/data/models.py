"""Request/response models for autom8_data insights API.

Per TDD-INSIGHTS-001 Section 4.2-4.4: Models with dtype metadata and staleness support.
Per ADR-INS-002: JSON response with dtype metadata (Arrow deferred).
Per ADR-INS-004 (revised): Staleness indicators for cache fallback.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl

# Import PhoneVerticalPair at runtime for Pydantic model resolution
# This is needed for BatchInsightsResult and BatchInsightsResponse models
from autom8_asana.models.contracts import PhoneVerticalPair


class InsightsRequest(BaseModel):
    """Request body for insights factory API.

    Maps to POST /api/v1/factory/{factory_name} request body.

    Attributes:
        office_phone: E.164 formatted phone number for business identification.
        vertical: Business vertical (e.g., chiropractic, dental).
        insights_period: Time period preset (lifetime, t30, l7, etc.).
        start_date: Custom start date (for date-range queries).
        end_date: Custom end date (for date-range queries).
        metrics: Override default metrics returned.
        dimensions: Override default dimensions for grouping.
        groups: Additional grouping columns.
        break_down: Break down results by these columns.
        refresh: Force cache refresh on server.
        filters: Additional factory-specific filters.

    Example:
        >>> request = InsightsRequest(
        ...     office_phone="+17705753103",
        ...     vertical="chiropractic",
        ...     insights_period="t30",
        ...     metrics=["spend", "impressions"],
        ... )
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
    )

    # Filtering (required)
    office_phone: str
    vertical: str

    # Time period
    insights_period: str | None = Field(default="lifetime")
    start_date: date | None = None
    end_date: date | None = None

    # Grouping
    metrics: list[str] | None = None
    dimensions: list[str] | None = None
    groups: list[str] | None = None
    break_down: list[str] | None = None

    # Caching
    refresh: bool = False

    # Additional factory-specific filters
    filters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("insights_period")
    @classmethod
    def validate_period(cls, v: str | None) -> str | None:
        """Validate period format.

        Valid formats:
        - Standard: lifetime, date, day, week, month, quarter, year
        - Trailing: t1, t3, t7, t10, t14, t30, t90, t180, t365
        - Last: l1, l3, l7, l10, l14, l30, l90, l180, l365, l24h

        Args:
            v: Period value to validate.

        Returns:
            Normalized period string (lowercase).

        Raises:
            ValueError: If period format is invalid.
        """
        if v is None:
            return v

        v_lower = v.lower()
        valid_standards = {
            "lifetime",
            "date",
            "day",
            "week",
            "month",
            "quarter",
            "year",
        }

        if v_lower in valid_standards:
            return v_lower

        # Trailing days: t{N}
        if re.match(r"^t\d+$", v_lower):
            return v_lower

        # Last days: l{N} or l{N}h
        if re.match(r"^l\d+h?$", v_lower):
            return v_lower

        raise ValueError(
            f"Invalid period format: {v}. Expected: lifetime, t30, l7, etc."
        )


class ColumnInfo(BaseModel):
    """Column metadata for dtype preservation.

    Per TDD-INSIGHTS-001: Include dtype hints for DataFrame reconstruction.

    Attributes:
        name: Column name in the DataFrame.
        dtype: Data type string (int64, float64, datetime64[ns], object, etc.).
        nullable: Whether the column can contain null values.
    """

    model_config = ConfigDict(
        extra="ignore",
    )

    name: str
    dtype: str
    nullable: bool = True


class InsightsMetadata(BaseModel):
    """Metadata about the insights response.

    Per TDD-INSIGHTS-001: Include sort_history from DataFrame.attrs.
    Per ADR-INS-004 (revised): Include staleness indicators for cache fallback.

    Attributes:
        factory: Name of the insights factory used.
        frame_type: Type of DataFrame returned (optional).
        insights_period: Period used for the query.
        row_count: Number of rows in the response.
        column_count: Number of columns in the response.
        columns: List of column metadata with dtype info.
        cache_hit: Whether response was served from server cache.
        duration_ms: Server-side processing duration in milliseconds.
        sort_history: List of columns the data was sorted by.
        is_stale: True if served from client cache during service unavailability.
        cached_at: When response was originally cached (if stale).
    """

    model_config = ConfigDict(
        extra="ignore",
    )

    factory: str
    frame_type: str | None = None
    insights_period: str | None = None

    row_count: int
    column_count: int
    columns: list[ColumnInfo]

    cache_hit: bool
    duration_ms: float

    sort_history: list[str] | None = None

    # Staleness indicators (per ADR-INS-004 revision)
    is_stale: bool = False
    cached_at: datetime | None = None


class InsightsResponse(BaseModel):
    """Response from insights factory API.

    Per TDD-INSIGHTS-001 FR-005: Contains data, metadata, and DataFrame conversion.

    The response contains raw data as a list of dictionaries, along with metadata
    about the columns and their types. Use `to_dataframe()` or `to_pandas()` to
    convert to DataFrame format with proper dtypes.

    Attributes:
        data: List of row dictionaries from the insights query.
        metadata: Response metadata including column types and cache info.
        request_id: Unique request correlation ID for tracing.
        warnings: List of warning messages (e.g., data quality issues).

    Example:
        >>> response = InsightsResponse(
        ...     data=[{"spend": 100.0, "impressions": 5000}],
        ...     metadata=InsightsMetadata(
        ...         factory="account",
        ...         row_count=1,
        ...         column_count=2,
        ...         columns=[
        ...             ColumnInfo(name="spend", dtype="float64"),
        ...             ColumnInfo(name="impressions", dtype="int64"),
        ...         ],
        ...         cache_hit=False,
        ...         duration_ms=50.0,
        ...     ),
        ...     request_id="abc-123",
        ... )
        >>> df = response.to_dataframe()
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="ignore",
    )

    data: list[dict[str, Any]]
    metadata: InsightsMetadata
    request_id: str
    warnings: list[str] = Field(default_factory=list)

    def to_dataframe(self) -> pl.DataFrame:
        """Convert response to Polars DataFrame.

        Per ADR-0028: autom8_asana uses Polars as primary DataFrame library.
        Per TDD-INSIGHTS-001 FR-005.4: Reconstructs dtypes from metadata.

        Returns:
            Polars DataFrame with proper dtypes based on column metadata.
            Empty DataFrame with schema if no data rows.

        Example:
            >>> df = response.to_dataframe()
            >>> df.schema
            {'spend': Float64, 'impressions': Int64}
        """
        import polars as pl

        if not self.data:
            # Return empty DataFrame with schema from metadata
            schema = {
                col.name: self._polars_dtype(col.dtype)
                for col in self.metadata.columns
                if self._polars_dtype(col.dtype) is not None
            }
            return pl.DataFrame(schema=schema)

        df = pl.DataFrame(self.data)

        # Cast columns to correct dtypes based on metadata
        for col_info in self.metadata.columns:
            if col_info.name in df.columns:
                target_dtype = self._polars_dtype(col_info.dtype)
                if target_dtype is not None:
                    try:
                        df = df.with_columns(pl.col(col_info.name).cast(target_dtype))
                    except Exception:
                        # Log warning and continue with original dtype
                        # This handles cases where the data cannot be cast
                        pass

        return df

    def to_pandas(self) -> pd.DataFrame:
        """Convert response to pandas DataFrame.

        Per TDD-INSIGHTS-001 FR-005.5: Backward compatibility with pandas consumers.

        Returns:
            pandas DataFrame converted from Polars DataFrame.

        Example:
            >>> pdf = response.to_pandas()
            >>> pdf.dtypes
            spend          float64
            impressions      int64
            dtype: object
        """
        return self.to_dataframe().to_pandas()

    @staticmethod
    def _polars_dtype(dtype_str: str) -> type[pl.DataType] | None:
        """Map dtype string to Polars dtype.

        Args:
            dtype_str: String representation of dtype (e.g., "int64", "float64").

        Returns:
            Corresponding Polars DataType class, or None if unknown.
        """
        import polars as pl

        dtype_map: dict[str, type[pl.DataType]] = {
            "int64": pl.Int64,
            "int32": pl.Int32,
            "int16": pl.Int16,
            "int8": pl.Int8,
            "uint64": pl.UInt64,
            "uint32": pl.UInt32,
            "uint16": pl.UInt16,
            "uint8": pl.UInt8,
            "float64": pl.Float64,
            "float32": pl.Float32,
            "bool": pl.Boolean,
            "boolean": pl.Boolean,
            "object": pl.Utf8,
            "string": pl.Utf8,
            "str": pl.Utf8,
            "datetime64[ns]": pl.Datetime,
            "datetime": pl.Datetime,
            "date": pl.Date,
        }
        return dtype_map.get(dtype_str.lower())


class BatchInsightsResult(BaseModel):
    """Result for a single PVP in batch response.

    Per TDD-INSIGHTS-001 Section 4.4: Result model for batch operations.

    Attributes:
        pvp: The PhoneVerticalPair that was queried.
        response: Successful InsightsResponse, or None if failed.
        error: Error message if the request failed.

    Example:
        >>> result = BatchInsightsResult(
        ...     pvp=PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
        ...     response=insights_response,
        ... )
        >>> result.success
        True
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="ignore",
    )

    pvp: PhoneVerticalPair
    response: InsightsResponse | None = None
    error: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success(self) -> bool:
        """Whether this PVP succeeded.

        Returns:
            True if response is present and no error occurred.
        """
        return self.response is not None and self.error is None


class BatchInsightsResponse(BaseModel):
    """Response from batch insights request.

    Per TDD-INSIGHTS-001 Section 4.4: Batch response model.
    Per FR-006: Partial failures included in response, not raised.

    Attributes:
        results: Dictionary mapping canonical_key to BatchInsightsResult.
        request_id: Unique batch request correlation ID.
        total_count: Total number of PVPs in the batch.
        success_count: Number of successful PVP requests.
        failure_count: Number of failed PVP requests.

    Example:
        >>> batch_response = await client.get_insights_batch_async(pairs)
        >>> print(f"Success: {batch_response.success_count}/{batch_response.total_count}")
        >>> df = batch_response.to_dataframe()  # Combines all successful results
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="ignore",
    )

    results: dict[str, BatchInsightsResult]  # keyed by canonical_key
    request_id: str
    total_count: int
    success_count: int
    failure_count: int

    def to_dataframe(self) -> pl.DataFrame:
        """Concatenate all successful results into single DataFrame.

        Per TDD-INSIGHTS-001 FR-006.5: Combines all successful responses
        into a single DataFrame with _pvp_key column for grouping.

        Returns:
            Combined Polars DataFrame from all successful responses.
            Empty DataFrame if no successful results.

        Example:
            >>> df = batch_response.to_dataframe()
            >>> df.group_by("_pvp_key").agg(pl.sum("spend"))
        """
        import polars as pl

        dfs = []
        for result in self.results.values():
            if result.success and result.response:
                df = result.response.to_dataframe()
                # Add canonical_key column for grouping
                df = df.with_columns(pl.lit(result.pvp.canonical_key).alias("_pvp_key"))
                dfs.append(df)

        if not dfs:
            return pl.DataFrame()

        return pl.concat(dfs)

    def to_pandas(self) -> pd.DataFrame:
        """Convert combined results to pandas DataFrame.

        Returns:
            pandas DataFrame converted from combined Polars DataFrame.

        Example:
            >>> batch_response = await client.get_insights_batch_async(pairs)
            >>> pdf = batch_response.to_pandas()
            >>> pdf.groupby("_pvp_key")["spend"].sum()
        """
        return self.to_dataframe().to_pandas()

    def get(self, pvp: PhoneVerticalPair) -> BatchInsightsResult | None:
        """Get result for a specific PhoneVerticalPair.

        Args:
            pvp: The PhoneVerticalPair to look up.

        Returns:
            BatchInsightsResult for the PVP, or None if not in batch.
        """
        return self.results.get(pvp.canonical_key)

    def successful_results(self) -> list[BatchInsightsResult]:
        """Get all successful results.

        Returns:
            List of BatchInsightsResult where success is True.
        """
        return [r for r in self.results.values() if r.success]

    def failed_results(self) -> list[BatchInsightsResult]:
        """Get all failed results.

        Returns:
            List of BatchInsightsResult where success is False.
        """
        return [r for r in self.results.values() if not r.success]
