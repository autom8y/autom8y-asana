"""Saved query model and loader for YAML/JSON query templates.

Enables defining reusable query templates as YAML or JSON files that can
be executed via `python -m autom8_asana.query run <name_or_path>`.

The SavedQuery model maps cleanly to RowsRequest or AggregateRequest
depending on the `command` field.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class SavedJoinSpec(BaseModel):
    """Join specification within a saved query.

    Mirrors JoinSpec fields from query/join.py to support both
    entity joins (Asana-to-Asana) and data-service joins (Asana-to-autom8y-data).
    """

    entity_type: str
    select: list[str] = Field(min_length=1, max_length=10)
    on: str | None = None

    # Cross-service extension (mirrors JoinSpec)
    source: Literal["entity", "data-service"] = "entity"
    factory: str | None = None
    period: str = "LIFETIME"

    @model_validator(mode="after")
    def validate_source_params(self) -> SavedJoinSpec:
        """Ensure factory is provided for data-service joins and absent for entity joins."""
        if self.source == "data-service" and self.factory is None:
            raise ValueError("factory is required when source='data-service'")
        if self.source == "entity" and self.factory is not None:
            raise ValueError("factory is only valid when source='data-service'")
        return self


class SavedQuery(BaseModel):
    """A saved query template loaded from YAML/JSON.

    The `command` field determines whether the query executes as a
    RowsRequest ("rows") or AggregateRequest ("aggregate").

    Attributes:
        name: Human-readable query name (also used for file lookup).
        description: Optional description of what this query does.
        command: Query type -- "rows" for filtered retrieval, "aggregate" for grouping.
        entity_type: Target entity type (offer, unit, business, etc.).
        classification: Classification filter (active, inactive, etc.).
        section: Section name filter (mutually exclusive with classification).
        select: Column list for rows queries.
        where: Predicate filter (single dict or list of dicts for AND).
        limit: Max rows to return (rows queries only).
        offset: Row offset for pagination.
        order_by: Column to sort by.
        order_dir: Sort direction.
        join: Cross-entity join specification.
        group_by: Grouping columns (aggregate queries only).
        aggregations: Aggregation specifications (aggregate queries only).
        having: Post-aggregation filter.
        format: Output format for CLI rendering.
    """

    name: str
    description: str = ""
    command: Literal["rows", "aggregate"] = "rows"
    entity_type: str
    # rows fields
    classification: str | None = None
    section: str | None = None
    select: list[str] | None = None
    where: dict[str, Any] | list[dict[str, Any]] | None = None
    limit: int = 100
    offset: int = 0
    order_by: str | None = None
    order_dir: Literal["asc", "desc"] = "asc"
    join: SavedJoinSpec | None = None
    # aggregate fields
    group_by: list[str] | None = None
    aggregations: list[dict[str, str]] | None = None
    having: dict[str, Any] | list[dict[str, Any]] | None = None
    # output
    format: Literal["table", "json", "csv", "jsonl"] = "table"


def load_saved_query(path: Path) -> SavedQuery:
    """Load a saved query from a YAML or JSON file.

    Args:
        path: Path to a .yaml, .yml, or .json file containing query definition.

    Returns:
        Validated SavedQuery instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If YAML parsing fails.
        json.JSONDecodeError: If JSON parsing fails.
        pydantic.ValidationError: If the data does not match the SavedQuery schema.
    """
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return SavedQuery(**data)


def save_query(saved: SavedQuery, name: str) -> Path:
    """Save a query template to ``~/.autom8/queries/{name}.yaml``.

    Creates the directory if it does not exist. Raises ``FileExistsError``
    if a file with that name already exists (no silent overwrite).

    Args:
        saved: The SavedQuery instance to persist.
        name: File stem used for the YAML file (without extension).

    Returns:
        Path to the written file.

    Raises:
        FileExistsError: If the target file already exists.
    """
    target_dir = Path.home() / ".autom8" / "queries"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{name}.yaml"
    if target.exists():
        raise FileExistsError(f"Query file already exists: {target}")
    data = saved.model_dump(exclude_none=True)
    target.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return target


def find_saved_query(name: str, search_dirs: list[Path] | None = None) -> Path | None:
    """Find a saved query file by name in standard search directories.

    Searches for files named `{name}.yaml`, `{name}.yml`, or `{name}.json`
    in each directory in order. Returns the first match found.

    Args:
        name: Query name to search for (without extension).
        search_dirs: Directories to search. Defaults to:
            1. `./queries/` (project-local)
            2. `~/.autom8/queries/` (user-global)

    Returns:
        Path to the found query file, or None if not found.
    """
    if search_dirs is None:
        search_dirs = [
            Path.cwd() / "queries",
            Path.home() / ".autom8" / "queries",
        ]
    for d in search_dirs:
        for suffix in (".yaml", ".yml", ".json"):
            candidate = d / f"{name}{suffix}"
            if candidate.exists():
                return candidate
    return None
