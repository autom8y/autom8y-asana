"""Tests for Entity Knowledge Registry.

Per TDD-ENTITY-REGISTRY-001 test strategy:
- Unit tests for EntityDescriptor
- Unit tests for EntityRegistry
- Integration tests for backward-compatible facades
- Validation tests for integrity checks
"""

from __future__ import annotations

import pytest

from autom8_asana.core.entity_registry import (
    ENTITY_DESCRIPTORS,
    EntityCategory,
    EntityDescriptor,
    EntityRegistry,
    _resolve_dotted_path,
    _validate_registry_integrity,
    get_registry,
)

# =============================================================================
# EntityDescriptor Unit Tests
# =============================================================================


class TestEntityDescriptor:
    """Unit tests for EntityDescriptor dataclass."""

    def test_descriptor_is_frozen(self) -> None:
        """Cannot mutate after creation."""
        desc = EntityDescriptor(name="test", pascal_name="Test", display_name="Test")
        with pytest.raises(AttributeError):
            desc.name = "modified"  # type: ignore[misc]

    def test_effective_schema_key_default(self) -> None:
        """Returns pascal_name when schema_key is None."""
        desc = EntityDescriptor(
            name="test", pascal_name="TestEntity", display_name="Test"
        )
        assert desc.effective_schema_key == "TestEntity"

    def test_effective_schema_key_override(self) -> None:
        """Returns schema_key when explicitly set."""
        desc = EntityDescriptor(
            name="test",
            pascal_name="TestEntity",
            display_name="Test",
            schema_key="CustomKey",
        )
        assert desc.effective_schema_key == "CustomKey"

    def test_is_holder_true_for_holders(self) -> None:
        """Category HOLDER returns True."""
        desc = EntityDescriptor(
            name="test_holder",
            pascal_name="TestHolder",
            display_name="Test",
            category=EntityCategory.HOLDER,
        )
        assert desc.is_holder is True

    def test_is_holder_false_for_leaves(self) -> None:
        """Category LEAF returns False."""
        desc = EntityDescriptor(name="test", pascal_name="Test", display_name="Test")
        assert desc.is_holder is False

    def test_is_holder_false_for_root(self) -> None:
        """Category ROOT returns False."""
        desc = EntityDescriptor(
            name="test",
            pascal_name="Test",
            display_name="Test",
            category=EntityCategory.ROOT,
        )
        assert desc.is_holder is False

    def test_has_project_true(self) -> None:
        """True when primary_project_gid is set."""
        desc = EntityDescriptor(
            name="test",
            pascal_name="Test",
            display_name="Test",
            primary_project_gid="123",
        )
        assert desc.has_project is True

    def test_has_project_false(self) -> None:
        """False when primary_project_gid is None."""
        desc = EntityDescriptor(name="test", pascal_name="Test", display_name="Test")
        assert desc.has_project is False

    def test_get_join_key_found(self) -> None:
        """Returns join key for known target."""
        desc = EntityDescriptor(
            name="test",
            pascal_name="Test",
            display_name="Test",
            join_keys=(("business", "office_phone"), ("unit", "vertical")),
        )
        assert desc.get_join_key("business") == "office_phone"
        assert desc.get_join_key("unit") == "vertical"

    def test_get_join_key_not_found(self) -> None:
        """Returns None for unknown target."""
        desc = EntityDescriptor(
            name="test",
            pascal_name="Test",
            display_name="Test",
            join_keys=(("business", "office_phone"),),
        )
        assert desc.get_join_key("unknown") is None

    def test_get_model_class_none_when_unset(self) -> None:
        """Returns None when model_class_path is None."""
        desc = EntityDescriptor(name="test", pascal_name="Test", display_name="Test")
        assert desc.get_model_class() is None

    def test_get_model_class_lazy_import(self) -> None:
        """Resolves model class from dotted path."""
        # Use a known importable class
        desc = EntityDescriptor(
            name="test",
            pascal_name="Test",
            display_name="Test",
            model_class_path="autom8_asana.core.entity_registry.EntityRegistry",
        )
        cls = desc.get_model_class()
        assert cls is EntityRegistry

    def test_default_values(self) -> None:
        """Verify all default field values."""
        desc = EntityDescriptor(name="test", pascal_name="Test", display_name="Test")
        assert desc.entity_type is None
        assert desc.category == EntityCategory.LEAF
        assert desc.primary_project_gid is None
        assert desc.model_class_path is None
        assert desc.parent_entity is None
        assert desc.holder_for is None
        assert desc.holder_attr is None
        assert desc.name_pattern is None
        assert desc.emoji is None
        assert desc.schema_key is None
        assert desc.default_ttl_seconds == 300
        assert desc.warmable is False
        assert desc.warm_priority == 99
        assert desc.aliases == ()
        assert desc.join_keys == ()
        assert desc.key_columns == ()
        assert desc.explicit_name_mappings == ()
        assert desc.custom_field_resolver_class_path is None


# =============================================================================
# EntityRegistry Unit Tests
# =============================================================================


