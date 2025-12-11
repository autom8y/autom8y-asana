# TDD: Structured Dataframe Layer

## Metadata
- **TDD ID**: TDD-0009
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-09
- **Last Updated**: 2025-12-09
- **PRD Reference**: [PRD-0003](../requirements/PRD-0003-structured-dataframe-layer.md)
- **Related TDDs**:
  - [TDD-0008](TDD-0008-intelligent-caching.md) - Intelligent Caching (cache infrastructure)
  - [TDD-0001](TDD-0001-sdk-architecture.md) - SDK Architecture (foundation)
- **Related ADRs**:
  - [ADR-0027](../decisions/ADR-0027-dataframe-layer-migration-strategy.md) - Migration Strategy
  - [ADR-0028](../decisions/ADR-0028-polars-dataframe-library.md) - Polars DataFrame Library
  - [ADR-0029](../decisions/ADR-0029-task-subclass-strategy.md) - Task Subclass Strategy
  - [ADR-0030](../decisions/ADR-0030-custom-field-typing.md) - Custom Field Typing
  - [ADR-0031](../decisions/ADR-0031-lazy-eager-evaluation.md) - Lazy/Eager Evaluation
  - [ADR-0032](../decisions/ADR-0032-cache-granularity.md) - Cache Granularity
  - [ADR-0033](../decisions/ADR-0033-schema-enforcement.md) - Schema Enforcement

## Overview

This design introduces a Structured Dataframe Layer for the autom8_asana SDK that transforms Asana task hierarchies into typed Polars DataFrames. The layer provides schema-driven extraction with 32 typed columns (12 base + 11 Unit + 9 Contact), concurrent task processing, STRUC cache integration via TDD-0008, and a deprecated `struc()` wrapper for backward compatibility. The architecture uses schema-driven composition for extensibility while maintaining type safety through Pydantic models and Polars dtype enforcement.

## Requirements Summary

This design addresses [PRD-0003](../requirements/PRD-0003-structured-dataframe-layer.md) v2.0, which defines:

- **60 functional requirements** across model (FR-MODEL), project (FR-PROJECT), section (FR-SECTION), custom field (FR-CUSTOM), subclass (FR-SUBCLASS), cache (FR-CACHE), export (FR-EXPORT), compatibility (FR-COMPAT), and error handling (FR-ERROR) domains
- **40 non-functional requirements** covering performance (NFR-PERF), reliability (NFR-REL), compatibility (NFR-COMPAT), and observability (NFR-OBS)
- **MVP scope**: Unit (11 fields) and Contact (9 fields) task types plus 12 base fields
- **Key constraints**: Polars output, 20-30% performance improvement, TDD-0008 cache integration

Key requirements driving this design:

| Requirement | Summary | Design Impact |
|-------------|---------|---------------|
| FR-MODEL-001 | DataFrameSchema with typed columns | Schema dataclass with ColumnDef |
| FR-PROJECT-001 | Project.to_dataframe() method | Public API on Project class |
| FR-CACHE-001 | STRUC entry type caching | Cache integration module |
| FR-COMPAT-001 | struc() deprecated wrapper | Deprecation module |
| NFR-PERF-020 | Lazy evaluation for >100 tasks | Threshold-based mode selection |

## System Context

The Structured Dataframe Layer sits between SDK consumers and the existing SDK infrastructure, orchestrating task extraction through schema-driven extractors with caching support.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM CONTEXT                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌───────────────────────┐
                            │    SDK Consumers      │
                            │  (autom8, services)   │
                            └───────────┬───────────┘
                                        │
                           project.to_dataframe()
                           section.to_dataframe()
                           project.struc() [deprecated]
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         autom8_asana SDK                                     │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    Structured Dataframe Layer                          │ │
│  │                                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │ │
│  │  │   Schemas    │  │  Extractors  │  │   Builders   │                │ │
│  │  │  (registry)  │  │(type-specific)│  │(project/sect)│                │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │ │
│  │         │                 │                  │                        │ │
│  │         └─────────────────┼──────────────────┘                        │ │
│  │                           │                                           │ │
│  │                           ▼                                           │ │
│  │              ┌─────────────────────────┐                              │ │
│  │              │   Cache Integration     │                              │ │
│  │              │   (STRUC entry type)    │                              │ │
│  │              └───────────┬─────────────┘                              │ │
│  │                          │                                            │ │
│  └──────────────────────────┼────────────────────────────────────────────┘ │
│                             │                                              │
│  ┌──────────────────────────┼────────────────────────────────────────────┐ │
│  │                          │                                            │ │
│  │  ┌──────────────┐   ┌────┴─────┐   ┌──────────────┐                  │ │
│  │  │ Task Models  │   │  Cache   │   │  LogProvider │                  │ │
│  │  │ (AsanaTask)  │   │ Provider │   │  (events)    │                  │ │
│  │  └──────────────┘   └──────────┘   └──────────────┘                  │ │
│  │                         TDD-0008                                      │ │
│  │                                                                        │ │
│  │                    Existing SDK Infrastructure                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │    Infrastructure     │
                            │  (Redis, Asana API)   │
                            └───────────────────────┘
