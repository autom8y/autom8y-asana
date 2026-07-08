"""BUILD-GATE: the Option-B accumulation premise (HANDOFF ITEM-F TL-A, TDD §8).

Two synthetic offices staged through the UNCHANGED ``stage_deck_bundle`` into ONE
shared deploy root must yield BOTH slug dirs + ONE byte-identical ``_headers``,
with per-slug ``verify_bundle_parity`` passing. If ``stage_deck_bundle`` mutated
or removed a sibling slug dir, the Option-B (stage-INTO-deck-host) premise would
be FALSIFIED and the sprint HALTs — this test is that gate, run FIRST.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from autom8_asana.automation.workflows.onboarding_walkthrough.host_bundle import (
    HEADERS_FILE_CONTENT,
    stage_deck_bundle,
    verify_bundle_parity,
)

if TYPE_CHECKING:
    from pathlib import Path

# Two distinct capability-shaped slugs (32 lowercase hex; _SLUG_RE shape).
SLUG_A = "1f2e3d4c5b6a798801234567890abcde"
SLUG_B = "fedcba9876543210aabbccddeeff0011"
BYTES_A = b"<!doctype html><html><body>office A frozen deck</body></html>"
BYTES_B = b"<!doctype html><html><body>office B frozen deck</body></html>"


class TestTwoOfficeAccumulation:
    def test_two_offices_accumulate_in_one_shared_root(self, tmp_path: Path) -> None:
        """UNCHANGED stage_deck_bundle x2 into one root: both slug dirs survive, ONE
        byte-identical ``_headers``, per-slug byte-parity GREEN — the Option-B premise."""
        shared_root = tmp_path / "shared"
        artifact_a = tmp_path / "a.html"
        artifact_a.write_bytes(BYTES_A)
        artifact_b = tmp_path / "b.html"
        artifact_b.write_bytes(BYTES_B)

        stage_deck_bundle(
            deck_template="email-forwarding-setup",
            frozen_artifact=artifact_a,
            slug=SLUG_A,
            deploy_root=shared_root,
        )
        headers_after_a = (shared_root / "_headers").read_bytes()

        stage_deck_bundle(
            deck_template="email-forwarding-setup",
            frozen_artifact=artifact_b,
            slug=SLUG_B,
            deploy_root=shared_root,
        )

        # Both slug dirs present; office A's bytes NOT mutated/removed by office B's stage.
        assert (shared_root / SLUG_A / "index.html").read_bytes() == BYTES_A
        assert (shared_root / SLUG_B / "index.html").read_bytes() == BYTES_B

        # Exactly ONE _headers, byte-identical before/after the second stage and to the
        # canonical HEADERS_FILE_CONTENT (idempotent byte-constant rewrite).
        headers_after_b = (shared_root / "_headers").read_bytes()
        assert headers_after_a == headers_after_b == HEADERS_FILE_CONTENT.encode("utf-8")

        # The shared root holds ONLY the two slug dirs + _headers (nothing stray).
        assert {p.name for p in shared_root.iterdir()} == {"_headers", SLUG_A, SLUG_B}

        # Per-slug byte-parity passes for BOTH offices in the shared root.
        sha_a = hashlib.sha256(BYTES_A).hexdigest()
        sha_b = hashlib.sha256(BYTES_B).hexdigest()
        assert verify_bundle_parity(deploy_root=shared_root, slug=SLUG_A, expected_sha256=sha_a)
        assert verify_bundle_parity(deploy_root=shared_root, slug=SLUG_B, expected_sha256=sha_b)
