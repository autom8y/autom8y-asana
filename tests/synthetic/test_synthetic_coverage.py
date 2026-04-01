"""Full-surface OpenAPI test harness for autom8y-asana.

Project Aegis: A single pytest invocation exercises every path in the OpenAPI
spec (44 paths, ~54 operations) with per-endpoint-group memory bounds, proving
resource management holds across the full API surface without manual test authorship.

Architecture:
    Component 1: Spec Parser (~150 LOC)
        - load_spec, resolve_ref, resolve_schema, generate_value, generate_object,
          generate_request, iter_all_operations
    Component 1b: Response Schema Validation
        - validate_response_schema() with deep $ref resolver
    Component 3: Test Harness (~120 LOC)
        - Parametrize over all operations (sorted by category for RSS grouping)
        - Classify by OpenAPI tags (not hardcoded path prefixes)
        - PASSED/FAILED/SKIPPED tracking
        - Response schema validation (findings, not failures)

Ported from autom8y-data. 9 spec parser functions copied VERBATIM.
Asana-specific: _resolve_path_param, _categorize, constants, tolerated sets.

Fixtures, memory measurement, and reporting are in conftest.py.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.synthetic.conftest import (
    _category_rss,
    _current_category,
    _current_rss_mb,
    _record_category_boundary,
    _results,
)

# =============================================================================
# Constants
# =============================================================================

SPEC_PATH = (
    Path(__file__).parent.parent.parent / "docs" / "api-reference" / "openapi.json"
)


# =============================================================================
# Component 1: Spec Parser (9 functions copied VERBATIM from autom8y-data)
# =============================================================================


def load_spec(path: Path) -> dict:
    """Load and return the OpenAPI spec as a dict."""
    with open(path) as f:
        return json.load(f)


def resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a local $ref pointer (e.g. '#/components/schemas/Foo') to its schema."""
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        node = node[part]
    return node


def resolve_schema(spec: dict, schema: dict, _depth: int = 0) -> dict:
    """Recursively resolve $ref and unwrap anyOf-with-null (Pydantic nullable pattern).

    _depth caps recursion for self-referencing schemas (e.g. FilterGroup).
    Depth cap raised from 3 to 10 for deeper $ref chains (Task 5 hardening).
    """
    if _depth > 10:
        return {"type": "null"}

    if "$ref" in schema:
        resolved = resolve_ref(spec, schema["$ref"])
        return resolve_schema(spec, resolved, _depth + 1)

    # Unwrap Pydantic nullable pattern: anyOf: [{type: T}, {type: null}]
    if "anyOf" in schema:
        non_null = [
            s
            for s in schema["anyOf"]
            if s.get("type") != "null" and s != {"type": "null"}
        ]
        if non_null:
            resolved = resolve_schema(spec, non_null[0], _depth + 1)
            merged = {**schema, **resolved}
            merged.pop("anyOf", None)
            return merged
        return {"type": "null"}

    # Handle allOf composition (Task 5: schema composition)
    if "allOf" in schema:
        merged: dict[str, Any] = {}
        for sub in schema["allOf"]:
            resolved_sub = resolve_schema(spec, sub, _depth + 1)
            # Merge properties
            if "properties" in resolved_sub:
                merged.setdefault("properties", {}).update(resolved_sub["properties"])
            # Merge required
            if "required" in resolved_sub:
                existing = set(merged.get("required", []))
                existing.update(resolved_sub["required"])
                merged["required"] = list(existing)
            # Copy type and other metadata from resolved
            for key in ("type", "title", "description"):
                if key in resolved_sub and key not in merged:
                    merged[key] = resolved_sub[key]
        if "type" not in merged:
            merged["type"] = "object"
        return merged

    # Handle oneOf (Task 5: pick first non-null variant)
    if "oneOf" in schema:
        non_null = [s for s in schema["oneOf"] if s.get("type") != "null"]
        if non_null:
            return resolve_schema(spec, non_null[0], _depth + 1)
        return {"type": "null"}

    return schema


