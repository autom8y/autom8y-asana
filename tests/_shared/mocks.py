"""Shared mock objects for test suite.

This module contains mock objects that are used across multiple test files
to avoid duplication and ensure consistency.
"""

from __future__ import annotations

from typing import Any


class MockTask:
    """Canonical MockTask. SUPERSET of all 11 prior bespoke variants per HYG-003.

    Use via: from tests._shared.mocks import MockTask. Bespoke redefinition forbidden.

    Attributes:
        gid: Task global identifier.
        name: Task name.
        modified_at: ISO 8601 timestamp of last modification.
        created_at: ISO 8601 timestamp of creation.
        due_on: Date string (YYYY-MM-DD) when task is due.
        due_at: ISO 8601 timestamp when task is due (with time).
        completed: Whether the task is completed.
        parent: Parent task reference (Any — local MockNameGid or None).
        custom_fields: List of custom field dicts.
        memberships: List of membership dicts.
        notes: Task notes/description.
        num_subtasks: Number of subtasks.
        completed_at: ISO 8601 timestamp of completion.
        tags: List of tag objects.
        resource_subtype: Task resource subtype string.
        _data: Dict-wrapper escape hatch for site-9 dict-wrapper paradigm.
    """

    def __init__(
        self,
        gid: str | None = None,
        name: str | None = None,
        modified_at: str | None = None,
        created_at: str | None = None,
        due_on: str | None = None,
        due_at: str | None = None,
        completed: bool = False,
        # New (additive per HYG-003):
        parent: Any = None,
        custom_fields: list[dict[str, Any]] | None = None,
        memberships: list[dict[str, Any]] | None = None,
        notes: str | None = None,
        num_subtasks: int | None = None,
        completed_at: str | None = None,
        tags: list[Any] | None = None,
        resource_subtype: str = "default_task",
        _data: dict[str, Any] | None = None,  # site-9 escape hatch
    ) -> None:
        self.gid = gid
        self.name = name
        self.modified_at = modified_at
        self.created_at = created_at
        self.due_on = due_on
        self.due_at = due_at
        self.completed = completed
        self.parent = parent
        self.custom_fields = custom_fields if custom_fields is not None else []
        self.memberships = memberships if memberships is not None else []
        self.notes = notes
        self.num_subtasks = num_subtasks
        self.completed_at = completed_at
        self.tags = tags if tags is not None else []
        self.resource_subtype = resource_subtype
        self._data = _data

    def model_dump(self, exclude_none: bool = False) -> dict[str, Any]:
        """Return raw dict (site-9 dict-wrapper paradigm).

        Raises NotImplementedError unless _data kwarg was provided at construction.
        """
        if self._data is None:
            raise NotImplementedError("model_dump() requires _data kwarg (site-9 paradigm)")
        return self._data
