"""Singleton registry for task-type to schema mapping.

Per FR-MODEL-030 through FR-MODEL-033: Singleton with lazy initialization
and runtime registration support.
"""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from autom8y_log import get_logger

from autom8_asana.dataframes.errors import SchemaNotFoundError, SchemaVersionError

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.core.entity_registry import EntityDescriptor
    from autom8_asana.dataframes.models.schema import DataFrameSchema


# =============================================================================
# Model<->schema drift gate (FRAME-005) -- per ADR-gfr-dynvocab-drift-gate.
#
# The gate DETECTS divergence between an entity's task-model field_name set
# (materialized into cls.Fields from the ADR-0082 _pending_fields registry) and
# that entity's DataFrame schema cf/cascade-name coverage. It is NAME-keyed,
# warn-first, and non-fatal at real import. It HONORS ADR-S4-001: it is a
# read-only comparator -- it never writes a schema, generates a column, or
# mutates a descriptor. Remediation is a human edit to the hand-authored schema.
# =============================================================================

# Per-entity allowlist of model field_names intentionally absent from the
# schema. An excluded field emits at debug (still observable) and does NOT count
# toward ModelSchemaDrift. This is the named-deferral surface that converts a
# silent gap into a visible, owned decision. Keyed by snake_case entity name.
# Matched NAME-normalized (see detect_model_schema_drift).
#
# Empty by default: SPRINT-4 ships warn-first observing the present drift, it
# does NOT pre-accept any gap. Maintainers add entries as gaps are adjudicated.
DRIFT_EXCLUSIONS: dict[str, frozenset[str]] = {}

# Failure-mode knob (ADR Option 1 default + Option 2 promotion path, shipped
# DISABLED). "warn" (default) NEVER raises -- it logs + emits a metric. "error"
# is the operator opt-in promotion path: once a repo's drift is drained to zero
# (every field schema-covered or exclusion-registered) an operator may set
# GFR_DRIFT_GATE_MODE=error to turn NEW drift into a build break. SPRINT-4 does
# NOT promote; the default ships at "warn".
DRIFT_GATE_MODE: Literal["warn", "error"] = (
    "error" if os.environ.get("GFR_DRIFT_GATE_MODE") == "error" else "warn"
)


def _normalize_name(name: str) -> str:
    """NAME-key normalization, identical to the dynvocab tail's.

    Routes through the canonical ``NameNormalizer`` so the gate's NAME-keying is
    byte-for-byte consistent with the runtime resolution path (case- and
    whitespace-agnostic; "Weekly AD Spend" == "Weekly Ad Spend" == "weekly_ad_spend").
    """
    from autom8_asana.dataframes.resolver.normalizer import NameNormalizer

    return NameNormalizer.normalize(name)


def detect_model_schema_drift(
    model_field_names: frozenset[str] | set[str],
    schema_cf_names: frozenset[str] | set[str],
    exclusions: frozenset[str] | set[str],
) -> frozenset[str]:
    """Pure detector: model field_names with NO schema coverage and no exclusion.

    NAME-keyed and side-effect-free (no I/O, no logging) so tests can assert
    RED-on-divergence directly. Returns the ORIGINAL (un-normalized) model field
    names whose NAME-normalized form is neither covered by the schema nor present
    in the exclusion set.

    Args:
        model_field_names: The model's declared cf display names (from cls.Fields).
        schema_cf_names: The schema's covered cf/cascade names + column names.
        exclusions: Accepted-gap field names for this entity (NAME-normalized on match).

    Returns:
        Frozenset of drifted model field names (empty == coherent).
    """
    covered = {_normalize_name(n) for n in schema_cf_names}
    excluded = {_normalize_name(n) for n in exclusions}
    return frozenset(
        f
        for f in model_field_names
        if _normalize_name(f) not in covered and _normalize_name(f) not in excluded
    )


