"""Dispatch tests for push_orchestrator Lambda utility module.

Per SCAN-asana-deep-triage Task 4: Cold-start dispatch validation for
push_orchestrator.py. Validates module importability, function signatures,
error propagation (failures are isolated, never abort the warmer), and
that both GID push and account-status push paths work as documented.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestPushOrchestratorModuleInterface:
    """Module is importable and exposes expected interface."""

    def test_module_importable(self) -> None:
        import autom8_asana.lambda_handlers.push_orchestrator as mod

        assert mod is not None

    def test_push_gid_mappings_callable(self) -> None:
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        assert callable(_push_gid_mappings_for_completed_entities)

    def test_push_account_status_callable(self) -> None:
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        assert callable(_push_account_status_for_completed_entities)

    def test_all_exports_present(self) -> None:
        from autom8_asana.lambda_handlers import push_orchestrator

        assert "_push_gid_mappings_for_completed_entities" in push_orchestrator.__all__
        assert "_push_account_status_for_completed_entities" in push_orchestrator.__all__


class TestPushGidMappingsDispatch:
    """_push_gid_mappings_for_completed_entities dispatch validation."""

    async def test_empty_entities_is_noop(self) -> None:
        """No entities means no pushes, no errors."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        await _push_gid_mappings_for_completed_entities(
            completed_entities=[],
            get_project_gid=lambda _: None,
            cache=mock_cache,
            invocation_id="test-inv",
        )

        mock_cache.get_async.assert_not_awaited()

    async def test_entity_with_no_project_gid_skipped(self) -> None:
        """Entities where get_project_gid returns None are skipped."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        await _push_gid_mappings_for_completed_entities(
            completed_entities=["unit"],
            get_project_gid=lambda _: None,
            cache=mock_cache,
            invocation_id="test-inv",
        )

        mock_cache.get_async.assert_not_awaited()

    async def test_cache_miss_skipped_gracefully(self) -> None:
        """When cache returns None for a project, entity is skipped without error."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        with patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"):
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: "proj-001",
                cache=mock_cache,
                invocation_id="test-inv",
            )

        mock_cache.get_async.assert_awaited_once_with("proj-001", "unit")

    async def test_push_failure_does_not_propagate(self) -> None:
        """push_gid_mappings_to_data_service failure is isolated — must not raise."""
        import polars as pl

        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_gid_mappings_for_completed_entities,
        )

        mock_entry = MagicMock()
        mock_entry.dataframe = pl.DataFrame({"gid": ["123"], "office_phone": ["555"]})

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        mock_index = MagicMock()
        mock_index.__len__ = MagicMock(return_value=1)

        with (
            patch("autom8_asana.services.gid_lookup.GidLookupIndex") as mock_index_cls,
            patch(
                "autom8_asana.services.gid_push.push_gid_mappings_to_data_service",
                side_effect=Exception("push service down"),
            ),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"),
        ):
            mock_index_cls.from_dataframe.return_value = mock_index
            # Must not raise — failure is isolated per BROAD-CATCH: isolation
            await _push_gid_mappings_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: "proj-001",
                cache=mock_cache,
                invocation_id="test-inv",
            )


