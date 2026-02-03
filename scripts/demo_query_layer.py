#!/usr/bin/env python3
"""Dynamic Query Service — Interactive Demo

Runs representative queries through the full engine pipeline.

Data source is selected automatically based on ASANA_ENVIRONMENT, or
overridden via CLI flags:

    uv run python scripts/demo_query_layer.py              # auto-detect
    uv run python scripts/demo_query_layer.py --live       # force live data
    uv run python scripts/demo_query_layer.py --synthetic  # force synthetic
    uv run python scripts/demo_query_layer.py --entity offer  # single entity

Live mode requires ASANA_BOT_PAT and ASANA_WORKSPACE_GID.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import polars as pl

from autom8_asana.query import (
    AggFunction,
    AggregateRequest,
    AggSpec,
    JoinSpec,
    QueryEngine,
    RowsRequest,
)
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.errors import QueryEngineError
from autom8_asana.query.guards import QueryLimits
from autom8_asana.query.hierarchy import (
    ENTITY_RELATIONSHIPS,
    get_joinable_types,
)
from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA
from autom8_asana.dataframes.models.registry import SchemaRegistry


# ── Palette ──────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"
RULE = f"{DIM}{'─' * 78}{RESET}"

# Disable colors if piped
if not sys.stdout.isatty():
    BOLD = DIM = GREEN = CYAN = YELLOW = RED = MAGENTA = RESET = ""
    RULE = "─" * 78


# ── Pretty helpers ───────────────────────────────────────────────────

def heading(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 78}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 78}{RESET}\n")


def subheading(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    print(RULE)


def show_query(label: str, payload: dict[str, Any]) -> None:
    print(f"{YELLOW}▸ {label}{RESET}")
    formatted = json.dumps(payload, indent=2, default=str)
    for line in formatted.splitlines():
        print(f"  {DIM}{line}{RESET}")
    print()


def show_meta(meta: Any) -> None:
    d = meta.model_dump() if hasattr(meta, "model_dump") else meta
    parts = [f"{k}={v}" for k, v in d.items() if v is not None]
    print(f"  {MAGENTA}meta: {', '.join(parts)}{RESET}")


def show_rows(data: list[dict[str, Any]], *, max_rows: int = 12) -> None:
    if not data:
        print(f"  {DIM}(no rows){RESET}")
        return

    cols = list(data[0].keys())
    widths = {c: len(c) for c in cols}
    display = data[:max_rows]
    for row in display:
        for c in cols:
            widths[c] = max(widths[c], len(_fmt(row.get(c))))
    for c in cols:
        widths[c] = min(widths[c], 28)

    print("  " + " │ ".join(f"{BOLD}{c:<{widths[c]}}{RESET}" for c in cols))
    print("  " + "─┼─".join("─" * widths[c] for c in cols))

    for row in display:
        cells = []
        for c in cols:
            val = _fmt(row.get(c))
            if len(val) > widths[c]:
                val = val[: widths[c] - 1] + "…"
            cells.append(f"{val:<{widths[c]}}")
        print("  " + " │ ".join(cells))

    if len(data) > max_rows:
        print(f"  {DIM}... and {len(data) - max_rows} more rows{RESET}")
    print()


def _fmt(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, float):
        return f"{v:,.2f}"
    if isinstance(v, list):
        return str(v)
    return str(v)


def show_error(err: QueryEngineError) -> None:
    d = err.to_dict()
    print(f"  {RED}✗ {d['error']}: {d['message']}{RESET}")
    for k, v in d.items():
        if k not in ("error", "message"):
            print(f"    {DIM}{k}: {v}{RESET}")
    print()


# ── Data source resolution ───────────────────────────────────────────

PROD_ENVIRONMENTS = {"production", "prod", "main", "staging"}


def resolve_data_mode(args: argparse.Namespace) -> str:
    """Return 'live' or 'synthetic' based on args and environment."""
    if args.live:
        return "live"
    if args.synthetic:
        return "synthetic"

    # Auto-detect from ASANA_ENVIRONMENT
    env = os.environ.get("ASANA_ENVIRONMENT", "development").lower()
    if env in PROD_ENVIRONMENTS:
        return "live"
    return "synthetic"


# ── Synthetic data builders ──────────────────────────────────────────

def build_synthetic_offer_df() -> pl.DataFrame:
    """30 offers across 3 sections, 4 verticals, varied MRR."""
    rows: list[dict[str, Any]] = []
    sections = ["Active", "Active", "Active", "Pending", "Pending", "Churned"]
    verticals = ["Dental", "Medical", "Legal", "Home Services"]
    phones = [
        "555-0100", "555-0100", "555-0200", "555-0200",
        "555-0300", "555-0300", "555-0400", "555-0400",
        "555-0500", "555-0500",
    ]
    for i in range(30):
        section = sections[i % len(sections)]
        vertical = verticals[i % len(verticals)]
        phone = phones[i % len(phones)]
        rows.append({
            "gid": f"offer-{i:03d}",
            "name": f"Offer {i:03d} ({vertical})",
            "type": "Offer",
            "date": date(2025, 1, 1 + (i % 28)),
            "created": datetime(2025, 1, 1, 12, 0, 0),
            "due_on": date(2025, 6, 15) if i % 5 != 0 else None,
            "is_completed": section == "Churned",
            "completed_at": datetime(2025, 5, 1) if section == "Churned" else None,
            "url": f"https://app.asana.com/0/proj/offer-{i:03d}",
            "last_modified": datetime(2025, 3, 15, 8, i % 60, 0),
            "section": section,
            "tags": ["priority"] if i % 4 == 0 else [],
            "office": f"Office {i % 5}",
            "office_phone": phone,
            "vertical": vertical,
            "vertical_id": f"v-{verticals.index(vertical) + 1}",
            "specialty": f"Specialty-{chr(65 + i % 6)}",
            "offer_id": f"OID-{i:04d}",
            "platforms": ["google", "facebook"] if i % 3 == 0 else ["google"],
            "language": "en" if i % 7 != 0 else "es",
            "cost": str(round(50 + i * 12.5, 2)),
            "mrr": str(100 + i * 75),
            "weekly_ad_spend": str(round(200 + i * 30.0, 2)),
        })
    return pl.DataFrame(rows).cast({
        "date": pl.Date, "created": pl.Datetime, "due_on": pl.Date,
        "completed_at": pl.Datetime, "last_modified": pl.Datetime,
        "tags": pl.List(pl.Utf8), "platforms": pl.List(pl.Utf8),
    })


def build_synthetic_business_df() -> pl.DataFrame:
    """10 businesses matching the office_phone join keys."""
    rows: list[dict[str, Any]] = []
    booking_types = ["Premium", "Standard", "Enterprise", "Trial", "Premium"]
    for i in range(10):
        phone = f"555-0{(i // 2 + 1) * 100}"
        rows.append({
            "gid": f"biz-{i:03d}",
            "name": f"Business {i:03d}",
            "type": "business",
            "date": date(2024, 6, 1 + i),
            "created": datetime(2024, 6, 1, 10, 0, 0),
            "due_on": None,
            "is_completed": False,
            "completed_at": None,
            "url": f"https://app.asana.com/0/proj/biz-{i:03d}",
            "last_modified": datetime(2025, 2, 1, 12, 0, 0),
            "section": "Active" if i < 7 else "Inactive",
            "tags": [],
            "company_id": f"CID-{i:04d}",
            "office_phone": phone,
            "stripe_id": f"cus_{i:06d}",
            "booking_type": booking_types[i % len(booking_types)],
            "facebook_page_id": f"fb-{i:05d}" if i % 3 == 0 else None,
        })
    return pl.DataFrame(rows).cast({
        "date": pl.Date, "created": pl.Datetime, "due_on": pl.Date,
        "completed_at": pl.Datetime, "last_modified": pl.Datetime,
        "tags": pl.List(pl.Utf8),
    })


# ── Live data loader ─────────────────────────────────────────────────

async def load_live_dataframes(
    entity_types: list[str],
) -> tuple[dict[str, pl.DataFrame], dict[str, str], dict[str, datetime | None]]:
    """Discover projects and load DataFrames directly from S3 cache.

    Bypasses TTL/watermark/schema freshness checks — reads whatever
    parquet exists in S3. Good enough for demo/observability use.

    Returns (dataframes, project_gids, watermarks) keyed by entity_type.
    """
    from autom8_asana.dataframes.section_persistence import SectionPersistence
    from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
    from autom8_asana.services.discovery import discover_entity_projects_async

    s3_bucket = os.environ.get("ASANA_CACHE_S3_BUCKET")
    if not s3_bucket:
        print(f"  {RED}ASANA_CACHE_S3_BUCKET is not set{RESET}")
        print(f"  {DIM}Live mode requires S3 access to cached DataFrames{RESET}")
        sys.exit(1)

    print(f"  {DIM}Discovering entity projects...{RESET}")
    registry = await discover_entity_projects_async()

    dataframes: dict[str, pl.DataFrame] = {}
    project_gids: dict[str, str] = {}
    watermarks: dict[str, datetime | None] = {}

    async with SectionPersistence() as persistence:
        tier = ProgressiveTier(persistence=persistence)

        for entity_type in entity_types:
            project_gid = registry.get_project_gid(entity_type)
            if not project_gid:
                print(f"  {YELLOW}Skipping '{entity_type}' — no project discovered{RESET}")
                continue

            project_gids[entity_type] = project_gid
            print(f"  {DIM}Loading {entity_type} ({project_gid})...{RESET}", end="", flush=True)

            try:
                # Direct S3 read — no freshness checks
                entry = await tier.get_async(f"{entity_type}:{project_gid}")
                if entry is not None:
                    dataframes[entity_type] = entry.dataframe
                    watermarks[entity_type] = entry.watermark
                    print(f" {GREEN}{entry.row_count} rows × {entry.dataframe.shape[1]} cols{RESET}")
                else:
                    # Fallback: assemble from section parquets
                    print(f" {YELLOW}no merged parquet, trying sections...{RESET}", end="", flush=True)
                    df = await persistence.merge_sections_to_dataframe_async(project_gid)
                    if df is not None:
                        dataframes[entity_type] = df
                        watermarks[entity_type] = None
                        print(f" {GREEN}{df.shape[0]} rows × {df.shape[1]} cols (from sections){RESET}")
                    else:
                        print(f" {RED}no data in S3{RESET}")
            except Exception as e:
                print(f" {RED}FAILED: {e}{RESET}")

    return dataframes, project_gids, watermarks


# ── Engine wiring ────────────────────────────────────────────────────

@dataclass
class DemoContext:
    """Holds the query engine and data, regardless of source."""

    mode: str  # "live" or "synthetic"
    dataframes: dict[str, pl.DataFrame]
    project_gids: dict[str, str]
    watermarks: dict[str, datetime | None] = field(default_factory=dict)
    engine: QueryEngine = field(init=False)
    entity_project_registry: Any = field(init=False)

    def __post_init__(self) -> None:
        # Build a query service that returns our loaded DataFrames
        mock_service = AsyncMock()
        dfs = self.dataframes

        async def _get_df(entity_type: str, project_gid: str, client: Any) -> pl.DataFrame:
            if entity_type in dfs:
                return dfs[entity_type]
            msg = f"No DataFrame loaded for entity type '{entity_type}'"
            raise ValueError(msg)

        mock_service.get_dataframe = AsyncMock(side_effect=_get_df)

        # Use real SchemaRegistry singleton for column/dtype validation
        schema_registry = SchemaRegistry.get_instance()

        self.engine = QueryEngine(
            query_service=mock_service,
            compiler=PredicateCompiler(),
            limits=QueryLimits(),
        )
        self.engine.schema_registry = schema_registry

        # Entity project registry — uses real GIDs in live mode
        reg = MagicMock()
        gids = self.project_gids
        reg.get_project_gid = MagicMock(side_effect=lambda et: gids.get(et))
        self.entity_project_registry = reg

    @property
    def available_entities(self) -> list[str]:
        return sorted(self.dataframes.keys())


async def build_context(args: argparse.Namespace) -> DemoContext:
    """Build a DemoContext from the resolved data mode."""
    mode = resolve_data_mode(args)

    heading(f"DATA SOURCE: {'LIVE (Asana cache)' if mode == 'live' else 'SYNTHETIC'}")

    if mode == "live":
        entity_types = [args.entity] if args.entity else ["offer", "business"]
        dataframes, project_gids, watermarks = await load_live_dataframes(entity_types)
        if not dataframes:
            print(f"\n  {RED}No DataFrames loaded. Is the cache warm?{RESET}")
            print(f"  {DIM}Hint: Start the API first, or run with --synthetic{RESET}\n")
            sys.exit(1)
    else:
        print(f"  {DIM}Using 30 synthetic offers + 10 synthetic businesses{RESET}")
        dataframes = {
            "offer": build_synthetic_offer_df(),
            "business": build_synthetic_business_df(),
        }
        project_gids = {
            "offer": "proj-synthetic-offer",
            "business": "proj-synthetic-business",
        }
        watermarks: dict[str, datetime | None] = {}
        if args.entity:
            dataframes = {k: v for k, v in dataframes.items() if k == args.entity}
            project_gids = {k: v for k, v in project_gids.items() if k == args.entity}

    return DemoContext(mode=mode, dataframes=dataframes, project_gids=project_gids, watermarks=watermarks)


# ── Query runners ────────────────────────────────────────────────────

async def run_rows(
    ctx: DemoContext,
    entity_type: str,
    request: RowsRequest,
    *,
    label: str = "",
) -> None:
    if entity_type not in ctx.dataframes:
        print(f"  {DIM}(skipped — {entity_type} not loaded){RESET}\n")
        return

    payload = request.model_dump(exclude_none=True, by_alias=True)
    show_query(label or f"POST /v1/query/{entity_type}/rows", payload)

    try:
        resp = await ctx.engine.execute_rows(
            entity_type=entity_type,
            project_gid=ctx.project_gids[entity_type],
            client=AsyncMock(),
            request=request,
            section_index=None,
            entity_project_registry=ctx.entity_project_registry,
        )
        show_meta(resp.meta)
        show_rows(resp.data)
    except QueryEngineError as e:
        show_error(e)


async def run_aggregate(
    ctx: DemoContext,
    entity_type: str,
    request: AggregateRequest,
    *,
    label: str = "",
) -> None:
    if entity_type not in ctx.dataframes:
        print(f"  {DIM}(skipped — {entity_type} not loaded){RESET}\n")
        return

    payload = request.model_dump(exclude_none=True, by_alias=True)
    show_query(label or f"POST /v1/query/{entity_type}/aggregate", payload)

    try:
        resp = await ctx.engine.execute_aggregate(
            entity_type=entity_type,
            project_gid=ctx.project_gids[entity_type],
            client=AsyncMock(),
            request=request,
            section_index=None,
        )
        show_meta(resp.meta)
        show_rows(resp.data)
    except QueryEngineError as e:
        show_error(e)


# ── Demo scenarios ───────────────────────────────────────────────────

async def demo_data_overview(ctx: DemoContext) -> None:
    heading("DATA OVERVIEW")

    for entity_type, df in sorted(ctx.dataframes.items()):
        subheading(f"{entity_type} ({df.shape[0]} rows × {df.shape[1]} cols)")
        print(f"  Source:   {ctx.mode}")
        print(f"  Project:  {ctx.project_gids.get(entity_type, 'N/A')}")
        wm = ctx.watermarks.get(entity_type)
        if wm is not None:
            age = datetime.now(UTC) - wm
            if age.total_seconds() > 3600:
                age_str = f"{age.total_seconds() / 3600:.1f}h ago"
            else:
                age_str = f"{age.total_seconds() / 60:.0f}m ago"
            print(f"  Cached:   {wm.strftime('%Y-%m-%d %H:%M UTC')} ({age_str})")
        elif ctx.mode == "live":
            print(f"  Cached:   {DIM}(watermark unavailable){RESET}")
        print(f"  Columns:  {df.columns}")

        # Show section distribution if column exists
        if "section" in df.columns:
            sections = df["section"].drop_nulls().value_counts().sort("section")
            dist = ", ".join(
                f"{row['section']}: {row['count']}"
                for row in sections.to_dicts()
            )
            print(f"  Sections: {dist}")

        # Show a few key column stats
        for col_name in ["vertical", "booking_type", "language"]:
            if col_name in df.columns:
                uniques = df[col_name].drop_nulls().unique().sort().to_list()
                print(f"  {col_name}: {uniques}")

        for col_name in ["mrr", "cost", "weekly_ad_spend"]:
            if col_name in df.columns:
                series = df[col_name].cast(pl.Float64, strict=False).drop_nulls()
                if series.len() > 0:
                    print(f"  {col_name}: min={series.min():.0f}, max={series.max():.0f}, mean={series.mean():.0f}")
        print()

    subheading("Entity Relationships (Join Graph)")
    for rel in ENTITY_RELATIONSHIPS:
        markers = []
        if rel.parent_type in ctx.dataframes:
            markers.append(f"{GREEN}loaded{RESET}")
        if rel.child_type in ctx.dataframes:
            markers.append(f"{GREEN}loaded{RESET}")
        status = f"  [{', '.join(markers)}]" if markers else ""
        print(f"  {rel.parent_type} <── {rel.default_join_key} ──> {rel.child_type}{status}")
    print()


async def demo_basic_rows(ctx: DemoContext) -> None:
    heading("1. BASIC ROW QUERIES")

    subheading("1a. All offers, first page")
    await run_rows(ctx, "offer", RowsRequest(
        select=["gid", "name", "section", "vertical", "mrr"],
        limit=8,
    ), label="All offers (first 8)")

    subheading("1b. Paginated — offset into results")
    await run_rows(ctx, "offer", RowsRequest(
        select=["gid", "name", "mrr"],
        limit=5,
        offset=10,
    ), label="Offers page 3 (offset=10, limit=5)")


async def demo_predicates(ctx: DemoContext) -> None:
    heading("2. PREDICATE FILTERING")

    subheading("2a. Simple equality — Active offers only")
    await run_rows(ctx, "offer", RowsRequest(
        where={"field": "section", "op": "eq", "value": "Active"},
        select=["gid", "name", "section", "mrr"],
        limit=8,
    ), label="WHERE section = 'Active'")

    subheading("2b. IN operator — specific verticals")
    await run_rows(ctx, "offer", RowsRequest(
        where={"field": "vertical", "op": "in", "value": ["Dental", "Legal"]},
        select=["gid", "name", "vertical", "section"],
        limit=8,
    ), label="WHERE vertical IN ['Dental', 'Legal']")

    subheading("2c. CONTAINS — substring search")
    await run_rows(ctx, "offer", RowsRequest(
        where={"field": "name", "op": "contains", "value": "Medical"},
        select=["gid", "name", "vertical"],
        limit=8,
    ), label="WHERE name CONTAINS 'Medical'")

    subheading("2d. AND composition — Active Dental offers")
    await run_rows(ctx, "offer", RowsRequest(
        where={
            "and": [
                {"field": "section", "op": "eq", "value": "Active"},
                {"field": "vertical", "op": "eq", "value": "Dental"},
            ]
        },
        select=["gid", "name", "section", "vertical", "mrr"],
    ), label="WHERE section='Active' AND vertical='Dental'")

    subheading("2e. OR composition — Dental or Legal")
    await run_rows(ctx, "offer", RowsRequest(
        where={
            "or": [
                {"field": "vertical", "op": "eq", "value": "Dental"},
                {"field": "vertical", "op": "eq", "value": "Legal"},
            ]
        },
        select=["gid", "name", "vertical"],
        limit=8,
    ), label="WHERE vertical='Dental' OR vertical='Legal'")

    subheading("2f. NOT — everything except Churned")
    await run_rows(ctx, "offer", RowsRequest(
        where={"not": {"field": "section", "op": "eq", "value": "Churned"}},
        select=["gid", "name", "section"],
        limit=8,
    ), label="WHERE NOT section='Churned'")

    subheading("2g. Nested — Active AND (Dental OR Medical)")
    await run_rows(ctx, "offer", RowsRequest(
        where={
            "and": [
                {"field": "section", "op": "eq", "value": "Active"},
                {"or": [
                    {"field": "vertical", "op": "eq", "value": "Dental"},
                    {"field": "vertical", "op": "eq", "value": "Medical"},
                ]},
            ]
        },
        select=["gid", "name", "section", "vertical", "mrr"],
    ), label="WHERE Active AND (Dental OR Medical)")

    subheading("2h. Date comparison")
    await run_rows(ctx, "offer", RowsRequest(
        where={"field": "date", "op": "gt", "value": "2025-01-15"},
        select=["gid", "name", "date"],
        limit=8,
    ), label="WHERE date > '2025-01-15'")


async def demo_section_scoping(ctx: DemoContext) -> None:
    heading("3. SECTION SCOPING")

    subheading("3a. Section + predicate composition")
    await run_rows(ctx, "offer", RowsRequest(
        section="Active",
        where={"field": "vertical", "op": "eq", "value": "Dental"},
        select=["gid", "name", "section", "vertical", "mrr"],
    ), label="Section=Active + WHERE vertical='Dental'")


async def demo_joins(ctx: DemoContext) -> None:
    heading("4. CROSS-ENTITY JOINS")

    subheading("Joinable types for 'offer'")
    joinable = get_joinable_types("offer")
    print(f"  offer can join to: {joinable}\n")

    subheading("4a. Enrich offers with business booking_type")
    await run_rows(ctx, "offer", RowsRequest(
        select=["gid", "name", "vertical", "mrr", "office_phone"],
        join=JoinSpec(entity_type="business", select=["booking_type"]),
        limit=10,
    ), label="Offers + JOIN business(booking_type)")

    subheading("4b. Join + WHERE — Active Dental offers with business context")
    await run_rows(ctx, "offer", RowsRequest(
        section="Active",
        where={"field": "vertical", "op": "eq", "value": "Dental"},
        select=["gid", "name", "vertical", "mrr", "office_phone"],
        join=JoinSpec(entity_type="business", select=["booking_type", "company_id"]),
    ), label="Active Dental offers + business(booking_type, company_id)")

    subheading("4c. Join with multiple target columns")
    await run_rows(ctx, "offer", RowsRequest(
        select=["gid", "name", "office_phone"],
        join=JoinSpec(entity_type="business", select=["booking_type", "stripe_id", "facebook_page_id"]),
        limit=8,
    ), label="Offers + business(booking_type, stripe_id, facebook_page_id)")

    subheading("4d. Error — join to unrelated entity")
    await run_rows(ctx, "offer", RowsRequest(
        select=["gid", "name"],
        join=JoinSpec(entity_type="asset_edit", select=["some_col"]),
    ), label="Offers + JOIN asset_edit (should fail)")


async def demo_aggregation(ctx: DemoContext) -> None:
    heading("5. AGGREGATION QUERIES")

    subheading("5a. Count offers by vertical")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["vertical"],
        aggregations=[AggSpec(column="gid", agg=AggFunction.COUNT)],
    ), label="COUNT(gid) GROUP BY vertical")

    subheading("5b. Sum MRR by section")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["section"],
        aggregations=[AggSpec(column="mrr", agg=AggFunction.SUM)],
    ), label="SUM(mrr) GROUP BY section")

    subheading("5c. Full stats by vertical")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["vertical"],
        aggregations=[
            AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr"),
            AggSpec(column="mrr", agg=AggFunction.MEAN, alias="avg_mrr"),
            AggSpec(column="mrr", agg=AggFunction.MIN, alias="min_mrr"),
            AggSpec(column="mrr", agg=AggFunction.MAX, alias="max_mrr"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="offer_count"),
        ],
    ), label="Full MRR stats GROUP BY vertical")

    subheading("5d. Multi-dimension GROUP BY — section x vertical")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["section", "vertical"],
        aggregations=[
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="count"),
            AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr"),
        ],
    ), label="COUNT + SUM(mrr) GROUP BY section, vertical")

    subheading("5e. Count distinct — unique offices per section")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["section"],
        aggregations=[
            AggSpec(column="office", agg=AggFunction.COUNT_DISTINCT, alias="unique_offices"),
            AggSpec(column="vertical", agg=AggFunction.COUNT_DISTINCT, alias="unique_verticals"),
        ],
    ), label="COUNT_DISTINCT(office, vertical) GROUP BY section")

    subheading("5f. Date aggregation — earliest and latest per section")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["section"],
        aggregations=[
            AggSpec(column="date", agg=AggFunction.MIN, alias="earliest"),
            AggSpec(column="date", agg=AggFunction.MAX, alias="latest"),
        ],
    ), label="MIN/MAX(date) GROUP BY section")


async def demo_having(ctx: DemoContext) -> None:
    heading("6. HAVING CLAUSES")

    subheading("6a. Verticals with more than 7 offers")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["vertical"],
        aggregations=[AggSpec(column="gid", agg=AggFunction.COUNT, alias="offer_count")],
        having={"field": "offer_count", "op": "gt", "value": 7},
    ), label="COUNT(gid) GROUP BY vertical HAVING count > 7")

    subheading("6b. Section x vertical combos with total MRR > $2000")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["section", "vertical"],
        aggregations=[
            AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="count"),
        ],
        having={"field": "total_mrr", "op": "gt", "value": 2000},
    ), label="GROUP BY section,vertical HAVING total_mrr > 2000")

    subheading("6c. Nested HAVING — count > 5 AND avg MRR > $500")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["vertical"],
        aggregations=[
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="count"),
            AggSpec(column="mrr", agg=AggFunction.MEAN, alias="avg_mrr"),
        ],
        having={
            "and": [
                {"field": "count", "op": "gt", "value": 5},
                {"field": "avg_mrr", "op": "gt", "value": 500},
            ]
        },
    ), label="HAVING count > 5 AND avg_mrr > 500")


async def demo_full_pipeline(ctx: DemoContext) -> None:
    heading("7. WHERE + AGGREGATE (Full Pipeline)")

    subheading("7a. Active offers only — MRR by vertical")
    await run_aggregate(ctx, "offer", AggregateRequest(
        where={"field": "section", "op": "eq", "value": "Active"},
        group_by=["vertical"],
        aggregations=[
            AggSpec(column="mrr", agg=AggFunction.SUM, alias="active_mrr"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="active_count"),
        ],
    ), label="WHERE Active -> SUM(mrr) GROUP BY vertical")

    subheading("7b. Full composition — WHERE + section + GROUP BY + HAVING")
    await run_aggregate(ctx, "offer", AggregateRequest(
        section="Active",
        where={
            "or": [
                {"field": "vertical", "op": "eq", "value": "Dental"},
                {"field": "vertical", "op": "eq", "value": "Medical"},
            ]
        },
        group_by=["vertical"],
        aggregations=[
            AggSpec(column="mrr", agg=AggFunction.SUM, alias="total_mrr"),
            AggSpec(column="gid", agg=AggFunction.COUNT, alias="count"),
        ],
        having={"field": "count", "op": "gte", "value": 1},
    ), label="Active + (Dental|Medical) -> GROUP BY vertical HAVING count >= 1")


async def demo_error_handling(ctx: DemoContext) -> None:
    heading("8. ERROR HANDLING (Guard Rails)")

    subheading("8a. Unknown column in predicate")
    await run_rows(ctx, "offer", RowsRequest(
        where={"field": "nonexistent_column", "op": "eq", "value": "x"},
    ), label="WHERE nonexistent_column = 'x'")

    subheading("8b. Invalid operator for dtype")
    await run_rows(ctx, "offer", RowsRequest(
        where={"field": "is_completed", "op": "gt", "value": True},
    ), label="WHERE is_completed > true (gt on Boolean)")

    subheading("8c. Predicate too deep (depth 6, max 5)")
    deep: dict[str, Any] = {"field": "vertical", "op": "eq", "value": "Dental"}
    for _ in range(5):
        deep = {"and": [deep]}
    await run_rows(ctx, "offer", RowsRequest(where=deep), label="Depth-6 nested predicate")

    subheading("8d. GROUP BY on List column")
    await run_aggregate(ctx, "offer", AggregateRequest(
        group_by=["tags"],
        aggregations=[AggSpec(column="gid", agg=AggFunction.COUNT)],
    ), label="GROUP BY tags (List dtype — should fail)")


async def demo_business_queries(ctx: DemoContext) -> None:
    heading("9. BUSINESS ENTITY QUERIES")

    subheading("9a. All businesses")
    await run_rows(ctx, "business", RowsRequest(
        select=["gid", "name", "booking_type", "office_phone", "stripe_id"],
        limit=10,
    ), label="All businesses")

    subheading("9b. Premium businesses only")
    await run_rows(ctx, "business", RowsRequest(
        where={"field": "booking_type", "op": "eq", "value": "Premium"},
        select=["gid", "name", "booking_type", "office_phone"],
    ), label="WHERE booking_type = 'Premium'")

    subheading("9c. Business count by booking_type")
    await run_aggregate(ctx, "business", AggregateRequest(
        group_by=["booking_type"],
        aggregations=[AggSpec(column="gid", agg=AggFunction.COUNT, alias="count")],
    ), label="COUNT GROUP BY booking_type")


async def demo_summary(ctx: DemoContext) -> None:
    heading("FEATURE SUMMARY")

    features = [
        "Row queries with select/limit/offset",
        "10 predicate operators (eq, ne, gt, lt, gte, lte, in, not_in, contains, starts_with)",
        "AND / OR / NOT composition",
        "Nested predicates (up to depth 5)",
        "Section scoping",
        "Cross-entity joins (offer <-> business)",
        "6 aggregation functions (sum, count, mean, min, max, count_distinct)",
        "GROUP BY (1-5 columns)",
        "HAVING with predicate reuse",
        "WHERE + section + GROUP BY + HAVING composition",
        "Utf8-to-Float64 numeric casting (MRR, cost)",
        "Date/Datetime comparison and aggregation",
        "Guard rails (depth, limits, dtype validation)",
        "Structured error responses",
    ]
    for feat in features:
        print(f"  {GREEN}✓{RESET} {feat}")

    print(f"\n  {DIM}Data source: {ctx.mode} | Entities loaded: {ctx.available_entities}{RESET}")
    print()


# ── Main ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dynamic Query Service demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Data source precedence:
  --live / --synthetic    Explicit override (highest priority)
  ASANA_ENVIRONMENT       Auto-detect: production/prod/main/staging → live
  (default)               synthetic

Environment variables for live mode:
  ASANA_BOT_PAT           Asana bot Personal Access Token
  ASANA_WORKSPACE_GID     Asana workspace GID
  ASANA_ENVIRONMENT       Environment name (production, staging, development)
""",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--live", action="store_true",
        help="Force live data from Asana cache",
    )
    source.add_argument(
        "--synthetic", action="store_true",
        help="Force synthetic demo data",
    )
    parser.add_argument(
        "--entity", type=str, default=None,
        help="Run demos for a single entity type (e.g., offer, business)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    ctx = await build_context(args)

    await demo_data_overview(ctx)
    await demo_basic_rows(ctx)
    await demo_predicates(ctx)
    await demo_section_scoping(ctx)
    await demo_joins(ctx)
    await demo_aggregation(ctx)
    await demo_having(ctx)
    await demo_full_pipeline(ctx)
    await demo_error_handling(ctx)
    await demo_business_queries(ctx)
    await demo_summary(ctx)


if __name__ == "__main__":
    asyncio.run(main())
