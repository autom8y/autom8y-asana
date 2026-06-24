"""Regression tests: DefaultLogProvider must not crash on reserved LogRecord keys.

Cold-frame root cause (FAMILY-A, not auth):

The asana hierarchy-gap warm refresh re-reports any in-warm failure via the broad
``except Exception`` at ``dataframes/builders/hierarchy_warmer.py``. When the warm
path's stdlib ``DefaultLogProvider`` (``client._log_provider``, the default when no
custom provider is injected -- ``client.py:144``) is handed an ``extra`` dict that
carries a reserved ``LogRecord`` attribute key (e.g. ``name``, the shape of an
offer/business payload row), Python's ``logging.Logger.makeRecord`` raises
``KeyError("Attempt to overwrite 'name' in LogRecord")``. That KeyError aborts the
warm refresh, the offer frame stays COLD, and asana sheds ASR's
``POST /v1/query/offer/rows`` read as a 503.

The defect lives in ``DefaultLogProvider._sanitize_kwargs``: it sanitizes stray
``**kwargs`` (folding reserved keys into ``extra`` with a ``log_`` prefix) but it
NEVER sanitizes the ``extra`` dict itself, and it short-circuits entirely when no
stray ``**kwargs`` are present -- so a plain ``extra={"name": ...}`` call flows to
``makeRecord`` unguarded.

This module drives the REAL production provider (no mocked logger, no hand-rolled
``logging`` call) with a data-shaped ``extra`` dict. The fixtures are two-sided:

* Reserved-key fixtures (offer/business shape) MUST NOT raise after the fix; they
  are the RED-pre-fix surface and fire on the SPECIFIC reserved-key ``KeyError``.
* The anti-beg-question guard fixture carries only NON-reserved keys and MUST stay
  GREEN on both sides; if it ever goes RED the sanitizer is over-broad.

See: ``.know/scar-tissue.md`` (ASR offer-503 = cold frame); ``autom8y-asana
query503 cold-frame`` memory; PR #150 (the stdlib-chokepoint hardening this
extends from the ``**kwargs`` door to the ``extra`` door).
"""

from __future__ import annotations

import logging

import pytest

from autom8_asana._defaults.log import DefaultLogProvider

# Co-locate on a single xdist worker under --dist=loadgroup (pyproject.toml:110):
# all tests in this module mutate/observe the shared stdlib logger named
# "autom8_asana" and its handlers, so they must not interleave across workers.
pytestmark = [pytest.mark.xdist_group("default_log_provider_reserved_key")]


# The full set of stdlib LogRecord attributes that cannot appear as `extra` keys.
# A row fetched on the warm path (an offer/business payload) realistically carries
# "name"; the others are included so the sanitizer is proven complete, not just
# patched for the one key seen in the live crash.
_RESERVED_KEYS = (
    "name",
    "msg",
    "module",
    "levelname",
    "message",
)