class TestPushAccountStatusDispatch:
    """_push_account_status_for_completed_entities dispatch validation."""

    async def test_empty_entities_is_noop(self) -> None:
        """No entities means no pushes, no errors."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        with patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"):
            await _push_account_status_for_completed_entities(
                completed_entities=[],
                get_project_gid=lambda _: None,
                cache=mock_cache,
                invocation_id="test-inv",
            )

        mock_cache.get_async.assert_not_awaited()

    async def test_entity_with_no_project_gid_skipped(self) -> None:
        """Entities where get_project_gid returns None are skipped."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=None)

        with patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"):
            await _push_account_status_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: None,
                cache=mock_cache,
                invocation_id="test-inv",
            )

        mock_cache.get_async.assert_not_awaited()

    async def test_unmapped_entity_surfaced_and_mapped_rows_still_pushed(self) -> None:
        """T3 (sprint-C6): warm-set vs PIPELINE_TYPE_BY_PROJECT_GID
        reconciliation -- an entity whose project GID is absent from the map is
        surfaced (WARNING + StatusPushUnmappedEntities), NOT silently accepted,
        and the mapped entity's rows are still pushed."""
        import polars as pl

        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        unit_gid = "1201081073731555"  # mapped -> pipeline_type "unit"
        offer_gid = "1143843662099250"  # absent from PIPELINE_TYPE_BY_PROJECT_GID
        gid_by_entity = {"unit": unit_gid, "offer": offer_gid}

        unit_df = pl.DataFrame(
            {
                "office_phone": ["+15551230001"],
                "vertical": ["chiropractor"],
                "section": ["Active"],
                # Non-marketing: activity is its own section, so the row pushes.
                "products": [["Videography"]],
            }
        )
        offer_df = pl.DataFrame(
            {
                "office_phone": ["+15551230002"],
                "vertical": ["chiropractor"],
                "section": ["ACTIVE"],
            }
        )
        frames = {unit_gid: unit_df, offer_gid: offer_df}

        def _make_entry(gid: str) -> MagicMock:
            entry = MagicMock()
            entry.dataframe = frames[gid]
            return entry

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(side_effect=lambda gid, et: _make_entry(gid))

        with (
            patch(
                "autom8_asana.services.gid_push.push_status_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_push,
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric") as mock_emit,
            patch("autom8_asana.lambda_handlers.push_orchestrator.logger") as mock_logger,
        ):
            await _push_account_status_for_completed_entities(
                completed_entities=["unit", "offer"],
                get_project_gid=gid_by_entity.get,
                cache=mock_cache,
                invocation_id="test-inv",
            )

        # WARNING status_push_registry_coverage with unmapped=["offer"]
        coverage_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args[0] == "status_push_registry_coverage"
        ]
        assert coverage_calls, "expected status_push_registry_coverage WARNING"
        extra = coverage_calls[0].kwargs["extra"]
        assert extra["mapped"] == ["unit"]
        assert extra["unmapped"] == ["offer"]
        assert extra["invocation_id"] == "test-inv"

        # StatusPushUnmappedEntities = 1 to the bridge fleet namespace
        unmapped_emits = [
            c for c in mock_emit.call_args_list if c.args[0] == "StatusPushUnmappedEntities"
        ]
        assert len(unmapped_emits) == 1
        assert unmapped_emits[0].args[1] == 1
        assert unmapped_emits[0].kwargs["namespace"] == "Autom8y/AsanaBridgeFleet"

        # Unit rows STILL pushed (the narrowing is surfaced, not fatal)
        mock_push.assert_awaited_once()
        pushed_entries = mock_push.call_args.kwargs["entries"]
        assert len(pushed_entries) == 1
        assert pushed_entries[0]["pipeline_type"] == "unit"

    async def test_all_mapped_entities_emit_zero_unmapped_and_no_warning(self) -> None:
        """Positive control: an all-mapped warm set produces NO coverage
        warning and StatusPushUnmappedEntities = 0."""
        import polars as pl

        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        unit_gid = "1201081073731555"
        unit_df = pl.DataFrame(
            {
                "office_phone": ["+15551230001"],
                "vertical": ["chiropractor"],
                "section": ["Active"],
            }
        )
        mock_entry = MagicMock()
        mock_entry.dataframe = unit_df
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with (
            patch(
                "autom8_asana.services.gid_push.push_status_to_data_service",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric") as mock_emit,
            patch("autom8_asana.lambda_handlers.push_orchestrator.logger") as mock_logger,
        ):
            await _push_account_status_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid={"unit": unit_gid}.get,
                cache=mock_cache,
                invocation_id="test-inv",
            )

        assert not [
            c
            for c in mock_logger.warning.call_args_list
            if c.args[0] == "status_push_registry_coverage"
        ], "positive control must not warn"
        unmapped_emits = [
            c for c in mock_emit.call_args_list if c.args[0] == "StatusPushUnmappedEntities"
        ]
        assert len(unmapped_emits) == 1
        assert unmapped_emits[0].args[1] == 0

    async def test_extract_failure_does_not_propagate(self) -> None:
        """Extraction failure per-entity is isolated — must not raise.

        Uses a non-unit entity so the patched extraction is actually reached
        (a unit frame first goes through the Unit activity step).
        """
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        mock_entry = MagicMock()
        mock_entry.dataframe = MagicMock()

        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with (
            patch(
                "autom8_asana.services.gid_push.extract_status_from_dataframe",
                side_effect=Exception("extraction failed"),
            ) as mock_extract,
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric"),
        ):
            # Must not raise — BROAD-CATCH: isolation
            await _push_account_status_for_completed_entities(
                completed_entities=["offer"],
                get_project_gid=lambda _: "proj-001",
                cache=mock_cache,
                invocation_id="test-inv",
            )

        mock_extract.assert_called_once()


