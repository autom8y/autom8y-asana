"""Shared test data factories.

Reusable builders for test fixtures used across multiple test modules.
Use via: ``from tests._shared.factories import make_task_dict``. Bespoke
redefinition is forbidden (mirrors the ``tests/_shared/mocks.py`` discipline).
"""

from __future__ import annotations

_DEFAULT_MODIFIED_AT = "2025-12-23T10:00:00.000Z"


def make_task_dict(
    gid: str,
    name: str | None = None,
    parent_gid: str | None = None,
    modified_at: str = _DEFAULT_MODIFIED_AT,
) -> dict:
    """Build a minimal Asana task dict for cache/pacing tests.

    Args:
        gid: Task gid.
        name: Task name; defaults to ``f"Task {gid}"`` when omitted.
        parent_gid: When set, adds a ``parent`` reference ``{"gid": parent_gid}``.
        modified_at: ISO-8601 modification timestamp.
    """
    task: dict = {
        "gid": gid,
        "name": name if name is not None else f"Task {gid}",
        "modified_at": modified_at,
    }
    if parent_gid:
        task["parent"] = {"gid": parent_gid}
    return task
