#!/usr/bin/env python3
"""Calculate metrics from Business Offers section parquets.

Unified CLI replacing calc_mrr.py and calc_ad_spend.py.

Usage:
    python scripts/calc_metric.py active_mrr
    python scripts/calc_metric.py active_ad_spend --verbose
    python scripts/calc_metric.py --list

Environment Variables:
    ASANA_CACHE_S3_BUCKET  - S3 bucket for persistence (required)
    ASANA_CACHE_S3_REGION  - AWS region (default: us-east-1)
"""

from __future__ import annotations

import argparse
import io
import os
import sys

import boto3
import polars as pl

from autom8_asana.metrics import MetricRegistry, SectionIndex, compute_metric, resolve_metric_scope


# Business Offers project GID (same as Offer.PRIMARY_PROJECT_GID)
PROJECT_GID = "1143843662099250"


def load_section_parquet(bucket: str, project_gid: str, section_gid: str) -> pl.DataFrame:
    """Load a section parquet from S3.

    Reads from the same S3 key structure used by SectionPersistence:
        dataframes/{project_gid}/sections/{section_gid}.parquet

    Args:
        bucket: S3 bucket name.
        project_gid: Asana project GID.
        section_gid: Asana section GID.

    Returns:
        Polars DataFrame from the parquet file.

    Raises:
        botocore.exceptions.ClientError: If the S3 object doesn't exist.
    """
    region = os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name=region)

    key = f"dataframes/{project_gid}/sections/{section_gid}.parquet"
    response = s3.get_object(Bucket=bucket, Key=key)
    buf = io.BytesIO(response["Body"].read())
    return pl.read_parquet(buf)


def main() -> None:
    registry = MetricRegistry()

    parser = argparse.ArgumentParser(
        description="Calculate metrics from Asana section data",
    )
    parser.add_argument(
        "metric",
        nargs="?",
        help="Metric name to compute (e.g., active_mrr, active_ad_spend)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-row breakdown",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_metrics",
        help="List all available metrics",
    )
    args = parser.parse_args()

    # --list mode
    if args.list_metrics:
        names = registry.list_metrics()
        print("Available metrics:")
        for name in names:
            metric = registry.get_metric(name)
            print(f"  {name:25s} {metric.description}")
        return

    # Require metric name
    if not args.metric:
        parser.error("metric name is required (or use --list)")

    # Look up metric
    try:
        metric = registry.get_metric(args.metric)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Resolve section name → GID if needed
    if metric.scope.section is None and metric.scope.section_name is not None:
        index = SectionIndex.from_enum_fallback(metric.scope.entity_type)
        metric = resolve_metric_scope(metric, index)

    # Load data
    bucket = os.environ.get("ASANA_CACHE_S3_BUCKET")
    if not bucket:
        print("ERROR: Set ASANA_CACHE_S3_BUCKET environment variable.", file=sys.stderr)
        sys.exit(1)

    if metric.scope.section is None:
        print("ERROR: Metrics without a section scope are not yet supported.", file=sys.stderr)
        sys.exit(1)

    df = load_section_parquet(bucket, PROJECT_GID, metric.scope.section)
    section_label = metric.scope.section_name or metric.scope.section
    print(f"Section {section_label}: {len(df)} tasks")

    # Compute
    result = compute_metric(metric, df, verbose=args.verbose)

    # Aggregate and display
    total = result[metric.expr.column].sum()
    if metric.scope.dedup_keys:
        dedup_desc = ", ".join(metric.scope.dedup_keys)
        print(f"Unique ({dedup_desc}) combos: {len(result)}")
    print(f"{metric.description}: ${total:,.0f}")


if __name__ == "__main__":
    main()