class TestEntityRegistry:
    """Unit tests for EntityRegistry class."""

    @pytest.fixture
    def sample_descriptors(self) -> tuple[EntityDescriptor, ...]:
        """Create a minimal set of test descriptors."""
        return (
            EntityDescriptor(
                name="alpha",
                pascal_name="Alpha",
                display_name="Alpha Entity",
                primary_project_gid="gid_alpha",
                default_ttl_seconds=600,
                warmable=True,
                warm_priority=2,
                aliases=("a",),
                key_columns=("col_a",),
                join_keys=(("beta", "shared_key"),),
            ),
            EntityDescriptor(
                name="beta",
                pascal_name="Beta",
                display_name="Beta Entity",
                primary_project_gid="gid_beta",
                default_ttl_seconds=120,
                warmable=True,
                warm_priority=1,
                key_columns=("col_b",),
            ),
            EntityDescriptor(
                name="gamma_holder",
                pascal_name="GammaHolder",
                display_name="Gamma",
                category=EntityCategory.HOLDER,
                primary_project_gid="gid_gamma",
                parent_entity="alpha",
                holder_for="beta",
                holder_attr="_gamma_holder",
            ),
        )

    @pytest.fixture
    def registry(
        self, sample_descriptors: tuple[EntityDescriptor, ...]
    ) -> EntityRegistry:
        """Create a test registry."""
        return EntityRegistry(sample_descriptors)

    def test_get_by_name_returns_descriptor(self, registry: EntityRegistry) -> None:
        """Primary lookup returns correct descriptor."""
        desc = registry.get("alpha")
        assert desc is not None
        assert desc.name == "alpha"
        assert desc.display_name == "Alpha Entity"

    def test_get_by_name_returns_none_for_unknown(
        self, registry: EntityRegistry
    ) -> None:
        """Unknown name returns None."""
        assert registry.get("nonexistent") is None

    def test_require_returns_descriptor(self, registry: EntityRegistry) -> None:
        """require() returns descriptor for valid name."""
        desc = registry.require("alpha")
        assert desc.name == "alpha"

    def test_require_raises_for_unknown(self, registry: EntityRegistry) -> None:
        """require() raises KeyError with helpful message."""
        with pytest.raises(KeyError, match="Unknown entity type"):
            registry.require("nonexistent")

    def test_get_by_gid_returns_descriptor(self, registry: EntityRegistry) -> None:
        """GID lookup returns correct descriptor."""
        desc = registry.get_by_gid("gid_alpha")
        assert desc is not None
        assert desc.name == "alpha"

    def test_get_by_gid_returns_none_for_unknown(
        self, registry: EntityRegistry
    ) -> None:
        """Unknown GID returns None."""
        assert registry.get_by_gid("unknown_gid") is None

    def test_get_by_type_returns_descriptor(self) -> None:
        """EntityType lookup returns correct descriptor."""
        # Use the real registry since it has entity_type bound
        reg = get_registry()
        from autom8_asana.core.types import EntityType

        desc = reg.get_by_type(EntityType.UNIT)
        assert desc is not None
        assert desc.name == "unit"

    def test_get_by_type_returns_none_for_unknown(
        self, registry: EntityRegistry
    ) -> None:
        """Unknown EntityType returns None (test registry has no types)."""
        assert registry.get_by_type("fake_type") is None

    def test_all_names_preserves_order(self, registry: EntityRegistry) -> None:
        """all_names() matches definition order."""
        names = registry.all_names()
        assert names == ["alpha", "beta", "gamma_holder"]

    def test_all_descriptors_preserves_order(
        self,
        registry: EntityRegistry,
        sample_descriptors: tuple[EntityDescriptor, ...],
    ) -> None:
        """all_descriptors() returns the original tuple."""
        assert registry.all_descriptors() == sample_descriptors

    def test_warmable_sorted_by_priority(self, registry: EntityRegistry) -> None:
        """warmable_entities() returns ascending priority."""
        warmable = registry.warmable_entities()
        assert len(warmable) == 2
        assert warmable[0].name == "beta"  # priority=1
        assert warmable[1].name == "alpha"  # priority=2

    def test_dataframe_entities(self, registry: EntityRegistry) -> None:
        """dataframe_entities() returns warmable entity names."""
        entities = registry.dataframe_entities()
        assert set(entities) == {"alpha", "beta"}

    def test_holders(self, registry: EntityRegistry) -> None:
        """holders() returns only holder entities."""
        holders = registry.holders()
        assert len(holders) == 1
        assert holders[0].name == "gamma_holder"

    def test_get_join_key_both_directions(self, registry: EntityRegistry) -> None:
        """Join key lookup works source->target and reverse."""
        # Forward: alpha has join_key to beta
        assert registry.get_join_key("alpha", "beta") == "shared_key"
        # Reverse: beta -> alpha (checks alpha's join_keys)
        assert registry.get_join_key("beta", "alpha") == "shared_key"
        # Unknown pair
        assert registry.get_join_key("alpha", "gamma_holder") is None

    def test_get_entity_ttl_returns_correct_value(
        self, registry: EntityRegistry
    ) -> None:
        """TTL lookup matches descriptor."""
        assert registry.get_entity_ttl("alpha") == 600
        assert registry.get_entity_ttl("beta") == 120

    def test_get_entity_ttl_case_insensitive(self, registry: EntityRegistry) -> None:
        """TTL lookup is case-insensitive."""
        assert registry.get_entity_ttl("Alpha") == 600

    def test_get_entity_ttl_fallback(self, registry: EntityRegistry) -> None:
        """Unknown entity returns default TTL."""
        assert registry.get_entity_ttl("unknown") == 300
        assert registry.get_entity_ttl("unknown", default=999) == 999

    def test_get_aliases(self, registry: EntityRegistry) -> None:
        """get_aliases() returns alias tuple."""
        assert registry.get_aliases("alpha") == ("a",)
        assert registry.get_aliases("beta") == ()
        assert registry.get_aliases("unknown") == ()

    def test_get_key_columns(self, registry: EntityRegistry) -> None:
        """get_key_columns() returns key column tuple."""
        assert registry.get_key_columns("alpha") == ("col_a",)
        assert registry.get_key_columns("gamma_holder") == ()
        assert registry.get_key_columns("unknown") == ()

    def test_duplicate_name_raises(self) -> None:
        """Constructor rejects duplicate names."""
        descriptors = (
            EntityDescriptor(name="dup", pascal_name="Dup1", display_name="A"),
            EntityDescriptor(name="dup", pascal_name="Dup2", display_name="B"),
        )
        with pytest.raises(ValueError, match="Duplicate entity name"):
            EntityRegistry(descriptors)

    def test_duplicate_gid_raises(self) -> None:
        """Constructor rejects duplicate project GIDs."""
        descriptors = (
            EntityDescriptor(
                name="a",
                pascal_name="A",
                display_name="A",
                primary_project_gid="same_gid",
            ),
            EntityDescriptor(
                name="b",
                pascal_name="B",
                display_name="B",
                primary_project_gid="same_gid",
            ),
        )
        with pytest.raises(ValueError, match="Duplicate project GID"):
            EntityRegistry(descriptors)

    def test_duplicate_entity_type_raises(self) -> None:
        """Constructor rejects duplicate EntityType values."""
        from autom8_asana.core.types import EntityType

        descriptors = (
            EntityDescriptor(
                name="a",
                pascal_name="A",
                display_name="A",
                entity_type=EntityType.UNIT,
            ),
            EntityDescriptor(
                name="b",
                pascal_name="B",
                display_name="B",
                entity_type=EntityType.UNIT,
            ),
        )
        with pytest.raises(ValueError, match="Duplicate EntityType"):
            EntityRegistry(descriptors)


# =============================================================================
# Integration Tests: Global Registry
# =============================================================================


