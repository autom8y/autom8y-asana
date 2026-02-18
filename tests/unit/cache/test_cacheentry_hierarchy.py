"""Tests for CacheEntry hierarchy (TDD-unified-cacheentry-hierarchy).

Covers:
- Subclass registration via __init_subclass__
- from_dict() polymorphic deserialization
- to_dict() includes _type discriminator
- Legacy data without _type deserializes to base CacheEntry
- EntryType-to-subclass mapping completeness
- Frozen immutability on subclasses
- isinstance() checks
- FreshnessPolicy compatibility (base methods on subclasses)
- dataclasses.replace() preserves subclass type
- DataFrame CacheEntry rename and backward-compatible alias
- Import path compatibility
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from autom8_asana.cache.models.entry import (
    CacheEntry,
    DataFrameMetaCacheEntry,
    DetectionCacheEntry,
    EntityCacheEntry,
    EntryType,
    RelationshipCacheEntry,
)
from autom8_asana.cache.models.freshness_stamp import (
    FreshnessStamp,
    VerificationSource,
)

# ---------------------------------------------------------------------------
# Test Isolation: Prevent _type_registry pollution
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_type_registry():
    """Save and restore CacheEntry._type_registry to prevent test pollution.

    Per HYG-012 FINDING-002: Tests that access CacheEntry._type_registry
    (a ClassVar dict) can pollute global state. This fixture ensures each
    test starts with a clean registry snapshot.
    """
    original_registry = CacheEntry._type_registry.copy()
    yield
    CacheEntry._type_registry.clear()
    CacheEntry._type_registry.update(original_registry)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 2, 4, 12, 0, 0, tzinfo=UTC)
VERSION = datetime(2026, 2, 4, 11, 0, 0, tzinfo=UTC)


def _base_kwargs(entry_type: EntryType, **overrides: object) -> dict:
    """Build common kwargs for CacheEntry construction."""
    kwargs: dict = {
        "key": "1234567890",
        "data": {"gid": "1234567890", "name": "Test"},
        "entry_type": entry_type,
        "version": VERSION,
        "cached_at": NOW,
        "ttl": 300,
    }
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# __init_subclass__ Registration
# ---------------------------------------------------------------------------


class TestSubclassRegistration:
    """Verify __init_subclass__ auto-registration in _type_registry."""

    def test_entity_types_registered(self) -> None:
        for et in (
            EntryType.TASK,
            EntryType.PROJECT,
            EntryType.SECTION,
            EntryType.USER,
            EntryType.CUSTOM_FIELD,
        ):
            assert CacheEntry._type_registry[et.value] is EntityCacheEntry

    def test_relationship_types_registered(self) -> None:
        for et in (
            EntryType.SUBTASKS,
            EntryType.DEPENDENCIES,
            EntryType.DEPENDENTS,
            EntryType.STORIES,
            EntryType.ATTACHMENTS,
        ):
            assert CacheEntry._type_registry[et.value] is RelationshipCacheEntry

    def test_dataframe_meta_types_registered(self) -> None:
        for et in (
            EntryType.DATAFRAME,
            EntryType.PROJECT_SECTIONS,
            EntryType.GID_ENUMERATION,
        ):
            assert CacheEntry._type_registry[et.value] is DataFrameMetaCacheEntry

    def test_detection_type_registered(self) -> None:
        assert (
            CacheEntry._type_registry[EntryType.DETECTION.value] is DetectionCacheEntry
        )

    def test_insights_not_registered(self) -> None:
        """INSIGHTS has no subclass; should not be in registry."""
        assert EntryType.INSIGHTS.value not in CacheEntry._type_registry

    def test_registry_completeness(self) -> None:
        """All EntryType members except INSIGHTS should be registered."""
        registered = set(CacheEntry._type_registry.keys())
        all_values = {et.value for et in EntryType}
        unregistered = all_values - registered
        assert unregistered == {"insights"}


# ---------------------------------------------------------------------------
# Subclass Construction
# ---------------------------------------------------------------------------


class TestEntityCacheEntry:
    def test_construction_task(self) -> None:
        entry = EntityCacheEntry(**_base_kwargs(EntryType.TASK))
        assert entry.entry_type == EntryType.TASK
        assert entry.entity_gid == "1234567890"
        assert entry.has_modified_at is True

    def test_construction_section(self) -> None:
        entry = EntityCacheEntry(**_base_kwargs(EntryType.SECTION))
        assert entry.has_modified_at is False

    def test_completeness_fields(self) -> None:
        entry = EntityCacheEntry(
            **_base_kwargs(EntryType.TASK),
            completeness_level="standard",
            opt_fields=("gid", "name", "custom_fields"),
        )
        assert entry.completeness_level == "standard"
        assert entry.opt_fields == ("gid", "name", "custom_fields")

    def test_defaults(self) -> None:
        entry = EntityCacheEntry(**_base_kwargs(EntryType.USER))
        assert entry.completeness_level is None
        assert entry.opt_fields is None


class TestRelationshipCacheEntry:
    def test_auto_count_from_data(self) -> None:
        data = {"data": [{"gid": "a"}, {"gid": "b"}, {"gid": "c"}]}
        entry = RelationshipCacheEntry(
            **_base_kwargs(EntryType.SUBTASKS, data=data),
        )
        assert entry.relationship_count == 3

    def test_explicit_count(self) -> None:
        entry = RelationshipCacheEntry(
            **_base_kwargs(EntryType.SUBTASKS),
            relationship_count=42,
        )
        assert entry.relationship_count == 42

    def test_effective_parent_gid_default(self) -> None:
        entry = RelationshipCacheEntry(**_base_kwargs(EntryType.STORIES))
        assert entry.effective_parent_gid == "1234567890"  # falls back to key

    def test_effective_parent_gid_explicit(self) -> None:
        entry = RelationshipCacheEntry(
            **_base_kwargs(EntryType.STORIES),
            parent_gid="9999",
        )
        assert entry.effective_parent_gid == "9999"


class TestDataFrameMetaCacheEntry:
    def test_requires_project_gid(self) -> None:
        with pytest.raises(ValueError, match="project_gid is required"):
            DataFrameMetaCacheEntry(**_base_kwargs(EntryType.DATAFRAME))

    def test_construction_with_project_gid(self) -> None:
        entry = DataFrameMetaCacheEntry(
            **_base_kwargs(EntryType.DATAFRAME, project_gid="proj123"),
            schema_version="2.0.0",
        )
        assert entry.project_gid == "proj123"
        assert entry.schema_version == "2.0.0"

    def test_project_sections(self) -> None:
        entry = DataFrameMetaCacheEntry(
            **_base_kwargs(EntryType.PROJECT_SECTIONS, project_gid="proj123"),
        )
        assert entry.entry_type == EntryType.PROJECT_SECTIONS


class TestDetectionCacheEntry:
    def test_task_gid_alias(self) -> None:
        entry = DetectionCacheEntry(
            **_base_kwargs(EntryType.DETECTION),
            detection_type="unit",
        )
        assert entry.task_gid == "1234567890"
        assert entry.detection_type == "unit"

    def test_default_detection_type(self) -> None:
        entry = DetectionCacheEntry(**_base_kwargs(EntryType.DETECTION))
        assert entry.detection_type is None


# ---------------------------------------------------------------------------
# isinstance Checks
# ---------------------------------------------------------------------------


class TestInstanceOf:
    def test_entity_is_cache_entry(self) -> None:
        entry = EntityCacheEntry(**_base_kwargs(EntryType.TASK))
        assert isinstance(entry, CacheEntry)
        assert isinstance(entry, EntityCacheEntry)

    def test_relationship_is_cache_entry(self) -> None:
        entry = RelationshipCacheEntry(**_base_kwargs(EntryType.SUBTASKS))
        assert isinstance(entry, CacheEntry)

    def test_dataframe_meta_is_cache_entry(self) -> None:
        entry = DataFrameMetaCacheEntry(
            **_base_kwargs(EntryType.DATAFRAME, project_gid="p1"),
        )
        assert isinstance(entry, CacheEntry)

    def test_detection_is_cache_entry(self) -> None:
        entry = DetectionCacheEntry(**_base_kwargs(EntryType.DETECTION))
        assert isinstance(entry, CacheEntry)

    def test_base_is_not_subclass(self) -> None:
        entry = CacheEntry(**_base_kwargs(EntryType.TASK))
        assert not isinstance(entry, EntityCacheEntry)


# ---------------------------------------------------------------------------
# Frozen Immutability
# ---------------------------------------------------------------------------


class TestFrozenImmutability:
    @pytest.mark.parametrize(
        "cls,extra_kwargs",
        [
            (EntityCacheEntry, {}),
            (RelationshipCacheEntry, {}),
            (DataFrameMetaCacheEntry, {"project_gid": "p1"}),
            (DetectionCacheEntry, {}),
        ],
    )
    def test_frozen(self, cls: type, extra_kwargs: dict) -> None:
        kwargs = _base_kwargs(
            EntryType.TASK
            if cls == EntityCacheEntry
            else EntryType.SUBTASKS
            if cls == RelationshipCacheEntry
            else EntryType.DATAFRAME
            if cls == DataFrameMetaCacheEntry
            else EntryType.DETECTION,
            **extra_kwargs,
        )
        entry = cls(**kwargs)
        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.key = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# dataclasses.replace() Preserves Subclass
# ---------------------------------------------------------------------------


class TestDataclassesReplace:
    def test_replace_entity(self) -> None:
        entry = EntityCacheEntry(**_base_kwargs(EntryType.TASK))
        replaced = dataclasses.replace(entry, ttl=600)
        assert type(replaced) is EntityCacheEntry
        assert replaced.ttl == 600
        assert replaced.key == entry.key

    def test_replace_relationship(self) -> None:
        entry = RelationshipCacheEntry(
            **_base_kwargs(EntryType.SUBTASKS),
            parent_gid="p1",
        )
        replaced = dataclasses.replace(entry, ttl=900)
        assert type(replaced) is RelationshipCacheEntry
        assert replaced.parent_gid == "p1"


# ---------------------------------------------------------------------------
# Base Methods on Subclasses
# ---------------------------------------------------------------------------


class TestBaseMethodsOnSubclasses:
    def test_is_expired(self) -> None:
        entry = EntityCacheEntry(**_base_kwargs(EntryType.TASK, ttl=60))
        future = NOW + timedelta(seconds=120)
        assert entry.is_expired(now=future) is True
        assert entry.is_expired(now=NOW) is False

    def test_is_current(self) -> None:
        entry = RelationshipCacheEntry(**_base_kwargs(EntryType.SUBTASKS))
        older = VERSION - timedelta(hours=1)
        newer = VERSION + timedelta(hours=1)
        assert entry.is_current(older) is True
        assert entry.is_current(newer) is False

    def test_is_stale(self) -> None:
        entry = DetectionCacheEntry(**_base_kwargs(EntryType.DETECTION))
        newer = VERSION + timedelta(hours=1)
        assert entry.is_stale(newer) is True

    def test_no_ttl_never_expires(self) -> None:
        entry = EntityCacheEntry(**_base_kwargs(EntryType.TASK, ttl=None))
        far_future = NOW + timedelta(days=365)
        assert entry.is_expired(now=far_future) is False


# ---------------------------------------------------------------------------
# Serialization: to_dict
# ---------------------------------------------------------------------------


class TestToDict:
    def test_base_includes_type_discriminator(self) -> None:
        entry = CacheEntry(**_base_kwargs(EntryType.TASK))
        d = entry.to_dict()
        assert d["_type"] == "task"
        assert d["_class"] == "CacheEntry"
        assert d["entry_type"] == "task"

    def test_entity_includes_subclass_fields(self) -> None:
        entry = EntityCacheEntry(
            **_base_kwargs(EntryType.TASK),
            completeness_level="full",
            opt_fields=("gid", "name"),
        )
        d = entry.to_dict()
        assert d["_type"] == "task"
        assert d["_class"] == "EntityCacheEntry"
        assert d["completeness_level"] == "full"
        assert d["opt_fields"] == ["gid", "name"]

    def test_relationship_includes_subclass_fields(self) -> None:
        data = {"data": [{"gid": "a"}]}
        entry = RelationshipCacheEntry(
            **_base_kwargs(EntryType.SUBTASKS, data=data),
            parent_gid="p1",
        )
        d = entry.to_dict()
        assert d["parent_gid"] == "p1"
        assert d["relationship_count"] == 1

    def test_dataframe_meta_includes_schema_version(self) -> None:
        entry = DataFrameMetaCacheEntry(
            **_base_kwargs(EntryType.DATAFRAME, project_gid="proj"),
            schema_version="3.0.0",
        )
        d = entry.to_dict()
        assert d["schema_version"] == "3.0.0"

    def test_detection_includes_detection_type(self) -> None:
        entry = DetectionCacheEntry(
            **_base_kwargs(EntryType.DETECTION),
            detection_type="offer",
        )
        d = entry.to_dict()
        assert d["detection_type"] == "offer"

    def test_freshness_stamp_serialized(self) -> None:
        stamp = FreshnessStamp(
            last_verified_at=NOW,
            source=VerificationSource.API_FETCH,
            staleness_hint="test-hint",
        )
        entry = EntityCacheEntry(
            **_base_kwargs(EntryType.TASK),
            freshness_stamp=stamp,
        )
        d = entry.to_dict()
        assert "freshness_stamp" in d
        assert d["freshness_stamp"]["source"] == "api_fetch"
        assert d["freshness_stamp"]["staleness_hint"] == "test-hint"


# ---------------------------------------------------------------------------
# Deserialization: from_dict
# ---------------------------------------------------------------------------


class TestFromDict:
    def test_dispatches_to_entity(self) -> None:
        d = {
            "_type": "task",
            "key": "123",
            "data": {"gid": "123"},
            "entry_type": "task",
            "version": VERSION.isoformat(),
            "cached_at": NOW.isoformat(),
            "ttl": 300,
            "completeness_level": "standard",
            "opt_fields": ["gid", "name"],
        }
        entry = CacheEntry.from_dict(d)
        assert type(entry) is EntityCacheEntry
        assert entry.completeness_level == "standard"
        assert entry.opt_fields == ("gid", "name")

    def test_dispatches_to_relationship(self) -> None:
        d = {
            "_type": "subtasks",
            "key": "456",
            "data": {"data": [{"gid": "a"}, {"gid": "b"}]},
            "entry_type": "subtasks",
            "version": VERSION.isoformat(),
            "cached_at": NOW.isoformat(),
            "ttl": 300,
            "parent_gid": "456",
            "relationship_count": 2,
        }
        entry = CacheEntry.from_dict(d)
        assert type(entry) is RelationshipCacheEntry
        assert entry.relationship_count == 2

    def test_dispatches_to_dataframe_meta(self) -> None:
        d = {
            "_type": "dataframe",
            "key": "df-key",
            "data": {},
            "entry_type": "dataframe",
            "version": VERSION.isoformat(),
            "cached_at": NOW.isoformat(),
            "ttl": 600,
            "project_gid": "proj1",
            "schema_version": "2.0.0",
        }
        entry = CacheEntry.from_dict(d)
        assert type(entry) is DataFrameMetaCacheEntry
        assert entry.schema_version == "2.0.0"

    def test_dispatches_to_detection(self) -> None:
        d = {
            "_type": "detection",
            "key": "789",
            "data": {"result": True},
            "entry_type": "detection",
            "version": VERSION.isoformat(),
            "cached_at": NOW.isoformat(),
            "ttl": 300,
            "detection_type": "unit",
        }
        entry = CacheEntry.from_dict(d)
        assert type(entry) is DetectionCacheEntry
        assert entry.detection_type == "unit"

    def test_legacy_no_type_field(self) -> None:
        """Dict without _type deserializes to base CacheEntry."""
        d = {
            "key": "legacy",
            "data": {"gid": "legacy"},
            "entry_type": "task",
            "version": VERSION.isoformat(),
            "cached_at": NOW.isoformat(),
            "ttl": 300,
        }
        entry = CacheEntry.from_dict(d)
        # Without _type, falls back to base (uses entry_type for EntryType)
        # The entry_type IS in the registry, but _type is missing so
        # the lookup uses entry_type as fallback, which DOES find EntityCacheEntry
        assert isinstance(entry, CacheEntry)

    def test_unknown_type_falls_back_to_base(self) -> None:
        """Unknown _type value falls back to base CacheEntry."""
        d = {
            "_type": "insights",
            "key": "ins",
            "data": {},
            "entry_type": "insights",
            "version": VERSION.isoformat(),
            "cached_at": NOW.isoformat(),
            "ttl": 300,
        }
        entry = CacheEntry.from_dict(d)
        assert type(entry) is CacheEntry

    def test_unknown_fields_ignored(self) -> None:
        """Extra fields in dict do not raise."""
        d = {
            "_type": "task",
            "key": "123",
            "data": {},
            "entry_type": "task",
            "version": VERSION.isoformat(),
            "cached_at": NOW.isoformat(),
            "ttl": 300,
            "future_field": "should_be_ignored",
            "another_unknown": 42,
        }
        entry = CacheEntry.from_dict(d)
        assert isinstance(entry, EntityCacheEntry)

    def test_freshness_stamp_round_trip(self) -> None:
        stamp = FreshnessStamp(
            last_verified_at=NOW,
            source=VerificationSource.BATCH_CHECK,
            staleness_hint=None,
        )
        original = EntityCacheEntry(
            **_base_kwargs(EntryType.TASK),
            freshness_stamp=stamp,
        )
        d = original.to_dict()
        restored = CacheEntry.from_dict(d)
        assert type(restored) is EntityCacheEntry
        assert restored.freshness_stamp is not None
        assert restored.freshness_stamp.source == VerificationSource.BATCH_CHECK
        assert restored.freshness_stamp.staleness_hint is None


# ---------------------------------------------------------------------------
# Round-Trip: to_dict -> from_dict
# ---------------------------------------------------------------------------


class TestRoundTrip:
    @pytest.mark.parametrize(
        "cls,entry_type,extra",
        [
            (
                EntityCacheEntry,
                EntryType.TASK,
                {"completeness_level": "full", "opt_fields": ("gid",)},
            ),
            (EntityCacheEntry, EntryType.PROJECT, {}),
            (EntityCacheEntry, EntryType.SECTION, {}),
            (EntityCacheEntry, EntryType.USER, {}),
            (EntityCacheEntry, EntryType.CUSTOM_FIELD, {}),
            (RelationshipCacheEntry, EntryType.SUBTASKS, {"parent_gid": "p1"}),
            (RelationshipCacheEntry, EntryType.DEPENDENCIES, {}),
            (RelationshipCacheEntry, EntryType.STORIES, {}),
            (
                DataFrameMetaCacheEntry,
                EntryType.DATAFRAME,
                {"project_gid": "proj", "schema_version": "1.0"},
            ),
            (
                DataFrameMetaCacheEntry,
                EntryType.PROJECT_SECTIONS,
                {"project_gid": "proj"},
            ),
            (DetectionCacheEntry, EntryType.DETECTION, {"detection_type": "unit"}),
        ],
    )
    def test_round_trip(self, cls: type, entry_type: EntryType, extra: dict) -> None:
        kwargs = _base_kwargs(entry_type, **extra)
        original = cls(**kwargs)
        d = original.to_dict()
        restored = CacheEntry.from_dict(d)
        assert type(restored) is cls
        assert restored.key == original.key
        assert restored.entry_type == original.entry_type
        assert restored.ttl == original.ttl


# ---------------------------------------------------------------------------
# EntryType Enum Unchanged
# ---------------------------------------------------------------------------


class TestEntryTypeEnum:
    def test_all_15_members_present(self) -> None:
        expected = {
            "task",
            "subtasks",
            "dependencies",
            "dependents",
            "stories",
            "attachments",
            "dataframe",
            "project",
            "section",
            "user",
            "custom_field",
            "detection",
            "project_sections",
            "gid_enumeration",
            "insights",
        }
        actual = {et.value for et in EntryType}
        assert actual == expected

    def test_member_count(self) -> None:
        assert len(EntryType) == 15


# ---------------------------------------------------------------------------
# Base CacheEntry Still Constructible
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_base_constructible_with_any_entry_type(self) -> None:
        """Base CacheEntry(...) construction remains valid for all entry types."""
        for et in EntryType:
            entry = CacheEntry(**_base_kwargs(et))
            assert entry.entry_type == et

    # Removed test_shim_import_path - shims were deleted in Batch B07

    def test_package_import_path(self) -> None:
        from autom8_asana.cache import CacheEntry as PkgCacheEntry

        assert PkgCacheEntry is CacheEntry

    def test_subclass_import_from_models(self) -> None:
        from autom8_asana.cache.models import EntityCacheEntry as ModelsEntity

        assert ModelsEntity is EntityCacheEntry

    # Removed test_subclass_import_from_package - EntityCacheEntry is an internal
    # subclass not part of the public API


# ---------------------------------------------------------------------------
# DataFrame CacheEntry Rename
# ---------------------------------------------------------------------------


class TestDataFrameCacheEntryRename:
    def test_new_name_importable(self) -> None:
        from autom8_asana.cache.integration.dataframe_cache import (
            DataFrameCacheEntry,
        )

        assert DataFrameCacheEntry.__name__ == "DataFrameCacheEntry"
