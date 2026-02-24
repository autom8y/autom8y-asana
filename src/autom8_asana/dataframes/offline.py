"""Offline DataFrame loader for S3-persisted section parquets.

Sync, no platform dependencies. Uses boto3 directly to load and
concatenate section parquets matching the SectionPersistence key
structure: dataframes/{project_gid}/sections/{section_gid}.parquet

Example:
    >>> from autom8_asana.dataframes.offline import load_project_dataframe
    >>> df = load_project_dataframe("1143843662099250")
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
) -> pl.DataFrame:
    """Load all section parquets for a project, concatenated.

    Reads from S3 using the same key structure as SectionPersistence.
    Uses paginated listing to handle projects with many sections.

    Args:
        project_gid: Asana project GID.
        bucket: S3 bucket name. Falls back to ASANA_CACHE_S3_BUCKET env var.
        region: AWS region (default: us-east-1).

    Returns:
        Concatenated DataFrame of all section parquets.

    Raises:
        ValueError: If no bucket is configured.
        FileNotFoundError: If no parquet files found under the project prefix.
    """
    df, _ = load_project_dataframe_with_meta(
        project_gid, bucket=bucket, region=region
    )
    return df


def load_project_dataframe_with_meta(
    project_gid: str,
    *,
    bucket: str | None = None,
    region: str = "us-east-1",
) -> tuple[pl.DataFrame, datetime | None]:
    """Load all section parquets for a project with S3 freshness metadata.

    Same behavior as load_project_dataframe(), but additionally returns the
    most recent LastModified timestamp from S3 object metadata.

    Args:
        project_gid: Asana project GID.
        bucket: S3 bucket name. Falls back to ASANA_CACHE_S3_BUCKET env var.
        region: AWS region (default: us-east-1).

    Returns:
        Tuple of (concatenated DataFrame, max LastModified datetime or None).

    Raises:
        ValueError: If no bucket is configured.
        FileNotFoundError: If no parquet files found under the project prefix.
    """
    bucket = bucket or os.environ.get("ASANA_CACHE_S3_BUCKET")
    if not bucket:
        raise ValueError(
            "No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET."
        )

    region = region or os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
    client = boto3.client("s3", region_name=region)

    prefix = f"dataframes/{project_gid}/sections/"
    keys, max_last_modified = _list_parquet_keys(client, bucket, prefix)

    if not keys:
        raise FileNotFoundError(f"No parquet files found under s3://{bucket}/{prefix}")

    frames: list[pl.DataFrame] = []
    for key in keys:
        resp = client.get_object(Bucket=bucket, Key=key)
        df = pl.read_parquet(io.BytesIO(resp["Body"].read()))
        frames.append(df)

    return pl.concat(frames, how="diagonal_relaxed"), max_last_modified


def _list_parquet_keys(
    client: Any,
    bucket: str,
    prefix: str,
) -> tuple[list[str], datetime | None]:
    """List all .parquet object keys under a prefix using pagination.

    Returns:
        Tuple of (list of S3 keys, max LastModified datetime or None).
    """
    paginator = client.get_paginator("list_objects_v2")
    keys: list[str] = []
    max_mtime: datetime | None = None
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".parquet"):
                keys.append(key)
                mtime = obj.get("LastModified")
                if mtime is not None and (max_mtime is None or mtime > max_mtime):
                    max_mtime = mtime
    return keys, max_mtime
