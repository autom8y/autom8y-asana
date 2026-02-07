"""Unit task extractor with 23 fields (12 base + 11 Unit-specific).

Per TDD-0009 Phase 3: UnitExtractor extends BaseExtractor with
Unit-specific custom field extraction and derived field stubs.
Per WS3-001: Implements _extract_office_async for Business ancestor name resolution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import UnitRow
from autom8_asana.models.business import EntityType, detect_entity_type

if TYPE_CHECKING:
    from autom8_asana.models.task import Task

logger = get_logger(__name__)


class UnitExtractor(BaseExtractor):
    """Extractor for Unit task type with 23 fields.

    Per FR-SUBCLASS-001: Extracts 12 base fields plus 11 Unit-specific fields.

    Direct custom fields (6):
        mrr, weekly_ad_spend, products, languages, discount, office_phone
        These are extracted via CustomFieldResolver from cf: sources.

    Derived fields (5):
        office, vertical_id, max_pipeline_stage
        vertical_id extracts the Vertical custom field value as-is.
        office and max_pipeline_stage return None pending autom8 team input.
        Note: vertical and specialty are direct custom fields, not derived.

    Example:
        >>> from autom8_asana.dataframes.schemas import UNIT_SCHEMA
        >>> from autom8_asana.dataframes.resolver import MockCustomFieldResolver
        >>> from decimal import Decimal
        >>>
        >>> resolver = MockCustomFieldResolver({
        ...     "mrr": Decimal("5000"),
        ...     "products": ["Product A", "Product B"],
        ... })
        >>> extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        >>> row = extractor.extract(task)
        >>> row.type
        'Unit'
    """

    def _create_row(self, data: dict[str, Any]) -> UnitRow:
        """Create UnitRow from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            UnitRow instance with all 23 fields
        """
        # Ensure type is set correctly
        data["type"] = "Unit"

        # Convert None lists to empty lists for list fields
        if data.get("tags") is None:
            data["tags"] = []
        if data.get("products") is None:
            data["products"] = []
        if data.get("languages") is None:
            data["languages"] = []

        return UnitRow.model_validate(data)

    # =========================================================================
    # Derived field extraction methods (stubs)
    # Per MVP Note: Return None with TODO comments pending business logic input
    # =========================================================================

    def _extract_office(self, task: Task) -> str | None:
        """Extract office name (sync fallback).

        Per WS3-001: The office name is the Business ancestor task's name.
        Sync extraction cannot traverse the parent chain (requires API calls),
        so this returns None. Use extract_async() for full resolution via
        _extract_office_async().

        Args:
            task: Task to extract from

        Returns:
            None (sync path cannot resolve parent chain)
        """
        return None

    async def _extract_office_async(self, task: Task) -> str | None:
        """Extract office name by traversing the parent chain to the Business ancestor.

        Per WS3-001: The office name is the Business task's name. The hierarchy is:
            Unit -> parent(UnitHolder) -> parent(Business)
        This method traverses upward through the parent chain, using entity type
        detection to identify the Business ancestor, then returns its name.

        Uses the CascadingFieldResolver's parent fetching infrastructure to avoid
        duplicate API calls when cascade fields (e.g., office_phone) are also being
        resolved in the same extraction pass.

        Args:
            task: Task to extract from

        Returns:
            Business task name (the office name), or None if:
            - Client is not configured (no parent chain traversal possible)
            - Parent chain is broken (no parent reference)
            - Business ancestor not found within max_depth
            - Entity type detection fails for all ancestors
        """
        if self._client is None:
            logger.debug(
                "extract_office_no_client",
                extra={"task_gid": task.gid},
            )
            return None

        resolver = self._get_cascading_resolver()
        max_depth = 5
        visited: set[str] = set()
        current = task
        depth = 0

        while depth < max_depth:
            if current.gid in visited:
                logger.warning(
                    "extract_office_loop_detected",
                    extra={
                        "task_gid": task.gid,
                        "visited_gids": list(visited),
                    },
                )
                return None

            visited.add(current.gid)

            # Move to parent
            parent_gid = resolver._get_parent_gid(current)
            if parent_gid is None:
                # Reached root of parent chain without finding Business via detection.
                # Per cascade resolver pattern: if root has no parent, treat it as
                # Business (common when project isn't registered in ProjectTypeRegistry).
                detection_result = detect_entity_type(current)
                if (
                    detection_result.entity_type == EntityType.BUSINESS
                    or detection_result.entity_type == EntityType.UNKNOWN
                ):
                    office_name = current.name
                    logger.debug(
                        "extract_office_found_at_root",
                        extra={
                            "task_gid": task.gid,
                            "root_gid": current.gid,
                            "office_name": office_name,
                            "depth": depth,
                            "detection_method": "root_fallback",
                        },
                    )
                    return office_name
                return None

            parent = await resolver._fetch_parent_async(parent_gid)
            if parent is None:
                logger.warning(
                    "extract_office_parent_fetch_failed",
                    extra={
                        "task_gid": task.gid,
                        "parent_gid": parent_gid,
                    },
                )
                return None

            # Check if parent is the Business entity
            detection_result = detect_entity_type(parent)
            if detection_result.entity_type == EntityType.BUSINESS:
                office_name = parent.name
                logger.debug(
                    "extract_office_found",
                    extra={
                        "task_gid": task.gid,
                        "business_gid": parent.gid,
                        "office_name": office_name,
                        "depth": depth + 1,
                        "detection_method": "entity_type",
                    },
                )
                return office_name

            current = parent
            depth += 1

        logger.info(
            "extract_office_max_depth_exceeded",
            extra={
                "task_gid": task.gid,
                "max_depth": max_depth,
            },
        )
        return None

    def _extract_vertical_id(self, task: Task) -> str | None:
        """Extract vertical identifier from the Vertical custom field.

        The Vertical custom field value IS the vertical_id. Values are
        already lowercase snake_case (e.g., "dental", "medical",
        "chiropractic") and require no transformation.

        Uses the same "cf:Vertical" source as the `vertical` column,
        with Utf8 coercion to handle multi-enum list values.

        Args:
            task: Task to extract from

        Returns:
            Vertical identifier string, or None if resolver unavailable
            or field not set on the task.
        """
        if self._resolver is None:
            return None

        # Find the vertical_id column def for Utf8 coercion (handles
        # multi-enum list -> comma-joined string conversion)
        vertical_id_col = next(
            (c for c in self._schema.columns if c.name == "vertical_id"),
            None,
        )
        return self._resolver.get_value(task, "cf:Vertical", column_def=vertical_id_col)

    def _extract_max_pipeline_stage(self, task: Task) -> str | None:
        """Extract maximum pipeline stage reached (derived field stub).

        Per PRD-0003 Appendix A: Derived from UnitHolder model.
        Per MVP Note: Full implementation deferred pending autom8 team input.

        Args:
            task: Task to extract from

        Returns:
            None (stub implementation)

        TODO:
            Implement max_pipeline_stage derivation from UnitHolder.
            Requires access to UnitHolder model and pipeline stage tracking.
        """
        # TODO: Implement max_pipeline_stage derivation from UnitHolder
        # This requires:
        # 1. Access to the Unit's associated UnitHolder(s)
        # 2. Determination of maximum pipeline stage across holders
        # Deferred pending autom8 team input on UnitHolder model
        return None

    # =========================================================================
    # Type override
    # =========================================================================

    def _extract_type(self, task: Task) -> str:
        """Override type extraction to always return 'Unit'.

        Args:
            task: Task to extract from

        Returns:
            'Unit' (always)
        """
        return "Unit"
