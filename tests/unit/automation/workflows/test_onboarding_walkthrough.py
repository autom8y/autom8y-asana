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
