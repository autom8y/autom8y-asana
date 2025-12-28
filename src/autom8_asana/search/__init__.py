"""Search interface for cached project frames.

Per TDD-search-interface: Provides efficient GID retrieval from cached
project DataFrames using Polars filter expressions.

Public API:
    - SearchService: Main search interface
    - SearchCriteria: Query specification model
    - SearchResult: Query result model
    - SearchHit: Single result model
    - FieldCondition: Single field condition model

Example:
    >>> from autom8_asana import AsanaClient
    >>>
    >>> client = AsanaClient()
    >>> result = await client.search.find_async(
    ...     "1143843662099250",
    ...     {"Office Phone": "555-1234", "Vertical": "Medical"}
    ... )
    >>> for hit in result.hits:
    ...     print(hit.gid, hit.name)
"""

from autom8_asana.search.models import (
    FieldCondition,
    SearchCriteria,
    SearchHit,
    SearchResult,
)
from autom8_asana.search.service import SearchService

__all__ = [
    "FieldCondition",
    "SearchCriteria",
    "SearchHit",
    "SearchResult",
    "SearchService",
]
