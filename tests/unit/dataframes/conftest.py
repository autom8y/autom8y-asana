"""Shared fixtures for the dataframes unit test suite.

Provides shared mock factories and test helpers used across
test_schema_extractor.py, test_schema_extractor_completeness.py, and
test_schema_extractor_adversarial.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from autom8_asana.dataframes.builders.base import DataFrameBuilder

if TYPE_CHECKING:
    from autom8_asana.dataframes.extractors.base import BaseExtractor
    from autom8_asana.dataframes.models.schema import DataFrameSchema


def make_mock_task() -> MagicMock:
    """Create a minimal mock task that satisfies BaseExtractor's base 13 fields."""
    task = MagicMock()
    task.gid = "1234567890"
    task.name = "Test Task"
    task.resource_subtype = "default_task"
    task.created_at = "2026-01-01T00:00:00Z"
    task.due_on = "2026-01-15"
    task.completed = False
    task.completed_at = None
    task.modified_at = "2026-01-01T00:00:00Z"
    task.tags = []
    task.memberships = []
    task.custom_fields = []
    task.parent = None
    return task


class _TestBuilder(DataFrameBuilder):
    """Minimal concrete builder for calling _create_extractor in tests."""

    def __init__(self, schema: DataFrameSchema) -> None:
        super().__init__(schema)

    def get_tasks(self) -> list:
        return []

    def _get_project_gid(self) -> str | None:
        return None

    def _get_extractor(self) -> BaseExtractor:
        return self._create_extractor(self._schema.task_type)
