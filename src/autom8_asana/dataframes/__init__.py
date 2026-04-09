"""Structured Dataframe Layer for autom8_asana SDK.

Per TDD-0009: Provides schema-driven extraction of Asana task data
into typed Polars DataFrames.

Per TDD-0009.1: Custom field resolution via resolver module enables
dynamic mapping of schema field names to Asana custom field GIDs.

Per TDD-0009 Phase 4: Builders package provides lazy/eager evaluation,
resolver lifecycle management, and extractor factory pattern.

Per TDD-0008 Session 4 Phase 4: Cache integration layer provides
schema-version-aware caching for dataframe rows with async operations.

Public API:
    - TaskRow, UnitRow, ContactRow: Row models for type-safe extraction
    - ColumnDef, DataFrameSchema: Schema definition models
    - SchemaRegistry: Task-type to schema mapping
    - BASE_SCHEMA, UNIT_SCHEMA, CONTACT_SCHEMA: Built-in schemas
    - BaseExtractor, UnitExtractor, ContactExtractor: Task extractors
    - DataFrameBuilder, ProgressiveProjectBuilder, SectionDataFrameBuilder: DataFrame builders
    - DataFrameError and subclasses: Exception hierarchy
    - CustomFieldResolver, DefaultCustomFieldResolver: Dynamic field resolution
    - MockCustomFieldResolver, FailingResolver: Testing support
    - NameNormalizer: Field name normalization utility
    - LAZY_THRESHOLD: Default threshold for lazy evaluation (100 tasks)
    - CachedRow, DataFrameCacheIntegration: Cache integration (TDD-0008)
"""

from autom8_asana.dataframes.builders import (
    LAZY_THRESHOLD,
    DataFrameBuilder,
    ProgressiveProjectBuilder,
    SectionDataFrameBuilder,
)
from autom8_asana.dataframes.cache_integration import (
    CachedRow,
    DataFrameCacheIntegration,
)
from autom8_asana.dataframes.exceptions import (
    DataFrameError,
    ExtractionError,
    SchemaNotFoundError,
    SchemaVersionError,
    TypeCoercionError,
)
from autom8_asana.dataframes.extractors import (
    BaseExtractor,
    ContactExtractor,
    UnitExtractor,
)
from autom8_asana.dataframes.models.registry import SchemaRegistry, get_schema
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.models.task_row import ContactRow, TaskRow, UnitRow
from autom8_asana.dataframes.resolver import (
    CustomFieldResolver,
    DefaultCustomFieldResolver,
    FailingResolver,
    MockCustomFieldResolver,
    NameNormalizer,
)
from autom8_asana.dataframes.schemas.base import BASE_SCHEMA
from autom8_asana.dataframes.schemas.contact import CONTACT_SCHEMA
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA

__all__ = [
    # Constants
    "LAZY_THRESHOLD",
    # Exceptions
    "DataFrameError",
    "SchemaNotFoundError",
    "ExtractionError",
    "TypeCoercionError",
    "SchemaVersionError",
    # Models
    "ColumnDef",
    "DataFrameSchema",
    "TaskRow",
    "UnitRow",
    "ContactRow",
    # Registry
    "SchemaRegistry",
    "get_schema",
    # Schemas
    "BASE_SCHEMA",
    "UNIT_SCHEMA",
    "CONTACT_SCHEMA",
    # Extractors (TDD-0009 Phase 3)
    "BaseExtractor",
    "UnitExtractor",
    "ContactExtractor",
    # Builders (TDD-0009 Phase 4)
    "DataFrameBuilder",
    "ProgressiveProjectBuilder",
    "SectionDataFrameBuilder",
    # Resolver (TDD-0009.1)  # noqa: ERA001
    "CustomFieldResolver",
    "DefaultCustomFieldResolver",
    "MockCustomFieldResolver",
    "FailingResolver",
    "NameNormalizer",
    # Cache Integration (TDD-0008 Session 4 Phase 4)
    "CachedRow",
    "DataFrameCacheIntegration",
]
