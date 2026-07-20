"""Sprint-F GFR tenant-identity round-trip — the PROVEN-candidate realization gate.

This lifts the unit-altitude anti-vacuity gate (``tests/unit/resolution/gfr/
test_collision_closure.py``) to INTEGRATION altitude by carrying the GFR-resolved
``company_id`` through the mint convention and into the REAL inbound
``resolve_office_stage`` (email-booking-intake), proving the realization predicate:

    an Offer gid resolves ``company_id`` (== ``chiropractors.guid``); the minted
    ``{guid}@appointments.contenteapp.com`` round-trips through inbound
    ``resolve_office_stage`` to the CORRECT tenant — proven by a live positive on a
    positively-selected REAL tenant with an a-priori-known guid AND a
    deliberately-broken cross-tenant fixture (tenant B positively seeded as the
    ``keep='first'`` dedup-WINNER) firing RED, NEVER by a green suite alone.

Design: ``.ledge/specs/gfr-sprintF-test-design.md`` (option (a) — reach the REAL
inbound stage via a test-only existence-guarded ``sys.path`` insert to the
co-located EBI ``src/``). This is the ONLY option that exercises the real inbound
code byte-for-byte at integration altitude; a vendored contract-mirror (option b)
would pass green on real-code drift and is the coverage theater the predicate
forbids.

BOUNDARY (PROVEN-candidate, this rite's deliverable):
  * ``data_read_client`` is an ``AsyncMock`` bound to the REAL canary
    ``BusinessRecord`` values, exactly per EBI's own ``test_resolve_office.py``
    pattern, so the ``:105`` by-guid HIT path is taken (NOT ``None`` -> fallback).
  * GFR runs against mocked substrate (``hydrate_from_gid_async`` +
    ``query_engine.execute_rows`` patched as in ``test_collision_closure``) but the
    GFR engine, planner, and the engine-owned guard (``assert_rows_tenant_identity``,
    GAP-1) run UNMOCKED as the system under test.
  * The mint is stubbed at the boundary: ``f"{guid}@appointments.contenteapp.com"``
    (the producer is UNBUILT — telos NOTE-4 / R-6; GFR supplies gid -> company_id
    -> guid only).

The user-gated live-against-prod run (NOT this test, NEVER faked here) REPLACES, on
a positively-selected REAL tenant: a real ``DataServiceClient`` (not ``AsyncMock``)
hitting the live ``get_business_by_guid_async`` against the real chiropractors
table, and real tenant credentials so the asana side reads ``company_id`` from the
live multi-tenant Business frame. That live run is the INPUT to PROVEN-attested; the
attestation itself is the rite-disjoint review rite's (CERT-3 close), never the
author's, never a green suite alone. See design §6.

Build ON TOP: the frozen ``execute_join`` and the GFR engine are imported and CALLED
(read-only), never edited; the scar tests are untouched.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

# --------------------------------------------------------------------------- #
# TEST HOME fork mechanism (design §1 option (a) / import_strategy):
# existence-guarded test-only sys.path insert to the co-located EBI src/. If the
# EBI checkout is absent we pytest.skip at COLLECTION — never an import error,
# never a false red (CI-in-asana-alone stays green-skip). When sprint-E lands GFR
# into autom8y-core and EBI takes a real dependency edge, delete this insert and
# the import becomes a plain ``from email_booking_intake...``; the test body
# (positive/negative/defense asserts) is unchanged by that migration.
# The coupling is NAMED, BOUNDED, and SURFACED (harness-sovereignty), not silent.
# --------------------------------------------------------------------------- #
_ASANA_REPO_ROOT = Path(__file__).resolve().parents[2]
_EBI_SRC = os.environ.get(
    "GFR_EBI_SRC",
    str(_ASANA_REPO_ROOT.parent / "autom8y" / "services" / "email-booking-intake" / "src"),
)

if not Path(_EBI_SRC).is_dir():
    pytest.skip(
        f"EBI src not co-located at {_EBI_SRC!r}; cross-repo round-trip skipped "
        "(see sprint-E: GFR -> autom8y-core; set GFR_EBI_SRC for non-default checkouts)",
        allow_module_level=True,
    )

if _EBI_SRC not in sys.path:
    sys.path.insert(0, _EBI_SRC)

# REAL inbound code (option a — byte-for-byte, not a mirror; design D5).
from email_booking_intake.pipeline.context import PipelineContext  # noqa: E402
from email_booking_intake.pipeline.result import StageStatus  # noqa: E402
from email_booking_intake.pipeline.stages.resolve_office import (  # noqa: E402
    _DEFAULT_OVERRIDES,
    resolve_office_stage,
)

# GFR engine (system under test on the asana half) + the FROZEN execute_join,
# consumed read-only as a client to re-introduce the v1 trap (design D6).
from autom8_asana.core.types import EntityType  # noqa: E402
from autom8_asana.query.join import execute_join  # noqa: E402  frozen — read-only client
from autom8_asana.query.models import Comparison, Op, RowsRequest  # noqa: E402
from autom8_asana.resolution.gfr.engine import resolve_async  # noqa: E402
from autom8_asana.resolution.gfr.errors import GuardViolationError  # noqa: E402
from tests.unit.resolution.gfr.conftest import (  # noqa: E402
    make_hydration_result,
    make_rows_response,
)

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]

_HYDRATE = "autom8_asana.resolution.gfr.entry.hydrate_from_gid_async"
_MINT_DOMAIN = "@appointments.contenteapp.com"

# --------------------------------------------------------------------------- #
# Positively-selected REAL tenant (design §3).
# G_correct is the To: guid of prod-canary-real-2026-04-13.eml — an a-priori-known
# guid for a real canary tenant. It is NOT the U+200B override key (33e3a930-...),
# so the _DEFAULT_OVERRIDES remap does NOT fire (defense D1); it is a clean UUID.
# --------------------------------------------------------------------------- #
G_CORRECT = "b167331c-536f-4996-9b2d-2f696f35f556"  # canary real-tenant guid
GID_OFFER = "canary_offer_gid"  # a positively-selected Offer gid in A's tree
GID_BIZ = "canary_business_gid"  # A's Business gid (the parent-chain anchor)
CANARY_PHONE = "+15557654321"
CANARY_NAME = "Canary Chiropractic"

# Cross-tenant negative (design §4): tenant B positively seeded as keep='first'
# dedup-WINNER for A's shared phone. G_A is the canary tenant; G_B is a DIFFERENT
# tenant's company_id; the SHARED_PHONE is the collision surface.
G_A = G_CORRECT
G_B = "ffffffff-eeee-4ddd-8ccc-bbbbaaaa0000"  # a DIFFERENT tenant — must NEVER win
SHARED_PHONE = "+15551112222"
GID_BIZ_B = "wrong_tenant_business_gid"


@pytest.fixture
def mock_client() -> MagicMock:
    """Local AsanaClient mock with an async task getter.

    ``tests/unit/resolution/gfr/conftest.py`` defines an identical fixture, but
    conftest fixtures are tree-scoped and not visible to ``tests/integration/``.
    GFR's ``resolve_async`` only threads ``client`` to the entry fetch (which we
    patch via ``_HYDRATE``) and to ``execute_rows`` (patched per-test), so a minimal
    local mock is sufficient and keeps the integration module self-contained.
    """
    client = MagicMock()
    client.tasks = MagicMock()
    client.tasks.get_async = AsyncMock()
    return client


def _mint(guid: str) -> str:
    """Stub the mint at the boundary (design §2): the convention formatted directly.

    The producer is UNBUILT (telos NOTE-4 / R-6); GFR supplies gid -> guid only.
    """
    return f"{guid}{_MINT_DOMAIN}"


def _canary_business_record() -> AsyncMock:
    """A real-canary ``BusinessRecord``-shaped mock (EBI test_resolve_office.py:39-42).

    Carries ``.office_phone`` / ``.business_name`` so the ``:105`` by-guid HIT path
    is taken (NOT ``None`` -> ``:121`` fallback). These are DISPLAY fields — the
    round-trip identity assertion targets ``ctx.chiropractor_guid`` only (D4).
    """
    record = AsyncMock()
    record.office_phone = CANARY_PHONE
    record.business_name = CANARY_NAME
    return record


def _canary_data_read_client() -> AsyncMock:
    """The inbound ``data_read_client`` mock bound to the canary record.

    Both ``get_business_by_guid_async`` (the :105 PRIMARY identity HIT) and
    ``get_business_by_phone_async`` (the :141 display lookup) return the real-shaped
    canary record so the stage walks the by-guid HIT path end to end.
    """
    client = AsyncMock()
    client.get_business_by_guid_async.return_value = _canary_business_record()
    client.get_business_by_phone_async.return_value = _canary_business_record()
    return client


def _make_ctx(to: str) -> PipelineContext:
    """Build a minimal PipelineContext with the minted address on ``ctx.to``."""
    ctx = PipelineContext(raw_body=b"", headers={})
    ctx.to = to
    return ctx


def _single_tenant_business_frame() -> pl.DataFrame:
    """The gid-exact Business frame for the canary tenant (no collision)."""
    return pl.DataFrame([{"gid": GID_BIZ, "office_phone": CANARY_PHONE, "company_id": G_CORRECT}])


def _collision_business_frame() -> pl.DataFrame:
    """Multi-tenant Business frame with B ORDERED BEFORE A for the shared phone.

    Row order is load-bearing (design §4): ``unique(subset=['office_phone'],
    keep='first')`` (``query/join.py:157``) keeps the FIRST occurrence, so placing
    B's row first makes B the dedup-WINNER for the shared phone key. This is the
    positive seeding that makes the broken phone-join half non-vacuous.
    """
    return pl.DataFrame(
        [
            {"gid": GID_BIZ_B, "office_phone": SHARED_PHONE, "company_id": G_B},  # FIRST
            {"gid": GID_BIZ, "office_phone": SHARED_PHONE, "company_id": G_A},  # second
        ]
    )


def _offer_a_primary_frame() -> pl.DataFrame:
    """A's offer row carrying the shared phone — the broken-path join primary."""
    return pl.DataFrame([{"gid": GID_OFFER, "office_phone": SHARED_PHONE}])


