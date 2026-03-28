"""Validate the generated OpenAPI spec against the OpenAPI 3.2.0 schema.

Usage:
    uv run python scripts/validate_openapi.py           # Validate spec (exits 0 on success)

Environment:
    Sets AUTOM8Y_ENV=local and AUTH_DEV_MODE=true before importing so the
    app factory initializes without real credentials or external connections.

What this checks:
    1. Spec validates against the OpenAPI 3.2.0 meta-schema (openapi-spec-validator)
    2. openapi field declares "3.2.0"
    3. jsonSchemaDialect is present
    4. Shared registry types (SuccessResponse, ErrorResponse, ErrorDetail) are
       present in components/schemas
"""

from __future__ import annotations

import os
import sys

# Environment must be configured BEFORE any app imports touch pydantic-settings.
os.environ.setdefault("AUTOM8Y_ENV", "local")
os.environ.setdefault("AUTH_DEV_MODE", "true")

# Registry types that the fleet's shared envelope schema must export.
REQUIRED_REGISTRY_SCHEMAS = [
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
]


def _generate_spec() -> dict:  # type: ignore[type-arg]
    """Import the app, extract the OpenAPI dict."""
    from autom8_asana.api.main import create_app

    app = create_app()
    return app.openapi()  # type: ignore[no-any-return]


def _validate_spec(spec: dict) -> list[str]:  # type: ignore[type-arg]
    """Run all checks against the spec. Return list of error messages."""
    errors: list[str] = []

    # 1. openapi-spec-validator structural validation
    try:
        from openapi_spec_validator import validate
        from openapi_spec_validator.readers import read_from_filename

        validate(spec)
    except ImportError:
        errors.append(
            "openapi-spec-validator is not installed. "
            "Add 'openapi-spec-validator>=0.7.1' to dev dependencies."
        )
    except Exception as exc:
        errors.append(f"OpenAPI spec validation failed: {exc}")

    # 2. openapi version must be 3.2.0
    openapi_version = spec.get("openapi", "")
    if openapi_version != "3.2.0":
        errors.append(
            f"Expected openapi: '3.2.0', got: '{openapi_version}'. "
            "Service must declare OpenAPI 3.2.0."
        )

    # 3. jsonSchemaDialect must be present
    if "jsonSchemaDialect" not in spec:
        errors.append(
            "jsonSchemaDialect is missing from spec root. "
            "Required for OpenAPI 3.2.0 compliance."
        )

    # 4. Registry types must be present in components/schemas
    schemas = spec.get("components", {}).get("schemas", {})
    for schema_name in REQUIRED_REGISTRY_SCHEMAS:
        if schema_name not in schemas:
            errors.append(
                f"components/schemas/{schema_name} is missing. "
                f"Shared registry type '{schema_name}' must be present in the spec."
            )

    return errors


def main() -> None:
    print("Generating OpenAPI spec...", file=sys.stderr)
    try:
        spec = _generate_spec()
    except Exception as exc:
        print(f"ERROR: Failed to generate spec: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Validating spec...", file=sys.stderr)
    errors = _validate_spec(spec)

    if errors:
        print("OpenAPI spec validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    print("OpenAPI spec validation passed.")


if __name__ == "__main__":
    main()