def generate_value(spec: dict, schema: dict, _depth: int = 0) -> Any:
    """Generate a single value from a schema, preferring `examples` annotations."""
    if _depth > 4:
        return None

    resolved = resolve_schema(spec, schema, _depth)

    if "examples" in resolved:
        candidates = resolved["examples"]
        for c in candidates:
            if c is not None:
                return c
    if "example" in resolved:
        v = resolved["example"]
        if v is not None:
            return v
    if "default" in resolved:
        d = resolved["default"]
        if d is not None:
            return d

    typ = resolved.get("type", "string")

    if typ == "string":
        fmt = resolved.get("format")
        if fmt == "date":
            return "2026-01-15"
        if fmt == "date-time":
            return "2026-01-15T00:00:00Z"
        pattern = resolved.get("pattern", "")
        if "\\+" in pattern or "E.164" in resolved.get("description", ""):
            return "+15555550100"
        if "enum" in resolved:
            return resolved["enum"][0]
        return "test_string"
    elif typ == "integer":
        minimum = resolved.get("minimum")
        if minimum is not None:
            return int(minimum)
        return 1
    elif typ == "number":
        minimum = resolved.get("minimum")
        if minimum is not None:
            return float(minimum)
        return 1.0
    elif typ == "boolean":
        return True
    elif typ == "array":
        items_schema = resolved.get("items", {})
        if not items_schema:
            return []
        return [generate_value(spec, items_schema, _depth + 1)]
    elif typ == "object":
        return generate_object(spec, resolved, _depth + 1)
    elif typ == "null":
        return None

    return None


def generate_object(spec: dict, schema: dict, _depth: int = 0) -> dict:
    """Generate a valid object dict from a schema's properties."""
    if _depth > 4:
        return {}

    resolved = resolve_schema(spec, schema, _depth)
    props = resolved.get("properties", {})
    required = set(resolved.get("required", []))
    result: dict[str, Any] = {}

    for name, prop_schema in props.items():
        if name in required:
            result[name] = generate_value(spec, prop_schema, _depth + 1)
        elif "examples" in prop_schema or "default" in prop_schema:
            result[name] = generate_value(spec, prop_schema, _depth + 1)

    return result


def generate_request(spec: dict, path: str, method: str) -> dict:
    """Generate a complete HTTP request dict from the spec for a given path+method."""
    path_item = spec["paths"].get(path, {})
    operation = path_item.get(method.lower(), {})

    path_params: dict[str, Any] = {}
    query_params: dict[str, Any] = {}
    json_body = None

    all_params = path_item.get("parameters", []) + operation.get("parameters", [])
    for param in all_params:
        name = param["name"]
        location = param["in"]
        param_schema = param.get("schema", {})

        if location == "path":
            value = _resolve_path_param(name, path, param_schema, spec)
            path_params[name] = value
        elif location == "query":
            if param.get("required", False):
                query_params[name] = generate_value(spec, param_schema)

    request_body = operation.get("requestBody", {})
    if request_body:
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        body_schema = json_content.get("schema", {})
        if body_schema:
            json_body = generate_value(spec, body_schema)

    resolved_path = path
    for param_name, value in path_params.items():
        resolved_path = resolved_path.replace(f"{{{param_name}}}", str(value))

    return {
        "method": method.upper(),
        "url": resolved_path,
        "template_path": path,
        "params": query_params or None,
        "json_body": json_body,
        "headers": {"Content-Type": "application/json"},
    }


def iter_all_operations(spec: dict):
    """Yield (path, method, request_dict) for every operation in the spec."""
    for path, path_item in spec["paths"].items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method not in path_item:
                continue
            yield path, method, generate_request(spec, path, method)


# =============================================================================
# Component 1b: Response Schema Validation (VERBATIM from autom8y-data)
# =============================================================================


