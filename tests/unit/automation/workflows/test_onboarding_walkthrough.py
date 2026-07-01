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

import asyncio
import hashlib
import inspect
import io
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from autom8_asana.automation.workflows.bridge_base import BridgeWorkflowAction
from autom8_asana.automation.workflows.onboarding_walkthrough import (
    constants,
    identity_guard,
)
from autom8_asana.automation.workflows.onboarding_walkthrough import (
    producer as producer_module,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.identity_guard import (
    AnchorResult,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.producer import (
    ProducerFreezeError,
    freeze_walkthrough_deck,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TenantBindingError,
    _mask_addr,
    assert_exclusive_tenant_binding,
    harvest_routing_addresses,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.workflow import (
    OnboardingWalkthroughWorkflow,
)
from autom8_asana.core.types import EntityType
from autom8_asana.resolution.gfr.models import TruthTier
from tests.unit.resolution.gfr.conftest import (
    FakeByGuidVerifier,
    make_hydration_result,
    make_record,
    make_rows_response,
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


def _make_attachment(
    gid: str,
    name: str,
    *,
    addr: str | None = None,
    created_at: str | None = None,
) -> MagicMock:
    att = MagicMock()
    att.gid = gid
    att.name = name
    # ``_addr`` is the canonical routing address the prior deck's BYTES embed -- the
    # W2 0a harvest reads it via download_async + harvest_routing_addresses. None =>
    # a non-walkthrough / address-free attachment (harvests nothing).
    att._addr = addr
    att.created_at = created_at
    return att


def _passthrough_anchor(resolver: MagicMock) -> AsyncMock:
    """A W1 Source-B anchor stub that ECHOES the resolver's address guid.

    For tests NOT exercising W1 (freeze / T7 / idempotency), the guard must pass
    transparently: Source B == Source A by construction. The stub reads whatever
    address the resolver is configured to return and yields its embedded guid, so
    ``address_guid == anchored_company_id`` holds. The REAL guard (the GFR-backed
    default) is exercised by the dedicated W1 fixtures, never neutered globally.
    """
    address = resolver.resolve_routing_address_by_phone_async.return_value

    async def _anchor(
        *, task_gid: str, client: Any, query_engine: Any, verifier: Any
    ) -> AnchorResult:
        if not isinstance(address, str):
            # No resolvable address (the resolver returns None) -> this path is not
            # reached (the workflow skips at address_unresolved before W1); return a
            # sentinel that would mismatch if it ever were.
            return AnchorResult(company_id="no-address", tier=TruthTier.CACHE)
        # Models the production-default CACHE-tier anchor (no verifier wired).
        return AnchorResult(company_id=address.split("@", 1)[0].lower(), tier=TruthTier.CACHE)

    return AsyncMock(side_effect=_anchor)


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
    query_engine: Any | None = None,
    company_id_anchor: Any | None = None,
    verifier: Any | None = None,
    delete_raises_times: int = 0,
) -> tuple[OnboardingWalkthroughWorkflow, MagicMock, MagicMock, list[str]]:
    """Construct the workflow with mocked asana + attachments clients.

    Returns (workflow, mock_attachments, resolver, order) where ``order`` records
    the sequence of attachment side effects ("upload" / "list" / "delete" /
    "download") to assert upload-first-then-delete ordering and W2 harvest behavior.

    The attachments client is a STATEFUL in-memory Asana model (the faithful
    double-run substrate): ``upload_async`` APPENDS a new attachment (its ``_addr``
    harvested from the uploaded frozen bytes), ``delete_async`` REMOVES by gid,
    ``list_for_task_async`` returns the CURRENT store, ``download_async`` streams
    each attachment's bytes. So run-1's upload lands in the store and run-2's W2 0a
    harvest sees it -- no per-call index juggling. ``existing_attachments`` seeds the
    initial store (priors); ``delete_raises_times`` makes the first N deletes raise
    (the soft-fail-delete-residue arm).

    W1 is wired transparently by default (a pass-through anchor echoing the resolved
    address guid + a non-None query_engine), so tests that do not exercise W1 reach
    the freeze/T7/idempotency path unchanged. The dedicated W1 fixtures override
    ``company_id_anchor`` / ``query_engine`` to drive the guard precisely.
    """
    mock_asana = MagicMock()
    mock_attachments = MagicMock()
    resolver = resolver or _make_resolver()
    order: list[str] = []

    # Stateful in-memory attachment store (the faithful Asana model for the double-run).
    store: list[MagicMock] = list(existing_attachments or [])
    _upload_seq = {"n": 0}

    async def _upload(**kwargs: Any) -> MagicMock:
        order.append("upload")
        # Model the upload: append a new attachment whose embedded address is harvested
        # from the uploaded frozen bytes (so a later harvest reads its real guid).
        _upload_seq["n"] += 1
        name = kwargs.get("name", f"walkthrough_uploaded_{_upload_seq['n']}.html")
        raw = kwargs["file"].getvalue() if "file" in kwargs else b""
        harvested = harvest_routing_addresses(raw)
        addr = next(iter(harvested)) if harvested else None
        store.append(
            _make_attachment(
                f"uploaded-{_upload_seq['n']}",
                name,
                addr=addr,
                created_at=f"2026-06-30T00:00:{_upload_seq['n']:02d}.000Z",
            )
        )
        return MagicMock()

    mock_attachments.upload_async = AsyncMock(side_effect=_upload)

    def _list(_gid: str, **_kwargs: Any) -> _AsyncIterator:
        order.append("list")
        return _AsyncIterator(list(store))  # snapshot of the current store

    mock_attachments.list_for_task_async = MagicMock(side_effect=_list)

    async def _download(attachment_gid: str, *, destination: Any) -> None:
        order.append("download")
        payload = b"<html>no routing address</html>"
        for att in store:
            if att.gid == attachment_gid:
                # ``_raise_download is True`` => the download fails for THIS prior (F5:
                # one bad prior must not abort the whole task's idempotency check).
                if getattr(att, "_raise_download", None) is True:
                    raise RuntimeError(f"simulated download failure for {attachment_gid}")
                # ``_raw`` (explicit bytes) wins -- lets a test plant a deck whose
                # BYTES carry the same guid in multiple case-variants (F2) or several
                # distinct addresses, beyond the single-address ``_addr`` shorthand.
                explicit = getattr(att, "_raw", None)
                if isinstance(explicit, (bytes, bytearray)):
                    payload = bytes(explicit)
                elif att._addr:
                    payload = _deck_bytes(att._addr)
                break
        destination.write(payload)

    mock_attachments.download_async = AsyncMock(side_effect=_download)

    _delete_state = {"call": 0}

    async def _delete(att_gid: str) -> None:
        order.append("delete")
        _delete_state["call"] += 1
        if _delete_state["call"] <= delete_raises_times:
            raise RuntimeError(f"simulated delete failure #{_delete_state['call']}")
        # Remove from the store (the faithful delete).
        store[:] = [a for a in store if a.gid != att_gid]

    mock_attachments.delete_async = AsyncMock(side_effect=_delete)

    wf = OnboardingWalkthroughWorkflow(
        asana_client=mock_asana,
        resolver=resolver,
        attachments_client=mock_attachments,
        producer_dir=producer_dir if producer_dir is not None else Path("/tmp/_no_producer"),
        query_engine=query_engine if query_engine is not None else MagicMock(),
        company_id_anchor=(
            company_id_anchor if company_id_anchor is not None else _passthrough_anchor(resolver)
        ),
        verifier=verifier,
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


# --- F1 / opt-IN kill-switch: disabled unless EXPLICITLY enabled (MC-2 #725) ---


class TestOptInKillSwitch:
    """Two-sided: unset/false => disabled (skip); explicit-true => proceeds.

    Inverts the opt-OUT sibling default so dispatch-wiring can never fire this
    automation by default before the operator pulls the (reserved) enable lever.
    """

    async def test_unset_flag_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(constants.WALKTHROUGH_ENABLED_ENV_VAR, raising=False)
        wf, _att, _r, _o = _make_workflow()
        errors = await wf.validate_async()
        assert errors, "unset flag MUST disable (opt-in safe-default)"  # RED leg
        assert constants.WALKTHROUGH_ENABLED_ENV_VAR in errors[0]

    async def test_explicit_false_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(constants.WALKTHROUGH_ENABLED_ENV_VAR, "false")
        wf, _att, _r, _o = _make_workflow()
        assert await wf.validate_async(), "explicit false MUST disable"

    async def test_explicit_enable_proceeds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(constants.WALKTHROUGH_ENABLED_ENV_VAR, "true")
        wf, _att, _r, _o = _make_workflow()  # data_client=None => base health no-op
        assert await wf.validate_async() == [], "explicit enable MUST proceed"  # GREEN leg


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
    async def test_freeze_red_non_canonical_addr_raises_and_writes_no_file(self) -> None:
        pdir = _producer_dir()
        out_name = "walkthrough_unittest_red.html"
        out_path = pdir / "export" / out_name
        if out_path.exists():
            out_path.unlink()
        with pytest.raises(ProducerFreezeError):
            await freeze_walkthrough_deck(
                producer_dir=pdir,
                deck_template=SPIKE_DECK,
                gated_address="not-a-valid-address",
                client_name="Unit Test Clinic",
                out_filename=out_name,
            )
        # ADDR-NON-CANONICAL fires -> producer writes NO file.
        assert not out_path.exists()

    async def test_freeze_green_canonical_addr_returns_bytes_with_address(self) -> None:
        pdir = _producer_dir()
        out_name = "walkthrough_unittest_green.html"
        out_path = pdir / "export" / out_name
        try:
            frozen = await freeze_walkthrough_deck(
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

        async def _fake_freeze(**_kwargs: Any) -> bytes:
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


# --- T7 runtime tenant-binding assertion: the runtime byte-exact oracle ---
#
# Two loci close the §6 two-tenant hazard (North Star Medical 7639994340 NO guid
# vs Family +17156902466 guid d167d635):
#   (b) the upstream multiplicity guard prevents the wrong-tenant RESOLVE
#       (a colliding office_phone fail-closes in autom8y-data); and
#   (a) the runtime tenant-binding assertion (THESE tests) ensures the frozen
#       artifact carries EXACTLY the resolved address -- no producer-side drift.

# The pilot tenant (the one-guid spine: resolved == frozen == allowlisted).
_T7_RESOLVED = "d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com"
# A distinct WRONG tenant -- the address that must NEVER ride along in the deck.
_T7_FOREIGN = "11111111-2222-4333-8444-555555555555@appointments.contenteapp.com"


def _deck_bytes(*addresses: str) -> bytes:
    """A minimal frozen-deck stand-in embedding the given routing address(es).

    Mirrors how the producer renders the address (mailto + display text). The
    FIRST address is rendered twice so the oracle's dedup is exercised.
    """
    parts = ["<html><body>"]
    for i, addr in enumerate(addresses):
        parts.append(f'<a href="mailto:{addr}">Forward to {addr}</a>')
        if i == 0:
            parts.append(f"<p>Your routing address: {addr}</p>")
    parts.append("</body></html>")
    return "".join(parts).encode("utf-8")


class TestT7TenantBindingOracle:
    """Two-sided unit proof of the byte-exact oracle (pure function, no mocks).

    G-THEATER: every RED fires on a deliberately-broken INPUT (a frozen-bytes
    fixture that carries a wrong/extra/absent address), NEVER a defect injected
    into production code; the clean fixture passes GREEN.
    """

    def test_green_exact_single_address_passes(self) -> None:
        # Resolved address present (rendered twice) and NOTHING else -> no raise.
        assert_exclusive_tenant_binding(
            frozen=_deck_bytes(_T7_RESOLVED), gated_address=_T7_RESOLVED
        )

    def test_green_harvest_dedups_repeated_address(self) -> None:
        assert harvest_routing_addresses(_deck_bytes(_T7_RESOLVED)) == {_T7_RESOLVED}

    def test_red_foreign_extra_address_failcloses(self) -> None:
        # Presence holds (resolved IS in the deck) but a SECOND wrong-tenant
        # address rides along -- exclusivity fails. This is the precise gap the
        # producer's substring presence check (producer.py) cannot catch.
        with pytest.raises(TenantBindingError) as ei:
            assert_exclusive_tenant_binding(
                frozen=_deck_bytes(_T7_RESOLVED, _T7_FOREIGN),
                gated_address=_T7_RESOLVED,
            )
        msg = str(ei.value)
        assert "resolved_present=True" in msg
        assert "distinct_addresses=2" in msg
        # The foreign address is MASKED, never spilled in full.
        assert _T7_FOREIGN not in msg
        assert "11111111" in msg

    def test_red_wrong_tenant_only_failcloses(self) -> None:
        # Resolve says A; the deck carries only B -> presence fails too.
        with pytest.raises(TenantBindingError) as ei:
            assert_exclusive_tenant_binding(
                frozen=_deck_bytes(_T7_FOREIGN), gated_address=_T7_RESOLVED
            )
        assert "resolved_present=False" in str(ei.value)

    def test_red_no_routing_address_failcloses(self) -> None:
        with pytest.raises(TenantBindingError):
            assert_exclusive_tenant_binding(
                frozen=b"<html>no routing address here</html>",
                gated_address=_T7_RESOLVED,
            )

    def test_red_uppercase_hex_foreign_address_failcloses_after_casefold(self) -> None:
        """GAP-1 (chaos N3 H-T1) -- the case-sensitivity seam, RED arm through the REAL guard.

        An UPPERCASE-hex foreign routing address embedded in the frozen bytes EVADED the
        lowercase-only harvester regex: ``findall`` never saw it, so the exclusivity
        set-equality saw ONLY the resolved address and passed GREEN -- fail-OPEN, a
        wrong-tenant address riding silently in the artifact the client receives. The
        case-insensitive harvest (``re.IGNORECASE``) + lowercase-normalized set-equality now
        HARVEST the variant and bind exclusively -> RED.

        Teeth: this fixture is GREEN on the lowercase-only regex (the evaded seam); it fires
        RED only through the case-folded guard. The RED is a deliberately-broken INPUT (a
        contaminated deck-template literal -- the documented pre-flip manual-NOTE hazard) the
        hardened guard CORRECTLY rejects, NEVER a defect injected into prod code
        (@discriminating-canary-doctrine)."""
        foreign_upper = "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE@appointments.contenteapp.com"
        with pytest.raises(TenantBindingError) as ei:
            assert_exclusive_tenant_binding(
                frozen=_deck_bytes(_T7_RESOLVED, foreign_upper),
                gated_address=_T7_RESOLVED,
            )
        msg = str(ei.value)
        assert "resolved_present=True" in msg
        assert "distinct_addresses=2" in msg
        # The foreign variant is MASKED (and lowercase-normalized for DB matching), never
        # spilled in full; the normalized breadcrumb still identifies the implicated tenant.
        assert foreign_upper not in msg
        assert "aaaaaaaa" in msg

    def test_green_uppercase_variant_of_resolved_does_not_false_red(self) -> None:
        """GAP-1 GREEN twin -- the case-fold must not OVER-correct.

        An UPPERCASE-hex rendering of the SAME resolved tenant (the canonical lowercase
        address is present AND an uppercase rendering of the identical guid) is the SAME
        tenant under the lowercase-canonical invariant. The case-fold normalizes both onto
        the resolved address and binds EXCLUSIVELY -> GREEN. Case-folding catches a FOREIGN
        variant (RED above) WITHOUT false-RED'ing a case-variant of the resolved address
        itself -- the two-sided teeth bite ONLY on a wrong tenant."""
        resolved_upper = _T7_RESOLVED.upper()  # same guid, uppercase hex
        assert_exclusive_tenant_binding(
            frozen=_deck_bytes(_T7_RESOLVED, resolved_upper),
            gated_address=_T7_RESOLVED,
        )


class TestT7RuntimeBindingWorkflow:
    """Two-sided proof of the assertion in the LIVE workflow path (process_entity).

    The producer freeze is mocked to PLANT the frozen bytes -- the RED fires on a
    deliberately-broken INPUT (a wrong-tenant/extra address in the artifact),
    NEVER a defect injected into production code; the clean resolve passes GREEN.
    The Asana attach is mocked (no live write).
    """

    async def test_green_clean_freeze_binds_and_uploads(self) -> None:
        resolver = _make_resolver(address=_T7_RESOLVED)
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        with patch.object(
            producer_module,
            "freeze_walkthrough_deck",
            AsyncMock(return_value=_deck_bytes(_T7_RESOLVED)),
        ):
            out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "succeeded"
        atts.upload_async.assert_awaited_once()

    async def test_red_wrong_tenant_artifact_failcloses_no_upload(self) -> None:
        resolver = _make_resolver(address=_T7_RESOLVED)
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        with patch.object(
            producer_module,
            "freeze_walkthrough_deck",
            AsyncMock(return_value=_deck_bytes(_T7_RESOLVED, _T7_FOREIGN)),
        ):
            out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "tenant_binding_violation"
        assert out.error.recoverable is False
        atts.upload_async.assert_not_called()


class TestT7ResolveAssertIntegration:
    """Deterministic local-fixture integration: the resolve->freeze->assert path
    end-to-end, with NO live data-service (the @integration live test above stays
    the reserved AUTOM8Y_DATA_URL operator lever). Exercises BOTH walls:

      * the upstream multiplicity-guard fail-closed arm -- a colliding office_phone
        surfaces from autom8y-data as HTTP 409 / DATA-CONFLICT-002 ->
        DataServiceUnavailableError; the workflow fail-closes BEFORE any freeze, so
        no wrong-tenant address is ever minted; and
      * the producer-side runtime tenant-binding assertion -- a clean resolve binds
        (GREEN); a drifted/contaminated artifact fail-closes (RED).
    """

    async def test_collision_failcloses_before_freeze(self) -> None:
        # autom8y-data business.py:346 _single_business_or_raise raises
        # OfficePhoneCollisionError -> 409 DATA-CONFLICT-002 (errors.py) -> the core
        # SDK surfaces the non-200 as DataServiceUnavailableError. The freeze must
        # never be reached -> no wrong-tenant address is minted.
        from autom8y_core.errors import DataServiceUnavailableError

        resolver = _make_resolver(
            raises=DataServiceUnavailableError(method="resolve_routing_address_by_phone_async")
        )
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        freeze_spy = AsyncMock(return_value=_deck_bytes(_T7_RESOLVED))
        with patch.object(producer_module, "freeze_walkthrough_deck", freeze_spy):
            out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "resolve_unavailable"
        freeze_spy.assert_not_awaited()
        atts.upload_async.assert_not_called()

    async def test_clean_resolve_binds_end_to_end_dry_run(self) -> None:
        # dry_run exercises resolve -> freeze -> tenant-binding assert WITHOUT the
        # attach boundary. GREEN: the artifact binds to exactly the resolved tenant.
        resolver = _make_resolver(address=_T7_RESOLVED)
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        with patch.object(
            producer_module,
            "freeze_walkthrough_deck",
            AsyncMock(return_value=_deck_bytes(_T7_RESOLVED)),
        ):
            out = await wf.process_entity(_entity(provider="GHL"), {"dry_run": True})
        assert out.status == "succeeded"
        assert out.reason == "dry_run"
        resolver.resolve_routing_address_by_phone_async.assert_awaited_once_with(
            office_phone=PILOT_PHONE
        )
        atts.upload_async.assert_not_called()

    async def test_drifted_artifact_failcloses_end_to_end_dry_run(self) -> None:
        # Resolve is clean (tenant A) but the frozen artifact drifts to ALSO carry
        # tenant B -> the assertion fail-closes even in dry_run (it runs before the
        # dry_run return), so a contaminated deck is caught regardless of attach.
        resolver = _make_resolver(address=_T7_RESOLVED)
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        with patch.object(
            producer_module,
            "freeze_walkthrough_deck",
            AsyncMock(return_value=_deck_bytes(_T7_RESOLVED, _T7_FOREIGN)),
        ):
            out = await wf.process_entity(_entity(provider="GHL"), {"dry_run": True})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "tenant_binding_violation"
        atts.upload_async.assert_not_called()


# =====================================================================
# W1 -- GFR by-GUID identity guard (GATE-1, resolve-CORRECTNESS) unit arms
# =====================================================================
# The cross-tenant SAFETY proof through process_entity at INTEGRATION altitude
# (the mandated fixture (a), extending the real GFR roundtrip) lives in
# tests/integration/test_gfr_tenant_roundtrip.py. THESE unit arms drive the guard
# at the workflow boundary with a stubbed Source-B anchor: they assert the
# fail-closed control flow (mismatch / unresolved / unwired => skip, ZERO upload,
# NO freeze) and the two-sided GREEN (matching anchor => proceeds). Every RED fires
# on a deliberately-broken INPUT (a wrong-tenant anchor), NEVER a defect injected
# into production code (@discriminating-canary-doctrine).

# Source-A address embeds G_A's guid; the mismatch arm anchors a DIFFERENT guid.
_W1_RESOLVED_A = "d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com"
_W1_GUID_A = "d167d635-1468-4ad5-9f88-8d44c8a4d1a9"
_W1_GUID_B = "ffffffff-eeee-4ddd-8ccc-bbbbaaaa0000"  # a DIFFERENT tenant


def _stub_anchor(company_id: str, *, tier: TruthTier = TruthTier.CACHE) -> AsyncMock:
    """A Source-B anchor stub that returns a FIXED company_id (independent of A)."""

    async def _anchor(
        *, task_gid: str, client: Any, query_engine: Any, verifier: Any
    ) -> AnchorResult:
        return AnchorResult(company_id=company_id, tier=tier)

    return AsyncMock(side_effect=_anchor)


def _raising_anchor(exc: Exception) -> AsyncMock:
    """A Source-B anchor stub that raises (GFR cannot independently anchor)."""

    async def _anchor(*, task_gid: str, client: Any, query_engine: Any, verifier: Any) -> AsyncMock:
        raise exc

    return AsyncMock(side_effect=_anchor)


class TestW1IdentityGuardUnit:
    """Two-sided W1 guard arms at the workflow boundary (Source-B stubbed)."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        spy = AsyncMock(return_value=_deck_bytes(_W1_RESOLVED_A))
        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", spy)
        return spy

    async def test_red_guid_anchor_mismatch_skips_no_upload_no_freeze(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Source A (phone-resolved address) embeds G_A; Source B (parent-chain
        # anchor) is G_B -> cross-tenant. FAIL-CLOSED: skipped(guid_anchor_mismatch),
        # ZERO upload, freeze NEVER runs (the guard precedes FREEZE). The RED asserts
        # on the SKIP + no-attach, NOT on the resolved address (P6).
        freeze_spy = self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver, company_id_anchor=_stub_anchor(_W1_GUID_B)
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "guid_anchor_mismatch"
        atts.upload_async.assert_not_called()
        freeze_spy.assert_not_awaited()

    async def test_green_guid_anchor_match_proceeds_and_uploads(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The two-sided GREEN twin: Source B == Source A (G_A) -> the guard PASSES,
        # the deck binds (T7) and uploads. W1 bites ONLY on the cross-tenant case.
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver, company_id_anchor=_stub_anchor(_W1_GUID_A)
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "succeeded"
        atts.upload_async.assert_awaited_once()

    async def test_red_anchor_unresolved_skips_no_upload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GFR cannot independently anchor (no parent chain to a Business root):
        # UnresolvedError -> skipped(anchor_unresolved), ZERO upload, NO freeze. The
        # safe degrade (an un-anchorable task must never attach on the phone alone).
        from autom8_asana.resolution.gfr.errors import UnresolvedError

        freeze_spy = self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver,
            company_id_anchor=_raising_anchor(
                UnresolvedError(fields=["company_id"], reason="no-identity-path")
            ),
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "anchor_unresolved"
        atts.upload_async.assert_not_called()
        freeze_spy.assert_not_awaited()

    async def test_red_guard_violation_skips_distinct_reason_no_upload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # F3: a GuardViolationError (the v1 PHI-leak trap / identity-path purity drift
        # -- a hard STRUCTURAL signal) still fail-closes (skip, no upload) but is now
        # surfaced with a DISTINCT, LOUD reason ("guard_violation"), never masked as a
        # routine "anchor_unresolved". The trap-reintroduction signal must not hide in
        # the benign no-identity-path noise.
        from autom8_asana.resolution.gfr.errors import GuardViolationError

        freeze_spy = self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver,
            company_id_anchor=_raising_anchor(GuardViolationError("identity-path drift")),
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "guard_violation"  # F3: distinct, NOT anchor_unresolved
        atts.upload_async.assert_not_called()
        freeze_spy.assert_not_awaited()

    async def test_red_query_engine_unwired_skips_no_upload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No substrate wired (query_engine=None) -> the guard cannot certify
        # correctness -> fail-closed skip BEFORE the anchor call, ZERO upload.
        freeze_spy = self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        # Force query_engine None by constructing the workflow directly (the builder
        # defaults it to a MagicMock; here we assert the unwired fail-closed path).
        wf = OnboardingWalkthroughWorkflow(
            asana_client=MagicMock(),
            resolver=resolver,
            attachments_client=_make_workflow(resolver=resolver)[1],
            producer_dir=Path("/tmp/_no_producer"),
            query_engine=None,
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "anchor_unresolved"
        freeze_spy.assert_not_awaited()


# =====================================================================
# W2 -- idempotency presence-gate (GATE-3, attach-IDEMPOTENCY) -- fixture (b)
# =====================================================================
# The mandated double-run + four arms. Spine: upload/delete ALWAYS mocked, the SDK
# resolve mocked, the W1 guard wired pass-through (Source B == Source A) so the
# idempotency behavior is isolated. The date-FREE key is the EMBEDDED company guid,
# byte-harvested from prior decks -- NEVER the date-stamped name. Every arm is
# two-sided: run-2 (or a matching prior) yields ZERO net-new attachments.

# The deck the sweep would attach embeds this address (guid == target).
_W2_RESOLVED = "d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com"
_W2_OTHER = "11111111-2222-4333-8444-555555555555@appointments.contenteapp.com"


class TestW2IdempotencyPresenceGate:
    """Fixture (b): double-run zero-net-new + arms (i) no-prior, (ii) different-guid
    replace, (iii) legacy date-stamped skip, (iv) >1-prior dedupe-down + delete-fail."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        spy = AsyncMock(return_value=_deck_bytes(_W2_RESOLVED))
        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", spy)
        return spy

    async def test_double_run_zero_net_new(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # THE double-run invariant: run twice on the same task; run-2 yields ZERO
        # net-new attachments and ZERO uploads/deletes. Run-1 sees no prior and
        # mints exactly 1 (the stateful store records it); run-2's 0a harvest sees
        # that deck (same embedded guid) and SKIPS. The store is the faithful Asana
        # model -- run-1's REAL upload is what run-2 reads, not a hand-seeded prior.
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W2_RESOLVED)
        wf, atts, _, _ = _make_workflow(resolver=resolver, existing_attachments=[])

        out1 = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out1.status == "succeeded"
        assert atts.upload_async.await_count == 1  # run-1 mints exactly 1

        out2 = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out2.status == "skipped"
        assert out2.reason == "already_attached"
        assert atts.upload_async.await_count == 1  # NO net-new upload on run-2
        # run-2 performed zero deletes (no dedupe needed for a single matching prior).
        atts.delete_async.assert_not_called()

    async def test_arm_i_no_prior_mints_exactly_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W2_RESOLVED)
        wf, atts, _, _ = _make_workflow(resolver=resolver, existing_attachments=[])
        out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out.status == "succeeded"
        atts.upload_async.assert_awaited_once()

    async def test_arm_ii_different_guid_prior_does_not_skip_replaces(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A prior deck embeds a DIFFERENT guid (the tenant changed) -> does NOT skip;
        # proceeds to freeze->upload->delete-old (the replace arm).
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W2_RESOLVED)
        other = _make_attachment(
            "deck-other", "walkthrough_task-1_20250101000000.html", addr=_W2_OTHER
        )
        wf, atts, _, _ = _make_workflow(resolver=resolver, existing_attachments=[other])
        out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out.status == "succeeded"
        atts.upload_async.assert_awaited_once()  # 1 upload (replace)
        # delete-old reaps the foreign-guid prior (upload-first replacement).
        atts.delete_async.assert_awaited_once_with("deck-other")

    async def test_arm_iii_legacy_date_stamped_matching_guid_skips(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A LEGACY date-stamped deck (walkthrough_{gid}_{ts}.html) minted before any
        # guid-in-name convention, embedding the SAME target guid -> SKIP (migration).
        # Recognized by its EMBEDDED address, not its name.
        freeze_spy = self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W2_RESOLVED)
        legacy = _make_attachment(
            "deck-legacy", "walkthrough_task-1_20240101000000.html", addr=_W2_RESOLVED
        )
        wf, atts, _, _ = _make_workflow(resolver=resolver, existing_attachments=[legacy])
        out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "already_attached"
        atts.upload_async.assert_not_called()
        freeze_spy.assert_not_awaited()

    async def test_arm_iv_more_than_one_prior_dedupes_down_no_compounding(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # TWO priors for the target guid (a delete-FAILURE residue from a prior run):
        # dedupe-DOWN to exactly 1, SKIP the re-mint, ZERO net-new uploads. Covers
        # GATE-3 on the delete-FAILURE branch (the named residual).
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W2_RESOLVED)
        residue_old = _make_attachment(
            "deck-old",
            "walkthrough_task-1_20240101000000.html",
            addr=_W2_RESOLVED,
            created_at="2024-01-01T00:00:00.000Z",
        )
        residue_new = _make_attachment(
            "deck-new",
            "walkthrough_task-1_20260601000000.html",
            addr=_W2_RESOLVED,
            created_at="2026-06-01T00:00:00.000Z",
        )
        wf, atts, _, _ = _make_workflow(
            resolver=resolver, existing_attachments=[residue_old, residue_new]
        )
        out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "already_attached_deduped"
        # Dedupe-down: keep the NEWEST (deck-new), delete the older residue.
        atts.delete_async.assert_awaited_once_with("deck-old")
        # No re-mint: zero net-new uploads (non-compounding).
        atts.upload_async.assert_not_called()

    async def test_arm_iv_delete_failure_does_not_cascade_to_duplicates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The residue's delete FAILS (mock delete_async to raise) -> the dedupe-down
        # soft-fails per item, STILL skips the re-mint (zero uploads). A persistent
        # delete failure can never cascade into unbounded duplicate decks.
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W2_RESOLVED)
        residue_old = _make_attachment(
            "deck-old",
            "walkthrough_task-1_20240101000000.html",
            addr=_W2_RESOLVED,
            created_at="2024-01-01T00:00:00.000Z",
        )
        residue_new = _make_attachment(
            "deck-new",
            "walkthrough_task-1_20260601000000.html",
            addr=_W2_RESOLVED,
            created_at="2026-06-01T00:00:00.000Z",
        )
        wf, atts, _, _ = _make_workflow(
            resolver=resolver,
            existing_attachments=[residue_old, residue_new],
            delete_raises_times=99,  # every delete fails
        )
        out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "already_attached_deduped"
        # The delete was ATTEMPTED (and soft-failed) but the re-mint is STILL skipped:
        # no duplicate created despite the stuck delete.
        atts.delete_async.assert_awaited_once_with("deck-old")
        atts.upload_async.assert_not_called()


# =====================================================================
# OB-GUIDE byte-exact attestation (forwarding-cutover-first-value · S3)
# =====================================================================
# Land predicate (a) of first-value for North Star Family Chiropractic: prove the
# personalized walkthrough deck carries the BYTE-EXACT grandeur routing address
# d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com (the FULL
# uuidv4 -- never the 8-char shorthand d167d635@...). Proven by a TWO-SIDED
# byte-diff through the REAL Node producer + an INDEPENDENT oracle, never by
# "the producer ran". N=1, positively selected: the address is DERIVED from the
# confirmed guid via the autom8y-core gate -- never reverse-matched from a render
# or name-guessed (G-DENOM).

NSF_GUID = "d167d635-1468-4ad5-9f88-8d44c8a4d1a9"
# A DIFFERENT, equally-valid uuidv4. The producer ACCEPTS it (it is MC-1
# canonical); the oracle CATCHES it (AC-3) -- proving the teeth are independent
# of the producer.
WRONG_BUT_CANONICAL_GUID = "b167331c-536f-4996-9b2d-2f696f35f556"

# The vendored producer lives at <repo-root>/vendor/deck-producer; resolve it
# relative to THIS file so the attestation tests need no env var to find it.
_VENDORED_PRODUCER_DIR = Path(__file__).resolve().parents[4] / "vendor" / "deck-producer"

# FORK-DECK(a): the provider-agnostic email-forwarding deck (the OB guide).
OB_GUIDE_DECK = "email-forwarding-setup"


def _core_mint_available() -> bool:
    """True iff the autom8y-core canonical-address gate is importable."""
    try:
        from autom8y_core.helpers.routing import format_routing_address  # noqa: F401

        return True
    except ImportError:
        return False


def _vendored_producer_available() -> bool:
    """True iff node + the vendored producer (entrypoint + node_modules) exist."""
    return (
        shutil.which("node") is not None
        and (_VENDORED_PRODUCER_DIR / "build" / "inline.mjs").exists()
        and (_VENDORED_PRODUCER_DIR / "node_modules").exists()
    )


requires_ob_guide_mechanism = pytest.mark.skipif(
    not (_vendored_producer_available() and _core_mint_available()),
    reason="OB-guide mechanism needs node>=22 + vendored producer node_modules + autom8y-core mint",
)

requires_core_mint = pytest.mark.skipif(
    not _core_mint_available(),
    reason="autom8y-core format_routing_address gate not importable",
)


def _mint(guid: str) -> str:
    """Mint the canonical routing address via the autom8y-core gate.

    G-PROPAGATE: calls ``format_routing_address`` DIRECTLY -- it does NOT
    reimplement the formatter, the canonical-address regex, or any phone->guid
    resolution. Imported lazily so test COLLECTION is robust where autom8y-core
    is absent (callers are skip-gated on _core_mint_available()).
    """
    from autom8y_core.helpers.routing import format_routing_address

    return format_routing_address(guid)


# --- the byte-diff ORACLE (the TEETH) ---
#
# Version/variant-AGNOSTIC, UUID-shaped routing-address harvester. It is STRICTLY
# WEAKER than the producer's CANONICAL_ADDR_RE (inline-dc-runtime.mjs:115-116),
# which anchors ^...$ AND pins the v4 version nibble `4` and the variant nibble
# `[89ab]`. This pattern is unanchored (substring search) and accepts ANY hex in
# every UUID slot -- a provable superset of CANONICAL_ADDR_RE's acceptance set --
# so it CANNOT be a reimplementation of the canonical formatter/validator. Being
# shape-based it excludes, by construction, BOTH the deck placeholder
# `xxxx-xxxx@appointments.contenteapp.com` (EmailForwardingSetup.dc.html:342 --
# 'x' is not a hex digit) AND the okAddr-regex source literal (which carries
# `[0-9a-f]` class text, not literal hex in the UUID slots).
_APPOINTMENT_ADDR_RE = re.compile(
    rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}@appointments\.contenteapp\.com"
)


def harvest_appointment_addresses(frozen: bytes) -> set[str]:
    """Extract EVERY appointments.contenteapp.com routing address embedded in the
    frozen deck bytes, returned as a set of decoded strings.

    An independent extractor (strictly-weaker shape than the producer's
    validator), NOT a re-derivation of the canonical address form.
    """
    return {match.decode("ascii") for match in _APPOINTMENT_ADDR_RE.findall(frozen)}


def assert_byte_exact_tenant_address(frozen: bytes, expected: str) -> None:
    """Two-part byte-exact oracle (the TEETH):

    1. PRESENCE    -- ``expected`` is a literal substring of the frozen bytes.
    2. EXCLUSIVITY -- the ONLY appointment address harvested is exactly
       ``expected`` (no wrong-but-canonical guid, no 8-char prefix shorthand, no
       name-resolved address, no placeholder).

    ``expected`` MUST be minted INDEPENDENTLY via the autom8y-core gate. Comparing
    the render against the same ``--addr`` fed to the producer would be
    tautological theater (G-THEATER): the oracle must be able to DISAGREE with the
    producer, which AC-3's RED arm proves.
    """
    assert expected.encode("utf-8") in frozen, (
        f"PRESENCE failed: {expected!r} is not a substring of the frozen bytes"
    )
    harvested = harvest_appointment_addresses(frozen)
    assert harvested == {expected}, (
        f"EXCLUSIVITY (byte-diff teeth) failed: harvested {harvested!r} != {{{expected!r}}}"
    )


async def _freeze_ob_guide(*, gated_address: str, out_filename: str) -> bytes:
    """Render+freeze the OB-guide deck via the PYTHON invoker, which retains the
    producer.py:141-142 output re-validation (NOT a raw ``node`` shell)."""
    return await freeze_walkthrough_deck(
        producer_dir=_VENDORED_PRODUCER_DIR,
        deck_template=OB_GUIDE_DECK,
        gated_address=gated_address,
        client_name="North Star Family Chiropractic",
        out_filename=out_filename,
    )


async def _render_placeholder_no_addr(out_filename: str) -> bytes:
    """Render the deck WITHOUT ``--addr`` (the placeholder path).

    ``freeze_walkthrough_deck`` mandates an address, so the no-addr arm (AC-1 RED)
    shells the SAME node producer directly with no address. This is NOT a
    reimplementation of the freeze -- it is the identical producer invoked without
    a gated address, so the oracle can prove it harvests NOTHING from a
    placeholder-only deck.
    """
    proc = await asyncio.create_subprocess_exec(
        "node",
        "build/inline.mjs",
        "--deck",
        f"templates/{OB_GUIDE_DECK}",
        "--out",
        out_filename,
        cwd=_VENDORED_PRODUCER_DIR,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, (stderr or b"").decode("utf-8", "replace")[:300]
    return (_VENDORED_PRODUCER_DIR / "export" / out_filename).read_bytes()


def _ob_out(tag: str) -> str:
    """Unique export filename (xdist-safe) that matches ATTACHMENT_GLOB."""
    return f"walkthrough_1210776074464695_obguide_{tag}_{uuid.uuid4().hex[:12]}.html"


def _ob_cleanup(out_filename: str) -> None:
    (_VENDORED_PRODUCER_DIR / "export" / out_filename).unlink(missing_ok=True)


@requires_ob_guide_mechanism
class TestObGuideByteExactAttestation:
    """Two-sided byte-exact attestation through the REAL producer + the oracle.

    AC-1 / AC-2 / AC-3 / AC-7. The LIVE Asana attach is NEVER performed (staged
    only); the deck address is byte-verified, never assumed from a green run.
    """

    async def test_ac1_green_oracle_passes_on_grandeur_render(self) -> None:
        # GREEN: the real d167d635 render satisfies presence AND exclusivity.
        out = _ob_out("ac1g")
        try:
            expected = _mint(NSF_GUID)
            frozen = await _freeze_ob_guide(gated_address=expected, out_filename=out)
            assert_byte_exact_tenant_address(frozen, expected)
            assert harvest_appointment_addresses(frozen) == {expected}
        finally:
            _ob_cleanup(out)

    async def test_ac1_red_no_addr_harvests_empty(self) -> None:
        # RED: with NO --addr the deck renders only the `xxxx-xxxx` placeholder
        # (raw-present, but 'x' is not hex), so the oracle harvests the EMPTY set.
        out = _ob_out("ac1r")
        try:
            frozen = await _render_placeholder_no_addr(out)
            assert harvest_appointment_addresses(frozen) == set()
        finally:
            _ob_cleanup(out)

    async def test_ac2_red_prefix_shorthand_raises(self) -> None:
        # RED: the 8-char prefix shorthand is NOT MC-1 canonical -> the producer
        # refuses (ADDR-NON-CANONICAL) -> ProducerFreezeError.
        out = _ob_out("ac2r")
        try:
            with pytest.raises(ProducerFreezeError):
                await _freeze_ob_guide(
                    gated_address="d167d635@appointments.contenteapp.com",
                    out_filename=out,
                )
        finally:
            _ob_cleanup(out)

    async def test_ac2_green_full_uuid_accepted(self) -> None:
        # GREEN: the full uuidv4 address is accepted and frozen into the deck.
        out = _ob_out("ac2g")
        try:
            expected = _mint(NSF_GUID)
            frozen = await _freeze_ob_guide(gated_address=expected, out_filename=out)
            assert expected.encode("utf-8") in frozen
        finally:
            _ob_cleanup(out)

    async def test_ac3_green_byte_equal_independent_mint(self) -> None:
        # GREEN keystone: feed the d167d635 mint; compare against an INDEPENDENT
        # d167d635 mint (never the fed --addr) -> byte-equal, oracle PASSES.
        out = _ob_out("ac3g")
        try:
            fed = _mint(NSF_GUID)
            frozen = await _freeze_ob_guide(gated_address=fed, out_filename=out)
            expected = _mint(NSF_GUID)  # independent re-mint from the guid
            assert_byte_exact_tenant_address(frozen, expected)
        finally:
            _ob_cleanup(out)

    async def test_ac3_red_wrong_but_canonical_caught(self) -> None:
        # RED keystone: feed a DIFFERENT valid v4. The producer ACCEPTS it (it is
        # canonical) and injects it; the oracle -- comparing against the d167d635
        # mint -- RAISES. Break the INPUT, never the SURFACE
        # (discriminating-canary-doctrine): proves the teeth are producer-
        # independent. The grandeur address is genuinely absent from this render.
        out = _ob_out("ac3r")
        try:
            fed_wrong = _mint(WRONG_BUT_CANONICAL_GUID)
            frozen = await _freeze_ob_guide(gated_address=fed_wrong, out_filename=out)
            assert fed_wrong.encode("utf-8") in frozen  # producer DID accept+inject
            expected = _mint(NSF_GUID)
            with pytest.raises(AssertionError):
                assert_byte_exact_tenant_address(frozen, expected)
        finally:
            _ob_cleanup(out)

    async def test_ac7_integrity_receipt_sha256_and_byte_diff_pass(self) -> None:
        # AC-7 TIER-1: compute a sha256 integrity digest over the frozen bytes and
        # assert the byte-diff oracle PASSES on the real grandeur render.
        out = _ob_out("ac7")
        try:
            expected = _mint(NSF_GUID)
            frozen = await _freeze_ob_guide(gated_address=expected, out_filename=out)
            digest = hashlib.sha256(frozen).hexdigest()
            assert len(digest) == 64
            assert all(c in "0123456789abcdef" for c in digest)
            assert len(frozen) > 0
            assert_byte_exact_tenant_address(frozen, expected)
        finally:
            _ob_cleanup(out)


@requires_core_mint
class TestObGuideMint:
    """AC-4: the autom8y-core gate mints ONLY from a guid -- phone, E.164, and
    name inputs each raise ValueError (the address is never name/phone-derived)."""

    @pytest.mark.parametrize(
        "bad_input",
        ["7639994340", "+17156902466", "North Star Medical Clinic"],
    )
    def test_ac4_red_phone_or_name_raises_valueerror(self, bad_input: str) -> None:
        with pytest.raises(ValueError):
            _mint(bad_input)

    def test_ac4_green_guid_mints_grandeur_address(self) -> None:
        assert (
            _mint(NSF_GUID) == "d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com"
        )


class TestObGuideOracleHygiene:
    """AC-6 + harvester shape unit-tests. No producer/core required -- these run
    everywhere (pure source inspection + synthetic bytes)."""

    def test_ac6_oracle_source_has_no_live_attach_no_phone_or_name_resolution(self) -> None:
        # Static grep-zero over the oracle source: the byte-exact path must NOT
        # route through the live Asana attach, phone->guid resolution, or
        # name->guid resolution.
        source = inspect.getsource(harvest_appointment_addresses) + inspect.getsource(
            assert_byte_exact_tenant_address
        )
        for forbidden in (
            "upload_async",
            "resolve_routing_address_by_phone",
            "resolve_routing_address_by_name",
            "nameparser",
        ):
            assert forbidden not in source, f"oracle must not reference {forbidden!r}"

    def test_harvester_ignores_placeholder_and_shorthand_catches_canonical(self) -> None:
        # Deterministic shape proof (no producer): the placeholder and the 8-char
        # shorthand are invisible to the harvester; a real canonical address is
        # caught exactly once.
        grandeur = "d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com"
        blob = (
            b"placeholder xxxx-xxxx@appointments.contenteapp.com and shorthand "
            b"d167d635@appointments.contenteapp.com and real " + grandeur.encode("utf-8") + b" end"
        )
        assert harvest_appointment_addresses(blob) == {grandeur}

    def test_harvester_strictly_weaker_than_canonical_addr_re(self) -> None:
        # The harvester accepts a NON-v4 UUID-shaped address (version nibble 'd',
        # variant nibble 'c') that CANONICAL_ADDR_RE would REJECT -- proving the
        # harvester is strictly weaker, hence not a reimplementation (G-PROPAGATE).
        non_v4 = b"00000000-0000-d000-c000-000000000000@appointments.contenteapp.com"
        assert harvest_appointment_addresses(non_v4) == {
            "00000000-0000-d000-c000-000000000000@appointments.contenteapp.com"
        }


# =====================================================================
# PR1-HARDEN -- robustness fixes F1..F5 (QA-adversary fail-safe flags)
# =====================================================================
# Each fix is two-sided through the REAL process_entity / validate_async with the
# faithful stateful attachments store. The per-task SAFETY core already PASSED
# adversarial review (no wrong-tenant attach in any probe); these prove the
# robustness deltas (tenant-isolation reap, dedupe correctness, guard
# observability, sweep-inert detection, bounded harvest) WITHOUT regressing it.

# Reuse the W2 tenant guids: target (A) vs a distinct foreign tenant (X).
_HARDEN_TARGET = _W2_RESOLVED  # tenant A's canonical address (the deck to keep)
_HARDEN_FOREIGN = _W2_OTHER  # a DIFFERENT tenant's address (the wrong-tenant residue)
_HARDEN_TARGET_GUID = _W2_RESOLVED.split("@", 1)[0].lower()
_HARDEN_FOREIGN_GUID = _W2_OTHER.split("@", 1)[0].lower()


def _capture_workflow_logs() -> Any:
    """structlog capture over the workflow module logger (level + event + kwargs).

    Clears the BoundLoggerLazyProxy ``bind`` cache so ``capture_logs`` intercepts
    even when an earlier test triggered ``cache_logger_on_first_use`` binding
    (mirrors tests/unit/core/test_concurrency.py::TestStructuredLogging).
    """
    from autom8_asana.automation.workflows.onboarding_walkthrough import workflow as _wf_mod

    proxy = _wf_mod.logger
    if "bind" in getattr(proxy, "__dict__", {}):
        del proxy.__dict__["bind"]
    return structlog.testing.capture_logs()


class TestF1ForeignPriorReap:
    """F1 -- a foreign-tenant survivor (delete-old soft-fail residue) is REAPED on the
    already-attached SKIP path, closing the wrong-tenant-persists tenant-isolation hole."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        spy = AsyncMock(return_value=_deck_bytes(_HARDEN_TARGET))
        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", spy)
        return spy

    async def test_foreign_survivor_reaped_on_run2_target_intact_no_remint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # run1: target A has NO prior but a FOREIGN tenant-X deck sits on the task.
        # A's deck mints (upload), then delete-old tries to reap X but SOFT-FAILS
        # (delete_raises_times=1) -> X SURVIVES alongside A (the residue). run2: A is
        # already_attached; F1 reaps the foreign X deck (deletes=1 on the survivor),
        # A's deck stays intact, and there is NO re-mint.
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_HARDEN_TARGET)
        foreign = _make_attachment(
            "deck-foreign-X", "walkthrough_task-1_20200101000000.html", addr=_HARDEN_FOREIGN
        )
        wf, atts, _, _ = _make_workflow(
            resolver=resolver, existing_attachments=[foreign], delete_raises_times=1
        )

        out1 = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out1.status == "succeeded"
        assert atts.upload_async.await_count == 1  # A's deck minted
        deletes_after_run1 = atts.delete_async.await_count  # the soft-failed reap attempt

        out2 = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out2.status == "skipped"
        assert out2.reason == "already_attached"
        # F1: run2 performed exactly ONE delete -- the foreign survivor.
        assert atts.delete_async.await_count - deletes_after_run1 == 1
        assert atts.delete_async.await_args.args == ("deck-foreign-X",)
        # No re-mint across the double run.
        assert atts.upload_async.await_count == 1

        # Post-condition via the REAL harvest: the foreign guid is GONE, the target
        # deck SURVIVES (one prior for the target guid).
        after = await wf._existing_walkthrough_guids("task-1")
        assert _HARDEN_FOREIGN_GUID not in after, "foreign wrong-tenant deck must be reaped"
        assert _HARDEN_TARGET_GUID in after, "target deck must survive the reap"
        assert len(after[_HARDEN_TARGET_GUID]) == 1
        print(
            f"[F1] run2 reaped foreign={_HARDEN_FOREIGN_GUID[:8]} deletes=1 "
            f"target_intact={_HARDEN_TARGET_GUID[:8]} uploads={atts.upload_async.await_count}"
        )

    async def test_no_foreign_prior_reap_is_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Two-sided: with ONLY the target's own deck present, the reap is a strict
        # no-op (zero deletes) -- it acts solely when a foreign prior exists.
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_HARDEN_TARGET)
        own = _make_attachment(
            "deck-A", "walkthrough_task-1_20260101000000.html", addr=_HARDEN_TARGET
        )
        wf, atts, _, _ = _make_workflow(resolver=resolver, existing_attachments=[own])
        out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "already_attached"
        atts.delete_async.assert_not_called()  # reap no-op; nothing foreign to reap
        atts.upload_async.assert_not_called()


class TestF2MixedCaseDedupe:
    """F2 -- a single legacy deck embedding the target guid in MIXED CASE is recognized
    as ONE prior (already_attached), never double-counted into a self-deleting dedupe."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        spy = AsyncMock(return_value=_deck_bytes(_HARDEN_TARGET))
        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", spy)
        return spy

    async def test_mixed_case_single_deck_survives_skip_no_self_delete(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The legacy deck's BYTES carry the SAME guid in two case-variants (lower +
        # UPPER) -- harvest_routing_addresses returns two distinct strings that both
        # fold to one guid. Pre-F2 this counted as 2 priors -> dedupe-down deleted the
        # only real deck. Post-F2: ONE prior -> already_attached, deletes=0, survives.
        freeze_spy = self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_HARDEN_TARGET)
        legacy = _make_attachment(
            "deck-legacy-mixed", "walkthrough_task-1_2018.html", addr=_HARDEN_TARGET
        )
        # Plant mixed-case bytes (lower + UPPER of the same guid) on this one deck.
        legacy._raw = _deck_bytes(_HARDEN_TARGET, _HARDEN_TARGET.upper())
        wf, atts, _, _ = _make_workflow(resolver=resolver, existing_attachments=[legacy])

        out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})

        assert out.status == "skipped"
        # CRITICAL: already_attached, NOT already_attached_deduped (no spurious dedupe).
        assert out.reason == "already_attached"
        assert atts.delete_async.await_count == 0  # deletes=0: the deck is NOT self-deleted
        assert atts.upload_async.await_count == 0  # no re-mint
        freeze_spy.assert_not_awaited()

        # The single legacy deck SURVIVES and is still recognized as one prior.
        after = await wf._existing_walkthrough_guids("task-1")
        assert _HARDEN_TARGET_GUID in after
        assert [a.gid for a in after[_HARDEN_TARGET_GUID]] == ["deck-legacy-mixed"]
        print(
            f"[F2] mixed-case single deck -> {out.reason} deletes=0 uploads=0 "
            f"survivors={sorted(after)}"
        )


class TestF3GuardObservability:
    """F3 -- the W1 anchor failure modes emit DISTINCT, LOUD reasons + levels: a
    GuardViolationError / AmbiguousCardinalityError is no longer masked as a benign
    anchor_unresolved WARNING. All still fail-closed (skip, no upload)."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        spy = AsyncMock(return_value=_deck_bytes(_W1_RESOLVED_A))
        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", spy)
        return spy

    async def _run_with_anchor_exc(
        self, monkeypatch: pytest.MonkeyPatch, exc: Exception
    ) -> tuple[Any, list[dict[str, Any]]]:
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(resolver=resolver, company_id_anchor=_raising_anchor(exc))
        with _capture_workflow_logs() as captured:
            out = await wf.process_entity(_entity(provider="GHL"), {})
        atts.upload_async.assert_not_called()  # all arms remain fail-closed
        return out, captured

    async def test_guard_violation_distinct_reason_error_level(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from autom8_asana.resolution.gfr.errors import GuardViolationError

        out, captured = await self._run_with_anchor_exc(
            monkeypatch, GuardViolationError("the PHI-leak trap was reintroduced")
        )
        assert out.status == "skipped"
        assert out.reason == "guard_violation"
        entry = next(e for e in captured if e["event"] == "onboarding_walkthrough_skipped")
        assert entry["reason"] == "guard_violation"
        assert entry["log_level"] == "error"  # LOUD, not a routine warning
        print(f"[F3] GuardViolationError -> reason={out.reason!r} level={entry['log_level']!r}")

    async def test_ambiguous_cardinality_distinct_reason_error_level(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from autom8_asana.resolution.gfr.errors import AmbiguousCardinalityError

        out, captured = await self._run_with_anchor_exc(
            monkeypatch, AmbiguousCardinalityError(row_count=2)
        )
        assert out.status == "skipped"
        assert out.reason == "ambiguous_anchor"
        entry = next(e for e in captured if e["event"] == "onboarding_walkthrough_skipped")
        assert entry["reason"] == "ambiguous_anchor"
        assert entry["log_level"] == "error"
        print(
            f"[F3] AmbiguousCardinalityError -> reason={out.reason!r} level={entry['log_level']!r}"
        )

    async def test_benign_no_identity_path_stays_anchor_unresolved_warning(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The two-sided twin: a BENIGN UnresolvedError(no-identity-path) MUST stay the
        # quiet anchor_unresolved WARNING -- F3 must not over-escalate the routine case.
        from autom8_asana.resolution.gfr.errors import UnresolvedError

        out, captured = await self._run_with_anchor_exc(
            monkeypatch, UnresolvedError(fields=["company_id"], reason="no-identity-path")
        )
        assert out.status == "skipped"
        assert out.reason == "anchor_unresolved"
        entry = next(e for e in captured if e["event"] == "onboarding_walkthrough_skipped")
        assert entry["reason"] == "anchor_unresolved"
        assert entry["log_level"] == "warning"  # benign stays quiet
        print(f"[F3] benign UnresolvedError -> reason={out.reason!r} level={entry['log_level']!r}")


class TestF4UnwiredGuardInert:
    """F4 -- an ENABLED-but-unwired deploy (query_engine=None) is surfaced LOUDLY at
    validate_async (sweep INERT), distinct from a per-task skip, so a dark sweep is
    detectable rather than silently attaching nothing."""

    async def test_validate_async_flags_unwired_query_engine(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(constants.WALKTHROUGH_ENABLED_ENV_VAR, "true")
        wf = OnboardingWalkthroughWorkflow(
            asana_client=MagicMock(),
            resolver=_make_resolver(),
            attachments_client=MagicMock(),
            producer_dir=Path("/tmp/_no_producer"),
            query_engine=None,  # ENABLED but UNWIRED -> whole sweep would be inert
        )
        with _capture_workflow_logs() as captured:
            problems = await wf.validate_async()

        assert problems, "unwired guard MUST fail pre-flight (not silently dark)"
        assert any("INERT" in p and "query_engine" in p for p in problems)
        inert = [e for e in captured if e["event"] == "onboarding_walkthrough_guard_inert"]
        assert len(inert) == 1, "exactly one LOUD inert signal at pre-flight"
        assert inert[0]["log_level"] == "error"
        print(
            f"[F4] unwired validate_async -> problems={len(problems)} level={inert[0]['log_level']!r}"
        )

    async def test_validate_async_clean_when_wired(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Two-sided: enabled AND wired (non-None query_engine) -> no inert problem.
        monkeypatch.setenv(constants.WALKTHROUGH_ENABLED_ENV_VAR, "true")
        wf, _atts, _r, _o = _make_workflow()  # builder wires a non-None query_engine
        with _capture_workflow_logs() as captured:
            problems = await wf.validate_async()
        assert problems == [], "enabled + wired MUST pass pre-flight"
        assert not [e for e in captured if e["event"] == "onboarding_walkthrough_guard_inert"]


class TestF5BoundedHarvest:
    """F5 -- the W2 prior byte-harvest is BOUNDED: an oversized prior is skipped (by
    reported size up front, and by a hard mid-stream cap), and a single
    failing/oversized prior returns None instead of aborting the task."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        spy = AsyncMock(return_value=_deck_bytes(_HARDEN_TARGET))
        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", spy)
        return spy

    async def test_oversize_prior_skipped_by_reported_size_no_download(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A prior whose reported size exceeds the cap is skipped BEFORE download (never
        # pulled into memory) and logged. The task still mints the target normally.
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_HARDEN_TARGET)
        oversize = _make_attachment(
            "deck-oversize", "walkthrough_task-1_20200101000000.html", addr=_HARDEN_FOREIGN
        )
        oversize.size = constants.MAX_PRIOR_DECK_BYTES + 1
        wf, atts, _, _ = _make_workflow(resolver=resolver, existing_attachments=[oversize])

        with _capture_workflow_logs() as captured:
            out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})

        assert out.status == "succeeded"  # task completes, not aborted/OOM
        # The oversized prior was NEVER downloaded (skipped by the size pre-check).
        downloaded_gids = [c.args[0] for c in atts.download_async.await_args_list]
        assert "deck-oversize" not in downloaded_gids
        skip_logs = [
            e for e in captured if e["event"] == "onboarding_walkthrough_prior_oversize_skipped"
        ]
        assert len(skip_logs) == 1
        assert skip_logs[0]["log_level"] == "warning"
        print(f"[F5] oversize prior (size={oversize.size}) skipped pre-download, task={out.status}")

    async def test_capped_buffer_aborts_oversize_stream_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Mid-stream guard: when the reported size is unknown/under-reported, the
        # _CappedBuffer aborts a download that streams past the cap and the helper
        # returns None (skip), never materializing an unbounded blob.
        monkeypatch.setattr(constants, "MAX_PRIOR_DECK_BYTES", 64)  # tiny cap, no big alloc
        wf, atts, _, _ = _make_workflow()

        async def _flood(_gid: str, *, destination: Any) -> None:
            destination.write(b"x" * 200)  # 200 > 64 cap -> _CappedBuffer trips

        atts.download_async = AsyncMock(side_effect=_flood)
        with _capture_workflow_logs() as captured:
            raw = await wf._download_attachment_bytes("deck-flood")
        assert raw is None  # oversized stream -> skip, not an unbounded buffer
        trunc = [
            e for e in captured if e["event"] == "onboarding_walkthrough_prior_oversize_truncated"
        ]
        assert len(trunc) == 1
        print(f"[F5] streamed 200B past 64B cap -> raw={raw} (truncated+skipped)")

    async def test_download_error_returns_none_does_not_abort(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A prior whose download RAISES returns None (logged) rather than propagating,
        # so one bad prior never aborts the whole task's idempotency check.
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_HARDEN_TARGET)
        bad = _make_attachment(
            "deck-bad", "walkthrough_task-1_20200101000000.html", addr=_HARDEN_FOREIGN
        )
        bad._raise_download = True
        good = _make_attachment(
            "deck-good", "walkthrough_task-1_20260101000000.html", addr=_HARDEN_TARGET
        )
        wf, atts, _, _ = _make_workflow(resolver=resolver, existing_attachments=[bad, good])

        with _capture_workflow_logs() as captured:
            out = await wf.process_entity(_entity(gid="task-1", provider="GHL"), {})

        # The bad prior did NOT abort the task: the GOOD target prior is still
        # recognized (already_attached), no crash, no re-mint.
        assert out.status == "skipped"
        assert out.reason == "already_attached"
        assert atts.upload_async.await_count == 0
        fail_logs = [
            e for e in captured if e["event"] == "onboarding_walkthrough_prior_download_failed"
        ]
        assert len(fail_logs) == 1
        print(f"[F5] one bad-download prior tolerated -> task={out.status}/{out.reason}, no abort")