# ---------------------------------------------------------------------------
# Unit activity at the push seam: computed once from the Unit and Offer frames
# ---------------------------------------------------------------------------


def _project_of(kind: str) -> str:
    from autom8_asana.services.gid_push import PIPELINE_TYPE_BY_PROJECT_GID

    return next(g for g, k in PIPELINE_TYPE_BY_PROJECT_GID.items() if k == kind)


def _frames_cache(frames: dict[str, object]):
    """A DataFrameCache fake (autospec) serving real entries by entity type."""
    from datetime import UTC, datetime
    from unittest.mock import create_autospec

    from autom8_asana.cache.integration.dataframe_cache import (
        DataFrameCache,
        DataFrameCacheEntry,
    )

    def _get(project_gid: str, entity_type: str, current_watermark=None):
        df = frames.get(entity_type)
        if df is None:
            return None
        now = datetime.now(UTC)
        return DataFrameCacheEntry(
            project_gid=project_gid,
            entity_type=entity_type,
            dataframe=df,
            watermark=now,
            created_at=now,
            schema_version="test",
        )

    cache = create_autospec(DataFrameCache, instance=True)
    cache.get_async.side_effect = _get
    return cache


def _gids(entity_type: str) -> str | None:
    known = {"unit": _project_of("unit"), "offer": "offer-project", "sales": _project_of("sales")}
    return known.get(entity_type)