def deep_resolve_schema(spec: dict, schema: dict, _seen: set | None = None) -> dict:
    """Recursively resolve ALL $ref pointers in a schema tree.

    D-4 fix: The previous resolve_schema() only resolved top-level $ref and
    anyOf/allOf/oneOf composition. Nested $ref within properties were left
    unresolved, causing 79 PointerToNowhere findings from jsonschema.validate().

    This function walks the entire schema tree and resolves every $ref it
    encounters, producing a fully-inlined schema safe for jsonschema.validate().

    Circular references are detected via _seen set and collapsed to empty dict.

    Args:
        spec: The full OpenAPI spec (for $ref resolution context).
        schema: The schema node to resolve.
        _seen: Set of already-visited $ref pointers (circular ref guard).

    Returns:
        Fully-resolved schema dict with no remaining $ref pointers.
    """
    if _seen is None:
        _seen = set()

    if not isinstance(schema, dict):
        return schema  # type: ignore[return-value]

    # Resolve $ref at this level
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in _seen:
            return {}  # Circular reference -- collapse
        _seen = _seen | {ref}  # Copy to allow sibling branches
        try:
            resolved = resolve_ref(spec, ref)
        except (KeyError, TypeError):
            return {}  # Broken ref -- collapse gracefully
        return deep_resolve_schema(spec, resolved, _seen)

    result: dict[str, Any] = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            result[key] = deep_resolve_schema(spec, value, _seen.copy())
        elif isinstance(value, list):
            result[key] = [
                deep_resolve_schema(spec, item, _seen.copy())
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def validate_response_schema(
    spec: dict, path: str, method: str, status_code: int, response_body: Any
) -> tuple[bool, str | None]:
    """Validate response body against the OpenAPI response schema.

    Returns (is_valid, error_message). Schema validation failures are FINDINGS
    (spec-implementation drift), not test failures.

    Task 5 hardening:
    - Depth cap raised from 3 to 10 for deep $ref chains
    - allOf/oneOf schema composition handled

    D-4 fix: Uses deep_resolve_schema() to recursively resolve ALL nested $ref
    pointers before passing to jsonschema.validate(). This eliminates the 79
    PointerToNowhere false findings caused by unresolved nested $ref.
    """
    try:
        import jsonschema as _jsonschema
    except ImportError:
        return True, None

    path_item = spec.get("paths", {}).get(path, {})
    operation = path_item.get(method.lower(), {})
    responses = operation.get("responses", {})

    response_spec = responses.get(str(status_code), responses.get("default", {}))
    if not response_spec:
        return True, None

    schema = (
        response_spec.get("content", {}).get("application/json", {}).get("schema", {})
    )
    if not schema:
        return True, None

    # D-4 fix: Deep-resolve ALL $ref pointers (not just top-level)
    resolved = deep_resolve_schema(spec, schema)

    try:
        _jsonschema.validate(response_body, resolved)
        return True, None
    except _jsonschema.ValidationError as e:
        return False, str(e.message)[:200]
    except Exception as e:
        return False, f"validation-error: {str(e)[:150]}"


# =============================================================================
# Asana-Specific: Path Parameter Resolution
# =============================================================================

# Known path parameter values for Asana entities.
# All params are string-typed (no integer IDs in Asana spec).
_KNOWN_PATH_PARAMS: dict[str, str] = {
    "gid": "1234567890123456",
    "project_gid": "1234567890123456",
    "tag_gid": "2222222222222222",
    "workflow_id": "test-workflow-001",
    "entity_type": "unit",
    "factory": "lead",
    "name": "base",
    "field_name": "status",
}


def _resolve_path_param(name: str, path: str, schema: dict, spec: dict) -> Any:
    """Resolve a path parameter, preferring known seed values.

    Asana uses {gid} not {entity_id}. All path params are string-typed.
    """
    if name in _KNOWN_PATH_PARAMS:
        return _KNOWN_PATH_PARAMS[name]

    return generate_value(spec, schema)


# =============================================================================
# Asana-Specific: Category Classification
# =============================================================================


def _categorize(path: str, method: str, operation: dict | None = None) -> str:
    """Classify an operation into a coverage category for memory grouping.

    Uses OpenAPI tags from the operation (spec-driven, zero hardcoding).
    Falls back to path-based heuristic if no tags present.
    """
    if operation and operation.get("tags"):
        return operation["tags"][0]

    # Fallback: derive from path structure
    if path.startswith("/health") or path == "/ready":
        return "health"
    segments = path.strip("/").split("/")
    if len(segments) >= 3:
        return segments[2]  # e.g., /api/v1/tasks -> "tasks"
    return "uncategorized"


# =============================================================================
# Component 3: Test Harness
# =============================================================================

_spec = load_spec(SPEC_PATH)


def _get_operation(path: str, method: str) -> dict:
    """Get the operation dict for tag-based categorization."""
    path_item = _spec.get("paths", {}).get(path, {})
    return path_item.get(method.lower(), {})


# Build parametrize list at module import time, SORTED BY CATEGORY for RSS grouping
_all_operations_unsorted = list(iter_all_operations(_spec))
_all_operations = sorted(
    _all_operations_unsorted,
    key=lambda op: _categorize(op[0], op[1], _get_operation(op[0], op[1])),
)
_operation_ids = [f"{method.upper()}:{path}" for path, method, _ in _all_operations]


@pytest.mark.parametrize(
    "path,method,req",
    _all_operations,
    ids=_operation_ids,
)
def test_operation(
    synthetic_client: TestClient, path: str, method: str, req: dict
) -> None:
    """Exercise a single API operation and assert no 5xx (except known gaps).

    PASSED: 2xx or 4xx response (expected for data mismatches with shallow mock).
    EXPECTED-5xx: 5xx from known fixture gaps (genuinely environment-dependent).
    FAILED: Unexpected 5xx for endpoints that should work with mocked data.
    """
    operation = _get_operation(path, method)
    category = _categorize(path, method, operation)

    # Detect category transition for RSS tracking
    if category != _current_category[0]:
        _record_category_boundary(category)

    # Increment operation count for current category
    if category in _category_rss:
        _category_rss[category]["operations"] += 1

    url = req["url"]

    # Per-endpoint RSS measurement
    rss_before = _current_rss_mb()

    start = time.perf_counter()

    # Execute request
    http_method = req["method"].lower()
    caller = getattr(synthetic_client, http_method)

    kwargs: dict[str, Any] = {}
    if req["params"]:
        kwargs["params"] = req["params"]
    # httpx/TestClient DELETE does not accept json body -- skip for DELETE
    if req["json_body"] is not None and http_method != "delete":
        kwargs["json"] = req["json_body"]

    try:
        response = caller(url, **kwargs)
        status = response.status_code
    except Exception as exc:
        rss_after = _current_rss_mb()
        _results.append(
            {
                "path": path,
                "method": method.upper(),
                "status": None,
                "outcome": "FAILED",
                "category": category,
                "note": str(exc)[:100],
                "rss_before_mb": round(rss_before, 2),
                "rss_after_mb": round(rss_after, 2),
                "rss_delta_mb": round(rss_after - rss_before, 2),
            }
        )
        pytest.fail(f"Request raised exception: {exc}")
        return

    duration_ms = (time.perf_counter() - start) * 1000

    # Per-endpoint RSS measurement: after request
    rss_after = _current_rss_mb()

    # Determine outcome
    is_5xx = status >= 500

    # Tolerated 5xx paths -- minimal for Phase 1 shallow mock
    # Health dependency probes may 503 without real JWKS/Asana connections
    tolerated_5xx_paths: set[str] = {
        "/health/deps",
        "/ready",
        # section-timelines: 502 without real Asana data (upstream mock gap)
        "/api/v1/offers/section-timelines",
    }

    # Path+method combos where 5xx is expected
    tolerated_5xx_path_methods: set[tuple[str, str]] = {
        # Webhook endpoint requires WEBHOOK_SECRET env var not set in test
        ("POST", "/api/v1/webhooks/inbound"),
    }

    if not is_5xx:
        outcome = "PASSED"
    elif path in tolerated_5xx_paths:
        outcome = "EXPECTED-5xx"
    elif (method.upper(), path) in tolerated_5xx_path_methods:
        outcome = "EXPECTED-5xx"
    else:
        outcome = "FAILED"

    # Schema validation -- findings only, not failures
    schema_valid = None
    schema_error = None
    if outcome == "PASSED" and status < 300:
        try:
            body = response.json()
            schema_valid, schema_error = validate_response_schema(
                _spec,
                path,
                method,
                status,
                body,
            )
        except Exception:
            schema_valid = None

    rss_delta = rss_after - rss_before

    result_entry: dict[str, Any] = {
        "path": path,
        "method": method.upper(),
        "status": status,
        "outcome": outcome,
        "category": category,
        "duration_ms": round(duration_ms, 1),
        "rss_before_mb": round(rss_before, 2),
        "rss_after_mb": round(rss_after, 2),
        "rss_delta_mb": round(rss_delta, 2),
    }
    if schema_valid is not None:
        result_entry["schema_valid"] = schema_valid
        if schema_error:
            result_entry["schema_error"] = schema_error
    _results.append(result_entry)

    # Fail the test only for unexpected 5xx
    if outcome == "FAILED":
        pytest.fail(
            f"{method.upper()} {path} -> {status} (unexpected 5xx). "
            f"Body: {response.text[:200]}"
        )
