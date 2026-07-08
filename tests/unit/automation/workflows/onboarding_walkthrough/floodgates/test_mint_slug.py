"""``host_bundle.mint_slug`` — the net-new capability-slug mint (SLUG-1).

The repo lacked a slug mint (TDD §1: ``stage_deck_bundle`` takes a *pre-minted*
``--slug``; a full-repo grep for ``token_hex(16)`` outside onboarding returns only
``observability/correlation.py``). ``mint_slug`` closes that gap in its natural home.

Two properties are load-bearing:

* **shape** — every minted slug matches ``_SLUG_RE`` (32 lowercase hex chars, the
  128-bit CSPRNG token shape ``stage_deck_bundle`` refuses anything else against);
* **uniqueness** — independent draws do not collide (a re-mint that returned a prior
  slug would silently orphan a live deployed deck — the SLUG-1 hazard).
"""

from __future__ import annotations

from autom8_asana.automation.workflows.onboarding_walkthrough.host_bundle import (
    _SLUG_RE,
    mint_slug,
    stage_deck_bundle,
)


def test_mint_slug_matches_slug_re_shape() -> None:
    """Every minted slug is exactly 32 lowercase hex chars (``_SLUG_RE``)."""
    for _ in range(256):
        slug = mint_slug()
        assert _SLUG_RE.fullmatch(slug), f"minted slug is not _SLUG_RE-shaped: {slug!r}"
        assert len(slug) == 32
        assert slug == slug.lower()


def test_mint_slug_is_unique_across_draws() -> None:
    """Independent draws do not collide (re-minting orphans a deployed deck — SLUG-1)."""
    slugs = {mint_slug() for _ in range(1024)}
    assert len(slugs) == 1024, "mint_slug produced a collision across independent draws"


def test_minted_slug_is_accepted_by_stage(tmp_path) -> None:
    """A minted slug is accepted by the very gate it exists to feed: ``stage_deck_bundle``.

    Proves shape-compatibility end-to-end (the deny-first slug check at
    ``host_bundle.py:125-129`` does not refuse a freshly-minted token)."""
    frozen = tmp_path / "frozen.html"
    frozen.write_bytes(b"<html>deck</html>")
    slug = mint_slug()
    deploy_root = tmp_path / "deploy"
    served = stage_deck_bundle(
        deck_template="email-forwarding-setup",
        frozen_artifact=frozen,
        slug=slug,
        deploy_root=deploy_root,
    )
    assert served == deploy_root / slug / "index.html"
    assert served.read_bytes() == b"<html>deck</html>"
