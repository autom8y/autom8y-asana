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

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

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
    phone: str | None = None
    vertical: str | None = None

    # Offer resolution (Phase 2)
    offer_id: str | None = None
    offer_name: str | None = None

    # Contact resolution (Phase 2)
    contact_email: str | None = None
    contact_phone: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_e164(cls, v: str | None) -> str | None:
        """Validate E.164 format: +[1-9][0-9]{1,14}.

        Per ITU-T E.164: + followed by 1-15 digits, where the first digit
        after + must be non-zero (country code cannot start with 0).

        Args:
            v: Phone number string or None

        Returns:
            Validated phone number or None

        Raises:
            ValueError: If phone format is invalid.
        """
        if v is None:
            return None

        # Strip whitespace (including trailing newlines) before validation
        v = v.strip()

        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError(
                f"Invalid E.164 format: {v}. "
                f"Expected format: +[country][number] (e.g., +15551234567)"
            )
        return v


class ResolutionRequest(BaseModel):
    """Request body for entity resolution.

    Per TDD: Batch resolution with max 1000 criteria.

    Attributes:
        criteria: List of lookup criteria (max 1000 items)
        fields: Optional field filtering (Phase 2)
    """

    model_config = ConfigDict(extra="forbid")

    criteria: list[ResolutionCriterion]
    fields: list[str] | None = None

    @field_validator("criteria")
    @classmethod
    def validate_batch_size(
        cls, v: list[ResolutionCriterion]
    ) -> list[ResolutionCriterion]:
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
                f"Batch size {len(v)} exceeds maximum {MAX_BATCH_SIZE}. "
                f"Please chunk requests."
            )
        return v


class ResolutionResultModel(BaseModel):
    """Single resolution result.

    Per TDD: Result of a single criterion resolution.
    Per TDD-FIELDS-ENRICHMENT-001: Added data field for enriched field values.

    Attributes:
        gid: First matching GID or None if not found (backwards compat)
        gids: All matching GIDs (new multi-match support)
        match_count: Number of matches
        error: Error code if resolution failed
        data: Field data for each match (only when fields requested)
    """

    model_config = ConfigDict(extra="forbid")

    gid: str | None  # Backwards compatible - first match
    gids: list[str] | None = None  # All matches
    match_count: int = 0
    error: str | None = None
    data: list[dict[str, Any]] | None = None  # Field data per match


class ResolutionMeta(BaseModel):
    """Response metadata.

    Per TDD: Summary statistics for the resolution batch.

    Attributes:
        resolved_count: Number of successful resolutions
        unresolved_count: Number of failed resolutions
        entity_type: Entity type that was resolved
        project_gid: Project GID used for resolution
    """

    model_config = ConfigDict(extra="forbid")

    resolved_count: int
    unresolved_count: int
    entity_type: str
    project_gid: str


class ResolutionResponse(BaseModel):
    """Response body for entity resolution.

    Per TDD: Results in same order as input criteria.

    Attributes:
        results: List of resolution results
        meta: Response metadata
    """

    model_config = ConfigDict(extra="forbid")

    results: list[ResolutionResultModel]
    meta: ResolutionMeta
