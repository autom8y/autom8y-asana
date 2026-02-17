"""Entity Knowledge Registry -- single source of truth for entity metadata.

Consolidates entity knowledge into one declaration per entity type. All 4
DataFrame layer consumers are descriptor-driven:

1. SchemaRegistry._ensure_initialized() -- auto-discovers schemas via
   schema_module_path (no hardcoded imports).
2. _create_extractor() -- resolves extractor classes via extractor_class_path
   (no hardcoded match/case branches).
3. ENTITY_RELATIONSHIPS -- derived from join_keys on descriptors.
4. _build_cascading_field_registry() -- discovers providers via
   cascading_field_provider flag.

Validation checks 6a-6f run at import time to catch triad inconsistencies
(schema/extractor/row model). Path syntax is validated at module load;
actual import resolution is deferred to avoid circular imports (tested in
TestDataFramePathResolution).

Backward-compatible facades (ENTITY_TYPES, DEFAULT_ENTITY_TTLS,
ENTITY_ALIASES, DEFAULT_KEY_COLUMNS) delegate to this registry.

Per TDD-ENTITY-REGISTRY-001:
- EntityDescriptor: Frozen dataclass capturing all metadata for one entity type
- EntityRegistry: Singleton with O(1) lookup by name, project GID, and EntityType
- ENTITY_DESCRIPTORS: Module-level tuple of all descriptors (the single source of truth)
- Import-time integrity validation

Usage:
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()
    desc = registry.get("unit")
    desc = registry.get_by_gid("1201081073731555")
    warmable = registry.warmable_entities()
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


def _resolve_dotted_path(dotted_path: str) -> Any:
    """Resolve a dotted import path to the referenced object.

    Handles both 'module.path.ClassName' and 'module.path.CONSTANT_NAME'.

    Args:
        dotted_path: Fully qualified dotted path.

    Returns:
        The resolved object (class, constant, etc.)

    Raises:
        ImportError: If the module cannot be imported or path is invalid.
        AttributeError: If the attribute does not exist on the module.
    """
    module_path, _, attr_name = dotted_path.rpartition(".")
    if not module_path:
        raise ImportError(f"Invalid dotted path (no module): {dotted_path!r}")
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


class EntityCategory(str, Enum):
    """Classification of entity types by their role in the hierarchy."""

    ROOT = "root"  # Business
    COMPOSITE = "composite"  # Unit (has nested holders)
    LEAF = "leaf"  # Contact, Offer, Process, Location, Hours, AssetEdit
    HOLDER = "holder"  # All *Holder types


@dataclass(frozen=True, slots=True)
class EntityDescriptor:
    """Complete metadata for a single entity type.

    Frozen for thread safety and hashability. One instance per entity type
    is defined in ENTITY_DESCRIPTORS and never mutated after module load.

    Attributes:
        name: Canonical snake_case identifier (e.g., "unit", "asset_edit_holder").
        pascal_name: PascalCase form for SchemaRegistry lookups.
        display_name: Human-readable name for UI/logging.
        entity_type: EntityType enum member, or None for entities without one.
        category: Classification as root, composite, leaf, or holder.
        primary_project_gid: Asana project GID, or None.
        model_class_path: Dotted import path for lazy model class resolution.
        parent_entity: Name of the parent entity type, or None for root.
        holder_for: Name of the leaf entity this holder contains, or None.
        holder_attr: Private attribute name on parent model, or None.
        name_pattern: Substring pattern for Tier 2 name detection.
        emoji: Custom emoji indicator for holder matching.
        schema_key: SchemaRegistry lookup key. Defaults to pascal_name.
        default_ttl_seconds: Cache TTL in seconds. Defaults to 300.
        warmable: Whether included in Lambda cache warming.
        warm_priority: Warming order (lower = higher priority).
        aliases: Field normalization alias chain for resolver.
        join_keys: Default join column by target entity type.
        key_columns: Default key columns for DynamicIndex resolution.
        explicit_name_mappings: Asana project name -> entity type mappings.
        schema_module_path: Dotted path to DataFrame schema constant (e.g.,
            "autom8_asana.dataframes.schemas.unit.UNIT_SCHEMA").
        extractor_class_path: Dotted path to extractor class (e.g.,
            "autom8_asana.dataframes.extractors.unit.UnitExtractor").
        row_model_class_path: Dotted path to row model class (e.g.,
            "autom8_asana.dataframes.models.task_row.UnitRow").
        cascading_field_provider: True if model_class has a CascadingFields
            inner class used by _build_cascading_field_registry().
    """

    # --- Identity ---
    name: str
    pascal_name: str
    display_name: str
    entity_type: Any = None  # EntityType | None -- Any to avoid circular import
    category: EntityCategory = EntityCategory.LEAF

    # --- Asana Project ---
    primary_project_gid: str | None = None
    model_class_path: str | None = None

    # --- Hierarchy ---
    parent_entity: str | None = None
    holder_for: str | None = None
    holder_attr: str | None = None

    # --- Detection ---
    name_pattern: str | None = None
    emoji: str | None = None

    # --- Schema ---
    schema_key: str | None = None  # Defaults to pascal_name if None

    # --- Cache Behavior ---
    default_ttl_seconds: int = 300
    warmable: bool = False
    warm_priority: int = 99

    # --- Field Normalization ---
    aliases: tuple[str, ...] = ()
    join_keys: tuple[tuple[str, str], ...] = ()  # ((target, key), ...)
    key_columns: tuple[str, ...] = ()

    # --- Discovery ---
    explicit_name_mappings: tuple[tuple[str, str], ...] = ()

    # --- DataFrame Layer ---
    schema_module_path: str | None = None
    extractor_class_path: str | None = None
    row_model_class_path: str | None = None
    cascading_field_provider: bool = False

    @property
    def effective_schema_key(self) -> str:
        """Schema key for SchemaRegistry lookup."""
        return self.schema_key or self.pascal_name

    @property
    def is_holder(self) -> bool:
        """True if this entity is a holder type."""
        return self.category == EntityCategory.HOLDER

    @property
    def has_project(self) -> bool:
        """True if this entity has a dedicated Asana project."""
        return self.primary_project_gid is not None

    def get_join_key(self, target: str) -> str | None:
        """Get the default join column for joining with target entity type."""
        for t, k in self.join_keys:
            if t == target:
                return k
        return None

    def get_model_class(self) -> type | None:
        """Lazily resolve model class from dotted path.

        Returns None if model_class_path is not set. Raises ImportError
        if the path is invalid.
        """
        if self.model_class_path is None:
            return None
        result: type | None = _resolve_dotted_path(self.model_class_path)
        return result


class EntityRegistry:
    """Singleton registry providing O(1) lookup of entity metadata.

    Built at module load time from ENTITY_DESCRIPTORS. Provides three
    indexes for different lookup patterns:
    - by name (snake_case): Primary lookup for most subsystems
    - by project GID: Used by detection Tier 1 and bootstrap
    - by EntityType enum: Used by detection, hydration, holder logic

    Thread Safety:
        All state is built once at module load and never mutated.
        No locks needed for reads.

    Attributes:
        strict_triad_validation: When True, check 6d ("schema_without_extractor")
            becomes a ValueError instead of a warning. Default: False (preserving
            backward compatibility). Set to True after all schemas have matching
            extractors. See ADR-S4-001 and ARCH doc section 4.3.
    """

    def __init__(
        self,
        descriptors: tuple[EntityDescriptor, ...],
        *,
        strict_triad_validation: bool = False,
    ) -> None:
        self._descriptors = descriptors
        self._by_name: dict[str, EntityDescriptor] = {}
        self._by_gid: dict[str, EntityDescriptor] = {}
        self._by_type: dict[Any, EntityDescriptor] = {}
        self.strict_triad_validation = strict_triad_validation

        for d in descriptors:
            if d.name in self._by_name:
                raise ValueError(f"Duplicate entity name: {d.name!r}")
            self._by_name[d.name] = d

            if d.primary_project_gid is not None:
                if d.primary_project_gid in self._by_gid:
                    existing = self._by_gid[d.primary_project_gid]
                    raise ValueError(
                        f"Duplicate project GID {d.primary_project_gid!r}: "
                        f"{d.name!r} conflicts with {existing.name!r}"
                    )
                self._by_gid[d.primary_project_gid] = d

            if d.entity_type is not None:
                if d.entity_type in self._by_type:
                    existing = self._by_type[d.entity_type]
                    raise ValueError(
                        f"Duplicate EntityType {d.entity_type!r}: "
                        f"{d.name!r} conflicts with {existing.name!r}"
                    )
                self._by_type[d.entity_type] = d

    # --- Primary Lookups ---

    def get(self, name: str) -> EntityDescriptor | None:
        """Lookup by canonical snake_case name. O(1)."""
        return self._by_name.get(name)

    def require(self, name: str) -> EntityDescriptor:
        """Lookup by name, raising if not found.

        Raises:
            KeyError: If entity name is not registered.
        """
        desc = self._by_name.get(name)
        if desc is None:
            available = sorted(self._by_name.keys())
            raise KeyError(f"Unknown entity type: {name!r}. Available: {available}")
        return desc

    def get_by_gid(self, project_gid: str) -> EntityDescriptor | None:
        """Lookup by Asana project GID. O(1)."""
        return self._by_gid.get(project_gid)

    def get_by_type(self, entity_type: Any) -> EntityDescriptor | None:
        """Lookup by EntityType enum member. O(1)."""
        return self._by_type.get(entity_type)

    # --- Collection Queries ---

    def all_descriptors(self) -> tuple[EntityDescriptor, ...]:
        """All registered descriptors in definition order."""
        return self._descriptors

    def all_names(self) -> list[str]:
        """All registered entity names in definition order."""
        return [d.name for d in self._descriptors]

    def warmable_entities(self) -> list[EntityDescriptor]:
        """Entities included in cache warming, sorted by priority (ascending).

        Returns:
            List of warmable EntityDescriptors, lowest warm_priority first.
        """
        return sorted(
            [d for d in self._descriptors if d.warmable],
            key=lambda d: d.warm_priority,
        )

    def dataframe_entities(self) -> list[str]:
        """Entity names that have DataFrame schemas (warmable or schema-bearing).

        Used by schema providers and cache stats initialization.
        """
        return [d.name for d in self._descriptors if d.warmable]

    def holders(self) -> list[EntityDescriptor]:
        """All holder entity types."""
        return [d for d in self._descriptors if d.is_holder]

    def get_join_key(self, source: str, target: str) -> str | None:
        """Get the default join key between two entity types.

        Checks both directions (source -> target and target -> source).
        """
        desc = self._by_name.get(source)
        if desc is not None:
            key = desc.get_join_key(target)
            if key is not None:
                return key

        # Check reverse direction
        desc = self._by_name.get(target)
        if desc is not None:
            key = desc.get_join_key(source)
            if key is not None:
                return key

        return None

    def get_entity_ttl(self, name: str, default: int = 300) -> int:
        """Get cache TTL for entity type.

        Args:
            name: Entity name (case-insensitive).
            default: Fallback TTL if entity not found.
        """
        desc = self._by_name.get(name.lower())
        if desc is not None:
            return desc.default_ttl_seconds
        return default

    def get_aliases(self, name: str) -> tuple[str, ...]:
        """Get field normalization aliases for entity type."""
        desc = self._by_name.get(name)
        if desc is not None:
            return desc.aliases
        return ()

    def get_key_columns(self, name: str) -> tuple[str, ...]:
        """Get default key columns for DynamicIndex resolution."""
        desc = self._by_name.get(name)
        if desc is not None:
            return desc.key_columns
        return ()


# --- Module-Level Singleton ---


def _to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


# =============================================================================
# ENTITY_DESCRIPTORS: The single source of truth for all entity types.
# Adding a new entity type means adding one entry here.
#
# Adding a New Entity with a DataFrame Schema (2-File Pattern):
#   1. Add an EntityDescriptor entry below with schema_module_path set.
#   2. Create the corresponding schema file in dataframes/schemas/.
#   Schema files are auto-discovered via schema_module_path; no hardcoded
#   imports needed in SchemaRegistry. Validation check 6a catches mismatches
#   at import time. See ADR-S4-001 for the rationale behind keeping schemas
#   as separate files rather than generating them from descriptor metadata.
# =============================================================================

ENTITY_DESCRIPTORS: tuple[EntityDescriptor, ...] = (
    # =========================================================================
    # Root Entity
    # =========================================================================
    EntityDescriptor(
        name="business",
        pascal_name="Business",
        display_name="Business",
        entity_type=None,  # Set post-import via _bind_entity_types()
        category=EntityCategory.ROOT,
        primary_project_gid="1200653012566782",
        model_class_path="autom8_asana.models.business.business.Business",
        default_ttl_seconds=3600,
        warmable=True,
        warm_priority=2,
        aliases=("office",),
        join_keys=(
            ("unit", "office_phone"),
            ("contact", "office_phone"),
            ("offer", "office_phone"),
        ),
        key_columns=("office_phone",),
        schema_module_path="autom8_asana.dataframes.schemas.business.BUSINESS_SCHEMA",
        cascading_field_provider=True,
    ),
    # =========================================================================
    # Composite Entity
    # =========================================================================
    EntityDescriptor(
        name="unit",
        pascal_name="Unit",
        display_name="Business Units",
        entity_type=None,  # Set post-import
        category=EntityCategory.COMPOSITE,
        primary_project_gid="1201081073731555",
        model_class_path="autom8_asana.models.business.unit.Unit",
        default_ttl_seconds=900,
        warmable=True,
        warm_priority=1,
        aliases=("business_unit",),
        join_keys=(
            ("business", "office_phone"),
            ("offer", "office_phone"),
        ),
        key_columns=("office_phone", "vertical"),
        schema_module_path="autom8_asana.dataframes.schemas.unit.UNIT_SCHEMA",
        extractor_class_path="autom8_asana.dataframes.extractors.unit.UnitExtractor",
        row_model_class_path="autom8_asana.dataframes.models.task_row.UnitRow",
        cascading_field_provider=True,
    ),
    # =========================================================================
    # Leaf Entities
    # =========================================================================
    EntityDescriptor(
        name="contact",
        pascal_name="Contact",
        display_name="Contact",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid="1200775689604552",
        model_class_path="autom8_asana.models.business.contact.Contact",
        default_ttl_seconds=900,
        warmable=True,
        warm_priority=4,
        aliases=(),
        join_keys=(("business", "office_phone"),),
        key_columns=("office_phone", "contact_phone", "contact_email"),
        schema_module_path="autom8_asana.dataframes.schemas.contact.CONTACT_SCHEMA",
        extractor_class_path="autom8_asana.dataframes.extractors.contact.ContactExtractor",
        row_model_class_path="autom8_asana.dataframes.models.task_row.ContactRow",
    ),
    EntityDescriptor(
        name="offer",
        pascal_name="Offer",
        display_name="Offer",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid="1143843662099250",
        model_class_path="autom8_asana.models.business.offer.Offer",
        default_ttl_seconds=180,
        warmable=True,
        warm_priority=3,
        aliases=("business_offer",),
        join_keys=(
            ("unit", "office_phone"),
            ("business", "office_phone"),
        ),
        key_columns=("office_phone", "vertical", "offer_id"),
        schema_module_path="autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA",
    ),
    EntityDescriptor(
        name="asset_edit",
        pascal_name="AssetEdit",
        display_name="Asset Edits",
        entity_type=None,  # No dedicated EntityType enum member
        category=EntityCategory.LEAF,
        primary_project_gid="1202204184560785",
        model_class_path="autom8_asana.models.business.asset_edit.AssetEdit",
        default_ttl_seconds=300,
        warmable=True,
        warm_priority=5,
        aliases=("process",),
        key_columns=("office_phone", "vertical", "asset_id", "offer_id"),
        explicit_name_mappings=(("paid content", "asset_edit"),),
        schema_module_path="autom8_asana.dataframes.schemas.asset_edit.ASSET_EDIT_SCHEMA",
    ),
    EntityDescriptor(
        name="process",
        pascal_name="Process",
        display_name="Process",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid=None,  # Dynamic via workspace discovery
        model_class_path="autom8_asana.models.business.process.Process",
        default_ttl_seconds=60,
    ),
    EntityDescriptor(
        name="location",
        pascal_name="Location",
        display_name="Location",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid="1200836133305610",
        model_class_path="autom8_asana.models.business.location.Location",
        default_ttl_seconds=3600,
    ),
    EntityDescriptor(
        name="hours",
        pascal_name="Hours",
        display_name="Hours",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid="1201614578074026",
        model_class_path="autom8_asana.models.business.hours.Hours",
        default_ttl_seconds=3600,
    ),
    # =========================================================================
    # Business-Level Holders
    # =========================================================================
    EntityDescriptor(
        name="contact_holder",
        pascal_name="ContactHolder",
        display_name="Contacts",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1201500116978260",
        model_class_path="autom8_asana.models.business.contact.ContactHolder",
        parent_entity="business",
        holder_for="contact",
        holder_attr="_contact_holder",
        name_pattern="contacts",
        emoji="busts_in_silhouette",
    ),
    EntityDescriptor(
        name="unit_holder",
        pascal_name="UnitHolder",
        display_name="Business Units",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1204433992667196",
        model_class_path="autom8_asana.models.business.unit.UnitHolder",
        parent_entity="business",
        holder_for="unit",
        holder_attr="_unit_holder",
        name_pattern="units",
        emoji="package",
    ),
    EntityDescriptor(
        name="location_holder",
        pascal_name="LocationHolder",
        display_name="Location",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid=None,
        model_class_path="autom8_asana.models.business.location.LocationHolder",
        parent_entity="business",
        holder_for="location",
        holder_attr="_location_holder",
        name_pattern="location",
        emoji="round_pushpin",
    ),
    EntityDescriptor(
        name="dna_holder",
        pascal_name="DNAHolder",
        display_name="DNA",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1167650840134033",
        model_class_path="autom8_asana.models.business.business.DNAHolder",
        parent_entity="business",
        holder_attr="_dna_holder",
        name_pattern="dna",
        emoji="dna",
    ),
    EntityDescriptor(
        name="reconciliation_holder",
        pascal_name="ReconciliationHolder",
        display_name="Reconciliations",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1203404998225231",
        model_class_path="autom8_asana.models.business.business.ReconciliationHolder",
        parent_entity="business",
        holder_attr="_reconciliation_holder",
        name_pattern="reconciliations",
        emoji="abacus",
    ),
    EntityDescriptor(
        name="asset_edit_holder",
        pascal_name="AssetEditHolder",
        display_name="Asset Edits",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1203992664400125",
        model_class_path="autom8_asana.models.business.business.AssetEditHolder",
        parent_entity="business",
        holder_for="asset_edit",
        holder_attr="_asset_edit_holder",
        name_pattern="asset edit",
        emoji="art",
        warmable=True,
        warm_priority=6,
        aliases=(),
        key_columns=("office_phone",),
        schema_module_path="autom8_asana.dataframes.schemas.asset_edit_holder.ASSET_EDIT_HOLDER_SCHEMA",
    ),
    EntityDescriptor(
        name="videography_holder",
        pascal_name="VideographyHolder",
        display_name="Videography",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1207984018149338",
        model_class_path="autom8_asana.models.business.business.VideographyHolder",
        parent_entity="business",
        holder_attr="_videography_holder",
        name_pattern="videography",
        emoji="video_camera",
    ),
    # =========================================================================
    # Unit-Level Holders
    # =========================================================================
    EntityDescriptor(
        name="offer_holder",
        pascal_name="OfferHolder",
        display_name="Offers",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1210679066066870",
        model_class_path="autom8_asana.models.business.offer.OfferHolder",
        parent_entity="unit",
        holder_for="offer",
        holder_attr="_offer_holder",
        name_pattern="offers",
        emoji="gift",
    ),
    EntityDescriptor(
        name="process_holder",
        pascal_name="ProcessHolder",
        display_name="Processes",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid=None,
        model_class_path="autom8_asana.models.business.process.ProcessHolder",
        parent_entity="unit",
        holder_for="process",
        holder_attr="_process_holder",
        name_pattern="processes",
        emoji="gear",
    ),
)


# --- EntityType Binding ---
# Performed at module load AFTER EntityType is importable.
# This deferred binding avoids circular imports from core -> models.
# Per ADR-001: Uses object.__setattr__ to mutate frozen dataclass instances.
# Safe because this runs exactly once before any consumer reads the descriptors.


def _bind_entity_types() -> None:
    """Bind EntityType enum values to descriptors.

    Called once at module load. Uses object.__setattr__ to mutate
    frozen dataclass instances (safe because this runs exactly once
    before any consumer reads the descriptors).
    """
    from autom8_asana.models.business.detection.types import EntityType

    _TYPE_MAP: dict[str, Any] = {
        "business": EntityType.BUSINESS,
        "unit": EntityType.UNIT,
        "contact": EntityType.CONTACT,
        "offer": EntityType.OFFER,
        "process": EntityType.PROCESS,
        "location": EntityType.LOCATION,
        "hours": EntityType.HOURS,
        "contact_holder": EntityType.CONTACT_HOLDER,
        "unit_holder": EntityType.UNIT_HOLDER,
        "location_holder": EntityType.LOCATION_HOLDER,
        "dna_holder": EntityType.DNA_HOLDER,
        "reconciliation_holder": EntityType.RECONCILIATIONS_HOLDER,
        "asset_edit_holder": EntityType.ASSET_EDIT_HOLDER,
        "videography_holder": EntityType.VIDEOGRAPHY_HOLDER,
        "offer_holder": EntityType.OFFER_HOLDER,
        "process_holder": EntityType.PROCESS_HOLDER,
        # Note: "asset_edit" intentionally has no EntityType member
    }

    for desc in ENTITY_DESCRIPTORS:
        et = _TYPE_MAP.get(desc.name)
        if et is not None:
            object.__setattr__(desc, "entity_type", et)


# --- Startup Validation ---


def _validate_registry_integrity(registry: EntityRegistry) -> None:
    """Cross-reference registry against known facade expectations.

    Called at module load time. Raises ValueError if inconsistencies
    are detected. This is the import-time validation gate that would
    have caught the RF-L21 gap.

    Checks:
    1. Warmable entities with no key_columns (warning only)
    2. Holder references valid leaf entity
    3. No duplicate pascal_names
    4. Join key targets exist
    5. Parent entity references exist
    6. Schema-Extractor-Row triad consistency:
       6a. Schema path syntax valid (ERROR)
       6b. Extractor path syntax valid (ERROR)
       6c. Row model path syntax valid (ERROR)
       6d. Schema without extractor (WARNING -- partial wiring)
       6e. Schema without row model (WARNING -- partial wiring)
       6f. Extractor without schema (ERROR -- nonsensical)
    7. Cascading field provider has model_class_path (ERROR)

    Note: Checks 6a-6c validate path syntax only (module.attr format).
    Actual import resolution is tested in the test suite to avoid circular
    imports at module load time (dataframes/__init__.py triggers config.py
    which imports entity_registry.py).
    """
    names = set(registry.all_names())

    # Check 1: Warmable entities have key_columns (warning only, not error)
    for desc in registry.warmable_entities():
        if not desc.key_columns:
            logger.warning(
                "warmable_entity_no_key_columns",
                extra={"entity": desc.name},
            )

    # Check 2: Holder references valid leaf entity
    for desc in registry.holders():
        if desc.holder_for and desc.holder_for not in names:
            raise ValueError(
                f"Holder {desc.name!r} references unknown entity {desc.holder_for!r}"
            )

    # Check 3: No duplicate pascal_names
    pascal_names: dict[str, str] = {}
    for desc in registry.all_descriptors():
        pn = desc.pascal_name
        if pn in pascal_names:
            raise ValueError(
                f"Duplicate pascal_name {pn!r}: {desc.name!r} "
                f"conflicts with {pascal_names[pn]!r}"
            )
        pascal_names[pn] = desc.name

    # Check 4: Join key targets exist
    for desc in registry.all_descriptors():
        for target, _key in desc.join_keys:
            if target not in names:
                raise ValueError(
                    f"Entity {desc.name!r} has join_key to unknown target {target!r}"
                )

    # Check 5: Parent entity references exist
    for desc in registry.all_descriptors():
        if desc.parent_entity and desc.parent_entity not in names:
            raise ValueError(
                f"Entity {desc.name!r} references unknown parent {desc.parent_entity!r}"
            )

    # IMPORTANT: Schema/extractor/row model modules must NOT import from
    # core.entity_registry, because _validate_registry_integrity() resolves
    # their paths during entity_registry.py module load. Any such import
    # would create a circular dependency.
    #
    # NOTE: Checks 6a-6c validate path SYNTAX only at import time (the module
    # part must be non-empty). Actual import resolution is deferred to test
    # time because importing dataframes/ subpackages triggers the parent
    # dataframes/__init__.py, which imports builders -> config -> entity_registry
    # (circular). Per ARCH doc section 6.4 mitigation: split into "module-load
    # checks" (syntax) and "first-use / test checks" (import resolution).

    # Check 6: Schema-Extractor-Row triad consistency
    for desc in registry.all_descriptors():
        # 6a: Schema path has valid syntax (module.attr format)
        if desc.schema_module_path:
            _module, _, _attr = desc.schema_module_path.rpartition(".")
            if not _module or not _attr:
                raise ValueError(
                    f"Entity {desc.name!r}: schema_module_path "
                    f"{desc.schema_module_path!r} is not a valid dotted path"
                )

        # 6b: Extractor path has valid syntax
        if desc.extractor_class_path:
            _module, _, _attr = desc.extractor_class_path.rpartition(".")
            if not _module or not _attr:
                raise ValueError(
                    f"Entity {desc.name!r}: extractor_class_path "
                    f"{desc.extractor_class_path!r} is not a valid dotted path"
                )

        # 6c: Row model path has valid syntax
        if desc.row_model_class_path:
            _module, _, _attr = desc.row_model_class_path.rpartition(".")
            if not _module or not _attr:
                raise ValueError(
                    f"Entity {desc.name!r}: row_model_class_path "
                    f"{desc.row_model_class_path!r} is not a valid dotted path"
                )

        # 6d: Schema without extractor (WARNING or ERROR per strict_triad_validation)
        if desc.schema_module_path and not desc.extractor_class_path:
            if registry.strict_triad_validation:
                raise ValueError(
                    f"Entity {desc.name!r}: has schema_module_path but no "
                    f"extractor_class_path (strict_triad_validation=True). "
                    f"See ADR-S4-001."
                )
            logger.warning(
                "schema_without_extractor",
                extra={
                    "entity": desc.name,
                    "schema_path": desc.schema_module_path,
                },
            )

        # 6e: Schema without row model (WARNING)
        if desc.schema_module_path and not desc.row_model_class_path:
            logger.warning(
                "schema_without_row_model",
                extra={
                    "entity": desc.name,
                    "schema_path": desc.schema_module_path,
                },
            )

        # 6f: Extractor without schema (ERROR -- nonsensical)
        if desc.extractor_class_path and not desc.schema_module_path:
            raise ValueError(
                f"Entity {desc.name!r}: has extractor_class_path but no "
                f"schema_module_path (extractor requires a schema)"
            )

    # Check 7: Cascading field provider validity
    for desc in registry.all_descriptors():
        if desc.cascading_field_provider and not desc.model_class_path:
            raise ValueError(
                f"Entity {desc.name!r}: cascading_field_provider=True but "
                f"no model_class_path to resolve the model"
            )


# --- Build the singleton registry ---
_bind_entity_types()
_REGISTRY = EntityRegistry(ENTITY_DESCRIPTORS)
_validate_registry_integrity(_REGISTRY)


def get_registry() -> EntityRegistry:
    """Get the module-level EntityRegistry singleton.

    Returns:
        The singleton EntityRegistry instance.
    """
    return _REGISTRY