def model_field_names(model_class: type) -> frozenset[str]:
    """The model's declared cf display names from the ADR-0082 Fields registry.

    Reads ``cls.Fields`` (auto-generated in ``__init_subclass__`` from
    ``_pending_fields``) -- each public SCREAMING_SNAKE constant maps to a cf
    display ``field_name`` (e.g. ``ASSET_ID = "Asset ID"``). Returns the set of
    those display names. Empty frozenset if the model has no Fields class.

    EXTRACTION COMPLETENESS (PT-04 investigation): ``cls.Fields`` is generated
    EXCLUSIVELY by ``BusinessEntity.__init_subclass__`` (models/business/base.py)
    from ``_pending_fields``, which is populated EXCLUSIVELY by
    ``CustomFieldDescriptor.__set_name__`` for every cf descriptor subclass
    (TextField/NumberField/EnumField/...). Therefore this captures ALL cf
    descriptors declared on a ``BusinessEntity`` model -- there is no cf-declaration
    idiom outside ``cls.Fields``. The ``*_holder`` entities inherit from
    ``HolderFactory`` (NOT ``BusinessEntity``), so they have NO ``Fields`` class and
    return ``frozenset()`` here. That empty result is INDISTINGUISHABLE from a model
    that genuinely declares zero cf fields -- which is exactly why the caller
    (``model_fields_are_extractable`` -- which keys on the NON-EMPTINESS of this
    function -- plus the UNANALYZABLE state in ``_validate_model_schema_coverage``)
    must NOT treat empty-extraction as "coherent". See ADR-gfr-dynvocab-drift-gate
    §"PT-04 false-green remediation".
    """
    fields_cls = getattr(model_class, "Fields", None)
    if fields_cls is None:
        return frozenset()
    names: set[str] = set()
    for attr in dir(fields_cls):
        if attr.isupper() and not attr.startswith("_"):
            value = getattr(fields_cls, attr)
            if isinstance(value, str):
                names.add(value)
    return frozenset(names)


def model_fields_are_extractable(model_class: type) -> bool:
    """Whether ``model_field_names`` actually materializes >=1 cf field name.

    Re-keyed (PT-04 TERMINATING fix) on the NON-EMPTINESS of ``model_field_names``,
    NOT on the mere presence of a ``cls.Fields`` class. The earlier predicate
    (``getattr(model_class, "Fields", None) is not None``) tested Fields-CLASS
    PRESENCE -- which let an EMPTY / all-private / inherited-empty ``Fields`` class
    (``Fields`` not None, but ``model_field_names() == frozenset()``) report
    extractable=True. The validator then fell through to compare the schema's cf
    coverage against an EMPTY model set, returned no drift, and reported the entity
    COHERENT with a silent ``ModelSchemaDrift=0.0`` -- a verdict reached without a
    single field name ever being extracted to compare. That is the exact
    silent-false-green this gate exists to prevent.

    Keying on ``model_field_names`` non-emptiness closes the WHOLE class: every
    empty-extraction shape -- no ``Fields`` class, an empty ``Fields`` class, an
    all-private/non-str ``Fields`` class, an inherited-empty ``Fields`` class --
    yields False and routes to the DISTINCT ``model_schema_coverage_unanalyzable``
    signal. After this, COHERENT (analyzed, no drift) is reachable ONLY when >=1
    field name was actually extracted; UNANALYZABLE (could not extract any name) is
    its strictly disjoint complement. No narrower false-green case survives.
    """
    return bool(model_field_names(model_class))


def schema_cf_cascade_count(schema: DataFrameSchema) -> int:
    """Number of schema columns that declare a ``cf:`` or ``cascade:`` source.

    A non-zero count means the schema asserts this entity HAS cf/cascade coverage
    to check. Combined with a non-extractable model, that is the UNANALYZABLE
    surface: the gate is being asked to verify coverage it structurally cannot
    extract from the model side.
    """
    return sum(
        1
        for col in schema.columns
        if col.source and (col.source.startswith("cf:") or col.source.startswith("cascade:"))
    )


