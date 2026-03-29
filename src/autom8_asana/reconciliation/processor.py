"""Reconciliation batch processor for unit-to-offer activity matching.

Per REVIEW-reconciliation-deep-audit TC-1: All DataFrame column checks use
the canonical "section" column name from schemas/base.py:84. The processor
previously used "section_name" which is a non-existent column in production
DataFrames.

Per REVIEW-reconciliation-deep-audit TC-2: Section exclusion uses
EXCLUDED_SECTION_NAMES from section_registry.py (4 entries), NOT
UNIT_CLASSIFIER.ignored (1 entry). GID-based exclusion fires first;
name-based fallback fires only when GID is unavailable.

Per ADR-pipeline-stage-aggregation Phase 3: Pipeline summary is the
PRIMARY signal for target section derivation. Offer comparison is the
SECONDARY fallback when no pipeline entry exists for a (phone, vertical).

Module: src/autom8_asana/reconciliation/processor.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.clients.utils.pii import mask_phone_number
from autom8_asana.reconciliation.section_registry import (
    EXCLUDED_SECTION_GIDS,
    EXCLUDED_SECTION_NAMES,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pipeline derivation table (ADR-pipeline-stage-aggregation)
# ---------------------------------------------------------------------------
# Built dynamically from lifecycle_stages.yaml cascading_sections.unit values.
# Per ADR-derivation-table-hardcoded-dict: YAML is the single source of truth
# now that the expansion gap is closed (unit: "Active" added to YAML).
# load_config() handles project root detection; LifecycleConfig() alone is a
# no-op (returns _model=None by design for optional-config consumers).
from autom8_asana.lifecycle.config import load_config as _load_lifecycle_config

DERIVATION_TABLE: dict[str, str] = _load_lifecycle_config().build_derivation_table()

# Process pipeline section names that classify as IGNORED (terminal states).
# When the latest process section falls into this set, the process has
# completed and the unit has "graduated" past that pipeline stage.
# In that case, we fall through to the offer-based fallback rather than
# using the derivation table.
_IGNORED_PROCESS_SECTIONS: frozenset[str] = frozenset({
    "TEMPLATE", "TEMPLATES", "COMPLETED", "CONVERTED", "TASKS",
    "FREE MONTH", "VIDEO ONLY", "Untitled section",
})


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ReconciliationAction:
    """A single reconciliation action to be executed.

    Represents a unit task that should be moved to a different section
    based on its offer activity state.
    """

    unit_gid: str
    phone: str
    vertical: str
    current_section: str | None
    target_section: str | None
    reason: str


@dataclass
class ProcessorResult:
    """Aggregated result from a single batch processor run.

    Tracks actions to execute, exclusions, no-ops, and errors for
    downstream reporting and execution.
    """

    actions: list[ReconciliationAction] = field(default_factory=list)
    excluded_count: int = 0
    no_op_count: int = 0
    error_count: int = 0
    total_scanned: int = 0
    skipped_no_section: int = 0


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------


class ReconciliationBatchProcessor:
    """Matches unit activity states against offer activity and derives moves.

    Per REVIEW-reconciliation-deep-audit:
    - P0-A: Column checks use "section" (canonical name from BASE_SCHEMA)
    - P0-B: Exclusion uses EXCLUDED_SECTION_NAMES (4 entries) from
      section_registry, NOT UNIT_CLASSIFIER.ignored (1 entry)
    - P1-B: Schema entry guard warns when neither "section" nor
      "section_name" is present in the DataFrame

    Per ADR-pipeline-stage-aggregation Phase 3:
    - Pipeline summary is PRIMARY signal for target section derivation
    - Offer comparison is SECONDARY fallback
    - When pipeline_summary is None, existing offer logic runs unchanged

    Args:
        unit_df: Polars DataFrame of unit tasks.
        offer_df: Polars DataFrame of offer tasks.
        excluded_section_gids: Section GIDs to exclude from processing.
            Defaults to EXCLUDED_SECTION_GIDS from section_registry.
        dry_run: If True, compute actions but do not execute them.
        pipeline_summary: Optional pipeline summary DataFrame from
            pipeline_stage_aggregator. Columns: office_phone, vertical,
            latest_process_type, latest_process_section, latest_created.
    """

    def __init__(
        self,
        unit_df: Any,
        offer_df: Any,
        *,
        excluded_section_gids: frozenset[str] | None = None,
        dry_run: bool = True,
        pipeline_summary: Any | None = None,
    ) -> None:
        self._unit_df = unit_df
        self._offer_df = offer_df
        self._pipeline_summary = pipeline_summary
        self._excluded_section_gids = (
            excluded_section_gids
            if excluded_section_gids is not None
            else EXCLUDED_SECTION_GIDS
        )
        self._dry_run = dry_run
        self._offer_activity_index: dict[str, str] = {}
        # Composite index: (phone, vertical) -> section for exact match
        self._offer_composite_index: dict[tuple[str, str], str] = {}
        # Phone-only index: phone -> (section, vertical) for fallback
        self._offer_phone_index: dict[str, tuple[str, str]] = {}
        # Pipeline activity index: (phone, vertical) -> (process_type, section)
        self._pipeline_index: dict[tuple[str, str], tuple[str, str]] = {}

        # P1-B: Schema entry guard -- warn if DataFrame lacks section column
        self._validate_schema_entry(unit_df, "unit_df")
        self._validate_schema_entry(offer_df, "offer_df")

    @staticmethod
    def _validate_schema_entry(df: Any, df_name: str) -> None:
        """Warn if DataFrame has neither 'section' nor 'section_name' column.

        Per REVIEW-reconciliation-deep-audit P1-B: Entry guard logs a warning
        when the expected column is missing, making schema mismatches visible
        in logs rather than silently producing empty results.
        """
        if not hasattr(df, "columns"):
            return
        columns = set(df.columns)
        if "section" not in columns and "section_name" not in columns:
            logger.warning(
                "reconciliation_schema_entry_guard",
                extra={
                    "df_name": df_name,
                    "available_columns": sorted(columns),
                    "expected": "section",
                    "reason": "DataFrame has neither 'section' nor 'section_name' column",
                },
            )

    def _build_offer_activity_index(self, offer_df: Any) -> dict[str, str]:
        """Build activity lookup from offer DataFrame using 'section' column.

        Per REVIEW-reconciliation-deep-audit TC-1 / P0-A:
        Uses 'section' column (canonical name from BASE_SCHEMA), NOT
        'section_name'.

        Returns:
            Dict mapping offer_gid -> section_name for offers with
            a non-null section value.
        """
        index: dict[str, str] = {}

        if not hasattr(offer_df, "columns"):
            return index

        # P0-A: Check for canonical "section" column
        has_section = "section" in offer_df.columns

        if not has_section:
            logger.warning(
                "reconciliation_offer_no_section_column",
                extra={
                    "available_columns": sorted(offer_df.columns),
                    "expected": "section",
                },
            )
            return index

        has_gid = "gid" in offer_df.columns
        if not has_gid:
            return index

        for row_idx in range(len(offer_df)):
            gid = offer_df["gid"][row_idx]
            section = offer_df["section"][row_idx]
            if gid and section:
                index[str(gid)] = str(section)

        return index

    def _build_offer_phone_indexes(
        self,
        offer_df: Any,
    ) -> tuple[dict[tuple[str, str], str], dict[str, tuple[str, str]]]:
        """Build phone-based lookup indexes from offer DataFrame.

        Per remediation-vertical-investigation-spike Option C: builds a
        composite (phone, vertical) -> section index for exact match AND a
        phone-only phone -> (section, vertical) fallback index.

        Returns:
            Tuple of (composite_index, phone_only_index) where:
            - composite_index maps (phone, vertical) -> section
            - phone_only_index maps phone -> (section, vertical)
              (first occurrence wins for phone-only; used only as fallback)
        """
        composite: dict[tuple[str, str], str] = {}
        phone_only: dict[str, tuple[str, str]] = {}

        if not hasattr(offer_df, "columns"):
            return composite, phone_only

        columns = set(offer_df.columns)
        has_section = "section" in columns
        has_phone = "office_phone" in columns
        has_vertical = "vertical" in columns

        if not (has_section and has_phone):
            return composite, phone_only

        for row_idx in range(len(offer_df)):
            section = offer_df["section"][row_idx]
            phone = offer_df["office_phone"][row_idx]

            if not section or not phone:
                continue

            phone_str = str(phone)
            section_str = str(section)
            vertical_str = (
                str(offer_df["vertical"][row_idx])
                if has_vertical and offer_df["vertical"][row_idx] is not None
                else ""
            )

            composite[(phone_str, vertical_str)] = section_str

            # Phone-only: first occurrence wins
            if phone_str not in phone_only:
                phone_only[phone_str] = (section_str, vertical_str)

        return composite, phone_only

    def _build_pipeline_index(
        self,
        pipeline_summary: Any,
    ) -> dict[tuple[str, str], tuple[str, str]]:
        """Build pipeline activity index from pipeline_summary DataFrame.

        Maps (phone, vertical) -> (latest_process_type, latest_process_section)
        for use as the PRIMARY signal in reconciliation.

        Args:
            pipeline_summary: Polars DataFrame with columns:
                office_phone, vertical, latest_process_type,
                latest_process_section.

        Returns:
            Dict mapping (phone, vertical) -> (process_type, process_section).
        """
        index: dict[tuple[str, str], tuple[str, str]] = {}

        if not hasattr(pipeline_summary, "columns"):
            return index

        columns = set(pipeline_summary.columns)
        required = {"office_phone", "vertical", "latest_process_type", "latest_process_section"}
        if not required.issubset(columns):
            logger.warning(
                "reconciliation_pipeline_summary_missing_columns",
                extra={
                    "available_columns": sorted(columns),
                    "required": sorted(required),
                },
            )
            return index

        for row_idx in range(len(pipeline_summary)):
            phone = pipeline_summary["office_phone"][row_idx]
            vertical = pipeline_summary["vertical"][row_idx]
            if phone and vertical:
                process_type = pipeline_summary["latest_process_type"][row_idx]
                process_section = pipeline_summary["latest_process_section"][row_idx]
                if process_type is not None and process_section is not None:
                    index[(str(phone), str(vertical))] = (
                        str(process_type),
                        str(process_section),
                    )

        return index

    def _iter_unit_rows(self) -> Iterator[dict[str, Any]]:
        """Iterate unit DataFrame rows as dicts with safe column access.

        Yields dicts with keys: gid, section, section_gid, phone, vertical.
        Missing columns yield None values.
        """
        df = self._unit_df
        if not hasattr(df, "columns"):
            return

        columns = set(df.columns)
        has_gid = "gid" in columns
        # P0-A: Check for canonical "section" column
        has_section = "section" in columns
        has_section_gid = "section_gid" in columns
        has_phone = "office_phone" in columns
        has_vertical = "vertical" in columns

        for row_idx in range(len(df)):
            yield {
                "gid": str(df["gid"][row_idx]) if has_gid else None,
                "section": str(df["section"][row_idx]) if has_section and df["section"][row_idx] is not None else None,
                "section_gid": str(df["section_gid"][row_idx]) if has_section_gid and df["section_gid"][row_idx] is not None else None,
                "phone": str(df["office_phone"][row_idx]) if has_phone and df["office_phone"][row_idx] is not None else None,
                "vertical": str(df["vertical"][row_idx]) if has_vertical and df["vertical"][row_idx] is not None else "",
            }

    def process(self) -> ProcessorResult:
        """Run reconciliation matching on unit DataFrame.

        Per REVIEW-reconciliation-deep-audit:
        - P0-A: Checks "section" in self._unit_df.columns (not "section_name")
        - P0-B: GID exclusion fires first; name fallback uses
          EXCLUDED_SECTION_NAMES (4 entries)

        Per remediation-vertical-investigation-spike Option C:
        - Composite (phone, vertical) index for exact offer matching
        - Phone-only fallback when composite key misses
        - Mismatch warning logged when fallback activates

        Returns:
            ProcessorResult with actions, exclusion counts, and diagnostics.
        """
        result = ProcessorResult()

        # Build pipeline activity index (PRIMARY signal, Phase 3)
        if self._pipeline_summary is not None:
            self._pipeline_index = self._build_pipeline_index(
                self._pipeline_summary,
            )
            logger.info(
                "reconciliation_pipeline_index_built",
                extra={"pipeline_index_size": len(self._pipeline_index)},
            )

        # Build offer activity index (GID-based, existing)
        self._offer_activity_index = self._build_offer_activity_index(
            self._offer_df,
        )

        # Build phone-based indexes for offer matching (Option C -- SECONDARY)
        self._offer_composite_index, self._offer_phone_index = (
            self._build_offer_phone_indexes(self._offer_df)
        )

        # P0-A: Check for canonical "section" column in unit DataFrame
        has_section = "section" in self._unit_df.columns

        if not has_section:
            logger.warning(
                "reconciliation_unit_no_section_column",
                extra={
                    "available_columns": sorted(self._unit_df.columns),
                    "expected": "section",
                    "impact": "all units will be excluded via no-section path",
                },
            )

        for row in self._iter_unit_rows():
            result.total_scanned += 1

            unit_gid = row["gid"]
            section_name = row["section"]
            section_gid = row["section_gid"]
            phone = row["phone"]
            vertical = row["vertical"]

            if not unit_gid:
                result.error_count += 1
                continue

            # P0-B: Section exclusion logic
            # Step 1: GID exclusion fires FIRST
            if section_gid and section_gid in self._excluded_section_gids:
                result.excluded_count += 1
                logger.debug(
                    "reconciliation_excluded_by_gid",
                    extra={
                        "unit_gid": unit_gid,
                        "section_gid": section_gid,
                    },
                )
                continue

            # Step 2: Name fallback fires ONLY when GID unavailable
            if not section_gid and section_name and section_name in EXCLUDED_SECTION_NAMES:
                result.excluded_count += 1
                logger.debug(
                    "reconciliation_excluded_by_name",
                    extra={
                        "unit_gid": unit_gid,
                        "section_name": section_name,
                    },
                )
                continue

            # Step 3: No section at all -- exclude with diagnostic
            if not section_name:
                result.skipped_no_section += 1
                result.excluded_count += 1
                continue

            # Reconciliation matching logic: compare unit section against
            # pipeline activity (PRIMARY) then offer activity (SECONDARY).
            if not phone:
                result.no_op_count += 1
                continue

            composite_key = (phone, vertical)

            # =============================================================
            # PRIMARY: Pipeline-driven derivation (Phase 3)
            # =============================================================
            pipeline_entry = self._pipeline_index.get(composite_key)
            if pipeline_entry is not None:
                process_type, process_section = pipeline_entry

                # Check if the process section is an IGNORED terminal state
                # (CONVERTED, COMPLETED, etc.). When IGNORED, the process
                # has finished and the unit has "graduated" -- fall through
                # to offer-based comparison rather than using DERIVATION_TABLE.
                if process_section.upper() in _IGNORED_PROCESS_SECTIONS:
                    logger.debug(
                        "reconciliation_pipeline_ignored",
                        extra={
                            "unit_gid": unit_gid,
                            "process_type": process_type,
                            "process_section": process_section,
                            "match_type": "pipeline_ignored_fallthrough",
                        },
                    )
                    # Fall through to offer-based comparison below.
                else:
                    target_section = DERIVATION_TABLE.get(process_type)
                    if target_section is not None and target_section != section_name:
                        # Pipeline says unit should be in a different section.
                        result.actions.append(
                            ReconciliationAction(
                                unit_gid=unit_gid,
                                phone=mask_phone_number(phone),
                                vertical=vertical,
                                current_section=section_name,
                                target_section=target_section,
                                reason=(
                                    f"Unit in '{section_name}' but pipeline "
                                    f"'{process_type}' indicates '{target_section}'"
                                ),
                            )
                        )
                        continue
                    elif target_section == section_name:
                        # Pipeline confirms unit is in the correct section.
                        result.no_op_count += 1
                        continue
                    # target_section is None (unknown process_type) -- fall
                    # through to offer-based comparison.

            # =============================================================
            # SECONDARY: Offer-based comparison (existing logic)
            # =============================================================
            # Option C: Composite key lookup with phone-only fallback.
            # Try exact (phone, vertical) match first; fall back to
            # phone-only when composite key misses.
            offer_section = self._offer_composite_index.get(composite_key)

            if offer_section is not None:
                # Exact match found
                logger.debug(
                    "reconciliation_unit_processed",
                    extra={
                        "unit_gid": unit_gid,
                        "section": section_name,
                        "lookup_key": f"{phone}:{vertical}",
                        "match_type": "exact",
                    },
                )
            else:
                # Fallback: phone-only lookup
                phone_match = self._offer_phone_index.get(phone)
                if phone_match is not None:
                    offer_section, offer_vertical = phone_match
                    logger.warning(
                        "reconciliation_vertical_mismatch",
                        extra={
                            "unit_gid": unit_gid,
                            "phone": phone,
                            "unit_vertical": vertical,
                            "offer_vertical": offer_vertical,
                            "match_type": "phone_only_fallback",
                        },
                    )
                else:
                    logger.debug(
                        "reconciliation_unit_processed",
                        extra={
                            "unit_gid": unit_gid,
                            "section": section_name,
                            "lookup_key": f"{phone}:{vertical}",
                            "match_type": "no_match",
                        },
                    )

            # Three-way action decision based on offer lookup outcome.
            if offer_section is None:
                # No offer data found for this unit -- nothing to compare.
                result.no_op_count += 1
            elif offer_section == section_name:
                # Unit is already in the correct section.
                result.no_op_count += 1
            else:
                # Section mismatch -- unit needs to move.
                result.actions.append(
                    ReconciliationAction(
                        unit_gid=unit_gid,
                        phone=mask_phone_number(phone),
                        vertical=vertical,
                        current_section=section_name,
                        target_section=offer_section,
                        reason=(
                            f"Unit in '{section_name}' but offer indicates "
                            f"'{offer_section}'"
                        ),
                    )
                )

        return result