async def _gfr_resolve_company_id(
    *,
    offer_gid: str,
    business_gid: str,
    business_frame: pl.DataFrame,
    mock_client,
) -> str:
    """Run the REAL GFR engine (unmocked) against a mocked substrate; return company_id.

    Mirrors ``test_collision_closure.py``: ``hydrate_from_gid_async`` is patched to
    anchor the Offer to ``business_gid`` (offer path_len=3); ``execute_rows`` is
    patched to serve the gid-exact Business row by filtering ``business_frame`` on
    the ``where`` predicate's gid value (exactly what the frozen substrate's
    ``df.filter`` does). The engine, planner, and engine-owned guard run UNMOCKED.
    """

    async def _gid_exact_execute(entity_type, project_gid, client, request):
        assert isinstance(request.where, Comparison)
        target_gid = request.where.value
        rows = business_frame.filter(pl.col("gid") == target_gid).to_dicts()
        return make_rows_response(rows=rows)

    query_engine = AsyncMock()
    query_engine.execute_rows = _gid_exact_execute

    anchor = make_hydration_result(
        business_gid=business_gid, entry_type=EntityType.OFFER, path_len=3
    )
    with patch(_HYDRATE, AsyncMock(return_value=anchor)):
        result = await resolve_async(
            offer_gid,
            ["company_id"],
            client=mock_client,
            query_engine=query_engine,
        )
    return result.rows[0]["company_id"].value


