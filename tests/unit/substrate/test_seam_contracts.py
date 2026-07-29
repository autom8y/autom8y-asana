"""SEAM-0 trivial import-and-typecheck test for the five FROZEN seam contracts.

The real static typecheck is the ``mypy src/autom8_asana/substrate`` gate; this
module is the runtime smoke that proves the export surface imports, the CLOSED
enums keep their frozen members, and the value objects are frozen and
constructible. ALL four owned-function bodies are now filled (S2:
``is_provable``/``canonical_digest`` — covered in test_freshness.py; S3:
``artifact_key``/``is_servable`` — covered in test_identity.py), so the former
stub-raise assertions are retired here.
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
)

# The frozen export surface (TDD §4). Seam 2 is v1.1 (F1/C15 amendment 2026-07-29:
# ``stage_version`` drops its proof param; ``swap_pointer`` gains one — the mypy
# ``mypy src/autom8_asana/substrate`` gate enforces those v1.1 signatures). The
# PACKAGE export COUNT is unchanged (no ``__all__`` symbol added/removed — the
# retired ``refresh_pointer_proof`` and ``StaleProofRefused`` were intra-package,
# never re-exported), so the "count change = architect finding" guard stays GREEN
# and correctly did not need bumping for this architect-ruled amendment.
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
