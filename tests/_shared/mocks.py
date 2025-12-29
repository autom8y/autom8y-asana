"""Shared mock objects for test suite.

This module contains mock objects that are used across multiple test files
to avoid duplication and ensure consistency.
"""

from __future__ import annotations


class MockTask:
    """Mock task object that mimics Asana task attributes.

    Used for TriggerEvaluator tests where we need precise control
    over date fields without hitting the API.

    Attributes:
        gid: Task global identifier.
        name: Task name.
        modified_at: ISO 8601 timestamp of last modification.
        created_at: ISO 8601 timestamp of creation.
        due_on: Date string (YYYY-MM-DD) when task is due.
        due_at: ISO 8601 timestamp when task is due (with time).
        completed: Whether the task is completed.
    """

    def __init__(
        self,
        gid: str,
        name: str,
        modified_at: str | None = None,
        created_at: str | None = None,
        due_on: str | None = None,
        due_at: str | None = None,
        completed: bool = False,
    ) -> None:
        self.gid = gid
        self.name = name
        self.modified_at = modified_at
        self.created_at = created_at
        self.due_on = due_on
        self.due_at = due_at
        self.completed = completed
