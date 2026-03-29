"""Loader-to-processor contract tests.

Per REVIEW-reconciliation-deep-audit TC-9 / P0-C:
These tests verify that the canonical DataFrame schemas (BASE_SCHEMA,
UNIT_SCHEMA) use the correct column name "section" and do NOT use
the processor-local misnomer "section_name".

These are schema-level regression guards: if someone changes the column
name in the schema, these tests will catch it before it reaches production.

Module: tests/unit/reconciliation/test_contract.py
"""

from __future__ import annotations

from autom8_asana.dataframes.schemas.base import BASE_SCHEMA
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA


class TestLoaderToProcessorContract:
    """Schema-level contract tests for loader-to-processor column agreement.

    Per REVIEW-reconciliation-deep-audit TC-1:
    The root cause of 756 phantom exclusions was that processor.py expected
    "section_name" while BASE_SCHEMA defines "section". These tests ensure
    the schema maintains the canonical name.
    """

    def test_base_schema_has_section_column(self) -> None:
        """BASE_SCHEMA defines a 'section' column.

        Per REVIEW-reconciliation-deep-audit TC-1: The canonical column name
        is "section", established at schemas/base.py:84.
        """
        column_names = {col.name for col in BASE_SCHEMA.columns}
        assert "section" in column_names, (
            "BASE_SCHEMA must define a 'section' column. "
            "Per REVIEW-reconciliation-deep-audit TC-1, this is the canonical "
            "column name used by all downstream consumers."
        )

    def test_base_schema_does_not_have_section_name_column(self) -> None:
        """BASE_SCHEMA does NOT define a 'section_name' column.

        Per REVIEW-reconciliation-deep-audit TC-1: "section_name" was a
        processor-local misnomer. The canonical name is "section".
        """
        column_names = {col.name for col in BASE_SCHEMA.columns}
        assert "section_name" not in column_names, (
            "BASE_SCHEMA must NOT define a 'section_name' column. "
            "The canonical column name is 'section'. "
            "Per REVIEW-reconciliation-deep-audit TC-1."
        )

    def test_unit_schema_has_section_column(self) -> None:
        """UNIT_SCHEMA inherits 'section' column from BASE_SCHEMA.

        UNIT_SCHEMA extends BASE_COLUMNS, so it should include the
        'section' column from the base schema.
        """
        column_names = {col.name for col in UNIT_SCHEMA.columns}
        assert "section" in column_names, (
            "UNIT_SCHEMA must include a 'section' column (inherited from BASE_SCHEMA). "
            "Per REVIEW-reconciliation-deep-audit TC-1."
        )

    def test_unit_schema_does_not_have_section_name_column(self) -> None:
        """UNIT_SCHEMA does NOT define a 'section_name' column.

        Neither the base schema nor the unit-specific columns should
        introduce a 'section_name' column.
        """
        column_names = {col.name for col in UNIT_SCHEMA.columns}
        assert "section_name" not in column_names, (
            "UNIT_SCHEMA must NOT define a 'section_name' column. "
            "The canonical column name is 'section'. "
            "Per REVIEW-reconciliation-deep-audit TC-1."
        )
