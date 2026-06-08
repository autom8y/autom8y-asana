"""Tests for the CR-3 GATE-2 P2-a receiver self-measurement EMF export.

Covers the additive ``emit_receiver_sli_emf`` emitter wired at the request seam
(api/routes/query.py:596) per
``TDD-cr3-gate2-receiver-self-measurement-export-2026-06-08.md`` (Option A).

The emitter writes one Embedded Metric Format (EMF) JSON line to stdout per
request so a cross-repo CloudWatch Logs + EMF extraction pipeline can produce a
durable, deploy-surviving, fleet-aggregated SLI time series. These tests assert
the IN-REPO contract only (emit shape, ship-dark flag, fire-and-forget swallow,
and the load-bearing co-read invariant). The cross-repo backend binding is OUT
of scope here (TDD §"G-RUNG honesty": this yields "designed + emitting to
stdout", NOT "exported live").

Each test names the TDD invariant it covers in its docstring.
"""

from __future__ import annotations

import json

import pytest

from autom8_asana.api.metrics import (
    RECEIVER_SLI_EMF_FLAG_ENV,
    RECEIVER_SLI_EMF_NAMESPACE,
    emit_receiver_sli_emf,
)

# Outcome-constituent field names co-emitted in every EMF document. The success
# rate is DELIBERATELY absent — it is derived downstream so the co-read
# prohibition cannot be bypassed (TDD §"Honoring the co-read PROHIBITION").
_OUTCOME_FIELDS = ("ReceiverQueryOutcomeSuccess", "ReceiverQueryOutcomeServerError")
_STALE_FIELD = "ServingStaleTotal"