# =========================================================================== #
# 1. POSITIVE round-trip — real tenant, a-priori-known G_correct, by-guid HIT.
# =========================================================================== #
class TestPositiveRoundTrip:
    """GFR resolves the canary Offer to G_correct; the minted address round-trips
    through the REAL resolve_office_stage to ctx.chiropractor_guid == G_correct."""

    @pytest.mark.asyncio
    async def test_offer_gid_round_trips_to_correct_tenant(self, mock_client) -> None:
        # --- GFR half: Offer gid -> company_id == G_correct (engine + guard unmocked).
        company_id = await _gfr_resolve_company_id(
            offer_gid=GID_OFFER,
            business_gid=GID_BIZ,
            business_frame=_single_tenant_business_frame(),
            mock_client=mock_client,
        )
        assert company_id == G_CORRECT

        # --- Mint half: the convention formatted directly (producer unbuilt).
        minted = _mint(company_id)
        assert minted == f"{G_CORRECT}{_MINT_DOMAIN}"

        # --- Inbound half: the REAL resolve_office_stage with empty mapping + no
        # extra overrides (D2/D3). The canary client returns the real-shaped record
        # so the :105 by-guid HIT path is taken, NOT the :121 fallback.
        client = _canary_data_read_client()
        stage = resolve_office_stage(client, guid_phone_mapping={}, guid_overrides={})
        ctx = _make_ctx(minted)
        result = await stage(ctx)

        # --- ROUND-TRIP ASSERT (G-DENOM): assert on tenant identity, NEVER display.
        assert result.status == StageStatus.COMPLETED
        assert ctx.chiropractor_guid == G_CORRECT

        # --- HIT-path proof (D3): the :105 by-guid HIT was taken with G_correct,
        # NOT the :121 guid_phone_mapping fallback.
        client.get_business_by_guid_async.assert_awaited_once_with(G_CORRECT)


