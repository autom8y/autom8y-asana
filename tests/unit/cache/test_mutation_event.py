"""Tests for MutationEvent dataclass and extract_project_gids helper.

Per TDD-CACHE-INVALIDATION-001 Test Strategy: Unit tests for MutationEvent
and extract_project_gids().
"""

import pytest

from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
    extract_project_gids,
)


class TestMutationEvent:
    """Tests for MutationEvent frozen dataclass."""

    def test_create_task_event(self) -> None:
        """MutationEvent for task creation has correct fields."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.CREATE,
            project_gids=["proj1", "proj2"],
        )
        assert event.entity_kind == EntityKind.TASK
        assert event.entity_gid == "12345"
        assert event.mutation_type == MutationType.CREATE
        assert event.project_gids == ["proj1", "proj2"]
        assert event.section_gid is None
        assert event.source_section_gid is None

    def test_move_event_with_section_context(self) -> None:
        """MutationEvent for section move carries section context."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.MOVE,
            project_gids=["proj1"],
            section_gid="sect_dest",
            source_section_gid="sect_src",
        )
        assert event.mutation_type == MutationType.MOVE
        assert event.section_gid == "sect_dest"
        assert event.source_section_gid == "sect_src"

    def test_frozen_immutability(self) -> None:
        """MutationEvent is frozen (immutable)."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.UPDATE,
        )
        with pytest.raises(AttributeError):
            event.entity_gid = "99999"  # type: ignore[misc]

    def test_default_project_gids_empty(self) -> None:
        """MutationEvent defaults to empty project_gids list."""
        event = MutationEvent(
            entity_kind=EntityKind.TASK,
            entity_gid="12345",
            mutation_type=MutationType.DELETE,
        )
        assert event.project_gids == []

    def test_section_event(self) -> None:
        """MutationEvent for section mutation."""
        event = MutationEvent(
            entity_kind=EntityKind.SECTION,
            entity_gid="sect1",
            mutation_type=MutationType.CREATE,
            project_gids=["proj1"],
        )
        assert event.entity_kind == EntityKind.SECTION

    def test_mutation_type_enum_values(self) -> None:
        """MutationType enum values match expected strings."""
        assert MutationType.CREATE == "create"
        assert MutationType.UPDATE == "update"
        assert MutationType.DELETE == "delete"
        assert MutationType.MOVE == "move"
        assert MutationType.ADD_MEMBER == "add"
        assert MutationType.REMOVE_MEMBER == "remove"

    def test_entity_kind_enum_values(self) -> None:
        """EntityKind enum values match expected strings."""
        assert EntityKind.TASK == "task"
        assert EntityKind.SECTION == "section"
        assert EntityKind.PROJECT == "project"


class TestExtractProjectGids:
    """Tests for extract_project_gids helper."""

    def test_extract_from_projects_array(self) -> None:
        """Extracts GIDs from task.projects[] (REST format)."""
        task_data = {
            "gid": "12345",
            "name": "Test Task",
            "projects": [
                {"gid": "proj1", "name": "Project 1"},
                {"gid": "proj2", "name": "Project 2"},
            ],
        }
        gids = extract_project_gids(task_data)
        assert gids == ["proj1", "proj2"]

    def test_extract_from_memberships_array(self) -> None:
        """Extracts GIDs from task.memberships[].project (SaveSession format)."""
        task_data = {
            "gid": "12345",
            "memberships": [
                {"project": {"gid": "proj1"}, "section": {"gid": "sect1"}},
                {"project": {"gid": "proj2"}, "section": {"gid": "sect2"}},
            ],
        }
        gids = extract_project_gids(task_data)
        assert gids == ["proj1", "proj2"]

    def test_prefers_projects_over_memberships(self) -> None:
        """Projects array takes precedence over memberships."""
        task_data = {
            "gid": "12345",
            "projects": [{"gid": "proj1"}],
            "memberships": [{"project": {"gid": "proj_other"}}],
        }
        gids = extract_project_gids(task_data)
        assert gids == ["proj1"]

    def test_returns_empty_for_none_input(self) -> None:
        """Returns empty list for None input."""
        assert extract_project_gids(None) == []

    def test_returns_empty_for_empty_dict(self) -> None:
        """Returns empty list for dict with no projects/memberships."""
        assert extract_project_gids({"gid": "12345"}) == []

    def test_returns_empty_for_empty_projects_list(self) -> None:
        """Returns empty list when projects array is empty."""
        assert extract_project_gids({"projects": []}) == []

    def test_handles_malformed_projects(self) -> None:
        """Gracefully handles non-dict entries in projects array."""
        task_data = {
            "projects": [
                {"gid": "proj1"},
                "not_a_dict",
                {"name": "no_gid"},
                {"gid": "proj2"},
            ],
        }
        gids = extract_project_gids(task_data)
        assert gids == ["proj1", "proj2"]

    def test_handles_malformed_memberships(self) -> None:
        """Gracefully handles non-dict entries in memberships array."""
        task_data = {
            "memberships": [
                {"project": {"gid": "proj1"}},
                "not_a_dict",
                {"project": "not_a_dict"},
                {"project": {"gid": "proj2"}},
            ],
        }
        gids = extract_project_gids(task_data)
        assert gids == ["proj1", "proj2"]

    def test_projects_not_a_list(self) -> None:
        """Returns empty if projects is not a list."""
        assert extract_project_gids({"projects": "not_a_list"}) == []
