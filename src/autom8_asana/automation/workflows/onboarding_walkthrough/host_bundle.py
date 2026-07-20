"""Capability-URL host bundle: audience-gated staging + byte-parity verification.

The serving model (WS-GUARD contract, CONDITIONAL-SEAL 2026-07-04; ADR-fork
D-01=Pages / D-02=direct-upload) is a per-client FROZEN artifact: the producer
bakes personalization at freeze time and the host (Cloudflare Pages) serves the
frozen bytes verbatim at a capability slug. Two invariants are load-bearing:

* **G-PROPAGATE arm-2 (byte-parity):** the host MOVES bytes, it never
  re-renders. served-bytes SHA-256 == frozen-artifact SHA-256, or the deploy is
  refused. ``verify_bundle_parity`` is the two-sided harness for that claim.
* **EGRESS-DENY-1 (default-deny audience egress):** no deck reaches the
  capability-URL surface unless the RESOLVED template's manifest classifies
  ``audience=customer``. Absence of a valid customer manifest IS denial
  (fail-closed). The gate is :func:`deck_manifests.assert_customer_deck` -- the
  SAME producer classification used by the runtime 2b attach-gate (contract
  C-3: extend, never reimplement; a per-Pages orphan check would drift). On
  denial the staging emits ``reason=deck_audience_denied`` and publishes ZERO
  bytes.

N-1 (mailbox never in the URL) is structural here: the slug is a separate
128-bit CSPRNG token (lowercase hex, 32 chars) carrying zero identity bytes --
never the guid, never the mailbox local-part, never the client name
(contract FORK-SLUG; ``slug≡guid`` and ``H(guid)`` are RED). ``_SLUG_RE``
rejects every identity-shaped slug (uuid dashes, ``@``, mixed case) by shape.

Deploy-root layout produced by :func:`stage_deck_bundle`::

    <deploy-root>/
      _headers              # Pages config (noindex/no-store/no-referrer/nosniff)
      <slug>/index.html     # frozen per-client deck; bytes verbatim

Nothing else is ever written into the deploy root: any stray file would be
PUBLISHED by ``wrangler pages deploy`` (a guessable non-capability path).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import secrets
import sys
from pathlib import Path

from autom8y_log import get_logger

from autom8_asana.automation.workflows.onboarding_walkthrough import deck_manifests

logger = get_logger(__name__)

#: Exact ``_headers`` content (contract §1.2, SVR: CF Pages ``_headers`` --
#: ≤100 rule-blocks, ≤2000 chars/line, native ``X-Robots-Tag`` support).
#: One host-agnostic rule block (``/*`` covers both the custom domain and
#: ``<project>.pages.dev``). C-4 (T-HDR-INERT) requires the header be asserted
#: SERVED post-deploy (``curl -I``), not merely authored here.
HEADERS_FILE_CONTENT = (
    "/*\n"
    "  X-Robots-Tag: noindex, nofollow\n"
    "  Cache-Control: no-store\n"
    "  Referrer-Policy: no-referrer\n"
    "  X-Content-Type-Options: nosniff\n"
)

#: Capability slug shape: exactly 32 lowercase hex chars (128-bit CSPRNG draw,
#: ``secrets.token_hex(16)``). Case-stable (Pages path resolution), URL-safe,
#: and structurally disjoint from every identity encoding: a raw uuid (dashes),
#: a mailbox (``@``), or a client name can never match.
_SLUG_RE = re.compile(r"^[0-9a-f]{32}$")


class HostBundleError(Exception):
    """The host bundle staging or parity verification refused (fail-closed)."""


class BundleParityError(HostBundleError):
    """Served/staged bytes do not hash-match the frozen artifact (drift REJECTED)."""


def mint_slug() -> str:
    """Mint a fresh capability slug: 32 lowercase hex chars (128-bit CSPRNG token).

    The net-new SLUG-1 mint the repo lacked (``stage_deck_bundle`` only ever *consumed*
    a pre-minted ``--slug``; no module minted one). ``secrets.token_hex(16)`` draws 16
    CSPRNG bytes and renders them as 32 lowercase hex chars -- exactly the :data:`_SLUG_RE`
    shape the deploy-root staging gate refuses anything else against, and structurally
    disjoint from every identity encoding (guid dashes, mailbox ``@``, client name).

    The minted slug MUST be pinned in the office manifest and REUSED on any re-run: a
    re-mint would orphan the already-deployed deck at the prior slug (SLUG-1 hazard).

    Returns:
        A fresh 32-lowercase-hex capability slug.

    Raises:
        HostBundleError: defensive -- if a future stdlib change ever yielded a
            non-``_SLUG_RE`` token, fail closed rather than emit a mis-shaped slug.
    """
    slug = secrets.token_hex(16)
    if not _SLUG_RE.fullmatch(slug):  # pragma: no cover - token_hex(16) is 32 lowercase hex
        raise HostBundleError(f"minted slug failed shape validation: {slug!r}")
    return slug


def sha256_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 of ``path``'s bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_deck_bundle(
    *,
    deck_template: str,
    frozen_artifact: Path,
    slug: str,
    deploy_root: Path,
) -> Path:
    """Stage a frozen deck into a Cloudflare-Pages deploy root (fail-closed).

    Order is deny-first: the audience gate and slug/artifact validation all run
    BEFORE any byte is written, so every refusal publishes zero bytes.

    Args:
        deck_template: Producer template folder name (e.g.
            ``"email-forwarding-setup"``). Gated through
            :func:`deck_manifests.assert_customer_deck` (C-3: the one gate).
        frozen_artifact: Path to the producer-frozen single-file HTML.
        slug: The capability token -- 32 lowercase hex chars, minted by CSPRNG,
            never derived from guid/mailbox/client.
        deploy_root: Directory to (create and) populate. Must not already
            contain a different deck at the same slug.

    Returns:
        The staged served file path ``<deploy_root>/<slug>/index.html``.

    Raises:
        deck_manifests.DeckAudienceError: non-customer or unmanifested deck
            (``reason=deck_audience_denied``; zero bytes published).
        HostBundleError: malformed slug, missing/empty artifact.
    """
    # EGRESS-DENY-1 / C-3: the producer classification IS the egress gate.
    try:
        deck_manifests.assert_customer_deck(deck_template)
    except deck_manifests.DeckAudienceError as exc:
        logger.error(
            "deck_host_bundle_denied",
            reason="deck_audience_denied",
            deck_template=deck_template,
            detail=exc.detail,
        )
        raise

    if not _SLUG_RE.fullmatch(slug):
        raise HostBundleError(
            "capability slug must be 32 lowercase hex chars (128-bit CSPRNG token); "
            "identity-derived slugs (guid/mailbox/client) are structurally refused"
        )
    if not frozen_artifact.is_file() or frozen_artifact.stat().st_size == 0:
        raise HostBundleError(f"frozen artifact missing or empty: {frozen_artifact}")

    frozen_bytes = frozen_artifact.read_bytes()

    slug_dir = deploy_root / slug
    slug_dir.mkdir(parents=True, exist_ok=True)
    served = slug_dir / "index.html"
    served.write_bytes(frozen_bytes)
    (deploy_root / "_headers").write_text(HEADERS_FILE_CONTENT, encoding="utf-8")

    # Immediate write-back parity (belt+braces; the deploy-time gate re-runs it).
    frozen_sha = hashlib.sha256(frozen_bytes).hexdigest()
    verify_bundle_parity(deploy_root=deploy_root, slug=slug, expected_sha256=frozen_sha)

    logger.info(
        "deck_host_bundle_staged",
        deck_template=deck_template,
        slug=slug,
        served=str(served),
        sha256=frozen_sha,
    )
    return served


def verify_bundle_parity(*, deploy_root: Path, slug: str, expected_sha256: str) -> str:
    """Assert staged served bytes hash-match the frozen artifact (arm-2 proof).

    Two-sided by contract: an exact match returns the sha; ANY byte drift
    raises :class:`BundleParityError` (REJECT). This is the acceptance test
    that the host moves bytes and never re-renders -- run it against the
    staged bundle before deploy, and against ``curl``-fetched served bytes
    after deploy.

    Returns:
        The verified lowercase hex SHA-256.

    Raises:
        BundleParityError: missing served file or hash mismatch.
    """
    served = deploy_root / slug / "index.html"
    if not served.is_file():
        raise BundleParityError(f"served file missing: {served}")
    actual = sha256_file(served)
    if actual != expected_sha256:
        raise BundleParityError(
            f"byte-parity REJECTED for /{slug}/index.html: "
            f"staged sha256={actual} != frozen sha256={expected_sha256} "
            "(the host must move frozen bytes verbatim, never re-render)"
        )
    return actual


def _main(argv: list[str] | None = None) -> int:
    """CLI: ``stage`` a bundle or ``verify`` parity. Exit 0 GREEN / 1 refused."""
    parser = argparse.ArgumentParser(prog="host_bundle")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stage = sub.add_parser("stage", help="stage a frozen deck into a deploy root")
    p_stage.add_argument("--deck", required=True, help="producer template folder name")
    p_stage.add_argument("--artifact", required=True, type=Path)
    p_stage.add_argument("--slug", required=True)
    p_stage.add_argument("--deploy-root", required=True, type=Path)

    p_verify = sub.add_parser("verify", help="verify staged bytes == frozen sha256")
    p_verify.add_argument("--deploy-root", required=True, type=Path)
    p_verify.add_argument("--slug", required=True)
    p_verify.add_argument("--expected-sha256", required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "stage":
            served = stage_deck_bundle(
                deck_template=args.deck,
                frozen_artifact=args.artifact,
                slug=args.slug,
                deploy_root=args.deploy_root,
            )
            sys.stdout.write(f"STAGED {served} sha256={sha256_file(served)}\n")
        else:
            sha = verify_bundle_parity(
                deploy_root=args.deploy_root,
                slug=args.slug,
                expected_sha256=args.expected_sha256,
            )
            sys.stdout.write(f"PARITY-OK sha256={sha}\n")
    except (HostBundleError, deck_manifests.DeckAudienceError) as exc:
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
