"""Query engine: composable predicate filtering for DataFrame cache.

Public API:
- QueryEngine: Orchestrates filtered row retrieval.
- PredicateCompiler: AST to pl.Expr compilation.
- Models: PredicateNode, Comparison, Op, RowsRequest, RowsResponse, etc.
- Errors: QueryEngineError hierarchy.
- Guards: QueryLimits, predicate_depth.
"""

from autom8_asana.query.aggregator import (
    AGG_COMPATIBILITY,
    AggregationCompiler,
    build_post_agg_schema,
    validate_alias_uniqueness,
)
from autom8_asana.query.compiler import PredicateCompiler, strip_section_predicates
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
    AggregationError,
    CoercionError,
    InvalidOperatorError,
    JoinError,
    QueryEngineError,
    QueryTooComplexError,
    UnknownFieldError,
    UnknownSectionError,
)
from autom8_asana.query.hierarchy import (
    ENTITY_RELATIONSHIPS,
    EntityRelationship,
    find_relationship,
    get_join_key,
    get_joinable_types,
)
from autom8_asana.query.join import JoinResult, JoinSpec, MAX_JOIN_DEPTH, execute_join
from autom8_asana.query.guards import QueryLimits, predicate_depth
from autom8_asana.query.models import (
    AggFunction,
    AggregateMeta,
    AggregateRequest,
    AggregateResponse,
    AggSpec,
    AndGroup,
    Comparison,
    NotGroup,
    Op,
    OrGroup,
    PredicateNode,
    RowsMeta,
    RowsRequest,
    RowsResponse,
)

__all__ = [
    "AGG_COMPATIBILITY",
    "AggFunction",
    "AggregateGroupLimitError",
    "AggregateMeta",
    "AggregateRequest",
    "AggregateResponse",
    "AggregationCompiler",
    "AggregationError",
    "AggSpec",
    "AndGroup",
    "CoercionError",
    "Comparison",
    "ENTITY_RELATIONSHIPS",
    "EntityRelationship",
    "InvalidOperatorError",
    "JoinError",
    "JoinResult",
    "JoinSpec",
    "MAX_JOIN_DEPTH",
    "NotGroup",
    "Op",
    "OrGroup",
    "PredicateCompiler",
    "PredicateNode",
    "QueryEngine",
    "QueryEngineError",
    "QueryLimits",
    "QueryTooComplexError",
    "RowsMeta",
    "RowsRequest",
    "RowsResponse",
    "UnknownFieldError",
    "UnknownSectionError",
    "build_post_agg_schema",
    "validate_alias_uniqueness",
    "execute_join",
    "find_relationship",
    "get_join_key",
    "get_joinable_types",
    "predicate_depth",
    "strip_section_predicates",
]
