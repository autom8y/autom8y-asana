"""Schema-driven generic extractor using dynamic Pydantic row models.

Per TDD-ENTITY-EXT-001: SchemaExtractor dynamically generates a Pydantic
row model from any DataFrameSchema, eliminating the need for per-entity
extractor and row model boilerplate for entities whose schemas contain
only cf:, cascade:, gid:, and direct-attribute sources.

Entities with custom derived field logic (source=None columns needing
traversal or computation) still require hand-coded extractors (e.g.,
UnitExtractor for _extract_office_async).
"""

from __future__ import annotations

import datetime as dt
import threading
from typing import TYPE_CHECKING, Any

from pydantic import Field, create_model

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import TaskRow

if TYPE_CHECKING:
    pass


# Module-level cache: schema task_type -> dynamically created model class
_MODEL_CACHE: dict[str, type[TaskRow]] = {}
_MODEL_CACHE_LOCK = threading.Lock()

# Dtype string -> (Python type, default value) mapping
# Covers all dtype strings used in existing schemas (PRD Section 10)
DTYPE_MAP: dict[str, tuple[type, Any]] = {
    "Utf8": (str, None),
    "String": (str, None),
    "Int64": (int, None),
    "Int32": (int, None),
    "Float64": (float, None),
    "Boolean": (bool, None),
    "Date": (dt.date, None),
    "Datetime": (dt.datetime, None),
    "Decimal": (float, None),  # Polars maps Decimal->Float64; Python float suffices
    "List[Utf8]": (list[str], None),  # List normalization handled by BaseExtractor
    "List[String]": (list[str], None),
}


class SchemaExtractor(BaseExtractor):
    """Generic extractor that works with any DataFrameSchema.

    Dynamically generates a Pydantic row model from the schema's ColumnDefs,
    enabling extraction for any entity type without a dedicated extractor class.

    The dynamic model:
    - Inherits from TaskRow (gets the 12 base fields and to_dict())
    - Adds Optional fields for each schema column beyond the base 12
    - Uses create_model() for field generation, cached per schema task_type
    - Sets model_config with extra="ignore" on the dynamic subclass to
      accept the entity-specific columns that TaskRow(extra="forbid") rejects

    Thread Safety:
        The dynamic model is generated once per schema task_type and cached
        in a module-level dict protected by threading.Lock. Concurrent calls
        to _build_dynamic_row_model() are safe.

    Attributes:
        schema: DataFrameSchema defining columns to extract
        resolver: Optional CustomFieldResolver for cf:/gid: fields
        client: Optional AsanaClient for cascade: field resolution
    """

    def _create_row(self, data: dict[str, Any]) -> TaskRow:
        """Create a dynamically-generated row model from extracted data.

        Sets the type field to schema.task_type. List field normalization
        (None -> []) is handled by BaseExtractor._normalize_list_fields()
        before this method is called.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            Instance of the dynamically-generated TaskRow subclass
        """
        # Set type to match schema
        data["type"] = self._schema.task_type

        model_class = self._build_dynamic_row_model()
        return model_class.model_validate(data)

    def _extract_type(self, task: Any) -> str:
        """Return the schema's task_type as the type discriminator.

        Args:
            task: Task to extract from (unused -- type is schema-defined)

        Returns:
            Schema task_type string (e.g., "Offer", "AssetEdit")
        """
        return self._schema.task_type

    def _build_dynamic_row_model(self) -> type[TaskRow]:
        """Build or retrieve cached Pydantic model matching the schema.

        Uses pydantic.create_model() to generate a TaskRow subclass with
        fields for each column beyond the base 12. The model is cached
        per schema task_type in a thread-safe module-level dict.

        Returns:
            Dynamically-generated type[TaskRow] with all schema columns
        """
        cache_key = self._schema.task_type

        # Fast path: check cache without lock
        if cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]

        # Slow path: build model under lock
        with _MODEL_CACHE_LOCK:
            # Double-checked locking
            if cache_key in _MODEL_CACHE:
                return _MODEL_CACHE[cache_key]

            base_field_names = set(TaskRow.model_fields.keys())
            extra_fields: dict[str, Any] = {}

            for col in self._schema.columns:
                if col.name in base_field_names:
                    continue  # Skip base 12 fields -- already on TaskRow

                python_type, default = DTYPE_MAP.get(col.dtype, (str, None))

                if col.dtype in ("List[Utf8]", "List[String]"):
                    # List fields use Field(default_factory=list) for safety
                    extra_fields[col.name] = (
                        python_type | None,
                        Field(default_factory=list),
                    )
                else:
                    # All other fields are Optional with None default
                    extra_fields[col.name] = (python_type | None, None)

            model_name = f"{self._schema.task_type}SchemaRow"

            # Create model with extra="ignore" to accept dynamic fields
            # that TaskRow's extra="forbid" would reject
            DynamicModel = create_model(
                model_name,
                __base__=TaskRow,
                **extra_fields,
            )
            # Override the model_config to allow extra fields on THIS subclass
            # while keeping TaskRow's config for its own direct usage
            DynamicModel.model_config["extra"] = "ignore"
            DynamicModel.model_config["strict"] = False

            _MODEL_CACHE[cache_key] = DynamicModel
            return DynamicModel
