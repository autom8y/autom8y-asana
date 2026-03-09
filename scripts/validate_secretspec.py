#!/usr/bin/env python3
"""Validate secretspec.toml against Pydantic Settings classes.

Compares the env var surface declared in Python Settings classes against
the entries documented in secretspec.toml. Exits non-zero on any
discrepancy (missing or phantom entries).

Usage:
    uv run python scripts/validate_secretspec.py [--verbose]
"""

from __future__ import annotations

import argparse
import sys
import tomllib
import typing
from pathlib import Path

from pydantic import AliasChoices
from pydantic_settings import BaseSettings

# ============================================================================
# PER-REPO CONFIGURATION (only this block differs between satellites)
# ============================================================================

# Import Settings classes
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

TOML_PATH = Path("secretspec.toml")

# ADR-env-naming-convention: valid prefix patterns for this service.
# Tier 1: AUTOM8Y_ (ecosystem), Tier 3: AUTOM8Y_{TARGET}_URL (cross-service),
# Tier 4: service-specific, Vendor: REDIS_ (infrastructure convention).
# Bare-prefix classes (ObservabilitySettings, RuntimeSettings) use exact prefixes.
VALID_PREFIXES: list[str] = [
    "AUTOM8Y_", "AUTOM8_DATA_", "ASANA_", "REDIS_", "WEBHOOK_",
    "CLOUDWATCH_", "ENVIRONMENT", "DATAFRAME_", "CONTAINER_",
    "SECTION_", "API_",
]

# ============================================================================
# CORE ALGORITHM (shared across all satellites -- do not modify per-repo)
# Shared algorithm. If modifying, update all 4 satellite scripts.
# ============================================================================

def _is_settings_subclass(annotation: typing.Any) -> bool:
    """Check if a type annotation is a BaseSettings subclass."""
    origin = typing.get_origin(annotation)
    if origin is not None:
        for arg in typing.get_args(annotation):
            if isinstance(arg, type) and issubclass(arg, BaseSettings):
                return True
        return False
    if isinstance(annotation, type) and issubclass(annotation, BaseSettings):
        return True
    return False


def resolve_field_env_var(
    field_name: str,
    field_info: typing.Any,
    env_prefix: str,
) -> tuple[str, list[str]]:
    """Resolve canonical env var name and all aliases for a field.

    Returns:
        (canonical_name, all_aliases) where all_aliases includes canonical.
    """
    alias = field_info.validation_alias

    if isinstance(alias, AliasChoices):
        all_names = []
        for choice in alias.choices:
            if isinstance(choice, str):
                all_names.append(choice.upper())
        if all_names:
            return all_names[0], all_names
        # Fallback for list-of-list aliases
        canonical = (env_prefix + field_name).upper()
        return canonical, [canonical]

    if isinstance(alias, str):
        canonical = alias.upper()
        return canonical, [canonical]

    canonical = (env_prefix + field_name).upper()
    return canonical, [canonical]


def resolve_env_vars(
    settings_classes: list[type[BaseSettings]],
    excluded_vars: set[str],
    excluded_classes: set[type],
    verbose: bool = False,
) -> tuple[set[str], dict[str, list[str]]]:
    """Resolve all env var names from Settings classes.

    Returns:
        (env_vars_set, alias_map) where alias_map maps canonical -> all aliases.
    """
    env_vars: set[str] = set()
    alias_map: dict[str, list[str]] = {}

    for cls in settings_classes:
        if cls in excluded_classes:
            if verbose:
                print(f"[verbose]   {cls.__name__} -- EXCLUDED", file=sys.stderr)
            continue

        env_prefix = cls.model_config.get("env_prefix", "")
        field_count = 0

        if verbose:
            print(
                f"[verbose]   {cls.__name__} "
                f"(env_prefix='{env_prefix}', "
                f"fields={len(cls.model_fields)})",
                file=sys.stderr,
            )

        for field_name, field_info in cls.model_fields.items():
            annotation = field_info.annotation

            if _is_settings_subclass(annotation):
                if verbose:
                    print(
                        f"[verbose]     {field_name} -> SKIPPED (subsettings container)",
                        file=sys.stderr,
                    )
                continue

            if field_info.exclude:
                if verbose:
                    print(
                        f"[verbose]     {field_name} -> SKIPPED (exclude=True)",
                        file=sys.stderr,
                    )
                continue

            if field_info.init is False:
                if verbose:
                    print(
                        f"[verbose]     {field_name} -> SKIPPED (init=False)",
                        file=sys.stderr,
                    )
                continue

            canonical, aliases = resolve_field_env_var(field_name, field_info, env_prefix)

            # SDK deduplication: autom8y_env is inherited by every
            # Autom8yBaseSettings subclass.  When a subclass has a non-empty
            # env_prefix and does NOT override autom8y_env with a
            # validation_alias, the field resolves to {PREFIX}AUTOM8Y_ENV
            # (e.g. DB_AUTOM8Y_ENV).  These are SDK infrastructure, not
            # intentional env var surface.  Normalise them to the single
            # canonical AUTOM8Y_ENV entry.
            if field_name == "autom8y_env" and canonical != "AUTOM8Y_ENV":
                if verbose:
                    print(
                        f"[verbose]     {field_name} -> {canonical} "
                        f"NORMALISED to AUTOM8Y_ENV (SDK inherited field)",
                        file=sys.stderr,
                    )
                canonical = "AUTOM8Y_ENV"
                aliases = ["AUTOM8Y_ENV"]

            if canonical in excluded_vars:
                if verbose:
                    print(
                        f"[verbose]     {field_name} -> {canonical} EXCLUDED",
                        file=sys.stderr,
                    )
                continue

            env_vars.add(canonical)
            if len(aliases) > 1:
                alias_map[canonical] = aliases
            field_count += 1

            if verbose:
                method = "AliasChoices" if isinstance(
                    field_info.validation_alias, AliasChoices
                ) else (
                    "validation_alias" if field_info.validation_alias
                    else "env_prefix + field_name"
                )
                print(
                    f"[verbose]     {field_name} -> {canonical} ({method})",
                    file=sys.stderr,
                )

    return env_vars, alias_map


