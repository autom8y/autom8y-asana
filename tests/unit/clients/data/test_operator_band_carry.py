"""Guard-PRESENCE tests for the operator-batch band carry (Sprint 5, client seam).

provenance-to-the-human Sprint 5 (the-band-itself): the typed ``band`` sibling
(BAND-MECHANISM §6.1/§6.2) rides the per-phone ``data.meta`` block alongside
``weights_version`` / ``coverage`` and is folded to RESPONSE/META grain by
``distribute_per_office_meta`` + ``_merge_batch_metas``. These tests assert the
carry EXISTS and its declared-absence discipline holds at the transport:

  - the typed mirror parses the emitted six-key shape VERBATIM;
  - a malformed block is DECLARED ABSENT (``band=None``) -- never a throw at
    the passthrough transport (§2.1 corollary);
  - the C1 VALUE fence is deliberately NOT re-asserted here: a laundered
    interval with a well-FORMED shape is carried through, so the render-side
    refusal seam (``formatter._band_line_html``, FIRE-SEAM BAND-C1) is the one
    reachable refusal point for the adversarial-disprover's Arm-1 mutation;
  - first-observer at batch grain + first-non-None at run-merge grain mirror
    the coverage/synced_at rules (one weight scheme -- one band -- per batch).

CRITIC-NEVER-AUTHOR: authored by the carry's BUILDER; presence only. The
two-sided §7.5 fixture is S5-F's with the adversarial-disprover.
"""

from __future__ import annotations

from typing import Any

from autom8_asana.clients.data._endpoints.operator import (
    OperatorBatchMeta,
    WeightIgnoranceBand,
    _band_from_meta_block,
    _merge_batch_metas,
    distribute_per_office_meta,
)

_CURRENT_VERSION = "2026-03-24-static-UNRATIFIED"

# The emitted honest-band wire shape (exact six keys, data plane §build-receipt).
_WIRE_BAND: dict[str, Any] = {
    "status": "ignorance_overlay",
    "lower": 0.0,
    "upper": 1.0,
    "overlay_direction": "understate",
    "overlay_citation": "WORM-LEDGER §1.1 / BAND-MECHANISM §2",
    "scheme_version": _CURRENT_VERSION,
}


def _envelope_with_meta(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": {
            "results": [
                {
                    "status": "success",
                    "phone": "+1",
                    "data": {"result_type": "result", "data": [], "meta": meta},
                }
            ]
        }
    }


class TestBandParse:
    """_band_from_meta_block parses the emitted shape verbatim, typed."""

    def test_overlay_band_parsed_verbatim(self) -> None:
        band = _band_from_meta_block({"band": dict(_WIRE_BAND)})
        assert band == WeightIgnoranceBand(
            status="ignorance_overlay",
            scheme_version=_CURRENT_VERSION,
            lower=0.0,
            upper=1.0,
            overlay_direction="understate",
            overlay_citation="WORM-LEDGER §1.1 / BAND-MECHANISM §2",
        )

    def test_no_band_applicable_parsed(self) -> None:
        band = _band_from_meta_block(
            {
                "band": {
                    "status": "no_band_applicable",
                    "lower": None,
                    "upper": None,
                    "overlay_direction": None,
                    "overlay_citation": None,
                    "scheme_version": _CURRENT_VERSION,
                }
            }
        )
        assert band is not None
        assert band.status == "no_band_applicable"
        assert band.lower is None
        assert band.overlay_direction is None

    def test_absent_band_is_declared_none(self) -> None:
        assert _band_from_meta_block({"weights_version": _CURRENT_VERSION}) is None

    def test_malformed_shapes_yield_none_never_throw(self) -> None:
        # Each malformed shape is a declared absence at the transport --
        # NEVER a throw (§2.1 corollary), NEVER a partially-fabricated band.
        malformed: list[Any] = [
            "not-a-dict",
            [],
            42,
            {"status": "confidence_interval", "scheme_version": _CURRENT_VERSION},
            {"status": "ignorance_overlay"},  # scheme_version missing (§4)
            {"status": "ignorance_overlay", "scheme_version": 123},
            {"status": "ignorance_overlay", "scheme_version": ""},
            {
                "status": "ignorance_overlay",
                "scheme_version": _CURRENT_VERSION,
                "overlay_direction": "sideways",  # out-of-vocabulary token
            },
            {
                "status": "ignorance_overlay",
                "scheme_version": _CURRENT_VERSION,
                "overlay_citation": ["not", "a", "str"],
            },
        ]
        for raw in malformed:
            assert _band_from_meta_block({"band": raw}) is None

    def test_laundered_interval_with_wellformed_shape_is_carried(self) -> None:
        # The C1 VALUE fence is NOT the transport's: a well-FORMED band carrying
        # the REFUSED Wilson ribbon parses and is carried through, so the
        # render-side C1 refusal (FIRE-SEAM BAND-C1) is reachable by the
        # disprover's Arm-1 mutation instead of being silently swallowed here.
        laundered = dict(_WIRE_BAND, lower=0.3093, upper=0.3150)
        band = _band_from_meta_block({"band": laundered})
        assert band is not None
        assert band.lower == 0.3093
        assert band.upper == 0.3150