class TestGlobalRegistry:
    """Tests for the module-level singleton registry."""

    def test_singleton_returns_same_instance(self) -> None:
        """get_registry() returns the same instance."""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_entity_types_bound(self) -> None:
        """EntityType enum values are bound to descriptors."""
        from autom8_asana.core.types import EntityType

        registry = get_registry()
        unit = registry.get("unit")
        assert unit is not None
        assert unit.entity_type == EntityType.UNIT

    def test_asset_edit_has_entity_type(self) -> None:
        """asset_edit has EntityType.ASSET_EDIT after binding."""
        from autom8_asana.core.types import EntityType

        registry = get_registry()
        desc = registry.get("asset_edit")
        assert desc is not None
        assert desc.entity_type == EntityType.ASSET_EDIT

    def test_all_entity_types_have_descriptors(self) -> None:
        """Every EntityType enum member (except UNKNOWN) has a registry entry."""
        from autom8_asana.core.types import EntityType

        registry = get_registry()
        for et in EntityType:
            if et == EntityType.UNKNOWN:
                continue
            desc = registry.get_by_type(et)
            assert desc is not None, f"EntityType.{et.name} has no registry entry"

    def test_descriptor_count(self) -> None:
        """Registry has expected number of descriptors."""
        registry = get_registry()
        assert len(registry.all_descriptors()) == 27

    def test_warmable_count_and_order(self) -> None:
        """Warmable entities match expected count and priority order."""
        registry = get_registry()
        warmable = registry.warmable_entities()
        names = [d.name for d in warmable]
        assert names == [
            "business",
            "unit",
            "offer",
            "contact",
            "asset_edit",
            "asset_edit_holder",
            "process_sales",
            "process_outreach",
            "process_onboarding",
            "process_implementation",
            "process_month1",
            "process_retention",
            "process_reactivation",
            "process_account_error",
            "process_expansion",
        ]


# =============================================================================
# Integration Tests: Backward-Compatible Facades
# =============================================================================


class TestFacadeBackwardCompatibility:
    """Tests ensuring facade outputs match original hardcoded values."""

    def test_entity_types_matches_legacy(self) -> None:
        """ENTITY_TYPES facade produces same values as old hardcoded list."""
        from autom8_asana.core.entity_types import ENTITY_TYPES

        expected = [
            "business",
            "unit",
            "offer",
            "contact",
            "asset_edit",
            "process_sales",
            "process_outreach",
            "process_onboarding",
            "process_implementation",
            "process_month1",
            "process_retention",
            "process_reactivation",
            "process_account_error",
            "process_expansion",
        ]
        assert expected == ENTITY_TYPES

    def test_entity_types_with_derivatives_matches(self) -> None:
        """ENTITY_TYPES_WITH_DERIVATIVES facade matches."""
        from autom8_asana.core.entity_types import ENTITY_TYPES_WITH_DERIVATIVES

        expected = [
            "business",
            "unit",
            "offer",
            "contact",
            "asset_edit",
            "asset_edit_holder",
            "process_sales",
            "process_outreach",
            "process_onboarding",
            "process_implementation",
            "process_month1",
            "process_retention",
            "process_reactivation",
            "process_account_error",
            "process_expansion",
        ]
        assert expected == ENTITY_TYPES_WITH_DERIVATIVES

    def test_default_entity_ttls_matches(self) -> None:
        """DEFAULT_ENTITY_TTLS facade produces same dict."""
        from autom8_asana.config import DEFAULT_ENTITY_TTLS

        expected = {
            "business": 3600,
            "contact": 900,
            "unit": 900,
            "offer": 180,
            "process": 60,
            "location": 3600,
            "hours": 3600,
        }
        assert expected == DEFAULT_ENTITY_TTLS

    def test_entity_aliases_matches(self) -> None:
        """ENTITY_ALIASES facade produces same dict."""
        from autom8_asana.services.resolver import ENTITY_ALIASES

        expected = {
            "unit": ["business_unit"],
            "offer": ["business_offer"],
            "business": ["office"],
            "contact": [],
            "asset_edit": ["process"],
            "asset_edit_holder": [],
            "process_sales": [],
            "process_outreach": [],
            "process_onboarding": [],
            "process_implementation": [],
            "process_month1": [],
            "process_retention": [],
            "process_reactivation": [],
            "process_account_error": [],
            "process_expansion": [],
        }
        assert expected == ENTITY_ALIASES

    def test_default_key_columns_matches(self) -> None:
        """DEFAULT_KEY_COLUMNS facade produces same dict."""
        from autom8_asana.services.universal_strategy import DEFAULT_KEY_COLUMNS

        expected = {
            "unit": ["office_phone", "vertical"],
            "business": ["office_phone"],
            "offer": ["office_phone", "vertical", "offer_id"],
            "contact": ["office_phone", "contact_phone", "contact_email"],
            "asset_edit": [
                "office_phone",
                "vertical",
                "asset_id",
                "offer_id",
            ],
            "asset_edit_holder": ["office_phone"],
            "process_sales": ["office_phone", "vertical"],
            "process_outreach": ["office_phone", "vertical"],
            "process_onboarding": ["office_phone", "vertical"],
            "process_implementation": ["office_phone", "vertical"],
            "process_month1": ["office_phone", "vertical"],
            "process_retention": ["office_phone", "vertical"],
            "process_reactivation": ["office_phone", "vertical"],
            "process_account_error": ["office_phone", "vertical"],
            "process_expansion": ["office_phone", "vertical"],
        }
        assert expected == DEFAULT_KEY_COLUMNS


# =============================================================================
# Validation Tests
# =============================================================================


