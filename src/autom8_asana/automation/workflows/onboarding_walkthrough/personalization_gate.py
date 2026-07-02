"""Field-level customer-personalization gate -- the fault-13 content lock (PR-2).

Live receipt (2026-07-02, decks 1216243790085943 / 1216237303036469): the
customer cover's "Prepared for" line bound the RAW INTERNAL Asana task name
("PLAY: Custom Calendar Integration — {clinic}"). PR-1 fixed the PROVENANCE
(the display name now comes from the data-service ``BusinessRecord`` row that
also yields the gated address). THIS module fixes the missing CLASS of gate:
before fault-13, no runtime check ever verified the personalization VALUE
itself was customer-plane content -- the deck-audience lock gates the deck,
W1/T7 gate the tenant identity, but the field CONTENT rode ungated.

``assert_customer_personalization`` is that gate: fail-closed, called at
workflow step 2c (after the W1 anchor, before FREEZE -- the same
refuse-precedes-FREEZE discipline as G1 ``deck_audience_denied``). It refuses
any value that is not a plausible customer-facing display name, with a CLOSED
detail vocabulary consumed by observability:

* ``"nomenclature_internal"`` -- operational-plane material: a
  PLAY/TASK/OB/TEST/INTERNAL prefix, an embedded gid-shaped digit run (13+),
  a ``templates/`` path fragment, or the ALL-CAPS-prefix + " — " separator
  pattern of internal task nomenclature;
* ``"placeholder"`` -- the "Clinic" generic (a lie rendered as
  personalization) or an empty-after-strip value;
* ``"too_long"`` -- more than 140 code points, the PR-1 template clamp bound
  (refusing above the honest-render bound, never the old silent-slice bound).

The refused value NEVER rides an exception or log in full: it is masked to
its first 8 characters + an ellipsis (``mask_personalization_value``, the same
mask the G12 C-BN1-05 audit record uses). Symmetric producer-side floor: the
deck producer refuses over-length / control-character ``--client`` values
fail-closed (``vendor/deck-producer/build/inline.mjs``, CLIENT-TOO-LONG /
CLIENT-CONTROL-CHARS -- beside the ADDR-NON-CANONICAL gate).

Owned module, deliberately beside ``deck_manifests.py`` and never inside
``vendor/`` (the vendored producer tree is an upstream drop whose upgrade path
re-vendors wholesale -- policy must live in the owned src tree).
"""

from __future__ import annotations

import re

#: Maximum renderable display-name length in Unicode code points. Matches the
#: PR-1 template clamp bound EXACTLY (the ``.dc.html`` covers clamp at 140 code
#: points -- JS spread semantics -- with an honest visible cut; Python ``len``
#: on ``str`` counts the same code points). Above this, the cover cannot render
#: the name whole, so the gate refuses rather than let a clamp cut it.
MAX_PERSONALIZATION_LENGTH = 140

#: How many leading characters of a refused value survive masking (G12 mask:
#: first 8 chars + ellipsis).
_MASK_VISIBLE_CHARS = 8

#: The closed detail vocabulary (positive enumeration -- no fourth value).
KNOWN_DETAILS: frozenset[str] = frozenset({"nomenclature_internal", "placeholder", "too_long"})

# Internal-plane nomenclature markers (the ``nomenclature_internal`` arm):
# a recognized operational prefix word bound by ``:`` or ``-`` (the exact live
# leak class: "PLAY: ..."; a clinic legitimately NAMED "Playa ..." is untouched
# because the separator is required).
_INTERNAL_PREFIX_RE = re.compile(r"^\s*(PLAY|TASK|OB|TEST|INTERNAL)\b\s*[:\-]")
# A gid-shaped digit run: Asana gids are long numeric strings (live receipts:
# 1216243790085943, 1213653428400851 -- 16 digits). 13+ consecutive digits is
# never part of a legitimate display name; shorter runs (phone fragments,
# "24-7", street numbers) pass.
_EMBEDDED_GID_RE = re.compile(r"\d{13,}")
# An internal template-path fragment (the S5 leak class: "templates/...").
_TEMPLATES_PATH_RE = re.compile(r"templates/", re.IGNORECASE)
# The internal-nomenclature shape "ALLCAPS-PREFIX — remainder": a leading
# segment with at least one letter and NO lowercase, terminated by the
# space-em-dash-space separator internal task names use. A mixed-case segment
# before an em-dash (a real name like "Salt — Lake ...") does not match.
_ALLCAPS_EMDASH_RE = re.compile(r"^\s*[^a-z—]*[A-Z][^a-z—]*\s—\s")


class PersonalizationError(Exception):
    """A personalization value failed the customer-content gate (fail-closed).

    Carries the MASKED value only (first 8 chars + ellipsis) -- the full value
    never rides the exception, its ``str()``, or any log line built from it.

    ``detail`` is the closed vocabulary in :data:`KNOWN_DETAILS`:

    * ``"nomenclature_internal"`` -- operational-plane material in the value;
    * ``"placeholder"`` -- the "Clinic" generic or empty-after-strip;
    * ``"too_long"`` -- above :data:`MAX_PERSONALIZATION_LENGTH` code points.
    """

    def __init__(self, value_masked: str, detail: str, message: str | None = None) -> None:
        self.value_masked = value_masked
        self.detail = detail
        super().__init__(message or f"personalization value {value_masked!r} refused: {detail}")


def mask_personalization_value(value: str) -> str:
    """Mask a personalization value for logs/errors: first 8 chars + ellipsis.

    The same mask the G12 C-BN1-05 audit record carries (``client_name``), so a
    denied value and an attached value are correlatable without ever spilling a
    display name (or a leaked internal string) in full.
    """
    if len(value) <= _MASK_VISIBLE_CHARS:
        return value
    return value[:_MASK_VISIBLE_CHARS] + "…"


def assert_customer_personalization(client_name: str) -> None:
    """Fail-closed content gate: raise unless ``client_name`` is customer-plane.

    Order of arms: the placeholder arms (empty / "Clinic") first, then the
    nomenclature markers, then the length bound -- so a value that is BOTH
    internal-shaped and over-length reports the more diagnostic
    ``nomenclature_internal``.

    Args:
        client_name: the candidate customer-facing display name (the value the
            producer would freeze into the cover's "Prepared for" line).

    Raises:
        PersonalizationError: with the masked value and a closed-vocab detail.
    """
    value = (client_name or "").strip()
    masked = mask_personalization_value(value)
    if not value or value.lower() == "clinic":
        raise PersonalizationError(masked, "placeholder")
    if (
        _INTERNAL_PREFIX_RE.search(value)
        or _EMBEDDED_GID_RE.search(value)
        or _TEMPLATES_PATH_RE.search(value)
        or _ALLCAPS_EMDASH_RE.search(value)
    ):
        raise PersonalizationError(masked, "nomenclature_internal")
    if len(value) > MAX_PERSONALIZATION_LENGTH:
        raise PersonalizationError(masked, "too_long")
