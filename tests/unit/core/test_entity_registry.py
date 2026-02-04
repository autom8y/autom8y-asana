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
    get_registry,
)


# =============================================================================
# EntityDescriptor Unit Tests
# =============================================================================


class TestEntityDescriptor:
    """Unit tests for EntityDescriptor dataclass."""

    def test_descriptor_is_frozen(self) -> None:
        """Cannot mutate after creation."""
        desc = EntityDescriptor(
            name="test", pascal_name="Test", display_name="Test"
        )
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
        desc = EntityDescriptor(
            name="test", pascal_name="Test", display_name="Test"
        )
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
        desc = EntityDescriptor(
            name="test", pascal_name="Test", display_name="Test"
        )
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
        desc = EntityDescriptor(
            name="test", pascal_name="Test", display_name="Test"
        )
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
        desc = EntityDescriptor(
            name="test", pascal_name="Test", display_name="Test"
        )
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

    def test_get_by_name_returns_descriptor(
        self, registry: EntityRegistry
    ) -> None:
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

    def test_require_returns_descriptor(
        self, registry: EntityRegistry
    ) -> None:
        """require() returns descriptor for valid name."""
        desc = registry.require("alpha")
        assert desc.name == "alpha"

    def test_require_raises_for_unknown(
        self, registry: EntityRegistry
    ) -> None:
        """require() raises KeyError with helpful message."""
        with pytest.raises(KeyError, match="Unknown entity type"):
            registry.require("nonexistent")

    def test_get_by_gid_returns_descriptor(
        self, registry: EntityRegistry
    ) -> None:
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
        from autom8_asana.models.business.detection.types import EntityType

        desc = reg.get_by_type(EntityType.UNIT)
        assert desc is not None
        assert desc.name == "unit"

    def test_get_by_type_returns_none_for_unknown(
        self, registry: EntityRegistry
    ) -> None:
        """Unknown EntityType returns None (test registry has no types)."""
        assert registry.get_by_type("fake_type") is None

    def test_all_names_preserves_order(
        self, registry: EntityRegistry
    ) -> None:
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

    def test_warmable_sorted_by_priority(
        self, registry: EntityRegistry
    ) -> None:
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

    def test_get_join_key_both_directions(
        self, registry: EntityRegistry
    ) -> None:
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

    def test_get_entity_ttl_case_insensitive(
        self, registry: EntityRegistry
    ) -> None:
        """TTL lookup is case-insensitive."""
        assert registry.get_entity_ttl("Alpha") == 600

    def test_get_entity_ttl_fallback(
        self, registry: EntityRegistry
    ) -> None:
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
        from autom8_asana.models.business.detection.types import EntityType

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
        from autom8_asana.models.business.detection.types import EntityType

        registry = get_registry()
        unit = registry.get("unit")
        assert unit is not None
        assert unit.entity_type == EntityType.UNIT

    def test_asset_edit_has_no_entity_type(self) -> None:
        """asset_edit intentionally has no EntityType member."""
        registry = get_registry()
        desc = registry.get("asset_edit")
        assert desc is not None
        assert desc.entity_type is None

    def test_all_entity_types_have_descriptors(self) -> None:
        """Every EntityType enum member (except UNKNOWN) has a registry entry."""
        from autom8_asana.models.business.detection.types import EntityType

        registry = get_registry()
        for et in EntityType:
            if et == EntityType.UNKNOWN:
                continue
            desc = registry.get_by_type(et)
            assert desc is not None, (
                f"EntityType.{et.name} has no registry entry"
            )

    def test_descriptor_count(self) -> None:
        """Registry has expected number of descriptors."""
        registry = get_registry()
        assert len(registry.all_descriptors()) == 17

    def test_warmable_count_and_order(self) -> None:
        """Warmable entities match expected count and priority order."""
        registry = get_registry()
        warmable = registry.warmable_entities()
        names = [d.name for d in warmable]
        assert names == [
            "unit",
            "business",
            "offer",
            "contact",
            "asset_edit",
            "asset_edit_holder",
        ]


# =============================================================================
# Integration Tests: Backward-Compatible Facades
# =============================================================================


class TestFacadeBackwardCompatibility:
    """Tests ensuring facade outputs match original hardcoded values."""

    def test_entity_types_matches_legacy(self) -> None:
        """ENTITY_TYPES facade produces same values as old hardcoded list."""
        from autom8_asana.core.entity_types import ENTITY_TYPES

        expected = ["unit", "business", "offer", "contact", "asset_edit"]
        assert ENTITY_TYPES == expected

    def test_entity_types_with_derivatives_matches(self) -> None:
        """ENTITY_TYPES_WITH_DERIVATIVES facade matches."""
        from autom8_asana.core.entity_types import ENTITY_TYPES_WITH_DERIVATIVES

        expected = [
            "unit",
            "business",
            "offer",
            "contact",
            "asset_edit",
            "asset_edit_holder",
        ]
        assert ENTITY_TYPES_WITH_DERIVATIVES == expected

    def test_default_entity_ttls_matches(self) -> None:
        """DEFAULT_ENTITY_TTLS facade produces same dict."""
        from autom8_asana.config import DEFAULT_ENTITY_TTLS

        expected = {
            "business": 3600,
            "contact": 900,
            "unit": 900,
            "offer": 180,
            "process": 60,
            "address": 3600,
            "hours": 3600,
        }
        assert DEFAULT_ENTITY_TTLS == expected

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
        }
        assert ENTITY_ALIASES == expected

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
        }
        assert DEFAULT_KEY_COLUMNS == expected


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
            EntityDescriptor(
                name="alpha", pascal_name="Same", display_name="A"
            ),
            EntityDescriptor(
                name="beta", pascal_name="Same", display_name="B"
            ),
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
                    f"Holder {holder.name} references "
                    f"unknown leaf {holder.holder_for}"
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