def schema_covered_names(schema: DataFrameSchema) -> frozenset[str]:
    """The cf-names a schema covers: cf:/cascade: source suffixes + column names.

    A ``source="cf:Asset ID"`` column covers "Asset ID"; a ``source="cascade:Office
    Phone"`` column covers "Office Phone" (covered, just from an ancestor). The
    plain column ``name`` is also treated as coverage so a model field whose
    display name matches a column name (after normalization) is not false-drift.
    """
    covered: set[str] = set()
    for col in schema.columns:
        if col.source and (col.source.startswith("cf:") or col.source.startswith("cascade:")):
            covered.add(col.source.split(":", 1)[1])
        covered.add(col.name)
    return frozenset(covered)


def get_schema(task_type: str) -> DataFrameSchema:
    """Convenience accessor: look up schema by task type.

    Equivalent to ``SchemaRegistry.get_instance().get_schema(task_type)``
    but avoids the ceremony of obtaining the singleton first.

    Args:
        task_type: Task type identifier (e.g., "Unit", "Contact", "*")

    Returns:
        DataFrameSchema for the task type

    Raises:
        SchemaNotFoundError: If no schema registered for type
    """
    return SchemaRegistry.get_instance().get_schema(task_type)


class SchemaRegistry:
    """Singleton registry for task-type to schema mapping (FR-MODEL-030-033).

    Per TDD-0009: Singleton with lazy initialization and runtime
    registration support. Thread-safe via lock.

    Usage:
        >>> registry = SchemaRegistry.get_instance()
        >>> schema = registry.get_schema("Unit")
        >>> schema.name
        'unit'

    Thread Safety:
        The registry is thread-safe. Schema registration and retrieval
        use a lock to prevent race conditions.
    """

    _instance: ClassVar[SchemaRegistry | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _on_reset_callbacks: ClassVar[list[Callable[[], None]]] = []

    # Instance attributes (set in __new__)
    _schemas: dict[str, DataFrameSchema]
    _initialized: bool

    def __new__(cls) -> SchemaRegistry:
        """Create or return singleton instance."""
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._schemas = {}
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> SchemaRegistry:
        """Get or create singleton instance.

        Returns:
            The singleton SchemaRegistry instance
        """
        return cls()

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing only).

        Warning:
            This method is intended for testing only. Do not use
            in production code.

        Note:
            Notifies subscribers via on_reset callbacks (e.g., resolver
            cache clearing) instead of importing private functions directly.
        """
        with cls._lock:
            cls._instance = None

        for callback in cls._on_reset_callbacks:
            callback()

    @classmethod
    def on_reset(cls, callback: Callable[[], None]) -> None:
        """Register a callback to be invoked when the registry is reset.

        Used by dependent modules to subscribe to reset events without
        creating cross-boundary private API imports.

        Args:
            callback: Zero-argument callable invoked on reset.
        """
        cls._on_reset_callbacks.append(callback)

    def _ensure_initialized(self) -> None:
        """Lazy initialization of built-in schemas.

        Per WS1-S2: Auto-wires schemas from EntityDescriptor registry instead
        of hardcoded imports. Each descriptor with a schema_module_path is
        resolved via _resolve_dotted_path() and keyed by effective_schema_key.
        BASE_SCHEMA remains hardcoded because "*" is not an entity type.

        Errors from _resolve_dotted_path() propagate -- a misconfigured
        descriptor must fail loudly at initialization time.
        """
        if self._initialized:
            return

        with self._lock:
            # Double-checked locking
            if self._initialized:
                return

            # Deferred import to avoid circular dependency:
            # dataframes/ must not import core.entity_registry at module scope
            from autom8_asana.core.entity_registry import (
                _resolve_dotted_path,
                get_registry,
            )

            # Auto-wire from entity descriptors
            for desc in get_registry().all_descriptors():
                if desc.schema_module_path:
                    schema = _resolve_dotted_path(desc.schema_module_path)
                    self._schemas[desc.effective_schema_key] = schema

            # BASE_SCHEMA has no entity descriptor -- it's a universal fallback
            from autom8_asana.dataframes.schemas.base import BASE_SCHEMA

            self._schemas["*"] = BASE_SCHEMA
            self._initialized = True

            # Per TDD-ENTITY-EXT-001: Import-time validation
            # Warn about schemas without dedicated extractors
            try:
                self._validate_extractor_coverage()
                # Per ADR-gfr-dynvocab-drift-gate (FRAME-005): sibling validator
                # warns on model->schema drift (where the extractor validator
                # warns on schema->extractor gaps). Warn-first, non-fatal.
                self._validate_model_schema_coverage()
            except Exception:  # noqa: BLE001
                # Per R1.1: Validation MUST NOT crash startup
                # If validation itself fails, log and continue
                from autom8y_log import get_logger

                get_logger(__name__).warning(
                    "schema_validation_failed",
                    exc_info=True,
                )

    def _validate_extractor_coverage(self) -> None:
        """Warn about schemas that lack dedicated extractors.

        Per TDD-ENTITY-EXT-001 US-7: Emits structured warnings for schemas
        registered without hand-coded extractors. SchemaExtractor will handle
        these at runtime, but the warning makes the situation visible in logs.

        This method is called inside _ensure_initialized() and MUST NOT raise
        exceptions that propagate to callers.
        """
        from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

        # Known hand-coded extractors by task_type
        dedicated_extractors: set[str] = {"Unit", "Contact", "*"}

        base_col_names = {c.name for c in BASE_COLUMNS}

        for task_type, schema in self._schemas.items():
            if task_type in dedicated_extractors:
                continue  # Has a hand-coded extractor -- no warning

            schema_col_names = {c.name for c in schema.columns}
            extra_columns = schema_col_names - base_col_names

            if extra_columns:
                from autom8y_log import get_logger

                get_logger(__name__).warning(
                    "schema_using_generic_extractor",
                    extra={
                        "entity": task_type,
                        "schema_name": schema.name,
                        "extra_column_count": len(extra_columns),
                        "note": (
                            "SchemaExtractor will handle extraction; "
                            "add a dedicated extractor only if custom "
                            "derived field logic is needed"
                        ),
                    },
                )

    def _validate_model_schema_coverage(self) -> None:
        """Warn about model fields with no schema/vocabulary coverage (FRAME-005).

        Per ADR-gfr-dynvocab-drift-gate. Sibling of ``_validate_extractor_coverage``:
        where that validator warns on schema->extractor gaps, this one warns on
        model->schema gaps. For each entity descriptor carrying BOTH a
        ``model_class_path`` and a ``schema_module_path``, it compares the model's
        declared cf ``field_name`` set against the schema's covered cf/cascade
        names (NAME-keyed via the canonical NameNormalizer, identical to the
        runtime tail) and emits a structured ``model_schema_drift_detected``
        warning + ``ModelSchemaDrift`` deploy-gate metric for any non-empty,
        non-excluded result.

        WARN-FIRST / NON-FATAL: in the default ``warn`` mode this method NEVER
        raises -- it logs and returns. (And even if it had a bug that raised, the
        ``try/except`` wrapper in ``_ensure_initialized`` swallows it to a
        warning -- a second, defense-in-depth layer.) The ``error`` promotion mode
        (operator opt-in via ``GFR_DRIFT_GATE_MODE=error``) is the documented
        warn->error path; it ships DISABLED. This method is called inside
        ``_ensure_initialized()`` and MUST NOT raise in ``warn`` mode.

        HONORS ADR-S4-001: read-only comparator. It never writes a schema,
        generates a column, or mutates a descriptor.
        """
        from autom8_asana.core.entity_registry import _resolve_dotted_path, get_registry

        total_drift = 0
        total_unanalyzable = 0
        total_unpaired = 0
        for desc in get_registry().all_descriptors():
            has_model = bool(desc.model_class_path)
            has_schema = bool(desc.schema_module_path)
            if not (has_model and has_schema):
                # Single-path (or no-path) descriptor. There is NO counterpart to
                # compare against, so drift analysis is genuinely undefined -- this
                # loop never attempts it for unpaired descriptors. But a single side
                # carrying cf/cascade SUBSTANCE (a schema declaring cf/cascade cols,
                # OR a model declaring >=1 cf field) is precisely the silent
                # coverage-gap class this gate exists to surface. Pre-fix it was
                # dropped with a bare `continue` -- the same silent-skip shape as the
                # PT-04 false-green, one altitude up. Emit a DISTINCT, observable,
                # alarmable `model_schema_coverage_unpaired` signal instead.
                # Descriptors with NEITHER path carry no substance -> nothing to surface.
                if has_model != has_schema:  # exactly one side present
                    total_unpaired += self._emit_unpaired_if_substantive(
                        desc, has_model=has_model, resolve=_resolve_dotted_path
                    )
                continue

            # The guard above `continue`s unless BOTH paths are present (truthy),
            # so both are non-None from here; assert it so the str|None -> str the
            # resolver expects is SOUND (the bool guard cannot narrow the optionals
            # for mypy on its own).
            assert desc.model_class_path is not None and desc.schema_module_path is not None
            model_class = _resolve_dotted_path(desc.model_class_path)
            schema = _resolve_dotted_path(desc.schema_module_path)

            # PT-04 false-green fix (TERMINATING): distinguish COHERENT from
            # UNANALYZABLE. If the schema asserts cf/cascade coverage to check, but
            # the model is not extractable, the gate CANNOT analyze this entity.
            # `model_fields_are_extractable` keys on model_field_names NON-EMPTINESS,
            # so this covers the WHOLE empty-extraction class: no cls.Fields (a
            # HolderFactory entity that never runs the BusinessEntity Fields-gen
            # path), an EMPTY Fields class, an all-private/non-str Fields class, an
            # inherited-empty Fields class -- ANY of which yields zero extracted
            # names. Reporting any of them ModelSchemaDrift=0.0 ("coherent") would be
            # a SILENT FALSE-GREEN reached without comparing a single field name --
            # the exact failure class this gate exists to prevent. Emit a DISTINCT,
            # observable, alarmable signal instead. "Coherent" is now reachable ONLY
            # when >=1 field name was actually extracted.
            cf_cascade_count = schema_cf_cascade_count(schema)
            if cf_cascade_count > 0 and not model_fields_are_extractable(model_class):
                total_unanalyzable += 1
                entity_type = getattr(desc.entity_type, "name", None)
                get_logger(__name__).warning(
                    "model_schema_coverage_unanalyzable",
                    extra={
                        "entity": desc.name,
                        "entity_type": entity_type,
                        "schema_name": schema.name,
                        "schema_cf_cascade_count": cf_cascade_count,
                        "reason": (
                            "model_field_names extracted ZERO cf field names (no "
                            "cls.Fields, OR an empty / all-private / inherited-empty "
                            "Fields class) so the model side is structurally empty; "
                            "the schema declares cf/cascade column(s) the gate "
                            "therefore cannot verify against the model. This is "
                            "UNANALYZABLE, not coherent."
                        ),
                        # DISTINCT metric (1.0 == this entity could not be analyzed).
                        # NOT ModelSchemaDrift=0.0 -- coherent and unanalyzable are
                        # different states and MUST be separately alarmable.
                        "metrics": {"ModelSchemaCoverageUnanalyzable": 1.0},
                        "note": (
                            "fail-loud, never silent-green: an entity whose model cf "
                            "fields cannot be extracted is not asserted coherent. See "
                            "ADR-gfr-dynvocab-drift-gate §PT-04 false-green remediation."
                        ),
                    },
                )
                continue

            field_names = model_field_names(model_class)
            covered_names = schema_covered_names(schema)
            exclusions = DRIFT_EXCLUSIONS.get(desc.name, frozenset())

            drift = detect_model_schema_drift(field_names, covered_names, exclusions)
            if not drift:
                continue

            drift_count = len(drift)
            total_drift += drift_count
            entity_type = getattr(desc.entity_type, "name", None)

            get_logger(__name__).warning(
                "model_schema_drift_detected",
                extra={
                    "entity": desc.name,
                    "entity_type": entity_type,
                    "drifted_fields": tuple(sorted(drift)),
                    "drift_count": drift_count,
                    "schema_name": schema.name,
                    "has_explicit_exclusion": bool(exclusions),
                    # Deploy-gate metric (0.0 == coherent; >0 == drift). Mirrors
                    # the ColumnContractFailure convention, but computed over the
                    # model's FULL declared field set so it cannot be silently
                    # false-green for a field the model knows about.
                    "metrics": {"ModelSchemaDrift": float(drift_count)},
                    "note": (
                        "model declares cf field(s) with no schema/vocabulary "
                        "coverage; the dynvocab tail resolves these at runtime "
                        "but the curated schema under-represents the entity. Add "
                        "a schema column or an explicit drift exclusion. See "
                        "ADR-gfr-dynvocab-drift-gate."
                    ),
                },
            )

        # Promotion path (Option 2), shipped DISABLED. In "error" mode a NEW,
        # un-excluded divergence raises at import (CI/test build break for new
        # drift). The default "warn" mode never reaches this branch.
        if DRIFT_GATE_MODE == "error" and total_drift > 0:
            raise ValueError(
                f"model<->schema drift gate (error mode): {total_drift} uncovered "
                "model field(s) across entities. Add schema coverage or register "
                "a DRIFT_EXCLUSIONS entry. See ADR-gfr-dynvocab-drift-gate."
            )

    def _emit_unpaired_if_substantive(
        self,
        desc: EntityDescriptor,
        *,
        has_model: bool,
        resolve: Callable[[str], Any],
    ) -> int:
        """Emit ``model_schema_coverage_unpaired`` for a substantive single-path descriptor.

        A descriptor carrying exactly one of {``model_class_path``,
        ``schema_module_path``} has NO counterpart to compare against -- drift
        analysis is genuinely undefined and is NOT attempted. But if the single
        present side carries cf/cascade SUBSTANCE (a schema declaring cf/cascade
        columns, or a model declaring >=1 cf field), the missing counterpart is a
        coverage gap the gate must surface rather than silently skip. Emits a
        DISTINCT warn-level signal + ``ModelSchemaCoverageUnpaired`` metric naming
        the descriptor and which side is missing.

        WARN-FIRST / NON-FATAL: never raises. A resolution failure on the single
        present side is itself logged (``model_schema_coverage_unpaired_resolve_failed``)
        and swallowed, so one broken single-path descriptor cannot abort analysis of
        the rest of the registry.

        Returns 1 if an unpaired signal was emitted, else 0 (no substance, or the
        present side could not be resolved).
        """
        try:
            if has_model:
                # Caller invokes this only when exactly one side is present, and
                # passes has_model accordingly, so model_class_path is non-None here.
                model_path = desc.model_class_path
                assert model_path is not None
                substance_count = len(model_field_names(resolve(model_path)))
            else:
                # Symmetric: not-has_model + exactly-one-side => schema_module_path present.
                schema_path = desc.schema_module_path
                assert schema_path is not None
                substance_count = schema_cf_cascade_count(resolve(schema_path))
        except Exception:  # noqa: BLE001 -- warn-first: a bad single-path desc must not abort the loop
            get_logger(__name__).warning(
                "model_schema_coverage_unpaired_resolve_failed",
                extra={"entity": getattr(desc, "name", None)},
                exc_info=True,
            )
            return 0

        if substance_count <= 0:
            # Single-path descriptor with no cf/cascade substance: nothing to
            # surface (e.g. a *_holder model that extracts zero field names, or a
            # schema with no cf/cascade columns). Silent skip is correct here.
            return 0

        present_side = "model" if has_model else "schema"
        missing_side = "schema" if has_model else "model"
        get_logger(__name__).warning(
            "model_schema_coverage_unpaired",
            extra={
                "entity": getattr(desc, "name", None),
                "entity_type": getattr(desc.entity_type, "name", None),
                "present_side": present_side,
                "missing_side": missing_side,
                "substance_count": substance_count,
                # DISTINCT metric (1.0 == this descriptor is unpaired-with-substance).
                # NOT ModelSchemaDrift (no counterpart to compute drift against) and
                # NOT ModelSchemaCoverageUnanalyzable (which is a PAIRED entity whose
                # model could not be extracted). Three separately-alarmable states.
                "metrics": {"ModelSchemaCoverageUnpaired": 1.0},
                "note": (
                    f"descriptor declares a {present_side} carrying cf/cascade "
                    f"substance but has no {missing_side} counterpart; drift analysis "
                    "is undefined (nothing to compare), but the gap is now observable "
                    "instead of silently skipped. See ADR-gfr-dynvocab-drift-gate "
                    "§unpaired single-path observability."
                ),
            },
        )
        return 1

    def get_schema(self, task_type: str) -> DataFrameSchema:
        """Get schema for task type (FR-MODEL-004).

        Args:
            task_type: Task type identifier (e.g., "Unit", "Contact")

        Returns:
            DataFrameSchema for the task type

        Raises:
            SchemaNotFoundError: If no schema registered for type
        """
        self._ensure_initialized()

        with self._lock:
            if task_type in self._schemas:
                return self._schemas[task_type]

            # Fall back to base schema for unknown types
            if "*" in self._schemas:
                return self._schemas["*"]

        raise SchemaNotFoundError(task_type)

    def register(
        self,
        task_type: str,
        schema: DataFrameSchema,
        *,
        allow_override: bool = False,
    ) -> None:
        """Register schema for task type (FR-MODEL-031, post-MVP).

        Args:
            task_type: Task type identifier
            schema: Schema to register
            allow_override: If True, allow replacing existing schema

        Raises:
            SchemaVersionError: If schema conflicts with existing registration
        """
        self._ensure_initialized()

        with self._lock:
            if task_type in self._schemas and not allow_override:
                existing = self._schemas[task_type]
                if existing.version != schema.version:
                    raise SchemaVersionError(
                        schema.name,
                        existing.version,
                        schema.version,
                    )
                # Same version, same type - skip registration
                return

            self._schemas[task_type] = schema

    def has_schema(self, task_type: str) -> bool:
        """Check if schema exists for task type.

        Args:
            task_type: Task type identifier

        Returns:
            True if schema is registered, False otherwise
        """
        self._ensure_initialized()

        with self._lock:
            return task_type in self._schemas

    def list_task_types(self) -> list[str]:
        """List all registered task types.

        Returns:
            List of registered task type identifiers (excludes "*")
        """
        self._ensure_initialized()

        with self._lock:
            return [k for k in self._schemas if k != "*"]

    def get_all_schemas(self) -> dict[str, DataFrameSchema]:
        """Get all registered schemas.

        Returns:
            Dict mapping task types to schemas
        """
        self._ensure_initialized()

        with self._lock:
            return dict(self._schemas)


def get_schema_version(entity_type: str | None) -> str | None:
    """Look up schema version from SchemaRegistry for an entity type.

    Args:
        entity_type: Entity type in lowercase (e.g., "unit", "contact").
            Returns None if entity_type is None or empty.

    Returns:
        Schema version string if found, None if lookup fails.
    """
    if not entity_type:
        return None
    try:
        from autom8_asana.core.string_utils import to_pascal_case

        registry = SchemaRegistry.get_instance()
        registry_key = to_pascal_case(entity_type)
        schema = registry.get_schema(registry_key)
        return schema.version if schema else None
    except (ValueError, KeyError, TypeError, AttributeError, RuntimeError) as e:
        get_logger(__name__).warning(
            "schema_version_lookup_failed",
            extra={"entity_type": entity_type, "error": str(e)},
        )
        return None


# Self-register for SystemContext.reset_all()
from autom8_asana.core.system_context import register_reset  # noqa: E402

register_reset(SchemaRegistry.reset)