```

### Integration Points

| Integration Point | Interface | Direction | Notes |
|-------------------|-----------|-----------|-------|
| `AsanaTask` model | Pydantic model | Read | Source data for extraction |
| `Project` class | Method extension | Extend | Adds `to_dataframe()` |
| `Section` class | Method extension | Extend | Adds `to_dataframe()` |
| `CacheProvider` (TDD-0008) | Protocol | Read/Write | STRUC entry caching |
| `LogProvider` | Protocol | Write | Extraction events/metrics |

## Design

### Package Structure

```
src/autom8_asana/
├── dataframes/
│   ├── __init__.py              # Public API exports
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task_row.py          # TaskRow, UnitRow, ContactRow
│   │   ├── schema.py            # ColumnDef, DataFrameSchema
│   │   ├── registry.py          # SchemaRegistry singleton
│   │   └── custom_fields.py     # Custom field GID constants
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base.py              # BASE_SCHEMA (12 columns)
│   │   ├── unit.py              # UNIT_SCHEMA (23 columns)
│   │   └── contact.py           # CONTACT_SCHEMA (21 columns)
│   │
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseExtractor (abstract)
│   │   ├── unit.py              # UnitExtractor (derived fields)
│   │   └── contact.py           # ContactExtractor
│   │
│   ├── builders/
│   │   ├── __init__.py
│   │   ├── base.py              # DataFrameBuilder (abstract)
│   │   ├── section.py           # SectionDataFrameBuilder
│   │   └── project.py           # ProjectDataFrameBuilder
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   ├── parquet.py           # Parquet export utilities
│   │   ├── csv.py               # CSV export utilities
│   │   └── json.py              # JSON export utilities
│   │
│   ├── cache_integration.py     # Bridge to TDD-0008 STRUC cache
│   ├── coercion.py              # TypeCoercer for schema enforcement
│   ├── exceptions.py            # DataFrameError hierarchy
│   └── deprecation.py           # struc() wrapper
│
└── ... (existing SDK structure)
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMPONENT ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              PUBLIC API                                      │
│                                                                              │
│    Project.to_dataframe()          Section.to_dataframe()                   │
│    Project.to_dataframe_async()    Section.to_dataframe_async()             │
│    Project.struc() [deprecated]                                              │
│                                                                              │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BUILDERS                                        │
│                                                                              │
│  ┌────────────────────────┐       ┌────────────────────────┐                │
│  │ ProjectDataFrameBuilder│       │ SectionDataFrameBuilder│                │
│  │                        │       │                        │                │
│  │ - project_gid          │       │ - section_gid          │                │
│  │ - sections filter      │       │ - project_gid          │                │
│  │ - concurrent extract   │       │ - concurrent extract   │                │
│  │ - lazy/eager selection │       │ - lazy/eager selection │                │
│  └────────────┬───────────┘       └───────────┬────────────┘                │
│               │                               │                              │
│               └───────────┬───────────────────┘                              │
│                           │                                                  │
│                           ▼                                                  │
│               ┌───────────────────────┐                                      │
│               │   DataFrameBuilder    │ (abstract base)                      │
│               │   (base.py)           │                                      │
│               └───────────┬───────────┘                                      │
│                           │                                                  │
└───────────────────────────┼──────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐
│  EXTRACTORS   │  │   SCHEMAS     │  │   CACHE INTEGRATION   │
│               │  │               │  │                       │
│ BaseExtractor │  │ SchemaRegistry│  │ DataFrameCacheIntegr. │
│      │        │  │       │       │  │         │             │
│      ├──Unit  │  │  ┌────┴────┐  │  │         ▼             │
│      │  Extr  │  │  │         │  │  │  CacheProvider        │
│      │        │  │  ▼         ▼  │  │  (TDD-0008)           │
│      └──Cont  │  │ UNIT    CONTACT│ │                       │
│         Extr  │  │ SCHEMA  SCHEMA │  │  EntryType.STRUC     │
│               │  │               │  │                       │
└───────┬───────┘  └───────────────┘  └───────────────────────┘
        │
        ▼
