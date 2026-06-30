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
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TenantBindingError,
    assert_exclusive_tenant_binding,
    harvest_routing_addresses,
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

    async def _anchor(*, task_gid: str, client: Any, query_engine: Any, verifier: Any) -> str:
        if not isinstance(address, str):
            # No resolvable address (the resolver returns None) -> this path is not
            # reached (the workflow skips at address_unresolved before W1); return a
            # sentinel that would mismatch if it ever were.
            return "no-address"
        return address.split("@", 1)[0].lower()

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
        addr = None
        for att in store:
            if att.gid == attachment_gid:
                addr = att._addr
                break
        payload = _deck_bytes(addr) if addr else b"<html>no routing address</html>"
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


def _stub_anchor(company_id: str) -> AsyncMock:
    """A Source-B anchor stub that returns a FIXED company_id (independent of A)."""

    async def _anchor(*, task_gid: str, client: Any, query_engine: Any, verifier: Any) -> str:
        return company_id

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

    async def test_red_guard_violation_skips_no_upload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A GuardViolationError (identity-path purity drift -- a hard structural
        # signal) is ALSO caught by the GfrError base -> fail-closed skip, no upload.
        from autom8_asana.resolution.gfr.errors import GuardViolationError

        freeze_spy = self._patch_freeze(monkeypatch)
        resolver = _make_resolver(address=_W1_RESOLVED_A)
        wf, atts, _, _ = _make_workflow(
            resolver=resolver,
            company_id_anchor=_raising_anchor(GuardViolationError("identity-path drift")),
        )
        out = await wf.process_entity(_entity(provider="GHL"), {})
        assert out.status == "skipped"
        assert out.reason == "anchor_unresolved"
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
