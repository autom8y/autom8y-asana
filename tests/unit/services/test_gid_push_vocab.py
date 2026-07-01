"""Unit tests for the vocabulary-sync producer path (dyn-enum-contract sprint-1).

Implements the D-6 two-sided discriminating canary: the RED cases (C-EMPTY /
C-TRUNCATED) are deliberately-broken INPUTS the guard CORRECTLY REJECTS -- never
a defect injected into production code. The no-defect variant (C-HEALTHY) passes
the SAME guard GREEN. Discrimination: if C-HEALTHY ever REFUSES, or
C-EMPTY/C-TRUNCATED ever PUBLISH, the guard is miscalibrated.

Plus the projection/normalize (Lock-3 NAME-keying), the ship-dark flag (DEFAULT
OFF), and the operator-tunable truncation floor.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from autom8_asana.contracts import vocabulary_sync as vocabulary_sync_module
from autom8_asana.contracts.vocabulary_sync import VocabularyOption, VocabularySyncRequest
from autom8_asana.models.custom_field import CustomFieldEnumOption
from autom8_asana.services import gid_push as gid_push_module
from autom8_asana.services.gid_push import (
    GID_PUSH_ENABLED_ENV_VAR,
    STATUS_PUSH_ENABLED_ENV_VAR,
    VOCAB_DRIFT_REASON_DEGENERATE_NAME,
    VOCAB_DRIFT_REASON_DISABLED_OPTION,
    VOCAB_DRIFT_REASON_NAME_COLLISION,
    VOCAB_REFUSE_REASON_EMPTY,
    VOCAB_REFUSE_REASON_GROSS_TRUNCATION,
    VOCAB_SYNC_ENABLED_ENV_VAR,
    VOCAB_SYNC_MIN_OPTIONS_ENV_VAR,
    _get_vocab_sync_min_options,
    _is_vocab_sync_enabled,
    detect_vocab_drift,
    normalize_vertical_key,
    project_enum_options_to_vocabulary_options,
    push_vocabulary_to_data_service,
)

_PUSH_TARGET = "autom8_asana.services.gid_push._push_to_data_service"
_EMIT_TARGET = "autom8_asana.services.gid_push.emit_metric"
_HTTP_TARGET = "autom8_asana.services.gid_push.Autom8yHttpClient"
_DRIFT_OBSERVER_TARGET = "autom8_asana.services.gid_push.detect_vocab_drift"
_DRIFT_METRIC = "VocabSyncDriftDetected"


def _enum_option(
    name: str | None, *, gid: str = "1", enabled: bool = True
) -> CustomFieldEnumOption:
    """Build a realistic Asana enum option (WITH a gid -- to prove Lock-3 drops it)."""
    return CustomFieldEnumOption.model_validate({"gid": gid, "name": name, "enabled": enabled})


def _metric_dims(mock_emit: MagicMock, metric_name: str) -> list[dict[str, str]]:
    """Extract the dimensions dicts for every emit_metric call of metric_name."""
    return [
        call.kwargs.get("dimensions", {})
        for call in mock_emit.call_args_list
        if call.args and call.args[0] == metric_name
    ]


def _make_push_mocks(mock_http_cls: MagicMock, *, post_return: object) -> AsyncMock:
    """Build the two-layer Autom8yHttpClient mock chain (mirrors test_gid_push)."""
    mock_raw_client = AsyncMock()
    mock_raw_client.post.return_value = post_return

    mock_raw_cm = AsyncMock()
    mock_raw_cm.__aenter__.return_value = mock_raw_client

    mock_outer = MagicMock()
    mock_outer.raw.return_value = mock_raw_cm

    mock_http_cls.return_value = AsyncMock()
    mock_http_cls.return_value.__aenter__.return_value = mock_outer

    return mock_raw_client


# ============================================================================
# normalize_vertical_key (Lock-3 NAME-keying) -- pure, deterministic
# ============================================================================


class TestNormalizeVerticalKey:
    """The deterministic NAME-key normalizer."""

    def test_lowercases(self) -> None:
        assert normalize_vertical_key("Dental") == "dental"

    def test_strips_surrounding_whitespace(self) -> None:
        assert normalize_vertical_key("  Dental  ") == "dental"

    def test_collapses_internal_whitespace(self) -> None:
        assert normalize_vertical_key("General   Practice") == "general practice"

    def test_case_and_whitespace_variants_round_trip(self) -> None:
        """C-NAMEKEY core: display variants collapse to ONE stable key."""
        assert normalize_vertical_key("General Practice") == normalize_vertical_key(
            " general  practice "
        )

    def test_idempotent_on_already_normalized(self) -> None:
        once = normalize_vertical_key("General Practice")
        assert normalize_vertical_key(once) == once


# ============================================================================
# project_enum_options_to_vocabulary_options (the read projection)
# ============================================================================


class TestProjectEnumOptions:
    """Projection of the live option-SET onto the typed contract."""

    def test_none_returns_empty(self) -> None:
        assert project_enum_options_to_vocabulary_options(None) == []

    def test_empty_returns_empty(self) -> None:
        assert project_enum_options_to_vocabulary_options([]) == []

    def test_projects_name_and_enabled(self) -> None:
        opts = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental", enabled=True), _enum_option("Chiropractic", enabled=False)]
        )
        assert opts == [
            VocabularyOption(vertical_key="dental", name="Dental", enabled=True),
            VocabularyOption(vertical_key="chiropractic", name="Chiropractic", enabled=False),
        ]

    def test_skips_nameless_option(self) -> None:
        """An option with no name cannot yield a NAME-key (Lock-3) -> skipped."""
        opts = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option(None)]
        )
        assert [o.name for o in opts] == ["Dental"]

    def test_skips_empty_string_name(self) -> None:
        """F-2: an empty-string name collapses to the degenerate key "" -> skipped
        exactly like None (no VocabularyOption(vertical_key="") ever projects)."""
        opts = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("")]
        )
        assert [o.name for o in opts] == ["Dental"]
        assert all(o.vertical_key for o in opts)

    def test_skips_whitespace_only_name(self) -> None:
        """F-2: whitespace-only names normalize to the degenerate key "" -> skipped.

        A read whose names collapsed to blanks is degraded; the projection drops
        them (like None) so the emptiness/floor guard sees the reduced usable
        count instead of a wire full of empty-keyed rows.
        """
        opts = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("   "), _enum_option("\t\n ")]
        )
        assert [o.name for o in opts] == ["Dental"]
        assert all(o.vertical_key for o in opts)  # no empty key survives projection

    def test_namekey_variants_collapse(self) -> None:
        """C-NAMEKEY: whitespace/case variants project to the SAME vertical_key."""
        opts = project_enum_options_to_vocabulary_options(
            [_enum_option("General Practice"), _enum_option(" general  practice ")]
        )
        assert opts[0].vertical_key == opts[1].vertical_key == "general practice"

    def test_projection_carries_no_gid(self) -> None:
        """Lock-3: the source option's gid never reaches the wire model."""
        opts = project_enum_options_to_vocabulary_options([_enum_option("Dental", gid="99999")])
        dumped = opts[0].model_dump()
        assert "gid" not in dumped
        assert "99999" not in dumped.values()