# =========================================================================== #
# 2. NEGATIVE cross-tenant — B seeded as keep='first' winner; DELTA fires RED.
# =========================================================================== #
class TestNegativeCrossTenant:
    """B positively seeded as the dedup-WINNER for A's gid. The broken phone-join
    returns G_B (RED); the gid-exact GFR path returns G_A; the round-trip mints A's
    address and lands A — NEVER B. A green suite WITHOUT this RED half is rejected."""

    def test_b_is_positively_seeded_as_dedup_winner(self) -> None:
        """INSPECT the seeded dedup ordering (not the assertion text) — the
        non-vacuity construction (design §4): B precedes A for the shared phone, so
        B wins the keep='first' dedup the frozen execute_join uses (join.py:157)."""
        frame = _collision_business_frame()
        phone_rows = frame.filter(pl.col("office_phone") == SHARED_PHONE)
        # Both tenants share the phone — the collision is real.
        assert phone_rows.height == 2
        # B is ordered FIRST — positively the keep='first' survivor.
        assert phone_rows.row(0, named=True)["gid"] == GID_BIZ_B
        # Exercise the SAME dedup the frozen execute_join uses, and confirm B wins.
        deduped = frame.unique(subset=["office_phone"], keep="first")
        survivor = deduped.filter(pl.col("office_phone") == SHARED_PHONE).row(0, named=True)
        assert survivor["gid"] == GID_BIZ_B
        assert survivor["company_id"] == G_B  # the WRONG tenant survives the join

    @pytest.mark.asyncio
    async def test_delta_broken_returns_b_v2_returns_a_then_round_trips_to_a(
        self, mock_client
    ) -> None:
        """The DELTA hinge: same fixture, broken (real frozen execute_join) == G_B,
        v2 (gid-exact GFR) == G_A; then mint G_A and round-trip through the real
        stage to ctx.chiropractor_guid == G_A, never G_B."""
        # --- DELTA broken half (RED): the REAL frozen execute_join keyed on the
        # shared office_phone enriches A's offer with B's company_id (the wrong
        # tenant survives keep='first'). Read-only call of the frozen file.
        broken = execute_join(
            primary_df=_offer_a_primary_frame(),
            target_df=_collision_business_frame(),
            join_key="office_phone",
            select_columns=["company_id"],
            target_entity_type="business",
        )
        broken_company_id = broken.df.row(0, named=True)["business_company_id"]
        assert broken_company_id == G_B  # RED — the wrong tenant survives

        # --- DELTA v2 half (GREEN): gid-exact GFR resolves A to A's own company_id.
        v2_company_id = await _gfr_resolve_company_id(
            offer_gid=GID_OFFER,
            business_gid=GID_BIZ,
            business_frame=_collision_business_frame(),
            mock_client=mock_client,
        )
        assert v2_company_id == G_A

        # --- The non-vacuity hinge: broken == G_B, v2 == G_A, and they DIFFER.
        assert G_A != G_B
        assert broken_company_id != v2_company_id
        assert broken_company_id == G_B
        assert v2_company_id == G_A

        # --- Round-trip continuation: mint A's address (carries G_A because GFR
        # resolved A correctly), run it through the REAL resolve_office_stage.
        minted = _mint(v2_company_id)
        client = _canary_data_read_client()
        stage = resolve_office_stage(client, guid_phone_mapping={}, guid_overrides={})
        ctx = _make_ctx(minted)
        await stage(ctx)

        # The round-trip lands A, NEVER the phone-collision tenant B.
        assert ctx.chiropractor_guid == G_A
        assert ctx.chiropractor_guid != G_B
        client.get_business_by_guid_async.assert_awaited_once_with(G_A)

    @pytest.mark.asyncio
    async def test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame(
        self, mock_client
    ) -> None:
        """Engine-guard RED corroboration (GAP-1, design §4.3): feeding the engine an
        UNFILTERED multi-tenant frame (B's row leaking past the gid-exact filter)
        raises GuardViolationError via the LIVE assert_rows_tenant_identity
        (guard.py:183) — Vector-A fails CLOSED, never silently reads B's company_id."""

        async def _leaky_execute(entity_type, project_gid, client, request):
            # Simulate a drifted/buggy substrate that returns the UNFILTERED frame:
            # B's row (gid != anchored GID_BIZ) leaks past the gid-exact df.filter.
            return make_rows_response(rows=_collision_business_frame().to_dicts())

        query_engine = AsyncMock()
        query_engine.execute_rows = _leaky_execute

        # Anchor to A's Business gid; the leaked frame's first row carries B's gid.
        anchor = make_hydration_result(
            business_gid=GID_BIZ, entry_type=EntityType.OFFER, path_len=3
        )
        with patch(_HYDRATE, AsyncMock(return_value=anchor)):
            with pytest.raises(GuardViolationError):
                await resolve_async(
                    GID_OFFER,
                    ["company_id"],
                    client=mock_client,
                    query_engine=query_engine,
                )


