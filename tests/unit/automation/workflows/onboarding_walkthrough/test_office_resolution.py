"""Two-sided test matrix for the hierarchy-first office-guid / task->business resolver.

Per TDD-entity-resolution-primitive-2026-07-08 §6 (T-1..T-6) + HANDOFF ITEM-4. The
load-bearing claims:

  * T-1 (POSITIVE, hierarchy): a TWC-class office resolves via the ANCESTOR WALK where the
    office_phone path is AMBIGUOUS -- the discriminating teeth (the walk bites correctly,
    phone refuses correctly on the SAME office).
  * T-2 (POSITIVE, fallback): a phone-only / orphan-parent office still resolves via the
    labeled phone fallback; the crosscheck tripwire passes on agreement.
  * T-3 (NEGATIVE, B5 non-regression): the resolver imports NO ``get_gid_map`` /
    ``DataServiceClient`` (grep EMPTY) -- the external-dataset coverage-gap failure MODE is
    structurally unreachable.
  * T-4 (NEGATIVE, ambiguity discipline): a multi-Business ancestor chain refuses LOUD
    (``BusinessResolutionAmbiguous`` with both gids), never a silent first-match.
  * T-5 (NEGATIVE, refusal-code distinctness): depth-exhausted
    (``BusinessResolutionDepthExhausted``) is diagnosably distinct from no-business-ancestor
    (``business_gid=None``).
  * T-6 (INVARIANT): the crown-jewel ``TaskOfficeMismatch`` guard is preserved.

Store-independence is the primary architecture: the walk unit tests construct synthetic
``HierarchyIndex``-shaped node dicts and a fake client with NO ``UnifiedTaskStore`` handle.
If the walk needed a store, the design would be falsified (HANDOFF ITEM-1 TL-A).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough import contact_synthesis as cs
from autom8_asana.automation.workflows.onboarding_walkthrough import office_resolution as orr
from autom8_asana.automation.workflows.onboarding_walkthrough import template_comment as tc
from autom8_asana.automation.workflows.onboarding_walkthrough.contact_synthesis import (
    ContactCardBusinessAmbiguous,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.office_resolution import (
    BusinessResolution,
    BusinessResolutionAmbiguous,
    BusinessResolutionDepthExhausted,
    DivergentOfficeResolution,
    resolve_business_gid,
    resolve_office_guid,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TaskOfficeMismatch,
)
from autom8_asana.core.project_registry import BUSINESS_PROJECT

# --- Real Total Wellness Center chain (SPIKE-office-guid-resolution-hierarchy-vs-phone) ---
# PLAY 1215766139321621
#   -> 1214127290389479  "Total Wellness Center PLAYS/REQUESTS"
#        -> 1214127219419742  "Total Wellness Center"  [BUSINESS_PROJECT member]
#             Company ID = 7363c7ea-66f8-487f-9f6e-c7a12a63d33f
TWC_PLAY = "1215766139321621"
TWC_MID = "1214127290389479"
TWC_BUSINESS = "1214127219419742"
TWC_COMPANY_ID = "7363c7ea-66f8-487f-9f6e-c7a12a63d33f"
TWC_PHONE = "+13036277995"
# The opportunity/lead card that aliases the same office phone (phone-path ambiguity source).
TWC_OPPORTUNITY = "1214420107547660"


def _task_node(
    gid: str,
    *,
    parent: str | None = None,
    projects: list[str] | None = None,
    company_id: str | None = None,
    office_phone: str | None = None,
    name: str = "",
) -> dict:
    """Build a raw Asana task node dict exactly as ``tasks.get_async(raw=True)`` returns it."""
    custom_fields = []
    if company_id is not None:
        custom_fields.append({"name": "Company ID", "display_value": company_id})
    if office_phone is not None:
        custom_fields.append({"name": "Office Phone", "display_value": office_phone})
    node: dict = {
        "gid": gid,
        "name": name,
        "projects": [{"gid": p} for p in (projects or [])],
        "custom_fields": custom_fields,
    }
    if parent is not None:
        node["parent"] = {"gid": parent}
    return node


class _FakeTasks:
    """A fake ``client.tasks`` whose ``get_async(raw=True)`` serves from a synthetic chain map.

    The ONLY network primitive the resolver depends on (TDD T-3 behavioral claim). Records
    every gid fetched so tests can assert the walk short-circuits on the first Business.
    """

    def __init__(self, nodes: dict[str, dict]):
        self._nodes = nodes
        self.fetched: list[str] = []

    async def get_async(self, task_gid: str, *, opt_fields=None, raw: bool = False):
        self.fetched.append(task_gid)
        assert raw is True, "the walk must fetch raw dicts (store-independent), not Task models"
        return self._nodes[task_gid]


class _FakeClient:
    """A fake AsanaClient with NO UnifiedTaskStore -- proves the walk is store-independent."""

    def __init__(self, nodes: dict[str, dict]):
        self.tasks = _FakeTasks(nodes)


def _twc_chain() -> dict[str, dict]:
    """The real TWC ancestor chain: PLAY -> mid -> BUSINESS (Company ID on the Business)."""
    return {
        TWC_PLAY: _task_node(TWC_PLAY, parent=TWC_MID, office_phone=TWC_PHONE, name="PLAY: TWC"),
        TWC_MID: _task_node(TWC_MID, parent=TWC_BUSINESS, name="TWC PLAYS/REQUESTS"),
        TWC_BUSINESS: _task_node(
            TWC_BUSINESS,
            projects=[BUSINESS_PROJECT],
            company_id=TWC_COMPANY_ID,
            office_phone=TWC_PHONE,
            name="Total Wellness Center",
        ),
    }


# ============================================================ T-1 POSITIVE (hierarchy)


class TestT1HierarchyResolvesWherePhoneAmbiguous:
    async def test_twc_resolves_via_walk_at_depth_2(self) -> None:
        """T-1: the TWC PLAY walks PLAY -> mid -> BUSINESS and resolves the Business gid +
        Company ID at ancestor_depth==2, method=='hierarchy'. This is the office the phone
        path HOLDS fail-closed."""
        client = _FakeClient(_twc_chain())
        res = await resolve_business_gid(client, task_gid=TWC_PLAY)
        assert res.business_gid == TWC_BUSINESS
        assert res.company_id == TWC_COMPANY_ID
        assert res.method == "hierarchy"
        assert res.ancestor_depth == 2
        assert res.candidates == ()

    async def test_resolve_office_guid_reads_company_id(self) -> None:
        """resolve_office_guid is the guid-only convenience over resolve_business_gid: it
        returns the Company ID the walk already read off the matched Business node."""
        client = _FakeClient(_twc_chain())
        guid = await resolve_office_guid(client, task_gid=TWC_PLAY)
        assert guid == TWC_COMPANY_ID

    async def test_walk_short_circuits_on_first_business(self) -> None:
        """The walk stops at the first BUSINESS ancestor -- it fetches exactly PLAY, mid,
        Business (3 gets), never continuing past the resolved office."""
        client = _FakeClient(_twc_chain())
        await resolve_business_gid(client, task_gid=TWC_PLAY)
        assert client.tasks.fetched == [TWC_PLAY, TWC_MID, TWC_BUSINESS]

    async def test_phone_path_on_same_office_refuses_ambiguous(self) -> None:
        """T-1 DISCRIMINATING TEETH (two-sided): the office_phone bridge on the SAME office
        raises ContactCardBusinessAmbiguous (2 Business-project matches for the shared phone)
        -- the walk succeeds precisely where phone fails."""

        class _AmbiguousPhoneHttp:
            async def get(self, path, params=None):
                # Two Business-project members share TWC_PHONE (the BUSINESS card + the
                # opportunity card) -- the exact aliasing that HELD TWC fail-closed.
                return {
                    "data": [
                        {"gid": TWC_BUSINESS, "projects": [{"gid": BUSINESS_PROJECT}]},
                        {"gid": TWC_OPPORTUNITY, "projects": [{"gid": BUSINESS_PROJECT}]},
                    ]
                }

        phone_client = SimpleNamespace(
            default_workspace_gid="1143357799778608", _http=_AmbiguousPhoneHttp()
        )
        with pytest.raises(ContactCardBusinessAmbiguous, match="refusing to pick"):
            await cs._business_gid_by_phone(phone_client, TWC_PHONE)


# ============================================================ T-2 POSITIVE (fallback)


class TestT2PhoneFallbackAndCrosscheck:
    async def test_crosscheck_passes_on_agreement(self) -> None:
        """T-2: a clean single-Business office resolves by BOTH paths; with
        phone_crosscheck=True the hierarchy gid == the phone gid, so NO
        DivergentOfficeResolution is raised."""
        client = _FakeClient(_twc_chain())
        with (
            patch.object(cs, "_read_office_phone", new=AsyncMock(return_value=TWC_PHONE)),
            patch.object(cs, "_business_gid_by_phone", new=AsyncMock(return_value=TWC_BUSINESS)),
        ):
            res = await resolve_business_gid(client, task_gid=TWC_PLAY, phone_crosscheck=True)
        assert res.business_gid == TWC_BUSINESS
        assert res.method == "hierarchy"

    async def test_crosscheck_raises_on_disagreement(self) -> None:
        """T-2 TEETH: when the phone bridge points at a DIFFERENT Business than the walk,
        the crosscheck raises DivergentOfficeResolution (the LOUD shadow tripwire)."""
        client = _FakeClient(_twc_chain())
        with (
            patch.object(cs, "_read_office_phone", new=AsyncMock(return_value=TWC_PHONE)),
            patch.object(
                cs, "_business_gid_by_phone", new=AsyncMock(return_value="9999999999999999")
            ),
        ):
            with pytest.raises(DivergentOfficeResolution, match="disagree"):
                await resolve_business_gid(client, task_gid=TWC_PLAY, phone_crosscheck=True)

    async def test_orphan_play_returns_none_for_caller_fallback(self) -> None:
        """T-2: a walk-None case (orphan PLAY: chain ends at a non-Business root) returns
        business_gid=None so the CALLER falls back to phone. The resolver does not silently
        phone-fallback itself."""
        orphan_chain = {
            TWC_PLAY: _task_node(TWC_PLAY, parent="ROOTNOB", office_phone=TWC_PHONE),
            "ROOTNOB": _task_node("ROOTNOB", projects=["8888888888"], name="not a Business"),
        }
        client = _FakeClient(orphan_chain)
        res = await resolve_business_gid(client, task_gid=TWC_PLAY)
        assert res.business_gid is None
        assert res.company_id is None
        assert res.ancestor_depth is None
        assert res.method == "hierarchy"

    async def test_caller_falls_back_to_phone_method_labeled(self) -> None:
        """T-2 (caller contract): resolve_ranked_cards with a walk-None PLAY falls back to the
        office_phone bridge (method='phone' provenance in the fleet signal). Here the walk
        returns None (orphan), the phone bridge locates the Business, and the traversal
        proceeds -- proving the fallback contract is LIVE."""
        orphan_chain = {
            TWC_PLAY: _task_node(TWC_PLAY, parent="ROOTNOB"),
            "ROOTNOB": _task_node("ROOTNOB", projects=["8888888888"]),
        }
        client = _FakeClient(orphan_chain)
        # Fallback locates the Business by phone; subtasks_async returns no holder -> no_holder,
        # but critically the phone bridge WAS consulted (the fallback fired).
        client.tasks.subtasks_async = lambda gid, include_detection_fields=False: SimpleNamespace(
            collect=AsyncMock(return_value=[])
        )
        phone_probe = AsyncMock(return_value=TWC_BUSINESS)
        with patch.object(cs, "_business_gid_by_phone", new=phone_probe):
            found, cards = await cs.resolve_ranked_cards(client, TWC_PHONE, task_gid=TWC_PLAY)
        phone_probe.assert_awaited_once_with(client, TWC_PHONE)
        assert (found, cards) == (False, [])


# ============================================================ T-3 NEGATIVE (B5 non-regression)


class TestT3B5NonRegression:
    def test_no_get_gid_map_or_dataserviceclient_import(self) -> None:
        """T-3 (static): office_resolution.py imports NO get_gid_map / DataServiceClient /
        vertical export symbol -- the B5 external-dataset coverage-gap failure MODE is
        structurally unreachable. grep returns EMPTY."""
        source = Path(orr.__file__).read_text()
        assert "get_gid_map" not in source
        assert "DataServiceClient" not in source

    def test_only_network_dependency_is_tasks_get_async(self) -> None:
        """T-3 (behavioral): the resolver's ONLY network dependency is
        asana_client.tasks.get_async -- no M2M creds, no vertical key, no data-service
        client. The source references no other client surface for its reads."""
        source = Path(orr.__file__).read_text()
        assert "tasks.get_async" in source
        # No other read-plane client surfaces leak in.
        assert "_http" not in source
        assert "get_gid_map" not in source


# ============================================================ T-4 NEGATIVE (ambiguity)


class TestT4MultiBusinessRefusesLoud:
    async def test_two_business_ancestors_raise_ambiguous(self) -> None:
        """T-4: a synthetic chain with TWO ancestors both members of BUSINESS_PROJECT ->
        BusinessResolutionAmbiguous naming BOTH gids (never a silent first-match). Mirrors
        contact_synthesis.py:406-410 discipline at the hierarchy altitude."""
        chain = {
            "PLAY": _task_node("PLAY", parent="BIZ_A"),
            "BIZ_A": _task_node("BIZ_A", parent="BIZ_B", projects=[BUSINESS_PROJECT]),
            "BIZ_B": _task_node("BIZ_B", projects=[BUSINESS_PROJECT], company_id="cid-b"),
        }
        client = _FakeClient(chain)
        with pytest.raises(BusinessResolutionAmbiguous) as exc_info:
            await resolve_business_gid(client, task_gid="PLAY")
        assert "BIZ_A" in str(exc_info.value)
        assert "BIZ_B" in str(exc_info.value)


# ============================================================ T-5 NEGATIVE (refusal codes)


class TestT5RefusalCodeDistinctness:
    async def test_depth_exhausted_is_distinct_code(self) -> None:
        """T-5: a chain DEEPER than max_depth with a live parent still pending ->
        BusinessResolutionDepthExhausted (distinct from no-business-ancestor)."""
        # A long non-Business chain: N0 -> N1 -> ... -> N5 -> N6 (live parent past depth 5).
        chain = {}
        for i in range(7):
            parent = f"N{i + 1}" if i < 6 else "N7"
            chain[f"N{i}"] = _task_node(f"N{i}", parent=parent)
        # N7 exists but is never reached under max_depth=5 (kept in the map so the fetch that
        # WOULD happen has a target; the walk stops BEFORE fetching it).
        chain["N7"] = _task_node("N7")
        client = _FakeClient(chain)
        with pytest.raises(BusinessResolutionDepthExhausted, match="depth-exhausted"):
            await resolve_business_gid(client, task_gid="N0", max_depth=5)

    async def test_no_business_ancestor_returns_none_not_depth_error(self) -> None:
        """T-5: an orphan / mis-parented PLAY whose chain ENDS (null parent) with no Business
        member returns business_gid=None -- diagnosably DIFFERENT from depth-exhaustion (no
        raise; the caller falls back to phone then TemplateCommentRefused / no_holder)."""
        chain = {
            "PLAY": _task_node("PLAY", parent="ROOT"),
            "ROOT": _task_node("ROOT", projects=["7777777777"]),  # chain ends, not a Business
        }
        client = _FakeClient(chain)
        res = await resolve_business_gid(client, task_gid="PLAY", max_depth=5)
        assert res.business_gid is None
        assert res.ancestor_depth is None

    async def test_self_is_business_resolves_at_depth_zero(self) -> None:
        """A task that IS itself a BUSINESS member resolves at ancestor_depth==0 (0 hops)."""
        chain = {
            "BIZ": _task_node("BIZ", projects=[BUSINESS_PROJECT], company_id="cid-self"),
        }
        client = _FakeClient(chain)
        res = await resolve_business_gid(client, task_gid="BIZ")
        assert res.business_gid == "BIZ"
        assert res.ancestor_depth == 0
        assert res.company_id == "cid-self"


# ============================================================ T-6 INVARIANT (crown-jewel)


class TestT6CrownJewelPreserved:
    async def test_task_office_mismatch_still_refuses(self) -> None:
        """T-6: post_template_comment with a mismatched supplied office_guid still raises
        TaskOfficeMismatch -- now against the HIERARCHY-resolved guid (strictly stronger).
        The crown-jewel verify (template_comment.py:319-327) is byte-for-byte unchanged."""
        client = SimpleNamespace(
            stories=SimpleNamespace(
                list_for_task_async=lambda *a, **k: SimpleNamespace(
                    collect=AsyncMock(return_value=[])
                ),
                create_comment_async=AsyncMock(),
            )
        )
        deck_url = "https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/"
        foreign_guid = "b167331c-536f-4996-9b2d-2f696f35f556"
        # The task resolves (via hierarchy) to TWC's OWN guid; a supplied FOREIGN guid != it.
        with patch.object(tc, "_resolve_office_guid", new=AsyncMock(return_value=TWC_COMPANY_ID)):
            with pytest.raises(TaskOfficeMismatch, match="does not belong to PLAY"):
                await tc.post_template_comment(
                    client,
                    task_gid=TWC_PLAY,
                    deck_url=deck_url,
                    office_guid=foreign_guid,
                    execute=True,
                )
        client.stories.create_comment_async.assert_not_awaited()


# ============================================================ ITEM-1 TL-A (store-independence)


class TestStoreIndependence:
    async def test_walk_resolves_root_at_depth_2_without_any_store(self) -> None:
        """HANDOFF ITEM-1 TL-A: construct a fresh chain (child -> parent -> BUSINESS-member
        root) and resolve the root gid at ancestor_depth==2 WITHOUT any UnifiedTaskStore
        handle. If it needed a store, the design is falsified. The fake client has ONLY a
        .tasks attribute (no store)."""
        chain = {
            "child": _task_node("child", parent="parent"),
            "parent": _task_node("parent", parent="root"),
            "root": _task_node("root", projects=[BUSINESS_PROJECT], company_id="cid-root"),
        }
        client = _FakeClient(chain)
        assert not hasattr(client, "store")
        res = await resolve_business_gid(client, task_gid="child")
        assert res.business_gid == "root"
        assert res.ancestor_depth == 2
        assert res.company_id == "cid-root"

    def test_result_is_frozen(self) -> None:
        """BusinessResolution is a frozen dataclass (immutable result envelope)."""
        res = BusinessResolution(
            business_gid="B", company_id="C", method="hierarchy", ancestor_depth=1
        )
        with pytest.raises((AttributeError, TypeError)):
            res.business_gid = "X"  # type: ignore[misc]