# ============================================================================
# _is_vocab_sync_enabled -- SHIP-DARK (DEFAULT OFF)
# ============================================================================


class TestIsVocabSyncEnabled:
    """The ship-dark flag: enabled ONLY when explicitly truthy."""

    def test_unset_is_disabled(self) -> None:
        """THE ship-dark proof: unset -> disabled (default OFF)."""
        with patch.dict("os.environ", {}, clear=True):
            assert _is_vocab_sync_enabled() is False

    def test_explicit_false_values_disabled(self) -> None:
        for val in ("false", "0", "no", "", "off", "False"):
            with patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: val}, clear=True):
                assert _is_vocab_sync_enabled() is False, val

    def test_truthy_values_enabled(self) -> None:
        for val in ("1", "true", "yes", "TRUE", "Yes"):
            with patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: val}, clear=True):
                assert _is_vocab_sync_enabled() is True, val

    def test_default_on_push_flags_do_not_enable_vocab(self) -> None:
        """Ship-dark integrity: the vocab path does NOT ride the default-ON flags.

        Setting GID_PUSH_ENABLED / STATUS_PUSH_ENABLED true leaves vocab OFF --
        reusing either would ship the vocab path live-by-default.
        """
        with patch.dict(
            "os.environ",
            {GID_PUSH_ENABLED_ENV_VAR: "true", STATUS_PUSH_ENABLED_ENV_VAR: "true"},
            clear=True,
        ):
            assert _is_vocab_sync_enabled() is False


