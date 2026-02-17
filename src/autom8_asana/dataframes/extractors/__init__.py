"""Extractor package for schema-driven task field extraction.

Per TDD-0009 Phase 3: Provides extractors that transform Asana tasks
into typed TaskRow instances based on schema definitions.

Public API:
    - BaseExtractor: Abstract base with 12 base field extraction methods
    - DefaultExtractor: Default task extraction with 12 base fields
    - SchemaExtractor: Schema-driven generic extraction via dynamic Pydantic models
    - UnitExtractor: Unit task extraction with 23 fields
    - ContactExtractor: Contact task extraction with 21 fields

Example:
    >>> from autom8_asana.dataframes.extractors import UnitExtractor
    >>> from autom8_asana.dataframes.schemas import UNIT_SCHEMA
    >>> from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
    >>>
    >>> resolver = DefaultCustomFieldResolver()
    >>> resolver.build_index(task.custom_fields)
    >>> extractor = UnitExtractor(UNIT_SCHEMA, resolver)
    >>> row = extractor.extract(task)
    >>> row.mrr
    Decimal('5000')
"""

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.extractors.contact import ContactExtractor
from autom8_asana.dataframes.extractors.default import DefaultExtractor
from autom8_asana.dataframes.extractors.schema import SchemaExtractor
from autom8_asana.dataframes.extractors.unit import UnitExtractor

__all__ = [
    "BaseExtractor",
    "DefaultExtractor",
    "SchemaExtractor",
    "UnitExtractor",
    "ContactExtractor",
]
