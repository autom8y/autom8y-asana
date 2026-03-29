"""Backfill cf:Vertical for unit tasks with empty vertical values.

Per remediation-vertical-investigation-spike Option A+C:
Cache-warmer passthrough approach that accepts a DataFrame of unit tasks,
identifies those with empty cf:Vertical, parses the vertical value from
task notes, and writes the custom field via the Asana API.

Module: src/autom8_asana/services/vertical_backfill.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    import polars as pl

logger = get_logger(__name__)

# Regex to extract vertical from task notes.
# Matches "Vertical: <value>" at the start of notes or on its own line.
_VERTICAL_NOTES_RE = re.compile(r"(?:^|\n)\s*Vertical:\s*(.+?)(?:\n|$)", re.IGNORECASE)


@dataclass
class BackfillResult:
    """Aggregated result from a vertical backfill run.

    Attributes:
        attempted: Number of tasks that were candidates for backfill.
        succeeded: Number of tasks where cf:Vertical was written successfully.
        skipped: Number of tasks skipped (no vertical found in notes, etc.).
        failed: Number of tasks where the write attempt raised an error.
        errors: List of (task_gid, error_message) for failed tasks.
    """

    attempted: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)


class VerticalBackfillService:
    """Backfill cf:Vertical for unit tasks with empty vertical values.

    Stakeholder-approved cache-warmer passthrough approach:
    1. Accept a DataFrame of unit tasks
    2. Filter for tasks where vertical is null/empty
    3. For each, fetch task notes and parse "Vertical: {value}"
    4. Write cf:Vertical via the Asana enum resolution pattern

    Args:
        client: Asana client instance with a ``tasks`` attribute providing
            ``get_async`` and ``update_async`` methods.
        log: Optional logger override. Defaults to module-level logger.
    """

    def __init__(self, client: Any, log: Any | None = None) -> None:
        self._client = client
        self._log = log or logger

    async def backfill_from_dataframe(
        self,
        unit_df: pl.DataFrame,
    ) -> BackfillResult:
        """Identify unit tasks with empty vertical and backfill cf:Vertical.

        Filters the DataFrame for rows where the ``vertical`` column is
        null or empty AND ``gid`` is present. For each candidate, attempts
        to parse the vertical from Asana task notes and write the custom
        field.

        Args:
            unit_df: Polars DataFrame of unit tasks. Must contain ``gid``
                and ``vertical`` columns.

        Returns:
            BackfillResult with counts of attempted, succeeded, skipped,
            and failed tasks.
        """
        result = BackfillResult()

        if not hasattr(unit_df, "columns"):
            return result

        has_gid = "gid" in unit_df.columns
        has_vertical = "vertical" in unit_df.columns

        if not has_gid:
            self._log.warning(
                "vertical_backfill_no_gid_column",
                extra={"available_columns": sorted(unit_df.columns)},
            )
            return result

        if not has_vertical:
            self._log.warning(
                "vertical_backfill_no_vertical_column",
                extra={"available_columns": sorted(unit_df.columns)},
            )
            return result

        # Identify candidate rows: vertical is null or empty string, gid present
        for row_idx in range(len(unit_df)):
            gid = unit_df["gid"][row_idx]
            vertical = unit_df["vertical"][row_idx]

            if not gid:
                continue

            gid_str = str(gid)

            # Skip rows that already have a non-empty vertical
            if vertical is not None and str(vertical).strip():
                continue

            result.attempted += 1

            try:
                success = await self._backfill_single_task(gid_str)
                if success:
                    result.succeeded += 1
                else:
                    result.skipped += 1
            except Exception as e:  # BROAD-CATCH: isolation -- single task failure must not abort batch
                result.failed += 1
                result.errors.append((gid_str, str(e)))
                self._log.warning(
                    "vertical_backfill_task_error",
                    extra={
                        "task_gid": gid_str,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

        self._log.info(
            "vertical_backfill_complete",
            extra={
                "attempted": result.attempted,
                "succeeded": result.succeeded,
                "skipped": result.skipped,
                "failed": result.failed,
            },
        )

        return result

    async def _backfill_single_task(self, task_gid: str) -> bool:
        """Fetch task notes, parse vertical, and write cf:Vertical.

        Reuses the enum resolution pattern from
        ``IntakeCreateService._write_vertical_custom_field``: fetch task
        custom fields, locate the "Vertical" field by name
        (case-insensitive), match the enum option by name
        (case-insensitive), and write via ``tasks.update_async``.

        Args:
            task_gid: The Asana GID of the unit task to backfill.

        Returns:
            True if the custom field was written successfully.
            False if the task was skipped (no vertical in notes, no
            matching custom field or enum option).
        """
        # Fetch task with notes and custom field metadata
        task_data = await self._client.tasks.get_async(
            task_gid,
            opt_fields=[
                "notes",
                "custom_fields.gid",
                "custom_fields.name",
                "custom_fields.enum_options.gid",
                "custom_fields.enum_options.name",
            ],
        )

        # Extract notes
        notes = (
            task_data.get("notes", "")
            if isinstance(task_data, dict)
            else getattr(task_data, "notes", "")
        ) or ""

        # Parse vertical from notes
        vertical = parse_vertical_from_notes(notes)
        if not vertical:
            self._log.warning(
                "vertical_backfill_no_vertical_in_notes",
                extra={"task_gid": task_gid},
            )
            return False

        # Resolve custom fields
        custom_fields = (
            task_data.get("custom_fields", [])
            if isinstance(task_data, dict)
            else getattr(task_data, "custom_fields", []) or []
        )

        # Find the "Vertical" custom field entry (case-insensitive)
        vertical_cf = None
        for cf in custom_fields:
            cf_name = (
                cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            )
            if cf_name and cf_name.lower() == "vertical":
                vertical_cf = cf
                break

        if vertical_cf is None:
            self._log.warning(
                "vertical_backfill_cf_not_found",
                extra={"task_gid": task_gid},
            )
            return False

        cf_gid = (
            vertical_cf.get("gid", "")
            if isinstance(vertical_cf, dict)
            else getattr(vertical_cf, "gid", "")
        )
        enum_options = (
            vertical_cf.get("enum_options", [])
            if isinstance(vertical_cf, dict)
            else getattr(vertical_cf, "enum_options", []) or []
        )

        # Match enum option by name (case-insensitive)
        enum_option_gid = None
        for opt in enum_options:
            opt_name = (
                opt.get("name", "") if isinstance(opt, dict) else getattr(opt, "name", "")
            )
            if opt_name and opt_name.lower() == vertical.lower():
                enum_option_gid = (
                    opt.get("gid", "")
                    if isinstance(opt, dict)
                    else getattr(opt, "gid", "")
                )
                break

        if not enum_option_gid:
            self._log.warning(
                "vertical_backfill_enum_option_not_found",
                extra={"task_gid": task_gid, "vertical": vertical},
            )
            return False

        # Write the custom field
        await self._client.tasks.update_async(
            task_gid,
            data={"custom_fields": {cf_gid: {"gid": enum_option_gid}}},
        )

        self._log.info(
            "vertical_backfill_task_success",
            extra={
                "task_gid": task_gid,
                "vertical": vertical,
                "cf_gid": cf_gid,
                "enum_option_gid": enum_option_gid,
            },
        )

        return True


def parse_vertical_from_notes(notes: str) -> str | None:
    """Extract the vertical value from task notes.

    Looks for a line matching ``Vertical: <value>`` (case-insensitive).
    Returns the stripped value, or None if not found.

    Args:
        notes: The raw task notes string.

    Returns:
        The vertical value string, or None if not found.
    """
    if not notes:
        return None

    match = _VERTICAL_NOTES_RE.search(notes)
    if match:
        value = match.group(1).strip()
        return value if value else None

    return None