# =========================================================================== #
# 3. DEFENSES — override-key on both surfaces; mapping neutralized; display trap.
# =========================================================================== #
class TestDefenses:
    """The build-must-encode defenses (design §5)."""

    def test_d1_g_correct_is_not_the_default_override_key(self) -> None:
        """D1: G_correct is NOT the U+200B _DEFAULT_OVERRIDES key (33e3a930-...).

        If it were, the :80 override-apply would remap the minted address to
        abb01032-... and the round-trip would prove the WRONG guid. We assert the
        canary guid is absent from every override key (the U+200B prefix is part of
        the key, so a substring check over the keys is the precise guard)."""
        override_key_guid = "33e3a930-2ade-4551-9e5b-409e31a2a8ef"
        assert override_key_guid != G_CORRECT
        for key in _DEFAULT_OVERRIDES:
            assert G_CORRECT not in key
            # And the minted canary address is not itself an override key.
            assert _mint(G_CORRECT) != key.replace("​", "")

    @pytest.mark.asyncio
    async def test_d1_default_override_remap_does_not_fire_for_g_correct(
        self,
    ) -> None:
        """D1 (behavioral): with the default overrides ACTIVE (guid_overrides=None,
        so _DEFAULT_OVERRIDES applies), the canary address is untouched and
        ctx.chiropractor_guid == G_correct — proving the U+200B remap did NOT fire."""
        client = _canary_data_read_client()
        # guid_overrides omitted entirely -> _DEFAULT_OVERRIDES is the active map.
        stage = resolve_office_stage(client, guid_phone_mapping={})
        ctx = _make_ctx(_mint(G_CORRECT))
        await stage(ctx)
        assert ctx.chiropractor_guid == G_CORRECT
        client.get_business_by_guid_async.assert_awaited_once_with(G_CORRECT)

    @pytest.mark.asyncio
    async def test_d2_injected_override_for_other_key_does_not_touch_g_correct(
        self,
    ) -> None:
        """D2: an injected guid_overrides entry for a DIFFERENT key does NOT remap
        G_correct's address. ``overrides = {**_DEFAULT_OVERRIDES, **guid_overrides}``
        (:73) is also a remap surface; this proves a foreign override is inert for
        the canary tenant."""
        client = _canary_data_read_client()
        foreign_override = {
            "someone-else@appointments.contenteapp.com": "remapped@appointments.contenteapp.com"
        }
        stage = resolve_office_stage(client, guid_phone_mapping={}, guid_overrides=foreign_override)
        ctx = _make_ctx(_mint(G_CORRECT))
        await stage(ctx)
        assert ctx.chiropractor_guid == G_CORRECT
        client.get_business_by_guid_async.assert_awaited_once_with(G_CORRECT)

    @pytest.mark.asyncio
    async def test_d3_empty_mapping_takes_by_guid_hit_not_fallback(self) -> None:
        """D3: guid_phone_mapping is empty AND get_business_by_guid_async HITs with
        G_correct (the :105 by-guid path). Negative-control: the :121 elif-guid-in-
        mapping fallback is NOT taken — the mapping is empty, so a None from the
        data-service would raise OfficeResolutionError rather than silently
        resolving via a stale override map. Here the HIT path is proven."""
        client = _canary_data_read_client()
        stage = resolve_office_stage(client, guid_phone_mapping={}, guid_overrides={})
        ctx = _make_ctx(_mint(G_CORRECT))
        result = await stage(ctx)
        assert result.status == StageStatus.COMPLETED
        # The :105 by-guid HIT was taken with G_correct.
        client.get_business_by_guid_async.assert_awaited_once_with(G_CORRECT)
        # And the :121 fallback path (mapping consult) was unreachable: the mapping
        # is empty, so identity came from the data-service record, not the map.

    @pytest.mark.asyncio
    async def test_d4_identity_is_chiropractor_guid_not_display_fields(self) -> None:
        """D4: the tenant-identity surface is ctx.chiropractor_guid ONLY. Display
        fields (ctx.office_name / ctx.office_phone) are written by the phone lookup
        (:149-170) and are NOT the identity proof. This test asserts identity on
        chiropractor_guid and explicitly does NOT assert tenant identity on display
        fields — the display values are unrelated to the tenant guid (the canary
        record name/phone are NOT the guid)."""
        client = _canary_data_read_client()
        stage = resolve_office_stage(client, guid_phone_mapping={}, guid_overrides={})
        ctx = _make_ctx(_mint(G_CORRECT))
        await stage(ctx)
        # Identity assertion targets chiropractor_guid.
        assert ctx.chiropractor_guid == G_CORRECT
        # Display fields are NOT the tenant-identity surface: the guid is never
        # carried by office_name / office_phone (proving we did not accidentally
        # assert identity on a display field).
        assert ctx.office_name != G_CORRECT
        assert ctx.office_phone != G_CORRECT


