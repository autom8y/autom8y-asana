"""Single source of truth for the dtype <-> field-class invariant (FPC Phase-1).

The Field-Provenance-&-Population-Contract lattice has a recurring failure mode:
a schema ``ColumnDef.dtype`` string and the model field-class that populates that
column drift apart silently (e.g. a number-sourced cell typed ``Utf8`` in the
schema, or an enum-sourced cell typed ``Decimal``). Nothing in the build path
asserts the two agree, so the drift is unrepresentable-as-an-error until it
surfaces as a null-at-rest or a coercion divergence downstream.

This module makes the invariant STRUCTURAL by giving it a single propagation
point. Two maps key off the Python value type a field carries:

- ``DTYPE_MAP`` -- value type -> the canonical schema dtype string for it.
- ``FIELDCLASS_MAP`` -- value type -> the model field-class tokens that produce it
  (descriptor class names like ``NumberField`` AND the asset_edit helper-method
  tokens like ``_get_number_field`` that the method/property style fields call).

The parity check (``tests/unit/dataframes/test_field_contract_parity.py``) reads
ONLY these maps to compute the expected dtype for a cell from its model
field-class. No per-cell dtype is hardcoded anywhere; adding or changing the
invariant happens here and nowhere else (the G-PROPAGATE guarantee).

SCOPE NOTE (FPC Phase-1, G-DEFER): the dtype-parity maps + the parity CHECK are
Phase-1. The full ``FieldContract`` dataclass/registry and schema-FROM-model
derivation remain deferred (NO model-codegen -- that reverses ADR-S4-001, a
one-way door). The CONSUMER-required-column contract below (FM-5 ARM-B) is the
Phase-3 work this file's scope note anticipated, built INTO this module so the
field-contract substrate keeps exactly one propagation point (G-PROPAGATE): the
consumer manifest is ingested here, the per-query-shape required SET is derived
here, and nothing replicates that logic per-consumer (C2 derive/delegate-never-
replicate). See ``ADR-fm5-armb-contract-locus`` / ``TDD-fm5-armb-honest-refusal-
contract``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

__all__ = [
    "DTYPE_MAP",
    "FIELDCLASS_MAP",
    "VENDORED_MANIFEST_PATH",
    "ConsumerManifestError",
    "ConsumerRequirement",
    "ConsumerRequirements",
    "DriftReport",
    "QueryShape",
    "derive_required_columns",
    "expected_dtype_for_value_type",
    "load_consumer_requirements",
    "requirements_drift_check",
    "value_type_for_field_class",
]


# Python value type -> canonical schema dtype string (the ``ColumnDef.dtype``
# vocabulary). "Decimal" and "Float64" both resolve to ``pl.Float64`` at runtime
# (see ColumnDef.get_polars_dtype), but the schema STRING is the contract surface
# the parity check audits: a number-sourced cell's canonical string is "Decimal".
DTYPE_MAP: dict[type, str] = {
    Decimal: "Decimal",
    int: "Int64",
    str: "Utf8",
    bool: "Boolean",
    float: "Float64",
}


# Python value type -> the set of model field-class identifiers that produce it.
# Membership tokens are matched against BOTH:
#   - descriptor class names (Unit/Offer fields are class-level descriptor
#     instances: NumberField, IntField, EnumField, TextField, ...), and
#   - asset_edit helper-method tokens (AssetEdit's number/int cells are
#     @property getters whose body calls ``self._get_number_field(...)`` /
#     ``self._get_int_field(...)``).
# A field-class identifier resolving into one of these frozensets pins the value
# type, and DTYPE_MAP then pins the expected schema dtype string.
FIELDCLASS_MAP: dict[type, frozenset[str]] = {
    Decimal: frozenset({"NumberField", "_get_number_field"}),
    int: frozenset({"IntField", "_get_int_field"}),
    str: frozenset({"TextField", "EnumField"}),
}


def value_type_for_field_class(field_class_token: str) -> type | None:
    """Return the Python value type a model field-class identifier produces.

    Args:
        field_class_token: A descriptor class name (e.g. ``"NumberField"``) or an
            asset_edit helper-method token (e.g. ``"_get_number_field"``).

    Returns:
        The Python value type per ``FIELDCLASS_MAP``, or ``None`` if the token is
        not a number/int/text-producing field class (e.g. MultiEnumField).
    """
    for value_type, tokens in FIELDCLASS_MAP.items():
        if field_class_token in tokens:
            return value_type
    return None


def expected_dtype_for_value_type(value_type: type) -> str | None:
    """Return the canonical schema dtype string for a Python value type.

    Args:
        value_type: A Python type key present in ``DTYPE_MAP``.

    Returns:
        The canonical schema dtype string, or ``None`` if the value type has no
        mapped dtype.
    """
    return DTYPE_MAP.get(value_type)


# ---------------------------------------------------------------------------
# FM-5 ARM-B — the consumer-required-column contract (Phase-3 SCOPE NOTE).
#
# A consumer DECLARES the columns its code indexes (the vendored manifest); this
# module ingests that declaration and DERIVES the per-(entity_type, endpoint)
# required-column SET. The derivation is the SOLE propagation point that seeds:
#   (i)  the CI parity test (a declared column the served schema cannot satisfy
#        is build-time visible, not a prod KeyError),
#   (ii) the two-sided discriminating canary, and
#   (iii) what the monolith bridge reads to populate the /v1/query wire field.
# Runtime enforcement uses the wire field as authoritative (see query/engine.py
# ``_derive_column_contract``); this layer is the declaration of record + seed.
# ---------------------------------------------------------------------------

# The vendored copy of the monolith-owned manifest. The monolith repo is the
# source of truth; ``requirements_drift_check`` asserts vendored == source once
# the source path is handed back (telos DEFER input — the cross-repo round-trip).
VENDORED_MANIFEST_PATH: Path = Path(__file__).parent / "consumer_column_requirements.vendored.json"

# v1 closed vocabularies (fail-loud on anything outside them; never silently
# coerce an unknown token).
_SUPPORTED_SCHEMA_VERSION = 1
_VALID_POPULATION_EXPECTATIONS = frozenset(
    {"present_any", "present_all_rows", "nonnull_over_active_subset"}
)
_VALID_ON_MISSING = frozenset({"typed_incomplete"})


class ConsumerManifestError(ValueError):
    """The vendored consumer manifest is malformed or carries an unsupported value.

    Raised eagerly at load time so a structurally-broken declaration fails loud at
    build/CI time rather than silently degrading the contract at runtime.
    """


@dataclass(frozen=True)
class QueryShape:
    """The (endpoint, entity_type) a consumer's declaration targets."""

    endpoint: str
    entity_type: str