┌───────────────┐
│    MODELS     │
│               │
│ TaskRow       │
│   │           │
│   ├── UnitRow │
│   │           │
│   └── Contact │
│       Row     │
│               │
│ ColumnDef     │
│ DataFrameSchema│
└───────────────┘
```

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `TaskRow` | Type-safe Pydantic model for extracted row | `models/task_row.py` |
| `UnitRow`, `ContactRow` | Type-specific row extensions | `models/task_row.py` |
| `ColumnDef` | Single column definition (name, dtype, source) | `models/schema.py` |
| `DataFrameSchema` | Complete schema with validation | `models/schema.py` |
| `SchemaRegistry` | Task-type to schema mapping singleton | `models/registry.py` |
| `BaseExtractor` | Abstract extractor with shared logic | `extractors/base.py` |
| `UnitExtractor` | Unit-specific extraction with derived fields | `extractors/unit.py` |
| `ContactExtractor` | Contact-specific extraction | `extractors/contact.py` |
| `DataFrameBuilder` | Abstract builder with lazy/eager selection | `builders/base.py` |
| `SectionDataFrameBuilder` | Section-scoped extraction | `builders/section.py` |
| `ProjectDataFrameBuilder` | Project-scoped with section support | `builders/project.py` |
| `DataFrameCacheIntegration` | Bridge to TDD-0008 STRUC cache | `cache_integration.py` |
| `TypeCoercer` | Schema enforcement with coercion | `coercion.py` |

### Data Model

#### ColumnDef and DataFrameSchema

```python
# autom8_asana/dataframes/models/schema.py

from dataclasses import dataclass, field
from typing import Any, Callable
import polars as pl


@dataclass(frozen=True)
class ColumnDef:
    """Definition of a single DataFrame column.

    Per FR-MODEL-001: Type-safe column definitions with Polars dtypes.

    Attributes:
        name: Column name in output DataFrame
        dtype: Polars data type for the column
        nullable: Whether column allows null values
        source: Attribute path or custom field GID for extraction
        extractor: Optional custom extraction function
        description: Human-readable description
    """
    name: str
    dtype: pl.DataType
    nullable: bool = True
    source: str | None = None
    extractor: Callable[[Any], Any] | None = None
    description: str | None = None


@dataclass
class DataFrameSchema:
    """Schema definition for typed DataFrame generation.

    Per FR-MODEL-001-006: Complete schema with column definitions,
    versioning, and export capabilities.

    Attributes:
        name: Schema identifier
        task_type: Task type this schema applies to
        columns: List of column definitions
        version: Schema version for cache compatibility
    """
    name: str
    task_type: str
    columns: list[ColumnDef]
    version: str = "1.0.0"

    def get_column(self, name: str) -> ColumnDef | None:
        """Get column definition by name."""
        return next((c for c in self.columns if c.name == name), None)

    def to_polars_schema(self) -> dict[str, pl.DataType]:
        """Convert to Polars schema dict for DataFrame construction."""
        return {col.name: col.dtype for col in self.columns}

    def column_names(self) -> list[str]:
        """Return ordered list of column names."""
        return [col.name for col in self.columns]

    def to_dict(self) -> dict[str, Any]:
        """Export schema as JSON-serializable dict (FR-MODEL-006)."""
        return {
            "name": self.name,
            "task_type": self.task_type,
            "version": self.version,
            "columns": [
                {
                    "name": col.name,
                    "dtype": str(col.dtype),
                    "nullable": col.nullable,
                    "source": col.source,
                    "description": col.description,
                }
                for col in self.columns
            ],
        }

    def validate_row(self, row: dict[str, Any]) -> list[str]:
        """Validate row against schema, return list of errors."""
        errors = []
        for col in self.columns:
            value = row.get(col.name)
            if value is None and not col.nullable:
                errors.append(f"{col.name}: required field is null")
        return errors
```

#### SchemaRegistry Singleton

```python
# autom8_asana/dataframes/models/registry.py

import threading
from typing import ClassVar

from .schema import DataFrameSchema
from ..exceptions import SchemaNotFoundError


