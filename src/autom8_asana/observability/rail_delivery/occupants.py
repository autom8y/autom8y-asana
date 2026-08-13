"""Channel-occupant registry — the reserved-token source of truth for D-1..D-4.

EX-6 of the exec-insight-delivery wave (shape
``.sos/wip/frames/exec-insight-delivery.shape.md`` §EX-6, L414-472). Design limb.

Why this module exists
----------------------
``#account-health`` is NOT a dark channel. It carries an alert on every abort
tick (6x/day at ``cron(0 */4 * * ? *)``). The design problem for a recurring
readout is therefore *co-tenancy*, not silence
(``RAILS-insight-delivery-verified-2026-08-12.md:570-586``).

The codebase already solved this exact class of problem and wrote down the rule
(``report.py:70-76`` AMENDMENT-001 D-6, quoted verbatim at ``RAILS…:591-596``):

    "One glyph carrying two meanings inside one block is a legibility defect."

Generalised: **one token, one meaning, channel-wide.** This module encodes the
tokens each live occupant already claims, so a readout can be authored to reuse
none of them. It is the reserved registry the four distinguishability duties
(``distinguishability.py``) check against.

Provenance and SVR posture
--------------------------
The occupant tokens below are transcribed from the probed inventory at
``RAILS…:576-607`` (§5.1 table + the D-1..D-4 requirement table). That table in
turn cites monorepo anchors (``orchestrator.py:1330-1359``, ``report.py:264-269``,
``:226``) that live in the ``autom8y`` monorepo and are NOT readable from this
repo (monorepo-boundary fence; the ASR service is out of scope for this PR). The
in-repo authoritative anchor is therefore RAILS §5.1, cited per field.

``sdk_severity_glyphs_complete=False`` records the one honest gap: the full set
of SDK severity glyphs (beyond the verbatim-known ``:warning:`` == ``Severity.HIGH``)
is a monorepo fact. It is left as an injectable, extend-only set rather than
guessed — a readout picks a glyph manifestly outside any severity/truncation
family (e.g. ``:bar_chart:``), and the monorepo wiring can pass the authoritative
set at application time.

    [UV-P: the exhaustive set of ASR SDK severity glyphs emitted into
    #account-health beyond :warning: | METHOD: read the autom8y_reconciliation
    report.py _severity_emoji mapping at origin/main (monorepo) | REASON: the
    reconciliation SDK is not a dependency of autom8y-asana and is not importable
    here; the monorepo is out of scope for this PR. The reserved-alert set is
    seeded with the verbatim-known :warning: and left extend-only so the
    application limb can pass the full set without a code change.]
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class ChannelOccupants:
    """The tokens already claimed by live occupants of a shared channel.

    A readout is *distinguishable* iff it reuses none of these at the surface
    the duty governs. ``reserved_identity_glyphs`` is derived: an identity glyph
    may be neither an alert glyph nor the truncation glyph, because a readout
    headed by either reads as an alert or a truncation rather than a report.
    """

    #: Header prefixes any live occupant opens with. D-1 forbids a readout header
    #: that begins with any of these (compared normalised: lowercased, leading
    #: glyphs/punctuation stripped). RAILS…:604 — both live occupants open with
    #: "Account Status Reconciliation".
    reserved_header_prefixes: tuple[str, ...]

    #: Context-footer producer strings a live occupant already attributes itself
    #: with. D-3 forbids reusing these. RAILS…:606 —
    #: "account-status-recon | readiness gate".
    reserved_footer_producers: tuple[str, ...]

    #: Fallback-``text`` prefixes a live occupant opens its notification line
    #: with. D-4 forbids a readout ``text`` that opens with any of these.
    #: RAILS…:607 — "Account status reconciliation aborted: ...".
    reserved_text_prefixes: tuple[str, ...]

    #: Glyphs that carry a fixed alert meaning and MUST NOT appear anywhere in a
    #: readout (a stray one reads as an alert). Seeded with :warning: (==
    #: Severity.HIGH, RAILS…:605); extend-only pending the SDK severity set.
    reserved_alert_glyphs: frozenset[str]

    #: The channel's truncation token — one meaning, channel-wide. A readout may
    #: use it ONLY on a truncation marker (never as its identity glyph).
    #: RAILS…:593-596 — :scissors: "is unambiguous and reads as truncation".
    truncation_glyph: str = ":scissors:"

    #: False => ``reserved_alert_glyphs`` is a verbatim-known seed, not the
    #: exhaustive SDK severity set (see module UV-P).
    sdk_severity_glyphs_complete: bool = False

    #: A source anchor carried on the registry so a receipt can cite where the
    #: reserved tokens came from.
    provenance: str = field(default="RAILS-insight-delivery-verified-2026-08-12.md:576-607 (§5.1)")

    @property
    def reserved_identity_glyphs(self) -> frozenset[str]:
        """Glyphs a readout may not adopt as its identity: alert ∪ truncation."""
        return self.reserved_alert_glyphs | {self.truncation_glyph}

    def with_sdk_severity_glyphs(self, glyphs: frozenset[str] | set[str]) -> ChannelOccupants:
        """Return a copy with the authoritative SDK severity set folded in.

        The application limb (monorepo wiring) calls this once it can read the
        real ``_severity_emoji`` mapping, flipping ``sdk_severity_glyphs_complete``.
        """
        return replace(
            self,
            reserved_alert_glyphs=self.reserved_alert_glyphs | frozenset(glyphs),
            sdk_severity_glyphs_complete=True,
        )


# The reserved registry for #account-health, seeded from RAILS §5.1 (probed,
# verbatim). This is the ``occupants`` default every duty check runs against.
DEFAULT_ACCOUNT_HEALTH_OCCUPANTS = ChannelOccupants(
    reserved_header_prefixes=("account status reconciliation",),
    reserved_footer_producers=(
        "account-status-recon | readiness gate",
        "account-status-recon",
    ),
    reserved_text_prefixes=("account status reconciliation",),
    reserved_alert_glyphs=frozenset({":warning:"}),
    truncation_glyph=":scissors:",
    sdk_severity_glyphs_complete=False,
)
