"""Offer schema using BASE_COLUMNS only.

Per FR-SUBCLASS-003: OFFER_SCHEMA uses base fields for now.
Offer-specific custom fields can be added when requirements are defined.
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS


OFFER_SCHEMA = DataFrameSchema(
    name="offer",
    task_type="Offer",
    columns=BASE_COLUMNS,  # 12 base columns
    version="1.0.0",
)
