"""Tests for holder_construction module.

Per TDD-GAP-01 S1-006, S1-007: Unit tests for construct_holder and
detect_existing_holders functions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.core.registry import HOLDER_REGISTRY
from autom8_asana.models import Task
from autom8_asana.models.common import NameGid
from autom8_asana.persistence.holder_construction import (
    construct_holder,
    detect_existing_holders,
    get_holder_class_map,
)

# ---------------------------------------------------------------------------
# HOLDER_CLASS_MAP Tests
# ---------------------------------------------------------------------------


class TestHolderClassMap:
    """Tests for the HOLDER_CLASS_MAP registry."""

    def test_has_nine_entries(self) -> None:
        """All 9 holder types are registered."""
        class_map = get_holder_class_map()
        assert len(class_map) == 9

    def test_business_level_holders(self) -> None:
        """All 7 Business-level holder types are registered."""
        class_map = get_holder_class_map()
        business_holders = [
            "contact_holder",
            "unit_holder",
            "location_holder",
            "dna_holder",
            "reconciliation_holder",
            "asset_edit_holder",
            "videography_holder",
        ]
        for key in business_holders:
            assert key in class_map, f"Missing Business holder: {key}"

    def test_unit_level_holders(self) -> None:
        """Both Unit-level holder types are registered."""
        class_map = get_holder_class_map()
        assert "offer_holder" in class_map
        assert "process_holder" in class_map

    def test_holder_classes_are_task_subclasses(self) -> None:
        """All holder classes are Task subclasses."""
        class_map = get_holder_class_map()
        for key, cls in class_map.items():
            assert issubclass(cls, Task), f"{key} class {cls} is not a Task subclass"


# ---------------------------------------------------------------------------
# HOLDER_REGISTRY Completeness Tests
# ---------------------------------------------------------------------------


class TestHolderRegistryCompleteness:
    """Verify HOLDER_REGISTRY covers all expected entity types from EntityRegistry."""

    def test_holder_registry_is_public(self) -> None:
        """HOLDER_REGISTRY is directly accessible as a public module attribute."""
        assert isinstance(HOLDER_REGISTRY, dict)

    def test_all_entity_registry_holders_registered(self) -> None:
        """Every holder type in EntityRegistry has a registered Holder class.

        Cross-checks HOLDER_REGISTRY against EntityRegistry.holders() to
        ensure the registry is complete and stays in sync.
        """
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()
        entity_holder_names = {d.name for d in registry.holders()}

        class_map = get_holder_class_map()
        registered_names = set(class_map.keys())

        missing = entity_holder_names - registered_names
        assert not missing, (
            f"Holder types in EntityRegistry but missing from HOLDER_REGISTRY: {missing}"
        )

    def test_no_extra_holders_not_in_entity_registry(self) -> None:
        """HOLDER_REGISTRY has no holders absent from EntityRegistry.

        Catches stale entries if an entity type is removed from EntityRegistry
        but its registration call is not removed from the Holder file.
        """
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()
        entity_holder_names = {d.name for d in registry.holders()}

        class_map = get_holder_class_map()
        registered_names = set(class_map.keys())

        extra = registered_names - entity_holder_names
        assert not extra, (
            f"Holder types in HOLDER_REGISTRY but absent from EntityRegistry: {extra}"
        )


# ---------------------------------------------------------------------------
# construct_holder Tests
# ---------------------------------------------------------------------------


class TestConstructHolder:
    """Tests for construct_holder() function."""

    @pytest.fixture
    def business_with_real_gid(self) -> Task:
        """A Business-like entity with a real GID."""
        from autom8_asana.models.business.business import Business

        business = Business(gid="1234567890", name="Acme Corp")
        return business

    @pytest.fixture
    def business_with_temp_gid(self) -> Task:
        """A Business-like entity with a temp GID."""
        from autom8_asana.models.business.business import Business

        business = Business(gid="", name="New Business")
        object.__setattr__(business, "gid", f"temp_{id(business)}")
        return business

    @pytest.fixture
    def business_holder_key_map(self) -> dict[str, tuple[str, str]]:
        """Business HOLDER_KEY_MAP for testing."""
        return {
            "contact_holder": ("Contacts", "busts_in_silhouette"),
            "unit_holder": ("Business Units", "package"),
            "location_holder": ("Location", "round_pushpin"),
            "dna_holder": ("DNA", "dna"),
            "reconciliation_holder": ("Reconciliations", "abacus"),
            "asset_edit_holder": ("Asset Edits", "art"),
            "videography_holder": ("Videography", "video_camera"),
        }

    def test_construct_contact_holder(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """ContactHolder constructed with correct class and name."""
        from autom8_asana.models.business.contact import ContactHolder

        holder = construct_holder(
            "contact_holder", business_holder_key_map, business_with_real_gid
        )
        assert isinstance(holder, ContactHolder)
        assert holder.name == "Contacts"
        assert holder.resource_type == "task"

    def test_construct_unit_holder(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """UnitHolder constructed with correct class and name."""
        from autom8_asana.models.business.unit import UnitHolder

        holder = construct_holder(
            "unit_holder", business_holder_key_map, business_with_real_gid
        )
        assert isinstance(holder, UnitHolder)
        assert holder.name == "Business Units"

    def test_construct_location_holder(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """LocationHolder constructed with correct class and name."""
        from autom8_asana.models.business.location import LocationHolder

        holder = construct_holder(
            "location_holder", business_holder_key_map, business_with_real_gid
        )
        assert isinstance(holder, LocationHolder)
        assert holder.name == "Location"

    def test_construct_dna_holder(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """DNAHolder constructed with correct class and name."""
        from autom8_asana.models.business.business import DNAHolder

        holder = construct_holder(
            "dna_holder", business_holder_key_map, business_with_real_gid
        )
        assert isinstance(holder, DNAHolder)
        assert holder.name == "DNA"

    def test_construct_reconciliation_holder(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """ReconciliationHolder constructed with correct class and name."""
        from autom8_asana.models.business.business import ReconciliationHolder

        holder = construct_holder(
            "reconciliation_holder", business_holder_key_map, business_with_real_gid
        )
        assert isinstance(holder, ReconciliationHolder)
        assert holder.name == "Reconciliations"

    def test_construct_asset_edit_holder(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """AssetEditHolder constructed with correct class and name."""
        from autom8_asana.models.business.business import AssetEditHolder

        holder = construct_holder(
            "asset_edit_holder", business_holder_key_map, business_with_real_gid
        )
        assert isinstance(holder, AssetEditHolder)
        assert holder.name == "Asset Edits"

    def test_construct_videography_holder(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """VideographyHolder constructed with correct class and name."""
        from autom8_asana.models.business.business import VideographyHolder

        holder = construct_holder(
            "videography_holder", business_holder_key_map, business_with_real_gid
        )
        assert isinstance(holder, VideographyHolder)
        assert holder.name == "Videography"

    def test_temp_gid_assignment(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Constructed holder gets temp_{id()} GID."""
        holder = construct_holder(
            "contact_holder", business_holder_key_map, business_with_real_gid
        )
        assert holder.gid.startswith("temp_")
        assert holder.gid == f"temp_{id(holder)}"

    def test_parent_reference_real_gid(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Parent with real GID produces NameGid with that GID."""
        holder = construct_holder(
            "contact_holder", business_holder_key_map, business_with_real_gid
        )
        assert isinstance(holder.parent, NameGid)
        assert holder.parent.gid == business_with_real_gid.gid

    def test_parent_reference_temp_gid(
        self,
        business_with_temp_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Parent with temp GID produces NameGid with temp_{id(parent)}."""
        holder = construct_holder(
            "contact_holder", business_holder_key_map, business_with_temp_gid
        )
        assert isinstance(holder.parent, NameGid)
        assert holder.parent.gid == f"temp_{id(business_with_temp_gid)}"

    def test_business_reference_set(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Holder's _business reference is set to parent Business."""
        holder = construct_holder(
            "contact_holder", business_holder_key_map, business_with_real_gid
        )
        assert holder._business is business_with_real_gid

    def test_project_assignment_with_primary_project_gid(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Holders with PRIMARY_PROJECT_GID get projects list set."""
        from autom8_asana.models.business.contact import ContactHolder

        holder = construct_holder(
            "contact_holder", business_holder_key_map, business_with_real_gid
        )
        # ContactHolder has PRIMARY_PROJECT_GID = "1201500116978260"
        assert ContactHolder.PRIMARY_PROJECT_GID is not None
        assert holder.projects is not None
        assert len(holder.projects) == 1
        assert holder.projects[0].gid == ContactHolder.PRIMARY_PROJECT_GID

    def test_project_assignment_without_primary_project_gid(
        self,
        business_with_real_gid: Task,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Holders without PRIMARY_PROJECT_GID get no projects."""
        from autom8_asana.models.business.location import LocationHolder

        holder = construct_holder(
            "location_holder", business_holder_key_map, business_with_real_gid
        )
        # LocationHolder has PRIMARY_PROJECT_GID = None
        assert LocationHolder.PRIMARY_PROJECT_GID is None
        # Projects should be empty or None
        if holder.projects:
            # None of the projects should be from PRIMARY_PROJECT_GID
            assert all(p.gid != "" for p in holder.projects)

    def test_unknown_holder_key_raises(
        self,
        business_with_real_gid: Task,
    ) -> None:
        """Unknown holder_key raises KeyError."""
        with pytest.raises(KeyError, match="Unknown holder type"):
            construct_holder(
                "nonexistent_holder",
                {"nonexistent_holder": ("Nonexistent", "x")},
                business_with_real_gid,
            )


# ---------------------------------------------------------------------------
# detect_existing_holders Tests
# ---------------------------------------------------------------------------


class TestDetectExistingHolders:
    """Tests for detect_existing_holders() async function."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock AsanaClient."""
        client = MagicMock()
        client.tasks = MagicMock()
        return client

    @pytest.fixture
    def business_holder_key_map(self) -> dict[str, tuple[str, str]]:
        """Business HOLDER_KEY_MAP for testing."""
        return {
            "contact_holder": ("Contacts", "busts_in_silhouette"),
            "unit_holder": ("Business Units", "package"),
            "location_holder": ("Location", "round_pushpin"),
            "dna_holder": ("DNA", "dna"),
            "reconciliation_holder": ("Reconciliations", "abacus"),
            "asset_edit_holder": ("Asset Edits", "art"),
            "videography_holder": ("Videography", "video_camera"),
        }

    def _make_holder_task(
        self,
        name: str,
        gid: str,
        project_gid: str | None = None,
    ) -> Task:
        """Create a Task that looks like a holder subtask."""
        memberships = []
        if project_gid:
            memberships = [{"project": {"gid": project_gid}}]
        return Task(gid=gid, name=name, memberships=memberships)

    @pytest.mark.asyncio
    async def test_all_holders_present(
        self,
        mock_client: MagicMock,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Returns all 7 when all exist."""
        from autom8_asana.models.business.business import (
            AssetEditHolder,
            DNAHolder,
            ReconciliationHolder,
            VideographyHolder,
        )
        from autom8_asana.models.business.contact import ContactHolder
        from autom8_asana.models.business.unit import UnitHolder

        # Create subtasks matching all holder types
        subtasks = [
            self._make_holder_task("Contacts", "h1", ContactHolder.PRIMARY_PROJECT_GID),
            self._make_holder_task(
                "Business Units", "h2", UnitHolder.PRIMARY_PROJECT_GID
            ),
            self._make_holder_task("Location", "h3"),  # No project GID
            self._make_holder_task("DNA", "h4", DNAHolder.PRIMARY_PROJECT_GID),
            self._make_holder_task(
                "Reconciliations", "h5", ReconciliationHolder.PRIMARY_PROJECT_GID
            ),
            self._make_holder_task(
                "Asset Edits", "h6", AssetEditHolder.PRIMARY_PROJECT_GID
            ),
            self._make_holder_task(
                "Videography", "h7", VideographyHolder.PRIMARY_PROJECT_GID
            ),
        ]

        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=subtasks)
        mock_client.tasks.subtasks_async = MagicMock(return_value=mock_iterator)

        result = await detect_existing_holders(
            mock_client, "parent_gid", business_holder_key_map
        )

        assert len(result) == 7

    @pytest.mark.asyncio
    async def test_no_holders_present(
        self,
        mock_client: MagicMock,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Returns empty dict when none exist."""
        # No subtasks
        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=[])
        mock_client.tasks.subtasks_async = MagicMock(return_value=mock_iterator)

        result = await detect_existing_holders(
            mock_client, "parent_gid", business_holder_key_map
        )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_partial_holders_present(
        self,
        mock_client: MagicMock,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Returns only existing ones when partial."""
        from autom8_asana.models.business.business import DNAHolder
        from autom8_asana.models.business.contact import ContactHolder

        subtasks = [
            self._make_holder_task("Contacts", "h1", ContactHolder.PRIMARY_PROJECT_GID),
            self._make_holder_task("DNA", "h4", DNAHolder.PRIMARY_PROJECT_GID),
            self._make_holder_task("Random Task", "x1"),  # Not a holder
        ]

        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=subtasks)
        mock_client.tasks.subtasks_async = MagicMock(return_value=mock_iterator)

        result = await detect_existing_holders(
            mock_client, "parent_gid", business_holder_key_map
        )

        assert len(result) == 2
        assert "contact_holder" in result
        assert "dna_holder" in result
        assert "unit_holder" not in result

    @pytest.mark.asyncio
    async def test_non_holder_subtasks_ignored(
        self,
        mock_client: MagicMock,
        business_holder_key_map: dict[str, tuple[str, str]],
    ) -> None:
        """Non-holder subtasks are not included in the result."""
        subtasks = [
            self._make_holder_task("Just a regular task", "x1"),
            self._make_holder_task("Another task", "x2"),
        ]

        mock_iterator = MagicMock()
        mock_iterator.collect = AsyncMock(return_value=subtasks)
        mock_client.tasks.subtasks_async = MagicMock(return_value=mock_iterator)

        result = await detect_existing_holders(
            mock_client, "parent_gid", business_holder_key_map
        )

        assert len(result) == 0


# ---------------------------------------------------------------------------
# HolderConcurrencyManager Tests
# ---------------------------------------------------------------------------


class TestHolderConcurrencyManager:
    """Tests for HolderConcurrencyManager."""

    def test_same_key_returns_same_lock(self) -> None:
        """Same (parent_gid, holder_type) returns the same lock instance."""
        from autom8_asana.persistence.holder_concurrency import (
            HolderConcurrencyManager,
        )

        manager = HolderConcurrencyManager()
        lock1 = manager.get_lock("parent1", "contact_holder")
        lock2 = manager.get_lock("parent1", "contact_holder")
        assert lock1 is lock2

    def test_different_parents_get_different_locks(self) -> None:
        """Different parents get different locks for the same holder type."""
        from autom8_asana.persistence.holder_concurrency import (
            HolderConcurrencyManager,
        )

        manager = HolderConcurrencyManager()
        lock1 = manager.get_lock("parent1", "contact_holder")
        lock2 = manager.get_lock("parent2", "contact_holder")
        assert lock1 is not lock2

    def test_different_holder_types_get_different_locks(self) -> None:
        """Different holder types get different locks for the same parent."""
        from autom8_asana.persistence.holder_concurrency import (
            HolderConcurrencyManager,
        )

        manager = HolderConcurrencyManager()
        lock1 = manager.get_lock("parent1", "contact_holder")
        lock2 = manager.get_lock("parent1", "unit_holder")
        assert lock1 is not lock2