class TestGetVocabSyncMinOptions:
    """The operator-tunable truncation floor."""

    def test_default_is_one(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert _get_vocab_sync_min_options() == 1

    def test_env_override(self) -> None:
        with patch.dict("os.environ", {VOCAB_SYNC_MIN_OPTIONS_ENV_VAR: "40"}, clear=True):
            assert _get_vocab_sync_min_options() == 40

    def test_non_parseable_falls_back_to_default(self) -> None:
        with patch.dict("os.environ", {VOCAB_SYNC_MIN_OPTIONS_ENV_VAR: "lots"}, clear=True):
            assert _get_vocab_sync_min_options() == 1

    def test_below_one_clamped_to_default(self) -> None:
        """The guard can never be disabled into a no-op (< 1 -> default)."""
        with patch.dict("os.environ", {VOCAB_SYNC_MIN_OPTIONS_ENV_VAR: "0"}, clear=True):
            assert _get_vocab_sync_min_options() == 1


# ============================================================================
# push_vocabulary_to_data_service -- the two-sided discriminating canary
# ============================================================================


class TestPushVocabularyCanary:
    """C-EMPTY / C-TRUNCATED / C-HEALTHY / C-SHIPDARK / C-NAMEKEY."""

    _HEALTHY = [VocabularyOption(vertical_key="dental", name="Dental")]

    # ---- C-SHIPDARK -----------------------------------------------------

    async def test_shipdark_flag_unset_skips_push(self) -> None:
        """C-SHIPDARK: flag UNSET (default OFF) -> no push; skip metric emitted."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(
                self._HEALTHY, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, "VocabSyncSkipped") == [{"skip_reason": "feature_disabled"}]

    # ---- C-EMPTY --------------------------------------------------------

    async def test_empty_none_refused(self) -> None:
        """C-EMPTY: None read -> REFUSE{empty}; push NOT called."""
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(
                None, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, "VocabSyncRefused") == [
            {"refuse_reason": VOCAB_REFUSE_REASON_EMPTY, "option_count": "0"}
        ]

    async def test_empty_list_refused(self) -> None:
        """C-EMPTY: [] read -> REFUSE{empty}; push NOT called."""
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(
                [], data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, "VocabSyncRefused")[0]["refuse_reason"] == "empty"

    async def test_refuse_short_circuits_before_credential_resolution(self) -> None:
        """The refuse fires BEFORE creds -> the signal is 'empty', NOT 'url_absent'.

        Proves the ordering: a broken read is refused with the correct reason
        even when transport config is entirely absent.
        """
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(None)  # no url/token anywhere
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, "VocabSyncRefused")[0]["refuse_reason"] == "empty"
        assert _metric_dims(mock_emit, "VocabSyncSkipped") == []  # NOT a url/key skip

    # ---- C-TRUNCATED ----------------------------------------------------

    async def test_gross_truncation_refused(self) -> None:
        """C-TRUNCATED: floor=5, feed 2 -> REFUSE{gross_truncation}; push NOT called."""
        two = [
            VocabularyOption(vertical_key="dental", name="Dental"),
            VocabularyOption(vertical_key="chiropractic", name="Chiropractic"),
        ]
        with (
            patch.dict(
                "os.environ",
                {VOCAB_SYNC_ENABLED_ENV_VAR: "true", VOCAB_SYNC_MIN_OPTIONS_ENV_VAR: "5"},
                clear=True,
            ),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(
                two, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, "VocabSyncRefused") == [
            {"refuse_reason": VOCAB_REFUSE_REASON_GROSS_TRUNCATION, "option_count": "2"}
        ]

    async def test_exactly_at_floor_is_not_truncated(self) -> None:
        """Boundary: len == floor passes the guard (only len < floor refuses)."""
        two = [
            VocabularyOption(vertical_key="dental", name="Dental"),
            VocabularyOption(vertical_key="chiropractic", name="Chiropractic"),
        ]
        with (
            patch.dict(
                "os.environ",
                {VOCAB_SYNC_ENABLED_ENV_VAR: "true", VOCAB_SYNC_MIN_OPTIONS_ENV_VAR: "2"},
                clear=True,
            ),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                two, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is True
        mock_push.assert_awaited_once()

    # ---- C-HEALTHY ------------------------------------------------------

    async def test_healthy_set_pushes_with_generic_path(self) -> None:
        """C-HEALTHY: full set -> push called ONCE with the Lock-1 generic path;
        the payload validates as VocabularySyncRequest (field_key + NAME-keyed)."""
        healthy = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("Chiropractic"), _enum_option("General Practice")]
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                healthy, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is True
        mock_push.assert_awaited_once()
        kwargs = mock_push.call_args.kwargs
        assert kwargs["endpoint_path"] == "/api/v1/vocabularies/sync"  # Lock-1
        # The wire payload conforms to the typed contract.
        parsed = VocabularySyncRequest.model_validate(kwargs["payload"])
        assert parsed.field_key == "vertical"  # Lock-2
        assert {o.vertical_key for o in parsed.options} == {
            "dental",
            "chiropractic",
            "general practice",
        }
        # Lock-3: no gid / vertical_id on the wire.
        assert "gid" not in kwargs["payload"]["options"][0]

    async def test_healthy_set_http_roundtrip_hits_vocab_endpoint(self) -> None:
        """C-HEALTHY through the REAL _push_to_data_service helper: the POST URL
        is the generic vocab path and the serialized body is a valid Request."""
        healthy = [VocabularyOption(vertical_key="dental", name="Dental", enabled=True)]
        response = httpx.Response(
            status_code=200, json={"inserted": 1, "updated": 0, "refused": []}
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_HTTP_TARGET) as mock_http_cls,
        ):
            mock_raw = _make_push_mocks(mock_http_cls, post_return=response)
            result = await push_vocabulary_to_data_service(
                healthy, data_service_url="http://localhost:8000", auth_token="test-token"
            )
        assert result is True
        mock_raw.post.assert_called_once()
        call = mock_raw.post.call_args
        assert call.args[0] == "http://localhost:8000/api/v1/vocabularies/sync"
        payload = call.kwargs["json"]
        assert VocabularySyncRequest.model_validate(payload).field_key == "vertical"
        assert call.kwargs["headers"]["Authorization"] == "Bearer test-token"

    # ---- transport-config skips (benign, distinct from REFUSE) ----------

    async def test_healthy_but_no_url_skips(self) -> None:
        """Flag on + healthy set + no URL -> benign skip{url_absent}; push not sent."""
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(self._HEALTHY, auth_token="t")
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, "VocabSyncSkipped") == [{"skip_reason": "url_absent"}]

    async def test_healthy_but_no_token_skips(self) -> None:
        """Flag on + healthy set + URL but no token -> benign skip{invalid_key}."""
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(
                self._HEALTHY, data_service_url="http://localhost:8000"
            )
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, "VocabSyncSkipped") == [{"skip_reason": "invalid_key"}]


# ============================================================================
# F-1: strict 2xx-body parse -- fail CLOSED, never a false empty-success no-op
# ============================================================================


class TestPushVocabularyStrictParseFailClosed:
    """F-1: a 2xx whose body does not validate against the typed contract is an
    UNKNOWN outcome -> FAIL CLOSED (return False + VocabSyncContractParseFailed),
    NEVER a silent inserted=0/updated=0 success that merely LOOKS benign.

    Two-sided (TEETH): the contract-skewed and unparseable 2xx bodies BITE
    (False + alarm); the valid 2xx body passes GREEN (True + NO parse-failed
    metric). This is a regression guard against re-introducing the shared
    helper's argless-construction fallback on the vocab path -- the fail-closed
    correctness must NOT depend on whether VocabularySyncResponse happens to be
    argless-constructible (the exact fragility F-1 named).
    """

    _HEALTHY = [VocabularyOption(vertical_key="dental", name="Dental", enabled=True)]

    async def test_2xx_contract_skewed_body_fails_closed(self) -> None:
        """RED: 2xx + a body that violates the typed contract (missing required
        inserted/updated/refused, plus an extra="forbid" key) -> model_validate
        raises -> strict FAIL CLOSED, alarm emitted, never a false success."""
        response = httpx.Response(status_code=200, json={"unexpected": "shape"})
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_HTTP_TARGET) as mock_http_cls,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_raw = _make_push_mocks(mock_http_cls, post_return=response)
            result = await push_vocabulary_to_data_service(
                self._HEALTHY, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False  # NOT a false empty-success no-op
        mock_raw.post.assert_called_once()  # it DID reach transport (not a pre-refuse/skip)
        assert _metric_dims(mock_emit, "VocabSyncContractParseFailed") == [
            {"field_key": "vertical"}
        ]

    async def test_2xx_unparseable_json_body_fails_closed(self) -> None:
        """RED: a 2xx whose body is not even JSON (e.g. an upstream HTML error
        page proxied with a 200) -> response.json() raises -> same strict
        FAIL CLOSED path, alarm emitted."""
        response = httpx.Response(status_code=200, text="<html>502 upstream</html>")
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_HTTP_TARGET) as mock_http_cls,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_raw = _make_push_mocks(mock_http_cls, post_return=response)
            result = await push_vocabulary_to_data_service(
                self._HEALTHY, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False
        mock_raw.post.assert_called_once()
        assert _metric_dims(mock_emit, "VocabSyncContractParseFailed") == [
            {"field_key": "vertical"}
        ]

    async def test_2xx_valid_contract_body_succeeds_without_alarm(self) -> None:
        """GREEN (no-defect variant): a body that DOES validate against the typed
        contract -> True, and the parse-failed alarm is NEVER emitted. The
        two-sided half that proves the RED tests bite on the defect, not on the
        transport."""
        response = httpx.Response(
            status_code=200, json={"inserted": 3, "updated": 1, "refused": []}
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_HTTP_TARGET) as mock_http_cls,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_raw = _make_push_mocks(mock_http_cls, post_return=response)
            result = await push_vocabulary_to_data_service(
                self._HEALTHY, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is True
        mock_raw.post.assert_called_once()
        assert _metric_dims(mock_emit, "VocabSyncContractParseFailed") == []  # no false alarm


# ============================================================================
# detect_vocab_drift -- the PURE read-only drift observer (ADR-S4-001)
#
# The two-sided TEETH live here at the function level: each drift class FIRES on
# a drift INPUT and is SILENT on a clean INPUT (same pure function). A one-sided
# always-emit observer would redden the clean assertions; a never-emit observer
# would silence the drift assertions. Neither survives.
# ============================================================================


class TestVocabDriftObserver:
    """detect_vocab_drift: pure, read-only, two-sided per drift class."""

    def test_name_collision_fires_on_drift_silent_on_clean(self) -> None:
        """DW-COLLISION teeth (observer): 2 names -> 1 key FIRES {name_collision,1};
        2 distinct keys is SILENT. len(projected) - len(distinct keys)."""
        drift = [
            VocabularyOption(vertical_key="dental", name="Dental"),
            VocabularyOption(vertical_key="dental", name="dental "),
        ]
        clean = [
            VocabularyOption(vertical_key="dental", name="Dental"),
            VocabularyOption(vertical_key="chiropractic", name="Chiropractic"),
        ]
        assert detect_vocab_drift(drift) == [(VOCAB_DRIFT_REASON_NAME_COLLISION, 1)]
        assert detect_vocab_drift(clean) == []

    def test_disabled_option_fires_on_drift_silent_on_clean(self) -> None:
        """DW-DISABLED teeth (observer): an enabled=False option FIRES
        {disabled_option,1}; all-enabled is SILENT. enabled=None is NOT disabled."""
        drift = [
            VocabularyOption(vertical_key="dental", name="Dental", enabled=True),
            VocabularyOption(vertical_key="chiropractic", name="Chiropractic", enabled=False),
        ]
        clean = [
            VocabularyOption(vertical_key="dental", name="Dental", enabled=True),
            VocabularyOption(vertical_key="chiropractic", name="Chiropractic", enabled=True),
        ]
        assert detect_vocab_drift(drift) == [(VOCAB_DRIFT_REASON_DISABLED_OPTION, 1)]
        assert detect_vocab_drift(clean) == []

    def test_enabled_none_is_not_counted_disabled(self) -> None:
        """enabled=None (unspecified) is NOT a disabled option -- only `is False`."""
        opts = [VocabularyOption(vertical_key="dental", name="Dental", enabled=None)]
        assert detect_vocab_drift(opts) == []

    def test_degenerate_name_fires_on_drift_silent_on_clean(self) -> None:
        """DW-DEGENERATE teeth (observer): raw=3 / projected=1 FIRES
        {degenerate_name,2}; raw=2 / projected=2 is SILENT. raw - len(projected)."""
        survivor = [VocabularyOption(vertical_key="dental", name="Dental")]
        two = [
            VocabularyOption(vertical_key="dental", name="Dental"),
            VocabularyOption(vertical_key="chiropractic", name="Chiropractic"),
        ]
        assert detect_vocab_drift(survivor, raw_option_count=3) == [
            (VOCAB_DRIFT_REASON_DEGENERATE_NAME, 2)
        ]
        assert detect_vocab_drift(two, raw_option_count=2) == []

    def test_degenerate_needs_raw_count_else_not_computed(self) -> None:
        """The degenerate signal is computed ONLY when raw_option_count is threaded
        (the projected set alone cannot see what projection dropped) -- no false
        positive when the caller does not supply it."""
        survivor = [VocabularyOption(vertical_key="dental", name="Dental")]
        assert detect_vocab_drift(survivor) == []  # raw_option_count absent

    def test_fully_clean_set_returns_no_signals(self) -> None:
        """A healthy set (distinct keys, all enabled, no drops) is fully SILENT."""
        clean = [
            VocabularyOption(vertical_key="dental", name="Dental", enabled=True),
            VocabularyOption(vertical_key="chiropractic", name="Chiropractic", enabled=True),
        ]
        assert detect_vocab_drift(clean, raw_option_count=2) == []

    def test_multiple_drift_classes_coexist_in_stable_order(self) -> None:
        """Collision + disabled + degenerate coexist; order is stable
        (collision, disabled, degenerate)."""
        opts = [
            VocabularyOption(vertical_key="dental", name="Dental", enabled=True),
            VocabularyOption(vertical_key="dental", name="dental ", enabled=False),
        ]
        assert detect_vocab_drift(opts, raw_option_count=3) == [
            (VOCAB_DRIFT_REASON_NAME_COLLISION, 1),
            (VOCAB_DRIFT_REASON_DISABLED_OPTION, 1),
            (VOCAB_DRIFT_REASON_DEGENERATE_NAME, 1),
        ]

    def test_observer_is_pure_never_mutates_input(self) -> None:
        """ADR-S4-001: read-only. The observer never mutates/deletes the input set
        -- the list and its members are unchanged after observation."""
        opts = [
            VocabularyOption(vertical_key="dental", name="Dental", enabled=False),
            VocabularyOption(vertical_key="dental", name="dental "),
        ]
        before = [o.model_copy() for o in opts]
        _ = detect_vocab_drift(opts, raw_option_count=5)
        assert len(opts) == 2  # no delete
        assert [o.model_dump() for o in opts] == [o.model_dump() for o in before]


# ============================================================================
# push_vocabulary_to_data_service -- the TWO-SIDED drift-WARN canary (§S3-4)
#
# Through the push seam: drift FIRES the WARN+metric AND the drifting options
# RIDE the pushed payload (present-but-flagged, NEVER dropped-as-delete); the
# push PROCEEDS (drift != refuse). Clean inputs stay SILENT on the same path.
# ============================================================================


class TestPushVocabularyDriftCanary:
    """DW-COLLISION / DW-DISABLED / DW-DEGENERATE / DW-PROCEEDS through push."""

    # ---- DW-COLLISION ---------------------------------------------------

    async def test_collision_warns_and_both_rows_ride_the_payload(self) -> None:
        """DW-COLLISION RED: 2 names -> 1 key emits {name_collision,1} AND BOTH
        rows still ride the pushed payload (present-but-flagged, no producer-side
        drop). The consumer's FR-007 per-row guard resolves the collision."""
        projected = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("dental ")]
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                projected, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is True
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == [
            {
                "drift_reason": VOCAB_DRIFT_REASON_NAME_COLLISION,
                "count": "1",
                "field_key": "vertical",
            }
        ]
        mock_push.assert_awaited_once()
        payload_keys = [o["vertical_key"] for o in mock_push.call_args.kwargs["payload"]["options"]]
        assert payload_keys == ["dental", "dental"]  # BOTH collided rows ride; no drop

    async def test_collision_clean_input_emits_no_drift_metric(self) -> None:
        """DW-COLLISION clean: 2 distinct keys -> NO name_collision metric."""
        projected = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("Chiropractic")]
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                projected, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is True
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == []
        mock_push.assert_awaited_once()

    # ---- DW-DISABLED ----------------------------------------------------

    async def test_disabled_warns_and_option_rides_with_enabled_false(self) -> None:
        """DW-DISABLED RED: an enabled=False option emits {disabled_option,1} AND
        the disabled option is IN the pushed payload with enabled=False -- carried
        present-but-flagged, NEVER dropped-as-delete (RR2 / BC-3)."""
        projected = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental", enabled=True), _enum_option("Chiropractic", enabled=False)]
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                projected, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is True
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == [
            {
                "drift_reason": VOCAB_DRIFT_REASON_DISABLED_OPTION,
                "count": "1",
                "field_key": "vertical",
            }
        ]
        mock_push.assert_awaited_once()
        rows = mock_push.call_args.kwargs["payload"]["options"]
        disabled_rows = [o for o in rows if o["vertical_key"] == "chiropractic"]
        assert len(disabled_rows) == 1  # the disabled option rides -- not deleted
        assert disabled_rows[0]["enabled"] is False  # present-but-flagged

    async def test_disabled_clean_input_emits_no_drift_metric(self) -> None:
        """DW-DISABLED clean: all-enabled -> NO disabled_option metric."""
        projected = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental", enabled=True), _enum_option("Chiropractic", enabled=True)]
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                projected, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is True
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == []

    # ---- DW-DEGENERATE --------------------------------------------------

    async def test_degenerate_warns_and_survivor_still_ships(self) -> None:
        """DW-DEGENERATE RED: raw=3 (one None, one blank) / projected=1 emits
        {degenerate_name,2} AND the surviving Dental still ships. The degenerate
        options never had a constructible NAME-key -- unprojectable, never on the
        wire, never dropped-as-delete."""
        raw = [_enum_option("Dental"), _enum_option(None), _enum_option("  ")]
        projected = project_enum_options_to_vocabulary_options(raw)
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                projected,
                raw_option_count=len(raw),
                data_service_url="http://localhost:8000",
                auth_token="t",
            )
        assert result is True
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == [
            {
                "drift_reason": VOCAB_DRIFT_REASON_DEGENERATE_NAME,
                "count": "2",
                "field_key": "vertical",
            }
        ]
        mock_push.assert_awaited_once()
        payload_keys = [o["vertical_key"] for o in mock_push.call_args.kwargs["payload"]["options"]]
        assert payload_keys == ["dental"]  # survivor ships; no empty-keyed row on the wire

    async def test_degenerate_clean_input_emits_no_drift_metric(self) -> None:
        """DW-DEGENERATE clean: raw=2 / projected=2 -> NO degenerate_name metric."""
        raw = [_enum_option("Dental"), _enum_option("Chiropractic")]
        projected = project_enum_options_to_vocabulary_options(raw)
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                projected,
                raw_option_count=len(raw),
                data_service_url="http://localhost:8000",
                auth_token="t",
            )
        assert result is True
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == []

    # ---- DW-PROCEEDS + drift-vs-refuse orthogonality --------------------

    async def test_drift_proceeds_push_is_still_called(self) -> None:
        """DW-PROCEEDS: drift NEVER short-circuits -- _push_to_data_service is
        STILL called on a drift set (contrast VocabSyncRefused, which blocks the
        push). Drift RIDES the push; refuse BLOCKS it."""
        projected = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("dental ")]  # collision drift
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                projected, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is True
        mock_push.assert_awaited_once()  # drift did NOT block the push
        assert _metric_dims(mock_emit, _DRIFT_METRIC)  # and the WARN did fire
        assert _metric_dims(mock_emit, "VocabSyncRefused") == []  # drift is not a refuse

    async def test_drift_not_emitted_on_refused_empty_path(self) -> None:
        """Drift observes ONLY what ships: on the REFUSED empty path the louder
        VocabSyncRefused fires and NO drift metric is emitted (nothing ships)."""
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(
                None, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == []
        assert _metric_dims(mock_emit, "VocabSyncRefused")[0]["refuse_reason"] == "empty"

    async def test_drift_not_emitted_on_refused_truncation_path(self) -> None:
        """Drift observes ONLY what ships: on the REFUSED gross-truncation path no
        drift metric is emitted even if the truncated set would carry drift."""
        # Two options that collide (drift), but floor=5 -> the set is REFUSED first.
        projected = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("dental ")]
        )
        with (
            patch.dict(
                "os.environ",
                {VOCAB_SYNC_ENABLED_ENV_VAR: "true", VOCAB_SYNC_MIN_OPTIONS_ENV_VAR: "5"},
                clear=True,
            ),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(
                projected, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == []
        assert _metric_dims(mock_emit, "VocabSyncRefused")[0]["refuse_reason"] == "gross_truncation"

    async def test_drift_never_fires_when_shipdark_flag_off(self) -> None:
        """Ship-dark: the drift observer lives INSIDE the flag-gated push; with the
        flag OFF (default) the dark path returns before any drift observation."""
        projected = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("dental ")]  # would drift if reached
        )
        with (
            patch.dict("os.environ", {}, clear=True),  # flag UNSET -> dark
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
        ):
            result = await push_vocabulary_to_data_service(
                projected, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert result is False
        mock_push.assert_not_called()
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == []
        assert _metric_dims(mock_emit, "VocabSyncSkipped") == [{"skip_reason": "feature_disabled"}]


# ============================================================================
# DW-TEETH -- the mutation bite (push <-> observer wiring is faithful both ways)
# ============================================================================


class TestPushVocabularyDriftTeeth:
    """DW-TEETH: the matched pairs BITE on both mis-calibrations.

    These prove the push<->observer wiring is faithful in BOTH directions, so the
    clean-silence and drift-fire in the canary above are the OBSERVER's verdict,
    never an artifact of the push seam swallowing or manufacturing drift.
    """

    async def test_teeth_always_emit_observer_reddens_a_clean_set(self) -> None:
        """DW-TEETH (always-emit bite): if the observer were miscalibrated to emit
        on a CLEAN set, the push would faithfully ALARM -- proving the clean-silence
        in the real canary is the OBSERVER returning [], not the push swallowing
        drift. (Monkeypatch stands in for the 'flip observer to always-emit'
        mutation; the RED here is a broken OBSERVER, never shipped code.)"""
        clean = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("Chiropractic")]  # genuinely clean
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
            patch(
                _DRIFT_OBSERVER_TARGET,
                return_value=[(VOCAB_DRIFT_REASON_NAME_COLLISION, 99)],
            ),
        ):
            mock_push.return_value = True
            await push_vocabulary_to_data_service(
                clean, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == [
            {
                "drift_reason": VOCAB_DRIFT_REASON_NAME_COLLISION,
                "count": "99",
                "field_key": "vertical",
            }
        ]

    async def test_teeth_deleted_observer_silences_a_drift_set(self) -> None:
        """DW-TEETH (delete-observer bite): if the observer were deleted (returns
        []), even a genuine DRIFT set produces NO drift metric -- proving the RED
        metric in the real canary comes from the OBSERVER detecting drift, not a
        spurious always-on emit in the push seam."""
        drift = project_enum_options_to_vocabulary_options(
            [_enum_option("Dental"), _enum_option("dental ")]  # genuinely collides
        )
        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(_EMIT_TARGET) as mock_emit,
            patch(_DRIFT_OBSERVER_TARGET, return_value=[]),
        ):
            mock_push.return_value = True
            await push_vocabulary_to_data_service(
                drift, data_service_url="http://localhost:8000", auth_token="t"
            )
        assert _metric_dims(mock_emit, _DRIFT_METRIC) == []
        mock_push.assert_awaited_once()  # push still proceeded (the set is healthy-len)


