"""Deck-audience classification manifests -- the deck-audience lock.

Product ruling (operator, 2026-07-02): ``ghl-calendar-setup`` is INTERNAL-ONLY
(an internal ops/setup deck); the customer-facing walkthrough deck is
``email-forwarding-setup``. Before this lock existed, no gate ever verified
deck CONTENT against product intent (the payload-correctness gap), and the
internal deck was attached to a live customer task (2026-07-02T11:55:47Z).

Each producer deck template is classified by a JSON manifest at
``deck_manifests/{template-dir-name}.json`` with body
``{"audience": "customer" | "internal"}``. The manifests live in THIS owned
src tree -- deliberately NOT co-located inside ``vendor/deck-producer/``: the
vendored tree is an upstream drop (``@contente/deck-inliner``) whose documented
upgrade path (NODE_BUNDLING.md, A4) re-vendors or replaces it wholesale, which
would silently delete co-located manifests and turn default-deny into a silent
fleet-wide outage. A completeness test pins the manifest set to the template
set so the two filesystems cannot drift.

Semantics are DEFAULT-DENY: a template without a valid customer manifest is
refused (absence IS denial). The runtime gate (``assert_customer_deck``) reads
the manifest file at call time for the RESOLVED deck template, so a
dynamically or bypassed selection is still gated.
"""

from __future__ import annotations

import json
from pathlib import Path

#: Directory of per-template audience manifests. One ``{template-dir-name}.json``
#: per producer deck template dir; filename == exact template folder name.
MANIFEST_DIR = Path(__file__).resolve().parent / "deck_manifests"

#: The closed audience enum. Positive classification only -- no third value.
KNOWN_AUDIENCES: frozenset[str] = frozenset({"customer", "internal"})


class DeckAudienceError(Exception):
    """A deck failed the customer-audience gate (fail-closed refusal).

    ``detail`` is a closed vocabulary consumed by observability:

    * ``"audience_internal"`` -- the manifest classifies the deck non-customer;
    * ``"manifest_missing"`` -- missing / unparseable / malformed manifest
      (default-deny: absence IS denial).
    """

    def __init__(self, deck_template: str, detail: str, message: str | None = None) -> None:
        self.deck_template = deck_template
        self.detail = detail
        super().__init__(message or f"deck {deck_template!r} refused: {detail}")


def load_audience(deck_template: str) -> str | None:
    """Return the classified audience for ``deck_template``, or ``None`` when denied.

    ``None`` covers every default-deny arm: no manifest file, unreadable file,
    non-JSON body, non-object body, absent/typo'd/out-of-enum ``audience``, and
    a path-shaped (non-basename) template name. Reads the manifest at call time
    (never a cached import-time snapshot).
    """
    if not deck_template or Path(deck_template).name != deck_template:
        # A path-shaped name can never address a manifest (no traversal escape).
        return None
    path = MANIFEST_DIR / f"{deck_template}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    audience = data.get("audience")
    if not isinstance(audience, str) or audience not in KNOWN_AUDIENCES:
        return None
    return audience


def load_title(deck_template: str) -> str | None:
    """Return the deck's customer-facing ``title`` from its manifest, or ``None``.

    Fault-13 (S5): the producer defaults the frozen artifact's ``<title>`` from
    ``--deck`` when no ``--title`` is passed, which shipped the INTERNAL template
    path (``templates/email-forwarding-setup``) as the browser-tab title of every
    live customer deck. The customer-facing title is manifest-owned (beside the
    audience classification -- the same audience-locked source of truth) and
    threaded to the producer as ``--title``.

    Tolerant read, same posture as ``load_audience``: a missing/unreadable
    manifest, non-object body, or an absent/empty/non-string ``title`` yields
    ``None`` (the producer's default-title path must itself be customer-safe;
    AC-TITLE-DEFAULT pins that). A path-shaped fragment (contains ``/``) is
    refused -- the exact leak class this field exists to prevent.
    """
    if not deck_template or Path(deck_template).name != deck_template:
        return None
    path = MANIFEST_DIR / f"{deck_template}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    title = data.get("title")
    if not isinstance(title, str):
        return None
    title = title.strip()
    if not title or "/" in title:
        return None
    return title


def assert_customer_deck(deck_template: str) -> None:
    """Fail-closed audience gate: raise unless ``deck_template`` is classified customer.

    Raises:
        DeckAudienceError: with ``detail="audience_internal"`` (classified
            non-customer) or ``detail="manifest_missing"`` (default-deny).
    """
    audience = load_audience(deck_template)
    if audience is None:
        raise DeckAudienceError(deck_template, "manifest_missing")
    if audience != "customer":
        raise DeckAudienceError(deck_template, "audience_internal")


def assert_map_customer_only(deck_map: dict[str, str | None]) -> None:
    """Map-purity validator: every mapped (non-None) deck must be customer-classified.

    Applies to any ``provider -> deck`` mapping -- today the provider-agnostic
    ``WALKTHROUGH_DECK_OVERRIDES`` seam (a ``None`` value is an EXPLICIT exclusion
    and is skipped here). Construction fails LOUDLY: the raised error names the
    offending provider AND deck, so a wrong-audience override can never build
    quietly. Pair with ``assert_customer_deck(WALKTHROUGH_DECK_DEFAULT)`` to pin
    the universal default deck itself.

    Raises:
        DeckAudienceError: naming the first offending ``provider -> deck`` entry.
    """
    for provider, deck in deck_map.items():
        if deck is None:
            continue
        audience = load_audience(deck)
        if audience == "customer":
            continue
        detail = "manifest_missing" if audience is None else "audience_internal"
        raise DeckAudienceError(
            deck,
            detail,
            message=(
                f"deck override [{provider!r}] = {deck!r} is not a customer deck "
                f"({detail}); map a customer-classified deck or None"
            ),
        )
