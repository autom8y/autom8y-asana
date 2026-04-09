#!/usr/bin/env python3
"""Validate secretspec.toml against Pydantic Settings classes.

Thin wrapper around autom8y_config.specvalidator. All validation logic
lives in the shared library; this file only declares per-repo config.

Usage:
    uv run python scripts/validate_secretspec.py [--verbose] [--check-naming]
"""

from __future__ import annotations

import argparse
import sys

from pydantic_settings import BaseSettings

from autom8y_config.specvalidator import validate_secretspec

# ============================================================================
# PER-REPO CONFIGURATION
# ============================================================================
from autom8_asana.settings import (  # noqa: E402
    AsanaSettings,
    CacheSettings,
    DataServiceSettings,
    ObservabilitySettings,
    PacingSettings,
    ProjectOverrideSettings,
    RateLimitSettings,
    RedisSettings,
    RuntimeSettings,
    S3RetrySettings,
    S3Settings,
    Settings,
    WebhookSettings,
)

SETTINGS_CLASSES: list[type[BaseSettings]] = [
    AsanaSettings,
    CacheSettings,
    RedisSettings,
    S3Settings,
    PacingSettings,
    RateLimitSettings,
    S3RetrySettings,
    DataServiceSettings,
    ObservabilitySettings,
    RuntimeSettings,
    WebhookSettings,
    Settings,
    ProjectOverrideSettings,
]

EXCLUDED_CLASSES: set[type] = {ProjectOverrideSettings}

EXCLUDED_VARS: set[str] = set()

# ADR-ENV-NAMING-CONVENTION: valid prefix patterns for this service.
VALID_PREFIXES: list[str] = [
    "AUTOM8Y_",
    "AUTOM8_DATA_",
    "ASANA_",
    "REDIS_",
    "WEBHOOK_",
    "CLOUDWATCH_",
    "ENVIRONMENT",
    "DATAFRAME_",
    "CONTAINER_",
    "SECTION_",
    "API_",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate secretspec.toml")
    parser.add_argument("--verbose", action="store_true", help="Print introspection details")
    parser.add_argument(
        "--check-naming",
        action="store_true",
        help="Enforce ADR-ENV-NAMING-CONVENTION tier system",
    )
    args = parser.parse_args()

    return validate_secretspec(
        settings_classes=SETTINGS_CLASSES,
        excluded_vars=EXCLUDED_VARS,
        toml_path="secretspec.toml",
        valid_prefixes=VALID_PREFIXES,
        excluded_classes=EXCLUDED_CLASSES,
        check_naming=args.check_naming,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
