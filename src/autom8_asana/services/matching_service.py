"""Matching service layer for the matching query API.

Orchestrates:
1. Fetch Business DataFrame from cache (no direct Asana API calls).
2. Convert DataFrame rows to Candidate objects.
3. Apply blocking rules to prune candidates before scoring.
4. Run the MatchingEngine against pruned candidates.
5. Project MatchResult to API response models (hiding internals).

Per ADR constraint: Must NOT make direct Asana API calls during matching.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from autom8y_api_schemas import OfficePhone
from autom8y_log import get_logger

from autom8_asana.api.routes.matching_models import (
    MatchCandidate,
    MatchFieldComparison,
    MatchingQueryResponse,
)
from autom8_asana.models.business.matching import (
    Candidate,
    CompositeBlockingRule,
    MatchingConfig,
    MatchingEngine,
    MatchResult,
)
from autom8_asana.models.business.seeder import BusinessData

if TYPE_CHECKING:
    import polars as pl

logger = get_logger(__name__)


class MatchingService:
    """Service layer bridging the matching engine to the API.

    Attributes:
        _engine: Probabilistic matching engine.
        _blocking_rule: Composite blocking rule for candidate pruning.
    """

    def __init__(
        self,
        config: MatchingConfig | None = None,
        engine: MatchingEngine | None = None,
    ) -> None:
        """Initialize matching service.

        Args:
            config: Optional matching config override.
            engine: Optional pre-built engine (for testing). Takes precedence over config.
        """
        self._engine = engine or MatchingEngine(config=config)
        self._blocking_rule = CompositeBlockingRule()

    @property
    def config(self) -> MatchingConfig:
        """Get the engine's matching config."""
        return self._engine.config

    def query(
        self,
        *,
        name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        domain: str | None = None,
        dataframe: pl.DataFrame,
        limit: int = 10,
        threshold: float | None = None,
    ) -> MatchingQueryResponse:
        """Execute a matching query against cached business data.

        Args:
            name: Business name.
            phone: Business phone.
            email: Business email.
            domain: Website domain.
            dataframe: Polars DataFrame of business records from cache.
            limit: Maximum results to return.
            threshold: Minimum score; defaults to engine config.

        Returns:
            MatchingQueryResponse with scored candidates.
        """
        start = time.monotonic()
        effective_threshold = (
            threshold if threshold is not None else self._engine.config.match_threshold
        )

        # Build query object
        query_data = BusinessData(
            name=name or "",
            phone=OfficePhone(phone) if phone else None,
            email=email,
            domain=domain,
        )

        # Convert DataFrame rows to Candidate objects
        candidates = self._dataframe_to_candidates(dataframe)
        total_candidates = len(candidates)

        logger.info(
            "matching_query_start",
            extra={
                "total_candidates": total_candidates,
                "has_name": name is not None,
                "has_phone": phone is not None,
                "has_email": email is not None,
                "has_domain": domain is not None,
            },
        )

        # Apply blocking rules to prune candidate space
        pruned = self._blocking_rule.filter_candidates(query_data, candidates)
        pruned_count = len(pruned)

        logger.debug(
            "matching_blocking_complete",
            extra={
                "total_candidates": total_candidates,
                "pruned_candidates": pruned_count,
                "pruned_pct": round((1 - pruned_count / total_candidates) * 100, 1)
                if total_candidates > 0
                else 0,
            },
        )

        # Score all pruned candidates
        results: list[MatchResult] = []
        for candidate in pruned:
            result = self._engine.compute_match(query_data, candidate)
            results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        # Project to API response models
        response_candidates: list[MatchCandidate] = []
        for result in results[:limit]:
            response_candidates.append(self._project_result(result, effective_threshold))

        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            "matching_query_complete",
            extra={
                "total_candidates": total_candidates,
                "pruned_candidates": pruned_count,
                "results_returned": len(response_candidates),
                "matches_found": sum(1 for c in response_candidates if c.is_match),
                "duration_ms": round(elapsed_ms, 2),
            },
        )

        return MatchingQueryResponse(
            candidates=response_candidates,
            total_candidates_evaluated=pruned_count,
            query_threshold=effective_threshold,
        )

    def _dataframe_to_candidates(self, df: pl.DataFrame) -> list[Candidate]:
        """Convert a Polars DataFrame to Candidate objects.

        Maps DataFrame column names to Candidate fields.
        Tolerates missing columns gracefully.

        Args:
            df: Business DataFrame from cache.

        Returns:
            List of Candidate objects.
        """
        candidates: list[Candidate] = []
        columns = set(df.columns)

        for row in df.iter_rows(named=True):
            gid = row.get("gid")
            if not gid:
                continue

            candidates.append(
                Candidate(
                    gid=str(gid),
                    name=row.get("name") if "name" in columns else None,
                    email=row.get("email") if "email" in columns else None,
                    phone=row.get("office_phone") if "office_phone" in columns else None,
                    domain=row.get("domain") if "domain" in columns else None,
                    city=row.get("business_city") if "business_city" in columns else None,
                    state=row.get("business_state") if "business_state" in columns else None,
                    zip_code=row.get("business_zip") if "business_zip" in columns else None,
                    company_id=row.get("company_id") if "company_id" in columns else None,
                )
            )

        return candidates

    @staticmethod
    def _project_result(result: MatchResult, threshold: float) -> MatchCandidate:
        """Project internal MatchResult to API-safe MatchCandidate.

        Strips PII (left_value, right_value), raw_score, and weight details.
        Only exposes field_name, similarity, and contributed flag.

        Args:
            result: Internal match result from the engine.
            threshold: Effective match threshold for is_match.

        Returns:
            MatchCandidate suitable for API response.
        """
        field_comparisons = [
            MatchFieldComparison(
                field_name=comp.field_name,
                similarity=comp.similarity,
                contributed=comp.contributed,
            )
            for comp in result.comparisons
        ]

        return MatchCandidate(
            candidate_gid=result.candidate_gid or "",
            score=round(result.score, 4),
            is_match=result.score >= threshold,
            field_comparisons=field_comparisons,
        )


__all__ = [
    "MatchingService",
]
