"""Two-sided tests for the capability-URL host bundle (EGRESS-DENY-1 + arm-2 parity).

The host bundle has exactly two jobs and each is proven from BOTH sides here:

* **Default-deny audience egress** (contract §1.4, C-3): the customer deck
  stages GREEN; the internal deck and an unmanifested deck REFUSE with zero
  bytes published. The gate IS ``deck_manifests.assert_customer_deck`` -- the
  same producer classification the runtime 2b attach-gate calls (no per-Pages
  orphan gate to drift).
* **Byte-parity** (G-PROPAGATE arm-2): staged served bytes hash-match the
  frozen artifact GREEN; a single flipped byte is REJECTED.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from autom8_asana.automation.workflows.onboarding_walkthrough import host_bundle
from autom8_asana.automation.workflows.onboarding_walkthrough.deck_manifests import (
    DeckAudienceError,
)

# A stand-in frozen artifact: the parity contract is byte-level, so any bytes do.
FROZEN_BYTES = b"<!doctype html><html><body>frozen deck fixture bytes</body></html>"
SLUG = "207688021de88a6d7231e1d08ea77a85"  # shape of the minted 128-bit token


@pytest.fixture()
def frozen_artifact(tmp_path: Path) -> Path:
    artifact = tmp_path / "frozen.html"
    artifact.write_bytes(FROZEN_BYTES)
    return artifact


class TestDefaultDenyAudienceEgress:
    def test_customer_deck_publishes(self, frozen_artifact: Path, tmp_path: Path) -> None:
        deploy_root = tmp_path / "deploy"
        served = host_bundle.stage_deck_bundle(
            deck_template="email-forwarding-setup",
            frozen_artifact=frozen_artifact,
            slug=SLUG,
            deploy_root=deploy_root,
        )
        assert served == deploy_root / SLUG / "index.html"
        assert served.read_bytes() == FROZEN_BYTES

    def test_internal_deck_refused_zero_bytes(self, frozen_artifact: Path, tmp_path: Path) -> None:
        deploy_root = tmp_path / "deploy"
        with pytest.raises(DeckAudienceError) as excinfo:
            host_bundle.stage_deck_bundle(
                deck_template="ghl-calendar-setup",
                frozen_artifact=frozen_artifact,
                slug=SLUG,
                deploy_root=deploy_root,
            )
        assert excinfo.value.detail == "audience_internal"
        assert not deploy_root.exists()  # zero bytes published on denial

    def test_absent_manifest_is_denial(self, frozen_artifact: Path, tmp_path: Path) -> None:
        deploy_root = tmp_path / "deploy"
        with pytest.raises(DeckAudienceError) as excinfo:
            host_bundle.stage_deck_bundle(
                deck_template="no-such-deck",
                frozen_artifact=frozen_artifact,
                slug=SLUG,
                deploy_root=deploy_root,
            )
        assert excinfo.value.detail == "manifest_missing"
        assert not deploy_root.exists()

    @pytest.mark.parametrize(
        "bad_slug",
        [
            "b167331c-536f-4996-9b2d-2f696f35f556",  # raw guid (dashes): slug≡guid is RED
            "b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com",
            "Sand Lake Dental",
            "207688021DE88A6D7231E1D08EA77A85",  # mixed/upper case (case-unstable)
            "abc123",  # too short (low entropy)
        ],
    )
    def test_identity_shaped_slug_refused(
        self, frozen_artifact: Path, tmp_path: Path, bad_slug: str
    ) -> None:
        deploy_root = tmp_path / "deploy"
        with pytest.raises(host_bundle.HostBundleError):
            host_bundle.stage_deck_bundle(
                deck_template="email-forwarding-setup",
                frozen_artifact=frozen_artifact,
                slug=bad_slug,
                deploy_root=deploy_root,
            )
        assert not (deploy_root / bad_slug).exists()


class TestHeadersFile:
    def test_headers_authored_exactly(self, frozen_artifact: Path, tmp_path: Path) -> None:
        deploy_root = tmp_path / "deploy"
        host_bundle.stage_deck_bundle(
            deck_template="email-forwarding-setup",
            frozen_artifact=frozen_artifact,
            slug=SLUG,
            deploy_root=deploy_root,
        )
        content = (deploy_root / "_headers").read_text(encoding="utf-8")
        assert content == host_bundle.HEADERS_FILE_CONTENT
        assert content.startswith("/*\n")  # host-agnostic glob, one rule block
        assert "X-Robots-Tag: noindex, nofollow" in content
        assert "Cache-Control: no-store" in content
        assert "Referrer-Policy: no-referrer" in content
        assert "X-Content-Type-Options: nosniff" in content
        # CF Pages budgets: <=100 rule blocks, <=2000 chars per line.
        assert content.count("/*") == 1
        assert max(len(line) for line in content.splitlines()) <= 2000

    def test_deploy_root_contains_only_headers_and_slug(
        self, frozen_artifact: Path, tmp_path: Path
    ) -> None:
        """Anything else in the deploy root would be PUBLISHED by wrangler."""
        deploy_root = tmp_path / "deploy"
        host_bundle.stage_deck_bundle(
            deck_template="email-forwarding-setup",
            frozen_artifact=frozen_artifact,
            slug=SLUG,
            deploy_root=deploy_root,
        )
        assert {p.name for p in deploy_root.iterdir()} == {"_headers", SLUG}
        assert [p.name for p in (deploy_root / SLUG).iterdir()] == ["index.html"]


class TestBundleParityTwoSided:
    def test_green_staged_bytes_hash_match(self, frozen_artifact: Path, tmp_path: Path) -> None:
        deploy_root = tmp_path / "deploy"
        host_bundle.stage_deck_bundle(
            deck_template="email-forwarding-setup",
            frozen_artifact=frozen_artifact,
            slug=SLUG,
            deploy_root=deploy_root,
        )
        expected = hashlib.sha256(FROZEN_BYTES).hexdigest()
        assert (
            host_bundle.verify_bundle_parity(
                deploy_root=deploy_root, slug=SLUG, expected_sha256=expected
            )
            == expected
        )

    def test_red_byte_drift_rejected(self, frozen_artifact: Path, tmp_path: Path) -> None:
        deploy_root = tmp_path / "deploy"
        served = host_bundle.stage_deck_bundle(
            deck_template="email-forwarding-setup",
            frozen_artifact=frozen_artifact,
            slug=SLUG,
            deploy_root=deploy_root,
        )
        drifted = bytearray(served.read_bytes())
        drifted[0] ^= 0x01  # single flipped bit == drift
        served.write_bytes(bytes(drifted))
        expected = hashlib.sha256(FROZEN_BYTES).hexdigest()
        with pytest.raises(host_bundle.BundleParityError):
            host_bundle.verify_bundle_parity(
                deploy_root=deploy_root, slug=SLUG, expected_sha256=expected
            )

    def test_red_missing_served_file_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(host_bundle.BundleParityError):
            host_bundle.verify_bundle_parity(
                deploy_root=tmp_path,
                slug=SLUG,
                expected_sha256=hashlib.sha256(FROZEN_BYTES).hexdigest(),
            )


class TestCli:
    def test_cli_stage_and_verify_green(
        self, frozen_artifact: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        deploy_root = tmp_path / "deploy"
        expected = hashlib.sha256(FROZEN_BYTES).hexdigest()
        assert (
            host_bundle._main(
                [
                    "stage",
                    "--deck",
                    "email-forwarding-setup",
                    "--artifact",
                    str(frozen_artifact),
                    "--slug",
                    SLUG,
                    "--deploy-root",
                    str(deploy_root),
                ]
            )
            == 0
        )
        assert (
            host_bundle._main(
                [
                    "verify",
                    "--deploy-root",
                    str(deploy_root),
                    "--slug",
                    SLUG,
                    "--expected-sha256",
                    expected,
                ]
            )
            == 0
        )
        out = capsys.readouterr().out
        assert f"PARITY-OK sha256={expected}" in out

    def test_cli_refusals_exit_nonzero(
        self, frozen_artifact: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        deploy_root = tmp_path / "deploy"
        assert (
            host_bundle._main(
                [
                    "stage",
                    "--deck",
                    "ghl-calendar-setup",
                    "--artifact",
                    str(frozen_artifact),
                    "--slug",
                    SLUG,
                    "--deploy-root",
                    str(deploy_root),
                ]
            )
            == 1
        )
        assert (
            host_bundle._main(
                [
                    "verify",
                    "--deploy-root",
                    str(deploy_root),
                    "--slug",
                    SLUG,
                    "--expected-sha256",
                    "0" * 64,
                ]
            )
            == 1
        )
        err = capsys.readouterr().err
        assert "REFUSED" in err
