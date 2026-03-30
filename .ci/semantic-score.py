#!/usr/bin/env python3
"""Semantic Compliance Engine -- OpenAPI spec quality scorer.

Computes 7 governance metrics from OpenAPI 3.x specs, produces per-metric
and composite scores, and optionally detects regressions against a saved
baseline.

Usage:
    python score_spec.py <spec.json>                     # single spec
    python score_spec.py <spec.json> --baseline b.json   # with regression check
    python score_spec.py --fleet                         # all 5 fleet specs
    python score_spec.py --fleet --save-baselines        # fleet + persist baselines
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METRIC_DEFS: dict[str, dict[str, Any]] = {
    "M-01_field_description": {"floor": 0.80, "weight": 0.25},
    "M-02_field_example":     {"floor": 0.50, "weight": 0.15},
    "M-03_endpoint_summary":  {"floor": 0.90, "weight": 0.15},
    "M-04_error_coverage":    {"floor": 0.70, "weight": 0.15},
    "M-05_type_strictness":   {"floor": 0.90, "weight": 0.15},
    "M-06_extension_completeness": {"floor": 0.30, "weight": 0.10},
    "M-07_constraint_coverage":    {"floor": 0.60, "weight": 0.05},
}

HTTP_METHODS = frozenset(
    ("get", "post", "put", "patch", "delete", "head", "options", "trace")
)
MUTATING_METHODS = frozenset(("post", "put", "patch", "delete"))

FLEET_SPECS: dict[str, str] = {
    "autom8y-data":       "autom8y-data/docs/api-reference/openapi.json",
    "autom8y-sms":        "autom8y-sms/docs/api-reference/openapi.json",
    "autom8y-ads":        "autom8y-ads/docs/api-reference/openapi.json",
    "autom8y-scheduling": "autom8y-scheduling/docs/api-reference/openapi.json",
    "autom8y-asana":      "autom8y-asana/docs/api-reference/openapi.json",
}

# ---------------------------------------------------------------------------
# Spec loading
# ---------------------------------------------------------------------------


def load_spec(path: str) -> dict:
    """Load and return an OpenAPI spec from a JSON file."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Property extraction helpers
# ---------------------------------------------------------------------------


def collect_schema_properties(spec: dict) -> list[dict]:
    """Return a flat list of all property dicts from components/schemas.

    Each entry in the returned list is the raw property definition dict
    (e.g. {"type": "string", "description": "..."}).
    """
    schemas = spec.get("components", {}).get("schemas", {})
    properties: list[dict] = []
    for _schema_name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        for _prop_name, prop in schema.get("properties", {}).items():
            if isinstance(prop, dict):
                properties.append(prop)
    return properties


