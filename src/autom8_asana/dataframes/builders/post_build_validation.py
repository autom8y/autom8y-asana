"""Post-build cascade validation and audit for progressive builder.

Extracted from ProgressiveProjectBuilder.build_progressive_async to separate
the post-build verification concern from the main build pipeline.

Handles:
- Step 5.5: Cascade field validation (corrects stale cascade values)
- Step 5.6: Cascade null rate audit (diagnostic logging)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    import polars as pl

    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin

__all__ = ["post_build_validate_and_audit"]

logger = get_logger(__name__)


async def post_build_validate_and_audit(
    merged_df: pl.DataFrame,
    store: Any,
    dataframe_view: DataFrameViewPlugin | None,
    schema: DataFrameSchema,
    entity_type: str,
    project_gid: str,
) -> tuple[pl.DataFrame, int]:
    """Run post-build cascade validation and audit on merged DataFrame.

    Step 5.5: Cascade field validation (corrects stale cascade values).
    Step 5.6: Cascade null rate audit (diagnostic logging).

    Args:
        merged_df: Merged DataFrame from all sections.
        store: UnifiedStore for cascade resolution.
        dataframe_view: View plugin (needed for cascade_plugin access).
        schema: DataFrame schema for the entity type.
        entity_type: Entity type string.
        project_gid: Project GID string.

    Returns:
        Tuple of (potentially-modified DataFrame, total_rows after validation).
    """
    total_rows = len(merged_df)

    # Step 5.5: Post-build cascade validation pass
    # Per TDD-CASCADE-FAILURE-FIXES-001 Fix 3: Detect and correct stale
    # cascade fields after section merge, before final artifact write.
    if store is not None:
        from autom8_asana.settings import get_settings

        if get_settings().runtime.section_cascade_validation != "0":
            from autom8_asana.dataframes.builders.cascade_validator import (
                validate_cascade_fields_async,
            )

            cascade_plugin = dataframe_view.cascade_plugin if dataframe_view is not None else None
            if cascade_plugin is not None:
                try:
                    (
                        merged_df,
                        _cascade_result,
                    ) = await validate_cascade_fields_async(
                        merged_df=merged_df,
                        store=store,
                        cascade_plugin=cascade_plugin,
                        project_gid=project_gid,
                        entity_type=entity_type,
                        schema=schema,
                    )
                    total_rows = len(merged_df)
                except Exception as e:  # BROAD-CATCH: validation is additive
                    logger.warning(
                        "cascade_validation_failed",
                        extra={
                            "project_gid": project_gid,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )

    # Step 5.6: Post-correction cascade null rate audit
    # Per ADR-cascade-contract-policy: log null rates for cascade-sourced
    # key columns so that regressions analogous to SCAR-005/006 are
    # observable via structured logging.
    if total_rows > 0 and schema is not None:
        try:
            from autom8_asana.core.entity_registry import get_registry
            from autom8_asana.dataframes.builders.cascade_validator import (
                audit_cascade_display_nulls,
                audit_cascade_key_nulls,
                audit_phone_e164_compliance,
            )

            desc = get_registry().get(entity_type)
            if desc is not None and desc.key_columns:
                audit_cascade_key_nulls(
                    df=merged_df,
                    entity_type=entity_type,
                    project_gid=project_gid,
                    schema=schema,
                    key_columns=desc.key_columns,
                )
                # Per GAP-A sprint-4: audit display-column null rates
                # (cascade-sourced but not key columns, e.g., office)
                audit_cascade_display_nulls(
                    df=merged_df,
                    entity_type=entity_type,
                    project_gid=project_gid,
                    schema=schema,
                    key_columns=desc.key_columns,
                )
            # Per GAP-B sprint-4: audit phone E.164 compliance
            # (runs for any entity with office_phone column)
            audit_phone_e164_compliance(
                df=merged_df,
                entity_type=entity_type,
                project_gid=project_gid,
            )
        except Exception as e:  # BROAD-CATCH: audit is diagnostic only
            logger.warning(
                "cascade_key_null_audit_failed",
                extra={
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

    return merged_df, total_rows