# =========================================================================== #
# 4. W1 SAFETY (fixture a) -- the cross-tenant guard THROUGH process_entity.
# =========================================================================== #
# The mandated SAFETY proof: extend the SAME collision DELTA (broken phone-join ==
# G_B, gid-exact GFR == G_A) all the way THROUGH the REAL
# OnboardingWalkthroughWorkflow.process_entity, with the REAL W1 guard
# (identity_guard.anchor_company_id -> the REAL gfr.resolve_async, engine+guard
# UNMOCKED) wired into the workflow.
#
# Setup: task T anchors tenant A (parent-chain -> G_A); T.office_phone resolves
# single-and-valid to tenant B (the mocked SDK resolver returns an address
# embedding G_B -- the phone-collision wrong tenant). The deck the producer would
# freeze carries the RESOLVED (B's) address.
#
#   * UNGUARDED leg (RED): with W1 absent (an anchor that always matches), the deck
#     for tenant B lands on tenant A's task -> assert RED on the
#     (task_gid, attached_deck_company_id) tuple / a NON-empty upload. We assert on
#     the CAPTURED UPLOAD ARGS (the deck bytes), NOT on resolved_address (P6: the
#     resolve is cleanly B by construction; the bug is attaching B's deck to A's
#     task).
#   * GUARDED leg (GREEN-by-skip): with the REAL W1, process_entity returns
#     skipped(guid_anchor_mismatch) and the mocked upload records ZERO calls. NO
#     freeze runs.
#   * CORRECT-PHONE variant (GREEN both ways): T.office_phone resolves to A's own
#     address (embedding G_A) -> W1 passes (G_A == G_A) -> freeze->T7->upload
#     proceeds; the unguarded leg ALSO lands correctly (no mismatch to catch). The
#     two-sided proof: W1 bites ONLY on the cross-tenant case.
#
# G-THEATER: the RED fires on a deliberately-broken INPUT (a wrong-tenant phone
# resolve), NEVER a defect injected into production code. The asana attach + the
# SDK resolve are mocked (no live write, no live data-service); the GFR engine,
# planner, and engine-owned guard run UNMOCKED as the system under test.

_WALKTHROUGH_WF = "autom8_asana.automation.workflows.onboarding_walkthrough.workflow"


def _addr_for(guid: str) -> str:
    """The canonical routing address embedding ``guid`` (the deck/SDK address form)."""
    return f"{guid}{_MINT_DOMAIN}"


def _wf_deck_bytes(addr: str) -> bytes:
    """A minimal frozen-deck stand-in embedding ``addr`` (mirrors the producer)."""
    return f'<html><body><a href="mailto:{addr}">{addr}</a></body></html>'.encode()


def _harvest_deck_guid(frozen: bytes) -> str | None:
    """Harvest the single embedded routing-address guid from captured deck bytes.

    The independent oracle for the SAFETY assertion: reads the guid the attached
    deck actually carries (the attached_deck_company_id), so the RED asserts on the
    TASK+attached-deck-tenant tuple, not on the resolved address (P6).
    """
    import re as _re

    m = _re.search(
        rb"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})@appointments",
        frozen,
    )
    return m.group(1).decode("ascii") if m else None