@dataclass(frozen=True)
class ConsumerRequirement:
    """One consumer's required-column declaration for a single query shape."""

    consumer_id: str
    code_anchor: str
    query_shape: QueryShape
    required_columns: tuple[str, ...]
    population_expectation: str
    on_missing: str


@dataclass(frozen=True)
class ConsumerRequirements:
    """The parsed, validated vendored manifest."""

    schema_version: int
    declared_by: str
    declared_at: str
    consumers: tuple[ConsumerRequirement, ...]


@dataclass(frozen=True)
class DriftReport:
    """Result of the freshness guard (``requirements_drift_check``).

    Attributes:
        mode: ``"schema-only"`` until the monolith source is handed back, then
            ``"source-compared"``.
        ok: True iff the vendored manifest is valid AND (in source-compared mode)
            byte-identical to the monolith source.
        drift: True iff source-compared and the bytes diverge.
        vendored_sha256: SHA-256 of the vendored manifest bytes (the recorded seed).
        declared_at: ``declared_at`` from the vendored manifest.
        source_sha256: SHA-256 of the monolith-source bytes, or ``None`` in
            schema-only mode.
        detail: Human-auditable one-line summary.
    """

    mode: str
    ok: bool
    drift: bool
    vendored_sha256: str
    declared_at: str
    source_sha256: str | None
    detail: str


