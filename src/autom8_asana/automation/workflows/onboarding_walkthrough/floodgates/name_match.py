"""D9 clinic-name confirmation for the floodgates produce step.

Ratified decision D9: the agent proceeds only if the name in the PLAY card title matches
the parent Business task's name; on a mismatch it stops and asks the operator. D1 adds
that the frozen clinic name is never wrong, so the operator's ``--clinic`` string is a
third witness that must agree too. Design of record: FORK-S1 (option 5 + 6a, phone path
refused).

Three strings take part:

* **T** -- ``clinic_from_play_name(title)``, the clinic part of the PLAY title;
* **B** -- the parent Business task's ``name``, read in the SAME walk that supplies the
  Company ID (``BusinessResolution.business_name``);
* **C** -- the ``--clinic`` argument.

The rule forgives only differences that cannot render differently (Unicode NFC form,
zero-width characters, runs of whitespace) and refuses every visible one: case, spelling,
a suffix, a location qualifier. NFKC is deliberately NOT used: it folds visible
compatibility characters (full-width forms, ligatures). There is no override flag: under
the standing grant (D7) an agent could approve itself, and D9 says ask.

``clinic_from_play_name`` lives here (re-exported by ``batch``) so the runner can import
the predicate without an import cycle through ``batch``.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import PLAY_NAME_RE

if TYPE_CHECKING:
    from autom8_asana.automation.workflows.onboarding_walkthrough.office_resolution import (
        BusinessResolution,
    )

logger = get_logger(__name__)

__all__ = [
    "ClinicNameMismatch",
    "assert_clinic_name_confirmed",
    "canon",
    "clinic_from_play_name",
]

# Zero-width characters that never render. U+200D (zero-width joiner) is NOT in this set:
# it binds emoji sequences, so stripping it would freeze a different glyph sequence than
# the Business name shows. A ZWJ-only difference therefore refuses (D1).
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u2060\ufeff"))
# Whitespace that renders as a plain gap: ASCII whitespace plus the two no-break spaces.
# Not str.split(): that folds every Unicode White_Space character, including U+1680
# (Ogham space mark), which has a visible glyph.
_PLAIN_WHITESPACE = re.compile(r"[ \t\n\r\f\v\u00a0\u202f]+")
_LEADING_SEPARATORS = re.compile(r"^[\s—–:-]+")


def clinic_from_play_name(name: str | None) -> str | None:
    """Suggest a clinic name from a PLAY title; None when the title is not a PLAY.

    ``"PLAY: Custom Calendar Integration — X"`` -> ``"X"``. Zero-width characters are
    dropped, whitespace is collapsed and leading separators are stripped. The produce step
    confirms this against the Business name and ``--clinic`` (D9) before anything freezes.
    """
    if not name:
        return None
    match = PLAY_NAME_RE.search(name)
    if match is None:
        return None
    rest = name[match.end() :].translate(_ZERO_WIDTH)
    rest = _PLAIN_WHITESPACE.sub(" ", _LEADING_SEPARATORS.sub("", rest)).strip()
    return rest or None


def canon(s: str | None) -> str:
    """Canonical form for the D9 comparison: NFC, drop zero-width, collapse whitespace.

    Only differences that cannot render differently are removed. Case, punctuation and
    every visible character survive, so they still count as a mismatch.
    """
    s = unicodedata.normalize("NFC", s or "").translate(_ZERO_WIDTH)
    return _PLAIN_WHITESPACE.sub(" ", s).strip()


class ClinicNameMismatch(RuntimeError):
    """D9 refusal: the clinic name cannot be confirmed, so produce stops and asks.

    Raised when the PLAY has no Business parent, or when the title's clinic part, the
    Business name and ``--clinic`` do not all agree under :func:`canon`. NOT transient:
    re-running reproduces it until the record is fixed or the operator answers. A
    ``RuntimeError`` subclass, so the batch records it as ``failed`` and exits non-zero.
    """


def assert_clinic_name_confirmed(
    *,
    play_gid: str,
    title: str | None,
    resolution: BusinessResolution,
    clinic_arg: str,
) -> str:
    """Confirm T == B == C under :func:`canon`; return canonical B (the name to freeze).

    Args:
        play_gid: the PLAY task gid (carried on the refusal).
        title: the PLAY task title, as returned by the produce preflight.
        resolution: the hierarchy walk result for this PLAY (one walk supplies both the
            Business name and the Company ID).
        clinic_arg: the operator's ``--clinic`` string (or the manifest's recorded clinic
            on the already-produced path).

    Returns:
        ``canon(resolution.business_name)``, the string to freeze as the client name.

    Raises:
        ClinicNameMismatch: no Business parent (a phone match is not a parent), an empty
            Business name or title clinic part, or any visible disagreement among the three.
            The message carries the gids and all three strings via ``ascii()`` so NFD and
            zero-width differences show; the structured log event carries gids only.
    """
    t = clinic_from_play_name(title)
    if resolution.method != "hierarchy" or not resolution.business_gid:
        logger.warning(
            "floodgates_d9_refused",
            play_gid=play_gid,
            business_gid=resolution.business_gid,
            reason="no_business_parent",
        )
        raise ClinicNameMismatch(
            f"D9: PLAY {play_gid} has no Business parent; the clinic name cannot be "
            "confirmed. Stopped; ask the operator."
        )
    b = resolution.business_name
    ct, cb, cc = canon(t), canon(b), canon(clinic_arg)
    if not ct or not cb or ct != cb or cc != cb:
        logger.warning(
            "floodgates_d9_refused",
            play_gid=play_gid,
            business_gid=resolution.business_gid,
            reason="name_mismatch",
        )
        raise ClinicNameMismatch(
            f"D9: name mismatch on PLAY {play_gid} / Business {resolution.business_gid}: "
            f"title={ascii(t)} business={ascii(b)} --clinic={ascii(clinic_arg)}. "
            "Stopped; ask the operator."
        )
    return cb