async def _run_status_push_with_metrics(
    frames: dict[str, object], completed: tuple[str, ...] = ("unit", "offer")
):
    """Run the real orchestrator; return the push, logger and emit_metric mocks."""
    from unittest.mock import create_autospec

    from autom8y_log import LoggerProtocol

    from autom8_asana.lambda_handlers.push_orchestrator import (
        _push_account_status_for_completed_entities,
    )

    with (
        patch(
            "autom8_asana.services.gid_push.push_status_to_data_service",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_push,
        patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric") as emit,
        patch(
            "autom8_asana.lambda_handlers.push_orchestrator.logger",
            new=create_autospec(LoggerProtocol, instance=True),
        ) as log,
    ):
        await _push_account_status_for_completed_entities(
            completed_entities=list(completed),
            get_project_gid=_gids,
            cache=_frames_cache(frames),
            invocation_id="test-inv",
        )
    return mock_push, log, emit


async def _run_status_push(
    frames: dict[str, object], completed: tuple[str, ...] = ("unit", "offer")
):
    mock_push, log, _ = await _run_status_push_with_metrics(frames, completed)
    return mock_push, log


def _units():
    import polars as pl

    return pl.DataFrame(
        {
            "office_phone": ["+15550100001", "+15550100002"],
            "vertical": ["dental", "dental"],
            "section": ["Engaged", "Engaged"],
            "products": [["Meta Marketing"], ["Videography"]],
        }
    )


def _offers(sections: list[str]):
    import polars as pl

    return pl.DataFrame(
        {
            "office_phone": ["+15550100001"] * len(sections),
            "vertical": ["dental"] * len(sections),
            "section": sections,
        },
        schema={"office_phone": pl.Utf8, "vertical": pl.Utf8, "section": pl.Utf8},
    )


def _skip_reasons(log) -> list[str]:
    return [
        c.kwargs["extra"]["reason"]
        for c in log.warning.call_args_list
        if c.args[0] == "status_push_unit_activity_skipped"
    ]


class TestUnitActivityAtThePushSeam:
    async def test_marketing_unit_is_pushed_from_its_offers_not_its_section(self) -> None:
        """Both Units sit in Engaged; only the marketing one, read from its Offer, pushes."""
        mock_push, _ = await _run_status_push({"unit": _units(), "offer": _offers(["ACTIVE"])})

        mock_push.assert_awaited_once()
        entries = mock_push.call_args.kwargs["entries"]
        assert [(e["phone"], e["account_activity"]) for e in entries] == [
            ("+15550100001", "active")
        ]
        # The label still carries the Unit's own section (meaning shift, named in the PR).
        assert entries[0]["pipeline_section"] == "Engaged"

    async def test_unit_rows_are_left_out_without_an_offer_frame(self) -> None:
        mock_push, log = await _run_status_push({"unit": _units()})

        mock_push.assert_not_awaited()
        assert _skip_reasons(log) == ["offer_frame_unavailable"]

    async def test_unit_rows_are_left_out_on_an_empty_offer_frame(self) -> None:
        mock_push, log = await _run_status_push({"unit": _units(), "offer": _offers([])})

        mock_push.assert_not_awaited()
        assert len(_skip_reasons(log)) == 1
        assert "no rows" in _skip_reasons(log)[0]

    async def test_unit_rows_are_left_out_when_products_are_missing(self) -> None:
        mock_push, log = await _run_status_push(
            {"unit": _units().drop("products"), "offer": _offers(["ACTIVE"])}
        )

        mock_push.assert_not_awaited()
        assert len(_skip_reasons(log)) == 1
        assert "products" in _skip_reasons(log)[0]

    async def test_snapshot_is_withheld_not_pushed_without_its_unit_rows(self) -> None:
        """The receiver replaces the whole snapshot: other rows never go out alone."""
        import polars as pl

        sales = pl.DataFrame({"office_phone": ["+15550100003"], "section": ["ACTIVE"]})

        mock_push, log = await _run_status_push(
            {"unit": _units(), "sales": sales}, completed=("unit", "sales", "offer")
        )

        mock_push.assert_not_awaited()
        withheld = [
            c for c in log.warning.call_args_list if c.args[0] == "status_push_snapshot_withheld"
        ]
        assert len(withheld) == 1
        assert withheld[0].kwargs["extra"]["reason"] == "unit_activity_unavailable"
        assert withheld[0].kwargs["extra"]["entry_count"] == 1

    async def test_a_failing_unit_extraction_also_withholds_the_snapshot(self) -> None:
        """Any loss of the Unit rows withholds; the other entity's row is not pushed alone."""
        import polars as pl

        from autom8_asana.services import gid_push

        real_extract = gid_push.extract_status_from_dataframe

        def _extract(df, project_gid, entity_type):
            if entity_type == "unit":
                raise ValueError("unit extraction failed")
            return real_extract(df=df, project_gid=project_gid, entity_type=entity_type)

        sales = pl.DataFrame({"office_phone": ["+15550100003"], "section": ["ACTIVE"]})
        with patch(
            "autom8_asana.services.gid_push.extract_status_from_dataframe",
            autospec=True,
            side_effect=_extract,
        ):
            mock_push, log = await _run_status_push(
                {"unit": _units(), "offer": _offers(["ACTIVE"]), "sales": sales},
                completed=("unit", "sales", "offer"),
            )

        mock_push.assert_not_awaited()
        assert [
            c.kwargs["extra"]["entry_count"]
            for c in log.warning.call_args_list
            if c.args[0] == "status_push_snapshot_withheld"
        ] == [1]


def _skip_metric_reasons(emit) -> list[str]:
    """The skip_reason of every StatusPushSkipped emit, in order."""
    return [
        (c.kwargs.get("dimensions") or {}).get("skip_reason")
        for c in emit.call_args_list
        if c.args and c.args[0] == "StatusPushSkipped"
    ]


def _withheld_entry_counts(log) -> list[int]:
    return [
        c.kwargs["extra"]["entry_count"]
        for c in log.warning.call_args_list
        if c.args[0] == "status_push_snapshot_withheld"
    ]


def _sales():
    import polars as pl

    return pl.DataFrame({"office_phone": ["+15550100003"], "section": ["ACTIVE"]})


class TestUnitCacheMissWithholds:
    """A Unit cache miss loses the Unit rows: the other entity's rows never go out alone."""

    async def test_a_unit_cache_miss_withholds_the_snapshot_and_counts_it(self) -> None:
        mock_push, log, emit = await _run_status_push_with_metrics(
            {"offer": _offers(["ACTIVE"]), "sales": _sales()},
            completed=("unit", "sales", "offer"),
        )

        mock_push.assert_not_awaited()
        assert _skip_reasons(log) == ["unit_frame_unavailable"]
        assert _withheld_entry_counts(log) == [1]
        assert _skip_metric_reasons(emit) == ["unit_activity_unavailable"]

    async def test_a_unit_hit_pushes_with_the_other_entitys_rows(self) -> None:
        mock_push, log, emit = await _run_status_push_with_metrics(
            {"unit": _units(), "offer": _offers(["ACTIVE"]), "sales": _sales()},
            completed=("unit", "sales", "offer"),
        )

        mock_push.assert_awaited_once()
        entries = mock_push.call_args.kwargs["entries"]
        assert sorted((e["pipeline_type"], e["phone"]) for e in entries) == [
            ("sales", "+15550100003"),
            ("unit", "+15550100001"),
        ]
        assert _skip_reasons(log) == []
        assert _withheld_entry_counts(log) == []
        assert _skip_metric_reasons(emit) == []


# ---------------------------------------------------------------------------
# The products null share: a present but mostly-null column withholds
# ---------------------------------------------------------------------------


def _unit_population(null_products: int, total: int = 100):
    """``total`` marketing Units in Engaged, each with an ACTIVE Offer.

    The first ``null_products`` Units have a null ``products`` value. Every Unit
    has an ACTIVE Offer, so a null Unit that pushed would prove a guessed branch.
    """
    import polars as pl

    phones = [f"+1555010{i:04d}" for i in range(total)]
    units = pl.DataFrame(
        {
            "office_phone": phones,
            "vertical": ["dental"] * total,
            "section": ["Engaged"] * total,
            "products": [None] * null_products + [["Meta Marketing"]] * (total - null_products),
        },
        schema={
            "office_phone": pl.Utf8,
            "vertical": pl.Utf8,
            "section": pl.Utf8,
            "products": pl.List(pl.Utf8),
        },
    )
    offers = pl.DataFrame(
        {"office_phone": phones, "vertical": ["dental"] * total, "section": ["ACTIVE"] * total},
        schema={"office_phone": pl.Utf8, "vertical": pl.Utf8, "section": pl.Utf8},
    )
    return units, offers, phones


class TestProductsNullShare:
    """Refuse when more than half the Units have null products (exactly half passes)."""

    async def test_a_present_all_null_column_is_withheld_and_counted(self) -> None:
        units, offers, _ = _unit_population(null_products=100)
        assert "products" in units.columns

        mock_push, log, emit = await _run_status_push_with_metrics({"unit": units, "offer": offers})

        mock_push.assert_not_awaited()
        assert _skip_reasons(log) == [
            "products is null for 100 of 100 units, more than the 50% limit"
        ]
        assert _withheld_entry_counts(log) == [0]
        assert _skip_metric_reasons(emit) == ["unit_activity_unavailable"]

    async def test_just_over_the_limit_is_withheld(self) -> None:
        units, offers, _ = _unit_population(null_products=51)

        mock_push, log, emit = await _run_status_push_with_metrics({"unit": units, "offer": offers})

        mock_push.assert_not_awaited()
        assert _skip_reasons(log) == [
            "products is null for 51 of 100 units, more than the 50% limit"
        ]
        assert _skip_metric_reasons(emit) == ["unit_activity_unavailable"]

    async def test_exactly_half_null_is_at_the_limit_and_pushes(self) -> None:
        """The boundary: 50 of 100 is not MORE than half, so the frame is read."""
        units, offers, phones = _unit_population(null_products=50)

        mock_push, log, emit = await _run_status_push_with_metrics({"unit": units, "offer": offers})

        mock_push.assert_awaited_once()
        entries = mock_push.call_args.kwargs["entries"]
        assert sorted(e["phone"] for e in entries) == phones[50:]
        assert {e["account_activity"] for e in entries} == {"active"}
        assert _skip_reasons(log) == []
        assert _skip_metric_reasons(emit) == []

    async def test_just_under_the_limit_pushes_and_null_units_get_no_activity(self) -> None:
        units, offers, phones = _unit_population(null_products=49)

        mock_push, log, emit = await _run_status_push_with_metrics({"unit": units, "offer": offers})

        mock_push.assert_awaited_once()
        pushed = sorted(e["phone"] for e in mock_push.call_args.kwargs["entries"])
        assert pushed == phones[49:]
        assert set(pushed).isdisjoint(phones[:49])
        assert _skip_reasons(log) == []
        assert _skip_metric_reasons(emit) == []

    async def test_a_real_shape_mix_pushes_every_resolved_unit_and_no_null_one(self) -> None:
        """Mostly marketing, a few non-marketing, many with no products, two null."""
        import polars as pl

        marketing = ["Meta Marketing"]
        rows: list[tuple[str, str, list[str] | None, str | None]] = [
            # (phone last-4, own section, products, Offer section)
            ("0201", "Engaged", marketing, "ACTIVE"),
            ("0202", "Active", marketing, "ACTIVE"),
            ("0203", "Month 1", marketing, "STAGED"),
            ("0204", "Engaged", marketing, "MANUAL"),
            ("0205", "Scheduled", marketing, "ACTIVE"),
            ("0206", "Paused", marketing, "OPTIMIZE - Human Review"),
            ("0207", "Onboarding", marketing, "IMPLEMENTING"),
            ("0208", "Engaged", marketing, "NEW LAUNCH REVIEW"),
            ("0209", "Active", marketing, "INACTIVE"),
            ("0210", "Active", marketing, None),
            ("0211", "Active", ["Videography"], "INACTIVE"),
            ("0212", "Month 1", [], None),
            ("0213", "Active", [], None),
            ("0214", "Consulting", [], None),
            ("0215", "Onboarding", [], None),
            ("0216", "Delayed", [], None),
            ("0217", "Paused", [], None),
            ("0218", "Cancelled", [], None),
            ("0219", "Active", None, "ACTIVE"),
            ("0220", "Onboarding", None, "IMPLEMENTING"),
        ]
        phone = "+1555010{}".format
        units = pl.DataFrame(
            {
                "office_phone": [phone(r[0]) for r in rows],
                "vertical": ["dental"] * len(rows),
                "section": [r[1] for r in rows],
                "products": [r[2] for r in rows],
            },
            schema={
                "office_phone": pl.Utf8,
                "vertical": pl.Utf8,
                "section": pl.Utf8,
                "products": pl.List(pl.Utf8),
            },
        )
        offer_rows = [(phone(r[0]), r[3]) for r in rows if r[3] is not None]
        offers = pl.DataFrame(
            {
                "office_phone": [p for p, _ in offer_rows],
                "vertical": ["dental"] * len(offer_rows),
                "section": [s for _, s in offer_rows],
            },
            schema={"office_phone": pl.Utf8, "vertical": pl.Utf8, "section": pl.Utf8},
        )

        mock_push, log, emit = await _run_status_push_with_metrics({"unit": units, "offer": offers})

        mock_push.assert_awaited_once()
        pushed = {e["phone"]: e["account_activity"] for e in mock_push.call_args.kwargs["entries"]}
        assert pushed == {
            phone("0201"): "active",
            phone("0202"): "active",
            phone("0203"): "active",
            phone("0204"): "active",
            phone("0205"): "active",
            phone("0206"): "active",
            phone("0207"): "activating",
            phone("0208"): "activating",
            phone("0211"): "active",
            phone("0212"): "active",
            phone("0213"): "active",
            phone("0214"): "active",
            phone("0215"): "activating",
            phone("0216"): "activating",
        }
        assert phone("0219") not in pushed
        assert phone("0220") not in pushed
        assert _skip_reasons(log) == []
        assert _skip_metric_reasons(emit) == []
