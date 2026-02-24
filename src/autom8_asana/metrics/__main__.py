"""CLI entry point for metrics computation.

Usage:
    python -m autom8_asana.metrics active_mrr
    python -m autom8_asana.metrics active_mrr --verbose
    python -m autom8_asana.metrics --list
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    from autom8_asana.dataframes.offline import load_project_dataframe
    from autom8_asana.metrics.compute import compute_metric
    from autom8_asana.metrics.registry import MetricRegistry
    from autom8_asana.models.business.activity import CLASSIFIERS

    registry = MetricRegistry()

    parser = argparse.ArgumentParser(
        description="Compute metrics from cached Asana section data",
    )
    parser.add_argument(
        "metric",
        nargs="?",
        help="Metric name to compute (e.g., active_mrr, active_ad_spend)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-row breakdown",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_metrics",
        help="List all available metrics",
    )
    parser.add_argument(
        "--project-gid",
        help="Override project GID (default: resolved from metric entity type)",
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

    # Resolve project GID
    project_gid = args.project_gid
    if project_gid is None:
        classifier = CLASSIFIERS.get(metric.scope.entity_type)
        if classifier is None:
            print(
                f"ERROR: Cannot resolve project GID for entity type "
                f"'{metric.scope.entity_type}'",
                file=sys.stderr,
            )
            sys.exit(1)
        project_gid = classifier.project_gid

    # Load data
    try:
        df = load_project_dataframe(project_gid)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(df)} rows from project {project_gid}")

    # Compute
    result = compute_metric(metric, df, verbose=args.verbose)

    # Aggregate
    agg_fn = getattr(result[metric.expr.column], metric.expr.agg)
    total = agg_fn()

    if metric.scope.dedup_keys:
        dedup_desc = ", ".join(metric.scope.dedup_keys)
        print(f"Unique ({dedup_desc}) combos: {len(result)}")

    print(f"\n  {metric.name}: ${total:,.2f}")


if __name__ == "__main__":
    main()
