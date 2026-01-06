"""Contact schema using BASE_COLUMNS only.

Per user feedback: DataFrames default to basic entity information.
Contact-specific custom fields can be added when verified on the project.

Previous schema had 9 custom field columns (cf:Full Name, cf:Contact Phone, etc.)
that caused resolution timeouts on large Contacts projects.
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS


CONTACT_SCHEMA = DataFrameSchema(
    name="contact",
    task_type="Contact",
    columns=BASE_COLUMNS,  # 12 base columns only
    version="2.0.0",  # Bumped version for schema change
)
