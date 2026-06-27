"""Two-sided discriminating tests for OnboardingWalkthroughWorkflow.

Per TDD §Test Matrix (T1..T7 + AC-MECHANISM). Every test is RED/GREEN
discriminating. The two production-mutating boundaries are NEVER hit:
  * the Asana attach (upload/delete) is ALWAYS mocked (WONT-2 -- no live write);
  * the SDK resolve is mocked for unit determinism (no live data-service call).
The MECHANISM legs (the Node producer freeze) are REAL -- guarded by a
producer-availability skip so the suite is robust where Node/node_modules are
absent. The standalone producer->frozen-HTML receipt (AC-MECHANISM) is captured
separately in the build log, not by a green test alone (G-THEATER).
"""

from __future__ import annotations

import io
import os
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.automation.workflows.bridge_base import BridgeWorkflowAction
from autom8_asana.automation.workflows.onboarding_walkthrough import (
    constants,
)
from autom8_asana.automation.workflows.onboarding_walkthrough import (
    producer as producer_module,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.producer import (
    ProducerFreezeError,
    freeze_walkthrough_deck,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.workflow import (
    OnboardingWalkthroughWorkflow,
)

# --- Fixtures / probe constants (N0 live probe 2026-06-27) ---

# Spike-proven canonical gated address (test GUID). Used as the SDK-resolved
# value in mocked-resolve tests and as the real --addr in producer-real tests.
SPIKE_ADDRESS = "b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com"
PILOT_PHONE = "+15596996816"  # real Office Phone on pilot task 1214919448732981
SPIKE_DECK = "email-forwarding-setup"  # the deck proven in the committed spike

# Producer worktree (CONFIG; overridable). Default = the dispatch producer path.
_DEFAULT_PRODUCER_DIR = Path(
    "/tmp/10x-producer-wt/contente-design-system/contente-design-system/project"
)


def _producer_dir() -> Path:
    return Path(os.environ.get(constants.WALKTHROUGH_PRODUCER_DIR_ENV_VAR, _DEFAULT_PRODUCER_DIR))


def _producer_available() -> bool:
    pdir = _producer_dir()
    return (
        shutil.which("node") is not None
        and (pdir / "build" / "inline.mjs").exists()
        and (pdir / "node_modules").exists()
    )


requires_producer = pytest.mark.skipif(
    not _producer_available(),
    reason="Node producer not available (need node + producer node_modules)",
)


# --- Mock builders ---


class _AsyncIterator:
    """Async iterator for mock attachment page iterators."""

    def __init__(self, items: list[Any]) -> None:
        self._items = items
        self._index = 0

    def __aiter__(self) -> _AsyncIterator:
        return self

    async def __anext__(self) -> Any:
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


def _make_attachment(gid: str, name: str) -> MagicMock:
    att = MagicMock()
    att.gid = gid
    att.name = name
    return att


def _make_resolver(
    *,
    address: str | None = SPIKE_ADDRESS,
    raises: Exception | None = None,
) -> MagicMock:
    """Build a mocked sole-address-source resolver (autom8y-core SDK stand-in)."""
    resolver = MagicMock()
    if raises is not None:
        resolver.resolve_routing_address_by_phone_async = AsyncMock(side_effect=raises)
    else:
        resolver.resolve_routing_address_by_phone_async = AsyncMock(return_value=address)
    return resolver


def _make_workflow(
    *,
    resolver: MagicMock | None = None,
    producer_dir: Path | str | None = None,
    existing_attachments: list[MagicMock] | None = None,
) -> tuple[OnboardingWalkthroughWorkflow, MagicMock, MagicMock, list[str]]:
    """Construct the workflow with mocked asana + attachments clients.

    Returns (workflow, mock_attachments, resolver, order) where ``order`` records
    the sequence of attachment side effects ("upload" / "list" / "delete") to
    assert upload-first-then-delete ordering.
    """
    mock_asana = MagicMock()
    mock_attachments = MagicMock()
    resolver = resolver or _make_resolver()
    order: list[str] = []

    async def _upload(**_kwargs: Any) -> MagicMock:
        order.append("upload")
        return MagicMock()

    mock_attachments.upload_async = AsyncMock(side_effect=_upload)

    att_list = existing_attachments or []

    def _list(_gid: str, **_kwargs: Any) -> _AsyncIterator:
        order.append("list")
        return _AsyncIterator(att_list)

    mock_attachments.list_for_task_async = MagicMock(side_effect=_list)

    async def _delete(_gid: str) -> None:
        order.append("delete")

    mock_attachments.delete_async = AsyncMock(side_effect=_delete)

    wf = OnboardingWalkthroughWorkflow(
        asana_client=mock_asana,
        resolver=resolver,
        attachments_client=mock_attachments,
        producer_dir=producer_dir if producer_dir is not None else Path("/tmp/_no_producer"),
    )
    return wf, mock_attachments, resolver, order


def _entity(
    *,
    gid: str = "task-1",
    provider: str | None = "GHL",
    office_phone: str | None = PILOT_PHONE,
    name: str = "Restore Neuro Rehab",
) -> dict[str, Any]:
    return {
        "gid": gid,
        "calendar_provider": provider,
        "office_phone": office_phone,
        "name": name,
        "client_name": name,
    }


# --- T2 / AC-GATE RED: wrong / absent / unmapped enum -> no-op skip ---


class TestNecessityGate:
    """Positive enum gate (G-DENOM): only triggering providers proceed."""

    async def test_unknown_provider_skips_no_side_effects(self) -> None:
        wf, atts, resolver, _ = _make_workflow()
        out = await wf.process_entity(_entity(provider="UNKNOWN_PROVIDER_VALUE"), {})
        assert out.status == "skipped"
        assert out.reason == "provider_not_triggering"
        resolver.resolve_routing_address_by_phone_async.assert_not_called()
        atts.upload_async.assert_not_called()

    async def test_none_provider_skips_no_side_effects(self) -> None:
        wf, atts, resolver, _ = _make_workflow()
        out = await wf.process_entity(_entity(provider=None), {})
        assert out.status == "skipped"
        assert out.reason == "provider_not_triggering"
        resolver.resolve_routing_address_by_phone_async.assert_not_called()
        atts.upload_async.assert_not_called()

    async def test_known_but_unmapped_provider_skips(self) -> None:
        # "Acuity" is a real enum option mapped to None (PROBE-GATED) -> distinct
        # reason from a wholly-unknown value; still a no-op skip.
        wf, atts, resolver, _ = _make_workflow()
        out = await wf.process_entity(_entity(provider="Acuity"), {})
        assert out.status == "skipped"
        assert out.reason == "provider_unmapped"
        resolver.resolve_routing_address_by_phone_async.assert_not_called()
        atts.upload_async.assert_not_called()


# --- T3 / AC-RESOLVE-skip RED: missing office_phone -> fail-closed skip ---


class TestMissingOfficePhone:
    async def test_missing_phone_fails_closed(self) -> None:
        wf, atts, resolver, _ = _make_workflow()
        out = await wf.process_entity(_entity(provider="GHL", office_phone=None), {})
        assert out.status == "skipped"
        assert out.reason == "missing_office_phone"
        resolver.resolve_routing_address_by_phone_async.assert_not_called()
        atts.upload_async.assert_not_called()

    async def test_empty_phone_fails_closed(self) -> None:
        wf, atts, resolver, _ = _make_workflow()
        out = await wf.process_entity(_entity(provider="GHL", office_phone=""), {})
        assert out.status == "skipped"
        assert out.reason == "missing_office_phone"
        atts.upload_async.assert_not_called()


# --- T1 / AC-FREEZE: REAL producer, two-sided (G-THEATER #1) ---


@requires_producer
class TestProducerFreezeReal:
    def test_freeze_red_non_canonical_addr_raises_and_writes_no_file(self) -> None:
        pdir = _producer_dir()
        out_name = "walkthrough_unittest_red.html"
        out_path = pdir / "export" / out_name
        if out_path.exists():
            out_path.unlink()
        with pytest.raises(ProducerFreezeError):
            freeze_walkthrough_deck(
                producer_dir=pdir,
                deck_template=SPIKE_DECK,
                gated_address="not-a-valid-address",
                client_name="Unit Test Clinic",
                out_filename=out_name,
            )
        # ADDR-NON-CANONICAL fires -> producer writes NO file.
        assert not out_path.exists()

    def test_freeze_green_canonical_addr_returns_bytes_with_address(self) -> None:
        pdir = _producer_dir()
        out_name = "walkthrough_unittest_green.html"
        out_path = pdir / "export" / out_name
        try:
            frozen = freeze_walkthrough_deck(
                producer_dir=pdir,
                deck_template=SPIKE_DECK,
                gated_address=SPIKE_ADDRESS,
                client_name="Unit Test Clinic",
                out_filename=out_name,
            )
            assert frozen, "expected non-empty frozen HTML"
            assert SPIKE_ADDRESS.encode("utf-8") in frozen
        finally:
            out_path.unlink(missing_ok=True)

    async def test_workflow_freeze_failure_no_upload(self) -> None:
        # Resolver returns a non-canonical address -> the REAL producer refuses
        # (ADDR-NON-CANONICAL) -> ProducerFreezeError -> failed, NO upload.
        resolver = _make_resolver(address="not-a-valid-address")
        wf, atts, _, _ = _make_workflow(resolver=resolver, producer_dir=_producer_dir())
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "producer_freeze_failed"
        atts.upload_async.assert_not_called()


# --- T4 / AC-GATE GREEN + AC-SIBLING GREEN: full path (REAL freeze, MOCK attach) ---


@requires_producer
class TestFullPathGreen:
    async def test_full_path_uploads_then_deletes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # G-DENOM: production map keeps JaneApp None. Override the deck map IN THE
        # TEST ONLY so JaneApp -> the spike-proven deck, exercising the mechanism
        # end-to-end with the real pilot value + phone.
        monkeypatch.setitem(constants.WALKTHROUGH_DECK_MAP, "JaneApp", SPIKE_DECK)

        old_att = _make_attachment("old-gid", "walkthrough_task-1_20260101000000.html")
        resolver = _make_resolver(address=SPIKE_ADDRESS)
        wf, atts, _, order = _make_workflow(
            resolver=resolver,
            producer_dir=_producer_dir(),
            existing_attachments=[old_att],
        )

        out = await wf.process_entity(
            _entity(gid="task-1", provider="JaneApp", office_phone=PILOT_PHONE), {}
        )

        assert out.status == "succeeded"
        # Sole address source called exactly once with the pilot phone.
        resolver.resolve_routing_address_by_phone_async.assert_awaited_once_with(
            office_phone=PILOT_PHONE
        )
        # upload_async called exactly once, correct shape.
        atts.upload_async.assert_awaited_once()
        kwargs = atts.upload_async.await_args.kwargs
        assert kwargs["parent"] == "task-1"
        assert isinstance(kwargs["file"], io.BytesIO)
        assert kwargs["name"].startswith("walkthrough_task-1_")
        assert kwargs["name"].endswith(".html")
        assert kwargs["content_type"] == "text/html"
        # The frozen bytes carry the gated address (mechanism, not just exit 0).
        assert SPIKE_ADDRESS.encode("utf-8") in kwargs["file"].getvalue()
        # Replace cycle: prior walkthrough deleted, AFTER the upload.
        atts.delete_async.assert_awaited_once_with("old-gid")
        assert order.index("upload") < order.index("delete")
        # Temp file cleaned up (FR-8).
        assert not (_producer_dir() / "export" / kwargs["name"]).exists()


# --- T5 / AC-ATTACH: upload-first replacement (freeze MOCKED for determinism) ---


class TestAttachReplaceCycle:
    """Mock the freezer to isolate the attach contract from the Node producer."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> None:
        frozen = b"<html>" + SPIKE_ADDRESS.encode("utf-8") + b"</html>"

        def _fake_freeze(**_kwargs: Any) -> bytes:
            return frozen

        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", _fake_freeze)

    async def test_green_upload_then_delete(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_freeze(monkeypatch)
        old_att = _make_attachment("old-gid", "walkthrough_task-9_20250101000000.html")
        wf, atts, _, order = _make_workflow(existing_attachments=[old_att])
        out = await wf.process_entity(_entity(gid="task-9", provider="GHL"), {})
        assert out.status == "succeeded"
        atts.upload_async.assert_awaited_once()
        atts.delete_async.assert_awaited_once_with("old-gid")
        assert order.index("upload") < order.index("delete")

    async def test_red_upload_failure_preserves_prior_attachment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._patch_freeze(monkeypatch)
        old_att = _make_attachment("old-gid", "walkthrough_task-9_20250101000000.html")
        wf, atts, _, order = _make_workflow(existing_attachments=[old_att])
        atts.upload_async = AsyncMock(side_effect=RuntimeError("network down"))

        out = await wf.process_entity(_entity(gid="task-9", provider="GHL"), {})

        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "upload_failed"
        # Upload failed -> old attachment NOT deleted: no half-replaced state.
        atts.delete_async.assert_not_called()
        assert "delete" not in order


# --- T6 / AC-SIBLING RED: abstract base contract ---


class TestSiblingContract:
    def test_abstract_base_cannot_be_instantiated(self) -> None:
        # Python ABC: instantiating a class with unimplemented abstract methods
        # raises TypeError (NOT NotImplementedError).
        with pytest.raises(TypeError):
            BridgeWorkflowAction(MagicMock(), None, MagicMock())  # type: ignore[abstract]

    def test_concrete_subclass_instantiates(self) -> None:
        wf, _, _, _ = _make_workflow()
        assert isinstance(wf, BridgeWorkflowAction)
        assert wf.workflow_id == "onboarding-walkthrough"
        assert wf.feature_flag_env_var == "AUTOM8_WALKTHROUGH_ENABLED"


# --- T7 / AC-RESOLVE: sole address source (B1) ---


class TestResolveContract:
    """RED/GREEN on the resolve leg. Unit cases mock the SDK; a live integration
    case is gated on real data-service creds (reserved user lever)."""

    def test_sdk_method_importable_at_4_9_0(self) -> None:
        # D-6 receipt: B1 method exists on the installed autom8y-core SDK (>=4.9.0).
        import autom8y_core
        from autom8y_core.clients.data_service import DataServiceClient

        assert hasattr(DataServiceClient, "resolve_routing_address_by_phone_async")
        major, minor = (int(p) for p in autom8y_core.__version__.split(".")[:2])
        assert (major, minor) >= (4, 9), (
            f"need autom8y-core >=4.9.0, got {autom8y_core.__version__}"
        )

    async def test_resolve_unavailable_fails_closed(self) -> None:
        from autom8y_core.errors import DataServiceUnavailableError

        resolver = _make_resolver(
            raises=DataServiceUnavailableError(method="resolve_routing_address_by_phone_async")
        )
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "resolve_unavailable"
        atts.upload_async.assert_not_called()

    async def test_resolve_none_skips_no_subprocess_no_upload(self) -> None:
        resolver = _make_resolver(address=None)
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "address_unresolved"
        atts.upload_async.assert_not_called()

    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.environ.get("AUTOM8Y_DATA_URL"),
        reason="live data-service resolve requires AUTOM8Y_DATA_URL + creds (reserved lever)",
    )
    async def test_live_resolve_returns_canonical_address(self) -> None:
        import re

        from autom8y_core.clients.data_service import DataServiceClient

        client = DataServiceClient()
        addr = await client.resolve_routing_address_by_phone_async(office_phone=PILOT_PHONE)
        assert addr is not None
        assert re.fullmatch(r"[0-9a-f-]{36}@appointments\.contenteapp\.com", addr), (
            f"non-canonical: {addr}"
        )
