"""CC-5: Tier-1 offers-only story-warm repair + per-entity warm receipt.

Sprint CC-5 (chain-of-custody-closure Phase 2, operator ruling R-1: Tier 1,
offers-only, ~4,192 tasks, ONE Lambda invocation, one project GID).

The defect under repair
-----------------------
The piggyback story warmer's budget is TIME-bound and was exhausted every run
inside the first four cascade entities. ``offer`` is entity #5 (cumulative
slice 10,617-14,808) against a warmer that never got past ~8,527 tasks:
0 of 4,192 offer tasks warmed across 324+ runs / 14 days. ``total_tasks``
crossed offer's boundary every run; ``success`` never did.

The two-sided discrimination
----------------------------
``test_offer_starves_under_legacy_order_and_warms_under_priority_order`` runs
ONE fixture and ONE budget through BOTH orderings:

* RED leg  -- ``ASANA_STORY_WARM_PRIORITY_ENTITIES=""`` (the pre-CC-5 pure
  cascade order, reachable via the operator revert lever): offer.success == 0.
* GREEN leg -- default priority set: offer.success == full population.

The AGGREGATE ``StoryWarmSuccess`` is IDENTICAL (200) on both legs. Only the
per-entity receipt moves. That is not incidental -- it is the precise reason
the SLATE section 4 receipt shape exists: the aggregate counter cannot
distinguish "warmed offer" from "warmed 200 more of entity #1", so a fix
proven only against the aggregate is not proven at all. A test that asserted
only on ``stats["success"]`` would read GREEN on the broken code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl

from autom8_asana.lambda_handlers.story_warmer import (
    _STORY_WARM_CONCURRENCY,
    DEFAULT_STORY_WARM_PRIORITY_ENTITIES,
    STORY_WARM_PRIORITY_ENV_VAR,
    _build_warm_order,
    _resolve_priority_entities,
    _warm_story_caches_for_completed_entities,
)

if TYPE_CHECKING:
    import pytest

# --------------------------------------------------------------------------
# Fixtures / helpers
# --------------------------------------------------------------------------


def _project_gid(entity_type: str) -> str:
    """Registry-shaped GID resolver (never a hardcoded offer GID in src)."""
    return f"project-{entity_type}"


def _make_cache(populations: dict[str, int]) -> MagicMock:
    """DataFrame cache returning ``populations[entity]`` distinct task GIDs."""

    async def _get_async(project_gid: str, entity_type: str) -> Any:
        count = populations.get(entity_type)
        if count is None:
            return None
        entry = MagicMock()
        entry.dataframe = pl.DataFrame({"gid": [f"{entity_type}-task-{i}" for i in range(count)]})
        return entry

    cache = MagicMock()
    cache.get_async = _get_async
    return cache


def _make_client() -> MagicMock:
    client = MagicMock()
    client.stories = MagicMock()
    client.stories.list_for_task_cached_async = AsyncMock(return_value=[])
    return client


def _budget(allowed_chunk_checks: int) -> MagicMock:
    """Lambda context granting exactly N timeout-clean chunk checks.

    ``_should_exit_early`` is consulted once per 100-task chunk, so this is a
    deterministic stand-in for the production time budget.
    """
    context = MagicMock()
    calls = {"n": 0}

    def get_remaining() -> int:
        calls["n"] += 1
        return 300_000 if calls["n"] <= allowed_chunk_checks else 60_000

    context.get_remaining_time_in_millis = get_remaining
    return context


def _receipt(stats: dict[str, Any], entity_type: str) -> dict[str, Any]:
    for entry in stats["entities"]:
        if entry["entity_type"] == entity_type:
            return entry
    raise AssertionError(
        f"no receipt emitted for {entity_type!r}; "
        f"got {[e['entity_type'] for e in stats['entities']]}"
    )


async def _run(
    completed_entities: list[str],
    populations: dict[str, int],
    context: Any,
    mock_emit: Any = None,
    mock_logger: Any = None,
) -> dict[str, Any]:
    emit_ctx = patch(
        "autom8_asana.lambda_handlers.story_warmer.emit_metric",
        mock_emit or MagicMock(),
    )
    log_ctx = patch(
        "autom8_asana.lambda_handlers.story_warmer.logger",
        mock_logger or MagicMock(),
    )
    with emit_ctx, log_ctx:
        return await _warm_story_caches_for_completed_entities(
            completed_entities=completed_entities,
            get_project_gid=_project_gid,
            dataframe_cache=_make_cache(populations),
            client=_make_client(),
            invocation_id="cc5-test",
            context=context,
        )


# --------------------------------------------------------------------------
# The two-sided discriminating canary
# --------------------------------------------------------------------------


class TestTierOneOfferWarmDiscrimination:
    """RED under the pre-CC-5 order, GREEN under priority-first. Same budget."""

    CASCADE = ["business", "unit", "offer"]
    POPULATIONS = {"business": 200, "unit": 200, "offer": 200}
    # Two clean chunk checks == exactly one entity's worth of budget.
    BUDGET_CHUNK_CHECKS = 2

    async def test_offer_starves_under_legacy_order_and_warms_under_priority_order(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # ---- RED leg: pre-CC-5 pure cascade order (priority set disabled).
        monkeypatch.setenv(STORY_WARM_PRIORITY_ENV_VAR, "")
        red = await _run(self.CASCADE, self.POPULATIONS, _budget(self.BUDGET_CHUNK_CHECKS))

        assert _receipt(red, "offer")["success"] == 0, (
            "RED leg must reproduce the production defect (offer warmed 0). "
            "If this passes offer > 0, the fixture no longer starves and the "
            "GREEN leg proves nothing."
        )
        assert _receipt(red, "offer")["enumerated"] is True
        assert _receipt(red, "offer")["budget_exhausted"] is True
        assert _receipt(red, "business")["success"] == 200

        # ---- GREEN leg: default priority set, identical fixture and budget.
        monkeypatch.delenv(STORY_WARM_PRIORITY_ENV_VAR, raising=False)
        green = await _run(self.CASCADE, self.POPULATIONS, _budget(self.BUDGET_CHUNK_CHECKS))

        assert _receipt(green, "offer")["success"] == 200
        assert _receipt(green, "offer")["priority"] is True
        assert _receipt(green, "offer")["position"] == 0
        assert _receipt(green, "business")["success"] == 0

        # ---- The teeth: the AGGREGATE cannot tell the two legs apart.
        assert red["success"] == green["success"] == 200
        assert red["total_tasks"] == green["total_tasks"] == 600
        # Only the per-entity receipt discriminates.
        assert _receipt(red, "offer")["success"] != _receipt(green, "offer")["success"]

    async def test_offer_warmed_even_when_absent_from_completed_entities(self) -> None:
        """CF-18 / checkpoint-resume robustness.

        ``cascade_warm_phases`` breaks ``warm_priority`` ties by iterating a
        ``set`` (order not stable across processes), and a checkpoint resume
        can trim entities out of ``completed_entities`` entirely. The priority
        pass is keyed on the entity's own project GID, so neither can demote
        or drop offer.
        """
        stats = await _run(
            ["business", "unit"],  # offer absent
            self.POPULATIONS,
            _budget(self.BUDGET_CHUNK_CHECKS),
        )
        assert _receipt(stats, "offer")["success"] == 200
        assert _receipt(stats, "offer")["position"] == 0

    async def test_offer_warmed_once_not_twice_when_also_in_cascade(self) -> None:
        """Priority membership must not double-enumerate the population."""
        stats = await _run(["offer", "business"], self.POPULATIONS, _budget(99))
        offer_receipts = [e for e in stats["entities"] if e["entity_type"] == "offer"]
        assert len(offer_receipts) == 1
        assert stats["total_tasks"] == 400  # offer 200 + business 200, not 600

    async def test_partial_offer_coverage_is_reported_honestly(self) -> None:
        """A budget too small for the full population must NOT read as done."""
        stats = await _run(["offer"], {"offer": 500}, _budget(2))
        receipt = _receipt(stats, "offer")
        assert receipt["task_count"] == 500  # denominator always present
        assert receipt["success"] == 200
        assert receipt["budget_exhausted"] is True
        assert receipt["success"] < receipt["task_count"]


# --------------------------------------------------------------------------
# SLATE section 4 receipt shape
# --------------------------------------------------------------------------


class TestPerEntityWarmReceipt:
    async def test_receipt_emitted_for_every_planned_entity_every_run(self) -> None:
        mock_logger = MagicMock()
        stats = await _run(
            ["business", "unit", "offer"],
            {"business": 200, "unit": 200, "offer": 200},
            _budget(2),
            mock_logger=mock_logger,
        )

        emitted = [
            call.kwargs["extra"]
            for call in mock_logger.info.call_args_list
            if call.args and call.args[0] == "story_warm_entity_complete"
        ]
        assert len(emitted) == 3
        assert {e["entity_type"] for e in emitted} == {"business", "unit", "offer"}
        assert len(stats["entities"]) == 3

    async def test_zero_is_emitted_explicitly_not_omitted(self) -> None:
        """NR-4(d): an absent record is indistinguishable from an explicit 0.

        Budget of zero clean chunk checks reproduces the worst case (the
        frame warm consumed everything). Every entity must still emit a
        record carrying an explicit ``success: 0``.
        """
        mock_logger = MagicMock()
        await _run(
            ["business", "offer"],
            {"business": 200, "offer": 200},
            _budget(0),
            mock_logger=mock_logger,
        )
        records = {
            call.kwargs["extra"]["entity_type"]: call.kwargs["extra"]
            for call in mock_logger.info.call_args_list
            if call.args and call.args[0] == "story_warm_entity_complete"
        }
        assert set(records) == {"offer", "business"}
        for entity_type, record in records.items():
            assert "success" in record, entity_type  # present...
            assert record["success"] == 0, entity_type  # ...explicit, and zero
            assert record["enumerated"] is True, entity_type  # reached, not warmed
            assert record["task_count"] == 200, entity_type  # denominator present

    async def test_two_negatives_are_distinguishable(self) -> None:
        """starvation (enumerated, 0 warmed) vs never-reached (not enumerated)."""
        # unit has no DataFrame at all -> never reached.
        stats = await _run(
            ["business", "unit", "offer"],
            {"business": 200, "offer": 200},  # 'unit' absent from the cache
            _budget(2),
        )

        starved = _receipt(stats, "business")
        assert starved["enumerated"] is True
        assert starved["success"] == 0
        assert starved["budget_exhausted"] is True
        assert starved["skip_reason"] is None

        never_reached = _receipt(stats, "unit")
        assert never_reached["enumerated"] is False
        assert never_reached["skip_reason"] == "no_cache_entry"
        assert never_reached["task_count"] == 0

    async def test_priority_entity_emits_dimensioned_metrics_including_zero(
        self,
    ) -> None:
        mock_emit = MagicMock()
        await _run(
            ["business", "offer"],
            {"business": 200, "offer": 200},
            _budget(0),  # nothing warms at all
            mock_emit=mock_emit,
        )

        offer_metrics = {
            call.args[0]: call.args[1]
            for call in mock_emit.call_args_list
            if call.kwargs.get("dimensions") == {"entity_type": "offer"}
        }
        assert offer_metrics["StoryWarmEntitySuccess"] == 0
        assert offer_metrics["StoryWarmEntityTaskCount"] == 200  # denominator
        assert offer_metrics["StoryWarmEntityReached"] == 1
        assert offer_metrics["StoryWarmEntityFailure"] == 0

    async def test_non_priority_entities_do_not_mint_dimensioned_series(self) -> None:
        """Bounds the new CloudWatch series to the Tier-1 scope."""
        mock_emit = MagicMock()
        await _run(
            ["business", "unit", "offer"],
            {"business": 10, "unit": 10, "offer": 10},
            None,
            mock_emit=mock_emit,
        )
        dimensioned = [
            call.kwargs["dimensions"]
            for call in mock_emit.call_args_list
            if call.kwargs.get("dimensions")
        ]
        assert dimensioned, "priority entity must still emit dimensioned metrics"
        assert all(d == {"entity_type": "offer"} for d in dimensioned)

    async def test_story_warm_complete_is_unconditional(self) -> None:
        """An all-zero run must log a measured zero, not nothing at all."""
        mock_logger = MagicMock()
        await _run([], {}, None, mock_logger=mock_logger)
        completes = [
            call.kwargs["extra"]
            for call in mock_logger.info.call_args_list
            if call.args and call.args[0] == "story_warm_complete"
        ]
        assert len(completes) == 1
        assert completes[0]["success"] == 0
        assert completes[0]["total_tasks"] == 0

    async def test_timeout_exit_log_preserves_probe_query_fields(self) -> None:
        """The PROBE/CRITIQUE Logs Insights queries parse these two fields.

        ``tasks_processed`` and ``total_tasks`` keep their pre-CC-5 cumulative
        semantics so the 14-day baseline series stays comparable across the
        deploy boundary.
        """
        mock_logger = MagicMock()
        await _run(
            ["offer", "business"],
            {"offer": 200, "business": 200},
            _budget(2),
            mock_logger=mock_logger,
        )
        exits = [
            call.kwargs["extra"]
            for call in mock_logger.warning.call_args_list
            if call.args and call.args[0] == "story_warm_timeout_exit"
        ]
        assert exits, "a starved entity must still log story_warm_timeout_exit"
        first = exits[0]
        assert first["tasks_processed"] == 200  # cumulative, across entities
        assert first["total_tasks"] == 400  # cumulative, includes this entity
        assert first["entity_type"] == "business"

    async def test_cf3_population_overlap_is_measured_not_assumed(self) -> None:
        """CF-3: shared GIDs between entities are counted, not waved away."""
        shared = pl.DataFrame({"gid": ["dup-1", "dup-2", "only-a"]})
        other = pl.DataFrame({"gid": ["dup-1", "dup-2", "only-b"]})

        async def _get_async(project_gid: str, entity_type: str) -> Any:
            entry = MagicMock()
            entry.dataframe = shared if entity_type == "offer" else other
            return entry

        cache = MagicMock()
        cache.get_async = _get_async

        with (
            patch("autom8_asana.lambda_handlers.story_warmer.emit_metric"),
            patch("autom8_asana.lambda_handlers.story_warmer.logger"),
        ):
            stats = await _warm_story_caches_for_completed_entities(
                completed_entities=["business"],
                get_project_gid=_project_gid,
                dataframe_cache=cache,
                client=_make_client(),
                invocation_id="cc5-cf3",
                context=None,
            )

        # offer runs FIRST, so it can never inherit a prior entity's GIDs --
        # CF-3's specific worry is structurally dissolved for the priority
        # entity, and the overlap surfaces on the follower instead.
        assert _receipt(stats, "offer")["shared_gids_with_prior"] == 0
        assert _receipt(stats, "business")["shared_gids_with_prior"] == 2


# --------------------------------------------------------------------------
# Order construction + operator lever
# --------------------------------------------------------------------------


class TestWarmOrderAndLever:
    def test_priority_leads_regardless_of_cascade_position(self) -> None:
        order = _build_warm_order(["a", "b", "offer", "c"], ("offer",))
        assert order[0] == ("offer", True)
        assert [e for e, _ in order] == ["offer", "a", "b", "c"]

    def test_priority_entity_absent_from_cascade_is_still_planned(self) -> None:
        order = _build_warm_order(["a", "b"], ("offer",))
        assert order == [("offer", True), ("a", False), ("b", False)]

    def test_empty_priority_preserves_pure_cascade_order(self) -> None:
        order = _build_warm_order(["a", "b", "offer"], ())
        assert order == [("a", False), ("b", False), ("offer", False)]

    def test_duplicates_are_collapsed(self) -> None:
        order = _build_warm_order(["offer", "offer", "a"], ("offer", "offer"))
        assert order == [("offer", True), ("a", False)]

    def test_default_priority_is_offers_only(self) -> None:
        """R-1 Tier-1 fence: the default must not smuggle a Tier-2 set."""
        assert DEFAULT_STORY_WARM_PRIORITY_ENTITIES == ("offer",)
        assert _resolve_priority_entities({}) == ("offer",)

    def test_empty_env_var_is_the_revert_lever(self) -> None:
        assert _resolve_priority_entities({STORY_WARM_PRIORITY_ENV_VAR: ""}) == ()

    def test_env_var_parses_list_with_whitespace_and_dupes(self) -> None:
        resolved = _resolve_priority_entities(
            {STORY_WARM_PRIORITY_ENV_VAR: " offer , contact ,offer, "}
        )
        assert resolved == ("offer", "contact")

    def test_concurrency_envelope_is_not_raised(self) -> None:
        """O-G fence tripwire.

        Raising concurrency re-enters the documented 429-storm surface and
        would confound any post-deploy AL-5 reading. If this constant is ever
        raised, that is a decision requiring its own ruling -- not a silent
        edit riding this sprint's diff.
        """
        assert _STORY_WARM_CONCURRENCY == 3