# --- W3: ACTIVE-section enumeration over Calendar-Integrations (NO OFFER_CLASSIFIER) ---


def _collectable(items: list[Any]) -> MagicMock:
    """A PageIterator-like mock whose async ``.collect()`` yields ``items``."""
    obj = MagicMock()
    obj.collect = AsyncMock(return_value=list(items))
    return obj


def _collectable_raises(exc: Exception | None = None) -> MagicMock:
    """A PageIterator-like mock whose async ``.collect()`` raises (network/5xx)."""
    obj = MagicMock()
    obj.collect = AsyncMock(side_effect=exc or RuntimeError("section api down"))
    return obj


def _section_obj(name: str, gid: str) -> MagicMock:
    # NOTE: MagicMock(name=...) sets the repr name, NOT a .name attribute -- set both
    # attributes explicitly so resolve_section_gids reads the real section name.
    s = MagicMock()
    s.name = name
    s.gid = gid
    return s


def _task_obj(gid: str, *, completed: bool = False, name: str = "Task") -> MagicMock:
    t = MagicMock()
    t.gid = gid
    t.completed = completed
    t.name = name
    return t


class TestW3Enumeration:
    """W3 re-points enumerate_entities to Calendar-Integrations/ACTIVE by NAME."""

    @staticmethod
    def _wire(
        wf: OnboardingWalkthroughWorkflow,
        *,
        sections: list[MagicMock] | None = None,
        tasks_by_section: dict[str, list[MagicMock]] | None = None,
        project_tasks: list[MagicMock] | None = None,
        sections_raise: bool = False,
        section_fetch_raises: bool = False,
    ) -> None:
        # Shadow the entity-builder so the unit-under-test is the section-targeting
        # logic, not pydantic Business validation (covered elsewhere).
        wf._task_to_entity = lambda task: {"gid": task.gid, "name": getattr(task, "name", None)}  # type: ignore[method-assign]

        if sections_raise:
            wf._asana_client.sections.list_for_project_async = MagicMock(
                return_value=_collectable_raises()
            )
        else:
            wf._asana_client.sections.list_for_project_async = MagicMock(
                return_value=_collectable(sections or [])
            )

        def _list_async(**kwargs: Any) -> MagicMock:
            if "section" in kwargs:
                if section_fetch_raises:
                    return _collectable_raises(RuntimeError("section fetch 5xx"))
                return _collectable((tasks_by_section or {}).get(kwargs["section"], []))
            return _collectable(project_tasks or [])

        wf._asana_client.tasks.list_async = MagicMock(side_effect=_list_async)

    def test_constructor_sets_calendar_project_gid_default(self) -> None:
        wf, _a, _r, _o = _make_workflow()
        assert wf._calendar_integrations_project_gid == constants.CALENDAR_INTEGRATIONS_PROJECT_GID

    async def test_targets_calendar_integrations_active_section(self) -> None:
        wf, _a, _r, _o = _make_workflow()
        active = [_task_obj("t-active-1"), _task_obj("t-active-2")]
        self._wire(
            wf,
            sections=[
                _section_obj("ACTIVE", "sec-active"),
                _section_obj("TEMPLATE", "sec-tmpl"),
                _section_obj("REVIEW", "sec-review"),
            ],
            tasks_by_section={"sec-active": active},
        )

        entities = await wf.enumerate_entities(MagicMock())

        assert {e["gid"] for e in entities} == {"t-active-1", "t-active-2"}
        # Sections resolved against the Calendar-Integrations project (constructor default).
        wf._asana_client.sections.list_for_project_async.assert_called_once_with(
            constants.CALENDAR_INTEGRATIONS_PROJECT_GID
        )
        # ONLY the ACTIVE section was fetched -- not TEMPLATE/REVIEW.
        section_calls = [
            c.kwargs.get("section") for c in wf._asana_client.tasks.list_async.call_args_list
        ]
        assert section_calls == ["sec-active"]
        print(f"[W3] enumerated ACTIVE-only gids={sorted(e['gid'] for e in entities)}")

    async def test_completed_active_tasks_excluded(self) -> None:
        wf, _a, _r, _o = _make_workflow()
        self._wire(
            wf,
            sections=[_section_obj("ACTIVE", "sec-active")],
            tasks_by_section={"sec-active": [_task_obj("live"), _task_obj("done", completed=True)]},
        )
        entities = await wf.enumerate_entities(MagicMock())
        assert {e["gid"] for e in entities} == {"live"}

    async def test_enumeration_uses_overridable_calendar_project_gid(self) -> None:
        wf, _a, _r, _o = _make_workflow()
        wf._calendar_integrations_project_gid = "override-proj-777"  # two-way door
        self._wire(
            wf,
            sections=[_section_obj("ACTIVE", "sec-x")],
            tasks_by_section={"sec-x": [_task_obj("ov-1")]},
        )
        await wf.enumerate_entities(MagicMock())
        wf._asana_client.sections.list_for_project_async.assert_called_once_with(
            "override-proj-777"
        )

    async def test_falls_back_to_onboarding_project_on_section_resolution_failure(self) -> None:
        wf, _a, _r, _o = _make_workflow()
        self._wire(wf, sections_raise=True, project_tasks=[_task_obj("onb-1"), _task_obj("onb-2")])

        entities = await wf.enumerate_entities(MagicMock())

        assert {e["gid"] for e in entities} == {"onb-1", "onb-2"}
        # Preserved N=1 pilot path: the fallback enumerates the ONBOARDING project.
        project_calls = [
            c.kwargs.get("project") for c in wf._asana_client.tasks.list_async.call_args_list
        ]
        assert project_calls == [constants.ONBOARDING_PROJECT_GID]
        print("[W3] section-resolution failure -> Onboarding project-level fallback fired")

    async def test_falls_back_on_empty_active_resolution(self) -> None:
        wf, _a, _r, _o = _make_workflow()
        # Sections exist but NONE is named ACTIVE -> resolve_section_gids returns {} -> fallback.
        self._wire(
            wf,
            sections=[_section_obj("TEMPLATE", "s1"), _section_obj("REVIEW", "s2")],
            project_tasks=[_task_obj("onb-9")],
        )
        entities = await wf.enumerate_entities(MagicMock())
        assert {e["gid"] for e in entities} == {"onb-9"}
        project_calls = [
            c.kwargs.get("project") for c in wf._asana_client.tasks.list_async.call_args_list
        ]
        assert project_calls == [constants.ONBOARDING_PROJECT_GID]

    async def test_falls_back_on_partial_section_fetch_failure(self) -> None:
        wf, _a, _r, _o = _make_workflow()
        # ACTIVE resolves, but the section task-fetch raises -> no partial sweep, full fallback.
        self._wire(
            wf,
            sections=[_section_obj("ACTIVE", "sec-active")],
            section_fetch_raises=True,
            project_tasks=[_task_obj("onb-fallback")],
        )
        entities = await wf.enumerate_entities(MagicMock())
        assert {e["gid"] for e in entities} == {"onb-fallback"}

    def test_enumeration_path_has_no_offer_classifier(self) -> None:
        """Static guard (G-DENOM): the workflow never IMPORTS or USES the Offers
        OFFER_CLASSIFIER nor the active_offer_enumeration module that carries it.

        Parsed via AST so the guard bites on real imports/usage and is NOT tripped
        by the explanatory prose that documents *why* the divergence exists.
        """
        import ast as _ast
        import inspect as _inspect

        import autom8_asana.automation.workflows.onboarding_walkthrough.workflow as wf_mod

        tree = _ast.parse(_inspect.getsource(wf_mod))

        imported: set[str] = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ImportFrom):
                imported.add(node.module or "")
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, _ast.Import):
                imported.update(alias.name for alias in node.names)
        names_used = {n.id for n in _ast.walk(tree) if isinstance(n, _ast.Name)}

        assert "OFFER_CLASSIFIER" not in imported, "must not import OFFER_CLASSIFIER"
        assert "OFFER_CLASSIFIER" not in names_used, "must not reference OFFER_CLASSIFIER in code"
        assert not any("active_offer_enumeration" in m for m in imported), (
            "enumeration must reuse section_resolution, NOT the Offers active_offer_enumeration"
        )


