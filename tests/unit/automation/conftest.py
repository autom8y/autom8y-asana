"""Shared test infrastructure for automation unit tests."""

from __future__ import annotations

from typing import Any


class MockPageIterator:
    """Mock PageIterator that returns a fixed list."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items

    async def collect(self) -> list[Any]:
        return self._items