@pytest.fixture
def emf_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Flip the ship-dark RECEIVER_SLI_EMF_ENABLED flag on for a test."""
    monkeypatch.setenv(RECEIVER_SLI_EMF_FLAG_ENV, "true")


def _read_one_emf_doc(captured: str) -> dict:
    """Parse exactly one EMF JSON document from captured stdout.

    The emitter prints exactly one line per call; this asserts that and returns
    the parsed document. Non-EMF lines (e.g. unrelated module log output) are
    tolerated by scanning for the line carrying the EMF ``_aws`` envelope.
    """
    docs = []
    for line in captured.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "_aws" in parsed:
            docs.append(parsed)
    assert len(docs) == 1, f"expected exactly one EMF doc, got {len(docs)}: {docs}"
    return docs[0]


class TestShipDarkFlag:
    """Default-off behavior (TDD §"ship-dark default until cross-repo #1")."""

    def test_no_emit_when_flag_unset(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Flag unset => the emitter is a no-op (no stdout written)."""
        monkeypatch.delenv(RECEIVER_SLI_EMF_FLAG_ENV, raising=False)
        emit_receiver_sli_emf("project", success=True, serving_stale_total=0.0)
        assert capsys.readouterr().out == ""

    def test_no_emit_when_flag_falsey(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A non-truthy flag value (e.g. "false"/"0") keeps the emitter dark."""
        for value in ("false", "0", "no", "off", ""):
            monkeypatch.setenv(RECEIVER_SLI_EMF_FLAG_ENV, value)
            emit_receiver_sli_emf("project", success=True, serving_stale_total=0.0)
            assert capsys.readouterr().out == "", f"emitted for flag value {value!r}"

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " True "])
    def test_emit_when_flag_truthy(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        value: str,
    ) -> None:
        """Recognized truthy spellings (case/space-insensitive) enable emission."""
        monkeypatch.setenv(RECEIVER_SLI_EMF_FLAG_ENV, value)
        emit_receiver_sli_emf("project", success=True, serving_stale_total=0.0)
        assert "_aws" in capsys.readouterr().out, f"no emit for flag value {value!r}"


@pytest.mark.usefixtures("emf_enabled")
class TestEmfDocumentShape:
    """The EMF document conforms to the published cross-repo contract."""

    def test_namespace_and_dimension_match_contract(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Namespace Autom8y/AsanaReceiverSLI + single ``arm`` dimension."""
        emit_receiver_sli_emf("project", success=True, serving_stale_total=0.0)
        doc = _read_one_emf_doc(capsys.readouterr().out)
        cw = doc["_aws"]["CloudWatchMetrics"][0]
        assert cw["Namespace"] == RECEIVER_SLI_EMF_NAMESPACE
        assert cw["Dimensions"] == [["arm"]]
        assert doc["arm"] == "project"

    def test_timestamp_is_epoch_millis(self, capsys: pytest.CaptureFixture[str]) -> None:
        """EMF requires an epoch-millisecond Timestamp (int, not seconds)."""
        emit_receiver_sli_emf("section", success=True, serving_stale_total=0.0)
        doc = _read_one_emf_doc(capsys.readouterr().out)
        ts = doc["_aws"]["Timestamp"]
        assert isinstance(ts, int)
        # Millis since epoch are ~1.7e12 in 2026; seconds would be ~1.7e9.
        assert ts > 1_000_000_000_000

    def test_success_maps_to_success_constituent(self, capsys: pytest.CaptureFixture[str]) -> None:
        """success=True => Success=1, ServerError=0 (XOR == 1)."""
        emit_receiver_sli_emf("project", success=True, serving_stale_total=2.0)
        doc = _read_one_emf_doc(capsys.readouterr().out)
        assert doc["ReceiverQueryOutcomeSuccess"] == 1
        assert doc["ReceiverQueryOutcomeServerError"] == 0
        assert doc["ReceiverQueryOutcomeSuccess"] + doc["ReceiverQueryOutcomeServerError"] == 1

    def test_failure_maps_to_server_error_constituent(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """success=False => Success=0, ServerError=1 (XOR == 1)."""
        emit_receiver_sli_emf("section", success=False, serving_stale_total=0.0)
        doc = _read_one_emf_doc(capsys.readouterr().out)
        assert doc["ReceiverQueryOutcomeSuccess"] == 0
        assert doc["ReceiverQueryOutcomeServerError"] == 1
        assert doc["ReceiverQueryOutcomeSuccess"] + doc["ReceiverQueryOutcomeServerError"] == 1

    def test_serving_stale_total_is_carried_verbatim(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The caller-supplied stale-total flows into the document unchanged."""
        emit_receiver_sli_emf("project", success=True, serving_stale_total=7.0)
        doc = _read_one_emf_doc(capsys.readouterr().out)
        assert doc[_STALE_FIELD] == 7.0


@pytest.mark.usefixtures("emf_enabled")
class TestCoReadInvariant:
    """The load-bearing PROHIBITION: rate is never exported bare (TDD §co-read).

    Any EMF document carrying the outcome constituents MUST also carry
    ``ServingStaleTotal`` in the SAME document, and MUST NOT carry a
    pre-computed success rate. This is the structural enforcement of
    observability-plan §2 at the export boundary.
    """

    @pytest.mark.parametrize(
        ("success", "stale"),
        [(True, 0.0), (False, 0.0), (True, 5.0), (False, 12.0)],
    )
    def test_outcome_metric_always_co_carries_stale_total(
        self, capsys: pytest.CaptureFixture[str], success: bool, stale: float
    ) -> None:
        """Outcome constituents present => ServingStaleTotal present (same doc)."""
        emit_receiver_sli_emf("project", success=success, serving_stale_total=stale)
        doc = _read_one_emf_doc(capsys.readouterr().out)
        metric_names = {m["Name"] for m in doc["_aws"]["CloudWatchMetrics"][0]["Metrics"]}
        # Both the metric-definition list and the value payload carry it.
        for field in _OUTCOME_FIELDS:
            assert field in metric_names, f"{field} missing from metric defs"
            assert field in doc, f"{field} missing from value payload"
        assert _STALE_FIELD in metric_names, "co-read: ServingStaleTotal missing from defs"
        assert _STALE_FIELD in doc, "co-read: ServingStaleTotal missing from payload"

    def test_no_bare_success_rate_field_is_emitted(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """No pre-computed rate field anywhere — it is derived downstream only."""
        emit_receiver_sli_emf("section", success=True, serving_stale_total=0.0)
        out = capsys.readouterr().out
        doc = _read_one_emf_doc(out)
        metric_names = {m["Name"] for m in doc["_aws"]["CloudWatchMetrics"][0]["Metrics"]}
        forbidden = {"success_rate", "SuccessRate", "ReceiverQuerySuccessRate"}
        assert not (forbidden & set(doc.keys())), "bare rate leaked into payload"
        assert not (forbidden & metric_names), "bare rate leaked into metric defs"


@pytest.mark.usefixtures("emf_enabled")
class TestFireAndForget:
    """Emission must never raise on the request hot path (TDD §Reliability)."""

    def test_serialization_failure_is_swallowed(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A json.dumps failure is caught — the emitter returns None, no raise."""

        def _boom(*_args: object, **_kwargs: object) -> str:
            raise TypeError("not serializable")

        monkeypatch.setattr("autom8_asana.api.metrics.json.dumps", _boom)
        # Must not raise despite the internal serialization error.
        assert emit_receiver_sli_emf("project", success=True, serving_stale_total=0.0) is None
        # Nothing leaked to stdout.
        assert "_aws" not in capsys.readouterr().out

    def test_stdout_write_failure_is_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A stdout.write() failure is caught — fire-and-forget contract upheld."""

        def _boom(*_args: object, **_kwargs: object) -> None:
            raise OSError("stdout broken")

        monkeypatch.setattr("autom8_asana.api.metrics.sys.stdout.write", _boom)
        assert emit_receiver_sli_emf("section", success=False, serving_stale_total=1.0) is None
