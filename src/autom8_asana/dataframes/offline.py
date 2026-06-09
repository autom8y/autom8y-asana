"""Offline DataFrame loader for S3-persisted section parquets.

Sync, no platform dependencies. Uses boto3 directly to load and
concatenate section parquets matching the SectionPersistence key structure.

SEAM-1 (ADR-SEAM1) layouts:
    Legacy (entity-agnostic): dataframes/{project_gid}/sections/{section_gid}.parquet
    v2 (entity-segmented):    dataframes/{project_gid}/{entity_type}/sections/{section_gid}.parquet

This is the ONE reader that historically had no entity_type in scope (a sync
CLI). It now accepts an optional ``entity_type``:
    - When provided: scan the v2 prefix; fall back to the legacy prefix on miss.
    - When omitted: scan-all -- concatenate BOTH the legacy prefix AND every
      ``dataframes/{project_gid}/*/sections/`` v2 prefix, preserving the CLI's
      "load everything for this project" semantics. Pass ``--entity-type offer``
      (metrics CLI) to get the clean, single-entity re-derived count.

Example:
    >>> from autom8_asana.dataframes.offline import load_project_dataframe
    >>> df = load_project_dataframe("1143843662099250", entity_type="offer")
    >>> print(f"{len(df)} rows, {df.columns}")
"""

from __future__ import annotations

import io
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

import boto3
import polars as pl


def load_project_dataframe(
    project_gid: str,
    *,
    bucket: str | None = None,
    region: str = "us-east-1",
    entity_type: str | None = None,
) -> pl.DataFrame:
    """Load all section parquets for a project, concatenated.

    Reads from S3 using the same key structure as SectionPersistence.
    Uses paginated listing to handle projects with many sections.

    Args:
        project_gid: Asana project GID.
        bucket: S3 bucket name. Falls back to ASANA_CACHE_S3_BUCKET env var.
        region: AWS region (default: us-east-1).
        entity_type: SEAM-1 entity type. When given, reads the v2 prefix
            (legacy fallback on miss). When None, scans ALL layouts for the
            project (legacy + every v2 entity segment).

    Returns:
        Concatenated DataFrame of all section parquets.

    Raises:
        ValueError: If no bucket is configured.
        FileNotFoundError: If no parquet files found under the project prefix.
    """
    df, _ = load_project_dataframe_with_meta(
        project_gid, bucket=bucket, region=region, entity_type=entity_type
    )
    return df


def load_project_dataframe_with_meta(
    project_gid: str,
    *,
    bucket: str | None = None,
    region: str = "us-east-1",
    entity_type: str | None = None,
) -> tuple[pl.DataFrame, datetime | None]:
    """Load all section parquets for a project with S3 freshness metadata.

    Same behavior as load_project_dataframe(), but additionally returns the
    most recent LastModified timestamp from S3 object metadata.

    SEAM-1 layout resolution:
        - ``entity_type`` given: read ``dataframes/{gid}/{entity_type}/sections/``;
          on miss fall back to the legacy ``dataframes/{gid}/sections/`` prefix.
        - ``entity_type`` None: scan-all -- concat the legacy prefix AND every
          ``dataframes/{gid}/{*}/sections/`` v2 prefix (one paginated list of the
          whole project prefix, filtered to ``/sections/`` parquet keys).

    Args:
        project_gid: Asana project GID.
        bucket: S3 bucket name. Falls back to ASANA_CACHE_S3_BUCKET env var.
        region: AWS region (default: us-east-1).
        entity_type: SEAM-1 entity type (see above).

    Returns:
        Tuple of (concatenated DataFrame, max LastModified datetime or None).

    Raises:
        ValueError: If no bucket is configured.
        FileNotFoundError: If no parquet files found under the project prefix.
    """
    bucket = bucket or os.environ.get("ASANA_CACHE_S3_BUCKET")
    if not bucket:
        raise ValueError("No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.")

    region = region or os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
    client = boto3.client("s3", region_name=region)

    keys, max_last_modified, scanned_prefix = _resolve_section_keys(
        client, bucket, project_gid, entity_type
    )

    if not keys:
        raise FileNotFoundError(f"No parquet files found under s3://{bucket}/{scanned_prefix}")

    frames: list[pl.DataFrame] = []
    for key in keys:
        resp = client.get_object(Bucket=bucket, Key=key)
        df = pl.read_parquet(io.BytesIO(resp["Body"].read()))
        frames.append(df)

    return pl.concat(frames, how="diagonal_relaxed"), max_last_modified


def _resolve_section_keys(
    client: Any,
    bucket: str,
    project_gid: str,
    entity_type: str | None,
) -> tuple[list[str], datetime | None, str]:
    """Resolve the section parquet keys for a project under the SEAM-1 layouts.

    Returns:
        Tuple of (keys, max LastModified, the prefix scanned for error messages).
    """
    if entity_type:
        # v2-first, legacy fallback.
        v2_prefix = f"dataframes/{project_gid}/{entity_type}/sections/"
        keys, max_mtime = _list_parquet_keys(client, bucket, v2_prefix)
        if keys:
            return keys, max_mtime, v2_prefix
        legacy_prefix = f"dataframes/{project_gid}/sections/"
        keys, max_mtime = _list_parquet_keys(client, bucket, legacy_prefix)
        return keys, max_mtime, v2_prefix

    # Scan-all: one paginated list of the whole project prefix, keep any
    # ``.../sections/*.parquet`` key (matches both legacy and any v2 segment).
    project_prefix = f"dataframes/{project_gid}/"
    keys, max_mtime = _list_parquet_keys(
        client, bucket, project_prefix, require_sections_segment=True
    )
    return keys, max_mtime, project_prefix


def _list_parquet_keys(
    client: Any,
    bucket: str,
    prefix: str,
    *,
    require_sections_segment: bool = False,
) -> tuple[list[str], datetime | None]:
    """List all .parquet object keys under a prefix using pagination.

    Args:
        require_sections_segment: When True (scan-all mode), only keep keys whose
            path contains a ``/sections/`` segment, so non-section artifacts
            (dataframe.parquet, watermark.json) under the project prefix are
            excluded.

    Returns:
        Tuple of (list of S3 keys, max LastModified datetime or None).
    """
    paginator = client.get_paginator("list_objects_v2")
    keys: list[str] = []
    max_mtime: datetime | None = None
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".parquet"):
                continue
            if require_sections_segment and "/sections/" not in key:
                continue
            keys.append(key)
            mtime = obj.get("LastModified")
            if mtime is not None and (max_mtime is None or mtime > max_mtime):
                max_mtime = mtime
    return keys, max_mtime
