"""Pydantic request/response models for entity resolution.

Per TDD-I10: Extracted from resolver.py to separate model definitions
from endpoint logic. These models define the API contract for the
POST /v1/resolve/{entity_type} endpoint.

Models:
    ResolutionCriterion: Single lookup criterion with E.164 validation
    ResolutionRequest: Batch request with size validation
    ResolutionResultModel: Single resolution result
    ResolutionMeta: Response metadata
    ResolutionResponse: Full response envelope
"""

from __future__ import annotations

from typing import Any

from autom8y_api_schemas import E164PhoneField
from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "ResolutionCriterion",
    "ResolutionRequest",
    "ResolutionResultModel",
    "ResolutionMeta",
    "ResolutionResponse",
]


class ResolutionCriterion(BaseModel):
    """Single lookup criterion - accepts any schema column dynamically.

    Per SPIKE-dynamic-api-criteria: Uses extra="allow" to accept arbitrary
    schema columns. Common fields are typed for validation and documentation.
    Additional fields are validated against the entity schema at runtime.

    Common Fields (typed):
        - phone: E.164 formatted phone number (maps to office_phone)
        - vertical: Business vertical

    Offer Fields:
        - offer_id: Offer identifier
        - offer_name: For phone/vertical + discriminator

    Contact Fields:
        - contact_email: Email address
        - contact_phone: Phone number

    Dynamic Fields (any schema column):
        - Use GET /v1/resolve/{entity_type}/schema to discover valid fields
        - Examples: mrr, specialty, weekly_ad_spend, stripe_id, etc.
    """

    model_config = ConfigDict(extra="allow")

    # Unit/Business resolution
    phone: E164PhoneField | None = Field(
        default=None,
        description="E.164 formatted phone number for unit/business resolution.",
        examples=["+19259998806"],
    )
    vertical: str | None = Field(
        default=None,
        description="Business vertical to narrow resolution scope.",
        examples=["chiro"],
    )

    # Offer resolution (Phase 2)
    offer_id: str | None = Field(
        default=None,
        description="Offer identifier for offer entity resolution.",
        examples=["OFF-0042"],
    )
    offer_name: str | None = Field(
        default=None,
        description="Offer name used with phone/vertical as a discriminator.",
        examples=["Free Consultation"],
    )

    # Contact resolution (Phase 2)
    contact_email: str | None = Field(
        default=None,
        description="Contact email address for contact resolution.",
        examples=["jane@acmechiro.com"],
    )
    contact_phone: E164PhoneField | None = Field(
        default=None,
        description="Contact phone number for contact resolution.",
        examples=["+14155551234"],
    )

    @field_validator("phone", "contact_phone", mode="before")
    @classmethod
    def strip_phone_whitespace(cls, v: str | None) -> str | None:
        """Strip whitespace from phone fields before E.164 pattern validation.

        Maintains backward compatibility with callers that send trailing
        newlines or spaces. The fleet E164PhoneField pattern requires an
        exact match, so whitespace must be stripped beforehand.
        """
        if isinstance(v, str):
            return v.strip()
        return v


class ResolutionRequest(BaseModel):
    """Request body for entity resolution.

    Per TDD: Batch resolution with max 1000 criteria.
    Per TDD-STATUS-AWARE-RESOLUTION / FR-1, SD-1:
    active_only defaults to True (intentional breaking change).

    Attributes:
        criteria: List of lookup criteria (max 1000 items)
        fields: Optional field filtering (Phase 2)
        active_only: Per FR-1, SD-1. Filter to active statuses only.
    """

    model_config = ConfigDict(extra="forbid")

    criteria: list[ResolutionCriterion] = Field(
        description="Lookup criteria to resolve (max 1000 per request).",
    )
    fields: list[str] | None = Field(
        default=None,
        description="Optional field names to return in enriched result data.",
        examples=[["mrr", "weekly_ad_spend"]],
    )

    # Per TDD-STATUS-AWARE-RESOLUTION / FR-1, SD-1:
    # Intentional breaking change. See ADR-status-aware-resolution Decision 1.
    active_only: bool = Field(
        default=True,
        description="Filter results to active statuses only. True by default (FR-1).",
        examples=[True],
    )

    @field_validator("criteria")
    @classmethod
    def validate_batch_size(cls, v: list[ResolutionCriterion]) -> list[ResolutionCriterion]:
        """Enforce max 1000 criteria per request.

        Per TDD: Batch size limit preserves existing API behavior.

        Args:
            v: List of criteria to validate

        Returns:
            Validated criteria list

        Raises:
            ValueError: If batch size exceeds 1000.
        """
        MAX_BATCH_SIZE = 1000
        if len(v) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {len(v)} exceeds maximum {MAX_BATCH_SIZE}. Please chunk requests."
            )
        return v


