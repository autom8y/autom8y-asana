"""Scaffold fixtures for the substrate-v2 seam-contract unit tests.

SEAM-0 lands the frozen contract surface only, so these fixtures build the two
core value objects (``ArtifactId``, ``FreshnessProof``) that the S2-S7 fan will
reach for. No ``__post_init__`` guard runs yet (the guards are the FORK-W1 scope
cut owned by S2/S3), so construction here is unconditional by design.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate import ArtifactId, FreshnessProof


@pytest.fixture
def sample_artifact_id() -> ArtifactId:
    """A servable (project, entity) address for downstream seam tests."""
    return ArtifactId(project_gid="1200000000000001", entity_type=EntityType.OFFER)


@pytest.fixture
def sample_freshness_proof() -> FreshnessProof:
    """A well-formed, tz-aware freshness proof for downstream seam tests."""
    return FreshnessProof(
        built_from_live_at=datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC),
        content_digest="0" * 64,
        sla_seconds=3600,
    )