class SchemaRegistry:
    """Singleton registry for task-type to schema mapping.

    Per FR-MODEL-030-033: Singleton with lazy initialization
    and runtime registration support.

    Usage:
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema("Unit")
    """
    _instance: ClassVar["SchemaRegistry | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls) -> "SchemaRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._schemas = {}
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SchemaRegistry":
        """Get or create singleton instance."""
        return cls()

    def _ensure_initialized(self) -> None:
        """Lazy initialization of built-in schemas."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            from ..schemas.base import BASE_SCHEMA
            from ..schemas.unit import UNIT_SCHEMA
            from ..schemas.contact import CONTACT_SCHEMA

            self._schemas["*"] = BASE_SCHEMA
            self._schemas["Unit"] = UNIT_SCHEMA
            self._schemas["Contact"] = CONTACT_SCHEMA
            self._initialized = True

    def get_schema(self, task_type: str) -> DataFrameSchema:
        """Get schema for task type (FR-MODEL-004).

        Args:
            task_type: Task type identifier (e.g., "Unit", "Contact")

        Returns:
            DataFrameSchema for the task type

        Raises:
            SchemaNotFoundError: If no schema registered for type
        """
        self._ensure_initialized()

        if task_type in self._schemas:
            return self._schemas[task_type]

        # Fall back to base schema for unknown types
        if "*" in self._schemas:
            return self._schemas["*"]

        raise SchemaNotFoundError(task_type)

    def register(self, task_type: str, schema: DataFrameSchema) -> None:
        """Register schema for task type (FR-MODEL-031, post-MVP).

        Args:
            task_type: Task type identifier
            schema: Schema to register

        Raises:
            ValueError: If schema conflicts with existing registration
        """
        self._ensure_initialized()

        if task_type in self._schemas:
            existing = self._schemas[task_type]
            if existing.version != schema.version:
                raise ValueError(
                    f"Schema conflict for {task_type}: "
                    f"existing v{existing.version} vs new v{schema.version}"
                )

        self._schemas[task_type] = schema

    def has_schema(self, task_type: str) -> bool:
        """Check if schema exists for task type."""
        self._ensure_initialized()
        return task_type in self._schemas

    def list_task_types(self) -> list[str]:
        """List all registered task types."""
        self._ensure_initialized()
        return [k for k in self._schemas.keys() if k != "*"]
```

#### TaskRow Pydantic Models

```python
# autom8_asana/dataframes/models/task_row.py

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskRow(BaseModel):
    """Base row model for all task types.

    Per FR-MODEL-020-025: Pydantic model with typed fields,
    frozen for immutability, and to_dict() for Polars compatibility.

    Attributes:
        gid: Task identifier (non-nullable)
        name: Task name (non-nullable)
        type: Task type discriminator (non-nullable)
        date: Primary date field
        created: Task creation timestamp (non-nullable)
        due_on: Due date
        is_completed: Completion status (non-nullable)
        completed_at: Completion timestamp
        url: Asana task URL (non-nullable)
        last_modified: Last modification timestamp (non-nullable)
        section: Section name
        tags: List of tag names (non-nullable, defaults empty)
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Base fields (12) - FR-MODEL-021
    gid: str
    name: str
    type: str
    date: date | None = None
    created: datetime
    due_on: date | None = None
    is_completed: bool
    completed_at: datetime | None = None
    url: str
    last_modified: datetime
    section: str | None = None
    tags: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for Polars compatibility (FR-MODEL-024).

        Returns:
            Dict with all fields, suitable for pl.DataFrame construction
        """
        return self.model_dump()


class UnitRow(TaskRow):
    """Unit-specific row with 11 additional fields.

    Per FR-SUBCLASS-001: Extends base with Unit-specific fields
    including direct custom fields and derived fields.
    """
    type: str = "Unit"

    # Direct custom fields (5)
    mrr: Decimal | None = None
    weekly_ad_spend: Decimal | None = None
    products: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    discount: Decimal | None = None

    # Derived fields (6)
    office: str | None = None
    office_phone: str | None = None
    vertical: str | None = None
    vertical_id: str | None = None
    specialty: str | None = None
    max_pipeline_stage: str | None = None


class ContactRow(TaskRow):
    """Contact-specific row with 9 additional fields.

    Per FR-SUBCLASS-002: Extends base with Contact-specific fields.
    """
    type: str = "Contact"

    # Contact fields (9)
    full_name: str | None = None
    nickname: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    position: str | None = None
    employee_id: str | None = None
    contact_url: str | None = None
    time_zone: str | None = None
    city: str | None = None
```

#### Custom Field Constants

```python
# autom8_asana/dataframes/models/custom_fields.py

"""Custom field GID constants for MVP task types.

Per ADR-0030: Static GIDs hardcoded for MVP. Post-MVP supports
configurable field mappings.

These GIDs are stable identifiers in Asana. Names can change;
GIDs cannot. Each constant documents the current field name.

NOTE: Actual GIDs must be populated before implementation.
These are placeholder values for design documentation.
"""

# === Unit Custom Fields ===

# MRR (Monthly Recurring Revenue)
# Type: number
MRR_GID = "PLACEHOLDER_MRR_GID"

# Weekly Ad Spend
# Type: number
WEEKLY_AD_SPEND_GID = "PLACEHOLDER_WEEKLY_AD_SPEND_GID"

# Products
# Type: multi_enum
PRODUCTS_GID = "PLACEHOLDER_PRODUCTS_GID"

# Languages
# Type: multi_enum
LANGUAGES_GID = "PLACEHOLDER_LANGUAGES_GID"

# Discount
# Type: number (percentage)
DISCOUNT_GID = "PLACEHOLDER_DISCOUNT_GID"

# Vertical
# Type: enum
VERTICAL_GID = "PLACEHOLDER_VERTICAL_GID"

# Specialty
# Type: text
SPECIALTY_GID = "PLACEHOLDER_SPECIALTY_GID"


# === Contact Custom Fields ===

# Full Name
# Type: text
FULL_NAME_GID = "PLACEHOLDER_FULL_NAME_GID"

# Nickname
# Type: text
NICKNAME_GID = "PLACEHOLDER_NICKNAME_GID"

# Contact Phone
# Type: text
CONTACT_PHONE_GID = "PLACEHOLDER_CONTACT_PHONE_GID"

# Contact Email
# Type: text
CONTACT_EMAIL_GID = "PLACEHOLDER_CONTACT_EMAIL_GID"

# Position
# Type: text
POSITION_GID = "PLACEHOLDER_POSITION_GID"

# Employee ID
# Type: text
EMPLOYEE_ID_GID = "PLACEHOLDER_EMPLOYEE_ID_GID"

# Contact URL
# Type: text
CONTACT_URL_GID = "PLACEHOLDER_CONTACT_URL_GID"

# Time Zone
# Type: enum or text
TIME_ZONE_GID = "PLACEHOLDER_TIME_ZONE_GID"

# City
# Type: text
CITY_GID = "PLACEHOLDER_CITY_GID"
```

### API Contracts

#### Project.to_dataframe()

```python
# Extension to existing Project class

import polars as pl

class Project:
    def to_dataframe(
        self,
        task_type: str | None = None,
        concurrency: int = 10,
        use_cache: bool = True,
        sections: list[str] | None = None,
        completed: bool | None = None,
        since: date | None = None,
        lazy: bool | None = None,
        incremental: bool = False,
    ) -> pl.DataFrame:
        """Generate typed DataFrame from project tasks.

        Per FR-PROJECT-001-006: Primary API for project-level extraction.

        Args:
            task_type: Filter to specific type (Unit, Contact). None = all types.
            concurrency: Max concurrent extraction workers (default 10).
            use_cache: Whether to use STRUC cache (default True).
            sections: Filter by section names (FR-PROJECT-010).
            completed: Filter by completion status (FR-PROJECT-011).
            since: Filter by modified_at >= since (FR-PROJECT-012).
            lazy: Evaluation mode override. None = auto (100-task threshold).
            incremental: Use story-based incremental refresh (FR-CACHE-024).

        Returns:
            Polars DataFrame with schema-defined columns.

        Raises:
            SchemaNotFoundError: If task_type has no registered schema.
            DataFrameError: If extraction fails.

        Example:
            >>> df = project.to_dataframe(task_type="Unit")
            >>> df.schema
            {'gid': Utf8, 'name': Utf8, 'mrr': Decimal, ...}
        """
        ...

    async def to_dataframe_async(
        self,
        task_type: str | None = None,
        concurrency: int = 10,
        use_cache: bool = True,
        **kwargs,
    ) -> pl.DataFrame:
        """Async variant of to_dataframe (FR-PROJECT-006)."""
        ...

    def estimate_dataframe_size(self) -> int:
        """Return task count without full extraction (FR-PROJECT-013).

        Returns:
            Number of tasks that would be included in DataFrame.
        """
        ...
```

#### Section.to_dataframe()

```python
# Extension to existing Section class

class Section:
    def to_dataframe(
        self,
        task_type: str | None = None,
        concurrency: int = 10,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Generate DataFrame from section tasks.

        Per FR-SECTION-001-005: Section-scoped extraction with
        project context for cache keys.

        Args:
            task_type: Filter to specific type. None = all types.
            concurrency: Max concurrent workers.
            use_cache: Whether to use STRUC cache.
            lazy: Evaluation mode override.

        Returns:
            Polars DataFrame with schema-defined columns.
        """
        ...

    async def to_dataframe_async(
        self,
        task_type: str | None = None,
        concurrency: int = 10,
        use_cache: bool = True,
        **kwargs,
    ) -> pl.DataFrame:
        """Async variant of to_dataframe."""
        ...
```

#### struc() Deprecation Wrapper

```python
# autom8_asana/dataframes/deprecation.py

import warnings
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def create_struc_wrapper(to_dataframe_method):
    """Create deprecated struc() wrapper for backward compatibility.

    Per ADR-0027 and FR-COMPAT-001-008: Wrapper that delegates
    to to_dataframe() and converts to pandas.
    """

    def struc(
        self,
        task_type: str | None = None,
        concurrency: int = 10,
        use_cache: bool = True,
    ) -> "pd.DataFrame":
        """Generate structured dataframe from project tasks.

        .. deprecated:: 1.0.0
            Use `to_dataframe()` instead. `struc()` will be removed
            in version 2.0.0.

        This method is a compatibility wrapper that calls `to_dataframe()`
        and converts the result to pandas.

        Args:
            task_type: Filter to specific task type
            concurrency: Number of concurrent extraction workers
            use_cache: Whether to use cached struc data

        Returns:
            pandas.DataFrame with extracted task fields
        """
        # Emit deprecation warning (FR-COMPAT-002)
        warnings.warn(
            "struc() is deprecated and will be removed in version 2.0.0. "
            "Use to_dataframe() instead. Migration guide: "
            "https://docs.autom8.dev/migration/struc-to-dataframe",
            DeprecationWarning,
            stacklevel=2,
        )

        # Log caller location for migration tracking (FR-COMPAT-006)
        caller = traceback.extract_stack()[-2]
        self._log.info(
            "struc_deprecated_call",
            caller_file=caller.filename,
            caller_line=caller.lineno,
            caller_function=caller.name,
        )

        # Delegate to new implementation
        polars_df = to_dataframe_method(
            self,
            task_type=task_type,
            concurrency=concurrency,
            use_cache=use_cache,
        )

        # Convert to pandas for backward compatibility (FR-EXPORT-004)
        return polars_df.to_pandas()

    return struc
```

### Data Flow

#### Extraction Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTRACTION PIPELINE FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

  Client Code
       │
       │ project.to_dataframe(task_type="Unit")
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. RESOLVE SCHEMA                                                            │
│                                                                              │
│    SchemaRegistry.get_schema("Unit") ──► UNIT_SCHEMA (23 columns)           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 2. CREATE BUILDER                                                            │
│                                                                              │
│    ProjectDataFrameBuilder(                                                  │
│        project_gid=self.gid,                                                 │
│        schema=UNIT_SCHEMA,                                                   │
│        concurrency=10,                                                       │
│        use_cache=True,                                                       │
│        lazy_threshold=100,                                                   │
│    )                                                                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 3. LOAD TASKS                                                                │
│                                                                              │
│    tasks = self.get_tasks(task_type="Unit")  # From existing SDK            │
│    task_count = len(tasks)  # e.g., 500                                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 4. DETERMINE EVALUATION MODE                                                 │
│                                                                              │
│    if lazy is not None:                                                      │
│        use_lazy = lazy                                                       │
│    else:                                                                     │
│        use_lazy = task_count > 100  # True for 500 tasks                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 5. CONCURRENT EXTRACTION (with semaphore limiting)                           │
│                                                                              │
│    ┌────────────────────────────────────────────────────────────────────┐   │
│    │  For each task (up to 10 concurrent):                              │   │
│    │                                                                    │   │
│    │  ┌──────────────┐                                                 │   │
│    │  │ Cache Check  │ cache.get_cached_row(task.gid, project_gid)     │   │
│    │  └──────┬───────┘                                                 │   │
│    │         │                                                          │   │
│    │    ┌────┴────┐                                                    │   │
│    │    │         │                                                    │   │
│    │   HIT      MISS                                                   │   │
│    │    │         │                                                    │   │
│    │    ▼         ▼                                                    │   │
│    │  Return   ┌──────────────┐                                        │   │
│    │  cached   │ Extract      │ UnitExtractor.extract(task)            │   │
│    │  row      └──────┬───────┘                                        │   │
│    │                  │                                                 │   │
│    │                  ▼                                                 │   │
│    │           ┌──────────────┐                                        │   │
│    │           │ Cache Write  │ cache.cache_row(gid, project_gid, row) │   │
│    │           └──────┬───────┘                                        │   │
│    │                  │                                                 │   │
│    │                  ▼                                                 │   │
│    │           Return extracted row                                     │   │
│    │                                                                    │   │
│    └────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
       │
       │ Collect all rows: list[UnitRow]
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 6. BUILD DATAFRAME                                                           │
│                                                                              │
│    if use_lazy:                                                              │
│        lf = pl.LazyFrame([row.to_dict() for row in rows], schema=schema)    │
│        df = lf.collect()  # Query optimization applied                       │
│    else:                                                                     │
│        df = pl.DataFrame([row.to_dict() for row in rows], schema=schema)    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
       │
       │ Return pl.DataFrame
       ▼
  Client Code
```

#### Type Coercion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TYPE COERCION FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

  Raw Value from Task
       │
       │ e.g., custom_field.number_value = "5000.00"
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TypeCoercer.coerce(value, pl.Decimal, "mrr", task_gid)                       │
│                                                                              │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │ 1. Check if value is None                                           │  │
│    │    └── If None → Return None                                        │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│                           │                                                  │
│                           ▼                                                  │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │ 2. Attempt coercion to target type                                  │  │
│    │    └── Decimal("5000.00") → Decimal('5000.00')                      │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│                           │                                                  │
│                      ┌────┴────┐                                            │
│                      │         │                                            │
│                   SUCCESS    FAILURE                                        │
│                      │         │                                            │
│                      ▼         ▼                                            │
│               Return       Log Warning                                       │
│               coerced      Return None                                       │
│               value                                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| DataFrame library | Polars | 10-100x performance, native lazy eval, strict typing | [ADR-0028](../decisions/ADR-0028-polars-dataframe-library.md) |
| Task subclass approach | Schema-driven composition | Extensibility without class explosion | [ADR-0029](../decisions/ADR-0029-task-subclass-strategy.md) |
| Custom field typing | Static GIDs (MVP) | Type safety, IDE support | [ADR-0030](../decisions/ADR-0030-custom-field-typing.md) |
| Evaluation mode | Threshold-based (100 tasks) | Balance performance vs debugging | [ADR-0031](../decisions/ADR-0031-lazy-eager-evaluation.md) |
| Cache granularity | Per-task with project context | Fine-grained invalidation, multi-homed support | [ADR-0032](../decisions/ADR-0032-cache-granularity.md) |
| Schema enforcement | Strict Polars dtype with logged fallbacks | Type safety with robustness | [ADR-0033](../decisions/ADR-0033-schema-enforcement.md) |
| Migration strategy | Big-bang with interface evolution | Clean cutover, struc() wrapper | [ADR-0027](../decisions/ADR-0027-dataframe-layer-migration-strategy.md) |

## Complexity Assessment

**Level**: SERVICE

**Justification**:

This feature adds significant complexity to the SDK but remains within the SERVICE level:

1. **Multiple interacting components**: SchemaRegistry, extractors, builders, cache integration, coercion
2. **Configuration complexity**: Per-type schemas, lazy thresholds, concurrency settings
3. **Integration requirements**: TDD-0008 cache, LogProvider, existing task models
4. **Async/concurrent processing**: Semaphore-limited concurrent extraction
5. **Type system complexity**: Polars dtypes, Pydantic models, schema inheritance

**Not PLATFORM because**:
- Single SDK boundary (no multi-service orchestration)
- No infrastructure provisioning logic
- Cache and storage are external dependencies, not managed by this layer
- No deployment coordination required

## Implementation Plan

### Phase 1: Core Models (Session 6, ~3 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `ColumnDef` dataclass | None | 0.5h |
| `DataFrameSchema` class with validation | ColumnDef | 1h |
| `TaskRow` base Pydantic model | None | 0.5h |
| `UnitRow`, `ContactRow` extensions | TaskRow | 0.5h |
| Unit tests for models | All models | 0.5h |

**Exit Criteria**: All model classes pass mypy strict; unit tests cover validation and serialization.

### Phase 2: Schema Definitions (Session 6, ~2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `BASE_SCHEMA` (12 columns) | DataFrameSchema | 0.5h |
| `UNIT_SCHEMA` (23 columns) | BASE_SCHEMA | 0.5h |
| `CONTACT_SCHEMA` (21 columns) | BASE_SCHEMA | 0.5h |
| `SchemaRegistry` singleton | Schemas | 0.5h |

**Exit Criteria**: Schemas registered; registry returns correct schema per type.

### Phase 3: Extractors (Session 6-7, ~4 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `BaseExtractor` with 12 base field methods | Schema, TaskRow | 1.5h |
| `TypeCoercer` for schema enforcement | ColumnDef | 0.5h |
| `UnitExtractor` with derived field logic | BaseExtractor | 1h |
| `ContactExtractor` | BaseExtractor | 0.5h |
| Unit tests for extractors | Extractors | 0.5h |

**Exit Criteria**: Extractors correctly transform mock tasks to typed rows.

### Phase 4: Builders (Session 7, ~4 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `DataFrameBuilder` abstract base | Extractors, Schema | 1h |
| Lazy/eager evaluation logic | Builder base | 0.5h |
| `SectionDataFrameBuilder` | Builder base | 1h |
| `ProjectDataFrameBuilder` | Builder base | 1h |
| Unit tests for builders | Builders | 0.5h |

**Exit Criteria**: Builders produce correct DataFrames; lazy/eager threshold works.

### Phase 5: Cache Integration (Session 7, ~2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `DataFrameCacheIntegration` class | TDD-0008 CacheProvider | 1h |
| STRUC entry type handling | CacheEntry | 0.5h |
| Unit tests with mocked CacheProvider | Cache integration | 0.5h |

**Exit Criteria**: Cache hits return cached rows; misses trigger extraction and caching.

### Phase 6: API Surface (Session 7, ~2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `Project.to_dataframe()` method | Builders | 0.5h |
| `Project.to_dataframe_async()` method | Builders | 0.5h |
| `Section.to_dataframe()` methods | Builders | 0.5h |
| `struc()` deprecation wrapper | to_dataframe | 0.5h |

**Exit Criteria**: Public API works; deprecation warnings emit correctly.

### Phase 7: Integration Testing (Session 7, ~3 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| End-to-end tests with mock tasks | All components | 1.5h |
| Performance benchmarks | Full implementation | 0.5h |
| Documentation and examples | All | 1h |

**Exit Criteria**: All integration tests pass; benchmarks meet NFR targets.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Custom field GIDs unknown | High | High | Document as open question; use placeholders in design; GIDs must be provided before implementation |
| Polars API changes | Medium | Low | Pin Polars version >= 0.20.0; abstract Polars usage behind internal interface |
| Performance regression vs legacy | Medium | Medium | Benchmark early in Phase 7; profile critical paths; optimize hot spots |
| Derived field logic complexity | Medium | Medium | Analyze legacy struc() implementation; extract logic to separate module; thorough unit testing |
| Schema versioning conflicts | Medium | Low | Include version in cache key; cache migration logic if schema changes |
| Concurrent extraction race conditions | Medium | Low | Use asyncio semaphore; thread-safe cache integration |

## Observability

### Metrics

All metrics emitted via `LogProvider.log()` with structured data:

| Metric | Type | Description |
|--------|------|-------------|
| `dataframe_extraction_time_ms` | Histogram | Total time from to_dataframe() call to return |
| `dataframe_row_count` | Counter | Number of rows extracted |
| `dataframe_cache_hit_rate` | Gauge | Percentage of tasks served from STRUC cache |
| `dataframe_cache_hits` | Counter | Number of STRUC cache hits |
| `dataframe_cache_misses` | Counter | Number of STRUC cache misses |
| `dataframe_extraction_errors` | Counter | Number of task extraction failures |
| `dataframe_coercion_failures` | Counter | Number of type coercion failures (by field) |
| `dataframe_lazy_evaluations` | Counter | Number of lazy evaluation paths taken |
| `dataframe_eager_evaluations` | Counter | Number of eager evaluation paths taken |

### Logging

| Level | Events |
|-------|--------|
| DEBUG | Per-task extraction start/complete, cache hit/miss, coercion attempt |
| INFO | DataFrame build started, DataFrame build completed (with row count, duration), struc() deprecated call |
| WARNING | Type coercion failure (with field, expected, actual), cache write failure |
| ERROR | Extraction failure (with task GID, error), schema not found |

### Log Examples

```python
# INFO: Build started
logger.info(
    "dataframe_build_started",
    project_gid="123456",
    task_type="Unit",
    estimated_count=500,
    use_cache=True,
    lazy_mode=True,
)

# DEBUG: Cache hit
logger.debug(
    "dataframe_cache_hit",
    task_gid="789012",
    project_gid="123456",
)

# WARNING: Coercion failure
logger.warning(
    "dataframe_coercion_failed",
    task_gid="789012",
    field="mrr",
    expected_type="Decimal",
    actual_type="str",
    actual_value="N/A",
)

# INFO: Build completed
logger.info(
    "dataframe_build_completed",
    project_gid="123456",
    row_count=500,
    duration_ms=2500,
    cache_hit_rate=0.85,
    coercion_warnings=3,
)
```

### Alerting Triggers

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Extraction time spike | p95 > 2x baseline for 5 min | Alert team |
| Error rate increase | > 1% extraction failures for 5 min | Alert team |
| Cache hit rate drop | < 50% for 15 min | Investigate cache health |
| Coercion failure spike | > 5% of fields for 15 min | Review data quality |

## Testing Strategy

### Unit Testing (Target: 90% coverage)

- **Models**: TaskRow validation, serialization, to_dict()
- **Schema**: ColumnDef creation, DataFrameSchema to_polars_schema(), validation
- **Registry**: Singleton behavior, schema registration, get_schema()
- **Extractors**: Base field extraction, custom field extraction, type coercion
- **Builders**: Lazy/eager selection, row collection, DataFrame construction
- **Coercion**: Each type coercion rule, failure handling, warning logging

### Integration Testing (Target: 80% coverage)

- **End-to-end extraction**: Mock tasks through full pipeline to DataFrame
- **Cache integration**: Hit/miss flows with mocked CacheProvider
- **Concurrent extraction**: Multiple tasks with semaphore limiting
- **Lazy vs eager**: Both paths produce identical results
- **Deprecation wrapper**: struc() produces pandas DataFrame with warning

### Performance Testing

| Scenario | Target | Measurement |
|----------|--------|-------------|
| 100 tasks, cold cache | < 5s | Time to DataFrame |
| 100 tasks, warm cache | < 1s | Time to DataFrame |
| 1000 tasks, cold cache | < 30s | Time to DataFrame |
| 1000 tasks, warm cache | < 5s | Time to DataFrame |
| Memory per 1000 tasks | < 100MB | Peak RSS during extraction |
| Cache hit improvement | >= 50% reduction | Warm vs cold extraction time |

### Security Testing

- No custom field GIDs in logs (truncate values)
- No task content in error messages
- Cache keys do not expose sensitive data

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Exact Unit custom field GIDs | autom8 team | Before Phase 3 | Required for schema definition and UnitExtractor |
| Exact Contact custom field GIDs | autom8 team | Before Phase 3 | Required for schema definition and ContactExtractor |
| Derived field logic for `office`, `vertical_id` | autom8 team | Before Phase 3 | Need legacy struc() analysis or documentation |
| Derived field logic for `max_pipeline_stage` | autom8 team | Before Phase 3 | May depend on UnitHolder model |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-09 | Architect | Initial design |
