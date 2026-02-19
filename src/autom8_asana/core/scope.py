"""Workflow-agnostic entity targeting and execution control.

Per TDD-ENTITY-SCOPE-001 Section 2.1, ADR-001:
EntityScope is a frozen dataclass consumed by the handler factory
(lambda_handlers/), the API layer (api/routes/), and the CLI (scripts/).
Placed in core/ because it is a cross-cutting invocation concern, not a
workflow-specific concern. Dependency direction: core/ -> consumed by
automation/, lambda_handlers/, api/.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityScope:
    """Workflow-agnostic entity targeting and execution control.

    Frozen dataclass constructed once at the invocation boundary (Lambda
    handler, API endpoint, or CLI). Passed to WorkflowAction.enumerate_async()
    to control which entities are resolved.

    Attributes:
        entity_ids: GIDs to target. Empty tuple means full enumeration.
        section_filter: Section names to restrict enumeration to.
            Ignored when entity_ids is non-empty.
        limit: Maximum entities to process. None means no limit.
        dry_run: If True, skip write operations (upload, delete).
    """

    entity_ids: tuple[str, ...] = ()
    section_filter: frozenset[str] = frozenset()
    limit: int | None = None
    dry_run: bool = False

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> EntityScope:
        """Construct from a Lambda event dict or API request body.

        Normalizes input types:
        - entity_ids: accepts list[str] or tuple[str, ...], stored as tuple
        - section_filter: accepts list[str] or set[str], stored as frozenset
        - limit: accepts int or None
        - dry_run: accepts bool (default False)

        Unknown keys are silently ignored (forward-compatible).

        Args:
            event: Raw event dict from Lambda, API, or CLI.

        Returns:
            Frozen EntityScope instance.
        """
        raw_ids = event.get("entity_ids", ())
        raw_sections = event.get("section_filter", ())
        return cls(
            entity_ids=tuple(raw_ids) if raw_ids else (),
            section_filter=frozenset(raw_sections) if raw_sections else frozenset(),
            limit=event.get("limit"),
            dry_run=bool(event.get("dry_run", False)),
        )

    @property
    def has_entity_ids(self) -> bool:
        """True when specific entities are targeted."""
        return bool(self.entity_ids)

    def to_params(self) -> dict[str, Any]:
        """Serialize to flat dict for injection into workflow params.

        Returns:
            Dict with dry_run key only. Entity targeting is handled
            via enumerate_async, not params.
        """
        return {
            "dry_run": self.dry_run,
        }
