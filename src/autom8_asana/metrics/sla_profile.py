"""SLA profile / TTL persistence per ADR-005 (TTL manifest YAML schema + S3 sidecar JSON).

Implements the layered persistence model declared by HANDOFF §3 LD-P3-1 and
schema-frozen by ADR-005:

- Manifest at ``.know/cache-freshness-ttl-manifest.yaml`` — canonical,
  version-controlled, human-edited.
- S3 sidecar at ``s3://{bucket}/dataframes/{project_gid}/cache-freshness-ttl.json``
  — runtime override, machine-written.
- Built-in defaults — fallback when neither manifest nor sidecar covers a
  ``(project_gid, section_gid)`` pair.

Override precedence: ``sidecar > manifest > built-in defaults``.

Public surface:

    - SLA_CLASSES               -- 4-class enum (active|warm|cold|near-empty)
    - DEFAULT_THRESHOLDS        -- canonical seconds per class
    - SLA_MANIFEST_PATH         -- canonical manifest path
    - TtlManifestError          -- raised on validator V-1..V-5 failures
    - SectionTtl                -- per-section record
    - TtlManifest               -- full manifest dataclass
    - load_manifest(path=...)   -- read + validate manifest
    - load_sidecar(s3_client, bucket, project_gid)
                                -- read + validate S3 sidecar (returns None
                                  if absent; logs WARN on parse error and
                                  treats sidecar as absent per ADR-005 §1.4)
    - resolve_ttl(project_gid, section_gid, manifest=None, sidecar=None)
                                -- override-precedence lookup, returning
                                  (sla_class, threshold_seconds)

The validator executes ADR-005 V-1 through V-6:

    V-1: schema_version present and == 1 (hard fail above 1).
    V-2: sla_class in 4-class enum (hard fail).
    V-3: threshold_seconds is positive int (hard fail on float, neg, zero).
    V-4: section_gid / project_gid are strings (hard fail on bare-int).
    V-5: (project_gid, section_gid) duplicates (WARN; YAML/JSON map
         collapse to last-write-wins by spec — best-effort detection).
    V-6: cross-validation: threshold deviates from canonical class default
         (WARN; legitimate operator override allowed).

Future schema evolution per ADR-005 §"Additive evolution" — unknown fields
tolerated; required-field changes bump ``schema_version``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from autom8y_log import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants — FROZEN by HANDOFF FLAG-2 / ADR-005
# ---------------------------------------------------------------------------

#: 4-class taxonomy (FROZEN by HANDOFF FLAG-2 / LD-P2-1).
SLA_CLASSES: tuple[str, ...] = ("active", "warm", "cold", "near-empty")

#: Canonical threshold seconds per class (P3 §2.2).
DEFAULT_THRESHOLDS: dict[str, int] = {
    "active": 21600,  # 6h
    "warm": 43200,  # 12h
    "cold": 86400,  # 24h
    "near-empty": 604800,  # 7d
}

#: Default class when manifest absent and sidecar absent (ADR-005 step 3).
BUILTIN_DEFAULT_CLASS: str = "active"

#: Schema version this module reads/writes (ADR-005 V-1).
CURRENT_SCHEMA_VERSION: int = 1

#: Canonical manifest path relative to repo root (ADR-005 §"Manifest format").
SLA_MANIFEST_PATH: str = ".know/cache-freshness-ttl-manifest.yaml"

#: S3 key under bucket for the sidecar (ADR-005 §"Sidecar format").
SIDECAR_S3_KEY_TEMPLATE: str = "dataframes/{project_gid}/cache-freshness-ttl.json"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TtlManifestError(ValueError):
    """Raised when a TTL manifest or sidecar fails ADR-005 validation V-1..V-4.

    V-5 and V-6 emit WARN logs but do NOT raise; only hard-fail rules raise.

    The ``rule`` attribute names which validator rule failed (e.g. ``"V-2"``).
    """

    def __init__(self, rule: str, message: str) -> None:
        self.rule = rule
        super().__init__(f"[{rule}] {message}")


# ---------------------------------------------------------------------------
# Dataclasses (logical schema — format-agnostic per ADR-005)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SectionTtl:
    """Per-section TTL record (ADR-005 logical schema)."""

    section_gid: str
    sla_class: str
    threshold_seconds: int
    notes: str | None = None


@dataclass(frozen=True)
class ProjectTtl:
    """Per-project TTL record (manifest-only; sidecar is single-project)."""

    project_gid: str
    sections: dict[str, SectionTtl] = field(default_factory=dict)


@dataclass(frozen=True)
class TtlManifest:
    """Full manifest record (ADR-005 logical schema, manifest variant)."""

    schema_version: int
    default_class: str = BUILTIN_DEFAULT_CLASS
    projects: dict[str, ProjectTtl] = field(default_factory=dict)
    generated_at: str | None = None
    generator: str | None = None


@dataclass(frozen=True)
class TtlSidecar:
    """Single-project sidecar (ADR-005 logical schema, sidecar variant).

    The S3 sidecar's top-level shape omits the multi-project ``projects`` map
    and inlines the project as a sibling key.
    """

    schema_version: int
    project_gid: str
    sections: dict[str, SectionTtl] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validator helpers
# ---------------------------------------------------------------------------


def _validate_schema_version(raw: Any) -> int:
    """V-1: schema_version MUST be present and equal to CURRENT_SCHEMA_VERSION.

    Future readers tolerate additive fields without bumping schema_version
    (ADR-005 §Additive evolution); they MUST error loudly on schema_version
    > CURRENT_SCHEMA_VERSION.
    """
    if raw is None:
        raise TtlManifestError("V-1", "schema_version is required")
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise TtlManifestError(
            "V-1",
            f"schema_version must be an integer, got {type(raw).__name__}: {raw!r}",
        )
    if raw > CURRENT_SCHEMA_VERSION:
        raise TtlManifestError(
            "V-1",
            f"schema_version {raw} exceeds reader version {CURRENT_SCHEMA_VERSION}; "
            "upgrade reader before consuming",
        )
    if raw < 1:
        raise TtlManifestError("V-1", f"schema_version must be >= 1, got {raw!r}")
    return raw


def _validate_sla_class(raw: Any) -> str:
    """V-2: sla_class MUST be one of SLA_CLASSES."""
    if not isinstance(raw, str):
        raise TtlManifestError(
            "V-2",
            f"sla_class must be a string, got {type(raw).__name__}: {raw!r}",
        )
    if raw not in SLA_CLASSES:
        raise TtlManifestError(
            "V-2",
            f"sla_class {raw!r} not in {SLA_CLASSES}",
        )
    return raw


def _validate_threshold_seconds(raw: Any) -> int:
    """V-3: threshold_seconds MUST be a positive int (>0).

    Floats (even round ones like 21600.0) are rejected at parse time per
    ADR-005 V-3. Negative values and zero are rejected.
    """
    # bool is a subclass of int in Python — exclude it explicitly.
    if isinstance(raw, bool):
        raise TtlManifestError(
            "V-3",
            f"threshold_seconds must be a positive int, got bool: {raw!r}",
        )
    if not isinstance(raw, int):
        raise TtlManifestError(
            "V-3",
            f"threshold_seconds must be a positive int, got {type(raw).__name__}: {raw!r}",
        )
    if raw <= 0:
        raise TtlManifestError(
            "V-3",
            f"threshold_seconds must be > 0, got {raw!r}",
        )
    return raw


def _validate_gid(raw: Any, field_name: str) -> str:
    """V-4: section_gid / project_gid MUST be strings (no bare ints).

    YAML's int-vs-string ambiguity for 16-digit Asana GIDs is a documented
    foot-gun; the validator forces explicit string typing at the persistence
    boundary.
    """
    if isinstance(raw, bool):
        raise TtlManifestError(
            "V-4",
            f"{field_name} must be a string, got bool: {raw!r}",
        )
    if not isinstance(raw, str):
        raise TtlManifestError(
            "V-4",
            f"{field_name} must be a string (quote it in YAML), got {type(raw).__name__}: {raw!r}",
        )
    if not raw:
        raise TtlManifestError("V-4", f"{field_name} must be a non-empty string")
    return raw


def _emit_v6_cross_validation_warning(
    section_gid: str, sla_class: str, threshold_seconds: int
) -> None:
    """V-6: WARN if threshold deviates from canonical class default.

    Operators may intentionally tune individual sections; per ADR-005 V-6
    this is a WARN, NOT an error.
    """
    canonical = DEFAULT_THRESHOLDS.get(sla_class)
    if canonical is None:
        # V-2 should have caught this; defensive log only.
        return
    if threshold_seconds != canonical:
        logger.warning(
            "ttl_manifest_v6_threshold_deviation",
            extra={
                "section_gid": section_gid,
                "sla_class": sla_class,
                "threshold_seconds": threshold_seconds,
                "canonical_threshold": canonical,
            },
        )


def _build_section_ttl(section_gid: str, raw: Mapping[str, Any]) -> SectionTtl:
    """Validate-and-construct one SectionTtl record (V-2 + V-3 + V-4 + V-6)."""
    declared_gid = _validate_gid(raw.get("section_gid", section_gid), "section_gid")
    if declared_gid != section_gid:
        # Map key vs payload field disagree; trust the map key (user index).
        logger.warning(
            "ttl_manifest_section_gid_key_field_mismatch",
            extra={"key": section_gid, "payload_section_gid": declared_gid},
        )
    sla_class = _validate_sla_class(raw.get("sla_class"))
    threshold_seconds = _validate_threshold_seconds(raw.get("threshold_seconds"))
    notes = raw.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise TtlManifestError(
            "V-4",
            f"notes must be a string or absent, got {type(notes).__name__}: {notes!r}",
        )
    _emit_v6_cross_validation_warning(section_gid, sla_class, threshold_seconds)
    return SectionTtl(
        section_gid=section_gid,
        sla_class=sla_class,
        threshold_seconds=threshold_seconds,
        notes=notes,
    )


def _build_sections_map(
    project_gid: str,
    raw_sections: Mapping[str, Any] | None,
) -> dict[str, SectionTtl]:
    """Build a {section_gid: SectionTtl} map; empty if input is None/empty."""
    if raw_sections is None:
        return {}
    if not isinstance(raw_sections, Mapping):
        raise TtlManifestError(
            "V-4",
            f"sections for project {project_gid!r} must be a map, "
            f"got {type(raw_sections).__name__}",
        )
    sections: dict[str, SectionTtl] = {}
    for raw_key, raw_record in raw_sections.items():
        section_gid = _validate_gid(raw_key, "section_gid")
        if not isinstance(raw_record, Mapping):
            raise TtlManifestError(
                "V-4",
                f"section {section_gid!r} record must be a map, got {type(raw_record).__name__}",
            )
        if section_gid in sections:
            # YAML/JSON parsers normally collapse duplicates last-wins; this
            # branch is defensive (unreachable for well-formed input).
            logger.warning(
                "ttl_manifest_v5_duplicate_section",
                extra={"project_gid": project_gid, "section_gid": section_gid},
            )
        sections[section_gid] = _build_section_ttl(section_gid, raw_record)
    return sections


# ---------------------------------------------------------------------------
# Manifest reader (YAML)
# ---------------------------------------------------------------------------


def parse_manifest(raw: Mapping[str, Any]) -> TtlManifest:
    """Parse and validate an in-memory mapping into a TtlManifest record.

    Raises:
        TtlManifestError: on V-1..V-4 violations.
    """
    schema_version = _validate_schema_version(raw.get("schema_version"))

    default_class_raw = raw.get("default_class", BUILTIN_DEFAULT_CLASS)
    default_class = _validate_sla_class(default_class_raw)

    generated_at = raw.get("generated_at")
    if generated_at is not None and not isinstance(generated_at, str):
        raise TtlManifestError(
            "V-4",
            f"generated_at must be a string or absent, got {type(generated_at).__name__}",
        )
    generator = raw.get("generator")
    if generator is not None and not isinstance(generator, str):
        raise TtlManifestError(
            "V-4",
            f"generator must be a string or absent, got {type(generator).__name__}",
        )

    raw_projects = raw.get("projects") or {}
    if not isinstance(raw_projects, Mapping):
        raise TtlManifestError(
            "V-4",
            f"projects must be a map, got {type(raw_projects).__name__}",
        )

    projects: dict[str, ProjectTtl] = {}
    for raw_key, raw_project in raw_projects.items():
        project_gid = _validate_gid(raw_key, "project_gid")
        if not isinstance(raw_project, Mapping):
            raise TtlManifestError(
                "V-4",
                f"project {project_gid!r} record must be a map, got {type(raw_project).__name__}",
            )
        # Validate the inner project_gid field if present.
        declared_pg = raw_project.get("project_gid", project_gid)
        _validate_gid(declared_pg, "project_gid")
        sections = _build_sections_map(project_gid, raw_project.get("sections"))
        projects[project_gid] = ProjectTtl(project_gid=project_gid, sections=sections)

    return TtlManifest(
        schema_version=schema_version,
        default_class=default_class,
        projects=projects,
        generated_at=generated_at,
        generator=generator,
    )


def load_manifest(path: str | Path | None = None) -> TtlManifest | None:
    """Read and validate the TTL manifest at the given path.

    Args:
        path: Manifest path. Defaults to SLA_MANIFEST_PATH (relative to CWD).

    Returns:
        TtlManifest if the file exists and parses cleanly. ``None`` if the
        file is absent (this is the normal "no operator declarations yet"
        case; callers fall through to built-in defaults).

    Raises:
        TtlManifestError: on V-1..V-4 violations. Manifest parse errors are
            promoted to errors (manifest is a version-controlled artifact;
            silently ignoring corruption would mask declared TTL intent).
    """
    manifest_path = Path(path) if path is not None else Path(SLA_MANIFEST_PATH)
    if not manifest_path.exists():
        logger.debug(
            "ttl_manifest_absent",
            extra={"path": str(manifest_path)},
        )
        return None
    try:
        with manifest_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise TtlManifestError(
            "V-1",
            f"manifest at {manifest_path} is not valid YAML: {exc!r}",
        ) from exc
    if raw is None:
        raise TtlManifestError(
            "V-1",
            f"manifest at {manifest_path} is empty",
        )
    if not isinstance(raw, Mapping):
        raise TtlManifestError(
            "V-1",
            f"manifest at {manifest_path} must be a YAML mapping, got {type(raw).__name__}",
        )
    return parse_manifest(raw)


# ---------------------------------------------------------------------------
# Sidecar reader (JSON, S3-backed)
# ---------------------------------------------------------------------------


def parse_sidecar(raw: Mapping[str, Any]) -> TtlSidecar:
    """Parse and validate an in-memory mapping into a TtlSidecar record.

    Raises:
        TtlManifestError: on V-1..V-4 violations.
    """
    schema_version = _validate_schema_version(raw.get("schema_version"))
    project_gid = _validate_gid(raw.get("project_gid"), "project_gid")
    raw_sections = raw.get("sections") or {}
    if not isinstance(raw_sections, Mapping):
        raise TtlManifestError(
            "V-4",
            f"sections for sidecar must be a map, got {type(raw_sections).__name__}",
        )
    sections = _build_sections_map(project_gid, raw_sections)
    return TtlSidecar(
        schema_version=schema_version,
        project_gid=project_gid,
        sections=sections,
    )


def load_sidecar(
    s3_client: Any,
    bucket: str,
    project_gid: str,
) -> TtlSidecar | None:
    """Read the S3 sidecar for a project; return None if absent.

    Per ADR-005 §"Override precedence" step 1 + §"Sidecar absence MUST NOT
    raise an error":

        - Sidecar absent (NoSuchKey, 404) → return None (manifest fallback).
        - Sidecar present, parse fails → log WARN, return None (manifest
          fallback). This is per ADR-005: "Sidecar parse error MUST NOT
          short-circuit the lookup chain — the warmer logs a WARN and falls
          through to step 2 (treat sidecar as absent)."
        - Sidecar present, validates → return TtlSidecar.

    Args:
        s3_client: boto3 S3 client (or moto-backed equivalent).
        bucket: S3 bucket name (typically settings.cache.s3.bucket).
        project_gid: Asana project GID (used in key template).

    Returns:
        TtlSidecar if present and valid; None otherwise.
    """
    key = SIDECAR_S3_KEY_TEMPLATE.format(project_gid=project_gid)
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 -- degrade across the heterogeneous botocore exception surface (NoSuchKey, ClientError, NoCredentials, EndpointConnection); per ADR-005 sidecar errors MUST NOT short-circuit the lookup chain
        # Distinguish "absent" (NoSuchKey / 404) from other errors.
        if _is_no_such_key(exc):
            logger.debug(
                "ttl_sidecar_absent",
                extra={"bucket": bucket, "key": key, "project_gid": project_gid},
            )
            return None
        # All other errors (auth, network, etc.) — log WARN and fall through.
        # Per ADR-005: sidecar errors MUST NOT short-circuit the lookup chain.
        logger.warning(
            "ttl_sidecar_read_error",
            extra={
                "bucket": bucket,
                "key": key,
                "project_gid": project_gid,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )
        return None

    try:
        body = response["Body"].read()
        raw = json.loads(body)
    except (json.JSONDecodeError, KeyError, AttributeError) as exc:
        logger.warning(
            "ttl_sidecar_parse_error",
            extra={
                "bucket": bucket,
                "key": key,
                "project_gid": project_gid,
                "error": str(exc),
            },
        )
        return None

    if not isinstance(raw, Mapping):
        logger.warning(
            "ttl_sidecar_not_mapping",
            extra={
                "bucket": bucket,
                "key": key,
                "project_gid": project_gid,
                "type": type(raw).__name__,
            },
        )
        return None

    try:
        sidecar = parse_sidecar(raw)
    except TtlManifestError as exc:
        # Per ADR-005: sidecar validation failure WARN + fall through.
        logger.warning(
            "ttl_sidecar_validation_failed",
            extra={
                "bucket": bucket,
                "key": key,
                "project_gid": project_gid,
                "rule": exc.rule,
                "error": str(exc),
            },
        )
        return None

    if sidecar.project_gid != project_gid:
        logger.warning(
            "ttl_sidecar_project_gid_mismatch",
            extra={
                "key_project_gid": project_gid,
                "payload_project_gid": sidecar.project_gid,
            },
        )
        return None

    return sidecar


def _is_no_such_key(exc: BaseException) -> bool:
    """Detect S3 NoSuchKey / 404 from an arbitrary boto3-shaped exception.

    Avoids coupling to botocore.exceptions at import time so the module is
    importable in test environments without boto3 installed.
    """
    # botocore.exceptions.ClientError shape: exc.response["Error"]["Code"]
    response = getattr(exc, "response", None)
    if isinstance(response, Mapping):
        error_block = response.get("Error")
        if isinstance(error_block, Mapping):
            code = error_block.get("Code")
            if code in ("NoSuchKey", "404", "NoSuchBucket"):
                # NoSuchBucket also treated as absent — sidecar is optional;
                # a missing bucket means the override channel is not in use.
                return True
        meta = response.get("ResponseMetadata")
        if isinstance(meta, Mapping):
            status = meta.get("HTTPStatusCode")
            if status == 404:
                return True
    # Some shapes (moto with response_class=None) raise a custom subclass.
    name = type(exc).__name__
    return name in ("NoSuchKey", "NoSuchBucket")


# ---------------------------------------------------------------------------
# Resolver — override precedence sidecar > manifest > built-in defaults
# ---------------------------------------------------------------------------


def resolve_ttl(
    project_gid: str,
    section_gid: str,
    *,
    manifest: TtlManifest | None = None,
    sidecar: TtlSidecar | None = None,
) -> tuple[str, int]:
    """Resolve (sla_class, threshold_seconds) for a (project, section) pair.

    Per ADR-005 §"Override precedence":

        1. If sidecar present AND contains entry for section_gid → sidecar.
        2. Else if manifest present AND contains entry for
           manifest.projects[project_gid].sections[section_gid] → manifest.
        3. Else: built-in defaults — manifest.default_class (or "active" if
           manifest absent) and DEFAULT_THRESHOLDS[class].

    Args:
        project_gid: Asana project GID.
        section_gid: Asana section GID.
        manifest: Pre-loaded TtlManifest (None if not yet loaded).
        sidecar: Pre-loaded TtlSidecar for this project (None if absent).

    Returns:
        Tuple of (sla_class, threshold_seconds).
    """
    # Step 1 — sidecar.
    if sidecar is not None and sidecar.project_gid == project_gid:
        section = sidecar.sections.get(section_gid)
        if section is not None:
            return section.sla_class, section.threshold_seconds

    # Step 2 — manifest.
    if manifest is not None:
        project = manifest.projects.get(project_gid)
        if project is not None:
            section = project.sections.get(section_gid)
            if section is not None:
                return section.sla_class, section.threshold_seconds

    # Step 3 — built-in default.
    default_class = manifest.default_class if manifest is not None else BUILTIN_DEFAULT_CLASS
    return default_class, DEFAULT_THRESHOLDS[default_class]


def resolve_threshold_for_class(sla_class: str) -> int:
    """Return the canonical threshold seconds for a known SLA class.

    Used by the CLI ``--sla-profile=<class>`` flag (HANDOFF AC-2 / LD-P2-1)
    where the operator passes the class directly without going through the
    per-section manifest/sidecar lookup.
    """
    if sla_class not in DEFAULT_THRESHOLDS:
        raise TtlManifestError(
            "V-2",
            f"sla_class {sla_class!r} not in {SLA_CLASSES}",
        )
    return DEFAULT_THRESHOLDS[sla_class]
