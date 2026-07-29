"""SEAM-0 trivial import-and-typecheck test for the five FROZEN seam contracts.

The real static typecheck is the ``mypy src/autom8_asana/substrate`` gate; this
module is the runtime smoke that proves the export surface imports, the CLOSED
enums keep their frozen members, the owned-function stubs stay contract-only
(raise with their owner tag), and the value objects are frozen and constructible.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import autom8_asana.substrate as substrate
from autom8_asana.core.types import EntityType
from autom8_asana.substrate import (
    ArtifactId,
    FreshnessProof,
    Provability,
    Provable,
    RebuildOutcome,
    Refused,
    RefusePayload,
    RefuseReason,
    ServedNumber,
    artifact_key,
    canonical_digest,
    is_provable,
    is_servable,
)

# The frozen SEAM-0 export surface (TDD §4). If this count changes, a seam
# changed — which is an architect finding, not a silent edit.
EXPECTED_EXPORTS = 24


def test_export_surface_is_complete() -> None:
    """The full frozen vocabulary is re-exported from the package root."""
    assert len(substrate.__all__) == EXPECTED_EXPORTS
    assert len(set(substrate.__all__)) == EXPECTED_EXPORTS  # no dupes
    for name in substrate.__all__:
        assert hasattr(substrate, name), f"missing export: {name}"


def test_closed_enums_have_frozen_members() -> None:
    """The three CLOSED enums carry exactly their §4 members — no more, no fewer."""
    assert {m.value for m in Provability} == {"provable", "stale", "corrupt"}
    assert {m.value for m in RebuildOutcome} == {
        "swapped",
        "staged_rejected",
        "fetch_refused",
    }
    assert {m.value for m in RefuseReason} == {
        "stale",
        "corrupt",
        "missing",
        "divergent",
    }


def test_owned_stubs_raise_with_owner_tag() -> None:
    """The four owned-function stubs stay contract-only until their owner sprint fills them."""
    with pytest.raises(NotImplementedError, match="owned by S2"):
        is_provable(_a_proof(), "digest", datetime.now(tz=UTC))
    with pytest.raises(NotImplementedError, match="owned by S2"):
        canonical_digest(object())
    with pytest.raises(NotImplementedError, match="owned by S3"):
        artifact_key(ArtifactId(project_gid="1", entity_type=EntityType.OFFER))
    with pytest.raises(NotImplementedError, match="owned by S3"):
        is_servable(EntityType.OFFER)


def test_value_objects_are_frozen_and_constructible() -> None:
    """The frozen value objects construct and reject attribute mutation."""
    aid = ArtifactId(project_gid="1", entity_type=EntityType.BUSINESS)
    with pytest.raises(AttributeError):
        aid.project_gid = "2"  # type: ignore[misc]

    refused = Refused(
        reason=RefuseReason.DIVERGENT,
        detail=RefusePayload(
            plane="v2",
            absolute_age={"v2": 12.5, "legacy": 90.0},
            magnitude=3.0,
            per_section_delta={"section-a": 1.0},
        ),
    )
    served: ServedNumber = refused
    assert isinstance(served, Refused)

    provable: ServedNumber = Provable(frame=b"bytes", proof=_a_proof())
    assert isinstance(provable, Provable)


def _a_proof() -> FreshnessProof:
    return FreshnessProof(
        built_from_live_at=datetime(2026, 7, 29, tzinfo=UTC),
        content_digest="0" * 64,
        sla_seconds=3600,
    )