class TestIntegrityValidation:
    """Tests for import-time integrity validation."""

    def test_integrity_check_catches_bad_holder_ref(self) -> None:
        """Validation rejects holder referencing unknown entity."""
        from autom8_asana.core.entity_registry import _validate_registry_integrity

        descriptors = (
            EntityDescriptor(
                name="bad_holder",
                pascal_name="BadHolder",
                display_name="Bad",
                category=EntityCategory.HOLDER,
                holder_for="nonexistent",
            ),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(ValueError, match="references unknown entity"):
            _validate_registry_integrity(registry)

    def test_integrity_check_catches_bad_join_target(self) -> None:
        """Validation rejects join key to unknown entity."""
        from autom8_asana.core.entity_registry import _validate_registry_integrity

        descriptors = (
            EntityDescriptor(
                name="source",
                pascal_name="Source",
                display_name="Source",
                join_keys=(("nonexistent_target", "some_key"),),
            ),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(ValueError, match="join_key to unknown target"):
            _validate_registry_integrity(registry)

    def test_integrity_check_catches_bad_parent_ref(self) -> None:
        """Validation rejects unknown parent_entity."""
        from autom8_asana.core.entity_registry import _validate_registry_integrity

        descriptors = (
            EntityDescriptor(
                name="child",
                pascal_name="Child",
                display_name="Child",
                parent_entity="nonexistent_parent",
            ),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(ValueError, match="references unknown parent"):
            _validate_registry_integrity(registry)

    def test_integrity_check_catches_duplicate_pascal(self) -> None:
        """Validation rejects duplicate pascal_names."""
        from autom8_asana.core.entity_registry import _validate_registry_integrity

        descriptors = (
            EntityDescriptor(name="alpha", pascal_name="Same", display_name="A"),
            EntityDescriptor(name="beta", pascal_name="Same", display_name="B"),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(ValueError, match="Duplicate pascal_name"):
            _validate_registry_integrity(registry)

    def test_global_registry_passes_integrity(self) -> None:
        """The production registry passes all integrity checks (implicit)."""
        # If we got here, the module loaded successfully, which means
        # _validate_registry_integrity() passed. Verify the registry is usable.
        registry = get_registry()
        assert len(registry.all_names()) > 0


# =============================================================================
# ENTITY_DESCRIPTORS Data Tests
# =============================================================================


class TestEntityDescriptorData:
    """Tests for the completeness and correctness of ENTITY_DESCRIPTORS."""

    def test_all_descriptors_are_frozen(self) -> None:
        """Every descriptor in ENTITY_DESCRIPTORS is frozen."""
        for desc in ENTITY_DESCRIPTORS:
            with pytest.raises(AttributeError):
                desc.name = "modified"  # type: ignore[misc]

    def test_entity_categories_correct(self) -> None:
        """Key entities have expected categories."""
        registry = get_registry()
        assert registry.require("business").category == EntityCategory.ROOT
        assert registry.require("unit").category == EntityCategory.COMPOSITE
        assert registry.require("contact").category == EntityCategory.LEAF
        assert registry.require("contact_holder").category == EntityCategory.HOLDER

    def test_holder_relationships(self) -> None:
        """All holders reference valid leaf entities."""
        registry = get_registry()
        for holder in registry.holders():
            if holder.holder_for is not None:
                leaf = registry.get(holder.holder_for)
                assert leaf is not None, (
                    f"Holder {holder.name} references unknown leaf {holder.holder_for}"
                )

    def test_pascal_names_are_unique(self) -> None:
        """All pascal_names are unique across descriptors."""
        pascal_names = [d.pascal_name for d in ENTITY_DESCRIPTORS]
        assert len(pascal_names) == len(set(pascal_names))

    def test_project_gids_are_unique_where_set(self) -> None:
        """All non-None project GIDs are unique."""
        gids = [
            d.primary_project_gid
            for d in ENTITY_DESCRIPTORS
            if d.primary_project_gid is not None
        ]
        assert len(gids) == len(set(gids))


# =============================================================================
# DataFrame Layer Field Tests (WS1-S1)
# =============================================================================


class TestDataFrameLayerFields:
    """Tests for the 4 new DataFrame layer fields on EntityDescriptor."""

    def test_new_fields_exist_with_correct_defaults(self) -> None:
        """New fields default to None/False when not explicitly set."""
        desc = EntityDescriptor(name="test", pascal_name="Test", display_name="Test")
        assert desc.schema_module_path is None
        assert desc.extractor_class_path is None
        assert desc.row_model_class_path is None
        assert desc.cascading_field_provider is False
        assert desc.custom_field_resolver_class_path is None

    def test_new_fields_are_settable(self) -> None:
        """New fields accept explicit values at construction time."""
        desc = EntityDescriptor(
            name="test",
            pascal_name="Test",
            display_name="Test",
            schema_module_path="some.module.SCHEMA",
            extractor_class_path="some.module.Extractor",
            row_model_class_path="some.module.Row",
            cascading_field_provider=True,
        )
        assert desc.schema_module_path == "some.module.SCHEMA"
        assert desc.extractor_class_path == "some.module.Extractor"
        assert desc.row_model_class_path == "some.module.Row"
        assert desc.cascading_field_provider is True

    def test_new_fields_are_frozen(self) -> None:
        """New fields cannot be mutated after creation (frozen dataclass)."""
        desc = EntityDescriptor(
            name="test",
            pascal_name="Test",
            display_name="Test",
            schema_module_path="some.module.SCHEMA",
        )
        with pytest.raises(AttributeError):
            desc.schema_module_path = "other.path"  # type: ignore[misc]
        with pytest.raises(AttributeError):
            desc.cascading_field_provider = True  # type: ignore[misc]


class TestDataFrameLayerPopulation:
    """Tests that schema-bearing entities have correct field values."""

    def test_business_descriptor_fields(self) -> None:
        """Business has full triad (schema, extractor, row) and cascading=True."""
        desc = get_registry().require("business")
        assert desc.schema_module_path == (
            "autom8_asana.dataframes.schemas.business.BUSINESS_SCHEMA"
        )
        assert desc.extractor_class_path == (
            "autom8_asana.dataframes.extractors.business.BusinessExtractor"
        )
        assert desc.row_model_class_path == (
            "autom8_asana.dataframes.models.task_row.BusinessRow"
        )
        assert desc.cascading_field_provider is True
        assert desc.custom_field_resolver_class_path == (
            "autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"
        )

    def test_unit_descriptor_fields(self) -> None:
        """Unit has full triad (schema, extractor, row) and cascading=True."""
        desc = get_registry().require("unit")
        assert desc.schema_module_path == (
            "autom8_asana.dataframes.schemas.unit.UNIT_SCHEMA"
        )
        assert desc.extractor_class_path == (
            "autom8_asana.dataframes.extractors.unit.UnitExtractor"
        )
        assert desc.row_model_class_path == (
            "autom8_asana.dataframes.models.task_row.UnitRow"
        )
        assert desc.cascading_field_provider is True
        assert desc.custom_field_resolver_class_path == (
            "autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"
        )

    def test_contact_descriptor_fields(self) -> None:
        """Contact has full triad, no cascading."""
        desc = get_registry().require("contact")
        assert desc.schema_module_path == (
            "autom8_asana.dataframes.schemas.contact.CONTACT_SCHEMA"
        )
        assert desc.extractor_class_path == (
            "autom8_asana.dataframes.extractors.contact.ContactExtractor"
        )
        assert desc.row_model_class_path == (
            "autom8_asana.dataframes.models.task_row.ContactRow"
        )
        assert desc.cascading_field_provider is False

    def test_offer_descriptor_fields(self) -> None:
        """Offer has full triad (schema, extractor, row)."""
        desc = get_registry().require("offer")
        assert desc.schema_module_path == (
            "autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA"
        )
        assert desc.extractor_class_path == (
            "autom8_asana.dataframes.extractors.offer.OfferExtractor"
        )
        assert desc.row_model_class_path == (
            "autom8_asana.dataframes.models.task_row.OfferRow"
        )
        assert desc.cascading_field_provider is False
        assert desc.custom_field_resolver_class_path == (
            "autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"
        )

    def test_asset_edit_descriptor_fields(self) -> None:
        """AssetEdit has full triad (schema, extractor, row)."""
        desc = get_registry().require("asset_edit")
        assert desc.schema_module_path == (
            "autom8_asana.dataframes.schemas.asset_edit.ASSET_EDIT_SCHEMA"
        )
        assert desc.extractor_class_path == (
            "autom8_asana.dataframes.extractors.asset_edit.AssetEditExtractor"
        )
        assert desc.row_model_class_path == (
            "autom8_asana.dataframes.models.task_row.AssetEditRow"
        )

    def test_asset_edit_holder_descriptor_fields(self) -> None:
        """AssetEditHolder has full triad (schema, extractor, row)."""
        desc = get_registry().require("asset_edit_holder")
        assert desc.schema_module_path == (
            "autom8_asana.dataframes.schemas.asset_edit_holder.ASSET_EDIT_HOLDER_SCHEMA"
        )
        assert desc.extractor_class_path == (
            "autom8_asana.dataframes.extractors.asset_edit_holder.AssetEditHolderExtractor"
        )
        assert desc.row_model_class_path == (
            "autom8_asana.dataframes.models.task_row.AssetEditHolderRow"
        )

    def test_non_schema_entities_have_none_defaults(self) -> None:
        """Entities without schemas keep None/False defaults."""
        non_schema_entities = [
            "process",
            "location",
            "hours",
            "contact_holder",
            "unit_holder",
            "location_holder",
            "dna_holder",
            "reconciliation_holder",
            "videography_holder",
            "offer_holder",
            "process_holder",
        ]
        registry = get_registry()
        for name in non_schema_entities:
            desc = registry.require(name)
            assert desc.schema_module_path is None, f"{name} should have no schema"
            assert desc.extractor_class_path is None, f"{name} should have no extractor"
            assert desc.row_model_class_path is None, f"{name} should have no row model"
            assert desc.cascading_field_provider is False, (
                f"{name} should not be a cascading provider"
            )

    def test_cascading_field_provider_only_business_and_unit(self) -> None:
        """Only business and unit have cascading_field_provider=True."""
        registry = get_registry()
        providers = [
            d.name for d in registry.all_descriptors() if d.cascading_field_provider
        ]
        assert sorted(providers) == ["business", "unit"]


# =============================================================================
# _resolve_dotted_path Tests (WS1-S1)
# =============================================================================


class TestResolveDottedPath:
    """Tests for the _resolve_dotted_path() utility function."""

    def test_resolves_class(self) -> None:
        """Resolves a dotted path to a class."""
        cls = _resolve_dotted_path("autom8_asana.core.entity_registry.EntityRegistry")
        assert cls is EntityRegistry

    def test_resolves_constant(self) -> None:
        """Resolves a dotted path to a module-level constant."""
        result = _resolve_dotted_path(
            "autom8_asana.core.entity_registry.ENTITY_DESCRIPTORS"
        )
        assert result is ENTITY_DESCRIPTORS

    def test_resolves_enum(self) -> None:
        """Resolves a dotted path to an enum class."""
        result = _resolve_dotted_path(
            "autom8_asana.core.entity_registry.EntityCategory"
        )
        assert result is EntityCategory

    def test_raises_import_error_for_bad_module(self) -> None:
        """Raises ImportError when module does not exist."""
        with pytest.raises(ImportError):
            _resolve_dotted_path("nonexistent.module.SomeClass")

    def test_raises_attribute_error_for_bad_attr(self) -> None:
        """Raises AttributeError when attribute does not exist on module."""
        with pytest.raises(AttributeError):
            _resolve_dotted_path("autom8_asana.core.entity_registry.NonexistentClass")

    def test_raises_import_error_for_no_module(self) -> None:
        """Raises ImportError for path with no module part."""
        with pytest.raises(ImportError, match="Invalid dotted path"):
            _resolve_dotted_path("JustAName")

    def test_get_model_class_delegates_to_resolve(self) -> None:
        """get_model_class() uses _resolve_dotted_path internally."""
        desc = EntityDescriptor(
            name="test",
            pascal_name="Test",
            display_name="Test",
            model_class_path="autom8_asana.core.entity_registry.EntityRegistry",
        )
        cls = desc.get_model_class()
        assert cls is EntityRegistry


# =============================================================================
# DataFrame Path Resolution Tests (WS1-S1)
# =============================================================================


class TestDataFramePathResolution:
    """Verify that all populated dotted paths actually resolve to real objects.

    These tests perform the actual import that validation defers at module load
    time (to avoid circular imports). This ensures the paths are not just
    syntactically valid but point to real schema/extractor/row objects.
    """

    def test_all_schema_paths_resolve(self) -> None:
        """Every populated schema_module_path resolves to a real object."""
        for desc in get_registry().all_descriptors():
            if desc.schema_module_path:
                result = _resolve_dotted_path(desc.schema_module_path)
                assert result is not None, f"{desc.name}: schema path did not resolve"

    def test_all_extractor_paths_resolve(self) -> None:
        """Every populated extractor_class_path resolves to a class."""
        for desc in get_registry().all_descriptors():
            if desc.extractor_class_path:
                cls = _resolve_dotted_path(desc.extractor_class_path)
                assert isinstance(cls, type), (
                    f"{desc.name}: extractor path did not resolve to a class"
                )

    def test_all_row_model_paths_resolve(self) -> None:
        """Every populated row_model_class_path resolves to a class."""
        for desc in get_registry().all_descriptors():
            if desc.row_model_class_path:
                cls = _resolve_dotted_path(desc.row_model_class_path)
                assert isinstance(cls, type), (
                    f"{desc.name}: row model path did not resolve to a class"
                )


# =============================================================================
# Triad Validation Tests (WS1-S1)
# =============================================================================


class TestTriadValidation:
    """Tests for validation checks 6a-6f and 7."""

    def test_check_6a_bad_schema_path_syntax(self) -> None:
        """Check 6a: Invalid schema_module_path syntax raises ValueError."""
        descriptors = (
            EntityDescriptor(
                name="bad_schema",
                pascal_name="BadSchema",
                display_name="Bad",
                schema_module_path="NoModulePart",
            ),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(
            ValueError, match="schema_module_path.*not a valid dotted path"
        ):
            _validate_registry_integrity(registry)

    def test_check_6b_bad_extractor_path_syntax(self) -> None:
        """Check 6b: Invalid extractor_class_path syntax raises ValueError."""
        descriptors = (
            EntityDescriptor(
                name="bad_extractor",
                pascal_name="BadExtractor",
                display_name="Bad",
                schema_module_path="some.module.SCHEMA",
                extractor_class_path="NoModulePart",
            ),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(
            ValueError, match="extractor_class_path.*not a valid dotted path"
        ):
            _validate_registry_integrity(registry)

    def test_check_6c_bad_row_model_path_syntax(self) -> None:
        """Check 6c: Invalid row_model_class_path syntax raises ValueError."""
        descriptors = (
            EntityDescriptor(
                name="bad_row",
                pascal_name="BadRow",
                display_name="Bad",
                schema_module_path="some.module.SCHEMA",
                row_model_class_path="NoModulePart",
            ),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(
            ValueError, match="row_model_class_path.*not a valid dotted path"
        ):
            _validate_registry_integrity(registry)

    def test_check_6d_schema_without_extractor_does_not_raise(self) -> None:
        """Check 6d: Schema with no extractor logs warning but does not raise."""
        descriptors = (
            EntityDescriptor(
                name="partial",
                pascal_name="Partial",
                display_name="Partial",
                schema_module_path="some.module.SCHEMA",
            ),
        )
        registry = EntityRegistry(descriptors)
        # Validation should complete without error (warning only via logger)
        _validate_registry_integrity(registry)

    def test_check_6e_schema_without_row_model_warns(self) -> None:
        """Check 6e: Schema with no row_model logs warning."""
        descriptors = (
            EntityDescriptor(
                name="partial",
                pascal_name="Partial",
                display_name="Partial",
                schema_module_path="some.module.SCHEMA",
                extractor_class_path="some.module.Extractor",
            ),
        )
        registry = EntityRegistry(descriptors)
        # Should complete without error (warning only for 6e)
        _validate_registry_integrity(registry)

    def test_check_6f_extractor_without_schema_raises(self) -> None:
        """Check 6f: Extractor without schema is an error (nonsensical)."""
        descriptors = (
            EntityDescriptor(
                name="bad_combo",
                pascal_name="BadCombo",
                display_name="Bad",
                extractor_class_path="some.module.Extractor",
            ),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(
            ValueError, match="has extractor_class_path but no schema_module_path"
        ):
            _validate_registry_integrity(registry)

    def test_check_7_cascading_provider_without_model_raises(self) -> None:
        """Check 7: cascading_field_provider=True without model_class_path."""
        descriptors = (
            EntityDescriptor(
                name="bad_provider",
                pascal_name="BadProvider",
                display_name="Bad",
                cascading_field_provider=True,
            ),
        )
        registry = EntityRegistry(descriptors)
        with pytest.raises(
            ValueError, match="cascading_field_provider=True but no model_class_path"
        ):
            _validate_registry_integrity(registry)

    def test_check_7_cascading_provider_with_model_passes(self) -> None:
        """Check 7: cascading_field_provider=True with model_class_path is valid."""
        descriptors = (
            EntityDescriptor(
                name="good_provider",
                pascal_name="GoodProvider",
                display_name="Good",
                model_class_path="autom8_asana.core.entity_registry.EntityRegistry",
                cascading_field_provider=True,
            ),
        )
        registry = EntityRegistry(descriptors)
        _validate_registry_integrity(registry)

    def test_valid_triad_passes_all_checks(self) -> None:
        """A descriptor with valid schema+extractor+row passes all checks."""
        descriptors = (
            EntityDescriptor(
                name="complete",
                pascal_name="Complete",
                display_name="Complete",
                schema_module_path="some.module.SCHEMA",
                extractor_class_path="some.module.Extractor",
                row_model_class_path="some.module.Row",
            ),
        )
        registry = EntityRegistry(descriptors)
        _validate_registry_integrity(registry)

    def test_global_registry_passes_all_new_checks(self) -> None:
        """The production registry passes all triad/cascading checks."""
        # If module loaded, validation already passed at import time.
        # Re-run explicitly to confirm no regression.
        _validate_registry_integrity(EntityRegistry(ENTITY_DESCRIPTORS))


# =============================================================================
# Strict Triad Validation Tests (WS1-S4a Task 1)
# =============================================================================


class TestStrictTriadValidation:
    """Tests for configurable severity of check 6d via strict_triad_validation."""

    def test_strict_false_is_default(self) -> None:
        """strict_triad_validation defaults to False."""
        registry = EntityRegistry(())
        assert registry.strict_triad_validation is False

    def test_strict_false_schema_without_extractor_does_not_raise(self) -> None:
        """With strict=False, check 6d emits warning but does not raise."""
        descriptors = (
            EntityDescriptor(
                name="partial",
                pascal_name="Partial",
                display_name="Partial",
                schema_module_path="some.module.SCHEMA",
            ),
        )
        registry = EntityRegistry(descriptors, strict_triad_validation=False)
        # Should complete without error (warning only)
        _validate_registry_integrity(registry)

    def test_strict_true_schema_without_extractor_raises(self) -> None:
        """With strict=True, check 6d raises ValueError."""
        descriptors = (
            EntityDescriptor(
                name="partial",
                pascal_name="Partial",
                display_name="Partial",
                schema_module_path="some.module.SCHEMA",
            ),
        )
        registry = EntityRegistry(descriptors, strict_triad_validation=True)
        with pytest.raises(ValueError, match="strict_triad_validation=True"):
            _validate_registry_integrity(registry)

    def test_strict_true_complete_triad_passes(self) -> None:
        """With strict=True, a complete triad (schema+extractor+row) passes."""
        descriptors = (
            EntityDescriptor(
                name="complete",
                pascal_name="Complete",
                display_name="Complete",
                schema_module_path="some.module.SCHEMA",
                extractor_class_path="some.module.Extractor",
                row_model_class_path="some.module.Row",
            ),
        )
        registry = EntityRegistry(descriptors, strict_triad_validation=True)
        _validate_registry_integrity(registry)

    def test_strict_true_no_schema_entities_pass(self) -> None:
        """With strict=True, entities without schemas are unaffected."""
        descriptors = (
            EntityDescriptor(
                name="no_schema",
                pascal_name="NoSchema",
                display_name="No Schema",
            ),
        )
        registry = EntityRegistry(descriptors, strict_triad_validation=True)
        _validate_registry_integrity(registry)

    def test_strict_true_error_message_includes_entity_name(self) -> None:
        """The strict error message includes the offending entity name."""
        descriptors = (
            EntityDescriptor(
                name="my_entity",
                pascal_name="MyEntity",
                display_name="My Entity",
                schema_module_path="some.module.SCHEMA",
            ),
        )
        registry = EntityRegistry(descriptors, strict_triad_validation=True)
        with pytest.raises(ValueError, match="my_entity"):
            _validate_registry_integrity(registry)

    def test_production_registry_uses_strict_true(self) -> None:
        """The production registry uses strict=True (all triads complete)."""
        registry = get_registry()
        assert registry.strict_triad_validation is True


# =============================================================================
# Import-Resolution Coverage Tests (WS1-S4a Task 2)
# =============================================================================


class TestImportResolutionCoverage:
    """Verify that _resolve_dotted_path() succeeds for ALL populated paths.

    Extends the existing TestDataFramePathResolution tests by using
    parametrized tests that explicitly name each entity, providing
    clear failure diagnostics. Covers schema_module_path,
    extractor_class_path, and row_model_class_path for every entity
    that declares them.
    """

    @staticmethod
    def _entities_with_path(attr_name: str) -> list[tuple[str, str]]:
        """Collect (entity_name, path) pairs for all descriptors with the given attr set."""
        registry = get_registry()
        return [
            (desc.name, getattr(desc, attr_name))
            for desc in registry.all_descriptors()
            if getattr(desc, attr_name) is not None
        ]

    @pytest.mark.parametrize(
        "entity_name,path",
        _entities_with_path.__func__("schema_module_path"),
        ids=lambda x: x if isinstance(x, str) and "." not in x else "",
    )
    def test_schema_module_path_resolves(self, entity_name: str, path: str) -> None:
        """schema_module_path for {entity_name} resolves to a real object."""
        result = _resolve_dotted_path(path)
        assert result is not None, (
            f"Entity {entity_name!r}: schema_module_path {path!r} resolved to None"
        )

    @pytest.mark.parametrize(
        "entity_name,path",
        _entities_with_path.__func__("extractor_class_path"),
        ids=lambda x: x if isinstance(x, str) and "." not in x else "",
    )
    def test_extractor_class_path_resolves(self, entity_name: str, path: str) -> None:
        """extractor_class_path for {entity_name} resolves to a class."""
        cls = _resolve_dotted_path(path)
        assert isinstance(cls, type), (
            f"Entity {entity_name!r}: extractor_class_path {path!r} "
            f"did not resolve to a class, got {type(cls)}"
        )

    @pytest.mark.parametrize(
        "entity_name,path",
        _entities_with_path.__func__("row_model_class_path"),
        ids=lambda x: x if isinstance(x, str) and "." not in x else "",
    )
    def test_row_model_class_path_resolves(self, entity_name: str, path: str) -> None:
        """row_model_class_path for {entity_name} resolves to a class."""
        cls = _resolve_dotted_path(path)
        assert isinstance(cls, type), (
            f"Entity {entity_name!r}: row_model_class_path {path!r} "
            f"did not resolve to a class, got {type(cls)}"
        )

    def test_all_paths_covered(self) -> None:
        """Ensure this test class covers every populated path across all descriptors.

        Guards against new paths being added without corresponding test coverage.
        """
        schema_paths = self._entities_with_path("schema_module_path")
        extractor_paths = self._entities_with_path("extractor_class_path")
        row_model_paths = self._entities_with_path("row_model_class_path")

        # Known counts from current descriptors:
        # 6 entities with schema_module_path (business, unit, contact, offer,
        #   asset_edit, asset_edit_holder)
        # 6 entities with extractor_class_path (business, unit, contact, offer,
        #   asset_edit, asset_edit_holder)
        # 6 entities with row_model_class_path (business, unit, contact, offer,
        #   asset_edit, asset_edit_holder)
        assert len(schema_paths) >= 6, (
            f"Expected at least 6 schema paths, got {len(schema_paths)}"
        )
        assert len(extractor_paths) >= 6, (
            f"Expected at least 6 extractor paths, got {len(extractor_paths)}"
        )
        assert len(row_model_paths) >= 6, (
            f"Expected at least 6 row model paths, got {len(row_model_paths)}"
        )


# =============================================================================
# Schema Column Count Smoke Tests (WS1-S4a Task 3)
# =============================================================================


# Known baseline column counts per entity schema. If a schema changes columns,
# this test will fail, signaling that the change is intentional (update the
# count) or accidental (investigate).
EXPECTED_SCHEMA_COLUMN_COUNTS: list[tuple[str, int]] = [
    ("business", 18),  # 13 base + 5 business-specific
    ("unit", 24),  # 13 base + 11 unit-specific
    ("contact", 26),  # 13 base + 13 contact-specific
    ("offer", 24),  # 13 base + 11 offer-specific
    ("asset_edit", 34),  # 13 base + 21 asset_edit-specific
    ("asset_edit_holder", 14),  # 13 base + 1 asset_edit_holder-specific
    ("process_sales", 16),  # 13 base + 3 process-specific
    ("process_outreach", 16),  # 13 base + 3 process-specific
    ("process_onboarding", 16),  # 13 base + 3 process-specific
    ("process_implementation", 16),  # 13 base + 3 process-specific
    ("process_month1", 16),  # 13 base + 3 process-specific
    ("process_retention", 16),  # 13 base + 3 process-specific
    ("process_reactivation", 16),  # 13 base + 3 process-specific
    ("process_account_error", 16),  # 13 base + 3 process-specific
    ("process_expansion", 16),  # 13 base + 3 process-specific
]


class TestSchemaColumnCountSmoke:
    """Smoke test: verify each entity schema has the expected number of columns.

    Catches accidental column removal or duplication. The expected counts
    are baseline values from the current schema definitions. If a legitimate
    schema change occurs, update EXPECTED_SCHEMA_COLUMN_COUNTS above.
    """

    @pytest.mark.parametrize(
        "entity_name,expected_count",
        EXPECTED_SCHEMA_COLUMN_COUNTS,
        ids=[name for name, _ in EXPECTED_SCHEMA_COLUMN_COUNTS],
    )
    def test_schema_column_count(self, entity_name: str, expected_count: int) -> None:
        """Schema for {entity_name} has {expected_count} columns."""
        desc = get_registry().require(entity_name)
        assert desc.schema_module_path is not None, (
            f"Entity {entity_name!r} has no schema_module_path"
        )
        schema = _resolve_dotted_path(desc.schema_module_path)
        actual_count = len(schema.columns)
        assert actual_count == expected_count, (
            f"Entity {entity_name!r}: expected {expected_count} columns, "
            f"got {actual_count}. If this is intentional, update "
            f"EXPECTED_SCHEMA_COLUMN_COUNTS in test_entity_registry.py."
        )

    def test_all_schema_entities_have_baselines(self) -> None:
        """Every entity with a schema has a baseline entry in EXPECTED_SCHEMA_COLUMN_COUNTS."""
        schema_entities = {
            desc.name
            for desc in get_registry().all_descriptors()
            if desc.schema_module_path
        }
        baseline_entities = {name for name, _ in EXPECTED_SCHEMA_COLUMN_COUNTS}
        missing = schema_entities - baseline_entities
        assert not missing, (
            f"Entities with schemas missing from EXPECTED_SCHEMA_COLUMN_COUNTS: {missing}. "
            f"Add baseline column counts for these entities."
        )


# =============================================================================
# Entity Type Binding Regression Tests (schema-topology-triage Sprint 2)
# =============================================================================


class TestEntityTypeBindingRegression:
    """Regression tests ensuring all warmable+resolvable entities have entity_type bound.

    Prevents recurrence of the gap where asset_edit was warmable and resolvable
    but had no EntityType enum member, causing entity_type-dispatching code to
    silently fall through.
    """

    def test_asset_edit_descriptor_has_entity_type_after_binding(self) -> None:
        """After registry init, asset_edit descriptor has EntityType.ASSET_EDIT."""
        from autom8_asana.core.types import EntityType

        registry = get_registry()
        desc = registry.get("asset_edit")
        assert desc is not None, "asset_edit descriptor not found in registry"
        assert desc.entity_type == EntityType.ASSET_EDIT, (
            f"Expected asset_edit.entity_type == EntityType.ASSET_EDIT, "
            f"got {desc.entity_type!r}"
        )

    def test_asset_edit_resolvable_via_get_by_type(self) -> None:
        """EntityRegistry.get_by_type(EntityType.ASSET_EDIT) returns asset_edit descriptor."""
        from autom8_asana.core.types import EntityType

        registry = get_registry()
        desc = registry.get_by_type(EntityType.ASSET_EDIT)
        assert desc is not None, (
            "get_by_type(EntityType.ASSET_EDIT) returned None -- "
            "binding or _by_type index is broken"
        )
        assert desc.name == "asset_edit"

    # Pipeline process entities (process_sales, process_outreach, etc.) are
    # intentionally warmable without individual EntityType enum members.
    # They share the conceptual "Process" entity type but are registered as
    # 9 separate entities to work within the 1-entity-1-project warming
    # infrastructure. See ADR-pipeline-stage-aggregation.
    _PIPELINE_PROCESS_NAMES = frozenset({
        "process_sales",
        "process_outreach",
        "process_onboarding",
        "process_implementation",
        "process_month1",
        "process_retention",
        "process_reactivation",
        "process_account_error",
        "process_expansion",
    })

    def test_all_warmable_entities_have_entity_type(self) -> None:
        """Every warmable entity has a non-None entity_type after binding.

        Guards against future entities being added as warmable without
        a corresponding EntityType enum member and _TYPE_MAP entry.
        Pipeline process entities are excluded (see ADR-pipeline-stage-aggregation).
        """
        registry = get_registry()
        for desc in registry.warmable_entities():
            if desc.name in self._PIPELINE_PROCESS_NAMES:
                continue
            assert desc.entity_type is not None, (
                f"Warmable entity {desc.name!r} has entity_type=None. "
                f"Add an EntityType enum member and _TYPE_MAP entry for it."
            )

    def test_all_resolvable_entities_have_entity_type(self) -> None:
        """Every entity with a primary_project_gid has a non-None entity_type.

        Entities with projects are resolvable via Tier 1 detection and should
        participate in entity_type-dispatching code paths.
        Pipeline process entities are excluded (see ADR-pipeline-stage-aggregation).
        """
        registry = get_registry()
        for desc in registry.all_descriptors():
            if desc.name in self._PIPELINE_PROCESS_NAMES:
                continue
            if desc.primary_project_gid is not None:
                assert desc.entity_type is not None, (
                    f"Entity {desc.name!r} has primary_project_gid "
                    f"{desc.primary_project_gid!r} but entity_type=None. "
                    f"Add an EntityType enum member and _TYPE_MAP entry for it."
                )


# =============================================================================
# Warm-Priority Cascade Ordering Invariant (ADR-cascade-contract-policy)
# =============================================================================


class TestWarmPriorityCascadeInvariant:
    """Validate that warm_priority ordering respects the cascade dependency graph.

    Per ADR-cascade-contract-policy: cascade source entities must warm before
    cascade consumers.  If this invariant is violated, cascade fields will be
    null at extraction time, reproducing SCAR-005/006 conditions.
    """

    # Maps each cascade-dependent entity to {cascade_field_name: source_entity_name}.
    # Derived from ADR-cascade-contract-policy "Affected Entities" table.
    _CASCADE_DEPS: dict[str, dict[str, str]] = {
        "unit": {"Office Phone": "business"},
        "offer": {"Office Phone": "business", "Vertical": "unit"},
        "contact": {"Office Phone": "business"},
        "asset_edit": {"Office Phone": "business", "Vertical": "unit"},
        "asset_edit_holder": {"Office Phone": "business"},
    }

    def test_cascade_source_has_lower_warm_priority(self) -> None:
        """For every cascade-dependent key column, the source entity warms first.

        Checks that the cascade source entity has a strictly lower
        warm_priority number than the consumer entity.
        """
        registry = get_registry()

        for consumer_name, deps in self._CASCADE_DEPS.items():
            consumer = registry.get(consumer_name)
            assert consumer is not None, f"Entity {consumer_name!r} not in registry"
            assert consumer.warmable, (
                f"Entity {consumer_name!r} has cascade deps but is not warmable"
            )

            for cascade_field, source_name in deps.items():
                source = registry.get(source_name)
                assert source is not None, (
                    f"Cascade source {source_name!r} for "
                    f"{consumer_name}.{cascade_field} not in registry"
                )
                assert source.warmable, (
                    f"Cascade source {source_name!r} for "
                    f"{consumer_name}.{cascade_field} is not warmable"
                )
                assert source.warm_priority < consumer.warm_priority, (
                    f"Cascade ordering violated: {source_name!r} "
                    f"(priority={source.warm_priority}) must warm before "
                    f"{consumer_name!r} (priority={consumer.warm_priority}) "
                    f"for cascade field {cascade_field!r}"
                )

    def test_business_is_first_warmable(self) -> None:
        """Business (the root cascade origin) has the lowest warm_priority."""
        registry = get_registry()
        warmable = registry.warmable_entities()
        assert len(warmable) > 0
        assert warmable[0].name == "business"
        assert warmable[0].warm_priority == 1
