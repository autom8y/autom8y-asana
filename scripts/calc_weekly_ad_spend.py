#!/usr/bin/env python3
"""Calculate weekly ad spend from Business Offers using section classification.

Unlike calc_metric.py (which reads a single section parquet), this script
loads ALL offer section parquets and applies the OFFER_CLASSIFIER "active"
status group to capture offers across all active-classified sections
(ACTIVE, STAGED, OPTIMIZE *, etc.).

Weekly ad spend is a Unit-level value that cascades to sibling Offers. To
avoid inflation, results are deduped by (office_phone, vertical) -- the
phone-vertical pair that uniquely identifies a Unit.

Usage:
    python scripts/calc_weekly_ad_spend.py
    python scripts/calc_weekly_ad_spend.py --verbose
    python scripts/calc_weekly_ad_spend.py --classification billable

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

# Business Offers project GID (Offer.PRIMARY_PROJECT_GID)
OFFER_PROJECT_GID = "1143843662099250"

# OFFER_CLASSIFIER groups -- mirrors activity.py exactly.
# Kept inline to avoid importing the full SDK (platform deps not required).
OFFER_ACTIVE_SECTIONS: set[str] = {
    "pending approval",
    "call",
    "optimize - human review",
    "optimize quantity - request asset edit",
    "optimize quantity - decrease lead friction",
    "optimize quantity - update offer price too high",
    "optimize quantity - update targeting of proven asset",
    "optimize quantity - update offer name",
    "optimize quality - update targeting",
    "optimize quality - poor show rates",
    "optimize quality - pending leads and/or update targeting",
    "restart - request testimonial",
    "run optimizations",
    "staging",
    "staged",
    "active",
    "restart - pending leads",
    "system error",
    "rejections / review",
    "review optimization",
    "manual",
}

OFFER_ACTIVATING_SECTIONS: set[str] = {
    "activating",
    "launch error",
    "implementing",
    "new launch review",
    "awaiting access",
}

OFFER_INACTIVE_SECTIONS: set[str] = {
    "account error",
    "awaiting rep update",
    "inactive",
}

CLASSIFICATION_GROUPS: dict[str, set[str]] = {
    "active": OFFER_ACTIVE_SECTIONS,
    "activating": OFFER_ACTIVATING_SECTIONS,
    "inactive": OFFER_INACTIVE_SECTIONS,
    "billable": OFFER_ACTIVE_SECTIONS | OFFER_ACTIVATING_SECTIONS,
}

DEDUP_KEYS = ["office_phone", "vertical"]


def list_section_parquets(
    s3_client: boto3.client, bucket: str, project_gid: str
) -> list[str]:
    """List all section parquet keys under a project prefix."""
    prefix = f"dataframes/{project_gid}/sections/"
    resp = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    contents = resp.get("Contents", [])
    return [obj["Key"] for obj in contents if obj["Key"].endswith(".parquet")]


def load_all_sections(
    s3_client: boto3.client, bucket: str, project_gid: str
) -> pl.DataFrame:
    """Load and concatenate all section parquets for a project."""
    keys = list_section_parquets(s3_client, bucket, project_gid)
    if not keys:
        print(f"ERROR: No parquets found under dataframes/{project_gid}/sections/", file=sys.stderr)
        sys.exit(1)

    frames: list[pl.DataFrame] = []
    for key in keys:
        resp = s3_client.get_object(Bucket=bucket, Key=key)
        df = pl.read_parquet(io.BytesIO(resp["Body"].read()))
        frames.append(df)

    return pl.concat(frames, how="diagonal_relaxed")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate weekly ad spend using section classification groups",
    )
    parser.add_argument(
        "--classification", "-c",
        default="active",
        choices=sorted(CLASSIFICATION_GROUPS),
        help="Classification group to filter by (default: active)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-row breakdown after dedup",
    )
    args = parser.parse_args()

    bucket = os.environ.get("ASANA_CACHE_S3_BUCKET")
    if not bucket:
        print("ERROR: Set ASANA_CACHE_S3_BUCKET environment variable.", file=sys.stderr)
        sys.exit(1)

    region = os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name=region)

    # Load all offer sections
    all_offers = load_all_sections(s3, bucket, OFFER_PROJECT_GID)
    print(f"Loaded {len(all_offers)} total offers across {all_offers['section'].n_unique()} sections")

    # Apply classification filter
    target_sections = CLASSIFICATION_GROUPS[args.classification]
    classified = all_offers.filter(
        pl.col("section").str.to_lowercase().is_in(list(target_sections))
    )
    print(f"Classification '{args.classification}': {len(classified)} offers")

    # Section breakdown
    section_counts = (
        classified.group_by("section")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    for row in section_counts.iter_rows():
        print(f"  {row[0]:50s} {row[1]:>4}")

    # Filter to rows with valid weekly_ad_spend
    with_spend = classified.filter(pl.col("weekly_ad_spend").is_not_null()).with_columns(
        pl.col("weekly_ad_spend").cast(pl.Float64).alias("spend_f")
    ).filter(pl.col("spend_f") > 0)

    if len(with_spend) == 0:
        print("\nNo offers with weekly_ad_spend > 0 found.")
        return

    print(f"\nOffers with weekly_ad_spend > 0: {len(with_spend)}")
    print(f"Raw sum (before dedup): ${with_spend['spend_f'].sum():,.0f}")

    # Dedup by (office_phone, vertical) -- take first spend per combo
    deduped = with_spend.group_by(DEDUP_KEYS).agg(
        pl.col("spend_f").first().alias("weekly_ad_spend"),
        pl.col("office").first().alias("office"),
        pl.len().alias("offer_count"),
    ).sort("weekly_ad_spend", descending=True)

    total_spend = deduped["weekly_ad_spend"].sum()
    print(f"Unique ({', '.join(DEDUP_KEYS)}) combos: {len(deduped)}")
    print(f"\n  Active Weekly Ad Spend: ${total_spend:,.0f}\n")

    if args.verbose:
        print("Per-unit breakdown:")
        print(f"  {'Phone':<16s} {'Vertical':<20s} {'Office':<30s} {'Spend':>10s} {'Offers':>6s}")
        print(f"  {'-'*16} {'-'*20} {'-'*30} {'-'*10} {'-'*6}")
        for row in deduped.iter_rows(named=True):
            phone = row["office_phone"] or "—"
            vert = row["vertical"] or "—"
            office = (row["office"] or "—")[:30]
            print(f"  {phone:<16s} {vert:<20s} {office:<30s} ${row['weekly_ad_spend']:>9,.0f} {row['offer_count']:>6}")
        print(f"  {' ' * 68}----------")
        print(f"  {'TOTAL':<68s}${total_spend:>9,.0f}")


if __name__ == "__main__":
    main()