def _coerce_str(value: object, *, field_name: str, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConsumerManifestError(
            f"{context}: field '{field_name}' must be a non-empty string, got {value!r}"
        )
    return value


def _parse_consumer(entry: object, *, index: int) -> ConsumerRequirement:
    context = f"consumers[{index}]"
    if not isinstance(entry, dict):
        raise ConsumerManifestError(f"{context}: each consumer entry must be an object")

    shape_raw = entry.get("query_shape")
    if not isinstance(shape_raw, dict):
        raise ConsumerManifestError(f"{context}: 'query_shape' must be an object")
    query_shape = QueryShape(
        endpoint=_coerce_str(
            shape_raw.get("endpoint"), field_name="query_shape.endpoint", context=context
        ),
        entity_type=_coerce_str(
            shape_raw.get("entity_type"), field_name="query_shape.entity_type", context=context
        ),
    )

    columns_raw = entry.get("required_columns")
    if not isinstance(columns_raw, list) or not all(isinstance(c, str) for c in columns_raw):
        raise ConsumerManifestError(f"{context}: 'required_columns' must be a list of strings")

    population_expectation = _coerce_str(
        entry.get("population_expectation"), field_name="population_expectation", context=context
    )
    if population_expectation not in _VALID_POPULATION_EXPECTATIONS:
        raise ConsumerManifestError(
            f"{context}: unsupported population_expectation {population_expectation!r}; "
            f"expected one of {sorted(_VALID_POPULATION_EXPECTATIONS)}"
        )

    on_missing = _coerce_str(entry.get("on_missing"), field_name="on_missing", context=context)
    if on_missing not in _VALID_ON_MISSING:
        raise ConsumerManifestError(
            f"{context}: unsupported on_missing {on_missing!r}; expected one of {sorted(_VALID_ON_MISSING)}"
        )

    return ConsumerRequirement(
        consumer_id=_coerce_str(
            entry.get("consumer_id"), field_name="consumer_id", context=context
        ),
        code_anchor=_coerce_str(
            entry.get("code_anchor"), field_name="code_anchor", context=context
        ),
        query_shape=query_shape,
        required_columns=tuple(columns_raw),
        population_expectation=population_expectation,
        on_missing=on_missing,
    )


def load_consumer_requirements(path: Path | None = None) -> ConsumerRequirements:
    """Read and validate the vendored consumer-required-column manifest.

    Args:
        path: Manifest path. Defaults to :data:`VENDORED_MANIFEST_PATH`.

    Returns:
        The parsed :class:`ConsumerRequirements`.

    Raises:
        ConsumerManifestError: The file is missing, is not valid JSON, declares an
            unsupported ``schema_version``, or any consumer entry is malformed.
            Always fail-loud — never a silent partial parse.
    """
    manifest_path = path or VENDORED_MANIFEST_PATH
    try:
        raw_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConsumerManifestError(
            f"cannot read consumer manifest at {manifest_path}: {exc}"
        ) from exc

    try:
        doc = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConsumerManifestError(
            f"consumer manifest at {manifest_path} is not valid JSON: {exc}"
        ) from exc

    if not isinstance(doc, dict):
        raise ConsumerManifestError(f"consumer manifest at {manifest_path} must be a JSON object")

    schema_version = doc.get("schema_version")
    if schema_version != _SUPPORTED_SCHEMA_VERSION:
        raise ConsumerManifestError(
            f"unsupported manifest schema_version {schema_version!r}; "
            f"this build supports v{_SUPPORTED_SCHEMA_VERSION}"
        )

    consumers_raw = doc.get("consumers")
    if not isinstance(consumers_raw, list):
        raise ConsumerManifestError("consumer manifest field 'consumers' must be a list")

    consumers = tuple(_parse_consumer(entry, index=i) for i, entry in enumerate(consumers_raw))

    return ConsumerRequirements(
        schema_version=schema_version,
        declared_by=_coerce_str(
            doc.get("declared_by"), field_name="declared_by", context="manifest"
        ),
        declared_at=_coerce_str(
            doc.get("declared_at"), field_name="declared_at", context="manifest"
        ),
        consumers=consumers,
    )


def derive_required_columns(
    entity_type: str,
    endpoint: str,
    *,
    requirements: ConsumerRequirements | None = None,
) -> frozenset[str]:
    """Derive the required-column SET for a query shape (the union over consumers).

    The per-(entity_type, endpoint) required set = the union of ``required_columns``
    over every consumer whose ``query_shape`` matches. This is RULING-1's
    contract-driven SUBSET: the set grows only as a consumer declares, never an
    eager full-parity set. It is the build-time / canary / CI source of truth and
    what the monolith bridge reads to populate the authoritative wire field.

    Args:
        entity_type: The query's entity type (e.g. ``"project"``).
        endpoint: The query endpoint (e.g. ``"/v1/query/project/rows"``).
        requirements: Pre-loaded requirements; loads the vendored manifest if None.

    Returns:
        The union of required column names for the matching query shape (possibly
        empty if no consumer declares against it).
    """
    reqs = requirements if requirements is not None else load_consumer_requirements()
    required: set[str] = set()
    for consumer in reqs.consumers:
        if (
            consumer.query_shape.entity_type == entity_type
            and consumer.query_shape.endpoint == endpoint
        ):
            required.update(consumer.required_columns)
    return frozenset(required)


def requirements_drift_check(monolith_source: Path | None) -> DriftReport:
    """Freshness guard for the vendored manifest (reversed-SNC pattern, WARN-first).

    Two modes:
        * ``monolith_source is None`` (schema-only) — validates that the vendored
          manifest loads against the v1 schema and records its sha256 + declared_at.
          This is the mode until the monolith source path is handed back (telos
          DEFER): a parseable vendored manifest is OK; no source comparison is made.
        * ``monolith_source`` provided (source-compared) — asserts the vendored
          bytes equal the monolith-source bytes; any divergence is DRIFT (ok=False).

    This is a WARN-first guard (the report carries ``ok``/``drift``; the CI test
    decides the gate). It performs NO model-codegen and NO auto-regeneration —
    that would reverse ADR-S4-001 (a one-way door).

    Args:
        monolith_source: Path to the monolith source manifest, or None for
            schema-only mode.

    Returns:
        A :class:`DriftReport`.

    Raises:
        ConsumerManifestError: The vendored manifest itself is unparseable (a hard
            failure in either mode — the seed of record must always be valid).
    """
    vendored = load_consumer_requirements()  # raises if the vendored seed is malformed
    vendored_bytes = VENDORED_MANIFEST_PATH.read_bytes()
    vendored_sha = hashlib.sha256(vendored_bytes).hexdigest()

    if monolith_source is None:
        return DriftReport(
            mode="schema-only",
            ok=True,
            drift=False,
            vendored_sha256=vendored_sha,
            declared_at=vendored.declared_at,
            source_sha256=None,
            detail=(
                "schema-only: vendored manifest valid; monolith source not yet "
                "handed back (telos DEFER) — no source comparison performed"
            ),
        )

    try:
        source_bytes = monolith_source.read_bytes()
    except OSError as exc:
        raise ConsumerManifestError(
            f"cannot read monolith source manifest at {monolith_source}: {exc}"
        ) from exc
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    drift = vendored_bytes != source_bytes

    return DriftReport(
        mode="source-compared",
        ok=not drift,
        drift=drift,
        vendored_sha256=vendored_sha,
        declared_at=vendored.declared_at,
        source_sha256=source_sha,
        detail=(
            "source-compared: vendored == source"
            if not drift
            else "source-compared: DRIFT — vendored manifest diverges from monolith source"
        ),
    )