# ============================================================================
# §S3-2 COMPOSE-UP SEED -- a 2nd field_key is a DATA addition, not a code path
# ============================================================================


class TestComposeUpSeed:
    """CU-1 (value-blind wiring) + CU-2 (grep-zero regression guard).

    The single extension point already exists: field_key: Literal["vertical"] is
    the typed registry -- the analogue of the origin/main dynvocab OVERRIDE_REGISTRY
    dict (a 2nd override is a new dict entry = DATA; a 2nd vocabulary is a new
    Literal permitted value = DATA). CU-1 proves the push machinery is value-BLIND;
    CU-2 is the regression guard that no field_key value-branch exists. Neither
    edits the Literal (editing it would be BUILDING, not PROVING). The fleet
    registry is NOT built here -- ESCALATE-only at N>=3 (G-DEFER, ADR §7,§11 A10).
    """

    async def test_cu1_push_machinery_is_field_key_value_blind(self) -> None:
        """CU-1: model_construct bypasses the Literal["vertical"] validator (the
        point is to exercise the DOWNSTREAM wiring, not the validator). A
        hypothetical "campaign_type" vocabulary drives the SAME push wiring:
          (i)   the endpoint is the SAME generic /api/v1/vocabularies/sync
                (NOT a field_key-specific /campaign_type/sync);
          (ii)  field_key is threaded VERBATIM into payload + metric_dimensions;
          (iii) the option-SET (produced by the field_key-agnostic projection)
                rides through unbranched.
        No new code path is taken -- the machinery never inspects the value."""
        # The 2nd vocabulary's option-SET, projected by the SAME projection, which
        # takes NO field_key argument (proof (iii): projection is field_key-blind).
        projected = project_enum_options_to_vocabulary_options(
            [_enum_option("Brand Awareness"), _enum_option("Lead Gen")]
        )

        def _construct_via_model_construct(**kwargs: object) -> VocabularySyncRequest:
            # Bypass the Literal["vertical"] validator to reach the downstream
            # wiring with a hypothetical 2nd field_key value (the validator is the
            # ONE deliberate gatekeeper; everything downstream is value-blind).
            return VocabularySyncRequest.model_construct(**kwargs)

        with (
            patch.dict("os.environ", {VOCAB_SYNC_ENABLED_ENV_VAR: "true"}, clear=True),
            patch(_PUSH_TARGET, new_callable=AsyncMock) as mock_push,
            patch(
                "autom8_asana.services.gid_push.VocabularySyncRequest",
                side_effect=_construct_via_model_construct,
            ),
        ):
            mock_push.return_value = True
            result = await push_vocabulary_to_data_service(
                projected,
                field_key="campaign_type",  # type: ignore[arg-type]  # hypothetical 2nd vocab
                data_service_url="http://localhost:8000",
                auth_token="t",
            )
        assert result is True
        mock_push.assert_awaited_once()
        kwargs = mock_push.call_args.kwargs
        # (i) SAME generic path -- never a field_key-specific /campaign_type/sync.
        assert kwargs["endpoint_path"] == "/api/v1/vocabularies/sync"
        # (ii) field_key threaded VERBATIM into payload + metric dimensions.
        assert kwargs["payload"]["field_key"] == "campaign_type"
        assert kwargs["metric_dimensions"]["field_key"] == "campaign_type"
        # (iii) the option-SET rode through unbranched (both rows, NAME-keyed).
        assert [o["vertical_key"] for o in kwargs["payload"]["options"]] == [
            "brand awareness",
            "lead gen",
        ]

    def test_cu2_no_field_key_value_branch_in_machinery(self) -> None:
        """CU-2: the compose-up seed is DATA, mechanically. A source scan of the
        projection/push machinery contains NO field_key value-branch
        (`field_key == "..."` / `field_key is "..."` / `field_key in (...)`). This
        is the value-blind property CU-1 relies on: if a future edit adds a
        value-branch, this goes RED -- the 2nd vocabulary would then need CODE, not
        DATA. (Mirrors the dynvocab discipline: apply_override reads the mapping; it
        never `if entity_type == "offer"`-branches.)"""
        value_branch = re.compile(r"""field_key\s*(?:==|!=|\bis\b|\bin\b)\s*[\[("']""")
        for module in (gid_push_module, vocabulary_sync_module):
            src = Path(module.__file__).read_text(encoding="utf-8")
            hits = value_branch.findall(src)
            assert hits == [], f"field_key value-branch in {module.__name__}: {hits}"

    def test_cu2_endpoint_is_generic_plural_not_field_key_specific(self) -> None:
        """CU-2 corollary: the ONLY vocab endpoint_path literal is the Lock-1
        generic plural /api/v1/vocabularies/sync -- never a field_key-specific path.
        A 2nd vocabulary POSTs to the SAME path (no per-vocabulary route)."""
        src = Path(gid_push_module.__file__).read_text(encoding="utf-8")
        assert 'endpoint_path="/api/v1/vocabularies/sync"' in src
        assert 'endpoint_path="/verticals/sync"' not in src
        assert 'endpoint_path="/api/v1/verticals/sync"' not in src
        assert 'endpoint_path="/campaign_type/sync"' not in src