def parse_toml_entries(toml_path: Path) -> set[str]:
    """Extract env var keys from secretspec.toml [profiles.default]."""
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    default_profile = data.get("profiles", {}).get("default", {})
    return {key.upper() for key in default_profile}


def compare_with_fallback(
    code_vars: set[str],
    toml_vars: set[str],
    alias_map: dict[str, list[str]],
) -> tuple[set[str], set[str], list[str]]:
    """Compare code vars against toml vars with AliasChoices fallback."""
    warnings: list[str] = []
    matched_code: set[str] = set()
    matched_toml: set[str] = set()

    for canonical in code_vars:
        if canonical in toml_vars:
            matched_code.add(canonical)
            matched_toml.add(canonical)
        elif canonical in alias_map:
            for alias_name in alias_map[canonical]:
                upper_alias = alias_name.upper()
                if upper_alias != canonical and upper_alias in toml_vars:
                    matched_code.add(canonical)
                    matched_toml.add(upper_alias)
                    warnings.append(
                        f"TOML uses '{upper_alias}' instead of canonical "
                        f"'{canonical}'. Consider updating secretspec.toml."
                    )
                    break

    missing = code_vars - matched_code
    phantom = toml_vars - matched_toml

    return missing, phantom, warnings


import re


def check_naming_conventions(
    env_vars: set[str],
    valid_prefixes: list[str],
    verbose: bool = False,
) -> list[str]:
    """Check env var names against ADR-env-naming-convention tier system.

    Rules enforced:
    - REJECT A8_* prefix (Tier 2 is CLI-only, not for Python services)
    - VALIDATE SCREAMING_SNAKE_CASE format
    - WARN on vars not matching any valid prefix for this service

    Returns list of violation messages (empty = all pass).
    """
    violations: list[str] = []

    for var in sorted(env_vars):
        # Tier 2 rejection: A8_* is CLI-only per ADR-env-naming-convention
        if var.startswith("A8_"):
            violations.append(
                f"NAMING ERROR: '{var}' uses A8_* prefix "
                f"(CLI-only per ADR-env-naming-convention Tier 2)"
            )
            continue

        # SCREAMING_SNAKE_CASE format check
        if not re.match(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$", var):
            violations.append(f"NAMING WARN: '{var}' is not SCREAMING_SNAKE_CASE")
            continue

        # Check against valid prefixes for this service
        matched = any(var.startswith(p) for p in valid_prefixes)
        if not matched:
            violations.append(
                f"NAMING WARN: '{var}' does not match any expected prefix "
                f"for this service: {valid_prefixes}"
            )
        elif verbose:
            print(f"[naming]   {var} OK", file=sys.stderr)

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate secretspec.toml")
    parser.add_argument("--verbose", action="store_true", help="Print introspection details")
    parser.add_argument(
        "--check-naming", action="store_true",
        help="Enforce ADR-env-naming-convention tier system",
    )
    args = parser.parse_args()

    if not TOML_PATH.exists():
        print(f"ERROR: {TOML_PATH} not found", file=sys.stderr)
        return 2

    if args.verbose:
        print("[verbose] Discovering Settings classes...", file=sys.stderr)

    code_vars, alias_map = resolve_env_vars(
        SETTINGS_CLASSES, EXCLUDED_VARS, EXCLUDED_CLASSES, verbose=args.verbose,
    )
    toml_vars = parse_toml_entries(TOML_PATH)

    missing, phantom, warnings = compare_with_fallback(code_vars, toml_vars, alias_map)

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    # Naming convention enforcement (opt-in via --check-naming)
    naming_violations: list[str] = []
    if args.check_naming:
        if args.verbose:
            print("[verbose] Checking naming conventions...", file=sys.stderr)
        naming_violations = check_naming_conventions(
            code_vars, VALID_PREFIXES, verbose=args.verbose,
        )

    has_sync_errors = bool(missing or phantom)
    has_naming_errors = bool(naming_violations)

    if not has_sync_errors and not has_naming_errors:
        msg = (
            f"secretspec validation passed: {len(code_vars)} env vars in code, "
            f"{len(toml_vars)} entries in secretspec.toml, 0 discrepancies."
        )
        if args.check_naming:
            msg += " Naming conventions OK."
        print(msg)
        return 0

    if has_sync_errors:
        print("secretspec validation FAILED\n")

        if missing:
            print("Missing from secretspec.toml (in code, not in toml):")
            for var in sorted(missing):
                print(f"  - {var}")
            print()

        if phantom:
            print("Phantom in secretspec.toml (in toml, not in code):")
            for var in sorted(phantom):
                print(f"  - {var}")
            print()

        print(f"Code env vars ({len(code_vars)}):  {sorted(code_vars)}")
        print(f"TOML entries ({len(toml_vars)}):   {sorted(toml_vars)}")

    if has_naming_errors:
        print("\nNaming convention violations:\n")
        for v in naming_violations:
            print(f"  {v}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