class ResolutionResultModel(BaseModel):
    """Single resolution result with status annotation.

    Per TDD: Result of a single criterion resolution.
    Per TDD-FIELDS-ENRICHMENT-001: Added data field for enriched field values.
    Per TDD-STATUS-AWARE-RESOLUTION / FR-3:
    Each match carries a status string from AccountActivity vocabulary.

    Attributes:
        gid: First matching GID or None if not found (backwards compat)
        gids: All matching GIDs (new multi-match support)
        match_count: Number of matches (post-filter when active_only=True)
        error: Error code if resolution failed
        data: Field data for each match (only when fields requested)
        status: Per FR-3. Parallel list, same length as gids.
            None when no classifier available (FR-7).
        total_match_count: Per FR-11. Pre-filter total for diagnostic visibility.
    """

    model_config = ConfigDict(extra="forbid")

    gid: str | None = Field(
        description="First matching Asana GID, or null if not found. Backwards compatible.",
        examples=["1234567890123456"],
    )
    gids: list[str] | None = Field(
        default=None,
        description="All matching Asana GIDs for multi-match resolution.",
        examples=[["1234567890123456"]],
    )
    match_count: int = Field(
        default=0,
        description="Number of matches after active_only filtering.",
        examples=[1],
    )
    error: str | None = Field(
        default=None,
        description="Error code if resolution failed for this criterion.",
        examples=[None],
    )
    data: list[dict[str, Any]] | None = Field(
        default=None,
        description="Enriched field data per match (only when fields requested).",
    )

    # Per TDD-STATUS-AWARE-RESOLUTION / FR-3:
    # Parallel list, same length as gids. None when no classifier (FR-7).
    status: list[str | None] | None = Field(
        default=None,
        description="Activity status per match (parallel to gids). Null when no classifier available.",
        examples=[["active"]],
    )

    # Per TDD-STATUS-AWARE-RESOLUTION / FR-11:
    # Pre-filter total for diagnostic visibility.
    total_match_count: int | None = Field(
        default=None,
        description="Pre-filter total match count for diagnostic visibility.",
        examples=[1],
    )


class ResolutionMeta(BaseModel):
    """Response metadata.

    Per TDD: Summary statistics for the resolution batch.

    Attributes:
        resolved_count: Number of successful resolutions
        unresolved_count: Number of failed resolutions
        entity_type: Entity type that was resolved
        project_gid: Project GID used for resolution
        available_fields: Valid fields for entity (from schema)
        criteria_schema: Fields used in the resolution request criteria
    """

    model_config = ConfigDict(extra="forbid")

    resolved_count: int = Field(
        description="Number of criteria that resolved to at least one match.",
        examples=[8],
    )
    unresolved_count: int = Field(
        description="Number of criteria that found no matches.",
        examples=[2],
    )
    entity_type: str = Field(description="Entity type that was resolved.", examples=["unit"])
    project_gid: str = Field(
        description="Asana project GID used for resolution.",
        examples=["1111111111111111"],
    )
    available_fields: list[str] = Field(
        default_factory=list, description="Valid field names for this entity type."
    )
    criteria_schema: list[str] = Field(
        default_factory=list,
        description="Field names used in the resolution request criteria.",
    )


class ResolutionResponse(BaseModel):
    """Response body for entity resolution.

    Per TDD: Results in same order as input criteria.

    Attributes:
        results: List of resolution results
        meta: Response metadata
    """

    model_config = ConfigDict(extra="forbid")

    results: list[ResolutionResultModel] = Field(
        description="Resolution results in the same order as input criteria."
    )
    meta: ResolutionMeta = Field(description="Summary statistics for the resolution batch.")