# =====================================================================
# C-BN1-05 (SEC-N2 §3) -- the affirmative per-task SUCCESS audit record
# =====================================================================
# The batch replacement for the retired N=1 human attestation line: on the SUCCESS
# path (W1 passed AND T7 passed AND the upload succeeded) the workflow emits ONE
# structured record binding the automation identity, the task, the MASKED tenant
# company_id (Source B) + MASKED gated routing address (Source A -- a routing-secret;
# never logged in full), the W1 anchor-basis TIER (read from the GFR provenance), and
# a timestamp. Two-sided: present on success, ABSENT on every skip/fail path.

_AUDIT_EVENT = "onboarding_walkthrough_upload_succeeded"


class TestCBN105SuccessAuditRecord:
    """C-BN1-05: the per-task success audit record (presence + masking + tier; absence)."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        spy = AsyncMock(return_value=_deck_bytes(_W1_RESOLVED_A))
        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", spy)
        return spy

    async def test_success_emits_audit_record_with_masked_fields_and_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GREEN: a clean attach emits the structured audit record. The default
        # (no-verifier) anchor resolves the CACHE tier, so anchor_tier == "CACHE".
        from datetime import datetime

        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        with _capture_workflow_logs() as captured:
            out = await wf.process_entity(_entity(gid="task-audit", provider="GHL"), {})

        assert out.status == "succeeded"
        atts.upload_async.assert_awaited_once()
        record = next(e for e in captured if e["event"] == _AUDIT_EVENT)

        # Bound identity + task.
        assert record["workflow_id"] == "onboarding-walkthrough"
        assert record["task_gid"] == "task-audit"
        # MASKED tenant company_id (Source B) -- the 8-hex breadcrumb, never the full guid.
        assert record["company_id"] == identity_guard.mask_guid(_W1_GUID_A)
        # MASKED gated routing address (Source A) -- domain kept, secret guid masked.
        assert record["gated_address"] == _mask_addr(_W1_RESOLVED_A)
        # W1 anchor-basis TIER read from the GFR provenance.
        assert record["anchor_tier"] == "CACHE"
        # A parseable timestamp.
        assert isinstance(record["attached_at"], str)
        datetime.fromisoformat(record["attached_at"])  # raises if not ISO-8601
        # The existing operational fields survive the augmentation.
        assert record["filename"].startswith("walkthrough_task-audit_")
        assert isinstance(record["size_bytes"], int)

        # PII discipline (G-PROVE): the FULL guid and FULL routing address NEVER appear
        # in any value of the record (mask-only; the address is a routing secret).
        for value in record.values():
            if isinstance(value, str):
                assert _W1_GUID_A not in value, f"full guid leaked in {value!r}"
                assert _W1_RESOLVED_A not in value, f"full routing address leaked in {value!r}"
        print(
            f"[C-BN1-05] audit record: workflow_id={record['workflow_id']!r} "
            f"company_id={record['company_id']!r} gated_address={record['gated_address']!r} "
            f"anchor_tier={record['anchor_tier']!r} attached_at={record['attached_at']!r}"
        )

    async def test_audit_record_reflects_verified_anchor_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The tier field is read from the anchor result: an anchor that resolved at the
        # VERIFIED tier yields anchor_tier == "VERIFIED" in the record (the BTM-3
        # real-anchor arms prove the REAL anchor flips the tier; this proves the
        # success-record mapping carries it for BOTH tier values).
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver,
            company_id_anchor=_stub_anchor(_W1_GUID_A, tier=TruthTier.VERIFIED),
        )
        with _capture_workflow_logs() as captured:
            out = await wf.process_entity(_entity(gid="task-v", provider="GHL"), {})
        assert out.status == "succeeded"
        record = next(e for e in captured if e["event"] == _AUDIT_EVENT)
        assert record["anchor_tier"] == "VERIFIED"
        print(f"[C-BN1-05] anchor_tier reflects VERIFIED: {record['anchor_tier']!r}")

    async def test_skip_path_emits_no_audit_record(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A W1 cross-tenant mismatch SKIPs -> NO success audit record (ABSENT on skip).
        freeze_spy = self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver, company_id_anchor=_stub_anchor(_W1_GUID_B)
        )
        with _capture_workflow_logs() as captured:
            out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "guid_anchor_mismatch"
        atts.upload_async.assert_not_called()
        freeze_spy.assert_not_awaited()
        assert not [e for e in captured if e["event"] == _AUDIT_EVENT], (
            "no success audit record may be emitted on a skip"
        )

    async def test_upload_failure_emits_no_audit_record(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # An upload failure FAILs (preserving the prior) -> NO success audit record
        # (ABSENT on fail; the record sits AFTER the upload in the try).
        self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        atts.upload_async = AsyncMock(side_effect=RuntimeError("network down"))
        with _capture_workflow_logs() as captured:
            out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "upload_failed"
        assert not [e for e in captured if e["event"] == _AUDIT_EVENT], (
            "no success audit record may be emitted on a failed upload"
        )


# =====================================================================
# BTM-3 (SEC-N3 F-N3-002) -- VERIFIED-tier anchor via the wired ByGuidVerifier
# =====================================================================
# With the W4 handler wiring a ByGuidVerifier, the W1 anchor runs TruthTier.VERIFIED
# (tier-2 by-GUID round-trip), not the blind CACHE tier. These arms drive the REAL
# identity_guard.anchor_company_id + REAL GFR engine over a mocked substrate (the
# gid-exact Business row + the by-guid verifier), proving: (a) the tier the REAL anchor
# resolves at flips to VERIFIED when a verifier is wired (and CACHE when not -- the
# two-sided twin), read from the GFR provenance via an anchor spy; and (b) a poisoned
# cache company_id that does NOT round-trip by-GUID fails CLOSED to a skip (zero upload,
# zero freeze). The tier -> audit-record mapping itself is proven separately at
# TestCBN105SuccessAuditRecord (capture is reliable there -- no real-engine logging that
# reconfigures structlog mid-capture).

_BTM3_BIZ = "biz-verified-gid"
_BTM3_HYDRATE = "autom8_asana.resolution.gfr.entry.hydrate_from_gid_async"


def _spy_real_anchor() -> tuple[Any, list[TruthTier]]:
    """The REAL GFR anchor wrapped to record the ``TruthTier`` it resolves at.

    Reads the ground-truth tier off the REAL anchor's ``AnchorResult`` (which reads it
    off the GFR provenance) -- robust to the structlog-capture/real-engine interaction,
    and a direct proof that the wiring flips the tier the anchor actually resolves at.
    """
    tiers: list[TruthTier] = []

    async def _spy(*, task_gid: str, client: Any, query_engine: Any, verifier: Any) -> AnchorResult:
        result = await identity_guard.anchor_company_id(
            task_gid=task_gid, client=client, query_engine=query_engine, verifier=verifier
        )
        tiers.append(result.tier)
        return result

    return _spy, tiers


def _real_anchor_verified_workflow(
    *, verifier: Any, cache_company_id: str, anchor: Any = None
) -> tuple[OnboardingWalkthroughWorkflow, MagicMock]:
    """Wire the REAL W1 anchor + REAL GFR engine over a mocked gid-exact substrate.

    ``cache_company_id`` is the company_id the gid-exact Business cache row serves
    (Source B tier-1); ``verifier`` is the tier-2 by-GUID port. The SDK resolver
    returns A's canonical address (Source A). ``anchor`` overrides the anchor (e.g. a
    tier-recording spy); it defaults to the REAL GFR-backed ``anchor_company_id``. The
    producer freeze + hydrate are patched by the caller.
    """
    resolver = _make_resolver(address=_W1_RESOLVED_A)
    query_engine = AsyncMock()
    query_engine.execute_rows = AsyncMock(
        return_value=make_rows_response(rows=[{"gid": _BTM3_BIZ, "company_id": cache_company_id}])
    )
    wf, atts, _, _ = _make_workflow(
        resolver=resolver,
        query_engine=query_engine,
        company_id_anchor=anchor if anchor is not None else identity_guard.anchor_company_id,
        verifier=verifier,
    )
    return wf, atts


class TestBTM3VerifiedTierAnchor:
    """BTM-3: a wired ByGuidVerifier flips the W1 anchor to VERIFIED and narrows poison."""

    def _patch_freeze(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        spy = AsyncMock(return_value=_deck_bytes(_W1_RESOLVED_A))
        monkeypatch.setattr(producer_module, "freeze_walkthrough_deck", spy)
        return spy

    async def test_verifier_wired_real_anchor_resolves_verified_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # GREEN: the cache company_id round-trips by-GUID (verifier has the record) ->
        # the REAL anchor resolves at the VERIFIED tier (read off the GFR provenance).
        self._patch_freeze(monkeypatch)
        anchor, tiers = _spy_real_anchor()
        verifier = FakeByGuidVerifier(records={_W1_GUID_A: make_record(_W1_GUID_A)})
        wf, atts = _real_anchor_verified_workflow(
            verifier=verifier, cache_company_id=_W1_GUID_A, anchor=anchor
        )
        with patch(
            _BTM3_HYDRATE,
            AsyncMock(
                return_value=make_hydration_result(
                    business_gid=_BTM3_BIZ, entry_type=EntityType.OFFER, path_len=3
                )
            ),
        ):
            out = await wf.process_entity(_entity(gid="task-v", provider="GHL"), {})
        assert out.status == "succeeded"
        atts.upload_async.assert_awaited_once()
        # The REAL anchor resolved at the VERIFIED tier (ground-truth GFR provenance).
        assert tiers == [TruthTier.VERIFIED]
        # The by-GUID port WAS consulted (INVARIANT I7), not the office_phone join.
        assert verifier.calls == [_W1_GUID_A]
        print(f"[BTM-3] verifier wired -> real anchor tier={tiers[0].name!r} (VERIFIED), uploaded")

    async def test_no_verifier_real_anchor_resolves_cache_tier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # CACHE twin (two-sided): with NO verifier the REAL engine stamps CACHE
        # provenance; the anchor resolves at CACHE. Proves the tier readout is the
        # ground-truth GFR provenance, not an inference -- the teeth bite per-tier.
        self._patch_freeze(monkeypatch)
        anchor, tiers = _spy_real_anchor()
        wf, atts = _real_anchor_verified_workflow(
            verifier=None, cache_company_id=_W1_GUID_A, anchor=anchor
        )
        with patch(
            _BTM3_HYDRATE,
            AsyncMock(
                return_value=make_hydration_result(
                    business_gid=_BTM3_BIZ, entry_type=EntityType.OFFER, path_len=3
                )
            ),
        ):
            out = await wf.process_entity(_entity(gid="task-v", provider="GHL"), {})
        assert out.status == "succeeded"
        assert tiers == [TruthTier.CACHE]
        print(f"[BTM-3] no verifier -> real anchor tier={tiers[0].name!r} (CACHE), uploaded")

    async def test_poisoned_cache_skips_under_verified_no_upload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # RED: the gid-exact cache row carries a POISON company_id that does NOT
        # round-trip by-GUID (the verifier's record set omits it) -> verify fails ->
        # UnresolvedError -> skipped(anchor_unresolved), ZERO upload, ZERO freeze. The
        # VERIFIED tier narrows cache poisoning that CACHE would trust verbatim.
        freeze_spy = self._patch_freeze(monkeypatch)
        poison = "deadbeef-0000-4000-8000-000000000000"
        verifier = FakeByGuidVerifier(records={})  # every by-guid lookup MISSES
        wf, atts = _real_anchor_verified_workflow(verifier=verifier, cache_company_id=poison)
        with patch(
            _BTM3_HYDRATE,
            AsyncMock(
                return_value=make_hydration_result(
                    business_gid=_BTM3_BIZ, entry_type=EntityType.OFFER, path_len=3
                )
            ),
        ):
            out = await wf.process_entity(_entity(gid="task-v", provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "anchor_unresolved"
        atts.upload_async.assert_not_called()
        freeze_spy.assert_not_awaited()
        # The by-GUID port was consulted on the poison and missed -> fail-closed.
        assert verifier.calls == [poison]
        print(f"[BTM-3] poisoned cache under VERIFIED -> {out.reason!r}, uploads=0 (narrowed)")


# --- AC-2: autom8_data fault-naming taxonomy (resolve + anchor except-widening) ---


class TestFaultNamingTaxonomy:
    """AC-2: known autom8_data faults in the resolve/anchor legs become NAMED
    ``failed`` reasons (not the generic terminal ``unexpected_error``); the auth
    family deliberately falls through to the SHARED runner's now-logged terminal net
    where its true class name self-identifies R2. GFR-family dispositions are
    unchanged (regression guard on ladder ordering).

    Every named leg returns a per-entity ``failed`` BEFORE FREEZE (no upload, no
    producer subprocess), preserving INV-1 (customer-clean) and INV-3 (isolation).
    """

    # -- Resolve leg (B, workflow.py:440) --

    async def test_resolve_valueerror_named_failed(self) -> None:
        # AC-2a: ``format_routing_address`` raises ``ValueError`` on a non-canonical
        # STORED guid (R1 candidate). It must become a NAMED failed reason, NOT escape
        # to the terminal swallow (which would report error_type='unexpected_error').
        resolver = _make_resolver(raises=ValueError("non-canonical stored guid"))
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "resolve_invalid_input"  # NAMED, not unexpected_error
        assert out.error.recoverable is False
        atts.upload_async.assert_not_called()

    async def test_resolve_malformed_named_failed(self) -> None:
        # AC-2a sibling: a malformed / non-200 data-service body raises the
        # ``DataServiceError`` base -> resolve_data_error (recoverable).
        from autom8y_core.errors import DataServiceError

        resolver = _make_resolver(raises=DataServiceError("malformed body"))
        wf, atts, _, _ = _make_workflow(resolver=resolver)
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "resolve_data_error"
        assert out.error.recoverable is True
        atts.upload_async.assert_not_called()

    # -- Anchor leg (C, workflow.py:490) --

    async def test_anchor_unavailable_named_failed(self) -> None:
        # AC-2b: a transient data-service fault in the by-GUID anchor becomes a NAMED
        # failed reason (mirrors the resolve leg) -- alarmed, never a benign skip nor
        # the terminal swallow.
        from autom8y_core.errors import DataServiceUnavailableError

        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver,
            company_id_anchor=_raising_anchor(
                DataServiceUnavailableError(method="get_business_by_guid")
            ),
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "anchor_unavailable"
        assert out.error.recoverable is True
        atts.upload_async.assert_not_called()

    async def test_anchor_invalid_named_failed(self) -> None:
        # AC-2b sibling: a 4xx data-shape fault (INVALID_BUSINESS_GUID_FORMAT) raises
        # ``DataServiceValidationError`` -> NAMED anchor_invalid (non-recoverable, R1).
        from autom8y_core.errors import DataServiceValidationError

        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver,
            company_id_anchor=_raising_anchor(
                DataServiceValidationError(method="get_business_by_guid", status_code=400)
            ),
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "failed"
        assert out.error is not None
        assert out.error.error_type == "anchor_invalid"
        assert out.error.recoverable is False
        atts.upload_async.assert_not_called()

    async def test_anchor_auth_reaches_terminal_named_R2(self) -> None:
        # AC-2b teeth: the AUTH family (InvalidServiceKeyError) is NOT a DataServiceError
        # (siblings under TransportError), so it is deliberately NOT caught by the data
        # legs -> it falls through to the SHARED runner's terminal net, which now LOGS
        # it. Its true class name self-identifies R2. Proven END-TO-END via
        # ``execute_async`` so the terminal net is genuinely exercised.
        from autom8y_core.errors import InvalidServiceKeyError

        from autom8_asana.automation.workflows import bridge_base as _bb_mod

        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver,
            company_id_anchor=_raising_anchor(InvalidServiceKeyError()),
        )
        # Clear the shared runner's logger bind cache so capture intercepts the terminal
        # net line (bridge_base is a DIFFERENT module logger than the workflow).
        proxy = _bb_mod.logger
        if "bind" in getattr(proxy, "__dict__", {}):
            del proxy.__dict__["bind"]
        with structlog.testing.capture_logs() as captured:
            result = await wf.execute_async([_entity(provider="GHL")], {})
        assert result.failed == 1
        terminal = [e for e in captured if e["event"] == "bridge_entity_failed"]
        assert len(terminal) == 1
        assert terminal[0]["error_type"] == "InvalidServiceKeyError"  # R2 self-identifies
        atts.upload_async.assert_not_called()

    def test_auth_family_not_reparented_under_dataservice(self) -> None:
        # F4 forward-watch (cheap invariant): the AUTH family (TokenAcquisitionError and
        # its InvalidServiceKeyError subclass) must stay DISJOINT from the DATA family
        # (DataServiceError). If a future autom8y_core release reparents auth under the
        # data hierarchy, the workflow's ``except DataServiceError`` legs would silently
        # reclassify a 401 as a recoverable R1-data fault -- masking the R2 auth signal
        # the terminal net keys off. Pin the invariant so a reparent fails LOUDLY here in
        # CI instead of silently in production.
        from autom8y_core.errors import (
            DataServiceError,
            InvalidServiceKeyError,
            TokenAcquisitionError,
        )

        assert not issubclass(InvalidServiceKeyError, DataServiceError)
        assert not issubclass(TokenAcquisitionError, DataServiceError)

    # -- Regression guard (AC-2c): GFR-family dispositions unchanged --

    async def test_gfr_family_dispositions_unchanged(self) -> None:
        # AC-2c: widening the DataService family BELOW the GFR family must not perturb
        # the GFR ladder ordering (subclasses-before-base). Each GFR-family raise keeps
        # its EXISTING skip disposition; a resolved-but-foreign anchor still skips
        # guid_anchor_mismatch.
        from autom8_asana.resolution.gfr.errors import (
            AmbiguousCardinalityError,
            GuardViolationError,
            UnresolvedError,
        )

        raising_cases = [
            (GuardViolationError("identity-path drift"), "guard_violation"),
            (AmbiguousCardinalityError(row_count=2), "ambiguous_anchor"),
            (
                UnresolvedError(fields=["company_id"], reason="no-identity-path"),
                "anchor_unresolved",
            ),
        ]
        for exc, expected_reason in raising_cases:
            resolver = _make_resolver(address=_W1_RESOLVED_A)
            wf, atts, _, _ = _make_workflow(
                resolver=resolver, company_id_anchor=_raising_anchor(exc)
            )
            out = await wf.process_entity(_entity(provider="GHL"), {})
            assert out.status == "skipped", f"{type(exc).__name__} must skip, got {out.status}"
            assert out.reason == expected_reason
            atts.upload_async.assert_not_called()

        # A resolved-but-foreign anchor (guid mismatch) still skips guid_anchor_mismatch.
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver, company_id_anchor=_stub_anchor(_W1_GUID_B)
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "guid_anchor_mismatch"
        atts.upload_async.assert_not_called()