class TestDefaultLogProviderReservedKeyExtra:
    """The canonical stdlib chokepoint must survive reserved-key ``extra`` dicts.

    These exercise the production ``DefaultLogProvider`` API directly -- the same
    object that ``AsanaClient`` wires as ``self._log_provider`` and hands to the
    transport / ``@error_handler`` on the warm read path. The ``extra`` dict is a
    plain data fixture (offer/business row shape), so the test cannot beg the
    question by mocking the logger.
    """

    @pytest.mark.parametrize("reserved_key", _RESERVED_KEYS)
    def test_info_with_reserved_key_in_extra_does_not_crash(self, reserved_key: str) -> None:
        """``info(..., extra={<reserved>: ...})`` must not raise (warm-path shape).

        RED pre-fix: ``KeyError("Attempt to overwrite '<reserved>' in LogRecord")``
        propagates out of ``makeRecord`` because ``_sanitize_kwargs`` does not
        sanitize ``extra`` and short-circuits on empty ``**kwargs``.
        GREEN post-fix: the reserved key is folded to a ``log_`` prefix and the
        call completes.
        """
        provider = DefaultLogProvider(level=logging.DEBUG)

        # Shape of a real offer/business row fetched during hierarchy warm.
        offer_row_extra = {reserved_key: "Q3 Offer Bundle", "gid": "1143843662099250"}

        # Must NOT raise. If it raises the reserved-key KeyError, that IS the bug.
        try:
            provider.info("hierarchy_gap_warming_parent", extra=offer_row_extra)
        except KeyError as exc:  # pragma: no cover - this branch is the failure signal
            assert f"Attempt to overwrite '{reserved_key}' in LogRecord" in str(exc), (
                "Expected the reserved-key collision KeyError specifically; "
                f"got a different KeyError: {exc!r}"
            )
            pytest.fail(
                f"DefaultLogProvider.info crashed on reserved extra key {reserved_key!r}: "
                f"{exc!r}. This is the cold-frame warm-refresh crash."
            )

    def test_warning_with_reserved_name_in_extra_does_not_crash(self) -> None:
        """``warning(..., extra={'name': ...})`` must not raise.

        The warm broad-except re-report path is a ``.warning`` call; this pins the
        warning surface specifically.
        """
        provider = DefaultLogProvider(level=logging.DEBUG)
        try:
            provider.warning(
                "hierarchy_gap_warming_failed",
                extra={"name": "Offer Parent", "project_gid": "1143843662099250"},
            )
        except KeyError as exc:  # pragma: no cover - failure signal
            assert "Attempt to overwrite 'name' in LogRecord" in str(exc)
            pytest.fail(f"warning() crashed on reserved extra key 'name': {exc!r}")

    def test_reserved_key_value_is_preserved_under_safe_prefix(self) -> None:
        """The colliding value must survive, relocated to a ``log_``-prefixed key.

        Sanitization must not silently drop data -- the offer name still needs to
        appear in the structured record so observability is not blinded.
        """
        provider = DefaultLogProvider(level=logging.DEBUG)
        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _Capture()
        provider._logger.addHandler(handler)
        try:
            provider.info("warm_parent", extra={"name": "Offer Parent", "gid": "123"})
        finally:
            provider._logger.removeHandler(handler)

        assert len(records) == 1
        rec = records[0]
        # The reserved key was relocated, not dropped: value preserved under log_name.
        assert rec.log_name == "Offer Parent"
        assert rec.gid == "123"
        # And the stdlib LogRecord.name (the logger name) is intact, not clobbered.
        assert rec.name == "autom8_asana"


class TestDefaultLogProviderNonReservedExtraStaysGreen:
    """Anti-beg-question guard: NON-reserved ``extra`` keys must pass through clean.

    These MUST be GREEN both pre- and post-fix. If they ever go RED, the
    sanitizer is over-broad (mangling legitimate keys), which is a different bug
    than the cold-frame crash.
    """

    def test_non_reserved_extra_passes_through_unchanged(self) -> None:
        """A warm-path ``extra`` with only safe keys must not be mangled."""
        provider = DefaultLogProvider(level=logging.DEBUG)
        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _Capture()
        provider._logger.addHandler(handler)
        try:
            # Real reserved-clean warm extra (cf. unified.py / hierarchy_warmer.py).
            provider.info(
                "hierarchy_gap_warming_complete",
                extra={
                    "project_gid": "1143843662099250",
                    "entity_type": "offer",
                    "attempted": 3,
                    "fetched": 3,
                },
            )
        finally:
            provider._logger.removeHandler(handler)

        assert len(records) == 1
        rec = records[0]
        # Untouched: no log_-prefix rewriting for non-reserved keys.
        assert rec.project_gid == "1143843662099250"
        assert rec.entity_type == "offer"
        assert rec.attempted == 3
        assert rec.fetched == 3
        assert not hasattr(rec, "log_project_gid")

    def test_stray_kwarg_sanitization_unchanged(self) -> None:
        """The pre-existing ``**kwargs`` sanitization (PR #150) still works.

        Reserved keys arriving as stray kwargs (e.g. from ``autom8y_http``) must
        continue to be folded to a ``log_`` prefix without raising. This guards
        against regressing the door PR #150 already closed.
        """
        provider = DefaultLogProvider(level=logging.DEBUG)
        # Must not raise: stray reserved kwarg gets the log_ prefix.
        provider.info("transport_evt", name="OfferParent")
