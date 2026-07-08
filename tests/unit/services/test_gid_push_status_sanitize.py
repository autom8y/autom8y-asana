"""Tests for _sanitize_status_entries per-row snapshot guards (sprint-C6, T2).

The receiver (autom8y-data /api/v1/account-status/sync) is a transactional
snapshot-replace with extra="forbid" entry validation (E.164 OfficePhoneField)
and a uq_phone_vertical_pipeline UNIQUE constraint. Without per-row guards,
ONE defective row 422s (invalid phone) or rolls back (intra-snapshot duplicate
grain) the ENTIRE snapshot. The guards drop the ROW, never the snapshot.

Two-sided per the discriminating-canary doctrine: the guard bites ONLY on the
defect (broken rows dropped, push proceeds) and the all-valid positive control
passes through with ZERO skips and ZERO skip metrics.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, patch

from autom8_asana.services.gid_push import (
    SKIP_CLASS_DUP_GRAIN,
    SKIP_CLASS_INVALID_PHONE,
    _sanitize_status_entries,
    push_status_to_data_service,
)

_GID_PUSH_MODULE = "autom8_asana.services.gid_push"


def _entry(
    phone: str = "+15551230001",
    vertical: str = "chiropractor",
    pipeline_type: str = "unit",
    section: str = "Active",
) -> dict[str, Any]:
    return {
        "phone": phone,
        "vertical": vertical,
        "pipeline_type": pipeline_type,
        "account_activity": "active",
        "pipeline_section": section,
        "stage_entered_at": "2026-07-08T00:00:00+00:00",
    }


class TestSanitizeStatusEntries:
    """Direct unit tests of the pure sanitizer."""

    def test_broken_rows_are_dropped_not_snapshot_fatal(self) -> None:
        """[valid, invalid-phone, dup-of-valid-grain] -> ONLY the valid row kept."""
        valid = _entry()
        bad_phone = _entry(phone="555-1234")
        dup_grain = _entry(section="Month 1")  # same (phone, vertical, pipeline_type)

        with (
            patch(f"{_GID_PUSH_MODULE}.emit_metric") as mock_emit,
            patch(f"{_GID_PUSH_MODULE}.logger") as mock_logger,
        ):
            result = _sanitize_status_entries([valid, bad_phone, dup_grain])

        assert result == [valid]

        # status_push_rows_skipped logged with honest counts
        warn_calls = [
            c for c in mock_logger.warning.call_args_list if c.args[0] == "status_push_rows_skipped"
        ]
        assert len(warn_calls) == 1
        extra = warn_calls[0].kwargs["extra"]
        assert extra["invalid_phone_count"] == 1
        assert extra["dup_grain_count"] == 1
        assert extra["kept_count"] == 1

        # StatusPushRowsSkipped emitted once per skip_class
        skip_emits = {
            c.kwargs["dimensions"]["skip_class"]: c.args[1]
            for c in mock_emit.call_args_list
            if c.args[0] == "StatusPushRowsSkipped"
        }
        assert skip_emits == {
            SKIP_CLASS_INVALID_PHONE: 1,
            SKIP_CLASS_DUP_GRAIN: 1,
        }

    def test_positive_control_all_valid_passes_with_zero_skips(self) -> None:
        """Teeth (discriminating-canary doctrine): the guard bites ONLY on the
        defect -- an all-valid snapshot passes through untouched, ZERO skips,
        ZERO skip metrics, ZERO warnings."""
        entries = [
            _entry(phone="+15551230001"),
            _entry(phone="+15551230002"),
            _entry(phone="+15551230001", pipeline_type="sales"),  # different grain
        ]

        with (
            patch(f"{_GID_PUSH_MODULE}.emit_metric") as mock_emit,
            patch(f"{_GID_PUSH_MODULE}.logger") as mock_logger,
        ):
            result = _sanitize_status_entries(entries)

        assert result == entries
        assert not [c for c in mock_emit.call_args_list if c.args[0] == "StatusPushRowsSkipped"], (
            "positive control must emit ZERO skip metrics"
        )
        assert not [
            c for c in mock_logger.warning.call_args_list if c.args[0] == "status_push_rows_skipped"
        ], "positive control must log ZERO skip warnings"

    def test_e164_pattern_is_the_receivers_pattern(self) -> None:
        """The guard imports E164_PHONE_PATTERN from autom8y_api_schemas (the
        SAME pattern the receiver's OfficePhoneField enforces) -- spot-check
        agreement on representative accept/reject cases."""
        accepted = _sanitize_status_entries([_entry(phone="+15551234567")])
        assert len(accepted) == 1

        for bad in ["555-1234", "15551234567", "+05551234567", "", "+1 555 123 4567"]:
            with (
                patch(f"{_GID_PUSH_MODULE}.emit_metric"),
                patch(f"{_GID_PUSH_MODULE}.logger"),
            ):
                assert _sanitize_status_entries([_entry(phone=bad)]) == []

    def test_dedupe_keeps_first_occurrence(self) -> None:
        """Deterministic FIRST-occurrence keep on the dup grain."""
        first = _entry(section="Active")
        second = _entry(section="Consulting")

        with (
            patch(f"{_GID_PUSH_MODULE}.emit_metric"),
            patch(f"{_GID_PUSH_MODULE}.logger"),
        ):
            result = _sanitize_status_entries([first, second])

        assert result == [first]

    def test_non_string_phone_is_dropped_not_raised(self) -> None:
        """Never raises; pure function of entries."""
        with (
            patch(f"{_GID_PUSH_MODULE}.emit_metric"),
            patch(f"{_GID_PUSH_MODULE}.logger"),
        ):
            assert _sanitize_status_entries([_entry() | {"phone": None}]) == []
            assert _sanitize_status_entries([{"vertical": "x", "pipeline_type": "unit"}]) == []

    def test_rejected_phone_never_logged_raw(self) -> None:
        """XR-003: NO substring of a rejected phone reaches the log call.

        This is deliberately NOT a mask_pii_in_string test: that masker only
        matches E.164-ish shapes (``\\+\\d{10,15}``), and the values rejected
        here are precisely the ones that FAILED that shape -- masking them is
        a guaranteed no-op. The contract is therefore structural: the warning
        carries a shape descriptor ONLY, and the raw value (or its digits)
        must not appear ANYWHERE in the logged payload. Fixtures are the
        real-world formatted/plus-less shapes the QA lens proved unmaskable.
        """
        for raw_phone in ["(415) 555-2671", "415-555-2671", "07911 123456", "5551234567"]:
            with (
                patch(f"{_GID_PUSH_MODULE}.emit_metric"),
                patch(f"{_GID_PUSH_MODULE}.logger") as mock_logger,
            ):
                assert _sanitize_status_entries([_entry(phone=raw_phone)]) == []

            warn_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if c.args[0] == "status_push_rows_skipped"
            ]
            assert len(warn_calls) == 1
            extra = warn_calls[0].kwargs["extra"]

            # The whole logged payload, flattened: the raw phone and even its
            # bare digit string must be absent.
            flattened = repr(extra)
            digits = "".join(ch for ch in raw_phone if ch.isdigit())
            assert raw_phone not in flattened, f"raw phone {raw_phone!r} leaked into log"
            assert digits not in flattened, f"phone digits of {raw_phone!r} leaked into log"

            # The shape descriptor carries triage structure, not the value.
            shape = extra["sample_shape"]
            assert shape == {
                "type": "str",
                "length": len(raw_phone),
                "has_plus": raw_phone.startswith("+"),
                "digit_count": len(digits),
            }

    def test_non_string_phone_shape_carries_type_only(self) -> None:
        """A non-str rejected phone logs only its type name -- nothing else."""
        with (
            patch(f"{_GID_PUSH_MODULE}.emit_metric"),
            patch(f"{_GID_PUSH_MODULE}.logger") as mock_logger,
        ):
            assert _sanitize_status_entries([_entry() | {"phone": 4155552671}]) == []

        warn_calls = [
            c for c in mock_logger.warning.call_args_list if c.args[0] == "status_push_rows_skipped"
        ]
        extra = warn_calls[0].kwargs["extra"]
        assert extra["sample_shape"] == {"type": "int"}
        assert "4155552671" not in repr(extra)


class TestPushStatusSanitizeIntegration:
    """Sanitizer wired into push_status_to_data_service before the empty check."""

    async def test_push_proceeds_with_only_valid_rows(self) -> None:
        """Broken payload rows are per-row skipped; the POST carries ONLY the
        valid row and entry_count integrity holds."""
        valid = _entry()
        entries = [valid, _entry(phone="555-1234"), _entry(section="Month 1")]

        env = {
            "AUTOM8Y_DATA_URL": "http://data.internal.test",
            "STATUS_PUSH_ENABLED": "true",
        }
        with (
            patch.dict(os.environ, env),
            patch(f"{_GID_PUSH_MODULE}._get_auth_token", return_value="test-token"),
            patch(f"{_GID_PUSH_MODULE}.emit_metric"),
            patch(
                f"{_GID_PUSH_MODULE}._push_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_transport,
        ):
            result = await push_status_to_data_service(
                entries=entries,
                source_timestamp="2026-07-08T00:00:00+00:00",
            )

        assert result is True
        mock_transport.assert_awaited_once()
        payload = mock_transport.call_args.kwargs["payload"]
        assert payload["entries"] == [valid]
        assert payload["entry_count"] == 1

    async def test_sanitize_emptied_list_falls_through_to_skip(self) -> None:
        """All rows dropped -> existing no_entries_to_push skip (returns True,
        no HTTP) -- but the rows-skipped warning already made it non-silent."""
        env = {
            "AUTOM8Y_DATA_URL": "http://data.internal.test",
            "STATUS_PUSH_ENABLED": "true",
        }
        with (
            patch.dict(os.environ, env),
            patch(f"{_GID_PUSH_MODULE}._get_auth_token", return_value="test-token"),
            patch(f"{_GID_PUSH_MODULE}.emit_metric"),
            patch(f"{_GID_PUSH_MODULE}.logger") as mock_logger,
            patch(
                f"{_GID_PUSH_MODULE}._push_to_data_service",
                new_callable=AsyncMock,
            ) as mock_transport,
        ):
            result = await push_status_to_data_service(
                entries=[_entry(phone="not-a-phone")],
                source_timestamp="2026-07-08T00:00:00+00:00",
            )

        assert result is True
        mock_transport.assert_not_awaited()
        events = [c.args[0] for c in mock_logger.warning.call_args_list]
        assert "status_push_rows_skipped" in events
        info_events = [
            c for c in mock_logger.info.call_args_list if c.args[0] == "status_push_skipped"
        ]
        assert any(c.kwargs["extra"]["reason"] == "no_entries_to_push" for c in info_events)