def _make_walkthrough_workflow(
    *,
    resolved_address: str,
    company_id_anchor: object,
) -> tuple[object, AsyncMock]:
    """Build the REAL OnboardingWalkthroughWorkflow with mocked I/O boundaries.

    The SDK resolver returns ``resolved_address`` (Source A). ``company_id_anchor``
    is the Source-B anchor (the REAL identity_guard.anchor_company_id for the
    guarded legs, or an always-match stub for the unguarded RED). The producer
    freeze is patched to plant a deck embedding the RESOLVED address (so an
    unguarded attach lands the resolved tenant's deck). Attachments are mocked;
    the returned ``upload_mock`` captures every upload (the SAFETY oracle).
    """
    from autom8_asana.automation.workflows.onboarding_walkthrough.workflow import (
        OnboardingWalkthroughWorkflow,
    )

    resolver = MagicMock()
    # Fault-13 widened seam: the workflow reads the full BusinessRecord row (the
    # SAME row yields the SDK-composed gated address AND the customer-plane
    # display name). Real-shaped mock: .guid drives format_routing_address.
    _record = MagicMock()
    _record.guid = resolved_address.split("@", 1)[0]
    _record.business_name = "Roundtrip Integration Clinic"
    resolver.get_business_by_phone_async = AsyncMock(return_value=_record)
    resolver.resolve_routing_address_by_phone_async = AsyncMock(return_value=resolved_address)

    upload_mock = AsyncMock(return_value=MagicMock())
    attachments = MagicMock()
    attachments.upload_async = upload_mock
    attachments.delete_async = AsyncMock()

    # No prior walkthrough decks (W2 0a harvest sees an empty task -> no skip there;
    # the SAFETY proof is about W1, not idempotency).
    def _empty_list(_gid: str, **_kwargs: object) -> object:
        async def _gen():
            return
            yield  # pragma: no cover - empty async generator

        return _gen()

    attachments.list_for_task_async = MagicMock(side_effect=_empty_list)
    attachments.download_async = AsyncMock()

    asana_client = MagicMock()
    asana_client.tasks = MagicMock()
    asana_client.tasks.get_async = AsyncMock()

    wf = OnboardingWalkthroughWorkflow(
        asana_client=asana_client,
        resolver=resolver,
        attachments_client=attachments,
        producer_dir="/tmp/_no_producer_integration",
        query_engine=MagicMock(),  # threaded to the REAL anchor's GFR call
        company_id_anchor=company_id_anchor,
    )
    return wf, upload_mock


def _real_anchor_over_collision_frame(business_gid: str):
    """The REAL identity_guard.anchor_company_id wired over the collision substrate.

    Returns a Source-B anchor that runs the REAL gfr.resolve_async (engine+guard
    UNMOCKED) against the SAME mocked substrate the roundtrip tests use: the entry
    fetch is patched to anchor the task to ``business_gid`` and execute_rows serves
    the gid-exact Business row from the collision frame. So the anchor returns
    G_A (the gid-exact tenant) while Source A is G_B (the phone-collision tenant).
    """
    from autom8_asana.automation.workflows.onboarding_walkthrough import identity_guard

    async def _anchor(*, task_gid, client, query_engine, verifier):
        async def _gid_exact_execute(entity_type, project_gid, _client, request):
            target_gid = request.where.value
            rows = _collision_business_frame().filter(pl.col("gid") == target_gid).to_dicts()
            return make_rows_response(rows=rows)

        real_engine = AsyncMock()
        real_engine.execute_rows = _gid_exact_execute
        anchor_result = make_hydration_result(
            business_gid=business_gid, entry_type=EntityType.OFFER, path_len=3
        )
        with patch(_HYDRATE, AsyncMock(return_value=anchor_result)):
            # Call the REAL guard helper -> REAL gfr.resolve_async.
            return await identity_guard.anchor_company_id(
                task_gid=task_gid,
                client=client,
                query_engine=real_engine,
                verifier=verifier,
            )

    return _anchor


