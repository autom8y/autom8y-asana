"""Pydantic models for intake custom field write endpoint.

Contract constraint: These models MUST produce the exact same JSON shape
as CustomFieldWriteRequest/Response in autom8y-interop/asana/models.py.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CustomFieldWriteRequest(BaseModel):
    """Write custom field values to an Asana task.

    Fields are specified as a dict of field_name -> value.
    The service resolves field names to Asana custom field GIDs
    internally.
    """

    model_config = ConfigDict(frozen=True)

    fields: dict[str, str | int | float | bool | None]


class CustomFieldWriteResponse(BaseModel):
    """Result of custom field writes."""

    model_config = ConfigDict(frozen=True)

    task_gid: str
    fields_written: int
    errors: list[str] = Field(default_factory=list)  # Field names that failed


__all__ = [
    "CustomFieldWriteRequest",
    "CustomFieldWriteResponse",
]