def collect_operations(spec: dict) -> list[tuple[str, dict]]:
    """Return a list of (http_method, operation_dict) tuples."""
    ops: list[tuple[str, dict]] = []
    for _path, methods in spec.get("paths", {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                ops.append((method.lower(), operation))
    return ops


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return numerator/denominator, or 1.0 when denominator is zero."""
    if denominator == 0:
        return 1.0
    return numerator / denominator


def compute_m01(properties: list[dict]) -> dict:
    """M-01: Field description coverage."""
    total = len(properties)
    with_desc = sum(
        1 for p in properties if p.get("description", "").strip()
    )
    score = _safe_ratio(with_desc, total)
    return {"score": round(score, 4), "numerator": with_desc, "denominator": total}


def compute_m02(properties: list[dict]) -> dict:
    """M-02: Field example coverage."""
    total = len(properties)
    with_example = sum(
        1 for p in properties if "example" in p or "examples" in p
    )
    score = _safe_ratio(with_example, total)
    return {"score": round(score, 4), "numerator": with_example, "denominator": total}


def compute_m03(operations: list[tuple[str, dict]]) -> dict:
    """M-03: Endpoint summary coverage."""
    total = len(operations)
    with_summary = sum(
        1 for (_m, op) in operations if op.get("summary", "").strip()
    )
    score = _safe_ratio(with_summary, total)
    return {"score": round(score, 4), "numerator": with_summary, "denominator": total}


def compute_m04(operations: list[tuple[str, dict]]) -> dict:
    """M-04: Error code coverage (at least one 4xx or 5xx response)."""
    total = len(operations)
    with_error = 0
    for _m, op in operations:
        responses = op.get("responses", {})
        has_error = any(
            str(code).startswith("4") or str(code).startswith("5")
            for code in responses
        )
        if has_error:
            with_error += 1
    score = _safe_ratio(with_error, total)
    return {"score": round(score, 4), "numerator": with_error, "denominator": total}


def compute_m05(properties: list[dict]) -> dict:
    """M-05: Type strictness (properties that are NOT empty/Any schema)."""
    total = len(properties)
    empty_count = 0
    for p in properties:
        # A property is "empty/Any" if it has no meaningful type information.
        # That means: no "type", no "$ref", no "anyOf", no "oneOf", no "allOf",
        # no "enum", and no "const".
        type_keys = {"type", "$ref", "anyOf", "oneOf", "allOf", "enum", "const"}
        if not any(k in p for k in type_keys):
            empty_count += 1
    strict = total - empty_count
    score = _safe_ratio(strict, total)
    return {"score": round(score, 4), "numerator": strict, "denominator": total}


def compute_m06(operations: list[tuple[str, dict]]) -> dict:
    """M-06: Extension completeness (x-fleet-* on mutating operations)."""
    mutating = [(m, op) for m, op in operations if m in MUTATING_METHODS]
    total = len(mutating)
    with_ext = 0
    for _m, op in mutating:
        if any(k.startswith("x-fleet-") for k in op):
            with_ext += 1
    score = _safe_ratio(with_ext, total)
    return {"score": round(score, 4), "numerator": with_ext, "denominator": total}


def compute_m07(properties: list[dict]) -> dict:
    """M-07: Constraint coverage on numeric properties."""
    constraint_keys = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "enum"}
    numeric: list[dict] = []
    for p in properties:
        ptype = p.get("type", "")
        if ptype in ("integer", "number"):
            numeric.append(p)
    total = len(numeric)
    constrained = sum(
        1 for p in numeric if any(k in p for k in constraint_keys)
    )
    score = _safe_ratio(constrained, total)
    return {"score": round(score, 4), "numerator": constrained, "denominator": total}


# ---------------------------------------------------------------------------
# Scoring orchestration
# ---------------------------------------------------------------------------


def score_spec(spec: dict, spec_path: str) -> dict:
    """Compute all 7 metrics and the weighted composite score."""
    properties = collect_schema_properties(spec)
    operations = collect_operations(spec)

    raw_metrics = {
        "M-01_field_description":      compute_m01(properties),
        "M-02_field_example":          compute_m02(properties),
        "M-03_endpoint_summary":       compute_m03(operations),
        "M-04_error_coverage":         compute_m04(operations),
        "M-05_type_strictness":        compute_m05(properties),
        "M-06_extension_completeness": compute_m06(operations),
        "M-07_constraint_coverage":    compute_m07(properties),
    }

    # Attach floor/weight and pass/fail to each metric
    metrics: dict[str, dict] = {}
    composite = 0.0
    floor_violations: list[str] = []

    for metric_id, result in raw_metrics.items():
        defn = METRIC_DEFS[metric_id]
        result["floor"] = defn["floor"]
        result["weight"] = defn["weight"]
        result["pass"] = result["score"] >= defn["floor"]
        metrics[metric_id] = result
        composite += result["score"] * defn["weight"]
        if not result["pass"]:
            floor_violations.append(metric_id)

    return {
        "spec_path": spec_path,
        "metrics": metrics,
        "composite_score": round(composite, 4),
        "floor_violations": floor_violations,
        "regression_safe": True,  # will be updated by baseline comparison
    }


# ---------------------------------------------------------------------------
# Baseline comparison
# ---------------------------------------------------------------------------


def compare_baseline(current: dict, baseline: dict) -> dict:
    """Compare current scores against a baseline and flag regressions.

    A regression is any individual metric score decrease, regardless of
    composite direction.  This is a deliberate design choice (see ADR).
    """
    regressions: list[dict] = []
    for metric_id, cur in current["metrics"].items():
        base = baseline.get("metrics", {}).get(metric_id)
        if base is None:
            continue
        delta = round(cur["score"] - base["score"], 4)
        if delta < 0:
            regressions.append({
                "metric": metric_id,
                "baseline": base["score"],
                "current": cur["score"],
                "delta": delta,
            })

    current["regressions"] = regressions
    current["regression_safe"] = len(regressions) == 0
    current["baseline_composite"] = baseline.get("composite_score")
    current["composite_delta"] = round(
        current["composite_score"] - baseline.get("composite_score", 0), 4
    )
    return current


# ---------------------------------------------------------------------------
# Fleet mode
# ---------------------------------------------------------------------------


def resolve_fleet_paths(base_dir: str) -> dict[str, str]:
    """Resolve fleet spec paths relative to a base directory."""
    resolved: dict[str, str] = {}
    for service, rel_path in FLEET_SPECS.items():
        full = os.path.join(base_dir, rel_path)
        if os.path.isfile(full):
            resolved[service] = full
        else:
            print(
                f"WARNING: spec not found for {service}: {full}",
                file=sys.stderr,
            )
    return resolved


def score_fleet(base_dir: str, save_baselines: bool = False) -> dict:
    """Score all fleet specs and produce an aggregate report."""
    fleet_paths = resolve_fleet_paths(base_dir)
    results: dict[str, dict] = {}
    baselines_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "baselines"
    )

    for service, spec_path in sorted(fleet_paths.items()):
        spec = load_spec(spec_path)
        result = score_spec(spec, spec_path)

        # Check for existing baseline
        baseline_path = os.path.join(baselines_dir, f"{service}.baseline.json")
        if os.path.isfile(baseline_path):
            with open(baseline_path, encoding="utf-8") as fh:
                baseline = json.load(fh)
            result = compare_baseline(result, baseline)

        results[service] = result

        if save_baselines:
            os.makedirs(baselines_dir, exist_ok=True)
            with open(baseline_path, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
                fh.write("\n")

    # Aggregate metrics
    aggregate = compute_fleet_aggregate(results)

    return {
        "mode": "fleet",
        "services": results,
        "aggregate": aggregate,
    }


def compute_fleet_aggregate(results: dict[str, dict]) -> dict:
    """Compute fleet-wide aggregate scores."""
    if not results:
        return {}

    n = len(results)
    metric_ids = list(METRIC_DEFS.keys())

    per_metric: dict[str, dict] = {}
    for mid in metric_ids:
        scores = [r["metrics"][mid]["score"] for r in results.values()]
        avg = sum(scores) / n
        floor = METRIC_DEFS[mid]["floor"]
        per_metric[mid] = {
            "fleet_avg": round(avg, 4),
            "fleet_min": round(min(scores), 4),
            "fleet_max": round(max(scores), 4),
            "floor": floor,
            "fleet_pass": avg >= floor,
        }

    composites = [r["composite_score"] for r in results.values()]
    fleet_composite = round(sum(composites) / n, 4)

    all_violations: list[str] = []
    for r in results.values():
        all_violations.extend(r["floor_violations"])
    unique_violations = sorted(set(all_violations))

    all_regression_safe = all(r.get("regression_safe", True) for r in results.values())

    return {
        "fleet_composite": fleet_composite,
        "fleet_composites": {svc: r["composite_score"] for svc, r in results.items()},
        "per_metric": per_metric,
        "fleet_floor_violations": unique_violations,
        "fleet_regression_safe": all_regression_safe,
        "services_scored": n,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Semantic Compliance Engine -- OpenAPI spec quality scorer",
    )
    parser.add_argument(
        "spec_path",
        nargs="?",
        help="Path to an OpenAPI spec JSON file",
    )
    parser.add_argument(
        "--baseline",
        metavar="FILE",
        help="Path to a baseline JSON for regression detection",
    )
    parser.add_argument(
        "--fleet",
        action="store_true",
        help="Score all 5 fleet specs and produce aggregate",
    )
    parser.add_argument(
        "--save-baselines",
        action="store_true",
        help="(fleet mode) Save per-service baselines alongside the tool",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Repository root (default: auto-detect from script location)",
    )
    return parser


def detect_base_dir() -> str:
    """Walk up from this script's location to find the repo root.

    Heuristic: the directory that contains the 'tools/' directory and at
    least one 'autom8y-*' directory.
    """
    script_dir = Path(os.path.abspath(__file__)).parent
    candidate = script_dir
    for _ in range(10):
        if (candidate / "tools").is_dir() and any(
            d.name.startswith("autom8y-") for d in candidate.iterdir() if d.is_dir()
        ):
            return str(candidate)
        candidate = candidate.parent
    # Fallback: two levels up from tools/semantic-score/
    return str(script_dir.parent.parent)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    base_dir = args.base_dir or detect_base_dir()

    if args.fleet:
        result = score_fleet(base_dir, save_baselines=args.save_baselines)
        print(json.dumps(result, indent=2))
        return 0

    if not args.spec_path:
        parser.error("spec_path is required unless --fleet is used")
        return 1  # unreachable but makes typing happy

    spec = load_spec(args.spec_path)
    result = score_spec(spec, args.spec_path)

    if args.baseline:
        with open(args.baseline, encoding="utf-8") as fh:
            baseline = json.load(fh)
        result = compare_baseline(result, baseline)

    print(json.dumps(result, indent=2))

    # Exit non-zero when regressions are detected (CI gate support)
    if not result.get("regression_safe", True):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