class TestBatchGrainCarry:
    """distribute_per_office_meta folds the band at RESPONSE/META grain."""

    def test_band_extracted_alongside_weights_version(self) -> None:
        body = _envelope_with_meta({"weights_version": _CURRENT_VERSION, "band": dict(_WIRE_BAND)})
        meta = distribute_per_office_meta(body)
        assert meta.weights_version == _CURRENT_VERSION
        assert meta.band is not None
        assert meta.band.status == "ignorance_overlay"
        assert meta.band.scheme_version == _CURRENT_VERSION

    def test_bandless_batch_yields_declared_none(self) -> None:
        meta = distribute_per_office_meta(
            _envelope_with_meta({"weights_version": _CURRENT_VERSION})
        )
        assert meta.band is None

    def test_band_only_batch_is_not_collapsed_to_empty(self) -> None:
        # A batch carrying ONLY a band still yields a non-empty meta (the
        # emptiness collapse names band as a first-class provenance field).
        meta = distribute_per_office_meta(_envelope_with_meta({"band": dict(_WIRE_BAND)}))
        assert meta != OperatorBatchMeta()
        assert meta.band is not None

    def test_first_observed_meta_owns_the_batch_band(self) -> None:
        # One weight scheme -- one band -- per execute-batch (§6.2): the FIRST
        # observed per-phone meta owns it, mirroring the coverage rule.
        body = _envelope_with_meta({"band": dict(_WIRE_BAND)})
        second = dict(_WIRE_BAND, overlay_citation="second-office-citation")
        body["data"]["results"].append(
            {
                "status": "success",
                "phone": "+2",
                "data": {"result_type": "result", "data": [], "meta": {"band": second}},
            }
        )
        meta = distribute_per_office_meta(body)
        assert meta.band is not None
        assert meta.band.overlay_citation == "WORM-LEDGER §1.1 / BAND-MECHANISM §2"

    def test_default_meta_band_is_none(self) -> None:
        assert OperatorBatchMeta().band is None


class TestRunMergeCarry:
    """_merge_batch_metas reduces the band across sub-batches, first-non-None."""

    def test_first_nonnone_band_owns_the_run(self) -> None:
        band = _band_from_meta_block({"band": dict(_WIRE_BAND)})
        merged = _merge_batch_metas([OperatorBatchMeta(), OperatorBatchMeta(band=band)])
        assert merged.band is band

    def test_all_absent_collapses_to_none(self) -> None:
        merged = _merge_batch_metas([OperatorBatchMeta(), OperatorBatchMeta()])
        assert merged.band is None

    def test_band_rides_alongside_existing_siblings_unchanged(self) -> None:
        band = _band_from_meta_block({"band": dict(_WIRE_BAND)})
        merged = _merge_batch_metas(
            [
                OperatorBatchMeta(
                    weights_version=_CURRENT_VERSION,
                    synced_at="2026-07-13T00:00:00Z",
                    band=band,
                )
            ]
        )
        assert merged.weights_version == _CURRENT_VERSION
        assert merged.synced_at == "2026-07-13T00:00:00Z"
        assert merged.band is band