class TestW1SafetyThroughProcessEntity:
    """Fixture (a): the cross-tenant SAFETY guard exercised THROUGH process_entity
    with the REAL GFR engine + guard (UNMOCKED) as the system under test."""

    @pytest.mark.asyncio
    async def test_unguarded_leg_attaches_wrong_tenant_deck_red(self) -> None:
        """RED: WITHOUT W1, tenant B's deck lands on tenant A's task.

        The unguarded leg uses an anchor that ECHOES Source A (so the gid-exact
        compare never trips -- W1 effectively absent). The phone resolves to B's
        address; the producer freezes B's deck; the attach fires with B's deck on
        A's task. Assert RED on (A's task_gid, attached_deck_company_id == G_B) and
        a NON-empty upload -- NOT on resolved_address (P6)."""

        async def _echo_source_a(*, task_gid, client, query_engine, verifier):
            # Echo Source A (G_B) so address_guid == anchored -> NO mismatch (W1 off).
            from autom8_asana.automation.workflows.onboarding_walkthrough.identity_guard import (
                AnchorResult,
            )
            from autom8_asana.resolution.gfr.models import TruthTier

            return AnchorResult(company_id=G_B.lower(), tier=TruthTier.CACHE)

        wf, upload_mock = _make_walkthrough_workflow(
            resolved_address=_addr_for(G_B),  # phone collision -> WRONG tenant B
            company_id_anchor=_echo_source_a,
        )
        with patch(
            f"{_WALKTHROUGH_WF}._producer.freeze_walkthrough_deck",
            AsyncMock(return_value=_wf_deck_bytes(_addr_for(G_B))),
        ):
            # T is tenant A's task (anchors G_A); office_phone collides to B.
            out = await wf.process_entity(
                {"gid": "task_A", "calendar_provider": "GHL", "office_phone": SHARED_PHONE},
                {},
            )

        # The UNGUARDED leak: the attach fired (deck for B on A's task).
        upload_mock.assert_awaited_once()
        attached_bytes = upload_mock.await_args.kwargs["file"].getvalue()
        attached_deck_company_id = _harvest_deck_guid(attached_bytes)
        # RED on the (task_gid, attached_deck_company_id) tuple: B's deck on A's task.
        assert attached_deck_company_id == G_B  # the WRONG tenant's deck was attached
        assert attached_deck_company_id != G_A
        assert out.status == "succeeded"  # unguarded => the leak "succeeds"

    @pytest.mark.asyncio
    async def test_guarded_leg_skips_cross_tenant_zero_uploads_green(self) -> None:
        """GREEN-by-skip: WITH the REAL W1, the cross-tenant case is caught.

        Source A (phone) resolves to B (G_B); the REAL GFR anchor walks A's
        parent-chain to G_A; G_B != G_A -> skipped(guid_anchor_mismatch), the mocked
        upload records ZERO calls, NO freeze runs."""
        freeze_spy = AsyncMock(return_value=_wf_deck_bytes(_addr_for(G_B)))
        wf, upload_mock = _make_walkthrough_workflow(
            resolved_address=_addr_for(G_B),  # phone collision -> WRONG tenant B
            company_id_anchor=_real_anchor_over_collision_frame(GID_BIZ),  # REAL GFR -> G_A
        )
        with patch(f"{_WALKTHROUGH_WF}._producer.freeze_walkthrough_deck", freeze_spy):
            out = await wf.process_entity(
                {"gid": "task_A", "calendar_provider": "GHL", "office_phone": SHARED_PHONE},
                {},
            )
        assert out.status == "skipped"
        assert out.reason == "guid_anchor_mismatch"
        upload_mock.assert_not_awaited()  # ZERO uploads -- the leak is closed
        freeze_spy.assert_not_awaited()  # NO freeze ran (guard precedes FREEZE)

    @pytest.mark.asyncio
    async def test_correct_phone_variant_green_both_ways(self) -> None:
        """The two-sided canary: correct phone (resolves to A) -> W1 PASSES -> attach.

        T.office_phone resolves to A's OWN address (embedding G_A); the REAL GFR
        anchor is also G_A; G_A == G_A -> the guard passes; freeze->T7->upload
        proceeds and the deck for A lands on A's task. W1 bites ONLY on the
        cross-tenant case, never on the correct one."""
        wf, upload_mock = _make_walkthrough_workflow(
            resolved_address=_addr_for(G_A),  # correct phone -> A's own address
            company_id_anchor=_real_anchor_over_collision_frame(GID_BIZ),  # REAL GFR -> G_A
        )
        with patch(
            f"{_WALKTHROUGH_WF}._producer.freeze_walkthrough_deck",
            AsyncMock(return_value=_wf_deck_bytes(_addr_for(G_A))),
        ):
            out = await wf.process_entity(
                {"gid": "task_A", "calendar_provider": "GHL", "office_phone": CANARY_PHONE},
                {},
            )
        assert out.status == "succeeded"
        upload_mock.assert_awaited_once()
        attached_deck_company_id = _harvest_deck_guid(
            upload_mock.await_args.kwargs["file"].getvalue()
        )
        # GREEN: A's OWN deck lands on A's task (correct tenant).
        assert attached_deck_company_id == G_A
